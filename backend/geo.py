"""Mzigo Geospatial Validation & Helper Functions.

Validates Kenya bounding coordinates and calculates distance.
"""

import math

# Kenya Geographic Bounding Box
KENYA_MIN_LAT = -4.7
KENYA_MAX_LAT = 5.1
KENYA_MIN_LON = 33.8
KENYA_MAX_LON = 41.9


class OutOfBoundsCoordinateError(ValueError):
    """Raised when coordinates fall outside national Kenya bounds."""

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        super().__init__(
            f"Coordinates ({lat}, {lon}) are outside Kenya boundaries: "
            f"lat [{KENYA_MIN_LAT}, {KENYA_MAX_LAT}], lon [{KENYA_MIN_LON}, {KENYA_MAX_LON}]"
        )


def validate_kenya_bounds(lat: float, lon: float) -> bool:
    """Validate that coordinates fall strictly inside Kenya bounds."""
    if not (KENYA_MIN_LAT <= lat <= KENYA_MAX_LAT and KENYA_MIN_LON <= lon <= KENYA_MAX_LON):
        raise OutOfBoundsCoordinateError(lat, lon)
    return True


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two points in kilometers."""
    radius_earth_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_earth_km * c
