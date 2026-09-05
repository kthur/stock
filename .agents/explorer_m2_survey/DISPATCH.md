# DISPATCH: Survey Explorer M2 (Portfolio Allocation & Execution Architecture)

## 2026-09-05T02:17:15Z

## Working Directory
`d:\Finance\code\stock\.agents\explorer_m2_survey`

## Mission
Investigate R2 codebase for Phase 8 Sovereign Quantitative Enhancements (v15):
1. Investigate `src/risk/unified_portfolio_allocator.py`, `src/execution/smart_order_router.py`, `src/core/fast_lob_engine.py`, and `src/execution/oms_engine.py`.
2. Analyze Phase 7 implementation:
   - F49: Archimedean Copula tail dependence (Clayton/Gumbel) 4-model dynamic reliability tilting and Euler CCVaR risk budgeting.
   - F50: Level-3 queue imbalance micro-price pegging, Hawkes toxicity-shaded pricing, SmartOrderRouter ATS lit preemption up to 75%.
3. Formulate detailed technical design and integration plan for Phase 8:
   - R2-1: Multivariate Regular Vine (R-Vine) tree copula modeling higher-order downside contagion cascade across the 4 allocation models (Black-Litterman, HERC, Risk Parity, EVT-CVaR) and Information Entropy Parity dynamic reliability tilting.
   - R2-2: Level-3 queue imbalance 2nd-order time derivative acceleration ($d^2\text{QI}/dt^2$) and cross-asset flow toxicity pegging with darkpool/ATS liquidity capture.
4. Identify all affected methods, line numbers, variable names, and unit tests in `tests/` (e.g., `test_unified_portfolio_allocator.py`, `test_smart_order_router.py`, `test_fast_lob_engine.py`, `test_oms_engine.py`).
5. Write handoff report with exact code snippets, proposed interfaces, and test strategies to `d:\Finance\code\stock\.agents\explorer_m2_survey\handoff.md`.

