# Project: 37 Strategies Overhaul & Coverage Assurance

## Architecture
- 37 Multi-factor Strategies:
  1. XGBoost Regression (`pipeline_result.txt`)
  2. Surge Classifier (`surge_predictions.txt`)
  3. Lead-Lag (`lead_lag_predictions.txt`)
  4. VCP Rule (`vcp_patterns.txt`)
  5. VCP ML (`vcp_ml_predictions.txt`)
  6. Strict Causal LSTM (`lstm_predictions.txt`)
  7. Stat-Arb Cointegration (`stat_arb_predictions.txt`)
  8. Sector Rotation (`sector_predictions.txt`)
  9. RIM Valuation (`rim_predictions.txt`)
  10. Event-Driven (`event_driven_predictions.txt`)
  11. Momentum Quality (MQ) (`mq_factor_predictions.txt`)
  12. Options IV Skew (`iv_skew_predictions.txt`)
  13. Order Flow Imbalance (`order_flow_predictions.txt`)
  14. Short-Term Reversal (`short_term_reversal_predictions.txt`)
  15. Analyst Revision Momentum (ARM) (`arm_factor_predictions.txt`)
  16. Cross-Asset Regime Divergence (CARD) (`card_factor_predictions.txt`)
  17. Liquidity-Adjusted Tail Risk (LATR) (`latr_factor_predictions.txt`)
  18. Inst & Foreign Sector (`inst_foreign_sector_predictions.txt`)
  19. Supply Chain Momentum (`supply_chain_predictions.txt`)
  20. NLP Sentiment Catalyst (`sentiment_predictions.txt`)
  21. Multi-Factor Style Neutralizer (`factor_neutralized_predictions.txt`)
  22. Dynamic Volatility Targeting (`vol_target_predictions.txt`)
  23. Microstructure Imbalance (`microstructure_predictions.txt`)
  24. Accruals Quality Anomaly (`accruals_quality_predictions.txt`)
  25. Short Interest & Squeeze (`short_squeeze_predictions.txt`)
  26. Value-Up & Shareholder Yield (`valueup_catalyst_predictions.txt`)
  27. Kaufman Trend Efficiency (`trend_efficiency_predictions.txt`)
  28. Gamma Squeeze (`gamma_squeeze_predictions.txt`)
  29. Insider Buying (`insider_buying_predictions.txt`)
  30. Darkpool & HFT Flow (`darkpool_predictions.txt`)
  31. Earnings Tone Drift (`earnings_tone_drift_predictions.txt`)
  32. Cross-Asset Spillover Momentum (`cross_asset_spillover_predictions.txt`)
  33. Supply Chain GNN (`supply_chain_gnn_predictions.txt`)
  34. Range Expansion Breakout (`range_expansion_predictions.txt`)
  35. Dual Correction (`dual_correction_predictions.txt`)
  36. Index Rebalance Structural Flow (`index_rebalance_predictions.txt`)
  37. Overnight Gap Reversal (`overnight_gap_predictions.txt`)
