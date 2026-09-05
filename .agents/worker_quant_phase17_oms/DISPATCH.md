## 2026-09-05T22:34:06Z
You are Worker 3 (Microstructure OMS Specialist) for Phase 17 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase17_oms\
The authoritative original request is located at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
The detailed Survey Handoff Report is located at: d:\Finance\code\stock\.agents\explorer_quant_phase17_risk_oms\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Exclusive File Ownership:
- src/core/fast_lob_engine.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- tests/test_phase17_microstructure_oms.py

Task Instructions:
1. Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md and d:\Finance\code\stock\.agents\explorer_quant_phase17_risk_oms\handoff.md.
2. Implement Feature F89.2:
   - In `src/core/fast_lob_engine.py`:
     * Kerr spacetime ergosphere frame-dragging rotational queue acceleration model.
     * Expand dark ATS routing preemption cap to 99.8% (0.998) when `version >= 17` or `"phase17"` in caller name.
   - In `src/execution/smart_order_router.py`:
     * Update `is_phase17 = (v_eff >= 17)`.
     * Preemptive lit queue imbalance allocation with maximum dark cap 0.998.
     * Lit maker ratio floor contracted to 0.0001 (0.01%) via $0.70 \cdot (1.0 - 0.999857 \cdot \gamma_{\text{toxic}})$.
     * Dynamic anti-gaming MinQty scaled up to 99.9% (0.999).
   - In `src/execution/oms_engine.py`:
     * In both `ExecutionOMSEngine.calculate_peg_limit_price` and `AlmgrenChrissScheduler.calculate_peg_limit_price`:
       Activate preemptive micro-tick shading when `version >= 17`: if `h_val > 0.12`, apply $\text{hawkes\_shift} = -\text{direction} \cdot 0.98 \cdot \text{spread} \cdot (h_{\text{val}} - 0.12)$.
3. Create comprehensive test suite `tests/test_phase17_microstructure_oms.py` verifying:
   - Fast LOB 99.8% dark routing under toxic conditions.
   - SmartOrderRouter maker floor contraction to 0.0001 and MinQty up to 99.9%.
   - Preemptive tick shading in both OMS engine and AlmgrenChriss scheduler at $h > 0.12$.
   - Backward compatibility for versions 14, 15, and 16.
4. Execute tests using `.venv\Scripts\pytest.exe tests/test_phase17_microstructure_oms.py -v`.
5. Write your handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase17_oms\handoff.md` detailing changes, formulas, test commands and passing output.
6. When done, send a message back to the orchestrator.
