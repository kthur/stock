# Project: Stock Trading System Autonomous Enhancement

## Architecture
- `trading_system/`: Core python package & scripts.
- `trading_system/run_pipeline.py`: Main orchestration pipeline.
- `trading_system/merge_predictions.py`: Ensemble merger & dynamic weighting.
- `trading_system/generate_report.py`: GitHub Pages report generator.
- `trading_system/scripts/verify_gha_artifacts.py`: GHA pipeline artifact verifier.
- `src/ai/`: Prediction models (Regression, Surge, Lead-Lag, VCP, Optuna, Ensemble).
- `src/trading/`: KIS trading API execution, ATR trailing stop, risk limits.
- `src/portfolio/`: HRP asset allocation & regime trend calculators.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Exploration & Gap Analysis | Baseline test run, code audit for R1, R2, R3 | none | DONE |
| 2 | R1 AI Model Precision & Dynamic Ensemble | Optuna HPO for 5 strategies + 2D regime Sharpe weighting | M1 | IN_PROGRESS |
| 3 | R2 GitHub Pages & HRP UX Enhancement | HRP allocation chart, regime trends, Naver/Foreign links | M1 | PLANNED |
| 4 | R3 KIS Trading Safety & ATR Trailing Stop | ATR trailing stop, portfolio exposure limits, order safety | M1 | PLANNED |
| 5 | Verification & Forensic Audit | Pytest 100%, verify_gha_artifacts PASSED, Auditor verdict CLEAN | M2, M3, M4 | PLANNED |

## Interface Contracts
- Optuna HPO: Output tuned hyperparameters to `models/tuned_params.json` or dynamic load during training.
- Dynamic Ensemble Weighting: `merge_predictions.py`, `prediction_model.py`, `ensemble_scorer.py` calculate weights using 2D regime + rolling Sharpe.
- Report Generator (`generate_report.py`): HTML dashboard includes HRP weights chart, regime trends, Naver (`https://m.stock.naver.com/item/main.nhn?code=`) & Foreign (`https://finance.yahoo.com/quote/`) hyperlinks.
- KIS Execution Engine: `src/trading/` receives target positions with ATR dynamic stops and exposure cap checks before sending orders to KIS API.
