"""
Suraksha Lanka -- Flood Risk Model Training (flood-only, v2: weighted)
Project : R26-IT-151

CHANGE FROM v1: satellite-verified rows (label_source == 'unosat_satellite')
now get a higher sample_weight during training, so the model doesn't drown
out the real ground-truth signal under the much larger rule-based majority.

Drop into: backend/Flood-Landslide/dataset/train_flood_model.py
Run from that folder. Reads gampaha_unosat_dataset.csv (same folder),
writes ../model/flood_model.pkl and ../model/flood_report.txt.
"""

import pandas as pd
import numpy as np
import pickle
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_score
from sklearn.metrics import (classification_report, confusion_matrix,
                              accuracy_score, roc_auc_score,
                              precision_score, recall_score, f1_score,
                              average_precision_score)
from xgboost import XGBClassifier

DATASET = "gampaha_unosat_dataset_newest.csv"
MODEL_DIR = "../model"
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH  = os.path.join(MODEL_DIR, "flood_model.pkl")
REPORT_PATH = os.path.join(MODEL_DIR, "flood_report.txt")

FLOOD_FEATURES = [
    "latitude",
    "longitude",
    "rainfall_mm",
    "humidity_pct",
    "temperature_c",
    "wind_speed_kmh",
    "elevation_m",
    "soil_type",
    "river_proximity_km",
]

SOIL_MAP = {"clay": 0, "loam": 1, "sandy": 2}

# How much more a satellite-verified row counts vs. a rule-based row.
# Satellite rows are ~5.4% of the data (507 / 9334) -- weighting them ~8x
# roughly balances their influence against the rule-based majority without
# letting them totally dominate (they're all positive-class, so overweighting
# too aggressively would just teach the model "always predict Flood").
SATELLITE_WEIGHT = 8.0
RULE_BASED_WEIGHT = 1.0

XGBOOST_PARAMS = dict(
    n_estimators=150,
    max_depth=3,
    learning_rate=0.05,
    gamma=2.0,
    min_child_weight=10,
    subsample=0.7,
    colsample_bytree=0.7,
    reg_alpha=1.0,
    reg_lambda=4.0,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42,
    n_jobs=-1,
)

print("=" * 60)
print("  Suraksha Lanka -- Flood Model Training (v2: weighted)")
print("=" * 60)

df = pd.read_csv(DATASET)
print(f"\nLoaded: {len(df)} rows")
print(df["risk_label"].value_counts())

if "label_source" in df.columns:
    sat_flood = df[(df["risk_label"] == "Flood") & (df["label_source"] == "unosat_satellite")]
    rule_flood = df[(df["risk_label"] == "Flood") & (df["label_source"] == "rule_based")]
    print(f"\nFlood labels -- satellite-verified: {len(sat_flood)} | rule-based: {len(rule_flood)}")

df["soil_type"] = df["soil_type"].map(SOIL_MAP)

y = (df["risk_label"] == "Flood").astype(int)
X = df[FLOOD_FEATURES]

# Build per-row sample weights
if "label_source" in df.columns:
    weights = df["label_source"].map(
        {"unosat_satellite": SATELLITE_WEIGHT, "rule_based": RULE_BASED_WEIGHT}
    ).fillna(RULE_BASED_WEIGHT)
else:
    weights = pd.Series(RULE_BASED_WEIGHT, index=df.index)

print(f"\nClass balance -- Flood: {y.sum()} | No Flood: {(y == 0).sum()}")
print(f"Sample weight -- satellite rows: {SATELLITE_WEIGHT}x | rule-based rows: {RULE_BASED_WEIGHT}x")

# Create one group ID for each coordinate
groups = (
    df["latitude"].round(3).astype(str)
    + "_"
    + df["longitude"].round(3).astype(str)
)

# Split by location so the same coordinates cannot appear
# in both training and testing datasets
splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=42
)

train_idx, test_idx = next(
    splitter.split(
        X,
        y,
        groups=groups
    )
)

# Create training and testing datasets
X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]

y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]

w_train = weights.iloc[train_idx]

# Confirm that training and testing locations are separate
train_groups = set(groups.iloc[train_idx])
test_groups = set(groups.iloc[test_idx])

assert train_groups.isdisjoint(test_groups)

print(f"\nTraining locations : {len(train_groups)}")
print(f"Testing locations  : {len(test_groups)}")

# Calculate flood class-balancing weight
negative_count = int((y_train == 0).sum())
positive_count = int((y_train == 1).sum())

if positive_count == 0:
    raise RuntimeError(
        "Training set contains no Flood records"
    )

