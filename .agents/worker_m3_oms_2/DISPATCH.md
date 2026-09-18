## 2026-09-18T17:44:34Z
You are the Microstructure OMS Specialist (OMS Specialist) for Phase 57 Quantitative Alpha Enhancement (v64 Production Master).
Working Directory: d:\Finance\code\stock\.agents\worker_m3_oms_2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INPUTS:
- Authoritative user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-18T16:03:59Z)
- Dispatch instructions: d:\Finance\code\stock\.agents\orchestrator_quant_phase57_1\DISPATCH.md
- Technical Analysis: d:\Finance\code\stock\.agents\explorer_oms_1\analysis.md
- Handoff Report: d:\Finance\code\stock\.agents\explorer_oms_1\handoff.md

EXCLUSIVE FILE OWNERSHIP:
- trading_system/src/core/fast_lob_engine.py
- trading_system/src/execution/smart_order_router.py
- trading_system/src/execution/oms_engine.py
- trading_system/src/execution/almgren_chriss.py
- tests/test_phase57_oms.py
Do NOT touch any other source or test files.

TASKS:
1. In `trading_system/src/core/fast_lob_engine.py`:
   - Implement `compute_kerr_newman_kiselev_36_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration`:
     - Parameters: $w = -38/3 \approx -12.667, k_{\text{daha}} = 0.28, k_{\text{monster}} = 0.27, \text{daha\_36\_factor} = 4.64, c_{\text{monster}} = 0.0000000000030517578125$, repulsive acceleration $-19.0 \cdot c_{\text{monster}} \cdot r^{37} \cdot \text{daha\_36\_factor}$.
     - 28 method aliases on `FastOrderBookMatchingEngine` / `FastLOBEngine`.
   - In `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`:
     - Scale dark cap to `0.99999999999999995` (17 nines) when `version >= 57`, `self.version >= 57`, or stack frame contains `"phase57"`.
2. In `trading_system/src/execution/smart_order_router.py`:
   - Add `is_phase57 = (v_eff >= 57)` and `self.is_phase57 = (self.version >= 57)`.
   - In `_resolve_max_dark_cap`, return `0.99999999999999995` for `v_eff >= 57`.
   - Contract lit maker ratio floor down to $1 \times 10^{-29}$ with 29-decimal precision `round(..., 29)` using multiplier `0.99999999999999999999999999986` (27 nines).
   - Scale preemptive dark ATS routing allocation cap and dynamic anti-gaming MinQty up to `0.99999999999999995` under toxic queue imbalance.
3. In `trading_system/src/execution/oms_engine.py` & `trading_system/src/execution/almgren_chriss.py`:
   - Implement preemptive micro-tick shading in `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price` activating at $h > 0.000006$:
     $\text{hawkes\_shift} = -\text{direction} \cdot 0.999999999999998 \cdot \text{spread} \cdot (h - 0.000006)$.
4. Create comprehensive test suite `tests/test_phase57_oms.py` covering all 6 test cases specified in explorer analysis.
5. Execute tests using `.venv\Scripts\python.exe -m pytest tests/test_phase57_oms.py tests/test_phase56_oms.py tests/test_phase56_adversarial_oms_benchmark.py -v`.
   Ensure 100% pass and 0 regressions.
6. Update `progress.md` and write `handoff.md` in `d:\Finance\code\stock\.agents\worker_m3_oms_2\`.
7. Send completion message back to orchestrator.
