# DISPATCH: Explorer 3 (Microstructure OMS & Benchmark Survey - Phase 41)

## Target Scope
Survey hook points for R3 Microstructure OMS and R4 Benchmark in Phase 41:
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `trading_system/scripts/benchmark_phase40_quant_performance.py`
- Reference Phase 40 implementation (F181.2, maker floor, tick shading, darkpool routing, F182) and tests `tests/test_phase40_oms.py`, `tests/test_phase40_benchmark.py`.

## Objectives
1. Investigate how Phase 40 implemented F181.2 (KNK 19-Dark-Energy Elliptic DAHA), maker floor $1 \times 10^{-12}$, preemptive tick shading, darkpool ATS 99.99999999%, anti-gaming 99.999999998%, and F182 benchmark engine.
2. Formulate concrete implementation specification for Phase 41:
   - F185.2: Kerr-Newman-Kiselev 20-Dark-Energy PCQTGBDDDDHKMAEE Elliptic-Trigonometric Macdonald-Koornwinder-Askey-Wilson ($w = -22/3$, $k_{\text{elliptic\_trig}} = 0.12$) DAHA L3 hydrodynamics in `fast_lob_engine.py`.
   - Maker floor $1 \times 10^{-13}$ in `smart_order_router.py`.
   - Preemptive tick shading $-0.9999999995 \cdot \text{spread} \cdot (h - 0.0006)$, darkpool ATS routing 99.999999995%, Anti-Gaming MinQty 99.999999999% in `oms_engine.py`.
   - Slippage <= 0.00004 bps, Trading & Friction Costs <= 0.00004 bps.
   - F186: `trading_system/scripts/benchmark_phase41_quant_performance.py` design, baseline metrics (Phase 40: Net Return 149.09%, Sharpe 27.38, MDD -0.00003%, Friction 0.00005 bps, Slippage 0.00005 bps, Top-Decile 124.12%), and target metrics (Phase 41: Net Return >= 151.15%, Sharpe >= 27.95, MDD <= -0.00002%, Friction <= 0.00004 bps, Slippage <= 0.00004 bps, Top-Decile >= 126.40%).
3. Provide exact code snippets, mathematical formulas, and unit test requirements.
4. Output your analysis report in `d:\Finance\code\stock\.agents\explorer_quant_phase41_survey3\handoff.md`.
