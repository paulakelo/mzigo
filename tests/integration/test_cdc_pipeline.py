"""Integration tests for Debezium CDC and Kafka event streaming."""

import httpx
from kafka import KafkaConsumer


def test_debezium_connector_health():
    with httpx.Client(base_url="http://localhost:8083", timeout=5.0) as client:
        res = client.get("/connectors/mzigo-connector/status")
        assert res.status_code == 200
        data = res.json()
        assert data["connector"]["state"] == "RUNNING"
        assert len(data["tasks"]) > 0
        assert data["tasks"][0]["state"] == "RUNNING"


def test_kafka_topics_and_records():
    consumer = KafkaConsumer(
        bootstrap_servers="localhost:29092",
        consumer_timeout_ms=3000,
    )
    topics = consumer.topics()
    consumer.close()

    expected_topics = [
        "mzigo.public.zones",
        "mzigo.public.shops",
        "mzigo.public.customers",
        "mzigo.public.riders",
        "mzigo.public.deliveries",
        "mzigo.public.delivery_status_events",
        "mzigo.public.rider_locations",
    ]
    for et in expected_topics:
        assert et in topics, f"Topic '{et}' missing from Kafka topics: {topics}"
