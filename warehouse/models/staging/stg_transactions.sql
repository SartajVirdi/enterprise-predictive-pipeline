select
    cast(transaction_id as varchar) as transaction_id,
    cast(customer_id as varchar) as customer_id,
    cast(event_ts as timestamp) as event_ts,
    cast(ingested_ts as timestamp) as ingested_ts,
    cast(amount as double precision) as amount,
    cast(status as varchar) as status
from main.raw_transactions
where transaction_id is not null