flood_class_weight = negative_count / positive_count

# Start with UNOSAT/rule-based sample weights
training_weights = w_train.to_numpy(
    dtype=float
).copy()

# Give every Flood record additional importance
training_weights *= np.where(
    y_train.to_numpy() == 1,
    flood_class_weight,
    1.0
)

print(f"Training No Flood rows : {negative_count}")
print(f"Training Flood rows    : {positive_count}")
print(
    f"Flood class weight     : "
    f"{flood_class_weight:.2f}x"
)
model = XGBClassifier(**XGBOOST_PARAMS)
model.fit(X_train, y_train, sample_weight=training_weights, eval_set=[(X_test, y_test)], verbose=False)

DECISION_THRESHOLD = 0.30

y_prob = model.predict_proba(X_test)[:, 1]

y_pred = (
    y_prob >= DECISION_THRESHOLD
).astype(int)

print(f"Decision threshold     : {DECISION_THRESHOLD:.2f}")
test_acc = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_prob)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
pr_auc = average_precision_score(y_test, y_prob)

print(f"\nOverall test accuracy : {test_acc*100:.2f}%")
print(f"Overall ROC-AUC       : {roc_auc:.4f}")
print(f"Flood precision       : {precision:.4f}")
print(f"Flood recall          : {recall:.4f}")
print(f"Flood F1-score        : {f1:.4f}")
print(f"Flood PR-AUC          : {pr_auc:.4f}")

# CV without weighting (cross_val_score doesn't cleanly thread sample_weight
# through per-fold splits here) -- treat this as a secondary sanity check,
# not the headline number.
cv = GroupKFold(n_splits=5)
cv_scores = cross_val_score(
    XGBClassifier(**XGBOOST_PARAMS), X, y, groups=groups,
    cv=cv, scoring="f1", n_jobs=-1
)
print(f"5-fold spatial CV F1 (unweighted): {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")

report = classification_report(y_test, y_pred, target_names=["No Flood", "Flood"])
cm = confusion_matrix(y_test, y_pred)
print("\n" + report)
print(cm)

# ---- Honest evaluation on satellite-verified rows only ----
sat_eval_text = "N/A -- no satellite-confirmed rows occurred in the spatial test split"
if "label_source" in df.columns:
    test_source = df.iloc[test_idx]["label_source"]
    sat_mask = test_source == "unosat_satellite"
    if sat_mask.sum() > 0:
        X_sat = X_test.loc[sat_mask]
        y_sat = y_test.loc[sat_mask]
        y_sat_prob = model.predict_proba(X_sat)[:, 1]
        y_sat_pred = (
            y_sat_prob >= DECISION_THRESHOLD
        ).astype(int)
        sat_recall = (y_sat_pred == 1).sum() / len(y_sat)  # all rows here are positive
        sat_eval_text = (
            f"Untouched satellite test rows evaluated: {sat_mask.sum()}\n"
            f"Recall on satellite test flood rows: {sat_recall*100:.2f}%\n"
            f"This is a positive-only spatial holdout check for one event;\n"
            f"it does not establish multi-event generalization."
        )
print("\n" + sat_eval_text)

importance = pd.DataFrame({
    "feature": FLOOD_FEATURES,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)
print("\nFeature importance:\n", importance.to_string(index=False))

with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

report_text = f"""Suraksha Lanka -- Flood Model Training Report (v2: weighted)
Project  : R26-IT-151
{"="*50}
Dataset       : {DATASET}
Model         : Binary XGBoost (Flood vs. Not Flood)
Total rows    : {len(df)}
Features      : {FLOOD_FEATURES}
Sample weighting: satellite-verified rows x{SATELLITE_WEIGHT}, rule-based x{RULE_BASED_WEIGHT}

Overall test accuracy : {test_acc*100:.2f}%
Overall ROC-AUC        : {roc_auc:.4f}
Flood precision        : {precision:.4f}
Flood recall           : {recall:.4f}
Flood F1-score         : {f1:.4f}
Flood PR-AUC           : {pr_auc:.4f}
5-fold spatial CV F1 (unweighted): {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}

IMPORTANT -- label source note:
{sat_eval_text}

Classification Report:
{report}

Confusion Matrix:
{cm}

Feature Importance:
{importance.to_string(index=False)}
"""
with open(REPORT_PATH, "w") as f:
    f.write(report_text)

print(f"\nSaved: {MODEL_PATH}")
print(f"Saved: {REPORT_PATH}")
print(f"\nmodel.feature_names_in_ = {list(model.feature_names_in_)}")
print("(this must match main.py's feature_map keys exactly -- it does)")
