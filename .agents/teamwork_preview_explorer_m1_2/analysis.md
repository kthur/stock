# Comprehensive Audit Report: Backtest Engine & Risk Management System (Requirement R2)

**Author:** Explorer 2  
**Date:** 2026-07-29  
**Milestone:** M1 — Baseline Exploration & Audit  
**Working Directory:** `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2`  

---

## 1. Executive Summary

This report presents a thorough, evidence-based audit of the **Backtest Engine & Risk Management System (R2)** within the Stock Trading System repository. The audit evaluates:
1. **Backtesting Modules**: `trading_system/src/analysis/backtest.py`, `backtest_summary.py`, `compare_backtests.py`.
2. **Performance Tracking Metrics**: Sharpe ratio, Max Drawdown (MDD), win rate, profit factor, net return after transaction costs, and recency-weighted metrics.
3. **Risk Management Systems**: Liquidity filtering, volatility-based position sizing (VIX, ATR, Kelly Criterion), dynamic risk limits (ATR trailing stops, crisis detection levels, sector risk caps, KIS execution safety caps).
4. **Test Suite Coverage**: Inspection of `test_backtest.py`, `test_risk_manager.py`, `test_risk_enhancements.py`, `test_portfolio_risk.py`, `test_kelly_sizing.py`, `test_kis_safety_and_atr.py`.
5. **Gaps & Enhancement Opportunities**: Identification of structural gaps between single-asset backtesting and multi-asset 14-strategy dynamic ensemble backtesting.

---

## 2. Examination of Backtesting Modules

### 2.1 Code Structure & Architecture (`trading_system/src/analysis/backtest.py`)
- **Primary Class**: `BacktestEngine` (1,618 lines).
- **Core Dataclasses**:
  - `PriceBar` (`trading_system/src/analysis/backtest.py:20-28`): OHLCV bar representation (`timestamp`, `open`, `high`, `low`, `close`, `volume`).
  - `BacktestTrade` (`trading_system/src/analysis/backtest.py:32-47`): Trade record (`entry_date`, `entry_price`, `exit_date`, `exit_price`, `quantity`, `pnl`, `pnl_pct`, `direction`, `exit_reason`, `duration`).
  - `BacktestResult` (`trading_system/src/analysis/backtest.py:51-72`): Comprehensive result object containing summary statistics, equity curves, price curves, dates, trade lists, and trailing stop counts.

### 2.2 Execution & Signal Handling Mechanism
- **Non-Lookahead Execution Loop** (`backtest.py:345-501`):
  - Signals evaluated at bar $i$ close (`pending_signal = strategy_func(price_bars[:i+1])`).
  - Orders executed at bar $i+1$ open (`bar.open`), eliminating look-ahead bias.
- **Intra-Bar Risk & Exit Management** (`backtest.py:504-643`):
  - Real-time intra-bar checking against `bar.high` and `bar.low`.
  - Exits evaluated in order: (1) Partial Take-Profit (`take_profit_pct`), (2) Stop Loss (`stop_loss_pct`), (3) Percentage Trailing Stop (`trailing_stop_pct`), and (4) ATR Trailing Stop (`atr_trailing_stop_mult`).
- **Scale-In Entry (Pyramiding)** (`backtest.py:644-670`):
  - 2-phase entry (50% initial, 50% scale-in) triggered when price moves >2% in favor.
- **Short Selling** (`backtest.py:397-447`, `601-638`, `706-725`):
  - Full short selling and cover simulation with reverse-position flipping logic.

### 2.3 Transaction Cost & Market Impact Modeling
- **Fee & Slippage Model** (`backtest.py:81-83`, `91-111`):
  - `fee_pct = 0.001` (0.1% broker commission).
  - `slippage_pct = 0.001` (0.1% slippage).
  - Square-root market impact model:
    $$\text{impact} = \text{market\_impact\_pct} \times \sqrt{\frac{\text{volume}}{\max(\text{avg\_volume}, 1.0)}}$$
  - Net cost entry/exit functions (`_cost_to_buy`, `_cost_to_sell`, `_cost_entry`, `_cost_exit`) ensure fees and slippage reduce total return and trade PnL.

---

## 3. Portfolio Performance Tracking Metrics

