with src as (
  select
    symbol_v,
    ts,
    price,
    volume
  from {{ source('bronze','ticks_enriched_v2_part') }}
)

select
  symbol_v,
  ts,
  from_unixtime(ts/1000.0) as event_time,
  price,
  volume
from src
