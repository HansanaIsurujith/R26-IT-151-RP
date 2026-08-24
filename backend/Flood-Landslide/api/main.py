# """
# Suraksha Lanka — FastAPI Backend
# Project : R26-IT-151
# Student : IT22294470

# Endpoints:
#   GET  /health
#   POST /predict/flood/zones     → Today's flood risk zones
#   POST /predict/landslide/zones → Today's landslide risk zones
#   GET  /predict/flood/today     → Auto fetch weather + predict
#   GET  /predict/flood/tomorrow  → Auto fetch tomorrow forecast + predict
#   GET  /predict/landslide/today
#   GET  /predict/landslide/tomorrow
# """

# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import pickle, json, numpy as np, requests
# from typing import List
# import uvicorn

# app = FastAPI(title="Suraksha Lanka API", version="1.0.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ── Load Models ────────────────────────────────────────────────────────────────
# with open("model/flood_model.pkl", "rb") as f:
#     FLOOD_MODEL = pickle.load(f)

# with open("model/landslide_model.pkl", "rb") as f:
#     LANDSLIDE_MODEL = pickle.load(f)

# with open("model/thresholds.json") as f:
#     THRESHOLDS = json.load(f)

# print("✅ Models loaded")
# print(f"   Flood threshold     : {THRESHOLDS['flood']['optimal']}")
# print(f"   Landslide threshold : {THRESHOLDS['landslide']['optimal']}")

# # ── Gampaha Grid (0.025° resolution) ──────────────────────────────────────────
# LAT_MIN, LAT_MAX = 6.90, 7.40
# LNG_MIN, LNG_MAX = 79.85, 80.35
# GRID_STEP = 0.05  # coarser for API speed (~100 points)

# GRID_POINTS = [
#     (round(lat, 3), round(lng, 3))
#     for lat in np.arange(LAT_MIN, LAT_MAX + GRID_STEP, GRID_STEP)
#     for lng in np.arange(LNG_MIN, LNG_MAX + GRID_STEP, GRID_STEP)
# ]

# # River points for proximity calc
# RIVER_POINTS = [
#     (6.92,79.87),(6.95,79.90),(6.98,79.93),(7.00,79.96),
#     (7.02,79.99),(7.05,80.02),(7.08,80.05),(7.10,80.08),
#     (7.12,80.11),(7.15,80.14),(7.18,80.17),(7.20,80.14),
#     (7.22,80.11),(7.25,80.08),(7.10,80.20),(7.13,80.23),
#     (7.16,80.26),(7.19,80.29),(7.22,80.32),
# ]

# # ── Terrain Helpers ────────────────────────────────────────────────────────────
# def river_proximity(lat, lng):
#     return round(min(
#         ((lat-r[0])**2 + (lng-r[1])**2)**0.5 * 111
#         for r in RIVER_POINTS
#     ), 2)

# def estimate_elevation(lat, lng):
#     if lng < 80.0:   return float(np.random.uniform(5, 30))
#     elif lng < 80.15: return float(np.random.uniform(20, 90))
#     elif lng < 80.25: return float(np.random.uniform(60, 160))
#     else:             return float(np.random.uniform(100, 250))

# def estimate_slope(elev):
#     if elev < 20:   return float(np.random.uniform(0.2, 2.5))
#     elif elev < 60:  return float(np.random.uniform(1.5, 8.0))
#     elif elev < 120: return float(np.random.uniform(6.0, 20.0))
#     else:            return float(np.random.uniform(15.0, 38.0))

# def soil_encode(lat, lng, elev):
#     if elev < 25 or river_proximity(lat, lng) < 1.5: return 0  # clay
#     elif elev < 80: return 1  # loam
#     else: return 2  # sandy

# # ── Open-Meteo Fetch ───────────────────────────────────────────────────────────
# def fetch_weather(lat, lng, day_offset=0):
#     """
#     Fetch weather for a specific day.
#     day_offset=0 → today, day_offset=1 → tomorrow
#     """
#     url = "https://api.open-meteo.com/v1/forecast"
#     params = {
#         "latitude":  lat,
#         "longitude": lng,
#         "daily": "precipitation_sum,relative_humidity_2m_max,temperature_2m_mean,wind_speed_10m_max",
#         "timezone": "Asia/Colombo",
#         "forecast_days": 2
#     }
#     try:
#         r = requests.get(url, params=params, timeout=10)
#         data = r.json().get("daily", {})
#         idx = day_offset  # 0=today, 1=tomorrow
#         return {
#             "rainfall_mm":    data["precipitation_sum"][idx] or 0,
#             "humidity_pct":   data["relative_humidity_2m_max"][idx] or 0,
#             "temperature_c":  data["temperature_2m_mean"][idx] or 0,
#             "wind_speed_kmh": data["wind_speed_10m_max"][idx] or 0,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=503, detail=f"Weather API error: {e}")

