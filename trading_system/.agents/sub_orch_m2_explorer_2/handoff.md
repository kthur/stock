# Handoff Report: Market Regime Detection & Weights (R2)

## 1. Observation
- **Codebase State**: 
  - File `src/core/strategy_engine.py` (lines 32–593) defines `HybridStrategyEngine` but does not contain a `detect_regime` method or a `set_strategy_parameters` method.
  - Verification execution `python -m pytest tests/phase4/e2e/test_e2e.py -k "r2"` fails all 12 target test cases with `AttributeError` for missing attributes.
  - Example traceback from test runner:
    ```
    FAILED tests/phase4/e2e/test_e2e.py::test_r2_detect_regime_bull - AttributeError: 'HybridStrategyEngine' object has no attribute 'detect_regime'
    FAILED tests/phase4/e2e/test_e2e.py::test_r1_r2_combination - AttributeError: 'HybridStrategyEngine' object has no attribute 'set_strategy_parameters'
    ```

## 2. Logic Chain
- **Reasoning**:
  1. The E2E tests in `tests/phase4/e2e/test_e2e.py` specifically expect `HybridStrategyEngine.detect_regime(price_bars)` to evaluate price trends and return `'bull'`, `'bear'`, or `'sideways'` (Observation 1).
  2. If the price bar series length is under 200, the E2E tests require the engine to return `'sideways'` (Observation 1, `test_r2_detect_regime_insufficient_bars`).
  3. If a price bar is missing required attributes/keys like `high` or `low`, the method must raise `ValueError` (Observation 1, `test_r2_detect_regime_missing_fields`).
  4. In `bull` regime, `technical_weight` must be adapted upwards (Observation 1, `test_r2_bull_weight_adaptation`).
  5. In `bear` regime, `sell_threshold` must fall below `0.45` (Observation 1, `test_r2_bear_sell_threshold`).
  6. Under all regimes, weights must be normalized such that they remain within `[0.0, 1.0]` and sum to exactly `1.0` (Observation 1, `test_r2_weight_adaptation_bounds`).
  7. In order to avoid cumulative drift during transitions (e.g., Bull -> Bear -> Sideways), we must keep track of original/baseline weights (`_baseline_weights`) and base thresholds (`_baseline_sell_threshold`), restoring them before applying new regime adaptations.

## 3. Caveats
- **Read-Only Scope**: In compliance with our role-based investigation guidelines, no source code changes have been committed directly to the repository codebase. Implementers must apply the proposed edits.
- **Mock Price Assumptions**: The test cases generate mock bars with values that can drop below zero (e.g. `price = 100 - i*0.5`). To prevent sign-reversal issues on negative prices in mock tests, our proposed ROC formula uses absolute value in the denominator: `roc20 = (current - prev) / abs(prev)`.

## 4. Conclusion
- Implementing R2 requires modifying `src/core/strategy_engine.py` to:
  1. Store the base/baseline weights and threshold in the constructor.
  2. Implement `detect_regime(price_bars)` to validate fields, filter length, compute EMA200 and ROC20, and classify the market regime.
  3. Apply temporary, non-cumulative weight and threshold modifications inside `detect_regime()`.
  4. Refactor `_normalize_weights()` to enforce value guards (`max(0.0, weight)`) and dynamically maintain base weights.
  5. Add `set_strategy_parameters(strategy_name, parameters)` to store custom parameters.

## 5. Verification Method
- Execute the R2 E2E tests command in the workspace:
  ```powershell
  python -m pytest tests/phase4/e2e/test_e2e.py -k "r2"
  ```
- All 12 test cases must pass successfully.
