# Risk Management System Audit Report

## Executive Summary
This audit provides a comprehensive analysis of the risk management subsystem in `trading_system/src/risk/risk_manager.py`, how stops are currently implemented, and how these risk rules interface with `trading_system.py`. While the subsystem includes robust features like Kelly sizing, crisis detection, and volatility scaling, a key discrepancy exists: `trading_system.py` duplicates and bypasses the `RiskManager`'s built-in stop methods, calculating its own adaptive stops and trailing stops locally.

---

## 1. Current Methods for Stops

The trading system employs three types of stops: **Stop Loss (SL)**, **Take Profit (TP)**, and **Trailing Stop (TS)**. These stops use both static percentages and dynamic ATR-based calculations depending on the context:

### A. Static vs. Dynamic Stops
1. **Static Percentage Stops**: 
   - Default stop loss and take profit are calculated as static percentages of the entry price:
     - $\text{Stop Loss Price} = \text{Entry Price} \times (1 - \text{default\_stop\_loss\_pct})$
     - $\text{Take Profit Price} = \text{Entry Price} \times (1 + \text{default\_take\_profit\_pct})$
   - These are checked by `RiskManager.check_stop_loss()` and `RiskManager.check_take_profit()`, and also serve as fallback values in `trading_system.py` when ATR data is unavailable.
2. **Dynamic ATR-Based Stops**:
   - Dynamic stop distances are computed as a multiple of the Average True Range (ATR):
     - $\text{Stop Distance} = \text{ATR} \times \text{atr\_multiplier\_stop}$
     - $\text{Target Distance} = \text{ATR} \times \text{atr\_multiplier\_target}$
   - These stops are implemented in `RiskManager.calculate_atr_based_stop()` and `RiskManager.calculate_atr_based_target()`, which restrict the stop to be at most twice the default static percentages to prevent extremely wide stops, and tighten them during market crises.

### B. Stop Fields on `RiskManager`
The following properties configure stops on the `RiskManager` instance:
- `default_stop_loss_pct` (float, default: `0.05`): Default static stop loss percentage (5%).
- `default_take_profit_pct` (float, default: `0.15`): Default static take profit percentage (15%).
- `atr_multiplier_stop` (float, default: `2.0`): Multiplier for ATR-based stop loss distance.
- `atr_multiplier_target` (float, default: `3.0`): Multiplier for ATR-based take profit distance.
- `REGIME_ATR_MULTIPLIERS` (class dict): Regime-adaptive stop, target, and trail parameters:
  - `"strong_bull"`: `{"stop": 3.0, "target": 5.0, "trail": 0.08}`
  - `"weak_bull"`: `{"stop": 2.5, "target": 4.0, "trail": 0.06}`
  - `"weak_bear"`: `{"stop": 1.5, "target": 2.5, "trail": 0.04}`
  - `"strong_bear"`: `{"stop": 1.0, "target": 2.0, "trail": 0.03}`

---

## 2. Risk Management Component Documentation

The risk management subsystem is composed of several key classes and configurations in `trading_system/src/risk/risk_manager.py`:

### A. Classes and Dataclasses
1. **`CrisisLevel` (Enum)**:
   - Defines the system-wide crisis state: `NONE`, `WATCH`, `ACTIVE`, `SEVERE`.
2. **`RiskLevel` (Enum)**:
   - Defines the overall portfolio risk: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
3. **`RiskMetrics` (dataclass)**:
   - Snapshot of current risk metrics. Fields include: `current_value`, `max_loss_limit`, `max_position_size`, `stop_loss_pct`, `take_profit_pct`, `current_drawdown`, `max_drawdown_allowed`, `portfolio_volatility`, `risk_level`, and `timestamp`.
4. **`CrisisDetector`**:
   - Detects systemic market shocks by combining VIX, portfolio drawdown, volume spikes, and macro economic indicators (USD/KRW, Crude Oil, TNX, DXY).
   - *Key methods*:
     - `evaluate()`: Computes a composite crisis score (0.0 to 1.0) and transitions `crisis_level`.
     - `get_crisis_cash_target()`: Dictates cash floor percentages (NONE: 10%, WATCH: 30%, ACTIVE: 60%, SEVERE: 85%).
     - `get_crisis_position_multiplier()`: Reduces new position sizes (NONE: 1.0x, WATCH: 0.70x, ACTIVE: 0.40x, SEVERE: 0.15x).
     - `get_crisis_stop_multiplier()`: Tightens stops during crisis (NONE: 1.0x, WATCH: 0.80x, ACTIVE: 0.60x, SEVERE: 0.40x).
     - `should_block_new_buys()`, `should_liquidate()`: Policy controls for SEVERE crisis levels.
5. **`RiskManager`**:
   - The central coordinator for risk policy, position sizing, drawdown tracking, and stop-loss calculations.
   - *Key methods*:
     - `calculate_atr_based_stop(entry_price, atr)` / `calculate_atr_based_target(entry_price, atr)`: Incorporate default caps and crisis-based tightening.
     - `get_adaptive_atr_multipliers(regime, adx)`: Resolves regime-specific stop, target, and trailing multipliers, scaled by ADX strength.
     - `calculate_position_sizing(...)`: Returns the optimized order quantity, applying Kelly Criterion, volatility scaling, VIX caps, and crisis limits.
     - `calculate_drawdown()`: Calculates current drawdown from the peak value.
     - `calculate_risk_level(positions)`: Determines overall risk based on drawdown, position concentration, correlation, and crisis level.
     - `calculate_var(returns)` / `calculate_cvar(returns)`: Computes Value-at-Risk and Conditional Value-at-Risk.

