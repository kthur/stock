# Technical Specification: Intraday Microstructure & Dynamic Stop-Loss Engine (Milestone 1 / R1)

## 1. Overview & Architecture

Milestone 1 (R1) establishes real-time intraday risk management by introducing an order book and price/volume momentum monitoring engine (`IntradayStopLossEngine`). This engine detects sudden market dislocations, volume-driven panic selling, peak-to-trough price decay, and dynamic ATR trailing breaches before broad daily close execution.

```
+-----------------------------------------------------------------------------------+
|                            Intraday Market Data Input                             |
|        (OHLCV 1m/5m Candles / Real-Time Order Book / Streaming Price & Vol)        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                             IntradayStopLossEngine                                |
|  - Real-time Peak-to-Trough Tracking (Default -4.0%, Configurable)               |
|  - Volume Acceleration Panic Detection (>3.0x 20-min SMA + Negative Return)      |
|  - Dynamic Trailing ATR / Volatility Adjusted Stop Level                         |
|  - Crisis-Level Dynamic Tightening (CrisisDetector Scaling)                       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        Output: StopLossResult Dataclass                           |
|  (triggered, symbol, drop_pct, panic_volume_ratio, reason, recommended_action)    |
+-----------------------------------------------------------------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
+------------------------------------------+  +-------------------------------------+
| RiskManager Integration                  |  | Pipeline Execution Integration      |
| - evaluate_intraday_stop_loss(symbol)    |  | (run_pipeline.py Risk Phase)        |
| - check_intraday_risk(portfolio_data)    |  | - Suppress buy signals / zero score |
| - Alert Generation                       |  | - Immediate liquidation flags       |
+------------------------------------------+  +-------------------------------------+
```

---

## 2. File Location & Module Structure

- **Core Module Path**: `trading_system/src/risk/intraday_stop_loss.py` (with compatibility bridge / alias in `src/risk/intraday_stop_loss.py`)
- **Integration Target 1**: `trading_system/src/risk/risk_manager.py`
- **Integration Target 2**: `trading_system/run_pipeline.py`
- **Unit Test Suite**: `trading_system/tests/test_intraday_stop_loss.py`

---

## 3. Class Specifications

### 3.1 Dataclass: `StopLossResult`

```python
from dataclasses import dataclass

@dataclass
class StopLossResult:
    """Dataclass holding evaluation output for intraday stop-loss checks."""
    triggered: bool
    symbol: str
    drop_pct: float            # Peak-to-trough price change ratio (e.g., -0.045 for -4.5%)
    panic_volume_ratio: float  # Current volume / 20-min rolling volume SMA (e.g., 3.5x)
    reason: str                # "NONE", "PEAK_TO_TROUGH_DROP", "PANIC_VOLUME_SPIKE", "DYNAMIC_ATR_TRAILING_BREACH"
    recommended_action: str    # "NO_ACTION", "FULL_LIQUIDATION", "PARTIAL_REDUCTION_50", "BLOCK_BUY"
```

### 3.2 Core Class: `IntradayStopLossEngine`

