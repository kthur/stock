# Execution Plan: 31-Strategy Quantitative Trading System v6 Audit

## Objectives
1. Perform a 100% rigorous, zero-hallucination, full-stack audit across 5 domains of the 31-strategy quantitative trading system (`kthur/stock`).
2. Identify and document verified, novel issues (V6-01 ~) that have zero overlap with v1-v5 (142 historical items).
3. Produce `system_improvement_report_v6.md` with:
   - Comprehensive issue summary table
   - Deep-dive technical analyses with mathematical/financial formulas
   - Concrete Before/After Git Diff code snippets
   - Cross-cutting architectural roadmap & strategy diversification matrix
4. Conduct independent forensic and victory audit verification.

## 5 Audit Domains
- **Domain 1: AI/ML & Prediction Integrity**: XGBoost, VCP ML, Strict Causal LSTM, Optuna HPO, Ensemble Scorer, PCA-ZCA Whitening & Ridge Shrinkage, Platt/Isotonic Calibration, Feature Suppression & VIF.
- **Domain 2: Portfolio & Risk Engineering**: HRP, Ledoit-Wolf Shrinkage, EVT-CVaR Tail Risk, Leland Dynamic Buffer Bands, 2D Regime Engine, CrisisDetector & Gating.
- **Domain 3: 31-Strategy Engines & Data Layer**: Event-Driven, Stat-Arb, Sector Rotation, MQ, LATR, ARM, CARD, Microstructure, Accruals, Short Squeeze, Value-Up, Trend Efficiency, Gamma Squeeze, Insider Buying, Tone Drift, Darkpool HFT, Data Layer (SQLite WAL, filing lags, lookahead bias).
- **Domain 4: Execution OMS & Friction Costs**: 8 Safety Gates, STT/SEC Taxes & Spread Costs, Slippage Feedback Loop (`trade_logs.db`), Inverse ETF Hedge Overlay, Emergency Liquidation.
- **Domain 5: Pipeline, CI/CD & Architecture**: `run_pipeline.py` orchestration order, thread/memory pooling, GHA 5-matrix workflows, test isolation & coverage.

## Work Breakdown & Milestones
- **Milestone 1: Baseline Survey & Historical Map**
  - Extract all historical item keys and topics from v1-v5 to establish strict novelty exclusion filter.
- **Milestone 2: Domain Deep-Dive Audit Dispatches (Parallel Explorers)**
  - Explorer 1: Domain 1 (AI/ML & Prediction Integrity)
  - Explorer 2: Domain 2 (Portfolio & Risk Engineering)
  - Explorer 3: Domain 3 (31 Strategy Engines & Data Layer)
  - Explorer 4: Domain 4 (Execution OMS & Friction Costs)
  - Explorer 5: Domain 5 (Pipeline, CI/CD, Concurrency & Infrastructure)
- **Milestone 3: Synthesis & Rigorous Cross-Validation**
  - Verify exact file existence and line numbers in workspace.
  - Check zero overlap against v1-v5.
  - Reviewer/Challenger validation of mathematical/financial formulas and diffs.
- **Milestone 4: v6 Report Generation**
  - Draft and compile `system_improvement_report_v6.md` following the exact standard of v1-v5.
- **Milestone 5: Independent Forensic & Victory Audit**
  - Invoke `teamwork_preview_auditor` for full-stack forensic integrity verification.
- **Milestone 6: Final Review & Sentinel Notification**
