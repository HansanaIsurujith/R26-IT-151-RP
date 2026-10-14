"""
Combine Environmental (Flood/Landslide) + Wildlife (Elephant/Deer) into one
grid-point dataset -- for testing fuzzy_engine.py end-to-end BEFORE the live
Kafka/API pipeline exists.

Environmental probabilities here are a PROXY: fraction of months at each grid
point labeled Flood / Landslide in the rule-based dataset (gampaha_unosat_dataset.csv).
This is NOT the same as the real XGBoost model's predict_proba() output --
replace with real probabilities once the environmental team's API is live.
This proxy is only for offline testing of your fuzzy engine and routing logic.
"""

import pandas as pd

ENV_CSV = "../data/gampaha_unosat_dataset.csv"  # place your teammate's CSV here
WILDLIFE_CSV = "../data/wildlife_risk_grid.csv"
OUTPUT_CSV = "../data/combined_hazard_grid.csv"

print("Loading environmental dataset...")
env = pd.read_csv(ENV_CSV)

# Proxy probability = fraction of recorded months at this grid point with that label
print("Computing per-point Flood/Landslide proxy probabilities...")
grp = env.groupby(["latitude", "longitude"])
flood_prob = grp.apply(lambda g: (g["risk_label"] == "Flood").mean(), include_groups=False)
landslide_prob = grp.apply(lambda g: (g["risk_label"] == "Landslide").mean(), include_groups=False)

env_grid = pd.DataFrame({
    "flood_probability_proxy": flood_prob,
    "landslide_probability_proxy": landslide_prob,
}).reset_index()

print(f"  Environmental grid points: {len(env_grid)}")

print("Loading wildlife risk grid...")
wildlife = pd.read_csv(WILDLIFE_CSV)
print(f"  Wildlife grid points: {len(wildlife)}")

print("Merging on (latitude, longitude)...")
combined = env_grid.merge(wildlife, on=["latitude", "longitude"], how="inner")
combined["segment_id"] = ["SEG_" + str(i).zfill(4) for i in range(len(combined))]

cols = ["segment_id", "latitude", "longitude", "flood_probability_proxy",
        "landslide_probability_proxy", "elephant_risk", "deer_risk",
        "wildboar_risk", "buffalo_risk"]
combined = combined[cols]
combined.to_csv(OUTPUT_CSV, index=False)

print(f"\nSaved: {OUTPUT_CSV}")
print(f"Rows: {len(combined)}")
print("\nSample rows:")
print(combined.head(5).to_string(index=False))
print("\nHigh-risk sample (any hazard proxy > 0.5):")
high = combined[(combined["flood_probability_proxy"] > 0.5) |
                 (combined["landslide_probability_proxy"] > 0.5) |
                 (combined["elephant_risk"] > 0.5)]
print(f"  {len(high)} of {len(combined)} points")
print(high.head(5).to_string(index=False))
