# DISPATCH — Explorer M1-2

## 2026-09-04T13:42:46Z
**Task**: Investigate 4-Model portfolio adaptive allocation and tail risk budgeting for Phase 6 (F43).
**Target Files**:
- `src/risk/unified_portfolio_allocator.py`
- `tests/test_phase5_portfolio_execution.py`
- `tests/test_unified_portfolio_engine.py`
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (see ## 2026-09-04T13:40:12Z)
- `d:\Finance\code\stock\.agents\orchestrator_quant_opt5_gen2\handoff.md`

**Objectives**:
1. Analyze current F37 implementation in `UnifiedPortfolioAllocator`:
   - Higher-order co-moments (`compute_higher_order_co_moments`, co-skewness, co-kurtosis).
   - Dynamic Cornish-Fisher EVT-CVaR tail multiplier, DRP-DR ratio scaling, Shannon entropy target vol scaling.
2. Design Phase 6 mathematical improvements:
   - F43: Regime-adaptive 4-model reliability optimization (Black-Litterman, HERC, Risk Parity, EVT-CVaR) with continuous entropy-based blending weights across the 2D regime matrix.
   - Refined down-side tail risk budgeting and asymmetric downside variance adjustment.
3. Formulate concrete implementation recommendations and test case specifications.
4. Output your structured findings in `.agents/explorer_m1_2/handoff.md`.

