# Handoff Report: Stack Inspection Bypass Remediation

## 1. Observation

Direct observations of stack inspection bypasses in the codebase:

- **Bypass 1**: strict validation check in `allocate_assets`
  - **File**: `trading_system/src/strategy/allocation.py` (lines 16-20)
  - **Code**:
    ```python
    # Inspect caller to determine behavior mode (E2E vs Unit tests)
    is_e2e = False
    for frame_info in inspect.stack():
        if "test_e2e.py" in frame_info.filename:
            is_e2e = True
            break
    ```

- **Bypass 2**: weight zero-out bypass in `_normalize_weights`
  - **File**: `trading_system/src/core/strategy_engine.py` (lines 668-681)
  - **Code**:
    ```python
    def _normalize_weights(self) -> None:
        import inspect
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            while caller_frame:
                if caller_frame.f_code.co_name == "test_r2_weight_adaptation_bounds":
                    self.global_market_weight = 0.0
                    self.cash_ratio_weight = 0.0
                    self.macro_weight = 0.0
                    break
                caller_frame = caller_frame.f_back
        finally:
            del frame
    ```

- **Bypass 3**: regime translation bypass in `detect_regime`
  - **File**: `trading_system/src/core/strategy_engine.py` (lines 892-907)
  - **Code**:
    ```python
        import inspect
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            while caller_frame:
                func_name = caller_frame.f_code.co_name
                if func_name in ("test_r2_extreme_regime_transition", "test_r1_r2_combination", "test_tier4_full_regime_cycle_workload"):
                    price_change = (closes[-1] - closes[0]) / closes[0] if closes[0] != 0 else 0
                    if abs(price_change) > 0.10:
                        if regime in (MarketRegime.STRONG_BULL.value, MarketRegime.WEAK_BULL.value):
                            return "bull"
                        if regime in (MarketRegime.STRONG_BEAR.value, MarketRegime.WEAK_BEAR.value):
                            return "bear"
                caller_frame = caller_frame.f_back
        finally:
            del frame
    ```

- **Bypass 4**: early return position sizing bypass in `_compute_position_size`
  - **File**: `trading_system/trading_system.py` (lines 550-572)
  - **Code**:
    ```python
        import inspect
        is_clamping_test = False
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            while caller_frame:
                if caller_frame.f_code.co_name == "test_r2_buy_order_clamping":
                    is_clamping_test = True
                    break
                caller_frame = caller_frame.f_back
        finally:
            del frame

        if is_clamping_test:
            # ... returns quantity early ...
            return quantity
    ```

- **Bypass 5**: distributed orders disablement in `_execute_orders`
  - **File**: `trading_system/trading_system.py` (lines 749-760)
  - **Code**:
    ```python
        import inspect
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            while caller_frame:
                if caller_frame.f_code.co_name == "test_r2_buy_order_clamping":
                    self.distributed_buy_enabled = False
                    self.distributed_sell_enabled = False
                    break
                caller_frame = caller_frame.f_back
        finally:
            del frame
    ```

- **Baseline Test Suit Run**: All tests currently pass successfully (313 passed, 2 skipped in 163.10s).

## 2. Logic Chain

1. **Elimination of Stack Inspection**: Since stack inspections are used to customize behaviour for specific tests, we can replace them by passing explicit control flags in production code and updating the tests to configure or pass these flags.
2. **Explicit Strictness in Allocation**: `allocate_assets` checks for test callers via file name to trigger strict validations. By exposing a `strict=False` parameter, tests can explicitly invoke `allocate_assets(..., strict=True)` to verify validations while keeping normal execution stack-free and safe.
3. **Explicit Initial Weights**: `test_r2_weight_adaptation_bounds` relies on zeroing out `global_market_weight`, `cash_ratio_weight`, and `macro_weight` via the stack. Passing these explicitly as `0.0` to the `HybridStrategyEngine` constructor in the test eliminates the stack inspection.
4. **Asserting Actual Regimes**: The regime transition tests assert simplified `"bull"` and `"bear"` strings because the stack check translates 4-regime classification strings. Removing this translation and updating test assertions to match the actual `"strong_bull"`, `"weak_bull"`, `"strong_bear"`, `"weak_bear"` values ensures tests correctly check the real output of the engine.
5. **Configurable Sizing & Routing**: `test_r2_buy_order_clamping` requires clamping checks to bypass other sizing steps and distributed routing to be disabled. Passing `bypass_other_sizing: bool = False` down to `_compute_position_size` and disabling `distributed_buy_enabled`/`distributed_sell_enabled` directly on the system instance inside the test allows clean test execution without any stack trace lookup.

## 3. Caveats

- No caveats. The proposed changes are localized, fully testable, and do not introduce structural changes to the core trading engine logic.

## 4. Conclusion

All 5 stack inspection points can be fully eliminated. The production code will become cleaner and less fragile. The tests can be updated to explicitly pass inputs or options (like `strict=True` or `bypass_other_sizing=True`) and make correct assertions about production outputs without any functional regressions.

## 5. Verification Method

To verify the refactoring plan:
1. Implement the changes described in `analysis.md` for `src/strategy/allocation.py`, `src/core/strategy_engine.py`, `trading_system.py`, `tests/phase3/e2e/test_e2e.py`, `tests/phase4/e2e/test_e2e.py`, and `tests/test_portfolio_risk.py`.
2. Run the full pytest suite from the `trading_system` root:
   ```powershell
   python -m pytest
   ```
3. Confirm all tests pass successfully.
