"""
Suraksha Lanka — Gampaha District Real Dataset Generator (FIXED v2)
Project: R26-IT-151
Student: IT22294470

FIXES in v2:
  - No Risk rule loosened (Gampaha wet zone reality)
  - Warning threshold tightened so No Risk gets proper share
  - Fog conditions adjusted
  - Augmentation targets balanced across all 5 classes

Sources:
  - Open-Meteo Archive API  → rainfall, humidity, temperature, wind (REAL)
  - Elevation               → Gampaha terrain zone estimation
  - Slope                   → derived from elevation
  - Soil type               → Gampaha geographic zone mapping
  - River proximity         → Kelani + Attanagalu Oya coordinates
  - NDVI                    → estimated from elevation + rainfall
  - Risk labels             → rule-based (NBRO/DMC Sri Lanka aligned)

Output: gampaha_real_dataset.csv
"""

import requests
import numpy as np
import pandas as pd
import time

# ── Config ─────────────────────────────────────────────────────────────────────
LAT_MIN, LAT_MAX = 6.90, 7.40
LNG_MIN, LNG_MAX = 79.85, 80.35
GRID_STEP        = 0.025
START_DATE       = "2023-01-01"
END_DATE         = "2025-05-31"
REQUEST_DELAY    = 0.3
OUTPUT_FILE      = "gampaha_real_dataset.csv"

# ── Gampaha River Paths ────────────────────────────────────────────────────────
# Kelani River & Attanagalu Oya approximate coordinates
RIVER_POINTS = [
    (6.92, 79.87), (6.95, 79.90), (6.98, 79.93), (7.00, 79.96),
    (7.02, 79.99), (7.05, 80.02), (7.08, 80.05), (7.10, 80.08),
    (7.12, 80.11), (7.15, 80.14), (7.18, 80.17), (7.20, 80.14),
    (7.22, 80.11), (7.25, 80.08), (7.10, 80.20), (7.13, 80.23),
    (7.16, 80.26), (7.19, 80.29), (7.22, 80.32),
]

def river_proximity(lat, lng):
    min_dist = float('inf')
    for rlat, rlng in RIVER_POINTS:
        dist = ((lat - rlat)**2 + (lng - rlng)**2) ** 0.5 * 111
        min_dist = min(min_dist, dist)
    return round(min(min_dist, 15.0), 2)

def estimate_elevation(lat, lng):
    """
    Gampaha terrain zones:
    - Western coastal belt (lng < 80.0)  : 5–30m
    - Central plains (80.0–80.2)         : 20–90m
    - Eastern foothills (lng > 80.2)     : 80–250m
    """
    if lng < 80.0:
        base = np.random.uniform(5, 30)
    elif lng < 80.15:
        base = np.random.uniform(20, 90)
    elif lng < 80.25:
        base = np.random.uniform(60, 160)
    else:
        base = np.random.uniform(100, 250)
    return max(3, round(base + np.random.normal(0, 5), 1))

def estimate_slope(elevation):
    if elevation < 20:
        return round(np.random.uniform(0.2, 2.5), 1)
    elif elevation < 60:
        return round(np.random.uniform(1.5, 8.0), 1)
    elif elevation < 120:
        return round(np.random.uniform(6.0, 20.0), 1)
    else:
        return round(np.random.uniform(15.0, 38.0), 1)

def estimate_soil(lat, lng, elevation):
    if elevation < 25 or river_proximity(lat, lng) < 1.5:
        soils = ['clay', 'clay', 'clay', 'loam']
    elif elevation < 80:
        soils = ['loam', 'loam', 'clay', 'sandy']
    else:
        soils = ['loam', 'sandy', 'sandy', 'loam']
    return np.random.choice(soils)

def estimate_ndvi(elevation, rainfall_monthly):
    base = 0.3 + min(elevation / 500, 0.25) + min(rainfall_monthly / 400, 0.25)
    return round(min(0.85, max(0.10, base + np.random.normal(0, 0.03))), 2)

