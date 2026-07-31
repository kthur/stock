# Baseline Test Audit & 5 Institutional-Grade Enhancements Exploration Report

**Agent Identity**: `explorer_m0_1` (teamwork_preview_explorer)  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_m0_1`  
**Date**: 2026-07-31  

---

## 1. Executive Summary

This report presents a thorough investigation of the stock trading codebase (`d:\Finance\code\stock`) to establish a baseline test suite audit and map out the exact integration architecture for **5 Key Institutional-Grade Quantitative Enhancements**:

1. **R1: Intraday Stop-Loss & Dynamic Drawdown Control** (`src/risk/intraday_stop_loss.py`)
2. **R2: Quadratic Programming Multi-Factor Portfolio Optimizer** (`src/strategy/quad_factor_optimizer.py`)
3. **R3: CPCV Stress Tester** (`src/ai/cpcv_stress_tester.py`)
4. **R4: Real-time Slippage Feedback Loop** (`src/execution/slippage_feedback.py`)
5. **R5: LLM / FinBERT Sentiment & Event Catalyst Engine** (`src/core/llm_sentiment_engine.py`)

All investigation was conducted under read-only mode using Python `.venv\Scripts\python.exe`.

---

## 2. Baseline Test Suite Audit

### 2.1 Test Directory Structure & Path Resolution
The codebase contains test suites under two main paths:
- `d:\Finance\code\stock\tests\` (root tests, 80 test files)
- `d:\Finance\code\stock\trading_system\tests\` (trading_system module tests, 69 test files)

Path resolution is managed by `conftest.py` at root:
```python
root_dir = os.path.dirname(os.path.abspath(__file__))
ts_dir = os.path.join(root_dir, "trading_system")
if ts_dir not in sys.path:
    sys.path.insert(0, ts_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
```

### 2.2 Test Execution Findings & Baseline Metrics
- **Command**: `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v`
- **Collected Test Items**: 616 test cases across unit, integration, and e2e test suites.
- **Root Collection Note**: Running `pytest tests/ -v` directly at root encountered a module name collision between `tests/phase3/e2e/test_e2e.py` and `tests/phase4/e2e/test_e2e.py` due to identical filenames in subpackages without explicit `__init__.py` namespaces. Running `pytest trading_system/tests/ -v` or adding `--ignore=tests/phase4/e2e/test_e2e.py` resolves this and runs clean test collection.
- **Coverage Areas**: Pre-existing test suite covers sentiment filters, RL trading environments, 18-strategy feature normalization, 2D market regime matrix, HRP/risk parity allocation, macro stress scenarios, and database WAL concurrency.

---

## 3. Detailed Codebase Mapping for 5 Quantitative Enhancements

### 3.1 R1: Intraday Stop-Loss & Dynamic Drawdown Control
- **Target New File**: `src/risk/intraday_stop_loss.py`
- **Class**: `IntradayStopLossManager` / `IntradayDrawdownController`
- **Current State**:
  - `RiskManager` (`trading_system/src/risk/risk_manager.py`) provides `calculate_trailing_stop_price()`, `check_trailing_stop_signal()`, and `evaluate_crisis()` via `CrisisDetector`.
  - Current stop-loss logic operates on daily EOD prices and static drawdown thresholds.
- **Integration Requirements & Design**:
  1. **Tick/Minute Price Monitoring**: Real-time high-frequency price updates for open positions.
  2. **Intraday Peak-to-Trough Drawdown Calculation**: $DD_{intraday} = \frac{P_{peak} - P_{curr}}{P_{peak}}$.
  3. **ATR & Regime-Scaled Trailing Stops**: Incorporates `get_adaptive_atr_multipliers(regime, adx)` to dynamically adjust stop distance.
  4. **Drawdown Breach Actions**:
     - Light breach (e.g. 3-5% intraday DD): Scales down position limits dynamically ($position\_multiplier \in [0.4, 0.7]$).
     - Severe breach (e.g. 8-10% intraday DD): Triggers emergency position liquidations and blocks new buy orders.
  5. **Integration Points**:
     - `src/risk/risk_manager.py`: Instantiate `IntradayStopLossManager` inside `RiskManager.__init__()`. Delegate real-time trailing stop checks to it.
     - `trading_system/run_pipeline.py`: Feed real-time price feeds into `IntradayStopLossManager`.
     - `src/execution/oms_engine.py`: Receive stop breach signals and dispatch immediate exit/cancellation order plans.

---

### 3.2 R2: Quadratic Programming Multi-Factor Portfolio Optimizer
- **Target New File**: `src/strategy/quad_factor_optimizer.py`
- **Class**: `QuadFactorOptimizer`
- **Current State**:
  - `PortfolioOptimizer` (`trading_system/src/risk/portfolio_optimizer.py`) implements SLSQP for Risk Parity (Equal Risk Contribution) and Mean-Variance Optimization.
  - Sector exposure control is currently applied via post-hoc heuristic weight scaling (`apply_factor_and_sector_constraints`).
- **Integration Requirements & Design**:
  1. **Convex QP Formulation**:
     $$\min_w \frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w - w_0\|_1$$
     subject to:
     - Budget: $\sum_i w_i = 1.0$ (or $\sum w_i \le 1 - c_{min}$)
     - Weight Bounds: $0 \le w_i \le w_{max}$ (e.g., 0.20 max single position)
     - Sector Caps: $\sum_{i \in S_k} w_i \le c_k$ (e.g., 0.30-0.35 max per sector)
     - Factor Exposure Limits: $B_{min, f} \le F_f^T w \le B_{max, f}$ (market beta neutrality, size/value/momentum exposure bands)
  2. **Numerical Robustness & Solver Strategy**: Uses `scipy.optimize.minimize` (SLSQP method) or matrix QP solvers (`cvxpy` / `osqp`). Incorporates shrinkage covariance matrices (`calculate_covariance_matrix`) and falls back to risk parity/MVO if constraints are infeasible.
  3. **Integration Points**:
     - `src/risk/portfolio_optimizer.py`: Wrap `QuadFactorOptimizer` as an optimization method in `PortfolioOptimizer`.
     - `src/risk/portfolio_allocator.py`: Call `QuadFactorOptimizer` for portfolio allocation in `PortfolioAllocator.allocate_portfolio()`.
     - `trading_system/run_pipeline.py`: Step 10g uses `QuadFactorOptimizer` to optimize expected returns $\mu$ generated by the 18-strategy ensemble.

---

### 3.3 R3: CPCV Stress Tester
- **Target New File**: `src/ai/cpcv_stress_tester.py`
- **Class**: `CPCVStressTester`
- **Current State**:
  - `PurgedKFold` (`trading_system/src/ai/purged_cv.py`) implements basic purged K-fold cross-validation with embargoing.
- **Integration Requirements & Design**:
  1. **Combinatorial Purged Cross-Validation (CPCV)**:
     - Generates $N$ equal groups and selects combinations $\binom{N}{k}$ to form backtest test paths $P$.
     - Purges overlapping sample event windows between train and test sets to eliminate lookahead leak.
     - Embargoes post-test observations to eliminate serial correlation leakage.
     - Reconstructs multiple backtest paths to compute empirical distributions of Sharpe Ratios and Max Drawdowns.
     - Computes Probability of Backtest Overfitting (PBO) and Deflated Sharpe Ratio (DSR).
  2. **Historical Crisis Stress Simulation**:
     - Simulates model predictions across key historical market crises:
       - 2008 Global Financial Crisis shock
       - 2020 COVID Market Crash
       - 2022 Fed Rate Hike Liquidity Shock
       - 2024 Tech Volatility Spike
     - Evaluates crisis VaR (99%), Expected Shortfall (CVaR 99%), and Stress Drawdown.
  3. **Integration Points**:
     - `src/ai/purged_cv.py`: `CPCVStressTester` builds upon `PurgedKFold`.
     - `src/ai/optuna_tuner.py`: Hyperparameter optimization uses `CPCVStressTester` path scores to prevent overfitting.
     - `trading_system/run_pipeline.py`: Model validation step runs `CPCVStressTester` before publishing predictions.

---

### 3.4 R4: Real-Time Slippage Feedback Loop
- **Target New File**: `src/execution/slippage_feedback.py`
- **Class**: `SlippageFeedbackLoop`
- **Current State**:
  - `ExecutionOMSEngine` (`trading_system/src/execution/oms_engine.py`) writes order plans to `order_plans` table and execution logs to `execution_logs` table in `trade_logs.db`.
  - `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`) subtracts microstructure costs (`_get_cost_pct()`) using static base formulas (`stt_tax`, `base_spread`, `impact_coeff`).
- **Integration Requirements & Design**:
  1. **DB Querying & Realized Slippage Calculation**:
     - Reads execution records from `trade_logs.db`:
       $$slippage\_bps = \frac{P_{exec} - P_{target}}{P_{target}} \times 10000$$
     - Computes market-specific, ticker-specific, and volume-weighted median/mean slippage bps.
  2. **EMA Dynamic Cost Parameter Calibration**:
     - Calculates realized vs. expected cost ratio ($ratio = \frac{\text{realized\_slippage}}{\text{predicted\_cost}}$).
     - Updates dynamic cost multiplier via Exponential Moving Average (EMA).
  3. **Integration Points**:
     - `src/execution/oms_engine.py`: `ExecutionOMSEngine.record_execution()` triggers `SlippageFeedbackLoop.update_feedback()`.
     - `src/ai/ensemble_scorer.py`: `EnsembleScoringEngine._get_cost_pct()` calls `SlippageFeedbackLoop.get_dynamic_cost_multiplier(market, symbol)` to adjust cost subtractions dynamically.

---

### 3.5 R5: LLM / FinBERT Sentiment & Event Catalyst Engine
- **Target New File**: `src/core/llm_sentiment_engine.py`
- **Class**: `LLMSentimentEngine`
- **Current State**:
  - `EventDrivenEngine` (`trading_system/src/core/event_driven.py`) uses string keyword matches (`'유상증자' in report_nm`, `'자사주' in report_nm`, etc.) to weight corporate disclosure events.
- **Integration Requirements & Design**:
  1. **Filing Tone Analysis**:
     - Evaluates disclosure texts, earnings report summaries, and corporate news headlines.
     - Outputs: sentiment direction (`bullish`, `bearish`, `neutral`), score $[-1.0, +1.0]$, and confidence $[0.0, 1.0]$.
  2. **Offline Fallback (CODE_ONLY Mode Compliance)**:
     - In CODE_ONLY network mode where remote LLM API calls are disabled, provides a robust, zero-network keyword/regex lexicon analyzer.
  3. **Integration Points**:
     - `src/core/event_driven.py`: `EventDrivenEngine` instantiates `LLMSentimentEngine`. In `compute_event_scores()`, report titles and text are passed to `LLMSentimentEngine.analyze_tone()` to refine event weights.
     - `src/risk/sentiment_filter.py`: Feeds negative disclosure sentiment scores directly into the sentiment blacklist.

---

## 4. Integration Dependency Matrix & Implementation Order

```
[R5: LLM Sentiment Engine] ───> [EventDrivenEngine] ──┐
                                                    │
[R3: CPCV Stress Tester] ────> [Prediction Models] ─┼──> [R4: Slippage Feedback]
                                                    │           │
[R2: Quad Factor Optimizer] ─> [Portfolio Allocator]─┴──> [R1: Intraday Stop Loss]
```

### Recommended Implementation Order for Subsequent Tasks:
1. **R5 (LLM Sentiment Engine)**: Standalone module with clear interface for `event_driven.py`.
2. **R4 (Slippage Feedback Loop)**: Connects `oms_engine.py` DB execution logs to `ensemble_scorer.py` cost modeling.
3. **R3 (CPCV Stress Tester)**: Enhances model cross-validation in `purged_cv.py` and model evaluation.
4. **R2 (Quad Factor Optimizer)**: Replaces post-hoc sector capping with strict QP optimization in `portfolio_optimizer.py`.
5. **R1 (Intraday Stop-Loss)**: Ties together real-time price updates, `RiskManager`, and `oms_engine.py`.

---

## 5. Verification Methods

For each enhancement, dedicated unit test files must be executed using `.venv\Scripts\python.exe -m pytest <test_file> -v`:
1. **R1**: `tests/test_intraday_stop_loss.py`
2. **R2**: `tests/test_quad_factor_optimizer.py`
3. **R3**: `tests/test_cpcv_stress_tester.py`
4. **R4**: `tests/test_slippage_feedback.py`
5. **R5**: `tests/test_llm_sentiment_engine.py`
