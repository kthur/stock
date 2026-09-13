# DISPATCH: Worker 3 (Microstructure OMS Specialist)

## Identity
- Role: Microstructure OMS Specialist
- Archetype: teamwork_preview_worker
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase39_oms`
- Original request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-13T20:29:00Z`)
- Survey blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3\handoff.md`

## Exclusive File Ownership
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase39_oms.py`
DO NOT touch any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Read the blueprint in `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3\handoff.md`.
2. In `trading_system/src/core/fast_lob_engine.py`:
   - Implement `compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_queue_acceleration` under F177.2 with $w_{\text{pcqtgbddddhkma}} = -20/3$ and $k_{\text{askey}} = 0.10$, plus all required aliases.
   - Update `DeepHawkesArrivalProcess.compute_preemptive_dark_routing` for `version >= 39` and `"phase39" in cname` with `cap = 0.9999999998`.
3. In `trading_system/src/execution/smart_order_router.py`:
   - Update version flags for `is_phase39 = (self.version >= 39)`.
   - Update `_resolve_max_dark_cap` for `v_eff >= 39` to return `0.9999999998`.
   - Update preemption routing: `eff_dark_ratio = float(np.clip(eff_dark_ratio + 0.88 * max(0.0, qi_aligned) + 0.78 * math.tanh(max(0.0, a_aligned)), self.dark_probe_ratio, 0.9999999998))`.
   - Update maker floor contraction under toxicity to `0.000000000005` ($5 \times 10^{-12}$).
   - Update dynamic anti-gaming MinQty cap to `0.99999999995` ($99.999999995\%$).
4. In `trading_system/src/execution/oms_engine.py`:
   - In `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
     Under `int(version) >= 39`, apply micro-tick shading when $h > 0.0008$:
     `hawkes_shift = -direction * 0.999999998 * spr * (h_val - 0.0008)`.
5. Create `tests/test_phase39_oms.py` containing the 7 test cases specified in the blueprint.
6. Run the tests using `.venv\Scripts\pytest tests/test_phase39_oms.py tests/test_phase38_oms.py -v` to ensure 100% pass and no regression.
7. Write your completion report to `d:\Finance\code\stock\.agents\worker_quant_phase39_oms\handoff.md`.

## 2026-09-13T20:37:12Z
Received prompt from orchestrator to implement F177.2 Microstructure OMS Specialist features and author 7 tests in `tests/test_phase39_oms.py`.