### 3.1 Standard Metrics Implementation
1. **Sharpe Ratio** (`backtest.py:858-885`):
   - Annualized using 252 trading days:
     $$\text{Sharpe} = \frac{\bar{R} - \frac{R_f}{252}}{\sigma_R} \times \sqrt{252}$$
   - Default risk-free rate $R_f = 0.02$ (2%).
2. **Max Drawdown (MDD)** (`backtest.py:837-856`):
   - Peak-to-trough decline across `equity_curve`:
     $$\text{MDD} = \max_{t} \left( \frac{\text{Peak}_t - \text{Equity}_t}{\text{Peak}_t} \right)$$
3. **Win Rate** (`backtest.py:816-823`):
   - Ratio of trades with $\text{PnL} > 0$ over total trades.
4. **Profit Factor** (`backtest.py:825-835`):
   - Gross profit divided by gross loss ($\sum \text{PnL}_{\text{win}} / |\sum \text{PnL}_{\text{loss}}|$).

### 3.2 Advanced Recency-Weighted Metrics (`backtest.py:1534-1617`)
- Uses exponential time decay weights ($w_i = e^{-\lambda \Delta t}$) based on trade exit dates.
- Metrics calculated: `_recency_weighted_sharpe`, `_recency_weighted_mdd`, `_recency_weighted_win_rate`, `_recency_weighted_profit_factor`.
- Recency-Weighted Composite Score:
  $$\text{Score} = 0.40 \times \text{Sharpe}_{\text{norm}} + 0.30 \times (1 - \text{MDD}_{\text{norm}}) + 0.15 \times \text{WinRate} + 0.15 \times \text{ProfitFactor}_{\text{norm}}$$

---

## 4. Risk Management Implementation Audit

### 4.1 Crisis Detector (`trading_system/src/risk/risk_manager.py:35-253`)
- **4 Crisis Levels**: `NONE`, `WATCH`, `ACTIVE`, `SEVERE`.
- **Composite Risk Score**:
  $$\text{Composite} = 0.25 \times \text{VIX} + 0.25 \times \text{Drawdown} + 0.15 \times \text{VolumeSpike} + 0.10 \times \text{TrendBreakdown} + 0.25 \times \text{MacroScore}$$
  where MacroScore evaluates USD/KRW exchange rate spikes, WTI oil surge ($100+), 10Y US Treasury yield (^TNX), and Dollar Index (DXY).
- **Crisis Response Escalation Matrix**:
  | Crisis Level | Cash Target % | Position Multiplier | Stop Multiplier | Action |
  |--------------|---------------|---------------------|-----------------|--------|
  | `NONE` | 10% | 1.00x | 1.00x | Normal Trading |
  | `WATCH` | 30% | 0.70x | 0.80x | Cautionary Tightening |
  | `ACTIVE` | 60% | 0.40x | 0.60x | High Risk Reduction |
  | `SEVERE` | 85% | 0.15x | 0.40x | Block New Buys (`should_block_new_buys`) |

- **Emergency Liquidation**: Triggered when in `SEVERE` for $\ge 3$ consecutive days (`risk_manager.py:250-252`).
- **Recovery Mode**: 20-day linear exposure restoration after crisis condition resolves (`risk_manager.py:104-111`).

### 4.2 Volatility-Based Position Sizing & Kelly Criterion
- **Kelly Criterion Allocation** (`trading_system/src/risk/position_sizing.py:160-166`):
  - Variance-matched 20-day horizon formula:
    $$f^* = \text{kelly\_fraction} \times \frac{\text{net\_return}}{20 \times \sigma_{\text{daily}}^2}$$
  - Regime-Adaptive Kelly fractions: Bull (0.40), Bear (0.15), Sideways (0.25).
- **Robust Kelly Safeguards** (`risk_manager.py:591-612`):
  - Half Kelly default.
  - Scaling by trade history count ($n / 50$).
  - Consecutive Loss Cooldown: 3 losses (50%), 5 losses (25%), 7 losses (6.25%), 10 losses (trading halt).
- **Volatility Scaling** (`risk_manager.py:471-473`, `613-619`):
  - VIX-based scalar: $\max(0.25, \min(1.5, 20.0 / \text{VIX}))$.
  - Composite Volatility Scalar: VIX (40%) + ATR ratio (35%) + Bollinger Band width (25%).

