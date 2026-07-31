# Project: 5 Key Institutional-Grade Quantitative Enhancements

## Architecture
- Target project: Integrated stock automated trading & prediction system (3,379 symbols, 18 multi-factor strategies, SQLite DBs).
- Modules to enhance / create:
  1. `src/risk/intraday_stop_loss.py`: Intraday order book/price momentum tracking, dynamic stop-loss gating (-4% drop or volume spike panic detection). Integrated with `RiskManager` (`src/risk/risk_manager.py`) and `run_pipeline.py`.
  2. `src/strategy/quad_factor_optimizer.py`: Quadratic Programming (QP) optimization balancing Sharpe ratio while constraining Market Beta, Size, Volatility, and Momentum factor exposures near zero, with max 25% sector caps. Integrated with portfolio allocation / risk parity.
  3. `src/ai/cpcv_stress_tester.py`: Combinatorial Purged Cross-Validation (CPCV) to eliminate time-series data leakage/embargo issues + historical stress testing simulating 2008 Financial Crisis, 2020 COVID panic, and 2022 Fed rate hike scenarios.
  4. `src/execution/slippage_feedback.py`: Closed-loop realized slippage feedback linking execution logs (`trade_logs.db`) to calculate real vs theoretical slippage and dynamically update microstructure cost parameters in `src/ai/ensemble_scorer.py`.
  5. `src/core/llm_sentiment_engine.py`: Extract sentiment/tone scores from DART/SEC filings using LLM/FinBERT tone analysis, incorporating sentiment metrics into Event-Driven alpha factor scores in `src/core/event_driven.py`.

## Code Layout
- `src/risk/intraday_stop_loss.py`
- `src/risk/risk_manager.py` (updated)
- `src/strategy/quad_factor_optimizer.py`
- `src/ai/cpcv_stress_tester.py`
- `src/execution/slippage_feedback.py`
- `src/ai/ensemble_scorer.py` (updated)
- `src/core/llm_sentiment_engine.py`
- `src/core/event_driven.py` (updated)
- `trading_system/run_pipeline.py` (updated)
- `tests/test_intraday_stop_loss.py`
- `tests/test_quad_factor_optimizer.py`
- `tests/test_cpcv_stress_tester.py`
- `tests/test_slippage_feedback.py`
- `tests/test_llm_sentiment_engine.py`
- `tests/test_integration_pipeline.py`

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Baseline Exploration & Test Infra | Codebase analysis, pytest setup, test baseline | None | DONE |
| M1 | R1 Intraday Microstructure & Stop-Loss Engine | `src/risk/intraday_stop_loss.py`, `RiskManager`, `run_pipeline.py` integration | M0 | DONE |
| M2 | R2 Quad-Factor Neutral QP Portfolio Risk Optimizer | `src/strategy/quad_factor_optimizer.py`, Sharpe optimization, factor neutrality, sector caps | M0 | DONE |
| M3 | R3 CPCV & Historical Stress Testing Engine | `src/ai/cpcv_stress_tester.py`, purging/embargo, historical crisis simulation | M0 | DONE |
| M4 | R4 Closed-Loop Realized Slippage Execution Feedback | `src/execution/slippage_feedback.py`, `trade_logs.db`, `ensemble_scorer.py` dynamic update | M0 | DONE |
| M5 | R5 LLM/NLP DART & SEC Filing Sentiment Engine | `src/core/llm_sentiment_engine.py`, FinBERT/LLM, `event_driven.py` integration | M0 | DONE |
| M6 | Final Integration & E2E Pipeline Verification | Full pytest suite execution, `run_pipeline.py` end-to-end dry run verification | M1, M2, M3, M4, M5 | IN_PROGRESS |

## Interface Contracts
### Intraday Stop-Loss ↔ RiskManager
- Function: `IntradayStopLossEngine.evaluate_stop_loss(symbol, intraday_ticks_df, position_entry_price)` -> `StopLossResult(triggered: bool, reason: str, adjusted_position_size: float)`
- Integration: `RiskManager.check_intraday_risk(...)` incorporates `IntradayStopLossEngine`.

### Quad-Factor Optimizer ↔ Portfolio Allocation
- Function: `QuadFactorOptimizer.optimize_weights(expected_returns, cov_matrix, factor_matrix, sector_labels)` -> `np.ndarray` (weights satisfying QP constraints: sum=1, w>=0, factor exposures ~= 0, sector sum <= 0.25).

### CPCV & Stress Tester ↔ Model Validation / Backtest
- Function: `CPCVStressTester.generate_purged_folds(n_splits, n_test_splits, purge_window, embargo_window)` -> generator of train/test indices.
- Function: `CPCVStressTester.run_historical_stress_test(strategy_returns, scenario='2008_CRISIS'|'2020_COVID'|'2022_FED_HIKE')` -> `StressTestReport`.

### Slippage Feedback ↔ Ensemble Scorer
- Function: `SlippageFeedbackEngine.calculate_realized_slippage(db_path)` -> `SlippageMetrics(avg_slippage_bps, market_impact_alpha)`
- Function: `EnsembleScoringEngine.update_microstructure_costs(slippage_metrics)` -> updates transaction cost models dynamically.

### LLM Sentiment Engine ↔ Event Driven Engine
- Function: `LLMSentimentEngine.analyze_filing_sentiment(filing_text, Market='KOSPI'|'SP500')` -> `SentimentScore(positive, negative, tone_score)`
- Function: `EventDrivenEngine.calculate_event_score(filing_data, sentiment_score)` -> modified catalyst score.
