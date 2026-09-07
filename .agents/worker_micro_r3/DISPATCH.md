## 2026-09-06T15:11:33Z

You are Worker subagent (identity: worker_micro_r3).
Working directory: d:\Finance\code\stock\.agents\worker_micro_r3
Original Request Path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Please read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-06T15:02:05Z).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Technical blueprints & explorer survey report:
Read `d:\Finance\code\stock\.agents\explorer_survey_2\handoff.md` for exact line numbers, formulas, and architecture.

Exclusive File Ownership:
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
DO NOT touch any other source files.

Your Mission (Milestone 3 - R3 Microstructure OMS Enhancement):
1. `trading_system/src/core/fast_lob_engine.py`:
   - In `FastOrderBookMatchingEngine`: Implement `compute_reissner_nordstrom_extremal_queue_acceleration(self, charge_parameter: float = 1.0, levels: int = 10, timestamp_sec: Optional[float] = None, **kwargs)` with extremal condition a=0, Q=M, r_H=M, vanishing frame-dragging omega_drag=0.0, radial tidal force field R^r_{trt} = M(2r-3M)/r^4, and near-horizon AdS_2 x S^2 throat amplification.
     Aliases: `compute_reissner_nordstrom_queue_acceleration`, `calculate_reissner_nordstrom_queue_acceleration`.
   - In `DeepHawkesArrivalProcess`: Expand dark routing preemption cap to 0.9995 (99.95%) under `version >= 19`.
2. `trading_system/src/execution/smart_order_router.py`:
   - Set version flag `is_phase19 = (v_eff >= 19)`.
   - In maker floor contraction (when `gamma_toxic > 0.80`): under Phase 19, contract maker floor down to 0.00002 (via `float(np.clip(0.70 * (1.0 - 0.9999714 * gamma_toxic), 0.00002, 0.70))`).
   - ATS dark routing preemption ratio cap: expand to 0.9995 (99.95%) under `is_phase19`.
   - Dynamic Anti-Gaming MinQty cap: expand to 0.9998 (99.98%) under `is_phase19`.
3. `trading_system/src/execution/oms_engine.py`:
   - In both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
     Implement Phase 19 preemptive tick shading when h_val > 0.08 with offset:
     `hawkes_shift = -direction * 0.995 * spr * (h_val - 0.08)`.
4. Verification:
   Run unit tests via `.venv\Scripts\python.exe -m pytest tests/test_fast_lob_engine.py tests/test_smart_order_router.py tests/test_oms_engine.py -v` (or related test files).
   Ensure 100% pass rate.
5. Deliver `handoff.md` in `d:\Finance\code\stock\.agents\worker_micro_r3\handoff.md` and message parent when complete.
