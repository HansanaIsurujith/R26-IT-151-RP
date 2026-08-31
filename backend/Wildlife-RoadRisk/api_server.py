from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from risk_model_v2_1 import evaluate_live_location, load_observations

app = FastAPI(title="RoadRisk API", version="1.0.0")


class LiveRiskRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


@app.get("/")
def root():
    return {"status": "RoadRisk API is running"}


@app.post("/api/v1/live-risk")
def live_risk(payload: LiveRiskRequest):
    try:
        current_time = datetime.now()
        observations = load_observations()
        result = evaluate_live_location(
            driver_latitude=payload.latitude,
            driver_longitude=payload.longitude,
            current_time=current_time,
            observations=observations,
            search_radius_km=10.0,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}") from exc
