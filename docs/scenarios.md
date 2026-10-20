# Mzigo: Chaos Scenarios & Resilience Matrix

This document defines the 10 core chaos scenarios for **Mzigo**, detailing failure injection mechanisms, expected system behaviors, and automated verification criteria.

| Scenario ID | Name | Trigger / Failure Injection | Expected System Outcome | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **C-01** | Consumer Killed Mid-Batch | SIGKILL `cdc-consumer` process midway through micro-batch processing; restart consumer. | Zero data loss, zero duplicated rows in Silver, offsets committed only after Delta writes succeed. | `make parity` passes; row counts and hash match source exactly. |
| **C-02** | Earliest Offset Replay | Reset Kafka consumer group offsets to `earliest` for `mzigo.public.*` topics and re-consume entire stream. | Silver current state remains identical; LSN guard rejects regressive updates. | Delta table version increments, but data hashes and row counts in Silver are identical. |
| **C-03** | Intra-Batch Out-of-Order Updates | Inject multiple status updates for a single delivery out-of-order within the same consumer poll batch. | Consumer groups batch by primary key, sorts by LSN, and merges the latest state. | Final delivery status matches highest LSN event in PostgreSQL. |
| **C-04** | Operational Hard Delete in Source | Execute `DELETE FROM deliveries WHERE delivery_id = ...` in PostgreSQL. | Bronze retains raw `op="d"` with before-image; Silver flags `deleted_at = ts_ms` (soft delete); history is preserved. | Row still exists in Silver with `deleted_at IS NOT NULL`; Bronze has delete event. |
| **C-05** | Source Schema Evolution Mid-Run | Execute `ALTER TABLE deliveries ADD COLUMN payment_method VARCHAR(50);` during active streaming. | CDC consumer detects new column, invokes `deltalake` schema merge, backfills nulls, and continues processing without restarts. | New column appears in Silver Delta table; parity check passes. |
| **C-06** | Debezium Connector Restart & Snapshot | Delete Debezium connector, trigger fresh initial snapshot from PostgreSQL, and re-stream. | Delta MERGE handles duplicate snapshot records idempotently; Silver state remains unchanged. | `make parity` passes; no duplicate primary keys in Silver. |
| **C-07** | GPS Jump Outside Kenya / Impossible Speed | Inject rider GPS ping with coordinates outside Kenya or implied speed > 120 km/h. | API rejects out-of-bounds coords (HTTP 422); speed anomalies flagged in `mrt_rider_scorecard` and excluded from route distance. | Gold route distance ignores anomaly; anomaly count logged. |
| **C-08** | Unassigned Rider Location Ping | Rider attempts to submit GPS ping for a delivery not assigned to them (`status != in_transit` or wrong rider ID). | FastAPI backend returns HTTP 400 Bad Request; ping is rejected at write time. | No ping row recorded in `rider_locations` table. |
| **C-09** | Illegal Delivery Status Transition | Attempt to transition delivery from `created` directly to `delivered` or backwards from `delivered` to `in_transit`. | State machine intercepts transition, rejects with HTTP 409 Conflict. | Status remains unchanged in PostgreSQL and lakehouse. |
| **C-10** | Extended Consumer Downtime & Slot Lag | Stop consumer for extended period while deliveries continue; verify replication slot WAL accumulation; restart consumer. | Replication slot retains WAL on PostgreSQL; consumer catches up rapidly on restart; zero events lost. | Parity passes after backlog drain; slot lag alert logic triggers during downtime. |

---

## Verification Suite

All chaos scenarios are codified as automated tests under `tests/chaos/` and can be executed via:
```bash
make test
```
