# Scope: Implementation Track

## Architecture
- **src/analysis/backtest.py**: Add `optimize_parameters`.
- **src/core/strategy_engine.py**: Add `detect_regime` and dynamic weight adjustment.
- **trading_system.py**: Add `_check_trailing_stop` and high-watermark tracking.
- **src/analysis/screener.py**: Create `StockScreener`.
- **src/web/dashboard.py**: Dash dashboard.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Requirements R1 & R2 | Implement parameter optimization (R1) and market regime detection & strategy weight switching (R2). | None | PLANNED |
| 2 | Requirements R3 & R4 | Implement trailing stop (R3) and StockScreener (R4) with configuration loading. | None | PLANNED |
| 3 | Requirement R5 | Re-implement dashboard in Dash (R5) with the 3 tabs and interactive curves. | None | PLANNED |
| 4 | Phase 1 Integration | Verify that all local tests and implementation files pass the initial build/checks. | M1, M2, M3 | PLANNED |

## Interface Contracts
- Must pass the E2E tests written in `tests/phase4/e2e/test_e2e.py` once `TEST_READY.md` is published.
