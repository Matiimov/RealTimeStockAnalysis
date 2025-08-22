import os, csv
import yfinance as yf
from pathlib import Path
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

def load_tickers():
    p = Path("data/tickers.csv")
    syms = []
    with p.open() as f:
        for row in csv.reader(f):
            if not row: continue
            s = row[0].strip()
            if s and s.lower() != "symbol":
                syms.append(s)
    return syms

def main():
    sr = SchemaRegistryClient({"url": os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")})
    avro_ser = AvroSerializer(sr, VALUE_AVRO_SCHEMA, to_dict,
                              conf={"auto.register.schemas": False, "use.latest.version": True})
    prod = SerializingProducer({
        "bootstrap.servers": os.getenv("BOOTSTRAP_SERVERS", "localhost:29092"),
        "key.serializer": StringSerializer("utf_8"),
        "value.serializer": avro_ser,
    })
    topic = os.getenv("TOPIC", "ticks.raw")

    count_ok = 0
    for sym in load_tickers():
        df = yf.Ticker(sym).history(period="2d", interval="60m", auto_adjust=False)
        if df is None or df.empty:
            print(f"[warn] no data for {sym}")
            continue
        df = df.dropna(subset=["Close"])
        ts, row = df.iloc[-1].name, df.iloc[-1]
        prod.produce(topic=topic, key=sym, value={
            "TS": to_ms(ts), "PRICE": float(row["Close"]), "VOLUME": int(row.get("Volume", 0) or 0)
        })
        count_ok += 1
    prod.flush()
    print(f"[hourly] sent {count_ok} symbols")

if __name__ == "__main__":
    main()
