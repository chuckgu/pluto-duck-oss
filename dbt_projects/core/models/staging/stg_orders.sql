{{ config(materialized='view') }}

with source as (
    select
        order_id,
        customer_name,
        total_amount,
        order_timestamp
    from {{ source('raw', 'orders') }}
)

select
    order_id,
    customer_name,
    total_amount,
    order_timestamp
from source

