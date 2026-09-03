# Project: Stock Trading System Pipeline & 37-Strategy Institutional Trading Architecture

## Architecture
- **Data & Ingestion Layer**: `src/data_layer/indicator_storage.py`, `src/data_layer/earnings_data.py`, `src/persistence/database.py`, `download_db.py`, `preseed_data.py`.
- **Model Training & Inference Layer**: `src/ai/prediction_model.py`, `src/ai/vcp_ml_predictor.py`, `src/ai/vcp_detector.py`, `train_models.py`, `run_pipeline.py`.
- **37-Strategy Factor Engine & Ensemble**: `src/core/*`, `src/ai/score_normalizer.py`, `src/ai/ensemble_scorer.py`, `src/ai/factor_orthogonalizer.py`, `src/core/strategy_registry.py`.
- **Portfolio & Risk Management Layer**: `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/risk/risk_manager.py`, `src/analysis/portfolio_optimizer.py`, `src/execution/oms_engine.py`, `src/execution/slippage_feedback.py`.
- **Reporting & Visualization Layer**: `src/pipeline/reporter.py`, `trading_system/generate_report.py`, `gh-pages/index.html`.
- **CI/CD & Verification Layer**: `.github/workflows/pipeline.yml`, `preseed.yml`, `training.yml`, `trading_system/scripts/verify_gha_artifacts.py`, `merge_predictions.py`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F01 | GHA 5-Market Pipeline Integrity | Validate and patch workflow scripts (`pipeline.yml`, `preseed.yml`, `training.yml`) for 5 markets end-to-end | M1 | Survey 1 / ORIGINAL_REQUEST R1 |
| F02 | GHA Static List & Cache Fallback | Add `lstm_predictions.txt` to `pipeline.yml` and `restore-keys` to `training.yml` | M1 | Survey 1 / ORIGINAL_REQUEST R1 |
| F03 | 31-Strategy Canonical Master Sequence | Standardize strategy ordering 1~31 across `AGENTS.md`, `run_pipeline.py`, and `reporter.py` | M2 | Survey 2 / ORIGINAL_REQUEST R2 |
| F04 | GHA Artifact Verifier 31-Strategy Expansion | Expand `verify_gha_artifacts.py` and `SKILL.md` from 23 to all 31 strategies in canonical order | M2 | Survey 2 / ORIGINAL_REQUEST R2 |
| F05 | Full Prediction Output Verification | Expand `run_pipeline.py` verification files list to cover all 31 strategy `.txt` files | M2 | Survey 2 / ORIGINAL_REQUEST R2 |
| F06 | Card 1: Market Regime & Risk Gates Console | Consolidate 2D Regime, Crisis Detector, VIX Velocity & Term Structure, Macro Grid into unified Card 1 | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F07 | Card 2: Strategy Coverage & Missingness Center | Consolidate 31-Strategy Health Monitor, Dynamic Status Filters, Missingness Reasons, and CPCV/PBO Stress Test into unified Card 2 | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F08 | Card 3: Portfolio Optimization & Execution OMS | Consolidate HRP Donut, Market Exposure, EVT-CVaR Tail Risk, Leland Buffer Bands, and Slippage Feedback into unified Card 3 | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F09 | 31-Strategy Canonical Tab Navigation & Responsive UX | Standardize 1~31 tab sequence, responsive desktop/mobile layouts, tooltips, and stock drawer factor breakdown | M3 | Survey 3 / ORIGINAL_REQUEST R3 |
| F10 | E2E Artifact Verification & 100% Test Suite Pass | Run full pytest test suite and `verify_gha_artifacts.py` validating 100% pass and non-zero artifacts | M4 | ORIGINAL_REQUEST Acceptance Criteria |
| F11 | 37-Strategy Factor Expansion | Implement strategies 32~37 (Cross-Asset Spillover, Supply Chain GNN, Range Expansion Breakout, Dual Correction, Index Rebalance, Overnight Gap Reversal) | M5 | Institutional Expansion R14, R15 |
| F12 | Unified Institutional Portfolio Allocator | Implement `UnifiedPortfolioAllocator` with BL + HERC + RP + CVaR 4-model regime blending & 3/2-power market impact penalty | M6 | Institutional Expansion R15 |
| F13 | OMS Gate 8 Synthetic Beta Inverse Hedge | Add Gate 8 for automated inverse ETF hedging during Bear/Crisis regimes and fix currency denominator | M6 | Execution OMS R15 |
| F14 | Comprehensive V8 System Integrity Remediation | Resolve 43 system defects (Critical 13, High 16, Medium 14) across data lag, causality, PSD flooring, and pooling | M7 | V8 Integrity Audit |
| F15 | World-Class Quant & Trader Enhancements | Continuous Fractional Kelly, Midpoint Peg, Intraday ATR Trailing Ratchet, and Top-K concentration | M8 | World-Class Alpha Upgrade |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | GHA Pipeline & Model Integrity (R1) | F01, F02: GHA workflows, caching fallback, 5-market pipeline data seeding & model training | none | DONE |
| M2 | 31-Strategy Canonical Sequence Unification (R2) | F03, F04, F05: Canonical sequence 1~31 across pipeline, verifier, SKILL.md, and text outputs | M1 | DONE |
| M3 | Dashboard Metric Consolidation & UX Enhancement (R3) | F06, F07, F08, F09: 3 unified consolidated cards, 31 canonical tabs, responsive design in `generate_report.py` | M2 | DONE |
| M4 | E2E Testing & Full Verification | F10: 100% pytest pass (1,569 tests, 0 fails), artifact non-zero verification across 5 markets, gh-pages validation | M1, M2, M3 | DONE |
| M5 | 37-Strategy Factor Engine Scaling | F11: Strategies 32~37 implementation, scoring pipeline, and output reports | M4 | DONE |
| M6 | Institutional Portfolio & OMS Gate 8 | F12, F13: `UnifiedPortfolioAllocator` 4-model blending, OMS Gate 8 synthetic inverse hedge overlay | M5 | DONE |
| M7 | V8 System Integrity Remediation | F14: 43 defects resolved across data pipeline, causality, covariance shrinkage, and DB connection pooling | M6 | DONE |
| M8 | World-Class Trader Alpha Upgrade & 2,130+ Tests | F15: Top-K concentration, fractional Kelly, tick grid rounding, and 2,130 pytest suite 100% pass | M7 | DONE |

