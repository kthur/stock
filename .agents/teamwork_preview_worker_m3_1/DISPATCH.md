# DISPATCH: Worker M3 — Microstructure OMS Specialist (OMS Specialist)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_1

## Role & Mission
You are the Microstructure OMS Specialist (OMS Specialist) for Phase 55 Quantitative Alpha Enhancement.
Your mission is to implement Features F249.1 and F249.2 in `fast_lob_engine.py`, `smart_order_router.py`, `oms_engine.py`, and `almgren_chriss.py`, create `tests/test_phase55_oms.py`, and verify test pass.

## Mandatory Reading
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-18T03:36:46Z`)
2. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\survey_report.md`
3. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\handoff.md`

## Exclusive Write Ownership
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `trading_system/src/execution/almgren_chriss.py` (if applicable, or within `oms_engine.py`)
- `tests/test_phase55_oms.py`
Do NOT edit any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **F249.1: Kerr-Newman-Kiselev 34-Dark-Energy DAHA L3 Spacetime Hydrodynamics (`fast_lob_engine.py`)**:
   - Implement `calculate_knk_34_dark_energy_daha_acceleration`:
     Parameters: $w = -36.0 / 3.0 = -12.0$, $k_{\text{daha}} = 0.26$, $k_{\text{monster}} = 0.25$, $\text{daha\_34\_factor} = 4.20$, $c_{\text{monster}} = 0.00000000001220703125$ ($1.220703125 \times 10^{-11}$).
     Repulsive acceleration: $-18.0 \cdot c_{\text{monster}} \cdot r^{35} \cdot \text{daha\_34\_factor}$.
   - Export 28 method aliases on `FastLOBEngine`:
     `calculate_knk_34_dark_energy_daha_acceleration`, `compute_knk_34_dark_energy_daha`, `knk_34_dark_energy_daha_acceleration`, `compute_phase55_lob_acceleration`, `phase55_lob_spacetime_hydrodynamics`, `daha_34_dark_energy_acceleration`, `kerr_newman_kiselev_34_acceleration`, `compute_34_dark_energy_acceleration`, `phase55_daha_l3_acceleration`, `knk_daha_34_acceleration`, `l3_knk_34_acceleration`, `spacetime_hydrodynamics_34_acceleration`, `daha_l3_phase55_acceleration`, `monster_daha_34_acceleration`, `phase55_dark_energy_acceleration`, `knk_34_spacetime_acceleration`, `calculate_phase55_knk_acceleration`, `compute_knk_phase55_acceleration`, `daha_phase55_acceleration`, `knk_dark_energy_34_acceleration`, `phase55_spacetime_hydrodynamics`, `compute_l3_hydrodynamics_v55`, `knk_34_daha_l3_acceleration`, `phase55_queue_acceleration`, `knk_34_acceleration`, `daha_34_acceleration`, `l3_phase55_acceleration`, `phase55_knk_acceleration`.
   - Update Deep Hawkes dark routing cap in `fast_lob_engine.py` to `0.9999999999999998` with stack frame inspection for `"phase55"` (or version gating).

2. **F249.2: SmartOrderRouter & Preemptive Micro-Tick Shading (`smart_order_router.py`, `oms_engine.py`, `almgren_chriss.py`)**:
   - `smart_order_router.py`:
     - Contract lit maker floor down to $1 \times 10^{-27}$ (27 decimals) under extreme toxic queue imbalance.
     - Scale preemptive dark ATS routing allocation cap up to $99.99999999999998\%$.
     - Scale anti-gaming MinQty up to $99.99999999999998\%$.
     - Ensure precision formatting handles 27 decimals without rounding corruption.
   - `oms_engine.py` (both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`):
     - Implement preemptive micro-tick shading activating at $h > 0.00001$:
       $$\text{hawkes\_shift} = -\text{direction} \cdot 0.99999999999999 \cdot \text{spread} \cdot (h - 0.00001)$$
     - Ensure both engine implementations are synchronized.

3. **Testing & Verification**:
   - Create `tests/test_phase55_oms.py` following the 8 test specifications from Survey Explorer 2's report.
   - Execute:
     `.venv\Scripts\python.exe -m pytest tests/test_phase55_oms.py -v`
     `.venv\Scripts\python.exe -m pytest tests/test_phase54_oms.py -v`
   - Confirm 100% test pass and zero regressions.

4. **Deliverables**:
   - Document changes in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_1\handoff.md`.
   - Report back with `send_message`.

## 2026-09-18T03:55:38Z
You are the Microstructure OMS Specialist (OMS Specialist) for Phase 55. Your working directory is d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_1.
Read your dispatch instructions in d:\Finance\code\stock\.agents\teamwork_preview_worker_m3_1\DISPATCH.md, the original request in d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-18T03:36:46Z), and Explorer 2's survey reports in d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\survey_report.md and handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement Features F249.1 and F249.2 in trading_system/src/core/fast_lob_engine.py, trading_system/src/execution/smart_order_router.py, and trading_system/src/execution/oms_engine.py.
Create tests/test_phase55_oms.py.
Run the test suites:
.venv\Scripts\python.exe -m pytest tests/test_phase55_oms.py -v
.venv\Scripts\python.exe -m pytest tests/test_phase54_oms.py -v
Write your handoff.md and send a completion message with send_message.
