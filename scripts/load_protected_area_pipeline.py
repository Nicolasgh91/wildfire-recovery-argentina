#!/usr/bin/env python3
"""
Pipeline script to load protected areas and compute fire intersections.
"""

import argparse
import subprocess
import sys


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Protected areas + intersections pipeline")
    parser.add_argument("--source", default="ign", help="Source for protected areas (ign, apn_wfs)")
    parser.add_argument("--simplify", type=int, default=100, help="Simplify geometries in meters")
    parser.add_argument("--truncate", action="store_true", help="Truncate protected_areas before load")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no inserts")
    parser.add_argument("--intersection-mode", default="incremental", choices=["batch", "incremental"])

    args = parser.parse_args()

    load_cmd = [
        sys.executable,
        "scripts/load_protected_areas.py",
        "--source",
        args.source,
        "--simplify",
        str(args.simplify),
    ]
    if args.truncate:
        load_cmd.append("--truncate")
    if args.dry_run:
        load_cmd.append("--dry-run")

    intersect_cmd = [
        sys.executable,
        "scripts/cross_fire_protected_areas.py",
        "--mode",
        args.intersection_mode,
    ]

    run_command(load_cmd)
    if not args.dry_run:
        run_command(intersect_cmd)


if __name__ == "__main__":
    main()
