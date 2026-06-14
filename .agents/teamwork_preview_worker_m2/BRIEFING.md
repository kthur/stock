# BRIEFING — 2026-06-13T04:52:36Z

## Mission
Implement risk management and portfolio construction upgrades (Milestone 2) for stop loss tightening, Adaptive ATR stop calculation, annualized volatility-based Kelly Criterion scaling, and fixed risk sizing scaling based on crisis levels.

## 🔒 My Identity
- Archetype: teamwork_preview_worker_m2
- Roles: implementer, qa, specialist
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\
- Original parent: d23ffd42-28b4-4f15-a6ee-33b72c3197cf
- Milestone: Daily Post-Market Stock Scoring Backend

## 🔒 Key Constraints
- CODE_ONLY network mode: No external internet access.
- Do not cheat: All implementations must be genuine, no hardcoding of expected outputs/results.
- Do not use run_command to execute HTTP clients targeting external URLs.

## Current Parent
- Conversation ID: 7635347b-53a9-4ba1-9cb3-cafe65efe2dc
- Updated: 2026-06-13T04:52:36Z

## Task Summary
- **What to build**:
  1. In `trading_system/src/risk/risk_manager.py`:
     - Implement `check_trailing_stop_signal` using Adaptive ATR, crisis stop multiplier, and portfolio drawdown-based stop tightening.
     - Update `calculate_position_sizing` to accept `atr`, scale Kelly Criterion percent by annualized volatility, and scale Fixed Risk unit percent by active crisis levels.
  2. In `trading_system/trading_system.py`:
     - Update `_compute_position_size` signature and calls to pass `atr`.
     - Refactor `_check_trailing_stop` to delegate evaluation to `check_trailing_stop_signal`.
- **Success criteria**:
  - `pytest tests/test_risk_manager.py` runs and passes.
  - Implementations are genuine (no hardcoding).
- **Interface contracts**:
  - `check_trailing_stop_signal(self, symbol: str, current_price: float, highest_price: float, atr: float, regime: str = "weak_bull", adx: float = 20.0) -> bool`
  - `calculate_position_sizing(self, symbol: str, entry_price: float, stop_loss_price: float, win_rate: float = 0.0, win_loss_ratio: float = 0.0, vix: float = 20.0, atr: float = 0.0) -> int`
- **Code layout**:
  - `trading_system/src/risk/risk_manager.py`
  - `trading_system/trading_system.py`

## Key Decisions Made
- Integrated crisis detector level and portfolio drawdown indicators directly into trailing stop logic for real-time risk mitigation.
- Added comprehensive unit tests targeting all the newly introduced branches in `calculate_position_sizing` and `check_trailing_stop_signal`.

## Change Tracker
- **Files modified**:
  - `trading_system/src/risk/risk_manager.py`: Added `check_trailing_stop_signal` method, updated `calculate_position_sizing` method to support annualized asset volatility scaling on Kelly sizing and crisis level scaling on Fixed Risk unit pct.
  - `trading_system/trading_system.py`: Updated `_compute_position_size` signature and calls, refactored `_check_trailing_stop` to delegate stop loss evaluations to the risk manager.
  - `trading_system/tests/test_risk_manager.py`: Added 7 new unit tests in `TestRiskManagerUpgrades` class.
- **Build status**: Pass (all tests pass)
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pass (40 tests passed in `test_risk_manager.py`, 55 in `test_system.py`, 3 in `test_portfolio_risk.py`)
- **Lint status**: Clean
- **Tests added/modified**: Added `TestRiskManagerUpgrades` with 7 test cases.

## Loaded Skills
- None

## Artifact Index
- d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\ORIGINAL_REQUEST.md — The current user request
- d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\BRIEFING.md — This briefing file
- d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\progress.md — Progress tracking heartbeat
- d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\changes.md — Change log
- d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\handoff.md — Handoff report
