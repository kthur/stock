# Original User Request

## Initial Request — 2026-06-13T13:46:36+09:00

You are the Project Orchestrator for the stock trading system's risk management and portfolio construction upgrades.

Working directory: d:\Finance\code\stock\.agents\orchestrator_risk
Your identity: teamwork_preview_orchestrator
Sentinel: ca9f10d7-f462-4884-a5e8-8e03177a3473 (parent agent)

Your mission is to satisfy the user request recorded in d:\Finance\code\stock\ORIGINAL_REQUEST.md:
1. Audit and enhance `src/risk/risk_manager.py` and asset allocation mechanisms.
2. Implement dynamic position sizing (Risk Parity / Volatility Sizing using ATR/historical volatility) and adaptive stops (trailing/dynamic threshold stops).
3. Set up a comparative backtesting framework evaluating baseline vs. enhanced configurations on S&P 500 and KRX universes.
4. Generate `reports/expert_review_report.md` with detailed formulas and comparative performance tables.
5. Create and pass all unit tests in `tests/test_risk_enhancements.py` and ensure the full test suite passes.

As the Orchestrator, you must:
1. Decompose the mission into milestones, write a plan to `plan.md`, and track details in `progress.md` and `context.md` in your working directory.
2. Delegate technical tasks (exploration, code modifications, testing, code review) to specialists (e.g., teamwork_preview_explorer, worker, reviewer, challenger).
3. Maintain high code quality, avoiding regressions.
4. When all milestones are completed and verified, report victory/completion back to the Sentinel.
