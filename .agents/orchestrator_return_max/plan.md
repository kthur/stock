# Quantitative Trading System Return Maximization Plan

## Architecture & Scope
5-Market Trading System (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) with 31 Multi-Factor / Multi-Model Strategies, 2D Regime Engine, Dynamic Ensemble, Portfolio Optimization, and Execution OMS.

## Planned Milestones
| # | Milestone | Scope | Deliverable / Output | Status |
|---|---|---|---|---|
| M1 | Deep Exploratory Diagnostic (AI & LSTM Models) | `src/ai/prediction_model.py`, `src/ai/lstm_model.py`, `src/ai/vcp_*.py`, calibration | Audit findings on predictive power, causal sequences, information leakage, overfitting, horizon scaling | PLANNED |
| M2 | Deep Exploratory Diagnostic (31 Strategy Engines) | All 31 strategy files under `src/core/` and `src/ai/`, data dependencies | SNR, factor decay, alpha degradation, cross-market applicability, classification (Strong Alpha, Moderate, Weak, Noise) | PLANNED |
| M3 | Deep Exploratory Diagnostic (Ensemble, Regime & Orthogonalization) | `src/ai/ensemble_scorer.py`, `src/ai/factor_orthogonalizer.py`, `src/ai/factor_suppression.py`, `src/risk/regime_detector.py` | Gram-Schmidt / PCA-ZCA whitening, VIF suppression, zero-centering, transaction cost modeling | PLANNED |
| M4 | Deep Exploratory Diagnostic (Portfolio Opt, Tail Risk & OMS) | `src/analysis/portfolio_optimizer.py`, `src/risk/portfolio_allocator.py`, `src/risk/risk_manager.py`, `src/execution/*` | HRP, Ledoit-Wolf shrinkage, EVT-CVaR, Leland buffer bands, 6-safety gates, slippage feedback | PLANNED |
| M5 | Return Maximization Master Report Synthesis & Drafting | Author `comprehensive_return_maximization_master_report.md` | Complete 5-section master report deliverable | PLANNED |
| M6 | Independent Review, Challenger Verification & Forensic Audit | Rigorous multi-agent review, verification of all formulas, metrics, code citations | `GATE_STATUS.md` approval & audit clearance | PLANNED |
