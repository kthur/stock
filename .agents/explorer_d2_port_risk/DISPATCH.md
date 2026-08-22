## 2026-08-22T00:20:25Z
You are the Principal Portfolio Theorist & Risk Engineering Auditor (Domain 2: Portfolio & Risk Engineering).
Your working directory is: `d:\Finance\code\stock\.agents\explorer_d2_port_risk`
Workspace root: `d:\Finance\code\stock`

MANDATORY INPUTS:
- Read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` before starting.
- Read `d:\Finance\code\stock\AGENTS.md`.
- Reference historical reports `system_improvement_report_v1.md` through `system_improvement_report_v5.md` to guarantee ZERO DUPLICATION (100% novel issues).

TARGET SCOPE (Domain 2: Portfolio & Risk Engineering):
- `src/analysis/portfolio_optimizer.py` (Hierarchical Risk Parity HRP, Ledoit-Wolf covariance shrinkage, Black-Litterman, minimum variance, quasi-diagonalization, recursive bisection)
- `src/risk/portfolio_allocator.py` (EVT-CVaR extreme value tail risk budgeting, Leland dynamic no-trade buffer bands, leverage constraints, turnover penalty)
- `src/risk/risk_manager.py` (CrisisDetector, macro crisis stage gating, VIX/USDKRW thresholds, exposure caps, circuit breakers, emergency derisking)
- `src/analysis/coverage_analyzer.py` (StrategyCoverageAnalyzer, missingness metrics, coverage matrices)
