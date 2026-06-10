import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.inspection import permutation_importance
import shap
from pipelines.models.train import FEATURES, TARGETS

def run_feature_selection(data_path: str, target: str = "elastic_modulus"):
    df = pd.read_parquet(data_path)
    X = df[FEATURES]
    y = df[target]
    
    print(f"Running Feature Selection Analysis for Target: {target}")
    
    # 1. Mutual Information
    mi_scores = mutual_info_regression(X, y, random_state=42)
    mi_df = pd.DataFrame({"Feature": FEATURES, "Mutual_Information": mi_scores})
    
    # 2. Permutation Importance (using RandomForest)
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
    perm_imp = permutation_importance(rf, X, y, n_repeats=5, random_state=42)
    perm_df = pd.DataFrame({
        "Feature": FEATURES, 
        "Permutation_Importance_Mean": perm_imp.importances_mean,
        "Permutation_Importance_Std": perm_imp.importances_std
    })
    
    # 3. SHAP Feature Importance
    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X)
    shap_mean_abs = np.abs(shap_values).mean(axis=0)
    shap_df = pd.DataFrame({"Feature": FEATURES, "SHAP_Importance": shap_mean_abs})
    
    # Merge and Sort
    merged = mi_df.merge(perm_df, on="Feature").merge(shap_df, on="Feature")
    merged = merged.sort_values(by="SHAP_Importance", ascending=False)
    
    print("\nFeature Importance Rankings:")
    print(merged.to_string(index=False))
    
    # Save Report
    out_dir = "models_artifacts"
    os.makedirs(out_dir, exist_ok=True)
    report_path = f"{out_dir}/feature_selection_{target}.csv"
    merged.to_csv(report_path, index=False)
    print(f"Saved feature importance rankings to: {report_path}")

if __name__ == "__main__":
    run_feature_selection("data/raw/alloy_dataset.parquet", target="elastic_modulus")
