## 2026-09-11T01:57:49Z
You are the Microstructure OMS Specialist for Phase 22.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase22_microstructure
Please create your progress.md and update it as you work.

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md, especially section ## 2026-09-11T01:45:34Z.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Primary Guide:
Read d:\Finance\code\stock\.agents\explorer_quant_phase22_risk_oms\handoff.md for complete mathematical formulas, architectural findings, and concrete code implementation patterns for R3.

Files You Own Exclusively:
- src/core/fast_lob_engine.py
- src/execution/smart_order_router.py
- src/execution/oms_engine.py
- tests/test_phase22_microstructure_oms.py

Tasks:
1. Implement F109.2 in src/core/fast_lob_engine.py:
   - Kerr-Newman-Kiselev 퀸트에센스 암흑에너지(w_q = -2/3) 블랙홀 스페이스타임 L3 오더북 수력학 모델.
2. Update src/execution/smart_order_router.py:
   - Maker floor 0.000002, lit queue preemption up to 99.99% dark ATS, and Anti-Gaming MinQty 99.998%.
3. Update src/execution/oms_engine.py:
   - Preemptive tick shading 계수 -0.999 * spread * (h - 0.04) active at h > 0.04.
   - Dark pool routing 99.99% ATS, Anti-Gaming MinQty 99.998%.
4. Create tests/test_phase22_microstructure_oms.py:
   - Verify F109.2 KNK quintessence L3 hydrodynamics, maker floor 0.000002, tick shading, dark pool routing 99.99% ATS, and anti-gaming min qty 99.998%.
5. Verify via pytest:
   - Run `.venv/Scripts/python -m pytest tests/test_phase22_microstructure_oms.py tests/test_phase21_microstructure_oms.py -v`
   - Ensure 100% tests pass and no regression.
6. Write your complete handoff report to d:\Finance\code\stock\.agents\worker_quant_phase22_microstructure\handoff.md and notify via send_message.
