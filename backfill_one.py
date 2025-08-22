import os, sys, math
import yfinance as yf
from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

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

def to_dict(v, ctx): return v

def to_ms(ts): return int(ts.tz_convert("UTC").timestamp() * 1000)

def main(symbol):
    # Robust hourly data fetch
    df = yf.Ticker(symbol).history(period="100d", interval="60m", auto_adjust=False)
    if df is None or df.empty:
        print(f"[warn] no data for {symbol}")
        return 1
    df = df.dropna(subset=["Close"]).copy()

    sr_url = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    bootstrap = os.getenv("BOOTSTRAP_SERVERS", "localhost:29092")
    topic = os.getenv("TOPIC", "ticks.raw")

    sr = SchemaRegistryClient({"url": sr_url})

    avro_ser = AvroSerializer(
        sr,
        VALUE_AVRO_SCHEMA,
        to_dict,
        conf={"auto.register.schemas": False, "use.latest.version": True} 
    )    

    prod = SerializingProducer({
        "bootstrap.servers": bootstrap,
        "key.serializer": StringSerializer("utf_8"),
        "value.serializer": avro_ser,
    })

    sent = 0
    for ts, row in df.iterrows():
        ts_ms = to_ms(ts)
        price = float(row["Close"])
        vol = int(row.get("Volume", 0) or 0)
        prod.produce(topic=topic, key=symbol, value={"TS": ts_ms, "PRICE": price, "VOLUME": vol})
        sent += 1
        if sent % 500 == 0: prod.flush()
    prod.flush()
    print(f"[backfill] sent {sent} hourly bars for {symbol}")
    return 0

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    raise SystemExit(main(sym))
