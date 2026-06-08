## 2026-06-07T20:51:45Z
You are Explorer 1.
Your working directory is `d:\Finance\code\stock\trading_system\.agents\explorer_m1_1\`.
Your parent is the Project Orchestrator at conversation ID `ac1ee229-ba62-4f98-b896-1b302cec30af`.

Your mission is to perform exploration for Phase 5 / Benchmark Optimization:
1. R1: Risk Parity Weight Optimization in `src/analysis/portfolio_optimizer.py` (needs to be created) or other suitable locations. Understand how portfolios are managed in `src/core/portfolio.py` (or similar) and where to integrate the risk parity solver.
2. R2: VIX-Linked Dynamic Asset Allocation (Risk-Off Switch). Spot the current position sizing code, VIX data handling, and where to intercept/clamp equity exposure to 30% and safety asset exposure to 70% when VIX >= 25.
3. R3: Machine Learning Model Upgrade. Update `src/analysis/macro_predictor.py` from RandomForest to LightGBM or XGBoost, incorporating foreign and institutional net purchase volumes. Locate where these net purchase volumes are fetched/simulated, and how they should be added as features.
4. R4: Dash Dashboard Components. Identify how `src/web/dashboard.py` can be upgraded to include the pie chart (`portfolio-weights-pie`) and gauge/bar chart in the 'Global Macro' tab.

Read d:\Finance\code\stock\trading_system\.agents\orchestrator_benchmark\SCOPE.md and d:\Finance\code\stock\trading_system\ORIGINAL_REQUEST.md for full context.
Do NOT write code or modify files. Produce a detailed analysis report in d:\Finance\code\stock\trading_system\.agents\explorer_m1_1\analysis.md and report back to parent.
