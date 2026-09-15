# DISPATCH: Phase 43 Survey 3 (OMS & Benchmark)

## Mission
You are Explorer 3 investigating R3 (Microstructure OMS) and R4 (Quant Benchmark & Verification) for Phase 43.

## Instructions & Tasks
1. Read the authoritative user request in `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-15T06:20:40Z`).
2. Examine:
   - `src/core/fast_lob_engine.py`
   - `src/execution/smart_order_router.py`
   - `src/execution/oms_engine.py`
   - `trading_system/scripts/benchmark_phase42_quant_performance.py`
3. Check how Phase 42 implemented F189.2 (KNK 21-Dark-Energy DAHA), maker floor $1 \times 10^{-14}$, tick shading, darkpool ATS routing, anti-gaming MinQty, and F190 benchmark script.
4. Establish the exact technical specification and code blueprint for Phase 43:
   - F193.2: Kerr-Newman-Kiselev 22-Dark-Energy PCQTGBDDDDHKMAEETU Elliptic-Hypergeometric-Askey-Wilson ($w = -24/3 = -8$, $k_{\text{daha}} = 0.14$) DAHA L3 hydrodynamics in `src/core/fast_lob_engine.py`.
   - Maker floor $1 \times 10^{-15}$ in `src/execution/smart_order_router.py`.
   - Preemptive tick shading $-0.9999999999 \cdot \text{spread} \cdot (h - 0.0004)$, darkpool ATS routing 99.999999999%, Anti-Gaming MinQty 99.9999999998% in `src/execution/oms_engine.py`.
   - Target metrics: Execution slippage <= 0.00002 bps, friction costs <= 0.00002 bps.
   - F194 benchmark script `trading_system/scripts/benchmark_phase43_quant_performance.py` design, baselines, and performance targets (Net Return >= 155.35%, Sharpe >= 29.15, MDD <= -0.00001%, Friction <= 0.00002 bps, Slippage <= 0.00002 bps, Top-Decile Spread >= 131.00%).
   - Report synchronization paths (4 destinations) and documentation update requirements (`AGENTS.md`, `PROJECT.md`).
   - Unit test design for `tests/test_phase43_oms.py` and `tests/test_phase43_benchmark.py`.
5. Write your complete handoff report to:
   `d:\Finance\code\stock\.agents\explorer_quant_phase43_survey3\handoff.md`
6. Send a completion message back to the orchestrator.

## 2026-09-15T06:23:17Z
You are Explorer 3 (OMS & Benchmark Specialist Explorer) for Phase 43 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\explorer_quant_phase43_survey3
Read your dispatch instructions at:
d:\Finance\code\stock\.agents\explorer_quant_phase43_survey3\DISPATCH.md
and authoritative request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

Investigate:
- src/core/fast_lob_engine.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- trading_system/scripts/benchmark_phase42_quant_performance.py
Detail the exact implementation blueprint for Phase 43:
- F193.2: KNK 22-Dark-Energy Elliptic-Hypergeometric-Askey-Wilson (w = -8, k_daha = 0.14) DAHA L3 hydrodynamics
- Maker floor 1e-15 in smart_order_router.py
- Preemptive tick shading -0.9999999999 * spread * (h - 0.0004), darkpool ATS routing 99.999999999%, Anti-Gaming MinQty 99.9999999998% in oms_engine.py
- F194 benchmark script trading_system/scripts/benchmark_phase43_quant_performance.py design, baseline and targets
- Report sync paths (4 files) and docs (AGENTS.md, PROJECT.md)
Design unit tests for tests/test_phase43_oms.py and tests/test_phase43_benchmark.py.
Write your handoff report to:
d:\Finance\code\stock\.agents\explorer_quant_phase43_survey3\handoff.md
Send a completion message back to the orchestrator when finished.
