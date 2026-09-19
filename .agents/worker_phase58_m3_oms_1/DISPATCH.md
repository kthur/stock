## 2026-09-19T13:30:00Z
You are the Microstructure OMS Specialist for Phase 58 Quantitative Alpha Enhancement (v65 Production Master).
Your working directory is: d:\Finance\code\stock\.agents\worker_phase58_m3_oms_1
Your parent orchestrator conversation ID: 6ec7eafc-8b42-4415-9793-92ec10afc894

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEPS:
1. Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-19T13:19:44Z)
2. Read your dispatch context at:
d:\Finance\code\stock\.agents\orchestrator_quant_phase58_1\DISPATCH.md
3. Read the detailed engineering and mathematical blueprint report prepared by your explorer:
d:\Finance\code\stock\.agents\explorer_phase58_oms_1\handoff.md

EXCLUSIVE FILE OWNERSHIP:
You have exclusive write ownership over:
- d:\Finance\code\stock\trading_system\src\core\fast_lob_engine.py
- d:\Finance\code\stock\trading_system\src\execution\smart_order_router.py
- d:\Finance\code\stock\trading_system\src\execution\oms_engine.py
- d:\Finance\code\stock\trading_system\src\execution\almgren_chriss.py
- d:\Finance\code\stock\tests\test_phase58_oms.py
Do NOT touch or modify any files outside these paths.

CORE IMPLEMENTATION REQUIREMENTS:
1. F264.1: In trading_system/src/core/fast_lob_engine.py:
   - Implement Kerr-Newman-Kiselev 37-dark-energy DAHA L3 Spacetime Hydrodynamics with 37th dark energy component:
     w = -39/3 = -13.0, k_daha = 0.29, k_monster = 0.28, daha_37_factor = 4.88,
     c_monster = 0.00000000000152587890625 (1.52587890625e-12),
     repulsive acceleration = -19.5 * c_monster * (r ** 38) * daha_37_factor.
   - Define all 28 canonical method aliases on FastOrderBookMatchingEngine (and FastLOBEngine).
   - In DeepHawkesArrivalProcess.compute_preemptive_dark_routing, inspect call frames for "phase58" in cname or version >= 58, setting max dark allocation cap to 0.99999999999999998 (18 nines).
2. F264.2: In trading_system/src/execution/smart_order_router.py, oms_engine.py, almgren_chriss.py:
   - In smart_order_router.py:
     Contract primary exchange lit maker ratio floor down to 1e-30 with 30-decimal precision under gamma_toxic > 0.80 and is_phase58:
     maker_ratio = float(np.clip(round(0.70 * (1.0 - 0.999999999999999999999999999986 * gamma_toxic), 40), 1e-30, 0.70))
     Scale preemptive dark ATS routing allocation cap up to 0.99999999999999998 (18 nines) in _resolve_max_dark_cap and route_order.
     Scale anti-gaming MinQty up to 0.99999999999999998 under adverse queue imbalance.
     Round maker_ratio and min_ratio to 30 decimals when is_phase58.
   - In oms_engine.py (ExecutionOMSEngine.calculate_peg_limit_price) and almgren_chriss.py (AlmgrenChrissScheduler.calculate_peg_limit_price):
     Implement preemptive micro-tick shading activating strictly at h > 0.000004:
     hawkes_shift = -direction * 0.999999999999999 * spread * (h - 0.000004)
     with zero shading (deadband) for h <= 0.000004.
3. Backward Compatibility:
   - Maintain 100% backward compatibility for version < 58.
4. Verification Test Suite:
   - Create tests/test_phase58_oms.py modeled after tests/test_phase57_oms.py covering KNK 37-dark-energy DAHA, 28 aliases, dark routing cap 18 nines, lit maker floor 1e-30, anti-gaming MinQty 18 nines, tick shading at h > 0.000004, and backward compatibility.
   - Run tests using:
     .venv\Scripts\pytest tests/test_phase58_oms.py -v
     .venv\Scripts\pytest tests/test_phase57_oms.py -v
   - Ensure 100% tests pass.
