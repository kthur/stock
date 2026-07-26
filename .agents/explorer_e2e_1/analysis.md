# Stock Trading System - E2E Testing Investigation Report

## 1. Executive Summary
This report presents an exhaustive read-only investigation of the Stock Trading System codebase at `d:\Finance\code\stock\`. The objective is to extract the core features of the 5-strategy consolidation pipeline (`run_pipeline.py`), assess the current state of existing tests in `trading_system/tests/`, verify the Windows Python environment, and propose a robust 4-tier E2E testing framework to ensure system reliability and correctness.

---

## 2. Windows Environment Verification
The environment has been verified on Windows using terminal command execution. The configuration details are as follows:

*   **Virtual Environment Path Structure**: The virtual environment uses Windows-standard directory structures.
    *   `python.exe` path: `.venv\Scripts\python.exe`
    *   `pytest.exe` path: `.venv\Scripts\pytest.exe`
*   **Active Python Version**: Python 3.11.9
*   **Active Pytest Version**: pytest-9.1.1 (pluggy-1.6.0)
*   **Configured Plugins**: anyio-4.14.0, dash-2.18.2, cov-7.1.0
*   **Verified Pytest Execution Command**:
    ```powershell
    .venv\Scripts\pytest trading_system\tests\ -v
    ```
    This command successfully executes the test runner from the workspace root. Running specific test files (e.g., `trading_system\tests\test_config.py`, `trading_system\tests\phase3\e2e\test_e2e.py`, `trading_system\tests\phase4\e2e\test_e2e.py`, `trading_system\tests\test_screener_dash_challenger.py`, and `trading_system\tests\test_ensemble_lgb_cat.py`) passed cleanly, confirming complete compatibility.

---

## 3. Core Pipeline & Strategy Features Extracted
The integrated consolidated pipeline is orchestrated by `trading_system/run_pipeline.py`, supported by modules under `src/`. Below is the map of core features that must be covered under E2E testing:

### A. Integrated Pipeline Orchestration (`run_pipeline.py`)
1.  **Configuration Verification**: Parses and validates configurations (`TradingConfig` loaded from `.env`), verifying DB paths, mock trading settings, and sample sizes.
2.  **Macro Indicator Storage**: Downloads global market indicators (VIX, TNX, USDKRW, etc.) via `GlobalMarketClient` and persists them to `market_indicators.db` using `MarketIndicatorStorage`.
3.  **Universe Sync & Caching**: Tracks 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500). Pulls price data using a batch prefetcher (`prefetch_prices_batch`) and local caching layers (`TechnicalCache` / `StockPriceDB`).
4.  **Parallel Model Training**: Segments data by market and trains regression, surge classifier, lead-lag, and VCP ML models in parallel via `ThreadPoolExecutor` threads.
5.  **Multi-Format Export**: Saves predictions to SQLite DB and outputs 8 report files under `trading_system/result/`.

### B. Core Prediction Strategies (The 5 Strategies)
1.  **Strategy 1: XGBoost/LightGBM/CatBoost Regressor** (`src/ai/prediction_model.py`):
    *   Predicts expected returns over 8 horizons: 1, 5, 10, 20, 30, 60, 120, and 200 days.
    *   Calculates 23+ features (returns, simple moving averages, normalized volatility, normalized market cap, normalized volume, 1y eps growth, etc.) and merges global macro indicators.
2.  **Strategy 2: Surge Classifier** (`src/ai/prediction_model.py`):
    *   XGBoost binary classifier predicting whether a stock's return will exceed 20% (threshold 0.20) over 4 horizons (1, 3, 5, 20 days).
    *   Balances positive class weight with `scale_pos_weight <= 500`.
3.  **Strategy 3: Lead-Lag** (`src/ai/prediction_model.py`):
    *   Computes a lag-1 correlation matrix for follower stocks based on the movement of the top 50 leader stocks (market cap).
    *   Generates a lead-lag score.
4.  **Strategy 4: VCP Pattern Detector (Rule-based)** (`src/ai/vcp_detector.py`):
    *   Minervini Volatility Contraction Pattern rules: decreasing daily ranges across windows (5, 10, 20, 40, 60 days), declining average volume, price above MA50 and MA200, price near 10d high, and positive 10d return.
    *   Generates a VCP score (0 to 100) and identifies pattern matches.
5.  **Strategy 5: VCP ML** (`src/ai/vcp_ml_predictor.py`):
    *   Trains an XGBClassifier per market (KOSPI, KOSDAQ, KONEX, SP500) over 4 horizons based on 11 vectorized VCP features (e.g., `range_5v20`, `monotonic`, `vcp_score`).

### C. Decision Support & Risk Management Systems
1.  **GMM Market Regime Detector** (`src/analysis/regime_detector.py`):
    *   Classifies market regime (Bull, Bear, Sideways) based on macro rolling returns and volatility.
    *   Restricts total allocation dynamically: BEAR = 20%, SIDEWAYS = 50%, BULL = 85%.
2.  **Statistical Arbitrage Engine** (`src/core/stat_arb.py`):
    *   Scans for cointegrated stock pairs and calculates Z-scores, beta, and signals (BUY/SELL/neutral).
3.  **Dynamic Ensemble Scorer** (`src/ai/ensemble_scorer.py`):
    *   Combines strategy scores into a unified `ensemble_score` and `ensemble_expected_return` using regime-adjusted weights.
4.  **Portfolio Position Sizing** (`src/risk/position_sizing.py`):
    *   Kelly/Sharpe optimized position weight allocator (`PortfolioAllocator`) based on ensemble expectancies, subject to the regime-dictated maximum ceiling.

---

## 4. Assessment of Existing Test Suite
A review of the test files under `trading_system/tests/` revealed that they are divided into three groups:

### A. Obsolete / Scaffolded Tests (To be Replaced or Refactored)
*   `tests/phase3/test_m1_ai_pipeline.py` & `tests/phase3/e2e/test_e2e.py` (partially):
    *   **What they test**: Sentiment analysis (`analyze_sentiment` using custom NLP) and RL trading agent training (`train_rl_model` using stable_baselines3 PPO).
    *   **Why they are obsolete**: These modules are not utilized in the consolidated `run_pipeline.py`. The consolidated pipeline relies on regression and VCP classifiers rather than PPO RL agents or NLP sentiment engines.
    *   **Action**: These tests should be moved to an archive or deprecated, and replaced with actual pipeline integration tests.

### B. Passing & Fully Functional Tests (Reusable Directly)
*   `tests/test_config.py`: Validates environmental overrides and parameters parsing. Works perfectly (10/10 tests passed).
*   `tests/test_screener_dash_challenger.py`: Tests Dash UI layout and callback robustness under null/invalid inputs.
*   `tests/test_indicators.py`: Unit tests verifying technical indicator mathematics (SMA, EMA, MACD, RSI, ATR). Passes cleanly.

### C. Reusable & Adaptable Test Scaffolds
*   `tests/test_ensemble_lgb_cat.py` (Feature engineering, LightGBM/CatBoost integration):
    *   **Value**: Trains XGBoost, LightGBM, and CatBoost models on mock price data, checks serialization, and verifies fallbacks.
    *   **E2E Adaptation**: Re-use this scaffold to test Strategy 1 (Regressor) and Strategy 5 (VCP ML) in Tier 1.
*   `tests/test_lead_lag_index.py` (Lead-lag calculations):
    *   **Value**: Validates lag-1 correlation computation and follower selection.
    *   **E2E Adaptation**: Directly forms the Tier 1 E2E validation for Strategy 3 (Lead-Lag).
*   `tests/test_post_market_scoring.py`:
    *   **Value**: Simulates daily post-market scoring using patched yfinance inputs.
    *   **E2E Adaptation**: Can be adapted for Tier 3/4 pipeline E2E integration test mocks.
*   `tests/phase4/e2e/test_e2e.py` (Dashboard, backtesting, stops):
    *   **Value**: Verifies `BacktestEngine`, trailing stop loss ATR checks, and Dash app server components.
    *   **E2E Adaptation**: Useful for Tier 2/3 boundary and combination tests.

---

## 5. Proposed 4-Tier E2E Testing Framework Plan
We propose a 4-tier E2E testing framework tailored specifically to the Stock Trading System's consolidated 5-strategy design:

```
+-------------------------------------------------------------------+
|               TIER 4: REAL-WORLD SCENARIOS (E2E)                  |
|  - Consolidated Daily Pipeline  - Macro Regime Shock Simulation   |
|  - Multi-Market Parallel Run    - Offline Cache-Only Execution    |
+-------------------------------------------------------------------+
                                  |
