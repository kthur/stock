# Requirement R3: Trailing Stop Analysis and Implementation Plan

## 1. Overview of Requirement R3
The Trailing Stop requirement (R3) introduces a dynamic exit mechanism to protect profits on active long or short positions. Specifically:
- The system must track the highest price (`highest_price` watermark) achieved by the stock since the position was opened.
- If the price drops by more than `2.0 * atr` (where `atr` is the Average True Range passed into the check) from the highest watermark, a `TradeSignal.SELL` is triggered.
- All watermarks must be tracked independently per symbol.
- Edge cases such as invalid prices, invalid ATR values, missing positions, and watermark resets must be handled gracefully.

---

## 2. Technical Mapping & Code Analysis

### Class: `StockTradingSystem` (in `trading_system.py`)
- We need to define `_check_trailing_stop(self, symbol: str, price: float, atr: float = 2.0) -> Optional[TradeSignal]` on the main `StockTradingSystem` class.
- The `TradeSignal` enum is imported from `src.core` (defined in `src/core/strategy_engine.py` as `BUY = 1`, `SELL = -1`, `HOLD = 0`).

### High Watermark Tracking
- Active positions are stored as `Position` objects inside `self.portfolio.positions` (which is a dictionary mapping `symbol` to `Position`).
- To avoid modifying `Position` dataclass files directly and to ensure compatibility with dynamic property access in python, we can initialize and update the `highest_price` attribute dynamically on the `Position` object inside `_check_trailing_stop`.

---

## 3. Detailed Edge Case Specifications

1. **No Active Position**:
   - If the requested symbol is not in `self.portfolio.positions`, the check must immediately return `None`.

2. **Price <= 0.0**:
   - A price of 0.0 or lower is considered invalid and triggers a defensive panic exit, returning `TradeSignal.SELL` immediately to prevent further downside or division errors.

3. **ATR <= 0.0**:
   - If ATR is zero or negative, the trailing stop calculation is mathematically invalid/unreachable. It is handled gracefully by returning `None` (i.e. no stop is triggered).

4. **High Watermark Initialization & Lower Bound**:
   - When a position is first checked, or if `highest_price` is missing/lower than `avg_price`, it must be initialized/reset to `avg_price` (the entry price).
   - This ensures that if the stock falls immediately after entry, the watermark remains at the entry price, preventing the stop boundary from shifting downward.

5. **High Watermark Update**:
   - If the current `price` exceeds the tracked `highest_price`, `highest_price` is updated to the new `price`.

6. **Trigger Condition**:
   - Drawdown is calculated as: `drawdown = highest_price - price`.
   - The threshold is: `2.0 * atr`.
   - If `drawdown >= threshold`, return `TradeSignal.SELL`.
   - Otherwise, return `None`.

---

## 4. Precise Code Modification Proposal

To implement this functionality, the following method will be added to the `StockTradingSystem` class in `trading_system.py`:

```python
    def _check_trailing_stop(self, symbol: str, price: float, atr: float = 2.0) -> Optional[TradeSignal]:
        """
        Evaluate trailing stop for a given symbol and price based on ATR.
        
        Args:
            symbol: Stock symbol
            price: Current stock price
            atr: Average True Range (drawdown threshold multiplier)
            
        Returns:
            TradeSignal.SELL if trailing stop is triggered, else None
        """
        # 1. Check if there is an active position
        if symbol not in self.portfolio.positions:
            return None
            
        # 2. Defensive check for invalid price <= 0 (triggers immediate sell)
        if price <= 0.0:
            return TradeSignal.SELL
            
        # 3. Defensive check for invalid atr <= 0 (disables trailing stop)
        if atr <= 0.0:
            return None
            
        position = self.portfolio.positions[symbol]
        
        # 4. Initialize or reset watermark to entry price (avg_price)
        if not hasattr(position, "highest_price") or position.highest_price is None or position.highest_price < position.avg_price:
            position.highest_price = position.avg_price
            
        # 5. Update watermark if price reaches new high
        if price > position.highest_price:
            position.highest_price = price
            
        # 6. Evaluate trailing stop condition (drawdown >= 2 * ATR)
        drawdown = position.highest_price - price
        if drawdown >= 2.0 * atr:
            return TradeSignal.SELL
            
        return None
```

---

## 5. Verification Plan

### Test Commands
The verification can be performed by running pytest on the phase4 E2E tests:
```powershell
pytest tests/phase4/e2e/test_e2e.py -k "r3"
```

### Affected E2E Test Cases
The following tests in `tests/phase4/e2e/test_e2e.py` specifically cover R3:
- `test_r3_no_stop_loss_trigger`
- `test_r3_stop_loss_trigger`
- `test_r3_high_watermark_update`
- `test_r3_multiple_symbols_stop`
- `test_r3_stop_loss_after_rebound`
- `test_r3_atr_zero`
- `test_r3_price_zero`
- `test_r3_no_active_position`
- `test_r3_high_watermark_lower_than_entry`
- `test_r3_atr_extreme_large`
- `test_r2_r3_combination`
- `test_r3_r4_combination`
- `test_tier4_volatile_market_trailing_stop_onslaught`
- `test_tier4_end_to_end_trading_session`
