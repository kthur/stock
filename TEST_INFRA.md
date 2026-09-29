# E2E Test Infrastructure: 37 Multi-Factor Quant Strategies & 5-Market Pipeline

## 1. Test Philosophy
- **Opaque-Box & Requirement-Driven**: Tests interact with strategy engines, pipeline execution contexts, normalization/orthogonalization routines, ensemble scorers, and prediction report generators solely through external interfaces and contract outputs.
- **Exhaustive 4-Tier Test Pyramid**:
  - **Tier 1 (Feature Coverage)**: Direct verification of all 37 individual alpha strategies for valid, non-zero, finite score generation in [0.0, 1.0] (or valid regression return values) across standard inputs.
  - **Tier 2 (Boundary & Corner Cases)**: Stress testing edge conditions including missing data, minimal lookback windows (N=1, N=2, N=5), NaN/Inf inputs, unmapped symbols, and adaptive fallback scoring (assigning neutral 0.50 without failure).
  - **Tier 3 (Cross-Feature Combinations & Interactions)**: Aggregating all 37 strategy outputs into `EnsembleScoringEngine`, verifying cross-sectional normalization (`CrossSectionalScoreNormalizer`), orthogonalization (`FactorOrthogonalizerEngine` PCA-ZCA whitening and Gram-Schmidt decorrelation), defensive weight reservation, and 2D regime weighting.
  - **Tier 4 (Real-World Market Scenarios & File Generation)**: End-to-end evaluation across all 5 core markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) verifying file generation for both consolidated (`result/{file}.txt`) and per-market partitioned (`result_split/{file}_{MARKET}.txt`) files with >= 10 non-zero predictions per strategy.

---

## 2. Feature Inventory: 37 Multi-Factor Strategies across Tiers 1–4

| # | Strategy Key | Canonical Strategy Name | Output File | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (5-Market E2E) |
|---|--------------|-------------------------|-------------|:----------------:|:-----------------:|:----------------------:|:---------------------:|
| 1 | `regression` | XGBoost Multi-Horizon Regression | `pipeline_result.txt` | ✓ | ✓ | ✓ | ✓ |
| 2 | `surge` | Extreme Surge Probability Classifier | `surge_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 3 | `lead_lag` | 2-Tier Lead-Lag Shift Engine | `lead_lag_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 4 | `vcp_rule` | Volatility Contraction Pattern (Rule) | `vcp_patterns.txt` | ✓ | ✓ | ✓ | ✓ |
| 5 | `vcp_ml` | VCP ML Surge Predictor | `vcp_ml_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 6 | `lstm` | Strict Causal LSTM Regressor | `lstm_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 7 | `stat_arb` | Statistical Arbitrage Cointegration | `stat_arb_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 8 | `sector` | Sector Rotation & Relative Momentum | `sector_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 9 | `rim` | Residual Income Model (RIM) Valuation | `rim_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 10 | `event` | Event-Driven & DART Disclosure Catalyst | `event_driven_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 11 | `mq` | Momentum Quality (MQ) Factor | `mq_factor_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 12 | `iv_skew` | Options Put/Call IV Skew | `iv_skew_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 13 | `order_flow` | Order Flow Imbalance (MFI) | `order_flow_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 14 | `reversal` | Short-Term Mean Reversal | `short_term_reversal_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 15 | `arm` | Analyst Revision Momentum (ARM) | `arm_factor_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 16 | `card` | Cross-Asset Regime Divergence (CARD) | `card_factor_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 17 | `latr` | Liquidity-Adjusted Tail Risk (LATR) | `latr_factor_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 18 | `inst_foreign_sector` | Inst & Foreign 2-Month Sector Flow | `inst_foreign_sector_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 19 | `supply_chain` | Supply Chain Lead-Lag Momentum | `supply_chain_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 20 | `sentiment` | NLP & FinBERT Sentiment Catalyst | `sentiment_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 21 | `factor_neutralized` | Multi-Factor Style Neutralized Alpha | `factor_neutralized_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 22 | `vol_target` | Dynamic Volatility Targeting Risk Parity | `vol_target_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 23 | `microstructure` | Order Book Microstructure Imbalance | `microstructure_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 24 | `accruals_quality` | Accruals Quality Accounting Anomaly | `accruals_quality_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 25 | `short_squeeze` | Short Interest & Squeeze Catalyst | `short_squeeze_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 26 | `valueup_catalyst` | Value-Up & Shareholder Yield | `valueup_catalyst_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 27 | `trend_efficiency` | Kaufman Trend Efficiency Ratio | `trend_efficiency_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 28 | `gamma_squeeze` | Options Gamma & Delta Squeeze | `gamma_squeeze_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 29 | `insider_buying` | Corporate Insider Buying Catalyst | `insider_buying_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 30 | `darkpool` | Darkpool Flow & Block Trade Tracking | `darkpool_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 31 | `earnings_tone_drift` | Earnings Call Tone Drift NLP | `earnings_tone_drift_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 32 | `cross_asset_spillover` | Cross-Asset Spillover Momentum | `cross_asset_spillover_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 33 | `supply_chain_gnn` | Supply Chain GNN & Sector Flow | `supply_chain_gnn_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 34 | `range_expansion_breakout` | Range Expansion Breakout (NR7/CLV) | `range_expansion_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 35 | `dual_correction` | Dual Correction (Fibonacci + VWAP) | `dual_correction_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 36 | `index_rebalance` | Index Rebalance Structural Flow | `index_rebalance_predictions.txt` | ✓ | ✓ | ✓ | ✓ |
| 37 | `overnight_gap_reversal` | Overnight Gap Reversal | `overnight_gap_predictions.txt` | ✓ | ✓ | ✓ | ✓ |

---

## 3. Test Architecture & Runner Invocation

### Runner Command
```bash
# Execute the comprehensive 37-strategy E2E test suite
.venv\Scripts\python.exe -m pytest tests/test_37strategies_e2e.py -v

