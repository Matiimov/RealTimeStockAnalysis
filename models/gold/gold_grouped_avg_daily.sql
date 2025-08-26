{{ config(
    schema='rtsa_gold',
    materialized='table',
    external_location='s3://rtsa-mat-dev-project01/athena-data-dev/tables/gold_grouped_avg_daily_v2/'
) }}

with base as (
  select
    sg.group_name,
    avg(t.price) as avg_price,
    CAST(from_unixtime(t.ts/1000) AS date) as day  
  from {{ ref('silver_ticks_v2') }} t
  join {{ ref('symbol_groups') }} sg
    on t.symbol_v = sg.symbol_v
  where sg.group_name in ('Technology','Defense')
  group by 1,3
)
select
  group_name,
  avg_price,
  day
from base