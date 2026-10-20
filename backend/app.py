"""Mzigo Operational FastAPI Write Application.

Handles deliveries creation, state machine transitions, and rider GPS pings.
"""

from fastapi import FastAPI, HTTPException, status

from backend.geo import OutOfBoundsCoordinateError, validate_kenya_bounds
from backend.models import CreateDeliveryRequest, RiderLocationPing, UpdateStatusRequest
from backend.state_machine import InvalidStateTransitionError, validate_transition

app = FastAPI(
    title="Mzigo Operational Write API",
    description="Operational API for deliveries, status events, and GPS pings with PostGIS.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mzigo-backend"}


@app.post("/deliveries", status_code=status.HTTP_201_CREATED)
def create_delivery(request: CreateDeliveryRequest):
    try:
        validate_kenya_bounds(request.pickup_point.lat, request.pickup_point.lon)
        validate_kenya_bounds(request.dropoff_point.lat, request.dropoff_point.lon)
    except OutOfBoundsCoordinateError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    # Delivery creation and zone assignment logic
    return {
        "delivery_id": f"DEL-{request.shop_id}-0001",
        "status": "created",
        "sla_minutes": request.sla_minutes,
        "message": "Delivery created successfully",
    }


@app.patch("/deliveries/{delivery_id}/status")
def update_status(delivery_id: str, request: UpdateStatusRequest):
    current_status = "created"  # In production, looked up from PostgreSQL
    try:
        validate_transition(current_status, request.to_status)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    return {
        "delivery_id": delivery_id,
        "from_status": current_status,
        "to_status": request.to_status,
        "status": "updated",
    }


@app.post("/locations", status_code=status.HTTP_202_ACCEPTED)
def post_location(ping: RiderLocationPing):
    try:
        validate_kenya_bounds(ping.lat, ping.lon)
    except OutOfBoundsCoordinateError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    return {"status": "accepted", "rider_id": ping.rider_id}
