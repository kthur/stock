# Project: Automated Stock Scoring, Ranking, and Backtest Dashboard

## Architecture
The system consists of:
- **Core Engine & Config**: `TradingConfig` in `src/config.py` and `trading_system.py`.
- **Backend Analytics**:
  - Daily post-market scoring script that queries technical, AI, and NLP sentiment indicators and computes a composite score.
  - Data layer / Database: Store composite scores, component scores, and ranks in SQLite database (`market_indicators.db` or a new table in the existing database).
  - Backtest engine: Run historical backtests, calculate annualized expected returns, Sharpe Ratio, Win Rate, and Max Drawdown.
- **Web Dashboard**: Dash application in `src/web/dashboard.py` (and `trading_system/run_dashboard.py`).
  - "Post-Market Rankings" Tab: Table of top 100 stocks.
  - "Strategy Performance Analysis" Section: Displays Sharpe, Win Rate, Annualized Return, MDD, and interactive equity curve.
- **Integrity & Compatibility Layer**:
  - PyTorch DLL fix / bypass for CPU environments.
  - Verification & testing via pytest suite.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | PyTorch & Config Fixes | Resolve PyTorch WinError 1114 DLL load crash and fix KIS mock config tests. | None | DONE |
| 2 | Post-Market Stock Scoring | Implement daily composite scoring engine & database persistence. | M1 | IN_PROGRESS |
| 3 | Dashboard Integration | Add "Post-Market Rankings" and "Strategy Performance Analysis" dashboard components. | M2 | PLANNED |
| 4 | E2E Testing Track | Design and implement comprehensive opaque-box E2E test suite, outputting TEST_READY.md. | None | PLANNED |
| 5 | E2E Verification & Audit | Integrate E2E tests, run challenger testing, and perform Forensic Integrity Audit. | M3, M4 | PLANNED |

## Interface Contracts
### Daily Scoring Engine ↔ Database
- Function: `run_daily_scoring()` or daily script execution.
- Outputs: Table `daily_stock_rankings` in SQLite database with fields: `date`, `symbol`, `name`, `composite_score`, `technical_score`, `ai_score`, `sentiment_score`, `rank`.

### Strategy Performance Analysis ↔ Dashboard
- Function: `get_backtest_performance()` or backtest result dictionary.
- Output keys: `annualized_return` (float), `sharpe_ratio` (float), `win_rate` (float), `max_drawdown` (float), `equity_curve` (List[Dict] or pd.Series).

## Code Layout
- Main config: `trading_system/src/config.py`
- Main UI/Dashboard: `trading_system/src/web/dashboard.py`
- Test suite: `trading_system/tests/`
- DB path: `market_indicators.db`
