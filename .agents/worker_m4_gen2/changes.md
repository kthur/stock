# Milestone 4 - Documentation Changes & Verification Report

## Documentation Changes
The system architecture documentation in `trading_system/docs/SYSTEM_ARCHITECTURE.md` has been updated to cover the following areas:

1. **9-Feature Model Structure (Sections 7.3 & 10.1)**:
   - Added documentation for the 9 features used by `OnDevicePredictionModel`: `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `dist_sma_20`, `vol_20d`, and the three newly introduced normalized features:
     - `norm_market_cap`: Region-normalized market capitalization.
     - `norm_floating_value`: Region-normalized floating market value (liquidity-weighted size).
     - `norm_volume`: Region-normalized trading volume.
   - Updated the horizons list to match the 8 horizons currently defined in the codebase: `1`, `5`, `10`, `20`, `30`, `60`, `120`, and `200` days.

2. **Regional Market Normalization & Currency Separation Logic (Section 10.1)**:
   - Documented the logic that separates stock tickers into US vs. KR groups to prevent mathematically invalid summation across different currencies (USD vs. KRW).
   - Documented the formulas used to calculate features and their normalized counterparts:
     - $\text{market\_cap} = \text{Close} \times \text{shares\_outstanding}$
     - $\text{floating\_value} = \text{Close} \times \text{floating\_shares}$ (with a fallback to $\text{Close} \times \text{Volume}$ if floating shares is invalid or <= 0).
     - Regional baseline totals calculated dynamically: $\text{total\_market\_cap}$, $\text{total\_floating\_value}$, and $\text{total\_volume}$.
     - Normalization formulas:
       - $\text{norm\_market\_cap} = \frac{\text{market\_cap}}{\text{total\_market\_cap}}$
       - $\text{norm\_floating\_value} = \frac{\text{floating\_value}}{\text{total\_floating\_value}}$
       - $\text{norm\_volume} = \frac{\text{Volume}}{\text{total\_volume}}$

3. **HybridStrategyEngine volume expansion and liquidity checks (Section 5.2.1)**:
   - **Volume Expansion Momentum Bonus/Penalty**:
     - Activates when $\ge 20$ volume bars are available.
     - Triggered when the 5-day volume SMA is more than 1.5 times the 20-day volume SMA (`volume_5sma > 1.5 * volume_20sma`).
     - Adds a **+0.05** bonus to the combined indicator score if the price trend is positive (defined as `EMA20 > EMA50` or `MACD Histogram > 0`).
     - Subtracts a **-0.05** penalty from the combined indicator score if the price trend is negative.
     - Capping: The combined score is capped to $[0.0, 1.0]$.
   - **Low Floating Value Liquidity Penalty**:
     - Activates when `floating_shares` is provided.
     - Checks if $\text{floating\_value} = \text{Close} \times \text{floating\_shares}$ is below a dynamic threshold:
       - $\text{Close} > 1000.0$ (KRW priced stock): Threshold = **10,000,000,000.0** (10 billion KRW).
       - $\text{Close} \le 1000.0$ (USD priced stock): Threshold = **10,000,000.0** (10 million USD).
     - If the floating value is below the threshold, the combined score is capped to a maximum of **0.4** (`combined = min(combined, 0.4)`).

---

## Verification Report
The test suite was run on the workspace codebase to verify that all modifications from Milestones 1-3 behave correctly.

### Run Details
- **Command**: `python -m pytest tests/`
- **Working Directory**: `D:\Finance\code\stock\trading_system`
- **Result**: `329 passed, 2 skipped, 14 warnings in 157.52s (0:02:37)`
- **Status**: **PASS**

### Test Categories Executed
- **Phase 3 E2E and Unit Tests**:
  - `tests\phase3\e2e\test_e2e.py` (Passed)
  - `tests\phase3\test_allocation.py` (Passed)
  - `tests\phase3\test_broker_reporting.py` (Passed)
  - `tests\phase3\test_m1_ai_pipeline.py` (Passed)
- **Phase 4 E2E Tests**:
  - `tests\phase4\e2e\test_e2e.py` (Passed)
- **Phase 6 Mock Trading Tests**:
  - `tests\phase6\unit\test_mock_trading.py` (Passed)
- **Feature Normalization & System Tests**:
  - `tests\test_feature_normalization.py` (Passed)
  - `tests\test_feature_normalization_stress.py` (Passed)
  - `tests\test_indicators.py` (Passed) (Verifies volume expansion & liquidity checks)
  - `tests\test_macro.py` & `test_macro_stress.py` (Passed)
  - `tests\test_ml_ensemble.py` (Passed)
  - `tests\test_portfolio_risk.py` (Passed)
  - `tests\test_post_market_scoring.py` (Passed)
  - `tests\test_risk_manager.py` (Passed)
  - `tests\test_screener_dash_challenger.py` (Passed)
  - `tests\test_strategy_updates.py` (Passed)
  - `tests\test_system.py` (Passed)
  - `tests\test_telegram_bot.py` (Passed)
