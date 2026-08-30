"""
Suraksha Lanka — Daily Flood-Risk XGBoost Trainer

Input : gampaha_daily_unosat_dataset.csv
Output: ../model/daily_flood_model.pkl
        ../model/daily_flood_report.txt
        ../model/daily_flood_thresholds.json

The final test set contains unseen coordinate groups. A second spatial split
inside the training data selects the probability threshold; the final test set
is not used for threshold selection.
"""

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBClassifier


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "gampaha_daily_unosat_dataset.csv"
MODEL_DIR = BASE_DIR.parent / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "daily_flood_model.pkl"
REPORT_PATH = MODEL_DIR / "daily_flood_report.txt"
THRESHOLD_PATH = MODEL_DIR / "daily_flood_thresholds.json"

FEATURES = [
    "today_rainfall_mm",
    "rain_3d_mm",
    "rain_7d_mm",
    "rain_30d_mm",
    "humidity_pct",
    "temperature_c",
    "wind_speed_kmh",
    "elevation_m",
    "soil_type",
    "river_proximity_km",
]

SOIL_MAP = {"clay": 0, "loam": 1, "sandy": 2}
SATELLITE_WEIGHT = 5.0

XGBOOST_PARAMS = {
    "n_estimators": 250,
    "max_depth": 4,
    "learning_rate": 0.05,
    "min_child_weight": 10,
    "gamma": 1.0,
    "subsample": 0.75,
    "colsample_bytree": 0.8,
    "reg_alpha": 1.0,
    "reg_lambda": 5.0,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "random_state": 42,
    "n_jobs": -1,
}


def make_groups(frame):
    return (
        frame["latitude"].round(3).astype(str)
        + "_"
        + frame["longitude"].round(3).astype(str)
    )


def split_by_group(frame, test_size, random_state):
    groups = make_groups(frame)
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=random_state,
    )
    train_positions, test_positions = next(
        splitter.split(frame, frame["flood_label"], groups=groups)
    )
    train = frame.iloc[train_positions].copy()
    test = frame.iloc[test_positions].copy()
    train_groups = set(make_groups(train))
    test_groups = set(make_groups(test))
    if not train_groups.isdisjoint(test_groups):
        raise RuntimeError("Coordinate leakage detected between splits")
    return train, test


def build_sample_weights(frame):
    positive = int(frame["flood_label"].sum())
    negative = int((frame["flood_label"] == 0).sum())
    if positive == 0 or negative == 0:
        raise RuntimeError("A training split contains only one target class")

    class_weight = negative / positive
    weights = np.where(
        frame["flood_label"].to_numpy() == 1,
        class_weight,
        1.0,
    ).astype(float)
    satellite = frame["label_source"].eq("unosat_event_window").to_numpy()
    weights[satellite] *= SATELLITE_WEIGHT
    return weights, class_weight


def make_model():
    return XGBClassifier(**XGBOOST_PARAMS)


def choose_threshold(y_true, probability):
    """Maximise F2 on inner validation, prioritising flood recall."""
    candidates = np.round(np.arange(0.05, 0.81, 0.01), 2)
    rows = []
    for threshold in candidates:
        prediction = (probability >= threshold).astype(int)
        rows.append({
            "threshold": float(threshold),
            "f2": fbeta_score(y_true, prediction, beta=2, zero_division=0),
            "f1": f1_score(y_true, prediction, zero_division=0),
            "precision": precision_score(
                y_true, prediction, zero_division=0
            ),
            "recall": recall_score(y_true, prediction, zero_division=0),
        })
    scores = pd.DataFrame(rows)
    best = scores.sort_values(
        ["f2", "recall", "precision"],
        ascending=False,
    ).iloc[0]
    return float(best["threshold"]), scores, best


