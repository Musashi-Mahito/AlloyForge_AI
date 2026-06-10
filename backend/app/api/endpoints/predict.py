from fastapi import APIRouter, HTTPException, Depends
from backend.app.models.schemas import PredictionRequest, PredictionResponse
from backend.app.services.prediction_service import PredictionService
import json
import hashlib
import redis
import os

router = APIRouter()
prediction_service = PredictionService()

# Setup Redis Cache connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(REDIS_URL, socket_connect_timeout=1)
except Exception:
    redis_client = None

@router.post("/", response_model=PredictionResponse)
def predict_properties(request: PredictionRequest):
    # Enforce weights constraint
    total_wt = sum(request.composition.values())
    if abs(total_wt - 100.0) > 1.0:
        raise HTTPException(status_code=400, detail="Elemental composition percentages must sum to approximately 100%.")

    # Generate cache key
    cache_key = None
    if redis_client:
        serialized_req = json.dumps(request.dict(), sort_keys=True)
        cache_key = f"predict:{hashlib.sha256(serialized_req.encode()).hexdigest()}"
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass  # Fail silent, bypass redis on timeout/failure

    # Perform prediction
    res = prediction_service.predict(request.composition)

    # Set cache
    if redis_client and cache_key:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(res)) # cache for 1 hour
        except Exception:
            pass

    return res
