import duckdb
import os

def main():
    print("Initializing DuckDB analytical warehouse...")
    db_path = "warehouse.db"
    
    # Check if CSV files exist before attempting ingestion
    if not os.path.exists("data/raw_customers.csv") or not os.path.exists("data/raw_transactions.csv"):
        raise FileNotFoundError("CSV files not found. Run generate_mock_data.py first.")
        
    # Connect to DuckDB (this creates warehouse.db automatically if it doesn't exist)
    conn = duckdb.connect(db_path)
    
    # Create the main schema explicitly
    conn.execute("CREATE SCHEMA IF NOT EXISTS main;")
    
    print("Ingesting raw_customers.csv into database...")
    conn.execute("""
        CREATE OR REPLACE TABLE main.raw_customers AS 
        SELECT * FROM read_csv_auto('data/raw_customers.csv');
    """)
    
    print("Ingesting raw_transactions.csv into database...")
    conn.execute("""
        CREATE OR REPLACE TABLE main.raw_transactions AS 
        SELECT * FROM read_csv_auto('data/raw_transactions.csv');
    """)
    
    # Audit row counts to verify successful load
    customer_count = conn.execute("SELECT COUNT(*) FROM main.raw_customers;").fetchone()[0]
    transaction_count = conn.execute("SELECT COUNT(*) FROM main.raw_transactions;").fetchone()[0]
    
    print(f"\nWarehouse Initialized Successfully!")
    print(f" -> Table 'main.raw_customers' populated with {customer_count} rows.")
    print(f" -> Table 'main.raw_transactions' populated with {transaction_count} rows.")
    
    conn.close()

if __name__ == "__main__":
    main()

