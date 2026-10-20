# ADR 0003: Write-Time PostGIS Point-in-Polygon Zone Assignment

## Context
In Dukastack, geographical regions and store locations were static dimensional metadata. In Mzigo's last-mile delivery domain, pickups and drop-offs occur dynamically across Nairobi's metropolitan area. Operational dispatchers require instantaneous zone allocation to price deliveries, assign nearby boda-boda riders, and enforce delivery SLAs.

Two approaches were evaluated:
1. **Downstream Spatial Enrichment**: Ingest raw lat/lon into the database and let downstream analytics (DuckDB or Python) resolve zones later.
2. **Synchronous Write-Time Spatial Assignment**: Use PostGIS `ST_Contains` spatial queries within the FastAPI transaction at delivery creation time.

## Decision
We enforce geospatial validation and zone assignment at write time inside the operational PostgreSQL database:
1. Coordinates are validated against Kenya national geographic bounds: latitude `[-4.7, 5.1]`, longitude `[33.8, 41.9]`. Coordinates outside this bounding box are rejected immediately with HTTP 422.
2. Hand-drawn approximate polygons for Nairobi operational zones (e.g., Westlands, CBD, Kilimani, Upper Hill, Industrial Area, Eastlands, Karen) are pre-seeded in the `zones` PostGIS table.
3. During `POST /deliveries`, `pickup_zone_id` and `dropoff_zone_id` are computed via `ST_Contains(zone.polygon, ST_SetSRID(ST_Point(lon, lat), 4326))`.

## Consequences
- **Instantaneous Dispatch Ready**: Every delivery record in PostgreSQL already possesses resolved pickup and drop-off zone foreign keys upon insertion.
- **Data Quality at the Source**: Bad GPS coordinates are stopped at the API gateway before ever polluting the operational database or downstream CDC stream.
- **Trade-off**: Requires running PostGIS spatial index lookups during ingestion, but on local spatial scales (< 20 zones), `ST_Contains` latency is under 2ms.
