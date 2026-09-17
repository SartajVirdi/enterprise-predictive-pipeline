<div align="center">

# 🛡️ Enterprise Fraud Analytics Platform

**A real-time fraud detection pipeline built around a point-in-time SQL feature store.**

All feature engineering lives in dbt models on top of DuckDB — the exact same logic runs at training time and at inference time, so there's no train/serve skew.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20App-FF4B4B?logo=streamlit&logoColor=white)](https://enterprise-fraud-analytics.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![dbt](https://img.shields.io/badge/dbt-Core-FF694B?logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-Model-red)](https://xgboost.readthedocs.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[→ Try the live dashboard](https://enterprise-fraud-analytics.streamlit.app)**

</div>

---

## 📖 Table of Contents

- [Screenshots](#-screenshots)
- [How It Works](#-how-it-works)
- [Highlights](#-highlights)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Tech Stack](#-tech-stack)
- [License](#-license)

---

## 🖼️ Screenshots

**Live risk evaluation against the feature store**

![Dashboard with an active customer](assets/im1.png)

**Cold-start path — unseen customer, imputed feature vector**

![Cold-start simulation](assets/im2.png)

---

## ⚙️ How It Works

```
raw_transactions (DuckDB)
        │
        ▼
     dbt Core            →  rolling-window features (1-µs leakage guard)
        │
        ▼
 f_customer_behavior      ← canonical feature table
        │
   ┌────┴────┐
   ▼         ▼
train.py   FastAPI
(XGBoost)  (live inference)
              │
              ▼
        Streamlit dashboard
```

---

## ✨ Highlights

| | |
|---|---|
| 🧮 **Feature engineering** | dbt models compute rolling transaction aggregates (spend, volume, averages) per customer |
| 🚧 **Leakage prevention** | Rolling windows are clamped to end 1 microsecond before the current transaction, so a row's own features never leak into its own label |
| 🏋️ **Training** | `train.py` reconstructs point-in-time correct feature snapshots with a `LEFT JOIN LATERAL` and fits an XGBoost classifier |
| ⚡ **Serving** | A FastAPI endpoint validates every request against a Pydantic schema and returns a fraud probability in real time |
| ❄️ **Cold start** | New customers with no transaction history get an imputed zero-vector and a flag (`is_imputed`), instead of a crash |
| 📊 **Dashboard** | A Streamlit UI lets you pick a customer, trigger a live prediction, and see the exact features the model consumed |

---

## 📂 Project Structure

```
enterprise-predictive-pipeline/
├── warehouse/                     # dbt models — the feature store
│   ├── macros/rolling_window.sql
│   └── models/
│       ├── staging/stg_transactions.sql
│       └── marts/features/f_customer_behavior.sql
├── ml_service/
│   ├── training/train.py          # point-in-time training + XGBoost fit
│   ├── models/artifacts/          # serialized model
│   └── api/
│       ├── app.py                 # FastAPI inference endpoint
│       ├── dashboard.py           # Streamlit dashboard (local, calls the API)
│       └── dashboard_cloud.py     # Streamlit dashboard (deployed, in-process)
├── assets/                        # README screenshots
├── generate_mock_data.py          # synthetic transaction data
├── init_warehouse.py              # loads raw data into DuckDB
├── warehouse_demo.db              # bundled demo database for the live app
├── dbt_project.yml
├── profiles.yml
├── Makefile
├── requirements.txt               # slim deps for the deployed dashboard
└── requirements-dev.txt           # full local stack (dbt, FastAPI, uvicorn)
```

---

## 🚀 Getting Started

```bash
# 1. Set up the environment and load raw data
make init
make warehouse

# 2. Build the dbt feature store
make build

# 3. Train the model
make train

# 4. Run the app (two terminals)
make serve       # FastAPI backend  → http://127.0.0.1:8000
make dashboard   # Streamlit UI     → http://localhost:8501
```

API docs (Swagger UI) are available at `http://127.0.0.1:8000/docs` once the backend is running.

> **Note on the two dashboards:** `dashboard.py` is the local development version — it calls the FastAPI service over HTTP, keeping the two layers decoupled. `dashboard_cloud.py` is the deployed variant: Streamlit Community Cloud runs a single process, so it executes the same inference logic in-process instead of over the network.

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| Feature store | dbt Core + DuckDB |
| Model | XGBoost |
| API | FastAPI + Pydantic |
| Dashboard | Streamlit |

---

## 📜 License

MIT — see [LICENSE](LICENSE).