# # ── Risk Label Helper ──────────────────────────────────────────────────────────
# def get_risk_level(prob, thresholds):
#     high  = thresholds.get("high_risk", 0.65)
#     warn  = thresholds.get("warning",   0.35)
#     if prob >= high: return "high"
#     elif prob >= warn: return "warning"
#     else: return "safe"

# # ── Predict Zones ──────────────────────────────────────────────────────────────
# def predict_zones(model, thresholds, features_list, day_label):
#     """Run model on all grid points and return risk zones."""
#     zones = []
#     high_count = warn_count = safe_count = 0

#     for lat, lng in GRID_POINTS:
#         elev  = estimate_elevation(lat, lng)
#         slope = estimate_slope(elev)
#         soil  = soil_encode(lat, lng, elev)
#         river = river_proximity(lat, lng)

#         # Build feature vector matching training features
#         feature_map = {
#             "latitude":           lat,
#             "longitude":          lng,
#             "rainfall_mm":        features_list["rainfall_mm"],
#             "humidity_pct":       features_list["humidity_pct"],
#             "temperature_c":      features_list["temperature_c"],
#             "wind_speed_kmh":     features_list["wind_speed_kmh"],
#             "elevation_m":        elev,
#             "slope_degree":       slope,
#             "soil_type":          soil,
#             "river_proximity_km": river,
#             "ndvi":               round(min(0.85, 0.3 + elev/500 + features_list["rainfall_mm"]/400), 2),
#         }

#         # Select features in correct order
#         X = [[feature_map[f] for f in model.feature_names_in_]]
#         prob = float(model.predict_proba(X)[0][1])
#         risk = get_risk_level(prob, thresholds)

#         if risk == "high":    high_count += 1
#         elif risk == "warning": warn_count += 1
#         else:                  safe_count += 1

#         zones.append({
#             "lat":         lat,
#             "lng":         lng,
#             "probability": round(prob, 4),
#             "risk_level":  risk,
#         })

#     return {
#         "day":    day_label,
#         "zones":  zones,
#         "summary": {
#             "total":   len(zones),
#             "high":    high_count,
#             "warning": warn_count,
#             "safe":    safe_count,
#         },
#         "weather": features_list,
#     }

# # ══════════════════════════════════════════════════════
# #  ENDPOINTS
# # ══════════════════════════════════════════════════════

# @app.get("/health")
# def health():
#     return {
#         "status": "ok",
#         "models": ["flood", "landslide"],
#         "grid_points": len(GRID_POINTS),
#         "thresholds": THRESHOLDS,
#     }

# # ── Flood ──────────────────────────────────────────────────────────────────────
# @app.get("/predict/flood/today")
# def flood_today():
#     """Fetch today's weather → predict flood zones across Gampaha."""
#     # Use center of Gampaha for weather (all grid points close enough)
#     weather = fetch_weather(7.08, 80.01, day_offset=0)
#     return predict_zones(
#         FLOOD_MODEL, THRESHOLDS["flood"], weather, "today"
#     )

# @app.get("/predict/flood/tomorrow")
# def flood_tomorrow():
#     """Fetch tomorrow's forecast → predict flood zones."""
#     weather = fetch_weather(7.08, 80.01, day_offset=1)
#     return predict_zones(
#         FLOOD_MODEL, THRESHOLDS["flood"], weather, "tomorrow"
#     )

# # ── Landslide ─────────────────────────────────────────────────────────────────
# @app.get("/predict/landslide/today")
# def landslide_today():
#     """Fetch today's weather → predict landslide zones."""
#     weather = fetch_weather(7.08, 80.01, day_offset=0)
#     return predict_zones(
#         LANDSLIDE_MODEL, THRESHOLDS["landslide"], weather, "today"
#     )

# @app.get("/predict/landslide/tomorrow")
# def landslide_tomorrow():
#     """Fetch tomorrow's forecast → predict landslide zones."""
#     weather = fetch_weather(7.08, 80.01, day_offset=1)
#     return predict_zones(
#         LANDSLIDE_MODEL, THRESHOLDS["landslide"], weather, "tomorrow"
#     )

