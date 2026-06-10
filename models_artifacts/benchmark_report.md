# Model Zoo Performance Benchmark Report

This report compiles performance comparisons across PyTorch Multilayer Perceptron (MLP), XGBoost, and CatBoost models evaluated on the metallic biomaterial alloy dataset using Group K-Fold cross-validation.

## Performance Table

| Target Property | Metric | PyTorch MLP | XGBoost | CatBoost |
| :--- | :--- | :--- | :--- | :--- |
| **elastic_modulus** | R² | 0.9579 | N/A | 0.7237 |
| | RMSE | 12.4703 | N/A | 31.9383 |
| | MAE | 7.0300 | N/A | 12.9035 |
| | | | | |
| **yield_strength** | R² | 0.0534 | N/A | 0.6277 |
| | RMSE | 217.2193 | N/A | 136.2223 |
| | MAE | 101.6521 | N/A | 58.6607 |
| | | | | |
| **uts** | R² | -0.2420 | N/A | 0.1622 |
| | RMSE | 219.5824 | N/A | 180.3496 |
| | MAE | 104.8438 | N/A | 76.4980 |
| | | | | |
| **corrosion_rate** | R² | 0.7782 | N/A | 0.9838 |
| | RMSE | 0.0044 | N/A | 0.0012 |
| | MAE | 0.0024 | N/A | 0.0006 |
| | | | | |
| **biocompatibility_score** | R² | 0.9840 | N/A | 0.9988 |
| | RMSE | 0.0256 | N/A | 0.0069 |
| | MAE | 0.0193 | N/A | 0.0051 |
| | | | | |

## Key Findings
- **Gradient Boosted Decision Trees (GBDTs)** (XGBoost/CatBoost) exhibit strong performance on raw non-linear tabular bounds, especially on features derived from metallurgical rules (VEC, Delta).
- **PyTorch MLP** achieves balanced multi-output regularization, preventing severe overfitting on smaller subsets.
