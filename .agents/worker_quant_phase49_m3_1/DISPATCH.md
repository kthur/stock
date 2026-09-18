## 2026-09-17T12:19:20Z

You are the Microstructure OMS Specialist Worker for Phase 49 Quantitative Enhancement (Milestone M3).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase49_m3_1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Read the authoritative inputs:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-17T12:06:49Z)
2. d:\Finance\code\stock\.agents\orchestrator_quant_phase49_1\DISPATCH.md
3. d:\Finance\code\stock\.agents\explorer_quant_phase49_1\report.md
4. d:\Finance\code\stock\.agents\explorer_quant_phase49_1\handoff.md
5. tests/test_phase48_oms.py (as blueprint for test_phase49_oms.py)

Files you exclusively own and modify:
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase49_oms.py` (new test suite)

Implementation Tasks:
1. Feature F219.1: KNK 28-Dark-Energy DAHA L3 Spacetime Hydrodynamics
   - In `fast_lob_engine.py`:
     - Update/extend `compute_kerr_newman_kiselev_28_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration` (or appropriate method) with parameters:
       - w = -10.0 (-30/3), k_daha = 0.20, k_monster = 0.19, daha_28_factor = 2.92, c_monster = 0.00000000078125.
       - Repulsive acceleration term: `- 15.0 * c * (r ** 29) * daha_28_factor` and metric warping `+ c * (r ** 31) * daha_28_factor`.
     - Expose all 21 method aliases on `FastLOBEngine` as detailed in `report.md`.
     - In `DeepHawkesArrivalProcess` / dark routing calculation: inspect stack frames for `"phase49"` or check version >= 49, and cap dark routing up to `0.99999999999998` (99.999999999998%).
2. Feature F219.2: SOR Lit Maker Floor & Dark ATS Anti-Gaming
   - In `smart_order_router.py`:
     - Define `self.is_phase49 = (self.version >= 49)`.
     - Contract lit maker floor to $1 \times 10^{-21}$ via `0.70 * (1.0 - 0.999999999999999999986 * gamma_toxic)` under `is_phase49`. Use `round(..., 23)` to preserve precision.
     - Dark ATS allocation cap scaled to `0.99999999999998` and anti-gaming MinQty scaled to `0.99999999999998` under severe toxic queue imbalance. Use `round(..., 21)`.
3. Preemptive Micro-Tick Shading in OMS:
   - In `oms_engine.py` (both in `ExecutionOMSEngine` around line 1513 and in `AlmgrenChrissScheduler` around line 2456):
     - For `version >= 49` (or `is_phase49`), activate preemptive tick shading at $h > 0.00006$:
       $$\text{hawkes\_shift} = -\text{direction} \cdot 0.999999999999 \cdot \text{spread} \cdot (h - 0.00006)$$
4. Test Suite `tests/test_phase49_oms.py`:
   - Build comprehensive unit test suite covering:
     - KNK 28-dark-energy DAHA acceleration and all 21 method aliases.
     - Lit maker floor reaching down to $10^{-21}$ without underflow to 0.
     - Dark ATS cap and MinQty reaching $0.99999999999998$.
     - Preemptive micro-tick shading activation at $h > 0.00006$ in both ExecutionOMSEngine and AlmgrenChrissScheduler.
   - Run verification using `.venv\Scripts\pytest.exe tests/test_phase49_oms.py` and regression test `.venv\Scripts\pytest.exe tests/test_phase48_oms.py`.

Deliverables:
- Implement code and tests.
- Run tests and ensure 100% PASS with zero errors.
- Write a complete `handoff.md` and update `progress.md`.
- Send completion message to parent when done.
