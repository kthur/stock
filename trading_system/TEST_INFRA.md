# E2E Test Infra: Phase 4 Trading System

## Test Philosophy
- **Opaque-box, requirement-driven**: Tests are constructed based on functional and boundary specifications, ensuring correctness without depending on implementation details.
- **Methodology**: Categorized into 4 Tiers (Happy Path Feature Coverage, Boundary & Corner Cases, Cross-Feature Combinations, and Real-World Workloads).
- **Execution isolation**: Mocking external services (specifically `yfinance`) to avoid HTTP calls, prevent timeouts, and guarantee deterministic test execution under strict network constraints (`CODE_ONLY` mode).

## Feature Inventory (Phase 4)
| Feature | Source Requirement | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **F1**: Parameter Optimization & Caching | R1 (`BacktestEngine`, caching in `data/optimized_params.json`) | 5 | 5 | ✓ | ✓ |
| **F2**: Market Regime & Strategy Switching | R2 (`HybridStrategyEngine` bull/bear/sideways weights/thresholds) | 5 | 5 | ✓ | ✓ |
| **F3**: Trailing Stop | R3 (ATR-based trailing stop updates and signals) | 5 | 5 | ✓ | ✓ |
| **F4**: Stock Screener | R4 (`StockScreener` filtering universe via config/data) | 5 | 5 | ✓ | ✓ |
| **F5**: Dash Dashboard | R5 (Dash web app layout, 3 tabs, Flask `app.server` exposure) | 5 | 5 | ✓ | ✓ |

## Test Layout
- Test Suite Path: `tests/phase4/e2e/test_e2e.py`
- Test Configs: `screener_config.json`, `risk_config.json`
- Cached Params: `data/optimized_params.json`

---

## Detailed Test Specification (60 Test Cases)

### Tier 1: Feature Coverage (Happy Path - 25 Tests)
#### F1: Parameter Optimization (R1)
1. `test_r1_optimize_parameters_happy_path`: Calling `BacktestEngine.optimize_parameters` returns a dict with `best_params`, `best_result`, and `best_return`.
2. `test_r1_json_saving_happy_path`: Running parameter optimization saves results to `data/optimized_params.json` with required keys.
3. `test_r1_best_params_structure`: Verifies saved `best_params` contains expected strategy configuration parameters.
4. `test_r1_caching_happy_path`: Verifies second optimization call with same inputs retrieves cached result without re-running.
5. `test_r1_different_strategy_happy_path`: Verifies optimizing a non-default strategy (e.g. RSI) saves to JSON successfully.

#### F2: Market Regime & Strategy Switching (R2)
6. `test_r2_detect_regime_bull`: `detect_regime` returns `"bull"` when indicators (EMA, ATR, ROC) are positive/expanding.
7. `test_r2_detect_regime_bear`: `detect_regime` returns `"bear"` when indicators show a downward trend.
8. `test_r2_detect_regime_sideways`: `detect_regime` returns `"sideways"` when indicators show low momentum/flat trend.
9. `test_r2_bull_weight_adaptation`: technical strategy weight increases relative to default in bull market.
10. `test_r2_bear_sell_threshold`: sell threshold decreases below default of 0.45 in bear market to trigger sell signals more conservatively.

#### F3: Trailing Stop (R3)
11. `test_r3_no_stop_loss_trigger`: Trailing stop not triggered if price drawdown is less than ATR-based threshold.
12. `test_r3_stop_loss_trigger`: Trailing stop triggers sell signal when price drawdown exceeds ATR-based threshold.
13. `test_r3_high_watermark_update`: High watermark updates correctly as prices rise.
14. `test_r3_multiple_symbols_stop`: Watermarks and trailing stops are tracked independently for multiple active positions.
15. `test_r3_stop_loss_after_rebound`: Stop loss triggers correctly after a rebound and subsequent drop.

#### F4: Stock Screener (R4)
16. `test_r4_screener_dummy_conditions`: Screener with relaxed criteria (min volume 0, RSI 0-100) returns the entire universe.
17. `test_r4_screener_config_load`: Screener initializes and loads criteria from config files.
18. `test_r4_screener_rsi_filter`: Screener filters out stocks with RSI outside bounds.
19. `test_r4_screener_volume_filter`: Screener filters out stocks with average volume below minimum threshold.
20. `test_r4_screener_52week_filter`: Screener filters stocks based on distance to 52-week high.

#### F5: Dash Dashboard (R5)
21. `test_r5_dashboard_server_instance`: Dashboard exposes a Flask server instance via `app.server`.
22. `test_r5_dashboard_layout_tabs`: Dashboard layout includes tabs for Strategy Performance, Real-time P&L, and Backtest Result Viewer.
23. `test_r5_dashboard_performance_tab_components`: Performance tab contains graphing components for cumulative returns comparison.
24. `test_r5_dashboard_pnl_tab_components`: Real-time position/P&L status tab contains a DataTable or HTML Table.
25. `test_r5_dashboard_backtest_viewer_components`: Backtest viewer contains selection dropdowns and interactive charts.

---

