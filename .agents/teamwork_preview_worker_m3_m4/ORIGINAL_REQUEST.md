## 2026-06-13T04:57:38Z
You are teamwork_preview_worker, a software engineer and quantitative researcher subagent.
Working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_m4
Your mission is to execute Milestones 3 and 4: backtesting, report generation, and unit testing.

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please perform the following steps:

1. Move the unit tests:
   - Extract the test class `TestRiskManagerUpgrades` from `trading_system/tests/test_risk_manager.py` (lines 224 to 322) and place it in a new unit test file at `trading_system/tests/test_risk_enhancements.py`.
   - Ensure `trading_system/tests/test_risk_enhancements.py` is fully compilable, runs, and passes (it should import the necessary modules like `unittest`, `sys`, `Path`, `RiskManager`, `CrisisLevel`, `RiskLevel`).
   - Run `pytest tests/test_risk_enhancements.py` and `pytest tests/test_risk_manager.py` under the virtual environment to ensure all tests pass.

2. Create and run the comparative backtesting framework:
   - Create a python script `trading_system/scripts/compare_backtests.py` that runs a comparative backtest on representative stock universes (S&P 500: SPY, AAPL, MSFT, GOOGL, AMZN; KRX: 005930.KS, 000660.KS, 035420.KS).
   - Use a simple strategy like a moving average crossover (EMA10 vs EMA30) to generate buy/sell signals.
   - Run both configurations:
     - Baseline: `volatility_sizing=False`, `stop_loss_pct=0.05`, `take_profit_pct=0.15`, `atr_trailing_stop_mult=0.0`
     - Enhanced: `volatility_sizing=True`, `stop_loss_pct=0.05`, `take_profit_pct=0.15`, `atr_trailing_stop_mult=2.0` (which enables dynamic ATR-based trailing stops in the engine).
   - Compute key quantitative metrics for each run: Cumulative Return (%), Annualized Return (%), Sharpe Ratio, Max Drawdown (%), Win Rate (%), and Profit Factor.
   - Run the script and capture the comparison results.

3. Generate the Expert Markdown Report:
   - Save a markdown report named `expert_review_report.md` in `d:\Finance\code\stock\reports/` folder.
   - The report must contain:
     - Detailed audit description of existing risk rules.
     - Complete mathematical formulas for the new models:
       - Volatility-Adjusted Kelly Sizing
       - Regime-Adaptive Risk-Unit Sizing (Dynamic Fixed Risk)
       - Regime-Adaptive and Drawdown-Tightened ATR Trailing Stops
     - Side-by-side comparative tables showing baseline vs enhanced metrics for the S&P 500 and KRX stocks.
     - Quantitative analysis demonstrating the risk-adjusted improvements (e.g. reduction in MDD, improvement in Sharpe ratio).

4. Verify the full test suite:
   - Run `pytest` inside `trading_system` and ensure all tests pass.

After completing all tasks, write a handoff report at `d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_m4\handoff.md` and notify the parent orchestrator (conv ID: 7635347b-53a9-4ba1-9cb3-cafe65efe2dc).
