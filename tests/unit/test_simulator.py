"""Unit tests for Mzigo deterministic simulator & kinematics engine."""

import random
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app import app
from simulator.chaos import (
    inject_illegal_status_jump,
    inject_out_of_bounds_order,
    inject_speed_anomaly,
    inject_terminal_state_mutation,
    inject_unassigned_location_ping,
)
from simulator.clock import VirtualClock
from simulator.deliveries import simulate_single_delivery
from simulator.riders import RIDER_FLEET, generate_kinematic_route

client = TestClient(app)


def test_virtual_clock_progression():
    clock = VirtualClock(start_time=datetime(2026, 10, 20, 8, 0, 0, tzinfo=UTC), speedup=60.0)
    assert clock.now().hour == 8
    clock.advance_minutes(30.0)
    assert clock.now().minute == 30
    clock.advance_seconds(90.0)
    assert clock.now().minute == 31
    assert clock.now().second == 30


def test_kinematic_route_generation():
    rng = random.Random(42)
    start_time = datetime(2026, 10, 20, 8, 0, 0, tzinfo=UTC)
    # CBD to Westlands (~3.5 km)
    pings = generate_kinematic_route(
        start_lat=-1.285,
        start_lon=36.820,
        end_lat=-1.265,
        end_lon=36.805,
        start_time=start_time,
        ping_interval_seconds=15.0,
        rng=rng,
    )
    assert len(pings) > 5
    assert pings[0].lat == -1.285
    assert pings[0].lon == 36.820
    assert pings[-1].lat == -1.265
    assert pings[-1].lon == 36.805
    # Speeds must be within boda-boda range (15 - 40 km/h)
    for p in pings:
        assert 15.0 <= p.speed_kmh <= 40.0


def test_simulate_single_delivery_lifecycle():
    rng = random.Random(123)
    clock = VirtualClock(start_time=datetime(2026, 10, 20, 9, 0, 0, tzinfo=UTC))
    rider = RIDER_FLEET[0]

    result = simulate_single_delivery(client, clock, rng, rider=rider, failure_rate=0.0)
    assert result.delivery_id.startswith("DEL-")
    assert result.status == "delivered"
    assert result.rider_id == rider["rider_id"]
    assert result.ping_count > 10
    assert result.duration_minutes > 5.0


def test_simulator_chaos_injections():
    rng = random.Random(999)
    clock = VirtualClock()

    # Out of bounds order
    res_c07 = inject_out_of_bounds_order(client)
    assert res_c07["status"] == "passed"

    # Create delivery for state machine violations
    deliv = simulate_single_delivery(client, clock, rng, failure_rate=0.0)

    # Illegal jump
    res_jump = inject_illegal_status_jump(client, deliv.delivery_id)
    assert res_jump["status"] == "passed"

    # Terminal state mutation
    res_term = inject_terminal_state_mutation(client, deliv.delivery_id)
    assert res_term["status"] == "passed"

    # Unassigned location ping (Scenario C-08)
    res_c08 = inject_unassigned_location_ping(
        client, rider_id="RIDER_15", delivery_id=deliv.delivery_id
    )
    assert res_c08["status"] == "passed"

    # Speed anomaly (> 120 km/h)
    res_speed = inject_speed_anomaly(client, rider_id=deliv.rider_id, delivery_id=deliv.delivery_id)
    assert res_speed["status"] == "passed"
