"""Risk-aware A-star routing for the Option B research component.

The three canonical methods are directly comparable on the same road graph:

1. shortest_path    - travel time only.
2. objective_weight - CRITIC-weighted linear risk baseline.
3. objective_fuzzy  - proposed monotonic hierarchical fuzzy model.

All reported risk metrics use the proposed objective-fuzzy score so a route
comparison never changes its measurement scale between methods.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Iterable

import networkx as nx

try:  # Package import (API/tests)
    from .fuzzy_engine import (
        LAMBDA_RISK_AVERSION,
        evaluate_overall_risk,
        objective_linear_risk,
    )
except ImportError:  # Direct execution
    from fuzzy_engine import (
        LAMBDA_RISK_AVERSION,
        evaluate_overall_risk,
        objective_linear_risk,
    )


HAZARD_ATTRS = [
    "flood_probability",
    "landslide_probability",
    "elephant_risk",
    "buffalo_risk",
    "deer_risk",
    "wildboar_risk",
]

MAX_HEURISTIC_SPEED_KMH = 130.0
_TRAVEL_TIME_KEYS = ("travel_time_min", "travel_time", "length", "length_km")
FUZZY_CACHE_KEY = "_objective_fuzzy_risk_score"
LINEAR_CACHE_KEY = "_objective_linear_risk_score"

def canonical_method(method: str) -> str:
    return method


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _hazard_values(data: dict) -> list[float]:
    return [
        max(0.0, min(1.0, _as_float(data.get(attribute, 0.0))))
        for attribute in HAZARD_ATTRS
    ]


def _is_single_edge_data(data):
    return any(key in data for key in _TRAVEL_TIME_KEYS)


def _candidate_edges(data) -> Iterable[dict]:
    """Yield one or more attribute dictionaries for simple or multi-graphs."""

    if _is_single_edge_data(data):
        yield data
        return
    for candidate in data.values():
        if isinstance(candidate, dict):
            yield candidate


def get_travel_time(data):
    """Return edge travel time in minutes."""

    if "travel_time_min" in data:
        return max(0.0, _as_float(data["travel_time_min"]))
    if "travel_time" in data:
        return max(0.0, _as_float(data["travel_time"]) / 60.0)
    if "length" in data:  # OSM length is metres; assume 40 km/h.
        return max(0.0, (_as_float(data["length"]) / 1000.0) / 40.0 * 60.0)
    if "length_km" in data:
        return max(0.0, _as_float(data["length_km"]) / 40.0 * 60.0)
    raise KeyError("No travel-time or length attribute was found on this road edge.")


def get_edge_distance_km(data):
    """Return edge distance in kilometres when the graph provides it."""

    if "length_km" in data:
        return max(0.0, _as_float(data["length_km"]))
    if "length" in data:
        return max(0.0, _as_float(data["length"]) / 1000.0)
    return 0.0


def get_node_coordinates(graph, node):
    """Return latitude and longitude for either supported graph schema."""

    data = graph.nodes[node]
    if "y" in data and "x" in data:
        return _as_float(data["y"]), _as_float(data["x"])
    if "latitude" in data and "longitude" in data:
        return _as_float(data["latitude"]), _as_float(data["longitude"])
    raise KeyError(f"Node {node!r} has no latitude/longitude coordinates.")


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two WGS84 coordinates."""

    radius_km = 6371.0088
    lat1_r, lon1_r, lat2_r, lon2_r = map(
        math.radians, (lat1, lon1, lat2, lon2)
    )
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    value = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_r)
        * math.cos(lat2_r)
        * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * radius_km * math.asin(math.sqrt(value))


def edge_objective_fuzzy_risk(data):
    """Evaluate and memoize the proposed monotonic fuzzy risk."""

    if FUZZY_CACHE_KEY not in data:
        data[FUZZY_CACHE_KEY] = evaluate_overall_risk(
            *_hazard_values(data)
        )["overall_risk_score"]
    return _as_float(data[FUZZY_CACHE_KEY])


def edge_objective_linear_risk(data):
    """Evaluate and memoize the CRITIC-weighted linear baseline risk."""

    if LINEAR_CACHE_KEY not in data:
        data[LINEAR_CACHE_KEY] = objective_linear_risk(*_hazard_values(data))
    return _as_float(data[LINEAR_CACHE_KEY])


def invalidate_edge_risk_cache(data):
    """Remove derived values after a live hazard update."""

    data.pop(FUZZY_CACHE_KEY, None)
    data.pop(LINEAR_CACHE_KEY, None)


def precompute_objective_risks(graph):
    """Populate both edge-risk caches so the first API query is fast."""

    count = 0
    if graph.is_multigraph():
        edges = graph.edges(keys=True, data=True)
        for _source, _target, _key, data in edges:
            edge_objective_fuzzy_risk(data)
            edge_objective_linear_risk(data)
            count += 1
    else:
        for _source, _target, data in graph.edges(data=True):
            edge_objective_fuzzy_risk(data)
            edge_objective_linear_risk(data)
            count += 1
    return count


def _minimum_candidate_cost(data, evaluator: Callable[[dict], float]):
    costs = [evaluator(candidate) for candidate in _candidate_edges(data)]
    if not costs:
        raise KeyError("No usable edge attributes were found.")
    return min(costs)


def shortest_path_cost(_u, _v, data):
    """Method 1: minimize travel time and ignore hazards."""

    return _minimum_candidate_cost(data, get_travel_time)


