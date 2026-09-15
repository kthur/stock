# DISPATCH: Milestone 3 — Microstructure OMS Specialist

## Working Directory
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_oms`

## Authoritative User Request
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-15T21:55:02Z`)

## Architectural Reference
`d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md`

## Files Exclusively Owned
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase45_oms.py`

## Mandate & Detailed Requirements (F201.2)
1. **`fast_lob_engine.py`**:
   - Implement `compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_hypergeometric_universal_virasoro_whittaker_queue_acceleration` (KNK 24-Dark-Energy PCQTGBDDDDHKMAEETUVW DAHA L3 hydrodynamics):
     - Parameters: $w = -26/3$, $k_{\text{daha}} = 0.16$, `daha_24_factor = 2.21`.
     - Radial metric discriminant exponent 27, repulsive tidal acceleration term $-13.0 \cdot c \cdot r^{25} \cdot \text{daha\_24\_factor}$, and complete alias set.
   - `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`: expand cap to `0.999999999998` for `v_eff >= 45` and `phase45` test frame.

2. **`smart_order_router.py`**:
   - In `_resolve_max_dark_cap`: return `0.999999999998` for `v_eff >= 45`.
   - In `route_order`: when `is_phase45` and `(qi_aligned > 0.00000002 or a_aligned > 0.000000002)`, scale `eff_dark_ratio` up to `0.999999999998`.
   - Lit maker floor contraction: when `is_phase45 and gamma_toxic > 0.80`, contract maker floor to `1e-17` (`0.00000000000000001`) via formula:
     `maker_ratio = float(np.clip(round(0.70 * (1.0 - 0.999999999999999986 * gamma_toxic), 20), 0.00000000000000001, 0.70))`.
   - Dynamic Anti-Gaming MinQty: when `is_phase45 and (gamma_toxic > 0.00000005 or is_accum)`, scale up to `99.99999999995%` (`0.9999999999995`).
   - Rounding precision: 19 decimals for maker_ratio, 18 decimals for min_ratio when `is_phase45`.

3. **`oms_engine.py`**:
   - In both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
     - Add `version >= 45` branching with threshold `h_val > 0.0002` and shift:
       `hawkes_shift = -direction * 0.99999999998 * spr * (h_val - 0.0002)`.

4. **`tests/test_phase45_oms.py`**:
   - Implement 8 tests as specified in `handoff.md` Section 2.5.
   - Run: `python -m pytest tests/test_phase45_oms.py -v` and `python -m pytest tests/test_phase44_oms.py -q`.
   - Ensure 100% pass rate.

## Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-09-15T22:02:30Z
You are Worker 3 (Microstructure OMS Specialist) for Phase 45 Full Team Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_oms
Your task assignment is in: d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_oms\DISPATCH.md
Architectural reference: d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md
Mandatory user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-15T21:55:02Z)
Files you exclusively own:
- trading_system/src/core/fast_lob_engine.py
- trading_system/src/execution/smart_order_router.py
- trading_system/src/execution/oms_engine.py
- tests/test_phase45_oms.py
Implement F201.2 (KNK 24-Dark-Energy DAHA L3 hydrodynamics, 99.9999999998% ATS cap, 1e-17 maker floor, 99.99999999995% anti-gaming, preemptive tick shading -0.99999999998 * spr * (h - 0.0002)) and write tests/test_phase45_oms.py as specified in DISPATCH.md.
Execute unit tests using python -m pytest tests/test_phase45_oms.py -v and ensure 100% pass rate.
Verify backward compatibility with tests/test_phase44_oms.py.

