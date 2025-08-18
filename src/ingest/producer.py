import os, time, math
from datetime import datetime, timezone

from dotenv import load_dotenv
import yfinance as yf

from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

load_dotenv()

BOOTSTRAP = os.getenv("BOOTSTRAP_SERVERS", "localhost:29092")
SR_URL    = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
TOPIC     = os.getenv("TOPIC", "ticks.raw")

VALUE_AVRO_SCHEMA = """
{
  "type":"record",
  "name":"KsqlDataSourceSchema",
  "namespace":"io.confluent.ksql.avro_schemas",
  "fields":[
    {"name":"TS","type":["null","long"],"default":null},
    {"name":"PRICE","type":["null","double"],"default":null},
    {"name":"VOLUME","type":["null","long"],"default":null}
  ]
}
"""

def to_dict(obj, ctx):
    return {
        "TS": int(obj["ts"]),
        "PRICE": float(obj["price"]),
        "VOLUME": int(obj["volume"]),
    }

def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def latest_price_and_volume(ticker: str):
    t = yf.Ticker(ticker)
    price = None
    vol = 0
    try:
        fi = getattr(t, "fast_info", {}) or {}
        price = fi.get("last_price", None)
    except Exception:
        pass
    if price is None or (isinstance(price, float) and (math.isnan(price) or price <= 0)):
        try:
            hist = t.history(period="1d", interval="1m").tail(1)
            if not hist.empty:
                price = float(hist["Close"].iloc[0])
                vol = int(hist["Volume"].iloc[0]) if "Volume" in hist.columns else 0
        except Exception:
            pass
    if price is None or (isinstance(price, float) and (math.isnan(price) or price <= 0)):
        raise RuntimeError(f"Could not fetch price for {ticker}")
    return price, vol

def main():
    sr = SchemaRegistryClient({"url": SR_URL})
    value_serializer = AvroSerializer(sr, VALUE_AVRO_SCHEMA, to_dict)
    producer = SerializingProducer({
        "bootstrap.servers": BOOTSTRAP,
        "key.serializer": StringSerializer("utf_8"),
        "value.serializer": value_serializer,
        "linger.ms": 50,
        "acks": "all",
    })

    tickers = ["AAPL", "EURUSD=X", "BTC-USD"]
    interval_sec = int(os.getenv("INTERVAL_SEC", "5"))
    iterations   = int(os.getenv("LOOP_COUNT", "5"))

    print(f"Producing to {TOPIC} @ {BOOTSTRAP} (SR: {SR_URL})")
    for _ in range(iterations):
        for sym in tickers:
            try:
                price, vol = latest_price_and_volume(sym)
                record = {"ts": now_ms(), "price": price, "volume": vol}
                producer.produce(topic=TOPIC, key=sym, value=record)
                print(f"[ok] {sym} price={price} vol={vol}")
            except Exception as e:
                print(f"[warn] {sym} skipped: {e}")
        producer.flush()
        time.sleep(interval_sec)

    producer.flush()
    print("Done.")

if __name__ == "__main__":
    main()
