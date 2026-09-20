# DISPATCH: Milestone M3 Worker (Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m3

## Exclusive File Ownership
You EXCLUSIVELY own and may modify:
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `src/execution/almgren_chriss.py`
- `tests/test_phase63_oms.py`
DO NOT modify any files outside this exclusive list.

## Authoritative Inputs
- `d:\Finance\code\stock\ORIGINAL_REQUEST.md` (Read this first)
- Explorer 3 Handoff Report: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_micro_3\handoff.md` (Contains exact code, lines, formulas, and blueprint)

## Objectives & Detailed Tasks
1. `src/core/fast_lob_engine.py`:
   - Implement `compute_kerr_newman_kiselev_42_dark_energy_daha_l3_spacetime_hydrodynamic_acceleration` with:
     $w = -44.0/3.0 \approx -14.667$, $k_{\text{daha}} = 0.34$, $k_{\text{monster}} = 0.33$, $\text{daha\_42\_factor} = 6.10$, $c_{\text{monster}} = 4.76837158203125 \times 10^{-14}$.
     Tidal force acceleration: $-22.0 \cdot c_{\text{monster}} \cdot r^{43} \cdot \text{daha\_42}$.
     Metric distortion term: $+ c_{\text{monster}} \cdot r^{45} \cdot \text{daha\_42}$.
     Radius scale: $c_{\text{monster\_scale}} = (1.0 / \max(1e-6, c_{\text{monster}}))^{1/44.0}$.
     Charge acceleration: $+ c_{\text{monster}} \cdot r^{42} \cdot \text{daha\_42}$.
   - Export 28 base aliases and 8 extended aliases on `FastOrderBookMatchingEngine`.
   - In `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`:
     Add stack frame inspection for `"phase63"` with routing cap $0.99999999999999999999$ (20 nines).
2. `src/execution/smart_order_router.py`:
   - Add `self.is_phase63 = (self.version >= 63)` and update `self.is_phase62`.
   - In `_resolve_max_dark_cap`: add `v_eff >= 63` returning $0.99999999999999999999$ (20 nines).
   - In dark preemption scaling: clip up to 20 nines under toxic queue imbalance.
   - In lit maker ratio floor: contract down to $1 \times 10^{-35}$ (with 35-decimal precision) across all 3 code locations.
   - In anti-gaming MinQty: scale up to $0.99999999999999999999$ (20 nines) under severe toxic queue imbalance.
3. `src/execution/oms_engine.py` & `src/execution/almgren_chriss.py`:
   - In `calculate_peg_limit_price` on both classes:
     Add `if int(version) >= 63:` branch activating preemptive micro-tick shading when $h > 0.0000010$:
     `hawkes_shift = -direction * 0.99999999999999999 * spr * (h_val - 0.0000010)`
4. Create `tests/test_phase63_oms.py` (mirrored from `tests/test_phase62_oms.py`).
5. Run build/tests:
   ```powershell
   .venv\Scripts\pytest.exe tests/test_phase63_oms.py tests/test_phase62_oms.py -v
   ```
   Ensure 100% pass rate.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverable
Write a complete, self-contained `handoff.md` in your working directory summarizing:
- Exact changes made
- Test execution output
- Verification results
When complete, send a message back to parent.

## 2026-09-20T13:04:18Z
You are Worker M3 specializing in Track C: Microstructure L3 Spacetime Hydrodynamics & Preemptive OMS (Features F289.1, F289.2).
Working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m3
Exclusive file ownership:
- src/core/fast_lob_engine.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- src/execution/almgren_chriss.py
- tests/test_phase63_oms.py
