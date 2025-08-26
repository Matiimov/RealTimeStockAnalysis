{{ config(schema='rtsa_gold', materialized='view') }}

with base as (
  select group_name, day, avg_price
  from {{ ref('gold_grouped_avg_daily') }}
),
returns as (
  select
    group_name,
    day,
    avg_price,
    (avg_price / lag(avg_price, 7)  over (partition by group_name order by day) - 1) * 100 as return_7d,
    (avg_price / lag(avg_price, 30) over (partition by group_name order by day) - 1) * 100 as return_30d,
    (avg_price / lag(avg_price, 90) over (partition by group_name order by day) - 1) * 100 as return_90d
  from base
)
select * from returns