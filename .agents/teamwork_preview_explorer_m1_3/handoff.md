# Handoff Report - Backtesting Framework Exploration

## 1. Observation

I directly observed the structure, parameters, and algorithms of the backtesting and optimization engine in the `trading_system/` workspace.

### Core Backtesting Module (`trading_system/src/analysis/backtest.py`)
*   **Engine Definition**:
    ```python
    class BacktestEngine:
        POSITION_SIZE_FRACTION = 0.95
        ...
        def run_backtest(
            self,
            symbol: str,
            price_bars: List[PriceBar],
            strategy_func,
            target_period_bars: Optional[int] = None,
            allow_short: bool = False,
            trailing_stop_pct: float = 0.0,
            scale_in: bool = False,
            stop_loss_pct: float = 0.0,
            take_profit_pct: float = 0.0,
            market_regime_filter: bool = False,
            volatility_sizing: bool = False,
            atr_trailing_stop_mult: float = 0.0,
        ) -> BacktestResult:
    ```
*   **Volatility Sizing Logic**:
    ```python
    if volatility_sizing:
        atr = self._calc_atr(price_bars[:i], 14)
        if atr > 0:
            risk_amount = capital * 0.02
            qty = int(risk_amount / (2 * atr))
            max_qty = int(capital * size_fraction / bar.open)
            position = min(qty, max_qty)
            if position <= 0:
                position = max_qty
        else:
            position = int(capital * size_fraction / bar.open)
    ```
*   **ATR Trailing Stop Logic**:
    ```python
    if atr_trailing_stop_mult > 0.0:
        atr = self._calc_atr(price_bars[: i + 1], 14)
        if atr > 0:
            ts_trigger = max(ts_trigger, trailing_peak - (atr * atr_trailing_stop_mult))
    ```
*   **Metric Calculation Logic**:
    *   *Win Rate* (Line 814): `winning_trades = sum(1 for t in trades if t.pnl > 0)` / `len(trades)`
    *   *Profit Factor* (Line 822): `gross_profit / gross_loss`
    *   *Maximum Drawdown* (Line 835): Tracks rolling `peak` and computes `dd = (peak - value) / peak`.
    *   *Sharpe Ratio* (Line 856): Annualized using daily returns: `((avg_return - risk_free_rate / 252) / std_dev) * (252**0.5)`.

### Data Loading & Ticker Management (`trading_system/src/data_layer/market_data_handler.py`)
*   **Historical Data Fetching**:
    ```python
    def fetch_historical_data(self, symbol: str, period: str = "10y") -> List[Any]:
    ```
    Uses `yfinance` to load ticker data: `ticker = yf.Ticker(symbol)` and `ticker.history(period=period)`.
*   **Local Cache**: Saves results in Parquet format to `trading_system/data/cache/{symbol}_{period}.parquet`. Cache checks file modification date to see if it is younger than 24 hours (Line 208).

### Stock Universe Mappings (`trading_system/src/utils/stock_list.py`)
*   **Suffixes**: Resolves Korean stock names using FinanceDataReader or a fallback dictionary, returning tickers with `.KS` or `.KQ` suffixes (e.g. `"삼성전자": "005930.KS"`).

### Verification Runner (`verify_adaptive.py`)
*   **Verification Script**: Contains a runner script that demonstrates baseline vs adaptive comparison via `run_backtest_comparison` (Line 160) and saves the aggregate metrics as JSON in `trading_system/data/verification_results.json`.

---

## 2. Logic Chain

1.  **Backtest Engine Execution**: Since `BacktestEngine.run_backtest` takes explicit parameters for `volatility_sizing` and `atr_trailing_stop_mult`, baseline runs and enhanced runs are distinguished by passing these flags accordingly (with baseline having them set to `False`/`0.0`, and enhanced having them set to `True`/`mult > 0`).
2.  **Data Fetching Scope**: Since `MarketDataHandler` fetches data through Yahoo Finance, it requires correct ticker formatting. Standard US tickers resolve natively, but KRX tickers require suffixes (`.KS` for KOSPI, `.KQ` for KOSDAQ). Any comparative backtest script must append the suffix for KRX codes before invoking `fetch_historical_data`.
3.  **Metrics Generation**: The `BacktestEngine` calculates return, Sharpe ratio, MDD, win rate, and profit factor. Advanced statistics are calculated by `AdvancedStatistics` in `src/analysis/statistics.py`. A comparative script can fetch these directly from the engine output or pass the equity curves to `AdvancedStatistics.get_performance_summary()` for deep metrics aggregation.

---

## 3. Caveats

*   **API Limits**: `MarketDataHandler` enforces rate limits (5 queries/sec) and a circuit breaker (5 failures -> 60s timeout). When running backtests over a large universe of assets, API throttling might be triggered.
*   **KRX Suffix Mapping**: The test universe in `verify_adaptive.py` has raw 6-digit codes (`"005930"`, `"000660"`). If passed directly, yfinance will fail or query incorrect symbols. The comparative backtester must append the correct suffixes (`.KS` / `.KQ`) or map them using `KoreanStockList`.

---

## 4. Conclusion

The backtesting framework is ready to support comparative backtesting. We can construct a comparative script using the existing `BacktestEngine` and `MarketDataHandler` modules by toggling the `volatility_sizing` and `atr_trailing_stop_mult` parameters to compare baseline and enhanced configurations. Aggregated metrics (Cumulative Return, Sharpe, MDD, Win Rate, and Profit Factor) can be computed cleanly via `AdvancedStatistics` and printed as a markdown table.

---

## 5. Verification Method

To independently verify the backtesting engine and parameter loader:
1.  Verify the baseline tests on the adaptive optimization framework:
    `python verify_adaptive.py --quick`
2.  Inspect the resulting output file `trading_system/data/verification_results.json` to verify the generated performance statistics for static and adaptive runs.
3.  Inspect `trading_system/src/analysis/backtest.py` and `trading_system/src/analysis/statistics.py` to confirm the formulas used for metric calculations.
