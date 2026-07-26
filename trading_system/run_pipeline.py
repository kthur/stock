import os
import sys
import logging
import socket
import time
import threading
import traceback
from datetime import datetime
from typing import Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import FinanceDataReader as fdr
import yfinance as yf
import warnings

cpu_count = os.cpu_count()
_CPU_WORKERS: int = max(1, cpu_count if cpu_count is not None else 4)
_PER_SYMBOL_TIMEOUT = 30  # seconds per symbol before skipping

# Rate limiter for network requests (shared across threads)
_rate_lock = threading.Lock()
_last_request_time = 0.0

# Reconfigure stdout to UTF-8 to prevent UnicodeEncodeError on Windows (cp949)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Set default socket timeout to prevent hanging connections
socket.setdefaulttimeout(5)

# Ignore Pandas pct_change FutureWarning to keep logs clean
warnings.filterwarnings('ignore', category=FutureWarning)

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.config import TradingConfig
from src.data_layer.global_market import GlobalMarketClient
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.data_layer.earnings_data import fetch_and_store_fundamentals_batch
from src.ai.prediction_model import OnDevicePredictionModel
from src.ai.vcp_ml_predictor import VCPSurgePredictor, SURGE_HORIZONS
from src.persistence.database import StockPriceDB
from src.risk.position_sizing import PortfolioAllocator
from src.analysis.regime_detector import MarketRegimeDetector
from src.utils.rate_limiter import get_global_rate_limiter
from src.utils.technical_cache import DataFrameCache
from src.utils.http_session import setup_global_http_headers
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result, retry_if_exception_type

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize global HTTP session headers for yfinance and FinanceDataReader calls
setup_global_http_headers()

