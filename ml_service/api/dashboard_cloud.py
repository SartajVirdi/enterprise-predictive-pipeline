import streamlit as st
import duckdb
import pandas as pd
import xgboost as xgb
from pydantic import BaseModel, Field

# ── Cloud-deployment variant ──────────────────────────────────────────
# Runs the same inference logic as ml_service/api/app.py, but in-process
# instead of over HTTP — Streamlit Community Cloud only runs one process,
# so there's no separate FastAPI backend to call out to here.
# Local development should still use dashboard.py + `make serve`.
# ───────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Enterprise Fraud Analytics Platform",
    layout="wide"
)

DB_PATH = "warehouse_demo.db"
MODEL_PATH = "ml_service/models/artifacts/fraud_model.json"

st.title("Enterprise Fraud Analytics Platform")
st.caption("Production telemetry dashboard monitoring real-time point-in-time dbt SQL feature stores.")
st.markdown("---")


# 1. Feature contract — same schema as the FastAPI service
class CustomerFeatureSchema(BaseModel):
    customer_id: str
    txn_count_1d: int = Field(..., ge=0)
    spend_7d: float = Field(..., ge=0.0)
    avg_amount_30d: float = Field(..., ge=0.0)
    is_imputed: int = Field(..., description="1 if cold-start customer, 0 if historical data exists")


# 2. Load the model once per container lifecycle
@st.cache_resource
def load_model():
    model = xgb.Booster()
    model.load_model(MODEL_PATH)
    return model


# 3. Fetch available customers for the dropdown
@st.cache_data
def get_customer_list():
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        df = conn.execute(
            "SELECT DISTINCT customer_id FROM main.f_customer_behavior ORDER BY customer_id;"
        ).fetchdf()
        conn.close()
        return list(df["customer_id"])
    except Exception:
        return [f"CUST_{i:03d}" for i in range(1, 101)]


# 4. Same prediction logic as app.py's /api/v1/predict/fraud endpoint,
#    called directly instead of over the network.
def predict_fraud(customer_id: str, model: xgb.Booster) -> dict:
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

    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        result = conn.execute(query, [customer_id]).fetchone()
    finally:
        conn.close()

    if not result:
        validated_features = CustomerFeatureSchema(
            customer_id=customer_id,
            txn_count_1d=0,
            spend_7d=0.0,
            avg_amount_30d=0.0,
            is_imputed=1
        )
    else:
        validated_features = CustomerFeatureSchema(
            customer_id=str(result[0]),
            txn_count_1d=int(result[1]),
            spend_7d=float(result[2]),
            avg_amount_30d=float(result[3]),
            is_imputed=0
        )

    input_df = pd.DataFrame([{
        "txn_count_1d": validated_features.txn_count_1d,
        "spend_7d": validated_features.spend_7d,
        "avg_amount_30d": validated_features.avg_amount_30d,
        "is_imputed": validated_features.is_imputed
    }])

    dmatrix = xgb.DMatrix(input_df)
    raw_prediction = model.predict(dmatrix)

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


model_artifact = load_model()
customer_options = get_customer_list()
customer_options.append("CUST_999 (Cold-Start Simulation)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Simulation Parameters")
    selected_customer = st.selectbox("Target Customer Entity ID", options=customer_options)
    customer_id_clean = selected_customer.split(" ")[0]

    st.markdown("""
    **Pipeline Context:**
    Triggering evaluation queries the active DuckDB table instance for pre-calculated rolling window aggregates
    before routing feature structures through the Pydantic type validation contract layer into the inference engine.
    """)
    trigger_inference = st.button("Execute Risk Evaluation", type="primary")

with col2:
    st.subheader("Model Inference Telemetry")

    if trigger_inference:
        with st.spinner("Processing execution pipeline metrics..."):
            try:
                data = predict_fraud(customer_id_clean, model_artifact)

                prob = data["fraud_probability"]
                action = data["action"]
                is_cold = data["is_imputed_cold_start"]

                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric(label="Calculated Risk Probability", value=f"{prob * 100:.2f}%")
                with m2:
                    if action == "BLOCK":
                        st.error(f"SYSTEM ACTION: {action}")
                    else:
                        st.success(f"SYSTEM ACTION: {action}")
                with m3:
                    st.metric(label="Cold-Start Vector Status", value="Imputed" if is_cold else "Active Ledger")

                st.markdown("---")
                st.markdown("##### Consumed Database Feature Store Matrix")
                features = data["engineered_features_consumed"]

                feat_df = pd.DataFrame([{
                    "Transaction Volume (Past 24 Hours)": f"{int(features['txn_count_1d']):,}",
                    "Aggregated Value Velocity (Past 7 Days)": f"${features['spend_7d']:,.2f}",
                    "Moving Arithmetic Mean (Past 30 Days)": f"${features['avg_amount_30d']:,.2f}"
                }])

                st.table(feat_df.T.rename(columns={0: "Warehouse Compiled Metric"}))

            except Exception as e:
                st.error(f"Inference Failure. Details: {str(e)}")
    else:
        st.info("Awaiting execution trigger parameter from input controller module.")
