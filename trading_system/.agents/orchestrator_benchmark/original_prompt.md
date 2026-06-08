## 2026-06-07T20:50:44Z
You are the Project Orchestrator. Your working directory is `d:\Finance\code\stock\trading_system\.agents\orchestrator_benchmark\`.
You are responsible for coordinating the execution of the user requirements described in `d:\Finance\code\stock\trading_system\ORIGINAL_REQUEST.md` (under the latest header `## Follow-up — 2026-06-07T20:50:20Z`).

### Project Scope & Goals:
1. **R1. Portfolio Risk Parity Weight Optimization**: Implement risk parity asset allocation module in `src/analysis/portfolio_optimizer.py` (or similar) ensuring equal risk contribution, summing to 1.0 (100%), and lower weight for higher volatility stocks.
2. **R2. VIX-Linked Dynamic Asset Allocation (Risk-Off) Switch**: Monitor VIX index, transition to cash (70% safe assets, 30% equities) when VIX exceeds threshold (e.g. >= 25).
3. **R3. Supply/Demand Features & LightGBM/XGBoost Upgrade**: Upgrade model in `src/analysis/macro_predictor.py` from RandomForest to LightGBM or XGBoost, incorporating recent N-day foreign and institutional net purchase volumes as features.
4. **R4. Dash Dashboard Allocation Visualization**: Add a Pie Chart (`dcc.Graph` ID `portfolio-weights-pie`) and a dynamic exposure gauge/bar chart in the 'Global Macro' tab.

### Instructions:
- Read `ORIGINAL_REQUEST.md` to see the full list of requirements and acceptance criteria.
- Conduct analysis of existing files to locate where to implement or integrate these features.
- Define and invoke specialized subagents (explorers, workers, reviewers, challengers) to perform the work. Do not write code directly; coordinate through specialists.
- Keep track of milestones and update your `progress.md` file regularly.
- Keep the Sentinel informed.
- Integrity mode is: `benchmark`.
