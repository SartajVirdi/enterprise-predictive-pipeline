import os
import csv
import random
from datetime import datetime, timedelta

def main():
    print("Generating mock dataset...")
    os.makedirs("data", exist_ok=True)
    
    customers = []
    segments = ["RETAIL", "CORP", "VIP", "SMB"]
    countries = ["IN", "US", "UK", "AE", "SG"]
    
    # Generate 100 Customers
    start_date = datetime(2026, 1, 1)
    for i in range(1, 101):
        cust_id = f"CUST_{i:03d}"
        signup = start_date + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        customers.append([cust_id, signup.strftime("%Y-%m-%d %H:%M:%S"), random.choice(countries), random.choice(segments)])
        
    with open("data/raw_customers.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_id", "signup_timestamp", "country", "segment"])
        writer.writerows(customers)
        
    # Generate 5000 Transactions
    tx_status = ["SUCCESS", "SUCCESS", "SUCCESS", "FAILED"]
    transactions = []
    tx_time = datetime(2026, 2, 1)
    
    for i in range(1, 5001):
        tx_id = f"TXN_{i:05d}"
        cust_id = f"CUST_{random.randint(1, 100):03d}"
        
        # Step out-of-order execution chunks occasionally
        tx_time += timedelta(minutes=random.randint(1, 15))
        event_ts = tx_time
        
        # Random ingestion delay (1 min to 4 hours)
        delay = timedelta(minutes=random.randint(1, 240))
        ingested_ts = event_ts + delay
        
        amount = round(random.uniform(5.0, 10000.0), 2)
        status = random.choice(tx_status)
        
        transactions.append([tx_id, cust_id, event_ts.strftime("%Y-%m-%d %H:%M:%S"), ingested_ts.strftime("%Y-%m-%d %H:%M:%S"), amount, status])
        
    with open("data/raw_transactions.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_id", "customer_id", "event_ts", "ingested_ts", "amount", "status"])
        writer.writerows(transactions)
        
    print("Successfully generated data/raw_customers.csv and data/raw_transactions.csv!")

if __name__ == "__main__":
    main()

