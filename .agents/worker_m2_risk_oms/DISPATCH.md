# DISPATCH for Worker M2 — Risk Management & Portfolio Optimization

Target Scope: Milestone 2: Risk Management & Portfolio Optimization
1. Verify GICS sector-based stress scenarios in `generate_report.py` (5 GICS sectors, 4 macro shock factors, 2 presets, client-side JS simulation engine).
2. Verify 4-tier crisis level thresholds (`NONE`, `WATCH`, `ACTIVE`, `SEVERE`) and risk manager gating in `src/risk/risk_manager.py` (VIX, Drawdown, Volume ratio, Trend breakdown, Macro scores gating cash target ratios, position multipliers 1.0x-0.15x, stop-loss tightening 1.0x-0.40x, buy blocking, panic liquidation after 3 days SEVERE, VIX caps, and 30% sector risk caps).
3. Validate real-time order execution tracking in `trade_logs.db` (`order_plans` and `execution_logs` tables) with basis point slippage tracking (`slippage_bps`), `SlippageFeedbackEngine` dynamic cost calibration, and tracking error monitoring in `ExecutionOMSEngine` / `PortfolioAllocator` (EVT-CVaR tail risk budget & Leland dynamic band rebalancing).
4. Run pytest test suite: `.venv\Scripts\python.exe -m pytest tests/test_risk_manager.py tests/test_risk_enhancements.py tests/test_portfolio_risk.py tests/test_portfolio_allocator.py tests/test_portfolio_optimizer_and_oms.py -v`.
5. Update `progress.md` and write a detailed `handoff.md` in your working directory.

Original Request File: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`
Explorer Handoff File: `d:\Finance\code\stock\.agents\explorer_r2_risk_oms\handoff.md`
Master Project File: `d:\Finance\code\stock\.agents\orchestrator_eval_opt\PROJECT.md`
Working Directory: `d:\Finance\code\stock\.agents\worker_m2_risk_oms`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-08-05T13:07:53Z
You are teamwork_preview_worker for Milestone 2: Risk Management & Portfolio Optimization.

Working directory: d:\Finance\code\stock\.agents\worker_m2_risk_oms
Dispatch file: d:\Finance\code\stock\.agents\worker_m2_risk_oms\DISPATCH.md
Original Request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Explorer Handoff file: d:\Finance\code\stock\.agents\explorer_r2_risk_oms\handoff.md
Master Project file: d:\Finance\code\stock\.agents\orchestrator_eval_opt\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please execute the verification and test suite execution tasks specified in DISPATCH.md:
1. Verify GICS sector-based stress scenarios in `generate_report.py` and `src/risk/risk_manager.py`.
2. Verify 4-tier crisis level thresholds and risk manager gating in `src/risk/risk_manager.py`.
3. Validate real-time order execution tracking in `trade_logs.db` and tracking error monitoring in `ExecutionOMSEngine` and `PortfolioAllocator`.
4. Run unit test suite: `.venv\Scripts\python.exe -m pytest tests/test_risk_manager.py tests/test_risk_enhancements.py tests/test_portfolio_risk.py tests/test_portfolio_allocator.py tests/test_portfolio_optimizer_and_oms.py -v`.
5. Update progress.md and write a detailed handoff.md in your working directory.
6. Send a completion message to the parent orchestrator with test results and handoff path.
