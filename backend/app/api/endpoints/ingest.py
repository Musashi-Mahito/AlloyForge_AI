from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.schemas import IngestionRequest
from backend.app.models.db_models import DBAlloy, DBProperty, DBMetallurgicalFeature
from pipelines.features.generation import calculate_metallurgical_descriptors
from neo4j import GraphDatabase
import os

router = APIRouter()

@router.post("/")
def ingest_alloy(request: IngestionRequest, db: Session = Depends(get_db)):
    # 1. Verify weight fractions sum to 100%
    total = sum(request.composition.values())
    if abs(total - 100.0) > 1.0:
        raise HTTPException(status_code=400, detail="Composition percentages must sum to approximately 100%.")

    # 2. Check if name already exists
    existing = db.query(DBAlloy).filter(DBAlloy.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Alloy with name '{request.name}' already exists.")

    try:
        # Calculate descriptors dynamically
        desc = calculate_metallurgical_descriptors(request.composition)
        
        # Save to SQL database
        db_alloy = DBAlloy(
            name=request.name,
            composition=request.composition,
            phase=request.phase
        )
        db.add(db_alloy)
        db.flush() # get alloy ID
        
        db_props = DBProperty(
            alloy_id=db_alloy.id,
            elastic_modulus=request.properties.get("elastic_modulus", 100.0),
            yield_strength=request.properties.get("yield_strength", 600.0),
            uts=request.properties.get("uts", 800.0),
            corrosion_rate=request.properties.get("corrosion_rate", 0.01),
            biocompatibility_score=request.properties.get("biocompatibility_score", 0.9),
            is_experimental=True
        )
        
        db_feat = DBMetallurgicalFeature(
            alloy_id=db_alloy.id,
            vec=desc["vec"],
            delta=desc["delta"],
            delta_h_mix=desc["delta_h_mix"],
            delta_s_mix=desc["delta_s_mix"],
            delta_chi=desc["delta_chi"],
            bo_bar=desc.get("bo_bar"),
            md_bar=desc.get("md_bar")
        )
        
        db.add(db_props)
        db.add(db_feat)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"SQL Database write failure: {e}")

    # 3. Synchronize with Neo4j Knowledge Graph
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_pw = os.getenv("NEO4J_PASSWORD", "alloy_graph_password")
    
    graph_msg = "Neo4j is not connected."
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pw))
        driver.verify_connectivity()
        
        with driver.session() as session:
            # Create alloy node and phase edge
            session.run(
                "MERGE (a:Alloy {name: $name}) SET a.phase = $phase, a.aus_score = $aus",
                {"name": request.name, "phase": request.phase, "aus": request.properties.get("biocompatibility_score", 0.9)}
            )
            session.run("MERGE (ph:Phase {name: $phase})", {"phase": request.phase})
            session.run("""
            MATCH (a:Alloy {name: $name})
            MATCH (ph:Phase {name: $phase})
            MERGE (a)-[:HAS_PHASE]->(ph)
            """, {"name": request.name, "phase": request.phase})
            
            # Create element edges
            for el, wt in request.composition.items():
                if wt > 0:
                    session.run("MERGE (e:Element {symbol: $el})", {"el": el})
                    session.run("""
                    MATCH (a:Alloy {name: $name})
                    MATCH (e:Element {symbol: $el})
                    MERGE (a)-[r:CONTAINS]->(e)
                    SET r.fraction = $wt
                    """, {"name": request.name, "el": el, "wt": wt})
                    
        driver.close()
        graph_msg = "Neo4j graph successfully updated."
    except Exception as e:
        graph_msg = f"Skipped Neo4j graph update (Neo4j offline): {e}"

    return {
        "status": "success",
        "message": f"Alloy '{request.name}' successfully ingested. {graph_msg}",
        "alloy_id": db_alloy.id,
        "descriptors": desc
    }
