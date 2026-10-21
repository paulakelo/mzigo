"""Mzigo CDC Consumer Main Service.

Subscribes to Kafka CDC topics (mzigo.public.*), writes immutable change events
to Bronze Delta Lake, and commits Kafka offsets only after Delta ACID commits.
"""

import argparse
import os
import time
from typing import Any

from kafka import KafkaConsumer

from cdc.consumer.bronze import append_bronze_batch, parse_debezium_message

CDC_TOPICS = [
    "mzigo.public.zones",
    "mzigo.public.shops",
    "mzigo.public.customers",
    "mzigo.public.riders",
    "mzigo.public.deliveries",
    "mzigo.public.delivery_status_events",
    "mzigo.public.rider_locations",
]


def create_consumer(
    bootstrap_servers: str,
    group_id: str = "mzigo_cdc_lakehouse",
    auto_offset_reset: str = "earliest",
) -> KafkaConsumer:
    """Instantiate a KafkaConsumer with manual offset commits."""
    return KafkaConsumer(
        *CDC_TOPICS,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
        enable_auto_commit=False,
        consumer_timeout_ms=3000,
        max_poll_records=500,
    )


def consume_batch(
    consumer: KafkaConsumer,
    max_records: int = 500,
) -> tuple[int, list[dict[str, Any]]]:
    """Poll a single micro-batch, write to Bronze Delta, and commit Kafka offsets."""
    raw_poll = consumer.poll(timeout_ms=2000, max_records=max_records)
    if not raw_poll:
        return 0, []

    records: list[dict[str, Any]] = []
    for tp, messages in raw_poll.items():
        for msg in messages:
            if msg.value:
                parsed = parse_debezium_message(
                    topic=tp.topic,
                    partition=tp.partition,
                    offset=msg.offset,
                    msg_bytes=msg.value,
                )
                records.append(parsed)

    if records:
        # 1. Write ACID transaction into Bronze Delta Lake
        append_bronze_batch(records)
        # 2. Commit Kafka offsets only after successful Delta write (effectively-once)
        consumer.commit()

    return len(records), records


def run_consumer_loop(
    bootstrap_servers: str,
    group_id: str = "mzigo_cdc_lakehouse",
    run_once: bool = False,
    max_batches: int | None = None,
) -> int:
    """Run CDC polling loop."""
    print(f"Connecting to Kafka on {bootstrap_servers} (group: {group_id})...")
    consumer = create_consumer(bootstrap_servers, group_id=group_id)

    total_records = 0
    batches_run = 0
    empty_polls = 0

    try:
        while True:
            count, _ = consume_batch(consumer)
            if count > 0:
                total_records += count
                batches_run += 1
                empty_polls = 0
                print(
                    f"[Bronze] Batch {batches_run}: Appended {count} events "
                    f"(total: {total_records})"
                )
            else:
                empty_polls += 1

            if run_once and empty_polls >= 2:
                print("No more messages on stream. Bounded run complete.")
                break

            if max_batches and batches_run >= max_batches:
                break

            if count == 0 and not run_once:
                time.sleep(1.0)
    finally:
        consumer.close()

    print(f"CDC Consumer finished. Ingested {total_records} events into Bronze.")
    return total_records


def main():
    parser = argparse.ArgumentParser(description="Mzigo CDC Consumer Service")
    parser.add_argument(
        "--bootstrap",
        type=str,
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
        help="Kafka bootstrap server address",
    )
    parser.add_argument(
        "--group-id",
        type=str,
        default="mzigo_cdc_lakehouse",
        help="Consumer group ID",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Poll until topics are drained then exit",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Maximum micro-batches to process",
    )

    args = parser.parse_args()
    run_consumer_loop(
        bootstrap_servers=args.bootstrap,
        group_id=args.group_id,
        run_once=args.once,
        max_batches=args.max_batches,
    )


if __name__ == "__main__":
    main()
