## 2026-08-21T10:20:35Z
You are Worker M4 for the Stock Trading System.
Your working directory is: D:\Finance\code\stock\.agents\teamwork_preview_worker_m4\

Read:
1. D:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
2. D:\Finance\code\stock\system_improvement_report_v5.md (Focus on Domain 4: V5-24 ~ V5-25)
3. D:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md

Your exclusive write boundaries:
- `trading_system/src/execution/oms_engine.py`
- `trading_system/src/execution/slippage_feedback.py`
Do NOT modify files outside your boundary.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks to implement:
- **V5-24**: In `oms_engine.py:363-365` and `slippage_feedback.py:56`, fix `calculate_realized_slippage()` signature and `SlippageMetrics` dataclass unpacking so that closed-loop slippage multiplier feedback functions without `TypeError`.
- **V5-25**: In `oms_engine.py:493-494`, replace hardcoded `10000.0` KRW hedge target price with actual real-time current price of the inverse ETF (`current_price` from market data / quote), ensuring exact 1:1 dynamic hedge sizing.

Run relevant tests using `.venv\Scripts\python.exe -m pytest tests/test_execution_oms.py tests/test_slippage_feedback.py -v`.
Write your full report to `D:\Finance\code\stock\.agents\teamwork_preview_worker_m4\handoff.md`.
Send message to parent when done.
