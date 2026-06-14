# Handoff Report

This report summarizes the risk management subsystem audit, identifying current methods, gaps, and recommendations.

## 1. Observation

1. **RiskManager Stop Logic**: In `trading_system/src/risk/risk_manager.py`, we observe that stops are calculated using static thresholds or ATR multipliers:
   - Line 325: `calculate_atr_based_stop` uses `atr_multiplier_stop` (default `2.0`) capped at `2.0 * default_stop_loss_pct` and adjusted by `crisis_detector.get_crisis_stop_multiplier()`.
     ```python
     def calculate_atr_based_stop(self, entry_price: float, atr: float) -> float:
         stop_distance = atr * self.atr_multiplier_stop
         base = max(entry_price - stop_distance, entry_price * (1 - self.default_stop_loss_pct * 2))
         crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()
         if crisis_mult < 1.0:
             tighter = entry_price - (entry_price - base) * crisis_mult
             self.logger.info(f"Crisis stop tightening: {base:.2f} -> {tighter:.2f} (mult={crisis_mult:.2f})")
             return tighter
         return base
     ```
   - Line 581: `check_stop_loss` is a static check based on `default_stop_loss_pct`:
     ```python
     def check_stop_loss(self, symbol: str, current_price: float, entry_price: float) -> bool:
         stop_loss_price = entry_price * (1 - self.default_stop_loss_pct)
         if current_price <= stop_loss_price:
             self._create_alert("STOP_LOSS", symbol, current_price, entry_price)
             return True
         return False
     ```

2. **Integration in `trading_system.py`**:
   - Line 512-521: `trading_system.py` calculates its initial orders' stop-loss and take-profit prices locally using multipliers from `RiskManager.get_adaptive_atr_multipliers` based on market regime and ADX strength:
     ```python
     if atr > 0:
         adaptive = self.risk_manager.get_adaptive_atr_multipliers(self._current_regime, self._current_adx)
         stop_loss_price = price - atr * adaptive["stop"]
         take_profit_price = price + atr * adaptive["target"]
         # ...
     else:
         stop_loss_price = price * (1 - self.risk_manager.default_stop_loss_pct)
         take_profit_price = price * (1 + self.risk_manager.default_take_profit_pct)
     ```
   - Line 1897-1920: `_check_trailing_stop` uses a static `2.0 * atr` threshold for real-time exit signal generation:
     ```python
     def _check_trailing_stop(self, symbol: str, price: float, atr: float) -> Optional[TradeSignal]:
         # ...
         drawdown = pos.highest_price - price
         if drawdown >= 2.0 * atr:
             return TradeSignal.SELL
         return None
     ```

3. **Subsystem Configurations**: In `trading_system/risk_config.json`, the following configuration properties exist:
   ```json
   {
       "default_stop_loss_pct": 0.05,
       "max_portfolio_loss_pct": 0.1,
       "max_position_size_pct": 0.2,
       "active_strategy": "HYBRID"
   }
   ```

4. **Test Verification**:
   - `pytest` on `tests/test_risk_manager.py` completed successfully:
     ```
     tests\test_risk_manager.py .................................             [100%]
     ============================= 33 passed in 14.21s =============================
     ```

---

## 2. Logic Chain

1. **Observation 1 & 2** reveal that stop calculations are duplicated. `RiskManager` has built-in `calculate_atr_based_stop` and `calculate_atr_based_target` methods, but `trading_system.py` bypasses them, opting to calculate stops using the raw values from `get_adaptive_atr_multipliers(...)`.
2. As a consequence of bypassing `calculate_atr_based_stop`, the trading system **does not benefit** from the boundary check limits (capping risk at `2 * default_stop_loss_pct`) or the crisis-tightening multiplier (`crisis_mult`) defined in `RiskManager`.
3. In **Observation 2**, we note that `_check_trailing_stop` uses a hardcoded `2.0 * atr` threshold. This prevents the trailing stop from adjusting dynamically to the current market regime (e.g., tightening to `1.0 * atr` in a strong bear market or widening to `3.0 * atr` in a strong bull market, as configured in `REGIME_ATR_MULTIPLIERS`).
4. Therefore, the trailing stop logic should be refactored to delegate the evaluation to `RiskManager`. This ensures that trailing stops remain synchronized with the regime-adaptive ATR multipliers and crisis-tightening factors.

---

## 3. Caveats

- **No Live Trading Impact Investigated**: We only audited the source code and executed unit tests. We did not run a full paper or live-trading simulation, so we cannot guarantee execution speed or order fill behavior for tightened stop-loss orders in high-volatility environments.
- **Watermark Initialization**: The trailing stop logic initializes the high watermark `highest_price` dynamically on the `Position` object. If the position is loaded from a persisted state (e.g. databases), we assume the watermark is loaded correctly, otherwise it defaults to `avg_price`.

---

## 4. Conclusion

- The system currently uses static percentage stops (5% SL, 15% TP) and dynamic ATR-based stops.
- Trailing stops track a dynamic high watermark but currently apply a static threshold (`2.0 * atr`).
- We recommend refactoring `_check_trailing_stop` to delegate the evaluation to `RiskManager.check_trailing_stop_signal()`, which dynamically computes stop distance using regime-adaptive multipliers (from `get_adaptive_atr_multipliers()`) and crisis tightening.
- We also recommend implementing a dynamic portfolio-drawdown feedback loop that tightens individual stock stops proportionally as the portfolio drawdown approaches the maximum allowed limit.

---

## 5. Verification Method

1. **Unit Tests**:
   - Run specific risk manager tests to ensure core logic remains intact:
     ```powershell
     .\.venv\Scripts\pytest tests/test_risk_manager.py
     ```
2. **Analysis Verification**:
   - Inspect `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\analysis.md` to review the detailed documentation of classes and methods, as well as code snippets of proposed refactoring.
