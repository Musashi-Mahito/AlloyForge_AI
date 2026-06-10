import os
import numpy as np
import shap
from typing import Dict, Any, Tuple
from pipelines.optimization.nsga import SurrogateModelEvaluator, ELEMENT_LIST
from pipelines.features.generation import calculate_metallurgical_descriptors

class PredictionService:
    def __init__(self, model_dir: str = "models_artifacts"):
        self.evaluator = SurrogateModelEvaluator(model_dir)
        self.model_dir = model_dir
        self.explainers = {}

    def predict(self, composition_wt: Dict[str, float]) -> Dict[str, Any]:
        """Predicts all physical properties from composition."""
        # 1. Normalize composition to sum to 100
        total = sum(composition_wt.values())
        if total == 0:
            norm_comp = {el: 0.0 for el in ELEMENT_LIST}
        else:
            norm_comp = {el: (wt / total) * 100.0 for el, wt in composition_wt.items()}
            
        props = self.evaluator.predict(norm_comp)
        
        # Calculate descriptors to return to frontend
        desc = calculate_metallurgical_descriptors(norm_comp)
        
        return {
            "composition": norm_comp,
            "descriptors": desc,
            "predicted_properties": props
        }

    def explain(self, composition_wt: Dict[str, float], target_property: str) -> Dict[str, Any]:
        """Calculates SHAP values explaining the model's prediction for target_property."""
        # Normalize
        total = sum(composition_wt.values())
        norm_comp = {el: (wt / total) * 100.0 for el, wt in composition_wt.items()} if total > 0 else {el: 0.0 for el in ELEMENT_LIST}
        
        # Compute inputs vector
        desc = calculate_metallurgical_descriptors(norm_comp)
        features_vector = []
        feature_names = []
        for el in ELEMENT_LIST:
            features_vector.append(norm_comp.get(el, 0.0))
            feature_names.append(el)
        for key in ["vec", "delta", "delta_h_mix", "delta_s_mix", "delta_chi", "bo_bar", "md_bar"]:
            features_vector.append(desc[key])
            feature_names.append(key)
            
        features_arr = np.array([features_vector])
        
        # Load model to compute SHAP
        model = self.evaluator.models.get(target_property)
        if not model:
            # Fallback mock SHAP values if models are not trained yet
            return self._get_mock_shap(norm_comp, desc, target_property)
            
        # Get or create tree explainer
        if target_property not in self.explainers:
            try:
                self.explainers[target_property] = shap.TreeExplainer(model)
            except Exception:
                # Fallback to general explainer
                self.explainers[target_property] = shap.Explainer(model)
                
        explainer = self.explainers[target_property]
        shap_values = explainer(features_arr)
        
        # Extract values
        base_value = float(explainer.expected_value) if hasattr(explainer, "expected_value") else float(shap_values.base_values[0])
        prediction = float(shap_values.values[0].sum() + base_value)
        
        contributions = {}
        for name, val in zip(feature_names, shap_values.values[0]):
            if abs(val) > 0.001:  # filter negligible impacts
                contributions[name] = round(float(val), 4)
                
        # Generate textual explanation
        major_contributors = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        text_desc = []
        for feat, val in major_contributors:
            direction = "increased" if val > 0 else "decreased"
            text_desc.append(f"{feat} ({direction} target by {abs(val):.2f})")
            
        explanation_text = f"The model predicted {prediction:.2f} for {target_property}. The primary drivers were: " + ", ".join(text_desc) + "."
        
        return {
            "base_value": base_value,
            "prediction": prediction,
            "shap_values": contributions,
            "textual_explanation": explanation_text
        }

    def _get_mock_shap(self, comp: Dict, desc: Dict, target: str) -> Dict:
        """Fallback mock explanation in case of missing model files."""
        base_values = {
            "elastic_modulus": 75.0,
            "yield_strength": 600.0,
            "uts": 800.0,
            "corrosion_rate": 0.015,
            "biocompatibility_score": 0.5
        }
        predictions = {
            "elastic_modulus": 38.5,
            "yield_strength": 890.0,
            "uts": 950.0,
            "corrosion_rate": 0.002,
            "biocompatibility_score": 0.98
        }
        
        base = base_values.get(target, 50.0)
        pred = predictions.get(target, 60.0)
        
        # Generate sample contributions
        shap_dict = {
            "VEC": -15.4 if target == "elastic_modulus" else 20.0,
            "delta": -8.2 if target == "elastic_modulus" else 15.0,
            "Nb": -12.3 if target == "elastic_modulus" else 50.0,
            "Zr": -3.2 if target == "elastic_modulus" else 10.0,
            "Ta": -2.0 if target == "elastic_modulus" else 5.0
        }
        
        return {
            "base_value": base,
            "prediction": pred,
            "shap_values": shap_dict,
            "textual_explanation": f"The mock model predicted {pred:.2f} for {target}. The primary structural driver was VEC lowering (shifting composition to beta phase), combined with strong biocompatibility contributions from Nb and Zr."
        }
