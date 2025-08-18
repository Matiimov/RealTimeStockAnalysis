-- Athena: convenience view for readable timestamps
USE rtsa_bronze;

CREATE OR REPLACE VIEW v_ticks_raw AS
SELECT
  from_unixtime(ts/1000) AS event_time,
  price,
  volume,
  ts
FROM ticks_raw_parquet;
