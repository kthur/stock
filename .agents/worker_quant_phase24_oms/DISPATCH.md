# DISPATCH: Worker 3 (Microstructure OMS Specialist - R3)

## Identity & Role
- Archetype: teamwork_preview_worker
- Role: Microstructure OMS Specialist
- Working directory: `d:\Finance\code\stock\.agents\worker_quant_phase24_oms`

## Strict File Ownership
You exclusively own and may edit/create ONLY these files:
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `tests/test_phase24_oms.py`
Do NOT edit any other files.

## Reference Inputs
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-11T10:54:49Z`)
- Explorer 3 Blueprint: `d:\Finance\code\stock\.agents\explorer_quant_phase24_survey3\handoff.md`
- Project Scope: `d:\Finance\code\stock\PROJECT.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements (R3)
1. **Feature F117.2: Kerr-Newman-Kiselev Quintessence-Phantom-Tachyon 3-Dark-Energy L3 Hydrodynamics**:
   - In `src/core/fast_lob_engine.py`:
     - Implement `compute_knk_quintessence_phantom_tachyon_hydrodynamics` with equation of state parameter $w_{\text{tachyon}} = -5/3$, tachyon metric term $-c_t r^6$, tachyon energy density $\rho_t = 2.5 c_t r^2$, cosmological horizon $r_T \sim (1/c_t)^{0.20}$, and repulsive tidal force $-c_q r - 2 c_p r^3 - 2.5 c_t r^4$.
     - Bind 8 method aliases.
     - In `DeepHawkesArrivalProcess`, configure dark pool routing cap to `0.99998` (99.998%) under phase24 mode.
2. **Maker Floor Contraction ($0.0000005$) in `src/execution/smart_order_router.py`**:
   - In `SmartOrderRouter.route_order`, implement contraction `0.70 * (1.0 - 0.9999992857 * gamma_toxic)` with floor `0.0000005` under extreme toxicity ($\gamma_{\text{toxic}} > 0.80$).
   - Dynamic anti-gaming MinQty `0.999995` (99.9995%).
   - Adjust dictionary formatting precision to 7 decimals (`round(float(maker_ratio), 7)`) to ensure `0.0000005` is preserved accurately without rounding up.
3. **Preemptive Micro-Tick Shading in `src/execution/oms_engine.py`**:
   - In `ExecutionOMSEngine.calculate_dynamic_pegged_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
   - Contract trigger threshold from $0.035$ to $0.030$. When $h > 0.030$, apply `hawkes_shift = -direction * 0.9998 * spr * (h - 0.030)`.
   - Ensure dark pool routing cap 99.998% ATS and anti-gaming MinQty 99.9995%.
4. **Unit Test Suite (`tests/test_phase24_oms.py`)**:
   - Implement comprehensive unit tests covering F117.2 hydrodynamics, aliases, maker floor 0.0000005, tick shading -0.9998, ATS 99.998%, anti-gaming 99.9995%, and execution slippage bounds.
   - Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase24_oms.py tests/test_phase23_*.py -v` to ensure 100% pass and 0 regressions.

Deliver your detailed report in `handoff.md`.

## 2026-09-11T11:03:06Z
You are Worker 3 (Microstructure OMS Specialist).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase24_oms
Read your dispatch at: d:\Finance\code\stock\.agents\worker_quant_phase24_oms\DISPATCH.md
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-11T10:54:49Z).
Read Explorer 3's blueprint at: d:\Finance\code\stock\.agents\explorer_quant_phase24_survey3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict File Ownership:
You may edit/create ONLY:
- src/core/fast_lob_engine.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- tests/test_phase24_oms.py

Implement:
1. Feature F117.2: Kerr-Newman-Kiselev Quintessence-Phantom-Tachyon 3-Dark-Energy ($w_{\text{tachyon}} = -5/3$) L3 Hydrodynamics in `fast_lob_engine.py` with 8 aliases and dark ATS routing cap 99.998% in `DeepHawkesArrivalProcess`.
2. Maker floor contraction $0.0000005$ in `smart_order_router.py` with 7-decimal formatting precision.
3. Preemptive micro-tick shading $-0.9998 \cdot \text{spread} \cdot (h - 0.030)$, dark ATS 99.998%, anti-gaming MinQty 99.9995% in `oms_engine.py`.
4. Unit test suite `tests/test_phase24_oms.py`.

Run build/tests using:
`.venv\Scripts\python.exe -m pytest tests/test_phase24_oms.py tests/test_phase23_*.py -v`
Verify 100% pass and no regressions.
Write full report with test results to `d:\Finance\code\stock\.agents\worker_quant_phase24_oms\handoff.md` and send a message when done.

