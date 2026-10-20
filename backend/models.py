"""Mzigo Operational Database Models & Pydantic Schemas."""

import hashlib
import os
from datetime import UTC, datetime

from geoalchemy2 import Geometry
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Double, ForeignKey, Integer, String

from backend.db.session import Base

# Secret salt for PII hashing (default test salt, overridable via env)
SALT = os.getenv("MZIGO_PII_SALT", "mzigo_nairobi_secret_salt_2026")


def hash_phone(phone: str) -> str:
    """Hash phone number with salted SHA-256 (preserves privacy, allows grouping)."""
    clean_phone = "".join(filter(str.isdigit, phone))
    return hashlib.sha256(f"{clean_phone}:{SALT}".encode()).hexdigest()[:24]


# -----------------------------------------------------------------------------
# SQLAlchemy ORM Models
# -----------------------------------------------------------------------------


class ZoneModel(Base):
    __tablename__ = "zones"

    zone_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    polygon = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ShopModel(Base):
    __tablename__ = "shops"

    shop_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    zone_id = Column(String(50), ForeignKey("zones.zone_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class CustomerModel(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    phone_hash = Column(String(64), nullable=False)
    zone_id = Column(String(50), ForeignKey("zones.zone_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RiderModel(Base):
    __tablename__ = "riders"

    rider_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    phone_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="available")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class DeliveryModel(Base):
    __tablename__ = "deliveries"

    delivery_id = Column(String(50), primary_key=True)
    shop_id = Column(String(50), ForeignKey("shops.shop_id"), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    rider_id = Column(String(50), ForeignKey("riders.rider_id"), nullable=True)
    pickup_point = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    dropoff_point = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    pickup_zone_id = Column(String(50), ForeignKey("zones.zone_id"), nullable=True)
    dropoff_zone_id = Column(String(50), ForeignKey("zones.zone_id"), nullable=True)
    status = Column(String(30), nullable=False, default="created")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    sla_minutes = Column(Integer, nullable=False, default=45)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class DeliveryStatusEventModel(Base):
    __tablename__ = "delivery_status_events"

    event_id = Column(String(50), primary_key=True)
    delivery_id = Column(String(50), ForeignKey("deliveries.delivery_id"), nullable=False)
    from_status = Column(String(30), nullable=False)
    to_status = Column(String(30), nullable=False)
    occurred_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RiderLocationModel(Base):
    __tablename__ = "rider_locations"

    ping_id = Column(String(50), primary_key=True)
    rider_id = Column(String(50), ForeignKey("riders.rider_id"), nullable=False)
    delivery_id = Column(String(50), ForeignKey("deliveries.delivery_id"), nullable=True)
    lat = Column(Double, nullable=False)
    lon = Column(Double, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


# -----------------------------------------------------------------------------
# Pydantic Request & Response Schemas
# -----------------------------------------------------------------------------


class Coordinate(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class CreateDeliveryRequest(BaseModel):
    shop_id: str
    customer_id: str
    customer_phone: str | None = None
    pickup_point: Coordinate
    dropoff_point: Coordinate
    sla_minutes: int = 45


class UpdateStatusRequest(BaseModel):
    to_status: str
    rider_id: str | None = None
    reason: str | None = None


class RiderLocationPing(BaseModel):
    rider_id: str
    delivery_id: str | None = None
    lat: float
    lon: float
    recorded_at: datetime | None = None


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    delivery_id: str
    shop_id: str
    customer_id: str
    rider_id: str | None = None
    pickup_zone_id: str | None = None
    dropoff_zone_id: str | None = None
    status: str
    sla_minutes: int
    created_at: datetime
    updated_at: datetime
