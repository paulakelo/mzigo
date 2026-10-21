"""Mzigo Delivery Order Generator & Lifecycle Simulator.

Walks orders through the complete state machine:
created -> assigned -> picked_up -> in_transit -> delivered | failed
Emits realistic rider location pings throughout the journey.
"""

import random
from dataclasses import dataclass
from typing import Any

from simulator.clock import VirtualClock
from simulator.riders import RIDER_FLEET, generate_kinematic_route

# Zone coordinate centers (lat, lon) for realistic coordinate generation
ZONE_CENTROIDS = {
    "ZONE_CBD": (-1.285, 36.822),
    "ZONE_WESTLANDS": (-1.262, 36.804),
    "ZONE_KILIMANI": (-1.295, 36.787),
    "ZONE_UPPERHILL": (-1.305, 36.815),
    "ZONE_IND_AREA": (-1.320, 36.850),
    "ZONE_EASTLANDS": (-1.295, 36.892),
    "ZONE_KAREN": (-1.335, 36.710),
}

SHOPS = [
    {"shop_id": "SHOP_CBD_01", "name": "Nairobi Electronics Hub", "zone": "ZONE_CBD"},
    {"shop_id": "SHOP_WEST_01", "name": "Westlands Fashion Boutique", "zone": "ZONE_WESTLANDS"},
    {"shop_id": "SHOP_KIL_01", "name": "Kilimani Gourmet Grocers", "zone": "ZONE_KILIMANI"},
]


@dataclass
class DeliverySimulationResult:
    delivery_id: str
    shop_id: str
    customer_id: str
    rider_id: str
    status: str
    pickup_zone: str
    dropoff_zone: str
    ping_count: int
    duration_minutes: float


def sample_point_in_zone(zone_id: str, rng: random.Random) -> tuple[float, float]:
    """Sample a coordinate around the centroid of a zone."""
    lat_center, lon_center = ZONE_CENTROIDS.get(zone_id, (-1.285, 36.822))
    # Add small dispersion within zone polygon
    lat = round(lat_center + rng.uniform(-0.008, 0.008), 6)
    lon = round(lon_center + rng.uniform(-0.008, 0.008), 6)
    return lat, lon


def simulate_single_delivery(
    client: Any,
    clock: VirtualClock,
    rng: random.Random,
    rider: dict[str, str] | None = None,
    failure_rate: float = 0.05,
) -> DeliverySimulationResult:
    """Simulate a complete single delivery lifecycle through the operational API."""
    rider = rider or rng.choice(RIDER_FLEET)
    shop = rng.choice(SHOPS)
    dropoff_zone_id = rng.choice(list(ZONE_CENTROIDS.keys()))

    pickup_lat, pickup_lon = sample_point_in_zone(shop["zone"], rng)
    dropoff_lat, dropoff_lon = sample_point_in_zone(dropoff_zone_id, rng)

    customer_id = f"CUST_{rng.randint(100, 999)}"
    phone = f"+2547{rng.randint(10000000, 99999999)}"
    sla_minutes = rng.choice([30, 45, 60])

    # 1. Create delivery (status: created)
    create_payload = {
        "shop_id": shop["shop_id"],
        "customer_id": customer_id,
        "customer_phone": phone,
        "pickup_point": {"lat": pickup_lat, "lon": pickup_lon},
        "dropoff_point": {"lat": dropoff_lat, "lon": dropoff_lon},
        "sla_minutes": sla_minutes,
    }
    res = client.post("/deliveries", json=create_payload)
    if res.status_code != 201:
        raise RuntimeError(f"Failed to create delivery: {res.text}")
    delivery_data = res.json()
    delivery_id = delivery_data["delivery_id"]

    start_sim_time = clock.now()
    ping_count = 0

    # 2. Assign rider (status: assigned)
    clock.advance_minutes(rng.uniform(1.0, 3.0))
    res_assigned = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "assigned", "rider_id": rider["rider_id"]},
    )
    if res_assigned.status_code != 200:
        raise RuntimeError(f"Failed to assign rider: {res_assigned.text}")

    # 3. Rider travels to pickup location
    rider_start_lat, rider_start_lon = sample_point_in_zone(rider["zone"], rng)
    pickup_pings = generate_kinematic_route(
        rider_start_lat,
        rider_start_lon,
        pickup_lat,
        pickup_lon,
        start_time=clock.now(),
        rng=rng,
    )
    for p in pickup_pings:
        client.post(
            "/locations",
            json={
                "rider_id": rider["rider_id"],
                "lat": p.lat,
                "lon": p.lon,
                "recorded_at": p.timestamp.isoformat(),
            },
        )
        ping_count += 1

    if pickup_pings:
        clock.current_time = pickup_pings[-1].timestamp

    # 4. Pick up package (status: picked_up)
    clock.advance_minutes(rng.uniform(2.0, 5.0))
    res_picked = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "picked_up"},
    )
    if res_picked.status_code != 200:
        raise RuntimeError(f"Failed to set picked_up: {res_picked.text}")

    # 5. In transit to customer (status: in_transit)
    clock.advance_seconds(30.0)
    res_transit = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": "in_transit"},
    )
    if res_transit.status_code != 200:
        raise RuntimeError(f"Failed to set in_transit: {res_transit.text}")

    # 6. Emit in-transit GPS pings linked to delivery
    transit_pings = generate_kinematic_route(
        pickup_lat,
        pickup_lon,
        dropoff_lat,
        dropoff_lon,
        start_time=clock.now(),
        rng=rng,
    )
    for p in transit_pings:
        client.post(
            "/locations",
            json={
                "rider_id": rider["rider_id"],
                "delivery_id": delivery_id,
                "lat": p.lat,
                "lon": p.lon,
                "recorded_at": p.timestamp.isoformat(),
            },
        )
        ping_count += 1

    if transit_pings:
        clock.current_time = transit_pings[-1].timestamp

    # 7. Final status disposition (delivered or failed)
    is_failure = rng.random() < failure_rate
    final_status = "failed" if is_failure else "delivered"
    clock.advance_minutes(rng.uniform(1.0, 3.0))

    res_final = client.patch(
        f"/deliveries/{delivery_id}/status",
        json={"to_status": final_status},
    )
    if res_final.status_code != 200:
        raise RuntimeError(f"Failed to set {final_status}: {res_final.text}")

    duration_minutes = (clock.now() - start_sim_time).total_seconds() / 60.0

    return DeliverySimulationResult(
        delivery_id=delivery_id,
        shop_id=shop["shop_id"],
        customer_id=customer_id,
        rider_id=rider["rider_id"],
        status=final_status,
        pickup_zone=delivery_data.get("pickup_zone_id") or "UNKNOWN",
        dropoff_zone=delivery_data.get("dropoff_zone_id") or "UNKNOWN",
        ping_count=ping_count,
        duration_minutes=round(duration_minutes, 1),
    )
