# Refactoring Plan: Elimination of Stack Inspection Bypasses

This document provides a detailed plan to refactor the production code and tests in order to completely eliminate python stack inspection (`inspect.stack()` and `inspect.currentframe()`).

---

## 1. Asset Allocation Strict Validation Bypass
- **Production File**: `trading_system/src/strategy/allocation.py`
- **Caller Test**: `tests/phase3/e2e/test_e2e.py`

### Current Implementation
`allocate_assets(prices_dict: dict)` inspects the call stack to check if `"test_e2e.py"` is in the caller filename. If it is, it enables strict validation mode (raising `ValueError` or `TypeError` on empty dictionary, negative prices, non-numeric prices, infinite prices, or zero prices). Otherwise, it silently filters out invalid prices and returns a partial weight dictionary.

```python
    # Inspect caller to determine behavior mode (E2E vs Unit tests)
    is_e2e = False
    for frame_info in inspect.stack():
        if "test_e2e.py" in frame_info.filename:
            is_e2e = True
            break
```

### Proposed Refactoring
1. **Production Code**:
   Add an optional parameter `strict: bool = False` to `allocate_assets` and remove the stack inspection.
   ```python
   def allocate_assets(prices_dict: dict, strict: bool = False) -> dict:
       """
       Allocate weights proportionally based on valid prices.
       """
       if prices_dict is None:
           raise TypeError("Input cannot be None")
       if not isinstance(prices_dict, dict):
           raise TypeError("Input must be a dictionary")

       if strict:
           if not prices_dict:
               raise ValueError("Input dictionary cannot be empty")
           for k, v in prices_dict.items():
               if isinstance(v, bool) or not isinstance(v, (int, float)):
                   raise TypeError(f"Price for {k} must be a number")
               if not math.isfinite(v):
                   raise ValueError(f"Price for {k} must be finite")
               if v < 0:
                   raise ValueError(f"Price for {k} cannot be negative")
               if v == 0:
                   raise ValueError(f"Price for {k} cannot be zero")
       # ... rest of the function remains the same ...
   ```

2. **Test Code (`tests/phase3/e2e/test_e2e.py`)**:
   Update E2E validation tests to pass `strict=True`:
   ```python
   def test_allocate_empty_dict():
       with pytest.raises(ValueError):
           allocate_assets({}, strict=True)

   def test_allocate_negative_prices():
       with pytest.raises(ValueError):
           allocate_assets({"AAPL": -150.0}, strict=True)

   def test_allocate_invalid_types():
       with pytest.raises(TypeError):
           allocate_assets({"AAPL": "high"}, strict=True)

   def test_allocate_none_input():
       with pytest.raises(TypeError):
           # None input is already checked regardless of strict, but can still accept parameter
           allocate_assets(None, strict=True)

   def test_allocate_zero_prices():
       with pytest.raises(ValueError):
           allocate_assets({"AAPL": 0.0}, strict=True)
   ```

---

## 2. HybridStrategyEngine Weight Normalization Bypass
- **Production File**: `trading_system/src/core/strategy_engine.py`
- **Caller Test**: `tests/phase4/e2e/test_e2e.py`

### Current Implementation
In `_normalize_weights`, the engine checks the stack to see if the caller function is `"test_r2_weight_adaptation_bounds"`. If so, it zeroes out `global_market_weight`, `cash_ratio_weight`, and `macro_weight` before applying normalization.

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

### Proposed Refactoring
1. **Production Code**:
   Remove the stack inspection logic entirely from `_normalize_weights()`:
   ```python
   def _normalize_weights(self) -> None:
       self.sentiment_weight = max(0.0, min(1.0, self.sentiment_weight))
       # ... rest of the standard normalization remains ...
   ```

2. **Test Code (`tests/phase4/e2e/test_e2e.py`)**:
   Explicitly pass `global_market_weight=0.0`, `cash_ratio_weight=0.0`, and `macro_weight=0.0` to the constructor in `test_r2_weight_adaptation_bounds`:
   ```python
   def test_r2_weight_adaptation_bounds():
       """R2 boundary: dynamic weights stay within [0.0, 1.0] and sum to exactly 1.0 after normalization."""
       from src.core.strategy_engine import HybridStrategyEngine
       engine = HybridStrategyEngine(
           sentiment_weight=9.0, # Initial out of bounds
           technical_weight=1.0,
           ml_weight=0.0,
           rl_weight=0.0,
           darkpool_weight=0.0,
           llm_weight=0.0,
           global_market_weight=0.0,
           cash_ratio_weight=0.0,
           macro_weight=0.0
       )
   ```

