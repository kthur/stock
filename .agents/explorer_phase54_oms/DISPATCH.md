# DISPATCH: Microstructure OMS & Benchmark Explorer (Phase 54)

## Working Directory
d:\Finance\code\stock\.agents\explorer_phase54_oms

## Mission
Survey and specify Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Features F244.1, F244.2) and Verification Benchmarking (F245) for Phase 54 Quantitative Alpha Enhancement.

## Reference Documents
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`
- Master Dispatch: `d:\Finance\code\stock\.agents\orchestrator_quant_phase54_1\DISPATCH.md`
- Master Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase54_1\plan.md`
- Previous Phase Implementation: `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `src/execution/almgren_chriss.py`
- Previous Phase Benchmark & Tests: `trading_system/scripts/benchmark_phase53_quant_performance.py`, `tests/test_phase53_oms.py`, `tests/test_phase53_adversarial_oms_benchmark.py`

## Instructions
1. Inspect `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, and `src/execution/almgren_chriss.py` to analyze how Phase 50~53 DAHA L3 hydrodynamics, maker floors, dark caps, and preemptive micro-tick shading are implemented.
2. Formulate the exact mathematical and code specifications for:
   - F244.1: Kerr-Newman-Kiselev 33-dark-energy DAHA L3 Spacetime Hydrodynamics with 33rd dark energy component ($w = -35/3 \approx -11.667, k_{\text{daha}} = 0.25, k_{\text{monster}} = 0.24, \text{daha\_33\_factor} = 3.98, c_{\text{monster}} = 0.0000000000244140625$, repulsive acceleration $-17.5 \cdot c_{\text{monster}} \cdot r^{34}$) in `fast_lob_engine.py`, with 28 method aliases and stack frame inspection for `"phase54"`.
   - F244.2: Lit maker floor contracted to $1 \times 10^{-26}$ with 26-decimal precision in `smart_order_router.py`. Preemptive dark ATS routing allocation cap up to $99.99999999999995\%$ and anti-gaming MinQty up to $99.99999999999995\%$. Preemptive micro-tick shading in `oms_engine.py` (both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`) activating at $h > 0.000015$:
     $$\text{hawkes\_shift} = -\text{direction} \cdot 0.99999999999998 \cdot \text{spread} \cdot (h - 0.000015)$$
3. Inspect `trading_system/scripts/benchmark_phase53_quant_performance.py` and analyze what is needed for `benchmark_phase54_quant_performance.py` (target metrics: Net Return 178.49%, Sharpe 35.78, MDD <= -0.00001%, friction <= 0.000000005859375 bps, slippage <= 0.0000000048828125 bps, Top-Decile Spread 156.32%, Win Rate 100.0%).
4. Detail all required aliases and exact integration locations.
5. Output your findings and precise implementation roadmap in `d:\Finance\code\stock\.agents\explorer_phase54_oms\handoff.md`.
