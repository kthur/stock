# DISPATCH: Worker 3 — Microstructure & OMS Specialist (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase40_oms

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\explorer_quant_phase40_survey3\handoff.md`
3. `d:\Finance\code\stock\PROJECT.md`

## Exclusive File Ownership
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `tests/test_phase40_oms.py`

## Implementation Tasks
1. In `src/core/fast_lob_engine.py`:
   - Implement `compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_queue_acceleration` (KNK 19-Dark-Energy DAHA model, $w = -7.0$, $k_{\text{elliptic}} = 0.11$, $c_{\text{pcqtgbddddhkmae}} = 5 \times 10^{-7}$) and all 11+ aliases.
   - In `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`, add `version >= 40` and stack frame detection for `"phase40"` setting `cap = 0.9999999999`.
2. In `src/execution/smart_order_router.py`:
   - Add `self.is_phase40 = (self.version >= 40)`.
   - Update `_resolve_max_dark_cap` for $v \ge 40$ to return `0.9999999999`.
   - Update queue preemption, lit maker floor to $1 \times 10^{-12}$ ($0.000000000001$), Anti-Gaming MinQty cap to $99.999999998\%$ ($0.99999999998$).
3. In `src/execution/oms_engine.py`:
   - In both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`, add `if int(version) >= 40:` with preemptive tick shading for $h > 0.0007$: $\Delta P = -\text{direction} \cdot 0.999999999 \cdot \text{spread} \cdot (h - 0.0007)$.
4. Write `tests/test_phase40_oms.py` covering all 8 test scenarios from Explorer 3's blueprint.
5. Execute tests via:
   `$env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_oms.py -v`
   Verify 100% pass rate.
6. Write your completion report in `d:\Finance\code\stock\.agents\worker_quant_phase40_oms\handoff.md` and send a message back to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`).
