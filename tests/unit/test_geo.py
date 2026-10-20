"""Unit tests for Mzigo geospatial validation and haversine calculations."""

import pytest

from backend.geo import OutOfBoundsCoordinateError, haversine_distance_km, validate_kenya_bounds


def test_valid_kenya_coordinates():
    # Nairobi CBD coordinates
    assert validate_kenya_bounds(-1.286389, 36.817223) is True
    # Mombasa coordinates
    assert validate_kenya_bounds(-4.043477, 39.668206) is True
    # Kisumu coordinates
    assert validate_kenya_bounds(-0.102214, 34.761715) is True


def test_out_of_bounds_coordinates():
    # London, UK
    with pytest.raises(OutOfBoundsCoordinateError):
        validate_kenya_bounds(51.5074, -0.1278)

    # South Africa
    with pytest.raises(OutOfBoundsCoordinateError):
        validate_kenya_bounds(-33.9249, 18.4241)


def test_haversine_distance():
    # Nairobi CBD to Westlands (approx 3.5 km)
    dist = haversine_distance_km(-1.2864, 36.8172, -1.2635, 36.8028)
    assert 3.0 < dist < 4.0
