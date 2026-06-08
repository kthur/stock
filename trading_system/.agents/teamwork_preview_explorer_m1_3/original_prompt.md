## 2026-06-07T22:25:20Z
You are Explorer 3. Your working directory is d:\Finance\code\stock\trading_system\.agents\teamwork_preview_explorer_m1_3\.
Your parent is the Project Orchestrator at conversation ID 03461a63-fdbb-4548-bf38-718f18bdb6e4.
Your mission is to perform exploration for Phase 5 / Benchmark Optimization:
1. R1: Risk Parity Weight Optimization. Understand how portfolios are managed and where to integrate the risk parity solver. Look for potential files or libraries (numpy, scipy, cvxpy, etc.) that we can use, and how to implement equal risk contribution (ERC) and sum to 1.0. Check if src/analysis/portfolio_optimizer.py needs to be created or if there's any existing allocator.
2. R2: VIX-Linked Dynamic Asset Allocation (Risk-Off Switch). Spot the current position sizing code, VIX data handling, and where to intercept/clamp equity exposure to 30% and safety asset (cash) exposure to 70% when VIX >= 25.
3. R3: Machine Learning Model Upgrade. Update src/analysis/macro_predictor.py from RandomForest to LightGBM or XGBoost, incorporating foreign and institutional net purchase volumes. Locate where these net purchase volumes are fetched/simulated, and how they should be added as features.
4. R4: Dash Dashboard Components. Identify how src/web/dashboard.py can be upgraded to include the pie chart (portfolio-weights-pie) and gauge/bar chart in the 'Global Macro' tab.

Read d:\Finance\code\stock\trading_system\.agents\orchestrator_benchmark_gen2\PROJECT.md and d:\Finance\code\stock\trading_system\ORIGINAL_REQUEST.md for full context.
Do NOT write code or modify files. Produce a detailed analysis report in d:\Finance\code\stock\trading_system\.agents\teamwork_preview_explorer_m1_3\analysis.md and report back to parent with a handoff report at d:\Finance\code\stock\trading_system\.agents\teamwork_preview_explorer_m1_3\handoff.md.
