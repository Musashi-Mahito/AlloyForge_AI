from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any
from backend.app.services.rag_service import RAGService
from backend.app.services.graph_service import GraphService
from backend.app.models.schemas import CitationSchema
import json

router = APIRouter()
rag_service = RAGService()
graph_service = GraphService()

@router.get("/evidence", response_model=List[CitationSchema])
def get_scientific_evidence(
    composition: str = Query(..., description="JSON representation of weight percentage composition, e.g., {'Ti':70,'Nb':20,'Zr':10}")
):
    try:
        comp_dict = json.loads(composition)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid composition query. Must be a valid JSON dictionary.")
        
    citations = rag_service.query_evidence(comp_dict)
    return citations

@router.get("/graph-neighborhood")
def get_graph_neighborhood(
    alloy_name: str = Query(..., description="The name of the alloy to inspect, e.g., Ti-35Nb-7Zr-5Ta")
):
    neighborhood = graph_service.get_alloy_neighborhood(alloy_name)
    return neighborhood
