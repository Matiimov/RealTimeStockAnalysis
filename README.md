# RTSA — Real‑Time Stocks (Architecture Demo)

This repo showcases a compact, cloud‑native analytics pipeline that ingests streaming stock ticks and makes them queryable for BI — **without** any schedulers or CI/CD. The goal is to demonstrate architecture, not to run in production.

**Stack**

- **Kafka → ksqlDB** for ingest + light enrichment
- **S3 (Parquet)** as the data lake
- **Athena** as the query layer
- **dbt** for bronze/silver/gold models
- **Metabase** for a minimal dashboard

---

## Architecture (bird’s‑eye)

```
┌─────────┐   ticks    ┌────────┐   enriched    ┌──────────┐   Parquet/Proj.   ┌────────┐   SQL models   ┌──────────┐
│ Producer├──────────▶ │ Kafka  │─────────────▶│  ksqlDB  │──────────────────▶│  S3    │───────────────▶│  Athena  │
└─────────┘            └────────┘              └──────────┘                    └────────┘               └──────────┘
                                                                                                              │
                                                                                                              ▼
                                                                                                            BI (Metabase)
```

- **Bronze/Silver/Gold** are implemented in **dbt** and compiled to Athena SQL.
- Seeded lookup `symbol_groups` provides **Technology** vs **Defense** grouping for comparisons.

---

## Repo layout (key parts)

```
.
├─ models/
│  ├─ bronze/ …
│  ├─ silver/ …
│  └─ gold/
│     ├─ gold_latest_price_v2.sql
│     ├─ gold_latest_price_v2_grouped.sql
│     ├─ gold_grouped_avg_daily.sql
│     └─ gold_grouped_returns.sql
├─ seeds/
│  └─ symbol_groups.csv          # (symbol_v, group_id, group_name) e.g. Technology / Defense
├─ dbt_project.yml
├─ docker-compose*.yml
└─ .env
```

---

## Prerequisites

- Docker & Docker Compose
- Python + `dbt-core==1.8.x` and `dbt-athena==1.8.x`
- AWS CLI configured
- **IAM permissions** for the user dbt uses:
  - `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:AbortMultipartUpload`, `DeleteObjectVersion`

Example profile (`~/.dbt/profiles.yml`):

```yaml
rtsa_athena:
  target: dev
  outputs:
    dev:
      type: athena
      region_name: ap-southeast-2
      work_group: primary
      database: AwsDataCatalog
      schema: rtsa_bronze
      threads: 4
      s3_staging_dir: s3://<bucket>/athena-results-dev/
      s3_data_dir: s3://<bucket>/athena-data-dev/
```

---

## Quickstart

1. **Bring up the local stack**

```bash
conda activate <your env>
docker compose up -d
docker compose ps
```

2. **Verify Kafka Connect & ksqlDB (optional smoke test)**

```bash
curl -s http://localhost:8083/connectors/s3-sink-ticks/status | jq .
curl -s -X POST http://localhost:8088/query \
  -H 'Content-Type: application/vnd.ksql.v1+json' \
  -d '{"ksql":"SELECT SYMBOL, TS, PRICE FROM TICKS_ENRICHED_V2 EMIT CHANGES LIMIT 3;",
       "streamsProperties":{"auto.offset.reset":"latest"}}'
```

3. **Seed the grouping table**

```bash
dbt seed --select symbol_groups
```

4. **Build models**

```bash
# Latest per symbol (gold), plus grouped views:
dbt run --select gold_latest_price_v2 gold_latest_price_v2_grouped
# Defense vs Technology averages and 7/30/90‑day growth:
dbt run --select gold_grouped_avg_daily gold_grouped_returns
```

5. **Query in Athena** (note the composed DB name):

```sql
SELECT * FROM rtsa_bronze_rtsa_gold.gold_grouped_avg_daily LIMIT 10;
SELECT group_name, day, return_7d, return_30d, return_90d
FROM rtsa_bronze_rtsa_gold.gold_grouped_returns
ORDER BY day DESC
LIMIT 10;
```

---

## Building the Tech vs Defense dashboard (Metabase)

1. Go to `http://localhost:3000` → add **Athena** database:

   - Region: your region (e.g., `ap-southeast-2`)
   - Staging S3 dir: e.g., `s3://<bucket>/athena-results-dev/`
   - Workgroup: `primary` (or your dev group)

2. Create a **line chart** with table `rtsa_bronze_rtsa_gold.gold_grouped_returns`:
   - X‑axis: `day`
   - Y‑axis: choose `return_7d` (or `return_30d` / `return_90d`)
   - Break out by: `group_name` (shows **Technology** vs **Defense**)
   - Add a dashboard filter (dropdown) to switch metric between 7/30/90‑day

> This project intentionally **does not** include scheduling/CI/CD — it’s a hands‑on architecture demo.