- Normalization & Orthogonalization: `CrossSectionalScoreNormalizer`, `FactorOrthogonalizerEngine`
- Dynamic Weighted Ensemble: `EnsembleScoringEngine` (6-Regime Matrix, Microstructure Costs)
- Portfolio Risk Allocation: `UnifiedPortfolioAllocator` (BL, HERC, RP, EVT-CVaR, Leland Buffer)
- Execution OMS: `ExecutionOMSEngine`, `AlmgrenChrissScheduler`
- Reporting & Artifacts: `PredictionReporter`, `StrategyCoverageAnalyzer`, `verify_gha_artifacts.py`

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone.
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Stat-Arb FDR & Neutral Fix | Fix FDR rank calculation & emit 0.50 for neutral pairs | M1 | Survey (Explorer 1) |
| 2 | Short Squeeze Proxy Fallback | Add price-volume microstructure proxy for missing short data | M1 | Survey (Explorer 1) |
| 3 | RIM Valuation US DB Proxy | Add price-trend proxy when BPS missing for NASDAQ/Russell | M1 | Survey (Explorer 1) |
| 4 | Sentiment & Tone Truncation Removal | Remove 100-sym cap & provide universe momentum sentiment | M1 | Survey (Explorer 1) |
| 5 | Sparse Signal Neutral Filling | Assign 0.50 neutral baseline to non-setup stocks (VCP, Lead-Lag) | M1 | Survey (Explorer 1) |
| 6 | Standardized Output Reporting | Replace inline writers with PredictionReporter; eliminate "데이터 없음" | M2 | Survey (Explorer 2) |
| 7 | Coverage Analyzer Scoping | Scope denominator to active market in single-target runs | M2 | Survey (Explorer 2) |
| 8 | Market Split File Reliability | Ensure result_split files are populated with >= 10 valid items | M2 | Survey (Explorer 2) |
| 9 | Pipeline Pre-Verification Gate | Runtime check in run_pipeline.py for >= 10 valid predictions | M2 | Survey (Explorer 2) |
| 10 | Ensemble Defensive Weight Reservation | Prevent defensive strategy dropout from inflating momentum beta | M3 | Survey (Explorer 3) |
| 11 | Portfolio Allocation Normalization | Verify Net Expected Return sorting and 4-model blending | M3 | Survey (Explorer 3) |
| 12 | Regression Test Suite Verification | Ensure pytest tests/ passes 100% | M4 | Survey (Explorer 3) |
| 13 | Pipeline End-to-End Validation | Run pipeline verification across all 5 markets | M4 | Survey (Explorer 2, 3) |
| 14 | HTML Dashboard & Artifact Verification | Confirm generate_report.py and verify_gha_artifacts.py pass | M4 | Survey (Explorer 2) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Strategy Defect & Fallback Remediation | Fix stat_arb, short_squeeze, rim_valuation, sentiment, tone drift, vcp, lead-lag | none | IN_PROGRESS |
| M2 | Output Generation & Coverage Reporting | Standardize PredictionReporter, fix CoverageAnalyzer, ensure >= 10 items | M1 | PLANNED |
| M3 | Ensemble Scoring & Risk Allocation | Weight re-normalization, defensive reservation, portfolio allocation | M1, M2 | PLANNED |
| M4 | Regression & E2E Validation | pytest tests/, pipeline validation, verify_gha_artifacts, HTML report | M1, M2, M3 | PLANNED |

## Interface Contracts
### Strategy Engines -> EnsembleScoringEngine
- Input: `dict[str, pd.DataFrame]` with strategy name as key, DataFrame indexed or with column `symbol` and strategy score column.
- Required: Every symbol in target market must have finite float score in [0.0, 1.0] (or neutral 0.50 for unselected stocks). Zero-coverage / NaN completely eliminated.

### PredictionReporter -> File System
- Output files: `trading_system/result/{strategy_file}.txt` and `trading_system/result_split/{strategy_file}_{MARKET}.txt`.
- Format: Standard header + tab/space-separated table. Every strategy must contain >= 10 non-zero predictions per market. No `"데이터 없음"` text.

### StrategyCoverageAnalyzer -> Coverage Report
- Input: `ensemble_df` with `raw_scores` attribute, active market target.
- Metric: Valid coverage = count(finite & notna) / active_market_symbols >= 95.0%.

## Code Layout
- `trading_system/src/core/`: Strategy engines (`stat_arb.py`, `short_interest_squeeze.py`, `rim_valuation.py`, etc.)
- `trading_system/src/pipeline/`: `strategy_executor.py`, `prediction_reporter.py`
- `trading_system/src/ai/`: `ensemble_scorer.py`, `score_normalizer.py`, `factor_orthogonalizer.py`
- `trading_system/src/risk/`: `unified_portfolio_allocator.py`
- `trading_system/src/analysis/`: `coverage_analyzer.py`
- `trading_system/run_pipeline.py`: Main pipeline orchestration script
- `trading_system/scripts/verify_gha_artifacts.py`: CI artifact validator
