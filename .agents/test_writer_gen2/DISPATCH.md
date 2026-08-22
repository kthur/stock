## 2026-08-21T21:24:15Z
You are test_writer_gen2 (E2E & Regression Test Suite Lead for V6-01 ~ V6-35).
Your working directory is: d:\Finance\code\stock\.agents\test_writer_gen2\

Mandatory inputs to read before starting:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
2. d:\Finance\code\stock\system_improvement_report_v6.md (Sections 1 through 6 for V6-01 ~ V6-35)
3. d:\Finance\code\stock\AGENTS.md
4. d:\Finance\code\stock\.agents\explorer_1\analysis.md
5. d:\Finance\code\stock\.agents\explorer_2\analysis.md
6. d:\Finance\code\stock\.agents\explorer_3\analysis.md

Your Task:
1. Construct comprehensive test suites for all 35 defects/enhancements (V6-01 ~ V6-35) across the 4 systematic tiers:
   - Tier 1: Direct feature tests for V6-01 through V6-35
   - Tier 2: Boundary value and corner cases (e.g., single symbol N=1, extreme macro moves, currency conversions KRW/USD, full liquidations w_targ=0, empty models, GPD shape bounds, etc.)
   - Tier 3: Cross-feature interaction tests (e.g., Leland buffer with HRP, 2D regime with ML decay filter, OMS currency conversion with Almgren-Chriss & Gate 7)
   - Tier 4: End-to-end multi-market realistic workflow scenarios
2. Write tests under `tests/` (e.g. `tests/test_v6_improvements.py`).
3. Run the tests using `.venv\Scripts\python.exe -m pytest tests/test_v6_improvements.py -q`.
4. When all tests are ready, create `d:\Finance\code\stock\TEST_READY.md` containing runner command and test inventory checklist.
5. Write your report to `d:\Finance\code\stock\.agents\test_writer_gen2\handoff.md`.
6. Send a completion message back.
