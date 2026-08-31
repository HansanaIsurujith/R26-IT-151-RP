"""
Run this on YOUR OWN machine (not in this sandbox), where you have internet
access to OpenStreetMap's servers. This sandbox cannot reach OSM (network
restrictions), so the real download must happen locally.

Requirements: pip install osmnx networkx
Tested against osmnx 2.1.1 (osmnx changed its bbox argument order in v2.0 --
this script handles both the old and new API automatically).

Output: gampaha_road_network.graphml -- your real routable road graph.
"""

import osmnx as ox
import networkx as nx

# Same bounding box as your environmental team's grid
LAT_MIN, LAT_MAX = 6.90, 7.40
LNG_MIN, LNG_MAX = 79.85, 80.35

print(f"osmnx version: {ox.__version__}")
print("Downloading Gampaha road network from OpenStreetMap...")
print("(This can take 1-3 minutes depending on connection.)")

try:
    # osmnx >= 2.0: bbox is (left, bottom, right, top) = (west, south, east, north)
    G = ox.graph_from_bbox(
        bbox=(LNG_MIN, LAT_MIN, LNG_MAX, LAT_MAX),
        network_type="drive"
    )
except TypeError:
    # osmnx < 2.0: separate north/south/east/west arguments
    G = ox.graph_from_bbox(
        north=LAT_MAX, south=LAT_MIN, east=LNG_MAX, west=LNG_MIN,
        network_type="drive"
    )

print(f"Downloaded: {len(G.nodes)} nodes, {len(G.edges)} edges")

# Add travel time as an edge attribute (needed for your cost function T(e))
G = ox.add_edge_speeds(G)       # estimates km/h per road type
G = ox.add_edge_travel_times(G) # adds 'travel_time' in seconds per edge

ox.save_graphml(G, "gampaha_road_network.graphml")
print("Saved: gampaha_road_network.graphml")
print("\nNext: load it with:")
print("  import osmnx as ox")
print("  G = ox.load_graphml('gampaha_road_network.graphml')")
print("\nEach edge has 'length' (meters) and 'travel_time' (seconds) attributes")
print("ready to feed into fuzzy_engine.py's segment_cost() function.")
