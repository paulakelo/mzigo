"""Mzigo Bronze Delta Lake Changelog Appender.

Preserves an immutable, append-only historical log of all raw Debezium CDC events
partitioned by event date on local disk using delta-rs without Apache Spark.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pyarrow as pa
from deltalake import write_deltalake

BRONZE_DELTA_PATH = "data/delta/bronze_changelog"

BRONZE_ARROW_SCHEMA = pa.schema(
    [
        ("event_id", pa.string()),
        ("topic", pa.string()),
        ("partition", pa.int32()),
        ("offset", pa.int64()),
        ("op", pa.string()),
        ("table_name", pa.string()),
        ("lsn", pa.int64()),
        ("source_ts_ms", pa.int64()),
        ("event_ts_ms", pa.int64()),
        ("before_json", pa.string()),
        ("after_json", pa.string()),
        ("raw_envelope", pa.string()),
        ("event_date", pa.string()),
        ("ingested_at", pa.timestamp("us", tz="UTC")),
    ]
)


def parse_debezium_message(
    topic: str, partition: int, offset: int, msg_bytes: bytes
) -> dict[str, Any]:
    """Parse raw Kafka message bytes into normalized Bronze dictionary."""
    raw_str = msg_bytes.decode("utf-8")
    raw_json = json.loads(raw_str)

    # Handle Debezium envelope (with or without schema wrapper)
    payload = raw_json.get("payload", raw_json)

    source = payload.get("source", {})
    table_name = source.get("table", topic.split(".")[-1])
    lsn = source.get("lsn", 0)
    source_ts_ms = source.get("ts_ms", 0)
    event_ts_ms = payload.get("ts_ms", source_ts_ms)
    op = payload.get("op", "u")

    # Determine date partition key
    if event_ts_ms:
        event_dt = datetime.fromtimestamp(event_ts_ms / 1000.0, tz=UTC)
        event_date = event_dt.strftime("%Y-%m-%d")
    else:
        event_date = datetime.now(UTC).strftime("%Y-%m-%d")

    before_val = payload.get("before")
    after_val = payload.get("after")

    return {
        "event_id": f"EVT-{uuid.uuid4().hex[:12].upper()}",
        "topic": topic,
        "partition": partition,
        "offset": offset,
        "op": op,
        "table_name": table_name,
        "lsn": int(lsn) if lsn is not None else 0,
        "source_ts_ms": int(source_ts_ms) if source_ts_ms is not None else 0,
        "event_ts_ms": int(event_ts_ms) if event_ts_ms is not None else 0,
        "before_json": json.dumps(before_val) if before_val is not None else None,
        "after_json": json.dumps(after_val) if after_val is not None else None,
        "raw_envelope": raw_str,
        "event_date": event_date,
        "ingested_at": datetime.now(UTC),
    }


def append_bronze_batch(records: list[dict[str, Any]], delta_path: str = BRONZE_DELTA_PATH) -> int:
    """Append a batch of parsed CDC records into the Bronze Delta table."""
    if not records:
        return 0

    pydict = {field.name: [r[field.name] for r in records] for field in BRONZE_ARROW_SCHEMA}
    table = pa.Table.from_pydict(pydict, schema=BRONZE_ARROW_SCHEMA)

    write_deltalake(
        delta_path,
        table,
        mode="append",
        partition_by=["event_date"],
    )
    return len(records)