### B. Configuration File (`risk_config.json`)
Located at `trading_system/risk_config.json`. Persists core parameters:
- `default_stop_loss_pct` (e.g. `0.05`)
- `max_portfolio_loss_pct` (e.g. `0.10`)
- `max_position_size_pct` (e.g. `0.20`)
- `active_strategy` (e.g. `"HYBRID"`)

---

## 3. Integration Discrepancies and Gap Analysis

A detailed inspection of `trading_system.py` reveals two critical gaps:

1. **Stop Calculation Duplication**:
   - `trading_system.py` does not call `RiskManager.calculate_atr_based_stop()` or `RiskManager.calculate_atr_based_target()`.
   - Instead, it directly retrieves adaptive multipliers and computes stops locally:
     ```python
     stop_loss_price = price - atr * adaptive["stop"]
     take_profit_price = price + atr * adaptive["target"]
     ```
   - This bypasses the crisis-tightening logic (`crisis_detector.get_crisis_stop_multiplier()`) and boundary safety caps implemented in `RiskManager`.
2. **Trailing Stop Static Threshold**:
   - While `trading_system.py._update_trailing_stops` dynamically adjusts order prices using `_get_trailing_pct(symbol)` and `adaptive["stop"]`, the real-time check in `_check_trailing_stop` uses a hardcoded `2.0 * atr` drawdown threshold:
     ```python
     drawdown = pos.highest_price - price
     if drawdown >= 2.0 * atr:
         return TradeSignal.SELL
     ```
   - This prevents the trailing stop from adapting to the current market regime or ADX strength.

---

## 4. Recommendations for Dynamic/ATR-Based Stops

To resolve the duplicate logic and implement a fully dynamic, regime-adaptive risk management flow, we recommend the following enhancements:

### Recommendation 1: Delegate Trailing Stop Evaluation to `RiskManager`
Unify the trailing stop evaluation by defining a `check_trailing_stop_signal` method in `RiskManager`. This method should calculate the trailing stop boundary dynamically based on the current regime and ADX.

**Proposed Implementation in `RiskManager`**:
```python
def check_trailing_stop_signal(
    self, 
    symbol: str, 
    current_price: float, 
    highest_price: float, 
    atr: float, 
    regime: str = "weak_bull", 
    adx: float = 20.0
) -> bool:
    """Checks if trailing stop is triggered using regime-adaptive ATR multipliers."""
    if current_price <= 0.0:
        return True  # Emergency exit for zero/invalid price
    if atr <= 0.0:
        return False # Gracefully ignore if ATR data is missing
        
    # Retrieve adaptive multipliers from regime & ADX strength
    adaptive = self.get_adaptive_atr_multipliers(regime, adx)
    stop_distance = atr * adaptive["stop"]
    
    # Apply crisis tightening if market is in WATCH/ACTIVE/SEVERE crisis
    crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()
    if crisis_mult < 1.0:
        stop_distance *= crisis_mult
        
    drawdown = highest_price - current_price
    return drawdown >= stop_distance
```

### Recommendation 2: Refactor `_check_trailing_stop` in `trading_system.py`
Modify `trading_system.py` to delegate the evaluation to the `RiskManager`, ensuring consistency between the static stops and trailing stops:
```python
def _check_trailing_stop(self, symbol: str, price: float, atr: float = 2.0) -> Optional[TradeSignal]:
    if symbol not in self.portfolio.positions:
        return None
    
    pos = self.portfolio.positions[symbol]
    if not hasattr(pos, "highest_price") or pos.highest_price is None or pos.highest_price == 0.0:
        pos.highest_price = getattr(pos, "avg_price", price)
        
    if price > pos.highest_price:
        pos.highest_price = price
        
    # Delegate trailing stop check to RiskManager
    triggered = self.risk_manager.check_trailing_stop_signal(
        symbol=symbol,
        current_price=price,
        highest_price=pos.highest_price,
        atr=atr,
        regime=self._current_regime,
        adx=self._current_adx
    )
    
    if triggered:
        return TradeSignal.SELL
        
    return None
```

### Recommendation 3: Implement Drawdown-Based Dynamic Stop Tightening
In corporate risk environments, individual stops should tighten as overall portfolio drawdown deepens to protect the capital floor.
We can scale the ATR multiplier based on current drawdown:
$$Multiplier_{adjusted} = Multiplier_{regime} \times \left(1.0 - \frac{Current Drawdown}{Max Drawdown Allowed}\right)$$
For example:
- If portfolio drawdown is 0%, stops remain at 100% of their regime-adaptive width.
- If portfolio drawdown is 10% (out of 20% max allowed), stops are tightened by 50% to restrict further risk.
- This creates an automated defensive feedback loop.
