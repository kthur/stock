# BRIEFING — 2026-07-25T01:22:15Z

## Mission
Implement Requirement 3: KIS Automated Trading Safety & ATR Trailing Stop.

## 🔒 My Identity
- Archetype: implementer, qa, specialist
- Roles: implementer, qa, specialist
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m4
- Original parent: 7743c0d7-2762-4e7d-bbff-54fcbb2e8514
- Milestone: Requirement 3

## 🔒 Key Constraints
- Pure implementation, no shortcuts or cheats.
- Sector Risk Cap: max exposure per sector across RiskManager, PortfolioAllocator, TradingAgent/trading_system.py.
- ATR Dynamic Trailing Stop & Order Sync: delegate evaluation to RiskManager.check_trailing_stop_signal(), sync trigger prices with OrderManagementSystem.
- KIS Broker Execution & Safety Guards: real order cancellation (cancel_order) & order status inquiry (get_order_status) in KoreaInvestmentBroker / KoreaInvestmentConnector, limit price sanity bounds (±3% deviation from market price), single order max value cap (50,000,000 KRW).
- Comprehensive unit tests in `trading_system/tests/test_kis_safety_and_atr.py`. Run tests using pytest.

## Current Parent
- Conversation ID: 7743c0d7-2762-4e7d-bbff-54fcbb2e8514
- Updated: 2026-07-25T01:22:15Z

## Task Summary
- **What to build**: KIS Automated Trading Safety & ATR Trailing Stop enhancements
- **Success criteria**: All 4 sub-requirements implemented, unit tests in test_kis_safety_and_atr.py pass cleanly.

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: None

## Quality Status
- **Build/test result**: Untested
- **Lint status**: OK
- **Tests added/modified**: Pending

## Loaded Skills
- None loaded yet

## Key Decisions Made
- Initializing workspace and starting investigation.

## Artifact Index
- `.agents/teamwork_preview_worker_m4/ORIGINAL_REQUEST.md` — Original user request
