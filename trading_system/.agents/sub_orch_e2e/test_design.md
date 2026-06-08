# E2E Test Suite Design: Phase 4 Trading System

We design a comprehensive, opaque-box, requirement-driven E2E test suite consisting of 60 test cases structured across 4 Tiers.

## Feature Map (Phase 4 Requirements)
- **F1 (R1)**: Parameter Optimization & caching in `data/optimized_params.json`
- **F2 (R2)**: Market Regime & Strategy Switching in `HybridStrategyEngine`
- **F3 (R3)**: Trailing Stop in `StockTradingSystem` (or `TradingSystem`)
- **F4 (R4)**: Stock Screener (`StockScreener` filtering user universe)
- **F5 (R5)**: Dash Dashboard with 3 tabs and Flask server exposure (`app.server`)

---

## Tier 1: Feature Coverage (Happy Path, 25 tests, 5 per feature)

### F1: Parameter Optimization (R1)
1. `test_r1_optimize_parameters_happy_path`: Calling `BacktestEngine.optimize_parameters` with mock bars and param ranges returns a dict containing `best_params`, `best_result`, and `best_return`.
2. `test_r1_json_saving_happy_path`: Running parameter optimization saves the results to `data/optimized_params.json` with the required keys (`best_params`, `best_return`, `sharpe_ratio`).
3. `test_r1_best_params_structure`: Verifies that the saved `best_params` inside the JSON is a dictionary containing the strategy's optimized parameters (e.g. `short_window`, `long_window`).
4. `test_r1_caching_happy_path`: Calling the optimizer a second time with the same inputs retrieves the cached result from `data/optimized_params.json` without re-running the grid search.
5. `test_r1_different_strategy_happy_path`: Optimizes parameters for a non-default strategy (e.g. "RSI" or "MACD") and saves to JSON successfully.

### F2: Market Regime & Strategy Switching (R2)
6. `test_r2_detect_regime_bull`: `HybridStrategyEngine.detect_regime(price_bars)` returns `"bull"` when market indicators (EMA200, ATR, ROC) are positive/expanding.
7. `test_r2_detect_regime_bear`: `HybridStrategyEngine.detect_regime(price_bars)` returns `"bear"` when indicators show a downward trend.
8. `test_r2_detect_regime_sideways`: `HybridStrategyEngine.detect_regime(price_bars)` returns `"sideways"` when indicators show low momentum/flat trend.
9. `test_r2_bull_weight_adaptation`: In a `"bull"` market regime, `HybridStrategyEngine` increases the weight of the technical strategy (`technical_weight`) relative to its default value.
10. `test_r2_bear_sell_threshold`: In a `"bear"` market regime, `HybridStrategyEngine` decreases the `sell_threshold` below its default value of 0.45 to trigger sell orders more conservatively/sensitively.

### F3: Trailing Stop (R3)
11. `test_r3_no_stop_loss_trigger`: A mock position with entry price 100, ATR=2, and highest price (watermark) 115 does not trigger a trailing stop when the current price is 110 (drawdown 5 < 2*ATR=4).
12. `test_r3_stop_loss_trigger`: A mock position with entry price 100, ATR=2, and highest price 115 triggers a sell signal when the price drops to 110 - 4 = 106 or lower.
13. `test_r3_high_watermark_update`: As the current price rises (e.g. 100 -> 110 -> 120), the high watermark stored in the trading system updates to match the highest observed price (120).
14. `test_r3_multiple_symbols_stop`: The trading system tracks high watermarks and checks trailing stops independently for multiple active positions.
15. `test_r3_stop_loss_after_rebound`: A stock rises (watermark goes to 110), drops slightly to 108 (no trigger), rises to 120 (watermark becomes 120), then drops to 115 (trigger at 120 - 4 = 116).

### F4: Stock Screener (R4)
16. `test_r4_screener_dummy_conditions`: Calling `StockScreener.screen` with dummy/relaxed conditions (minimum volume 0, RSI range 0-100) returns the entire input universe.
17. `test_r4_screener_config_load`: `StockScreener` initializes and loads screening criteria from `screener_config.json` or `risk_config.json`.
18. `test_r4_screener_rsi_filter`: Screener filters out stocks whose RSI is outside the configured bounds.
19. `test_r4_screener_volume_filter`: Screener filters out stocks with average volume below the minimum trading volume threshold.
20. `test_r4_screener_52week_filter`: Screener filters stocks based on their distance from their 52-week high.

### F5: Dash Dashboard (R5)
21. `test_r5_dashboard_server_instance`: The web dashboard module exposes a Flask server instance via `app.server`.
22. `test_r5_dashboard_layout_tabs`: The Dash app layout contains tab/section components representing the 3 required tabs: Strategy Performance Comparison, Real-time position/P&L status, and Backtest Result Viewer.
23. `test_r5_dashboard_performance_tab_components`: Verifies the strategy performance comparison tab contains a Graph component for displaying cumulative returns across strategies (MA, RSI, MACD, Ensemble, Bollinger).
24. `test_r5_dashboard_pnl_tab_components`: Verifies the real-time position/P&L status tab contains a DataTable or HTML Table for showing holdings, average prices, and valuation.
25. `test_r5_dashboard_backtest_viewer_components`: Verifies the backtest result viewer contains dropdowns for selecting symbol/strategy and an interactive chart for displaying the equity curve.

---

## Tier 2: Boundary & Corner Cases (25 tests, 5 per feature)

