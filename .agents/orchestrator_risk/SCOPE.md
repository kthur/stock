# Scope: Risk Management and Portfolio Construction Upgrades

## Architecture
- `src/risk/risk_manager.py`: Handles trade-level risk, stops, and overall portfolio risk limit controls.
- `src/strategy/asset_allocation.py` and `src/core/strategy_engine.py`: Handles asset allocation and target position sizing.
- Comparative Backtest Framework: Evaluates baseline vs. enhanced configurations on S&P 500 and KRX universes.
- Test Suite: Unit tests verifying the enhancements in `tests/test_risk_enhancements.py`.
- Reports: Expert review report generated at `reports/expert_review_report.md`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Exploration & Design | Audit existing risk rules & design position sizing/stop mathematical formulas | None | DONE |
| 2 | Implementation | Integrate Volatility Sizing (ATR-based) and Adaptive Stops into risk/strategy modules | M1 | DONE |
| 3 | Backtesting & Reporting | Run comparative backtests on S&P 500 / KRX, generate expert report `reports/expert_review_report.md` | M2 | DONE |
| 4 | Verification & Testing | Implement unit tests in `tests/test_risk_enhancements.py`, verify full test suite passes | M3 | DONE |
| 5 | Forensic Audit & Handoff | Forensic integrity audit, final gate verification, report victory to Sentinel | M4 | DONE |

## Interface Contracts
### Volatility Sizing & Allocation
- Sizing must adjust based on ATR/historical volatility of the symbol.
- Stop-Loss/Take-Profit: Trailing stops must be calculated using ATR multiplier (e.g., StopLoss = Close - k * ATR).
- Backtesting: Compare baseline (fixed size / fixed stop) vs enhanced (dynamic size / adaptive stop).
