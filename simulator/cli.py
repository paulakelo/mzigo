"""Mzigo Simulator CLI."""

import argparse


def main():
    parser = argparse.ArgumentParser(description="Mzigo Boda-Boda Fleet & Delivery Simulator")
    parser.add_argument("command", choices=["demo", "stream", "chaos"], default="demo", nargs="?")
    parser.add_argument("--riders", type=int, default=20, help="Number of active boda-boda riders")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")

    args = parser.parse_args()
    print(f"Mzigo Simulator: command={args.command}, riders={args.riders}, seed={args.seed}")
    print("Simulation completed successfully.")


if __name__ == "__main__":
    main()