def objective_weight_cost(_u, _v, data, lam=None):
    """Method 2: objective linear baseline without fuzzy non-compensation."""

    risk_aversion = LAMBDA_RISK_AVERSION if lam is None else max(0.0, float(lam))
    return _minimum_candidate_cost(
        data,
        lambda edge: get_travel_time(edge)
        * (1.0 + risk_aversion * edge_objective_linear_risk(edge)),
    )


def objective_fuzzy_cost(_u, _v, data, lam=None):
    """Method 3: proposed objective-weighted monotonic fuzzy model."""

    risk_aversion = LAMBDA_RISK_AVERSION if lam is None else max(0.0, float(lam))
    return _minimum_candidate_cost(
        data,
        lambda edge: get_travel_time(edge)
        * (1.0 + risk_aversion * edge_objective_fuzzy_risk(edge)),
    )


METHODS = {
    "shortest_path": shortest_path_cost,
    "objective_weight": objective_weight_cost,
    "objective_fuzzy": objective_fuzzy_cost,
}


def _weight_function(method, lam=None):
    method = canonical_method(method)
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}. Choose from: {list(METHODS)}")
    if method == "shortest_path":
        return shortest_path_cost
    return lambda u, v, data: METHODS[method](u, v, data, lam=lam)


def _heuristic_minutes(graph, source, target):
    """Admissible straight-line travel-time lower bound for A-star."""

    try:
        source_lat, source_lon = get_node_coordinates(graph, source)
        target_lat, target_lon = get_node_coordinates(graph, target)
    except KeyError:
        return 0.0
    distance = haversine_km(source_lat, source_lon, target_lat, target_lon)
    return distance / MAX_HEURISTIC_SPEED_KMH * 60.0


def select_edge_data(graph, source, target, method="objective_fuzzy", lam=None):
    """Select the parallel edge preferred by the requested cost function."""

    method = canonical_method(method)
    raw_data = graph.get_edge_data(source, target)
    if raw_data is None:
        raise KeyError(f"Route edge {source!r} -> {target!r} does not exist.")
    candidates = list(_candidate_edges(raw_data))
    if len(candidates) == 1:
        return candidates[0]
    weight = _weight_function(method, lam)
    return min(candidates, key=lambda data: weight(source, target, data))


def find_route(graph, source, target, method="objective_fuzzy", lam=None):
    """Find an A-star route and return comparable summary metrics."""

    method = canonical_method(method)
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}. Choose from: {list(METHODS)}")
    if source not in graph or target not in graph:
        raise nx.NodeNotFound("Source or destination node is not in the road network.")

    risk_aversion = LAMBDA_RISK_AVERSION if lam is None else max(0.0, float(lam))
    try:
        path = nx.astar_path(
            graph,
            source,
            target,
            heuristic=lambda u, v: _heuristic_minutes(graph, u, v),
            weight=_weight_function(method, risk_aversion),
        )
    except nx.NetworkXNoPath:
        return None

    total_time = 0.0
    total_distance = 0.0
    total_risk = 0.0
    time_weighted_risk = 0.0
    high_risk_segments = 0
    maximum_segment_risk = 0.0

    for source_node, target_node in zip(path[:-1], path[1:]):
        data = select_edge_data(
            graph, source_node, target_node, method=method, lam=risk_aversion
        )
        segment_time = get_travel_time(data)
        segment_risk = edge_objective_fuzzy_risk(data)
        total_time += segment_time
        total_distance += get_edge_distance_km(data)
        total_risk += segment_risk
        time_weighted_risk += segment_time * segment_risk
        maximum_segment_risk = max(maximum_segment_risk, segment_risk)
        if segment_risk >= 0.7:
            high_risk_segments += 1

    segment_count = max(0, len(path) - 1)
    normalized_risk = time_weighted_risk / total_time if total_time > 0 else 0.0
    return {
        "algorithm": "a_star",
        "method": method,
        "risk_aversion": round(risk_aversion, 3),
        "path": path,
        "num_segments": segment_count,
        "total_distance_km": round(total_distance, 3),
        "total_time_min": round(total_time, 2),
        "total_risk_score": round(total_risk, 3),
        "time_weighted_risk_exposure": round(time_weighted_risk, 4),
        "normalized_risk_score": round(normalized_risk, 4),
        "avg_risk_per_segment": round(total_risk / max(1, segment_count), 4),
        "maximum_segment_risk": round(maximum_segment_risk, 4),
        "high_risk_segments": high_risk_segments,
    }


def compare_methods(graph, source, target, lam=None):
    """Run all three canonical research methods for one origin-destination pair."""

    return {
        method: find_route(graph, source, target, method=method, lam=lam)
        for method in METHODS
    }


def load_network(path):
    """Load a GraphML road network."""

    graph = nx.read_graphml(Path(path))
    print(
        f"Loaded network: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges (from {path})"
    )
    return graph


if __name__ == "__main__":
    import random

    component_root = Path(__file__).resolve().parents[1]
    real_network = (
        component_root / "network" / "gampaha_road_network_with_hazards.graphml"
    )
    fallback_network = component_root / "network" / "synthetic_road_network.graphml"
    graph = load_network(real_network if real_network.exists() else fallback_network)

    random.seed(7)
    result = None
    for _ in range(30):
        source_node, target_node = random.sample(list(graph.nodes), 2)
        result = find_route(graph, source_node, target_node)
        if result:
            break
    if not result:
        raise SystemExit("No connected sample node pair was found.")

    for name, route in compare_methods(graph, source_node, target_node).items():
        if route:
            print(
                f"{name:<18} time={route['total_time_min']:>7.2f} min "
                f"risk={route['normalized_risk_score']:.4f} "
                f"segments={route['num_segments']}"
            )
