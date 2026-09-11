# DISPATCH — explorer_survey_2 (Risk & Microstructure OMS Survey)

## Task Description
You are the Risk & Microstructure OMS Explorer for Phase 21 Quant Enhancement.
Your working directory is: `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2`.
You MUST read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically section ## 2026-09-10T01:13:45Z) before beginning.

## Investigation Scope
Investigate `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, and `src/execution/oms_engine.py` to examine:
1. Existing Phase 19/20 implementations:
   - F101.1 Lurie Spectral AG Fisher-Rao manifold barycenter blending in `unified_portfolio_allocator.py` (version >= 20).
   - 16th-order cumulant expansion Ultra-Transcendent EVaR tail risk budgeting in `portfolio_allocator.py` and `unified_portfolio_allocator.py`.
   - F101.2 Kerr-Newman-AdS black hole L3 hydrodynamics in `fast_lob_engine.py`.
   - Maker floor 0.00001, ATS 99.97%, MinQty 99.99% in `smart_order_router.py`.
   - Tick shading coefficient `-0.997 * spread * (h - 0.06)` in `oms_engine.py`.
2. Requirements for Phase 21:
   - R2: F105.1 Lurie Chromatic Homotopy Theory Fisher-Rao manifold barycenter blending in `unified_portfolio_allocator.py` (version >= 21) with metric weights and convergence parameters.
   - 17th-order cumulant expansion Hyper-Transcendent EVaR in `portfolio_allocator.py` and `unified_portfolio_allocator.py` (17! = 355,687,428,096,000, target MDD <= -0.028%, Sharpe >= 15.92).
   - R3: F105.2 Kerr-Newman-AdS-dS cosmological black hole spacetime L3 orderbook hydrodynamics model in `fast_lob_engine.py` (incorporating cosmological constant Lambda / de Sitter horizon effects).
   - Maker floor 0.000005 in `smart_order_router.py`.
   - Tick shading coefficient `-0.998 * spread * (h - 0.05)` for Hawkes intensity h > 0.05, dark pool routing 99.98% ATS, Anti-Gaming MinQty 99.995% in `oms_engine.py`.
3. Identify exact file paths, line numbers, function signatures, class methods, and interface contracts needed for implementation workers.

## Output Requirements
- Write your complete survey report to:
  `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2\survey_report.md`

## 2026-09-10T01:15:58Z
You are explorer_survey_2, the Risk & Microstructure OMS Explorer for Phase 21 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2
Read d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2\DISPATCH.md and d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically ## 2026-09-10T01:13:45Z) first.
Investigate src/risk/unified_portfolio_allocator.py, src/risk/portfolio_allocator.py, src/core/fast_lob_engine.py, src/execution/smart_order_router.py, and src/execution/oms_engine.py to survey Phase 19/20 implementations and determine the exact technical specification, line numbers, function signatures, and interface contracts for Phase 21 (R2: F105.1 Lurie Chromatic Homotopy Theory Fisher-Rao barycenter in unified_portfolio_allocator.py version >= 21, 17th-order cumulant Hyper-Transcendent EVaR; R3: F105.2 Kerr-Newman-AdS-dS cosmological black hole L3 hydrodynamics in fast_lob_engine.py, maker floor 0.000005 in smart_order_router.py, tick shading -0.998 * spread * (h - 0.05), ATS 99.98%, MinQty 99.995% in oms_engine.py).
Write your survey report to d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2\survey_report.md and handoff.md, then send a completion message to the orchestrator.

## 2026-09-10T01:21:13Z
**Context**: Survey status check
**Content**: Checking in on your progress for the Risk & Microstructure OMS survey (F105.1, 17th-order EVaR, F105.2, OMS rules).
**Action**: Please report current status or estimated time to report completion.
