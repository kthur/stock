# Audit Report: Asset Allocation and Position Sizing

## Executive Summary
This report audits the position sizing mechanisms and asset allocation classes in the trading system. Currently, position sizing is performed on a trade-by-trade basis at entry using either a volatility-blind Kelly Criterion or an ATR-based Fixed Risk method, further adjusted by a multi-stage pipeline. The standalone `AssetAllocator` module (supporting Risk Parity) is completely decoupled from the live trading execution system.

---

## 1. How Position Sizes Are Determined (Current State)

Position sizing is initiated when `TradingSystem._create_and_submit_order` calls the position sizing pipeline in `_compute_position_size(...)`. Sizing undergoes a baseline calculation in the `RiskManager` followed by 13 pipeline filters in the `TradingSystem`.

### 1.1 Baseline Position Sizing (`RiskManager.calculate_position_sizing`)
Located at `trading_system/src/risk/risk_manager.py:525`, the baseline size is determined through two distinct paths:

*   **Path A: Kelly Criterion** (Active if `win_rate > 0` and `win_loss_ratio > 0`):
    *   Calculates the Kelly fraction:
        $$f^* = \text{win\_rate} - \frac{1 - \text{win\_rate}}{\text{win\_loss\_ratio}}$$
    *   Applies a "Half Kelly" (divided by 2) for conservative operation if enabled.
    *   Capped at `max_position_size_pct` (default: 25% of portfolio value).
    *   Allocates capital as: $\text{Capital} = \text{portfolio\_value} \times f^*$.
    *   *Audit observation*: This method is **volatility-blind** (allocates fixed capital fractions regardless of asset risk, except for price scaling).
*   **Path B: Fixed Risk Sizing** (Active if Kelly parameters are missing/inactive):
    *   Calculates the risk per share: $\text{risk\_per\_share} = \text{entry\_price} - \text{stop\_loss\_price}$.
    *   If ATR is available, the stop-loss is calculated dynamically (e.g., $\text{entry\_price} - \text{ATR} \times \text{stop\_multiplier}$).
    *   Caps trade risk at a fixed percentage of the portfolio: $\text{max\_loss} = \text{portfolio\_value} \times \text{max\_loss\_per\_trade\_pct}$ (default: 2%).
    *   Allocates capital as:
        $$\text{Capital} = \text{max\_loss} \times \left( \frac{\text{entry\_price}}{\text{risk\_per\_share}} \right)$$
    *   This translates directly to **ATR-based Volatility Sizing**:
        $$\text{Quantity} = \frac{\text{Portfolio Value} \times \text{max\_loss\_per\_trade\_pct}}{\text{ATR} \times \text{stop\_multiplier}}$$

### 1.2 Volatility and Risk Multipliers in `RiskManager`
The baseline capital allocation is subsequently adjusted by:
1.  **VIX Volatility Scalar**: Scales capital by `20.0 / VIX` (bounded between $0.25\text{x}$ and $1.5\text{x}$).
2.  **VIX Risk-Off Cap**: Hard caps the position size as a percentage of the portfolio based on VIX thresholds:
    *   $\text{VIX} > 30 \implies 15\%$ cap
    *   $\text{VIX} > 25 \implies 30\%$ cap
    *   $\text{VIX} > 20 \implies 50\%$ cap
    *   Else $\implies 100\%$ cap
3.  **Crisis Position Multiplier**: Scaled down by `CrisisDetector` depending on the system-wide crisis stage:
    *   `WATCH` $\implies 0.70$
    *   `ACTIVE` $\implies 0.40$
    *   `SEVERE` $\implies 0.15$
4.  **Absolute Caps**: Clamped to the absolute max single position size (`max_position_size_pct` of the portfolio) and symbol-specific limits.

### 1.3 Sizing Pipeline Filters (`TradingSystem._compute_position_size`)
Located at `trading_system/trading_system.py:546`, the quantity is sequentially scaled/clamped:
*   **Conservative Ramp**: Scales size down by $0.3\text{x} \to 1.0\text{x}$ if the total trade count is less than `_conservative_until`.
*   **Volatility Targeting**: Scales quantity by `get_volatility_scaler()` which adjusts standard deviation of daily returns over the last 10 days to match a target annualized volatility (default: 15%).
*   **Confidence Sizing**: Scales quantity by $0.5 + \text{confidence} \times 0.5$.
*   **Crisis Cash Ratio Sizing**: Scales size down if cash is below the crisis cash target.
*   **Macro Score**: Scales size down by $\max(0.3, \text{macro\_score})$ if the macro score is below $0.30$.
*   **Earnings Protection**: Halves size if earnings announcement is in $\le 5$ days.
*   **Information Ratio Sizing**: Adjusts size based on the asset's Information Ratio.
*   **Weekly Trend Confirmation**: Halves size if the weekly EMA20 < EMA50 (bearish).
*   **Concentration Check**: Clamps size based on a correlation-adjusted limit. If highly correlated ($r > 0.7$) with existing holdings, the limit is reduced.
*   **Market Impact Clamp**: Scales down if order size is $>2\%$ of average daily volume; caps at $5\%$.
*   **Correlation Regime**: Scales down by $25\%$ if average pairwise correlation of all held assets is $>0.8$.
*   **VIX Risk-Off switch**: If VIX $\ge 25$, clamps quantity to guarantee at least $70\%$ cash ratio remains post-trade.

