## 2026-08-29T22:40:05Z

You are the Milestone 2 Implementation Worker: Portfolio Optimization & OMS Hardening.
Your working directory is: d:\Finance\code\stock\.agents\m2_worker

Read:
- ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md
- PROJECT.md at: d:\Finance\code\stock\PROJECT.md
- Explorer 1 Analysis at: d:\Finance\code\stock\.agents\explorer_portfolio_oms\analysis.md
- Explorer 1 Handoff at: d:\Finance\code\stock\.agents\explorer_portfolio_oms\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write Ownership:
You have exclusive write ownership of:
- `trading_system/src/analysis/portfolio_optimizer.py` (and `src/analysis/portfolio_optimizer.py`)
- `trading_system/src/risk/portfolio_allocator.py` (and `src/risk/portfolio_allocator.py`)
- `trading_system/src/execution/oms_engine.py` (and `src/execution/oms_engine.py`)
- `trading_system/src/execution/order_manager.py` (and `src/execution/order_manager.py`)
- `tests/test_portfolio_allocator.py`
- `tests/test_portfolio_optimizer_and_oms.py`
- `tests/test_order_manager.py`

Implementation Tasks (per Explorer 1 findings):
1. **`apply_portfolio_constraints` refinement** (`src/analysis/portfolio_optimizer.py`):
   - Refactor the variable validation logic around lines 500–520 to use explicit parameter inspection rather than probing `locals()`, ensuring clean execution.
2. **`optimize_with_evt_cvar_constraint` adaptive iteration limits** (`src/risk/portfolio_allocator.py`):
   - Enhance SLSQP options with adaptive `maxiter` based on universe dimension ($N$ assets): e.g. `maxiter = min(250, max(50, 10 * N))`.
   - Add graceful fallback to Cornish-Fisher quadratic programming if SLSQP fails to converge or times out.
3. **Execution OMS Micro-Cap ADV Floor Capping** (`src/execution/oms_engine.py` / `src/execution/order_manager.py`):
   - Refine ADV capacity calculation (Gate 7.5) to bound the ADV floor:
     `effective_adv_cap = min(max_adv_ratio * adv, max(adv_floor, 0.50 * adv))` for micro-cap symbols where `adv_floor` might otherwise exceed total ADV.
4. **Dynamic Trailing Stop ATR Scaling** (`src/execution/oms_engine.py` / `src/execution/order_manager.py`):
   - In `calculate_trailing_stop_plan`, when historical price series has $< 14$ rows, dynamically scale the default ATR using `volatility_20d` (or annualized vol $/ \sqrt{252}$) if available in metadata, rather than an unscaled constant fallback.

Verification:
- Run all portfolio, risk, and OMS test suites using:
  `.venv\Scripts\pytest tests/test_portfolio_allocator.py tests/test_portfolio_optimizer_and_oms.py tests/test_black_litterman.py tests/test_hrp_optimizer.py tests/test_order_manager.py tests/test_turnover_optimizer.py tests/test_slippage_feedback.py tests/test_risk_manager.py tests/test_unified_portfolio_engine.py tests/test_challenger_portfolio_stress.py -v`
- Ensure 100% test pass rate with 0 failures.
- Write full report to `d:\Finance\code\stock\.agents\m2_worker\handoff.md`.
- Send message to orchestrator upon completion.
