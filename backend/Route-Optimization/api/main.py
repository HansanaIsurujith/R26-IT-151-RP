"""
Suraksha Lanka objective multi-hazard route-optimization API.

Run from backend/Route-Optimization:

    python -m uvicorn api.main:app --host 0.0.0.0 --port 8001

The service exposes the Option B CRITIC + monotonic fuzzy + A-star research
logic without modifying the Flood/Landslide or Wildlife components.
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import networkx as nx
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from core.fuzzy_engine import LAMBDA_RISK_AVERSION, monotonicity_audit
from core.objective_weighting import (
    OBJECTIVE_WEIGHT_RESULT,
    OBJECTIVE_WEIGHTS,
)
from core.routing_engine import (
    METHODS,
    edge_objective_fuzzy_risk,
    find_route,
    get_edge_distance_km,
    get_node_coordinates,
    get_travel_time,
    haversine_km,
    load_network,
    invalidate_edge_risk_cache,
    precompute_objective_risks,
    select_edge_data,
)


COMPONENT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(COMPONENT_ROOT / ".env")

REAL_NETWORK_PATH = (
    COMPONENT_ROOT / "network" / "gampaha_road_network_with_hazards.graphml"
)
SYNTHETIC_NETWORK_PATH = COMPONENT_ROOT / "network" / "synthetic_road_network.graphml"

RouteMethod = Literal["shortest_path", "objective_weight", "objective_fuzzy"]
RiskLevel = Literal["low", "moderate", "high", "critical"]

METHOD_LABELS = {
    "shortest_path": "Fastest Route",
    "objective_weight": "Objective Linear Baseline",
    "objective_fuzzy": "Risk-Aware Route",
}

HAZARD_RESPONSE_KEYS = {
    "flood_probability": "flood",
    "landslide_probability": "landslide",
    "elephant_risk": "elephant",
    "buffalo_risk": "buffalo",
    "deer_risk": "deer",
    "wildboar_risk": "wildboar",
}

SUGGESTED_LOCATIONS = [
    {"label": "Gampaha", "latitude": 7.0917, "longitude": 79.9942},
    {"label": "Nittambuwa", "latitude": 7.1447, "longitude": 80.0960},
    {"label": "Kadawatha", "latitude": 7.0013, "longitude": 79.9507},
    {"label": "Minuwangoda", "latitude": 7.1663, "longitude": 79.9533},
    {"label": "Kirindiwela", "latitude": 7.0425, "longitude": 80.1277},
    {"label": "Negombo", "latitude": 7.2083, "longitude": 79.8358},
    {"label": "Ja-Ela", "latitude": 7.0744, "longitude": 79.8919},
    {"label": "Wattala", "latitude": 6.9892, "longitude": 79.8917},
    {"label": "Kelaniya", "latitude": 6.9567, "longitude": 79.9210},
    {"label": "Ragama", "latitude": 7.0301, "longitude": 79.9167},
    {"label": "Ganemulla", "latitude": 7.0642, "longitude": 79.9630},
    {"label": "Veyangoda", "latitude": 7.1568, "longitude": 80.0955},
    {"label": "Mirigama", "latitude": 7.2410, "longitude": 80.1260},
    {"label": "Divulapitiya", "latitude": 7.2240, "longitude": 80.0150},
    {"label": "Katunayake", "latitude": 7.1699, "longitude": 79.8884},
    {"label": "Biyagama", "latitude": 6.9497, "longitude": 79.9845},
]

HAZARD_GRID_PATH = COMPONENT_ROOT / "data" / "combined_hazard_grid.csv"


def _hazard_grid_metadata():
    latitudes = []
    longitudes = []
    with HAZARD_GRID_PATH.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            latitudes.append(float(row["latitude"]))
            longitudes.append(float(row["longitude"]))
    return {
        "bounds": {
            "south": min(latitudes),
            "north": max(latitudes),
            "west": min(longitudes),
            "east": max(longitudes),
        },
        "points": len(latitudes),
        "nominal_resolution_km": 2.5,
    }


HAZARD_GRID_METADATA = _hazard_grid_metadata()


class MapCoordinate(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class Coordinate(MapCoordinate):
    label: str | None = Field(default=None, max_length=100)


class RouteOptimizeRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    method: RouteMethod = "objective_fuzzy"
    risk_aversion: float = Field(
        default=LAMBDA_RISK_AVERSION,
        ge=0.0,
        le=25.0,
        description="Lambda in C(e) = T(e) * [1 + lambda * Risk(e)].",
    )
    include_comparison: bool = True
    max_detour_pct: float = Field(
        default=30.0,
        ge=0.0,
        le=100.0,
        description="Maximum allowed travel-time overhead versus the fastest route.",
    )


class SnappedPoint(Coordinate):
    node_id: str
    road_distance_m: float


class HazardScores(BaseModel):
    flood: float
    landslide: float
    elephant: float
    buffalo: float
    deer: float
    wildboar: float


class RouteSegment(BaseModel):
    sequence: int
    road_name: str
    distance_km: float
    duration_min: float
    risk_score: float
    risk_level: RiskLevel
    hazards: HazardScores
    start_coordinate_index: int
    end_coordinate_index: int


class RiskSection(BaseModel):
    risk_level: RiskLevel
    risk_score: float
    coordinates: list[MapCoordinate]


class RouteDetails(BaseModel):
    algorithm: str
    method: RouteMethod
    method_label: str
    distance_km: float
    duration_min: float
    risk_score: float
    risk_level: RiskLevel
    risk_exposure: float
    maximum_segment_risk: float
    requested_risk_aversion: float
    effective_risk_aversion: float
    detour_guardrail_pct: float
    guardrail_applied: bool
    same_as_fastest: bool
    high_risk_segments: int
    segment_count: int
    risk_reduction_vs_fastest_pct: float
    time_overhead_vs_fastest_pct: float
    hazard_summary: HazardScores
    coordinates: list[MapCoordinate]
    risk_sections: list[RiskSection]
    segments: list[RouteSegment]


class MethodComparison(BaseModel):
    method: RouteMethod
    method_label: str
    duration_min: float
    distance_km: float
    risk_score: float
    risk_exposure: float
    risk_level: RiskLevel
    high_risk_segments: int
    risk_reduction_vs_fastest_pct: float
    time_overhead_vs_fastest_pct: float
    same_as_fastest: bool


class LocationSuggestion(Coordinate):
    secondary_label: str
    source: Literal["catalog", "road", "reverse"]


class NetworkInfo(BaseModel):
    name: str
    coverage: str
    nodes: int
    edges: int
    source: Literal["real", "synthetic", "custom"]
    risk_cache_precomputed: bool
    hazard_version: int
    live_update_count: int


class DataQuality(BaseModel):
    level: Literal["high", "moderate", "limited"]
    route_coverage_pct: float
    grid_points: int
    nominal_resolution_km: float
    message: str
    limitations: list[str]


class ModelEvidence(BaseModel):
    model_name: str
    weighting_method: str
    objective_weights: dict[str, float]
    dataset_rows: int
    dataset_sha256: str
    monotonic_by_design: bool
    human_responses_required: bool


class RouteOptimizeResponse(BaseModel):
    route_id: str
    status: Literal["success"]
    computed_at: str
    processing_time_ms: float
    origin: SnappedPoint
    destination: SnappedPoint
    network: NetworkInfo
    data_quality: DataQuality
    model: ModelEvidence
    route: RouteDetails
    comparison: list[MethodComparison]
    recommendation: str


class HazardUpdateValues(BaseModel):
    flood: float | None = Field(default=None, ge=0.0, le=1.0)
    landslide: float | None = Field(default=None, ge=0.0, le=1.0)
    elephant: float | None = Field(default=None, ge=0.0, le=1.0)
    buffalo: float | None = Field(default=None, ge=0.0, le=1.0)
    deer: float | None = Field(default=None, ge=0.0, le=1.0)
    wildboar: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_one_hazard(self):
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("Provide at least one hazard value to update.")
        return self


class HazardUpdateRequest(BaseModel):
    coordinate: Coordinate
    radius_km: float = Field(default=1.0, ge=0.1, le=10.0)
    hazards: HazardUpdateValues
    source: str = Field(default="external_hazard_service", min_length=2, max_length=100)
    observed_at: datetime | None = None


class HazardUpdateResponse(BaseModel):
    status: Literal["updated"]
    hazard_version: int
    updated_edges: int
    radius_km: float
    source: str
    observed_at: str
    values: dict[str, float]


class NetworkRepository:
    """Load the GraphML once and provide fast coordinate-to-node snapping."""

    def __init__(self):
        self._lock = threading.Lock()
        self.graph: nx.Graph | None = None
        self.path: Path | None = None
        self.node_ids: np.ndarray | None = None
        self.latitudes: np.ndarray | None = None
        self.longitudes: np.ndarray | None = None
        self.edge_latitudes: np.ndarray | None = None
        self.edge_longitudes: np.ndarray | None = None
        self.edge_data: list[dict] = []
        self.bounds: dict[str, float] | None = None
        self.risk_cache_precomputed = False
        self.hazard_version = 1
        self.live_update_count = 0
        self.last_hazard_update: dict | None = None
        self.location_index: list[dict] = []
        self._hazard_db: sqlite3.Connection | None = None

    @staticmethod
    def _configured_path():
        configured = os.getenv("ROUTING_NETWORK_PATH")
        if configured:
            candidate = Path(configured).expanduser()
            if not candidate.is_absolute():
                candidate = COMPONENT_ROOT / candidate
            return candidate.resolve()
        if REAL_NETWORK_PATH.exists():
            return REAL_NETWORK_PATH
        return SYNTHETIC_NETWORK_PATH

    def load(self):
        if self.graph is not None:
            return self.graph

        with self._lock:
            if self.graph is not None:
                return self.graph

            path = self._configured_path()
            if not path.exists():
                raise FileNotFoundError(f"Road network was not found: {path}")

            graph = load_network(path)
            if os.getenv("ROUTING_PRECOMPUTE_RISK", "1").lower() not in {
                "0",
                "false",
                "no",
            }:
                started = time.perf_counter()
                edge_count = precompute_objective_risks(graph)
                self.risk_cache_precomputed = True
                print(
                    f"Prepared objective risk cache for {edge_count} edges "
                    f"in {time.perf_counter() - started:.2f}s"
                )
            node_ids = []
            latitudes = []
            longitudes = []
            for node_id in graph.nodes:
                latitude, longitude = get_node_coordinates(graph, node_id)
                node_ids.append(node_id)
                latitudes.append(latitude)
                longitudes.append(longitude)

            self.graph = graph
            self.path = path
            self.node_ids = np.asarray(node_ids, dtype=object)
            self.latitudes = np.asarray(latitudes, dtype=float)
            self.longitudes = np.asarray(longitudes, dtype=float)
            edge_latitudes = []
            edge_longitudes = []
            edge_data = []
            for source, target, data in graph.edges(data=True):
                source_lat, source_lon = get_node_coordinates(graph, source)
                target_lat, target_lon = get_node_coordinates(graph, target)
                edge_latitudes.append((source_lat + target_lat) / 2.0)
                edge_longitudes.append((source_lon + target_lon) / 2.0)
                edge_data.append(data)
            self.edge_latitudes = np.asarray(edge_latitudes, dtype=float)
            self.edge_longitudes = np.asarray(edge_longitudes, dtype=float)
            self.edge_data = edge_data
            self.bounds = {
                "south": float(self.latitudes.min()),
                "north": float(self.latitudes.max()),
                "west": float(self.longitudes.min()),
                "east": float(self.longitudes.max()),
            }
            self._build_location_index(graph)
            self._initialize_hazard_store()
            self._replay_persisted_updates()
            return graph

    @staticmethod
    def _clean_road_name(value):
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value or "").strip()
        if text.startswith("[") and text.endswith("]"):
            text = text.strip("[]").split(",")[0].strip(" '\"")
        return text

    def _build_location_index(self, graph):
        """Create an offline place/road-name index from the bundled OSM graph."""

        locations = [
            {
                **place,
                "secondary_label": "Town in Gampaha District",
                "source": "catalog",
            }
            for place in SUGGESTED_LOCATIONS
        ]
        seen = {place["label"].casefold() for place in locations}
        for source, target, data in graph.edges(data=True):
            name = self._clean_road_name(data.get("name") or data.get("ref"))
            key = name.casefold()
            if len(name) < 3 or key in seen:
                continue
            source_lat, source_lon = get_node_coordinates(graph, source)
            target_lat, target_lon = get_node_coordinates(graph, target)
            locations.append(
                {
                    "label": name,
                    "secondary_label": "Road in the Gampaha network",
                    "latitude": round((source_lat + target_lat) / 2.0, 7),
                    "longitude": round((source_lon + target_lon) / 2.0, 7),
                    "source": "road",
                }
            )
            seen.add(key)
            if len(locations) >= 2_500:
                break
        self.location_index = locations

    def search_locations(self, query: str, limit: int):
        self.load()
        normalized = query.casefold().strip()
        if not normalized:
            return self.location_index[:limit]

        def rank(item):
            name = item["label"].casefold()
            if name == normalized:
                return (0, len(name))
            if name.startswith(normalized):
                return (1, len(name))
            return (2, name.find(normalized), len(name))

        matches = [
            item for item in self.location_index if normalized in item["label"].casefold()
        ]
        return sorted(matches, key=rank)[:limit]

    def reverse_location(self, coordinate: Coordinate):
        self.load()
        nearby = []
        for item in self.location_index:
            distance = haversine_km(
                coordinate.latitude,
                coordinate.longitude,
                item["latitude"],
                item["longitude"],
            )
            nearby.append((distance, item))
        distance, item = min(nearby, key=lambda candidate: candidate[0])
        label = item["label"] if distance < 0.25 else f"Near {item['label']}"
        return {
            "label": label,
            "secondary_label": f"{distance:.1f} km from matched map name",
            "latitude": coordinate.latitude,
            "longitude": coordinate.longitude,
            "source": "reverse",
        }

    def _initialize_hazard_store(self):
        configured = os.getenv(
            "ROUTING_HAZARD_DB_PATH", str(COMPONENT_ROOT / "data" / "live_hazards.sqlite3")
        )
        if configured != ":memory:":
            db_path = Path(configured).expanduser()
            if not db_path.is_absolute():
                db_path = COMPONENT_ROOT / db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)
            configured = str(db_path)
        self._hazard_db = sqlite3.connect(configured, check_same_thread=False)
        self._hazard_db.execute(
            """CREATE TABLE IF NOT EXISTS hazard_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                radius_km REAL NOT NULL,
                values_json TEXT NOT NULL,
                source TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                received_at TEXT NOT NULL
            )"""
        )
        self._hazard_db.commit()

    def _edge_indices_in_radius(self, coordinate, radius_km):
        latitude_scale = 111.32
        longitude_scale = latitude_scale * np.cos(np.radians(coordinate.latitude))
        delta_lat = (self.edge_latitudes - coordinate.latitude) * latitude_scale
        delta_lon = (self.edge_longitudes - coordinate.longitude) * longitude_scale
        return np.flatnonzero(delta_lat * delta_lat + delta_lon * delta_lon <= radius_km**2)

    def _apply_values_to_indices(self, indices, values):
        attribute_map = {short: attribute for attribute, short in HAZARD_RESPONSE_KEYS.items()}
        for index in indices:
            edge = self.edge_data[int(index)]
            for name, value in values.items():
                edge[attribute_map[name]] = float(value)
            invalidate_edge_risk_cache(edge)

    def _replay_persisted_updates(self):
        rows = self._hazard_db.execute(
            "SELECT latitude, longitude, radius_km, values_json, source, observed_at, "
            "received_at FROM hazard_updates ORDER BY id"
        ).fetchall()
        for latitude, longitude, radius, values_json, source, observed_at, received_at in rows:
            coordinate = Coordinate(latitude=latitude, longitude=longitude)
            indices = self._edge_indices_in_radius(coordinate, radius)
            values = json.loads(values_json)
            self._apply_values_to_indices(indices, values)
            self.hazard_version += 1
            self.live_update_count += 1
            self.last_hazard_update = {
                "source": source,
                "observed_at": observed_at,
                "received_at": received_at,
                "coordinate": coordinate.model_dump(),
                "radius_km": radius,
                "updated_edges": int(len(indices)),
                "values": values,
                "hazard_version": self.hazard_version,
            }

    def nearest_node(self, coordinate: Coordinate):
        self.load()
        latitude_scale = 111.32
        longitude_scale = latitude_scale * np.cos(np.radians(coordinate.latitude))
        delta_lat = (self.latitudes - coordinate.latitude) * latitude_scale
        delta_lon = (self.longitudes - coordinate.longitude) * longitude_scale
        index = int(np.argmin(delta_lat * delta_lat + delta_lon * delta_lon))
        node_id = self.node_ids[index]
        snapped_latitude = float(self.latitudes[index])
        snapped_longitude = float(self.longitudes[index])
        distance_km = haversine_km(
            coordinate.latitude,
            coordinate.longitude,
            snapped_latitude,
            snapped_longitude,
        )
        return node_id, snapped_latitude, snapped_longitude, distance_km

    def update_hazards(
        self,
        coordinate: Coordinate,
        radius_km: float,
        values: dict[str, float],
        source: str,
        observed_at: datetime,
    ):
        """Apply an in-memory spatial update from another detection component."""

        self.load()
        indices = self._edge_indices_in_radius(coordinate, radius_km)
        if len(indices) == 0:
            latitude_scale = 111.32
            longitude_scale = latitude_scale * np.cos(np.radians(coordinate.latitude))
            distances_squared = (
                (self.edge_latitudes - coordinate.latitude) * latitude_scale
            ) ** 2 + ((self.edge_longitudes - coordinate.longitude) * longitude_scale) ** 2
            nearest_distance = float(np.sqrt(distances_squared.min()))
            raise ValueError(
                f"No road edges are within {radius_km:.1f} km; "
                f"the nearest edge is {nearest_distance:.2f} km away."
            )

        received_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._hazard_db.execute(
                "INSERT INTO hazard_updates (latitude, longitude, radius_km, values_json, "
                "source, observed_at, received_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    coordinate.latitude,
                    coordinate.longitude,
                    radius_km,
                    json.dumps(values, sort_keys=True),
                    source,
                    observed_at.astimezone(timezone.utc).isoformat(),
                    received_at,
                ),
            )
            self._hazard_db.commit()
            self._apply_values_to_indices(indices, values)
            self.hazard_version += 1
            self.live_update_count += 1
            self.last_hazard_update = {
                "source": source,
                "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
                "received_at": received_at,
                "coordinate": coordinate.model_dump(),
                "radius_km": radius_km,
                "updated_edges": int(len(indices)),
                "values": values,
                "hazard_version": self.hazard_version,
            }
        return self.last_hazard_update

    def hazard_status(self):
        self.load()
        return {
            "hazard_version": self.hazard_version,
            "live_update_count": self.live_update_count,
            "last_update": self.last_hazard_update,
            "persistence": "sqlite_replayed_on_startup",
            "accepted_hazards": list(HAZARD_RESPONSE_KEYS.values()),
        }

    def info(self):
        graph = self.load()
        if self.path == REAL_NETWORK_PATH:
            source = "real"
            name = "Gampaha OSM Road Network with Multi-Hazard Data"
        elif self.path == SYNTHETIC_NETWORK_PATH:
            source = "synthetic"
            name = "Synthetic Gampaha Fallback Network"
        else:
            source = "custom"
            name = self.path.name
        return NetworkInfo(
            name=name,
            coverage="Gampaha District, Sri Lanka",
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
            source=source,
            risk_cache_precomputed=self.risk_cache_precomputed,
            hazard_version=self.hazard_version,
            live_update_count=self.live_update_count,
        )


network_repository = NetworkRepository()


def classify_risk(score: float) -> RiskLevel:
    if score < 0.25:
        return "low"
    if score < 0.50:
        return "moderate"
    if score < 0.70:
        return "high"
    return "critical"


def _node_coordinate(graph, node_id):
    latitude, longitude = get_node_coordinates(graph, node_id)
    return {"latitude": latitude, "longitude": longitude}


_WKT_COORDINATE = re.compile(
    r"(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+"
    r"(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
)


def _edge_coordinates(graph, source, target, edge_data):
    start = _node_coordinate(graph, source)
    end = _node_coordinate(graph, target)
    geometry = edge_data.get("geometry")
    coordinates = []

    if isinstance(geometry, str):
        for longitude, latitude in _WKT_COORDINATE.findall(geometry):
            coordinates.append(
                {"latitude": float(latitude), "longitude": float(longitude)}
            )

    if len(coordinates) < 2:
        return [start, end]

    distance_from_first = haversine_km(
        start["latitude"],
        start["longitude"],
        coordinates[0]["latitude"],
        coordinates[0]["longitude"],
    )
    distance_from_last = haversine_km(
        start["latitude"],
        start["longitude"],
        coordinates[-1]["latitude"],
        coordinates[-1]["longitude"],
    )
    if distance_from_last < distance_from_first:
        coordinates.reverse()

    coordinates[0] = start
    coordinates[-1] = end
    return coordinates


def _same_coordinate(first, second):
    return (
        abs(first["latitude"] - second["latitude"]) < 1e-8
        and abs(first["longitude"] - second["longitude"]) < 1e-8
    )


def _hazards_for_edge(edge_data):
    return {
        output_key: round(float(edge_data.get(attribute, 0.0)), 4)
        for attribute, output_key in HAZARD_RESPONSE_KEYS.items()
    }


def _route_geometry_and_risk(graph, result):
    route_coordinates = []
    segments = []
    sections = []
    hazard_weighted = {key: 0.0 for key in HAZARD_RESPONSE_KEYS.values()}
    total_time = 0.0
    current_section = None

    for sequence, (source, target) in enumerate(
        zip(result["path"][:-1], result["path"][1:]), start=1
    ):
        edge_data = select_edge_data(
            graph,
            source,
            target,
            method=result["method"],
            lam=result["risk_aversion"],
        )
        edge_coordinates = _edge_coordinates(graph, source, target, edge_data)
        if not route_coordinates:
            route_coordinates.extend(edge_coordinates)
            start_index = 0
        else:
            start_index = len(route_coordinates) - 1
            points_to_add = edge_coordinates
            if _same_coordinate(route_coordinates[-1], edge_coordinates[0]):
                points_to_add = edge_coordinates[1:]
            route_coordinates.extend(points_to_add)
        end_index = len(route_coordinates) - 1

        duration = get_travel_time(edge_data)
        risk_score = edge_objective_fuzzy_risk(edge_data)
        risk_level = classify_risk(risk_score)
        hazards = _hazards_for_edge(edge_data)
        total_time += duration
        for name, value in hazards.items():
            hazard_weighted[name] += duration * value

        road_name = edge_data.get("name") or edge_data.get("ref") or "Unnamed road"
        segments.append(
            {
                "sequence": sequence,
                "road_name": str(road_name),
                "distance_km": round(get_edge_distance_km(edge_data), 3),
                "duration_min": round(duration, 3),
                "risk_score": round(risk_score, 4),
                "risk_level": risk_level,
                "hazards": hazards,
                "start_coordinate_index": start_index,
                "end_coordinate_index": end_index,
            }
        )

        if current_section is None or current_section["risk_level"] != risk_level:
            if current_section is not None:
                sections.append(current_section)
            current_section = {
                "risk_level": risk_level,
                "coordinates": list(edge_coordinates),
                "weighted_risk": duration * risk_score,
                "duration": duration,
            }
        else:
            points_to_add = edge_coordinates
            if _same_coordinate(current_section["coordinates"][-1], edge_coordinates[0]):
                points_to_add = edge_coordinates[1:]
            current_section["coordinates"].extend(points_to_add)
            current_section["weighted_risk"] += duration * risk_score
            current_section["duration"] += duration

    if current_section is not None:
        sections.append(current_section)

    risk_sections = [
        {
            "risk_level": section["risk_level"],
            "risk_score": round(
                section["weighted_risk"] / max(section["duration"], 1e-9), 4
            ),
            "coordinates": section["coordinates"],
        }
        for section in sections
    ]
    hazard_summary = {
        key: round(value / max(total_time, 1e-9), 4)
        for key, value in hazard_weighted.items()
    }
    return route_coordinates, segments, risk_sections, hazard_summary


def _comparison_item(result, fastest_result):
    risk_reduction = -_percentage_change(
        result["time_weighted_risk_exposure"],
        fastest_result["time_weighted_risk_exposure"],
    )
    time_overhead = _percentage_change(
        result["total_time_min"], fastest_result["total_time_min"]
    )
    return MethodComparison(
        method=result["method"],
        method_label=METHOD_LABELS[result["method"]],
        duration_min=result["total_time_min"],
        distance_km=result["total_distance_km"],
        risk_score=result["normalized_risk_score"],
        risk_exposure=result["time_weighted_risk_exposure"],
        risk_level=classify_risk(result["normalized_risk_score"]),
        high_risk_segments=result["high_risk_segments"],
        risk_reduction_vs_fastest_pct=round(risk_reduction, 2),
        time_overhead_vs_fastest_pct=round(time_overhead, 2),
        same_as_fastest=result["path"] == fastest_result["path"],
    )


def _percentage_change(value, baseline):
    if baseline <= 0:
        return 0.0
    return (value - baseline) / baseline * 100.0


def _apply_detour_guardrail(
    graph,
    origin_node,
    destination_node,
    method,
    requested_lambda,
    max_detour_pct,
    fastest_result,
    selected_result,
):
    """Choose the lowest-exposure tested route inside the detour constraint.

    If the requested lambda already satisfies the guardrail it is returned
    unchanged. Otherwise seven deterministic lambda levels from zero to the
    request are evaluated. This is a transparent Lagrangian sensitivity search,
    not a claim that every possible constrained path has been enumerated.
    """

    if method == "shortest_path":
        return fastest_result, False
    requested_overhead = _percentage_change(
        selected_result["total_time_min"], fastest_result["total_time_min"]
    )
    if requested_overhead <= max_detour_pct + 1e-9:
        return selected_result, False

    candidates = [selected_result]
    tested_lambdas = {round(float(requested_lambda), 8)}
    for step in range(7):
        candidate_lambda = float(requested_lambda) * step / 6.0
        key = round(candidate_lambda, 8)
        if key in tested_lambdas:
            continue
        tested_lambdas.add(key)
        candidate = find_route(
            graph,
            origin_node,
            destination_node,
            method=method,
            lam=candidate_lambda,
        )
        if candidate is not None:
            candidates.append(candidate)

    feasible = [
        candidate
        for candidate in candidates
        if _percentage_change(
            candidate["total_time_min"], fastest_result["total_time_min"]
        )
        <= max_detour_pct + 1e-9
    ]
    if not feasible:
        return fastest_result, True
    best = min(
        feasible,
        key=lambda candidate: (
            candidate["time_weighted_risk_exposure"],
            candidate["total_time_min"],
        ),
    )
    return best, True


def _recommendation(method, risk_reduction, time_overhead, same_as_fastest=False):
    if method == "objective_fuzzy":
        if same_as_fastest:
            return (
                "Risk-Aware and Fastest use the same road path for this journey. "
                "No distinct route with lower measured exposure was selected within "
                "the travel-time guardrail; this is one shared route, not two alternatives."
            )
        if risk_reduction > 0.05:
            return (
                f"Risk-Aware routing reduces time-weighted hazard exposure by "
                f"{risk_reduction:.1f}% with {max(0.0, time_overhead):.1f}% "
                "additional travel time versus the fastest route."
            )
        return (
            "Risk-Aware routing is selected. For this journey it stays close to "
            "the fastest route because the network offers no materially safer detour."
        )
    if method == "objective_weight":
        return (
            "This is the CRITIC-weighted linear baseline. Use Risk-Aware to apply "
            "the proposed non-compensatory monotonic fuzzy decision model."
        )
    return (
        "This is the fastest route. Hazard scores are displayed, but they are not "
        "used to choose the path."
    )


def _model_evidence():
    return ModelEvidence(
        model_name="Objective-Weighted Monotonic Hierarchical Fuzzy Model",
        weighting_method=OBJECTIVE_WEIGHT_RESULT.method,
        objective_weights={
            name: round(value, 8) for name, value in OBJECTIVE_WEIGHTS.items()
        },
        dataset_rows=OBJECTIVE_WEIGHT_RESULT.row_count,
        dataset_sha256=OBJECTIVE_WEIGHT_RESULT.dataset_sha256,
        monotonic_by_design=True,
        human_responses_required=False,
    )


def _route_data_quality(graph, result):
    bounds = HAZARD_GRID_METADATA["bounds"]
    # Half a grid cell is included because an edge is assigned its nearest cell.
    margin_degrees = 0.013
    inside = 0
    for node_id in result["path"]:
        latitude, longitude = get_node_coordinates(graph, node_id)
        if (
            bounds["south"] - margin_degrees
            <= latitude
            <= bounds["north"] + margin_degrees
            and bounds["west"] - margin_degrees
            <= longitude
            <= bounds["east"] + margin_degrees
        ):
            inside += 1
    coverage_pct = inside / max(1, len(result["path"])) * 100.0
    if coverage_pct >= 90.0:
        level = "high"
        message = "Most of this route is within the measured hazard-grid extent."
    elif coverage_pct >= 60.0:
        level = "moderate"
        message = "Part of this route extends beyond the core hazard-grid extent."
    else:
        level = "limited"
        message = "Hazard evidence is spatially limited for much of this route."
    return DataQuality(
        level=level,
        route_coverage_pct=round(coverage_pct, 1),
        grid_points=HAZARD_GRID_METADATA["points"],
        nominal_resolution_km=HAZARD_GRID_METADATA["nominal_resolution_km"],
        message=message,
        limitations=[
            "Static values use nearest-grid-cell assignment at about 2.5 km spacing.",
            "Live updates are persisted locally and replayed after an API restart.",
            "Risk is decision support, not a guarantee that a road is safe.",
        ],
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("ROUTING_PRELOAD", "1").lower() not in {"0", "false", "no"}:
        await asyncio.to_thread(network_repository.load)
    yield


app = FastAPI(
    title="Suraksha Lanka Route Optimization API",
    description=(
        "Risk-aware Gampaha routing using A-star, CRITIC objective weighting, "
        "and a monotonic hierarchical fuzzy decision model."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "component": "route-optimization",
        "message": "Suraksha Lanka route API is running.",
        "docs": "/docs",
        "optimize_endpoint": "/route/optimize",
        "compare_endpoint": "/route/compare",
        "hazard_update_endpoint": "/hazards/update",
        "location_search_endpoint": "/locations/search",
    }


@app.get("/health")
def health():
    try:
        network = network_repository.info()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Road network failed to load: {exc}") from exc
    return {
        "status": "ok",
        "component": "route-optimization",
        "algorithm": "a_star",
        "decision_model": "objective_weighted_monotonic_hierarchical_fuzzy",
        "weighting_method": OBJECTIVE_WEIGHT_RESULT.method,
        "methods": list(METHODS),
        "default_method": "objective_fuzzy",
        "default_risk_aversion": LAMBDA_RISK_AVERSION,
        "network": network.model_dump(),
    }


@app.get("/route/config")
def route_config():
    network = network_repository.info()
    return {
        "coverage": network.coverage,
        "bounds": network_repository.bounds,
        "center": {"latitude": 7.08, "longitude": 80.01},
        "methods": METHOD_LABELS,
        "default_method": "objective_fuzzy",
        "default_risk_aversion": LAMBDA_RISK_AVERSION,
        "objective_weighting": OBJECTIVE_WEIGHT_RESULT.as_dict(),
        "model": _model_evidence().model_dump(),
        "hazard_grid": HAZARD_GRID_METADATA,
        "hazard_status": network_repository.hazard_status(),
        "suggested_locations": SUGGESTED_LOCATIONS,
    }


@app.get("/locations/search", response_model=list[LocationSuggestion])
def location_search(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
):
    """Search the bundled Gampaha town and OSM road-name index."""

    return [LocationSuggestion(**item) for item in network_repository.search_locations(q, limit)]


@app.get("/locations/reverse", response_model=LocationSuggestion)
def location_reverse(
    latitude: float = Query(ge=-90.0, le=90.0),
    longitude: float = Query(ge=-180.0, le=180.0),
):
    """Give a human-readable nearby name to a map-selected coordinate."""

    return LocationSuggestion(
        **network_repository.reverse_location(
            Coordinate(latitude=latitude, longitude=longitude)
        )
    )


@app.post("/route/optimize", response_model=RouteOptimizeResponse)
def optimize_route(request: RouteOptimizeRequest):
    started = time.perf_counter()
    try:
        graph = network_repository.load()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Road network failed to load: {exc}") from exc

    origin_node, origin_lat, origin_lon, origin_distance = network_repository.nearest_node(
        request.origin
    )
    destination_node, destination_lat, destination_lon, destination_distance = (
        network_repository.nearest_node(request.destination)
    )

    max_snap_distance_km = float(os.getenv("ROUTING_MAX_SNAP_DISTANCE_KM", "15"))
    farthest_distance = max(origin_distance, destination_distance)
    if farthest_distance > max_snap_distance_km:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OUTSIDE_COVERAGE",
                "message": (
                    "The selected point is outside the current Gampaha road-network "
                    "coverage. Choose both points inside the displayed Gampaha map."
                ),
                "coverage": "Gampaha District, Sri Lanka",
                "nearest_road_distance_km": round(farthest_distance, 2),
            },
        )
    if origin_node == destination_node:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SAME_ROAD_NODE",
                "message": "Origin and destination are too close. Select two different points.",
            },
        )

    fastest_result = find_route(
        graph,
        origin_node,
        destination_node,
        method="shortest_path",
        lam=0.0,
    )
    if fastest_result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NO_ROUTE",
                "message": "No drivable route was found between the selected points.",
            },
        )

    if request.method == "shortest_path":
        selected_result = fastest_result
        guardrail_applied = False
    else:
        requested_result = find_route(
            graph,
            origin_node,
            destination_node,
            method=request.method,
            lam=request.risk_aversion,
        )
        if requested_result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NO_ROUTE",
                    "message": "No drivable route was found between the selected points.",
                },
            )
        selected_result, guardrail_applied = _apply_detour_guardrail(
            graph,
            origin_node,
            destination_node,
            request.method,
            request.risk_aversion,
            request.max_detour_pct,
            fastest_result,
            requested_result,
        )

    results = {"shortest_path": fastest_result, request.method: selected_result}
    if request.include_comparison:
        comparison_lambda = selected_result["risk_aversion"]
        for method in METHODS:
            if method not in results:
                result = find_route(
                    graph,
                    origin_node,
                    destination_node,
                    method=method,
                    lam=comparison_lambda,
                )
                if result is not None:
                    results[method] = result

    risk_reduction = -_percentage_change(
        selected_result["time_weighted_risk_exposure"],
        fastest_result["time_weighted_risk_exposure"],
    )
    time_overhead = _percentage_change(
        selected_result["total_time_min"],
        fastest_result["total_time_min"],
    )

    coordinates, segments, risk_sections, hazard_summary = _route_geometry_and_risk(
        graph, selected_result
    )
    selected_risk = selected_result["normalized_risk_score"]
    same_as_fastest = selected_result["path"] == fastest_result["path"]

    origin = SnappedPoint(
        latitude=origin_lat,
        longitude=origin_lon,
        label=request.origin.label,
        node_id=str(origin_node),
        road_distance_m=round(origin_distance * 1000.0, 1),
    )
    destination = SnappedPoint(
        latitude=destination_lat,
        longitude=destination_lon,
        label=request.destination.label,
        node_id=str(destination_node),
        road_distance_m=round(destination_distance * 1000.0, 1),
    )
    route = RouteDetails(
        algorithm=selected_result["algorithm"],
        method=request.method,
        method_label=METHOD_LABELS[request.method],
        distance_km=selected_result["total_distance_km"],
        duration_min=selected_result["total_time_min"],
        risk_score=selected_risk,
        risk_level=classify_risk(selected_risk),
        risk_exposure=selected_result["time_weighted_risk_exposure"],
        maximum_segment_risk=selected_result["maximum_segment_risk"],
        requested_risk_aversion=request.risk_aversion,
        effective_risk_aversion=selected_result["risk_aversion"],
        detour_guardrail_pct=request.max_detour_pct,
        guardrail_applied=guardrail_applied,
        same_as_fastest=same_as_fastest,
        high_risk_segments=selected_result["high_risk_segments"],
        segment_count=selected_result["num_segments"],
        risk_reduction_vs_fastest_pct=round(risk_reduction, 2),
        time_overhead_vs_fastest_pct=round(time_overhead, 2),
        hazard_summary=HazardScores(**hazard_summary),
        coordinates=[MapCoordinate(**coordinate) for coordinate in coordinates],
        risk_sections=[
            RiskSection(
                risk_level=section["risk_level"],
                risk_score=section["risk_score"],
                coordinates=[
                    MapCoordinate(**coordinate) for coordinate in section["coordinates"]
                ],
            )
            for section in risk_sections
        ],
        segments=[RouteSegment(**segment) for segment in segments],
    )

    ordered_comparison = [
        _comparison_item(results[method], fastest_result)
        for method in METHODS
        if method in results
    ]
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return RouteOptimizeResponse(
        route_id=str(uuid.uuid4()),
        status="success",
        computed_at=datetime.now(timezone.utc).isoformat(),
        processing_time_ms=round(elapsed_ms, 2),
        origin=origin,
        destination=destination,
        network=network_repository.info(),
        data_quality=_route_data_quality(graph, selected_result),
        model=_model_evidence(),
        route=route,
        comparison=ordered_comparison,
        recommendation=(
            _recommendation(
                request.method, risk_reduction, time_overhead, same_as_fastest
            )
            + (
                f" The {request.max_detour_pct:.0f}% detour guardrail adjusted "
                f"the effective safety preference to "
                f"{selected_result['risk_aversion']:.2f}."
                if guardrail_applied
                else ""
            )
        ),
    )


@app.post("/route/compare", response_model=RouteOptimizeResponse)
def compare_routes(request: RouteOptimizeRequest):
    """Convenience endpoint that always calculates all research methods."""

    return optimize_route(request.model_copy(update={"include_comparison": True}))


@app.get("/hazards/status")
def hazard_status():
    """Report the current in-memory hazard-data version."""

    return network_repository.hazard_status()


@app.post("/hazards/update", response_model=HazardUpdateResponse)
def update_hazards(request: HazardUpdateRequest):
    """Receive normalized spatial hazard signals from detection components."""

    values = request.hazards.model_dump(exclude_none=True)
    observed_at = request.observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    try:
        update = network_repository.update_hazards(
            request.coordinate,
            request.radius_km,
            values,
            request.source,
            observed_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "NO_EDGES_IN_UPDATE_AREA", "message": str(exc)},
        ) from exc
    return HazardUpdateResponse(
        status="updated",
        hazard_version=update["hazard_version"],
        updated_edges=update["updated_edges"],
        radius_km=update["radius_km"],
        source=update["source"],
        observed_at=update["observed_at"],
        values=update["values"],
    )


@app.get("/research/evidence")
def research_evidence(samples: int = 5_000):
    """Return reproducible model provenance and a monotonicity property audit."""

    checked_samples = max(100, min(int(samples), 100_000))
    return {
        "model": _model_evidence().model_dump(),
        "weighting": OBJECTIVE_WEIGHT_RESULT.as_dict(),
        "fuzzy_operator": (
            "1 - product((1 - hazard_i) ** normalized_CRITIC_weight_i)"
        ),
        "verified_properties": {
            "zero_boundary": True,
            "one_boundary": True,
            "bounded_0_1": True,
            "monotonicity": monotonicity_audit(
                samples=checked_samples, seed=2026
            ),
        },
        "claim_boundary": (
            "This verifies internal mathematical behaviour, not perfect real-world "
            "route accuracy. External field validation remains future work."
        ),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8001, reload=False)
