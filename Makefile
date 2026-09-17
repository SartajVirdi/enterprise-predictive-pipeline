.PHONY: init warehouse build train serve dashboard clean

# 1. Automatic Python virtual workspace configuration
init:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt && pip install streamlit

# 2. Ingest raw logs and build DuckDB schema
warehouse:
	. .venv/bin/activate && python3 generate_mock_data.py && python3 init_warehouse.py

# 3. Compile dbt models
build:
	. .venv/bin/activate && dbt run --profiles-dir .

# 4. Execute Point-In-Time SQL training loop
train:
	. .venv/bin/activate && python3 ml_service/training/train.py

# 5. Boot backend API microservice
serve:
	. .venv/bin/activate && uvicorn ml_service.api.app:app --reload

# 6. Launch polished analytical dashboard
dashboard:
	. .venv/bin/activate && streamlit run ml_service/api/dashboard.py

# 7. Complete automated data stream refresh loop
pipeline: warehouse build train

