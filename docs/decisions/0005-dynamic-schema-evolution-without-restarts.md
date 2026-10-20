# ADR 0005: Dynamic Schema Evolution in Delta Tables Without Pipeline Restarts

## Context
Production databases frequently experience schema changes (DDL migrations), such as adding a new column (`payment_method` or `special_instructions` to `deliveries`). In brittle streaming pipelines, a schema change upstream causes downstream consumer crashes or schema validation exceptions, leading to replication slot lag and backpressure.

## Decision
We leverage Delta Lake's native schema evolution capabilities (`schema_mode="merge"`) in our Python CDC consumer:
1. Debezium detects PostgreSQL DDL changes automatically via WAL and includes new fields in the `after` JSON payload.
2. In the Python consumer, incoming batches are inspected against the existing Delta table schema.
3. When a new column is detected, `deltalake.write_deltalake` is invoked with `schema_mode="merge"`.
4. Existing historical rows in Delta have the new column backfilled with `NULL` upon read, and new records populate the column seamlessly.

## Consequences
- **Resilient Pipeline**: The consumer continues running through online DDL migrations without manual intervention or restarts.
- **Zero Loss & Zero Downtime**: New operational attributes immediately propagate from PostgreSQL into Bronze and Silver Delta tables.
- **Backward Compatibility**: Downstream DuckDB models remain backward compatible as new columns appear as nullable fields.
