## 2026-07-31T00:30:57Z
You are Explorer M3-1 (Gen 2) working on Milestone 3 (EVT-CVaR Risk Budget Constraints) for the Stock Trading System.
Working Directory: d:\Finance\code\stock\.agents\explorer_m3_1_gen2

Objective: Investigate src/risk/portfolio_allocator.py and src/risk/risk_manager.py to design Extreme Value Theory (EVT) CVaR loss budget constraints using Generalized Pareto Distribution (GPD) fitting.

Tasks:
1. Read src/risk/portfolio_allocator.py, src/risk/risk_manager.py, and PROJECT.md to understand the current portfolio optimization logic.
2. Analyze how to fit tail losses using EVT (Peaks-Over-Threshold / GPD via scipy.stats.genpareto or custom MLE/POT estimator) to compute EVT-VaR and EVT-CVaR at high confidence levels (e.g. 99%, 99.5%).
3. Formulate mathematical loss budget constraints: EVT_CVaR(w) <= max_cvar_limit (e.g. 15% max tail loss). Provide exact mathematical equations and Python implementation snippets using scipy.optimize or cvxpy.
4. Verify edge cases (e.g. insufficient tail samples, Gaussian fallback when tail sample count < threshold, numerical stability).
5. Document all findings, architecture recommendations, and exact code modification specifications in d:\Finance\code\stock\.agents\explorer_m3_1_gen2\handoff.md.

Update your progress.md as you work. When finished, send a completion message with summary to parent.
