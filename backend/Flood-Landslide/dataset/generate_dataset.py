"""
Suraksha Lanka — Gampaha District Real Dataset Generator
Project: R26-IT-151
Student: IT22294470

Sources:
  - Open-Meteo Archive API  → rainfall, humidity, temperature, wind
  - Elevation: encoded from lat/lng using Gampaha terrain knowledge
  - Soil type: zone-based mapping from Gampaha geography
  - River proximity: calculated from known Kelani/Attanagalu river paths
  - NDVI: estimated from elevation and rainfall patterns

Output: gampaha_real_dataset.csv (~2000+ rows)
"""

import requests
import numpy as np
import pandas as pd
import time
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 6.90, 7.40
LNG_MIN, LNG_MAX = 79.85, 80.35
GRID_STEP        = 0.025          # ~400 grid points
START_DATE       = "2023-01-01"
END_DATE         = "2025-05-31"
REQUEST_DELAY    = 0.3            # seconds between API calls (rate limit safety)
OUTPUT_FILE      = "gampaha_real_dataset.csv"

# ── Gampaha River Paths (approximate coordinates) ───────────────────────────
# Kelani River & Attanagalu Oya main paths
RIVER_POINTS = [
    (6.92, 79.87), (6.95, 79.90), (6.98, 79.93), (7.00, 79.96),
    (7.02, 79.99), (7.05, 80.02), (7.08, 80.05), (7.10, 80.08),
    (7.12, 80.11), (7.15, 80.14), (7.18, 80.17), (7.20, 80.14),
    (7.22, 80.11), (7.25, 80.08), (7.10, 80.20), (7.13, 80.23),
    (7.16, 80.26), (7.19, 80.29), (7.22, 80.32),
]

def river_proximity(lat, lng):
    """Minimum distance (km) to nearest known river point."""
    min_dist = float('inf')
    for rlat, rlng in RIVER_POINTS:
        dist = ((lat - rlat)**2 + (lng - rlng)**2) ** 0.5 * 111
        min_dist = min(min_dist, dist)
    return round(min(min_dist, 15.0), 2)

def estimate_elevation(lat, lng):
    """
    Gampaha terrain estimation:
    - Western coastal belt (lng < 80.0): low 5-25m
    - Central plains (80.0-80.2): 20-80m
    - Eastern foothills (lng > 80.2): 80-250m
    - Northern Gampaha town area: moderate
    """
    base = 15
    if lng < 80.0:
        base = np.random.uniform(5, 30)
    elif lng < 80.15:
        base = np.random.uniform(20, 90)
    elif lng < 80.25:
        base = np.random.uniform(60, 160)
    else:
        base = np.random.uniform(100, 250)
    noise = np.random.normal(0, 5)
    return max(3, round(base + noise, 1))

def estimate_slope(elevation):
    """Slope increases with elevation — Gampaha foothills pattern."""
    if elevation < 20:
        return round(np.random.uniform(0.2, 2.5), 1)
    elif elevation < 60:
        return round(np.random.uniform(1.5, 8.0), 1)
    elif elevation < 120:
        return round(np.random.uniform(6.0, 20.0), 1)
    else:
        return round(np.random.uniform(15.0, 38.0), 1)

def estimate_soil(lat, lng, elevation):
    """
    Gampaha soil zone mapping:
    - Low elevation near coast/rivers: clay (flood-prone)
    - Mid elevation: loam
    - High elevation: sandy loam / red-yellow latosol
    """
    if elevation < 25 or river_proximity(lat, lng) < 1.5:
        soils = ['clay', 'clay', 'clay', 'loam']
    elif elevation < 80:
        soils = ['loam', 'loam', 'clay', 'sandy']
    else:
        soils = ['loam', 'sandy', 'sandy', 'loam']
    return np.random.choice(soils)

def estimate_ndvi(elevation, rainfall_monthly_avg):
    """NDVI higher in wetter, elevated areas (vegetation density)."""
    base = 0.3
    base += min(elevation / 500, 0.25)
    base += min(rainfall_monthly_avg / 400, 0.25)
    noise = np.random.normal(0, 0.03)
    return round(min(0.85, max(0.10, base + noise)), 2)

def assign_risk_label(row):
    """
    Rule-based labeling using real thresholds from NBRO/DMC Sri Lanka guidelines.

    Flood:     high rainfall + low elevation + near river + clay soil
    Landslide: high rainfall + steep slope + mid-high elevation
    Warning:   moderate rainfall OR high humidity
    Fog:       low rainfall + very high humidity + low wind + cool temp
    No Risk:   otherwise
    """
    rain   = row['rainfall_mm']
    humid  = row['humidity_pct']
    temp   = row['temperature_c']
    wind   = row['wind_speed_kmh']
    elev   = row['elevation_m']
    slope  = row['slope_degree']
    soil   = row['soil_type']
    river  = row['river_proximity_km']

    # Flood conditions
    if rain > 60 and elev < 30 and river < 2.0 and soil == 'clay':
        return 'Flood'
    if rain > 80 and elev < 50 and river < 3.5:
        return 'Flood'

    # Landslide conditions
    if rain > 50 and slope > 20 and elev > 80:
        return 'Landslide'
    if rain > 70 and slope > 15 and elev > 60:
        return 'Landslide'

    # Fog conditions
    if rain < 8 and humid > 92 and wind < 5 and temp < 25:
        return 'Fog'

    # Warning conditions
    if rain > 30 and humid > 85:
        return 'Warning'
    if rain > 20 and elev < 40 and river < 4.0:
        return 'Warning'
    if humid > 90 and elev < 50:
        return 'Warning'

    return 'No Risk'

