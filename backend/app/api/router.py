from fastapi import APIRouter
from backend.app.api.endpoints import predict, explain, optimize, recommend, retrieve, ingest

api_router = APIRouter()

api_router.include_router(predict.router, prefix="/predict", tags=["Predict"])
api_router.include_router(explain.router, prefix="/explain", tags=["Explain"])
api_router.include_router(optimize.router, prefix="/optimize", tags=["Optimize"])
api_router.include_router(recommend.router, prefix="/recommend", tags=["Recommend"])
api_router.include_router(retrieve.router, prefix="/retrieve", tags=["Retrieve"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
