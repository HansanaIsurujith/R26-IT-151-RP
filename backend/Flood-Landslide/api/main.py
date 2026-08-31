
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

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pickle, json, numpy as np, requests
import pandas as pd
import uvicorn
from datetime import datetime, timedelta
from pathlib import Path

app = FastAPI(title="Suraksha Lanka API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Dynamic Path Resolution ───────────────────────────────────────────────────
# BASE_DIR dynamically gets the folder where main.py resides (...\Flood-Landslide\api)
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Load Models ────────────────────────────────────────────────────────────────
with open(BASE_DIR / "model" / "flood_model.pkl", "rb") as f:
    FLOOD_MODEL = pickle.load(f)

with open(BASE_DIR / "model" / "landslide_model.pkl", "rb") as f:
    LANDSLIDE_MODEL = pickle.load(f)

with open(BASE_DIR / "model" / "daily_flood_model.pkl", "rb") as f:
    DAILY_FLOOD_MODEL = pickle.load(f)

with open(BASE_DIR / "model" / "thresholds.json") as f:
    THRESHOLDS = json.load(f)

with open(BASE_DIR / "model" / "daily_flood_thresholds.json") as f:
    DAILY_FLOOD_THRESHOLDS = json.load(f)

print("✅ Models loaded")

# ── Current Supported Study Bounds ────────────────────────────────────────────
# These match the geographic coverage of the rebuilt training dataset.
LAT_MIN, LAT_MAX = 6.90, 7.275
LNG_MIN, LNG_MAX = 79.85, 80.35
GRID_STEP = 0.05

GRID_POINTS = [
    (round(lat, 3), round(lng, 3))
    for lat in np.arange(LAT_MIN, LAT_MAX + 1e-9, GRID_STEP)
    for lng in np.arange(LNG_MIN, LNG_MAX + 1e-9, GRID_STEP)
]
print(f"✅ Grid points : {len(GRID_POINTS)} (supported study area)")

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

# ── Rolling 30-Day Weather ────────────────────────────────────────────────────
def parse_rolling_weather(data, day_offset):
    """Match live inputs to the monthly aggregates used during training."""
    rainfall = data["precipitation_sum"]
    humidity = data["relative_humidity_2m_max"]
    temperature = data["temperature_2m_mean"]
    wind = data["wind_speed_10m_max"]

    # With past_days=29, index 29 is today and index 30 is tomorrow.
    target_index = 29 + day_offset
    start_index = target_index - 29

    def clean(values):
        return [0.0 if value is None else float(value) for value in values]

    rain_window = clean(rainfall[start_index:target_index + 1])
    humidity_window = clean(humidity[start_index:target_index + 1])
    temperature_window = clean(temperature[start_index:target_index + 1])
    wind_window = clean(wind[start_index:target_index + 1])

    if not all(
        len(window) == 30
        for window in (rain_window, humidity_window, temperature_window, wind_window)
    ):
        raise ValueError("Weather API did not return a complete 30-day window")

    return {
        "rainfall_mm": round(float(np.sum(rain_window)), 1),
        "humidity_pct": round(float(np.mean(humidity_window)), 1),
        "temperature_c": round(float(np.mean(temperature_window)), 1),
        "wind_speed_kmh": round(float(np.mean(wind_window)), 1),
    }

def fetch_weather_for_point(lat, lng, day_offset=0):
    """Fetch rolling 30-day weather for one grid point."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude":       lat,
        "longitude":      lng,
        "daily":          "precipitation_sum,relative_humidity_2m_max,temperature_2m_mean,wind_speed_10m_max",
        "timezone":       "Asia/Colombo",
        "past_days": 29,
        "forecast_days": 2,
    }
    try:
        r    = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json().get("daily", {})
        return parse_rolling_weather(data, day_offset)
        
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        # Fallback — use center point weather
        return None

def fetch_center_weather(day_offset=0):
    """Fallback rolling weather from the Gampaha center."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 7.08, "longitude": 80.01,
        "daily": "precipitation_sum,relative_humidity_2m_max,temperature_2m_mean,wind_speed_10m_max",
        "timezone": "Asia/Colombo", "past_days": 29, "forecast_days": 2
    }
    try:
        r    = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("daily", {})
        return parse_rolling_weather(data, day_offset)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Weather API error: {e}")

