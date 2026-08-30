"""
Attach Hazard Data to the REAL Gampaha Road Network
Research Component | Suraksha Lanka

The real road network (from download_real_road_network.py) has 73,000+ nodes
and 166,000+ edges of pure OpenStreetMap geometry (road names, speeds,
lengths) -- but NO hazard information. Your hazard data
(combined_hazard_grid.csv) only has 228 grid points.

This script joins them: for every road edge, it finds the NEAREST hazard grid
point (using its midpoint coordinates) and attaches that point's 6 hazard
values as edge attributes -- the same attribute names routing_engine.py
already expects, so no other code needs to change.

METHOD: nearest-neighbor spatial join via a KD-tree (fast even for 166k edges).
LIMITATION to note in your report: hazard values are only as precise as your
228-point grid (~2.5km spacing) -- a road edge gets the SAME hazard values as
its nearest grid point, not a true per-edge measurement. This is a reasonable
approximation, not a source of new hazards, but worth stating explicitly.
"""

import networkx as nx
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

REAL_NETWORK = "gampaha_road_network.graphml"
HAZARD_CSV = "combined_hazard_grid.csv"
OUTPUT_NETWORK = "gampaha_road_network_with_hazards.graphml"

HAZARD_COLS = ["flood_probability_proxy", "landslide_probability_proxy",
               "elephant_risk", "buffalo_risk", "deer_risk", "wildboar_risk"]
# Renamed to match what fuzzy_engine.py / routing_engine.py expect on edges:
OUT_ATTR_NAMES = ["flood_probability", "landslide_probability",
                   "elephant_risk", "buffalo_risk", "deer_risk", "wildboar_risk"]


def main():
    print("Loading real road network...")
    G = nx.read_graphml(REAL_NETWORK)
    print(f"  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print("Casting numeric node/edge attributes from string to float...")
    for n, data in G.nodes(data=True):
        for key in ("x", "y"):
            if key in data:
                data[key] = float(data[key])
    for u, v, data in G.edges(data=True):
        for key in ("length", "travel_time", "speed_kph"):
            if key in data:
                try:
                    data[key] = float(data[key])
                except (TypeError, ValueError):
                    pass

    print("Loading hazard grid...")
    hazard = pd.read_csv(HAZARD_CSV)
    print(f"  {len(hazard)} hazard grid points")

    tree = cKDTree(hazard[["latitude", "longitude"]].values)

    print("Computing edge midpoints and finding nearest hazard point for each edge...")
    edge_list = list(G.edges(keys=True, data=True)) if G.is_multigraph() else \
        [(u, v, None, d) for u, v, d in G.edges(data=True)]

    midpoints = []
    for u, v, k, data in edge_list:
        uy, ux = G.nodes[u]["y"], G.nodes[u]["x"]
        vy, vx = G.nodes[v]["y"], G.nodes[v]["x"]
        midpoints.append(((uy + vy) / 2, (ux + vx) / 2))
    midpoints = np.array(midpoints)

    _, nearest_idx = tree.query(midpoints)

    print("Attaching hazard attributes to edges...")
    for (u, v, k, data), idx in zip(edge_list, nearest_idx):
        row = hazard.iloc[idx]
        for src_col, out_attr in zip(HAZARD_COLS, OUT_ATTR_NAMES):
            data[out_attr] = float(row[src_col])
        # travel_time_min for routing_engine.py's get_travel_time()
        if "travel_time" in data:
            data["travel_time_min"] = data["travel_time"] / 60.0
        elif "length" in data:
            data["travel_time_min"] = (data["length"] / 1000.0) / 40.0 * 60.0

    print(f"Saving intermediate (multigraph) file skipped -- collapsing parallel edges next...")

    # ── Collapse MultiDiGraph -> simple DiGraph ────────────────────────────
    # Real OSM data has parallel edges (multiple road segments between the
    # same two points, e.g. dual carriageways represented as separate ways).
    # routing_engine.py expects one edge per (u,v) pair. For each pair with
    # multiple parallel edges, keep only the FASTEST one (min travel_time_min)
    # -- a standard simplification also used internally by routing libraries.
    if G.is_multigraph():
        print("Collapsing parallel edges (keeping fastest per node pair)...")
        simple_G = nx.DiGraph() if G.is_directed() else nx.Graph()
        simple_G.add_nodes_from(G.nodes(data=True))
        best_edge = {}
        for u, v, data in G.edges(data=True):
            key = (u, v)
            tt = data.get("travel_time_min", float("inf"))
            if key not in best_edge or tt < best_edge[key][1]:
                best_edge[key] = (data, tt)
        for (u, v), (data, _) in best_edge.items():
            simple_G.add_edge(u, v, **data)
        print(f"  Collapsed {G.number_of_edges()} edges -> {simple_G.number_of_edges()} edges "
              f"({simple_G.number_of_edges()} unique node pairs)")
        G = simple_G

    print(f"Saving: {OUTPUT_NETWORK}")
    nx.write_graphml(G, OUTPUT_NETWORK)

    # sanity check
    sample_edges = list(G.edges(data=True))[:3]
    print("\nSample joined edges:")
    for u, v, d in sample_edges:
        print(f"  {u} -> {v}: flood={d.get('flood_probability'):.3f} "
              f"landslide={d.get('landslide_probability'):.3f} "
              f"elephant={d.get('elephant_risk'):.4f} time_min={d.get('travel_time_min'):.2f}")

    print("\nDone. This file is now a drop-in replacement for the synthetic network")
    print("in routing_engine.py -- same attribute names, real roads, real hazard data.")


if __name__ == "__main__":
    main()
