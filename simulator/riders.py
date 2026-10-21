"""Mzigo Boda-Boda Rider Fleet & Kinematics Engine.

Simulates 20 synthetic boda-boda riders with realistic speeds (15-40 km/h),
noisy route interpolation, and regular GPS location pings.
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.geo import haversine_distance_km

# Canonical list of 20 synthetic riders matching backend seeds
RIDER_FLEET = [
    {"rider_id": "RIDER_01", "name": "Juma Mwangi", "zone": "ZONE_CBD"},
    {"rider_id": "RIDER_02", "name": "Kevin Kiprop", "zone": "ZONE_WESTLANDS"},
    {"rider_id": "RIDER_03", "name": "Brian Omondi", "zone": "ZONE_KILIMANI"},
    {"rider_id": "RIDER_04", "name": "David Njoroge", "zone": "ZONE_UPPERHILL"},
    {"rider_id": "RIDER_05", "name": "Dennis Mutua", "zone": "ZONE_IND_AREA"},
    {"rider_id": "RIDER_06", "name": "Evans Barasa", "zone": "ZONE_EASTLANDS"},
    {"rider_id": "RIDER_07", "name": "Francis Wekesa", "zone": "ZONE_KAREN"},
    {"rider_id": "RIDER_08", "name": "Geoffrey Maina", "zone": "ZONE_CBD"},
    {"rider_id": "RIDER_09", "name": "Hassan Ali", "zone": "ZONE_WESTLANDS"},
    {"rider_id": "RIDER_10", "name": "Ian Kariuki", "zone": "ZONE_KILIMANI"},
    {"rider_id": "RIDER_11", "name": "John Rotich", "zone": "ZONE_UPPERHILL"},
    {"rider_id": "RIDER_12", "name": "Joseph Kimani", "zone": "ZONE_IND_AREA"},
    {"rider_id": "RIDER_13", "name": "Kennedy Musyoka", "zone": "ZONE_EASTLANDS"},
    {"rider_id": "RIDER_14", "name": "Lucas Wafula", "zone": "ZONE_KAREN"},
    {"rider_id": "RIDER_15", "name": "Moses Cheruiyot", "zone": "ZONE_CBD"},
    {"rider_id": "RIDER_16", "name": "Patrick Otieno", "zone": "ZONE_WESTLANDS"},
    {"rider_id": "RIDER_17", "name": "Peter Karanja", "zone": "ZONE_KILIMANI"},
    {"rider_id": "RIDER_18", "name": "Samuel Koech", "zone": "ZONE_UPPERHILL"},
    {"rider_id": "RIDER_19", "name": "Victor Ndungu", "zone": "ZONE_IND_AREA"},
    {"rider_id": "RIDER_20", "name": "Vincent Kibet", "zone": "ZONE_EASTLANDS"},
]


@dataclass
class LocationPing:
    lat: float
    lon: float
    timestamp: datetime
    speed_kmh: float


def generate_kinematic_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    start_time: datetime,
    avg_speed_kmh: float | None = None,
    ping_interval_seconds: float = 15.0,
    noise_std: float = 0.0001,
    rng: random.Random | None = None,
) -> list[LocationPing]:
    """Interpolate a realistic noisy travel path between two coordinates.

    Riders move at 15-40 km/h, generating periodic location pings with
    Gaussian noise simulating urban GPS drift.
    """
    rng = rng or random.Random()
    distance_km = haversine_distance_km(start_lat, start_lon, end_lat, end_lon)

    # If speed is not given, assign random realistic boda speed between 18 and 36 km/h
    speed = avg_speed_kmh or rng.uniform(18.0, 36.0)

    # Total duration in seconds: hours = dist / speed
    duration_hours = max(distance_km / speed, 0.02)  # Minimum 1 minute
    total_seconds = duration_hours * 3600.0

    steps = max(int(total_seconds / ping_interval_seconds), 2)
    step_duration = total_seconds / steps

    pings: list[LocationPing] = []
    current_time = start_time

    for i in range(steps + 1):
        progress = i / steps
        # Linear interpolation
        lat_base = start_lat + (end_lat - start_lat) * progress
        lon_base = start_lon + (end_lon - start_lon) * progress

        # Add GPS jitter (except at exact start and end)
        if 0 < i < steps:
            lat_jitter = rng.gauss(0.0, noise_std)
            lon_jitter = rng.gauss(0.0, noise_std)
            lat = round(lat_base + lat_jitter, 6)
            lon = round(lon_base + lon_jitter, 6)
        else:
            lat = round(lat_base, 6)
            lon = round(lon_base, 6)

        pings.append(
            LocationPing(
                lat=lat,
                lon=lon,
                timestamp=current_time,
                speed_kmh=round(speed, 1),
            )
        )
        current_time += timedelta(seconds=step_duration)

    return pings
