from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class PredictionRequest(BaseModel):
    composition: Dict[str, float] = Field(
        ..., 
        example={"Ti": 0.70, "Nb": 0.20, "Zr": 0.05, "Ta": 0.05},
        description="Elemental weight fractions (should sum to 1.0)"
    )
    model_name: Optional[str] = Field("catboost", description="Surrogate model type (catboost, xgboost, mlp)")

class PredictionResponse(BaseModel):
    composition: Dict[str, float]
    descriptors: Dict[str, float]
    predicted_properties: Dict[str, float]

class ExplanationRequest(BaseModel):
    composition: Dict[str, float] = Field(..., example={"Ti": 70.0, "Nb": 20.0, "Zr": 5.0, "Ta": 5.0})
    target_property: str = Field("elastic_modulus", description="The property prediction to explain (e.g. elastic_modulus, uts)")

class ExplanationResponse(BaseModel):
    base_value: float
    prediction: float
    shap_values: Dict[str, float]
    textual_explanation: str

class ObjectiveSchema(BaseModel):
    name: str = Field(..., description="elastic_modulus, yield_strength, uts, corrosion_rate, biocompatibility_score")
    target: str = Field(..., description="minimize or maximize")
    weight: float = Field(0.25, description="Priority weight")

class OptimizationRequest(BaseModel):
    algorithm: str = Field("nsga-ii", description="nsga-ii, nsga-iii, bayesian")
    population_size: int = Field(50, ge=10, le=500)
    generations: int = Field(20, ge=5, le=200)
    objectives: List[ObjectiveSchema]
    constraints: Optional[Dict[str, float]] = Field(None, description="e.g. {'elastic_modulus_max': 45.0, 'uts_min': 800.0}")

class OptimizedCandidate(BaseModel):
    composition: Dict[str, float]
    properties: Dict[str, float]
    aus_score: float

class OptimizationResponse(BaseModel):
    run_id: str
    candidates: List[OptimizedCandidate]

class RecommendationRequest(BaseModel):
    constraints: Dict[str, float] = Field(
        ...,
        example={"elastic_modulus_max": 45.0, "uts_min": 800.0, "corrosion_rate_max": 0.05}
    )
    weights: Optional[Dict[str, float]] = Field(
        None, 
        example={"property": 0.5, "rag": 0.3, "graph": 0.2}
    )

class CitationSchema(BaseModel):
    title: str
    authors: str
    journal: str
    year: int
    doi: str
    relevance_score: float
    matching_snippet: str

class RecommendedAlloySchema(BaseModel):
    name: str
    composition: Dict[str, float]
    properties: Dict[str, float]
    descriptors: Dict[str, float]
    is_novel: bool
    aus_score: float
    rag_score: float
    graph_score: float
    recommendation_score: float
    confidence_score: float
    citations: List[CitationSchema]

class RAGQueryRequest(BaseModel):
    composition: Dict[str, float]
    n_results: Optional[int] = Field(3, ge=1, le=10)

class IngestionRequest(BaseModel):
    name: str = Field(..., example="Custom-Ti-35Nb")
    composition: Dict[str, float] = Field(..., example={"Ti": 0.65, "Nb": 0.35})
    phase: str = Field("beta", example="beta")
    properties: Dict[str, float] = Field(
        ..., 
        example={
            "elastic_modulus": 40.0,
            "yield_strength": 800.0,
            "uts": 900.0,
            "corrosion_rate": 0.002,
            "biocompatibility_score": 0.98
        }
    )

