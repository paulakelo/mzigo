# ADR 0002: LSN-Guarded MERGE in Silver Current-State via delta-rs (`deltalake`)

## Context
In Rekon, we utilized Apache Spark Structured Streaming with Delta Lake to perform micro-batch deduplication via `foreachBatch`. However, Apache Spark carries significant memory and JVM overhead, which strains an 8 GB laptop when running alongside PostgreSQL, PostGIS, Kafka, and Debezium.

Furthermore, Kafka provides at-least-once delivery guarantees. During consumer crashes, network reconnects, or re-snapshots, events may be redelivered out of order or replayed from offset 0. Overwriting Silver state with an out-of-order older event would cause silent state corruption.

## Decision
1. We eliminate Spark and the JVM from Mzigo's lakehouse layer by using **`delta-rs` (`deltalake` in Python)**. This provides native Rust-speed ACID table operations, versioning, time travel, and MERGE capabilities on local disk.
2. In the CDC consumer loop, each micro-batch of events is reduced to the highest LSN per primary key.
3. We perform an idempotent Delta Lake `MERGE` into Silver current-state tables guarded by the PostgreSQL Log Sequence Number (`source.lsn`):
   ```sql
   MERGE INTO silver_deliveries AS target
   USING batch_latest AS source
   ON target.delivery_id = source.delivery_id
   WHEN MATCHED AND source.lsn > target._lsn THEN
     UPDATE SET target.* = source.*, target._lsn = source.lsn
   WHEN NOT MATCHED THEN
     INSERT (source.*, source.lsn)
   ```

## Consequences
- **Lightweight $0 Stack**: Full Delta Lake capabilities run locally without Spark or Java runtime dependencies, easily fitting within an 8 GB RAM profile.
- **Strict Effectively-Once Semantics**: Out-of-order Kafka deliveries or full replays from earliest offset cannot regress newer state.
- **Deterministic Replayability**: Reprocessing events from the raw Bronze changelog produces identical Silver tables.
