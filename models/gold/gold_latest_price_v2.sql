with ranked as (
  select
    symbol_v,
    ts,
    from_unixtime(ts/1000.0) as event_time,
    price,
    volume,
    row_number() over (partition by symbol_v order by ts desc) as rn
  from {{ ref('silver_ticks_v2') }}
)
select
  symbol_v,
  ts,
  event_time,
  price,
  volume
from ranked
where rn = 1
