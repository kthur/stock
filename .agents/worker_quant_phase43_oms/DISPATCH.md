# DISPATCH: Worker 3 (Microstructure OMS Specialist)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase43_oms

## Authoritative User Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

## Technical Blueprint & Survey Report
Read and strictly follow:
`d:\Finance\code\stock\.agents\explorer_quant_phase43_survey3\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive File Ownership
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase43_oms.py`

## Implementation Directives (Milestone R3)
1. In `trading_system/src/core/fast_lob_engine.py`:
   - Implement F193.2: Kerr-Newman-Kiselev 22-Dark-Energy PCQTGBDDDDHKMAEETU Elliptic-Hypergeometric-Askey-Wilson ($w = -24/3 = -8.0$, $k_{\text{daha}} = 0.14$, $c_{\text{pcqtgbddddhkmaeetu}} = 5 \times 10^{-8}$) DAHA L3 hydrodynamics with $\text{daha\_22\_factor} = 1.90$, $r^{25}$ metric expansion, $-12.0 \cdot c \cdot r^{23}$ tidal force, $(1/c)^{1/24}$ outer horizon.
   - Update `DeepHawkesArrivalProcess.compute_preemptive_dark_routing` to support `version >= 43` and frame inspection (`"phase43"` in caller filename) capping at `0.99999999999` (99.999999999% ATS).
   - Add method aliases (`compute_phase43_queue_acceleration`, `compute_phase43_lob_hydrodynamics`, etc.).

2. In `trading_system/src/execution/smart_order_router.py`:
   - Set `self.is_phase43 = (self.version >= 43)`.
   - In `_resolve_max_dark_cap(v_eff)`: return `0.99999999999` when `v_eff >= 43`.
   - In `execute_route`: contract lit maker floor under extreme toxicity (`gamma_toxic > 0.80`) to $1 \times 10^{-15}$ (`np.clip(0.70 * (1.0 - 0.9999999999999986 * gamma_toxic), 0.000000000000001, 0.70)`).
   - In dynamic Anti-Gaming MinQty: cap at `0.999999999998` ($99.9999999998\%$) and round metadata to 16 digits when `is_phase43`.

3. In `trading_system/src/execution/oms_engine.py`:
   - In both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
     Implement Hawkes preemptive micro-tick shading when `int(version) >= 43`:
     when $h > 0.0004$, shift $-direction \cdot 0.9999999999 \cdot \text{spread} \cdot (h - 0.0004)$.

4. In `tests/test_phase43_oms.py`:
   - Implement the complete 8-test unit test suite as specified in the Survey 3 handoff report.
   - Run tests: `.venv/Scripts/python.exe -m pytest tests/test_phase43_oms.py -v`
   - Run regression test: `.venv/Scripts/python.exe -m pytest tests/test_phase42_oms.py -q`
   - Verify 100% pass rate.

5. Write completion report to:
   `d:\Finance\code\stock\.agents\worker_quant_phase43_oms\handoff.md`
   and send a completion message to the orchestrator.

## 2026-09-15T06:29:13Z
You are Worker 3 (Microstructure OMS Specialist Worker) for Phase 43 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase43_oms
Read your dispatch instructions at:
d:\Finance\code\stock\.agents\worker_quant_phase43_oms\DISPATCH.md
Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)
Read the technical blueprint at:
d:\Finance\code\stock\.agents\explorer_quant_phase43_survey3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive file ownership:
- trading_system/src/core/fast_lob_engine.py
- trading_system/src/execution/smart_order_router.py
- trading_system/src/execution/oms_engine.py
- tests/test_phase43_oms.py

Implement F193.2 KNK 22-Dark-Energy DAHA (w=-8.0, k_daha=0.14) L3 hydrodynamics, maker floor 1e-15 in SOR, preemptive tick shading -0.9999999999 * spread * (h - 0.0004) in OMS, dark ATS cap 99.999999999%, dynamic Anti-Gaming MinQty 99.9999999998%, and tests/test_phase43_oms.py.
Execute tests: .venv/Scripts/python.exe -m pytest tests/test_phase43_oms.py -v
Execute regression: .venv/Scripts/python.exe -m pytest tests/test_phase42_oms.py -q
Write handoff report to:
d:\Finance\code\stock\.agents\worker_quant_phase43_oms\handoff.md
Send a completion message back to orchestrator.