def assign_risk_label(row):
    """
    FIXED v2 — Adjusted thresholds for Gampaha wet zone reality.

    Priority order (top = checked first):
      1. Flood
      2. Landslide
      3. Fog
      4. Warning
      5. No Risk  ← loosened so dry/moderate months get labeled correctly
    """
    rain  = row['rainfall_mm']
    humid = row['humidity_pct']
    temp  = row['temperature_c']
    wind  = row['wind_speed_kmh']
    elev  = row['elevation_m']
    slope = row['slope_degree']
    soil  = row['soil_type']
    river = row['river_proximity_km']

    # ── Flood ──────────────────────────────────────────────────────────────────
    # High rainfall + low elevation + near river + clay soil
    if rain > 60 and elev < 30 and river < 2.0 and soil == 'clay':
        return 'Flood'
    if rain > 90 and elev < 50 and river < 3.5:
        return 'Flood'

    # ── Landslide ──────────────────────────────────────────────────────────────
    # High rainfall + steep slope + elevated terrain
    if rain > 55 and slope > 20 and elev > 80:
        return 'Landslide'
    if rain > 75 and slope > 15 and elev > 60:
        return 'Landslide'

    # ── Fog ────────────────────────────────────────────────────────────────────
    # Low rainfall + very high humidity + low wind + cool temp
    if rain < 10 and humid > 93 and wind < 6 and temp < 25:
        return 'Fog'

    # ── Warning ────────────────────────────────────────────────────────────────
    # TIGHTENED: requires stronger conditions to avoid swallowing No Risk
    if rain > 45 and humid > 88:
        return 'Warning'
    if rain > 35 and elev < 35 and river < 3.5:
        return 'Warning'
    if humid > 92 and elev < 40:
        return 'Warning'

    # ── No Risk ────────────────────────────────────────────────────────────────
    # Everything else — dry months, high elevation low rain, etc.
    return 'No Risk'

