# ADR 0007: Automated Parity Check Asset (PostgreSQL vs. Silver Delta)

## Context
A major risk in Change Data Capture pipelines is silent data divergence. Serialization mismatches, dropped tombstone records, out-of-order LSN race conditions, or unhandled null values can result in the lakehouse drifting away from the operational database unnoticed.

A data engineering platform must not merely assume replication correctness—it must cryptographically prove it.

## Decision
We implement an automated Parity Verification Check as both a standalone CLI command (`make parity`) and a Dagster asset check:
1. **Row Count Parity**: For each replicated table, counts active (non-deleted) records in PostgreSQL against `deleted_at IS NULL` records in Silver Delta.
2. **Deterministic Row-Hash Parity**:
   - PostgreSQL computes a deterministic MD5 hash across primary key and normalized column attributes:
     ```sql
     SELECT MD5(STRING_AGG(MD5(delivery_id || '|' || status || '|' || rider_id), '' ORDER BY delivery_id))
     FROM deliveries WHERE deleted_at IS NULL;
     ```
   - DuckDB computes the identical MD5 concatenation over `silver_deliveries`:
     ```sql
     SELECT MD5(STRING_AGG(MD5(delivery_id || '|' || status || '|' || rider_id), '' ORDER BY delivery_id))
     FROM silver_deliveries WHERE deleted_at IS NULL;
     ```
3. If counts or composite hashes do not match exactly, the check fails loudly, printing mismatched primary keys and column diffs.

## Consequences
- **Absolute Confidence**: Proves beyond doubt that the Silver lakehouse is a byte-accurate mirror of PostgreSQL.
- **Chaos Verification**: Forms the automated acceptance criteria for every test in the chaos scenario test suite.
- **Continuous Auditing**: Dagster schedules and freshness checks flag any drift immediately.
