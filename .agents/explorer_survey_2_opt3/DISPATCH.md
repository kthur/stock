## 2026-09-03T20:48:03Z

Investigate portfolio allocation 4-model blending and execution OMS optimization:
1. `src/risk/unified_portfolio_allocator.py` & `src/risk/portfolio_allocator.py`:
   - Current implementation of Black-Litterman, HERC, Risk Parity, and EVT-CVaR 4-model allocation and blending.
   - How regime-dependent confidence weights are currently assigned and blended across regimes.
   - How Gatheral 3/2-power market impact penalty, tail risk budgeting, and Leland no-trade buffer bands operate.
   - Exact enhancements needed to dynamically adjust 4-model confidence weights by regime to maximize risk-adjusted return and tail risk protection.
2. `src/execution/oms_engine.py`, `src/execution/smart_order_router.py`, `src/execution/almgren_chriss.py`:
   - Current smart order routing (SOR), darkpool / block trade handling, HFT micro-spread capture, and order tranche slicing.
   - Exact enhancements to reduce execution slippage and friction costs using darkpool/HFT liquidity pools.
3. Identify existing tests covering portfolio allocation and OMS execution.
4. Outline exact mathematical formulas, class/method modifications, and implementation design for Milestone 2.