### 4.3 Dynamic Risk Limits & Execution Safety
- **ATR Dynamic Trailing Stop** (`risk_manager.py:364-435`):
  - Adaptive ATR multipliers per regime: `strong_bull` (3.0x stop, 5.0x target), `weak_bull` (2.5x stop, 4.0x target), `weak_bear` (1.5x stop, 2.5x target), `strong_bear` (1.0x stop, 2.0x target).
  - ADX adjustment: ADX > 30 (+20% multiplier boost), ADX < 20 (-20% multiplier reduction).
  - Drawdown tightening scaler: $(1 - \text{Drawdown} / \text{MaxDrawdownAllowed})$.
- **Sector Risk Cap**: 30% maximum sector exposure limit enforced in `RiskManager.check_sector_risk_cap()` (`risk_manager.py:446-468`) and `PortfolioAllocator.allocate()` (`position_sizing.py:194-206`).
- **Broker Safety Guards** (`src/broker/korea_investment.py`, `real_broker.py`):
  - Single order max value cap: 50,000,000 KRW ($50\text{M KRW}$).
  - Limit price sanity bound: $\pm 3\%$ max price deviation from current market price.

---

## 5. Audit Findings & Gap Analysis (Requirement R2)

| # | Item / Feature | Current Codebase Implementation | Requirement R2 Gap / Status |
|---|---|---|---|
| 1 | **Single-Symbol vs. Multi-Asset Portfolio Backtest** | `BacktestEngine` runs symbol-by-symbol backtests. `PortfolioAllocator` optimizes weights on candidate data. | **Gap**: Lack of a unified multi-asset backtest loop that simulates 3,379 symbols concurrently with daily rebalancing, portfolio cash drag, sector caps, and multi-symbol capital constraints. |
| 2 | **14-Strategy Dynamic Ensemble Backtest Integration** | `BacktestEngine.get_strategy_func()` supports classic technical indicators (`MA`, `RSI`, `MACD`, `BOLLINGER`, etc.). | **Gap**: Strategies #6 through #14 (Causal LSTM, Stat-Arb, Sector Rotation, RIM, Event-Driven, MQ Factor, IV Skew, Order Flow, Short-Term Reversal) are implemented in `src/core/` and `src/ai/ensemble_scorer.py`, but not directly exposed as strategy choices in `BacktestEngine`. |
| 3 | **Transaction Cost Parameter Consistency** | `BacktestEngine` uses 0.1% fee + 0.1% slippage + sqrt market impact. `PortfolioAllocator` uses 20d daily trading value tiers (0.26% - 0.85%). `EnsembleScoringEngine` uses liquidity tiers (20/50/100 bps). | **Minor Gap**: Slight variation in transaction cost tier parameters across modules. Standardizing cost constants across backtester, allocator, and ensemble scorer will ensure 100% net-return alignment. |
| 4 | **Recency-Weighted Performance Metrics** | Implemented in `BacktestEngine.recency_weighted_score()` using exponential decay ($\lambda=0.02$). | **Fully Implemented**: Provides robust multi-objective scoring (Sharpe 40%, MDD 30%, WinRate 15%, ProfitFactor 15%). |
| 5 | **Risk Management & Execution Safety** | `RiskManager`, `CrisisDetector`, `PortfolioAllocator`, ATR trailing stops, KIS 50M KRW cap, $\pm 3\%$ price sanity bounds, 30% sector caps. | **Fully Implemented & Verified**: Robust multi-tier crisis detection and execution guards are fully tested and operational. |

---

## 6. Recommendations for Next Milestones (M2 / M3)

1. **Multi-Asset Ensemble Backtest Integration (M3)**:
   - Create a multi-asset simulation wrapper in `trading_system/src/analysis/backtest.py` or `trading_system/src/analysis/portfolio_backtest.py` that interfaces directly with `EnsembleScoringEngine` to run 14-strategy backtests across the full 3,379 universe.
2. **Unified Transaction Cost Model**:
   - Centralize transaction cost calculations into `TradingConfig` / `src/utils/` so `BacktestEngine`, `PortfolioAllocator`, and `EnsembleScoringEngine` reference identical fee, slippage, and liquidity-impact constants.
3. **Automated End-to-End Backtest Summary Generation**:
   - Connect `backtest_summary.py` directly to the execution of `BacktestEngine` OOS runs to dynamically populate `trading_system/result/backtest_summary.json` during pipeline execution.