---

## 2. Asset Allocation Classes and Strategy Engine Interactions

### 2.1 Asset Allocation Classes
The system defines allocation strategies in `trading_system/src/strategy/asset_allocation.py`. The `AssetAllocator` class supports:
*   **Equal Weight (`_equal_weight`)**: Weights all assets as $1/N$ and normalizes them.
*   **Risk Parity (`_risk_parity`)**:
    *   Computes returns from historical price series and aligns series lengths.
    *   Calculates the covariance matrix of returns.
    *   Invokes `calculate_risk_parity_weights` (defined in `trading_system/src/analysis/portfolio_optimizer.py`).
    *   `calculate_risk_parity_weights` uses SciPy's `minimize` solver with the log-barrier objective:
        $$\text{Minimize: } 0.5 \times w^T \Sigma w - \sum \log(w)$$
        under L-BFGS-B. If that fails, it falls back to a variance difference minimization under SLSQP.
    *   If numerical optimization fails, it falls back to **inverse-volatility weighting**:
        $$w_i \propto \frac{1}{\sigma_i}$$
        and finally to equal weighting if inverse-volatility is not computable.
*   **Momentum (`_momentum`)**: Weights assets proportionally to the total return series ($\text{last\_price} / \text{first\_price}$).

### 2.2 System Interactions and Decoupling
*   **Strategy Engine**: `HybridStrategyEngine` (in `trading_system/src/core/strategy_engine.py`) acts purely as a signal generator. It calculates buy/sell/hold decisions and confidence values. It **does not interact with or instantiate** `AssetAllocator` or use any portfolio weighting algorithms.
*   **Trading System**: `TradingSystem` (in `trading_system.py`) does not call `AssetAllocator` or run portfolio-level asset allocation. It executes on a trade-by-trade basis. Position sizes are determined individually as trades arrive, and correlation controls are applied post-sizing via local pairwise checks (`_get_correlation_adjusted_limit`).

---

## 3. Recommendations for Dynamic Position Sizing

To properly integrate risk-based sizing and bridge the gap between decoupled modules, we recommend three implementation options:

### Recommendation A: Volatility-Adjusted Kelly Sizing (Blended Sizing)
*   **Concept**: Modify the Kelly Criterion path in `RiskManager.calculate_position_sizing` to be volatility-aware.
*   **Implementation**: Scale the Kelly fraction by the ratio of target volatility to asset volatility.
    $$\text{Adjusted } f^* = f^* \times \left( \frac{\sigma_{\text{target}}}{\sigma_{\text{asset}}} \right)$$
    *   $\sigma_{\text{target}}$: Annualized target volatility (e.g. 15%).
    *   $\sigma_{\text{asset}}$: Annualized standard deviation of the asset's daily returns.
    This ensures that higher-volatility assets receive smaller capital allocations for the same Kelly signal.

### Recommendation B: Periodic Risk Parity Portfolio Rebalancing
*   **Concept**: Use the existing `AssetAllocator.allocate` and `PortfolioManager.compute_rebalance_plan` to implement a scheduled rebalancing cycle instead of relying only on trade-by-trade entry sizing.
*   **Implementation**:
    1.  Create a weekly rebalancing routine in `TradingSystem`.
    2.  For all currently held positions plus new buy candidates, fetch historical prices.
    3.  Call `AssetAllocator(strategy="risk_parity").allocate(prices_dict)` to compute optimal portfolio weights.
    4.  Pass the weights to `PortfolioManager.compute_rebalance_plan(target_weights, market_prices)` to generate the rebalance order list and execute it.

### Recommendation C: Regime-Adaptive Risk-Unit Sizing (Dynamic Fixed Risk)
*   **Concept**: Replace the static `max_loss_per_trade_pct` (currently 2%) with a dynamic risk unit that contracts during high volatility or negative regimes.
*   **Implementation**:
    1.  Scale `max_loss_per_trade_pct` using VIX or the active crisis level:
        $$\text{adaptive\_risk} = \text{max\_loss\_per\_trade\_pct} \times \max\left(0.25, \min\left(1.5, \frac{20.0}{\text{VIX}}\right)\right)$$
    2.  Or scale by crisis level:
        *   `NONE` $\implies 2.0\%$ risk per trade
        *   `WATCH` $\implies 1.5\%$ risk per trade
        *   `ACTIVE` $\implies 1.0\%$ risk per trade
        *   `SEVERE` $\implies 0.5\%$ risk per trade
    3.  Calculate the trade quantity as:
        $$\text{Quantity} = \frac{\text{Portfolio Value} \times \text{adaptive\_risk}}{\text{ATR} \times \text{stop\_multiplier}}$$
