"""
Suraksha Lanka — UNOSAT SHP + Dataset Combiner
Project : R26-IT-151
Student : IT22294470

What this does:
  1. Loads UNOSAT Flood + Landslide SHP files (Cyclone Ditwah, Nov 2025)
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
import warnings
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────────
SHP_FOLDER   = r"C:\Users\King Hany\Documents\Coding Workspace\Research R26-IT-151\R26-IT-151-new\FL20251128LKA_SHP"

# Auto-restore missing .shx files
import os
os.environ['SHAPE_RESTORE_SHX'] = 'YES'

FLOOD_SHP      = SHP_FOLDER + r"\Multisensors_20251126_20251202_FloodExtent_SriLanka.shp"
WATER_SHP      = SHP_FOLDER + r"\Multisensors_20251126_20251202_WaterExtent_SriLanka.shp"
LANDSLIDE_SHP  = SHP_FOLDER + r"\S2_20251130_20251202_LandslideExtent.shp"
LANDSLIDE_ASS  = SHP_FOLDER + r"\S2_20251126_20251130_LandslideAssessment.shp"

DATASET_CSV    = "gampaha_real_dataset.csv"
OUTPUT_CSV     = "gampaha_unosat_dataset.csv"

# ── Step 1: Load UNOSAT SHP Files ─────────────────────────────────────────────
print("=" * 55)
print("  Suraksha Lanka — UNOSAT SHP Combiner")
print("=" * 55)

print("\n[1/5] Loading UNOSAT SHP files...")

flood_gdf     = gpd.read_file(FLOOD_SHP)
water_gdf     = gpd.read_file(WATER_SHP)
landslide_gdf = gpd.read_file(LANDSLIDE_SHP)
landslide_ass = gpd.read_file(LANDSLIDE_ASS)

print(f"  FloodExtent    : {len(flood_gdf)} polygons | CRS: {flood_gdf.crs}")
print(f"  WaterExtent    : {len(water_gdf)} polygons | CRS: {water_gdf.crs}")
print(f"  LandslideExtent: {len(landslide_gdf)} polygons | CRS: {landslide_gdf.crs}")
print(f"  LandslideAssess: {len(landslide_ass)} points  | CRS: {landslide_ass.crs}")

# ── Step 2: Reproject all to WGS84 (EPSG:4326) ────────────────────────────────
print("\n[2/5] Reprojecting to WGS84...")

TARGET_CRS = "EPSG:4326"
flood_gdf     = flood_gdf.to_crs(TARGET_CRS)
water_gdf     = water_gdf.to_crs(TARGET_CRS)
landslide_gdf = landslide_gdf.to_crs(TARGET_CRS)
landslide_ass = landslide_ass.to_crs(TARGET_CRS)

# Clip to Gampaha District bounding box only (speed up spatial join)
from shapely.geometry import box
GAMPAHA_BBOX = box(79.85, 6.90, 80.35, 7.40)

flood_gdf     = flood_gdf.clip(GAMPAHA_BBOX)
water_gdf     = water_gdf.clip(GAMPAHA_BBOX)
landslide_gdf = landslide_gdf.clip(GAMPAHA_BBOX)
landslide_ass = landslide_ass.clip(GAMPAHA_BBOX)

print(f"  FloodExtent    (Gampaha): {len(flood_gdf)} polygons")
print(f"  WaterExtent    (Gampaha): {len(water_gdf)} polygons")
print(f"  LandslideExtent(Gampaha): {len(landslide_gdf)} polygons")
print(f"  LandslideAssess(Gampaha): {len(landslide_ass)} points")

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

# --- Landslide join ---
if len(landslide_gdf) > 0:
    landslide_union = landslide_gdf.geometry.union_all()
    in_landslide = gdf_points.geometry.within(landslide_union)
else:
    in_landslide = pd.Series([False] * len(gdf_points))

# Assessment points — buffer 500m around each point
if len(landslide_ass) > 0:
    landslide_ass_proj = landslide_ass.to_crs("EPSG:32644")  # UTM for meter buffer
    landslide_ass_buf  = landslide_ass_proj.buffer(500).to_crs(TARGET_CRS)
    landslide_ass_union = landslide_ass_buf.union_all()
    in_landslide_ass = gdf_points.geometry.within(landslide_ass_union)
else:
    in_landslide_ass = pd.Series([False] * len(gdf_points))

print(f"  Points in Flood zone     : {in_flood.sum()}")
print(f"  Points in Water zone     : {in_water.sum()}")
print(f"  Points in Landslide zone : {in_landslide.sum()}")
print(f"  Points near Landslide ass: {in_landslide_ass.sum()}")

# ── Step 5: Override Labels with UNOSAT Data ───────────────────────────────────
print("\n[5/5] Overriding labels with UNOSAT satellite data...")

df_out = df.copy()
df_out['unosat_flood']     = in_flood.values
df_out['unosat_water']     = in_water.values
df_out['unosat_landslide'] = (in_landslide | in_landslide_ass).values
df_out['label_source']     = 'rule_based'   # default

# Override: Landslide first (more specific), then Flood
landslide_mask = df_out['unosat_landslide']
flood_mask     = df_out['unosat_flood'] | df_out['unosat_water']

df_out.loc[flood_mask,     'risk_label']    = 'Flood'
df_out.loc[flood_mask,     'label_source']  = 'unosat_satellite'
df_out.loc[landslide_mask, 'risk_label']    = 'Landslide'
df_out.loc[landslide_mask, 'label_source']  = 'unosat_satellite'

# Stats
unosat_count = (df_out['label_source'] == 'unosat_satellite').sum()
rule_count   = (df_out['label_source'] == 'rule_based').sum()

print(f"\n  Labels overridden by UNOSAT : {unosat_count}")
print(f"  Labels kept (rule-based)    : {rule_count}")
print(f"\n  Final label distribution:")
print(df_out['risk_label'].value_counts())

# ── Save ───────────────────────────────────────────────────────────────────────
df_out.to_csv(OUTPUT_CSV, index=False)

print("\n" + "=" * 55)
print(f"  ✅ Saved: {OUTPUT_CSV}")
print(f"  Total rows     : {len(df_out)}")
print(f"  UNOSAT-verified: {unosat_count} rows ({unosat_count/len(df_out)*100:.1f}%)")
print("=" * 55)
print("\n  Next step: Run train_xgboost.py with gampaha_unosat_dataset.csv")