def evaluate(y_true, probability, threshold):
    prediction = (probability >= threshold).astype(int)
    return {
        "prediction": prediction,
        "accuracy": accuracy_score(y_true, prediction),
        "precision": precision_score(y_true, prediction, zero_division=0),
        "recall": recall_score(y_true, prediction, zero_division=0),
        "f1": f1_score(y_true, prediction, zero_division=0),
        "f2": fbeta_score(y_true, prediction, beta=2, zero_division=0),
        "roc_auc": roc_auc_score(y_true, probability),
        "pr_auc": average_precision_score(y_true, probability),
        "confusion_matrix": confusion_matrix(y_true, prediction),
        "report": classification_report(
            y_true,
            prediction,
            target_names=["No Flood Risk", "Flood Risk"],
            zero_division=0,
        ),
    }


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {DATASET_PATH}")

    frame = pd.read_csv(DATASET_PATH)
    required = set(FEATURES + [
        "latitude",
        "longitude",
        "date",
        "flood_label",
        "label_source",
    ])
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"Dataset missing columns: {missing}")

    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["soil_type"] = frame["soil_type"].map(SOIL_MAP)
    if frame[FEATURES].isna().any().any():
        raise RuntimeError("Missing or unknown feature values detected")

    print("=" * 68)
    print("Suraksha Lanka — Daily Flood-Risk Model Training")
    print("=" * 68)
    print(f"Rows                 : {len(frame)}")
    print(
        "Locations            : "
        f"{len(frame[['latitude', 'longitude']].drop_duplicates())}"
    )
    print(f"Flood-risk rows       : {int(frame['flood_label'].sum())}")
    print(
        "UNOSAT event rows    : "
        f"{int(frame['label_source'].eq('unosat_event_window').sum())}"
    )

    # Outer spatial holdout: never used for threshold selection.
    development, test = split_by_group(frame, test_size=0.20, random_state=42)
    # Inner spatial holdout: used only to choose the decision threshold.
    fit, validation = split_by_group(
        development,
        test_size=0.20,
        random_state=17,
    )

    print(
        f"Development locations: "
        f"{len(development[['latitude', 'longitude']].drop_duplicates())}"
    )
    print(
        f"Test locations       : "
        f"{len(test[['latitude', 'longitude']].drop_duplicates())}"
    )
    print(
        f"Fit/validation rows  : {len(fit)} / {len(validation)}"
    )

    tuning_weights, tuning_class_weight = build_sample_weights(fit)
    tuning_model = make_model()
    tuning_model.fit(
        fit[FEATURES],
        fit["flood_label"],
        sample_weight=tuning_weights,
        eval_set=[(validation[FEATURES], validation["flood_label"])],
        verbose=False,
    )
    validation_probability = tuning_model.predict_proba(
        validation[FEATURES]
    )[:, 1]
    threshold, threshold_scores, best_threshold = choose_threshold(
        validation["flood_label"],
        validation_probability,
    )
    print(f"Selected threshold   : {threshold:.2f}")
    print(
        "Validation F2/recall : "
        f"{best_threshold['f2']:.4f} / {best_threshold['recall']:.4f}"
    )

    # Refit on all development locations after threshold selection.
    final_weights, final_class_weight = build_sample_weights(development)
    model = make_model()
    model.fit(
        development[FEATURES],
        development["flood_label"],
        sample_weight=final_weights,
        verbose=False,
    )

    test_probability = model.predict_proba(test[FEATURES])[:, 1]
    metrics = evaluate(test["flood_label"], test_probability, threshold)

    print(f"Test accuracy        : {metrics['accuracy']:.4f}")
    print(f"Test precision       : {metrics['precision']:.4f}")
    print(f"Test recall          : {metrics['recall']:.4f}")
    print(f"Test F1              : {metrics['f1']:.4f}")
    print(f"Test F2              : {metrics['f2']:.4f}")
    print(f"Test ROC-AUC         : {metrics['roc_auc']:.4f}")
    print(f"Test PR-AUC          : {metrics['pr_auc']:.4f}")
    print("Confusion matrix:")
    print(metrics["confusion_matrix"])
    print(metrics["report"])

    satellite_test = test["label_source"].eq("unosat_event_window")
    if satellite_test.any():
        satellite_prediction = metrics["prediction"][satellite_test.to_numpy()]
        satellite_recall = float(satellite_prediction.mean())
        satellite_text = (
            f"Untouched UNOSAT test rows: {int(satellite_test.sum())}\n"
            f"UNOSAT positive recall: {satellite_recall:.4f}\n"
            "Positive-only spatial event-window check; not multi-event validation."
        )
    else:
        satellite_text = (
            "No UNOSAT event rows occurred in the untouched spatial test split."
        )
    print(satellite_text)

    importance = pd.DataFrame({
        "feature": FEATURES,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    print("Feature importance:")
    print(importance.to_string(index=False))

    with MODEL_PATH.open("wb") as model_file:
        pickle.dump(model, model_file)

    thresholds = {
        "warning": threshold,
        # Operational high band; report it as a prototype severity boundary.
        "high": min(0.95, max(0.70, round(threshold + 0.25, 2))),
        "selection": "inner_spatial_validation_max_f2",
    }
    THRESHOLD_PATH.write_text(
        json.dumps(thresholds, indent=2),
        encoding="utf-8",
    )

    report_text = f"""Suraksha Lanka — Daily Flood-Risk Training Report
{'=' * 64}
Dataset                  : {DATASET_PATH.name}
Rows                     : {len(frame)}
Locations                : {len(frame[['latitude', 'longitude']].drop_duplicates())}
Features                 : {FEATURES}
Validation design        : outer spatial test + inner spatial threshold selection
Satellite row weight     : {SATELLITE_WEIGHT}x
Tuning class weight      : {tuning_class_weight:.4f}
Final class weight       : {final_class_weight:.4f}
Selected warning threshold: {threshold:.2f}

Test accuracy  : {metrics['accuracy']:.4f}
Test precision : {metrics['precision']:.4f}
Test recall    : {metrics['recall']:.4f}
Test F1        : {metrics['f1']:.4f}
Test F2        : {metrics['f2']:.4f}
Test ROC-AUC   : {metrics['roc_auc']:.4f}
Test PR-AUC    : {metrics['pr_auc']:.4f}

Confusion matrix:
{metrics['confusion_matrix']}

Classification report:
{metrics['report']}

UNOSAT evaluation:
{satellite_text}

Feature importance:
{importance.to_string(index=False)}

Research limitation:
Most targets are weak-rule labels. UNOSAT contributes one composite event
window at three sampled locations. Metrics therefore demonstrate prototype
feasibility against hybrid labels, not production flood-detection accuracy.
"""
    REPORT_PATH.write_text(report_text, encoding="utf-8")

    print(f"Saved model           : {MODEL_PATH}")
    print(f"Saved thresholds      : {THRESHOLD_PATH}")
    print(f"Saved report          : {REPORT_PATH}")


if __name__ == "__main__":
    main()
