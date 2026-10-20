# ADR 0006: Dual-Engine Architecture (PostgreSQL for OLTP, DuckDB over Delta for Analytics)

## Context
In Dukastack, DuckDB served as the primary local analytical engine. In Rekon, FastAPI served reconciliation reports directly from Spark/Delta outputs.

For Mzigo, we have an operational backend receiving hundreds of concurrent rider GPS pings and status updates. If shop owners and dispatchers execute complex aggregation queries (rider scorecards, multi-stage duration percentiles, zone failure rates) directly against the operational PostgreSQL database, table locks and CPU spikes will degrade transactional ingestion.

## Decision
We enforce a strict separation of concerns across two storage and query engines:
1. **Operational OLTP (PostgreSQL 16 + PostGIS)**: Handles transactional writes, geospatial point-in-polygon checks, and the delivery status state machine. It serves only operational endpoints (`POST /deliveries`, `PATCH /status`, `POST /locations`).
2. **Analytical OLAP (Embedded DuckDB over Delta Lake)**: A dedicated Read API queries the Silver and Gold Delta tables directly via DuckDB.
3. **Data Freshness Header**: Every Read API response includes an `X-Data-As-Of` HTTP header indicating the timestamp of the latest replicated CDC event in Silver.
4. **Zero Cross-Querying**: The Read API is physically forbidden from connecting to PostgreSQL.

## Consequences
- **OLTP Isolation**: Operational database CPU remains dedicated to rider pings and dispatches without lock contention from analytic scans.
- **Fast Vectorized Aggregations**: DuckDB scans columnar Delta parquet files locally with sub-10ms response times.
- **Full Transparency**: API consumers can inspect the `X-Data-As-Of` header to determine replication latency down to the millisecond.
