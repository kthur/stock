# Project: Stock Trading System Optimization & Hardening (R1 ~ R4 / V6)

## Architecture
Comprehensive multi-factor quantitative equity auto-trading and forecasting engine across 5 global markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) with 31 multi-factor strategies, 2D market regime dynamic weighted ensemble, portfolio optimization (HRP, Ledoit-Wolf, EVT-CVaR, Leland buffer bands), and autonomous OMS execution.

Key Pipeline Layers:
1. Data Ingestion & Persistence (`StockPriceDB`, `MarketIndicatorStorage`, `EarningsDataFetcher`, `DARTCorpMapper`)
2. 31 Multi-Factor Alpha Engines (`src/core/`, `src/ai/`)
3. Factor Orthogonalization & Signal Normalization (`CrossSectionalScoreNormalizer`, `FactorOrthogonalizer`, `FactorSuppression`, `HybridCalibrator`, `EnsembleScorer`)
4. Portfolio Allocation & Tail Risk Budgeting (`PortfolioOptimizer`, `PortfolioAllocator`, `RiskManager`)
5. Execution OMS & Slippage Feedback (`ExecutionOMSEngine`, `AlmgrenChrissScheduler`, `TurnoverOptimizer`, `SlippageFeedbackEngine`)
6. Pipeline Orchestration (`trading_system/run_pipeline.py`)

## Feature Inventory (R1 ~ R4 / V6)
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| F01 | Cross-Sectional Score Normalizer | Build `CrossSectionalScoreNormalizer` (Percentile Rank / Winsorized Gaussian CDF) in `src/ai/score_normalizer.py` and apply to all 31 strategy inputs in `EnsembleScoringEngine` | M1 | R1 Survey | ✅ COMPLETED |
| F02 | Missing Strategy Zero-Weighting | Dynamic zero-weighting of uncalculated/missing strategy signals per ticker and exact active weight re-normalization ($\sum_{k \in \text{Active}} \tilde{w}_{i,k} = 1.0$) in `EnsembleScoringEngine` | M1 | R1 Survey | ✅ COMPLETED |
| F03 | Elimination of Artificial 0.50 Defaults | Purge all artificial `.fillna(0.50)` and default 0.50 mappings across strategy engines (`accruals_quality.py`, `valueup_catalyst.py`, `short_interest_squeeze.py`, `trend_efficiency.py`, `insider_buying.py`, `earnings_tone_drift.py`, `iv_skew.py`, `run_pipeline.py`) | M1 | R1 Survey | ✅ COMPLETED |
| F04 | Dynamic Market Filing Lag | Implement market-specific statutory lag (KRX 45 days, US 40 days) and immediate override on confirmed authentic public filing dates (`filing_date`/`rcept_dt`) across `earnings_data.py`, `prediction_model.py`, `run_pipeline.py` | M2 | R2 Survey | ✅ COMPLETED |
| F05 | Stratified Training Sampling | Multi-Level Stratified Sampling across Market × Sector × Market-Cap Quantiles in `prepare_training_data` (`prediction_model.py`, `run_pipeline.py`) replacing naive `random.sample()` | M2 | R2 Survey | ✅ COMPLETED |
| F06 | Elimination of Fake Stat-Arb BENCHMARK Pairs | Complete removal of artificial `(sym, 'BENCHMARK')` fallback injection in `run_pipeline.py` and `src/core/stat_arb.py`, ensuring only statistically valid cointegrated pairs are processed | M2 | R2 Survey | ✅ COMPLETED |
| F07 | Global Socket Timeout Removal & Adaptive Retries | Remove `socket.setdefaulttimeout(5)` from `run_pipeline.py`; Implement localized adaptive timeouts (8s/15s/25s) and jittered exponential backoff for `fred_client.py`, `ecos_client.py`, `dart_corp_mapper.py`, `market_data_handler.py` | M3 | R3 Survey | ✅ COMPLETED |
| F08 | FallbackMetadataDict & Normalization NaN Defense | Defend against zero-volume / missing denominator collapse in `apply_market_normalization`, enforce `safe_divide` in `_create_features`, sanitize covariance matrices (`np.nan_to_num`) in `FactorOrthogonalizerEngine` | M3 | R3 Survey | ✅ COMPLETED |
| F09 | VIX Term Structure & Velocity Buffering | Incorporate 5-day VIX velocity ($\Delta \text{VIX}_{5d}$) and Term Structure Inversion Ratio ($R_{\text{term}} = \text{VIX}/\text{VIX3M}$ or $20\text{d EMA}$ proxy) into `CrisisDetector` (`risk_manager.py`) to soften rigid gating during post-panic recovery rallies | M3 | R3 Survey | ✅ COMPLETED |
| F10 | Full Test Suite 100% Pass & Zero Lookahead Verification | Execute `.venv/Scripts/python.exe -m pytest tests/ -v` (1,569+ tests) with 100% PASS, zero regressions, and full integrity compliance | M4 | R4 Survey | ✅ COMPLETED |

