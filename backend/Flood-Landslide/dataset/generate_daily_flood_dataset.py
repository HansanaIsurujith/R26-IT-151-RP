"""
Suraksha Lanka — Daily Flood Dataset Builder

Purpose
-------
Build a daily, location-specific flood-risk research dataset from the 154
validated coordinates already present in gampaha_real_dataset.csv.

Real/modelled weather source: Open-Meteo Historical Weather API
Environmental columns: reused from the existing deterministic prototype data
Target before UNOSAT integration: explicitly marked weak_rule

Run from: backend/Flood-Landslide/dataset
Output  : gampaha_daily_flood_dataset.csv
"""

from pathlib import Path
import time

import numpy as np
import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parent
SOURCE_DATASET = BASE_DIR / "gampaha_real_dataset.csv"
OUTPUT_DATASET = BASE_DIR / "gampaha_daily_flood_dataset.csv"

START_DATE = "2023-01-01"
END_DATE = "2025-12-31"
REQUEST_DELAY_SECONDS = 0.35
MAX_RETRIES = 3

WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

REQUIRED_SOURCE_COLUMNS = [
    "latitude",
    "longitude",
    "elevation_m",
    "slope_degree",
    "soil_type",
    "river_proximity_km",
]


def fetch_daily_weather(latitude, longitude):
    """Return daily weather for one coordinate, with bounded retries."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": (
            "precipitation_sum,relative_humidity_2m_max,"
            "temperature_2m_mean,wind_speed_10m_max"
        ),
        "timezone": "Asia/Colombo",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                WEATHER_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            daily = response.json().get("daily", {})

            frame = pd.DataFrame({
                "date": daily["time"],
                "today_rainfall_mm": daily["precipitation_sum"],
                "humidity_pct": daily["relative_humidity_2m_max"],
                "temperature_c": daily["temperature_2m_mean"],
                "wind_speed_kmh": daily["wind_speed_10m_max"],
            })
            if frame.empty:
                raise ValueError("Open-Meteo returned no daily records")

            frame["date"] = pd.to_datetime(frame["date"])
            numeric = [
                "today_rainfall_mm",
                "humidity_pct",
                "temperature_c",
                "wind_speed_kmh",
            ]
            frame[numeric] = frame[numeric].apply(
                pd.to_numeric,
                errors="coerce",
            )
            frame["today_rainfall_mm"] = frame["today_rainfall_mm"].fillna(0)
            frame[["humidity_pct", "temperature_c", "wind_speed_kmh"]] = (
                frame[["humidity_pct", "temperature_c", "wind_speed_kmh"]]
                .interpolate(limit_direction="both")
            )
            if frame[numeric].isna().any().any():
                raise ValueError("Unresolved missing weather values")
            return frame.sort_values("date").reset_index(drop=True)

        except (requests.RequestException, KeyError, ValueError) as error:
            print(f"    Attempt {attempt}/{MAX_RETRIES} failed: {error}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    return None


def add_rolling_rainfall(frame):
    """Create antecedent rainfall features using only current/past dates."""
    rain = frame["today_rainfall_mm"]
    frame["rain_3d_mm"] = rain.rolling(3, min_periods=1).sum()
    frame["rain_7d_mm"] = rain.rolling(7, min_periods=1).sum()
    frame["rain_30d_mm"] = rain.rolling(30, min_periods=1).sum()
    return frame


def assign_weak_label(row):
    """
    Prototype weak-supervision rule, not observed flood ground truth.

    It combines daily/antecedent rain with low terrain and river proximity.
    UNOSAT event matching must later override confirmed event rows and change
    label_source to unosat_satellite.
    """
    today = row["today_rainfall_mm"]
    rain_3d = row["rain_3d_mm"]
    rain_7d = row["rain_7d_mm"]
    elevation = row["elevation_m"]
    river = row["river_proximity_km"]
    soil = row["soil_type"]

    high_antecedent_rain = (
        today >= 50
        or rain_3d >= 100
        or rain_7d >= 150
    )
    exposed_location = elevation < 50 and river < 3.5

    clay_lowland_event = (
        today >= 35
        and elevation < 30
        and river < 2.0
        and soil == "clay"
    )

    return int(
        (high_antecedent_rain and exposed_location)
        or clay_lowland_event
    )


def validate_dataset(frame, expected_locations):
    required = [
        "latitude",
        "longitude",
        "date",
        "today_rainfall_mm",
        "rain_3d_mm",
        "rain_7d_mm",
        "rain_30d_mm",
        "humidity_pct",
        "temperature_c",
        "wind_speed_kmh",
        "elevation_m",
        "slope_degree",
        "soil_type",
        "river_proximity_km",
        "flood_label",
        "label_source",
    ]
    missing_columns = sorted(set(required) - set(frame.columns))
    if missing_columns:
        raise RuntimeError(f"Missing output columns: {missing_columns}")
    if frame[required].isna().any().any():
        raise RuntimeError("Daily dataset contains missing values")
    if frame.duplicated(["latitude", "longitude", "date"]).any():
        raise RuntimeError("Duplicate coordinate-date records detected")

    actual_locations = frame[["latitude", "longitude"]].drop_duplicates()
    if len(actual_locations) != expected_locations:
        print(
            f"⚠ Completed {len(actual_locations)}/{expected_locations} locations; "
            "failed locations are listed above."
        )


def main():
    if not SOURCE_DATASET.exists():
        raise FileNotFoundError(f"Missing source dataset: {SOURCE_DATASET}")

    source = pd.read_csv(SOURCE_DATASET)
    missing = sorted(set(REQUIRED_SOURCE_COLUMNS) - set(source.columns))
    if missing:
        raise RuntimeError(f"Source dataset missing columns: {missing}")

    locations = (
        source[REQUIRED_SOURCE_COLUMNS]
        .drop_duplicates(["latitude", "longitude"])
        .sort_values(["latitude", "longitude"])
        .reset_index(drop=True)
    )
    print("=" * 64)
    print("Suraksha Lanka — Daily Flood Dataset Builder")
    print("=" * 64)
    print(f"Locations : {len(locations)}")
    print(f"Period    : {START_DATE} -> {END_DATE}")
    print("Labels    : weak_rule until UNOSAT integration")

    completed = []
    for number, location in locations.iterrows():
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
        print(
            f"[{number + 1}/{len(locations)}] "
            f"({latitude:.3f}, {longitude:.3f})"
        )

        weather = fetch_daily_weather(latitude, longitude)
        if weather is None:
            print("    SKIPPED after retries")
            continue

        weather = add_rolling_rainfall(weather)
        weather["latitude"] = latitude
        weather["longitude"] = longitude
        weather["elevation_m"] = float(location["elevation_m"])
        weather["slope_degree"] = float(location["slope_degree"])
        weather["soil_type"] = str(location["soil_type"])
        weather["river_proximity_km"] = float(
            location["river_proximity_km"]
        )
        weather["flood_label"] = weather.apply(assign_weak_label, axis=1)
        weather["label_source"] = "weak_rule"
        completed.append(weather)
        print(f"    OK: {len(weather)} daily rows")
        time.sleep(REQUEST_DELAY_SECONDS)

        if len(completed) % 20 == 0:
            checkpoint = pd.concat(completed, ignore_index=True)
            checkpoint.to_csv(OUTPUT_DATASET, index=False)
            print(f"    Checkpoint saved: {len(checkpoint)} rows")

    if not completed:
        raise RuntimeError("No locations were downloaded")

    dataset = pd.concat(completed, ignore_index=True)
    dataset["date"] = dataset["date"].dt.strftime("%Y-%m-%d")
    dataset = dataset.sort_values(
        ["latitude", "longitude", "date"]
    ).reset_index(drop=True)
    validate_dataset(dataset, len(locations))
    dataset.to_csv(OUTPUT_DATASET, index=False)

    print("\n" + "=" * 64)
    print(f"Saved       : {OUTPUT_DATASET.name}")
    print(f"Rows        : {len(dataset)}")
    print(
        "Locations   : "
        f"{len(dataset[['latitude', 'longitude']].drop_duplicates())}"
    )
    print(f"Date range  : {dataset['date'].min()} -> {dataset['date'].max()}")
    print("Label counts:")
    print(dataset["flood_label"].value_counts().sort_index())
    print("Label sources:")
    print(dataset["label_source"].value_counts())
    print("=" * 64)


if __name__ == "__main__":
    main()
