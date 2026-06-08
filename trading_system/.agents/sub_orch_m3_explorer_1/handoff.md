# Handoff Report — Requirement R3: Trailing Stop Analysis

This handoff report summarizes the investigation and proposed code changes to satisfy Requirement R3: Trailing Stop in `trading_system.py`.

---

## 1. Observation
- **Missing Method in `trading_system.py`**:
  A search for `_check_trailing_stop` in `trading_system.py` returned no results. The method is completely missing from the `StockTradingSystem` class.
- **Position Tracking in `src/core/asset_management.py`**:
  Line 23-27:
  ```python
  @dataclass
  class Position:
      """포지션 정보"""
      symbol: str
      quantity: int
      avg_price: float
  ```
  The `Position` object contains `symbol`, `quantity`, and `avg_price`, but does not define `highest_price` as a static field.
- **E2E Test Specifications in `tests/phase4/e2e/test_e2e.py`**:
  - `test_r3_price_zero` (Line 537-546): Checks that `price <= 0.0` triggers `TradeSignal.SELL` immediately.
  - `test_r3_atr_zero` (Line 526-535): Checks that `atr <= 0.0` returns `None` (graceful default, no trigger).
  - `test_r3_no_active_position` (Line 548-555): Checks that verifying trailing stop for a non-existent holding returns `None`.
  - `test_r3_high_watermark_lower_than_entry` (Line 556-566): Checks that high watermark is initialized to the entry price (`avg_price`) if the market immediately falls.
  - `test_r3_high_watermark_update` (Line 230-242): Checks that `highest_price` dynamically updates when price hits new highs.
  - `test_r3_stop_loss_trigger` (Line 217-228): Checks that trailing stop triggers a `TradeSignal.SELL` when drawdown exceeds `2 * atr`.

---

## 2. Logic Chain
- **Step 1**: The tests verify the existence and behavior of `_check_trailing_stop` on the `StockTradingSystem` instance. Therefore, the method must be added to the class in `trading_system.py` with the signature `_check_trailing_stop(self, symbol: str, price: float, atr: float = 2.0) -> Optional[TradeSignal]`.
- **Step 2**: The tests dynamically inspect `system.portfolio.positions[symbol].highest_price`. Therefore, `highest_price` should be attached directly to the `Position` instance corresponding to the traded `symbol`.
- **Step 3**: The watermark should never drop below the entry price (`position.avg_price`). Thus, during initialization (if the attribute is absent, `None`, or lower than `position.avg_price`), `position.highest_price` should be set to `position.avg_price`.
- **Step 4**: When `price` rises above `highest_price`, the watermark is updated to `price`.
- **Step 5**: Drawdown is calculated as `highest_price - price`. If `drawdown >= 2.0 * atr`, it means the price has fallen by at least `2.0 * atr` from its highest watermark, and `TradeSignal.SELL` should be returned.
- **Step 6**: For edge cases:
  - If `symbol` is not found in `self.portfolio.positions`, return `None` because there is no position to evaluate.
  - If `price <= 0.0`, return `TradeSignal.SELL` to prevent further loss and handle negative/zero values gracefully.
  - If `atr <= 0.0`, return `None` since a stop cannot be computed without a valid positive threshold.

---

## 3. Caveats
- **Dynamic Attribute Injection**: This plan relies on injecting `highest_price` dynamically into the dataclass `Position` instance at runtime during `_check_trailing_stop`. This avoids changing `src/core/asset_management.py` and is fully compatible with Python's dynamic typing.
- **Single-direction (Long Only) Trailing Stop**: The formula `drawdown = highest_price - price` assumes standard long position trailing stop logic, which aligns perfectly with all the E2E tests.

---

## 4. Conclusion
Adding `_check_trailing_stop` directly to the `StockTradingSystem` class with the proposed dynamic watermark tracking logic will satisfy all R3 requirements and enable all 14 related E2E test cases to pass successfully.

---

## 5. Verification Method
1. **Target File**: `d:\Finance\code\stock\trading_system\trading_system.py`
2. **Command to run test suite**:
   ```powershell
   pytest tests/phase4/e2e/test_e2e.py -k "r3"
   ```
3. **Invalidation Condition**: The tests will fail if `highest_price` is initialized to the current price when current price is lower than entry price, or if drawdown thresholds or return values deviate from `TradeSignal.SELL` / `None`.
