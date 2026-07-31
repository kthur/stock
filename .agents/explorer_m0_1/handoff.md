# Handoff Report: Baseline Test Audit & Codebase Mapping for 5 Quantitative Enhancements

**Agent**: `explorer_m0_1` (teamwork_preview_explorer)  
**Target Path**: `d:\Finance\code\stock\.agents\explorer_m0_1\handoff.md`  
**Date**: 2026-07-31  

---

## 1. Observation

- **Environment & Workspace**: Windows OS, Python virtual environment at `.venv\Scripts\python.exe`.
- **Directory Layout**:
  - `trading_system/src/` contains core modules: `risk/`, `strategy/`, `ai/`, `execution/`, `core/`, `analysis/`, `data_layer/`, `persistence/`, `utils/`.
  - `conftest.py` at root sets up `sys.path`:
    ```python
    root_dir = os.path.dirname(os.path.abspath(__file__))
    ts_dir = os.path.join(root_dir, "trading_system")
    if ts_dir not in sys.path:
        sys.path.insert(0, ts_dir)
    ```
- **Baseline Test Execution**:
  - Command: `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v`
  - Total collected test cases: **616 items** across unit, integration, and e2e test files.
  - Root pytest command issue: `pytest tests/ -v` stopped during collection due to duplicate test file name `test_e2e.py` in `tests/phase3/e2e/test_e2e.py` and `tests/phase4/e2e/test_e2e.py` lacking `__init__.py` module distinction. Specifying `trading_system/tests/` or `--ignore=tests/phase4/e2e/test_e2e.py` executes clean collection.
- **Key Codebase Locations**:
  - **R1**: `trading_system/src/risk/risk_manager.py` (lines 311-500: `RiskManager`, ATR multiplier scaling, peak value tracking) and `trading_system/run_pipeline.py`.
  - **R2**: `trading_system/src/risk/portfolio_optimizer.py` (lines 18-200: `PortfolioOptimizer`, SLSQP risk parity & mean-variance optimization, `apply_factor_and_sector_constraints`).
  - **R3**: `trading_system/src/ai/purged_cv.py` (lines 8-63: `PurgedKFold` with purging and embargoing).
  - **R4**: `trading_system/src/execution/oms_engine.py` (lines 12-155: `ExecutionOMSEngine`, `trade_logs.db`, `order_plans`, `execution_logs`) and `trading_system/src/ai/ensemble_scorer.py` (lines 1068-1150: microstructure cost calculations `_get_cost_pct`).
  - **R5**: `trading_system/src/core/event_driven.py` (lines 17-149: `EventDrivenEngine`, OpenDART filing fetch, `EVENT_WEIGHTS`, keyword sentiment adjustments).

---

## 2. Logic Chain

1. **Baseline Test Audit**:
   - Running tests with `.venv\Scripts\python.exe -m pytest trading_system/tests/ -v` confirms that the baseline system collects 616 test cases covering unit, integration, and e2e scenarios.
   - Identified test collection edge-case in root `tests/` directory due to duplicate filename `test_e2e.py` across phase3/phase4 subdirectories without packages.

2. **R1 Integration (Intraday Stop-Loss)**:
   - `RiskManager` currently handles EOD drawdown and ATR-based stops.
   - Adding `src/risk/intraday_stop_loss.py` (`IntradayStopLossManager`) provides minute/tick peak-to-trough drawdown calculation ($DD_{intraday} = \frac{P_{peak}-P_{curr}}{P_{peak}}$) and triggers real-time exit order plans via `oms_engine.py` when stop bounds are breached.

3. **R2 Integration (Quad-Factor Optimizer)**:
   - `PortfolioOptimizer` currently relies on SLSQP with post-hoc heuristic sector capping.
   - Adding `src/strategy/quad_factor_optimizer.py` (`QuadFactorOptimizer`) implements a convex QP solver ($\min_w \frac{1}{2} w^T \Sigma w - \lambda \mu^T w + \gamma \|w-w_0\|_1$) with strict linear constraint matrices for sector caps ($S_k^T w \le c_k$) and factor exposure bounds ($B_{min} \le F^T w \le B_{max}$).

4. **R3 Integration (CPCV Stress Tester)**:
   - `purged_cv.py` provides basic `PurgedKFold`.
   - Adding `src/ai/cpcv_stress_tester.py` (`CPCVStressTester`) generates combinatorial paths $\binom{N}{k}$, computes path Sharpe distribution and Probability of Backtest Overfitting (PBO), and simulates historical crisis shocks (2008, 2020, 2022, 2024).

5. **R4 Integration (Slippage Feedback Loop)**:
   - `oms_engine.py` logs trades to `trade_logs.db` (`execution_logs`), while `ensemble_scorer.py` deducts static market impact costs.
   - Adding `src/execution/slippage_feedback.py` (`SlippageFeedbackLoop`) queries `execution_logs`, computes empirical realized vs. predicted slippage ratios, and updates dynamic cost multipliers via EMA.

6. **R5 Integration (LLM / FinBERT Sentiment Engine)**:
   - `event_driven.py` uses string matches on disclosure titles.
   - Adding `src/core/llm_sentiment_engine.py` (`LLMSentimentEngine`) adds filing tone classification (direction, score, confidence) with zero-network offline fallback for CODE_ONLY compliance.

---

## 3. Caveats

- **Network Constraints**: The environment is operating in CODE_ONLY mode. External API calls (e.g. OpenDART remote fetch, live HuggingFace model downloading) are disabled. All enhancement modules must include offline heuristic fallback logic.
- **QP Dependencies**: Quadratic Programming solver implementation in R2 should utilize `scipy.optimize.minimize` (SLSQP method) to maintain zero external C++ library dependency issues on Windows.
- **Database Lock**: `trade_logs.db` uses SQLite WAL mode; concurrent access from `ExecutionOMSEngine` and `SlippageFeedbackLoop` must handle database locks gracefully with retries or explicit connection closures.

---

## 4. Conclusion

The codebase exploration and baseline test setup audit are complete.
- **Baseline Test Suite**: Operational with 616 test items collected in `trading_system/tests/`.
- **Enhancement Architecture**: Clear integration points, class structures, parameter flow, and verification methods mapped for all 5 institutional-grade quantitative enhancements in `analysis.md`.

---

## 5. Verification Method

To verify the exploration findings and run baseline test checks:
1. Run pytest suite:
   ```powershell
   .venv\Scripts\python.exe -m pytest trading_system/tests/ -v
   ```
2. Verify detailed analysis report exists and is populated:
   ```powershell
   type d:\Finance\code\stock\.agents\explorer_m0_1\analysis.md
   ```
3. Verify handoff report exists and is populated:
   ```powershell
   type d:\Finance\code\stock\.agents\explorer_m0_1\handoff.md
   ```
