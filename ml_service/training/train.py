import os
import duckdb
import pandas as pd
import xgboost as xgb
from datetime import datetime

def main():
    print("🚀 Phase 3: Commencing Offline Dataset Build & Model Training...")
    db_path = "warehouse.db"
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database {db_path} not found! Run dbt run first.")
        
    # 1. Establish connection to our analytical DuckDB warehouse
    conn = duckdb.connect(db_path)
    
    # 2. Synthesize Ground-Truth Labels in-memory to simulate historical events
    print("📋 Creating transaction labels table for historical evaluation...")
    conn.execute("""
        CREATE OR REPLACE TEMP TABLE target_labels AS 
        SELECT 
            transaction_id,
            customer_id,
            event_ts AS target_timestamp,
            -- Mock deterministic label rule: High amounts on FAILED txns flagged as fraud
            CASE WHEN amount > 8000 AND status = 'FAILED' THEN 1 ELSE 0 END AS is_fraud
        FROM main.raw_transactions;
    """)

    # 3. Execute Point-In-Time Correlated Subquery using LEFT JOIN LATERAL
    # INTERVIEW KNOWLEDGE: This correlates each target timestamp with the absolute latest
    # available feature calculation state *strictly before or equal to* that instance.
    print("🔍 Executing Point-in-Time As-Of Join via SQL LATERAL seek...")
    training_query = """
        SELECT 
            t.transaction_id,
            t.customer_id,
            t.target_timestamp,
            f.txn_count_1d,
            f.spend_7d,
            f.avg_amount_30d,
            t.is_fraud
        FROM target_labels t
        LEFT JOIN LATERAL (
            SELECT 
                txn_count_1d,
                spend_7d,
                avg_amount_30d
            FROM main.f_customer_behavior f
            WHERE f.customer_id = t.customer_id
              AND f.valid_from <= t.target_timestamp
            ORDER BY f.valid_from DESC
            LIMIT 1
        ) f ON TRUE;
    """
    
    df = conn.execute(training_query).fetchdf()
    print(f"📊 Gathered {len(df)} rows for the training matrix.")
    
    # 4. Gracefully Handle Cold-Start Nulls & Impute Features
    print("🛠️ Imputing missing metrics for cold-start customer vectors...")
    
    # Explicit indicator flag telling XGBoost if the system has zero transaction history
    df['is_imputed'] = df['txn_count_1d'].isna().astype(int)
    
    # Standard numerical fills
    df['txn_count_1d'] = df['txn_count_1d'].fillna(0).astype(int)
    df['spend_7d'] = df['spend_7d'].fillna(0.0).astype(float)
    df['avg_amount_30d'] = df['avg_amount_30d'].fillna(0.0).astype(float)
    
    # 5. Extract Feature Matrix and Target Array
    feature_cols = ['txn_count_1d', 'spend_7d', 'avg_amount_30d', 'is_imputed']
    X = df[feature_cols]
    y = df['is_fraud']
    
    print(f"🌲 Training features being evaluated: {feature_cols}")
    print(f"⚖️ Fraud Class Balance: \n{y.value_counts()}")
    
    # Convert matrix to XGBoost highly optimized input format
    dtrain = xgb.DMatrix(X, label=y)
    
    # 6. Fit XGBoost Model Classifier
    params = {
        'max_depth': 5,
        'eta': 0.1,
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'seed': 42
    }
    
    print("🏋️ Training XGBoost model ensemble...")
    bst = xgb.train(params, dtrain, num_boost_round=50)
    
    # 7. Serialize Artifacts out of memory to local file path
    os.makedirs("ml_service/models/artifacts", exist_ok=True)
    model_output_path = "ml_service/models/artifacts/fraud_model.json"
    bst.save_model(model_output_path)
    
    print(f"💾 Success! XGBoost model saved cleanly to: {model_output_path}")
    conn.close()

if __name__ == "__main__":
    main()

