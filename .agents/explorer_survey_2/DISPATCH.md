## 2026-09-05T13:48:47Z

You are an Explorer subagent for Portfolio Risk Budgeting and Adaptive Allocation.
Working directory: d:\Finance\code\stock\.agents\explorer_survey_2
Original request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (read the latest request under ## 2026-09-05T13:47:02Z).
Project rules: d:\Finance\code\stock\AGENTS.md.

Your Mission:
Investigate the existing codebase regarding R2:
- Portfolio risk budgeting and adaptive optimal asset allocation
- 4-model allocation (Black-Litterman, HERC, Risk Parity, EVT-CVaR) blending
- Information-geometric barycenter blending across the 4 models
- High-order cumulant expansion based super-coherent tail risk (EVaR / Entropic Value-at-Risk) budgeting
- Target files to examine: src/risk/unified_portfolio_allocator.py, src/risk/portfolio_allocator.py, src/analysis/portfolio_optimizer.py, src/risk/risk_manager.py.
- Check current blending methods, covariance shrinkage, risk parity, CVaR/EVaR formulation, Leland buffer bands, and MDD control mechanisms.
- Determine exact current implementations, mathematical formulations used in previous phases, and what changes are needed to achieve Sharpe Ratio >= 12.0, MDD <= -0.18%, Net Expected Return >= 95.0%.
- Write your detailed report to d:\Finance\code\stock\.agents\explorer_survey_2\survey_report.md and complete with handoff.md. Include specific file paths, line numbers, and proposed mathematical formulas.
