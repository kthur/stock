# Progress — Survey Explorer 2 (Requirement R2)

Last visited: 2026-09-04T05:54:00+09:00

## Status
- [x] Initialized DISPATCH.md, BRIEFING.md, progress.md
- [x] Investigate `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`
  - Deep-dived 4-model allocation (Black-Litterman, HERC, Risk Parity, CVaR) and current `REGIME_OPTIMIZER_BLENDS` lookup
  - Analyzed Gatheral 3/2-power market impact penalty closed-form convergence velocity ($\theta^*$)
  - Analyzed volatility-normalized asymmetric Leland dynamic no-trade buffer bands
  - Identified critical divergence: `unified_portfolio_allocator.py` uses sample Rockafellar-Uryasev linear CVaR ($T=60$, only 3 tail exceedances) while `portfolio_allocator.py` has EVT-GPD POT and Clayton copula tail covariance
  - Formulated continuous Markov / 2D regime transition probability blending with EMA smoothing
- [x] Investigate `src/execution/oms_engine.py`, `src/execution/smart_order_router.py`, `src/execution/almgren_chriss.py`, `src/core/hft_engine.py`
  - Analyzed 8-gate execution OMS order planning and Almgren-Chriss hyperbolic trajectory slicing
  - Analyzed SmartOrderRouter 3-tier venue routing (Dark ATS Midpoint -> Primary Peg Maker -> Lit Sweeper)
  - Identified gaps: OMS does not attach 3-tier SOR routing payload; Strategy #30 dark pool signals not used to adjust dark probing ratio; OBI not used in peg limit pricing
  - Formulated dynamic dark pool probing ratio, OBI-driven midpoint peg pricing, and dark-adjusted Gatheral impact
- [x] Map existing tests covering portfolio allocation and OMS execution
  - Verified 100% pass on `test_m2_portfolio_execution.py` (12 tests), `test_portfolio_allocator.py` (13 tests), `test_portfolio_optimizer_and_oms.py` (11 tests), `test_smart_router.py`, `test_adaptive_router.py`
- [x] Formulate quantitative enhancements, mathematical formulas, and class/method specs for Milestone 2
- [ ] Write handoff.md and send final report to caller
