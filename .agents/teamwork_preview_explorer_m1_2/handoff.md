# Handoff Report - Strategy Sizing and Asset Allocation Audit

## 1. Observation
We observed the following in the codebase:
*   **Position Sizing Entrance**: In `trading_system/trading_system.py`, order creation triggers a multi-stage position sizing pipeline:
    *   Line 524: `quantity = await self._compute_position_size(...)`
    *   Line 554: calls `self.risk_manager.calculate_position_sizing(...)` to get the baseline trade size.
*   **Baseline Sizing Logic**: In `trading_system/src/risk/risk_manager.py`:
    *   Lines 525–580 define `calculate_position_sizing(self, symbol, entry_price, stop_loss_price, win_rate, win_loss_ratio, vix)`.
    *   Lines 542–544: Kelly Criterion: `kelly_pct = self.calculate_kelly_fraction(win_rate, win_loss_ratio)` and `max_value = self.portfolio_value * kelly_pct`.
    *   Lines 546–547: Fixed Risk Sizing: `max_loss = self.portfolio_value * self.max_loss_per_trade_pct` and `max_value = max_loss * (entry_price / risk_per_share)`.
    *   Lines 549–550: Volatility scaling: `max_value *= vol_scalar` where `vol_scalar` is `20.0 / vix` (clamped).
    *   Lines 553–556: VIX Cap: `vix_cap = self.get_vix_position_cap(vix)` clamps `max_value` to a percentage of the portfolio.
    *   Lines 563–570: Crisis Multiplier: scales down size by `crisis_mult = self.crisis_detector.get_crisis_position_multiplier()`.
*   **Pipeline Adjustments**: In `trading_system/trading_system.py:546-737`, the quantity is adjusted through 13 sequential filters:
    *   Conservative Ramp (line 571)
    *   Volatility Targeting (line 583) using `get_volatility_scaler()`
    *   Confidence-based Sizing (line 593)
    *   Crisis Cash Target (line 602)
    *   Macro Score Sizing (line 615)
    *   Earnings Date Protection (line 626)
    *   Information Ratio (line 635)
    *   Multi-timeframe Trend Confirmation (line 645)
    *   Concentration Check (line 661) calling `_get_correlation_adjusted_limit` (line 1682)
    *   Market Impact Clamp (line 682)
    *   Correlation Regime Sizing (line 698)
    *   VIX Risk-Off Cash Clamp (line 715)
    *   Available Cash Check (line 729)
*   **Asset Allocator classes**:
    *   Defined in `trading_system/src/strategy/asset_allocation.py` (lines 53–171) which supports:
        *   `_equal_weight(self, tickers)` (line 107)
        *   `_risk_parity(self, price_data)` (line 112) calling `calculate_risk_parity_weights(cov_matrix)` in `src/analysis/portfolio_optimizer.py`.
        *   `_momentum(self, price_data)` (line 149)
    *   `calculate_risk_parity_weights` (in `trading_system/src/analysis/portfolio_optimizer.py:9-113`) solves log-barrier optimization: `0.5 * w.T @ cov_matrix @ w - sum(log(w))` using L-BFGS-B, falling back to SLSQP, inverse-volatility, or equal-weighting.
*   **Engine Decoupling**:
    *   `HybridStrategyEngine.analyze(...)` generates directional trade signals and confidence, but does not use `AssetAllocator`.
    *   `TradingSystem` executes per-trade sizing on entry, but does not invoke `AssetAllocator` for joint portfolio asset weighting.
*   **Test Suit Execution**:
    *   Ran `python -m pytest` inside `trading_system` with output:
        `347 passed, 2 skipped, 14 warnings in 125.89s (0:02:05)`

## 2. Logic Chain
1.  **Observation**: Sizing is determined trade-by-trade on entry in `TradingSystem._compute_position_size` using either the volatility-blind Kelly fraction or the ATR-based fixed risk sizing from `RiskManager.calculate_position_sizing`.
2.  **Observation**: `AssetAllocator` is located in `src/strategy/asset_allocation.py` and provides a true Risk Parity solver.
3.  **Observation**: Neither `HybridStrategyEngine` nor `TradingSystem` references or instantiates `AssetAllocator` in their core logic.
4.  **Inference**: The live trading system is completely decoupled from the portfolio-level `AssetAllocator`. Sizing decisions are made locally per-asset on entry, followed by a series of sequential heuristic filters (including correlation and volatility targeting), rather than through a joint portfolio optimizer.
5.  **Conclusion**: True Risk Parity or Volatility Sizing can be implemented by (A) scaling individual Kelly fractions by relative asset volatility, (B) integrating `AssetAllocator` for scheduled (e.g. weekly) portfolio rebalancing, or (C) scaling the risk-per-trade fraction based on the macro/volatility regime.

## 3. Caveats
*   We did not audit broker integration for live execution (e.g. multi-broker routing).
*   We assumed historical price bars are always populated and available for indicators (ATR, weekly EMAs, and standard deviation).

## 4. Conclusion
The current trading system determines target trade sizes at entry on an individual asset basis using either Kelly Criterion (fixed-fractional) or Fixed Risk Sizing (ATR-based volatility sizing), adjusted by a 13-stage pipeline. The standalone `AssetAllocator` supports equal weight, Risk Parity, and momentum but is decoupled from live execution. We recommend implementing dynamic position sizing via Volatility-Adjusted Kelly Sizing, periodic Risk Parity rebalancing, or Regime-Adaptive Risk-Unit Sizing.

## 5. Verification Method
*   Inspect `analysis.md` for detailed mathematical formulations and pipeline steps.
*   To verify test suite functionality:
    ```powershell
    cd d:\Finance\code\stock\trading_system
    python -m pytest
    ```