def fetch_recent_rainfall(latitude, longitude, day_offset=0):
    """Return location-specific daily and antecedent rainfall."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": (
            "precipitation_sum,relative_humidity_2m_max,"
            "temperature_2m_mean,wind_speed_10m_max"
        ),
        "timezone": "Asia/Colombo",
        "past_days": 29,
        "forecast_days": 2,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        daily = response.json()["daily"]

        # Twenty-nine historical days precede today; tomorrow is next.
        today_index = 29
        target_index = today_index + day_offset
        rainfall = [
            0.0 if value is None else float(value)
            for value in daily["precipitation_sum"]
        ]
        start_3d = target_index - 2
        start_7d = target_index - 6
        start_30d = target_index - 29
        if start_30d < 0 or target_index >= len(rainfall):
            raise ValueError("Incomplete recent-rainfall window")

        return {
            "latitude": latitude,
            "longitude": longitude,
            "date": daily["time"][target_index],
            "day": "today" if day_offset == 0 else "tomorrow",
            "today_rainfall_mm": round(rainfall[today_index], 1),
            "target_day_rainfall_mm": round(rainfall[target_index], 1),
            "rain_3d_mm": round(sum(rainfall[start_3d:target_index + 1]), 1),
            "rain_7d_mm": round(sum(rainfall[start_7d:target_index + 1]), 1),
            "rain_30d_mm": round(sum(rainfall[start_30d:target_index + 1]), 1),
            "humidity_pct": round(
                float(daily["relative_humidity_2m_max"][target_index] or 0), 1
            ),
            "temperature_c": round(
                float(daily["temperature_2m_mean"][target_index] or 0), 1
            ),
            "wind_speed_kmh": round(
                float(daily["wind_speed_10m_max"][target_index] or 0), 1
            ),
            "source": "Open-Meteo Forecast API",
            "measurement_type": "gridded_model_estimate",
        }
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail=f"Recent rainfall API error: {error}",
        ) from error

# ── Tightened Risk Levels ──────────────────────────────────────────────────────
def get_risk_level(prob, model_type="flood"):
    model_thresholds = THRESHOLDS.get(
        model_type,
        {}
    )

    warning_threshold = model_thresholds.get(
        "warning",
        0.30
    )

    high_threshold = model_thresholds.get(
        "high",
        0.70
    )

    if prob >= high_threshold:
        return "high"

    if prob >= warning_threshold:
        return "warning"

    return "safe"

def get_daily_flood_risk_level(probability):
    warning = float(DAILY_FLOOD_THRESHOLDS.get("warning", 0.80))
    high = float(DAILY_FLOOD_THRESHOLDS.get("high", 0.95))
    if probability >= high:
        return "high"
    if probability >= warning:
        return "warning"
    return "safe"

def build_model_input(model, feature_map):
    """Create a named one-row frame in the exact order expected by the model."""
    feature_names = list(model.feature_names_in_)
    missing = [name for name in feature_names if name not in feature_map]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing model features: {missing}",
        )
    return pd.DataFrame(
        [[feature_map[name] for name in feature_names]],
        columns=feature_names,
    )

def build_daily_flood_features(latitude, longitude, weather):
    elevation = estimate_elevation(latitude, longitude)
    slope = estimate_slope(elevation)
    soil = soil_encode(latitude, longitude, elevation)
    river = river_proximity(latitude, longitude)
    features = {
        "today_rainfall_mm": weather["target_day_rainfall_mm"],
        "rain_3d_mm": weather["rain_3d_mm"],
        "rain_7d_mm": weather["rain_7d_mm"],
        "rain_30d_mm": weather["rain_30d_mm"],
        "humidity_pct": weather["humidity_pct"],
        "temperature_c": weather["temperature_c"],
        "wind_speed_kmh": weather["wind_speed_kmh"],
        "elevation_m": elevation,
        "slope_degree": slope,
        "soil_type": soil,
        "river_proximity_km": river,
    }
    terrain = {
        "elevation_m": elevation,
        "slope_degree": slope,
        "soil_type": soil,
        "river_proximity_km": river,
    }
    return features, terrain

# ── Predict Zones ──────────────────────────────────────────────────────────────
def predict_zones(model, day_offset, day_label, model_type):
    cache_key = get_cache_key(model_type, day_offset)
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    print(f"\n🔄 Fetching {model_type} zones for {day_label}...")
    center_weather = fetch_center_weather(day_offset)
    zones = []
    high_count = warn_count = safe_count = fallback_count = 0
    total_rain = []

    for lat, lng in GRID_POINTS:
        weather = fetch_weather_for_point(lat, lng, day_offset)
        used_fallback = weather is None
        if used_fallback:
            weather = center_weather
            fallback_count += 1

        total_rain.append(weather["rainfall_mm"])
        terrain = GRID_TERRAIN[(lat, lng)]
        feature_map = {
            "latitude": lat,
            "longitude": lng,
            "rainfall_mm": weather["rainfall_mm"],
            "humidity_pct": weather["humidity_pct"],
            "temperature_c": weather["temperature_c"],
            "wind_speed_kmh": weather["wind_speed_kmh"],
            **terrain,
        }

        model_input = build_model_input(model, feature_map)
        probability = float(model.predict_proba(model_input)[0][1])
        risk = get_risk_level(probability, model_type)

        if risk == "high":
            high_count += 1
        elif risk == "warning":
            warn_count += 1
        else:
            safe_count += 1

        zones.append({
            "lat": lat,
            "lng": lng,
            "probability": round(probability, 4),
            "risk_level": risk,
            "rainfall": weather["rainfall_mm"],
            "elevation": terrain["elevation_m"],
            "weather_fallback": used_fallback,
        })

    avg_weather = {
        "rainfall_mm": round(float(np.mean(total_rain)), 1),
        "humidity_pct": center_weather["humidity_pct"],
        "temperature_c": center_weather["temperature_c"],
        "wind_speed_kmh": center_weather["wind_speed_kmh"],
    }
    visible_zones = [
        zone for zone in zones
        if zone["risk_level"] in ("high", "warning")
    ]
    result = {
        "model_type": model_type,
        "day": day_label,
        "zones": zones,
        "summary": {
            "total": len(zones),
            "high": high_count,
            "warning": warn_count,
            "safe": safe_count,
        },
        "weather": avg_weather,
        "weather_period": "rolling_30_days",
        "risk_zones": {
            "show": bool(visible_zones),
            "count": len(visible_zones),
            "zones": visible_zones,
        },
        "weather_quality": {
            "fallback_points": fallback_count,
            "total_points": len(zones),
        },
        "heavy_rainfall_advisory": avg_weather["rainfall_mm"] > 120,
        "cache_info": {
            "cached_until": (datetime.now() + CACHE_DURATION).strftime("%H:%M:%S"),
            "next_update": "Updates every 3 hours",
        },
    }
    # Backward-compatible response field for the flood map frontend.
    if model_type == "flood":
        result["flood_zones"] = result["risk_zones"]

    set_cache(cache_key, result)
    print(f"✅ Done: High={high_count} Warning={warn_count} Safe={safe_count}")
    return result

# ══════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "3.1.0",
        "models": ["monthly_flood", "daily_flood", "landslide"],
        "grid_points": len(GRID_POINTS),
        "area": "Supported Gampaha study sample",
        "bounds": {
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
            "lng_min": LNG_MIN,
            "lng_max": LNG_MAX,
        },
        "cache_size": len(CACHE),
        "update_cycle": "Every 3 hours",
        "thresholds": THRESHOLDS,
        "daily_flood_thresholds": DAILY_FLOOD_THRESHOLDS,
    }

@app.get("/weather/recent")
def recent_weather(
    latitude: float = Query(..., ge=LAT_MIN, le=LAT_MAX),
    longitude: float = Query(..., ge=LNG_MIN, le=LNG_MAX),
    day_offset: int = Query(0, ge=0, le=1),
):
    """Get today's/tomorrow's daily, 3-day and 7-day rainfall features."""
    return fetch_recent_rainfall(latitude, longitude, day_offset)

@app.get("/predict/flood/daily")
def predict_daily_flood_risk(
    latitude: float = Query(..., ge=LAT_MIN, le=LAT_MAX),
    longitude: float = Query(..., ge=LNG_MIN, le=LNG_MAX),
    day_offset: int = Query(0, ge=0, le=1),
):
    """Predict location-level daily flood risk from live/recent weather."""
    weather = fetch_recent_rainfall(latitude, longitude, day_offset)
    feature_map, terrain = build_daily_flood_features(
        latitude, longitude, weather
    )
    model_input = build_model_input(DAILY_FLOOD_MODEL, feature_map)
    probability = float(
        DAILY_FLOOD_MODEL.predict_proba(model_input)[0][1]
    )
    risk_level = get_daily_flood_risk_level(probability)
    warning_threshold = float(
        DAILY_FLOOD_THRESHOLDS.get("warning", 0.80)
    )

    return {
        "latitude": latitude,
        "longitude": longitude,
        "date": weather["date"],
        "day": weather["day"],
        "weather": {
            "today_rainfall_mm": weather["today_rainfall_mm"],
            "target_day_rainfall_mm": weather["target_day_rainfall_mm"],
            "rain_3d_mm": weather["rain_3d_mm"],
            "rain_7d_mm": weather["rain_7d_mm"],
            "rain_30d_mm": weather["rain_30d_mm"],
            "humidity_pct": weather["humidity_pct"],
            "temperature_c": weather["temperature_c"],
            "wind_speed_kmh": weather["wind_speed_kmh"],
        },
        "terrain": terrain,
        "flood_probability": round(probability, 4),
        "flood_risk": probability >= warning_threshold,
        "risk_level": risk_level,
        "prediction_type": "daily_flood_risk_prototype",
        "confirmed_flood": False,
        "data_source": weather["source"],
        "model_limitations": (
            "Primarily trained on weak-rule labels; external UNOSAT "
            "event-window recall was limited. Check official DMC warnings."
        ),
    }

@app.get("/predict/flood/daily/zones")
def predict_daily_flood_zones(
    day_offset: int = Query(0, ge=0, le=1),
):
    """Predict daily flood risk for every supported map grid point."""
    cache_key = get_cache_key("daily_flood_zones", day_offset)
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    center_weather = fetch_recent_rainfall(7.08, 80.01, day_offset)
    zones = []
    high_count = warning_count = safe_count = fallback_count = 0
    warning_threshold = float(
        DAILY_FLOOD_THRESHOLDS.get("warning", 0.80)
    )

    for latitude, longitude in GRID_POINTS:
        used_fallback = False
        try:
            weather = fetch_recent_rainfall(
                latitude, longitude, day_offset
            )
        except HTTPException:
            weather = {
                **center_weather,
                "latitude": latitude,
                "longitude": longitude,
            }
            used_fallback = True
            fallback_count += 1

        feature_map, terrain = build_daily_flood_features(
            latitude, longitude, weather
        )
        model_input = build_model_input(DAILY_FLOOD_MODEL, feature_map)
        probability = float(
            DAILY_FLOOD_MODEL.predict_proba(model_input)[0][1]
        )
        risk_level = get_daily_flood_risk_level(probability)

        if risk_level == "high":
            high_count += 1
        elif risk_level == "warning":
            warning_count += 1
        else:
            safe_count += 1

        zones.append({
            "lat": latitude,
            "lng": longitude,
            "flood_probability": round(probability, 4),
            "flood_risk": probability >= warning_threshold,
            "risk_level": risk_level,
            "today_rainfall_mm": weather["today_rainfall_mm"],
            "target_day_rainfall_mm": weather["target_day_rainfall_mm"],
            "rain_3d_mm": weather["rain_3d_mm"],
            "rain_7d_mm": weather["rain_7d_mm"],
            "rain_30d_mm": weather["rain_30d_mm"],
            "elevation_m": terrain["elevation_m"],
            "river_proximity_km": terrain["river_proximity_km"],
            "weather_fallback": used_fallback,
        })

    risk_zones = [zone for zone in zones if zone["flood_risk"]]
    result = {
        "model_type": "daily_flood_risk_prototype",
        "day": "today" if day_offset == 0 else "tomorrow",
        "date": center_weather["date"],
        "summary": {
            "total": len(zones),
            "high": high_count,
            "warning": warning_count,
            "safe": safe_count,
        },
        "zones": zones,
        "risk_zones": {
            "show": bool(risk_zones),
            "count": len(risk_zones),
            "zones": risk_zones,
        },
        "weather_quality": {
            "fallback_points": fallback_count,
            "total_points": len(zones),
        },
        "thresholds": DAILY_FLOOD_THRESHOLDS,
        "confirmed_flood": False,
        "model_limitations": (
            "Risk prediction, not observed inundation. Model targets are "
            "primarily weak-rule labels with limited UNOSAT event coverage."
        ),
        "cache_info": {
            "cached_until": (
                datetime.now() + CACHE_DURATION
            ).strftime("%H:%M:%S"),
            "next_update": "Updates every 3 hours",
        },
    }
    set_cache(cache_key, result)
    return result

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
    rainfall_mm: float = Field(..., ge=0, le=2000)
    humidity_pct: float = Field(..., ge=0, le=100)
    temperature_c: float = Field(..., ge=-20, le=60)
    wind_speed_kmh: float = Field(..., ge=0, le=300)

def predict_manual_weather_zones(data: WeatherInput):
    weather = data.model_dump()
    zones = []
    high_count = warn_count = safe_count = 0

    for lat, lng in GRID_POINTS:
        terrain = GRID_TERRAIN[(lat, lng)]
        feature_map = {
            "latitude": lat,
            "longitude": lng,
            **weather,
            **terrain,
        }
        model_input = build_model_input(FLOOD_MODEL, feature_map)
        probability = float(FLOOD_MODEL.predict_proba(model_input)[0][1])
        risk = get_risk_level(probability, "flood")

        if risk == "high":
            high_count += 1
        elif risk == "warning":
            warn_count += 1
        else:
            safe_count += 1

        zones.append({
            "lat": lat,
            "lng": lng,
            "probability": round(probability, 4),
            "risk_level": risk,
        })

    return {
        "day": "manual",
        "zones": zones,
        "summary": {
            "total": len(zones),
            "high": high_count,
            "warning": warn_count,
            "safe": safe_count,
        },
        "weather": weather,
        "weather_period": "manual_month_equivalent",
        "heavy_rainfall_advisory": weather["rainfall_mm"] > 120,
    }

@app.post("/predict/flood/zones")
def flood_zones_manual(data: WeatherInput):
    """Manual weather input — for testing."""
    return predict_manual_weather_zones(data)

# ── Manual Prediction Request Schema ──────────────────────────────────────────
class ManualPredictRequest(BaseModel):
    latitude: float = Field(..., ge=LAT_MIN, le=LAT_MAX)
    longitude: float = Field(..., ge=LNG_MIN, le=LNG_MAX)
    day_offset: int = Field(0, ge=0, le=1)

# ── Manual Prediction Endpoint ─────────────────────────────────────────────────
@app.post("/predict/manual")
def predict_manual(req: ManualPredictRequest):
    lat, lng = req.latitude, req.longitude

    elev  = estimate_elevation(lat, lng)
    slope = estimate_slope(elev)
    soil  = soil_encode(lat, lng, elev)
    river = river_proximity(lat, lng)
    ndvi  = round(min(0.85, 0.3 + elev / 500), 2)

    cache_key = get_cache_key(f"manual_{lat}_{lng}", req.day_offset)
    weather = get_cached(cache_key)
    if weather is None:
        weather = fetch_weather_for_point(lat, lng, req.day_offset)
        if weather is None:
            weather = fetch_center_weather(req.day_offset)
        set_cache(cache_key, weather)


    feature_map = {
        "latitude": lat,
        "longitude": lng,
        "rainfall_mm": weather["rainfall_mm"],
        "humidity_pct": weather["humidity_pct"],
        "temperature_c": weather["temperature_c"],
        "wind_speed_kmh": weather["wind_speed_kmh"],
        "elevation_m": elev,
        "slope_degree": slope,
        "soil_type": soil,
        "river_proximity_km": river,
        "ndvi": ndvi,
    }
    model_input = build_model_input(FLOOD_MODEL, feature_map)

    try:
        risk_score = float(FLOOD_MODEL.predict_proba(model_input)[0][1])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {e}")

    return {
        "latitude":  lat,
        "longitude": lng,
        "terrain": {
            "elevation_m": elev,
            "slope_degree": slope,
            "soil_type": soil,
            "river_proximity_km": river,
            "ndvi": ndvi,
        },
        "weather": weather,
        "weather_period": "rolling_30_days",
        "risk_score": round(risk_score, 4),
        "risk_level": get_risk_level(risk_score, "flood"),
    }

@app.post("/predict/flood/zones/gated")
def flood_zones_manual_gated(data: WeatherInput):
    """Backward-compatible alias; predictions are no longer hidden by rainfall."""
    result = predict_manual_weather_zones(data)
    result["flood_risk_gated"] = False
    result["deprecated"] = "Use /predict/flood/zones"
    return result

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
