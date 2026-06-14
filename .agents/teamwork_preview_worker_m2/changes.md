# Milestone 2 Risk Management & Portfolio Construction Upgrades Change Log

## Modified Files

### 1. `trading_system/src/risk/risk_manager.py`
- Implemented `check_trailing_stop_signal(self, symbol: str, current_price: float, highest_price: float, atr: float, regime: str = "weak_bull", adx: float = 20.0) -> bool`:
  - Returns `True` if `current_price <= 0.0` (emergency exit).
  - Returns `False` if `atr <= 0.0`.
  - Dynamically calculates the stop distance using regime multipliers (retrieved via `self.get_adaptive_atr_multipliers`).
  - Scales by the crisis stop multiplier if less than `1.0`.
  - Tightens the stop distance using the portfolio drawdown-based stop tightening formula `1.0 - (drawdown / max_drawdown_allowed)` clamped between `0.25` and `1.0`.
  - Evaluates and returns whether the price drawdown from the highest price meets or exceeds the stop distance.
- Updated `calculate_position_sizing` signature to accept `atr: float = 0.0`.
- Integrated Kelly Criterion volatility scaling:
  - If Kelly parameters are active and `atr > 0.0`, calculates `asset_vol_annual = (atr / entry_price) * (252**0.5)`.
  - Scales `kelly_pct` by `vol_scaler = self.target_annual_volatility / asset_vol_annual` clamped to `[0.25, 1.5]` before computing `max_value`.
- Integrated Fixed Risk active crisis scaling:
  - In Fixed Risk sizing paths, scales `max_loss_per_trade_pct` by a crisis risk multiplier (`NONE: 1.0`, `WATCH: 0.75`, `ACTIVE: 0.50`, `SEVERE: 0.25`) depending on `self.crisis_detector.crisis_level` before computing `max_loss`.

### 2. `trading_system/trading_system.py`
- Updated signature of `_compute_position_size` to accept `atr: float = 0.0`.
- In `_compute_position_size`, forwarded the `atr` argument to `calculate_position_sizing(..., atr=atr)`.
- Updated the call to `_compute_position_size` to pass the calculated local variable `atr`.
- Refactored `_check_trailing_stop` to:
  - Return `TradeSignal.SELL` if `price <= 0.0` (emergency exit).
  - Return `None` if `atr <= 0.0` or if the symbol is not in `self.portfolio.positions`.
  - Initialize the watermark (`pos.highest_price`) as before.
  - Delegate trailing stop evaluation to `self.risk_manager.check_trailing_stop_signal`, passing the current regime and ADX from the class instance.
  - Return `TradeSignal.SELL` if it returns `True`, else `None`.

### 3. `trading_system/tests/test_risk_manager.py`
- Added the `TestRiskManagerUpgrades` unit test class to verify all aspects of the new upgrades:
  - `test_check_trailing_stop_emergency_exit`
  - `test_check_trailing_stop_invalid_atr`
  - `test_check_trailing_stop_basic`
  - `test_check_trailing_stop_crisis_tightening`
  - `test_check_trailing_stop_drawdown_tightening`
  - `test_kelly_volatility_scaling`
  - `test_fixed_risk_crisis_scaling`

## Build & Test Status
- All 40 unit tests in `test_risk_manager.py` compiled and passed successfully in `11.76s`.
- All 55 unit tests in `test_system.py` and 3 unit tests in `test_portfolio_risk.py` compiled and passed successfully.