# # ── Manual Input (for testing) ────────────────────────────────────────────────
# class WeatherInput(BaseModel):
#     rainfall_mm:    float
#     humidity_pct:   float
#     temperature_c:  float
#     wind_speed_kmh: float

# @app.post("/predict/flood/zones")
# def flood_zones_manual(data: WeatherInput):
#     """Manual weather input → flood zones (for testing)."""
#     weather = data.dict()
#     return predict_zones(FLOOD_MODEL, THRESHOLDS["flood"], weather, "manual")

# @app.post("/predict/landslide/zones")
# def landslide_zones_manual(data: WeatherInput):
#     """Manual weather input → landslide zones (for testing)."""
#     weather = data.dict()
#     return predict_zones(LANDSLIDE_MODEL, THRESHOLDS["landslide"], weather, "manual")

# # ── Run ───────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

"""
Suraksha Lanka — FastAPI Backend (FIXED v3)
Project : R26-IT-151
Student : IT22294470

FIXES v3:
  - Per-point weather fetch (each grid point own rainfall)
  - 3-hour cache (stable zones, fast responses)
  - Tightened thresholds (more accurate flood detection)
  - Gampaha District only
  - Terrain pre-calculated at startup
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle, json, numpy as np, requests
import uvicorn
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI(title="Suraksha Lanka API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load Models ────────────────────────────────────────────────────────────────
with open("model/flood_model.pkl", "rb") as f:
    FLOOD_MODEL = pickle.load(f)

with open("model/landslide_model.pkl", "rb") as f:
    LANDSLIDE_MODEL = pickle.load(f)

with open("model/thresholds.json") as f:
    THRESHOLDS = json.load(f)

print("✅ Models loaded")

# ── Gampaha District EXACT Boundaries ─────────────────────────────────────────
LAT_MIN, LAT_MAX = 7.00, 7.42
LNG_MIN, LNG_MAX = 79.90, 80.35
GRID_STEP = 0.05

GRID_POINTS = [
    (round(lat, 3), round(lng, 3))
    for lat in np.arange(LAT_MIN, LAT_MAX + GRID_STEP, GRID_STEP)
    for lng in np.arange(LNG_MIN, LNG_MAX + GRID_STEP, GRID_STEP)
]
print(f"✅ Grid points : {len(GRID_POINTS)} (Gampaha District only)")

# ── River Points ───────────────────────────────────────────────────────────────
RIVER_POINTS = [
    (7.02,79.99),(7.05,80.02),(7.08,80.05),(7.10,80.08),
    (7.12,80.11),(7.15,80.14),(7.18,80.17),(7.20,80.14),
    (7.22,80.11),(7.25,80.08),(7.10,80.20),(7.13,80.23),
    (7.16,80.26),(7.19,80.29),(7.22,80.32),
]

# ── Terrain Helpers (Deterministic) ───────────────────────────────────────────
def river_proximity(lat, lng):
    return round(min(
        ((lat-r[0])**2 + (lng-r[1])**2)**0.5 * 111
        for r in RIVER_POINTS
    ), 2)

def estimate_elevation(lat, lng):
    if lng < 80.0:
        base = 8 + (lat - 7.0) * 10 + (lng - 79.9) * 15
    elif lng < 80.15:
        base = 25 + (lat - 7.0) * 20 + (lng - 80.0) * 30
    elif lng < 80.25:
        base = 60 + (lat - 7.0) * 30 + (lng - 80.15) * 50
    else:
        base = 120 + (lat - 7.0) * 40 + (lng - 80.25) * 80
    return round(max(3.0, min(250.0, base)), 1)

def estimate_slope(elev):
    if elev < 20:    return round(0.5 + elev * 0.08, 1)
    elif elev < 60:  return round(2.0 + (elev-20) * 0.12, 1)
    elif elev < 120: return round(6.8 + (elev-60) * 0.18, 1)
    else:            return round(17.6 + (elev-120) * 0.15, 1)

def soil_encode(lat, lng, elev):
    river = river_proximity(lat, lng)
    if elev < 25 or river < 1.5: return 0  # clay
    elif elev < 80: return 1               # loam
    else: return 2                         # sandy

# ── Pre-calculate Terrain at Startup ──────────────────────────────────────────
print("⏳ Pre-calculating terrain...")
GRID_TERRAIN = {}
for lat, lng in GRID_POINTS:
    elev  = estimate_elevation(lat, lng)
    slope = estimate_slope(elev)
    soil  = soil_encode(lat, lng, elev)
    river = river_proximity(lat, lng)
    ndvi  = round(min(0.85, 0.3 + elev/500), 2)
    GRID_TERRAIN[(lat, lng)] = {
        "elevation_m":        elev,
        "slope_degree":       slope,
        "soil_type":          soil,
        "river_proximity_km": river,
        "ndvi":               ndvi,
    }
print(f"✅ Terrain pre-calculated for {len(GRID_TERRAIN)} points")

# ── 3-Hour Cache ───────────────────────────────────────────────────────────────
CACHE = {}
CACHE_DURATION = timedelta(hours=3)

def get_cache_key(model_type, day_offset):
    # Cache key = model + day + 3-hour window
    now    = datetime.now()
    window = now.hour // 3  # 0,1,2 → window 0 | 3,4,5 → window 1 etc.
    return f"{model_type}_{day_offset}_{now.date()}_{window}"

def get_cached(key):
    if key in CACHE:
        data, timestamp = CACHE[key]
        if datetime.now() - timestamp < CACHE_DURATION:
            print(f"  📦 Cache hit: {key}")
            return data
    return None

def set_cache(key, data):
    CACHE[key] = (data, datetime.now())
    print(f"  💾 Cache saved: {key}")

# ── Per-Point Weather Fetch ────────────────────────────────────────────────────
def fetch_weather_for_point(lat, lng, day_offset=0):
    """Fetch weather for each individual grid point."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":       lat,
        "longitude":      lng,
        "daily":          "precipitation_sum,relative_humidity_2m_max,temperature_2m_mean,wind_speed_10m_max",
        "timezone":       "Asia/Colombo",
        "forecast_days":  2
    }
    try:
        r    = requests.get(url, params=params, timeout=8)
        data = r.json().get("daily", {})
        idx  = day_offset
        return {
            "rainfall_mm":    float(data["precipitation_sum"][idx]        or 0),
            "humidity_pct":   float(data["relative_humidity_2m_max"][idx] or 0),
            "temperature_c":  float(data["temperature_2m_mean"][idx]      or 0),
            "wind_speed_kmh": float(data["wind_speed_10m_max"][idx]       or 0),
        }
    except:
        # Fallback — use center point weather
        return None