def fetch_weather(lat, lng):
    """Fetch 2-year daily weather from Open-Meteo, aggregate to monthly rows."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   lat,
        "longitude":  lng,
        "start_date": START_DATE,
        "end_date":   END_DATE,
        "daily": "precipitation_sum,relative_humidity_2m_max,temperature_2m_mean,wind_speed_10m_max",
        "timezone": "Asia/Colombo"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json().get("daily", {})

        dates    = data.get("time", [])
        rainfall = data.get("precipitation_sum", [])
        humidity = data.get("relative_humidity_2m_max", [])
        temp     = data.get("temperature_2m_mean", [])
        wind     = data.get("wind_speed_10m_max", [])

        if not dates:
            return None

        # Group daily → monthly
        rain_m, hum_m, tmp_m, wnd_m = {}, {}, {}, {}
        for i, d in enumerate(dates):
            k = d[:7]
            rain_m.setdefault(k, []).append(rainfall[i] or 0)
            hum_m.setdefault(k, []).append(humidity[i] or 0)
            tmp_m.setdefault(k, []).append(temp[i] or 0)
            wnd_m.setdefault(k, []).append(wind[i] or 0)

        monthly = []
        for month in sorted(rain_m.keys()):
            monthly.append({
                "month":          month,
                "rainfall_mm":    round(sum(rain_m[month]), 1),
                "humidity_pct":   round(np.mean(hum_m[month]), 1),
                "temperature_c":  round(np.mean(tmp_m[month]), 1),
                "wind_speed_kmh": round(np.mean(wnd_m[month]), 1),
            })
        return monthly

    except Exception as e:
        print(f"  ⚠ Error ({lat},{lng}): {e}")
        return None

# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    np.random.seed(42)

    lats = np.arange(LAT_MIN, LAT_MAX + GRID_STEP, GRID_STEP)
    lngs = np.arange(LNG_MIN, LNG_MAX + GRID_STEP, GRID_STEP)
    grid_points = [(round(la, 3), round(lo, 3)) for la in lats for lo in lngs]

    print("=" * 55)
    print("  Suraksha Lanka — Dataset Generator v2 (FIXED)")
    print("=" * 55)
    print(f"  Grid points : {len(grid_points)}")
    print(f"  Period      : {START_DATE} → {END_DATE}")
    print(f"  Expected    : ~{len(grid_points) * 28} rows before augmentation")
    print("=" * 55)

    all_rows = []

    for i, (lat, lng) in enumerate(grid_points):
        print(f"[{i+1}/{len(grid_points)}] ({lat}, {lng})...", end=" ", flush=True)

        monthly_data = fetch_weather(lat, lng)
        if not monthly_data:
            print("SKIP")
            continue

        elev  = estimate_elevation(lat, lng)
        slope = estimate_slope(elev)
        soil  = estimate_soil(lat, lng, elev)
        river = river_proximity(lat, lng)

        for m in monthly_data:
            ndvi = estimate_ndvi(elev, m["rainfall_mm"])
            row = {
                "latitude":           lat,
                "longitude":          lng,
                "month":              m["month"],
                "rainfall_mm":        m["rainfall_mm"],
                "humidity_pct":       m["humidity_pct"],
                "temperature_c":      m["temperature_c"],
                "wind_speed_kmh":     m["wind_speed_kmh"],
                "elevation_m":        elev,
                "slope_degree":       slope,
                "soil_type":          soil,
                "river_proximity_km": river,
                "ndvi":               ndvi,
            }
            row["risk_label"] = assign_risk_label(row)
            all_rows.append(row)

        print(f"OK ({len(monthly_data)} months)")
        time.sleep(REQUEST_DELAY)

        # Checkpoint every 50 points
        if (i + 1) % 50 == 0:
            pd.DataFrame(all_rows).to_csv(OUTPUT_FILE, index=False)
            counts = pd.DataFrame(all_rows)['risk_label'].value_counts().to_dict()
            print(f"\n  ✓ Checkpoint @ {i+1} points | {len(all_rows)} rows | Labels: {counts}\n")

    df = pd.DataFrame(all_rows)

    print("\n" + "=" * 55)
    print("  Raw dataset complete")
    print(f"  Rows   : {len(df)}")
    print(f"  Labels :\n{df['risk_label'].value_counts()}")
    print("=" * 55)

    # ── Augmentation — balance minority classes ────────────────────────────────
    print("\n  Balancing classes...")
    label_counts = df['risk_label'].value_counts()
    target = int(label_counts.median() * 1.2)   # target = 120% of median class
    print(f"  Augmentation target per class: {target} rows")

    aug_rows = []
    for label in df['risk_label'].unique():
        class_df = df[df['risk_label'] == label]
        if len(class_df) < target:
            needed = target - len(class_df)
            sampled = class_df.sample(n=needed, replace=True, random_state=42).copy()
            # Add small Gaussian noise to numeric columns
            for col in ['rainfall_mm', 'humidity_pct', 'temperature_c', 'wind_speed_kmh']:
                std = sampled[col].std()
                sampled[col] = (sampled[col] + np.random.normal(0, std * 0.05, len(sampled))).round(1)
            aug_rows.append(sampled)
            print(f"  Augmented '{label}': +{needed} rows → total {len(class_df) + needed}")

    if aug_rows:
        df = pd.concat([df] + aug_rows, ignore_index=True)
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    df.to_csv(OUTPUT_FILE, index=False)

    print("\n" + "=" * 55)
    print(f"  ✅ Saved: {OUTPUT_FILE}")
    print(f"  Final rows  : {len(df)}")
    print(f"  Final labels:\n{df['risk_label'].value_counts()}")
    print("=" * 55)

if __name__ == "__main__":
    main()
