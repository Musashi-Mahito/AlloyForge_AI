import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Alloy Discovery Platform"
    API_V1_STR: str = "/api/v1"
    
    # Databases & Infrastructure
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://alloy_user:alloy_password@localhost:5432/alloy_db"
    )
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "alloy_graph_password")
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    CHROMA_HOST: str = os.getenv("CHROMA_SERVER_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_SERVER_HTTP_PORT", "8000"))
    
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    
    # Model storage path
    MODEL_DIR: str = os.getenv("MODEL_DIR", "./models_artifacts")

settings = Settings()
