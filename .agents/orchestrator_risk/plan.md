# Plan - Risk Management and Portfolio Construction Upgrades

We will decompose the upgrades into five milestones:

1. **Exploration & Design (M1)**:
   - Spawn Explorer subagents to audit `trading_system/src/risk/risk_manager.py`, `trading_system/src/strategy/asset_allocation.py`, and `trading_system/src/core/strategy_engine.py`.
   - Identify how position sizing and stop loss/take profit are currently implemented.
   - Design the dynamic position sizing (Risk Parity / Volatility Sizing using ATR/historical volatility) and adaptive stop-loss/take-profit models (e.g. ATR trailing stops).

2. **Implementation (M2)**:
   - Spawn a Worker subagent to modify risk_manager.py and asset_allocation.py.
   - Implement the dynamic sizing and adaptive stops logic.

3. **Backtesting & Reporting (M3)**:
   - Spawn a Worker/Explorer to set up and run comparative backtesting between baseline and enhanced configurations on S&P 500 and KRX universes.
   - Generate `reports/expert_review_report.md` with comparative performance tables.

4. **Verification & Testing (M4)**:
   - Spawn a Reviewer to verify correctness of changes.
   - Spawn a Challenger to run adversarial/stress testing.
   - Implement unit tests in `tests/test_risk_enhancements.py` and run full pytest suite.

5. **Forensic Audit & Handoff (M5)**:
   - Spawn a Forensic Auditor to ensure no cheating / integrity issues.
   - Report results to Sentinel.
