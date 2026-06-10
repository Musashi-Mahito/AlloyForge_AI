import os
import joblib
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor

XGBOOST_AVAILABLE = True
try:
    import xgboost as xgb
except Exception:
    XGBOOST_AVAILABLE = False
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.pytorch

# Setup MLflow Tracking
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
mlflow.set_experiment("Alloy_Properties_Prediction")

# Constants
FEATURES = ["Ti", "Nb", "Zr", "Ta", "Mo", "Fe", "Al", "V", "Cr", "Ni", "vec", "delta", "delta_h_mix", "delta_s_mix", "delta_chi", "bo_bar", "md_bar"]
TARGETS = ["elastic_modulus", "yield_strength", "uts", "corrosion_rate", "biocompatibility_score"]

def get_base_element_group(df: pd.DataFrame) -> pd.Series:
    """Groups alloys by their dominant chemical element to prevent data leakage during CV."""
    elements = ["Ti", "Nb", "Zr", "Ta", "Mo", "Fe", "Al", "V", "Cr", "Ni"]
    # Return the element with the highest percentage weight for each row
    return df[elements].idxmax(axis=1)

# Multi-output PyTorch MLP Class
class AlloyMLP(nn.Module):
    def __init__(self, input_dim=len(FEATURES), output_dim=len(TARGETS)):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, output_dim)
        )
        
    def forward(self, x):
        return self.net(x)

def train_pytorch_mlp(X_train, y_train, X_val, y_val, epochs=150, batch_size=32):
    """Trains a multi-output PyTorch Neural Network."""
    # Scale data
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    
    X_train_scaled = scaler_x.fit_transform(X_train)
    y_train_scaled = scaler_y.fit_transform(y_train)
    X_val_scaled = scaler_x.transform(X_val)
    y_val_scaled = scaler_y.transform(y_val)
    
    # Create DataLoaders
    train_dataset = TensorDataset(torch.tensor(X_train_scaled, dtype=torch.float32), torch.tensor(y_train_scaled, dtype=torch.float32))
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    
    model = AlloyMLP(input_dim=X_train.shape[1], output_dim=y_train.shape[1])
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
    
    # Training Loop
    for epoch in range(epochs):
        model.train()
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            
    # Evaluation
    model.eval()
    with torch.no_grad():
        val_preds_scaled = model(torch.tensor(X_val_scaled, dtype=torch.float32)).numpy()
        val_preds = scaler_y.inverse_transform(val_preds_scaled)
        
    return model, scaler_x, scaler_y, val_preds

