"""Bridge the included Flood/Landslide API to the routing hazard endpoint.

Run both APIs, then execute with --once for a viva demonstration or omit
--once to poll continuously. Only the highest-risk zones are forwarded to keep
the local prototype responsive and its update history auditable.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(url, method="GET", payload=None, timeout=120):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "Suraksha-Lanka-Bridge/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def merge_zones(flood_payload, landslide_payload):
    merged = {}
    for hazard, payload in (("flood", flood_payload), ("landslide", landslide_payload)):
        for zone in payload.get("zones", []):
            key = (round(float(zone["lat"]), 5), round(float(zone["lng"]), 5))
            merged.setdefault(key, {})[hazard] = float(zone["probability"])
    return [
        {"latitude": latitude, "longitude": longitude, "hazards": hazards}
        for (latitude, longitude), hazards in merged.items()
    ]


def sync_once(source_url, route_url, minimum_probability, max_zones, radius_km):
    flood = request_json(source_url + "/predict/flood/today")
    landslide = request_json(source_url + "/predict/landslide/today")
    zones = merge_zones(flood, landslide)
    zones = [
        zone
        for zone in zones
        if max(zone["hazards"].values(), default=0.0) >= minimum_probability
    ]
    zones.sort(key=lambda zone: max(zone["hazards"].values()), reverse=True)
    zones = zones[:max_zones]

    updates = []
    observed_at = datetime.now(timezone.utc).isoformat()
    for zone in zones:
        payload = {
            "coordinate": {
                "latitude": zone["latitude"],
                "longitude": zone["longitude"],
                "label": "Flood/Landslide detector grid",
            },
            "radius_km": radius_km,
            "hazards": zone["hazards"],
            "source": "flood_landslide_api_bridge",
            "observed_at": observed_at,
        }
        updates.append(
            request_json(route_url + "/hazards/update", method="POST", payload=payload)
        )
    return {
        "source_zones": len(merge_zones(flood, landslide)),
        "forwarded_zones": len(updates),
        "last_hazard_version": updates[-1]["hazard_version"] if updates else None,
        "updates": updates,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default="http://127.0.0.1:8000")
    parser.add_argument("--route-url", default="http://127.0.0.1:8001")
    parser.add_argument("--minimum-probability", type=float, default=0.35)
    parser.add_argument("--max-zones", type=int, default=20)
    parser.add_argument("--radius-km", type=float, default=1.5)
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            result = sync_once(
                args.source_url.rstrip("/"),
                args.route_url.rstrip("/"),
                max(0.0, min(1.0, args.minimum_probability)),
                max(1, min(100, args.max_zones)),
                max(0.1, min(10.0, args.radius_km)),
            )
            print(json.dumps(result, indent=2))
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            print(f"Bridge cycle failed: {error}")
            if args.once:
                raise SystemExit(1) from error
        if args.once:
            break
        time.sleep(max(30, args.interval_seconds))


if __name__ == "__main__":
    main()