## Milestones
| # | Name | Scope | Dependencies | Status | Verification |
|---|------|-------|-------------|--------|--------------|
| M1 | R1: 31-Strategy Score Normalization & Dynamic Weighting | F01, F02, F03 | None | ✅ COMPLETED | 100% Pass (`tests/test_score_normalizer.py`, `tests/test_ensemble_scorer.py`) |
| M2 | R2: Data Pipeline Refinement (Filing Lag, Stratified Sampling, Stat-Arb) | F04, F05, F06 | None | ✅ COMPLETED | 100% Pass (`tests/test_phase2_pit_universe_and_delisting.py`, `tests/test_stat_arb_execution.py`) |
| M3 | R3: Stability, Adaptive Timeouts, NaN Defense & VIX Buffering | F07, F08, F09 | None | ✅ COMPLETED | 100% Pass (`tests/test_network_hardening.py`, `tests/test_risk_manager.py`) |
| M4 | R4: Comprehensive Full Test Suite (1,569+ Tests) & Integrity Audit | F10 | M1, M2, M3 | ✅ COMPLETED | 1,569 / 1,569 Tests Passing (100%) |

## Interface Contracts

### 1. `CrossSectionalScoreNormalizer` ↔ `EnsembleScoringEngine`
- Class: `src/ai/score_normalizer.py:CrossSectionalScoreNormalizer`
- Signature: `normalize_cross_section(df: pd.DataFrame, score_cols: List[str], method: str = 'percentile_rank', group_col: Optional[str] = 'market') -> pd.DataFrame`
- Invariant: Output scores are strictly bounded in $[0.0, 1.0]$ with uniform variance, preserving authentic `NaN` for missing strategies.

### 2. `Dynamic Filing Lag` ↔ `EarningsData` & `PredictionModel`
- Function: `get_filing_lag_days(market: str, symbol: Optional[str] = None) -> int` (KRX: 45, US: 40)
- Invariant: If `filing_date` or `rcept_dt` is available and $\le \text{as\_of\_date}$, $\text{date\_available} = \text{filing\_date}$. Otherwise $\text{date\_available} = \text{period\_end} + \Delta_{\text{lag}}$. Merged strictly backward via `pd.merge_asof`.

### 3. `Stratified Sampling` ↔ `prepare_training_data`
- Function: `stratified_sample_symbols(symbols: List[str], universe_df: pd.DataFrame, sample_size: int, market: str, seed: int = 42) -> List[str]`
- Invariant: Guarantees proportional representation across sector and market-cap quartiles without random omission of mega/large-caps.

### 4. `StatisticalArbitrageEngine` ↔ Pipeline & Ensemble
- Contract: If zero cointegrated pairs meet Engle-Granger ADF ($p < 0.05$) and half-life criteria, return empty list `[]` / empty DataFrame without creating synthetic benchmark pairs. `EnsembleScoringEngine` dynamically zero-weights `stat_arb` for all tickers.

### 5. `Adaptive Network Client` ↔ External APIs
- Base helper: Localized timeout tuple/escalation `(connect=8s, read=15s)` with up to 3 retries and exponential backoff with jitter. Global socket timeout is never modified.

### 6. `CrisisDetector` ↔ VIX Dynamics
- Signature: `evaluate(vix: Optional[float] = None, ..., vix_history: Optional[List[float]] = None, vix3m: Optional[float] = None) -> Dict[str, Any]`
- Invariant: When `vix >= 30.0`, if $\Delta \text{VIX}_{5d} < -5.0$ and $R_{\text{term}} < 0.95$ (contango relief), crisis level softens to `WATCH` instead of locking into `ACTIVE`.

## Code Layout & Verified Test Map
- **Score Normalization & Dynamic Weighting**:
  - Implementation: `trading_system/src/ai/score_normalizer.py`, `trading_system/src/ai/ensemble_scorer.py`
  - Tests: `tests/test_score_normalizer.py`, `tests/test_regime_ensemble.py`
- **Data Pipeline Refinements**:
  - Implementation: `trading_system/src/data_layer/earnings_data.py`, `trading_system/src/data_layer/dart_corp_mapper.py`, `trading_system/src/ai/prediction_model.py`, `trading_system/src/core/stat_arb.py`
  - Tests: `tests/test_fast_cointegration.py`, `tests/test_pipeline_integration.py`
- **Network Hardening & Risk Defense**:
  - Implementation: `trading_system/src/data_layer/fred_client.py`, `trading_system/src/data_layer/ecos_client.py`, `trading_system/src/risk/risk_manager.py`
  - Tests: `tests/test_network_hardening.py`, `tests/test_risk_manager.py`
- **Full Suite Regression Verification**:
  - 1,569 tests collected and verified passing across unit, integration, and adversarial stress suites.
