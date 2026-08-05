# DISPATCH for Explorer R2 — Risk Management & Portfolio Optimization

Target Scope: R2. Risk Management & Portfolio Optimization
1. Verify GICS sector-based stress scenarios and crisis level thresholds in `generate_report.py` and `src/risk/risk_manager.py`.
2. Validate real-time order execution tracking in `trade_logs.db` and tracking error monitoring in OMS engine.

Original Request File: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`
Master Project File: `d:\Finance\code\stock\.agents\orchestrator_eval_opt\PROJECT.md`
Working Directory: `d:\Finance\code\stock\.agents\explorer_r2_risk_oms`

Your Role: `teamwork_preview_explorer`
Tasks:
- Read `ORIGINAL_REQUEST.md` and `PROJECT.md`.
- Thoroughly inspect relevant code in `generate_report.py`, `src/risk/risk_manager.py`, `src/execution/` (OMS engine, execution tracker, trade_logs.db database manager), and related test files in `tests/`.
- Verify how GICS sector stress scenarios are calculated, mapped, and presented in reports. Check crisis level thresholds (VIX, USDKRW, Drawdown) and risk manager gating.
- Inspect real-time order execution tracking, schema/operations on `trade_logs.db`, and tracking error calculations in the OMS engine.
- Formulate concrete, actionable recommendations and a step-by-step fix/improvement strategy.
- Produce `handoff.md` in `d:\Finance\code\stock\.agents\explorer_r2_risk_oms` detailing findings, logic chain, evidence, caveats, and recommendations.

## 2026-08-05T12:58:30Z
<USER_REQUEST>
You are teamwork_preview_explorer for R2 Risk Management & Portfolio Optimization.

Working directory: d:\Finance\code\stock\.agents\explorer_r2_risk_oms
Dispatch file: d:\Finance\code\stock\.agents\explorer_r2_risk_oms\DISPATCH.md
Original Request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Master Project file: d:\Finance\code\stock\.agents\orchestrator_eval_opt\PROJECT.md

Please perform the following investigation:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and your DISPATCH.md.
2. Investigate codebase files: generate_report.py, src/risk/risk_manager.py, src/execution/ (OMS engine, tracking error, trade_logs.db manager), and tests in tests/.
3. Focus on:
   - GICS sector-based stress scenarios and crisis level thresholds in generate_report.py and risk_manager.py.
   - Real-time order execution tracking in trade_logs.db and tracking error monitoring in OMS engine.
4. Update progress.md in your working directory as you work.
5. Write your comprehensive analysis, evidence chain, and concrete recommendations in handoff.md in your working directory (d:\Finance\code\stock\.agents\explorer_r2_risk_oms\handoff.md).
6. Send a message to the orchestrator with a summary of your findings and the path to handoff.md.
</USER_REQUEST>
