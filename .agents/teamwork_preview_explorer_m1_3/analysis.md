# Comparative Backtesting Framework Analysis

This report documents the structure and components of the backtesting framework in the `trading_system/` codebase, explains how data is loaded, how metrics are calculated, and outlines how to construct a comparative backtesting script.

---

## 1. Backtesting Engine & Runner Identification

The codebase implements its backtesting engine and parameter optimization routines through several core modules:

*   **Main Engine**: `trading_system/src/analysis/backtest.py`
    *   Defines `PriceBar` (OHLCV structure), `BacktestTrade` (individual execution details), and `BacktestResult` (aggregated performance data).
    *   Contains `BacktestEngine`, which manages the main simulation loop (`run_backtest`), transaction costs (fees, slippage, market impact), indicator caches, and parameter optimization (`optimize_parameters` and `walk_forward_optimize`).
*   **Adaptive Optimizer**: `trading_system/src/analysis/adaptive_optimizer.py`
    *   Manages recency-weighted Bayesian parameter optimization using a Tree-structured Parzen Estimator (`TPESampler`).
    *   Stores and loads optimized parameters (e.g. regime-specific thresholds, ATR multipliers, and stop levels) in `trading_system/data/adaptive_params.json`.
*   **Verification / Runner Script**: `verify_adaptive.py` (in workspace root)
    *   Verifies the adaptive optimizer phases.
    *   Implements a sample runner comparison in `run_backtest_comparison()` that loads historical data, runs a simple strategy under static and adaptive configurations, and saves the comparison metrics to `trading_system/data/verification_results.json`.

---

## 2. Historical Data Loading (S&P 500 vs. KRX)

Historical stock data is loaded through `MarketDataHandler.fetch_historical_data` in `trading_system/src/data_layer/market_data_handler.py`.

### A. Universe Definition & Fetching Suffixes
*   **S&P 500 Tickers**: Standard tickers (e.g., `"SPY"`, `"QQQ"`, `"AAPL"`, `"MSFT"`) are queried directly.
*   **KRX Tickers**: To query Korean stocks on Yahoo Finance via `yfinance`, tickers must end with a region suffix:
    *   KOSPI stocks require `.KS` (e.g., Samsung Electronics `"005930.KS"`).
    *   KOSDAQ stocks require `.KQ` (e.g., EcoPro BM `"247540.KQ"`).
*   *Caveat*: In some test runners like `verify_adaptive.py`, raw 6-digit codes like `"005930"` are specified. Unless these are converted or matched to their `.KS` suffix using the `KoreanStockList` utility (`trading_system/src/utils/stock_list.py`), yfinance calls on raw 6-digit codes will fail or return empty datasets.

### B. Caching Mechanism
*   Fetched historical data is stored as `.parquet` files under `trading_system/data/cache/` (e.g., `AAPL_3mo.parquet`).
*   For each query, the handler checks if the cache file exists and if its modification time is less than **24 hours** old. If fresh, it loads directly from the local cache. Otherwise, it downloads from `yfinance` and overwrites the cache.

---

## 3. Return and Metric Calculations

Performance metrics are computed in both `BacktestEngine` and `AdvancedStatistics` (`trading_system/src/analysis/statistics.py`):

### A. Cumulative Return
*   **Absolute Return**: `final_capital - initial_capital`
*   **Percentage Return**: `(total_return / initial_capital) * 100`

### B. Sharpe Ratio
Annualized Sharpe Ratio is calculated as:
$$\text{Sharpe} = \frac{\text{Mean Daily Return} - \frac{\text{Risk Free Rate}}{252}}{\text{Std Dev of Daily Returns}} \times \sqrt{252}$$
*   Daily returns $r_i$ are calculated as: $\frac{\text{Equity}_i - \text{Equity}_{i-1}}{\text{Equity}_{i-1}}$.
*   The default `risk_free_rate` is `0.02` (2% annually).

### C. Maximum Drawdown (MDD)
Tracks the peak equity value and calculates the largest drop from peak:
$$\text{Drawdown}_t = \frac{\text{Peak}_t - \text{Equity}_t}{\text{Peak}_t}$$
$$\text{MDD} = \max(\text{Drawdown}_t)$$

### D. Win Rate
$$\text{Win Rate} = \frac{\text{Count of Trades where PnL} > 0}{\text{Total Count of Trades}}$$

### E. Profit Factor
$$\text{Profit Factor} = \frac{\sum \text{PnL of Winning Trades}}{\sum \left| \text{PnL of Losing Trades} \right|}$$

---

## 4. Comparative Backtesting Script Design

To construct a comparative script that runs both baseline (static stops, simple weight sizing) and enhanced (volatility-based sizing, adaptive stops, regime-dependent parameters) configurations, we can define a python runner script.

Below is the structured outline of how this script should be implemented:

