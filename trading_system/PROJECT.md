# Project: Phase 4 Trading System Upgrade

## Architecture
- **src/analysis/backtest.py**: `BacktestEngine` with parameter optimization grid search.
- **src/core/strategy_engine.py**: `HybridStrategyEngine` with dynamic weight adaptation and market regime detection.
- **trading_system.py**: Core `StockTradingSystem` handling real-time loop and trailing stop logic.
- **src/analysis/screener.py**: `StockScreener` filtering assets based on configuration parameters.
- **src/web/dashboard.py**: Dash-based interactive web dashboard with tabs for performance comparison, real-time position/P&L status, and backtest viewer.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | E2E Test Suite | Create comprehensive E2E test cases (Tiers 1-4) in `tests/phase4/e2e/` and publish `TEST_READY.md`. | None | DONE |
| 2 | Param Optimization & Regime Detection | Implement R1 grid search optimization and JSON caching, and R2 market regime detection with dynamic weight switching in `HybridStrategyEngine`. | None | DONE |
| 3 | Trailing Stop & Screener | Implement R3 trailing stop logic in `StockTradingSystem` and R4 `StockScreener` with criteria-based filtering. | None | IN_PROGRESS |
| 4 | Dash Web UI | Re-implement `src/web/dashboard.py` in Dash with 3 required tabs, server exposure, and interactive backtest charting. | None | PLANNED |
| 5 | E2E Verification & Hardening | Run E2E test suite (Tiers 1-4), add Tier 5 white-box adversarial test cases, and pass Forensic Audit. | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### R1. Parameter Optimization
- `BacktestEngine.optimize_parameters(symbol: str, price_bars: List[PriceBar], param_ranges: Dict, strategy_name: str = "MA") -> Dict`: Runs parameter search, updates `data/optimized_params.json` and returns results.

### R2. Market Regime & Strategy Switching
- `HybridStrategyEngine.detect_regime(price_bars: List[Any]) -> Literal["bull", "bear", "sideways"]`: Identifies market regime.
- `HybridStrategyEngine` adapts weights and `sell_threshold` based on regime.

### R3. Trailing Stop
- `StockTradingSystem._check_trailing_stop(symbol: str, current_price: float, atr: float = 2.0) -> Optional[TradeSignal]`: Evaluates trailing stop triggers.

### R4. Stock Screener
- `StockScreener.screen(universe: List[str]) -> List[str]`: Filters symbols based on configuration.

### R5. Dash Dashboard
- `app = dash.Dash(__name__, ...)`: Dash app instance.
- `server = app.server`: Exposing the underlying Flask server.

## Code Layout
- `src/analysis/backtest.py`: Param optimization.
- `src/core/strategy_engine.py`: Regime-based strategy switcher.
- `trading_system.py`: Trailing stop implementation.
- `src/analysis/screener.py`: `StockScreener` class.
- `src/web/dashboard.py`: Dash UI application.
- `run_dashboard.py`: Dashboard launcher.
- `tests/phase4/`: Target verification and E2E tests.
