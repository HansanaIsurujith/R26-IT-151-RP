"""
Suraksha Lanka — UNOSAT SHP + Dataset Combiner
Project : R26-IT-151
Student : IT22294470

What this does:
  1. Loads UNOSAT flood and water SHP files (event imagery, Nov/Dec 2025)
  2. Loads our generated gampaha_real_dataset.csv
  3. Spatial join — checks which grid points fall inside real flood/landslide zones
  4. Overrides risk_label with satellite-verified labels
  5. Saves enhanced dataset: gampaha_unosat_dataset.csv

Requirements:
  pip install geopandas pandas numpy shapely pyproj fiona
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
SHP_FOLDER = PROJECT_DIR / "shp"

# Auto-restore missing .shx files
import os
os.environ['SHAPE_RESTORE_SHX'] = 'YES'

FLOOD_SHP = SHP_FOLDER / "Multisensors_20251126_20251202_FloodExtent_SriLanka.shp"
WATER_SHP = SHP_FOLDER / "Multisensors_20251126_20251202_WaterExtent_SriLanka.shp"

DATASET_CSV    = "gampaha_real_dataset.csv"
OUTPUT_CSV     = "gampaha_unosat_dataset_newest.csv"

# ── Step 1: Load UNOSAT SHP Files ─────────────────────────────────────────────
print("=" * 55)
print("  Suraksha Lanka — UNOSAT SHP Combiner")
print("=" * 55)

print("\n[1/5] Loading UNOSAT SHP files...")

flood_gdf = gpd.read_file(
    FLOOD_SHP,
    engine="pyogrio"
)

water_gdf = gpd.read_file(
    WATER_SHP,
    engine="pyogrio"
)

# The source files contain longitude/latitude coordinates,
# but their CRS metadata is missing.
if flood_gdf.crs is None:
    flood_gdf = flood_gdf.set_crs("EPSG:4326")

if water_gdf.crs is None:
    water_gdf = water_gdf.set_crs("EPSG:4326")

print(f"  FloodExtent    : {len(flood_gdf)} polygons | CRS: {flood_gdf.crs}")
print(f"  WaterExtent    : {len(water_gdf)} polygons | CRS: {water_gdf.crs}")

# ── Step 2: Reproject all to WGS84 (EPSG:4326) ────────────────────────────────
print("\n[2/5] Reprojecting to WGS84...")

TARGET_CRS = "EPSG:4326"
flood_gdf     = flood_gdf.to_crs(TARGET_CRS)
water_gdf     = water_gdf.to_crs(TARGET_CRS)

# Clip to Gampaha District bounding box only (speed up spatial join)
from shapely.geometry import box
GAMPAHA_BBOX = box(79.85, 6.90, 80.35, 7.40)

flood_gdf     = flood_gdf.clip(GAMPAHA_BBOX)
water_gdf     = water_gdf.clip(GAMPAHA_BBOX)

print(f"  FloodExtent    (Gampaha): {len(flood_gdf)} polygons")
print(f"  WaterExtent    (Gampaha): {len(water_gdf)} polygons")

# ── Step 3: Load Our Dataset ───────────────────────────────────────────────────
print(f"\n[3/5] Loading {DATASET_CSV}...")
df = pd.read_csv(DATASET_CSV)
print(f"  Rows   : {len(df)}")
print(f"  Labels : \n{df['risk_label'].value_counts()}")

# Convert to GeoDataFrame
gdf_points = gpd.GeoDataFrame(
    df,
    geometry=[Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])],
    crs=TARGET_CRS
)

# ── Step 4: Spatial Join ───────────────────────────────────────────────────────
print("\n[4/5] Running spatial joins...")

# --- Flood join ---
flood_union = flood_gdf.geometry.union_all()   # merge all flood polygons
water_union = water_gdf.geometry.union_all()

in_flood = gdf_points.geometry.within(flood_union)
in_water = gdf_points.geometry.within(water_union)

print(f"  Points in Flood zone     : {in_flood.sum()}")
print(f"  Points in Water zone     : {in_water.sum()}")

# ── Step 5: Override Labels with UNOSAT Data ───────────────────────────────────
print("\n[5/5] Overriding labels with UNOSAT satellite data...")

df_out = df.copy()

# unosat_flood / unosat_water / unosat_landslide describe the LOCATION
# (does this grid point sit inside the satellite-observed extent at all),
# independent of month. Keep these as location-level ground-truth flags --
# useful as model features -- but do NOT use them alone to override the
# monthly risk_label, or every month at that location gets mislabeled.
df_out['unosat_flood']     = in_flood.values
df_out['unosat_water']     = in_water.values
df_out['unosat_landslide'] = False
df_out['label_source']     = 'rule_based'   # default

# The satellite imagery for this SHP set was captured for Cyclone Ditwah,
# which occurred Nov 26 - Dec 2, 2025. Only rows whose `month` actually
# falls within that real event window may have their risk_label overridden
# with the satellite-observed outcome -- otherwise a location that flooded
# in Nov/Dec 2025 would incorrectly get "Flood" stamped onto e.g. its
# Jan 2023 (dry season) row too.
EVENT_MONTHS = ['2025-11', '2025-12']
event_month_mask = df_out['month'].isin(EVENT_MONTHS)

# WaterExtent can include permanent rivers/lakes. Only FloodExtent is used as
# a confirmed flood label; retain unosat_water as contextual metadata.
location_flood_mask     = df_out['unosat_flood']
flood_mask     = location_flood_mask & event_month_mask

df_out.loc[flood_mask,     'risk_label']    = 'Flood'
df_out.loc[flood_mask,     'label_source']  = 'unosat_satellite'

print(f"\n  Rows in event window ({'/'.join(EVENT_MONTHS)}) : {event_month_mask.sum()}")
print(f"  Of those, satellite-confirmed Flood     : {flood_mask.sum()}")

# Stats
unosat_count = (df_out['label_source'] == 'unosat_satellite').sum()
rule_count   = (df_out['label_source'] == 'rule_based').sum()

print(f"\n  Labels overridden by UNOSAT : {unosat_count}")
print(f"  Labels kept (rule-based)    : {rule_count}")
print(f"\n  Final label distribution:")
print(df_out['risk_label'].value_counts())

invalid_satellite_rows = df_out[
    (df_out['label_source'] == 'unosat_satellite')
    & ~df_out['month'].isin(EVENT_MONTHS)
]
if len(invalid_satellite_rows):
    raise RuntimeError("Satellite labels found outside the UNOSAT event months")
if flood_mask.sum() == 0:
    raise RuntimeError(
        "No event-matched flood rows found. Check dataset dates and SHP coverage."
    )

# ── Save ───────────────────────────────────────────────────────────────────────
df_out.to_csv(OUTPUT_CSV, index=False)

print("\n" + "=" * 55)
print(f"  ✅ Saved: {OUTPUT_CSV}")
print(f"  Total rows     : {len(df_out)}")
print(f"  UNOSAT-verified: {unosat_count} rows ({unosat_count/len(df_out)*100:.1f}%)")
print("=" * 55)
print("\n  Next step: Run train_xgboost.py with gampaha_unosat_dataset.csv")
