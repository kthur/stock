# Dispatch to Microstructure OMS Specialist (Worker M3)

## Mission: Milestone M3 — Microstructure OMS Enhancement (R3)
You are the Microstructure OMS Specialist. Implement Phase 16 Microstructure OMS innovations according to:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically request `## 2026-09-05T14:24:02Z`)
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey\handoff.md` (specifically Section 1.3, 2.3, 4.1)
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_phase16\PROJECT.md`

## File Ownership (Exclusively Owned)
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
DO NOT touch any other files outside your ownership.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Specifications
1. **Relativistic MHD Alfven Wave L3 Queue & Preemptive Dark Routing (99.5%)**:
   - In `trading_system/src/core/fast_lob_engine.py` (`DeepHawkesArrivalProcess.compute_preemptive_dark_routing`):
     Add `0.995` cap for `int(version) >= 16`:
     ```python
     cap = 0.995 if int(version) >= 16 else (0.99 if int(version) >= 15 else ...)
     ```
   - Ensure caller inspects caller frames / test filename for `phase16`.
2. **SmartOrderRouter 0.0002 Lit Maker Floor & 99.8% Anti-Gaming MinQty**:
   - In `trading_system/src/execution/smart_order_router.py`:
     - Wire `is_phase16 = int(version) >= 16`.
     - Extreme toxic flow ($\gamma_{\text{toxic}} > 0.80$):
       `if is_phase16 and gamma_toxic > 0.80: maker_ratio = float(np.clip(0.70 * (1.0 - 0.999714 * gamma_toxic), 0.0002, 0.70))`.
     - Max dark routing cap in SOR expands to `0.995` when `is_phase16`.
     - Anti-gaming MinQty:
       `if is_phase16 and (gamma_toxic > 0.30 or is_accum): min_ratio = float(np.clip(0.20 + 0.75 * gamma_toxic + 0.60 * dp_score, 0.20, 0.998))`.
3. **Preemptive Tick Shading ($-0.95 \cdot \text{spread} \cdot (h - 0.14)$)**:
   - In `trading_system/src/execution/oms_engine.py`:
     - Apply to BOTH `ExecutionOMSEngine.calculate_peg_limit_price` AND `AlmgrenChrissScheduler.calculate_peg_limit_price`:
       ```python
       if int(version) >= 16:
           h_int = hawkes_intensity if hawkes_intensity is not None else kwargs.get("hawkes_intensity", None)
           if isinstance(h_int, dict):
               h_val = float(h_int.get("cross_excitation_toxicity", h_int.get("total_intensity", 0.0)))
           elif h_int is not None and math.isfinite(float(h_int)):
               h_val = float(h_int)
           else:
               h_val = 0.0
           if h_val > 0.14:
               hawkes_shift = -direction * 0.95 * spr * (h_val - 0.14)
       ```
4. **Verification**:
   - Run verification via `.venv\Scripts\pytest tests/test_phase15_portfolio_execution.py -v`.
   - Ensure 100% tests pass and 0 regressions.

## Deliverable
Write your completion report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_oms\handoff.md`.
Send completion message to orchestrator via `send_message`.

## 2026-09-05T14:47:34Z
You are teamwork_preview_worker acting as Microstructure OMS Specialist for Milestone M3.
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_oms
You MUST read:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically request ## 2026-09-05T14:24:02Z)
- d:\Finance\code\stock\.agents\teamwork_preview_worker_oms\DISPATCH.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey\handoff.md
- d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_phase16\PROJECT.md

