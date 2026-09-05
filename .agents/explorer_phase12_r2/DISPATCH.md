## 2026-09-05T09:12:00Z

Task Objective:
Investigate the codebase for Requirement 2 (R2):
1. 4-Model allocation (Black-Litterman, HERC, Risk Parity, EVT-CVaR) with Fisher-Rao infinite-dimensional functional information geometry manifold barycenter blending & higher-order Fréchet extreme value tail risk (Ultra-EVaR) ceiling budget to achieve annualized Sharpe 10.08 (+0.73) and system MDD -0.45% (+0.15%p compression).
2. Deep Hawkes L3 arrival intensity process and Level-3 orderbook queue depth acceleration preemptive pegging, Darkpool/ATS liquidity pool up to 96% preemptive routing (0.005 maker floor, 95% anti-gaming MinQty, -0.60 * spread * (h - 0.25) preemptive tick shading) to minimize slippage to 0.2 bps (-0.1 bps), total friction cost to 1.4 bps (-0.6 bps), and turnover to 7.6% (-1.6%p).

Files to investigate:
- src/risk/unified_portfolio_allocator.py
- src/risk/portfolio_allocator.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- src/core/fast_lob_engine.py