```python
import logging
from collections import deque
from typing import Dict, Optional, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class IntradayStopLossEngine:
    """
    Intraday Microstructure & Dynamic Stop-Loss Engine
    Tracks intraday peak prices, volume acceleration, and dynamic ATR trailing boundaries.
    """

    def __init__(
        self,
        peak_drop_threshold: float = -0.04,  # -4% peak-to-trough default drop threshold
        volume_spike_threshold: float = 3.0, # 3.0x 20-min rolling SMA volume surge
        atr_multiplier: float = 2.0,        # ATR trailing distance multiplier
        window_size: int = 20,              # 20-period window for rolling statistics
    ):
        self.peak_drop_threshold = peak_drop_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.atr_multiplier = atr_multiplier
        self.window_size = window_size

        # Symbol state tracking (using deque with maxlen=window_size for O(1) streaming updates)
        self._symbol_peaks: Dict[str, float] = {}
        self._price_history: Dict[str, deque] = {}
        self._volume_history: Dict[str, deque] = {}

    def update_intraday_candle(
        self,
        symbol: str,
        price: float,
        volume: float,
        high: Optional[float] = None,
        low: Optional[float] = None,
    ) -> None:
        """Update streaming price and volume history for a symbol."""
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=self.window_size)
            self._volume_history[symbol] = deque(maxlen=self.window_size)
            self._symbol_peaks[symbol] = max(price, high if high is not None else price)

        self._price_history[symbol].append(price)
        self._volume_history[symbol].append(volume)

        current_peak = self._symbol_peaks.get(symbol, price)
        cand_peak = max(price, high if high is not None else price)
        if cand_peak > current_peak:
            self._symbol_peaks[symbol] = cand_peak

    def reset_symbol(self, symbol: str) -> None:
        """Reset intraday state for a specific symbol."""
        self._symbol_peaks.pop(symbol, None)
        self._price_history.pop(symbol, None)
        self._volume_history.pop(symbol, None)

    def evaluate(
        self,
        symbol: str,
        intraday_data: Union[pd.DataFrame, dict],
        entry_price: Optional[float] = None,
        atr: Optional[float] = None,
        crisis_multiplier: float = 1.0,
    ) -> StopLossResult:
        """
        Evaluates intraday market data against dynamic stop-loss rules.

        Args:
            symbol: Ticker symbol string.
            intraday_data: DataFrame with OHLCV columns OR dict with current price/volume metrics.
            entry_price: Purchase price of the position (if held).
            atr: Average True Range value (if available).
            crisis_multiplier: Tightening scalar from RiskManager/CrisisDetector (<= 1.0).

        Returns:
            StopLossResult dataclass instance.
        """
        # 1. Standardize Data Extraction
        if isinstance(intraday_data, pd.DataFrame):
            if intraday_data.empty:
                return StopLossResult(False, symbol, 0.0, 1.0, "NONE", "NO_ACTION")
            
            prices = intraday_data['close'].values if 'close' in intraday_data.columns else intraday_data['Close'].values
            volumes = intraday_data['volume'].values if 'volume' in intraday_data.columns else intraday_data['Volume'].values
            highs = intraday_data['high'].values if 'high' in intraday_data.columns else (intraday_data['High'].values if 'High' in intraday_data.columns else prices)
            
            current_price = float(prices[-1])
            current_volume = float(volumes[-1])
            peak_price = float(np.max(highs))
            if entry_price is not None and entry_price > peak_price:
                peak_price = entry_price
            
            # Compute 20-period rolling average volume
            if len(volumes) >= 2:
                vol_window = volumes[-min(len(volumes), self.window_size):-1]
                vol_sma = float(np.mean(vol_window)) if len(vol_window) > 0 and np.mean(vol_window) > 0 else current_volume
            else:
                vol_sma = current_volume
                
            prev_price = float(prices[-2]) if len(prices) >= 2 else current_price

        elif isinstance(intraday_data, dict):
            current_price = float(intraday_data.get('current_price', 0.0))
            current_volume = float(intraday_data.get('volume', 0.0))
            peak_price = float(intraday_data.get('peak_price', current_price))
            if entry_price is not None and entry_price > peak_price:
                peak_price = entry_price
            vol_sma = float(intraday_data.get('volume_ma_20', current_volume))
            prev_price = float(intraday_data.get('prev_price', current_price))
            if atr is None and 'atr' in intraday_data:
                atr = float(intraday_data['atr'])
        else:
            raise ValueError(f"Unsupported intraday_data type: {type(intraday_data)}")

        if current_price <= 0.0:
            return StopLossResult(False, symbol, 0.0, 1.0, "INVALID_PRICE", "NO_ACTION")

        # 2. Update Internal State
        self.update_intraday_candle(symbol, current_price, current_volume, high=peak_price)
        tracked_peak = max(self._symbol_peaks.get(symbol, current_price), peak_price)

        # 3. Calculate Core Metrics
        drop_pct = (current_price - tracked_peak) / tracked_peak
        panic_volume_ratio = current_volume / max(vol_sma, 1e-6)
        instant_return = (current_price - prev_price) / max(prev_price, 1e-6)

        # Apply Crisis Multiplier to Drop Threshold (e.g. -4% * 0.8 = -3.2% when crisis active)
        effective_drop_threshold = self.peak_drop_threshold * crisis_multiplier

        # 4. Evaluate Stop Loss Rules
        reasons = []
        
        # Rule A: Peak-to-Trough Drop Detection (-4% default)
        is_peak_drop = drop_pct <= effective_drop_threshold

        # Rule B: Volume Spike Panic Detection (Volume surge > 3.0x with negative price return)
        is_panic_volume = (panic_volume_ratio >= self.volume_spike_threshold) and (instant_return < 0.0 or drop_pct < -0.01)

        # Rule C: Dynamic Trailing ATR / Volatility Adjusted Stop Breach
        is_atr_breach = False
        if atr is not None and atr > 0.0:
            effective_atr_mult = self.atr_multiplier * crisis_multiplier
            atr_stop_price = tracked_peak - (atr * effective_atr_mult)
            if current_price <= atr_stop_price:
                is_atr_breach = True

        # Synthesize Trigger Status
        triggered = is_peak_drop or is_panic_volume or is_atr_breach

        if is_peak_drop:
            reasons.append("PEAK_TO_TROUGH_DROP")
        if is_panic_volume:
            reasons.append("PANIC_VOLUME_SPIKE")
        if is_atr_breach:
            reasons.append("DYNAMIC_ATR_TRAILING_BREACH")

        if triggered:
            reason_str = " & ".join(reasons)
            rec_action = "FULL_LIQUIDATION" if (is_peak_drop or is_atr_breach) else "PARTIAL_REDUCTION_50"
        else:
            reason_str = "NONE"
            rec_action = "NO_ACTION"

        return StopLossResult(
            triggered=triggered,
            symbol=symbol,
            drop_pct=float(drop_pct),
            panic_volume_ratio=float(panic_volume_ratio),
            reason=reason_str,
            recommended_action=rec_action,
        )
```

