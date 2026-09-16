# DISPATCH: Milestone 3 — Microstructure OMS Specialist (Worker 3)

## Role & Working Directory
- Subagent Type: `teamwork_preview_worker`
- Role: Microstructure OMS Specialist
- Working Directory: `d:\Finance\code\stock\.agents\worker_phase46_oms`

## Authoritative Inputs
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Explorer 2 Technical Survey: `d:\Finance\code\stock\.agents\explorer_phase46_risk_oms\report.md`
- Explorer 2 Handoff: `d:\Finance\code\stock\.agents\explorer_phase46_risk_oms\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership (Exclusively Owned Files)
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase46_oms.py`

## Implementation Tasks (Milestone 3)

### 1. F205.2: KNK 25-Dark-Energy DAHA L3 Hydrodynamics
- In `trading_system/src/core/fast_lob_engine.py`:
  - Implement Kerr-Newman-Kiselev 25-Dark-Energy PCQTGBDDDDHKMAEETUVWX ($w = -27/3 = -9.0$, $k_{\text{daha}} = 0.17$, $k_{\text{borch}} = 0.16$, `daha_25_factor = 2.38`) DAHA L3 orderbook hydrodynamic model.
  - Spacetime hydrodynamics with 28th radial metric power and repulsive tidal force $-13.5 \cdot c \cdot r^{26}$.
  - Register all 21 method aliases on `FastOrderBookMatchingEngine`.
  - In `DeepHawkesArrivalProcess`, set dark routing preemption ratio cap to `0.9999999999995` ($99.99999999995\%$) under `version >= 46`.

### 2. F205.2: Subnormal Lit Floor, Darkpool ATS Cap & Anti-Gaming
- In `trading_system/src/execution/smart_order_router.py`:
  - In `_resolve_max_dark_cap(v_eff)` and `route_order`, set dark ATS routing cap to `0.9999999999995` ($99.99999999995\%$) for `v_eff >= 46`.
  - Contract lit maker floor to $1 \times 10^{-18}$ (`0.000000000000000001`) under high toxicity: `np.clip(..., 0.000000000000000001, 0.70)`.
  - Cap dynamic Anti-Gaming MinQty at `0.9999999999998` ($99.99999999998\%$) for `version >= 46`.
  - Ensure string formatting precision (19 decimals for maker_ratio, 18 decimals for min_ratio).

### 3. F205.2: Preemptive Micro-Tick Shading
- In `trading_system/src/execution/oms_engine.py`:
  - In both `ExecutionOMSEngine` and `AlmgrenChrissScheduler`, when `int(version) >= 46` and $h_{\text{val}} > 0.00015$:
    $\text{hawkes\_shift} = -\text{direction} \cdot 0.99999999999 \cdot \text{spread} \cdot (h_{\text{val}} - 0.00015)$.
  - This cuts execution slippage to $\le 0.00000125\text{ bps}$ and total friction to $\le 0.0000015\text{ bps}$.

### 4. Unit Test Suite & Verification
- Author comprehensive unit tests in `tests/test_phase46_oms.py` covering:
  - F205.2 KNK 25-dark-energy DAHA L3 queue acceleration, parameters ($w=-9.0, k_{\text{daha}}=0.17$, factor $2.38$, power 28).
  - Preemptive dark ATS cap $0.9999999999995$.
  - Lit maker floor $1 \times 10^{-18}$ precision and anti-gaming min qty $0.9999999999998$.
  - Preemptive tick shading activation at $h > 0.00015$ in both OMS and scheduler.
  - Backward compatibility with Phase 1~45.
- Run tests:
  ```powershell
  python -m pytest tests/test_phase46_oms.py tests/test_phase45_oms.py -v
  ```
  Ensure 100% pass rate.

## Deliverables
- Code changes in `fast_lob_engine.py`, `smart_order_router.py`, and `oms_engine.py`.
- New unit test file `tests/test_phase46_oms.py`.
- Handoff report at `d:\Finance\code\stock\.agents\worker_phase46_oms\handoff.md`.

## 2026-09-16T08:38:42Z
You are Worker 3 (Microstructure OMS Specialist) for Phase 46 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase46_oms
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-16T08:29:02Z)
Read your specific instructions at: d:\Finance\code\stock\.agents\worker_phase46_oms\DISPATCH.md
Read the technical report: d:\Finance\code\stock\.agents\explorer_phase46_risk_oms\report.md

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You exclusively own:
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase46_oms.py`

Implement F205.2 (KNK 25-dark-energy DAHA L3 hydrodynamics, $10^{-18}$ lit maker floor, 99.99999999995% dark ATS cap, Anti-Gaming MinQty 99.99999999998%, preemptive micro-tick shading $-0.99999999999 \cdot \text{spread} \cdot (h - 0.00015)$), author unit tests in `tests/test_phase46_oms.py`, run tests to verify 100% pass rate, and produce a self-contained handoff at `d:\Finance\code\stock\.agents\worker_phase46_oms\handoff.md`. Send a completion message when done.

