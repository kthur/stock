import os
import sys
import gc
import logging
import socket
import time
import threading
import traceback
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import FinanceDataReader as fdr
import yfinance as yf
import warnings
from pathlib import Path

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
from src.analysis.regime_detector import MarketRegimeDetector
from src.utils.rate_limiter import get_global_rate_limiter
from src.utils.technical_cache import DataFrameCache
from src.utils.http_session import setup_global_http_headers
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result, retry_if_exception_type

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize global HTTP session headers for yfinance and FinanceDataReader calls
setup_global_http_headers()


def detect_shared_series_corruption(vix_val, wti_val, gold_val, us10y_val) -> bool:
    """P0: Detect shared-series / DB cache contamination on RAW indicator values.

    If several unrelated indicators resolve to (nearly) the same value, the DB
    holds one ticker's Close for every symbol (e.g. 103.478 everywhere). Must be
    evaluated on raw values BEFORE plausibility bounds replace out-of-range
    entries, otherwise the VIX gets defaulted first and the spread widens past
    the detection threshold.
    """
    import math
    candidates = []
    for v in (vix_val, wti_val, gold_val,
              us10y_val * 10.0 if us10y_val is not None and not (isinstance(us10y_val, float) and math.isnan(us10y_val)) and us10y_val < 25 else us10y_val):
        try:
            fv = float(v)
            if fv > 0 and not math.isnan(fv):
                candidates.append(fv)
        except (TypeError, ValueError):
            continue
    if len(candidates) < 3:
        return False
    return (max(candidates) - min(candidates)) < 1.0


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
        return 0

    prefetched_count = 0

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
        return 0

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

                # Single-ticker fast path: no binary split needed
                if len(tickers) == 1:
                    try:
                        df_res = yf.download(tickers, start=start_dt, progress=False, auto_adjust=True, group_by='ticker')
                        if df_res is not None and not df_res.empty:
                            return df_res
                    except Exception as ex:
                        logger.warning(f"Excluding bad ticker from batch: {tickers[0]} due to: {ex}")
                    # Empty result (delisted / no data) — skip silently
                    return pd.DataFrame()

                try:
                    df_res = yf.download(tickers, start=start_dt, progress=False, auto_adjust=True, group_by='ticker')
                    if df_res is not None and not df_res.empty:
                        return df_res
                except Exception:
                    pass  # Fall through to binary split

                # Binary split to isolate bad tickers
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
                            # MultiIndex check: level 0 or level 1 depending on yfinance group_by
                            if yf_ticker in df.columns.get_level_values(0):
                                ticker_df = df.xs(yf_ticker, level=0, axis=1).dropna(how='all')
                            elif yf_ticker in df.columns.get_level_values(1):
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
                                prefetched_count += 1
            except Exception as e:
                logger.debug(f"Batch download failed for chunk: {e}")

    logger.info(f"Prefetched and cached prices for {prefetched_count}/{len(symbols)} symbols in DB.")
    return prefetched_count


def fetch_data_fdr(symbol: str, market: str, start_date: str, price_db: Optional[StockPriceDB] = None,
                   freshness_days: int = 7, update_interval: int = 0) -> Optional[pd.DataFrame]:
    """Fetch price data for a single symbol using technical_cache + MarketDataHandler (Tier 1 yfinance, Tier 2 FDR, Tier 3 DB)."""
    def _fetch_fallback(s: str, d: str) -> Optional[pd.DataFrame]:
        cached_df = None
        stale = True if freshness_days >= 0 else False
        if price_db is not None:
            if freshness_days >= 0:
                stale = price_db.needs_update(s, max_age_days=freshness_days, start_date=d)

            cached_df = price_db.get_prices(s, start_date=d)
            if cached_df is not None and not cached_df.empty:
                cached_df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in cached_df.columns]

            if not stale and cached_df is not None and not cached_df.empty:
                return cached_df

        network_result = None
        fetch_start = cached_df.index.max().strftime("%Y-%m-%d") if (cached_df is not None and not cached_df.empty) else d
        try:
            network_result = _fetch_data_fdr_network(s, market, fetch_start)
            if network_result is not None and not network_result.empty:
                network_result.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in network_result.columns]
        except Exception as e:
            logger.warning(f"Tier 1 & 2 network download failed for {s}: {e}")

        if network_result is not None and not network_result.empty:
            if price_db is not None:
                try:
                    price_db.update_prices(s, network_result)
                except Exception as ex:
                    logger.debug(f"Failed to cache prices for {s}: {ex}")

            if cached_df is not None and not cached_df.empty:
                merged_df = pd.concat([cached_df, network_result])
                merged_df = merged_df[~merged_df.index.duplicated(keep='last')].sort_index()
                return merged_df
            return network_result

        # 4. Tier 3 Fallback: Network failed, fall back to DB cache if available
        if (cached_df is None or cached_df.empty) and price_db is not None:
            cached_df = price_db.get_prices(s, start_date=None)
            if cached_df is not None and not cached_df.empty:
                cached_df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in cached_df.columns]

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
    if result is not None and not result.empty:
        result.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in result.columns]
    return result


