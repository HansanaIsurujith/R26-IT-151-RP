from scripts.sync_flood_landslide_service import merge_zones


def test_bridge_merges_teammate_probabilities_by_grid_location():
    flood = {
        "zones": [
            {"lat": 7.1, "lng": 80.0, "probability": 0.81},
            {"lat": 7.2, "lng": 80.1, "probability": 0.20},
        ]
    }
    landslide = {
        "zones": [
            {"lat": 7.1, "lng": 80.0, "probability": 0.44},
            {"lat": 7.3, "lng": 80.2, "probability": 0.72},
        ]
    }

    merged = merge_zones(flood, landslide)
    shared = next(zone for zone in merged if zone["latitude"] == 7.1)

    assert shared["hazards"] == {"flood": 0.81, "landslide": 0.44}
    assert len(merged) == 3
