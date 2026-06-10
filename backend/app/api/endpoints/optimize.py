from fastapi import APIRouter, HTTPException
import uuid
import time
from backend.app.models.schemas import OptimizationRequest, OptimizationResponse, OptimizedCandidate
from pipelines.optimization.nsga import AlloyOptimizationEngine

router = APIRouter()
opt_engine = AlloyOptimizationEngine()

@router.post("/", response_model=OptimizationResponse)
def run_optimization(request: OptimizationRequest):
    start_time = time.time()
    run_id = str(uuid.uuid4())
    
    # Check if models are loaded/ready
    if not opt_engine.evaluator.is_ready():
        # Proceed but let the user know mock/fallback properties might be generated
        print("Surrogate models not fully initialized yet in optimization engine. Relying on default fallbacks.")
        
    candidates = []
    
    if request.algorithm.lower() in ["nsga-ii", "nsga-iii"]:
        results = opt_engine.run_nsga2(
            generations=request.generations,
            pop_size=request.population_size
        )
        for r in results:
            candidates.append(
                OptimizedCandidate(
                    composition=r["composition"],
                    properties=r["properties"],
                    aus_score=r["aus_score"]
                )
            )
    elif request.algorithm.lower() == "bayesian":
        # Optuna Bayesian optimization runs single-target (maximizes AUS)
        r = opt_engine.run_bayesian_opt(n_trials=request.generations)
        candidates.append(
            OptimizedCandidate(
                composition=r["composition"],
                properties=r["properties"],
                aus_score=r["aus_score"]
            )
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid algorithm. Supported: nsga-ii, nsga-iii, bayesian")
        
    # Write optimization run audit to database in background could be added here
    
    return OptimizationResponse(
        run_id=run_id,
        candidates=candidates
    )
