"""
Suraksha Lanka — Daily UNOSAT Flood Event Combiner

Adds event-specific UNOSAT flood labels to gampaha_daily_flood_dataset.csv.
The UNOSAT product is a composite event extent, so matched rows are described
as `unosat_event_window`, not as exact day-by-day satellite observations.

Run from: backend/Flood-Landslide/dataset
"""

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box


os.environ["SHAPE_RESTORE_SHX"] = "YES"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
SHP_DIR = PROJECT_DIR / "shp"

INPUT_CSV = BASE_DIR / "gampaha_daily_flood_dataset.csv"
OUTPUT_CSV = BASE_DIR / "gampaha_daily_unosat_dataset.csv"
FLOOD_SHP = (
    SHP_DIR
    / "Multisensors_20251126_20251202_FloodExtent_SriLanka.shp"
)
WATER_SHP = (
    SHP_DIR
    / "Multisensors_20251126_20251202_WaterExtent_SriLanka.shp"
)

TARGET_CRS = "EPSG:4326"
EVENT_START = pd.Timestamp("2025-11-26")
EVENT_END = pd.Timestamp("2025-12-02")
STUDY_BBOX = box(79.85, 6.90, 80.35, 7.40)


def load_wgs84(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing shapefile: {path}")
    frame = gpd.read_file(path, engine="pyogrio")
    if frame.empty:
        raise RuntimeError(f"Shapefile contains no geometries: {path}")
    if frame.crs is None:
        # Verified source bounds are Sri Lankan longitude/latitude coordinates.
        frame = frame.set_crs(TARGET_CRS)
    else:
        frame = frame.to_crs(TARGET_CRS)
    return frame.clip(STUDY_BBOX)


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing daily dataset: {INPUT_CSV}")

    print("=" * 64)
    print("Suraksha Lanka — Daily UNOSAT Flood Event Combiner")
    print("=" * 64)

    flood = load_wgs84(FLOOD_SHP)
    water = load_wgs84(WATER_SHP)
    print(f"Flood geometries in study bbox : {len(flood)}")
    print(f"Water geometries in study bbox : {len(water)}")

    dataset = pd.read_csv(INPUT_CSV)
    dataset["date"] = pd.to_datetime(dataset["date"], errors="raise")
    print(f"Input rows                    : {len(dataset)}")

    # Spatial matching is required only once for every unique coordinate.
    locations = (
        dataset[["latitude", "longitude"]]
        .drop_duplicates()
        .sort_values(["latitude", "longitude"])
        .reset_index(drop=True)
    )
    location_geo = gpd.GeoDataFrame(
        locations,
        geometry=[
            Point(longitude, latitude)
            for latitude, longitude in zip(
                locations["latitude"],
                locations["longitude"],
            )
        ],
        crs=TARGET_CRS,
    )

    flood_union = flood.geometry.union_all()
    water_union = water.geometry.union_all()
    location_geo["unosat_flood_location"] = (
        location_geo.geometry.within(flood_union)
    )
    location_geo["unosat_water_location"] = (
        location_geo.geometry.within(water_union)
    )

    flags = location_geo.drop(columns="geometry")
    output = dataset.merge(
        flags,
        on=["latitude", "longitude"],
        how="left",
        validate="many_to_one",
    )

    event_date = output["date"].between(EVENT_START, EVENT_END)
    satellite_positive = event_date & output["unosat_flood_location"]

    # Preserve weak rules elsewhere. Only positive flood extent observations
    # inside the mapped event window receive satellite provenance.
    output.loc[satellite_positive, "flood_label"] = 1
    output.loc[satellite_positive, "label_source"] = "unosat_event_window"

    if output.duplicated(["latitude", "longitude", "date"]).any():
        raise RuntimeError("Duplicate coordinate-date rows after spatial join")
    if output.isna().any().any():
        raise RuntimeError("Missing values detected after spatial join")
    invalid = output[
        output["label_source"].eq("unosat_event_window")
        & ~output["date"].between(EVENT_START, EVENT_END)
    ]
    if len(invalid):
        raise RuntimeError("UNOSAT label found outside the mapped event window")
    if satellite_positive.sum() == 0:
        raise RuntimeError(
            "No daily locations matched the UNOSAT flood extent. "
            "Check coordinate coverage and shapefile."
        )

    output["date"] = output["date"].dt.strftime("%Y-%m-%d")
    output.to_csv(OUTPUT_CSV, index=False)

    satellite_rows = output[
        output["label_source"].eq("unosat_event_window")
    ]
    print(f"Unique daily locations        : {len(locations)}")
    print(
        "UNOSAT flood locations       : "
        f"{int(location_geo['unosat_flood_location'].sum())}"
    )
    print(f"Rows in Ditwah event window   : {int(event_date.sum())}")
    print(f"UNOSAT-positive daily rows    : {len(satellite_rows)}")
    print(
        "UNOSAT-positive locations     : "
        f"{len(satellite_rows[['latitude', 'longitude']].drop_duplicates())}"
    )
    print("Final flood-label counts:")
    print(output["flood_label"].value_counts().sort_index())
    print("Final label sources:")
    print(output["label_source"].value_counts())
    print(f"Saved                         : {OUTPUT_CSV.name}")
    print("=" * 64)


if __name__ == "__main__":
    main()
