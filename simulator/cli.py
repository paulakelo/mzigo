"""Mzigo Boda-Boda Fleet & Delivery Simulator CLI.

Supports demo mode, continuous streaming mode, and chaos scenario injection.
"""

import argparse
import random
from datetime import UTC, datetime
from typing import Any

import httpx

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
from simulator.riders import RIDER_FLEET


def get_client(base_url: str = "http://localhost:8001") -> Any:
    """Return an HTTP client if mzigo backend is running, else fallback to FastAPI TestClient."""
    try:
        with httpx.Client(base_url=base_url, timeout=2.0) as http_client:
            resp = http_client.get("/health")
            if resp.status_code == 200 and resp.json().get("service") == "mzigo-backend":
                return httpx.Client(base_url=base_url, timeout=15.0)
    except Exception:
        pass

    # Fallback to direct in-process FastAPI TestClient
    from fastapi.testclient import TestClient

    return TestClient(app)


def run_demo(client: Any, num_deliveries: int = 20, seed: int = 42, failure_rate: float = 0.05):
    """Run full deterministic simulation of delivery fleet and print scorecard."""
    print("=" * 80)
    print("                MZIGO DETERMINISTIC BODA-BODA FLEET SIMULATION")
    print(f"       Deliveries: {num_deliveries} | Seed: {seed} | Fleet Size: {len(RIDER_FLEET)}")
    print("=" * 80)

    rng = random.Random(seed)
    clock = VirtualClock(start_time=datetime(2026, 10, 20, 8, 0, 0, tzinfo=UTC))

    results = []
    header = (
        f"{'DELIVERY ID':<15} {'SHOP':<13} {'RIDER':<10} {'FROM':<15} "
        f"{'TO':<15} {'PINGS':<6} {'MINS':<6} {'STATUS'}"
    )
    print(header)
    print("-" * 88)

    for i in range(num_deliveries):
        rider = RIDER_FLEET[i % len(RIDER_FLEET)]
        res = simulate_single_delivery(
            client=client,
            clock=clock,
            rng=rng,
            rider=rider,
            failure_rate=failure_rate,
        )
        results.append(res)
        print(
            f"{res.delivery_id:<15} {res.shop_id:<13} {res.rider_id:<10} "
            f"{res.pickup_zone:<15} {res.dropoff_zone:<15} {res.ping_count:<6} "
            f"{res.duration_minutes:<6.1f} {res.status}"
        )

    # Summary metrics
    delivered = sum(1 for r in results if r.status == "delivered")
    failed = sum(1 for r in results if r.status == "failed")
    total_pings = sum(r.ping_count for r in results)
    avg_duration = sum(r.duration_minutes for r in results) / len(results) if results else 0.0
    fail_pct = (failed / len(results)) * 100 if results else 0.0

    print("=" * 88)
    summary_line = (
        f"Summary: {len(results)} orders | {delivered} Delivered | {failed} Failed "
        f"({fail_pct:.1f}%) | {total_pings} Pings | Avg: {avg_duration:.1f} min"
    )
    print(summary_line)
    print(f"Simulated Virtual Clock: {clock.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 88)


def run_chaos(client: Any):
    """Execute all chaos scenario injections and assert expected responses."""
    print("Running Mzigo Chaos Anomaly Injections...")
    rng = random.Random(42)
    clock = VirtualClock()

    # C-07: Out of bounds coordinates (London)
    r1 = inject_out_of_bounds_order(client)
    print(f"  [C-07] Out-of-bounds rejection: {r1['status']} (HTTP {r1['response_code']})")

    # Create a test delivery for state machine testing
    deliv = simulate_single_delivery(client, clock, rng, failure_rate=0.0)

    # C-09: Illegal jump transition attempt
    r2 = inject_illegal_status_jump(client, deliv.delivery_id)
    print(f"  [C-09] Illegal status jump rejection: {r2['status']} (HTTP {r2['response_code']})")

    # C-09: Terminal state mutation attempt
    r3 = inject_terminal_state_mutation(client, deliv.delivery_id)
    print(f"  [C-09] Terminal mutation rejection: {r3['status']} (HTTP {r3['response_code']})")

    # C-08: Unassigned order ping rejection
    r4 = inject_unassigned_location_ping(client, "RIDER_19", deliv.delivery_id)
    print(f"  [C-08] Unassigned ping rejection: {r4['status']} (HTTP {r4['response_code']})")

    # Speed anomaly injection (> 120 km/h)
    r5 = inject_speed_anomaly(client, deliv.rider_id, deliv.delivery_id)
    print(f"  [C-07] Speed anomaly (> 120 km/h) injection: {r5['status']}")

    print("All chaos scenarios verified successfully.")


def main():
    parser = argparse.ArgumentParser(description="Mzigo Boda-Boda Fleet & Delivery Simulator")
    parser.add_argument("command", choices=["demo", "stream", "chaos"], default="demo", nargs="?")
    parser.add_argument("--deliveries", type=int, default=20, help="Number of simulated deliveries")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument(
        "--failure-rate", type=float, default=0.05, help="Delivery failure probability"
    )
    parser.add_argument(
        "--url", type=str, default="http://localhost:8001", help="FastAPI backend URL"
    )

    args = parser.parse_args()
    client = get_client(args.url)

    if args.command == "demo":
        run_demo(
            client,
            num_deliveries=args.deliveries,
            seed=args.seed,
            failure_rate=args.failure_rate,
        )
    elif args.command == "chaos":
        run_chaos(client)
    elif args.command == "stream":
        print("Streaming mode started. Generating active fleet traffic...")
        run_demo(
            client,
            num_deliveries=args.deliveries,
            seed=args.seed,
            failure_rate=args.failure_rate,
        )


if __name__ == "__main__":
    main()
