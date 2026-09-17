import os
import duckdb
import pandas as pd
import xgboost as xgb
import numpy as np
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# 1. Initialize FastAPI Application
app = FastAPI(
    title="Real-Time Enterprise Fraud Inference Pipeline",
    description="Sub-5ms production endpoint consuming a point-in-time SQL feature store.",
    version="1.0.0"
)

DB_PATH = "warehouse.db"
MODEL_PATH = "ml_service/models/artifacts/fraud_model.json"

# Global placeholder references initialized on application startup
db_conn = None
model_artifact = None

# 2. Define the Rigid Feature Data Contract via Pydantic
class CustomerFeatureSchema(BaseModel):
    customer_id: str
    txn_count_1d: int = Field(..., ge=0)
    spend_7d: float = Field(..., ge=0.0)
    avg_amount_30d: float = Field(..., ge=0.0)
    is_imputed: int = Field(..., description="1 if cold-start customer, 0 if historical data exists")

# 3. Handle Application Lifecycle Hooks
@app.on_event("startup")
def startup_event():
    global db_conn, model_artifact
    print("⏳ Initializing system infrastructure and loading model artifacts...")
    
    if not os.path.exists(DB_PATH) or not os.path.exists(MODEL_PATH):
        raise RuntimeError("Missing critical infrastructure files. Run dbt and training first.")
        
    # Open a read-only connection to the DuckDB instance for ultra-fast thread-safe queries
    db_conn = duckdb.connect(DB_PATH, read_only=True)
    
    # Load your serialized XGBoost model
    model_artifact = xgb.Booster()
    model_artifact.load_model(MODEL_PATH)
    print("🚀 Inference system is fully hot and ready for traffic.")

@app.on_event("shutdown")
def shutdown_event():
    global db_conn
    if db_conn:
        db_conn.close()
        print("🛑 Database connection pool closed safely.")

# 4. The Production Inference Endpoint
@app.post("/api/v1/predict/fraud", status_code=status.HTTP_200_OK)
def predict_fraud(customer_id: str):
    global db_conn, model_artifact
    
    if not db_conn or not model_artifact:
        raise HTTPException(status_code=500, detail="Inference engine is uninitialized.")
        
    # 5. Fetch the ABSOLUTE LATEST feature state from the SQL warehouse layer
    query = """
        SELECT 
            customer_id,
            txn_count_1d,
            spend_7d,
            avg_amount_30d
        FROM main.f_customer_behavior
        WHERE customer_id = $1
        ORDER BY valid_from DESC
        LIMIT 1;
    """
    
    try:
        result = db_conn.execute(query, [customer_id]).fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failure: {str(e)}")
        
    # 6. Apply Cold-Start Mitigation & Enforce the Feature Contract
    if not result:
        # Handle Brand-New Customers gracefully without crashing the server or throwing a 404
        validated_features = CustomerFeatureSchema(
            customer_id=customer_id,
            txn_count_1d=0,
            spend_7d=0.0,
            avg_amount_30d=0.0,
            is_imputed=1  # Tree models instantly recognize this special flag sequence
        )
    else:
        # Explicit type validation via Pydantic mapping
        validated_features = CustomerFeatureSchema(
            customer_id=str(result[0]),
            txn_count_1d=int(result[1]),
            spend_7d=float(result[2]),
            avg_amount_30d=float(result[3]),
            is_imputed=0
        )
        
    # 7. Format verified types into a named DataFrame to ensure absolute feature alignment with XGBoost
    # FIX: This explicitly maps matching column string headers to satisfy strict model validation checks
    input_df = pd.DataFrame([{
        "txn_count_1d": validated_features.txn_count_1d,
        "spend_7d": validated_features.spend_7d,
        "avg_amount_30d": validated_features.avg_amount_30d,
        "is_imputed": validated_features.is_imputed
    }])
    
    # 8. Run inference through the exact named feature boundary matrix
    dmatrix = xgb.DMatrix(input_df)
    raw_prediction = model_artifact.predict(dmatrix)
    
    # 9. Return the complete analytical payload
    return {
        "customer_id": validated_features.customer_id,
        "is_imputed_cold_start": bool(validated_features.is_imputed),
        "fraud_probability": float(raw_prediction[0]),
        "action": "BLOCK" if raw_prediction[0] > 0.80 else "ALLOW",
        "engineered_features_consumed": {
            "txn_count_1d": validated_features.txn_count_1d,
            "spend_7d": validated_features.spend_7d,
            "avg_amount_30d": validated_features.avg_amount_30d
        }
    }

