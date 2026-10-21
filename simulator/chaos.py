"""Mzigo Chaos Injection Engine.

Injects API edge anomalies and operational violations to verify system resilience:
- Out of bounds coordinates (Scenario C-07 edge rejection)
- Illegal status leaps and terminal mutations (Scenario C-09)
- Unassigned order location pings (Scenario C-08)
- Speed anomalies (> 120 km/h)
"""

from typing import Any


def inject_out_of_bounds_order(client: Any) -> dict[str, Any]:
    """Inject order with coordinates outside Kenya (e.g. London). Expects HTTP 422."""
    payload = {
        "shop_id": "SHOP_CBD_01",
        "customer_id": "CUST_CHAOS_01",
        "pickup_point": {"lat": 51.5074, "lon": -0.1278},  # London
        "dropoff_point": {"lat": -1.26, "lon": 36.80},
    }
    res = client.post("/deliveries", json=payload)
    assert res.status_code == 422, f"Expected 422, got {res.status_code}"
    return {
        "scenario": "out_of_bounds_coordinates",
        "status": "passed",
        "response_code": res.status_code,
    }


def inject_illegal_status_jump(client: Any, delivery_id: str) -> dict[str, Any]:
    """Attempt illegal jump: created -> delivered directly. Expects HTTP 409."""
    res = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "delivered"},
    )
    assert res.status_code == 409, f"Expected 409, got {res.status_code}"
    return {
        "scenario": "illegal_status_jump",
        "status": "passed",
        "response_code": res.status_code,
    }


def inject_unassigned_location_ping(client: Any, rider_id: str, delivery_id: str) -> dict[str, Any]:
    """Rider attempts to post location for an order assigned to another rider. Expects HTTP 400."""
    payload = {
        "rider_id": rider_id,
        "delivery_id": delivery_id,
        "lat": -1.285,
        "lon": 36.820,
    }
    res = client.post("/locations", json=payload)
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    return {
        "scenario": "unassigned_order_ping",
        "status": "passed",
        "response_code": res.status_code,
    }


def inject_speed_anomaly(client: Any, rider_id: str, delivery_id: str) -> dict[str, Any]:
    """Rider posts two consecutive pings 60 km apart in 5 seconds (> 120 km/h anomaly)."""
    # First ping: Nairobi CBD
    p1 = {
        "rider_id": rider_id,
        "delivery_id": delivery_id,
        "lat": -1.285,
        "lon": 36.820,
    }
    res1 = client.post("/locations", json=p1)
    assert res1.status_code == 202

    # Second ping: 60 km away (near Thika / Machakos)
    p2 = {
        "rider_id": rider_id,
        "delivery_id": delivery_id,
        "lat": -1.040,
        "lon": 37.070,
    }
    res2 = client.post("/locations", json=p2)
    assert res2.status_code == 202

    return {
        "scenario": "speed_anomaly_injection",
        "status": "passed",
        "details": "Two pings injected 60 km apart; flagged for downstream Gold model",
    }


def inject_terminal_state_mutation(client: Any, delivery_id: str) -> dict[str, Any]:
    """Attempt to mutate status of already delivered/failed order. Expects HTTP 409."""
    res = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "in_transit"},
    )
    assert res.status_code == 409, f"Expected 409, got {res.status_code}"
    return {
        "scenario": "terminal_state_mutation",
        "status": "passed",
        "response_code": res.status_code,
    }
