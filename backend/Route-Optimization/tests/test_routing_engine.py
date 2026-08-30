from pathlib import Path

import pytest

from core.routing_engine import METHODS, find_route, load_network


COMPONENT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_NETWORK = COMPONENT_ROOT / "network" / "synthetic_road_network.graphml"


@pytest.fixture(scope="module")
def graph():
    return load_network(SYNTHETIC_NETWORK)


def nearest_node(graph, latitude, longitude):
    return min(
        graph.nodes,
        key=lambda node: (
            float(graph.nodes[node]["latitude"]) - latitude
        )
        ** 2
        + (
            float(graph.nodes[node]["longitude"]) - longitude
        )
        ** 2,
    )


@pytest.mark.parametrize("method", list(METHODS))
def test_each_research_method_returns_a_valid_a_star_route(graph, method):
    source = nearest_node(graph, 6.90, 79.85)
    target = nearest_node(graph, 7.10, 80.10)

    result = find_route(graph, source, target, method=method, lam=8.0)

    assert result is not None
    assert result["algorithm"] == "a_star"
    assert result["method"] == method
    assert result["path"][0] == source
    assert result["path"][-1] == target
    assert result["num_segments"] == len(result["path"]) - 1
    assert result["total_time_min"] > 0
    assert result["total_distance_km"] > 0
    assert 0 <= result["normalized_risk_score"] <= 1


def test_safe_route_is_not_faster_than_the_time_optimal_baseline(graph):
    source = nearest_node(graph, 6.90, 79.85)
    target = nearest_node(graph, 7.10, 80.10)
    fastest = find_route(graph, source, target, method="shortest_path")
    adaptive = find_route(graph, source, target, method="objective_fuzzy", lam=8.0)

    assert fastest is not None
    assert adaptive is not None
    assert adaptive["total_time_min"] + 0.01 >= fastest["total_time_min"]
