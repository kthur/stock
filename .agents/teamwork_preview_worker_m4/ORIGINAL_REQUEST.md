## 2026-07-25T01:22:15Z
<USER_REQUEST>
You are Worker 4 (`teamwork_preview_worker`) working in `.agents/teamwork_preview_worker_m4/`.
Your objective is to implement Requirement 3 (R3: KIS Automated Trading Safety & ATR Trailing Stop).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Create workspace directory `.agents/teamwork_preview_worker_m4/` if it doesn't exist.
2. Sector Risk Cap: Implement Sector Risk Cap enforcement (e.g. max 30% total exposure per sector) across `RiskManager`, `PortfolioAllocator`, and `TradingAgent` / `trading_system.py`.
3. ATR Dynamic Trailing Stop & Order Sync:
   - Refactor trailing stop evaluation in `trading_system/trading_system.py` to delegate to `RiskManager.check_trailing_stop_signal()`.
   - Synchronize dynamic ATR trailing stop trigger prices with `OrderManagementSystem`.
4. KIS Broker Execution & Safety Guards:
   - Implement real order cancellation (`cancel_order`) and order status inquiry (`get_order_status`) methods in `KoreaInvestmentBroker` / `KoreaInvestmentConnector`.
   - Add pre-order execution safety guards: limit price sanity bounds (e.g. max ±3% deviation from market price) and single order max value cap (e.g. max 50,000,000 KRW per order).
5. Create comprehensive unit tests in `trading_system/tests/test_kis_safety_and_atr.py` and run `.venv/bin/python -m pytest trading_system/tests/ -v`. Fix any failures.
6. Write `.agents/teamwork_preview_worker_m4/changes.md` and `handoff.md`, and send a message to parent (Recipient: "parent") when completed.
</USER_REQUEST>
