# Project: 5th Comprehensive Stock Trading System Optimization (V5-01 ~ V5-32)

## Architecture
Multi-factor, multi-model automated quantitative trading and execution platform across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
Key layers:
1. Data Ingestion & Persistence (`StockPriceDB`, `MarketIndicatorStorage`, `EarningsData`)
2. 31-Strategy Multi-Factor Alpha Engine
3. Signal Refinement & Orthogonalization (`FactorOrthogonalizer`, `FactorSuppression`, `HybridCalibrator`, `EnsembleScorer`)
4. Portfolio Optimization & Tail Risk Budgeting (`PortfolioOptimizer`, `PortfolioAllocator`, `RiskManager`)
5. Execution OMS & Closed-Loop Feedback (`ExecutionOMSEngine`, `SlippageFeedbackEngine`)
6. Pipeline Orchestration & CI/CD (`run_pipeline.py`, GitHub Pages generator)

## Feature Inventory (V5-01 through V5-32)
| # | Task ID | Domain | Severity | Task Name | Milestone | Target File |
|---|---------|--------|----------|-----------|-----------|-------------|
| 1 | V5-01 | Domain 1 (AI/ML) | 🔴 CRITICAL | PCA-ZCA Whitening Variance Explosion on Rank-Deficient Score Matrices ($N < K$) | M1 | `trading_system/src/ai/factor_orthogonalizer.py` |
| 2 | V5-02 | Domain 1 (AI/ML) | 🟠 HIGH | WLS Mathematical Weighting Distortion & Pandas .loc Alignment KeyError | M1 | `trading_system/src/ai/factor_orthogonalizer.py` |
| 3 | V5-03 | Domain 1 (AI/ML) | 🟠 HIGH | Strategy Alias Mismatch in Cluster Map Bypassing Regime Noise Suppression | M1 | `trading_system/src/ai/factor_suppression.py` |
| 4 | V5-04 | Domain 1 (AI/ML) | 🟠 HIGH | Dynamic Sharpe Weight Bounding Floor Disconnected (150:1 Concentration) | M1 | `trading_system/src/ai/ensemble_scorer.py` |
| 5 | V5-05 | Domain 1 (AI/ML) | 🟠 HIGH | Disconnected Objective Function & 4 Phantom Hyperparameters in VCP Rule HPO | M1 | `trading_system/src/ai/optuna_tuner.py` |
| 6 | V5-06 | Domain 1 (AI/ML) | 🔴 CRITICAL | Platt Scaling Domain Mismatch (Log-Odds vs Linear Probability) Collapsing Probabilities | M1 | `trading_system/src/ai/vcp_ml_predictor.py` |
| 7 | V5-07 | Domain 2 (Portfolio) | 🟠 HIGH | Black-Litterman Prior vs View Scale Mismatch & Volatility Maximization on Negative Return | M2 | `trading_system/src/analysis/portfolio_optimizer.py` |
| 8 | V5-08 | Domain 2 (Portfolio) | 🟠 HIGH | Clayton Copula Asymmetric Correlation Non-PSD Distortion & Diagonal Under-Regularization | M2 | `trading_system/src/risk/portfolio_allocator.py` |
| 9 | V5-09 | Domain 2 (Portfolio) | 🟡 MEDIUM | Reverse Window Partitioning Starving Early CV Folds of Historical Training Data | M2 | `trading_system/src/ai/prediction_model.py` |
| 10 | V5-10 | Domain 2 (Portfolio) | 🟠 HIGH | HRP Inverse-Variance Cluster Division-by-Zero & NaN Weight Corruption | M2 | `trading_system/src/analysis/portfolio_optimizer.py` |
| 11 | V5-11 | Domain 2 (Portfolio) | 🟡 MEDIUM | TypeError on np.isnan(None) & Asymmetric Macro History Queue Desynchronization | M2 | `trading_system/src/risk/risk_manager.py` |
| 12 | V5-12 | Domain 2 (Portfolio) | 🟡 MEDIUM | Fundamental Column Schema Mismatch Generating Spurious Missingness Classification | M2 | `trading_system/src/analysis/coverage_analyzer.py` |
| 13 | V5-13 | Domain 3 (Strategy) | 🔴 CRITICAL | res_rows.append NameError Crashing Fallback Score Assignments | M3 | `trading_system/src/core/card_factor.py` |
| 14 | V5-14 | Domain 3 (Strategy) | 🔴 CRITICAL | Missing **kwargs in compute_gamma_squeeze_scores Crashing Pipeline Callers | M3 | `trading_system/src/core/gamma_squeeze.py` |
| 15 | V5-15 | Domain 3 (Strategy) | 🔴 CRITICAL | Empty DataFrame Returned on Default Invocation in Microstructure Engine | M3 | `trading_system/src/core/hft_engine.py` |
| 16 | V5-16 | Domain 3 (Strategy) | 🔴 CRITICAL | 10x–20x Scale Divergence Between Proxy and Explicit Short Squeeze Scores | M3 | `trading_system/src/core/short_interest_squeeze.py` |
| 17 | V5-17 | Domain 3 (Strategy) | 🟠 HIGH | Missing US Leader Data in Split-Runner Inverting Lead-Lag Alpha | M3 | `trading_system/src/core/cross_border_lead_lag.py` |
| 18 | V5-18 | Domain 3 (Strategy) | 🟠 HIGH | OBV Trend Slope Division by Arbitrary Zero-Crossing Cumulative Volume | M3 | `trading_system/src/core/order_flow.py` |
| 19 | V5-19 | Domain 3 (Strategy) | 🟠 HIGH | Distressed Companies Ranked Before NaN Invalidation in RIM Valuation | M3 | `trading_system/src/core/rim_valuation.py` |
| 20 | V5-20 | Domain 3 (Strategy) | 🟠 HIGH | Direct String Comparison of 8-digit DART corp_code with 6-digit Stock Ticker | M3 | `trading_system/src/core/event_driven.py` |
| 21 | V5-21 | Domain 3 (Strategy) | 🟠 HIGH | Factor Neutralizer Rank-Deficient Regression Ridge Regularization | M3 | `trading_system/src/core/multi_factor_neutralizer.py` |
| 22 | V5-22 | Domain 3 (Strategy) | 🟠 HIGH | Stock Split Detector Permanently Corrupting Historical Price/Volume on Severe Market Crashes | M3 | `trading_system/src/persistence/database.py` |
| 23 | V5-23 | Domain 3 (Strategy) | 🟡 MEDIUM | Case-Sensitivity KeyError on Lowercase Column Names in Short-Term Reversal | M3 | `trading_system/src/core/short_term_reversal.py` |
| 24 | V5-24 | Domain 4 (Execution) | 🔴 CRITICAL | calculate_realized_slippage(sym) TypeError & Dataclass Return Mismatch Severing Closed-Loop OMS Feedback | M4 | `trading_system/src/execution/oms_engine.py`, `slippage_feedback.py` |
| 25 | V5-25 | Domain 4 (Execution) | 🔴 CRITICAL | Hardcoded 10,000 KRW Hedge Target Price Under-Hedging Inverse Overlay by 80% | M4 | `trading_system/src/execution/oms_engine.py` |
| 26 | V5-26 | Domain 3 (Strategy) | 🟡 MEDIUM | Downside Semi-Variance Distortion Calculating Variance Around Negative Mean in Options IV Skew | M3 | `trading_system/src/core/iv_skew.py` |
| 27 | V5-27 | Domain 3 (Strategy) | 🟡 MEDIUM | Artificially Compressed Score Range [0.212, 0.788] Suppressing Volatility Targeting Factor Variance | M3 | `trading_system/src/core/vol_target.py` |
| 28 | V5-28 | Domain 3 (Strategy) | 🟡 MEDIUM | Boundary Collapse on Single-Stock Invocation in Accruals Quality Engine | M3 | `trading_system/src/core/accruals_quality.py` |
| 29 | V5-29 | Domain 3 (Strategy) | 🟡 MEDIUM | Discontinuous Piecewise Step Jumps Distorting Smooth Gradient Factor Rankings | M3 | `trading_system/src/core/card_factor.py`, `arm_factor.py`, `mq_factor.py`, `hft_engine.py` |
| 30 | V5-30 | Domain 3 (Strategy) | 🟡 MEDIUM | False Positive Default Attribution in Insider Buying Transaction Type | M3 | `trading_system/src/core/insider_buying.py` |
| 31 | V5-31 | Domain 3 (Strategy) | 🟠 HIGH | String Type Pollution from Environment Overrides in Trading Configuration | M3 | `trading_system/src/config.py` |
| 32 | V5-32 | Domain 5 (Pipeline) | 🟡 MEDIUM | 20-Day Market Return Metric Scale Distortion in Pipeline Reporting | M5 | `trading_system/run_pipeline.py` |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Domain 1: AI/ML & Prediction Integrity | V5-01 ~ V5-06 | None | PLANNED |
| M2 | Domain 2: Portfolio & Risk Engineering | V5-07 ~ V5-12 | M1 | PLANNED |
| M3 | Domain 3: 31 Strategy Engines & Data Layer | V5-13 ~ V5-23, V5-26 ~ V5-31 | None | PLANNED |
| M4 | Domain 4: Execution OMS & Transaction Costs | V5-24 ~ V5-25 | None | PLANNED |
| M5 | Domain 5: Pipeline Orchestration & CI/CD | V5-32 | M1-M4 | PLANNED |
| M_FINAL | Full Regression & Verification | 100% test pass on tests/ | M1-M5 | PLANNED |

## Code Layout & Write Boundaries
- M1: `trading_system/src/ai/` (`factor_orthogonalizer.py`, `factor_suppression.py`, `ensemble_scorer.py`, `optuna_tuner.py`, `vcp_ml_predictor.py`)
- M2: `trading_system/src/analysis/portfolio_optimizer.py`, `coverage_analyzer.py`, `trading_system/src/risk/portfolio_allocator.py`, `risk_manager.py`, `trading_system/src/ai/prediction_model.py`
- M3: `trading_system/src/core/` (`card_factor.py`, `gamma_squeeze.py`, `hft_engine.py`, `short_interest_squeeze.py`, `cross_border_lead_lag.py`, `order_flow.py`, `rim_valuation.py`, `event_driven.py`, `multi_factor_neutralizer.py`, `short_term_reversal.py`, `iv_skew.py`, `vol_target.py`, `accruals_quality.py`, `arm_factor.py`, `mq_factor.py`, `insider_buying.py`), `trading_system/src/persistence/database.py`, `trading_system/src/config.py`
- M4: `trading_system/src/execution/oms_engine.py`, `trading_system/src/execution/slippage_feedback.py`
- M5: `trading_system/run_pipeline.py`
