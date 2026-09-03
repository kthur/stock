# DISPATCH - Worker M2

## Mission
Implement Milestone 2 Features (Requirement R2):
- Feature 7 & 8: Dynamic Half-Life Convergence Speed ($\theta_i^*$) & Liquidity-Constrained Cash Buffer in `trading_system/src/risk/unified_portfolio_allocator.py` (per `d:\Finance\code\stock\.agents\explorer_m2_1_opt2\plan_m2_1.md`).
- Feature 9: Volatility-Normalized Asymmetric Leland Dynamic Buffer Bands & Boundary Rebalancing in `trading_system/src/risk/unified_portfolio_allocator.py` and `trading_system/src/risk/portfolio_allocator.py` (per `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\plan_m2_2.md`).
- Feature 10 & 11: End-to-End OMS Delta Rebalancing ($\Delta Q = Q_{\text{target}} - Q_{\text{current}}$) and Almgren-Chriss Slicing with `MIDPOINT_PEG` Tranches in `trading_system/src/execution/oms_engine.py` and `trading_system/run_pipeline.py` (per `d:\Finance\code\stock\.agents\explorer_m2_3_opt2\plan_m2_3.md`).

## Exclusive Write Ownership
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `trading_system/src/execution/oms_engine.py`
- `trading_system/run_pipeline.py`
- `tests/test_m2_portfolio_execution.py` (and test additions in `tests/test_order_manager.py`, `tests/test_institutional_portfolio_construction.py`)

## Verification
Run tests via `.venv\Scripts\pytest`:
- `.venv\Scripts\pytest tests/test_institutional_portfolio_construction.py tests/test_unified_portfolio_engine.py tests/test_portfolio_allocator.py -v`
- `.venv\Scripts\pytest tests/test_position_lifecycle_optimization.py tests/test_order_manager.py tests/test_portfolio_optimizer_and_oms.py -v`
- `.venv\Scripts\pytest tests/test_m2_portfolio_execution.py -v`
- Pass rate must be 100% with 0 failures and 0 regressions.


## 2026-09-03T16:12:00Z
You are Worker M2 (Portfolio Allocation & Execution Implementer).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_opt2
Project root / codebase directory is: d:\Finance\code\stock
Authoritative request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically read section ## 2026-09-03T15:32:22Z)
Project rules and architecture: d:\Finance\code\stock\AGENTS.md
Project plan: d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md
Your dispatch instructions: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_opt2\DISPATCH.md

Input technical implementation plans:
1. `d:\Finance\code\stock\.agents\explorer_m2_1_opt2\plan_m2_1.md` (Dynamic Half-Life Convergence Speed theta* and Cash Buffer Routing in UnifiedPortfolioAllocator)
2. `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\plan_m2_2.md` (Volatility-Normalized Asymmetric Leland Dynamic Buffer Bands & Boundary Rebalancing)
3. `d:\Finance\code\stock\.agents\explorer_m2_3_opt2\plan_m2_3.md` (OMS Delta Rebalancing Delta Q and Almgren-Chriss Slicing with Midpoint Peg Tranches)