# Filter by tier
.venv\Scripts\python.exe -m pytest tests/test_37strategies_e2e.py -k "Tier1" -v
.venv\Scripts\python.exe -m pytest tests/test_37strategies_e2e.py -k "Tier2" -v
.venv\Scripts\python.exe -m pytest tests/test_37strategies_e2e.py -k "Tier3" -v
.venv\Scripts\python.exe -m pytest tests/test_37strategies_e2e.py -k "Tier4" -v
```

### Pass / Fail Semantics
- **Zero Failures**: Exit code 0 required across all test methods.
- **Score Validity**: All calculated strategy scores must be strictly finite numeric floats (no `NaN`, `Inf`, or `-Inf`).
- **Score Boundedness**: Normalized factor scores must be bounded in $[0.0, 1.0]$.
- **Report Integrity**: No `"데이터 없음"` text in generated report files; header format and columns must match canonical specification.
- **File System Persistence**: Main consolidated file and per-market partitioned files must exist on disk and be non-empty.

---

## 4. Quality & Coverage Thresholds

| Metric | Target Threshold | Validation Method |
|--------|------------------|-------------------|
| **Active Strategy Coverage** | 100% (37 / 37 strategies active) | `StrategyCoverageAnalyzer` & `EnsembleScoringEngine` health gate |
| **Minimum Non-Zero Predictions per Market** | $\ge 10$ predictions per strategy per market | File content parsing & DataFrame length assertions |
| **Missingness Rate** | 0.0% for core price-volume strategies, $\le 5.0\%$ for sparse fundamental strategies with 0.50 neutral fallback | `StrategyCoverageAnalyzer` missingness mode checks |
| **Market Coverage** | 5 core markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) | Per-market file existence checks (`result_split/{strategy}_{MARKET}.txt`) |
| **Ensemble Monotonicity & Simplex** | Weights sum $= 1.000000 \pm 10^{-5}$ across active regimes | `EnsembleScoringEngine` regime weight sum check |
| **Friction Deduction** | Net expected return $\le$ gross expected return | Verification of microstructure cost deductions |
