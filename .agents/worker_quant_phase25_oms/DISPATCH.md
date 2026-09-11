## 2026-09-11T12:19:24Z
You are Worker 3 (Microstructure OMS Specialist) for Phase 25 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase25_oms

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Authoritative User Request:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (under header ## 2026-09-11T12:11:40Z)

Reference Architectural Survey & Blueprint:
d:\Finance\code\stock\.agents\explorer_quant_phase25_survey3\handoff.md

Exclusive Files Owned by You:
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase25_oms.py`

Your Tasks:
1. In `src/core/fast_lob_engine.py`:
   - Implement Feature F121.2: Kerr-Newman-Kiselev Quintom 4-Dark-Energy ($w_{\text{quintom}} = -2$) L3 Hydrodynamics Model (`compute_kerr_newman_kiselev_quintom_queue_acceleration`), energy density $\rho_m = 3.0 c_m r^3$, metric term $-c_m r^7$, outer cosmological horizon $r_M$, frame-dragging, radial tidal force, and dark routing cap 0.99999 under version >= 25, plus all 12+ aliases.
2. In `src/execution/smart_order_router.py`:
   - Add version >= 25 branching with maker floor contraction to `0.0000002`, Anti-Gaming MinQty expanded to `99.9998%` (0.999998), and lit queue preemption elevated to `0.99999`.
3. In `src/execution/oms_engine.py`:
   - Update `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price` with version >= 25 preemptive tick shading: `hawkes_shift = -direction * 0.9999 * spr * (h_val - 0.025)` when `h_val > 0.025`.
4. Implement unit test suite `tests/test_phase25_oms.py` (10 tests covering quintom L3 physics, dark routing cap, maker floor, anti-gaming MinQty, preemptive tick shading, and backward compatibility).
5. Execute tests using `.venv/Scripts/python.exe -m pytest tests/test_phase25_oms.py tests/test_phase24_oms.py -v`. Ensure 100% pass and 0 regressions.
6. Write detailed handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase25_oms\handoff.md`.
7. Send completion message back to orchestrator.
