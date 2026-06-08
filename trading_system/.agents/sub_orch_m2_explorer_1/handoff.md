# Handoff Report: Milestone 2 Explorer 1

This handoff report summarizes the investigation of **Requirement R1 (Strategy Parameter Optimization)** in `src/analysis/backtest.py`.

---

## 1. Observation

1. **Cache File Directory Creation & Location**:
   - `src/analysis/backtest.py` lines 905-907 defines the path calculation:
     ```python
     cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
     os.makedirs(cache_dir, exist_ok=True)
     cache_file = os.path.join(cache_dir, 'optimized_params.json')
     ```
2. **E2E Test Specifications**:
   - `tests/phase4/e2e/test_e2e.py` lines 400-456 define boundary and corner cases for R1:
     - Empty price bars: `test_r1_empty_price_bars`
     - Single price bar: `test_r1_single_price_bar`
     - Invalid parameter ranges: `test_r1_invalid_param_ranges`
     - Missing JSON directory: `test_r1_missing_json_directory`
     - Extreme parameters: `test_r1_extreme_parameters` (`{"short_window": [-5, 5000]}`)
3. **E2E Cache Overwrite Test**:
   - `tests/phase4/e2e/test_e2e.py` lines 131-136 modifies `data/optimized_params.json` with a flat dictionary:
     ```python
     with open("data/optimized_params.json", "w") as f:
         json.dump({
             "best_params": {"short_window": 99, "long_window": 99},
             "best_return": 999.9,
             "sharpe_ratio": 9.9
         }, f)
     ```
4. **Different Strategy Custom Parameter Names**:
   - `tests/phase4/e2e/test_e2e.py` lines 145-153:
     ```python
     param_ranges = {"rsi_period": [10, 14], "rsi_oversold": [30]}
     result = engine.optimize_parameters("AAPL", bars, param_ranges, strategy_name="RSI")
     assert "rsi_period" in result["best_params"]
     ```

---

## 2. Logic Chain

1. **Boundary Values and Indicator Robustness**:
   - From Obs 2, `test_r1_extreme_parameters` passes a negative value `-5` for `short_window`.
   - In `src/analysis/backtest.py`, `_get_sma` and indicator functions use slice operations `closes[:window]` and `sma[window-1]`. A negative `window` index like `-5` leads to slicing from the end, which does not represent simple moving average calculation, and `window <= 0` can lead to division by zero.
   - Therefore, all indicator/helper methods (`_get_sma`, `_calc_ema`, `_calc_rsi`, `_get_macd_hist`, `_get_bollinger_bands`, `_get_rolling_max`, `_get_rolling_mean_volume`, `_get_rolling_volatility`) must be updated to enforce `window >= 1` or `period >= 1` internally.
2. **Cache Cross-talk and Key Validation**:
   - From Obs 3 and 4, the test suite runs different strategies sequentially, which overwrite the global `data/optimized_params.json`.
   - If the cache checking logic only checks `"best_params" in cache_data`, it will read cached parameters of a different strategy (e.g. reading `MA` parameters when `RSI` is requested), causing assertions in `test_r1_different_strategy_happy_path` to fail.
   - Therefore, the cache check must validate that all keys of the requested `param_ranges` exist in the cached `best_params`, and that the cached `symbol` and `strategy_name` (if stored) match the current parameters.
3. **Parameter Aliases Resolution**:
   - From Obs 4, strategy engines may use custom names like `rsi_period` and `rsi_oversold`.
   - Therefore, `_rsi_strategy` should support mappings for these aliases (`window` -> `rsi_period`, `buy_threshold` -> `rsi_oversold`, `sell_threshold` -> `rsi_overbought`).
4. **Performance Metric Division Safeguards**:
   - Portfolio equity curves could hit 0 if a strategy goes bankrupt.
   - Therefore, `_calculate_sharpe_ratio` and `_calculate_max_drawdown` must verify that the peak or previous equity is non-zero before dividing.

---

## 3. Caveats

- This investigation is strictly read-only. We did not apply any code modifications to the codebase.
- The web dashboard re-implementation in Dash (Milestone 4) was not investigated as it is outside the scope of Milestone 2.

---

## 4. Conclusion

The parameter optimization engine (`BacktestEngine.optimize_parameters`) in `src/analysis/backtest.py` is mostly complete but requires critical robustness upgrades to handle boundary and corner cases successfully. Specifically, it must enforce minimum window sizes of 1 on all indicators, implement parameter key validation in the caching layer, map custom strategy parameter aliases, and safe-guard performance metrics against zero-division errors.

---

## 5. Verification Method

Once changes are applied by the implementer:
1. Run target tests:
   ```powershell
   pytest tests/phase4/e2e/test_e2e.py -k "test_r1"
   ```
2. Verify that `data/optimized_params.json` is correctly saved to the project root's `data/` directory.
