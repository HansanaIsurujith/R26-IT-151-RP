"""Create reproducible evidence that a detector update changes route risk.

The script runs the real API contract in-process, posts one clearly labelled
simulated detector event, and stores before/update/after evidence. It does not
claim that a teammate's deployed detector was connected.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


COMPONENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMPONENT_ROOT))


def route_request(method):
    return {
        "origin": {"latitude": 7.0917, "longitude": 79.9942, "label": "Gampaha"},
        "destination": {
            "latitude": 7.1447,
            "longitude": 80.0960,
            "label": "Nittambuwa",
        },
        "method": method,
        "risk_aversion": 8,
        "max_detour_pct": 30,
        "include_comparison": True,
    }


def compact_route(payload):
    route = payload["route"]
    return {
        "hazard_version": payload["network"]["hazard_version"],
        "method": route["method"],
        "duration_min": route["duration_min"],
        "risk_score": route["risk_score"],
        "risk_exposure": route["risk_exposure"],
        "maximum_segment_risk": route["maximum_segment_risk"],
        "same_as_fastest": route["same_as_fastest"],
        "node_count": route["segment_count"] + 1,
        "route_id": payload["route_id"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        type=Path,
        default=COMPONENT_ROOT / "network" / "gampaha_road_network_with_hazards.graphml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=COMPONENT_ROOT / "results" / "live_hazard_update_demo.json",
    )
    args = parser.parse_args()

    os.environ["ROUTING_NETWORK_PATH"] = str(args.network.resolve())
    os.environ["ROUTING_PRELOAD"] = "0"
    os.environ["ROUTING_HAZARD_DB_PATH"] = ":memory:"

    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as client:
        fastest_before_payload = client.post(
            "/route/optimize", json=route_request("shortest_path")
        ).json()
        safe_before_payload = client.post(
            "/route/optimize", json=route_request("objective_fuzzy")
        ).json()
        coordinates = fastest_before_payload["route"]["coordinates"]
        update_coordinate = coordinates[len(coordinates) // 2]
        detector_payload = {
            "coordinate": update_coordinate,
            "radius_km": 2.0,
            "hazards": {"flood": 1.0, "landslide": 1.0},
            "source": "reproducible_simulated_detector_demo",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        update_response = client.post("/hazards/update", json=detector_payload)
        update_response.raise_for_status()
        fastest_after_payload = client.post(
            "/route/optimize", json=route_request("shortest_path")
        ).json()
        safe_after_payload = client.post(
            "/route/optimize", json=route_request("objective_fuzzy")
        ).json()

    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Reproducible API integration demonstration using a simulated detector "
            "payload; not evidence of a deployed teammate detector connection."
        ),
        "sequence": [
            "calculate routes",
            "POST /hazards/update",
            "confirm hazard_version increment",
            "recalculate routes",
            "compare risk and path outcome",
        ],
        "detector_payload": detector_payload,
        "update_response": update_response.json(),
        "fastest_before": compact_route(fastest_before_payload),
        "fastest_after": compact_route(fastest_after_payload),
        "smart_safe_before": compact_route(safe_before_payload),
        "smart_safe_after": compact_route(safe_after_payload),
        "verified": {
            "hazard_version_incremented": (
                fastest_after_payload["network"]["hazard_version"]
                == fastest_before_payload["network"]["hazard_version"] + 1
            ),
            "same_fastest_path_risk_changed": (
                fastest_after_payload["route"]["risk_exposure"]
                != fastest_before_payload["route"]["risk_exposure"]
            ),
            "smart_safe_path_changed_when_beneficial": (
                safe_after_payload["route"]["coordinates"]
                != safe_before_payload["route"]["coordinates"]
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence["verified"], indent=2))
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
