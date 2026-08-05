## 2026-08-05T01:47:49Z

You are Worker 2 (Automated Test & Artifact Verification Specialist) for the Stock Trading System Deep Audit.

Working directory: `d:\Finance\code\stock\.agents\worker_m3_1`
Original request file: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`

Your task:
Execute automated test suite verification and GHA artifact verification on `d:\Finance\code\stock`.

Task details:
1. **Pytest Test Suite Execution**:
   - Run `.venv\Scripts\python.exe -m pytest tests/ -v` from the project root (`d:\Finance\code\stock`).
   - Capture full test execution logs, total test count, passed, failed, skipped.
   - Verify that 100% of tests pass with 0 failures.

2. **GHA Artifact Verifier Execution**:
   - Read `d:\Finance\code\stock\.agents\skills\gha-artifact-verifier\SKILL.md` using `view_file`.
   - Run `.venv\Scripts\python.exe trading_system/scripts/verify_gha_artifacts.py` (or the appropriate script path) against `gh-pages/index.html` and strategy outputs.
   - Assert non-zero prediction data rendering across all strategy panels on `gh-pages/index.html` (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).

3. **Output & Handoff**:
   - Document all command line strings, exact execution outputs, test pass counts, and artifact verification results in `d:\Finance\code\stock\.agents\worker_m3_1\verification_results.md`.
   - Write your complete handoff report to `d:\Finance\code\stock\.agents\worker_m3_1\handoff.md`.
   - Send a completion message back to parent summarizing test and verifier outcomes.
