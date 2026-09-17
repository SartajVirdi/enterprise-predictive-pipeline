import streamlit as st
import requests
import duckdb
import pandas as pd

# Configure professional minimalist workspace layout
st.set_page_config(
    page_title="Enterprise Fraud Analytics Platform",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"
DB_PATH = "warehouse.db"

st.title("Enterprise Fraud Analytics Platform")
st.caption("Production telemetry dashboard monitoring real-time point-in-time dbt SQL feature stores.")
st.markdown("---")

# 1. Fetch available customers out of the database warehouse index
@st.cache_data
def get_customer_list():
    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        df = conn.execute("SELECT DISTINCT customer_id FROM main.f_customer_behavior ORDER BY customer_id;").fetchdf()
        conn.close()
        return list(df["customer_id"])
    except Exception:
        return [f"CUST_{i:03d}" for i in range(1, 101)]

customer_options = get_customer_list()
customer_options.append("CUST_999 (Cold-Start Simulation)")

# 2. Section Partitioning (Explicitly passing 2 to fix the required spec layout argument)
col1, col2 = st.columns(2)

with col1:
    st.subheader("Simulation Parameters")
    selected_customer = st.selectbox("Target Customer Entity ID", options=customer_options)
    
    # Safely isolate the string token text from the dropdown array element selection
    customer_id_clean = selected_customer.split(" ")[0]
    
    st.markdown("""
    **Pipeline Context:**
    Triggering evaluation queries the active DuckDB table instance for pre-calculated rolling window aggregates 
    before routing feature structures through the Pydantic type validation contract layer into FastAPI.
    """)
    trigger_inference = st.button("Execute Risk Evaluation", type="primary")

with col2:
    st.subheader("Model Inference Telemetry")
    
    if trigger_inference:
        with st.spinner("Processing execution pipeline metrics..."):
            try:
                # Isolate target endpoint string into a clean, un-nested variable to avoid character formatting bugs
                endpoint_url = f"{API_URL}/api/v1/predict/fraud?customer_id={customer_id_clean}"
                response = requests.post(endpoint_url, json={})
                
                if response.status_code == 200:
                    data = response.json()
                    
                    prob = data["fraud_probability"]
                    action = data["action"]
                    is_cold = data["is_imputed_cold_start"]
                    
                    # 3. Clean Corporate Scoring Cards Grid
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
                    
                    # 4. Display Formatted Structural SQL Features Matrix
                    st.markdown("##### Consumed Database Feature Store Matrix")
                    features = data["engineered_features_consumed"]
                    
                    feat_df = pd.DataFrame([{
                        "Transaction Volume (Past 24 Hours)": f"{int(features['txn_count_1d']):,}",
                        "Aggregated Value Velocity (Past 7 Days)": f"${features['spend_7d']:,.2f}",
                        "Moving Arithmetic Mean (Past 30 Days)": f"${features['avg_amount_30d']:,.2f}"
                    }])
                    
                    st.table(feat_df.T.rename(columns={0: "Warehouse Compiled Metric"}))
                    
                else:
                    st.error(f"Inference Ingestion Failure. API Code: {response.status_code}")
                    st.text(response.text)
                    
            except Exception as e:
                st.error(f"Network Connection Disruption. Verify backend service is hot. Details: {str(e)}")
    else:
        st.info("Awaiting execution trigger parameter from input controller module.")
