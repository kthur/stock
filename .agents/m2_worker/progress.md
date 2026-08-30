# Progress Tracker - Milestone 2: Portfolio Optimization & OMS Hardening

Last visited: 2026-08-30T07:40:00+09:00

## Tasks
- [x] Read DISPATCH.md, BRIEFING.md setup
- [ ] Read ORIGINAL_REQUEST.md, PROJECT.md, Explorer 1 analysis.md, and Explorer 1 handoff.md
- [ ] Inspect existing implementation in `portfolio_optimizer.py`, `portfolio_allocator.py`, `oms_engine.py`, `order_manager.py`
- [ ] Inspect test suites and baseline test status
- [ ] Task 1: Refactor `apply_portfolio_constraints` parameter validation
- [ ] Task 2: Implement adaptive SLSQP `maxiter` and Cornish-Fisher QP fallback in `optimize_with_evt_cvar_constraint`
- [ ] Task 3: Implement Micro-Cap ADV Floor Capping in `oms_engine.py` / `order_manager.py`
- [ ] Task 4: Implement Dynamic Trailing Stop ATR Scaling in `oms_engine.py` / `order_manager.py`
- [ ] Add/update unit and integration tests to verify all 4 tasks
- [ ] Run full 10-suite pytest verification
- [ ] Write handoff.md and report to parent