## Interface Contracts
### GHA Workflows ↔ Pipeline Scripts
- `.github/workflows/pipeline.yml` executes `run_pipeline.py` producing per-market `result_split/*_{MARKET}.txt`.
- `merge_predictions.py` merges split files for all 37 strategies into `trading_system/result/*.txt` and invokes `generate_run_snapshot.py`.
- `generate_report.py` reads `trading_system/result/*.txt` and indicator SQLite DBs to produce `gh-pages/index.html`.

### 37-Strategy Canonical Specification (1~37)
1: `regression`, 2: `surge`, 3: `lead_lag`, 4: `vcp_rule`, 5: `vcp_ml`, 6: `lstm`, 7: `stat_arb`, 8: `sector_rotation`, 9: `rim_valuation`, 10: `event_driven`, 11: `mq_factor`, 12: `iv_skew`, 13: `order_flow`, 14: `short_term_reversal`, 15: `arm_factor`, 16: `card_factor`, 17: `latr_factor`, 18: `inst_foreign_sector`, 19: `supply_chain`, 20: `sentiment`, 21: `factor_neutralized`, 22: `vol_target`, 23: `microstructure`, 24: `accruals_quality`, 25: `short_squeeze`, 26: `valueup_catalyst`, 27: `trend_efficiency`, 28: `gamma_squeeze`, 29: `insider_buying`, 30: `darkpool`, 31: `earnings_tone_drift`, 32: `cross_asset_spillover`, 33: `supply_chain_gnn`, 34: `range_expansion_breakout`, 35: `dual_correction`, 36: `index_rebalance`, 37: `overnight_gap_reversal`.

## Code Layout
- `trading_system/run_pipeline.py`: Main orchestration script
- `trading_system/generate_report.py`: HTML dashboard generator
- `src/pipeline/reporter.py`: Pipeline summary text reporter
- `trading_system/scripts/verify_gha_artifacts.py`: CI artifact verifier
- `trading_system/scripts/merge_predictions.py`: 37-strategy multi-market file merger
- `src/risk/unified_portfolio_allocator.py`: Institutional multi-model portfolio allocator
- `src/execution/oms_engine.py`: 8-Safety Gate execution engine
- `tests/`: Automated unit, integration, and e2e test suite (2,130 items)