```python
import os
import sys
import json
import pandas as pd
from datetime import datetime

# Adjust Python path to resolve imports correctly
WORKSPACE_DIR = "d:/Finance/code/stock"
TRADING_SYS_DIR = os.path.join(WORKSPACE_DIR, "trading_system")
sys.path.insert(0, os.path.join(TRADING_SYS_DIR, "src"))
os.chdir(TRADING_SYS_DIR)

from analysis.backtest import BacktestEngine
from analysis.adaptive_optimizer import AdaptiveParameterOptimizer, DEFAULT_PARAMS
from data_layer.market_data_handler import MarketDataHandler
from analysis.statistics import AdvancedStatistics

def run_comparison():
    # 1. Initialize Components
    engine = BacktestEngine(initial_capital=1000000)
    handler = MarketDataHandler()
    stats = AdvancedStatistics(risk_free_rate=0.02)
    
    # Load optimized parameters
    adaptive_params = AdaptiveParameterOptimizer.load_params()
    
    # 2. Define Test Universe (S&P 500 & KRX with correct suffixes)
    universe = [
        "SPY", "QQQ", "AAPL", "MSFT", 
        "005930.KS", "000660.KS"  # Suffixes added for KRX stocks
    ]
    
    # 3. Strategy Logic (e.g., Simple RSI/MACD strategy)
    class TestStrategy:
        def __init__(self, params):
            self.params = params
            
        def __call__(self, bars):
            closes = [b.close for b in bars]
            if len(closes) < 20:
                return "HOLD"
            # Simple RSI/trend indicator
            rsi_val = 50 + (sum(1 for c in closes[-5:] if c > closes[-6]) * 10)
            if rsi_val > 60:
                return "BUY"
            elif rsi_val < 40:
                return "SELL"
            return "HOLD"

    results = []

    for symbol in universe:
        # Load historical data
        bars = handler.fetch_historical_data(symbol, period="1y")
        if not bars or len(bars) < 50:
            print(f"Skipping {symbol} due to insufficient data.")
            continue
            
        # --- BASELINE RUN ---
        baseline_strat = TestStrategy(DEFAULT_PARAMS)
        baseline_res = engine.run_backtest(
            symbol=symbol,
            price_bars=bars,
            strategy_func=baseline_strat,
            volatility_sizing=False,       # Simple position sizing
            atr_trailing_stop_mult=0.0,    # No ATR trailing stops
            stop_loss_pct=0.02,            # Static stop loss
            trailing_stop_pct=0.05         # Static trailing stop
        )
        
        # --- ENHANCED RUN ---
        enhanced_strat = TestStrategy(adaptive_params)
        # Load adaptive stop levels from params
        trail_pct = adaptive_params.get("trail_pct", 0.04)
        
        # Use a middle-regime stop multiplier (e.g., weak_bull stop = 2.0)
        atr_stop_mult = adaptive_params.get("atr_multipliers", {}).get("weak_bull", {}).get("stop", 2.0)
        
        enhanced_res = engine.run_backtest(
            symbol=symbol,
            price_bars=bars,
            strategy_func=enhanced_strat,
            volatility_sizing=True,                    # Volatility sizing enabled
            atr_trailing_stop_mult=atr_stop_mult,      # Dynamic ATR trailing stop
            stop_loss_pct=0.02,                        # Dynamic/regime stop loss
            trailing_stop_pct=trail_pct                # Dynamic trailing stop pct
        )
        
        # 4. Aggregate Metrics
        # Retrieve summaries from AdvancedStatistics
        baseline_summary = stats.get_performance_summary(
            baseline_res.equity_curve, 
            [{"pnl": t.pnl} for t in baseline_res.trades]
        )
        enhanced_summary = stats.get_performance_summary(
            enhanced_res.equity_curve, 
            [{"pnl": t.pnl} for t in enhanced_res.trades]
        )
        
        results.append({
            "Symbol": symbol,
            "Baseline Return": f"{baseline_summary['total_return'] * 100:.2f}%",
            "Enhanced Return": f"{enhanced_summary['total_return'] * 100:.2f}%",
            "Baseline Sharpe": f"{baseline_summary['sharpe_ratio']:.2f}",
            "Enhanced Sharpe": f"{enhanced_summary['sharpe_ratio']:.2f}",
            "Baseline MDD": f"{baseline_summary['max_drawdown'] * 100:.2f}%",
            "Enhanced MDD": f"{enhanced_summary['max_drawdown'] * 100:.2f}%",
            "Baseline WinRate": f"{baseline_summary['win_rate'] * 100:.1f}%",
            "Enhanced WinRate": f"{enhanced_summary['win_rate'] * 100:.1f}%",
            "Baseline PF": f"{baseline_summary['profit_factor']:.2f}",
            "Enhanced PF": f"{enhanced_summary['profit_factor']:.2f}"
        })
        
    # 5. Output Tabular Comparison
    df_results = pd.DataFrame(results)
    print("\n" + "=" * 80)
    print("COMPARATIVE BACKTESTING REPORT (BASELINE VS ENHANCED)")
    print("=" * 80)
    print(df_results.to_markdown(index=False))

if __name__ == "__main__":
    run_comparison()
```
