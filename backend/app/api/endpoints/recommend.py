from fastapi import APIRouter
from typing import List
from backend.app.models.schemas import RecommendationRequest, RecommendedAlloySchema
from backend.app.services.recommendation_service import RecommendationService

router = APIRouter()
rec_service = RecommendationService()

@router.post("/", response_model=List[RecommendedAlloySchema])
def get_recommendations(request: RecommendationRequest):
    candidates = rec_service.recommend(request.constraints, request.weights)
    return candidates
