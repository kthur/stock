## 2026-07-30T15:30:58Z
You are Explorer M3-3 (Gen 2) working on Milestone 3 (Test Strategy & Benchmarks) for the Stock Trading System.
Working Directory: d:\Finance\code\stock\.agents\explorer_m3_3_gen2

Objective: Investigate existing risk unit tests in tests/test_portfolio_allocator.py and tests/test_risk_manager.py, and design unit tests & benchmarks for Milestone 3 (EVT-CVaR and Dynamic Band Rebalancing).

Tasks:
1. Read tests/test_portfolio_allocator.py, tests/test_risk_manager.py, and related test files.
2. Formulate test specifications for EVT-CVaR constraint checking:
   - EVT-CVaR tail estimation correctness with synthetic heavy-tailed distributions (Student-t, Pareto).
   - Fallback behavior when tail sample size is small.
   - Convex/non-linear optimization constraint enforcement (CVaR <= max_cvar).
3. Formulate test specifications for Dynamic Band Rebalancing:
   - Zero turnover when weight drifts remain within buffer bands.
   - Trade execution triggered when drift breaches buffer bands.
   - Significant transaction cost reduction vs fixed periodic rebalancing.
4. Document all unit test code templates, test cases, and verification benchmarks in d:\Finance\code\stock\.agents\explorer_m3_3_gen2\handoff.md.

Update your progress.md as you work. When finished, send a completion message with summary to parent.
