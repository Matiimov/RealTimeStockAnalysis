-- Athena: external table over bronze Parquet (no symbol in value)
USE rtsa_bronze;

CREATE EXTERNAL TABLE IF NOT EXISTS ticks_raw_parquet (
  ts BIGINT,
  price DOUBLE,
  volume BIGINT
)
STORED AS PARQUET
LOCATION 's3://rtsa-mat-dev-project01/topics/ticks.raw/';
