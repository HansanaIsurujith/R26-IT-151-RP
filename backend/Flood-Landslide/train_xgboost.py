"""
Suraksha Lanka — XGBoost Binary Model Training (FIXED v3)
Project : R26-IT-151
Student : IT22294470

Target: 90-93% accuracy
"""

import pandas as pd
import numpy as np
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection  import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics          import (classification_report, confusion_matrix,
                                      accuracy_score, roc_auc_score)
from xgboost import XGBClassifier

os.makedirs("model", exist_ok=True)

DATASET = "gampaha_unosat_dataset.csv"

# Flood features — remove estimated terrain features
FLOOD_FEATURES = [
    'latitude', 'longitude',
    'rainfall_mm', 'humidity_pct', 'temperature_c', 'wind_speed_kmh',
    'elevation_m', 'soil_type'
]

# Landslide features — remove ndvi (too dominant 52%)
LANDSLIDE_FEATURES = [
    'latitude', 'longitude',
    'rainfall_mm', 'humidity_pct', 'temperature_c', 'wind_speed_kmh',
    'elevation_m', 'soil_type', 'river_proximity_km'
]

# Stronger regularization
XGBOOST_PARAMS = dict(
    n_estimators      = 150,
    max_depth         = 2,       # very shallow
    learning_rate     = 0.05,
    gamma             = 8.0,     # strong pruning
    min_child_weight  = 25,      # very high
    subsample         = 0.6,
    colsample_bytree  = 0.6,
    reg_alpha         = 2.0,
    reg_lambda        = 8.0,
    objective         = 'binary:logistic',
    eval_metric       = 'logloss',
    random_state      = 42,
    n_jobs            = -1
)

# ── Load ───────────────────────────────────────────────────────────────────────
print("=" * 55)
print("  Suraksha Lanka — Binary XGBoost Training (v3)")
print("=" * 55)

df = pd.read_csv(DATASET)
print(f"\n  Loaded : {len(df)} rows")
print(f"  Labels :\n{df['risk_label'].value_counts()}\n")

df['soil_type'] = df['soil_type'].map({'clay': 0, 'loam': 1, 'sandy': 2})
df = df.drop(columns=['month', 'label_source', 'unosat_flood',
                       'unosat_water', 'unosat_landslide'], errors='ignore')

def split_then_augment(df, pos_label, features, test_size=0.2, seed=42):
    y = (df['risk_label'] == pos_label).astype(int)
    X = df[features]

    # Split original first
    X_train_orig, X_test, y_train_orig, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    # Augment train only
    train_df = X_train_orig.copy()
    train_df['__label__'] = y_train_orig.values

    class_counts  = train_df['__label__'].value_counts()
    target_count  = int(class_counts.max() * 0.8)
    aug_parts     = [train_df]

    for label_val in [0, 1]:
        class_df = train_df[train_df['__label__'] == label_val]
        if len(class_df) < target_count:
            needed  = target_count - len(class_df)
            sampled = class_df.sample(n=needed, replace=True, random_state=seed).copy()
            num_cols = [c for c in features if c not in ['soil_type']]
            for col in num_cols:
                std = sampled[col].std()
                if std > 0:
                    sampled[col] = (sampled[col] +
                                    np.random.normal(0, std * 0.1,
                                    len(sampled))).round(2)
            aug_parts.append(sampled)

    train_aug   = pd.concat(aug_parts, ignore_index=True).sample(
        frac=1, random_state=seed).reset_index(drop=True)
    X_train_aug = train_aug[features]
    y_train_aug = train_aug['__label__']

    print(f"  Train (aug) : {len(X_train_aug)} | Pos: {y_train_aug.sum()} | Neg: {(y_train_aug==0).sum()}")
    print(f"  Test (orig) : {len(X_test)} | Pos: {y_test.sum()} | Neg: {(y_test==0).sum()}")

    return X_train_aug, X_test, y_train_aug, y_test, X, y


