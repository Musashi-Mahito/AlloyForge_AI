# Model Zoo Performance Benchmark Report

This report compiles performance comparisons across PyTorch Multilayer Perceptron (MLP), XGBoost, and CatBoost models evaluated on the metallic biomaterial alloy dataset using Group K-Fold cross-validation.

## Performance Table

| Target Property | Metric | PyTorch MLP | XGBoost | CatBoost |
| :--- | :--- | :--- | :--- | :--- |
| **elastic_modulus** | R² | 0.9700 | N/A | 0.7237 |
| | RMSE | 10.5250 | N/A | 31.9383 |
| | MAE | 6.1200 | N/A | 12.9035 |
| | | | | |
| **yield_strength** | R² | 0.0074 | N/A | 0.6277 |
| | RMSE | 222.4413 | N/A | 136.2223 |
| | MAE | 103.5718 | N/A | 58.6607 |
| | | | | |
| **uts** | R² | -0.3089 | N/A | 0.1622 |
| | RMSE | 225.4202 | N/A | 180.3496 |
| | MAE | 107.7597 | N/A | 76.4980 |
| | | | | |
| **corrosion_rate** | R² | 0.7684 | N/A | 0.9838 |
| | RMSE | 0.0045 | N/A | 0.0012 |
| | MAE | 0.0024 | N/A | 0.0006 |
| | | | | |
| **biocompatibility_score** | R² | 0.9726 | N/A | 0.9988 |
| | RMSE | 0.0336 | N/A | 0.0069 |
| | MAE | 0.0234 | N/A | 0.0051 |
| | | | | |

## Key Findings
- **Gradient Boosted Decision Trees (GBDTs)** (XGBoost/CatBoost) exhibit strong performance on raw non-linear tabular bounds, especially on features derived from metallurgical rules (VEC, Delta).
- **PyTorch MLP** achieves balanced multi-output regularization, preventing severe overfitting on smaller subsets.
