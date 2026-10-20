# ADR 0001: Debezium CDC via PostgreSQL Write-Ahead Log (WAL)

## Context
In Dukastack, data was ingested as batch CSV/JSON snapshots, and in Rekon, incoming transactions arrived via edge HTTP webhooks. For Mzigo, the challenge is different: we have an active operational PostgreSQL/PostGIS database processing real-time delivery dispatches, status transitions, and GPS pings.

Traditional approaches to replicating operational data include:
1. **Periodic SQL polling (`SELECT * WHERE updated_at > last_sync`)**: Causes high read load, misses intermediate state changes within the poll interval, cannot capture hard deletes without database-level triggers, and creates database replica lag.
2. **Dual-writing from FastAPI backend**: Backend writes simultaneously to PostgreSQL and Kafka. This creates distributed transaction failure modes (e.g., PostgreSQL commit succeeds but Kafka publish fails, or vice versa).
3. **Change Data Capture (CDC) via PostgreSQL WAL**: Read the transaction log directly using logical decoding (`pgoutput`).

## Decision
We adopt **Debezium with Kafka Connect** reading from PostgreSQL's write-ahead log using the native `pgoutput` logical replication plugin:
- PostgreSQL is configured with `wal_level = logical`, `max_wal_senders = 10`, and `max_replication_slots = 10`.
- We configure `REPLICA IDENTITY FULL` on critical operational tables (`deliveries`) to ensure that update and delete events carry complete before-and-after state images.
- Kafka topics (`mzigo.public.*`) capture every insert, update, and delete with sub-second latency.

## Consequences
- **Zero Query Overhead on OLTP**: Replicating data creates no query load on PostgreSQL; the Debezium engine reads WAL segments sequentially.
- **Complete Audit Trail**: Every intermediate status change is captured even if a delivery transitions multiple times in a single second.
- **Delete and LSN Tracking**: Captures hard deletes (with previous state) and exact Log Sequence Numbers (LSN).
- **Trade-off**: Requires monitoring replication slot lag to ensure inactive consumers do not cause WAL disk accumulation on the database host.
