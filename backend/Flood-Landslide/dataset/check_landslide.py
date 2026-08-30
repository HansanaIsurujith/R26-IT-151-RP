import pandas as pd

# Master dataset
FILE = "gampaha_master_nasa_dataset.csv"

df = pd.read_csv(FILE)

print("=" * 70)
print("NASA LANDSLIDE RECORD AUDIT")
print("=" * 70)

# 1. Distribution
print("\n=== LANDSLIDE LABEL DISTRIBUTION ===")
print(df["landslide_label"].value_counts())

print("\n=== PERCENTAGE ===")
print(
    df["landslide_label"]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)

# 2. Get landslide records only
landslides = df[df["landslide_label"] == 1].copy()

print("\n" + "=" * 70)
print(f"TOTAL LANDSLIDE RECORDS: {len(landslides)}")
print("=" * 70)

# 3. Show important NASA-related information
columns = [
    "latitude",
    "longitude",
    "month",
    "rainfall_mm",
    "humidity_pct",
    "temperature_c",
    "elevation_m",
    "slope_degree",
    "soil_type",
    "river_proximity_km",
    "ndvi",
    "nasa_landslide",
    "nasa_nearest_event_km",
    "nasa_trigger",
    "landslide_label"
]

# Only show columns that actually exist
available_columns = [c for c in columns if c in landslides.columns]

print("\n=== LANDSLIDE RECORDS ===\n")

print(
    landslides[available_columns]
    .to_string(index=False)
)

# 4. Geographic range
print("\n" + "=" * 70)
print("LANDSLIDE LOCATION RANGE")
print("=" * 70)

print(
    f"Latitude  : {landslides['latitude'].min()} → "
    f"{landslides['latitude'].max()}"
)

print(
    f"Longitude : {landslides['longitude'].min()} → "
    f"{landslides['longitude'].max()}"
)

# 5. NASA trigger distribution
if "nasa_trigger" in landslides.columns:
    print("\n=== NASA TRIGGER DISTRIBUTION ===")
    print(
        landslides["nasa_trigger"]
        .fillna("None")
        .value_counts()
    )

# 6. Distance distribution
if "nasa_nearest_event_km" in landslides.columns:
    print("\n=== NASA EVENT DISTANCE ===")

    print(
        landslides["nasa_nearest_event_km"]
        .describe()
    )

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)