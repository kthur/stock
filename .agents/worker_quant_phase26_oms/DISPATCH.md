# DISPATCH: Worker 3 — Microstructure OMS Specialist Implementation (Phase 26)

## Working Directory
`d:\Finance\code\stock\.agents\worker_quant_phase26_oms`

## Role
Microstructure OMS Specialist Implementation Worker (`teamwork_preview_worker`)

## Context & Objectives
You are Worker 3 implementing the Phase 26 R3 Microstructure OMS Enhancement.
Authoritative user request:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-11T13:18:53Z`)
Full architectural survey and implementation blueprint:
`d:\Finance\code\stock\.agents\explorer_quant_phase26_survey3\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You EXCLUSIVELY own and modify:
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `tests/test_phase26_oms.py`

DO NOT modify any other files.

## Technical Tasks
1. Implement Feature F125.2: Kerr-Newman-Kiselev Chameleon 5-Dark-Energy ($w_{\text{chameleon}} = -7/3$) Spacetime L3 Orderbook Hydrodynamics Model in `src/core/fast_lob_engine.py`:
   - Implement `compute_kerr_newman_kiselev_chameleon_queue_acceleration` with 5 dark energy components ($w_q = -2/3, w_p = -4/3, w_t = -5/3, w_m = -2.0, w_c = -7/3$).
   - Equation of state density: $\rho_c = 3.5 c_c r^4$.
   - Horizon function term: $-c_c r^8$.
   - Cosmological horizon: $r_C = \max(r_H + 0.1, (1/c_c)^{1/7}(1 - M/\max(1.0, (1/c_c)^{1/7})))$.
   - Radial tidal force: $-3.5 c_c r^6$. Conformal factor: $+ c_c r^8$.
   - Provide all 12 class aliases on `FastOrderBookMatchingEngine`.
   - In `DeepHawkesArrivalProcess.compute_preemptive_dark_routing`, set dark routing cap to `0.999995` (99.9995% ATS) under Phase 26.
2. Implement Maker Floor $0.0000001$ in `src/execution/smart_order_router.py`:
   - Add `is_phase26 = (v_eff >= 26)`.
   - Contract lit maker floor: `maker_ratio = float(np.clip(0.70 * (1.0 - 0.9999998571 * gamma_toxic), 0.0000001, 0.70))`.
   - Anti-Gaming MinQty: `min_ratio = float(np.clip(0.20 + 0.999 * gamma_toxic + 0.95 * dp_score, 0.20, 0.999999))` (99.9999%).
   - Return formatting precision: `round(float(maker_ratio), 7)` and `round(float(min_ratio), 6)`.
3. Implement Preemptive Tick Shading in `src/execution/oms_engine.py`:
   - In `calculate_peg_limit_price()`, add `is_phase26 = (version >= 26)`.
   - Dynamic shading coefficient: $-0.99995 \cdot \text{spread} \cdot (h - 0.020)$ for Phase 26.
   - Target metrics: Execution slippage $\le 0.0005$ bps, trading friction costs $\le 0.010$ bps.
4. Implement `tests/test_phase26_oms.py` with all 10 unit test cases specified in Explorer 3's handoff report.
5. Run tests using `.venv/Scripts/python.exe -m pytest tests/test_phase26_oms.py tests/test_phase25_oms.py -v`. Ensure 100% pass and 0 regressions.
6. Write your completion report to `d:\Finance\code\stock\.agents\worker_quant_phase26_oms\handoff.md` and send a message to Orchestrator (`23291457-ea26-4c49-8433-2bc79a9280cf`).
