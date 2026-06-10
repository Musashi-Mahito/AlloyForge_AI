import os
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions
import optuna
import math
from typing import Dict, List, Tuple
from pipelines.features.generation import calculate_metallurgical_descriptors, ELEMENTAL_DATA

ELEMENT_LIST = ["Ti", "Nb", "Zr", "Ta", "Mo", "Fe", "Al", "V", "Cr", "Ni"]

class SurrogateModelEvaluator:
    """Loads and runs surrogate GBDT models to predict physical properties from composition."""
    def __init__(self, model_dir: str = "models_artifacts"):
        self.models = {}
        for target in ["elastic_modulus", "yield_strength", "uts", "corrosion_rate", "biocompatibility_score"]:
            model_path = f"{model_dir}/cat_{target}.bin"
            if os.path.exists(model_path):
                model = CatBoostRegressor()
                model.load_model(model_path)
                self.models[target] = model
            else:
                self.models[target] = None

    def is_ready(self) -> bool:
        return all(m is not None for m in self.models.values())

    def predict(self, composition_wt: Dict[str, float]) -> Dict[str, float]:
        # Form features list
        descriptors = calculate_metallurgical_descriptors(composition_wt)
        
        # Build features vector
        features = []
        for el in ELEMENT_LIST:
            features.append(composition_wt.get(el, 0.0))
        for key in ["vec", "delta", "delta_h_mix", "delta_s_mix", "delta_chi", "bo_bar", "md_bar"]:
            features.append(descriptors[key])
            
        features_arr = np.array([features])
        
        predictions = {}
        for target, model in self.models.items():
            if model:
                predictions[target] = float(model.predict(features_arr)[0])
            else:
                # Fallbacks in case models are not trained yet
                predictions[target] = 100.0
                
        return predictions

def calculate_aus(properties: Dict[str, float], composition_wt: Dict[str, float], descriptors: Dict[str, float],
                  weights: Dict[str, float] = None) -> float:
    """
    Calculates the Alloy Utility Score (AUS) for a composition.
    AUS = w_mech * S_mech + w_corr * S_corr + w_biocompat * S_biocompat + w_mfg * S_mfg
    """
    if weights is None:
        weights = {"mech": 0.35, "corr": 0.25, "biocompat": 0.25, "mfg": 0.15}
        
    # 1. Mechanical Score: Target E ~ 30 GPa (bone matching), Maximize UTS
    E = properties.get("elastic_modulus", 100.0)
    uts = properties.get("uts", 500.0)
    
    # E deviation penalty (Gaussian centered at 30 GPa, width sigma=15)
    S_E = math.exp(-((E - 30.0) ** 2) / (2.0 * (15.0 ** 2)))
    # Normalized UTS (clamped between 0 and 1)
    S_uts = min(1.0, max(0.0, (uts - 200.0) / 1200.0))
    S_mech = 0.5 * S_E + 0.5 * S_uts
    
    # 2. Corrosion Score: Exp decay based on corrosion rate (mm/year)
    cr = properties.get("corrosion_rate", 0.05)
    S_corr = math.exp(-40.0 * cr) # Decays to near 0 around CR = 0.1
    
    # 3. Biocompatibility Score: Weighted toxicity indices
    biocompat_sum = 0.0
    total_wt = sum(composition_wt.values())
    if total_wt > 0:
        for el, wt in composition_wt.items():
            toxicity = ELEMENTAL_DATA.get(el, {}).get("biocompatibility", 0.0)
            biocompat_sum += (wt / total_wt) * toxicity
    # Normalize biocompatibility to [0, 1] range (Ni is -0.5, so we shift and scale)
    S_biocompat = min(1.0, max(0.0, biocompat_sum))
    
    # 4. Manufacturability Score: stability of mixture based on Mixing Enthalpy
    dH = descriptors.get("delta_h_mix", 0.0)
    # Target Delta H mix is near 0 or slightly negative for solid solution stability. Avoid massive intermetallic formation.
    S_mfg = math.exp(-abs(dH) / 25.0)
    
    # Combine
    aus = (
        weights["mech"] * S_mech +
        weights["corr"] * S_corr +
        weights["biocompat"] * S_biocompat +
        weights["mfg"] * S_mfg
    )
    return round(aus, 5)

