# DISPATCH — reviewer_m2_opt6_2

## Mission
Robustness, interface conformance, numerical stability, and multi-market execution review of Phase 6 Milestone 2 (Features F43 & F44).

## Working Directory
`d:\Finance\code\stock\.agents\reviewer_m2_opt6_2`

## Mandatory Reference Documents (Read before starting work)
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`
2. `d:\Finance\code\stock\.agents\worker_m2_opt6_gen2\handoff.md`
3. `d:\Finance\code\stock\.agents\explorer_m1_2\handoff.md`
4. `d:\Finance\code\stock\.agents\explorer_m1_3\handoff.md`
5. `d:\Finance\code\stock\.agents\orchestrator_quant_opt6_gen2\PROJECT.md`

## Review Scope
- Numerical stability under singular covariance, zero volume, negative prices, NaN inputs, extreme volatility, and correlation collapse.
- Interface conformance of `route_order`, `calculate_peg_limit_price`, `optimize_multi_model_blend`, `apply_target_volatility_scaling`.
- Venue-specific execution compliance for `KRX_ATS_NEXTRADE` and `US_SMART_DMA`.
- Backward compatibility with Phase 5, Phase 4, and core execution systems.

## Instructions
1. Run and inspect test suites:
   `.venv\Scripts\python.exe -m pytest tests/test_phase6_portfolio_execution.py -v`
   `.venv\Scripts\python.exe -m pytest tests/test_fast_lob_engine.py tests/test_smart_router.py -v`
2. Audit error handling, clipping bounds, and type safety across all modified code paths.
3. Deliver verdict: APPROVE or REQUEST_CHANGES in `handoff.md`.

## 2026-09-04T15:30:24Z
You are reviewer_m2_opt6_2 (Robustness, Interface Conformance & Multi-Venue Execution Reviewer for Milestone 2).
Your working directory is: d:\Finance\code\stock\.agents\reviewer_m2_opt6_2
Parent Conversation ID: 50f1a6ac-db69-4f79-9fec-0df831df4b17

MANDATORY FIRST ACTIONS:
1. Initialize BRIEFING.md and progress.md in your working directory.
2. Read your DISPATCH.md: d:\Finance\code\stock\.agents\reviewer_m2_opt6_2\DISPATCH.md
3. Read ORIGINAL_REQUEST.md: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
4. Read worker_m2_opt6_gen2 handoff: d:\Finance\code\stock\.agents\worker_m2_opt6_gen2\handoff.md
5. Read explorer_m1_2 handoff: d:\Finance\code\stock\.agents\explorer_m1_2\handoff.md
6. Read explorer_m1_3 handoff: d:\Finance\code\stock\.agents\explorer_m1_3\handoff.md

REVIEW MANDATE:
- Inspect interface contracts, type annotations, and backward compatibility in `unified_portfolio_allocator.py`, `fast_lob_engine.py`, `smart_order_router.py`, `oms_engine.py`.
- Verify handling of extreme degenerate inputs: singular covariance matrices, zero volume books, negative prices, NaN inputs, extreme volatility, and correlation spikes.
- Check venue compliance tags for `KRX_ATS_NEXTRADE` and `US_SMART_DMA`.
- Run tests:
  `.venv\Scripts\python.exe -m pytest tests/test_phase6_portfolio_execution.py -v`
  `.venv\Scripts\python.exe -m pytest tests/test_fast_lob_engine.py tests/test_smart_router.py -v`
- Deliver structured handoff.md with clear verdict: APPROVE or REQUEST_CHANGES.
- Send message to parent when done.
