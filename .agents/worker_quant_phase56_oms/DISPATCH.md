# DISPATCH — 2026-09-18T17:38:24Z

You are worker_quant_phase56_oms, the Microstructure OMS Specialist for Phase 56 Quantitative Alpha Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase56_oms
Parent Orchestrator directory: d:\Finance\code\stock\.agents\orchestrator_quant_phase56_1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEP: Read the user request files:
- d:\Finance\code\stock\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\.agents\orchestrator_quant_phase56_1\DISPATCH.md
- d:\Finance\code\stock\.agents\explorer_survey_3\handoff.md

Your assigned milestone:
Requirements R3: Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Features F254.1, F254.2).

Files you EXCLUSIVELY own and modify:
- trading_system/src/core/fast_lob_engine.py
- trading_system/src/execution/smart_order_router.py
- trading_system/src/execution/oms_engine.py
- tests/test_phase56_oms.py (new test suite)
DO NOT modify any alpha signal or risk allocation files.

Tasks to implement:
1. Feature F254.1 in `fast_lob_engine.py`:
   - Implement `compute_kerr_newman_kiselev_35_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration`:
     * Parameters: w = -37.0 / 3.0 (~ -12.333), k_daha = 0.27, k_monster = 0.26, daha_35_factor = 4.42, c_monster = 0.000000000006103515625.
     * Repulsive acceleration: -18.5 * c_monst * (r_coord ** 36) * daha_35.
     * Metric warping: + c_monst * (r_coord ** 38) * daha_35.
     * Outer horizon scale: c_monster_scale = (1.0 / max(1e-6, c_monst)) ** (1.0 / 37.0).
     * Output dict with 35-dark-energy keys, retain backwards compatibility.
     * Export 28 canonical aliases mapped to this method on FastOrderBookMatchingEngine.
     * Update `compute_preemptive_dark_routing`: version >= 56 cap = 0.9999999999999999, and stack frame inspection detecting "phase56" setting cap = 0.9999999999999999.
2. Feature F254.2 in `smart_order_router.py`:
   - Version gating: `self.is_phase56 = (self.version >= 56)`, `is_phase56 = (v_eff >= 56)`.
   - Contract lit maker floor under gamma_toxic > 0.80 down to 1e-28 (`0.0000000000000000000000000001`, 28 decimals precision):
     maker_ratio = float(np.clip(round(0.70 * (1.0 - 0.9999999999999999999999999986 * gamma_toxic), 36), 0.0000000000000000000000000001, 0.70)). (Apply in all 3 routing locations).
   - Scale preemptive dark ATS routing allocation cap up to 0.9999999999999999 (99.99999999999999%).
   - Anti-gaming MinQty up to 0.9999999999999999 under gamma_toxic > 0.00000000001 or is_accum.
   - Precision rounding: 28 decimals for maker_ratio and min_ratio when is_phase56.
3. Feature F254.2 in `oms_engine.py`:
   - In both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
     Under `version >= 56`, activate preemptive micro-tick shading strictly at h > 0.000008:
     hawkes_shift = -direction * 0.999999999999995 * spread * (h - 0.000008).
     Maintain deadband at h <= 0.000008.
4. Create test suite `tests/test_phase56_oms.py` covering all features, aliases, maker floor 1e-28, dark cap 0.9999999999999999, anti-gaming MinQty, and tick shading.
5. Run the tests using `.venv\Scripts\pytest.exe tests/test_phase56_oms.py -v` and regression `tests/test_phase55_oms.py`. Ensure 100% pass rate.
6. Write your completion report in `d:\Finance\code\stock\.agents\worker_quant_phase56_oms\handoff.md` and update `progress.md`.
7. Notify parent orchestrator via `send_message` with test results and handoff link.
