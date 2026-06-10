from fastapi import APIRouter, HTTPException
from backend.app.models.schemas import ExplanationRequest, ExplanationResponse
from backend.app.services.prediction_service import PredictionService

router = APIRouter()
prediction_service = PredictionService()

@router.post("/", response_model=ExplanationResponse)
def explain_prediction(request: ExplanationRequest):
    # Enforce constraints
    total_wt = sum(request.composition.values())
    if abs(total_wt - 100.0) > 1.0:
        raise HTTPException(status_code=400, detail="Elemental composition percentages must sum to approximately 100%.")
        
    valid_properties = ["elastic_modulus", "yield_strength", "uts", "corrosion_rate", "biocompatibility_score"]
    if request.target_property not in valid_properties:
        raise HTTPException(status_code=400, detail=f"Invalid target_property. Must be one of {valid_properties}")

    res = prediction_service.explain(request.composition, request.target_property)
    return res
