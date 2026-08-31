"""
Suraksha Lanka -- Flood decision-threshold generator
Project : R26-IT-151

Drop into: backend/Flood-Landslide/dataset/generate_flood_threshold.py
Run AFTER train_flood_model.py. Reads ../model/flood_model.pkl,
writes/updates ../model/thresholds.json with the optimal flood
probability cutoff (Youden's J statistic on the ROC curve --
maximizes true-positive rate minus false-positive rate).

If ../model/thresholds.json already has a "landslide" key from a
previous run, this script preserves it and only updates "flood".
"""

import pandas as pd
import numpy as np
import pickle
import json
import os

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve

DATASET = "gampaha_unosat_dataset.csv"
MODEL_DIR = "../model"
MODEL_PATH = os.path.join(MODEL_DIR, "flood_model.pkl")
THRESHOLDS_PATH = os.path.join(MODEL_DIR, "thresholds.json")

SOIL_MAP = {"clay": 0, "loam": 1, "sandy": 2}
FLOOD_FEATURES = [
    "latitude", "longitude",
    "rainfall_mm", "humidity_pct", "temperature_c", "wind_speed_kmh",
    "elevation_m", "soil_type",
]

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

df = pd.read_csv(DATASET)
df["soil_type"] = df["soil_type"].map(SOIL_MAP)
y = (df["risk_label"] == "Flood").astype(int)
X = df[FLOOD_FEATURES]

# Same split as training so this is evaluated on held-out data, not train data
_, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

y_prob = model.predict_proba(X_test)[:, 1]
fpr, tpr, thresh = roc_curve(y_test, y_prob)
youden_j = tpr - fpr
best_idx = np.argmax(youden_j)
optimal_threshold = float(thresh[best_idx])

print(f"Optimal flood threshold (Youden's J): {optimal_threshold:.4f}")
print(f"  TPR at this threshold: {tpr[best_idx]:.4f}")
print(f"  FPR at this threshold: {fpr[best_idx]:.4f}")

thresholds = {}
if os.path.exists(THRESHOLDS_PATH):
    with open(THRESHOLDS_PATH) as f:
        thresholds = json.load(f)

thresholds["flood"] = {"optimal": round(optimal_threshold, 4)}

with open(THRESHOLDS_PATH, "w") as f:
    json.dump(thresholds, f, indent=2)

print(f"\nSaved: {THRESHOLDS_PATH}")
print(json.dumps(thresholds, indent=2))
