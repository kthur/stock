# Project: Stock Trading System (14-Strategy Dynamic Weighted Ensemble)

## Architecture
- Target Universe: 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500)
- 14 Multi-Factor Strategies:
  1. XGBoost Regression
  2. Surge Classifier
  3. Lead-Lag Matrix
  4. VCP Pattern Detector
  5. VCP ML Classifier
  6. Strict Causal LSTM
  7. Stat-Arb Cointegration
  8. Sector Rotation
  9. RIM Valuation
  10. Event-Driven
  11. Momentum Quality (MQ)
  12. Options IV Skew
  13. Order Flow Imbalance
  14. Short-Term Reversal
- 2D Regime Engine: VIX, US10Y-US2Y, USD/KRW GMM regime classification
- Dynamic Ensemble Scorer: Transaction cost subtraction, liquidity screening, net return scoring, net-return decision rationale
- Data Coverage & Missingness Analyzer: `strategy_data_coverage_report.txt`

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Baseline Exploration & Audit | Audit codebase, tests, 14 strategies, coverage analyzer | none | DONE |
| 2 | Ensemble & 2D Regime Enhancement | R1: Fix valid_mask (0.0 issue), preserve raw strategy NaNs, fix macro header, unify transaction costs | M1 | DONE |
| 3 | Backtest Engine & Risk Management | R2: Multi-asset portfolio backtest for 14 strategies (Sharpe, MDD, win rate, net return), liquidity & position sizing | M1, M2 | DONE |
| 4 | Strategy Data Coverage & Test Suite | R3: Fix false 100% coverage bug, per-symbol fundamental missingness, fix 13 failing tests (100% pass) | M1, M2, M3 | DONE |
| 5 | Full Pipeline E2E & Forensic Audit | E2E run_pipeline.py execution, verification of output files, passing forensic audit | M1..M4 | DONE |

## Interface Contracts
### `EnsembleScoringEngine` ↔ `StrategyCoverageAnalyzer`
- Scorer preserves un-mutated raw strategy scores (containing NaNs for un-calculated strategies) in `self.raw_scores` alongside formatted output scores (`fillna(0.0)`).
- Coverage Analyzer uses `raw_scores` to compute true per-strategy missingness ratios.

### `EnsembleScoringEngine` ↔ `BacktestEngine`
- `BacktestEngine` accesses 14-strategy ensemble scores and regime weights with unified transaction costs (KONEX 1.30%, KOSDAQ 1.00%, KOSPI 0.85%, SP500 0.60%).

## Code Layout
- `trading_system/run_pipeline.py`: Main pipeline entry point
- `src/ai/prediction_model.py`: OnDevicePredictionModel (regression, surge, lead-lag)
- `src/ai/ensemble_scorer.py`: EnsembleScoringEngine (14-strategy ensemble & 2D regime)
- `src/analysis/coverage_analyzer.py`: StrategyCoverageAnalyzer
- `src/core/`: Event-Driven, MQ Factor, IV Skew, Order Flow, Short-Term Reversal, Sector Rotation, Stat-Arb engines
- `trading_system/src/analysis/backtest.py`: BacktestEngine
- `tests/`: Automated unit & integration tests (`pytest tests/`)
- `trading_system/tests/`: Additional tests
