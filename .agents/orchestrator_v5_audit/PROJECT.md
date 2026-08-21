# Project: 5th Comprehensive System Improvement Report (`system_improvement_report_v5.md`)

## Architecture
Full-stack multi-disciplinary audit of the 31-strategy quantitative trading system (`kthur/stock`).
5 Core Audit Domains:
1. **AI/ML & Prediction Integrity**: XGBoost, VCP ML, Strict Causal LSTM, Optuna HPO, 31-Strategy Dynamic Ensemble (`src/ai/ensemble_scorer.py`), PCA-ZCA whitening & Gram-Schmidt orthogonalization (`src/ai/factor_orthogonalizer.py`), Isotonic/Platt calibration (`src/ai/prediction_model.py`, `src/ai/vcp_ml_predictor.py`).
2. **Portfolio & Risk Engineering**: HRP (`src/analysis/portfolio_optimizer.py`), Ledoit-Wolf covariance shrinkage, EVT-CVaR extreme value tail risk budgeting & Leland dynamic buffer bands (`src/risk/portfolio_allocator.py`), 2D Market Regime Engine, RiskManager & CrisisDetector gating (`src/risk/risk_manager.py`).
3. **31 Strategy Engines & Data Layer**: Event-Driven, Stat-Arb, Sector Rotation, MQ Factor, LATR, ARM, CARD, Microstructure, Accruals Quality, Short Squeeze, Value-Up, Trend Efficiency, Gamma Squeeze, Insider Buying, Tone Drift, Darkpool HFT, Supply Chain, NLP Sentiment, Factor Neutralized, Vol Targeting (`src/core/*`), timezone synchronization (KST/EST), DB transaction lifecycle & mutex locks (`src/persistence/database.py`, `src/data_layer/indicator_storage.py`, `src/data_layer/earnings_data.py`), survivor bias / lookahead filing lag (60-day lag enforcement).
4. **Execution (OMS) & Transaction Costs**: 6 Safety Gates (`src/execution/order_manager.py`), STT/SEC fee structure & Kyle/Almgren-Chriss market impact & bid-ask spread models (`src/config.py`, `src/ai/ensemble_scorer.py`), slippage feedback loop (`trade_logs.db`, `src/execution/slippage_feedback.py`), emergency liquidation mechanisms.
5. **Pipeline Orchestration & CI/CD & Testing**: `trading_system/run_pipeline.py` execution sequence, thread pool and memory management (float32 downcasting, garbage collection), GitHub Actions workflow caching, test isolation & coverage (`tests/*`).

## Zero-Overlap Baseline References
- `SYSTEM_IMPROVEMENT_REPORT.md`
- `docs/improvement_report.md`
- `docs/PORTFOLIO_SYSTEM_IMPROVEMENT_REPORT.md`
- `tests/test_phase1_improvements.py`
- `tests/test_phase2_improvements.py`
- `tests/test_phase3_improvements.py`
- `tests/test_phase4_improvements.py`
- `tests/test_six_structural_improvements.py`
- `tests/test_v2_structural_improvements.py`
- `tests/test_architectural_improvements.py`

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Survey & Prior Audits Baseline Inventory | Extract & index all 110 items from prior reports to enforce zero overlap | none | DONE |
| M2 | Domain Exploration 1 (AI/ML & Portfolio/Risk) | Deep code inspection of `src/ai/*`, `src/analysis/*`, `src/risk/*` | M1 | DONE |
| M3 | Domain Exploration 2 (Strategies, Data & OMS/Pipeline) | Deep code inspection of `src/core/*`, `src/persistence/*`, `src/data_layer/*`, `src/execution/*`, `trading_system/*` | M1 | DONE |
| M4 | Report Drafting & Synthesis | Author complete `system_improvement_report_v5.md` following the required structure | M2, M3 | DONE |
| M5 | Adversarial Review & Challenger Verification | Cross-verify exact line numbers, formulas, zero duplicates, and Python code validity | M4 | DONE |
| M6 | Forensic Integrity Audit & Final Gating | Independent auditor verification of source integrity and evidence accuracy | M5 | DONE |
