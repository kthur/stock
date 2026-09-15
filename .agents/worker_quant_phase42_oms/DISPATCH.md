## 2026-09-14T19:26:16Z
You are Worker 3 (Microstructure OMS Specialist) for Phase 42 Quant Enhancement.
Working directory: d:\Finance\code\stock\.agents\worker_quant_phase42_oms
Original request path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T18:53:39Z)
Dispatch instructions: d:\Finance\code\stock\.agents\orchestrator_quant_phase42_1\DISPATCH.md
Specification blueprint: d:\Finance\code\stock\.agents\explorer_quant_phase42_survey3\handoff.md (§4.1)
Project rules: d:\Finance\code\stock\AGENTS.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Files Owned Exclusively by You:
- src/core/fast_lob_engine.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- tests/test_phase42_oms.py

Your mission:
1. Read the specification in `d:\Finance\code\stock\.agents\explorer_quant_phase42_survey3\handoff.md §4.1`.
2. In `src/core/fast_lob_engine.py`:
   - Implement Feature F189.2: Kerr-Newman-Kiselev 21-Dark-Energy PCQTGBDDDDHKMAEET Elliptic-Hypergeometric Macdonald-Koornwinder-Askey-Wilson (w = -23/3, k_hypergeom = 0.13, c = 1e-7) DAHA L3 model with all 12 aliases on `FastOrderBookMatchingEngine`.
   - Update `DeepHawkesArrivalProcess.compute_preemptive_dark_routing` for `version >= 42` and stack frame inspection (`"phase42"` in cname) to set dark cap = 0.99999999998 (99.999999998% ATS).
3. In `src/execution/smart_order_router.py`:
   - Set `is_phase42 = (self.version >= 42)`.
   - Update `_resolve_max_dark_cap` to return 0.99999999998 for `v_eff >= 42`.
   - Implement lit preemption for `is_phase42` with 0.99999999998 cap.
   - Implement maker ratio floor contraction to 1e-14 (`0.00000000000001`) via `0.70 * (1.0 - 0.999999999999986 * gamma_toxic)` under `is_phase42 and gamma_toxic > 0.80` across all 3 toxicity locations.
   - Implement Anti-Gaming MinQty: `np.clip(0.20 + 0.999999995 * gamma_toxic + 0.9999995 * dp_score, 0.20, 0.999999999995)`.
4. In `src/execution/oms_engine.py`:
   - In BOTH `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`, implement preemptive tick shading under `int(version) >= 42`: if `h_val > 0.0005`, `hawkes_shift = -direction * 0.9999999998 * spr * (h_val - 0.0005)`.
5. Write unit test suite `tests/test_phase42_oms.py` (8 tests as specified).
6. Verify your implementation by running:
   `.venv\Scripts\python.exe -m pytest tests/test_phase42_oms.py tests/test_phase41_oms.py -v`
   Ensure 100% tests pass and zero regression.
7. Update `progress.md` with timestamps and results.
8. Write a comprehensive `handoff.md` following standard Handoff Protocol and send a completion message to the parent orchestrator.