# P3: Rotating file logger — persists logs across terminal sessions and GHA log expiry
def _setup_rotating_logger() -> None:
    """Attach a RotatingFileHandler to the root logger (10MB × 5 backups)."""
    from logging.handlers import RotatingFileHandler
    from pathlib import Path
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "pipeline.log"
    file_handler = RotatingFileHandler(
        str(log_path),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    logging.getLogger().addHandler(file_handler)
    logger.info(f"[P3] RotatingFileHandler attached: {log_path}")

_setup_rotating_logger()



# ---------------------------------------------------------------------------
# P0: Telegram notification utility
# Reads TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID from env.
# Severity levels: INFO / SUCCESS / WARNING / CRITICAL
# ---------------------------------------------------------------------------
def _notify_telegram(msg: str, level: str = "INFO", buttons: list | None = None) -> None:
    """Send a Telegram notification with severity level badge.

    Args:
        msg:     Message body (Markdown).
        level:   INFO / SUCCESS / WARNING / CRITICAL
        buttons: Optional list-of-rows for Telegram InlineKeyboard.
                 Each row is a list of dicts: [{"text": "...", "url": "..."}]
                 Example: [[{"text": "📈 GHA", "url": "https://..."}]]

    No-ops silently when env vars are missing (local dev without bot).
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    icons = {
        "INFO": "\u2139\ufe0f",
        "SUCCESS": "\u2705",
        "WARNING": "\u26a0\ufe0f",
        "CRITICAL": "\U0001f6a8",
    }
    icon = icons.get(level, "\u2139\ufe0f")
    border = "\u2500" * 30
    text = f"{border}\n{icon} *[{level}] Pipeline Alert*\n{border}\n{msg}"
    try:
        import json
        import urllib.request
        import urllib.parse
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload: dict = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if buttons:
            payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        logger.debug("[Telegram] Notification sent (%s)", level)
    except Exception as e:
        logger.debug("[Telegram] Notification failed: %s", e)

technical_cache = DataFrameCache()

def is_empty_result(result):
    if result is None:
        return True
    if isinstance(result, pd.DataFrame) and result.empty:
        return True
    return False


# yfinance suffix mapping for Korean stock markets
_KR_MARKET_SUFFIX = {
    'KOSPI': '.KS',
    'KOSDAQ': '.KQ',
    'KONEX': '.KQ',
    'KRX': '.KS',
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=True
)
def _fetch_data_fdr_network(symbol: str, market: str, start_date: str) -> pd.DataFrame:
    # Enforce global rate limit coordination
    get_global_rate_limiter().wait()

    result = None

    if market in ('SP500', 'NYSE', 'NASDAQ') or not symbol.isdigit():
        yf_symbol = symbol
    else:
        suffix = _KR_MARKET_SUFFIX.get(market, '.KS')
        yf_symbol = f"{symbol}{suffix}"

    # Tier 1: Try yfinance primary download
    try:
        df = yf.download(yf_symbol, start=start_date, progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            result = df
    except Exception as e:
        logger.debug(f"Tier 1 (yfinance) network fetch failed for {yf_symbol}: {e}")

    # Tier 2: Secondary provider fallback (FinanceDataReader)
    if result is None or result.empty:
        try:
            logger.debug(f"Attempting Tier 2 (FinanceDataReader) download for {symbol}...")
            result = fdr.DataReader(symbol, start=start_date)
            if result is not None and not result.empty:
                logger.warning(f"Successfully retrieved Tier 2 (FinanceDataReader) data for {symbol}")
        except Exception as e:
            logger.debug(f"Tier 2 (FinanceDataReader) network fetch failed for {symbol}: {e}")
            raise e

    if result is None or result.empty:
        raise ValueError(f"Fetched data for {symbol} is empty or None across all providers")

    return result


def prefetch_prices_batch(symbols: list, symbol_market: dict, start_date: str,
                          price_db: Optional[StockPriceDB], freshness_days: int = 1):
    """Prefetch price data in batches from yfinance and store in SQLite DB to speed up subsequent queries."""
    if price_db is None or not symbols:
        return

    # Find symbols that actually need update
    symbols_to_update = []
    symbol_start_dates = {}

    for sym in symbols:
        if price_db.needs_update(sym, max_age_days=freshness_days, start_date=start_date):
            latest = price_db.get_latest_date(sym)
            if latest is not None:
                symbol_start_dates[sym] = latest
            else:
                symbol_start_dates[sym] = start_date
            symbols_to_update.append(sym)

    if not symbols_to_update:
        logger.info("All symbols are up-to-date in cache. No prefetching needed.")
        return

    logger.info(f"Prefetching {len(symbols_to_update)} symbols in batches...")

    from collections import defaultdict
    date_groups = defaultdict(list)
    for sym in symbols_to_update:
        date_groups[symbol_start_dates[sym]].append(sym)

    # Fetch in batches for each date group
    for fetch_start, group_syms in date_groups.items():
        batch_size = 100
        for i in range(0, len(group_syms), batch_size):
            batch = group_syms[i:i+batch_size]

            ticker_to_sym = {}
            yf_tickers = []
            for sym in batch:
                market = symbol_market.get(sym, 'SP500')
                if market == 'SP500' or market.startswith('NYSE') or market.startswith('NASDAQ'):
                    yf_ticker = sym
                else:
                    suffix = _KR_MARKET_SUFFIX.get(market, '.KS')
                    yf_ticker = f"{sym}{suffix}"
                yf_tickers.append(yf_ticker)
                ticker_to_sym[yf_ticker] = sym

            logger.info(f"Downloading batch of {len(batch)} symbols starting from {fetch_start}...")

            # ---------------------------------------------------------------------------
            # P2: Data Quality Gate — validate OHLCV data before storing to DB
            # ---------------------------------------------------------------------------
            def _validate_price_data(sym: str, df: pd.DataFrame) -> bool:
                """Return True if data passes quality checks, False if it should be skipped.

                Checks:
                  1. Close <= 0 or NaN ratio > 50% → reject
                  2. Daily return absolute value > 100% on more than 5% of rows → suspicious
                  3. Volume == 0 ratio > 90% → likely halted/suspended
                """
                if df is None or df.empty:
                    return False

                # Normalize column casing
                cols_lower = {str(c).lower(): c for c in df.columns}
                close_col = cols_lower.get('close')
                volume_col = cols_lower.get('volume')

                if close_col is None:
                    logger.warning(f"[DataQualityGate] {sym}: missing Close column, skipping")
                    return False

                close = df[close_col].astype(float)
                total_rows = len(close)

                # 1. Close zero/negative or too many NaN
                nan_ratio = close.isna().sum() / total_rows
                valid_close = close.dropna()
                non_positive = (valid_close <= 0).sum()
                if nan_ratio > 0.5:
                    logger.warning(f"[DataQualityGate] {sym}: Close NaN ratio={nan_ratio:.1%} > 50%, skipping")
                    return False
                if len(valid_close) > 0 and non_positive / len(valid_close) > 0.5:
                    logger.warning(f"[DataQualityGate] {sym}: Close non-positive ratio > 50%, skipping")
                    return False

                # 2. Extreme daily returns (> ±100% on more than 5% of rows)
                if len(valid_close) >= 5:
                    daily_ret = valid_close.pct_change().abs().dropna()
                    extreme_ratio = (daily_ret > 1.0).sum() / len(daily_ret)
                    if extreme_ratio > 0.05:
                        logger.warning(f"[DataQualityGate] {sym}: extreme return ratio={extreme_ratio:.1%} > 5%, skipping")
                        return False

                # 3. Volume zero ratio (likely suspended/halted ticker)
                if volume_col is not None:
                    volume = df[volume_col].astype(float)
                    zero_vol_ratio = (volume == 0).sum() / total_rows
                    if zero_vol_ratio > 0.90:
                        logger.debug(f"[DataQualityGate] {sym}: Volume zero ratio={zero_vol_ratio:.1%} > 90% (halted), skipping")
                        return False

                return True

            def _download_with_recovery(tickers: list, start_dt: str) -> pd.DataFrame:
                if not tickers:
                    return pd.DataFrame()
                try:
                    df_res = yf.download(tickers, start=start_dt, progress=False, auto_adjust=True, group_by='ticker')
                    if df_res is not None and not df_res.empty:
                        return df_res
                except Exception as ex:
                    # If batch is size 1, it's the failing ticker
                    if len(tickers) == 1:
                        logger.warning(f"Excluding bad ticker from batch: {tickers[0]} due to: {ex}")
                        return pd.DataFrame()

                # Binary split
                mid = len(tickers) // 2
                left_tickers = tickers[:mid]
                right_tickers = tickers[mid:]
                logger.info(f"Retrying batch split: Left={len(left_tickers)}, Right={len(right_tickers)}")

                df_left = _download_with_recovery(left_tickers, start_dt)
                df_right = _download_with_recovery(right_tickers, start_dt)

                if df_left.empty:
                    return df_right
                if df_right.empty:
                    return df_left
                # Merge along axis=1 (columns/tickers)
                return pd.concat([df_left, df_right], axis=1)

            try:
                df = _download_with_recovery(yf_tickers, fetch_start)
                if df is not None and not df.empty:
                    for yf_ticker in yf_tickers:
                        sym = ticker_to_sym.get(yf_ticker)
                        if not sym:
                            continue
                        ticker_df = None
                        if len(yf_tickers) == 1:
                            ticker_df = df
                        elif isinstance(df.columns, pd.MultiIndex):
                            # In yfinance >= 0.2.40, Ticker is at level 1
                            if yf_ticker in df.columns.get_level_values(1):
                                ticker_df = df.xs(yf_ticker, level=1, axis=1).dropna(how='all')
                        elif yf_ticker in df.columns:
                            # Single-level columns fallback
                            ticker_df = df[[yf_ticker]].dropna(how='all')

                        if ticker_df is not None and not ticker_df.empty:
                            if isinstance(ticker_df.columns, pd.MultiIndex):
                                ticker_df.columns = ticker_df.columns.droplevel(1)
                            # P2: Data Quality Gate — reject bad data before DB write
                            if _validate_price_data(sym, ticker_df):
                                price_db.update_prices(sym, ticker_df)
            except Exception as e:
                logger.warning(f"Failed to process download batch: {e}")


def fetch_data_fdr(symbol: str, market: str, start_date: str,
                   price_db: Optional[StockPriceDB] = None, freshness_days: int = 7,
                   update_interval: int = 0) -> pd.DataFrame:
    """Fetch OHLCV data using adjusted prices, with 3-tier fallback (yfinance -> FDR -> stock_prices.db cache)."""
    def _fetch_fallback(s: str, d: str) -> pd.DataFrame:
        global _last_request_time
        cached_df = None

        # 1. DB cache check (if provided)
        if price_db is not None:
            stale = True if freshness_days >= 0 else False
            if freshness_days >= 0:
                stale = price_db.needs_update(s, max_age_days=freshness_days, start_date=d)

            cached_df = price_db.get_prices(s, start_date=d)

            # If cache is fresh, return immediately
            if not stale and cached_df is not None and not cached_df.empty:
                logger.debug(f"Using StockPriceDB cached prices for {s}")
                return cached_df

            # If cache is up to date relative to today, return immediately
            if cached_df is not None and not cached_df.empty:
                latest_date_str = cached_df.index.max().strftime("%Y-%m-%d")
                if latest_date_str >= datetime.now().strftime("%Y-%m-%d"):
                    logger.debug(f"Cache for {s} is up to date (latest: {latest_date_str}). Skipping network fetch.")
                    return cached_df

        # If offline mode (freshness_days < 0), return cached_df directly without network request
        if freshness_days < 0:
            return cached_df

        # 2. Rate limit before network request
        if update_interval > 0:
            now = time.time()
            with _rate_lock:
                scheduled = max(_last_request_time + update_interval, now)
                sleep_sec = scheduled - now
                _last_request_time = scheduled
            if sleep_sec > 0:
                logger.debug(f"Rate limit: waiting {sleep_sec:.1f}s before {s}")
                time.sleep(sleep_sec)

        # 3. Network fetch (Tier 1 & Tier 2)
        network_result = None
        fetch_start = cached_df.index.max().strftime("%Y-%m-%d") if (cached_df is not None and not cached_df.empty) else d
        try:
            network_result = _fetch_data_fdr_network(s, market, fetch_start)
        except Exception as e:
            logger.warning(f"Tier 1 & 2 network download failed for {s}: {e}")

        if network_result is not None and not network_result.empty:
            if price_db is not None:
                try:
                    price_db.update_prices(s, network_result)
                except Exception as ex:
                    logger.debug(f"Failed to cache prices for {s}: {ex}")

            if cached_df is not None and not cached_df.empty:
                # Normalize network columns to match cached DB lowercase columns
                if network_result is not None and not network_result.empty:
                    network_result.columns = [str(c).lower() for c in network_result.columns]
                merged_df = pd.concat([cached_df, network_result])
                merged_df = merged_df[~merged_df.index.duplicated(keep='last')].sort_index()
                return merged_df
            return network_result

        # 4. Tier 3 Fallback: Network failed, fall back to DB cache if available
        if (cached_df is None or cached_df.empty) and price_db is not None:
            cached_df = price_db.get_prices(s, start_date=None)

        if cached_df is not None and not cached_df.empty:
            logger.warning(f"[Offline Cache Fallback] Network failed for {s}. Falling back to cached DB data ({len(cached_df)} rows)")
            return cached_df

        logger.warning(f"No network data or DB cache available for {s}.")
        return None

    # 0. TechnicalCache lookup (TTL based)
    result = technical_cache.get_or_compute(
        symbol,
        start_date,
        _fetch_fallback
    )
    return result


# Global indicator & Sector ETF tickers → feature column names
_INDICATOR_TICKERS = {
    '^VIX': 'vix_change',
    '^TNX': 'us10y',
    'USDKRW=X': 'usdkrw_change',
    '^GSPC': 'sp500_change',
    'DX-Y.NYB': 'dxy_change',
    'CL=F': 'wti_change',
    '^KS11': 'kospi_change',
    '^KQ11': 'kosdaq_change',
    '^CPC': 'put_call_ratio',
    # Sector ETFs
    '091160.KS': 'kodex_semicon_change',
    '305720.KS': 'kodex_battery_change',
    '244580.KS': 'kodex_bio_change',
    'XLK': 'xlk_change',
    'XLF': 'xlf_change',
    'XLV': 'xlv_change',
    'XLE': 'xle_change',
    # Expanded Macro Indicators (Yield Curve, Credit, Assets)
    '^IRX': 'us3m_yield',
    'TLT': 'tlt_change',
    'LQD': 'lqd_change',
    'HYG': 'hyg_change',
    'GLD': 'gold_change',
    'EEM': 'eem_change',
}


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=True
)
def _download_indicator_yf(ticker: str, start_date: str) -> pd.DataFrame:
    raw = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
    if raw is not None and not raw.empty:
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.droplevel(1)
        return raw
    raise ValueError(f"yfinance download for {ticker} returned empty data")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=False
)
def _download_indicator_network(ticker: str, start_date: str) -> pd.DataFrame:
    # Coordinate indicator fetch rate limiting
    get_global_rate_limiter().wait()

    # Tier 1: Primary provider (yfinance) with transient retry
    try:
        return _download_indicator_yf(ticker, start_date)
    except Exception as e:
        logger.debug(f"Tier 1 (yfinance) indicator download error for {ticker}: {e}")

    # Tier 2: Secondary provider fallback (FinanceDataReader)
    try:
        raw = fdr.DataReader(ticker, start=start_date)
        if raw is not None and not raw.empty:
            logger.warning(f"Successfully retrieved Tier 2 indicator data for {ticker} via FDR")
            return raw
    except Exception as e:
        logger.debug(f"Tier 2 indicator download error for {ticker}: {e}")

    raise ValueError(f"Downloaded indicator {ticker} is empty or None across all providers")


def fetch_indicator_history(start_date: str, price_db: Optional[StockPriceDB] = None,
                            freshness_days: int = 7) -> pd.DataFrame:
    """Download 8 global indicator tickers in parallel, return single DataFrame.

    Returns: DataFrame with DatetimeIndex and columns = _INDICATOR_TICKERS.values()
    """
    def _fetch_one(ticker: str, col_name: str):
        cached_df = None
        df = None
        if price_db is not None:
            stale = True if freshness_days >= 0 else False
            if freshness_days >= 0:
                stale = price_db.needs_update(ticker, max_age_days=freshness_days, start_date=start_date)

            cached_df = price_db.get_prices(ticker, start_date=start_date)
            if not stale and cached_df is not None and not cached_df.empty:
                df = cached_df

            # Incremental fetch for indicator if stale
            if stale and cached_df is not None and not cached_df.empty:
                latest_date_str = cached_df.index.max().strftime("%Y-%m-%d")
                if latest_date_str >= datetime.now().strftime("%Y-%m-%d"):
                    df = cached_df
                else:
                    logger.debug(f"Fetching incremental indicator {ticker} from {latest_date_str}...")
                    try:
                        new_df = _download_indicator_network(ticker, latest_date_str)
                        if new_df is not None and not new_df.empty:
                            price_db.update_prices(ticker, new_df)
                            df = pd.concat([cached_df, new_df])
                            df = df[~df.index.duplicated(keep='last')].sort_index()
                    except Exception as e:
                        logger.warning(f"Failed to fetch incremental indicator {ticker}: {e}")

        if freshness_days < 0 and (df is None or df.empty):
            df = cached_df

        if df is None or df.empty:
            try:
                df = _download_indicator_network(ticker, start_date)
                if df is not None and not df.empty and price_db is not None:
                    try:
                        price_db.update_prices(ticker, df)
                    except Exception as ex:
                        logger.debug(f"Failed to cache indicator {ticker}: {ex}")
            except Exception as e:
                logger.warning(f"Failed to fetch indicator {ticker} after retries: {e}")
                # Tier 3 Fallback: Use cached indicator data if network fails
                if cached_df is not None and not cached_df.empty:
                    logger.warning(f"[Indicator DB Fallback] Using cached indicator data for {ticker}")
                    df = cached_df

        if df is not None and not df.empty:
            if col_name.endswith('_change'):
                return (col_name, df['Close'].pct_change().fillna(0.0) * 100)
            elif col_name == 'put_call_ratio':
                return (col_name, df['Close'].ffill().fillna(0.6))
            else:
                return (col_name, df['Close'].ffill().fillna(0.0))
        return (col_name, pd.Series(dtype=float))

    combined = {}
    with ThreadPoolExecutor(max_workers=len(_INDICATOR_TICKERS)) as pool:
        futures = {pool.submit(_fetch_one, t, c): c for t, c in _INDICATOR_TICKERS.items()}
        for f in as_completed(futures):
            try:
                col_name, series = f.result()
                combined[col_name] = series
            except Exception as e:
                logger.debug(f"Indicator fetch failed for {futures[f]}: {e}")

    if not combined:
        logger.warning("No indicator data fetched; returning empty DataFrame")
        return pd.DataFrame()

    result = pd.concat(combined, axis=1)
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()

    # Derived Macro Features
    if 'us10y' in result.columns and 'us3m_yield' in result.columns:
        result['yield_curve_10y3m'] = result['us10y'] - result['us3m_yield']
    elif 'us10y' in result.columns:
        result['yield_curve_10y3m'] = 0.0

    if 'hyg_change' in result.columns and 'tlt_change' in result.columns:
        result['credit_spread_proxy'] = result['hyg_change'] - result['tlt_change']
    elif 'hyg_change' in result.columns:
        result['credit_spread_proxy'] = result['hyg_change']

    if 'usdkrw_change' in result.columns:
        result['usdkrw_lag1'] = result['usdkrw_change'].shift(1).fillna(0.0)

    if 'vix_change' in result.columns:
        result['vix_spike'] = (result['vix_change'] > 5.0).astype(float)

    if 'us10y' in result.columns:
        result['real_rate_proxy'] = result['us10y'] - 2.5  # Nominal 10Y minus 2.5% inflation anchor

    logger.info(f"Fetched indicator history: {len(result)} rows x {len(result.columns)} cols")
    return result


def _market_symbols(universe: pd.DataFrame) -> dict:
    """Return dict of {market: set(symbols)} for all known markets."""
    markets = {}
    for m in ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']:
        markets[m] = set(universe[universe['market'] == m]['symbol'])
    return markets

def _fmt_top(df: pd.DataFrame, horizon: int, symbol_to_name: dict, symbol_to_market: dict, count: int = 10) -> list:
    """Format top-N predictions for a single market segment."""
    lines = []
    for rank, (_, row) in enumerate(df.head(count).iterrows(), 1):
        sym = row['symbol']
        ret = row[horizon] * 100
        name = symbol_to_name.get(sym, "Unknown")
        marker = symbol_to_market.get(sym, "")
        lines.append(f"  {rank}. [{marker}] {sym} ({name}): +{ret:.2f}%")
    return lines

def format_prediction_message(res_df: pd.DataFrame, universe: pd.DataFrame) -> str:
    """Format prediction results as a Telegram-friendly message"""
    market_syms = _market_symbols(universe)
    symbol_to_name = dict(zip(universe['symbol'], universe['name']))
    symbol_to_market = dict(zip(universe['symbol'], universe['market']))
    horizons = [1, 5, 10, 20, 30, 60, 120, 200]
    lines = [
        "🤖 *XGBoost 예측 결과*",
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 30,
    ]
    krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
    for h in horizons:
        if h not in res_df.columns:
            continue
        sorted_df = res_df.sort_values(by=h, ascending=False)

        for m in krx_markets:
            m_df = sorted_df[sorted_df['symbol'].isin(market_syms.get(m, set()))]
            if not m_df.empty:
                lines.append(f"\n*{h}일 예상 — {m} TOP 10*")
                lines.extend(_fmt_top(m_df, h, symbol_to_name, symbol_to_market, 10))

        sp500_df = sorted_df[sorted_df['symbol'].isin(market_syms.get('SP500', set()))]
        if not sp500_df.empty:
            lines.append(f"\n*{h}일 예상 — S&P 500 TOP 10*")
            lines.extend(_fmt_top(sp500_df, h, symbol_to_name, symbol_to_market, 10))

    return "\n".join(lines)


def _get_excluded_krx_symbols() -> set:
    """Get KRX symbols excluded due to halted trading or admin status.

    Uses FinanceDataReader to check:
    - Volume=0: trading halted (거래정지) - only applied during active market hours
    - KRX-ADMINISTRATIVE: under administration (관리종목)

    Returns empty set on failure (e.g. offline mode).
    """
    excluded = set()
    try:
        try:
            krx = fdr.StockListing('KRX')
            krx.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume', 'code'] else str(c) for c in krx.columns]
            if 'Volume' in krx.columns and not krx.empty:
                zero_vol_ratio = (krx['Volume'] == 0).mean()
                if zero_vol_ratio <= 0.3:
                    halted = set(krx[krx['Volume'] == 0]['Code'].tolist())
                    if halted:
                        logger.info(f"Excluding {len(halted)} halted KRX stocks (Volume=0, active market)")
                    excluded |= halted
                else:
                    logger.info(f"Market off-hours detected (zero volume ratio={zero_vol_ratio:.1%}). Skipping Volume=0 purging.")
        except Exception as e:
            logger.debug(f"Could not fetch KRX listing: {e}")
        try:
            adm = fdr.StockListing('KRX-ADMINISTRATIVE')
            code_col = 'Code' if 'Code' in adm.columns else ('Symbol' if 'Symbol' in adm.columns else None)
            if code_col:
                admin = set()
                for s in adm[code_col]:
                    code_str = str(s).zfill(6) if str(s).isdigit() else str(s)
                    admin.add(code_str)
                if admin:
                    logger.info(f"Excluding {len(admin)} administrative KRX stocks (관리종목)")
                excluded |= admin
        except Exception as e:
            logger.debug(f"Could not fetch KRX-ADMINISTRATIVE listing: {e}")
    except Exception:
        pass
    return excluded


def execute_prediction_pipeline():
    logger.info("Starting consolidated market indicator and prediction pipeline...")

    # 1. Load configurations from TradingConfig (.env)
    cfg = TradingConfig()
    cfg.validate()
    logger.info(f"Loaded config: DB={cfg.db_path}, Broker={cfg.broker_type}, Mock Trading={cfg.mock_trading}")

    # Auto-download GitHub DB cache if configured
    if os.environ.get("DOWNLOAD_DB_FROM_GITHUB", "false").lower() == "true":
        try:
            from download_db import download_github_databases
            download_github_databases()
        except Exception as e:
            logger.warning(f"Failed to auto-download GitHub database cache: {e}")

    # 2. Fetch current global market indicators
    logger.info("Fetching global market indicators...")
    market_client = GlobalMarketClient()
    market_summary = market_client.get_summary()

    # 3. Store indicators
    date_str = datetime.now().strftime('%Y-%m-%d')
    storage = MarketIndicatorStorage(db_path=cfg.db_path)
    with storage.pipeline_stage("global_indicators"):
        storage.save_indicators(market_summary, date_str)
    logger.info("Saved market indicators to database.")

    # 4. Update stock universe if needed
    universe = storage.get_universe()
    if universe.empty:
        logger.info("Universe is empty. Syncing stock universe...")
        storage.update_stock_universe()
        universe = storage.get_universe()
    logger.info(f"Loaded {len(universe)} symbols from universe.")

    # Build symbol→market mapping for adjusted price fetching
    symbol_market = dict(zip(universe['symbol'], universe['market']))

    def _bg_fundamentals(syms, label):
        logger.info(f"[BG] Fetching fundamentals for {label} ({len(syms)} symbols)...")
        try:
            fetch_and_store_fundamentals_batch(syms, symbol_market, storage)
            logger.info(f"[BG] Fundamentals fetch complete for {label}")
        except Exception as e:
            logger.warning(f"[BG] Fundamentals fetch failed for {label}: {e}")

    # StockPriceDB 캐시 초기화
    price_db = StockPriceDB(db_path=cfg.stock_price_db_path)
    freshness = cfg.get_freshness_days()

    # 5. Fetch global indicator history for training & inference
    start_date_train = cfg.train_start_date
    from datetime import timedelta
    start_date_infer = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    # Check if we should skip training based on skip_training config and model availability
    should_skip = False
    model = OnDevicePredictionModel()
    vcp_ml = None

    if cfg.skip_training:
        logger.info("SKIP_TRAINING is active. Checking for existing models on disk...")
        model.load_models()
        model.load_surge_models()
        model.load_lead_lag()
        vcp_ml = VCPSurgePredictor(model_dir=str(model.model_dir))
        vcp_ml.load_models()

        # Verify that models are actually loaded for regression, surge, and VCP ML
        regression_loaded = any(len(mkt_dict) > 0 for mkt_dict in model.models.values()) or any(len(mkt_dict) > 0 for mkt_dict in model.lgb_models.values())
        surge_loaded = any(len(mkt_dict) > 0 for mkt_dict in model.surge_models.values())
        vcp_loaded = any(len(mkt_dict) > 0 for mkt_dict in vcp_ml.models.values()) or any(len(mkt_dict) > 0 for mkt_dict in vcp_ml.lgb_models.values())

        if regression_loaded and surge_loaded and vcp_loaded:
            logger.info("Pre-trained models found and loaded successfully. Skipping model training phase.")
            should_skip = True
        else:
            logger.warning("Missing or incomplete pre-trained models on disk. Falling back to training. Setting should_skip = False.")
            should_skip = False

    update_interval = cfg.get_update_interval()

    # 6. Prepare Training Data (On-device) — split by market
    kospi_symbols = universe[universe['market'] == 'KOSPI']['symbol'].tolist()
    kosdaq_symbols = universe[universe['market'] == 'KOSDAQ']['symbol'].tolist()
    konex_symbols = universe[universe['market'] == 'KONEX']['symbol'].tolist()
    sp500_symbols = universe[universe['market'] == 'SP500']['symbol'].tolist()
    krx_symbols = kospi_symbols + kosdaq_symbols + konex_symbols

    if should_skip:
        logger.info("Fetching global indicator history for inference only...")
        indicator_infer = fetch_indicator_history(start_date_infer, price_db, freshness)
        train_data_dict = {}
        indicator_train = pd.DataFrame()
        df_train = pd.DataFrame()
    else:
        logger.info("Fetching global indicator history...")
        indicator_train = fetch_indicator_history(start_date_train, price_db, freshness)
        # S2 fix: Reuse indicator_train for inference — slice to infer start date instead of
        # making a redundant second network request for the same data.
        if not indicator_train.empty and hasattr(indicator_train.index, 'date'):
            indicator_infer = indicator_train[indicator_train.index >= start_date_infer]
        else:
            indicator_infer = indicator_train

        # Sample from settings (절대값 / 퍼센트 / "all")
        import random
        seed = cfg.get_train_seed()
        if seed is not None:
            random.seed(seed)

        # Filter training sampling based on allowed INFERENCE_TARGET (OOM Fix)
        target_env = os.environ.get("INFERENCE_TARGET", "SP500,KRX").strip().upper()
        targets = [t.strip() for t in target_env.split(",") if t.strip()]

        sp500_active = "SP500" in targets or not targets
        kospi_active = "KOSPI" in targets or "KRX" in targets or not targets
        kosdaq_active = "KOSDAQ" in targets or "KRX" in targets or not targets
        konex_active = "KONEX" in targets or "KRX" in targets or not targets

        active_krx_symbols = []
        if kospi_active:
            active_krx_symbols.extend(kospi_symbols)
        if kosdaq_active:
            active_krx_symbols.extend(kosdaq_symbols)
        if konex_active:
            active_krx_symbols.extend(konex_symbols)

        sp500_sample = cfg.resolve_sample_size(cfg.train_sample_sp500, len(sp500_symbols)) if sp500_active else 0
        krx_sample = cfg.resolve_sample_size(cfg.train_sample_krx, len(active_krx_symbols)) if active_krx_symbols else 0

        if cfg.debug_mode:
            sp500_sample = min(5, sp500_sample) if sp500_active else 0
            krx_sample = min(5, krx_sample) if active_krx_symbols else 0
            logger.info(f"[DEBUG MODE] Overriding training samples: SP500={sp500_sample}, KRX={krx_sample}")

        def _safe_sample(population, k):
            if k >= len(population):
                return list(population)
            return random.sample(population, k)

        train_krx_overall = _safe_sample(active_krx_symbols, krx_sample) if active_krx_symbols else []
        train_krx_set = set(train_krx_overall)
        train_symbols = (_safe_sample(sp500_symbols, sp500_sample) if sp500_active else []) + train_krx_overall

        # Per-market breakdown for training (preserve market proportions)
        train_sp500 = [s for s in train_symbols if s in sp500_symbols]
        train_kospi = [s for s in train_krx_set if s in kospi_symbols]
        train_kosdaq = [s for s in train_krx_set if s in kosdaq_symbols]
        train_konex = [s for s in train_krx_set if s in konex_symbols]

        # 6. Fetch corporate fundamentals in background (non-blocking)
        if train_symbols:
            t = threading.Thread(target=_bg_fundamentals, args=(train_symbols, "training"))
            t.start()

        # Prefetch training data in batches to optimize performance
        prefetch_prices_batch(train_symbols, symbol_market, start_date_train, price_db, freshness)

        logger.info(f"Fetching training data for {len(train_symbols)} sampled symbols (update_interval={update_interval}s)...")
        train_data_dict = {}

        with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
            future_to_sym = {}
            for sym in train_symbols:
                sym_market = symbol_market.get(sym, 'SP500' if sym in sp500_symbols else 'KRX')
                future_to_sym[executor.submit(fetch_data_fdr, sym, sym_market, start_date_train, price_db, freshness, update_interval)] = sym

            done_count = 0
            with tqdm(
                total=len(train_symbols),
                desc="📥 Training data",
                unit="sym",
                ncols=100,
                colour="cyan",
                dynamic_ncols=True,
            ) as pbar:
                for future in as_completed(future_to_sym):
                    sym = future_to_sym[future]
                    try:
                        df = future.result(timeout=_PER_SYMBOL_TIMEOUT)
                        if df is not None and not df.empty:
                            train_data_dict[sym] = df
                    except TimeoutError:
                        logger.warning(f"[{done_count+1}/{len(train_symbols)}] Skipping {sym}: timeout (>={_PER_SYMBOL_TIMEOUT}s)")
                    except Exception as e:
                        logger.debug(f"Skipping {sym}: {e}")
                    done_count += 1
                    pbar.update(1)
                    pbar.set_postfix({"loaded": len(train_data_dict), "sym": sym[:10]})
                    if done_count % 100 == 0:
                        logger.info(f"Training data fetch progress: {done_count}/{len(train_symbols)} ({len(train_data_dict)} loaded)")

        # Wait for fundamentals fetch to complete before merging
        if train_symbols:
            logger.info("Waiting for training fundamentals fetch to complete...")
            t.join()

        # Batch fetch all fundamentals to avoid thousands of SQLite query roundtrips
        logger.info("Batch retrieving training fundamentals from SQLite database...")
        try:
            all_train_fund_df = storage.get_all_fundamentals(train_symbols)
            train_fund_cache = {sym: grp for sym, grp in all_train_fund_df.groupby('symbol')}
            logger.info(f"Loaded fundamentals cache for {len(train_fund_cache)} symbols.")
        except Exception as e:
            logger.error(f"Failed to batch fetch training fundamentals: {e}")
            train_fund_cache = {}

        # Merge fundamentals (synchronous loop to avoid SQLite multithreaded locking/deadlocks)
        for sym in list(train_data_dict.keys()):
            df = train_data_dict[sym]
            try:
                merged = model.merge_fundamentals(sym, df, storage, fundamentals_cache=train_fund_cache)
                if merged is not None:
                    train_data_dict[sym] = merged
                else:
                    train_data_dict.pop(sym, None)
            except Exception as e:
                logger.debug(f"Failed to merge fundamentals for {sym}: {e}")
                train_data_dict.pop(sym, None)

        df_train = model.prepare_training_data(train_data_dict, indicator_train, storage=storage)

        # 7. Train XGBoost models per market (KOSPI/KOSDAQ/KONEX/SP500)
        if not df_train.empty and 'symbol' in df_train.columns:
            df_train['symbol'] = df_train['symbol'].astype(str)
            train_symbol_set = set(df_train['symbol'])
            # Build per-market train DataFrames from the merged df_train
            market_dfs = {}
            for m_name, m_symbols in [('sp500', train_sp500), ('kospi', train_kospi),
                                       ('kosdaq', train_kosdaq), ('konex', train_konex)]:
                m_sym_strs = [str(s) for s in m_symbols]
                active = [s for s in m_sym_strs if s in train_symbol_set]
                m_df = df_train[df_train['symbol'].isin(active)] if active else pd.DataFrame()
                if not m_df.empty:
                    logger.info(f"Training data for {m_name}: {len(m_df)} rows, {m_df['symbol'].nunique()} symbols")
                market_dfs[m_name] = m_df
        else:
            market_dfs = {m: pd.DataFrame() for m in ['sp500', 'kospi', 'kosdaq', 'konex']}

        # S8 fix: ThreadPoolExecutor avoids pickle serialization overhead of ProcessPool.
        # XGBoost/LightGBM release the GIL during training, so threads are efficient here.
        with storage.pipeline_stage("train_regression"):
            with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as pool:
                futures = {}
                for m_name, m_df in market_dfs.items():
                    if not m_df.empty:
                        logger.info(f"Training {m_name.upper()} regression model ({len(m_df)} rows)...")
                        futures[pool.submit(model.train, m_df, market=m_name, save_after=True)] = m_name
                for f in as_completed(futures):
                    try:
                        f.result()
                    except Exception as e:
                        logger.error(f"Regression training failed for {futures[f]}: {e}")
        model.load_models()

        with storage.pipeline_stage("train_surge"):
            with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as pool:
                futures = {}
                for m_name, m_df in market_dfs.items():
                    if not m_df.empty:
                        futures[pool.submit(model.train_surge, m_df, market=m_name, save_after=True)] = m_name
                for f in as_completed(futures):
                    try:
                        f.result()
                    except Exception as e:
                        logger.error(f"Surge training failed for {futures[f]}: {e}")
        model.load_surge_models()

        # 7c. Compute lead-lag correlation matrix (which stocks follow which)
        with storage.pipeline_stage("train_lead_lag_vcp"):
            if not df_train.empty and len(df_train) > 1000:
                model.compute_lead_lag(df_train, indicator_df=indicator_train, symbol_to_market=symbol_market)

            # 7d. Train VCP ML surge models (4 markets, parallel inside)
            vcp_ml = VCPSurgePredictor(model_dir=str(model.model_dir))
            if train_data_dict:
                vcp_ml.train(train_data_dict, indicator_train, universe)

        # 7e. Fit Isotonic Regression calibrators on training data for score alignment
        if not df_train.empty and 'Close' in df_train.columns:
            try:
                from src.ai.ensemble_scorer import EnsembleScoringEngine
                scorer_calib = EnsembleScoringEngine(config=cfg)
                logger.info("Fitting Isotonic Regression calibrators on training dataset...")
                sample_train = df_train.sample(n=min(len(df_train), 5000), random_state=42)
                reg_preds = model.predict(sample_train)
                surge_preds = model.predict_surge(sample_train)
                if not reg_preds.empty and not surge_preds.empty:
                    y_true = (sample_train.groupby('symbol')['Close'].transform(lambda x: x.shift(-20) / x - 1) >= 0.15).astype(float).values
                    calib_scores = {
                        'regression': reg_preds.get(20, pd.Series(0.5, index=sample_train.index)).values,
                        'surge': surge_preds.get('surge_20d', pd.Series(0.5, index=sample_train.index)).values,
                    }
                    scorer_calib.fit_calibrators(calib_scores, y_true)
            except Exception as _calib_e:
                logger.warning(f"Isotonic calibration fitting skipped: {_calib_e}")

    # 8. Fetch fundamentals for all inference symbols (non-blocking background)
    target_env = os.environ.get("INFERENCE_TARGET", "SP500,KRX").strip().upper()
    targets = [t.strip() for t in target_env.split(",") if t.strip()]

    selected_symbols = []
    if "SP500" in targets:
        selected_symbols.extend(sp500_symbols)
    if "KRX" in targets:
        selected_symbols.extend(krx_symbols)
    elif any(k in targets for k in ["KOSPI", "KOSDAQ", "KONEX"]):
        if "KOSPI" in targets:
            selected_symbols.extend(kospi_symbols)
        if "KOSDAQ" in targets:
            selected_symbols.extend(kosdaq_symbols)
        if "KONEX" in targets:
            selected_symbols.extend(konex_symbols)

    all_symbols = selected_symbols if selected_symbols else (sp500_symbols + krx_symbols)

    # Exclude halted (거래정지) and administrative (관리종목) KRX stocks from all predictions
    excluded_krx = _get_excluded_krx_symbols()
    if excluded_krx:
        before = len(all_symbols)
        all_symbols = [s for s in all_symbols if s not in excluded_krx]
        logger.info(f"Excluded {before - len(all_symbols)} halted/admin KRX stocks from inference")

    if cfg.debug_mode:
        debug_symbols = []
        for m_syms in [sp500_symbols, kospi_symbols, kosdaq_symbols, konex_symbols]:
            active_m = [s for s in m_syms if s in all_symbols]
            debug_symbols.extend(active_m[:3])
        all_symbols = debug_symbols
        logger.info(f"[DEBUG MODE] Sampled {len(all_symbols)} symbols for fast pipeline dry run")

    # Do not start inference fundamentals thread when skipping inference
    # (avoids orphaned non-daemon thread that would keep the process alive after early return)
    t2 = None
    if all_symbols and not cfg.skip_inference:
        t2 = threading.Thread(target=_bg_fundamentals, args=(all_symbols, "inference"))
        t2.start()

    # Prefetch inference data in batches to optimize performance
    prefetch_prices_batch(all_symbols, symbol_market, start_date_infer, price_db, freshness)

    # 9. Fetch recent data for ALL symbols to run inference
    logger.info(f"Fetching inference data for ALL {len(all_symbols)} symbols (update_interval={update_interval}s)...")
    infer_data_dict = {}
    with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
        future_to_sym = {}
        for sym in all_symbols:
            sym_market = symbol_market.get(sym, 'SP500' if sym in sp500_symbols else 'KRX')
            future_to_sym[executor.submit(fetch_data_fdr, sym, sym_market, start_date_infer, price_db, freshness, update_interval)] = sym

        count = 0
        with tqdm(
            total=len(all_symbols),
            desc="📡 Inference data",
            unit="sym",
            ncols=100,
            colour="green",
            dynamic_ncols=True,
        ) as pbar:
            for future in as_completed(future_to_sym):
                sym = future_to_sym[future]
                try:
                    df = future.result(timeout=_PER_SYMBOL_TIMEOUT)
                    if df is not None and not df.empty:
                        infer_data_dict[sym] = df
                except TimeoutError:
                    logger.warning(f"[{count+1}/{len(all_symbols)}] Skipping {sym}: timeout (>={_PER_SYMBOL_TIMEOUT}s)")
                except Exception as e:
                    logger.debug(f"Skipping {sym}: {e}")
                count += 1
                pbar.update(1)
                pbar.set_postfix({"loaded": len(infer_data_dict), "sym": sym[:10]})
                if count % 500 == 0:
                    logger.info(f"Fetched inference data: {count}/{len(all_symbols)} ({len(infer_data_dict)} loaded)")

    # Filter out symbols with insufficient data (< 200 days)
    before = len(infer_data_dict)
    infer_data_dict = {s: df for s, df in infer_data_dict.items()
                       if df is not None and len(df) >= 200}
    dropped = before - len(infer_data_dict)
    if dropped:
        logger.info(f"Excluded {dropped} symbols with insufficient inference data (< 200 days)")

    # If skip-inference is enabled, stop pipeline here (only fetch and cache data)
    if cfg.skip_inference:
        logger.info("SKIP_INFERENCE is enabled. Pipeline completed successfully after caching data.")
        return pd.DataFrame(), "Pipeline completed successfully after caching data (skip-inference)."

    # Wait for inference fundamentals fetch to complete before merging
    if all_symbols and t2 is not None:
        logger.info("Waiting for inference fundamentals fetch to complete...")
        t2.join()

    # Batch fetch all inference fundamentals to avoid individual SQLite I/O bottlenecks
    logger.info("Batch retrieving inference fundamentals from SQLite database...")
    infer_symbols = list(infer_data_dict.keys())
    try:
        all_infer_fund_df = storage.get_all_fundamentals(infer_symbols)
        infer_fund_cache = {sym: grp for sym, grp in all_infer_fund_df.groupby('symbol')}
        logger.info(f"Loaded inference fundamentals cache for {len(infer_fund_cache)} symbols.")
    except Exception as e:
        logger.error(f"Failed to batch fetch inference fundamentals: {e}")
        infer_fund_cache = {}

    # Merge fundamentals (parallel)
    def _merge_infer_one(sym: str, df):
        try:
            merged = model.merge_fundamentals(sym, df, storage, fundamentals_cache=infer_fund_cache)
            return (sym, merged)
        except Exception as e:
            logger.debug(f"Failed to merge fundamentals for {sym}: {e}")
            return (sym, None)

    with ThreadPoolExecutor(max_workers=_CPU_WORKERS * 2) as pool:
        futures = {pool.submit(_merge_infer_one, sym, df): sym for sym, df in infer_data_dict.items()}
        for f in as_completed(futures):
            sym, merged = f.result()
            if merged is not None:
                infer_data_dict[sym] = merged
            else:
                infer_data_dict.pop(sym, None)

    # 10. Run predictions (regression + surge, shared feature computation)
    logger.info("Running inference (regression + surge)...")
    symbol_to_market_lower = {sym: mkt.lower() for sym, mkt in symbol_market.items()}
    with storage.pipeline_stage("inference_regression_surge"):
        res_df, surge_df = model.predict_all(infer_data_dict, indicator_infer, symbol_to_market_lower, storage=storage, fundamentals_cache=infer_fund_cache)

    if res_df.empty:
        logger.error("No predictions made.")
        return None, None
    logger.info(f"Regression: {len(res_df)} symbols, Surge: {len(surge_df) if not surge_df.empty else 0} symbols")

    # 10c. Run VCP pattern detection (parallel)
    logger.info("Running VCP pattern detection...")
    from src.ai.vcp_detector import detect_vcp

    def _detect_vcp(sym: str, df: pd.DataFrame):
        if df is None or len(df) < 200:
            return None
        try:
            result = detect_vcp(df)
            if result['is_vcp']:
                result['symbol'] = sym
                return result
        except Exception:
            pass
        return None

    vcp_results = []
    with ThreadPoolExecutor(max_workers=_CPU_WORKERS * 2) as pool:
        futures = {pool.submit(_detect_vcp, sym, df): sym for sym, df in infer_data_dict.items()}
        for f in as_completed(futures):
            try:
                r = f.result()
                if r is not None:
                    vcp_results.append(r)
            except Exception:
                continue
    vcp_results.sort(key=lambda x: -x['vcp_score'])
    logger.info(f"VCP patterns found: {len(vcp_results)} symbols")

    # ── Phase 5-C: VCP Real-Time Breakout Trigger ────────────────────────────
    _vcp_breakout_signals = []
    if vcp_results:
        try:
            from src.ai.vcp_realtime_trigger import VCPBreakoutTrigger
            _vcp_trigger = VCPBreakoutTrigger(config=cfg)
            for _vr in vcp_results:
                _vsym = _vr.get('symbol')
                _vdf = infer_data_dict.get(_vsym)
                if _vdf is None or len(_vdf) < 50:
                    continue
                try:
                    _close = _vdf['Close']
                    _volume = _vdf['Volume']
                    if isinstance(_close, pd.DataFrame):
                        _close = _close.iloc[:, 0]
                    if isinstance(_volume, pd.DataFrame):
                        _volume = _volume.iloc[:, 0]
                    _cur_price = float(_close.iloc[-1])
                    _cur_vol = float(_volume.iloc[-1])
                    _signal = _vcp_trigger.evaluate_realtime_breakout(
                        symbol=_vsym,
                        current_price=_cur_price,
                        current_volume=_cur_vol,
                        hist_df=_vdf,
                        vcp_score=float(_vr.get('vcp_score', 50.0)),
                    )
                    if _signal.is_breakout:
                        _vcp_breakout_signals.append(_signal)
                        # Apply 1.3× bonus to vcp_score for breakout confirmation
                        _vr['vcp_score'] = min(_vr['vcp_score'] * 1.3, 100.0)
                except Exception as _vsig_e:
                    logger.debug(f"[5-C] Breakout check failed for {_vsym}: {_vsig_e}")

            if _vcp_breakout_signals:
                _sym_to_name = dict(zip(universe['symbol'], universe.get('name', universe['symbol'])))
                _alert_lines = []
                for _sig in _vcp_breakout_signals[:5]:
                    _nm = _sym_to_name.get(_sig.symbol, _sig.symbol)
                    _alert_lines.append(
                        f"  🚀 {_sig.symbol} ({_nm}): ₩{_sig.current_price:,.0f} "
                        f"| Pivot ₩{_sig.pivot_price:,.0f} "
                        f"| Vol {_sig.volume_ratio:.1f}x"
                    )
                _notify_telegram(
                    f"🚀 [VCP 돌파] {len(_vcp_breakout_signals)}개 종목 당일 돌파 확인!\n"
                    + "\n".join(_alert_lines),
                    "SUCCESS",
                )
                logger.info(f"[5-C] VCP breakout detected: {len(_vcp_breakout_signals)} symbols")
            else:
                logger.info("[5-C] No VCP breakout signals detected today.")
        except Exception as _vcp_e:
            logger.warning(f"[5-C] VCP breakout trigger skipped: {_vcp_e}")

    # 10d. Run lead-lag inference (which stocks may surge based on leader movements)
    logger.info("Running lead-lag inference...")
    lead_lag_df = model.predict_lead_lag(infer_data_dict, indicator_df=indicator_infer)
    if not lead_lag_df.empty:
        logger.info(f"Lead-lag predictions generated for {len(lead_lag_df)} symbols")

    # 10e. Run Statistical Arbitrage pair scanning
    logger.info("Running Statistical Arbitrage pair scanning...")
    from src.core.stat_arb import StatisticalArbitrageEngine
    stat_arb_engine = StatisticalArbitrageEngine()

    stat_arb_prices = {}
    for sym, df_p in infer_data_dict.items():
        if df_p is not None and not df_p.empty:
            close_series = df_p['Close']
            if isinstance(close_series, pd.DataFrame):
                close_series = close_series.iloc[:, 0]
            stat_arb_prices[sym] = close_series.tolist()

    stat_arb_pairs = stat_arb_engine.find_cointegrated_pairs(stat_arb_prices)

    # Ensure result directory exists
    result_dir = os.path.join(os.path.dirname(__file__), "result")
    os.makedirs(result_dir, exist_ok=True)

    # Save Stat-Arb predictions to separate file (Limit TXT to Top 200 valid pairs to keep file small)
    stat_arb_output_path = os.path.join(result_dir, "stat_arb_predictions.txt")
    valid_stat_arb_pairs = [p for p in stat_arb_pairs if abs(p.get('z_score', 0.0)) >= 1.5]
    valid_stat_arb_pairs.sort(key=lambda x: abs(x.get('z_score', 0.0)), reverse=True)
    top_stat_arb_pairs = valid_stat_arb_pairs[:200]

    with open(stat_arb_output_path, "w", encoding="utf-8") as f:
        f.write("=== Statistical Arbitrage Pairs & Signals (Top 200 Valid Pairs) ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total cointegrated pairs found: {len(stat_arb_pairs)} (Showing top {len(top_stat_arb_pairs)})\n\n")
        f.write(f"{'Pair':<25}{'Z-Score':<10}{'Correlation':<15}{'Beta':<10}{'Signal':<20}\n")
        f.write("-" * 80 + "\n")
        for p in top_stat_arb_pairs:
            pair_str = f"{p['pair'][0]}-{p['pair'][1]}"
            f.write(f"{pair_str:<25}{p['z_score']:<10}{p['correlation']:<15}{p['beta']:<10}{p['signal']:<20}\n")
    logger.info(f"Saved Statistical Arbitrage pairs (Total: {len(stat_arb_pairs)}, Top 200 written) to {stat_arb_output_path}")


    # 11. Save predictions to DB
    storage.save_predictions(res_df, date_str)
    logger.info(f"Saved predictions to database table 'ai_predictions' for {date_str}.")

    # 11b. Run Market Regime Detection
    logger.info("Running GMM Market Regime Detection...")
    regime_detector = MarketRegimeDetector()

    # Train regime detector on available indicator history
    if not indicator_train.empty:
        regime_detector.train(indicator_train)
    elif not indicator_infer.empty:
        regime_detector.train(indicator_infer)

    current_regime_label = regime_detector.predict_regime_label(indicator_infer)
    current_regime = regime_detector.predict_regime(indicator_infer)
    regime_2d_info = regime_detector.predict_2d_regime(indicator_infer)
    current_2d_regime = regime_2d_info['combo_label']
    logger.info(f"==> CURRENT MARKET REGIME DETECTED: {current_regime_label} (Code: {current_regime}), 2D: {current_2d_regime}")

    # Adjust maximum total allocation based on regime
    if current_regime == 0:  # BEAR
        max_alloc = 0.20
        logger.info("Defensive mode active (BEAR market): restricting total allocation to 20.0%")
    elif current_regime == 1:  # SIDEWAYS
        max_alloc = 0.50
        logger.info("Moderate risk mode active (SIDEWAYS market): restricting total allocation to 50.0%")
    else:  # BULL
        max_alloc = 0.85
        logger.info("Standard risk mode active (BULL market): setting total allocation to 85.0%")



    # Build formatted message for Telegram (top-10 per market)
    message_text = format_prediction_message(res_df, universe)
    print(message_text)

    # Save summarized inference results (TOP10 per market, key horizons only)
    # Full raw data is available in pipeline_result.csv
    output_path = os.path.join(result_dir, "pipeline_result.txt")
    market_syms = _market_symbols(universe)
    symbol_to_name = dict(zip(universe['symbol'], universe['name']))
    _SUMMARY_HORIZONS = [h for h in [1, 5, 20, 60] if h in res_df.columns]  # Key horizons only
    _TOP_N = 20
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== Pipeline Inference Summary (TOP20 per Market) ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total symbols analyzed: {len(res_df)}\n")
        f.write(f"Showing: Top {_TOP_N} per market | Horizons: {', '.join(str(h)+'d' for h in _SUMMARY_HORIZONS)}\n")
        f.write("Full data: pipeline_result.csv / pipeline_result.jsonl\n\n")
        if res_df.empty:
            f.write("데이터 없음\n")
        krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
        for h in _SUMMARY_HORIZONS:
            sorted_df = res_df.sort_values(by=h, ascending=False)
            f.write(f"{'='*60}\n")
            f.write(f"Horizon: {h}d\n\n")
            for m in krx_markets:
                m_set = market_syms.get(m, set())
                m_df = sorted_df[sorted_df['symbol'].isin(m_set)].head(_TOP_N)
                if m_df.empty:
                    continue
                f.write(f"--- {m} TOP {_TOP_N} ---\n")
                for rank, (_, row) in enumerate(m_df.iterrows(), 1):
                    name = symbol_to_name.get(row['symbol'], "Unknown")
                    f.write(f"  {rank}. {row['symbol']} ({name}): {row[h]*100:+.2f}%\n")
                f.write("\n")
            sp500_set = market_syms.get('SP500', set())
            sp500_df = sorted_df[sorted_df['symbol'].isin(sp500_set)].head(_TOP_N)
            if not sp500_df.empty:
                f.write(f"--- S&P 500 TOP {_TOP_N} ---\n")
                for rank, (_, row) in enumerate(sp500_df.iterrows(), 1):
                    name = symbol_to_name.get(row['symbol'], "Unknown")
                    f.write(f"  {rank}. {row['symbol']} ({name}): {row[h]*100:+.2f}%\n")
                f.write("\n")
    logger.info(f"Saved summarized pipeline result (TOP{_TOP_N}, {len(_SUMMARY_HORIZONS)} horizons) to {output_path}")

    # [NEW] Save CSV and JSON Lines format for pipeline_result
    try:
        csv_path = os.path.join(result_dir, "pipeline_result.csv")
        jsonl_path = os.path.join(result_dir, "pipeline_result.jsonl")
        res_df.to_csv(csv_path, index=False)
        res_df.to_json(jsonl_path, orient='records', lines=True)
        logger.info(f"Saved pipeline CSV to {csv_path} and JSON Lines to {jsonl_path}")
    except Exception as e:
        logger.error(f"Failed to save CSV/JSONL results: {e}")

    # Save surge detection results to separate file
    surge_output_path = os.path.join(result_dir, "surge_predictions.txt")
    with open(surge_output_path, "w", encoding="utf-8") as f:
        f.write("=== Surge Detection Results (Classifier Probabilities) ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("Horizon Target Thresholds: 1d (>=3%), 3d (>=5%), 5d (>=8%), 20d (>=15%)\n")
        f.write(f"Total symbols: {len(surge_df)}\n\n")

        if surge_df.empty:
            f.write("데이터 없음\n")
        else:
            # Merge name/market info
            surge_df = surge_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')

            krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
            for h in model.surge_horizons:
                col = f'surge_{h}d'
                if col not in surge_df.columns:
                    continue
                for m in krx_markets + ['SP500']:
                    m_df = surge_df[surge_df['market'] == m].sort_values(by=col, ascending=False)
                    if m_df.empty:
                        continue
                    f.write(f"{'='*60}\n")
                    f.write(f"[{h}일] {m} Top 20 Surge Candidates\n")
                    f.write(f"{'='*60}\n")
                    for rank, (_, row) in enumerate(m_df.head(20).iterrows(), 1):
                        name = row.get('name', 'Unknown')
                        prob = row[col] * 100
                        f.write(f"  {rank}. [{m}] {row['symbol']} ({name}): {prob:.1f}%\n")
                    f.write("\n")
    logger.info(f"Saved surge predictions ({len(surge_df)} symbols) to {surge_output_path}")

    # Also save per-market suffix files for surge predictions
    if not surge_df.empty:
        for _m in ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']:
            _m_df_surge = surge_df[surge_df['market'] == _m]
            if _m_df_surge.empty:
                continue
            _mkt_surge_path = os.path.join(result_dir, f"surge_predictions_{_m}.txt")
            with open(_mkt_surge_path, "w", encoding="utf-8") as _mf:
                _mf.write("=== Surge Detection Results (Classifier Probabilities) ===\n")
                _mf.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                _mf.write("Horizon Target Thresholds: 1d (>=3%), 3d (>=5%), 5d (>=8%), 20d (>=15%)\n")
                _mf.write(f"Total symbols: {len(_m_df_surge)}\n\n")
                for h in model.surge_horizons:
                    col = f'surge_{h}d'
                    if col not in _m_df_surge.columns:
                        continue
                    m_sorted = _m_df_surge.sort_values(by=col, ascending=False)
                    if m_sorted.empty:
                        continue
                    _mf.write(f"{'='*60}\n")
                    _mf.write(f"[{h}일] {_m} Top 20 Surge Candidates\n")
                    _mf.write(f"{'='*60}\n")
                    for rank, (_, row) in enumerate(m_sorted.head(20).iterrows(), 1):
                        name = row.get('name', 'Unknown')
                        prob = row[col] * 100
                        _mf.write(f"  {rank}. [{_m}] {row['symbol']} ({name}): {prob:.1f}%\n")
                    _mf.write("\n")
            logger.info(f"Saved surge predictions for {_m} to {_mkt_surge_path}")

    if not surge_df.empty:
        # [NEW] Save CSV and JSON Lines format for surge predictions
        try:
            surge_csv_path = os.path.join(result_dir, "surge_predictions.csv")
            surge_jsonl_path = os.path.join(result_dir, "surge_predictions.jsonl")
            surge_df.to_csv(surge_csv_path, index=False)
            surge_df.to_json(surge_jsonl_path, orient='records', lines=True)
            logger.info(f"Saved surge CSV to {surge_csv_path} and JSON Lines to {surge_jsonl_path}")
        except Exception as e:
            logger.error(f"Failed to save surge CSV/JSONL results: {e}")


    # Save lead-lag predictions to separate file
    lead_lag_output_path = os.path.join(result_dir, "lead_lag_predictions.txt")
    with open(lead_lag_output_path, "w", encoding="utf-8") as f:
        f.write("=== Lead-Lag Surge Predictions ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Based on today's top {len(model.lead_lag_leaders)} leader stock movements\n")
        f.write("Metric: Lead-Lag Pearson Correlation Index [0.0 ~ 1.0]\n")
        f.write("        (Higher = stronger historical co-movement with market leaders)\n\n")

        if lead_lag_df.empty:
            f.write("데이터 없음\n")
        else:
            lead_lag_df = lead_lag_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
            # P1: clip correlation index to [0, 1] — values >1.0 indicate scaling issues
            lead_lag_df = lead_lag_df.copy()
            lead_lag_df['lead_lag_score'] = lead_lag_df['lead_lag_score'].clip(0.0, 1.0)
            krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
            for m in krx_markets + ['SP500']:
                m_df = lead_lag_df[lead_lag_df['market'] == m].sort_values(by='lead_lag_score', ascending=False)
                if m_df.empty:
                    continue
                f.write(f"--- {m} Top 20 ---\n")
                for rank, (_, row) in enumerate(m_df.head(20).iterrows(), 1):
                    name = row.get('name', 'Unknown')
                    score = row['lead_lag_score'] * 100  # now guaranteed <= 100%
                    f.write(f"  {rank}. [{m}] {row['symbol']} ({name}): {score:.2f}%\n")
                f.write("\n")
            # P1: filter leader returns outliers (>±30% likely corporate actions / data errors)
            _OUTLIER_THRESHOLD = 0.30
            f.write("--- Leaders with highest today return ---\n")
            f.write(f"(Outliers >\u00b1{_OUTLIER_THRESHOLD*100:.0f}% excluded as potential data errors)\n")
            leader_returns = []
            for sym in model.lead_lag_leaders:
                df = infer_data_dict.get(sym)
                if df is None or len(df) < 2:
                    continue
                close = df['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                ret = (close.iloc[-1] / close.iloc[-2]) - 1
                if abs(ret) <= _OUTLIER_THRESHOLD:  # Filter extreme outliers
                    leader_returns.append((sym, ret))
            leader_returns.sort(key=lambda x: -x[1])
            symbol_to_name = dict(zip(universe['symbol'], universe['name']))
            if leader_returns:
                for rank, (sym, ret) in enumerate(leader_returns[:10], 1):
                    name = symbol_to_name.get(sym, sym)
                    f.write(f"  {rank}. {sym} ({name}): {ret*100:+.2f}%\n")
            else:
                f.write("  (No valid leader returns within normal range today)\n")
    logger.info(f"Saved lead-lag predictions ({len(lead_lag_df)} symbols) to {lead_lag_output_path}")

    # Also save per-market suffix files so merge_predictions.py can find them when
    # running in a matrix environment where each job processes one market at a time.
    if not lead_lag_df.empty:
        # Ensure market column is available (lead_lag_df may already have it from merge above)
        if 'market' not in lead_lag_df.columns:
            _ll_merged = lead_lag_df.merge(universe[['symbol', 'market']], on='symbol', how='left')
        else:
            _ll_merged = lead_lag_df.copy()
        # Also ensure name column is available
        if 'name' not in _ll_merged.columns:
            _ll_merged = _ll_merged.merge(universe[['symbol', 'name']], on='symbol', how='left')
        for _m in ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']:
            _m_df = _ll_merged[_ll_merged['market'] == _m]
            if _m_df.empty:
                continue
            _mkt_path = os.path.join(result_dir, f"lead_lag_predictions_{_m}.txt")
            with open(_mkt_path, "w", encoding="utf-8") as _mf:
                _mf.write("=== Lead-Lag Surge Predictions ===\n")
                _mf.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                _mf.write(f"Based on today's top {len(model.lead_lag_leaders)} leader stock movements\n")
                _mf.write("Metric: Lead-Lag Pearson Correlation Index [0.0 ~ 1.0]\n")
                _mf.write("        (Higher = stronger historical co-movement with market leaders)\n\n")
                _mf.write(f"--- {_m} Top 20 ---\n")
                for _rank, (_, _row) in enumerate(_m_df.head(20).iterrows(), 1):
                    _name = _row.get('name', 'Unknown')
                    _score = float(_row['lead_lag_score']) * 100
                    _mf.write(f"  {_rank}. [{_m}] {_row['symbol']} ({_name}): {_score:.2f}%\n")
                _mf.write("\n")
            logger.info(f"Saved lead-lag predictions for {_m} to {_mkt_path}")

    # Save VCP pattern detection results
    vcp_output_path = os.path.join(result_dir, "vcp_patterns.txt")
    vcp_universe_map = {s: (n, m) for s, n, m in zip(universe['symbol'],
                        universe['name'], universe['market'])}
    krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
    with open(vcp_output_path, "w", encoding="utf-8") as f:
        f.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total VCP patterns found: {len(vcp_results)}\n\n")

        if not vcp_results:
            f.write("데이터 없음\n")
        else:
            for m in krx_markets + ['SP500']:
                m_results = [r for r in vcp_results if vcp_universe_map.get(r['symbol'], ('', ''))[1] == m]
                if not m_results:
                    continue
                f.write(f"--- {m} ---\n")
                for rank, r in enumerate(m_results[:30], 1):
                    sym = r['symbol']
                    name, _market = vcp_universe_map.get(sym, ('Unknown', ''))
                    peaks = ' > '.join(f'{p:.1f}%' for p in r['contraction_peaks'])
                    f.write(f"  {rank}. [{m}] {sym} ({name})\n")
                    f.write(f"       Score: {r['vcp_score']:.0f}/100 | "
                            f"Current range: {r['current_range_pct']:.1f}% | "
                            f"Contraction: {peaks}\n")
                    f.write(f"       Above MA50: {'✓' if r['above_sma50'] else '✗'} | "
                            f"Above MA200: {'✓' if r['above_sma200'] else '✗'} | "
                            f"Near high: {'✓' if r['near_high'] else '✗'} | "
                            f"Volume declining: {'✓' if r['volume_declining'] else '✗'}\n\n")
    logger.info(f"Saved VCP patterns ({len(vcp_results)} symbols) to {vcp_output_path}")

    # 10e. Run VCP ML surge predictions
    logger.info("Running VCP ML inference...")
    vcp_ml_df = pd.DataFrame()
    if vcp_ml is not None:
        vcp_ml_df = vcp_ml.predict(infer_data_dict, indicator_infer, universe)
    vcp_ml_output_path = os.path.join(result_dir, "vcp_ml_predictions.txt")
    with open(vcp_ml_output_path, "w", encoding="utf-8") as f:
        f.write("=== VCP ML Surge Predictions ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        for h in SURGE_HORIZONS:
            for market in ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']:
                if not vcp_ml_df.empty and 'market' in vcp_ml_df.columns and f'vcp_{h}d' in vcp_ml_df.columns:
                    m_df = vcp_ml_df[vcp_ml_df['market'] == market].sort_values(by=f'vcp_{h}d', ascending=False)
                else:
                    m_df = pd.DataFrame()

                if m_df.empty:
                    f.write(f"[{h}일] {market} - (no symbols) 0.0%\n\n")
                    continue
                top_n = min(20, len(m_df))
                f.write(f"[{h}일] {market} TOP {top_n}\n")
                for rank, (_, row) in enumerate(m_df.head(top_n).iterrows(), 1):
                    name = row.get('name', 'Unknown')
                    prob = row[f'vcp_{h}d'] * 100
                    f.write(f"  {rank}. [{market}] {row['symbol']} ({name}): {prob:.1f}%\n")
                f.write("\n")
    logger.info(f"Saved VCP ML predictions to {vcp_ml_output_path}")

    # 11d. Run Ensemble Scoring
    logger.info("Running Dynamic Multi-Strategy Ensemble scoring...")
    from src.ai.ensemble_scorer import EnsembleScoringEngine
    from pathlib import Path
    import joblib

    scorer = EnsembleScoringEngine(config=cfg)

    # ── Phase 5-B: Isotonic Calibrator load / fit ───────────────────────────
    _calibrator_path = Path(model.model_dir) / "calibrators.pkl"
    if _calibrator_path.exists():
        try:
            scorer._calibrators = joblib.load(str(_calibrator_path))
            logger.info(f"[5-B] Loaded Isotonic calibrators from {_calibrator_path}")
        except Exception as _cal_e:
            logger.warning(f"[5-B] Failed to load calibrators: {_cal_e}")
    else:
        # Build historical strategy scores + outcome labels for initial calibration
        try:
            _hist_df = storage.get_ensemble_predictions_history(days=60)
            if _hist_df is not None and len(_hist_df) >= 20 and 'outcome_label' in _hist_df.columns:
                _strategy_cols = {'regression': 'reg_score', 'surge': 'surge_score',
                                  'lead_lag': 'll_score', 'vcp_rule': 'vcp_rule_score',
                                  'vcp_ml': 'vcp_ml_score'}
                _strat_scores = {}
                for _sname, _scol in _strategy_cols.items():
                    if _scol in _hist_df.columns:
                        _strat_scores[_sname] = _hist_df[_scol].values
                _true_labels = _hist_df['outcome_label'].values
                if _strat_scores:
                    scorer.fit_calibrators(_strat_scores, _true_labels)
                    joblib.dump(scorer._calibrators, str(_calibrator_path))
                    logger.info(f"[5-B] Fitted and saved Isotonic calibrators "
                                f"({len(_true_labels)} samples) → {_calibrator_path}")
        except Exception as _cal_fit_e:
            logger.warning(f"[5-B] Calibrator fitting skipped: {_cal_fit_e}")

    # ── Phase 5-A: Sentiment Meta Filter evaluation ──────────────────────────
    _blacklist_map = {}
    try:
        from src.risk.sentiment_filter import SentimentMetaFilter
        _sentiment_filter = SentimentMetaFilter(
            risk_threshold=cfg.sentiment_risk_threshold,
            crawl_naver_news=cfg.sentiment_crawl_naver_news,
        )
        # Evaluate top-100 KRX candidates from ensemble preview (by reg_score)
        _krx_universe_syms = [
            row['symbol'] for _, row in universe.iterrows()
            if row.get('market', '') in ('KOSPI', 'KOSDAQ', 'KONEX')
            and str(row['symbol']).isdigit()
        ]
        # Prioritise by regression score if available, else use order
        if not res_df.empty and 'symbol' in res_df.columns:
            _reg_top = res_df.sort_values(by=20 if 20 in res_df.columns else res_df.columns[-1],
                                          ascending=False)['symbol'].tolist()
            _eval_syms = [s for s in _reg_top if s in set(_krx_universe_syms)][:100]
        else:
            _eval_syms = _krx_universe_syms[:100]

        if _eval_syms:
            logger.info(f"[5-A] Running SentimentMetaFilter on {len(_eval_syms)} KRX candidates...")
            for _sym in _eval_syms:
                try:
                    _result = _sentiment_filter.evaluate_symbol(_sym)
                    if _result.is_blacklisted:
                        _blacklist_map[_sym] = _result
                except Exception:
                    pass
            if _blacklist_map:
                logger.info(f"[5-A] Sentiment blacklist: {len(_blacklist_map)} symbols — "
                            f"{', '.join(list(_blacklist_map.keys())[:10])}")
                _notify_telegram(
                    f"⚠️ [감성 필터] {len(_blacklist_map)}개 종목 블랙리스트 등록:\n"
                    + "\n".join(f"  • {sym}: {res.reason[:60]}" for sym, res in list(_blacklist_map.items())[:5]),
                    "WARNING",
                )
            else:
                logger.info("[5-A] Sentiment filter: no blacklisted symbols detected.")
    except Exception as _sent_e:
        logger.warning(f"[5-A] SentimentMetaFilter skipped: {_sent_e}")

    # Compute Stat-Arb scores for ensemble
    stat_arb_df = pd.DataFrame()
    if 'stat_arb_pairs' in locals() and stat_arb_pairs:
        sa_rows = []
        for p in stat_arb_pairs:
            pair = p.get('pair', ())
            z = abs(p.get('z_score', 0.0))
            score = min(z / 3.0, 1.0)
            for s in pair:
                sa_rows.append({'symbol': s, 'stat_arb_score': score})
        if sa_rows:
            stat_arb_df = pd.DataFrame(sa_rows).groupby('symbol', as_index=False).max()

    # Compute Sector Rotation scores for ensemble
    try:
        from src.core.sector_rotation import SectorRotationEngine
        sector_engine = SectorRotationEngine()
        pipe_sector_map = storage.get_sector_map() if hasattr(storage, 'get_sector_map') else {}
        if not pipe_sector_map and 'sector' in universe.columns:
            pipe_sector_map = dict(zip(universe['symbol'], universe['sector'].fillna('General')))
        sector_df = sector_engine.compute_sector_momentum_scores(
            infer_data_dict,
            sector_map=pipe_sector_map,
            macro_indicators=indicator_infer,
            regime_label=str(current_2d_regime)
        )

        # Save Sector Rotation predictions report
        if sector_df is not None and not sector_df.empty:
            sector_output_path = os.path.join(result_dir, "sector_predictions.txt")
            sector_df_merged = sector_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
            if 'sector' in pipe_sector_map:
                sector_df_merged['sector'] = sector_df_merged['symbol'].map(lambda s: pipe_sector_map.get(s, 'General'))
            elif 'sector' in universe.columns:
                sec_sub = universe[['symbol', 'sector']]
                sector_df_merged = sector_df_merged.merge(sec_sub, on='symbol', how='left')
            else:
                sector_df_merged['sector'] = 'General'

            sector_df_merged = sector_df_merged.sort_values(by='sector_score', ascending=False)
            with open(sector_output_path, "w", encoding="utf-8") as f:
                f.write("=== Sector Rotation Momentum & Macro Sensitivity Report ===\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"Total symbols evaluated: {len(sector_df_merged)}\n\n")
                f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Market':<10}{'Sector':<25}{'Sector Score':<15}\n")
                f.write("-" * 85 + "\n")
                for rank, (_, row) in enumerate(sector_df_merged.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:18] if pd.notna(row['name']) else "Unknown"
                    sec_str = str(row.get('sector', 'General'))[:23]
                    mkt_str = str(row.get('market', 'KRX'))
                    f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<20}{mkt_str:<10}{sec_str:<25}{row['sector_score']*100:>13.1f}%\n")
            logger.info(f"Saved sector rotation predictions ({len(sector_df_merged)} symbols) to {sector_output_path}")
    except Exception as _sec_e:
        logger.warning(f"Sector rotation score calculation skipped: {_sec_e}")
        sector_df = pd.DataFrame()

    # Calculate rolling Sharpes for all strategies if strategy_returns exists
    _strat_ret = locals().get('strategy_returns')
    rolling_sharpes = scorer.compute_rolling_sharpe(_strat_ret) if isinstance(_strat_ret, dict) else None

    # default target horizon is 20d (8-Strategy Ensemble)
    ensemble_df = scorer.calculate_ensemble_score(
        regime=current_2d_regime,
        regression_df=res_df,
        surge_df=surge_df,
        lead_lag_df=lead_lag_df,
        vcp_rule_df=vcp_results,
        vcp_ml_df=vcp_ml_df,
        stat_arb_df=stat_arb_df,
        sector_df=sector_df,
        rolling_sharpes=rolling_sharpes,
        target_horizon=20,
        sentiment_blacklist=_blacklist_map,
    )


    # 11e. Save Ensemble Predictions to DB
    try:
        storage.save_ensemble_predictions(ensemble_df, date_str)
        logger.info(f"Saved ensemble predictions ({len(ensemble_df)} symbols) to DB table 'ensemble_predictions'")
    except Exception as e:
        logger.error(f"Failed to save ensemble predictions to DB: {e}")

    # 11f. Save Ensemble Predictions Report (ensemble_predictions.txt)
    # Gather decision basis metrics
    sp500_ret_20d = float(indicator_infer['sp500_change'].tail(20).mean()) if 'sp500_change' in indicator_infer.columns else 0.0
    sp500_vol_20d = float(indicator_infer['sp500_change'].tail(20).std()) if 'sp500_change' in indicator_infer.columns else 0.0
    kospi_ret_20d = float(indicator_infer['kospi_change'].tail(20).mean()) if 'kospi_change' in indicator_infer.columns else 0.0
    kospi_vol_20d = float(indicator_infer['kospi_change'].tail(20).std()) if 'kospi_change' in indicator_infer.columns else 0.0
    vix_val = float(indicator_infer['vix_change'].iloc[-1]) if 'vix_change' in indicator_infer.columns else 0.0
    usdkrw_val = float(indicator_infer['usdkrw_change'].iloc[-1]) if 'usdkrw_change' in indicator_infer.columns else 0.0
    us10y_val = float(indicator_infer['us10y'].iloc[-1]) if 'us10y' in indicator_infer.columns else 0.0

    ensemble_weights = scorer.compute_dynamic_weights_from_sharpe(rolling_sharpes or {}, current_2d_regime)

    ensemble_output_path = os.path.join(result_dir, "ensemble_predictions.txt")
    ensemble_df_merged = ensemble_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')

    with open(ensemble_output_path, "w", encoding="utf-8") as f:
        f.write("=== Dynamic Multi-Strategy Ensemble Predictions ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        # 1. Executive Summary & Basis
        f.write("--- Executive Market Summary ---\n")
        f.write(f"Current Market Regime Detected: {current_regime_label} (2D State: {current_2d_regime})\n")
        f.write(f"Maximum Total Allocation Allowed: {max_alloc*100:.1f}%\n\n")

        f.write("--- Judgment Basis (Global Macro Indicators) ---\n")
        f.write(f"  S&P 500 (20d Rolling Mean Return) : {sp500_ret_20d:+.3f}% / day\n")
        f.write(f"  S&P 500 (20d Rolling Volatility)  : {sp500_vol_20d:.3f}%\n")
        f.write(f"  KOSPI (20d Rolling Mean Return)   : {kospi_ret_20d:+.3f}% / day\n")
        f.write(f"  KOSPI (20d Rolling Volatility)    : {kospi_vol_20d:.3f}%\n")
        f.write(f"  VIX Index (Fear Gauge)            : {vix_val:.2f}\n")
        f.write(f"  USD/KRW FX Rate                   : {usdkrw_val:,.2f} KRW\n")
        f.write(f"  US 10Y Bond Yield (TNX)           : {us10y_val:.2f}%\n\n")

        f.write("--- Applied Ensemble Strategy Weights (8 Strategies) ---\n")
        f.write(f"  XGBoost Regression Fundamentals   : {ensemble_weights.get('regression', 0.0)*100:.1f}%\n")
        f.write(f"  Surge Classifier (XGBoost)        : {ensemble_weights.get('surge', 0.0)*100:.1f}%\n")
        f.write(f"  Index & Sector Lead-Lag Flow      : {ensemble_weights.get('lead_lag', 0.0)*100:.1f}%\n")
        f.write(f"  VCP Rule Pattern Detector         : {ensemble_weights.get('vcp_rule', 0.0)*100:.1f}%\n")
        f.write(f"  VCP Machine Learning Predictor    : {ensemble_weights.get('vcp_ml', 0.0)*100:.1f}%\n")
        f.write(f"  Strict Causal LSTM Deep Learning  : {ensemble_weights.get('lstm', 0.0)*100:.1f}%\n")
        f.write(f"  Stat-Arb Cointegration Mean Rev   : {ensemble_weights.get('stat_arb', 0.0)*100:.1f}%\n")
        f.write(f"  Sector Rotation Relative Momentum : {ensemble_weights.get('sector_rotation', 0.0)*100:.1f}%\n\n")

        # 2. Recommendations per market
        f.write("--- Top 20 Recommendations by Market ---\n")
        krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
        for market in krx_markets + ['SP500']:
            m_df = ensemble_df_merged[ensemble_df_merged['market'] == market].sort_values(by='ensemble_score', ascending=False)
            if m_df.empty:
                continue
            f.write("\n=========================================\n")
            f.write(f"[{market}] Top 20 Ensemble Picks\n")
            f.write("=========================================\n")
            f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Ensemble Score':<16}{'Expected Return':<18}{'Reg':<6}{'Surge':<6}{'L-L':<6}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<6}{'S-Arb':<6}{'Sec-R':<6}\n")
            f.write("-" * 125 + "\n")
            for rank, (_, row) in enumerate(m_df.head(20).iterrows(), 1):
                name_str = str(row['name'])[:18] if pd.notna(row['name']) else "Unknown"
                vcp_rule_val = row.get('vcp_rule_score', 0.0)
                lstm_val = row.get('lstm_score', 0.0)
                sa_val = row.get('stat_arb_score', 0.0)
                sec_val = row.get('sector_score', 0.0)
                f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<20}{row['ensemble_score']*100:>13.1f}%{row['ensemble_expected_return']:>15.1f}%{row['reg_score']*100:>5.0f}%{row['surge_score']*100:>5.0f}%{row['ll_score']*100:>5.0f}%{vcp_rule_val*100:>5.0f}%{row['vcp_ml_score']*100:>5.0f}%{lstm_val*100:>5.0f}%{sa_val*100:>5.0f}%{sec_val*100:>5.0f}%\n")
            f.write("\n")
    logger.info(f"Saved ensemble predictions ({len(ensemble_df)} symbols) to {ensemble_output_path}")

    # 11g. Run Portfolio Position Sizing (Ensemble Link)
    logger.info("Running Portfolio Position Sizing allocation on Ensemble expectancies...")
    # Prepare the input DataFrame expected by PortfolioAllocator: ['symbol', 20]
    ensemble_for_alloc = ensemble_df[['symbol', 'ensemble_expected_return']].rename(
        columns={'ensemble_expected_return': 20}
    )
    allocator = PortfolioAllocator(target_horizon=20, max_total_allocation=max_alloc)
    alloc_df = allocator.allocate(ensemble_for_alloc, infer_data_dict, total_portfolio_value=1000000000.0, use_hrp=True, regime=current_2d_regime)

    if not alloc_df.empty:
        alloc_df = alloc_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
        alloc_output_path = os.path.join(result_dir, "portfolio_allocation.txt")
        with open(alloc_output_path, "w", encoding="utf-8") as f:
            f.write("=== Portfolio Allocation Recommendations (Ensemble Kelly/Sharpe Optimized) ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("Total Capital: 1,000,000,000 KRW/USD\n")
            f.write("Target Horizon: 20d\n\n")
            f.write(f"Current Market Regime Detected: {current_regime_label} (Code: {current_regime})\n")
            f.write(f"Maximum Total Allocation Allowed: {max_alloc*100:.1f}%\n\n")

            f.write(f"{'No.':<4}{'Symbol':<10}{'Name':<20}{'Market':<10}{'Return':<10}{'Volatility':<12}{'Weight':<10}{'Amount':<15}\n")
            f.write("-" * 92 + "\n")
            for rank, (_, row) in enumerate(alloc_df.iterrows(), 1):
                name_str = str(row['name'])[:18] if pd.notna(row['name']) else "Unknown"
                f.write(f"{rank:<4}{row['symbol']:<10}{name_str:<20}{row['market']:<10}{row['predicted_return']:>8.2f}%{row['volatility']*100:>11.2f}%{row['weight']*100:>9.2f}%{row['allocation_amount']:>14,.0f}\n")

            allocated_weight = alloc_df['weight'].sum()
            cash_weight = 1.0 - allocated_weight
            cash_amount = cash_weight * 1000000000.0
            f.write("-" * 92 + "\n")
            f.write(f"Allocated Capital: {allocated_weight*100:>5.2f}% ({alloc_df['allocation_amount'].sum():>14,.0f})\n")
            f.write(f"Remaining Cash   : {cash_weight*100:>5.2f}% ({cash_amount:>14,.0f})\n")
        logger.info(f"Saved portfolio allocation recommendations to {alloc_output_path}")

    # ── Phase 6-A: Generate Backtest Summary for GitHub Pages ────────────────
    try:
        from src.analysis.backtest_summary import generate_backtest_summary
        generate_backtest_summary(result_dir=result_dir)
        logger.info("[6-A] Generated backtest_summary.json for GitHub Pages dashboard")
    except Exception as _bt_summary_e:
        logger.warning(f"[6-A] Backtest summary generation skipped: {_bt_summary_e}")

    # ── Phase 6-C: Save Pipeline Profiling Metrics ───────────────────────────
    try:
        from src.utils.pipeline_profiler import save_profile_report
        save_profile_report(result_dir=result_dir)
    except Exception as _prof_e:
        logger.warning(f"[6-C] Pipeline profiler report skipped: {_prof_e}")

    # ── Phase 6-D: Generate GitHub Pages HTML Dashboard ─────────────────────
    try:
        from generate_report import main as generate_html_report
        gh_pages_dir = Path(__file__).resolve().parent / "gh-pages"
        gh_pages_dir.mkdir(parents=True, exist_ok=True)
        generate_html_report(args_list=["--result-dir", str(result_dir), "--out", str(gh_pages_dir / "index.html")])
        logger.info(f"[6-D] Updated GitHub Pages HTML dashboard at {gh_pages_dir / 'index.html'}")
    except Exception as _gh_html_e:
        logger.warning(f"[6-D] GitHub Pages dashboard generation skipped: {_gh_html_e}")

    # 12. Post-pipeline verification
    logger.info("Running post-pipeline verification checks...")
    # stat_arb_predictions.txt is intentionally excluded — it is an optional output
    # that may not exist when no cointegrated pairs are found, so verification would
    # produce false-positive warnings.
    verification_files = [
        "pipeline_result.txt",
        "surge_predictions.txt",
        "lead_lag_predictions.txt",
        "vcp_patterns.txt",
        "vcp_ml_predictions.txt",
    ]
    for filename in verification_files:
        filepath = os.path.join(result_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Verification failed: Output file {filename} does not exist.")
        elif os.path.getsize(filepath) == 0:
            logger.warning(f"Verification failed: Output file {filename} is empty.")
        else:
            logger.info(f"Verification check: Output file {filename} exists and is not empty.")

    pipeline_res_path = os.path.join(result_dir, "pipeline_result.txt")
    if os.path.exists(pipeline_res_path):
        try:
            with open(pipeline_res_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            returns = re.findall(r'\):\s*([+-]?\d+\.\d+)%', content)
            if returns:
                all_zero = all(float(r) == 0.0 for r in returns)
                if all_zero:
                    logger.warning("Verification failed: All expected returns in pipeline_result.txt are 0.0.")
                else:
                    logger.info("Verification check: Found non-zero expected returns in pipeline_result.txt.")
            else:
                logger.warning("Verification failed: Could not parse expected returns from pipeline_result.txt.")
        except Exception as e:
            logger.warning(f"Verification failed: Error reading/parsing pipeline_result.txt: {e}")

    return res_df, message_text

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Stock Trading Prediction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py
  python run_pipeline.py --target KOSPI
  python run_pipeline.py --target SP500 --skip-training
  python run_pipeline.py --debug --target KOSDAQ
        """,
    )
    parser.add_argument(
        "--target",
        choices=["SP500", "KOSPI", "KOSDAQ", "KONEX", "KRX"],
        default=None,
        metavar="MARKET",
        help="Market to run inference on: SP500 / KOSPI / KOSDAQ / KONEX / KRX "
             "(default: reads INFERENCE_TARGET env var, or all markets)",
    )
    parser.add_argument(
        "--skip-training",
        action="store_true",
        default=False,
        help="Skip model training and use existing models from disk",
    )
    parser.add_argument(
        "--skip-inference",
        action="store_true",
        default=False,
        help="Skip prediction phase, only fetch and cache database data",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode: small sample (3 symbols/market), fast dry-run",
    )
    args = parser.parse_args()

    # Apply CLI overrides to environment (pipeline reads from os.environ)
    if args.target:
        os.environ["INFERENCE_TARGET"] = args.target
        logger.info(f"[CLI] INFERENCE_TARGET overridden to: {args.target}")
    if args.skip_training:
        os.environ["SKIP_TRAINING"] = "True"
        logger.info("[CLI] SKIP_TRAINING enabled")
    if args.skip_inference:
        os.environ["SKIP_INFERENCE"] = "True"
        logger.info("[CLI] SKIP_INFERENCE enabled")
    if args.debug:
        os.environ["DEBUG_MODE"] = "True"
        logger.info("[CLI] DEBUG_MODE enabled")

    _start = time.time()
    # Build GHA inline button when running inside GitHub Actions
    _gha_url = None
    _gha_server = os.environ.get("GITHUB_SERVER_URL", "").strip()
    _gha_repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    _gha_run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    if _gha_server and _gha_repo and _gha_run_id:
        _gha_url = f"{_gha_server}/{_gha_repo}/actions/runs/{_gha_run_id}"

    try:
        execute_prediction_pipeline()
        _elapsed = time.time() - _start
        _buttons = [[{"text": "📊 GHA 결과 보기", "url": _gha_url}]] if _gha_url else None
        _notify_telegram(
            f"✅ 파이프라인 완료\n"
            f"⏱ 소요시간: {_elapsed / 60:.1f}분\n"
            f"📅 실행시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "SUCCESS",
            buttons=_buttons,
        )
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
    except Exception as _exc:
        _elapsed = time.time() - _start
        _tb = traceback.format_exc()
        _tb_tail = _tb[-800:] if len(_tb) > 800 else _tb
        logger.exception("Pipeline failed with unhandled exception.")

        # Check if output files were still successfully written despite the error
        result_dir = os.path.join(os.path.dirname(__file__), "result")
        essential_file = os.path.join(result_dir, "pipeline_result.txt")
        has_results = os.path.exists(essential_file) and os.path.getsize(essential_file) > 0

        _buttons = [[{"text": "📋 에러 로그 보기", "url": _gha_url}]] if _gha_url else None

        if has_results:
            logger.info("Output files detected in result directory. Treating as partial success (exiting with 0).")
            _notify_telegram(
                f"⚠️ 파이프라인 부분 완료 (오류 발생)\n"
                f"⏱ 소요시각: {_elapsed / 60:.1f}분\n"
                f"❌ 오류: {type(_exc).__name__}: {_exc}\n\n"
                f"결과 파일이 정상 생성되어 프로세스를 완료 처리합니다.",
                "WARNING",
                buttons=_buttons,
            )
            sys.exit(0)
        else:
            _notify_telegram(
                f"🚨 파이프라인 실패\n"
                f"⏱ 소요시각: {_elapsed / 60:.1f}분\n"
                f"❌ 오류: {type(_exc).__name__}: {_exc}\n\n"
                f"```\n{_tb_tail}\n```",
                "CRITICAL",
                buttons=_buttons,
            )
            sys.exit(1)

