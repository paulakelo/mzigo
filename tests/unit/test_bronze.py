"""Unit tests for Bronze Delta Lake changelog parser and appender."""

import json
from datetime import UTC, datetime

from deltalake import DeltaTable

from cdc.consumer.bronze import append_bronze_batch, parse_debezium_message


def test_parse_debezium_message():
    sample_payload = {
        "op": "c",
        "ts_ms": 1792575984000,
        "before": None,
        "after": {
            "delivery_id": "DEL-TEST-001",
            "status": "created",
            "shop_id": "SHOP_CBD_01",
        },
        "source": {
            "table": "deliveries",
            "lsn": 39188096,
            "ts_ms": 1792575984000,
        },
    }
    raw_bytes = json.dumps({"payload": sample_payload}).encode("utf-8")

    record = parse_debezium_message(
        topic="mzigo.public.deliveries",
        partition=0,
        offset=42,
        msg_bytes=raw_bytes,
    )

    assert record["event_id"].startswith("EVT-")
    assert record["topic"] == "mzigo.public.deliveries"
    assert record["partition"] == 0
    assert record["offset"] == 42
    assert record["op"] == "c"
    assert record["table_name"] == "deliveries"
    assert record["lsn"] == 39188096
    assert record["before_json"] is None
    assert "DEL-TEST-001" in record["after_json"]
    expected_date = datetime.fromtimestamp(1792575984000 / 1000.0, tz=UTC).strftime("%Y-%m-%d")
    assert record["event_date"] == expected_date


def test_append_bronze_batch_local_tmp(tmp_path):
    delta_dir = str(tmp_path / "delta" / "bronze_test")

    records = [
        {
            "event_id": f"EVT-{i}",
            "topic": "mzigo.public.deliveries",
            "partition": 0,
            "offset": i,
            "op": "c" if i == 0 else "u",
            "table_name": "deliveries",
            "lsn": 1000 + i,
            "source_ts_ms": 1792575984000 + (i * 1000),
            "event_ts_ms": 1792575984000 + (i * 1000),
            "before_json": None if i == 0 else json.dumps({"status": "created"}),
            "after_json": json.dumps({"status": "assigned" if i > 0 else "created"}),
            "raw_envelope": json.dumps({"test": i}),
            "event_date": "2026-10-21",
            "ingested_at": datetime.now(UTC),
        }
        for i in range(5)
    ]

    count = append_bronze_batch(records, delta_path=delta_dir)
    assert count == 5

    dt = DeltaTable(delta_dir)
    assert dt.version() == 0
    assert len(dt.to_pyarrow_table()) == 5