---

## 4. RiskManager Integration Design

### 4.1 Integration into `trading_system/src/risk/risk_manager.py`

1. **Initialization**: Instantiates `IntradayStopLossEngine` inside `RiskManager.__init__()`.
2. **New Method: `evaluate_intraday_stop_loss()`**:
   ```python
   def evaluate_intraday_stop_loss(
       self,
       symbol: str,
       intraday_data: Union[pd.DataFrame, dict],
       entry_price: Optional[float] = None,
       atr: Optional[float] = None,
   ) -> StopLossResult:
       """
       Evaluates intraday stop-loss risk for a given symbol.
       Tightens thresholds based on active market crisis level.
       """
       crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()
       result = self.intraday_stop_loss_engine.evaluate(
           symbol=symbol,
           intraday_data=intraday_data,
           entry_price=entry_price,
           atr=atr,
           crisis_multiplier=crisis_mult,
       )
       if result.triggered:
           self._create_alert(
               alert_type=f"INTRADAY_STOP_LOSS_{result.reason}",
               symbol=symbol,
               current_price=getattr(result, 'current_price', 0.0),
               entry_price=entry_price or 0.0,
           )
           self.logger.warning(
               f"[INTRADAY STOP LOSS TRIGGERED] Symbol: {symbol} | Reason: {result.reason} | "
               f"Drop: {result.drop_pct:.2%} | Vol Ratio: {result.panic_volume_ratio:.2f}x | Action: {result.recommended_action}"
           )
       return result
   ```
3. **New Method: `check_intraday_risk()`**:
   ```python
   def check_intraday_risk(
       self,
       portfolio_intraday_data: Dict[str, Union[pd.DataFrame, dict]],
       positions: Optional[Dict[str, float]] = None,
   ) -> Dict[str, StopLossResult]:
       """
       Evaluates intraday stop-loss status across portfolio holdings or watchlist.
       Returns dictionary mapping symbol -> StopLossResult.
       """
       results = {}
       for symbol, data in portfolio_intraday_data.items():
           entry_price = positions.get(symbol) if positions else None
           res = self.evaluate_intraday_stop_loss(symbol, data, entry_price=entry_price)
           results[symbol] = res
       return results
   ```

---

## 5. Pipeline Execution Integration (`run_pipeline.py`)

In `trading_system/run_pipeline.py`, during Step 10 (Risk Management & Position Sizing phase around line 2445):

```python
# ── RiskManager & Intraday Stop-Loss Monitoring Phase ──
try:
    from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
    risk_mgr = RiskManager()
    
    # 1. Macro Crisis Evaluation
    crisis_lvl = risk_mgr.evaluate_crisis(
        vix=vix_val,
        usdkrw=usdkrw_val,
        oil=wti_val,
        tnx=us10y_val
    )
    logger.info(f"[RISK MANAGER] Market Crisis Level: {crisis_lvl.value}")
    
    # 2. Intraday Microstructure Stop-Loss Evaluation
    if 'infer_data_dict' in locals() and infer_data_dict:
        intraday_results = risk_mgr.check_intraday_risk(infer_data_dict)
        triggered_symbols = [sym for sym, res in intraday_results.items() if res.triggered]
        if triggered_symbols:
            logger.warning(f"[INTRADAY RISK] Intraday stop-loss triggered for {len(triggered_symbols)} symbols: {triggered_symbols}")
            # Zero out expected return / ensemble score for triggered symbols to block buy execution
            ensemble_df.loc[ensemble_df['symbol'].isin(triggered_symbols), 'ensemble_expected_return'] = -0.99
            ensemble_df.loc[ensemble_df['symbol'].isin(triggered_symbols), 'ensemble_score'] = 0.0

except Exception as _rm_e:
    logger.warning(f"RiskManager evaluation skipped: {_rm_e}")
```

