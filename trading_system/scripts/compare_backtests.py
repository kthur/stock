import sys
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.backtest import BacktestEngine, PriceBar
from src.data_layer.market_data_handler import MarketDataHandler
from src.persistence.database import StockPriceDB
from src.config import TradingConfig

config = TradingConfig()
BACKTEST_YEARS = config.backtest_years


def ema_crossover_strategy(bars):
    if len(bars) < 30:
        return "HOLD"
    closes = [b.close for b in bars]
    def calc_ema(values, period):
        ema = [0.0] * len(values)
        if not values:
            return ema
        ema[0] = values[0]
        multiplier = 2.0 / (period + 1)
        for idx in range(1, len(values)):
            ema[idx] = (values[idx] - ema[idx - 1]) * multiplier + ema[idx - 1]
        return ema
    ema10 = calc_ema(closes, 10)
    ema30 = calc_ema(closes, 30)
    if ema10[-1] > ema30[-1]:
        return "BUY"
    elif ema10[-1] < ema30[-1]:
        return "SELL"
    return "HOLD"


def generate_deterministic_bars(symbol: str, dates: list) -> list:
    seed_val = int(hashlib.md5(symbol.encode('utf-8')).hexdigest(), 16) % (2**32)
    np.random.seed(seed_val)
    params = {
        "MSFT": {"price": 380.0, "vol": 0.015, "drift": 0.0004},
        "GOOGL": {"price": 150.0, "vol": 0.018, "drift": 0.0003},
        "AMZN": {"price": 170.0, "vol": 0.020, "drift": 0.0005},
        "005930.KS": {"price": 75000.0, "vol": 0.016, "drift": 0.0003},
        "000660.KS": {"price": 140000.0, "vol": 0.024, "drift": 0.0006},
        "035420.KS": {"price": 190000.0, "vol": 0.020, "drift": 0.0002},
    }
    config = params.get(symbol, {"price": 100.0, "vol": 0.020, "drift": 0.0003})
    price = config["price"]
    vol = config["vol"]
    drift = config["drift"]
    bars = []
    current_price = price
    for idx, dt in enumerate(dates):
        ret = np.random.normal(drift, vol)
        cycle_contrib = 0.006 * np.cos(2 * np.pi * idx / 40)
        current_price = current_price * (1.0 + ret + cycle_contrib)
        current_price = max(current_price, 0.01)
        daily_range = current_price * np.random.exponential(vol * 0.8)
        close_val = current_price
        open_val = close_val * (1.0 + np.random.normal(0, vol * 0.25))
        high_val = max(open_val, close_val) + daily_range * 0.5
        low_val = min(open_val, close_val) - daily_range * 0.5
        low_val = max(low_val, 0.01)
        volume = int(np.random.normal(1500000 if symbol.endswith(".KS") else 2000000, 300000))
        volume = max(volume, 50000)
        if hasattr(dt, "to_pydatetime"):
            pydt = dt.to_pydatetime()
        else:
            pydt = pd.to_datetime(dt).to_pydatetime()
        pydt = pydt.replace(tzinfo=None)
        bars.append(PriceBar(
            timestamp=pydt, open=open_val, high=high_val,
            low=low_val, close=close_val, volume=volume
        ))
    return bars


def load_data(symbol: str) -> list:
    """StockPriceDB → yfinance 순으로 데이터 로드. BACKTEST_YEARS는 .env 설정."""
    db = StockPriceDB(db_path=config.stock_price_db_path)

    if BACKTEST_YEARS == "all":
        period = "all"
        start_date = None
        label = "ALL"
    else:
        years = int(BACKTEST_YEARS)
        period = f"{years}y"
        start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
        label = f"{years}y"

    df = db.get_prices(symbol, start_date=start_date)
    if not df.empty:
        print(f"Loaded {symbol} ({label}) from StockPriceDB ({len(df)} rows)")
        cols = {c.lower(): c for c in df.columns}
        bars = []
        for date_idx, row in df.iterrows():
            pydt = date_idx.to_pydatetime() if hasattr(date_idx, "to_pydatetime") else pd.to_datetime(date_idx).to_pydatetime()
            pydt = pydt.replace(tzinfo=None)
            bars.append(PriceBar(
                timestamp=pydt,
                open=float(row[cols["open"]]),
                high=float(row[cols["high"]]),
                low=float(row[cols["low"]]),
                close=float(row[cols["close"]]),
                volume=int(row[cols["volume"]]),
            ))
        return bars

    print(f"Fetching {symbol} ({label}) from yfinance...")
    handler = MarketDataHandler()
    bars = handler.fetch_historical_data(symbol, period=period)

    if bars:
        print(f"Loaded {len(bars)} bars for {symbol} (fetched + cached)")
        return bars

    print(f"Falling back to synthetic data for {symbol}...")
    spy_path = Path("data/cache/SPY_1y.parquet")
    if BACKTEST_YEARS == "all":
        n_years = 10
    else:
        n_years = int(BACKTEST_YEARS)
    if spy_path.exists():
        spy_df = pd.read_parquet(spy_path)
        dates = list(spy_df.index) * n_years
    else:
        start = datetime.now() - timedelta(days=365 * n_years)
        dates = [start + timedelta(days=i) for i in range(252 * n_years)]
    return generate_deterministic_bars(symbol, dates)


