# DISPATCH: Worker 3 (Microstructure OMS Specialist - Phase 41)

## Assigned Files (Exclusive Write Ownership)
- `trading_system/src/core/fast_lob_engine.py` (and `src/core/fast_lob_engine.py` if separate)
- `trading_system/src/execution/smart_order_router.py` (and `src/execution/smart_order_router.py` if separate)
- `trading_system/src/execution/oms_engine.py` (and `src/execution/oms_engine.py` if separate)
- `tests/test_phase41_oms.py`

## Authoritative Inputs
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-14T10:14:28Z`)
2. Blueprint and exact code specifications in `d:\Finance\code\stock\.agents\explorer_quant_phase41_survey3\handoff.md`

## Implementation Scope
1. **F185.2: KNK 20-Dark-Energy Elliptic-Trigonometric DAHA L3 Hydrodynamics in `fast_lob_engine.py`**:
   - Implement `compute_kerr_newman_kiselev_phantom_chameleon_quintom_tachyon_ghost_brane_dilaton_dirac_dunkl_hecke_cherednik_kostka_macdonald_askey_wilson_elliptic_trigonometric_queue_acceleration` with $w_{\text{pcqtgbddddhkmaee}} = -22/3$, $k_{\text{elliptic\_trig}} = 0.12$, $c = 2 \times 10^{-7}$, composite DAHA factor 1.63.
   - Register all 12 class aliases.
   - Update `DeepHawkesArrivalProcess.compute_preemptive_dark_routing` to cap at 0.99999999995 (99.999999995%) under version >= 41 and stack frame inspection.
2. **SmartOrderRouter Updates in `smart_order_router.py`**:
   - Version flag `self.is_phase41 = (self.version >= 41)`.
   - Max dark cap in `_resolve_max_dark_cap`: return 0.99999999995 for `v_eff >= 41`.
   - Preemptive queue imbalance dark ratio cap up to 0.99999999995.
   - Maker floor contraction: contract to $1 \times 10^{-13}$ under extreme toxicity ($\gamma_{\text{toxic}} > 0.80$) in both directional toxicity and Hawkes branches.
   - Anti-Gaming MinQty: cap at 0.99999999999 (99.999999999%).
   - Precision rounding: round maker_ratio to 16 decimals, min_ratio to 15 decimals for Phase 41.
3. **Preemptive Tick Shading in `oms_engine.py`**:
   - Implement $-0.9999999995 \cdot \text{spread} \cdot (h - 0.0006)$ at $h > 0.0006$ in BOTH:
     - `ExecutionOMSEngine.calculate_peg_limit_price` (line ~1505)
     - `AlmgrenChrissScheduler.calculate_peg_limit_price` (line ~2368)
4. **Unit Tests**:
   - Implement `tests/test_phase41_oms.py` covering all 8 unit tests specified in Explorer 3's blueprint.
   - Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase41_oms.py -v` and ensure 100% pass.
   - Verify that Phase 40 tests `tests/test_phase40_oms.py` continue to pass 100% without regression.

## Output


## 2026-09-14T10:25:50Z

Worker 3 (Microstructure OMS Specialist) for Phase 41 Quant Enhancement.
See details in ORIGINAL_REQUEST.md, DISPATCH.md, and explorer_quant_phase41_survey3/handoff.md.

