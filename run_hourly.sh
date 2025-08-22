#!/bin/bash
set -euo pipefail

# portable lock (no flock)
LOCKDIR="/tmp/rtsa_hourly.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "[skip] already running"
  exit 0
fi
trap 'rmdir "$LOCKDIR"' EXIT

# env
export BOOTSTRAP_SERVERS="${BOOTSTRAP_SERVERS:-localhost:29092}"
export SCHEMA_REGISTRY_URL="${SCHEMA_REGISTRY_URL:-http://localhost:8081}"
export TOPIC="${TOPIC:-ticks.raw}"

# run from repo root
cd "$(dirname "$0")"

# market open?
python is_us_market_open.py --now >/dev/null || { echo "[closed] skipping"; exit 0; }

# only at :31 ET
ET_MIN="$(TZ="America/New_York" date +%M)"
if [[ "$ET_MIN" != "31" ]]; then
  echo "[skip] not :31 ET (it's :$ET_MIN ET)"
  exit 0
fi

# send one 1h bar per ticker
python send_latest_one.py
echo "[done] hourly send"
