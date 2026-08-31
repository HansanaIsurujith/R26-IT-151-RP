from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from risk_model_v2_1 import evaluate_live_location, load_observations
from wildlife_locations import build_wildlife_locations, build_wildlife_map_locations

app = FastAPI(title="RoadRisk API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RiskEvaluateRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class WildlifeLocationsRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    search_radius_km: float = Field(10.0, gt=0.0, le=100.0)


class WildlifeMapLocationsRequest(BaseModel):
    north: float = Field(..., ge=-90.0, le=90.0)
    south: float = Field(..., ge=-90.0, le=90.0)
    east: float = Field(..., ge=-180.0, le=180.0)
    west: float = Field(..., ge=-180.0, le=180.0)


@app.on_event("startup")
def startup_event():
    try:
        app.state.observations = load_observations()
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize wildlife observations: {exc}") from exc


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/wildlife/locations")
def wildlife_locations(payload: WildlifeLocationsRequest):
    try:
        observations = getattr(app.state, "observations", None)

        if observations is None:
            raise RuntimeError("Model observations were not initialized.")

        return build_wildlife_locations(
            driver_latitude=payload.latitude,
            driver_longitude=payload.longitude,
            current_time=datetime.now(),
            observations=observations,
            search_radius_km=payload.search_radius_km,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Wildlife location evaluation failed: {exc}") from exc


@app.post("/api/wildlife/map-locations")
def wildlife_map_locations(payload: WildlifeMapLocationsRequest):
    try:
        observations = getattr(app.state, "observations", None)

        if observations is None:
            raise RuntimeError("Model observations were not initialized.")

        return build_wildlife_map_locations(
            north=payload.north,
            south=payload.south,
            east=payload.east,
            west=payload.west,
            current_time=datetime.now(),
            observations=observations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Wildlife map location evaluation failed: {exc}") from exc


@app.post("/api/risk/evaluate")
def evaluate_risk(payload: RiskEvaluateRequest):
    try:
        current_time = datetime.now()
        observations = getattr(app.state, "observations", None)

        if observations is None:
            raise RuntimeError("Model observations were not initialized.")

        return evaluate_live_location(
            driver_latitude=payload.latitude,
            driver_longitude=payload.longitude,
            current_time=current_time,
            observations=observations,
            search_radius_km=10.0,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc
