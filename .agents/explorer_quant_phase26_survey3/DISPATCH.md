# DISPATCH: Survey 3 — Microstructure OMS & Quant Benchmark Exploration (Phase 26)

## Working Directory
`d:\Finance\code\stock\.agents\explorer_quant_phase26_survey3`

## Role
Microstructure OMS & Quant Verification Specialist Explorer

## Context & Objectives
You are Explorer 3 surveying the codebases for Phase 26 R3 Microstructure OMS & R4 Quant Benchmark Enhancement.
Authoritative user request is in:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T13:18:53Z`)
Also read:
`d:\Finance\code\stock\PROJECT.md`
`d:\Finance\code\stock\.agents\orchestrator_quant_phase26_1\plan.md`

## Your Mission
1. Investigate existing hook points in:
   - `src/core/fast_lob_engine.py`
   - `src/execution/smart_order_router.py`
   - `src/execution/oms_engine.py`
   - `trading_system/scripts/benchmark_phase25_quant_performance.py`
2. Detail the exact design and implementation blueprint for:
   - F125.2: Kerr-Newman-Kiselev Chameleon 5-dark-energy ($w_{\text{chameleon}} = -7/3$) spacetime L3 orderbook hydrodynamics model in `fast_lob_engine.py`.
   - Maker floor $0.0000001$ in `smart_order_router.py`.
   - Preemptive tick shading $-0.99995 \cdot \text{spread} \cdot (h - 0.020)$, Darkpool ATS 99.9995%, Anti-Gaming MinQty 99.9999% in `oms_engine.py`.
   - Target metrics: Slippage $\le 0.0005$ bps, trading friction costs $\le 0.010$ bps.
   - F126: `trading_system/scripts/benchmark_phase26_quant_performance.py` script architecture, 5-market benchmarking, 3 comparison tables, and report synchronization.
3. Provide concrete line numbers, exact equations, class/method signatures, and unit test specifications for `tests/test_phase26_oms.py` and `tests/test_phase26_benchmark.py`.
4. Output your complete analysis to:
   `d:\Finance\code\stock\.agents\explorer_quant_phase26_survey3\handoff.md`
   And send a completion message to the Orchestrator (`23291457-ea26-4c49-8433-2bc79a9280cf`).