### Tier 2: Boundary & Corner Cases (25 Tests)
#### F1: Parameter Optimization
26. `test_r1_empty_price_bars`: `BacktestEngine.optimize_parameters` raises `ValueError` or returns graceful error dict on empty list.
27. `test_r1_single_price_bar`: Optimization handles a single price bar without crashing.
28. `test_r1_invalid_param_ranges`: Optimization handles empty or invalid parameter ranges by returning default configuration.
29. `test_r1_missing_json_directory`: Optimization successfully creates the parent `data/` directory and saves JSON if it did not exist.
30. `test_r1_extreme_parameters`: Handles extremely large or negative parameters without division by zero or errors.

#### F2: Market Regime & Strategy Switching
31. `test_r2_detect_regime_insufficient_bars`: `detect_regime` falls back gracefully to `"sideways"` if bars list length is less than indicator period.
32. `test_r2_detect_regime_constant_price`: Handles constant prices (zero volatility) without division by zero.
33. `test_r2_detect_regime_missing_fields`: Handles price bars missing high/low/close by skipping them or raising clean exceptions.
34. `test_r2_weight_adaptation_bounds`: Verifies weights are bounded between [0.0, 1.0] and sum to exactly 1.0.
35. `test_r2_extreme_regime_transition`: Immediate transition between bull and bear regimes adjusts weights immediately and correctly.

#### F3: Trailing Stop
36. `test_r3_atr_zero`: Handles trailing stop evaluation when ATR is 0 gracefully (no divide-by-zero, defaults to fixed or no stop).
37. `test_r3_price_zero`: Triggers trailing stop immediately if price drops to 0 or becomes negative.
38. `test_r3_no_active_position`: Checking trailing stop for symbols without active positions returns `None` without errors.
39. `test_r3_high_watermark_lower_than_entry`: Initializes high watermark to entry price if the price immediately falls.
40. `test_r3_atr_extreme_large`: High ATR values prevent premature triggers by making the stop boundary mathematically unreachable.

#### F4: Stock Screener
41. `test_r4_screener_empty_universe`: Screening an empty list of symbols returns empty list without crashes.
42. `test_r4_screener_missing_config`: Screener defaults to safe fallback configurations when config files are missing.
43. `test_r4_screener_malformed_config`: Handles malformed JSON config or negative thresholds with validation errors or safe fallbacks.
44. `test_r4_screener_yfinance_failure`: Screener skips symbols with empty yfinance responses instead of crashing.
45. `test_r4_screener_duplicate_symbols`: Screener deduplicates inputs and runs only on unique symbols.

#### F5: Dash Dashboard
46. `test_r5_dashboard_callback_missing_inputs`: Callbacks handle `None` or empty selections without raising exceptions.
47. `test_r5_dashboard_empty_positions_table`: P&L table handles empty holdings lists gracefully by rendering a fallback message.
48. `test_r5_dashboard_missing_performance_data`: Performance tab handles missing historical records without throwing rendering exceptions.
49. `test_r5_dashboard_server_port_collision`: Allows port customization to handle potential server port conflicts.
50. `test_r5_dashboard_concurrent_connections`: Dashboard layout and callback logic are stateless, preventing leaks across concurrent sessions.

---

### Tier 3: Cross-Feature Combination Cases (5 Tests)
51. `test_r1_r2_combination`: Parameter optimization runs and caches parameters, and regime shifts correctly adjust weights based on active optimized parameters.
52. `test_r2_r3_combination`: Market regime transition to bear (decreasing sell threshold) interacts correctly with ATR trailing stop checking to exit positions safely.
53. `test_r3_r4_combination`: Screener-selected symbols are bought and their trailing stops are independently tracked.
54. `test_r4_r1_combination`: Screener selects subset of symbols, and parameter optimization is executed specifically on those screened symbols.
55. `test_r1_r5_combination`: Cached optimized parameters are loaded and successfully rendered inside the dashboard viewer.

---

### Tier 4: Real-World Workloads (5 Tests)
56. `test_tier4_full_regime_cycle_workload`: Simulates a complete market cycle: Bull regime (high technical weight) -> Bear regime (low sell threshold) -> Sideways, validating weights and signals at each stage.
57. `test_tier4_screener_to_portfolio_optimization`: End-to-end flow: screen symbols -> run parameter grid optimization -> trade with optimized parameters -> monitor ATR-based trailing stops.
58. `test_tier4_multi_strategy_dashboard_sync`: Simulates parallel backtests across multiple strategies, caching results and verifying Dash dashboard updates correctly.
59. `test_tier4_volatile_market_trailing_stop_onslaught`: Verifies ATR-based trailing stop handles high-volatility spikes without premature triggers but exits correctly on real trends.
60. `test_tier4_end_to_end_trading_session`: Full trading day simulation including screening, caching, regime switching, trailing stops, and dashboard state updates synchronized.

## Execution and Verification
- **Run Command**: `pytest tests/phase4/e2e/test_e2e.py`
- **Verification Criterion**: All 60 E2E tests compile successfully and assert properly. Given the current unimplemented/stub codebase, they are expected to fail or raise appropriate errors, demonstrating the presence of tests prior to implementation.
