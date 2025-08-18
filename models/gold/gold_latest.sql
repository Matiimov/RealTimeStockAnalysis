{{ config(materialized='view') }}

-- Latest row from silver_ticks (Athena lacks QUALIFY; join on max ts)
select s.*
from {{ ref('silver_ticks') }} s
join (
  select max(ts) as max_ts
  from {{ ref('silver_ticks') }}
) m
  on s.ts = m.max_ts