# NSGA-II Problem Class
class AlloyDesignProblem(ElementwiseProblem):
    def __init__(self, evaluator: SurrogateModelEvaluator):
        self.evaluator = evaluator
        # 10 Decision variables corresponding to composition weights of:
        # Ti, Nb, Zr, Ta, Mo, Fe, Al, V, Cr, Ni
        super().__init__(
            n_var=10,
            n_obj=5,  # Minimize E, Minimize CR, Maximize UTS, Maximize Biocompatibility, Maximize AUS
            n_constr=2, # E <= 45 GPa, UTS >= 800 MPa
            xl=0.0,
            xu=1.0
        )

    def _evaluate(self, x, out, *args, **kwargs):
        # 1. Normalize variables to sum to 1.0 (simplex mapping)
        total = np.sum(x)
        if total == 0:
            wt_percentages = [1.0 / 10] * 10
        else:
            wt_percentages = (x / total) * 1.0
            
        composition_wt = {ELEMENT_LIST[i]: float(wt_percentages[i]) for i in range(10)}
        
        # Calculate descriptors & predict properties
        descriptors = calculate_metallurgical_descriptors(composition_wt)
        props = self.evaluator.predict(composition_wt)
        aus = calculate_aus(props, composition_wt, descriptors)
        
        # Pymoo minimizes objectives, so we negate UTS, biocompatibility, and AUS
        out["F"] = [
            props["elastic_modulus"],                   # Minimize
            props["corrosion_rate"],                    # Minimize
            -props["uts"],                              # Maximize
            -props["biocompatibility_score"],            # Maximize
            -aus                                        # Maximize
        ]
        
        # Constraints: E <= 45 GPa -> E - 45 <= 0
        # UTS >= 800 MPa -> 800 - UTS <= 0
        out["G"] = [
            props["elastic_modulus"] - 45.0,
            800.0 - props["uts"]
        ]

class AlloyOptimizationEngine:
    def __init__(self, model_dir: str = "models_artifacts"):
        self.evaluator = SurrogateModelEvaluator(model_dir)

    def run_nsga2(self, generations: int = 50, pop_size: int = 100) -> List[Dict]:
        """Runs NSGA-II genetic algorithm to generate Pareto-optimal alloys."""
        problem = AlloyDesignProblem(self.evaluator)
        algorithm = NSGA2(pop_size=pop_size)
        
        res = minimize(
            problem,
            algorithm,
            ('n_gen', generations),
            seed=42,
            verbose=False
        )
        
        # Process candidates
        candidates = []
        if res.X is not None:
            # Handle case of single vs multiple return solutions
            X_sol = [res.X] if res.X.ndim == 1 else res.X
            for x in X_sol:
                total = np.sum(x)
                wt = (x / total) * 1.0 if total > 0 else np.array([0.1]*10)
                comp = {ELEMENT_LIST[i]: round(float(wt[i]), 4) for i in range(10) if wt[i] > 0.0005}
                
                desc = calculate_metallurgical_descriptors(comp)
                props = self.evaluator.predict(comp)
                aus = calculate_aus(props, comp, desc)
                
                candidates.append({
                    "composition": comp,
                    "properties": props,
                    "aus_score": aus
                })
        
        # Sort by AUS score descending
        candidates = sorted(candidates, key=lambda c: c["aus_score"], reverse=True)
        return candidates[:50] # return top 50

    def run_bayesian_opt(self, n_trials: int = 50) -> Dict:
        """Runs Optuna Bayesian Optimization to find composition maximizing AUS."""
        def objective(trial):
            # Propose weights for each element
            weights = {}
            for el in ELEMENT_LIST:
                weights[el] = trial.suggest_float(el, 0.0, 1.0)
                
            total = sum(weights.values())
            if total == 0:
                comp = {el: 0.1 for el in ELEMENT_LIST}
            else:
                comp = {el: (weights[el] / total) * 1.0 for el in ELEMENT_LIST}
                
            desc = calculate_metallurgical_descriptors(comp)
            props = self.evaluator.predict(comp)
            
            # Constraint penaltys
            penalty = 0.0
            if props["elastic_modulus"] > 45.0:
                penalty += (props["elastic_modulus"] - 45.0) * 0.1
            if props["uts"] < 800.0:
                penalty += (800.0 - props["uts"]) * 0.01
                
            aus = calculate_aus(props, comp, desc)
            return aus - penalty # maximize penalized score
            
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)
        
        best_trial = study.best_trial
        best_weights = best_trial.params
        total = sum(best_weights.values())
        best_comp = {el: round((best_weights[el] / total) * 1.0, 4) for el in ELEMENT_LIST}
        best_comp = {el: val for el, val in best_comp.items() if val > 0.0005}
        
        desc = calculate_metallurgical_descriptors(best_comp)
        props = self.evaluator.predict(best_comp)
        aus = calculate_aus(props, best_comp, desc)
        
        return {
            "composition": best_comp,
            "properties": props,
            "aus_score": aus
        }

if __name__ == "__main__":
    engine = AlloyOptimizationEngine()
    print("Running Bayesian Optimization (Optuna)...")
    res_bo = engine.run_bayesian_opt(n_trials=30)
    print("Best Alloy composition from Bayesian Opt:")
    print(res_bo)
    
    print("\nRunning Multi-Objective NSGA-II...")
    res_nsga = engine.run_nsga2(generations=20, pop_size=50)
    print(f"Generated {len(res_nsga)} Pareto candidates. Best candidate properties:")
    if res_nsga:
        print(res_nsga[0])
