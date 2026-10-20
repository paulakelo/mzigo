"""Mzigo Operational Database Models & Pydantic Schemas."""

import hashlib
import os
from datetime import datetime

from pydantic import BaseModel, Field

# Secret salt for PII hashing (default test salt, overridable via env)
SALT = os.getenv("MZIGO_PII_SALT", "mzigo_nairobi_secret_salt_2026")


def hash_phone(phone: str) -> str:
    """Hash phone number with salted SHA-256 (preserves privacy, allows grouping)."""
    clean_phone = "".join(filter(str.isdigit, phone))
    return hashlib.sha256(f"{clean_phone}:{SALT}".encode()).hexdigest()[:24]


class Coordinate(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class CreateDeliveryRequest(BaseModel):
    shop_id: str
    customer_id: str
    customer_phone: str
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
