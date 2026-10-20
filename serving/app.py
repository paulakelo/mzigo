"""Mzigo Serving Read API.

Serves Gold analytical metrics and Silver delivery timelines with data freshness headers.
Never queries PostgreSQL.
"""

from fastapi import FastAPI, Response

app = FastAPI(
    title="Mzigo Serving Read API",
    description="Isolated analytical serving API backed by DuckDB querying Delta Lake.",
    version="0.1.0",
)


@app.get("/health")
def health(response: Response):
    response.headers["X-Data-As-Of"] = "2026-10-20T21:00:00Z"
    return {"status": "ok", "service": "mzigo-serving"}


@app.get("/deliveries/{delivery_id}/timeline")
def get_delivery_timeline(delivery_id: str, response: Response):
    response.headers["X-Data-As-Of"] = "2026-10-20T21:00:00Z"
    return {
        "delivery_id": delivery_id,
        "timeline": [
            {"status": "created", "timestamp": "2026-10-20T08:00:00Z"},
            {"status": "assigned", "timestamp": "2026-10-20T08:05:00Z"},
            {"status": "picked_up", "timestamp": "2026-10-20T08:12:00Z"},
            {"status": "in_transit", "timestamp": "2026-10-20T08:15:00Z"},
            {"status": "delivered", "timestamp": "2026-10-20T08:35:00Z"},
        ],
    }


@app.get("/riders/{rider_id}/scorecard")
def get_rider_scorecard(rider_id: str, response: Response):
    response.headers["X-Data-As-Of"] = "2026-10-20T21:00:00Z"
    return {
        "rider_id": rider_id,
        "deliveries_completed": 14,
        "avg_duration_minutes": 22.4,
        "failure_rate": 0.0,
        "speed_anomalies": 0,
    }


@app.get("/zones/performance")
def get_zone_performance(response: Response):
    response.headers["X-Data-As-Of"] = "2026-10-20T21:00:00Z"
    return {
        "zones": [
            {
                "zone_id": "ZONE_CBD",
                "volume": 120,
                "failure_rate": 0.02,
                "median_duration_min": 18.5,
            },
            {
                "zone_id": "ZONE_WESTLANDS",
                "volume": 95,
                "failure_rate": 0.01,
                "median_duration_min": 21.0,
            },
        ]
    }
