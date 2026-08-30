import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    balanced_accuracy_score,
    roc_auc_score
)

# ============================================================
# 1. LOAD DATASET
# ============================================================

DATASET_PATH = "gampaha_master_nasa_dataset.csv"

df = pd.read_csv(DATASET_PATH)

print("=" * 60)
print("LANDSLIDE MODEL TRAINING")
print("=" * 60)

print(f"Dataset shape: {df.shape}")

# ============================================================
# 2. REMOVE DUPLICATES
# ============================================================

before = len(df)

df = df.drop_duplicates().reset_index(drop=True)

after = len(df)

print(f"\nDuplicates removed: {before - after}")
print(f"Dataset after cleaning: {df.shape}")

# ============================================================
# 3. TARGET
# ============================================================

TARGET = "landslide_label"

X = df.drop(columns=[TARGET])
y = df[TARGET]

print("\n=== TARGET DISTRIBUTION ===")
print(y.value_counts())

print("\n=== TARGET PERCENTAGE ===")
print((y.value_counts(normalize=True) * 100).round(2))

# ============================================================
# 4. REMOVE COLUMNS THAT SHOULD NOT BE USED
# ============================================================

# These are labels / sources, not prediction features.
columns_to_remove = [
    "risk_label",
    "unosat_flood",
    "unosat_water",
    "unosat_landslide",
    "label_source",
    "nasa_landslide",
    "nasa_nearest_event_km",
    "nasa_trigger"
]

X = X.drop(
    columns=[c for c in columns_to_remove if c in X.columns],
    errors="ignore"
)

# ============================================================
# 5. CONVERT MONTH
# ============================================================

if "month" in X.columns:

    X["month"] = pd.to_datetime(
        X["month"],
        format="%Y-%m",
        errors="coerce"
    )

    X["year"] = X["month"].dt.year
    X["month_number"] = X["month"].dt.month

    X = X.drop(columns=["month"])

# ============================================================
# 6. FEATURES
# ============================================================

numeric_features = [
    "latitude",
    "longitude",
    "rainfall_mm",
    "humidity_pct",
    "temperature_c",
    "wind_speed_kmh",
    "elevation_m",
    "slope_degree",
    "river_proximity_km",
    "ndvi",
    "year",
    "month_number"
]

categorical_features = [
    "soil_type"
]

# Keep only columns that actually exist
numeric_features = [
    c for c in numeric_features if c in X.columns
]

categorical_features = [
    c for c in categorical_features if c in X.columns
]

print("\n=== FEATURES ===")
print("Numeric:", numeric_features)
print("Categorical:", categorical_features)

# ============================================================
# 7. PREPROCESSING
# ============================================================

numeric_pipeline = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ]
)

categorical_pipeline = Pipeline(
    steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore"
            )
        )
    ]
)

preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            numeric_features
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical_features
        )
    ]
)

# ============================================================
# 8. TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\n=== DATA SPLIT ===")
print("Training:", X_train.shape)
print("Testing :", X_test.shape)

print("\nTraining labels:")
print(y_train.value_counts())

print("\nTesting labels:")
print(y_test.value_counts())

# ============================================================
# 9. RANDOM FOREST
# ============================================================

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ]
)

# ============================================================
# 10. TRAIN
# ============================================================

print("\n" + "=" * 60)
print("TRAINING MODEL...")
print("=" * 60)

pipeline.fit(X_train, y_train)

print("Training completed.")

# ============================================================
# 11. PREDICTION
# ============================================================

y_pred = pipeline.predict(X_test)

# Probability for ROC-AUC
y_probability = pipeline.predict_proba(X_test)[:, 1]

# ============================================================
# 12. EVALUATION
# ============================================================

print("\n" + "=" * 60)
print("MODEL EVALUATION")
print("=" * 60)

print("\nAccuracy:")
print(round(accuracy_score(y_test, y_pred), 4))

print("\nBalanced Accuracy:")
print(round(balanced_accuracy_score(y_test, y_pred), 4))

print("\nROC-AUC:")
print(round(roc_auc_score(y_test, y_probability), 4))

print("\n=== CLASSIFICATION REPORT ===")

print(
    classification_report(
        y_test,
        y_pred,
        target_names=[
            "No Landslide",
            "Landslide"
        ],
        zero_division=0
    )
)

print("\n=== CONFUSION MATRIX ===")

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)

# ============================================================
# 13. SAVE MODEL
# ============================================================

import joblib

MODEL_PATH = "landslide_model.pkl"

joblib.dump(
    pipeline,
    MODEL_PATH
)

print("\n" + "=" * 60)
print(f"MODEL SAVED: {MODEL_PATH}")
print("=" * 60)