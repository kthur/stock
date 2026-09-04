# DISPATCH — Explorer M1-3

**Task**: Investigate Level-3 orderbook micro-price pegging, continuous Hawkes toxicity, and darkpool liquidity capture for Phase 6 (F44).
**Target Files**:
- `src/execution/smart_order_router.py`
- `src/core/fast_lob_engine.py`
- `src/execution/oms_engine.py`
- `tests/test_phase5_portfolio_execution.py`
- `tests/test_smart_order_router.py`
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (see ## 2026-09-04T13:40:12Z)
- `d:\Finance\code\stock\.agents\orchestrator_quant_opt5_gen2\handoff.md`

**Objectives**:
1. Analyze current F38 implementation:
   - Hawkes toxicity modulation $\Gamma_{\text{toxic}}$ in `SmartOrderRouter`.
   - Depth-adaptive micro-price curvature and peg limit price calculation.
   - Darkpool resting `"MIDPOINT_PEGGED_RESTING"` with MinQty >= 20%.
   - Intraday Gatheral slice count with U-shaped volume smile.
   - Leland buffer bands across 5 markets.
2. Design Phase 6 mathematical improvements:
   - F44: Level-3 micro-price pegging integrating queue position estimates and L3 book imbalance from `FastLOBEngine`.
   - Advanced darkpool liquidity capture with anti-gaming fill probability and adaptive routing across KRX/US venues.
3. Formulate concrete implementation recommendations and test case specifications.
4. Output your structured findings in `.agents/explorer_m1_3/handoff.md`.

## 2026-09-04T13:42:46Z
You are explorer_m1_3.
Your working directory is: d:\Finance\code\stock\.agents\explorer_m1_3\
Read d:\Finance\code\stock\.agents\explorer_m1_3\DISPATCH.md and d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (mandatory).
Read and analyze:
- src/execution/smart_order_router.py
- src/core/fast_lob_engine.py
- src/execution/oms_engine.py
- tests/test_phase5_portfolio_execution.py
- tests/test_smart_order_router.py
- d:\Finance\code\stock\.agents\orchestrator_quant_opt5_gen2\handoff.md

Investigate Phase 6 enhancements for F44 (Level-3 Micro-Price Pegging, Hawkes Toxicity & Darkpool Liquidity Capture).
Provide concrete mathematical models, code modification targets, and test cases.
Write your complete report to: d:\Finance\code\stock\.agents\explorer_m1_3\handoff.md
Send a completion message back to parent.

