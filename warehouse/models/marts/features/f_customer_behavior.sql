with base_events as (
    select * from main.raw_transactions
),

calculated_windows as (
    select
        customer_id,
        event_ts,
        ingested_ts,
        -- Force legal temporal availability to occur only after ingestion processing completes
        greatest(event_ts, ingested_ts) as valid_from,
        amount,

        -- Using our dynamic macro to cleanly calculate historical profiles
        {{ rolling_feature('amount', 'customer_id', 'event_ts', 1, 'count') }} as txn_count_1d,
        {{ rolling_feature('amount', 'customer_id', 'event_ts', 7, 'sum') }} as spend_7d,
        {{ rolling_feature('amount', 'customer_id', 'event_ts', 30, 'avg') }} as avg_amount_30d

    from base_events
)

select 
    customer_id,
    valid_from,
    cast(txn_count_1d as integer) as txn_count_1d,
    cast(spend_7d as double precision) as spend_7d,
    cast(avg_amount_30d as double precision) as avg_amount_30d
from calculated_windows

