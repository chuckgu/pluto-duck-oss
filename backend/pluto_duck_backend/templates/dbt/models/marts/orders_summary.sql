{{ config(materialized='table') }}

select
    customer_name,
    count(*) as orders_count,
    sum(total_amount) as total_spent
from {{ ref('stg_orders') }}
group by 1

