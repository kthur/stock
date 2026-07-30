# Project: Stock Trading System Algorithm Optimization

## Architecture
Integrated Stock Trading System running 17 dynamic factor strategies:
1. XGBoost Regression
2. Surge Classifier
3. Lead-Lag
4. VCP Rule-based
5. VCP ML
6. Strict Causal LSTM
7. Stat-Arb Cointegration
8. Sector Rotation
9. RIM Valuation
10. Event-Driven
11. Momentum Quality (MQ)
12. Options IV Skew
13. Order Flow Imbalance
14. Short-Term Reversal
15. Analyst Revision Momentum (ARM)
16. Cross-Asset Regime Divergence (CARD)
17. Liquidity-Adjusted Tail Risk (LATR)

All combined via 2D Market Regime Ensemble Scoring Engine (`src/ai/ensemble_scorer.py`), Risk Manager (`src/risk/risk_manager.py`), and Config (`src/config.py`).

## Code Layout
- `trading_system/run_pipeline.py`: Main orchestration script
- `src/config.py`: System configuration, cost parameters, risk limits
- `src/ai/ensemble_scorer.py`: 17-strategy dynamic weighted ensemble scoring engine
- `src/ai/optuna_tuner.py`: HPO hyperparameter tuning
- `src/analysis/coverage_analyzer.py`: Strategy coverage and missingness analyzer
- `src/risk/risk_manager.py`: Macro risk crisis detection and dynamic scoring gating
- `tests/`: Pytest test suite

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Dynamic Re-weighting Scoring (R1) | Normalize weights to 100% when strategy data missing (`src/ai/ensemble_scorer.py`) | None | IN_PROGRESS |
| 2 | Precision Order Book Impact Modeling (R2) | Liquidity-based order book impact & bid-ask spread modeling (`src/config.py`, `src/ai/ensemble_scorer.py`) | M1 | PLANNED |
| 3 | Multicollinearity & Regime Ensemble (R3) | Signal correlation monitoring, factor noise suppression, Optuna integration (`src/ai/ensemble_scorer.py`, `src/ai/optuna_tuner.py`) | M2 | PLANNED |
| 4 | Integration & E2E Pipeline Verification | Full pipeline execution generating `ensemble_predictions.txt` with top 20 recommendations | M1, M2, M3 | PLANNED |

## Interface Contracts
### Dynamic Weights Rescaling (`ensemble_scorer.py`)
- Input: `strategy_scores: Dict[str, float]`, `base_weights: Dict[str, float]`
- Output: `rescaled_weights: Dict[str, float]` summing to 1.0 for valid (non-NaN/non-missing) strategies.

### Market Impact Cost Modeling (`config.py` & `ensemble_scorer.py`)
- Input: stock liquidity metrics (turnover, market cap, volatility), order size hypothesis, bid-ask spread parameters.
- Output: market impact cost deduction applied to raw return predictions.
