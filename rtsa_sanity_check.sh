#!/usr/bin/env bash
# RTSA sanity check
set -euo pipefail

echo "== RTSA Sanity Check =="
date

# Helpers
has_cmd() { command -v "$1" >/dev/null 2>&1; }
maybe_jq() { if has_cmd jq; then jq; else cat; fi; }

echo ""
echo "-- Environment --"
python3 -V || true
if has_cmd conda; then
  conda info --envs || true
fi

echo ""
echo "-- Docker containers --"
if has_cmd docker && has_cmd docker-compose; then
  docker compose ps || true
else
  echo "Docker or docker compose not found."
fi

echo ""
echo "-- Service health checks --"
if has_cmd curl; then
  echo "Schema Registry:"
  curl -s http://localhost:8081/subjects | maybe_jq || true
  echo ""
  echo "ksqlDB /info:"
  curl -s http://localhost:8088/info | maybe_jq || true
  echo ""
  echo "Kafka Connect (connector list):"
  curl -s http://localhost:8083/connectors | maybe_jq || true
  echo ""
  echo "Kafka Connect s3-sink-ticks status:"
  curl -s http://localhost:8083/connectors/s3-sink-ticks/status | maybe_jq || true
else
  echo "curl not found."
fi

echo ""
echo "-- AWS / S3 checks (profile: rtsa) --"
if has_cmd aws; then
  aws sts get-caller-identity --profile rtsa || true
  echo ""
  echo "S3 raw objects:"
  aws s3 ls s3://rtsa-mat-dev-project01/topics/ticks.raw/ --recursive --profile rtsa | tail -n 10 || true
  echo ""
  echo "S3 enriched objects:"
  aws s3 ls s3://rtsa-mat-dev-project01/topics/ticks.enriched/ --recursive --profile rtsa | tail -n 10 || true
else
  echo "aws CLI not found."
fi

echo ""
echo "-- ksqlDB quick query for ticks_enriched (LIMIT 3) --"
read -r -d '' KSQL_PAYLOAD <<'JSON' || true
{
  "ksql": "SET 'auto.offset.reset'='earliest'; SELECT SYMBOL, TS, PRICE, VOLUME FROM TICKS_ENRICHED EMIT CHANGES LIMIT 3;",
  "streamsProperties": {}
}
JSON

if has_cmd curl; then
  curl -s -X POST http://localhost:8088/query \
    -H "Content-Type: application/vnd.ksql.v1+json; charset=utf-8" \
    -d "$KSQL_PAYLOAD" | maybe_jq || true
fi

echo ""
echo "== Done =="