---

## 3. HybridStrategyEngine Regime Detection Simplification Bypass
- **Production File**: `trading_system/src/core/strategy_engine.py`
- **Caller Tests**: `test_r2_extreme_regime_transition`, `test_r1_r2_combination`, and `test_tier4_full_regime_cycle_workload` in `tests/phase4/e2e/test_e2e.py`

### Current Implementation
In `detect_regime`, if the caller is one of the three specified tests and the price change magnitude exceeds 10%, the method translates 4-regime classification outcomes to simplified `"bull"` / `"bear"` strings instead of `"strong_bull"`, `"weak_bull"`, etc.

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

### Proposed Refactoring
1. **Production Code**:
   Remove the stack inspection logic entirely from `detect_regime()`, simply returning `regime` unmodified.
   ```python
       # Remove inspect block
       return regime
   ```

2. **Test Code (`tests/phase4/e2e/test_e2e.py`)**:
   Adjust the test assertions to match the actual returned `MarketRegime` values:
   - In `test_r2_extreme_regime_transition`:
     ```python
     # Replace: assert regime == "bear"
     assert regime in ("strong_bear", "weak_bear") # or assert regime == "strong_bear"
     ```
   - In `test_r1_r2_combination`:
     ```python
     # Replace: assert regime == "bull"
     assert regime in ("strong_bull", "weak_bull") # or assert regime == "strong_bull"
     ```
   - In `test_tier4_full_regime_cycle_workload`:
     ```python
     # Replace: assert regime == "bull"
     assert regime in ("strong_bull", "weak_bull")
     # Replace: assert regime == "bear"
     assert regime in ("strong_bear", "weak_bear")
     ```

---

## 4. Trading System Order Clamping and Routing Bypasses
- **Production File**: `trading_system/trading_system.py`
- **Caller Test**: `tests/test_portfolio_risk.py` (`test_r2_buy_order_clamping`)

### Current Implementation
1. **Position Sizing**: If the caller is `"test_r2_buy_order_clamping"`, the position sizing pipeline returns the clamped quantity early to prevent down-sizing by other rules (such as Conservative ramp or Volatility targeting).
2. **Order Execution**: If the caller is `"test_r2_buy_order_clamping"`, distributed orders are forced to `False`.

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
            vix = self.market_data_cache.get("VIX", {}).get("price") or 20.0
            if self.risk_manager.check_risk_off_signal(vix):
                max_spend = self.portfolio.cash - 0.70 * portfolio_value
                if max_spend < 0:
                    max_spend = 0.0
                max_qty = int(max_spend / price)
                if quantity > max_qty:
                    quantity = max_qty
            return quantity
```

### Proposed Refactoring
1. **Production Code**:
   Add a parameter `bypass_other_sizing: bool = False` to `_create_and_submit_order` and `_compute_position_size`. Remove stack checks in both methods.

   In `_compute_position_size`:
   ```python
       async def _compute_position_size(
           self, symbol: str, order_type: OrderType, price: float, confidence: float,
           portfolio_value: float, stop_loss_price: float, take_profit_price: float,
           win_rate: float, win_loss_ratio: float, min_trade_quantity: int,
           distributed_min_quantity: int, bypass_other_sizing: bool = False
       ) -> int:
           quantity = self.risk_manager.calculate_position_sizing(
               symbol=symbol, entry_price=price, stop_loss_price=stop_loss_price,
               win_rate=win_rate, win_loss_ratio=win_loss_ratio,
           )

           if bypass_other_sizing:
               vix = self.market_data_cache.get("VIX", {}).get("price") or 20.0
               if self.risk_manager.check_risk_off_signal(vix):
                   max_spend = self.portfolio.cash - 0.70 * portfolio_value
                   if max_spend < 0:
                       max_spend = 0.0
                   max_qty = int(max_spend / price)
                   if quantity > max_qty:
                       quantity = max_qty
               return quantity
           # ... rest of the normal sizing rules ...
   ```

   In `_execute_orders`, remove the inspect frame block entirely.

2. **Test Code (`tests/test_portfolio_risk.py`)**:
   Disable distributed order routing on the system object inside the test, and pass `bypass_other_sizing=True` to the order submission call:
   ```python
        system = StockTradingSystem(initial_cash=100000.0, config=config, components=components)
        system.distributed_buy_enabled = False
        system.distributed_sell_enabled = False
        
        # ... mocks ...
        
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(system._create_and_submit_order("AAPL", OrderType.BUY, 100.0, bypass_other_sizing=True))
        finally:
            loop.close()
   ```
