# Worker Dispatch: R3 Microstructure OMS Specialist (Phase 23)

## Mission
Implement Feature F113.2 and F113.2.2 in `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, and `src/execution/oms_engine.py`.

## Reference Documents
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Section ## 2026-09-11T07:03:36Z)
- `d:\Finance\code\stock\.agents\explorer_quant_phase23_survey2\handoff.md` (Architecture blueprint)
- `d:\Finance\code\stock\AGENTS.md`

## Exclusive File Ownership
You exclusively own and may edit:
- `src/core/fast_lob_engine.py` (or `trading_system/src/core/fast_lob_engine.py`)
- `src/execution/smart_order_router.py` (or `trading_system/src/execution/smart_order_router.py`)
- `src/execution/oms_engine.py` (or `trading_system/src/execution/oms_engine.py`)
Do NOT touch files owned by other workers.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **F113.2 Kerr-Newman-Kiselev Quintessence-Phantom Double Dark Energy L3 Order Book Hydrodynamics**:
   - In `fast_lob_engine.py`, implement `compute_kerr_newman_kiselev_phantom_queue_acceleration(self, charge_parameter=0.5, spin_parameter=0.5, quintessence_parameter=0.05, phantom_parameter=0.02, w_q=-2.0/3.0, w_p=-4.0/3.0, theta=math.pi/2.0, levels=10, timestamp_sec=None, **kwargs)`.
   - Physics formulation:
     - Phantom dark energy: $w_p = -4/3$, $\rho_p(r) = 2 c_p \cdot r$
     - Quintessence dark energy: $w_q = -2/3$, $\rho_q(r) = c_q / r$
     - Metric horizon equation: $\Delta_r = (r^2 + a^2) - 2Mr + Q^2 - c_q r^3 - c_p r^5$
     - Frame dragging: $\omega_{\text{drag}}^{\text{KNK-P}}(r, \theta) = \frac{a (2Mr - Q^2 + c_q r^3 + c_p r^5)}{\rho^2 (r^2 + a^2) + a^2 (2Mr - Q^2 + c_q r^3 + c_p r^5) \sin^2\theta}$
     - Repulsive tidal force: $F_{\text{tidal}} = F_{\text{tidal}}^{\text{KN}} - c_q r - 2 c_p r^3$
     - Conformal factor: $\Gamma = 1.0 + \max(0, \frac{r_H - r}{r_H}) + \frac{M^2}{(r - r_H)^2 + 0.05 M^2} + c_q r^3 + c_p r^5$
     - Total queue acceleration: $a_{\text{KNK-P}} = a_{QI} + (\omega_{\text{drag}} + |F_{\text{tidal}}|) v_{QI} \Gamma + \frac{Q^2 v_{QI}}{\max(10^{-4}, r^3)} (1 + c_q r + c_p r^2)$.
   - Add aliases: `compute_kerr_newman_kiselev_phantom_acceleration`, `compute_knk_phantom_acceleration`, `compute_knk_phantom_hydrodynamics`, etc.
   - In `DeepHawkesArrivalProcess`: update dark routing cap to `0.99995` (99.995%) for version >= 23.
2. **F113.2.2 Micro-Friction Minimization in SOR & OMS**:
   - `smart_order_router.py`:
     - Add `is_phase23 = (v_eff >= 23)`.
     - Maker floor contraction: under extreme toxicity ($\gamma_{\text{toxic}} > 0.80$), contract maker floor to `0.000001` ($0.0001\%$).
     - Dark pool routing cap: expand to `0.99995` ($99.995\%$).
     - Anti-Gaming dynamic MinQty: scale up to `0.99999` ($99.999\%$).
   - `oms_engine.py`:
     - In `ExecutionOMSEngine.calculate_peg_limit_price`: under `if int(version) >= 23:`, when $h > 0.035$, apply preemptive micro-tick shading:
       `hawkes_shift = -direction * 0.9995 * spr * (h_val - 0.035)`
     - In `AlmgrenChrissScheduler.calculate_peg_limit_price`: under `if int(version) >= 23:`, when $h > 0.035$, apply identical tick shading:
       `hawkes_shift = -direction * 0.9995 * spr * (h_val - 0.035)`
3. **Execution Quality Targets**:
   - Verify that these micro-friction controls reduce Trading & Friction Costs to <= 0.025 bps and Slippage to <= 0.0015 bps.

## Verification & Output
- Run pytest on microstructure tests (e.g. `.venv/bin/pytest tests/test_phase22_microstructure_oms.py` or existing tests) to verify no regressions.
- Document all changes, line numbers, formulas, and test results in `d:\Finance\code\stock\.agents\worker_quant_phase23_oms\handoff.md`.
- Send a completion message when done.

## 2026-09-11T07:12:44Z
You are Worker 3: Microstructure OMS Specialist for Phase 23 Full Team Quantitative Enhancement.
Your working directory: d:\Finance\code\stock\.agents\worker_quant_phase23_oms
Dispatch task file: d:\Finance\code\stock\.agents\worker_quant_phase23_oms\DISPATCH.md
Original user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (See section ## 2026-09-11T07:03:36Z)
Survey report: d:\Finance\code\stock\.agents\explorer_quant_phase23_survey2\handoff.md
Project rules: d:\Finance\code\stock\AGENTS.md

Exclusive write ownership:
- `src/core/fast_lob_engine.py` (and `trading_system/src/core/fast_lob_engine.py`)
- `src/execution/smart_order_router.py` (and `trading_system/src/execution/smart_order_router.py`)
- `src/execution/oms_engine.py` (and `trading_system/src/execution/oms_engine.py`)
DO NOT edit files owned by other workers.

Mandatory Integrity Warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Implement F113.2 Kerr-Newman-Kiselev Quintessence-Phantom Double Dark Energy L3 Hydrodynamics in `fast_lob_engine.py` (`compute_kerr_newman_kiselev_phantom_queue_acceleration` with w_q = -2/3, w_p = -4/3, rho_p = 2 c_p r, Delta_r = (r^2+a^2)-2Mr+Q^2 - c_q r^3 - c_p r^5, frame dragging, tidal force, conformal amplification, aliases, and DeepHawkesArrivalProcess dark routing cap at 99.995% for version >= 23).
2. Implement Micro-Friction Minimization in `smart_order_router.py` (maker floor contracted to 0.000001 under toxic flow, dark pool routing cap 99.995%, Anti-Gaming MinQty scaled up to 99.999% for version >= 23).
3. Implement Preemptive Micro-Tick Shading in `oms_engine.py` in both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`: under `if int(version) >= 23:` when h > 0.035, apply `hawkes_shift = -direction * 0.9995 * spr * (h_val - 0.035)`.
4. Run build/tests using `.venv/bin/pytest tests/test_phase22_microstructure_oms.py` (or existing tests) to verify 100% pass and no regressions.
5. Write your complete handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase23_oms\handoff.md` and send a completion message.