def train_and_evaluate_all_models(data_path: str):
    """Main training routine doing GroupKFold CV and logging to MLflow."""
    df = pd.read_parquet(data_path)
    X = df[FEATURES].values
    y = df[TARGETS].values
    groups = get_base_element_group(df).values
    
    gkf = GroupKFold(n_splits=3)
    
    # Save directory
    model_dir = "models_artifacts"
    os.makedirs(model_dir, exist_ok=True)
    
    print("Starting ML Model Zoo Training Pipeline...")
    
    # 1. Train PyTorch Multi-Output Model
    print("\n--- Training PyTorch MLP ---")
    with mlflow.start_run(run_name="PyTorch_MLP_MultiOutput"):
        fold_rmse, fold_r2 = [], []
        # Store predictions across all folds
        all_val_preds = np.zeros_like(y)
        
        for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=groups)):
            model, scaler_x, scaler_y, val_preds = train_pytorch_mlp(
                X[train_idx], y[train_idx], X[val_idx], y[val_idx]
            )
            all_val_preds[val_idx] = val_preds
            
            # Save fold scaler/model artifact (last fold saved as representative model)
            if fold == gkf.n_splits - 1:
                torch.save(model.state_dict(), f"{model_dir}/pytorch_mlp.pt")
                joblib.dump(scaler_x, f"{model_dir}/scaler_x.pkl")
                joblib.dump(scaler_y, f"{model_dir}/scaler_y.pkl")
        
        # Log aggregated metrics
        mlflow.log_param("epochs", 150)
        mlflow.log_param("batch_size", 32)
        mlflow.log_param("model_type", "pytorch_mlp")
        
        for t_idx, target in enumerate(TARGETS):
            rmse = root_mean_squared_error(y[:, t_idx], all_val_preds[:, t_idx])
            mae = mean_absolute_error(y[:, t_idx], all_val_preds[:, t_idx])
            r2 = r2_score(y[:, t_idx], all_val_preds[:, t_idx])
            
            print(f"MLP -> Target: {target:<25} | RMSE: {rmse:.4f} | MAE: {mae:.4f} | R²: {r2:.4f}")
            mlflow.log_metric(f"{target}_rmse", rmse)
            mlflow.log_metric(f"{target}_r2", r2)
            
        # Log PyTorch Model
        mlflow.pytorch.log_model(model, "model")
        
    # 2. Train XGBoost Independent Regressors
    if XGBOOST_AVAILABLE:
        print("\n--- Training XGBoost Regressors ---")
        try:
            with mlflow.start_run(run_name="XGBoost_Regressors"):
                mlflow.log_param("model_type", "xgboost")
                mlflow.log_param("max_depth", 6)
                mlflow.log_param("n_estimators", 150)
                
                for t_idx, target in enumerate(TARGETS):
                    all_val_preds = np.zeros(len(y))
                    # Hyperparameters
                    xgb_model = xgb.XGBRegressor(max_depth=6, n_estimators=150, random_state=42)
                    
                    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y[:, t_idx], groups=groups)):
                        xgb_model.fit(X[train_idx], y[train_idx, t_idx])
                        all_val_preds[val_idx] = xgb_model.predict(X[val_idx])
                        
                        if fold == gkf.n_splits - 1:
                            xgb_model.save_model(f"{model_dir}/xgb_{target}.json")
                    
                    rmse = root_mean_squared_error(y[:, t_idx], all_val_preds)
                    mae = mean_absolute_error(y[:, t_idx], all_val_preds)
                    r2 = r2_score(y[:, t_idx], all_val_preds)
                    
                    print(f"XGB -> Target: {target:<25} | RMSE: {rmse:.4f} | MAE: {mae:.4f} | R²: {r2:.4f}")
                    mlflow.log_metric(f"{target}_rmse", rmse)
                    mlflow.log_metric(f"{target}_r2", r2)
        except Exception as e:
            print(f"XGBoost runtime load error: {e}. Skipping XGBoost.")
    else:
        print("\n--- XGBoost Not Available (libomp missing). Skipping XGBoost Regressors ---")
            
    # 3. Train CatBoost Independent Regressors
    print("\n--- Training CatBoost Regressors ---")
    with mlflow.start_run(run_name="CatBoost_Regressors"):
        mlflow.log_param("model_type", "catboost")
        mlflow.log_param("iterations", 200)
        
        for t_idx, target in enumerate(TARGETS):
            all_val_preds = np.zeros(len(y))
            cat_model = CatBoostRegressor(iterations=200, depth=6, verbose=0, random_seed=42)
            
            for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y[:, t_idx], groups=groups)):
                cat_model.fit(X[train_idx], y[train_idx, t_idx])
                all_val_preds[val_idx] = cat_model.predict(X[val_idx])
                
                if fold == gkf.n_splits - 1:
                    cat_model.save_model(f"{model_dir}/cat_{target}.bin")
            
            rmse = root_mean_squared_error(y[:, t_idx], all_val_preds)
            mae = mean_absolute_error(y[:, t_idx], all_val_preds)
            r2 = r2_score(y[:, t_idx], all_val_preds)
            
            print(f"CAT -> Target: {target:<25} | RMSE: {rmse:.4f} | MAE: {mae:.4f} | R²: {r2:.4f}")
            mlflow.log_metric(f"{target}_rmse", rmse)
            mlflow.log_metric(f"{target}_r2", r2)

if __name__ == "__main__":
    train_and_evaluate_all_models("data/raw/alloy_dataset.parquet")
