import pandas as pd
import numpy as np

DATASET = "gampaha_unosat_dataset.csv"

print("=" * 70)
print("SURAKSHA LANKA — DATASET AUDIT")
print("=" * 70)

# ---------------------------------------------------------
# 1. LOAD DATASET
# ---------------------------------------------------------

df = pd.read_csv(DATASET)

print("\n[1] DATASET SIZE")
print("-" * 50)
print(f"Rows    : {len(df)}")
print(f"Columns : {len(df.columns)}")

# ---------------------------------------------------------
# 2. COLUMN INFORMATION
# ---------------------------------------------------------

print("\n[2] COLUMNS")
print("-" * 50)

for i, col in enumerate(df.columns, 1):
    print(f"{i:2}. {col}")

# ---------------------------------------------------------
# 3. DATA TYPES
# ---------------------------------------------------------

print("\n[3] DATA TYPES")
print("-" * 50)

print(df.dtypes)

# ---------------------------------------------------------
# 4. FIRST 5 ROWS
# ---------------------------------------------------------

print("\n[4] SAMPLE DATA")
print("-" * 50)

print(df.head().to_string())

# ---------------------------------------------------------
# 5. MISSING VALUES
# ---------------------------------------------------------

print("\n[5] MISSING VALUES")
print("-" * 50)

missing = df.isnull().sum()

missing_df = pd.DataFrame({
    "column": missing.index,
    "missing_count": missing.values,
    "missing_percent": (
        missing.values / len(df) * 100
    ).round(2)
})

print(
    missing_df[
        missing_df["missing_count"] > 0
    ].to_string(index=False)
)

# ---------------------------------------------------------
# 6. DUPLICATES
# ---------------------------------------------------------

print("\n[6] DUPLICATES")
print("-" * 50)

duplicates = df.duplicated().sum()

print(f"Duplicate rows : {duplicates}")

# ---------------------------------------------------------
# 7. RISK LABEL DISTRIBUTION
# ---------------------------------------------------------

print("\n[7] RISK LABEL DISTRIBUTION")
print("-" * 50)

if "risk_label" in df.columns:

    label_counts = df["risk_label"].value_counts(dropna=False)

    print(label_counts)

    print("\nPercentages:")

    print(
        (df["risk_label"]
         .value_counts(normalize=True, dropna=False) * 100)
        .round(2)
    )

else:
    print("WARNING: risk_label column NOT FOUND")

# ---------------------------------------------------------
# 8. UNOSAT LABEL DISTRIBUTION
# ---------------------------------------------------------

print("\n[8] UNOSAT LABEL COLUMNS")
print("-" * 50)

unosat_columns = [
    "unosat_flood",
    "unosat_water",
    "unosat_landslide",
    "label_source"
]

for col in unosat_columns:

    if col in df.columns:

        print(f"\n{col}")

        print(df[col].value_counts(dropna=False))

# ---------------------------------------------------------
# 9. NUMERIC SUMMARY
# ---------------------------------------------------------

print("\n[9] NUMERIC FEATURE SUMMARY")
print("-" * 50)

numeric_cols = df.select_dtypes(
    include=np.number
).columns

print(
    df[numeric_cols]
    .describe()
    .T
    .to_string()
)

# ---------------------------------------------------------
# 10. CATEGORICAL FEATURES
# ---------------------------------------------------------

print("\n[10] CATEGORICAL FEATURES")
print("-" * 50)

categorical_cols = df.select_dtypes(
    exclude=np.number
).columns

for col in categorical_cols:

    print(f"\n--- {col} ---")

    unique_values = df[col].value_counts(
        dropna=False
    )

    print(unique_values.head(20))

# ---------------------------------------------------------
# 11. LATITUDE / LONGITUDE RANGE
# ---------------------------------------------------------

print("\n[11] GEOGRAPHIC RANGE")
print("-" * 50)

for col in ["latitude", "longitude"]:

    if col in df.columns:

        print(
            f"{col}: "
            f"min={df[col].min()}, "
            f"max={df[col].max()}"
        )

# ---------------------------------------------------------
# 12. LANDSLIDE ROWS
# ---------------------------------------------------------

print("\n[12] LANDSLIDE RECORDS")
print("-" * 50)

if "risk_label" in df.columns:

    landslide = df[
        df["risk_label"]
        .astype(str)
        .str.lower()
        .eq("landslide")
    ]

    print(f"Landslide rows : {len(landslide)}")

    if len(landslide) > 0:

        print("\nSample Landslide records:")

        print(
            landslide.head(10)
            .to_string(index=False)
        )

# ---------------------------------------------------------
# 13. FLOOD ROWS
# ---------------------------------------------------------

print("\n[13] FLOOD RECORDS")
print("-" * 50)

if "risk_label" in df.columns:

    flood = df[
        df["risk_label"]
        .astype(str)
        .str.lower()
        .eq("flood")
    ]

    print(f"Flood rows : {len(flood)}")

    if len(flood) > 0:

        print("\nSample Flood records:")

        print(
            flood.head(10)
            .to_string(index=False)
        )

# ---------------------------------------------------------
# 14. NO RISK ROWS
# ---------------------------------------------------------

print("\n[14] NO-RISK RECORDS")
print("-" * 50)

if "risk_label" in df.columns:

    no_risk = df[
        df["risk_label"]
        .astype(str)
        .str.lower()
        .eq("no risk")
    ]

    print(f"No Risk rows : {len(no_risk)}")

# ---------------------------------------------------------
# 15. FEATURE CORRELATION
# ---------------------------------------------------------

print("\n[15] NUMERIC CORRELATION WITH LABEL")
print("-" * 50)

if "risk_label" in df.columns:

    temp = df.copy()

    temp["label_binary"] = (
        temp["risk_label"]
        .astype(str)
        .str.lower()
        .eq("landslide")
        .astype(int)
    )

    numeric = temp.select_dtypes(
        include=np.number
    )

    correlation = (
        numeric.corr()["label_binary"]
        .sort_values(ascending=False)
    )

    print(correlation)

# ---------------------------------------------------------
# COMPLETE
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)