### F1: Parameter Optimization
26. `test_r1_empty_price_bars`: `BacktestEngine.optimize_parameters` raises `ValueError` or returns a graceful error dict when input price bars list is empty.
27. `test_r1_single_price_bar`: Optimization is requested with only one price bar, returning a fallback or handling it without crashing.
28. `test_r1_invalid_param_ranges`: Optimization is called with empty or invalid parameter lists (e.g. empty lists), returning default parameters instead of failing.
29. `test_r1_missing_json_directory`: Optimization successfully creates the parent `data/` directory and saves `optimized_params.json` even if the directory didn't exist initially.
30. `test_r1_extreme_parameters`: Optimization with extremely large or negative parameter values is handled without division by zero or domain errors.

### F2: Market Regime & Strategy Switching
31. `test_r2_detect_regime_insufficient_bars`: `detect_regime` is called with fewer bars than the EMA200 period, falling back gracefully to `"sideways"`.
32. `test_r2_detect_regime_constant_price`: `detect_regime` handles a flat market where price never changes (ROC=0, ATR=0) without producing division-by-zero errors.
33. `test_r2_detect_regime_missing_fields`: Price bars missing required fields (e.g. high/low for ATR or close for EMA) are skipped or raise a clear exception.
34. `test_r2_weight_adaptation_bounds`: Ensures that after weight adaptation in response to regime changes, strategy weights are bounded between [0.0, 1.0] and sum to exactly 1.0.
35. `test_r2_extreme_regime_transition`: The system transitions instantly from bull to bear, and weights switch immediately and correctly according to regime rules.

### F3: Trailing Stop
36. `test_r3_atr_zero`: Handles trailing stop evaluation when ATR is 0 (does not divide by zero, defaults to no stop or fixed stop).
37. `test_r3_price_zero`: Check trailing stop when current price drops to 0 or becomes negative, triggering the stop immediately.
38. `test_r3_no_active_position`: Checking trailing stop for a symbol with no active position in the portfolio returns `None` without errors.
39. `test_r3_high_watermark_lower_than_entry`: If the price immediately falls upon entry, the high watermark is set to the entry price.
40. `test_r3_atr_extreme_large`: An extremely high ATR value makes the stop-loss boundary mathematically unreachable, preventing premature triggers during high volatility.

### F4: Stock Screener
41. `test_r4_screener_empty_universe`: Screening an empty list of symbols returns an empty list without making API requests or crashing.
42. `test_r4_screener_missing_config`: `StockScreener` defaults to safe fallback conditions if the config file is missing.
43. `test_r4_screener_malformed_config`: Malformed config JSON or negative thresholds in configuration are handled with validation errors or safe fallbacks.
44. `test_r4_screener_yfinance_failure`: If yfinance returns empty DataFrames for a symbol, the screener skips it without crashing the entire scan.
45. `test_r4_screener_duplicate_symbols`: The input universe contains duplicate symbols; the screener filters out duplicates and returns only unique symbols.

### F5: Dash Dashboard
46. `test_r5_dashboard_callback_missing_inputs`: Dashboard callback for updating backtest charts handles `None` or empty selections gracefully without raising dashboard exceptions.
47. `test_r5_dashboard_empty_positions_table`: The position/P&L status table displays an empty row or "No active positions" when there are no holdings.
48. `test_r5_dashboard_missing_performance_data`: The performance tab handles strategies with missing historical records without throwing JavaScript/React rendering errors.
49. `test_r5_dashboard_server_port_collision`: The web server configuration allows custom port binding to handle potential port conflicts.
50. `test_r5_dashboard_concurrent_connections`: Dashboard layout and callback states remain stateless, preventing state leaks between multiple concurrent user connections.

---

## Tier 3: Cross-Feature Combination Cases (5 tests)
51. `test_r1_r2_combination`: Parameter optimization (R1) runs and caches parameters, and when the market regime changes (R2), we verify that the regime-based weight adjustments interact correctly with the active optimized parameters.
52. `test_r2_r3_combination`: Market regime transitions to Bear, lowering the `sell_threshold` (R2), and we verify how this interacts with the ATR-based trailing stop (R3) to ensure positions are exited safely.
53. `test_r3_r4_combination`: The screener filters a list of symbols (R4), which are then loaded into the trading system. Once positions are opened, their trailing stops (R3) are tracked and checked.
54. `test_r4_r1_combination`: The screener selects a subset of symbols matching volume/RSI criteria (R4), and parameter optimization (R1) is run specifically on the screened symbols.
55. `test_r1_r5_combination`: Parameter optimization (R1) results are loaded and displayed in the Dash Dashboard's backtest viewer (R5) using interactive callbacks.

---

## Tier 4: Real-World Workloads (5 tests)
56. `test_tier4_full_regime_cycle_workload`: Simulates a stock going through a full market cycle: Bull regime (high technical weight) -> Bear regime (low sell_threshold) -> Sideways, and checks system weights and trading signals at each step.
57. `test_tier4_screener_to_portfolio_optimization`: End-to-end workflow where a user screens a stock universe (R4) -> runs grid search optimization on the top-ranked stock (R1) -> starts trading with the optimized strategy -> monitors the ATR trailing stop (R3).
58. `test_tier4_multi_strategy_dashboard_sync`: Runs backtests for multiple strategies in parallel, saves results to cached JSON files, and loads them into the Dash dashboard to verify chart updates and callback response.
59. `test_tier4_volatile_market_trailing_stop_onslaught`: Simulates a highly volatile market data feed with rapid changes in ATR and prices, verifying that trailing stop logic does not trigger prematurely on spikes but triggers correctly on real trends.
60. `test_tier4_end_to_end_trading_session`: Sets up the trading system with R1-R5 components active, runs a simulated trading day with multiple ticks, and verifies that screening, parameter caching, regime adaptation, trailing stops, and dashboard states are fully synchronized.
