## 2026-09-07T11:47:00Z

You are Worker M3 (Microstructure OMS Specialist).
Your working directory is: d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\worker_m3

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md first (specifically section ## 2026-09-07T11:39:07Z).
Also read:
- d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\PROJECT.md
- d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\explorer_survey_2\handoff.md

Your exclusive write ownership:
- trading_system/src/core/fast_lob_engine.py
- trading_system/src/execution/smart_order_router.py
- trading_system/src/execution/oms_engine.py
- tests/test_phase20_microstructure_oms.py

Tasks:
1. In trading_system/src/core/fast_lob_engine.py, implement compute_kerr_newman_ads_queue_acceleration (F101.2) with AdS cosmological constant Lambda = -3/L^2, frame dragging, tidal force, boundary reflection, and aliases. Update DeepHawkesArrivalProcess with 0.9997 dark routing cap for version >= 20.
2. In trading_system/src/execution/smart_order_router.py, implement maker floor contraction to 0.00001 (0.70 * (1.0 - 0.9999857 * gamma_toxic)), max dark cap 0.9997, and Anti-Gaming MinQty cap 0.9999 for version >= 20.
3. In trading_system/src/execution/oms_engine.py, implement preemptive micro-tick shading in ExecutionOMSEngine.calculate_peg_limit_price and AlmgrenChrissScheduler.calculate_peg_limit_price: for version >= 20 and h_val > 0.06, hawkes_shift = -direction * 0.997 * spr * (h_val - 0.06).
4. Create tests/test_phase20_microstructure_oms.py verifying Kerr-Newman-AdS physics, maker floor 0.00001, tick shading -0.997, ATS 99.97%, and Anti-Gaming 99.99%.
5. Verify by running tests:
   .venv\Scripts\python.exe -m pytest tests/test_phase20_microstructure_oms.py tests/test_phase19_microstructure_oms.py -v
6. Write your handoff report to:
   d:\Finance\code\stock\.agents\orchestrator_quant_phase20_1\worker_m3\handoff.md
   and notify the orchestrator via send_message.
