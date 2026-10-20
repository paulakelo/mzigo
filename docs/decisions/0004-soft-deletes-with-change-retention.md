# ADR 0004: Soft Deletes with Change History Retention in Lakehouse

## Context
In operational PostgreSQL databases, records may be hard-deleted (e.g., `DELETE FROM deliveries WHERE delivery_id = ...`) when dispatchers cancel accidental test orders or clean up invalid entries.

If the downstream lakehouse mirrored hard deletes by deleting rows from Silver tables, analytical models (such as `fct_delivery_lifecycle` or operational failure reports) would lose context, distorting historical SLA metrics and audit trails.

## Decision
We handle deletes across the lakehouse layers as follows:
1. **Bronze Layer**: Appends the raw Debezium delete event (`op = "d"`). Because `REPLICA IDENTITY FULL` is enabled on PostgreSQL, Debezium captures the complete `before` payload alongside LSN and transaction metadata.
2. **Silver Current State**: When a delete event is processed, the LSN-guarded MERGE sets `deleted_at = source.ts_ms` and marks the status as `deleted`, rather than physically executing a `DELETE` on the Delta table.
3. **Gold Layer**: Active operational marts filter out records where `deleted_at IS NOT NULL`, while audit and cancellation analyses retain full visibility of deleted orders.

## Consequences
- **Zero Historical Data Loss**: Complete lifecycle history and operational cancellations remain fully auditable.
- **Bi-temporal Visibility**: We preserve both the operational creation/update timeline and the lakehouse replication timeline.
- **Parity Alignment**: The parity check asset filters `deleted_at IS NULL` when verifying live state against operational PostgreSQL tables.
