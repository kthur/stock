# BRIEFING — 2026-07-29T14:40:00Z

## Mission
Perform independent quality and adversarial review of Worker 3's implementation for Requirement R2 (Backtest, Risk Management, Position Sizing, Portfolio Risk) for Milestone 3.

## 🔒 My Identity
- Archetype: reviewer / critic
- Roles: reviewer, critic
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m3
- Original parent: b0c9cad7-b1c0-41d5-bc8e-0a8d236ebdcb
- Milestone: Milestone 3 (Requirement R2)
- Instance: 4 of 4

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code.
- Report findings and integrity violations explicitly.
- Run tests via `.venv\Scripts\python.exe -m pytest ...`
- Write handoff report to `d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m3\handoff.md`.
- Send summary message back to parent orchestrator (`b0c9cad7-b1c0-41d5-bc8e-0a8d236ebdcb`).

## Current Parent
- Conversation ID: b0c9cad7-b1c0-41d5-bc8e-0a8d236ebdcb
- Updated: 2026-07-29T14:40:00Z

## Review Scope
- **Files to review**:
  - `trading_system/src/analysis/backtest.py`
  - `src/risk/risk_manager.py` (and `trading_system/src/risk/risk_manager.py` if present)
  - `src/risk/position_sizing.py` (and `trading_system/src/risk/position_sizing.py` if present)
  - `src/risk/portfolio_risk.py` (and `trading_system/src/risk/portfolio_risk.py` if present)
  - `trading_system/tests/test_backtest.py`
  - `trading_system/tests/test_risk_manager.py`
- **Review criteria**:
  - Correctness of Sharpe ratio, MDD, win rate, profit factor, net returns after transaction costs (KONEX 1.30%, KOSDAQ 1.00%, KOSPI 0.85%, SP500 0.60%).
  - Multi-factor 14-strategy backtest support via `run_ensemble_backtest`.
  - Liquidity screening (`screen_liquidity`), Kelly position sizing, ATR trailing stops, 30% sector caps, KIS safety limits.
  - Integrity violation checks (hardcoded results, facades, shortcuts, self-certifying output).
  - Passing pytest tests.

## Review Checklist
- **Items reviewed**: Pending initial file inspection
- **Verdict**: Pending
- **Unverified claims**: All worker claims

## Attack Surface
- **Hypotheses tested**: TBD
- **Vulnerabilities found**: TBD
- **Untested angles**: TBD

## Key Decisions Made
- Initializing briefing and starting code inspection.

## Artifact Index
- `d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m3\ORIGINAL_REQUEST.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m3\BRIEFING.md`
