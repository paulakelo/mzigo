"""Integration tests for Mzigo operational FastAPI backend & PostGIS."""

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_create_delivery_with_zone_assignment():
    # Pickup: CBD (lon: 36.82, lat: -1.285)
    # Dropoff: Westlands (lon: 36.80, lat: -1.26)
    payload = {
        "shop_id": "SHOP_CBD_01",
        "customer_id": "CUST_001",
        "customer_phone": "+254712345678",
        "pickup_point": {"lat": -1.285, "lon": 36.82},
        "dropoff_point": {"lat": -1.26, "lon": 36.80},
        "sla_minutes": 40,
    }
    response = client.post("/deliveries", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["delivery_id"].startswith("DEL-")
    assert data["status"] == "created"
    assert data["pickup_zone_id"] == "ZONE_CBD"
    assert data["dropoff_zone_id"] == "ZONE_WESTLANDS"
    assert data["sla_minutes"] == 40

    delivery_id = data["delivery_id"]

    # Verify retrieval
    get_res = client.get(f"/deliveries/{delivery_id}")
    assert get_res.status_code == 200
    assert get_res.json()["delivery_id"] == delivery_id


def test_create_delivery_out_of_bounds_rejected():
    payload = {
        "shop_id": "SHOP_CBD_01",
        "customer_id": "CUST_001",
        "pickup_point": {"lat": 51.5074, "lon": -0.1278},  # London
        "dropoff_point": {"lat": -1.26, "lon": 36.80},
    }
    response = client.post("/deliveries", json=payload)
    assert response.status_code == 422
    assert "outside Kenya" in response.json()["detail"]


def test_state_machine_workflow_and_rejections():
    # 1. Create delivery
    payload = {
        "shop_id": "SHOP_CBD_01",
        "customer_id": "CUST_002",
        "pickup_point": {"lat": -1.285, "lon": 36.82},
        "dropoff_point": {"lat": -1.29, "lon": 36.78},  # Kilimani
    }
    res = client.post("/deliveries", json=payload)
    assert res.status_code == 201
    delivery_id = res.json()["delivery_id"]

    # 2. Attempt illegal transition: created -> delivered (HTTP 409)
    bad_res = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "delivered"},
    )
    assert bad_res.status_code == 409

    # 3. Legal: created -> assigned
    res_assigned = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "assigned", "rider_id": "RIDER_01"},
    )
    assert res_assigned.status_code == 200
    assert res_assigned.json()["status"] == "assigned"
    assert res_assigned.json()["rider_id"] == "RIDER_01"

    # 4. Legal: assigned -> picked_up
    res_picked = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "picked_up"},
    )
    assert res_picked.status_code == 200
    assert res_picked.json()["status"] == "picked_up"

    # 5. Legal: picked_up -> in_transit
    res_transit = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "in_transit"},
    )
    assert res_transit.status_code == 200
    assert res_transit.json()["status"] == "in_transit"

    # 6. Legal: in_transit -> delivered
    res_delivered = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "delivered"},
    )
    assert res_delivered.status_code == 200
    assert res_delivered.json()["status"] == "delivered"

    # 7. Attempt transition out of terminal state: delivered -> in_transit (HTTP 409)
    res_terminal = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "in_transit"},
    )
    assert res_terminal.status_code == 409


def test_rider_location_pings_and_unassigned_rejection():
    # 1. Normal location ping
    ping_payload = {
        "rider_id": "RIDER_02",
        "lat": -1.285,
        "lon": 36.82,
    }
    res = client.post("/locations", json=ping_payload)
    assert res.status_code == 202
    assert res.json()["status"] == "accepted"

    # 2. Out-of-bounds location ping
    bad_ping = {
        "rider_id": "RIDER_02",
        "lat": 10.0,
        "lon": 50.0,
    }
    assert client.post("/locations", json=bad_ping).status_code == 422

    # 3. Create delivery assigned to RIDER_01
    deliv_payload = {
        "shop_id": "SHOP_CBD_01",
        "customer_id": "CUST_003",
        "pickup_point": {"lat": -1.285, "lon": 36.82},
        "dropoff_point": {"lat": -1.285, "lon": 36.82},
    }
    d_res = client.post("/deliveries", json=deliv_payload)
    delivery_id = d_res.json()["delivery_id"]
    client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "assigned", "rider_id": "RIDER_01"},
    )

    # 4. RIDER_03 attempts to post location for RIDER_01's delivery (Scenario C-08 rejection)
    unassigned_ping = {
        "rider_id": "RIDER_03",
        "delivery_id": delivery_id,
        "lat": -1.285,
        "lon": 36.82,
    }
    conflict_res = client.post("/locations", json=unassigned_ping)
    assert conflict_res.status_code == 400
    assert "not assigned" in conflict_res.json()["detail"]
