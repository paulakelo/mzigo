"""Mzigo Operational FastAPI Write Application.

Handles delivery creation, PostGIS zone assignment, state machine transitions,
and rider GPS pings with direct persistence to PostgreSQL 16 + PostGIS.
"""

import uuid
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.geo import OutOfBoundsCoordinateError, validate_kenya_bounds
from backend.models import (
    CreateDeliveryRequest,
    CustomerModel,
    DeliveryModel,
    DeliveryResponse,
    DeliveryStatusEventModel,
    RiderLocationModel,
    RiderLocationPing,
    RiderModel,
    ShopModel,
    UpdateStatusRequest,
    hash_phone,
)
from backend.state_machine import InvalidStateTransitionError, validate_transition

app = FastAPI(
    title="Mzigo Operational Write API",
    description="Operational API for deliveries, status events, and GPS pings with PostGIS.",
    version="0.1.0",
)


def resolve_zone(db: Session, lat: float, lon: float) -> str | None:
    """Find containing PostGIS delivery zone using ST_Contains."""
    query = text(
        "SELECT zone_id FROM zones "
        "WHERE ST_Contains(polygon, ST_SetSRID(ST_Point(:lon, :lat), 4326)) "
        "LIMIT 1"
    )
    result = db.execute(query, {"lon": lon, "lat": lat}).fetchone()
    return result[0] if result else None


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Healthcheck confirming database and PostGIS operational connectivity."""
    db.execute(text("SELECT 1")).fetchone()
    return {"status": "ok", "service": "mzigo-backend", "database": "connected"}


@app.post(
    "/deliveries",
    response_model=DeliveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery(request: CreateDeliveryRequest, db: Session = Depends(get_db)):
    """Create a new delivery with write-time PostGIS zone assignment."""
    try:
        validate_kenya_bounds(request.pickup_point.lat, request.pickup_point.lon)
        validate_kenya_bounds(request.dropoff_point.lat, request.dropoff_point.lon)
    except OutOfBoundsCoordinateError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e

    # Ensure shop exists or auto-register demo shop
    shop = db.query(ShopModel).filter(ShopModel.shop_id == request.shop_id).first()
    if not shop:
        shop = ShopModel(shop_id=request.shop_id, name=f"Shop {request.shop_id}")
        db.add(shop)

    # Ensure customer exists or auto-register
    customer = (
        db.query(CustomerModel).filter(CustomerModel.customer_id == request.customer_id).first()
    )
    if not customer:
        phone_hash = (
            hash_phone(request.customer_phone) if request.customer_phone else "default_hash"
        )
        customer = CustomerModel(
            customer_id=request.customer_id,
            name=f"Customer {request.customer_id}",
            phone_hash=phone_hash,
        )
        db.add(customer)

    # Synchronous write-time PostGIS point-in-polygon zone assignment
    pickup_zone = resolve_zone(db, request.pickup_point.lat, request.pickup_point.lon)
    dropoff_zone = resolve_zone(db, request.dropoff_point.lat, request.dropoff_point.lon)

    delivery_id = f"DEL-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(UTC)

    delivery = DeliveryModel(
        delivery_id=delivery_id,
        shop_id=request.shop_id,
        customer_id=request.customer_id,
        pickup_point=f"SRID=4326;POINT({request.pickup_point.lon} {request.pickup_point.lat})",
        dropoff_point=f"SRID=4326;POINT({request.dropoff_point.lon} {request.dropoff_point.lat})",
        pickup_zone_id=pickup_zone,
        dropoff_zone_id=dropoff_zone,
        status="created",
        sla_minutes=request.sla_minutes,
        created_at=now,
        updated_at=now,
    )
    db.add(delivery)

    # Record initial lifecycle status event
    event = DeliveryStatusEventModel(
        event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
        delivery_id=delivery_id,
        from_status="none",
        to_status="created",
        occurred_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(delivery)

    return delivery


@app.get("/deliveries/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(delivery_id: str, db: Session = Depends(get_db)):
    """Retrieve operational delivery state."""
    delivery = (
        db.query(DeliveryModel)
        .filter(
            DeliveryModel.delivery_id == delivery_id,
            DeliveryModel.deleted_at.is_(None),
        )
        .first()
    )
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery '{delivery_id}' not found",
        )
    return delivery


@app.patch("/deliveries/{delivery_id}/status", response_model=DeliveryResponse)
def update_delivery_status(
    delivery_id: str,
    request: UpdateStatusRequest,
    db: Session = Depends(get_db),
):
    """Enforce state machine transition and record audit event."""
    delivery = (
        db.query(DeliveryModel)
        .filter(
            DeliveryModel.delivery_id == delivery_id,
            DeliveryModel.deleted_at.is_(None),
        )
        .first()
    )
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery '{delivery_id}' not found",
        )

    # Strict state machine transition validation
    try:
        validate_transition(delivery.status, request.to_status)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    # Handle rider assignment
    if request.to_status == "assigned":
        if not request.rider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rider_id is required when transitioning to 'assigned'",
            )
        rider = db.query(RiderModel).filter(RiderModel.rider_id == request.rider_id).first()
        if not rider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rider '{request.rider_id}' not found",
            )
        delivery.rider_id = request.rider_id

    from_status = delivery.status
    now = datetime.now(UTC)

    delivery.status = request.to_status
    delivery.updated_at = now

    event = DeliveryStatusEventModel(
        event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
        delivery_id=delivery_id,
        from_status=from_status,
        to_status=request.to_status,
        occurred_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(delivery)

    return delivery


@app.post("/locations", status_code=status.HTTP_202_ACCEPTED)
def post_rider_location(ping: RiderLocationPing, db: Session = Depends(get_db)):
    """Record rider GPS location ping with bounds validation and order assignment check."""
    try:
        validate_kenya_bounds(ping.lat, ping.lon)
    except OutOfBoundsCoordinateError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e

    rider = db.query(RiderModel).filter(RiderModel.rider_id == ping.rider_id).first()
    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rider '{ping.rider_id}' not found",
        )

    # Scenario C-08: Check if ping is for an assigned order
    if ping.delivery_id:
        delivery = (
            db.query(DeliveryModel)
            .filter(
                DeliveryModel.delivery_id == ping.delivery_id,
                DeliveryModel.deleted_at.is_(None),
            )
            .first()
        )
        if not delivery:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery '{ping.delivery_id}' not found",
            )
        if delivery.rider_id != ping.rider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rider '{ping.rider_id}' is not assigned to delivery '{ping.delivery_id}'",
            )

    location_ping = RiderLocationModel(
        ping_id=f"PNG-{uuid.uuid4().hex[:8].upper()}",
        rider_id=ping.rider_id,
        delivery_id=ping.delivery_id,
        lat=ping.lat,
        lon=ping.lon,
        recorded_at=ping.recorded_at or datetime.now(UTC),
    )
    db.add(location_ping)
    db.commit()

    return {"status": "accepted", "ping_id": location_ping.ping_id}