def run_comparative_backtests():
    symbols = [
        "SPY", "AAPL", "MSFT", "GOOGL", "AMZN",
        "005930.KS", "000660.KS", "035420.KS"
    ]

    results = {}
    for symbol in symbols:
        price_bars = load_data(symbol)
        if not price_bars:
            print(f"Error: No data available for {symbol}")
            continue

        engine_base = BacktestEngine(initial_capital=1000000)
        res_base = engine_base.run_backtest(
            symbol=symbol,
            price_bars=price_bars,
            strategy_func=ema_crossover_strategy,
            volatility_sizing=False,
            stop_loss_pct=0.05,
            take_profit_pct=0.15,
            atr_trailing_stop_mult=0.0
        )

        engine_enh = BacktestEngine(initial_capital=1000000)
        res_enh = engine_enh.run_backtest(
            symbol=symbol,
            price_bars=price_bars,
            strategy_func=ema_crossover_strategy,
            volatility_sizing=True,
            stop_loss_pct=0.05,
            take_profit_pct=0.15,
            atr_trailing_stop_mult=2.0
        )

        results[symbol] = {"baseline": res_base, "enhanced": res_enh}

    print("\n" + "="*80)
    label = "ALL" if BACKTEST_YEARS == "all" else f"{BACKTEST_YEARS}-YEAR"
    print(f"BACKTEST COMPARISON RESULTS ({label})")
    print("="*80)

    table_rows = []
    for symbol, config in results.items():
        base = config["baseline"]
        enh = config["enhanced"]

        def calc_annualized_return(final, initial, start_dt, end_dt):
            days = (end_dt - start_dt).days
            if days > 0:
                return ((final / initial) ** (365.25 / days) - 1.0) * 100.0
            return 0.0

        ann_ret_base = calc_annualized_return(base.final_capital, base.initial_capital, base.start_date, base.end_date)
        ann_ret_enh = calc_annualized_return(enh.final_capital, enh.initial_capital, enh.start_date, enh.end_date)

        m_base = {
            "CumRet": base.total_return_pct, "AnnRet": ann_ret_base,
            "Sharpe": base.sharpe_ratio, "MaxDD": base.max_drawdown * 100,
            "WinRate": base.win_rate * 100, "ProfitFactor": base.profit_factor
        }
        m_enh = {
            "CumRet": enh.total_return_pct, "AnnRet": ann_ret_enh,
            "Sharpe": enh.sharpe_ratio, "MaxDD": enh.max_drawdown * 100,
            "WinRate": enh.win_rate * 100, "ProfitFactor": enh.profit_factor
        }

        print(f"\nTicker: {symbol}  ({base.start_date.date()} ~ {base.end_date.date()})")
        print(f"  {'Metric':<20} | {'Baseline':<12} | {'Enhanced':<12} | {'Change':<12}")
        print(f"  {'-'*20}-|-{'-'*12}-|-{'-'*12}-|-{'-'*12}")
        for key in m_base.keys():
            diff = m_enh[key] - m_base[key]
            sign = "+" if diff >= 0 else ""
            val_format = ".2f" if key != "ProfitFactor" else ".3f"
            base_str = f"{m_base[key]:{val_format}}"
            enh_str = f"{m_enh[key]:{val_format}}"
            if key == "ProfitFactor" and m_base[key] == float('inf'):
                base_str = "inf"
            if key == "ProfitFactor" and m_enh[key] == float('inf'):
                enh_str = "inf"
            diff_str = f"{sign}{diff:{val_format}}" if (m_base[key] != float('inf') and m_enh[key] != float('inf')) else "N/A"
            if key in ["CumRet", "AnnRet", "MaxDD", "WinRate"]:
                base_str += "%"
                enh_str += "%"
                diff_str += "%" if diff_str != "N/A" else ""
            print(f"  {key:<20} | {base_str:<12} | {enh_str:<12} | {diff_str:<12}")

        table_rows.append({
            "Symbol": symbol,
            "Base_CumRet": m_base["CumRet"], "Enh_CumRet": m_enh["CumRet"],
            "Base_AnnRet": m_base["AnnRet"], "Enh_AnnRet": m_enh["AnnRet"],
            "Base_Sharpe": m_base["Sharpe"], "Enh_Sharpe": m_enh["Sharpe"],
            "Base_MaxDD": m_base["MaxDD"], "Enh_MaxDD": m_enh["MaxDD"],
            "Base_WinRate": m_base["WinRate"], "Enh_WinRate": m_enh["WinRate"],
            "Base_ProfitFactor": m_base["ProfitFactor"], "Enh_ProfitFactor": m_enh["ProfitFactor"],
        })

    df_results = pd.DataFrame(table_rows)
    df_results.to_csv("scripts/backtest_comparison_results.csv", index=False)
    print("\nResults exported to scripts/backtest_comparison_results.csv")


if __name__ == "__main__":
    run_comparative_backtests()