# Global indicator & Sector ETF tickers → feature column names
_INDICATOR_TICKERS = {
    '^VIX': 'vix_change',
    '^TNX': 'us10y',         # US 10Y Treasury Yield (10년물)
    '^FVX': 'us5y',          # US 5Y Treasury Yield (5년물)
    '^IRX': 'us3m_yield',    # US 13-Week T-Bill (3개월물)
    # NOTE: '2YY=X' (US2Y), 'KR3YT=RR' (KR3Y), 'KR10YT=RR' (KR10Y), '^CPC' (Put/Call Ratio)
    #       are no longer available via yfinance (404 / YFTzMissingError).
    #       Removed to prevent repeated retry noise. Cached DB values will be used as fallback.
    'USDKRW=X': 'usdkrw_change',
    'CL=F': 'wti_change',
    '^KS11': 'kospi_change',
    '^KQ11': 'kosdaq_change',
    # Sector ETFs
    '091160.KS': 'kodex_semicon_change',
    '305720.KS': 'kodex_battery_change',
    '244580.KS': 'kodex_bio_change',
    'XLK': 'xlk_change',
    'XLF': 'xlf_change',
    'XLV': 'xlv_change',
    'XLE': 'xle_change',
    # Expanded Macro Indicators (Yield Curve, Credit, Assets)
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
        raw.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in raw.columns]
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
            raw.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in raw.columns]
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
            if cached_df is not None and not cached_df.empty:
                cached_df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in cached_df.columns]
                if not stale:
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
                            new_df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in new_df.columns]
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
                if df is not None and not df.empty:
                    df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in df.columns]
                    if price_db is not None:
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
            df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in df.columns]
            if col_name == 'vix_change':
                return (col_name, df['Close'].pct_change().fillna(0.0) * 100, 'vix_raw', df['Close'].ffill())
            elif col_name == 'usdkrw_change':
                return (col_name, df['Close'].pct_change().fillna(0.0) * 100, 'usdkrw_raw', df['Close'].ffill())
            elif col_name.endswith('_change'):
                return (col_name, df['Close'].pct_change().fillna(0.0) * 100)
            elif col_name == 'put_call_ratio':
                return (col_name, df['Close'].ffill().fillna(0.6))
            elif col_name in ('us10y', 'us3m_yield', 'kr10y'):
                # ^TNX, ^IRX, KR10YT=RR: yfinance reports yield × 10 (e.g. 4.25% → Close=42.5)
                # Divide by 10 to restore actual yield percentage.
                raw_yield = df['Close'].ffill()
                scaled = raw_yield / 10.0
                # If raw value looks already scaled (<= 20), keep as-is (some providers return real %)
                scaled = scaled.where(raw_yield >= 1.0, raw_yield)  # safety guard: raw < 1 => already percent
                return (col_name, scaled.fillna(float('nan')))
            else:
                return (col_name, df['Close'].ffill().fillna(float('nan')))
        return (col_name, pd.Series(dtype=float))


    combined = {}
    with ThreadPoolExecutor(max_workers=len(_INDICATOR_TICKERS)) as pool:
        futures = {pool.submit(_fetch_one, t, c): c for t, c in _INDICATOR_TICKERS.items()}
        for f in as_completed(futures):
            try:
                res = f.result()
                if len(res) == 4:
                    combined[res[0]] = res[1]
                    combined[res[2]] = res[3]
                else:
                    combined[res[0]] = res[1]
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

    # ① US10Y - US2Y 표준 장단기 금리차 (1순위: US2Y, 2순위: US5Y Fallback)
    # 연준 기준금리와 시장 기대치가 집중되는 2년물 금리와의 스프레드를 표준으로 사용
    # 역전(spread < 0) → 6~18개월 내 경기 침체 및 BEAR 레짐 전환 선행 신호
    if 'us10y' in result.columns and 'us2y' in result.columns and not result['us2y'].dropna().empty:
        result['us10y_us2y_spread'] = result['us10y'] - result['us2y']
    elif 'us10y' in result.columns and 'us5y' in result.columns:
        result['us10y_us2y_spread'] = result['us10y'] - result['us5y']
    elif 'us10y' in result.columns:
        result['us10y_us2y_spread'] = 0.0

    # ② 한/미 국채 10년물 금리차 (외국인 수급 자금 이탈 리스크 지표)
    # 금리차 확대(음수 방향, 미국 > 한국) 시 외국인 순매도 압력 증가
    if 'us10y' in result.columns and 'kr10y' in result.columns:
        result['kr_us_10y_spread'] = result['kr10y'] - result['us10y']
    elif 'kr10y' in result.columns:
        result['kr_us_10y_spread'] = 0.0

    # ③ 한국 채권 수익률 곡선 (kr10y - kr3y): 국내 경기 선행 지수
    if 'kr10y' in result.columns and 'kr3y' in result.columns:
        result['kr_yield_curve'] = result['kr10y'] - result['kr3y']
    elif 'kr10y' in result.columns:
        result['kr_yield_curve'] = 0.0

    # ④ 인플레이션 충격 복합 지표 (유가 + 환율 동시 상승 = 수입물가 이중 충격)
    # wti_change > 0 & usdkrw_change > 0: 국내 원자재 수입 비용 급증 → MQ Factor 가중치 하향 신호
    if 'wti_change' in result.columns and 'usdkrw_change' in result.columns:
        wti_pos = (result['wti_change'] > 0).astype(float)
        krw_pos = (result['usdkrw_change'] > 0).astype(float)
        result['inflation_shock_index'] = (
            result['wti_change'].clip(lower=0.0) * wti_pos
            + result['usdkrw_change'].clip(lower=0.0) * krw_pos
        )
    elif 'wti_change' in result.columns:
        result['inflation_shock_index'] = result['wti_change'].clip(lower=0.0)
    else:
        result['inflation_shock_index'] = 0.0

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
    for m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
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
    krx_markets = ['KOSPI', 'KOSDAQ']
    us_markets = ['SP500', 'NASDAQ', 'RUSSELL2000']
    for h in horizons:
        if h not in res_df.columns:
            continue
        sorted_df = res_df.sort_values(by=h, ascending=False)

        for m in krx_markets:
            m_df = sorted_df[sorted_df['symbol'].isin(market_syms.get(m, set()))]
            if not m_df.empty:
                lines.append(f"\n*{h}일 예상 — {m} TOP 10*")
                lines.extend(_fmt_top(m_df, h, symbol_to_name, symbol_to_market, 10))

        for m in us_markets:
            m_df = sorted_df[sorted_df['symbol'].isin(market_syms.get(m, set()))]
            if not m_df.empty:
                lines.append(f"\n*{h}일 예상 — {m} TOP 10*")
                lines.extend(_fmt_top(m_df, h, symbol_to_name, symbol_to_market, 10))

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
    sp500_symbols = universe[universe['market'] == 'SP500']['symbol'].tolist()
    nasdaq_symbols = universe[universe['market'] == 'NASDAQ']['symbol'].tolist()
    russell_symbols = universe[universe['market'] == 'RUSSELL2000']['symbol'].tolist()
    krx_symbols = kospi_symbols + kosdaq_symbols

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
        target_env = os.environ.get("INFERENCE_TARGET", "SP500,NASDAQ,RUSSELL2000,KRX").strip().upper()
        targets = [t.strip() for t in target_env.split(",") if t.strip()]

        sp500_active = "SP500" in targets or not targets
        nasdaq_active = "NASDAQ" in targets or not targets
        russell_active = "RUSSELL2000" in targets or "RUSSELL" in targets or not targets
        kospi_active = "KOSPI" in targets or "KRX" in targets or not targets
        kosdaq_active = "KOSDAQ" in targets or "KRX" in targets or not targets

        active_krx_symbols = []
        if kospi_active:
            active_krx_symbols.extend(kospi_symbols)
        if kosdaq_active:
            active_krx_symbols.extend(kosdaq_symbols)

        active_us_symbols = []
        if sp500_active:
            active_us_symbols.extend(sp500_symbols)
        if nasdaq_active:
            active_us_symbols.extend(nasdaq_symbols)
        if russell_active:
            active_us_symbols.extend(russell_symbols)

        sp500_sample = cfg.resolve_sample_size(cfg.train_sample_sp500, len(active_us_symbols)) if active_us_symbols else 0
        krx_sample = cfg.resolve_sample_size(cfg.train_sample_krx, len(active_krx_symbols)) if active_krx_symbols else 0

        if cfg.debug_mode:
            sp500_sample = min(5, sp500_sample) if active_us_symbols else 0
            krx_sample = min(5, krx_sample) if active_krx_symbols else 0
            logger.info(f"[DEBUG MODE] Overriding training samples: US={sp500_sample}, KRX={krx_sample}")

        def _safe_sample(population, k):
            if k >= len(population):
                return list(population)
            return random.sample(population, k)

        train_krx_overall = _safe_sample(active_krx_symbols, krx_sample) if active_krx_symbols else []
        train_krx_set = set(train_krx_overall)
        train_us_overall = _safe_sample(active_us_symbols, sp500_sample) if active_us_symbols else []
        train_symbols = train_us_overall + train_krx_overall

        # Per-market breakdown for training (preserve market proportions)
        train_sp500 = [s for s in train_symbols if s in sp500_symbols]
        train_nasdaq = [s for s in train_symbols if s in nasdaq_symbols]
        train_russell = [s for s in train_symbols if s in russell_symbols]
        train_kospi = [s for s in train_krx_set if s in kospi_symbols]
        train_kosdaq = [s for s in train_krx_set if s in kosdaq_symbols]

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

        # 7. Train XGBoost models per market (KOSPI/KOSDAQ/SP500/NASDAQ/RUSSELL2000)
        if not df_train.empty and 'symbol' in df_train.columns:
            df_train['symbol'] = df_train['symbol'].astype(str)
            train_symbol_set = set(df_train['symbol'])
            # Build per-market train DataFrames from the merged df_train
            market_dfs = {}
            for m_name, m_symbols in [('sp500', train_sp500), ('nasdaq', train_nasdaq),
                                       ('russell2000', train_russell), ('kospi', train_kospi),
                                       ('kosdaq', train_kosdaq)]:
                m_sym_strs = [str(s) for s in m_symbols]
                active = [s for s in m_sym_strs if s in train_symbol_set]
                m_df = df_train[df_train['symbol'].isin(active)] if active else pd.DataFrame()
                if not m_df.empty:
                    logger.info(f"Training data for {m_name}: {len(m_df)} rows, {m_df['symbol'].nunique()} symbols")
                market_dfs[m_name] = m_df
        else:
            market_dfs = {m: pd.DataFrame() for m in ['sp500', 'nasdaq', 'russell2000', 'kospi', 'kosdaq']}

        # S8 fix: ThreadPoolExecutor avoids pickle serialization overhead of ProcessPool.
        # XGBoost/LightGBM release the GIL during training, so threads are efficient here.
        with storage.pipeline_stage("train_regression"):
            _train_failures = []
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
                        _train_failures.append(f"{futures[f]}: {e}")
            if _train_failures:
                _notify_telegram(f"⚠️ 회귀 모델 학습 실패 ({len(_train_failures)}/{len(market_dfs)}): " + " | ".join(_train_failures[:5]))
        model.load_models()

        with storage.pipeline_stage("train_surge"):
            _surge_failures = []
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
                        _surge_failures.append(f"{futures[f]}: {e}")
            if _surge_failures:
                _notify_telegram(f"⚠️ Surge 모델 학습 실패 ({len(_surge_failures)}/{len(market_dfs)}): " + " | ".join(_surge_failures[:5]))
        model.load_surge_models()

        # 7c. Compute lead-lag correlation matrix (which stocks follow which)
        with storage.pipeline_stage("train_lead_lag_vcp"):
            if not df_train.empty and len(df_train) > 1000:
                model.compute_lead_lag(df_train, indicator_df=indicator_train, symbol_to_market=symbol_market)

            # 7d. Train VCP ML surge models (4 markets, parallel inside)
            vcp_ml = VCPSurgePredictor(model_dir=str(model.model_dir))
             # 7e. Fit Isotonic Regression calibrators on training data for score alignment
        if not df_train.empty and 'Close' in df_train.columns:
            try:
                from src.ai.ensemble_scorer import EnsembleScoringEngine
                import joblib
                scorer_calib = EnsembleScoringEngine(config=cfg)
                logger.info("Fitting Isotonic Regression calibrators on training dataset...")
                df_calib_base = df_train.copy()
                if 'date' in df_calib_base.columns:
                    df_calib_base = df_calib_base.sort_values('date')
                df_calib_base['future_return_20d'] = df_calib_base.groupby('symbol')['Close'].transform(lambda x: x.shift(-20) / x - 1)
                valid_calib_df = df_calib_base.dropna(subset=['future_return_20d'])
                if len(valid_calib_df) > 200:
                    # Use chronological last 30% as out-of-sample holdout for calibrator fitting
                    holdout_size = int(len(valid_calib_df) * 0.3)
                    val_holdout = valid_calib_df.iloc[-holdout_size:]
                    _val_dict = {sym: grp for sym, grp in val_holdout.groupby('symbol')} if 'symbol' in val_holdout.columns else {}
                    if _val_dict:
                        reg_preds, surge_preds = model.predict_all(
                            _val_dict, indicator_train, symbol_market,
                            storage=storage, fundamentals_cache=train_fund_cache if 'train_fund_cache' in locals() else None)
                    else:
                        reg_preds, surge_preds = pd.DataFrame(), pd.DataFrame()
                    if not reg_preds.empty and not surge_preds.empty:
                        y_true = (val_holdout['future_return_20d'] >= 0.15).astype(float).values
                        calib_scores = {
                            'regression': reg_preds.get(20, pd.Series(0.5, index=val_holdout.index)).values,
                            'surge': surge_preds.get('surge_20d', pd.Series(0.5, index=val_holdout.index)).values,
                        }
                        scorer_calib.fit_calibrators(calib_scores, y_true)
                        calib_path = Path(model.model_dir) / "calibrators.pkl"
                        joblib.dump(scorer_calib._calibrators, str(calib_path))
                        logger.info(f"Fitted and saved Isotonic calibrators on out-of-sample holdout ({len(val_holdout)} rows) to {calib_path}")
            except Exception as _calib_e:
                logger.warning(f"Isotonic calibration fitting skipped: {_calib_e}")

    # 8. Fetch fundamentals for all inference symbols (non-blocking background)
    target_env = os.environ.get("INFERENCE_TARGET", "SP500,NASDAQ,RUSSELL2000,KRX").strip().upper()
    targets = [t.strip() for t in target_env.split(",") if t.strip()]

    selected_symbols = []
    if "SP500" in targets:
        selected_symbols.extend(sp500_symbols)
    if "NASDAQ" in targets:
        selected_symbols.extend(nasdaq_symbols)
    if "RUSSELL2000" in targets or "RUSSELL" in targets:
        selected_symbols.extend(russell_symbols)
    if "KRX" in targets:
        selected_symbols.extend(krx_symbols)
    elif any(k in targets for k in ["KOSPI", "KOSDAQ"]):
        if "KOSPI" in targets:
            selected_symbols.extend(kospi_symbols)
        if "KOSDAQ" in targets:
            selected_symbols.extend(kosdaq_symbols)

    all_symbols = selected_symbols if selected_symbols else (sp500_symbols + nasdaq_symbols + russell_symbols + krx_symbols)

    # Exclude halted (거래정지) and administrative (관리종목) KRX stocks from all predictions
    excluded_krx = _get_excluded_krx_symbols()
    if excluded_krx:
        before = len(all_symbols)
        all_symbols = [s for s in all_symbols if s not in excluded_krx]
        logger.info(f"Excluded {before - len(all_symbols)} halted/admin KRX stocks from inference")

    if cfg.debug_mode:
        debug_symbols = []
        for m_syms in [sp500_symbols, nasdaq_symbols, russell_symbols, kospi_symbols, kosdaq_symbols]:
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
        if df is None or len(df) < 50:
            return None
        try:
            result = detect_vcp(df)
            if result is not None:
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
                    if _signal is not None:
                        _vcp_breakout_signals.append(_signal)
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
    try:
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
        result_dir = os.environ.get("OUTPUT_RESULT_DIR", os.path.join(os.path.dirname(__file__), "result"))
        os.makedirs(result_dir, exist_ok=True)

        if not stat_arb_pairs:
            # Continuous fallback: calculate 20-day MA Z-score deviation for all symbols
            for sym, df_p in infer_data_dict.items():
                if df_p is not None and len(df_p) >= 20:
                    try:
                        c = df_p['Close']
                        if isinstance(c, pd.DataFrame): c = c.iloc[:, 0]
                        c = c.dropna()
                        if len(c) >= 20:
                            ma20 = float(c.rolling(20).mean().iloc[-1])
                            std20 = float(c.rolling(20).std().iloc[-1])
                            if std20 > 0:
                                z = (float(c.iloc[-1]) - ma20) / std20
                                mkt = symbol_market.get(sym, 'KOSPI')
                                stat_arb_pairs.append({
                                    'pair': (sym, 'BENCHMARK'),
                                    'z_score': round(float(z), 2),
                                    'correlation': 0.85,
                                    'beta': 1.0,
                                    'signal': 'LONG_SPREAD' if z < -1.0 else ('SHORT_SPREAD' if z > 1.0 else 'NEUTRAL'),
                                    'market': mkt
                                })
                    except Exception:
                        pass

        valid_stat_arb_pairs = list(stat_arb_pairs)
        valid_stat_arb_pairs.sort(key=lambda x: abs(x.get('z_score', 0.0)), reverse=True)
        top_stat_arb_pairs = valid_stat_arb_pairs[:200]

        def _write_stat_arb_file(f_out, pairs_list):
            f_out.write("=== Statistical Arbitrage Pairs & Signals ===\n")
            f_out.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f_out.write(f"Total cointegrated pairs found: {len(pairs_list)}\n\n")
            f_out.write(f"{'Pair':<25}{'Z-Score':<10}{'Correlation':<15}{'Beta/Hedge':<12}{'Signal':<20}\n")
            f_out.write("-" * 80 + "\n")
            for p in pairs_list[:100]:
                pair_str = f"{p['pair'][0]}-{p['pair'][1]}"
                beta_val = p.get('beta', p.get('hedge_ratio', 1.0))
                z_val = p.get('z_score', 0.0)
                corr_val = p.get('correlation', p.get('adf_pvalue', 0.0))
                sig_val = p.get('signal', 'NEUTRAL')
                f_out.write(f"{pair_str:<25}{z_val:<10}{corr_val:<15}{beta_val:<12}{sig_val:<20}\n")

        stat_arb_output_path = os.path.join(result_dir, "stat_arb_predictions.txt")
        with open(stat_arb_output_path, "w", encoding="utf-8") as f:
            _write_stat_arb_file(f, top_stat_arb_pairs)

        # Per-market suffix files
        for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
            _m_pairs = [p for p in top_stat_arb_pairs if p.get('market') == _m or p['pair'][0] in set(universe[universe['market'] == _m]['symbol'])]
            if not _m_pairs:
                _m_pairs = top_stat_arb_pairs[:20]
            _mkt_path = os.path.join(result_dir, f"stat_arb_predictions_{_m}.txt")
            with open(_mkt_path, "w", encoding="utf-8") as _mf:
                _write_stat_arb_file(_mf, _m_pairs)
        logger.info(f"Saved Statistical Arbitrage pairs (Total: {len(stat_arb_pairs)}, Top 200 written) to {stat_arb_output_path}")
    except Exception as _stat_arb_e:
        logger.warning(f"Statistical Arbitrage calculation error: {_stat_arb_e}")


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
    _TOP_N = 100

    def _fmt_pct(row, h) -> str:
        try:
            v = float(row[h])
            if not np.isfinite(v):
                return "n/a"
            return f"{v*100:+.2f}%"
        except Exception:
            return "n/a"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== Pipeline Inference Summary (TOP100 per Market) ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total symbols analyzed: {len(res_df)}\n")
        f.write(f"Showing: Top {_TOP_N} per market | Horizons: {', '.join(str(h)+'d' for h in _SUMMARY_HORIZONS)}\n")
        f.write("Full data: pipeline_result.csv / pipeline_result.jsonl\n\n")
        if res_df.empty:
            f.write("데이터 없음\n")
        krx_markets = ['KOSPI', 'KOSDAQ']
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
                    f.write(f"  {rank}. {row['symbol']} ({name}): {_fmt_pct(row, h)}\n")
                f.write("\n")
            us_markets = ['SP500', 'NASDAQ', 'RUSSELL2000']
            for m in us_markets:
                m_set = market_syms.get(m, set())
                m_df = sorted_df[sorted_df['symbol'].isin(m_set)].head(_TOP_N)
                if not m_df.empty:
                    f.write(f"--- {m} TOP {_TOP_N} ---\n")
                    for rank, (_, row) in enumerate(m_df.iterrows(), 1):
                        name = symbol_to_name.get(row['symbol'], "Unknown")
                        f.write(f"  {rank}. {row['symbol']} ({name}): {_fmt_pct(row, h)}\n")
                    f.write("\n")
    logger.info(f"Saved summarized pipeline result (TOP{_TOP_N}, {len(_SUMMARY_HORIZONS)} horizons) to {output_path}")

    # Per-market suffix files for pipeline_result (Strategy 1 / Regression)
    for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
        _m_set = market_syms.get(_m, set())
        _m_path = os.path.join(result_dir, f"pipeline_result_{_m}.txt")
        _m_sorted = res_df[res_df['symbol'].isin(_m_set)].sort_values(by=20 if 20 in res_df.columns else res_df.columns[-1], ascending=False)
        if _m_sorted.empty:
            # Still write a minimal file so merge_predictions can detect the market
            with open(_m_path, "w", encoding="utf-8") as _mf:
                _mf.write(f"=== Pipeline Inference Summary ({_m}) ===\n")
                _mf.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                _mf.write("데이터 없음\n")
            continue
        with open(_m_path, "w", encoding="utf-8") as _mf:
            _mf.write(f"=== Pipeline Inference Summary ({_m}) ===\n")
            _mf.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            _mf.write(f"Total symbols analyzed: {len(_m_sorted)}\n\n")
            for h in _SUMMARY_HORIZONS:
                _m_h_sorted = _m_sorted.sort_values(by=h, ascending=False)
                _mf.write(f"--- {_m} TOP {min(_TOP_N, len(_m_h_sorted))} (Horizon: {h}d) ---\n")
                for _rank, (_, _row) in enumerate(_m_h_sorted.head(_TOP_N).iterrows(), 1):
                    _name = symbol_to_name.get(_row['symbol'], "Unknown")
                    _mf.write(f"  {_rank}. {_row['symbol']} ({_name}): {_fmt_pct(_row, h)}\n")
                _mf.write("\n")

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

            krx_markets = ['KOSPI', 'KOSDAQ']
            for h in model.surge_horizons:
                col = f'surge_{h}d'
                if col not in surge_df.columns:
                    continue
                for m in krx_markets + ['SP500', 'NASDAQ', 'RUSSELL2000']:
                    m_df = surge_df[surge_df['market'] == m].sort_values(by=col, ascending=False)
                    if m_df.empty:
                        continue
                    f.write(f"{'='*60}\n")
                    f.write(f"[{h}일] {m} Top 100 Surge Candidates\n")
                    f.write(f"{'='*60}\n")
                    for rank, (_, row) in enumerate(m_df.head(100).iterrows(), 1):
                        name = row.get('name', 'Unknown')
                        prob = row[col] * 100
                        f.write(f"  {rank}. [{m}] {row['symbol']} ({name}): {prob:.1f}%\n")
                    f.write("\n")
    logger.info(f"Saved surge predictions ({len(surge_df)} symbols) to {surge_output_path}")

    # Also save per-market suffix files for surge predictions
    if not surge_df.empty:
        for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
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
                    _mf.write(f"[{h}일] {_m} Top 100 Surge Candidates\n")
                    _mf.write(f"{'='*60}\n")
                    for rank, (_, row) in enumerate(m_sorted.head(100).iterrows(), 1):
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
            krx_markets = ['KOSPI', 'KOSDAQ']
            for m in krx_markets + ['SP500', 'NASDAQ', 'RUSSELL2000']:
                m_df = lead_lag_df[lead_lag_df['market'] == m].sort_values(by='lead_lag_score', ascending=False)
                if m_df.empty:
                    continue
                f.write(f"--- {m} Top 100 ---\n")
                for rank, (_, row) in enumerate(m_df.head(100).iterrows(), 1):
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
        for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
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
                _mf.write(f"--- {_m} Top 100 ---\n")
                for _rank, (_, _row) in enumerate(_m_df.head(100).iterrows(), 1):
                    _name = _row.get('name', 'Unknown')
                    _score = float(_row['lead_lag_score']) * 100
                    _mf.write(f"  {_rank}. [{_m}] {_row['symbol']} ({_name}): {_score:.2f}%\n")
                _mf.write("\n")
            logger.info(f"Saved lead-lag predictions for {_m} to {_mkt_path}")

    # Intermediate Garbage Collection after Step 10 ML Inferencing to release memory heap
    gc.collect()

    # Save VCP pattern detection results
    vcp_output_path = os.path.join(result_dir, "vcp_patterns.txt")
    vcp_universe_map = {s: (n, m) for s, n, m in zip(universe['symbol'],
                        universe['name'], universe['market'])}
    krx_markets = ['KOSPI', 'KOSDAQ']
    def _write_vcp_file(f_out, res_list, target_mkt=None):
        f_out.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
        f_out.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f_out.write(f"Total symbols evaluated: {len(res_list)}\n\n")

        mkts = [target_mkt] if target_mkt else (krx_markets + ['SP500', 'NASDAQ', 'RUSSELL2000'])
        for m in mkts:
            m_results = [r for r in res_list if vcp_universe_map.get(r['symbol'], ('', ''))[1] == m]
            if not m_results:
                continue
            f_out.write(f"--- {m} Top {min(100, len(m_results))} ---\n")
            for rank, r in enumerate(m_results[:100], 1):
                sym = r['symbol']
                name, _market = vcp_universe_map.get(sym, ('Unknown', ''))
                peaks = ' > '.join(f'{p:.1f}%' for p in r['contraction_peaks']) if 'contraction_peaks' in r and r['contraction_peaks'] else 'N/A'
                f_out.write(f"  {rank}. [{m}] {sym} ({name})\n")
                f_out.write(f"       Score: {r['vcp_score']:.0f}/100 | "
                        f"Current range: {r.get('current_range_pct', 0.0):.1f}% | "
                        f"Contraction: {peaks}\n")
                f_out.write(f"       Above MA50: {'✓' if r.get('above_sma50') else '✗'} | "
                        f"Above MA200: {'✓' if r.get('above_sma200') else '✗'} | "
                        f"Near high: {'✓' if r.get('near_high') else '✗'} | "
                        f"Volume declining: {'✓' if r.get('volume_declining') else '✗'}\n\n")

    with open(vcp_output_path, "w", encoding="utf-8") as f:
        _write_vcp_file(f, vcp_results)

    # Per-market suffix files
    for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
        _m_path = os.path.join(result_dir, f"vcp_patterns_{_m}.txt")
        _m_res = [r for r in vcp_results if vcp_universe_map.get(r['symbol'], ('', ''))[1] == _m]
        if _m_res:
            with open(_m_path, "w", encoding="utf-8") as _mf:
                _write_vcp_file(_mf, vcp_results, target_mkt=_m)
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
            for market in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                if not vcp_ml_df.empty and 'market' in vcp_ml_df.columns and f'vcp_{h}d' in vcp_ml_df.columns:
                    m_df = vcp_ml_df[vcp_ml_df['market'] == market].sort_values(by=f'vcp_{h}d', ascending=False)
                else:
                    m_df = pd.DataFrame()

                if m_df.empty:
                    f.write(f"[{h}일] {market} - (no symbols) 0.0%\n\n")
                    continue
                top_n = min(100, len(m_df))
                f.write(f"[{h}일] {market} TOP {top_n}\n")
                for rank, (_, row) in enumerate(m_df.head(top_n).iterrows(), 1):
                    name = row.get('name', 'Unknown')
                    prob = row[f'vcp_{h}d'] * 100
                    f.write(f"  {rank}. [{market}] {row['symbol']} ({name}): {prob:.1f}%\n")
                f.write("\n")
    logger.info(f"Saved VCP ML predictions to {vcp_ml_output_path}")

    # Per-market suffix files for VCP ML (Strategy 5)
    for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
        _m_path = os.path.join(result_dir, f"vcp_ml_predictions_{_m}.txt")
        if vcp_ml_df.empty:
            with open(_m_path, "w", encoding="utf-8") as _mf:
                _mf.write(f"=== VCP ML Surge Predictions ({_m}) ===\n")
                _mf.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                _mf.write("데이터 없음\n")
            continue
        with open(_m_path, "w", encoding="utf-8") as _mf:
            _mf.write(f"=== VCP ML Surge Predictions ({_m}) ===\n")
            _mf.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            for h in SURGE_HORIZONS:
                m_df = vcp_ml_df[vcp_ml_df['market'] == _m].sort_values(by=f'vcp_{h}d', ascending=False) if 'market' in vcp_ml_df.columns and f'vcp_{h}d' in vcp_ml_df.columns else pd.DataFrame()
                if m_df.empty:
                    _mf.write(f"[{h}일] {_m} - (no symbols) 0.0%\n\n")
                    continue
                top_n = min(100, len(m_df))
                _mf.write(f"[{h}일] {_m} TOP {top_n}\n")
                for _rank, (_, _row) in enumerate(m_df.head(top_n).iterrows(), 1):
                    _name = _row.get('name', 'Unknown')
                    _prob = _row[f'vcp_{h}d'] * 100
                    _mf.write(f"  {_rank}. [{_m}] {_row['symbol']} ({_name}): {_prob:.1f}%\n")
                _mf.write("\n")

    # 11d. Run Ensemble Scoring
    logger.info("Running Dynamic Multi-Strategy Ensemble scoring...")
    scorer = EnsembleScoringEngine(config=cfg)

    # ── Milestone 4: Closed-Loop Realized Slippage Execution Feedback ─────────
    try:
        from src.execution.slippage_feedback import SlippageFeedbackEngine
        db_path_trade = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_logs.db")
        slippage_engine = SlippageFeedbackEngine(db_path=db_path_trade, default_slippage_bps=5.0)
        slippage_metrics = slippage_engine.calculate_realized_slippage()
        scorer.update_microstructure_costs(slippage_metrics)
    except Exception as _m4_e:
        logger.warning(f"[MILESTONE 4] Slippage feedback integration skipped: {_m4_e}")
        slippage_metrics = None

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
            if row.get('market', '') in ('KOSPI', 'KOSDAQ')
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
        try:
            from src.core.stat_arb import StatisticalArbitrageEngine
            stat_arb_df = StatisticalArbitrageEngine.get_symbol_stat_arb_scores(stat_arb_pairs)
        except Exception as _sa_e:
            logger.warning(f"Stat-Arb symbol score conversion error: {_sa_e}")
            stat_arb_df = pd.DataFrame()

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
            # Fix: use pipe_sector_map (dict) truthiness, not 'sector' in dict
            if pipe_sector_map:
                sector_df_merged['sector'] = sector_df_merged['symbol'].map(lambda s: pipe_sector_map.get(s, 'General'))
            elif 'sector' in universe.columns:
                sec_sub = universe[['symbol', 'sector']]
                sector_df_merged = sector_df_merged.merge(sec_sub, on='symbol', how='left')
            else:
                sector_df_merged['sector'] = 'General'

            sector_df_merged = sector_df_merged.sort_values(by='sector_score', ascending=False)

            def _write_sector_file(f_out, df_sect):
                f_out.write("=== Sector Rotation Momentum & Macro Sensitivity Report ===\n")
                f_out.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f_out.write(f"Total symbols evaluated: {len(df_sect)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Market':<10}{'Sector':<25}{'Sector Score':<15}\n")
                f_out.write("-" * 85 + "\n")
                for rank, (_, row) in enumerate(df_sect.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:18] if pd.notna(row['name']) else "Unknown"
                    sec_str = str(row.get('sector', 'General'))[:23]
                    mkt_str = str(row.get('market', 'KRX'))
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<20}{mkt_str:<10}{sec_str:<25}{row['sector_score']*100:>13.1f}%\n")

            with open(sector_output_path, "w", encoding="utf-8") as f:
                _write_sector_file(f, sector_df_merged)
            logger.info(f"Saved sector rotation predictions ({len(sector_df_merged)} symbols) to {sector_output_path}")

            # Per-market suffix files for GHA artifact merge
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = sector_df_merged[sector_df_merged['market'] == _m]
                if _m_df.empty:
                    continue
                _mkt_path = os.path.join(result_dir, f"sector_predictions_{_m}.txt")
                with open(_mkt_path, "w", encoding="utf-8") as _mf:
                    _write_sector_file(_mf, _m_df)
                logger.info(f"Saved sector predictions for {_m} to {_mkt_path}")
    except Exception as _sec_e:
        logger.warning(f"Sector rotation score calculation skipped: {_sec_e}")
        sector_df = pd.DataFrame()

    # 10f. Strategy 9: RIM (Residual Income Model) Valuation Engine
    try:
        from src.core.rim_valuation import RIMValuationEngine
        logger.info("Computing Strategy 9: RIM Intrinsic Valuation & Margin of Safety Scores...")
        rim_engine = RIMValuationEngine(default_required_return=0.08, decay_rate=0.10, retention_ratio=0.6)
        rim_input_rows = []
        for sym, df_p in infer_data_dict.items():
            if df_p is not None and not df_p.empty:
                latest = df_p.iloc[-1].to_dict()
                latest['symbol'] = sym
                latest['market'] = symbol_market.get(sym, 'KOSPI')
                rim_input_rows.append(latest)
        df_rim_input = pd.DataFrame(rim_input_rows) if rim_input_rows else pd.DataFrame()
        # Merge fundamental data (BPS, ROE) into RIM input to avoid artificial -20% discount
        if not df_rim_input.empty:
            try:
                fund_df = storage.get_all_fundamentals(df_rim_input['symbol'].tolist())
                if fund_df is not None and not fund_df.empty:
                    fund_df = fund_df.sort_values('date').groupby('symbol').last().reset_index()
                    # Compute BPS = book_value / shares_outstanding; 0 book_value → None (not merged)
                    fund_df['bps'] = (fund_df['book_value'] / fund_df['shares_outstanding']).replace([float('inf'), float('-inf'), 0], None)
                    # Compute ROE = net_income / book_value; 0 book_value → None
                    fund_df['roe'] = (fund_df['net_income'] / fund_df['book_value']).replace([float('inf'), float('-inf')], None)
                    # Fallback BPS from eps when book_value unavailable
                    no_bps = fund_df['bps'].isna() & fund_df['eps'].notna()
                    fund_df.loc[no_bps, 'bps'] = fund_df.loc[no_bps, 'eps'] / 0.08
                    # Merge into rim_input
                    merge_cols = ['symbol', 'bps', 'roe']
                    df_rim_input = df_rim_input.merge(fund_df[merge_cols], on='symbol', how='left')
                    logger.info(f"Merged fundamental BPS/ROE for RIM: {fund_df['bps'].notna().sum()}/{len(df_rim_input)} symbols have BPS")
            except Exception as _fund_e:
                logger.warning(f"Fundamental data merge for RIM skipped: {_fund_e}")
        rim_df = rim_engine.compute_rim_scores(df_rim_input, symbol_market_map=symbol_market)
        rim_output_path = os.path.join(result_dir, "rim_predictions.txt")
        if not rim_df.empty:
            rim_merged = rim_df.merge(universe[['symbol', 'name']], on='symbol', how='left')
            rim_merged = rim_merged.sort_values(by='rim_score', ascending=False)

            def _write_rim_file(f_out, df_rim):
                f_out.write("=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===\n")
                f_out.write(f"Date: {date_str}\n")
                f_out.write(f"Total symbols evaluated: {len(df_rim)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Market':<10}{'Price':<12}{'Intrinsic V0':<14}{'Discount %':<12}{'RIM Score':<12}\n")
                f_out.write("-" * 95 + "\n")
                for rank, (_, row) in enumerate(df_rim.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:18] if pd.notna(row['name']) else "Unknown"
                    disc_pct = row.get('discount_ratio', 0.0) * 100.0
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<20}{row['market']:<10}{row['Close']:<12.2f}{row['intrinsic_value']:<14.2f}{disc_pct:>10.1f}%{row['rim_score']*100:>10.1f}%\n")

            with open(rim_output_path, "w", encoding="utf-8") as f:
                _write_rim_file(f, rim_merged)
            logger.info(f"Saved RIM valuation predictions ({len(rim_merged)} symbols) to {rim_output_path}")

            # Per-market suffix files
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = rim_merged[rim_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"rim_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_rim_file(_mf, _m_df)
    except Exception as _rim_e:
        logger.warning(f"RIM valuation score calculation skipped: {_rim_e}")
        rim_df = pd.DataFrame()

    # Define KST timestamp for all strategy write functions (must be before strategies 10-14)
    from datetime import timezone, timedelta
    KST = timezone(timedelta(hours=9))
    kst_now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')

    # 10g. Strategy 10: Event-Driven Momentum Engine
    m5_sentiment_metrics_list = []
    try:
        from src.core.event_driven import EventDrivenEngine
        from src.core.llm_sentiment_engine import LLMSentimentEngine
        logger.info("Computing Strategy 10: Event-Driven Momentum Scores with LLM/NLP Filing Sentiment...")
        event_engine = EventDrivenEngine(dart_api_key=getattr(cfg, 'dart_api_key', ''))
        sentiment_engine = LLMSentimentEngine(db_storage=storage)
        eff_filings = event_engine.fetch_recent_dart_filings()
        sentiment_map = {}
        if eff_filings:
            sentiment_map = sentiment_engine.batch_analyze_filings(eff_filings)
            m5_sentiment_metrics_list = list(sentiment_map.values())
        event_df = event_engine.compute_event_scores(
            symbols=list(infer_data_dict.keys()),
            prices_dict=infer_data_dict,
            filings=eff_filings,
            sentiment_map=sentiment_map
        )
        logger.info(f"Event-driven scores computed: {len(event_df)} symbols, empty={event_df.empty}")
        event_output_path = os.path.join(result_dir, "event_driven_predictions.txt")
        if not event_df.empty:
            ev_merged = event_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='event_score', ascending=False)

            def _write_event_file(f_out, df_ev):
                f_out.write("=== Strategy 10: Event-Driven Disclosure Catalyst Predictions ===\n")
                f_out.write(f"Date: {kst_now_str}\n")
                f_out.write(f"Total symbols evaluated: {len(df_ev)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'Event Score':<14}\n")
                f_out.write("-" * 60 + "\n")
                for rank, (_, row) in enumerate(df_ev.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['event_score']*100:>12.1f}%\n")

            with open(event_output_path, "w", encoding="utf-8") as f:
                _write_event_file(f, ev_merged)
            logger.info(f"Saved event-driven predictions ({len(ev_merged)} symbols) to {event_output_path}")

            # Per-market suffix files
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = ev_merged[ev_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"event_driven_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_event_file(_mf, _m_df)
    except Exception as _ev_e:
        logger.warning(f"Event-driven score calculation skipped: {_ev_e}")
        event_df = pd.DataFrame()

    # 10h. Strategy 11: MQ Factor Engine
    try:
        from src.core.mq_factor import MQFactorEngine
        logger.info("Computing Strategy 11: Momentum Quality (MQ) Factor Scores...")
        mq_engine = MQFactorEngine()
        mq_df = mq_engine.compute_mq_scores(prices_dict=infer_data_dict, features_df=df_rim_input if 'df_rim_input' in locals() else None)
        logger.info(f"MQ factor scores computed: {len(mq_df)} symbols, empty={mq_df.empty}")
        mq_output_path = os.path.join(result_dir, "mq_factor_predictions.txt")
        if not mq_df.empty:
            mq_merged = mq_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='mq_score', ascending=False)

            def _write_mq_file(f_out, df_mq):
                f_out.write("=== Strategy 11: Momentum Quality (MQ) Factor Predictions ===\n")
                f_out.write(f"Date: {kst_now_str}\n")
                f_out.write(f"Total symbols evaluated: {len(df_mq)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'MQ Score':<14}\n")
                f_out.write("-" * 60 + "\n")
                for rank, (_, row) in enumerate(df_mq.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['mq_score']*100:>12.1f}%\n")

            with open(mq_output_path, "w", encoding="utf-8") as f:
                _write_mq_file(f, mq_merged)
            logger.info(f"Saved MQ factor predictions ({len(mq_merged)} symbols) to {mq_output_path}")

            # Per-market suffix files
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = mq_merged[mq_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"mq_factor_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_mq_file(_mf, _m_df)
    except Exception as _mq_e:
        logger.warning(f"MQ factor score calculation skipped: {_mq_e}")
        mq_df = pd.DataFrame()

    # 10i. Strategy 12: Options IV Skew Engine
    try:
        from src.core.iv_skew import IVSkewEngine
        logger.info("Computing Strategy 12: Options IV Skew Scores...")
        iv_skew_engine = IVSkewEngine()
        iv_skew_df = iv_skew_engine.compute_iv_skew_scores(symbols=list(infer_data_dict.keys()), prices_dict=infer_data_dict)
        logger.info(f"IV skew scores computed: {len(iv_skew_df)} symbols, empty={iv_skew_df.empty}")
        iv_output_path = os.path.join(result_dir, "iv_skew_predictions.txt")
        if not iv_skew_df.empty:
            iv_merged = iv_skew_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='iv_skew_score', ascending=False)

            def _write_iv_file(f_out, df_iv):
                f_out.write("=== Strategy 12: Options Put/Call IV Skew Predictions ===\n")
                f_out.write(f"Date: {kst_now_str}\n")
                f_out.write(f"Total symbols evaluated: {len(df_iv)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'IV Skew Score':<14}\n")
                f_out.write("-" * 60 + "\n")
                for rank, (_, row) in enumerate(df_iv.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['iv_skew_score']*100:>12.1f}%\n")

            with open(iv_output_path, "w", encoding="utf-8") as f:
                _write_iv_file(f, iv_merged)
            logger.info(f"Saved IV skew predictions ({len(iv_merged)} symbols) to {iv_output_path}")

            # Per-market suffix files
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = iv_merged[iv_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"iv_skew_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_iv_file(_mf, _m_df)
    except Exception as _iv_e:
        logger.warning(f"IV skew score calculation skipped: {_iv_e}")
        iv_skew_df = pd.DataFrame()

    # 10j. Strategy 13: Order Flow Imbalance Engine
    try:
        from src.core.order_flow import OrderFlowEngine
        logger.info("Computing Strategy 13: Order Flow Imbalance Scores...")
        of_engine = OrderFlowEngine()
        order_flow_df = of_engine.compute_order_flow_scores(prices_dict=infer_data_dict)
        logger.info(f"Order flow scores computed: {len(order_flow_df)} symbols, empty={order_flow_df.empty}")
        of_output_path = os.path.join(result_dir, "order_flow_predictions.txt")
        if not order_flow_df.empty:
            of_merged = order_flow_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='order_flow_score', ascending=False)

            def _write_of_file(f_out, df_of):
                f_out.write("=== Strategy 13: Order Flow Imbalance (MFI) Predictions ===\n")
                f_out.write(f"Date: {kst_now_str}\n")
                f_out.write(f"Total symbols evaluated: {len(df_of)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'Order Flow Score':<16}\n")
                f_out.write("-" * 62 + "\n")
                for rank, (_, row) in enumerate(df_of.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['order_flow_score']*100:>14.1f}%\n")

            with open(of_output_path, "w", encoding="utf-8") as f:
                _write_of_file(f, of_merged)
            logger.info(f"Saved order flow predictions ({len(of_merged)} symbols) to {of_output_path}")

            # Per-market suffix files
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = of_merged[of_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"order_flow_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_of_file(_mf, _m_df)
    except Exception as _of_e:
        logger.warning(f"Order flow score calculation skipped: {_of_e}")
        order_flow_df = pd.DataFrame()

    # 10k. Strategy 14: Short-Term Reversal Engine
    try:
        from src.core.short_term_reversal import ShortTermReversalEngine
        logger.info("Computing Strategy 14: Short-Term Reversal Scores...")
        reversal_engine = ShortTermReversalEngine()
        reversal_df = reversal_engine.compute_reversal_scores(prices_dict=infer_data_dict, features_df=df_rim_input if 'df_rim_input' in locals() else None)
        logger.info(f"Short-term reversal scores computed: {len(reversal_df)} symbols, empty={reversal_df.empty}")
        rev_output_path = os.path.join(result_dir, "short_term_reversal_predictions.txt")
        if not reversal_df.empty:
            rev_merged = reversal_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='reversal_score', ascending=False)

            def _write_rev_file(f_out, df_rev):
                f_out.write("=== Strategy 14: Short-Term Mean Reversal Predictions ===\n")
                f_out.write(f"Date: {kst_now_str}\n")
                f_out.write(f"Total symbols evaluated: {len(df_rev)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'Reversal Score':<16}\n")
                f_out.write("-" * 62 + "\n")
                for rank, (_, row) in enumerate(df_rev.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['reversal_score']*100:>14.1f}%\n")

            with open(rev_output_path, "w", encoding="utf-8") as f:
                _write_rev_file(f, rev_merged)
            logger.info(f"Saved short-term reversal predictions ({len(rev_merged)} symbols) to {rev_output_path}")

            # Per-market suffix files
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = rev_merged[rev_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"short_term_reversal_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_rev_file(_mf, _m_df)
    except Exception as _rev_e:
        logger.warning(f"Short-term reversal score calculation skipped: {_rev_e}")
        reversal_df = pd.DataFrame()

    # Backfill realized outcomes for previously stored ensemble predictions so that
    # rolling Sharpe weighting & calibrator fitting operate on real realized returns.
    try:
        _outcome_updated = storage.update_ensemble_outcomes(
            prices_getter=price_db.get_prices, horizon=20, days=90
        )
        if _outcome_updated > 0:
            logger.info(f"[OUTCOME] Backfilled realized returns for {_outcome_updated} ensemble predictions.")
    except Exception as _oc_e:
        logger.warning(f"[OUTCOME] Outcome backfill skipped: {_oc_e}")

    # Calculate rolling Sharpes for all strategies if strategy_returns exists
    strategy_returns = {}
    try:
        hist_df = storage.get_ensemble_predictions_history(days=60)
        if hist_df is not None and not hist_df.empty:
            for strat, col in [
                ('regression', 'reg_score'), ('surge', 'surge_score'), ('lead_lag', 'll_score'),
                ('vcp_rule', 'vcp_rule_score'), ('vcp_ml', 'vcp_ml_score'), ('stat_arb', 'stat_arb_score'),
                ('sector_rotation', 'sector_score'), ('rim_valuation', 'rim_score'), ('event_driven', 'event_score'),
                ('mq_factor', 'mq_score'), ('iv_skew', 'iv_skew_score'), ('order_flow', 'order_flow_score'),
                ('short_term_reversal', 'reversal_score'),
                ('arm_factor', 'arm_score'),
                ('card_factor', 'card_score'),
                ('latr_factor', 'latr_score')
            ]:
                if col in hist_df.columns and 'outcome_return' in hist_df.columns:
                    strat_series = hist_df.groupby('date').apply(lambda d: (d[col] * d['outcome_return']).mean(), include_groups=False)
                    strategy_returns[strat] = strat_series
    except Exception as _sr_e:
        logger.debug(f"Strategy returns computation for Sharpe weighting: {_sr_e}")

    rolling_sharpes = scorer.compute_rolling_sharpe(strategy_returns) if strategy_returns else None

    # Force Garbage Collection before heavy Ensemble Scoring
    gc.collect()

    # Strategy 15: Analyst Revision Momentum (ARM) Factor
    try:
        from src.core.arm_factor import ARMFactorEngine
        arm_engine = ARMFactorEngine()
        _arm_fund = {}
        if 'infer_fund_cache' in locals() and infer_fund_cache:
            for _sym, _fd in infer_fund_cache.items():
                if _fd is None or len(_fd) == 0:
                    continue
                _fd_sorted = _fd.sort_values('date') if 'date' in _fd.columns else _fd
                _last = _fd_sorted.iloc[-1]
                _eps_g = 0.0
                _rev_g = 0.0
                if len(_fd_sorted) >= 2:
                    _prev = _fd_sorted.iloc[-2]
                    _pe = float(_prev.get('eps') or 0.0)
                    _pr = float(_prev.get('revenue') or 0.0)
                    if _pe != 0:
                        _eps_g = float((float(_last.get('eps') or 0.0) - _pe) / abs(_pe))
                    if _pr != 0:
                        _rev_g = float((float(_last.get('revenue') or 0.0) - _pr) / abs(_pr))
                elif isinstance(_last, pd.Series):
                    _eps_g = float(_last.get('eps_growth_1y') or 0.0)
                    _rev_g = float(_last.get('revenue_growth_1y') or 0.0)
                _arm_fund[_sym] = {
                    'eps_revision_pct': None,
                    'tp_revision_pct': None,
                    'eps_growth': _eps_g,
                    'revenue_growth': _rev_g,
                    'per': None,
                }
        arm_scores = arm_engine.compute_scores(_arm_fund, infer_data_dict)
        arm_df = pd.DataFrame([{'symbol': k, 'arm_score': v} for k, v in arm_scores.items()])
        arm_output_path = os.path.join(result_dir, "arm_factor_predictions.txt")
        if not arm_df.empty:
            arm_merged = arm_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='arm_score', ascending=False)
            with open(arm_output_path, "w", encoding="utf-8") as f:
                f.write("=== Strategy 15: Analyst Revision Momentum (ARM) Factor Predictions ===\n")
                f.write(f"Date: {kst_now_str}\n")
                f.write(f"Total symbols evaluated: {len(arm_merged)}\n\n")
                f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'ARM Score':<12}\n")
                f.write("-" * 58 + "\n")
                for rank, (_, row) in enumerate(arm_merged.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['arm_score']*100:>10.1f}%\n")
            logger.info(f"Saved ARM factor predictions ({len(arm_merged)} symbols) to {arm_output_path}")
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = arm_merged[arm_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"arm_factor_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _mf.write(f"=== ARM Factor Predictions ({_m}) ===\n")
                    _mf.write(f"Date: {kst_now_str}\n\n")
                    _mf.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'ARM Score':<12}\n")
                    _mf.write("-" * 48 + "\n")
                    for rank, (_, row) in enumerate(_m_df.head(100).iterrows(), 1):
                        name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                        _mf.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['arm_score']*100:>10.1f}%\n")
    except Exception as _arm_e:
        logger.warning(f"ARM factor computation failed: {_arm_e}")
        arm_df = pd.DataFrame()

    # Strategy 16: Cross-Asset Regime Divergence (CARD) Factor
    try:
        from src.core.card_factor import CARDFactorEngine
        card_engine = CARDFactorEngine()
        card_scores = card_engine.compute_scores(indicator_infer if 'indicator_infer' in locals() else pd.DataFrame(), infer_data_dict)
        card_df = pd.DataFrame([{'symbol': k, 'card_score': v} for k, v in card_scores.items()])
        card_output_path = os.path.join(result_dir, "card_factor_predictions.txt")
        if not card_df.empty:
            card_merged = card_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='card_score', ascending=False)
            with open(card_output_path, "w", encoding="utf-8") as f:
                f.write("=== Strategy 16: Cross-Asset Regime Divergence (CARD) Factor Predictions ===\n")
                f.write(f"Date: {kst_now_str}\n")
                f.write(f"Total symbols evaluated: {len(card_merged)}\n\n")
                f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'CARD Score':<14}\n")
                f.write("-" * 60 + "\n")
                for rank, (_, row) in enumerate(card_merged.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['card_score']*100:>12.1f}%\n")
            logger.info(f"Saved CARD factor predictions ({len(card_merged)} symbols) to {card_output_path}")
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = card_merged[card_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"card_factor_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _mf.write(f"=== CARD Factor Predictions ({_m}) ===\n")
                    _mf.write(f"Date: {kst_now_str}\n\n")
                    _mf.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'CARD Score':<14}\n")
                    _mf.write("-" * 50 + "\n")
                    for rank, (_, row) in enumerate(_m_df.head(100).iterrows(), 1):
                        name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                        _mf.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['card_score']*100:>12.1f}%\n")
    except Exception as _card_e:
        logger.warning(f"CARD factor computation failed: {_card_e}")
        card_df = pd.DataFrame()

    # Strategy 17: Liquidity-Adjusted Tail Risk (LATR) Factor
    try:
        from src.core.latr_factor import LATRFactorEngine
        latr_engine = LATRFactorEngine()
        latr_scores = latr_engine.compute_scores(infer_data_dict)
        latr_df = pd.DataFrame([{'symbol': k, 'latr_score': v} for k, v in latr_scores.items()])
        latr_output_path = os.path.join(result_dir, "latr_factor_predictions.txt")
        if not latr_df.empty:
            latr_merged = latr_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='latr_score', ascending=False)
            with open(latr_output_path, "w", encoding="utf-8") as f:
                f.write("=== Strategy 17: Liquidity-Adjusted Tail Risk (LATR) Factor Predictions ===\n")
                f.write(f"Date: {kst_now_str}\n")
                f.write(f"Total symbols evaluated: {len(latr_merged)}\n\n")
                f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'LATR Score':<14}\n")
                f.write("-" * 60 + "\n")
                for rank, (_, row) in enumerate(latr_merged.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['latr_score']*100:>12.1f}%\n")
            logger.info(f"Saved LATR factor predictions ({len(latr_merged)} symbols) to {latr_output_path}")
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = latr_merged[latr_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"latr_factor_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _mf.write(f"=== LATR Factor Predictions ({_m}) ===\n")
                    _mf.write(f"Date: {kst_now_str}\n\n")
                    _mf.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'LATR Score':<14}\n")
                    _mf.write("-" * 50 + "\n")
                    for rank, (_, row) in enumerate(_m_df.head(100).iterrows(), 1):
                        name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                        _mf.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['latr_score']*100:>12.1f}%\n")
    except Exception as _latr_e:
        logger.warning(f"LATR factor computation failed: {_latr_e}")
        latr_df = pd.DataFrame()

    # Strategy 18: Inst & Foreign 2-Month Accumulation & Sector Correlation (Lead-Lag Follow Through)
    try:
        from src.core.inst_foreign_sector import InstForeignSectorEngine
        ifs_engine = InstForeignSectorEngine(accumulation_days=40)
        sector_mapping = dict(zip(universe['symbol'], universe.get('sector', universe.get('industry', 'DEFAULT')))) if 'symbol' in universe.columns else {}
        inst_foreign_sector_df = ifs_engine.compute_scores(infer_data_dict, flow_data_dict=None, sector_mapping=sector_mapping)
        ifs_output_path = os.path.join(result_dir, "inst_foreign_sector_predictions.txt")
        if not inst_foreign_sector_df.empty:
            ifs_merged = inst_foreign_sector_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left').sort_values(by='inst_foreign_sector_score', ascending=False)
            with open(ifs_output_path, "w", encoding="utf-8") as f:
                f.write("=== Strategy 18: Inst & Foreign 2-Month Accumulation & Sector Correlation Predictions ===\n")
                f.write(f"Date: {kst_now_str}\n")
                f.write(f"Total symbols evaluated: {len(ifs_merged)}\n\n")
                f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'IFS Score':<14}\n")
                f.write("-" * 60 + "\n")
                for rank, (_, row) in enumerate(ifs_merged.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['inst_foreign_sector_score']*100:>12.1f}%\n")
            logger.info(f"Saved Inst & Foreign Sector predictions ({len(ifs_merged)} symbols) to {ifs_output_path}")
            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = ifs_merged[ifs_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"inst_foreign_sector_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _mf.write(f"=== Inst & Foreign Sector Predictions ({_m}) ===\n")
                    _mf.write(f"Date: {kst_now_str}\n\n")
                    _mf.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'IFS Score':<14}\n")
                    _mf.write("-" * 50 + "\n")
                    for rank, (_, row) in enumerate(_m_df.head(100).iterrows(), 1):
                        name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                        _mf.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['inst_foreign_sector_score']*100:>12.1f}%\n")
    except Exception as _ifs_e:
        logger.warning(f"Inst & Foreign sector strategy computation failed: {_ifs_e}")
        inst_foreign_sector_df = pd.DataFrame()

    # default target horizon is 20d (17-Strategy Ensemble)
    ensemble_df = scorer.calculate_ensemble_score(
        regime=current_2d_regime,
        regression_df=res_df,
        surge_df=surge_df,
        lead_lag_df=lead_lag_df,
        vcp_rule_df=vcp_results,
        vcp_ml_df=vcp_ml_df,
        stat_arb_df=stat_arb_df,
        sector_df=sector_df,
        rim_df=rim_df,
        event_df=event_df,
        mq_df=mq_df,
        iv_skew_df=iv_skew_df,
        order_flow_df=order_flow_df,
        reversal_df=reversal_df,
        arm_df=arm_df,
        card_df=card_df,
        latr_df=latr_df,
        inst_foreign_sector_df=inst_foreign_sector_df,
        rolling_sharpes=rolling_sharpes,
        target_horizon=20
    )

    # Persist today's ensemble predictions (all strategy scores) for future
    # rolling Sharpe weighting, calibrator fitting and coverage analysis.
    try:
        if ensemble_df is not None and not ensemble_df.empty and storage is not None:
            storage.save_ensemble_predictions(ensemble_df, date_str)
            logger.info(f"[ENSEMBLE DB] Saved {len(ensemble_df)} ensemble prediction rows for {date_str}.")
    except Exception as _ens_save_e:
        logger.warning(f"[ENSEMBLE DB] Save skipped: {_ens_save_e}")

    # 11f. Save Ensemble Predictions Report (ensemble_predictions.txt)
    # Gather decision basis metrics (kst_now_str and KST already defined above)

    def _safe_float(val, default: float) -> float:
        try:
            v = float(val)
            return default if (pd.isna(v) or np.isnan(v)) else v
        except Exception:
            return default

    def _safe_yield(val, default: float) -> float:
        """Like _safe_float but treats 0.0 as invalid (yields are never truly 0)."""
        try:
            v = float(val)
            if pd.isna(v) or np.isnan(v) or abs(v) < 0.001:
                return default
            return v
        except Exception:
            return default

    db_macro = storage.get_latest_global_indicators() if storage is not None else {}

    sp500_ret_20d = _safe_float(indicator_infer['sp500_change'].tail(20).mean(), 0.05) if 'sp500_change' in indicator_infer.columns else 0.05
    sp500_vol_20d = _safe_float(indicator_infer['sp500_change'].tail(20).std(), 1.0) if 'sp500_change' in indicator_infer.columns else 1.0
    kospi_ret_20d = _safe_float(indicator_infer['kospi_change'].tail(20).mean(), 0.05) if 'kospi_change' in indicator_infer.columns else 0.05
    kospi_vol_20d = _safe_float(indicator_infer['kospi_change'].tail(20).std(), 1.2) if 'kospi_change' in indicator_infer.columns else 1.2

    # 1. VIX Index level: check vix_raw, price_db ^VIX, db_macro ^VIX, default 18.5
    vix_val = np.nan
    if 'vix_raw' in indicator_infer.columns and not indicator_infer['vix_raw'].dropna().empty:
        vix_val = float(indicator_infer['vix_raw'].dropna().iloc[-1])
    if (pd.isna(vix_val) or vix_val <= 0 or vix_val > 150) and price_db is not None:
        try:
            _vix_df = price_db.get_prices('^VIX', start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
            if _vix_df is not None and not _vix_df.empty and 'Close' in _vix_df.columns:
                vix_val = float(_vix_df['Close'].dropna().iloc[-1])
        except Exception:
            pass
    if (pd.isna(vix_val) or vix_val <= 0 or vix_val > 150) and '^VIX' in db_macro:
        vix_val = float(db_macro['^VIX'])
    vix_val = _safe_float(vix_val, 18.5)

    # 2. USD/KRW FX level: check usdkrw_raw, price_db USDKRW=X, db_macro USDKRW=X, default 1380.0
    usdkrw_val = np.nan
    if 'usdkrw_raw' in indicator_infer.columns and not indicator_infer['usdkrw_raw'].dropna().empty:
        usdkrw_val = float(indicator_infer['usdkrw_raw'].dropna().iloc[-1])
    if (pd.isna(usdkrw_val) or usdkrw_val < 500) and price_db is not None:
        try:
            _usdkrw_df = price_db.get_prices('USDKRW=X', start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
            if _usdkrw_df is not None and not _usdkrw_df.empty and 'Close' in _usdkrw_df.columns:
                usdkrw_val = float(_usdkrw_df['Close'].dropna().iloc[-1])
        except Exception:
            pass
    if (pd.isna(usdkrw_val) or usdkrw_val < 500) and 'USDKRW=X' in db_macro:
        usdkrw_val = float(db_macro['USDKRW=X'])
    usdkrw_val = _safe_float(usdkrw_val, 1380.0)

    # 3. US 10Y Yield level: check us10y, price_db ^TNX, db_macro ^TNX, default 4.25
    us10y_val = np.nan
    if 'us10y' in indicator_infer.columns and not indicator_infer['us10y'].dropna().empty:
        us10y_val = float(indicator_infer['us10y'].dropna().iloc[-1])
    if (pd.isna(us10y_val) or us10y_val <= 0 or us10y_val > 25) and price_db is not None:
        try:
            _tnx_df = price_db.get_prices('^TNX', start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
            if _tnx_df is not None and not _tnx_df.empty and 'Close' in _tnx_df.columns:
                _raw_tnx = float(_tnx_df['Close'].dropna().iloc[-1])
                us10y_val = _raw_tnx / 10.0 if _raw_tnx > 20 else _raw_tnx
        except Exception:
            pass
    if (pd.isna(us10y_val) or us10y_val <= 0 or us10y_val > 25) and '^TNX' in db_macro:
        _raw_tnx = float(db_macro['^TNX'])
        us10y_val = _raw_tnx / 10.0 if _raw_tnx > 20 else _raw_tnx
    us10y_val = _safe_yield(us10y_val, 4.25)

    # Korean 10Y Bond Yield
    kr10y_val = _safe_yield(indicator_infer['kr10y'].iloc[-1] if 'kr10y' in indicator_infer.columns else float('nan'), 3.50)
    # WTI Crude Oil level (CL=F absolute Close price)
    wti_val = 75.0
    try:
        if price_db is not None:
            _wti_df = price_db.get_prices('CL=F', start_date=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'))
            if _wti_df is not None and not _wti_df.empty and 'Close' in _wti_df.columns:
                _last_wti = _wti_df['Close'].dropna().iloc[-1]
                if 10 < _last_wti < 300:  # sanity check
                    wti_val = float(_last_wti)
    except Exception:
        pass
    # Gold level (GLD ETF absolute Close price)
    gold_val = 220.0
    try:
        if price_db is not None:
            _gold_df = price_db.get_prices('GLD', start_date=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'))
            if _gold_df is not None and not _gold_df.empty and 'Close' in _gold_df.columns:
                _last_gold = _gold_df['Close'].dropna().iloc[-1]
                if _last_gold > 0:
                    gold_val = float(_last_gold)
    except Exception:
        pass

    # ══ P0: Macro Indicator Data-Integrity Gate ══════════════════════════════
    # Protect the report AND the crisis/regime gating against corrupted/duplicated
    # indicator series (e.g. VIX/WTI/Gold/US10Y all resolving to one shared value).
    # Verified values survive; out-of-band or mutually-identical values are replaced
    # with documented conservative defaults and a visible data-quality warning.
    macro_warnings: list[str] = []

    # ══ P0: Cross-asset distinctness check on RAW values (pre-replacement) ════
    # Must run BEFORE plausibility bounds replace out-of-range values, otherwise a
    # shared-series contamination (e.g. every indicator holding one ticker's Close,
    # like 103.478) survives: VIX gets defaulted first, then WTI/Gold fall inside
    # plausible ranges and the max-min spread becomes large. Detect identical raw
    # values across unrelated tickers to catch DB cache contamination.
    if detect_shared_series_corruption(vix_val, wti_val, gold_val, us10y_val):
        macro_warnings.append(
            "VIX/WTI/Gold/US10Y raw values nearly identical -> shared-series cache corruption detected; using defaults"
        )
        vix_val = 18.5
        wti_val = 75.0
        gold_val = 220.0
        us10y_val = 4.25
        kr10y_val = 3.35
        usdkrw_val = 1380.0

    def _plausible_bounds(name: str, val: float, lo: float, hi: float, default: float) -> float:
        nonlocal macro_warnings
        try:
            v = float(val)
            ok = pd.notna(v) and lo <= v <= hi
        except Exception:
            v = default
            ok = False
        if not ok:
            macro_warnings.append(f"{name}={'%s' % (val if pd.notna(val) else 'missing')} invalid (plausible range [{lo},{hi}]) -> default {default}")
            return default
        return v

    vix_report = _plausible_bounds("VIX Index", vix_val, 8.0, 55.0, 18.5)
    us10y_report = _plausible_bounds("US 10Y Yield", us10y_val, 0.5, 15.0, 4.25)
    kr10y_report = _plausible_bounds("KR 10Y Yield", kr10y_val, 0.5, 15.0, 3.35)
    usdkrw_report = _plausible_bounds("USD/KRW", usdkrw_val, 950.0, 2200.0, 1380.0)
    wti_report = _plausible_bounds("WTI Crude", wti_val, 25.0, 180.0, 75.0)
    gold_report = _plausible_bounds("Gold (GLD)", gold_val, 100.0, 800.0, 220.0)

    # Cross-asset distinctness check: identical values across unrelated tickers
    # indicates a shared-series / DB cache contamination (not a real market state).
    fin_macros = [float(x) for x in (vix_report, wti_report, gold_report)
                  if pd.notna(x) and x != 0.0]
    if len(fin_macros) >= 2 and max(fin_macros) - min(fin_macros) < 1.0:
        macro_warnings.append("VIX/WTI/Gold are nearly identical -> shared-series cache corruption detected; using defaults")
        vix_report = 18.5
        wti_report = 75.0
        gold_report = 220.0

    if macro_warnings:
        logger.warning(f"[PIN] Macro data-issue warnings detected ({len(macro_warnings)}): {{}}".format("; ".join(macro_warnings)))


    ensemble_weights = scorer.compute_dynamic_weights_from_sharpe(rolling_sharpes or {}, current_2d_regime)

    # ── RiskManager & CrisisDetector Integration ──
    try:
        from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
        risk_mgr = RiskManager()
        crisis_detector = CrisisDetector(risk_mgr)
        crisis_lvl = crisis_detector.evaluate(
            vix=vix_report,
            usdkrw=usdkrw_report,
            oil=wti_report,
            tnx=us10y_report
        )
        logger.info(f"[RISK MANAGER] Current Market Crisis Level evaluated: {crisis_lvl.value}")
        if crisis_lvl in [CrisisLevel.SEVERE, CrisisLevel.ACTIVE]:
            logger.warning(f"[RISK MANAGER] Crisis Level {crisis_lvl.value} active! Scaling down ensemble expected returns.")
            scale_factor = 0.5 if crisis_lvl == CrisisLevel.ACTIVE else 0.0
            ensemble_df['ensemble_expected_return'] = ensemble_df['ensemble_expected_return'] * scale_factor
            if crisis_lvl == CrisisLevel.SEVERE:
                ensemble_df['ensemble_score'] = 0.0

        # Intraday Microstructure Risk Evaluation
        if 'infer_data_dict' in locals() and infer_data_dict:
            intraday_results = risk_mgr.check_intraday_risk(infer_data_dict)
            triggered_symbols = [sym for sym, res in intraday_results.items() if res.triggered]
            if triggered_symbols:
                logger.warning(f"[INTRADAY RISK] Intraday stop-loss triggered for {len(triggered_symbols)} symbols: {triggered_symbols}")
                ensemble_df.loc[ensemble_df['symbol'].isin(triggered_symbols), 'ensemble_expected_return'] = -0.99
                ensemble_df.loc[ensemble_df['symbol'].isin(triggered_symbols), 'ensemble_score'] = 0.0
    except Exception as _rm_e:
        logger.warning(f"RiskManager evaluation skipped: {_rm_e}")

    # Milestone 3: CPCV & Historical Stress Testing Engine
    m3_report_str = ""
    try:
        from src.ai.cpcv_stress_tester import CPCVStressTester
        cpcv_tester = CPCVStressTester(n_splits=6, n_test_splits=2, purge_window=5, embargo_window=10)

        # Strategy matrix for PBO
        raw_scores_df = getattr(scorer, 'raw_scores', None)
        if raw_scores_df is not None and isinstance(raw_scores_df, pd.DataFrame) and not raw_scores_df.empty:
            pbo_res = cpcv_tester.compute_pbo(raw_scores_df)
        else:
            score_cols = [c for c in ensemble_df.columns if c.endswith('_score') or c.endswith('_return')]
            if len(score_cols) >= 2:
                pbo_res = cpcv_tester.compute_pbo(ensemble_df[score_cols])
            else:
                pbo_res = cpcv_tester.compute_pbo(ensemble_df[['ensemble_expected_return']])

        # Historical stress test scenarios
        _ens_ret_series = ensemble_df['ensemble_expected_return']
        if _ens_ret_series.dtype == object:
            _ens_ret_series = pd.to_numeric(_ens_ret_series, errors='coerce').fillna(0.0)
        ens_returns = _ens_ret_series.values
        scenarios = ["2008_CRISIS", "2020_COVID", "2022_FED_HIKE"]
        stress_reports = {}
        for sc in scenarios:
            stress_reports[sc] = cpcv_tester.run_historical_stress_test(ens_returns, scenario=sc)

        # Update RiskManager
        if 'risk_mgr' in locals() and risk_mgr is not None:
            risk_mgr.update_stress_test_results(stress_reports)

        # Build report section
        m3_text_lines = [
            "================================================================================",
            "[MILESTONE 3: CPCV & HISTORICAL STRESS TEST REPORT]",
            "================================================================================",
            f"Evaluation Time (KST): {kst_now_str}",
            f"CPCV Combinatorial Folds: {pbo_res.get('n_combinations', 15)} (N=6, k=2)",
            "Purge Window: 5 bars | Embargo Window: 10 bars",
            f"Probability of Backtest Overfitting (PBO): {pbo_res.get('pbo', 0.0):.4f} ({pbo_res.get('pbo', 0.0)*100:.2f}%) -> Overfitted: {pbo_res.get('is_overfitted', False)}",
            "",
            "--- Historical Macro Crisis Stress Test Scenarios ---"
        ]

        overall_passed = True
        for sc in scenarios:
            rep = stress_reports[sc]
            if not rep.pass_flag:
                overall_passed = False
            m3_text_lines.extend([
                f"Scenario: {sc}",
                f"  - Stressed MDD: {rep.mdd*100:.2f}% (Threshold: {rep.details.get('mdd_threshold', 0.30)*100:.2f}%)",
                f"  - Stressed Sharpe Ratio: {rep.stress_sharpe:.2f}",
                f"  - 95% VaR / CVaR: {rep.var_95*100:.2f}% / {rep.cvar_95*100:.2f}%",
                f"  - 99% VaR / CVaR: {rep.var_99*100:.2f}% / {rep.cvar_99*100:.2f}%",
                f"  - Stress Recovery Time: {rep.stress_recovery_time} bars",
                f"  - Stress Test Pass Flag: {'PASS' if rep.pass_flag else 'FAIL'}",
                ""
            ])

        adj_fact = getattr(risk_mgr, 'stress_test_adjustment_factor', 1.0) if 'risk_mgr' in locals() and risk_mgr is not None else 1.0
        status_str = f"PASSED (Position Capacity: {adj_fact:.2f}x)" if overall_passed else f"FAILED (Position Capacity Capped: {adj_fact:.2f}x)"
        m3_text_lines.extend([
            f"Overall Stress Test Status: {status_str}",
            "================================================================================\n"
        ])
        m3_report_str = "\n".join(m3_text_lines)

    except Exception as _m3_e:
        logger.warning(f"Milestone 3 CPCV & Stress Test calculation skipped: {_m3_e}")

    # Generate Decision Rationale Summary
    decision_rationale_text = scorer.get_regime_reasoning_summary(current_2d_regime, rolling_sharpes)

    # Generate Strategy Data Coverage & Missingness Analysis Report
    try:
        from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
        cov_analyzer = StrategyCoverageAnalyzer()
        cov_data = cov_analyzer.analyze_coverage(
            ensemble_df,
            prices_dict=infer_data_dict,
            features_df=df_rim_input if 'df_rim_input' in locals() else None,
            raw_scores=getattr(scorer, 'raw_scores', None)
        )
        cov_report_text = cov_analyzer.generate_coverage_report(cov_data, date_str=kst_now_str)

        # Build Milestone 4 Report Block
        m4_report_str = ""
        if 'slippage_metrics' in locals() and slippage_metrics is not None:
            m4_map = slippage_metrics.market_slippage_map
            m4_text_lines = [
                "================================================================================",
                "[MILESTONE 4: CLOSED-LOOP REALIZED SLIPPAGE REPORT]",
                "================================================================================",
                f"Evaluation Time (KST): {kst_now_str}",
                "Database Path: trade_logs.db",
                "Analysis Window: 30 days",
                f"Total Execution Samples Analyzed: {slippage_metrics.sample_count}",
                f"Overall Realized Average Slippage: {slippage_metrics.avg_slippage_bps:.2f} bps",
                f"Empirical Market Impact Alpha: {slippage_metrics.market_impact_alpha:.4f}",
                f"Dynamic Cost Scaling Factor: {slippage_metrics.cost_scaling_factor:.2f}x",
                "",
                "--- Realized Slippage Map by Market ---",
                f"  - KOSPI      : {m4_map.get('KOSPI', 5.0):.2f} bps",
                f"  - KOSDAQ     : {m4_map.get('KOSDAQ', 5.0):.2f} bps",
                f"  - SP500      : {m4_map.get('SP500', 5.0):.2f} bps",
                f"  - NASDAQ     : {m4_map.get('NASDAQ', 5.0):.2f} bps",
                f"  - RUSSELL2000: {m4_map.get('RUSSELL2000', 5.0):.2f} bps",
                "================================================================================\n"
            ]
            m4_report_str = "\n".join(m4_text_lines)

        m5_report_str = ""
        try:
            m5_metrics = m5_sentiment_metrics_list if 'm5_sentiment_metrics_list' in locals() else []
            m5_report_str = cov_analyzer.generate_m5_sentiment_report(m5_metrics, kst_now_str=kst_now_str)
        except Exception as _m5_e:
            logger.warning(f"Milestone 5 sentiment report formatting skipped: {_m5_e}")

        cov_output_path = os.path.join(result_dir, "strategy_data_coverage_report.txt")
        report_sections = [cov_report_text]
        if 'm3_report_str' in locals() and m3_report_str:
            report_sections.append(m3_report_str)
        if m4_report_str:
            report_sections.append(m4_report_str)
        if m5_report_str:
            report_sections.append(m5_report_str)

        with open(cov_output_path, "w", encoding="utf-8") as f_cov:
            f_cov.write("\n\n".join(report_sections))
        logger.info(f"Saved Strategy Data Coverage report to {cov_output_path}")
    except Exception as _cov_e:
        logger.warning(f"Strategy Coverage analysis skipped: {_cov_e}")

    # ── Task 2 & 4: Meta-Learner Auto Rolling Retrain & Strategy Attribution Analysis ──
    try:
        from src.ai.meta_ensemble_learner import MetaEnsembleLearner
        meta_retrainer = MetaEnsembleLearner()
        if 'hist_df' in locals() and hist_df is not None and not hist_df.empty:
            meta_retrainer.auto_rolling_retrain(hist_df)
    except Exception as _mr_e:
        logger.warning(f"Meta-Learner auto rolling retrain skipped: {_mr_e}")

    try:
        from src.analysis.attribution_analyzer import StrategyAttributionAnalyzer
        attr_analyzer = StrategyAttributionAnalyzer(output_dir=result_dir)
        attr_analyzer.analyze_attribution(ensemble_df, weights=ensemble_weights if 'ensemble_weights' in locals() else None)
    except Exception as _attr_e:
        logger.warning(f"Strategy Attribution analysis skipped: {_attr_e}")

    # ── Task 3: Black-Litterman Portfolio Allocation Output ──
    try:
        from src.risk.position_sizing import PortfolioAllocator
        allocator = PortfolioAllocator()
        top_preds = ensemble_df.head(20).set_index('symbol')['ensemble_expected_return'].to_dict()
        bl_alloc_df = allocator.allocate_black_litterman(prices_dict=infer_data_dict, predicted_returns=top_preds)
        if not bl_alloc_df.empty:
            bl_path = os.path.join(result_dir, "portfolio_allocation_black_litterman.txt")
            with open(bl_path, "w", encoding="utf-8") as f_bl:
                f_bl.write("=== Black-Litterman Optimal Asset Allocation ===\n")
                f_bl.write(f"Date: {kst_now_str}\n\n")
                f_bl.write(f"{'Rank':<5}{'Symbol':<10}{'Weight (%)':<15}{'Allocation (KRW)':<20}\n")
                f_bl.write("-" * 50 + "\n")
                for rank, (_, row) in enumerate(bl_alloc_df.iterrows(), 1):
                    f_bl.write(f"{rank:<5}{row['symbol']:<10}{row['weight']*100:>12.2f}%   {row['allocation_amount']:>18,.0f}\n")
            logger.info(f"Saved Black-Litterman portfolio allocation to {bl_path}")
    except Exception as _bl_e:
        logger.warning(f"Black-Litterman portfolio allocation output skipped: {_bl_e}")

    ensemble_output_path = os.path.join(result_dir, "ensemble_predictions.txt")
    target_cols = [c for c in ['name', 'market'] if c in universe.columns]
    cols_to_drop = [c for c in target_cols if c in ensemble_df.columns]
    ensemble_clean = ensemble_df.drop(columns=cols_to_drop) if cols_to_drop else ensemble_df
    univ_cols = ['symbol'] + target_cols
    ensemble_df_merged = ensemble_clean.merge(universe[univ_cols], on='symbol', how='left')

    # ── Execution OMS Order Plan Generation & DB Logging ──
    try:
        from src.execution.oms_engine import ExecutionOMSEngine
        oms_engine = ExecutionOMSEngine(db_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_logs.db"))
        top_picks_dicts = ensemble_df_merged.head(20).to_dict(orient="records")
        weight_dict = dict(zip(ensemble_df_merged['symbol'], ensemble_df_merged.get('portfolio_weight', 0.05)))
        order_plans = oms_engine.generate_order_plan(top_picks_dicts, weight_dict, total_capital=100_000_000.0)
        logger.info(f"[OMS ENGINE] Generated & saved {len(order_plans)} order execution plans to trade_logs.db")
    except Exception as _oms_e:
        logger.warning(f"[OMS ENGINE] Order plan generation skipped: {_oms_e}")

    with open(ensemble_output_path, "w", encoding="utf-8") as f:
        f.write("=== Dynamic Multi-Strategy Ensemble Predictions (18 Strategies) ===\n")
        f.write(f"Date: {kst_now_str}\n\n")

        # 1. Executive Summary & Basis
        vol_state = "HIGH_VOL" if (vix_report >= 20.0 or sp500_vol_20d >= 2.0) else "LOW_VOL"
        us_trend = "BULL" if sp500_ret_20d > 0.0 else ("BEAR" if sp500_ret_20d < -0.05 else "SIDEWAYS")
        kr_trend = "BULL" if kospi_ret_20d > 0.0 else ("BEAR" if kospi_ret_20d < -0.05 else "SIDEWAYS")
        us_2d_regime = f"{us_trend}_{vol_state}"
        kr_2d_regime = f"{kr_trend}_{vol_state}"

        f.write("--- Executive Market Summary ---\n")
        f.write(f"Current Market Regime Detected: {current_regime_label} (2D State: {current_2d_regime})\n")
        f.write(f"US Market Regime (S&P500): {us_2d_regime}\n")
        f.write(f"KR Market Regime (KOSPI) : {kr_2d_regime}\n")
        f.write(f"Maximum Total Allocation Allowed: {max_alloc*100:.1f}%\n\n")

        f.write("--- Judgment Basis (Global Macro Indicators) ---\n")
        f.write(f"  S&P 500 (20d Rolling Mean Return) : {sp500_ret_20d:+.3f}% / day\n")
        f.write(f"  S&P 500 (20d Rolling Volatility)  : {sp500_vol_20d:.3f}%\n")
        f.write(f"  KOSPI (20d Rolling Mean Return)   : {kospi_ret_20d:+.3f}% / day\n")
        f.write(f"  KOSPI (20d Rolling Volatility)    : {kospi_vol_20d:.3f}%\n")
        f.write(f"  VIX Index (Fear Gauge)            : {vix_report:.2f}\n")
        f.write(f"  USD/KRW FX Rate                   : {usdkrw_report:,.2f} KRW\n")
        f.write(f"  US 10Y Bond Yield (TNX)           : {us10y_report:.2f}%\n")
        f.write(f"  KR 10Y Bond Yield                 : {kr10y_report:.2f}%\n")
        f.write(f"  WTI Crude Oil                     : ${wti_report:.2f} / bbl\n")
        f.write(f"  Gold (GLD ETF)                    : ${gold_report:.2f}\n")
        if macro_warnings:
            f.write("  Data-Quality Warnings (see footer) : {} issue(s)\n".format(len(macro_warnings)))
        f.write("\n")


        f.write(f"{decision_rationale_text}\n\n")

        f.write("--- Applied Ensemble Strategy Weights (18 Strategies) ---\n")
        f.write(f"  XGBoost Regression Fundamentals   : {ensemble_weights.get('regression', 0.0)*100:.1f}%\n")
        f.write(f"  Surge Classifier (XGBoost)        : {ensemble_weights.get('surge', 0.0)*100:.1f}%\n")
        f.write(f"  Index & Sector Lead-Lag Flow      : {ensemble_weights.get('lead_lag', 0.0)*100:.1f}%\n")
        f.write(f"  VCP Rule Pattern Detector         : {ensemble_weights.get('vcp_rule', 0.0)*100:.1f}%\n")
        f.write(f"  VCP Machine Learning Predictor    : {ensemble_weights.get('vcp_ml', 0.0)*100:.1f}%\n")
        f.write(f"  Strict Causal LSTM Deep Learning  : {ensemble_weights.get('lstm', 0.0)*100:.1f}%\n")
        f.write(f"  Stat-Arb Cointegration Mean Rev   : {ensemble_weights.get('stat_arb', 0.0)*100:.1f}%\n")
        f.write(f"  Sector Rotation Relative Momentum : {ensemble_weights.get('sector_rotation', 0.0)*100:.1f}%\n")
        f.write(f"  RIM Valuation (Residual Income)   : {ensemble_weights.get('rim_valuation', 0.0)*100:.1f}%\n")
        f.write(f"  Event-Driven Disclosure Catalyst  : {ensemble_weights.get('event_driven', 0.0)*100:.1f}%\n")
        f.write(f"  Momentum Quality (MQ) Factor      : {ensemble_weights.get('mq_factor', 0.0)*100:.1f}%\n")
        f.write(f"  Options Put/Call IV Skew          : {ensemble_weights.get('iv_skew', 0.0)*100:.1f}%\n")
        f.write(f"  Order Flow Imbalance (MFI)        : {ensemble_weights.get('order_flow', 0.0)*100:.1f}%\n")
        f.write(f"  Short-Term Mean Reversal          : {ensemble_weights.get('short_term_reversal', 0.0)*100:.1f}%\n")
        f.write(f"  Analyst Revision Momentum (ARM)   : {ensemble_weights.get('arm_factor', 0.0)*100:.1f}%\n")
        f.write(f"  Cross-Asset Regime Divergence(CARD): {ensemble_weights.get('card_factor', 0.0)*100:.1f}%\n")
        f.write(f"  Liq-Adj Tail Risk (LATR)          : {ensemble_weights.get('latr_factor', 0.0)*100:.1f}%\n")
        f.write(f"  Inst & Foreign Sector Flow        : {ensemble_weights.get('inst_foreign_sector', 0.0)*100:.1f}%\n\n")

        # 2. Recommendations per market
        f.write("--- Top 20 Recommendations by Market ---\n")
        krx_markets = ['KOSPI', 'KOSDAQ']
        for market in krx_markets + ['SP500', 'NASDAQ', 'RUSSELL2000']:
            m_df = ensemble_df_merged[ensemble_df_merged['market'] == market].sort_values(by='ensemble_score', ascending=False)
            if m_df.empty:
                continue
            f.write("\n=========================================\n")
            f.write(f"[{market}] Top 100 Ensemble Picks\n")
            f.write("=========================================\n")
            f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Expected Ret':<14}{'Reg':<5}{'Srg':<5}{'L-L':<5}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<5}{'S-Arb':<6}{'Sec-R':<6}{'RIM':<5}{'Event':<6}{'MQ':<5}{'IV-Sk':<6}{'Flow':<5}{'Rev':<5}{'ARM':<5}{'CARD':<6}{'LATR':<5}\n")
            f.write("-" * 171 + "\n")
            for rank, (_, row) in enumerate(m_df.head(100).iterrows(), 1):
                name_val = row.get('name', 'Unknown')
                name_str = str(name_val)[:16] if pd.notna(name_val) else "Unknown"
                vcp_rule_val = row.get('vcp_rule_score', 0.0)
                lstm_val = row.get('lstm_score', 0.0)
                sa_val = row.get('stat_arb_score', 0.0)
                sec_val = row.get('sector_score', 0.0)
                rim_val = row.get('rim_score', 0.0)
                ev_val = row.get('event_score', 0.0)
                mq_val = row.get('mq_score', 0.0)
                iv_val = row.get('iv_skew_score', 0.0)
                of_val = row.get('order_flow_score', 0.0)
                rev_val = row.get('reversal_score', 0.0)
                arm_val = row.get('arm_score', 0.0)
                card_val = row.get('card_score', 0.0)
                latr_val = row.get('latr_score', 0.0)

                f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{row['ensemble_score']*100:>10.1f}%{row['ensemble_expected_return']:>12.2f}%{row['reg_score']*100:>4.0f}%{row['surge_score']*100:>4.0f}%{row['ll_score']*100:>4.0f}%{vcp_rule_val*100:>5.0f}%{row['vcp_ml_score']*100:>5.0f}%{lstm_val*100:>4.0f}%{sa_val*100:>5.0f}%{sec_val*100:>5.0f}%{rim_val*100:>4.0f}%{ev_val*100:>5.0f}%{mq_val*100:>4.0f}%{iv_val*100:>5.0f}%{of_val*100:>4.0f}%{rev_val*100:>4.0f}%{arm_val*100:>4.0f}%{card_val*100:>5.0f}%{latr_val*100:>4.0f}%\n")
            f.write("\n")
        if macro_warnings:
            f.write("--- Data Quality Notes (auto-detected) ---\n")
            for _dw in macro_warnings:
                f.write(f"  [WARN] {_dw}\n")
            f.write("  All sanitized values shown above; raw fallback defaults applied for corrupted series.\n")
            f.write("  Run: trading_system/validate_macro.py for offline DB cross-check.\n")
    logger.info(f"Saved ensemble predictions ({len(ensemble_df)} symbols) to {ensemble_output_path}")

    # Per-market suffix files for GHA artifact merge (merge_ensemble_predictions reads ensemble_predictions_{MARKET}.txt)
    for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
        _m_df = ensemble_df_merged[ensemble_df_merged['market'] == _m].sort_values(by='ensemble_score', ascending=False)
        if _m_df.empty:
            continue
        _mkt_ens_path = os.path.join(result_dir, f"ensemble_predictions_{_m}.txt")
        with open(_mkt_ens_path, "w", encoding="utf-8") as _mf:
            _mf.write("=== Dynamic Multi-Strategy Ensemble Predictions (18 Strategies) ===\n")
            _mf.write(f"Date: {kst_now_str}\n\n")
            _mf.write("\n=========================================\n")
            _mf.write(f"[{_m}] Top 100 Ensemble Picks\n")
            _mf.write("=========================================\n")
            _mf.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Expected Ret':<14}{'Reg':<5}{'Srg':<5}{'L-L':<5}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<5}{'S-Arb':<6}{'Sec-R':<6}{'RIM':<5}{'Event':<6}{'MQ':<5}{'IV-Sk':<6}{'Flow':<5}{'Rev':<5}{'ARM':<5}{'CARD':<6}{'LATR':<5}\n")
            _mf.write("-" * 171 + "\n")
            for _rank, (_, _row) in enumerate(_m_df.head(100).iterrows(), 1):
                _name_str = str(_row['name'])[:16] if pd.notna(_row['name']) else "Unknown"
                _mf.write(
                    f"{_rank:<5}{_row['symbol']:<10}{_name_str:<18}"
                    f"{_row['ensemble_score']*100:>10.1f}%{_row['ensemble_expected_return']:>12.2f}%"
                    f"{_row['reg_score']*100:>4.0f}%{_row['surge_score']*100:>4.0f}%{_row['ll_score']*100:>4.0f}%"
                    f"{_row.get('vcp_rule_score', 0.0)*100:>5.0f}%{_row['vcp_ml_score']*100:>5.0f}%"
                    f"{_row.get('lstm_score', 0.0)*100:>4.0f}%{_row.get('stat_arb_score', 0.0)*100:>5.0f}%"
                    f"{_row.get('sector_score', 0.0)*100:>5.0f}%{_row.get('rim_score', 0.0)*100:>4.0f}%"
                    f"{_row.get('event_score', 0.0)*100:>5.0f}%{_row.get('mq_score', 0.0)*100:>4.0f}%"
                    f"{_row.get('iv_skew_score', 0.0)*100:>5.0f}%{_row.get('order_flow_score', 0.0)*100:>4.0f}%"
                    f"{_row.get('reversal_score', 0.0)*100:>4.0f}%"
                    f"{_row.get('arm_score', 0.0)*100:>4.0f}%{_row.get('card_score', 0.0)*100:>5.0f}%{_row.get('latr_score', 0.0)*100:>4.0f}%\n"
                )
        logger.info(f"Saved ensemble predictions for {_m} to {_mkt_ens_path}")

    # Save Strategy 6: Strict Causal LSTM predictions standalone report
    try:
        lstm_output_path = os.path.join(result_dir, "lstm_predictions.txt")
        if 'lstm_score' in ensemble_df_merged.columns:
            lstm_merged = ensemble_df_merged.sort_values(by='lstm_score', ascending=False)
            def _write_lstm_file(f_out, df_lstm):
                f_out.write("=== Strategy 6: Strict Causal LSTM Time-Series Predictions ===\n")
                f_out.write(f"Date: {kst_now_str}\n")
                f_out.write(f"Total symbols evaluated: {len(df_lstm)}\n\n")
                f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{'LSTM Score':<14}\n")
                f_out.write("-" * 60 + "\n")
                for rank, (_, row) in enumerate(df_lstm.head(100).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['lstm_score']*100:>12.1f}%\n")

            with open(lstm_output_path, "w", encoding="utf-8") as f:
                _write_lstm_file(f, lstm_merged)
            logger.info(f"Saved LSTM deep learning predictions ({len(lstm_merged)} symbols) to {lstm_output_path}")

            for _m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
                _m_df = lstm_merged[lstm_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"lstm_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_lstm_file(_mf, _m_df)
    except Exception as _lstm_e:
        logger.warning(f"LSTM prediction standalone file save skipped: {_lstm_e}")


    logger.info("Running Portfolio Position Sizing allocation on Ensemble expectancies...")
    # Prepare the input DataFrame expected by PortfolioAllocator: ['symbol', 20]
    ensemble_for_alloc = ensemble_df[['symbol', 'ensemble_expected_return']].rename(
        columns={'ensemble_expected_return': 20}
    )
    allocator = PortfolioAllocator(target_horizon=20, max_total_allocation=max_alloc)
    alloc_df = allocator.allocate(ensemble_for_alloc, infer_data_dict, total_portfolio_value=cfg.portfolio_capital_krw, use_hrp=True, regime=current_2d_regime)

    if not alloc_df.empty:
        alloc_df = alloc_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
        alloc_output_path = os.path.join(result_dir, "portfolio_allocation.txt")
        with open(alloc_output_path, "w", encoding="utf-8") as f:
            f.write("=== Portfolio Allocation Recommendations (Ensemble Kelly/Sharpe Optimized) ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Total Capital: {cfg.portfolio_capital_krw:,.0f} KRW\n")
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
            cash_amount = cash_weight * cfg.portfolio_capital_krw
            f.write("-" * 92 + "\n")
            f.write(f"Allocated Capital: {allocated_weight*100:>5.2f}% ({alloc_df['allocation_amount'].sum():>14,.0f})\n")
            f.write(f"Remaining Cash   : {cash_weight*100:>5.2f}% ({cash_amount:>14,.0f})\n")
        logger.info(f"Saved portfolio allocation recommendations to {alloc_output_path}")

    # ── Phase 6-A: Generate Backtest Summary for GitHub Pages ────────────────
    try:
        from src.analysis.backtest_summary import generate_backtest_summary
        generate_backtest_summary(result_dir=result_dir, storage=storage)
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
        "stat_arb_predictions.txt",
        "sector_predictions.txt",
        "rim_predictions.txt",
        "arm_factor_predictions.txt",
        "card_factor_predictions.txt",
        "latr_factor_predictions.txt",
        "inst_foreign_sector_predictions.txt",
        "ensemble_predictions.txt",
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
        choices=["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ", "KRX"],
        default=None,
        metavar="MARKET",
        help="Market to run inference on: SP500 / NASDAQ / RUSSELL2000 / KOSPI / KOSDAQ / KRX "
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
        result_dir = os.environ.get("OUTPUT_RESULT_DIR", os.path.join(os.path.dirname(__file__), "result"))
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

