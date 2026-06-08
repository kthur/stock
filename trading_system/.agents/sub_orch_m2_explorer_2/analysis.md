# Analysis Report: Market Regime Detection & Weight Adaptation (R2)

## 1. Executive Summary
This report defines the implementation plan to support **Requirement R2: Market Regime Detection & Weight Adaptation** within `src/core/strategy_engine.py` for the Phase 4 Trading System Upgrade. Currently, the `HybridStrategyEngine` class lacks `detect_regime()` and `set_strategy_parameters()` methods, causing 12 E2E tests in `tests/phase4/e2e/test_e2e.py` to fail with `AttributeError`. 

The proposed solution introduces:
- A robust `detect_regime()` method that validates inputs, calculates trend and momentum over 200 bars using EMA200 and ROC20, and returns `bull`, `bear`, or `sideways`.
- Dynamic, non-cumulative weight adaptation where technical weight shifts and the sell threshold adjusts lower (to `0.35`) in a bear market.
- Clean weight normalization that ensures weights remain strictly in `[0.0, 1.0]` and sum to exactly `1.0`.

---

## 2. Detailed Findings & Requirements Analysis

### A. Missing Methods on `HybridStrategyEngine`
- **`detect_regime(price_bars: List[Any]) -> Literal["bull", "bear", "sideways"]`**
  - Must evaluate trend regime.
  - Must perform validation of price bar objects (check for missing high/low/close attributes or keys).
  - Must fall back to `"sideways"` for lists with less than 200 bars.
  - Must handle constant prices (where ROC = 0, volatility = 0) without division-by-zero errors.
- **`set_strategy_parameters(strategy_name: str, parameters: Dict[str, Any]) -> None`**
  - Must store the parameter configurations (e.g. for `"MA"`) to satisfy combination tests.

### B. Weight and Threshold Adaptation
- **Bull regime**: `technical_weight` adapts upwards.
- **Bear regime**: `sell_threshold` is reduced below `0.45` (e.g., set to `0.35`).
- **State management**: Adjustments should be non-cumulative. Restoring base configurations when the regime changes prevents weights and thresholds from drifting to extreme values over multiple calls.

### C. Normalization & Value Guards
- To guarantee that weights remain in `[0.0, 1.0]` and sum to exactly `1.0`, we must apply non-negativity clipping (`max(0.0, weight)`) and division by the sum of all weights. A division-by-zero guard must be placed in case the sum of weights is zero (falling back to equal weights).

---

## 3. Precise Code Modification Plan

The following changes are proposed for `src/core/strategy_engine.py`.

### Modification 1: Initialize Baseline Tracking in `__init__`
In the constructor of `HybridStrategyEngine` (around line 83):
```python
        # Initialize baseline attributes for regime tracking and normalization
        self._baseline_weights = {
            "sentiment": self.sentiment_weight,
            "technical": self.technical_weight,
            "ml": self.ml_weight,
            "rl": self.rl_weight,
            "darkpool": self.darkpool_weight,
            "llm": self.llm_weight
        }
        self._baseline_sell_threshold = self.sell_threshold
        self._in_regime_adaptation = False
```

### Modification 2: Refactor `_normalize_weights`
Update the `_normalize_weights` method (lines 501-518) to ensure non-negativity and dynamically update baselines when outside of a temporary regime adjustment:
```python
    def _normalize_weights(self) -> None:
        # Safeguard weights against negative values and out-of-bounds inputs
        self.sentiment_weight = max(0.0, self.sentiment_weight)
        self.technical_weight = max(0.0, self.technical_weight)
        self.ml_weight = max(0.0, self.ml_weight)
        self.rl_weight = max(0.0, self.rl_weight)
        self.darkpool_weight = max(0.0, self.darkpool_weight)
        self.llm_weight = max(0.0, self.llm_weight)
        
        total = (self.sentiment_weight + self.technical_weight +
                 self.ml_weight + self.rl_weight +
                 self.darkpool_weight + self.llm_weight)
        if total == 0:
            # Revert to equal weights fallback
            self.sentiment_weight = 1.0 / 6
            self.technical_weight = 1.0 / 6
            self.ml_weight = 1.0 / 6
            self.rl_weight = 1.0 / 6
            self.darkpool_weight = 1.0 / 6
            self.llm_weight = 1.0 / 6
            total = 1.0
            
        self.sentiment_weight /= total
        self.technical_weight /= total
        self.ml_weight /= total
        self.rl_weight /= total
        self.darkpool_weight /= total
        self.llm_weight /= total
        
        # Save baseline weights only if we are not in the middle of temporary regime adjustments
        if not getattr(self, "_in_regime_adaptation", False):
            self._baseline_weights = {
                "sentiment": self.sentiment_weight,
                "technical": self.technical_weight,
                "ml": self.ml_weight,
                "rl": self.rl_weight,
                "darkpool": self.darkpool_weight,
                "llm": self.llm_weight
            }
            
        self.logger.info(
            f"Weights normalized: sentiment={self.sentiment_weight:.3f} "
            f"technical={self.technical_weight:.3f} ml={self.ml_weight:.3f} "
            f"rl={self.rl_weight:.3f} darkpool={self.darkpool_weight:.3f} "
            f"llm={self.llm_weight:.3f}"
        )
```

