# DISPATCH — auditor_m2_opt6

## Mission
Forensic Integrity Audit of Phase 6 Milestone 2 (Features F43 & F44).

## Working Directory
`d:\Finance\code\stock\.agents\auditor_m2_opt6`

## Mandatory Reference Documents (Read before starting work)
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`
2. `d:\Finance\code\stock\.agents\worker_m2_opt6_gen2\handoff.md`
3. `d:\Finance\code\stock\.agents\explorer_m1_2\handoff.md`
4. `d:\Finance\code\stock\.agents\explorer_m1_3\handoff.md`
5. `d:\Finance\code\stock\.agents\orchestrator_quant_opt6_gen2\PROJECT.md`

## Audit Mandate
Conduct comprehensive forensic static and dynamic analysis across all files modified in Milestone 2:
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/core/fast_lob_engine.py`
- `trading_system/src/execution/smart_order_router.py`
- `trading_system/src/execution/oms_engine.py`
- `tests/test_phase6_portfolio_execution.py`

Verify:
1. NO HARDCODED TEST OUTPUTS: Check for conditional checks returning hardcoded values for specific test inputs, symbols, or mocks.
2. NO DUMMY OR FACADE IMPLEMENTATIONS: Confirm that mathematical operations (Softmax, GPD tail index, co-moments, Euler CCVaR, Bivariate Hawkes, L3 depth decay, logistic hazard) are genuinely computed.
3. NO SHORT-CIRCUITED GATES: Confirm that safety gates and constraints are genuinely evaluated and enforced.
4. RUNTIME VERIFICATION: Run the test suites directly and trace execution paths.
5. Deliver binary verdict: CLEAN or INTEGRITY VIOLATION in `handoff.md`.

## 2026-09-04T15:30:24Z
You are auditor_m2_opt6 (Forensic Integrity Auditor for Milestone 2: F43 & F44).
Your working directory is: d:\Finance\code\stock\.agents\auditor_m2_opt6
Parent Conversation ID: 50f1a6ac-db69-4f79-9fec-0df831df4b17

MANDATORY FIRST ACTIONS:
1. Initialize BRIEFING.md and progress.md in your working directory.
2. Read your DISPATCH.md: d:\Finance\code\stock\.agents\auditor_m2_opt6\DISPATCH.md
3. Read ORIGINAL_REQUEST.md: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
4. Read worker_m2_opt6_gen2 handoff: d:\Finance\code\stock\.agents\worker_m2_opt6_gen2\handoff.md
5. Read explorer_m1_2 handoff: d:\Finance\code\stock\.agents\explorer_m1_2\handoff.md
6. Read explorer_m1_3 handoff: d:\Finance\code\stock\.agents\explorer_m1_3\handoff.md

AUDIT MANDATE:
Perform a strict, independent forensic integrity audit on all Milestone 2 deliverables:
- Source files: `trading_system/src/risk/unified_portfolio_allocator.py`, `trading_system/src/core/fast_lob_engine.py`, `trading_system/src/execution/smart_order_router.py`, `trading_system/src/execution/oms_engine.py`.
- Test files: `tests/test_phase6_portfolio_execution.py`.

CHECK FOR INTEGRITY VIOLATIONS:
1. Static analysis: Check for any conditional statements returning hardcoded values matching test assertions (e.g. `if symbol == 'UP_CONVEX': return 1.6`).
2. Facade detection: Verify that mathematical functions (log-odds, Softmax, Euler CCVaR, Bivariate Hawkes, L3 depth decay, queue tracking, Leland buffer) execute genuine algorithms and do not bypass calculations.
3. Runtime tracing: Run pytest and confirm tests pass by executing production code.
4. Deliver binary verdict: CLEAN or INTEGRITY VIOLATION in `handoff.md`.
- Send message to parent when done.
