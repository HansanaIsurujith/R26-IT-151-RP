import os
from datetime import datetime, timezone

from fastapi.testclient import TestClient


os.environ["ROUTING_NETWORK_PATH"] = "network/synthetic_road_network.graphml"
os.environ["ROUTING_PRELOAD"] = "0"
os.environ["ROUTING_HAZARD_DB_PATH"] = ":memory:"

from api.main import Coordinate, NetworkRepository, app  # noqa: E402


SAMPLE_REQUEST = {
    "origin": {
        "latitude": 6.90,
        "longitude": 79.85,
        "label": "Test origin",
    },
    "destination": {
        "latitude": 7.10,
        "longitude": 80.10,
        "label": "Test destination",
    },
    "method": "objective_fuzzy",
    "risk_aversion": 8,
    "include_comparison": True,
}


def test_health_reports_loaded_route_component():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["component"] == "route-optimization"
    assert payload["algorithm"] == "a_star"
    assert payload["network"]["nodes"] == 228
    assert payload["network"]["source"] == "synthetic"


def test_optimize_endpoint_returns_geometry_risk_and_comparison():
    with TestClient(app) as client:
        response = client.post("/route/optimize", json=SAMPLE_REQUEST)

    assert response.status_code == 200
    payload = response.json()
    route = payload["route"]

    assert payload["status"] == "success"
    assert route["method"] == "objective_fuzzy"
    assert route["algorithm"] == "a_star"
    assert route["distance_km"] > 0
    assert route["duration_min"] > 0
    assert 0 <= route["risk_score"] <= 1
    assert len(route["coordinates"]) > 1
    assert len(route["segments"]) == route["segment_count"]
    assert len(route["risk_sections"]) >= 1
    assert {item["method"] for item in payload["comparison"]} == {
        "shortest_path",
        "objective_weight",
        "objective_fuzzy",
    }
    assert payload["model"]["weighting_method"] == "CRITIC"
    assert payload["model"]["human_responses_required"] is False
    assert payload["data_quality"]["grid_points"] == 228
    assert route["time_overhead_vs_fastest_pct"] <= 30.01
    assert route["detour_guardrail_pct"] == 30
    assert isinstance(route["same_as_fastest"], bool)
    assert all(isinstance(item["same_as_fastest"], bool) for item in payload["comparison"])
    assert "label" not in route["coordinates"][0]


def test_outside_gampaha_returns_clear_validation_error():
    request = {
        **SAMPLE_REQUEST,
        "origin": {"latitude": 6.05, "longitude": 80.80},
    }
    with TestClient(app) as client:
        response = client.post("/route/optimize", json=request)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "OUTSIDE_COVERAGE"


def test_same_snapped_road_node_is_rejected():
    request = {
        **SAMPLE_REQUEST,
        "destination": {"latitude": 6.900001, "longitude": 79.850001},
    }
    with TestClient(app) as client:
        response = client.post("/route/optimize", json=request)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SAME_ROAD_NODE"


def test_config_exposes_reproducible_objective_weighting():
    with TestClient(app) as client:
        response = client.get("/route/config")

    assert response.status_code == 200
    payload = response.json()
    objective = payload["objective_weighting"]
    assert objective["method"] == "CRITIC"
    assert objective["row_count"] == 228
    assert len(objective["dataset_sha256"]) == 64
    assert abs(sum(objective["weights"].values()) - 1.0) < 1e-9
    assert "ahp_weights" not in payload


def test_name_based_location_search_and_reverse_lookup():
    with TestClient(app) as client:
        search = client.get("/locations/search?q=Gamp&limit=5")
        reverse = client.get("/locations/reverse?latitude=7.0917&longitude=79.9942")

    assert search.status_code == 200
    assert search.json()[0]["label"] == "Gampaha"
    assert reverse.status_code == 200
    assert "Gampaha" in reverse.json()["label"]
    assert "latitude" in reverse.json()


def test_compare_endpoint_always_returns_all_methods():
    request = {**SAMPLE_REQUEST, "include_comparison": False}
    with TestClient(app) as client:
        response = client.post("/route/compare", json=request)

    assert response.status_code == 200
    assert len(response.json()["comparison"]) == 3


def test_live_hazard_update_changes_version_and_reports_source():
    request = {
        "coordinate": {"latitude": 7.0, "longitude": 79.95},
        "radius_km": 2.0,
        "hazards": {"flood": 0.91, "elephant": 0.44},
        "source": "integration_test",
    }
    with TestClient(app) as client:
        before = client.get("/hazards/status").json()["hazard_version"]
        response = client.post("/hazards/update", json=request)
        after = client.get("/hazards/status").json()

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated_edges"] > 0
    assert payload["hazard_version"] == before + 1
    assert after["last_update"]["source"] == "integration_test"
    assert after["persistence"] == "sqlite_replayed_on_startup"


def test_live_update_changes_route_risk_for_the_same_fastest_path():
    request = {
        **SAMPLE_REQUEST,
        "method": "shortest_path",
        "include_comparison": False,
    }
    with TestClient(app) as client:
        before = client.post("/route/optimize", json=request).json()
        midpoint = before["route"]["coordinates"][len(before["route"]["coordinates"]) // 2]
        update = client.post(
            "/hazards/update",
            json={
                "coordinate": midpoint,
                "radius_km": 3.0,
                "hazards": {"flood": 1.0, "landslide": 1.0},
                "source": "detector_integration_test",
            },
        )
        after = client.post("/route/optimize", json=request).json()

    assert update.status_code == 200
    assert after["network"]["hazard_version"] == before["network"]["hazard_version"] + 1
    assert after["route"]["risk_exposure"] != before["route"]["risk_exposure"]


def test_sqlite_hazard_update_is_replayed_after_repository_restart(tmp_path, monkeypatch):
    database = tmp_path / "hazards.sqlite3"
    monkeypatch.setenv("ROUTING_HAZARD_DB_PATH", str(database))
    first = NetworkRepository()
    first.load()
    first.update_hazards(
        Coordinate(latitude=7.0, longitude=79.95),
        2.0,
        {"flood": 0.93},
        "persistence_test",
        datetime.now(timezone.utc),
    )
    first._hazard_db.close()

    restarted = NetworkRepository()
    restarted.load()
    status = restarted.hazard_status()
    restarted._hazard_db.close()

    assert status["hazard_version"] == 2
    assert status["live_update_count"] == 1
    assert status["last_update"]["source"] == "persistence_test"


def test_research_evidence_has_zero_monotonicity_violations():
    with TestClient(app) as client:
        response = client.get("/research/evidence?samples=500")

    assert response.status_code == 200
    audit = response.json()["verified_properties"]["monotonicity"]
    assert audit["samples"] == 500
    assert audit["violations"] == 0
    assert audit["passed"] is True


def test_detour_guardrail_adjusts_an_excessive_safety_preference():
    request = {
        **SAMPLE_REQUEST,
        "risk_aversion": 25,
        "max_detour_pct": 5,
        "include_comparison": False,
    }
    with TestClient(app) as client:
        response = client.post("/route/optimize", json=request)

    assert response.status_code == 200
    route = response.json()["route"]
    assert route["time_overhead_vs_fastest_pct"] <= 5.01
    assert route["guardrail_applied"] is True
    assert route["effective_risk_aversion"] <= route["requested_risk_aversion"]