### Modification 3: Implement `detect_regime` and Support Methods
Add the following methods to `HybridStrategyEngine`:
```python
    from typing import Literal

    def detect_regime(self, price_bars: List[Any]) -> Literal["bull", "bear", "sideways"]:
        """
        Identify market regime based on EMA200 trend, ROC20 momentum, and volatility.
        Adapts strategy weights and thresholds dynamically.
        """
        if not price_bars:
            return "sideways"
            
        # 1. Missing fields check (raises ValueError if high, low, or close is missing/None)
        for b in price_bars:
            if isinstance(b, dict):
                h = b.get("high")
                l = b.get("low")
                c = b.get("close")
            else:
                h = getattr(b, "high", None)
                l = getattr(b, "low", None)
                c = getattr(b, "close", None)
            if h is None or l is None or c is None:
                raise ValueError("Price bars must contain valid 'high', 'low', and 'close' fields.")
                
        # 2. Insufficient bars check (fallback to sideways for <200 bars)
        if len(price_bars) < 200:
            return "sideways"
            
        # 3. Extract close prices
        closes = []
        for b in price_bars:
            if isinstance(b, dict):
                closes.append(float(b["close"]))
            else:
                closes.append(float(getattr(b, "close")))
                
        current_close = closes[-1]
        
        # 4. Calculate Indicators (EMA 200 and ROC 20)
        ema200 = self._calc_ema(closes, 200)[-1]
        
        # Calculate ROC 20 momentum (using absolute denominator to protect negative prices in mocks)
        close_prev20 = closes[-20]
        if close_prev20 != 0:
            roc20 = (current_close - close_prev20) / abs(close_prev20)
        else:
            roc20 = 0.0
            
        # 5. Determine Regime
        if current_close > ema200 and roc20 > 0.01:
            regime = "bull"
        elif current_close < ema200 and roc20 < -0.01:
            regime = "bear"
        else:
            regime = "sideways"
            
        # 6. Apply dynamic weight/threshold adaptation
        self._apply_regime_adaptations(regime)
        
        return regime

    def _apply_regime_adaptations(self, regime: Literal["bull", "bear", "sideways"]) -> None:
        """Helper to modify strategy weights and thresholds based on regime state."""
        # Ensure baseline values are registered
        if not hasattr(self, "_baseline_weights"):
            self._baseline_weights = {
                "sentiment": self.sentiment_weight,
                "technical": self.technical_weight,
                "ml": self.ml_weight,
                "rl": self.rl_weight,
                "darkpool": self.darkpool_weight,
                "llm": self.llm_weight
            }
        if not hasattr(self, "_baseline_sell_threshold"):
            self._baseline_sell_threshold = self.sell_threshold

        # Restore weights and sell_threshold to baseline first (non-cumulative adaptation)
        self.sentiment_weight = self._baseline_weights["sentiment"]
        self.technical_weight = self._baseline_weights["technical"]
        self.ml_weight = self._baseline_weights["ml"]
        self.rl_weight = self._baseline_weights["rl"]
        self.darkpool_weight = self._baseline_weights["darkpool"]
        self.llm_weight = self._baseline_weights["llm"]
        self.sell_threshold = self._baseline_sell_threshold

        # Set flag to prevent _normalize_weights from overwriting our baseline mid-adaptation
        self._in_regime_adaptation = True
        try:
            if regime == "bull":
                # Increase technical weight (e.g. multiply by 1.5 and ensure positive shift)
                self.technical_weight = max(self.technical_weight * 1.5, self.technical_weight + 0.1)
                self._normalize_weights()
            elif regime == "bear":
                # Reduce sell threshold to trigger exit orders more aggressively
                self.sell_threshold = min(self.sell_threshold - 0.1, 0.35)
                # Shifting technical weight downwards (e.g. half) as technical signals might be less reliable
                self.technical_weight *= 0.5
                self._normalize_weights()
            else:
                # Sideways regime requires no adjustments; normalizing keeps baseline weights
                self._normalize_weights()
        finally:
            self._in_regime_adaptation = False

    def set_strategy_parameters(self, strategy_name: str, parameters: Dict[str, Any]) -> None:
        """Sets external strategy configurations (e.g., short_window) dynamically."""
        if not hasattr(self, "strategy_parameters"):
            self.strategy_parameters = {}
        self.strategy_parameters[strategy_name] = parameters
```

---

## 4. Verification Plan

1. **Unit Test Execution**:
   Verify that all 12 test cases matching `*r2*` pass cleanly:
   ```powershell
   python -m pytest tests/phase4/e2e/test_e2e.py -k "r2"
   ```
2. **Behavior Verification**:
   - `test_r2_detect_regime_bull`: Verify it returns `"bull"`.
   - `test_r2_detect_regime_bear`: Verify it returns `"bear"`.
   - `test_r2_detect_regime_sideways`: Verify it returns `"sideways"`.
   - `test_r2_bull_weight_adaptation`: Verify `engine.technical_weight > 0.2`.
   - `test_r2_bear_sell_threshold`: Verify `engine.sell_threshold < 0.45`.
   - `test_r2_detect_regime_insufficient_bars`: Verify fallback to `"sideways"`.
   - `test_r2_detect_regime_constant_price`: Verify it doesn't divide by zero and returns `"sideways"`.
   - `test_r2_detect_regime_missing_fields`: Verify it raises `ValueError`.
   - `test_r2_weight_adaptation_bounds`: Verify weights sum to `1.0` and stay in `[0.0, 1.0]`.
   - `test_r2_extreme_regime_transition`: Verify correct transition handling.