+-------------------------------------------------------------------+
|             TIER 3: CROSS-FEATURE INTERACTIONS (INT)              |
|  - Regime -> Allocation Ceiling  - Shared Feature Engineering     |
|  - Lead-Lag Follower Pipeline   - VCP Rule vs VCP ML Consistency  |
+-------------------------------------------------------------------+
                                  |
+-------------------------------------------------------------------+
|               TIER 2: BOUNDARY & CORNER CASES                     |
|  - Insufficient price data (<200d) - Missing fundamentals (NaNs) |
|  - Zero/flat volatility data       - yfinance/fdr network errors  |
+-------------------------------------------------------------------+
                                  |
+-------------------------------------------------------------------+
|             TIER 1: FEATURE COVERAGE (HAPPY PATH)                 |
|  - Regression Prediction         - Surge Classification           |
|  - Lead-Lag Scoring              - VCP Rule-based Detection       |
|  - VCP ML Probabilities          - GMM Market Regime Classification|
+-------------------------------------------------------------------+
```

### Tier 1: Feature Coverage (Happy Path)
Verifies the isolated execution of each of the 5 strategies and support components.
1.  **XGBoost Regressor Happy Path**: Feed mock 350-day price data, verify 23 technical/fundamental features are constructed, train regression models for all 8 horizons, serialize to disk (`xgb_model_sp500_5d.json`, etc.), reload, and predict.
2.  **Surge Classifier Happy Path**: Assert that the surge target (return >= 20%) is created correctly, train the classifier with a valid `scale_pos_weight`, and output probabilities over 4 horizons.
3.  **Lead-Lag Correlation Happy Path**: Generate follower price data lagging behind a leader index, verify `compute_lead_lag` identifies the lag relationship, and score followers.
4.  **VCP Rule-based Pattern Happy Path**: Feed a mock price series with contraction peaks (e.g. daily ranges contracting 15% -> 8% -> 4%), assert `detect_vcp` identifies the pattern (`is_vcp=True`) and outputs a score >= 50.
5.  **VCP ML Classifier Happy Path**: Build 11 VCP vectorized features, segment the training dataset, train the VCP ML classifier, and verify predictions.
6.  **GMM Regime Classifier Happy Path**: Feed upward/downward trending macro histories, verify GMM clusters return Bull/Bear labels.
7.  **Ensemble & Sizing Happy Path**: Combine mock strategy results, assert the ensemble score matches the weighted equation, and verify the Kelly allocator outputs weights summing to the limit.

### Tier 2: Boundary & Corner Cases (Robustness)
Verifies system resilience against erroneous, missing, or extreme inputs.
1.  **Insufficient Price History**: Feed stock series with length < 200 days. Assert that technical indicators (like SMA200) and VCP pattern detectors handle this gracefully (skip/return default structures) instead of raising ValueError.
2.  **Missing Fundamentals (NaN Handling)**: Feed data with empty fundamental values. Verify the system merges them successfully by falling back to `FallbackMetadataDict` and default parameters without crashing.
3.  **Zero/Constant Price Series**: Pass price series with constant prices (0% returns) and zero volume. Verify that technical indicators (like ADX, ATR, RSI) do not encounter division-by-zero errors.
4.  **Network Timeouts / Offline Status**: Mock network fetches to fail. Assert the pipeline queries only the local `stock_prices.db` and indicators cache when `STOCK_PRICE_FRESHNESS_DAYS=none` is set.
5.  **Invalid Sizing / Allocation Limits**: Set the maximum allocation limit to extreme values (e.g. 0.0 or > 1.0). Verify the `PortfolioAllocator` limits the output cash weights to safe ranges.

### Tier 3: Cross-Feature Interaction (Integration)
Verifies that individual components collaborate correctly in the pipeline.
1.  **Regime Detector & Position Sizer Link**: Simulate a transition from BULL (regime 2) to BEAR (regime 0). Verify that the GMM regime status update dynamically propagates to the `PortfolioAllocator`, shrinking the maximum total allocation from 85% to 20% and resizing Kelly positions.
2.  **Shared Features Consistency**: Verify that the feature engineering pipeline constructs features once and distributes them identically to both the XGBRegressor and Surge Classifier without data corruption.
3.  **Lead-Lag Leader returns to Follower score flow**: Verify that daily return changes of leader stocks computed during the prediction step are successfully matched with the follower correlation matrix to generate lead-lag predictions.
4.  **VCP Rule vs ML Feature Alignment**: Assert that VCP features computed for VCP ML training (like `monotonic`, `vcp_score`) match the outputs of the rule-based `detect_vcp()` on the same input data.
5.  **DB and Text Report Synchronization**: Execute inference, assert that predicted data is written to the SQLite `ai_predictions` and `ensemble_predictions` tables, and verify the written text reports (`pipeline_result.txt`, `ensemble_predictions.txt`) contain matching ranks and scores.

### Tier 4: Real-World Workloads (E2E Scenarios)
Simulates realistic, production-like sessions under various stress profiles.
1.  **Consolidated Daily Pipeline Session**: Run the complete integrated pipeline from end-to-end on mocked inputs. Verify that config validation -> indicators fetch -> universe sync -> cached data loading -> training -> inference -> regime analysis -> ensemble -> portfolio sizing -> DB save -> 8 files export runs end-to-end in under 30 seconds with mock parameters.
2.  **Macro Collapse (Regime Shock) Simulation**: Feed a sequence of prices simulating a sudden market crash (indices drop 10%, VIX spikes 40%). Run the pipeline. Verify that the regime detector switches to BEAR, total capital allocation is restricted, and the output `portfolio_allocation.txt` restricts risky holdings.
3.  **Offline Cache-Only pipeline Run**: Disconnect network APIs using mocks. Configure `freshness_days = -1` (or `none`). Run the consolidated pipeline and verify it completes using only pre-existing database records.
4.  **Multi-Market Parallel Processing Stress**: Run the pipeline with KOSPI, KOSDAQ, KONEX, and SP500 markets active. Verify that market segment routing selects the correct model files and thread pools execute concurrently without race conditions.

---

## 6. Recommendations & Action Items
To implement this framework, the following steps are recommended:
1.  **Deprecate Obsolete Scaffolds**: Move `tests/phase3/e2e/test_e2e.py` and `tests/phase3/test_m1_ai_pipeline.py` to a deprecated folder, or refactor them.
2.  **Re-purpose LightGBM/CatBoost & Lead-Lag tests**: Elevate `tests/test_ensemble_lgb_cat.py` and `tests/test_lead_lag_index.py` to form the core of Tier 1 regression, surge, and lead-lag testing.
3.  **Construct a Consolidated E2E Pipeline Test**: Create `tests/test_e2e_consolidated_pipeline.py` under Tier 4. Use mocked network dependencies to verify the full flow of `run_pipeline.py` from configuration loading to file outputs.
4.  **Mock Network Calls**: Use standard `unittest.mock.patch` fixtures (similar to those in `tests/phase4/e2e/test_e2e.py`) to bypass external yfinance/fdr HTTP calls, avoiding timeouts.
