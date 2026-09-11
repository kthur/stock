# DISPATCH — worker_m3 (Microstructure OMS Specialist - Milestone M3)

## Mandatory Reading
You MUST read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically section ## 2026-09-10T01:13:45Z) and `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\PROJECT.md` before starting work.
Also read the detailed survey findings in `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2\survey_report.md`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership & Exclusivity
You have EXCLUSIVE write ownership of:
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
You MUST NOT edit any AI ensemble, risk, or benchmark files.

## Technical Specifications & Requirements
1. **Feature F105.2: Kerr-Newman-AdS-dS Cosmological Black Hole L3 Hydrodynamics**:
   - In `FastOrderBookMatchingEngine`: implement `compute_kerr_newman_ads_ds_queue_acceleration(charge_parameter=0.5, spin_parameter=0.5, ads_radius=10.0, ds_radius=20.0, cosmological_lambda=None, ...) -> Dict[str, float]`.
   - Incorporate cosmological constant $\Lambda = 3/L_{dS}^2 - 3/L_{AdS}^2$, rotation factor $\Xi_{AdS-dS}$, de Sitter expansion horizon $r_C = L_{dS}(1 - M/L_{dS})$, and hydrodynamic acceleration $a_{AdS-dS}$.
   - Return dictionary keys: `kn_ads_ds_hydrodynamic_acceleration`, `kn_ads_ds_accelerated_qi`, `kn_ads_ds_micro_price`, `kn_ads_ds_tidal_force`, `frame_dragging_omega`, `cosmological_lambda`, etc.
   - Aliases: `compute_kerr_newman_ads_ds_acceleration`.
2. **Feature F105.2.2 & F105.2.3 & F105.2.4: SmartOrderRouter Updates**:
   - Lit maker floor contracted to **0.000005** (0.0005%) when `is_phase21 and gamma_toxic > 0.80`.
   - Max dark pool ATS routing cap expanded to **99.98%** (0.9998) when `is_phase21`.
   - Dynamic Anti-Gaming MinQty ratio expanded to **99.995%** (0.99995) when `is_phase21`.
   - In `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`: Preemptive ATS cap $= 0.9998$ for version >= 21.
3. **Feature F105.2.5: Preemptive Hawkes Micro-Tick Shading in OMS Engine**:
   - In `ExecutionOMSEngine` and `AlmgrenChrissScheduler` (`calculate_peg_limit_price`):
     When `version >= 21` and $h_{val} > 0.05$, `hawkes_shift = -direction * 0.998 * spr * (h_val - 0.05)`.
4. **Testing & Verification**:
   - Run tests using `.venv\Scripts\python.exe -m pytest tests/test_fast_lob_engine.py` (or existing execution/oms tests) to verify 100% pass and no regression.

## Deliverables
- Genuine implementation of M3 in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, and `src/execution/oms_engine.py`.
- Write `handoff.md` with:
  * Files modified and line numbers
  * Test execution commands and passing output
  * Verification of all interface contracts and mathematical formulas

## 2026-09-10T01:23:37Z
You are worker_m3, the Microstructure OMS Specialist for Phase 21 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\worker_m3
Read d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\worker_m3\DISPATCH.md, d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-10T01:13:45Z), and d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\PROJECT.md before starting.
Also inspect d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2\survey_report.md for technical details.
Implement Feature F105.2 (Kerr-Newman-AdS-dS cosmological black hole L3 hydrodynamics in fast_lob_engine.py), maker floor 0.000005 in smart_order_router.py, tick shading coefficient -0.998 * spread * (h - 0.05), ATS 99.98%, MinQty 99.995% in oms_engine.py and smart_order_router.py.
DO NOT CHEAT. All implementations must be genuine.
Run tests using .venv\Scripts\python.exe -m pytest to verify 100% pass without regressions.
Write handoff.md in your working directory and send a completion message to the orchestrator.