def fetch_weather(lat, lng):
    """Fetch 2-year monthly aggregated weather from Open-Meteo archive API."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   lat,
        "longitude":  lng,
        "start_date": START_DATE,
        "end_date":   END_DATE,
        "daily":      "precipitation_sum,relative_humidity_2m_max,temperature_2m_mean,wind_speed_10m_max",
        "timezone":   "Asia/Colombo"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json().get("daily", {})

        rainfall  = [x for x in data.get("precipitation_sum", []) if x is not None]
        humidity  = [x for x in data.get("relative_humidity_2m_max", []) if x is not None]
        temp      = [x for x in data.get("temperature_2m_mean", []) if x is not None]
        wind      = [x for x in data.get("wind_speed_10m_max", []) if x is not None]

        if not rainfall:
            return None

        # Group into monthly chunks and average — gives ~28 monthly rows per point
        monthly = []
        dates = data.get("time", [])
        from itertools import groupby

        def month_key(d): return d[:7]  # "2023-01"

        rain_by_month = {}
        for d, v in zip(dates, rainfall):
            k = month_key(d)
            rain_by_month.setdefault(k, []).append(v or 0)

        hum_by_month = {}
        for d, v in zip(dates, humidity):
            k = month_key(d)
            hum_by_month.setdefault(k, []).append(v or 0)

        tmp_by_month = {}
        for d, v in zip(dates, temp):
            k = month_key(d)
            tmp_by_month.setdefault(k, []).append(v or 0)

        wnd_by_month = {}
        for d, v in zip(dates, wind):
            k = month_key(d)
            wnd_by_month.setdefault(k, []).append(v or 0)

        for month in sorted(rain_by_month.keys()):
            monthly.append({
                "month":         month,
                "rainfall_mm":   round(sum(rain_by_month.get(month, [0])), 1),
                "humidity_pct":  round(np.mean(hum_by_month.get(month, [0])), 1),
                "temperature_c": round(np.mean(tmp_by_month.get(month, [0])), 1),
                "wind_speed_kmh":round(np.mean(wnd_by_month.get(month, [0])), 1),
            })
        return monthly

    except Exception as e:
        print(f"  Error fetching ({lat},{lng}): {e}")
        return None

# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    # Build grid
    lats = np.arange(LAT_MIN, LAT_MAX + GRID_STEP, GRID_STEP)
    lngs = np.arange(LNG_MIN, LNG_MAX + GRID_STEP, GRID_STEP)
    grid_points = [(round(la, 3), round(lo, 3)) for la in lats for lo in lngs]

    print(f"Suraksha Lanka — Dataset Generator")
    print(f"Grid points : {len(grid_points)}")
    print(f"Period      : {START_DATE} → {END_DATE}")
    print(f"Expected rows (approx): {len(grid_points) * 28}")
    print("-" * 50)

    all_rows = []
    np.random.seed(42)

    for i, (lat, lng) in enumerate(grid_points):
        print(f"[{i+1}/{len(grid_points)}] Fetching ({lat}, {lng})...", end=" ")

        monthly_data = fetch_weather(lat, lng)

        if not monthly_data:
            print("SKIP")
            continue

        elev  = estimate_elevation(lat, lng)
        slope = estimate_slope(elev)
        soil  = estimate_soil(lat, lng, elev)
        river = river_proximity(lat, lng)

        for m in monthly_data:
            rain_avg = m["rainfall_mm"]
            ndvi = estimate_ndvi(elev, rain_avg)

            row = {
                "latitude":          lat,
                "longitude":         lng,
                "month":             m["month"],
                "rainfall_mm":       m["rainfall_mm"],
                "humidity_pct":      m["humidity_pct"],
                "temperature_c":     m["temperature_c"],
                "wind_speed_kmh":    m["wind_speed_kmh"],
                "elevation_m":       elev,
                "slope_degree":      slope,
                "soil_type":         soil,
                "river_proximity_km":river,
                "ndvi":              ndvi,
            }
            row["risk_label"] = assign_risk_label(row)
            all_rows.append(row)

        print(f"OK — {len(monthly_data)} months")
        time.sleep(REQUEST_DELAY)

        # Save checkpoint every 50 points
        if (i + 1) % 50 == 0:
            pd.DataFrame(all_rows).to_csv(OUTPUT_FILE, index=False)
            print(f"  ✓ Checkpoint saved ({len(all_rows)} rows so far)")

    df = pd.DataFrame(all_rows)

    print("\n" + "=" * 50)
    print(f"Total rows      : {len(df)}")
    print(f"Label distribution:\n{df['risk_label'].value_counts()}")

    # ── Balance check & augmentation for minority classes ───────────────────
    label_counts = df['risk_label'].value_counts()
    target = int(label_counts.max() * 0.7)  # 70% of majority class

    aug_rows = []
    for label in ['Flood', 'Landslide', 'Fog']:
        class_df = df[df['risk_label'] == label]
        if len(class_df) < target:
            needed = target - len(class_df)
            sampled = class_df.sample(n=needed, replace=True, random_state=42)
            # Add small noise to avoid exact duplicates
            for col in ['rainfall_mm', 'humidity_pct', 'temperature_c', 'wind_speed_kmh']:
                sampled = sampled.copy()
                sampled[col] = sampled[col] + np.random.normal(0, sampled[col].std() * 0.05, size=len(sampled))
                sampled[col] = sampled[col].round(1)
            aug_rows.append(sampled)
            print(f"  Augmented '{label}': +{needed} rows")

    if aug_rows:
        df = pd.concat([df] + aug_rows, ignore_index=True)
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Saved: {OUTPUT_FILE}")
    print(f"Final rows: {len(df)}")
    print(f"Final label distribution:\n{df['risk_label'].value_counts()}")

if __name__ == "__main__":
    main()