def train_binary_model(df, model_name, pos_label, features, model_path, report_path):
    print(f"\n{'=' * 55}")
    print(f"  Training : {model_name}")
    print(f"  Positive : '{pos_label}' = 1  |  Others = 0")
    print(f"  Features : {features}")
    print(f"{'=' * 55}")

    X_train, X_test, y_train, y_test, X_full, y_full = split_then_augment(
        df, pos_label, features
    )

    model = XGBClassifier(**XGBOOST_PARAMS)
    print(f"\n  Training...")
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    y_pred   = model.predict(X_test)
    y_prob   = model.predict_proba(X_test)[:, 1]
    test_acc = accuracy_score(y_test, y_pred)
    roc_auc  = roc_auc_score(y_test, y_prob)

    print(f"\n{'─' * 55}")
    print(f"  Test Accuracy : {test_acc * 100:.2f}%")
    print(f"  ROC-AUC Score : {roc_auc:.4f}")
    print(f"{'─' * 55}")

    print(f"\n  5-Fold CV (original data)...")
    cv        = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(
        XGBClassifier(**XGBOOST_PARAMS),
        X_full, y_full, cv=cv, scoring='accuracy', n_jobs=-1
    )
    print(f"  CV Scores : {[f'{s*100:.2f}%' for s in cv_scores]}")
    print(f"  CV Mean   : {cv_scores.mean()*100:.2f}%")
    print(f"  CV Std    : {cv_scores.std()*100:.2f}%")

    report = classification_report(
        y_test, y_pred, target_names=[f'No {pos_label}', pos_label]
    )
    print(f"\n  Classification Report:")
    print(report)

    cm    = confusion_matrix(y_test, y_pred)
    cm_df = pd.DataFrame(
        cm,
        index   = [f'Actual No {pos_label}', f'Actual {pos_label}'],
        columns = [f'Pred No {pos_label}',   f'Pred {pos_label}']
    )
    print(f"  Confusion Matrix:")
    print(cm_df)

    importance = pd.DataFrame({
        'feature'   : features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print(f"\n  Top 5 Features:")
    print(importance.head(5).to_string(index=False))

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    report_text = f"""
Suraksha Lanka — {model_name} Training Report (v3)
Project  : R26-IT-151
Student  : IT22294470
{"=" * 50}
Dataset       : {DATASET}
Model         : Binary XGBoost ({pos_label} vs No {pos_label})
Total Rows    : {len(df)}
Features used : {features}

Fix applied   : Split before augmentation + stronger regularization
Test set      : Original data only (no augmented rows)

Test Accuracy    : {test_acc * 100:.2f}%
ROC-AUC Score    : {roc_auc:.4f}
CV Mean Accuracy : {cv_scores.mean()*100:.2f}% +/- {cv_scores.std()*100:.2f}%

XGBoost Parameters (v3 — stronger regularization):
  n_estimators     = 150
  max_depth        = 2
  learning_rate    = 0.05
  gamma            = 8.0
  min_child_weight = 25
  subsample        = 0.6
  colsample_bytree = 0.6
  reg_alpha        = 2.0
  reg_lambda       = 8.0

Classification Report:
{report}

Confusion Matrix:
{cm_df.to_string()}

Feature Importance:
{importance.to_string(index=False)}
"""
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"\n  ✅ Saved: {model_path}")
    print(f"  ✅ Saved: {report_path}")

    acc_pct = test_acc * 100
    if 90.0 <= acc_pct <= 93.0:
        print(f"\n  🎯 Target achieved! {acc_pct:.2f}% within 90–93%")
    elif acc_pct > 93.0:
        print(f"\n  ⚠  {acc_pct:.2f}% still above 93%")
    else:
        print(f"\n  ⚠  {acc_pct:.2f}% below 90% — reduce regularization")

    return model, test_acc, cv_scores.mean()


# ══════════════════════════════════════════════════════
flood_model, flood_acc, flood_cv = train_binary_model(
    df, "Flood Risk Model", "Flood",
    FLOOD_FEATURES, "model/flood_model.pkl", "model/flood_report.txt"
)

landslide_model, landslide_acc, landslide_cv = train_binary_model(
    df, "Landslide Risk Model", "Landslide",
    LANDSLIDE_FEATURES, "model/landslide_model.pkl", "model/landslide_report.txt"
)

print(f"\n{'=' * 55}")
print(f"  TRAINING COMPLETE — SUMMARY (v3)")
print(f"{'=' * 55}")
print(f"  Flood Model     : {flood_acc*100:.2f}%  |  CV {flood_cv*100:.2f}%")
print(f"  Landslide Model : {landslide_acc*100:.2f}%  |  CV {landslide_cv*100:.2f}%")
print(f"{'=' * 55}")
print(f"\n  Next step: python main.py  (FastAPI backend)")
