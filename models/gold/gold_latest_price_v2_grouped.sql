{{ config(schema='rtsa_gold', materialized='view') }}

with latest as (
  select *
  from {{ ref('gold_latest_price_v2') }}
),
sg as (
  select symbol_v, group_id, group_name
  from {{ ref('symbol_groups') }}
)

select
  sg.group_id,
  sg.group_name,
  max(latest.event_time)   as latest_event_time,
  avg(latest.price)        as avg_price,
  count(*)                 as symbols_count
from latest
join sg on latest.symbol_v = sg.symbol_v
group by 1,2
