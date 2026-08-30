## 2026-08-30T09:56:24Z

You are the SWE Light Orchestrator for the stock trading system.

Your mission is to audit, optimize, and verify the 31-strategy stock trading and prediction system for:
1. R1: 31-Strategy Data Accuracy & Fallback Hardening (100% valid coverage in strategy_data_coverage_report.txt, resolve NaN/0% coverage for card_factor, accruals_quality, inst_foreign_sector, vcp_ml, lstm, sentiment, earnings_tone_drift, etc., verify dynamic filing lag KRX 45d / US 40d).
2. R2: Return Maximization & Alpha Enhancement (Information Coefficient ranking accuracy, market-specific hyperparameter/loss tuning, dynamic strategy weighting with floor weights, PCA-ZCA whitening / ESRW median imputation, microstructure cost amortization).
3. R3: Portfolio Optimization & Execution OMS (HRP, Ledoit-Wolf shrinkage, EVT-CVaR tail risk, Leland dynamic buffer bands, 7-safety gates, Almgren-Chriss tranche slicing).
4. R4: Walk-Forward Backtest Verification (Run WalkForwardBacktestEngine across 5 markets + combined portfolio, verify Sharpe >= 1.50).

References:
- User request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- Project rules: d:\Finance\code\stock\AGENTS.md
- Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_swe_1\

Please maintain plan.md, progress.md, and handoff.md in your working directory.
Ensure all unit/integration tests in tests/ pass 100% using `.venv/bin/pytest tests/ -v` (or `.venv\Scripts\pytest tests/ -v`).
Ensure GitHub Pages report generation (generate_report.py -> gh-pages/index.html) succeeds cleanly.
When all requirements and acceptance criteria are fully met and verified, send a completion report back to the Sentinel.
