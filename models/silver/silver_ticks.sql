{{ config(materialized='view') }}

select
  from_unixtime(ts/1000) as event_time,
  ts,
  price,
  volume
from {{ source('bronze','ticks_raw_parquet') }}
