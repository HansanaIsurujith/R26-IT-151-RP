"""
Wildlife Occurrence -> Grid-Point Risk Score
Converts raw GBIF sighting records (wildlife_road_master_step1.xlsx) into a
0-1 risk score per grid point, using an exponential distance-decay kernel.

METHOD (documented for your report):
  For each grid point g and species s:
    risk(g, s) = normalize( sum_i  exp( -distance(g, record_i) / BANDWIDTH_KM ) )
  where the sum is over all occurrence records of species s, distance is the
  haversine (great-circle) distance in km, and BANDWIDTH_KM controls how far
  a sighting's influence extends. This is a standard kernel density approach
  for occurrence-to-surface conversion (cite: kernel density estimation, KDE,
  in ecological risk mapping literature).

IMPORTANT FINDING (read before using this script):
  Only ~19 of 4,130 wildlife records fall strictly inside the Gampaha bounding
  box used by your environmental team (6.90-7.40N, 79.85-80.35E) -- 18
  Elephant, 1 Spotted Deer. The dataset is nationwide, and Gampaha itself
  (a wet-zone, more urbanized district) has comparatively few recorded
  elephant/deer-road interactions versus dry-zone districts.
  This script therefore fits the kernel using ALL national records (so the
  density estimate borrows spatial signal from nearby regions) but evaluates
  it only at Gampaha grid points. The resulting Gampaha risk scores will be
  LOW and relatively FLAT across most of the district -- this is very likely
  a genuine finding (Gampaha has low wildlife-road conflict), not a bug, but
  you MUST state this as a data limitation in your report: your wildlife risk
  layer for Gampaha is thin on ground-truth points, and study-area choice may
  be worth revisiting with your supervisor if strong wildlife variation is
  something the project actually needs to demonstrate.
"""

import pandas as pd
import numpy as np

INPUT_XLSX = "../data/wildlife_road_master_step1.xlsx"  # place teammate's xlsx here
OUTPUT_CSV = "../data/wildlife_risk_grid.csv"

# Grid -- MUST match the environmental team's grid exactly (generate_dataset_new.py)
LAT_MIN, LAT_MAX = 6.90, 7.40
LNG_MIN, LNG_MAX = 79.85, 80.35
GRID_STEP = 0.025

# Kernel bandwidth in km. Larger = smoother/more spread influence.
# 5km is a reasonable starting default for road-wildlife conflict zones;
# tune and justify this choice (e.g. via sensitivity check) in your report.
BANDWIDTH_KM = 5.0

# Scope decision (see prior discussion): core species per original proposal.
# Wild Boar / Buffalo columns are also computed below in case you extend scope.
SPECIES_LIST = ["Elephant", "Spotted Deer", "Wild Boar", "Buffalo"]
SPECIES_COL_NAME = {
    "Elephant": "elephant_risk",
    "Spotted Deer": "deer_risk",
    "Wild Boar": "wildboar_risk",
    "Buffalo": "buffalo_risk",
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorized haversine distance in km. lat1/lon1 can be arrays, lat2/lon2 scalars or arrays."""
    R = 6371.0
    lat1r, lon1r, lat2r, lon2r = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def build_grid():
    lats = np.arange(LAT_MIN, LAT_MAX + GRID_STEP, GRID_STEP)
    lngs = np.arange(LNG_MIN, LNG_MAX + GRID_STEP, GRID_STEP)
    grid = [(round(la, 3), round(lo, 3)) for la in lats for lo in lngs]
    return pd.DataFrame(grid, columns=["latitude", "longitude"])


def score_species(grid_df, records_df, bandwidth_km):
    """Returns a raw (unnormalized) kernel density score per grid point."""
    rec_lats = records_df["Latitude"].values
    rec_lons = records_df["Longitude"].values
    scores = np.zeros(len(grid_df))
    for idx, (glat, glon) in enumerate(zip(grid_df["latitude"], grid_df["longitude"])):
        d = haversine_km(glat, glon, rec_lats, rec_lons)
        scores[idx] = np.sum(np.exp(-d / bandwidth_km))
    return scores


def main():
    print("=" * 70)
    print("  Wildlife Occurrence -> Grid Risk Score")
    print("=" * 70)

    wl = pd.read_excel(INPUT_XLSX, sheet_name="Wildlife_Road_Master")
    print(f"  Loaded {len(wl)} occurrence records")

    grid = build_grid()
    print(f"  Grid points: {len(grid)} (matches environmental team's grid)")

    # Flag the sparsity finding
    in_box = wl[(wl["Latitude"] >= LAT_MIN) & (wl["Latitude"] <= LAT_MAX) &
                (wl["Longitude"] >= LNG_MIN) & (wl["Longitude"] <= LNG_MAX)]
    print(f"\n  ⚠ Records strictly inside Gampaha bbox: {len(in_box)} / {len(wl)}")
    print(f"    {in_box['Species'].value_counts().to_dict()}")
    print("    Kernel is fit on ALL national records, evaluated at Gampaha grid only.")
    print("    See docstring at top of this script for what this means for your report.\n")

    for species in SPECIES_LIST:
        recs = wl[wl["Species"] == species]
        col = SPECIES_COL_NAME[species]
        if len(recs) == 0:
            grid[col] = 0.0
            print(f"  {species}: 0 records -> risk set to 0.0 everywhere")
            continue
        raw = score_species(grid, recs, BANDWIDTH_KM)
        rng = raw.max() - raw.min()
        grid[col] = (raw - raw.min()) / rng if rng > 0 else 0.0
        print(f"  {species}: {len(recs)} records | raw score range [{raw.min():.3f}, {raw.max():.3f}] "
              f"-> normalized 0-1 | mean={grid[col].mean():.3f} max={grid[col].max():.3f}")

    grid.to_csv(OUTPUT_CSV, index=False)
    print(f"\n  Saved: {OUTPUT_CSV}")
    print(f"  Columns: {list(grid.columns)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
