"""
Synthetic PLACEHOLDER road network for Gampaha -- lets you test routing logic
(A*, cost function, fuzzy engine integration) TODAY, before you've run
download_real_road_network.py locally. This is NOT real road geometry --
replace it with the real OSMnx graph before running your actual experiments
and before showing anything to your panel as "results."

Builds a grid graph aligned to the same coordinates as your hazard grid
(combined_hazard_grid.csv), so hazard values attach directly to nodes/edges.
"""

import pandas as pd
import networkx as nx
import numpy as np

HAZARD_CSV = "../data/combined_hazard_grid.csv"
OUTPUT_GRAPHML = "../network/synthetic_road_network.graphml"

GRID_STEP = 0.025
AVG_SPEED_KMH = 40  # assumed average driving speed for placeholder travel-time calc


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1r, lon1r, lat2r, lon2r = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2r - lat1r, lon2r - lon1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def main():
    hazard = pd.read_csv(HAZARD_CSV)
    print(f"Loaded {len(hazard)} hazard grid points")

    G = nx.Graph()
    coord_to_id = {}
    for _, row in hazard.iterrows():
        nid = row["segment_id"]
        coord_to_id[(round(row["latitude"], 3), round(row["longitude"], 3))] = nid
        G.add_node(
            nid,
            latitude=row["latitude"],
            longitude=row["longitude"],
            flood_probability=row["flood_probability_proxy"],
            landslide_probability=row["landslide_probability_proxy"],
            elephant_risk=row["elephant_risk"],
            buffalo_risk=row["buffalo_risk"],
            deer_risk=row["deer_risk"],
            wildboar_risk=row["wildboar_risk"],
        )

    # Connect each node to its immediate grid neighbors (N/S/E/W) -> edges = road segments
    edge_count = 0
    for (lat, lng), nid in coord_to_id.items():
        neighbors = [
            (round(lat + GRID_STEP, 3), lng),
            (round(lat - GRID_STEP, 3), lng),
            (lat, round(lng + GRID_STEP, 3)),
            (lat, round(lng - GRID_STEP, 3)),
        ]
        for nlat, nlng in neighbors:
            nkey = (nlat, nlng)
            if nkey in coord_to_id:
                other_id = coord_to_id[nkey]
                if not G.has_edge(nid, other_id):
                    dist_km = haversine_km(lat, lng, nlat, nlng)
                    travel_time_min = (dist_km / AVG_SPEED_KMH) * 60
                    # edge hazard = average of the two endpoint nodes' hazard values
                    G.add_edge(
                        nid, other_id,
                        length_km=round(dist_km, 3),
                        travel_time_min=round(travel_time_min, 2),
                        flood_probability=(G.nodes[nid]["flood_probability"] + G.nodes[other_id]["flood_probability"]) / 2,
                        landslide_probability=(G.nodes[nid]["landslide_probability"] + G.nodes[other_id]["landslide_probability"]) / 2,
                        elephant_risk=(G.nodes[nid]["elephant_risk"] + G.nodes[other_id]["elephant_risk"]) / 2,
                        buffalo_risk=(G.nodes[nid]["buffalo_risk"] + G.nodes[other_id]["buffalo_risk"]) / 2,
                        deer_risk=(G.nodes[nid]["deer_risk"] + G.nodes[other_id]["deer_risk"]) / 2,
                        wildboar_risk=(G.nodes[nid]["wildboar_risk"] + G.nodes[other_id]["wildboar_risk"]) / 2,
                    )
                    edge_count += 1

    print(f"Built synthetic graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    nx.write_graphml(G, OUTPUT_GRAPHML)
    print(f"Saved: {OUTPUT_GRAPHML}")
    print("\nThis is placeholder geometry (grid-aligned straight edges), not real roads.")
    print("Swap in gampaha_road_network.graphml (from download_real_road_network.py) once available.")
    return G


if __name__ == "__main__":
    main()
