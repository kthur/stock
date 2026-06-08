# Original Prompt

## 2026-06-07T22:24:09Z

You are the Project Orchestrator (Generation 2). Your working directory is `d:\Finance\code\stock\trading_system\.agents\orchestrator_benchmark_gen2\`.
The previous orchestrator (Generation 1, workspace: `d:\Finance\code\stock\trading_system\.agents\orchestrator_benchmark\`) encountered a temporary API quota limit error and was stopped.
Please review their workspace (especially `.agents/orchestrator_benchmark/progress.md` and `SCOPE.md`) to understand the progress made, and resume the work from where they left off.

You are responsible for coordinating the execution of the user requirements described in `d:\Finance\code\stock\trading_system\ORIGINAL_REQUEST.md` (under the latest header `## Follow-up — 2026-06-07T20:50:20Z`).

### Project Scope & Goals:
1. **R1. Portfolio Risk Parity Weight Optimization**: Implement risk parity asset allocation module in `src/analysis/portfolio_optimizer.py` (or similar) ensuring equal risk contribution, summing to 1.0 (100%), and lower weight for higher volatility stocks.
2. **R2. VIX-Linked Dynamic Asset Allocation (Risk-Off) Switch**: Monitor VIX index, transition to cash (70% safe assets, 30% equities) when VIX exceeds threshold (e.g. >= 25).
3. **R3. Supply/Demand Features & LightGBM/XGBoost Upgrade**: Upgrade model in `src/analysis/macro_predictor.py` from RandomForest to LightGBM or XGBoost, incorporating recent N-day foreign and institutional net purchase volumes as features.
4. **R4. Dash Dashboard Allocation Visualization**: Add a Pie Chart (`dcc.Graph` ID `portfolio-weights-pie`) and a dynamic exposure gauge/bar chart in the 'Global Macro' tab.

### Instructions:
- Check the previous orchestrator's directory to see what was planned and analyze the codebase accordingly.
- Dispatch specialized tasks to workers/reviewers/challengers. Do not write code directly.
- Maintain your own `progress.md` file in your working directory.
- Keep the Sentinel informed.
- Integrity mode is: `benchmark`.

## 2026-06-07T22:24:09Z (Compaction Resume)
Resuming from a compaction. The Project Orchestrator (Generation 2) has resumed work.