---

## 6. Unit Test Specification (`test_intraday_stop_loss.py`)

The test suite in `trading_system/tests/test_intraday_stop_loss.py` validates all core behaviors:

```python
import unittest
import pandas as pd
import numpy as np

from src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossResult
from src.risk.risk_manager import RiskManager

class TestIntradayStopLossEngine(unittest.TestCase):

    def setUp(self):
        self.engine = IntradayStopLossEngine(
            peak_drop_threshold=-0.04,
            volume_spike_threshold=3.0,
            atr_multiplier=2.0,
        )

    def test_peak_to_trough_4pct_drop_triggers_stop_loss(self):
        """Test -4.5% drop from peak triggers PEAK_TO_TROUGH_DROP stop-loss."""
        data = {
            'current_price': 95.5,
            'peak_price': 100.0,
            'volume': 1000,
            'volume_ma_20': 1000,
        }
        res = self.engine.evaluate("005930", data)
        self.assertTrue(res.triggered)
        self.assertIn("PEAK_TO_TROUGH_DROP", res.reason)
        self.assertEqual(res.recommended_action, "FULL_LIQUIDATION")
        self.assertAlmostEqual(res.drop_pct, -0.045, places=3)

    def test_volume_spike_panic_detection_triggers_stop_loss(self):
        """Test 3.5x volume acceleration with negative price return triggers PANIC_VOLUME_SPIKE."""
        data = {
            'current_price': 98.5,
            'prev_price': 100.0,
            'peak_price': 100.0,
            'volume': 3500,
            'volume_ma_20': 1000,
        }
        res = self.engine.evaluate("005930", data)
        self.assertTrue(res.triggered)
        self.assertIn("PANIC_VOLUME_SPIKE", res.reason)
        self.assertGreaterEqual(res.panic_volume_ratio, 3.0)

    def test_normal_market_movement_no_trigger(self):
        """Test normal price movement (-1% drop, 1.2x volume) passes without trigger."""
        data = {
            'current_price': 99.0,
            'prev_price': 99.5,
            'peak_price': 100.0,
            'volume': 1200,
            'volume_ma_20': 1000,
        }
        res = self.engine.evaluate("005930", data)
        self.assertFalse(res.triggered)
        self.assertEqual(res.reason, "NONE")
        self.assertEqual(res.recommended_action, "NO_ACTION")

    def test_dynamic_atr_trailing_stop_breach(self):
        """Test dynamic ATR trailing stop breach triggers DYNAMIC_ATR_TRAILING_BREACH."""
        # Peak = 100.0, ATR = 2.0, Multiplier = 2.0 -> Stop level = 96.0
        data = {
            'current_price': 95.8,
            'peak_price': 100.0,
            'volume': 1000,
            'volume_ma_20': 1000,
            'atr': 2.0,
        }
        res = self.engine.evaluate("AAPL", data)
        self.assertTrue(res.triggered)
        self.assertIn("DYNAMIC_ATR_TRAILING_BREACH", res.reason)

    def test_dataframe_input_format(self):
        """Test evaluation using pandas DataFrame input."""
        dates = pd.date_range("2026-07-31 09:00", periods=20, freq="1min")
        df = pd.DataFrame({
            'open': np.linspace(100, 95, 20),
            'high': np.linspace(101, 95.5, 20),
            'low': np.linspace(99.5, 94.5, 20),
            'close': np.linspace(100, 95, 20),
            'volume': [1000] * 19 + [3500],
        }, index=dates)
        
        res = self.engine.evaluate("NVDA", df)
        self.assertTrue(res.triggered)

    def test_risk_manager_integration(self):
        """Test RiskManager's evaluate_intraday_stop_loss and check_intraday_risk methods."""
        rm = RiskManager(portfolio_value=1_000_000)
        data = {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000}
        
        res = rm.evaluate_intraday_stop_loss("005930", data)
        self.assertTrue(res.triggered)
        self.assertGreater(len(rm.alerts), 0)

        portfolio_data = {
            '005930': {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000},
            '000660': {'current_price': 99.5, 'peak_price': 100.0, 'volume': 1000, 'volume_ma_20': 1000},
        }
        batch_res = rm.check_intraday_risk(portfolio_data)
        self.assertEqual(len(batch_res), 2)
        self.assertTrue(batch_res['005930'].triggered)
        self.assertFalse(batch_res['000660'].triggered)

if __name__ == '__main__':
    unittest.main()
```