def fetch_center_weather(day_offset=0):
    """Fallback weather from Gampaha center."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 7.08, "longitude": 80.01,
        "daily": "precipitation_sum,relative_humidity_2m_max,temperature_2m_mean,wind_speed_10m_max",
        "timezone": "Asia/Colombo", "forecast_days": 2
    }
    try:
        r    = requests.get(url, params=params, timeout=10)
        data = r.json().get("daily", {})
        idx  = day_offset
        return {
            "rainfall_mm":    float(data["precipitation_sum"][idx]        or 0),
            "humidity_pct":   float(data["relative_humidity_2m_max"][idx] or 0),
            "temperature_c":  float(data["temperature_2m_mean"][idx]      or 0),
            "wind_speed_kmh": float(data["wind_speed_10m_max"][idx]       or 0),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Weather API error: {e}")

# ── Tightened Risk Levels ──────────────────────────────────────────────────────
def get_risk_level(prob):
    """
    Tightened thresholds — more accurate flood detection
    High    : >= 0.70 (was 0.65)
    Warning : >= 0.50 (was 0.35)
    Safe    : <  0.50
    """
    if prob >= 0.70:   return "high"
    elif prob >= 0.50: return "warning"
    else:              return "safe"

# ── Predict Zones ──────────────────────────────────────────────────────────────
def predict_zones(model, day_offset, day_label, model_type):
    # Check cache first
    cache_key = get_cache_key(model_type, day_offset)
    cached    = get_cached(cache_key)
    if cached:
        return cached

    print(f"\n🔄 Fetching {model_type} zones for {day_label}...")
    print(f"   Fetching weather for {len(GRID_POINTS)} points...")

    # Fetch center weather as fallback
    center_weather = fetch_center_weather(day_offset)

    zones      = []
    high_count = warn_count = safe_count = 0
    total_rain = []

    for lat, lng in GRID_POINTS:
        # Fetch per-point weather (fallback to center if fails)
        weather = fetch_weather_for_point(lat, lng, day_offset)
        if weather is None:
            weather = center_weather

        total_rain.append(weather["rainfall_mm"])

        terrain = GRID_TERRAIN[(lat, lng)]
        feature_map = {
            "latitude":           lat,
            "longitude":          lng,
            "rainfall_mm":        weather["rainfall_mm"],
            "humidity_pct":       weather["humidity_pct"],
            "temperature_c":      weather["temperature_c"],
            "wind_speed_kmh":     weather["wind_speed_kmh"],
            "elevation_m":        terrain["elevation_m"],
            "slope_degree":       terrain["slope_degree"],
            "soil_type":          terrain["soil_type"],
            "river_proximity_km": terrain["river_proximity_km"],
            "ndvi":               terrain["ndvi"],
        }

        X    = [[feature_map[f] for f in model.feature_names_in_]]
        prob = float(model.predict_proba(X)[0][1])
        risk = get_risk_level(prob)

        if risk == "high":      high_count += 1
        elif risk == "warning": warn_count += 1
        else:                   safe_count += 1

        zones.append({
            "lat":         lat,
            "lng":         lng,
            "probability": round(prob, 4),
            "risk_level":  risk,
            "rainfall":    weather["rainfall_mm"],
            "elevation":   terrain["elevation_m"],
        })

    # Summary weather (average across all points)
    avg_weather = {
        "rainfall_mm":    round(float(np.mean(total_rain)), 1),
        "humidity_pct":   center_weather["humidity_pct"],
        "temperature_c":  center_weather["temperature_c"],
        "wind_speed_kmh": center_weather["wind_speed_kmh"],
    }

    result = {
        "day":        day_label,
        "zones":      zones,
        "summary": {
            "total":   len(zones),
            "high":    high_count,
            "warning": warn_count,
            "safe":    safe_count,
        },
        "weather":    avg_weather,
        "cache_info": {
            "cached_until": (datetime.now() + CACHE_DURATION).strftime("%H:%M:%S"),
            "next_update":  f"Updates every 3 hours",
        }
    }

    set_cache(cache_key, result)
    print(f"✅ Done: High={high_count} Warning={warn_count} Safe={safe_count}")
    return result

# ══════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {
        "status":      "ok",
        "version":     "3.0.0",
        "models":      ["flood", "landslide"],
        "grid_points": len(GRID_POINTS),
        "area":        "Gampaha District only",
        "cache_size":  len(CACHE),
        "update_cycle":"Every 3 hours",
        "thresholds":  {"high": 0.70, "warning": 0.50},
    }

@app.get("/predict/flood/today")
def flood_today():
    return predict_zones(FLOOD_MODEL, 0, "today", "flood")

@app.get("/predict/flood/tomorrow")
def flood_tomorrow():
    return predict_zones(FLOOD_MODEL, 1, "tomorrow", "flood")

@app.get("/predict/landslide/today")
def landslide_today():
    return predict_zones(LANDSLIDE_MODEL, 0, "today", "landslide")

@app.get("/predict/landslide/tomorrow")
def landslide_tomorrow():
    return predict_zones(LANDSLIDE_MODEL, 1, "tomorrow", "landslide")

class WeatherInput(BaseModel):
    rainfall_mm:    float
    humidity_pct:   float
    temperature_c:  float
    wind_speed_kmh: float

@app.post("/predict/flood/zones")
def flood_zones_manual(data: WeatherInput):
    """Manual weather input — for testing."""
    weather = data.dict()
    zones   = []
    high_count = warn_count = safe_count = 0

    for lat, lng in GRID_POINTS:
        terrain = GRID_TERRAIN[(lat, lng)]
        feature_map = {
            "latitude": lat, "longitude": lng,
            **weather,
            "elevation_m":        terrain["elevation_m"],
            "slope_degree":       terrain["slope_degree"],
            "soil_type":          terrain["soil_type"],
            "river_proximity_km": terrain["river_proximity_km"],
            "ndvi":               terrain["ndvi"],
        }
        X    = [[feature_map[f] for f in FLOOD_MODEL.feature_names_in_]]
        prob = float(FLOOD_MODEL.predict_proba(X)[0][1])
        risk = get_risk_level(prob)
        if risk == "high":      high_count += 1
        elif risk == "warning": warn_count += 1
        else:                   safe_count += 1
        zones.append({"lat": lat, "lng": lng,
                      "probability": round(prob, 4), "risk_level": risk})

    return {"day": "manual", "zones": zones,
            "summary": {"total": len(zones), "high": high_count,
                        "warning": warn_count, "safe": safe_count},
            "weather": weather}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

