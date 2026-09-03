import os
import sys
import gc
import logging
import socket
import time
import threading
import traceback
from datetime import datetime
from typing import Optional, Any, Dict, List, Union, Tuple
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import FinanceDataReader as fdr
import yfinance as yf
import warnings
from pathlib import Path
import joblib

cpu_count = os.cpu_count()
_CPU_WORKERS: int = max(1, cpu_count if cpu_count is not None else 4)
_IO_WORKERS: int = min(32, max(16, _CPU_WORKERS * 8))
_PER_SYMBOL_TIMEOUT = 30  # seconds per symbol before skipping

# Reconfigure stdout to UTF-8 to prevent UnicodeEncodeError on Windows (cp949)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Set default socket timeout to prevent hanging connections (relaxed to 30s to prevent premature drops during batch downloads)
socket.setdefaulttimeout(30)

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
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.persistence.database import StockPriceDB
from src.analysis.regime_detector import MarketRegimeDetector
from src.data_layer.data_validator import DataValidator
from src.utils.rate_limiter import get_global_rate_limiter
from src.utils.technical_cache import DataFrameCache
from src.utils.http_session import setup_global_http_headers
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result, retry_if_exception_type
from src.data_layer.ecos_client import BOKECOSClient, ECOS_ITEM_MAP


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Initialize global HTTP session headers for yfinance and FinanceDataReader calls
setup_global_http_headers()


def detect_shared_series_corruption(vix_val, wti_val, gold_val, us10y_val) -> bool:
    """P0: Detect shared-series / DB cache contamination on RAW indicator values."""
    return DataValidator.detect_shared_series_corruption(vix_val, wti_val, gold_val, us10y_val)


def largest_remainder_round(values: list[float], target_sum: float = 100.0, decimals: int = 1) -> list[float]:
    """
    Distribute target_sum across values using Largest Remainder Method (Hare-Niemeyer)
    so that the rounded values sum exactly to target_sum at specified decimal places.
    """
    if not values:
        return []
    factor = 10 ** decimals
    safe_values = [float(v) if (v is not None and np.isfinite(v) and float(v) >= 0) else 0.0 for v in values]
    total_val = sum(safe_values)
    if total_val <= 0 or not np.isfinite(total_val):
        n = len(safe_values)
        if n == 0:
            return []
        base = int((target_sum * factor) // n)
        rem = int(round(target_sum * factor - base * n))
        res = [base + (1 if i < rem else 0) for i in range(n)]
        return [r / factor for r in res]
    
    target_int = int(round(target_sum * factor))
    scaled = [v * (target_int / total_val) for v in safe_values]
    floored = [int(s) for s in scaled]
    remainders = [(s - f, -v, i) for i, (s, f, v) in enumerate(zip(scaled, floored, safe_values))]
    
    current_sum = sum(floored)
    diff = target_int - current_sum
    
    if diff > 0:
        # Sort by remainder descending, then original value descending
        remainders.sort(key=lambda x: (x[0], x[1]), reverse=True)
        for j in range(diff):
            idx = remainders[j % len(remainders)][2]
            floored[idx] += 1
    elif diff < 0:
        remainders.sort(key=lambda x: (x[0], x[1]))
        for j in range(-diff):
            idx = remainders[j % len(remainders)][2]
            floored[idx] = max(0, floored[idx] - 1)
            
    return [f / factor for f in floored]


def _is_all_limit(limit: Union[int, str, None]) -> bool:
    """Check if prediction output limit is configured to all symbols."""
    if limit is None:
        return False
    return isinstance(limit, str) and limit.strip().lower() in ("all", "0", "-1", "none")


def _slice_top_df(df: Optional[pd.DataFrame], limit: Union[int, str, None]) -> pd.DataFrame:
    """Slice DataFrame to top limit rows, or return all rows if limit is 'all' / None / <=0."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    if limit is None or _is_all_limit(limit):
        return df
    try:
        n = int(limit)
        return df.head(n) if n > 0 else df
    except (ValueError, TypeError):
        return df.head(100)


def _slice_top_list(items: Optional[list], limit: Union[int, str, None]) -> list:
    """Slice list to top limit items, or return all items if limit is 'all' / None / <=0."""
    if items is None:
        return []
    if limit is None or _is_all_limit(limit):
        return items
    try:
        n = int(limit)
        return items[:n] if n > 0 else items
    except (ValueError, TypeError):
        return items[:100]


def _get_effective_limit(cfg: Any = None) -> Union[int, str]:
    """Retrieve effective prediction output limit from TradingConfig or os.environ."""
    raw = getattr(cfg, 'prediction_output_limit', None) if cfg is not None else None
    if raw is None:
        raw = os.environ.get("PREDICTION_OUTPUT_LIMIT", os.environ.get("STRATEGY_OUTPUT_LIMIT", "100"))
    if isinstance(raw, str) and raw.strip().lower() in ("all", "0", "-1", "none"):
        return "all"
    try:
        n = int(raw)
        return n if n > 0 else "all"
    except (ValueError, TypeError):
        return 100


# P3: Rotating file logger — persists logs across terminal sessions and GHA log expiry
def _setup_rotating_logger() -> None:
    """Attach a RotatingFileHandler to the root logger (10MB × 5 backups)."""
    from logging.handlers import RotatingFileHandler
    from pathlib import Path
    import json
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "run_id": os.environ.get("GITHUB_RUN_ID", ""),
                "market": os.environ.get("INFERENCE_TARGET", ""),
                "symbol": getattr(record, "symbol", "")
            }
            return json.dumps(log_obj)

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
    if os.environ.get('GITHUB_ACTIONS'):
        file_handler.setFormatter(JSONFormatter())
    else:
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

technical_cache = DataFrameCache(ttl=300.0, max_items=500)

def is_empty_result(result):
    if result is None:
        return True
    if isinstance(result, pd.DataFrame) and result.empty:
        return True
    return False


# yfinance suffix mapping for global stock markets
_MARKET_SUFFIX_MAP = {
    'KOSPI': '.KS',
    'KOSDAQ': '.KQ',
    'KRX': '.KS',
    'CHINA_SSE': '.SS',
    'SSE': '.SS',
    'CHINA_SZSE': '.SZ',
    'SZSE': '.SZ',
    'JAPAN_TSE': '.T',
    'TSE': '.T',
    'VIETNAM_HOSE': '.VN',
    'HOSE': '.VN',
    'INDIA_NSE': '.NS',
    'NSE': '.NS',
    'INDIA_BSE': '.BO',
    'BSE': '.BO',
    'TAIWAN_TWSE': '.TW',
    'TWSE': '.TW',
    'AUSTRALIA_ASX': '.AX',
    'ASX': '.AX',
    'BRAZIL_B3': '.SA',
    'B3': '.SA',
    'HKEX': '.HK',
    'SINGAPORE_SGX': '.SI',
    'SGX': '.SI',
    'CANADA_TSX': '.TO',
    'TSX': '.TO',
}
_KR_MARKET_SUFFIX = _MARKET_SUFFIX_MAP  # backward compatibility alias


def format_canonical_yf_symbol(symbol: str, market: str) -> str:
    """Format symbol for yfinance downloading based on market and international ticker conventions.

    HKEX normalization: HK ticker codes must be 4-digit zero-padded integers (e.g. "1281.HK",
    "0700.HK"). Leading zeros beyond 4 digits (e.g. "01281" from fdr.StockListing) are stripped
    via int() conversion so that yfinance receives the canonical form.
    """
    m = str(market).strip().upper()
    s = str(symbol).strip()

    # ── HKEX: normalize BEFORE the generic suffix early-return ──────────────
    # Handles both bare codes ("01281", "700") and already-suffixed ("01281.HK")
    # regardless of whether market is explicit or inferred from the .HK suffix.
    is_hk_market = (m == 'HKEX')
    is_hk_suffix = s.upper().endswith('.HK')
    if is_hk_market or is_hk_suffix:
        numeric_part = s.split('.')[0]  # "01281.HK" → "01281", "1281" → "1281"
        if numeric_part.isdigit():
            # int() strips leading zeros; :04d re-pads to minimum 4 digits
            return f"{int(numeric_part):04d}.HK"
        # Non-numeric HK symbol (e.g. "HSBA.HK") — keep as-is with suffix
        return s if is_hk_suffix else f"{s}.HK"
    # ────────────────────────────────────────────────────────────────────────

    known_suffixes = ('.KS', '.KQ', '.SS', '.SZ', '.T', '.VN', '.NS', '.BO', '.DE', '.PA', '.AS', '.L', '.SW', '.MI', '.TW', '.TWO', '.AX', '.SA', '.HK', '.SI', '.TO')
    if any(s.upper().endswith(sfx) for sfx in known_suffixes):
        return s

    if m in ('KOSPI', 'KOSDAQ', 'KRX'):
        canonical = s.zfill(6) if s.isdigit() and len(s) <= 6 else s
        suffix = _MARKET_SUFFIX_MAP.get(m, '.KS')
        return f"{canonical}{suffix}"

    if m in _MARKET_SUFFIX_MAP:
        suffix = _MARKET_SUFFIX_MAP[m]
        return f"{s}{suffix}"

    if m in ('SP500', 'NASDAQ', 'RUSSELL2000', 'NYSE', 'AMEX', 'US'):
        return s.replace('.', '-')

    # Fallback: if purely numeric and no explicit market specified, assume KRX
    if s.isdigit() and len(s) <= 6:
        return f"{s.zfill(6)}.KS"

    return s



def _fetch_naver_direct(symbol: str, start_date: str) -> pd.DataFrame:
    """Tier 3 fallback for KRX: Naver Financial Chart XML API."""
    import urllib.request
    import xml.etree.ElementTree as ET
    code = symbol.zfill(6) if symbol.isdigit() and len(symbol) <= 6 else symbol.split('.')[0]
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count=3000&requestType=0"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_data = resp.read().decode('euc-kr', errors='ignore')
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        rows = []
        for item in items:
            data_str = item.attrib.get('data', '')
            parts = data_str.split('|')
            if len(parts) >= 6:
                d_str = parts[0]
                date_str = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                if not start_date or date_str >= start_date:
                    rows.append({
                        'Date': pd.to_datetime(date_str),
                        'Open': float(parts[1]),
                        'High': float(parts[2]),
                        'Low': float(parts[3]),
                        'Close': float(parts[4]),
                        'Volume': float(parts[5]),
                    })
        if rows:
            df = pd.DataFrame(rows).set_index('Date').sort_index()
            return df
    except Exception as e:
        logger.debug(f"Naver direct API fetch failed for {symbol}: {e}")
    return pd.DataFrame()


def _fetch_pykrx(symbol: str, start_date: str) -> pd.DataFrame:
    """Tier 4 fallback for KRX: PyKRX API."""
    try:
        from pykrx import stock
        code = symbol.zfill(6) if symbol.isdigit() and len(symbol) <= 6 else symbol.split('.')[0]
        s_date = (start_date or "2018-01-01").replace('-', '')
        e_date = datetime.now().strftime('%Y%m%d')
        df = stock.get_market_ohlcv_by_date(s_date, e_date, code)
        if df is not None and not df.empty:
            col_map = {'시가': 'Open', '고가': 'High', '저가': 'Low', '종가': 'Close', '거래량': 'Volume'}
            df = df.rename(columns=col_map)
            cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
            df = df[cols]
            df.index.name = 'Date'
            return df
    except Exception as e:
        logger.debug(f"PyKRX fetch failed for {symbol}: {e}")
    return pd.DataFrame()


def _fetch_stooq_or_yahoo_direct(symbol: str, start_date: str) -> pd.DataFrame:
    """Tier 3 fallback for US: Stooq / Yahoo Direct API."""
    try:
        df = fdr.DataReader(f"STOOQ:{symbol.upper()}", start=start_date)
        if df is not None and not df.empty:
            df.columns = [str(c).capitalize() for c in df.columns]
            return df
    except Exception as e:
        logger.debug(f"FDR Stooq fetch failed for {symbol}: {e}")

    try:
        stooq_sym = symbol.lower().replace('.', '-')
        url = f"https://stooq.com/q/d/l/?s={stooq_sym}.us&i=d"
        df = pd.read_csv(url, parse_dates=['Date'], index_col='Date')
        if df is not None and not df.empty:
            if start_date:
                df = df[df.index >= pd.to_datetime(start_date)]
            df.columns = [str(c).capitalize() for c in df.columns]
            return df
    except Exception as e:
        logger.debug(f"Direct Stooq CSV fetch failed for {symbol}: {e}")

    return pd.DataFrame()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=True
)
def _fetch_yf_primary(yf_symbol: str, start_date: str) -> pd.DataFrame:
    """Tier 1 yfinance primary fetch with automatic exponential backoff retries."""
    df = yf.download(yf_symbol, start=start_date, progress=False, auto_adjust=True)
    if df is not None and not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    return pd.DataFrame()


def _fetch_data_fdr_network(symbol: str, market: str, start_date: str) -> pd.DataFrame:
    # Enforce global rate limit coordination
    get_global_rate_limiter().wait()

    # Symbol normalization
    is_krx = market in ('KOSPI', 'KOSDAQ', 'KRX') or (symbol.isdigit() and len(symbol) <= 6)
    canonical_symbol = symbol.zfill(6) if is_krx and symbol.isdigit() and len(symbol) <= 6 else symbol
    yf_symbol = format_canonical_yf_symbol(canonical_symbol, market)

    result = None
    tier_source = None

    # Tier 1: Try yfinance primary download (with automatic Tenacity retries)
    try:
        df = _fetch_yf_primary(yf_symbol, start_date)
        if df is not None and not df.empty:
            result = df
            tier_source = 'yf'
            logger.debug(f"Tier 1 (yfinance) succeeded for {yf_symbol}")
    except Exception as e:
        logger.debug(f"Tier 1 (yfinance) network fetch failed for {yf_symbol}: {e}")

    # Tier 2: Secondary provider fallback (FinanceDataReader)
    if result is None or result.empty:
        try:
            logger.debug(f"Attempting Tier 2 (FinanceDataReader) download for {canonical_symbol}...")
            fdr_sym = canonical_symbol if is_krx else yf_symbol
            df = fdr.DataReader(fdr_sym, start=start_date)
            if df is not None and not df.empty:
                result = df
                tier_source = 'raw'
                logger.warning(f"Successfully retrieved Tier 2 (FinanceDataReader) data for {canonical_symbol}")
        except Exception as e:
            logger.debug(f"Tier 2 (FinanceDataReader) network fetch failed for {canonical_symbol}: {e}")

    # Tier 3 & Tier 4 (KRX / US specific fallbacks)
    if result is None or result.empty:
        if is_krx:
            # Tier 3 KRX: Naver Direct API
            try:
                logger.debug(f"Attempting Tier 3 (Naver Direct API) download for {canonical_symbol}...")
                df = _fetch_naver_direct(canonical_symbol, start_date)
                if df is not None and not df.empty:
                    result = df
                    tier_source = 'raw'
                    logger.warning(f"Successfully retrieved Tier 3 (Naver Direct API) data for {canonical_symbol}")
            except Exception as e:
                logger.debug(f"Tier 3 (Naver Direct API) fetch failed for {canonical_symbol}: {e}")

            # Tier 4 KRX: PyKRX
            if result is None or result.empty:
                try:
                    logger.debug(f"Attempting Tier 4 (PyKRX) download for {canonical_symbol}...")
                    df = _fetch_pykrx(canonical_symbol, start_date)
                    if df is not None and not df.empty:
                        result = df
                        tier_source = 'raw'
                        logger.warning(f"Successfully retrieved Tier 4 (PyKRX) data for {canonical_symbol}")
                except Exception as e:
                    logger.debug(f"Tier 4 (PyKRX) fetch failed for {canonical_symbol}: {e}")
        else:
            # Tier 3 US: Stooq / Yahoo Direct API
            try:
                logger.debug(f"Attempting Tier 3 (Stooq / Yahoo Direct) download for {canonical_symbol}...")
                df = _fetch_stooq_or_yahoo_direct(canonical_symbol, start_date)
                if df is not None and not df.empty:
                    result = df
                    tier_source = 'raw'
                    logger.warning(f"Successfully retrieved Tier 3 (Stooq / Yahoo Direct) data for {canonical_symbol}")
            except Exception as e:
                logger.debug(f"Tier 3 (Stooq / Yahoo Direct) fetch failed for {canonical_symbol}: {e}")

    if result is None or result.empty:
        raise ValueError(f"Fetched data for {symbol} is empty or None across all providers")

    # ── P0-7: unify price convention ────────────────────────────────────────
    # Tier 1 (yfinance) returns split-adjusted prices. Raw providers
    # (FDR/Naver/PyKRX/Stooq) return unadjusted prices; backward-adjust split
    # gaps so all symbols share one convention (recent price level is preserved,
    # so order_plans target prices remain at actual market prices).
    if tier_source == 'raw':
        try:
            from src.data_layer.price_adjuster import CorporateActionAdjuster
            result = CorporateActionAdjuster().adjust_ohlcv(result)
        except Exception as e:
            logger.debug(f"Corporate action adjust failed for {symbol}: {e}")

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
                yf_ticker = format_canonical_yf_symbol(sym, market)
                yf_tickers.append(yf_ticker)
                ticker_to_sym[yf_ticker] = sym

            logger.info(f"Downloading batch of {len(batch)} symbols starting from {fetch_start}...")

            def _download_yf_batch_with_retry(tickers: list, start_dt: str, max_attempts: int = 3) -> pd.DataFrame:
                """Download batch of tickers with exponential backoff retry on HTTP 429 rate limits / network errors."""
                delay = 2.0
                for attempt in range(1, max_attempts + 1):
                    try:
                        get_global_rate_limiter().wait()
                        df_res = yf.download(tickers, start=start_dt, progress=False, auto_adjust=True, group_by='ticker')
                        if df_res is not None and not df_res.empty:
                            return df_res
                        if len(tickers) > 1 and attempt < max_attempts:
                            logger.warning(
                                f"Batch yf.download returned empty result for {len(tickers)} tickers "
                                f"(attempt {attempt}/{max_attempts}), backing off {delay}s..."
                            )
                            time.sleep(delay)
                            delay = min(delay * 2, 10.0)
                            continue
                        return pd.DataFrame()
                    except Exception as ex:
                        is_429 = "429" in str(ex) or "Too Many Requests" in str(ex)
                        if attempt < max_attempts:
                            logger.warning(
                                f"yf.download failed for batch of {len(tickers)} tickers "
                                f"(attempt {attempt}/{max_attempts}, HTTP 429={is_429}): {ex}. Backing off {delay}s..."
                            )
                            time.sleep(delay)
                            delay = min(delay * 2, 10.0)
                        else:
                            raise ex
                return pd.DataFrame()

            def _download_with_recovery(tickers: list, start_dt: str) -> pd.DataFrame:
                if not tickers:
                    return pd.DataFrame()

                # Single-ticker fast path: no binary split needed
                if len(tickers) == 1:
                    try:
                        df_res = _download_yf_batch_with_retry(tickers, start_dt)
                        if df_res is not None and not df_res.empty:
                            return df_res
                    except Exception as ex:
                        logger.warning(f"Excluding bad ticker from batch: {tickers[0]} due to: {ex}")
                    # Empty result (delisted / no data) — skip silently
                    return pd.DataFrame()

                try:
                    df_res = _download_yf_batch_with_retry(tickers, start_dt)
                    if df_res is not None and not df_res.empty:
                        return df_res
                except Exception as ex:
                    if "429" in str(ex) or "Too Many Requests" in str(ex) or "Rate Limit" in str(ex):
                        logger.warning(f"Rate limit HTTP 429 encountered in batch download. Aborting split for {len(tickers)} tickers: {ex}")
                        raise ex
                    logger.info(f"Batch download failed after retries for {len(tickers)} tickers: {ex}. Proceeding to binary split.")

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
                # Merge along axis=1 (columns/tickers) with outer join for index alignment
                return pd.concat([df_left, df_right], axis=1, join='outer')

            try:
                df = _download_with_recovery(yf_tickers, fetch_start)
                if df is not None and not df.empty:
                    batch_price_data = {}
                    for yf_ticker in yf_tickers:
                        sym = ticker_to_sym.get(yf_ticker)
                        if not sym:
                            continue
                        ticker_df = None
                        if isinstance(df.columns, pd.MultiIndex):
                            # MultiIndex check: level 0 or level 1 depending on yfinance group_by
                            if yf_ticker in df.columns.get_level_values(0):
                                ticker_df = df.xs(yf_ticker, level=0, axis=1).dropna(how='all')
                            elif yf_ticker in df.columns.get_level_values(1):
                                ticker_df = df.xs(yf_ticker, level=1, axis=1).dropna(how='all')
                            elif len(yf_tickers) == 1:
                                ticker_df = df.droplevel(0, axis=1) if df.columns.nlevels > 1 else df
                        elif len(yf_tickers) == 1:
                            ticker_df = df
                        elif yf_ticker in df.columns:
                            # Single-level columns fallback
                            ticker_df = df[[yf_ticker]].dropna(how='all')

                        if ticker_df is not None and not ticker_df.empty:
                            if isinstance(ticker_df.columns, pd.MultiIndex):
                                ticker_df.columns = ticker_df.columns.droplevel(1)
                            # P2: Data Quality Gate — adjust corporate actions and validate before DB write
                            is_valid, ticker_df = DataValidator.sanitize_and_validate_price_data(sym, ticker_df)
                            if is_valid:
                                if ticker_df is not None and not ticker_df.empty:
                                    f64_cols = ticker_df.select_dtypes(include=['float64']).columns
                                    if len(f64_cols) > 0:
                                        ticker_df[f64_cols] = ticker_df[f64_cols].astype(np.float32)
                                batch_price_data[sym] = ticker_df

                    if batch_price_data:
                        if hasattr(price_db, "update_prices_batch"):
                            price_db.update_prices_batch(batch_price_data)
                        else:
                            for s, d in batch_price_data.items():
                                price_db.update_prices(s, d)
                        prefetched_count += len(batch_price_data)
            except Exception as e:
                logger.debug(f"Batch download failed for chunk: {e}")

    logger.info(f"Prefetched and cached prices for {prefetched_count}/{len(symbols)} symbols in DB.")
    return prefetched_count


def fetch_data_fdr(symbol: str, market: str, start_date: str, price_db: Optional[StockPriceDB] = None,
                   freshness_days: int = 7, update_interval: int = 0) -> Optional[pd.DataFrame]:
    """Fetch price data for a single symbol using technical_cache + MarketDataHandler (Multi-tier network & DB cache)."""
    if update_interval > 0:
        import time
        key = (symbol, start_date)
        ts = technical_cache._timestamps.get(key)
        if ts is not None and time.time() - ts > update_interval:
            technical_cache.invalidate(symbol, start_date)
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
                ohlcv_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in cached_df.columns]
                if ohlcv_cols:
                    cached_df[ohlcv_cols] = cached_df[ohlcv_cols].ffill()
                return cached_df

        network_result = None
        fetch_start = cached_df.index.max().strftime("%Y-%m-%d") if (cached_df is not None and not cached_df.empty) else d
        try:
            network_result = _fetch_data_fdr_network(s, market, fetch_start)
            if network_result is not None and not network_result.empty:
                network_result.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in network_result.columns]
        except Exception as e:
            logger.warning(f"Multi-tier network download failed for {s}: {e}")

        if network_result is not None and not network_result.empty:
            # DataValidator Gate: Adjust corporate actions and validate before storing into DB
            is_valid, network_result = DataValidator.sanitize_and_validate_price_data(s, network_result)
            if is_valid:
                if price_db is not None:
                    try:
                        price_db.update_prices(s, network_result)
                    except Exception as ex:
                        logger.debug(f"Failed to cache prices for {s}: {ex}")
            else:
                logger.warning(f"[DataQualityGate] Network payload for {s} failed validation. Skipping price_db update.")

            if cached_df is not None and not cached_df.empty:
                # Discontinuity / split check on overlapping dates
                overlap_idx = cached_df.index.intersection(network_result.index)
                if len(overlap_idx) > 0:
                    c_col = 'Close' if 'Close' in cached_df.columns else ('close' if 'close' in cached_df.columns else None)
                    n_col = 'Close' if 'Close' in network_result.columns else ('close' if 'close' in network_result.columns else None)
                    if c_col and n_col:
                        try:
                            c_last_overlap = float(cached_df.loc[overlap_idx[-1], c_col])
                            n_last_overlap = float(network_result.loc[overlap_idx[-1], n_col])
                            if c_last_overlap > 0 and n_last_overlap > 0:
                                ratio = n_last_overlap / c_last_overlap
                                if ratio < 0.70 or ratio > 1.40:
                                    logger.warning(f"[DataQualityGate] Split / corporate action discontinuity detected for {s} (ratio={ratio:.2f}). Invalidate old cache.")
                                    cached_df = None
                        except Exception:
                            pass

            if cached_df is not None and not cached_df.empty:
                merged_df = pd.concat([cached_df, network_result])
                merged_df = merged_df[~merged_df.index.duplicated(keep='last')].sort_index()
                ohlcv_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in merged_df.columns]
                if ohlcv_cols:
                    merged_df[ohlcv_cols] = merged_df[ohlcv_cols].ffill()
                return merged_df

            ohlcv_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in network_result.columns]
            if ohlcv_cols:
                network_result[ohlcv_cols] = network_result[ohlcv_cols].ffill()
            return network_result

        # Network failed, fall back to DB cache if available
        if (cached_df is None or cached_df.empty) and price_db is not None:
            cached_df = price_db.get_prices(s, start_date=None)
            if cached_df is not None and not cached_df.empty:
                cached_df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in cached_df.columns]

        if cached_df is not None and not cached_df.empty:
            logger.warning(f"[Offline Cache Fallback] Network failed for {s}. Falling back to cached DB data ({len(cached_df)} rows)")
            ohlcv_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in cached_df.columns]
            if ohlcv_cols:
                cached_df[ohlcv_cols] = cached_df[ohlcv_cols].ffill()
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
        ohlcv_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in result.columns]
        if ohlcv_cols:
            result[ohlcv_cols] = result[ohlcv_cols].ffill()
        f64_cols = result.select_dtypes(include=['float64']).columns
        if len(f64_cols) > 0:
            result[f64_cols] = result[f64_cols].astype(np.float32)
    return result


# Global indicator & Sector ETF tickers → feature column names
_INDICATOR_TICKERS = {
    '^GSPC': 'sp500_change',
    '^VIX': 'vix_change',
    '^TNX': 'us10y',         # US 10Y Treasury Yield (10년물)
    '^FVX': 'us5y',          # US 5Y Treasury Yield (5년물)
    '^IRX': 'us3m_yield',    # US 13-Week T-Bill (3개월물)
    'FRED:IRLTLT01KRM156N': 'kr10y',  # Korea 10Y Government Bond Yield (FRED / ECOS fallback)
    'FRED:IRSTCI01KRM156N': 'kr3y',   # Korea 3M/Short-Term Bond Rate (FRED / ECOS fallback)
    'USDKRW=X': 'usdkrw_change',
    'CL=F': 'wti_change',
    '^KS11': 'kospi_change',
    '^KQ11': 'kosdaq_change',
    # Sector & Bond ETFs (KRX Direct Code)
    '091160': 'kodex_semicon_change',
    '305720': 'kodex_battery_change',
    '244580': 'kodex_bio_change',
    '148070': 'kodex_ktb10y_change',
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

# ECOS-only tickers: fetched directly from BOK ECOS API (not via yfinance/FDR)
# mapped as ECOS:<key> → col_name
_ECOS_ONLY_TICKERS = {
    'ECOS:kr_base_rate': 'kr_base_rate',  # 한국 기준금리 (%)
    'ECOS:cd_91d':       'kr_cd91d',       # CD 91일물 금리 (%)
    'ECOS:m2_supply':    'kr_m2_supply',   # M2 통화량 (십억원)
}

# FRED series → BOK ECOS statistic key fallback (원천 데이터는 BOK)
_FRED_TO_ECOS_KEY = {
    'FRED:IRSTCI01KRM156N': 'cd_91d',    # kr3y — 한국 단기금리 (CD 91일물)
    'FRED:IRLTLT01KRM156N': 'ktb_10y',   # kr10y — 한국 10년물 국고채
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
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=False
)
def _download_indicator_network(ticker: str, start_date: str) -> pd.DataFrame:
    # Coordinate indicator fetch rate limiting
    get_global_rate_limiter().wait()

    # 1. Fast Path for FRED series (direct FRED HTTP CSV download - 0.3s response)
    if ticker.startswith("FRED:"):
        fred_id = ticker.split("FRED:", 1)[1]
        try:
            import requests
            import io
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200 and len(resp.text) > 20 and ',' in resp.text:
                csv_df = pd.read_csv(io.StringIO(resp.text))
                if len(csv_df.columns) >= 2:
                    date_col, val_col = csv_df.columns[0], csv_df.columns[1]
                    csv_df[date_col] = pd.to_datetime(csv_df[date_col], errors='coerce')
                    csv_df = csv_df.dropna(subset=[date_col]).set_index(date_col)
                    csv_df = csv_df[[val_col]].apply(pd.to_numeric, errors='coerce').dropna()
                    csv_df.columns = ['Close']
                    csv_df = csv_df[csv_df.index >= pd.to_datetime(start_date)]
                    if not csv_df.empty:
                        logger.info(f"Successfully retrieved FRED indicator {ticker} via direct FRED CSV")
                        return csv_df
        except Exception as fred_e:
            logger.debug(f"Direct FRED CSV download failed for {ticker}: {fred_e}")

        # 1b. BOK ECOS fallback for Korea rate series (원천 데이터: 한국은행)
        ecos_key = _FRED_TO_ECOS_KEY.get(ticker)
        if ecos_key is not None:
            try:
                client = _get_ecos_client()
                meta = ECOS_ITEM_MAP[ecos_key]
                df_ecos = client.fetch_statistic(
                    stat_code=meta["stat_code"],
                    item_code=meta["item_code"],
                    cycle=meta["cycle"],
                    start_date=start_date.replace("-", ""),
                )
                if not df_ecos.empty:
                    s = df_ecos.set_index("Date")["Value"].sort_index()
                    s.index = pd.to_datetime(s.index)
                    logger.info(f"[ECOS Fallback] {ticker} fetched via BOK ECOS {ecos_key} ({len(s)} rows)")
                    return pd.DataFrame({"Close": s.ffill()})
            except Exception as ecos_e:
                logger.debug(f"ECOS fallback failed for {ticker}: {ecos_e}")

    # 2. Path for KRX ETFs or FRED fallback via FinanceDataReader with worker thread timeout
    if ticker.startswith("FRED:") or (ticker.isdigit() and len(ticker) == 6):
        _fdr_box: dict = {}
        def _fdr_fetch() -> None:
            raw = fdr.DataReader(ticker, start=start_date)
            if raw is not None and not raw.empty:
                raw.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in raw.columns]
                _fdr_box["df"] = raw
        try:
            worker = threading.Thread(target=_fdr_fetch, daemon=True)
            worker.start()
            worker.join(timeout=15.0)
            if "df" in _fdr_box:
                logger.info(f"Successfully retrieved indicator data for {ticker} via FDR")
                return _fdr_box["df"]
            if worker.is_alive():
                logger.warning(f"FDR indicator download timed out after 15s for {ticker}")
            else:
                logger.warning(f"Direct FDR indicator download error for {ticker}: empty result")
        except Exception as e:
            logger.warning(f"Direct FDR indicator download error for {ticker}: {e}")

        if ticker.startswith("FRED:"):
            raise ValueError(f"FRED indicator {ticker} download failed via direct FRED HTTP and FDR")

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



# Module-level ECOS client (lazy init): reused across calls
_ecos_client: Optional[BOKECOSClient] = None
_ecos_lock = threading.Lock()


def _get_ecos_client() -> BOKECOSClient:
    """Return module-level BOKECOSClient, initializing on first call with thread safety."""
    global _ecos_client
    if _ecos_client is None:
        with _ecos_lock:
            if _ecos_client is None:
                _ecos_client = BOKECOSClient()
                mode = "sample (rate-limited)" if _ecos_client.api_key == "sample" else "authenticated"
                logger.info(f"[ECOS] BOKECOSClient initialized in {mode} mode")
    return _ecos_client


def fetch_indicator_history(start_date: str, price_db: Optional[StockPriceDB] = None,
                            freshness_days: int = 1) -> pd.DataFrame:
    """Download 8 global indicator tickers in parallel, return single DataFrame.

    Returns: DataFrame with DatetimeIndex and columns = _INDICATOR_TICKERS.values()
    """
    def _fetch_one(ticker: str, col_name: str):
        # ── ECOS-only path (BOK ECOS API, no yfinance/FDR) ──────────────────
        if ticker.startswith("ECOS:"):
            ecos_key = ticker.split("ECOS:", 1)[1]
            meta = ECOS_ITEM_MAP.get(ecos_key)
            if meta is None:
                logger.warning(f"[ECOS] Unknown ECOS key: {ecos_key}")
                return (col_name, pd.Series(dtype=float))
            try:
                client = _get_ecos_client()
                df_ecos = client.fetch_statistic(
                    stat_code=meta["stat_code"],
                    item_code=meta["item_code"],
                    cycle=meta["cycle"],
                    start_date=start_date.replace("-", ""),
                )
                if not df_ecos.empty:
                    s = df_ecos.set_index("Date")["Value"].sort_index()
                    s.index = pd.to_datetime(s.index)
                    logger.info(f"[ECOS] {meta['name']} fetched via BOK ECOS ({len(s)} rows)")
                    return (col_name, s.ffill())
            except Exception as e:
                logger.warning(f"[ECOS] Fetch failed for {ticker}: {e}")
            return (col_name, pd.Series(dtype=float))

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
                # ^TNX, ^IRX: yfinance reports yield × 10 (e.g. 4.25% → Close=42.5, 1.2% → Close=12.0)
                # FRED / ECOS report actual percentage (e.g. 3.50% → Close=3.5)
                raw_yield = df['Close'].ffill()
                if ticker.startswith('^TNX') or ticker.startswith('^IRX'):
                    scaled = raw_yield / 10.0
                elif (raw_yield.median() > 10.0) if not raw_yield.empty else False:
                    scaled = raw_yield / 10.0
                else:
                    scaled = raw_yield
                return (col_name, scaled.fillna(float('nan')))
            elif col_name in ('kr_base_rate', 'kr_cd91d', 'kr3y'):
                # ECOS / FRED Korea interest rates: already in real % (e.g. 3.5)
                return (col_name, df['Close'].ffill().fillna(float('nan')))
            elif col_name == 'kr_m2_supply':
                # M2 in 십억원; return level (not pct_change) for regime use
                return (col_name, df['Close'].ffill().fillna(float('nan')))
            else:
                return (col_name, df['Close'].ffill().fillna(float('nan')))
        return (col_name, pd.Series(dtype=float))


    # Merge standard tickers + ECOS-only tickers for unified parallel fetch
    _all_tickers = {**_INDICATOR_TICKERS, **_ECOS_ONLY_TICKERS}

    combined = {}
    with ThreadPoolExecutor(max_workers=min(_IO_WORKERS, max(1, len(_all_tickers)))) as pool:
        futures = {pool.submit(_fetch_one, t, c): c for t, c in _all_tickers.items()}
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

    # ⑤ ECOS 기준금리 기반 파생 지표
    # (kr10y - kr_base_rate): 시장 장기금리 vs 정책금리 괴리 → 긴축/완화 사이클 포착
    if 'kr10y' in result.columns and 'kr_base_rate' in result.columns:
        result['kr_term_premium'] = result['kr10y'] - result['kr_base_rate']

    # (kr_cd91d - kr_base_rate): 단기 신용 스프레드 → 유동성 긴축 조기 경보
    if 'kr_cd91d' in result.columns and 'kr_base_rate' in result.columns:
        result['kr_cd_base_spread'] = result['kr_cd91d'] - result['kr_base_rate']

    # M2 전월 대비 변화율: 통화 팽창/수축 방향성 신호
    if 'kr_m2_supply' in result.columns:
        result['kr_m2_mom'] = result['kr_m2_supply'].pct_change(fill_method=None).fillna(0.0) * 100


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

    # Forward-fill to handle staggered market hours; fill initial warmup NaNs with neutral 0.0 (no backward lookahead)
    result = result.ffill().fillna(0.0)

    logger.info(f"Fetched indicator history: {len(result)} rows x {len(result.columns)} cols")
    return result



def _get_target_markets_to_save(df: pd.DataFrame = None, universe: pd.DataFrame = None) -> list[str]:
    """Return all unique market identifiers to save individual reports for."""
    markets = set()
    if df is not None and not df.empty and 'market' in df.columns:
        markets.update(df['market'].dropna().unique())
    if universe is not None and not universe.empty and 'market' in universe.columns:
        markets.update(universe['market'].dropna().unique())
    target_env = os.environ.get("INFERENCE_TARGET", "").strip().upper()
    if target_env:
        for t in target_env.split(','):
            t_clean = t.strip()
            if t_clean and t_clean not in ['ALL', 'CORE_5', 'ASIA_DEV', 'ASIA_EMG', 'COMMODITY']:
                markets.add(t_clean)
    if not markets:
        markets = {'KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'}
    return sorted(markets)


def _market_symbols(universe: pd.DataFrame) -> dict:
    """Return dict of {market: set(symbols)} for all known markets."""
    markets = {}
    if universe is not None and not universe.empty:
        if 'market' not in universe.columns:
            universe['market'] = universe['symbol'].map(lambda s: 'KOSPI' if str(s).isdigit() else 'SP500')
        all_mkts = sorted(set(universe['market'].dropna().unique()) | {'KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'})
        for m in all_mkts:
            markets[m] = set(universe[universe['market'] == m]['symbol'])
    else:
        for m in ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']:
            markets[m] = set()
    return markets

def _fmt_top(df: pd.DataFrame, horizon: int, symbol_to_name: dict, symbol_to_market: dict, count: int = 10) -> list:
    """Format top-N predictions for a single market segment."""
    lines = []
    for rank, row in enumerate(df.head(count).itertuples(index=False), 1):
        r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(df.columns, row))
        sym = r_dict.get('symbol', '')
        raw_ret = r_dict.get(horizon, 0.0)
        ret = float(raw_ret) * 100 if pd.notna(raw_ret) else 0.0
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
    active_markets = [m for m, syms in market_syms.items() if syms]
    if not active_markets:
        active_markets = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']
    for h in horizons:
        if h not in res_df.columns:
            continue
        sorted_df = res_df.sort_values(by=h, ascending=False)

        for m in active_markets:
            m_df = sorted_df[sorted_df['symbol'].isin(market_syms.get(m, set()))]
            if not m_df.empty:
                lines.append(f"\n*{h}일 예상수익률 — {m} TOP 10*")
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
    except Exception as e:
        logger.warning(f"Error checking excluded KRX symbols: {e}")
    return excluded


class _PipelineContext:
    storage: Optional[Any] = None
    price_db: Optional[Any] = None
    current_run_id: Optional[str] = None
    start_time: float = 0.0

_ACTIVE_PIPELINE_CTX = _PipelineContext()


def execute_prediction_pipeline():
    _pipeline_start_time = time.time()
    _ACTIVE_PIPELINE_CTX.start_time = _pipeline_start_time
    _ACTIVE_PIPELINE_CTX.storage = None
    _ACTIVE_PIPELINE_CTX.price_db = None
    _ACTIVE_PIPELINE_CTX.current_run_id = None
    logger.info("Starting consolidated market indicator and prediction pipeline...")

    try:
        return _execute_prediction_pipeline_core(_pipeline_start_time)
    except Exception as _pipe_err:
        ctx = _ACTIVE_PIPELINE_CTX
        if ctx.current_run_id and ctx.storage is not None:
            try:
                dur_secs = time.time() - _pipeline_start_time
                ctx.storage.finish_pipeline_run(
                    run_id=ctx.current_run_id,
                    status="FAILED",
                    duration_seconds=dur_secs,
                    error_summary=str(_pipe_err)[:500]
                )
            except Exception as _finish_err:
                logger.error(f"Failed to record pipeline failure status in storage: {_finish_err}")
        raise
    finally:
        ctx = _ACTIVE_PIPELINE_CTX
        try:
            if hasattr(ctx.price_db, 'close') and ctx.price_db is not None:
                ctx.price_db.close()
            if hasattr(ctx.storage, 'close') and ctx.storage is not None:
                ctx.storage.close()
        except Exception as e:
            logger.debug(f"DB close during pipeline cleanup: {e}")


def _execute_prediction_pipeline_core(_pipeline_start_time: float):
    # Ensure result directory exists early
    result_dir = os.environ.get("OUTPUT_RESULT_DIR", os.path.join(os.path.dirname(__file__), "result"))
    os.makedirs(result_dir, exist_ok=True)

    # 1. Load configurations from TradingConfig (.env)
    cfg = TradingConfig()
    cfg.validate()
    logger.info(f"Loaded config: DB={cfg.db_path}, Broker={cfg.broker_type}, Mock Trading={cfg.mock_trading}, ResultDir={result_dir}")

    # Auto-download GitHub DB cache if configured
    if os.environ.get("DOWNLOAD_DB_FROM_GITHUB", "false").lower() == "true":
        try:
            from download_db import download_github_databases
            download_github_databases()
        except Exception as e:
            logger.warning(f"Failed to auto-download GitHub database cache: {e}")

    # 2. Fetch current global market indicators
    logger.info("Fetching global market indicators...")
    storage = MarketIndicatorStorage(db_path=cfg.db_path)
    _ACTIVE_PIPELINE_CTX.storage = storage

    # Initialize Run History tracking
    _git_sha = os.environ.get("GITHUB_SHA", "")
    _trigger_type = os.environ.get("GITHUB_EVENT_NAME", "manual")
    current_run_id = storage.start_pipeline_run(trigger_type=_trigger_type, git_sha=_git_sha)
    _ACTIVE_PIPELINE_CTX.current_run_id = current_run_id
    previous_run_id = storage.get_previous_run_id(current_run_id)
    logger.info(f"[RUN HISTORY] Registered current_run_id={current_run_id} (previous_run_id={previous_run_id or 'None'})")

    try:
        market_client = GlobalMarketClient()
        market_summary = market_client.get_summary()
    except Exception as e:
        logger.error(f"Failed to fetch global market indicators: {e}. Falling back to DB cache.")
        market_summary = storage.get_latest_global_indicators()

    # 3. Store indicators
    from datetime import timezone, timedelta
    KST = timezone(timedelta(hours=9))
    date_str = datetime.now(KST).strftime('%Y-%m-%d')
    with storage.pipeline_stage("global_indicators"):
        storage.save_indicators(market_summary, date_str)
    logger.info("Saved market indicators to database.")

    # 4. Update stock universe if needed
    universe = storage.get_universe()
    force_universe_refresh = os.environ.get("FORCE_UNIVERSE_REFRESH", "false").lower() == "true"
    if universe.empty or force_universe_refresh:
        logger.info(
            "Syncing stock universe (%s)...",
            "FORCE_UNIVERSE_REFRESH is set" if force_universe_refresh else "universe is empty",
        )
        storage.update_stock_universe()
        universe = storage.get_universe()
    logger.info(f"Loaded {len(universe)} symbols from universe.")
    if 'market' not in universe.columns:
        universe['market'] = universe['symbol'].map(lambda s: 'KOSPI' if str(s).isdigit() else 'SP500')

    # Enforce active global markets (US, KR, CN, JP, IN, EU, VN, TW, AU, BR, HK, SG, CA)
    valid_markets = {
        'KOSPI', 'KOSDAQ', 'KRX',
        'SP500', 'NASDAQ', 'RUSSELL2000', 'NYSE', 'AMEX', 'US',
        'CHINA_SSE', 'CHINA_SZSE', 'SSE', 'SZSE', 'CHINA',
        'JAPAN_TSE', 'TSE', 'JAPAN',
        'INDIA_NSE', 'INDIA_BSE', 'NSE', 'BSE', 'INDIA',
        'EUROPE_STOXX', 'EUROPE', 'STOXX', 'DAX', 'FTSE', 'CAC',
        'VIETNAM_HOSE', 'HOSE', 'VIETNAM',
        'TAIWAN_TWSE', 'TWSE', 'TAIWAN',
        'AUSTRALIA_ASX', 'ASX', 'AUSTRALIA',
        'BRAZIL_B3', 'B3', 'BRAZIL',
        'HKEX', 'HONGKONG',
        'SINGAPORE_SGX', 'SGX', 'SINGAPORE',
        'CANADA_TSX', 'TSX', 'CANADA',
    }
    universe = universe[universe['market'].astype(str).str.upper().isin(valid_markets)]

    # Single-market or regional pipeline runs (GHA matrix / CLI target)
    _target_env_raw = os.environ.get("INFERENCE_TARGET", "").strip().upper()
    if _target_env_raw:
        _targets = [t.strip() for t in _target_env_raw.split(",") if t.strip()]
        _allowed_markets: list[str] = []
        for _t in _targets:
            if _t in ("ALL", "GLOBAL"):
                _allowed_markets.extend(valid_markets)
            elif _t in ("CORE_5", "CORE5"):
                _allowed_markets.extend(("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"))
            elif _t == "SP500":
                _allowed_markets.append("SP500")
            elif _t == "NASDAQ":
                _allowed_markets.append("NASDAQ")
            elif _t in ("RUSSELL2000", "RUSSELL"):
                _allowed_markets.append("RUSSELL2000")
            elif _t == "KOSPI":
                _allowed_markets.append("KOSPI")
            elif _t == "KOSDAQ":
                _allowed_markets.append("KOSDAQ")
            elif _t == "KRX":
                _allowed_markets.extend(("KOSPI", "KOSDAQ"))
            elif _t in ("CHINA", "CN"):
                _allowed_markets.extend(("CHINA_SSE", "CHINA_SZSE", "SSE", "SZSE"))
            elif _t in ("JAPAN", "JP"):
                _allowed_markets.extend(("JAPAN_TSE", "TSE"))
            elif _t in ("INDIA", "IN"):
                _allowed_markets.extend(("INDIA_NSE", "INDIA_BSE", "NSE", "BSE"))
            elif _t in ("EUROPE", "EU"):
                _allowed_markets.extend(("EUROPE_STOXX", "STOXX", "DAX", "FTSE", "CAC"))
            elif _t in ("VIETNAM", "VN"):
                _allowed_markets.extend(("VIETNAM_HOSE", "HOSE"))
            elif _t in ("TAIWAN", "TW"):
                _allowed_markets.extend(("TAIWAN_TWSE", "TWSE"))
            elif _t in ("AUSTRALIA", "AU"):
                _allowed_markets.extend(("AUSTRALIA_ASX", "ASX"))
            elif _t in ("BRAZIL", "BR"):
                _allowed_markets.extend(("BRAZIL_B3", "B3"))
            elif _t in ("HONGKONG", "HK", "HKEX"):
                _allowed_markets.append("HKEX")
            elif _t in ("SINGAPORE", "SG"):
                _allowed_markets.extend(("SINGAPORE_SGX", "SGX"))
            elif _t in ("CANADA", "CA"):
                _allowed_markets.extend(("CANADA_TSX", "TSX"))
            elif _t == "ASIA_DEV":
                _allowed_markets.extend(("JAPAN_TSE", "TSE", "TAIWAN_TWSE", "TWSE", "HKEX", "SINGAPORE_SGX", "SGX"))
            elif _t == "ASIA_EMG":
                _allowed_markets.extend(("CHINA_SSE", "CHINA_SZSE", "SSE", "SZSE", "INDIA_NSE", "NSE", "VIETNAM_HOSE", "HOSE"))
            elif _t == "COMMODITY":
                _allowed_markets.extend(("AUSTRALIA_ASX", "ASX", "BRAZIL_B3", "B3", "CANADA_TSX", "TSX"))
            elif _t in valid_markets:
                _allowed_markets.append(_t)
        if _allowed_markets:
            _allowed_set = set(_allowed_markets)
            _filtered = universe[universe['market'].astype(str).str.upper().isin(_allowed_set)]
            if not _filtered.empty:
                logger.info(f"INFERENCE_TARGET={_target_env_raw}: universe restricted to {len(_filtered)} symbols ({sorted(_allowed_set)}).")
                universe = _filtered
            else:
                logger.warning(
                    f"INFERENCE_TARGET={_target_env_raw}: no symbols matched markets {sorted(_allowed_set)}; "
                    "falling back to the full universe."
                )

    # Build symbol→market mapping for adjusted price fetching
    symbol_market = dict(zip(universe['symbol'], universe['market']))

    def _bg_fundamentals(syms, label):
        logger.info(f"[BG] Fetching fundamentals for {label} ({len(syms)} symbols)...")
        try:
            u_shares_map = dict(zip(universe['symbol'], universe['shares_outstanding'])) if (universe is not None and not universe.empty and 'shares_outstanding' in universe.columns) else None
            fetch_and_store_fundamentals_batch(syms, symbol_market, storage, shares_map=u_shares_map)
            logger.info(f"[BG] Fundamentals fetch complete for {label}")
        except Exception as e:
            logger.warning(f"[BG] Fundamentals fetch failed for {label}: {e}")

    # StockPriceDB 캐시 초기화
    price_db = StockPriceDB(db_path=cfg.stock_price_db_path)
    _ACTIVE_PIPELINE_CTX.price_db = price_db
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
        logger.info("SKIP_TRAINING is active. Checking for existing models on disk via ModelCacheManager...")
        from src.ai.model_cache import ModelCacheManager
        cache_mgr = ModelCacheManager.get_instance()
        cache_health = cache_mgr.validate_cache_health(
            model_dir=str(model.model_dir),
            required_markets=['sp500', 'nasdaq', 'russell2000', 'kospi', 'kosdaq'],
            max_age_days=getattr(cfg, 'model_cache_max_age_days', 7),
            verify_checksum=getattr(cfg, 'model_cache_verify_checksum', True),
            expected_features=getattr(model, 'ALL_FEATURES', None),
        )
        logger.info(
            f"[ModelCacheManager] Cache health: valid={cache_health.get('valid_models_count')}, "
            f"stale={cache_health.get('stale_models_count')}, corrupted={cache_health.get('corrupted_models_count')}, "
            f"ready={cache_health.get('is_fully_ready')}"
        )

        model.load_models()
        model.load_surge_models()
        model.load_lead_lag()
        vcp_ml = VCPSurgePredictor(model_dir=str(model.model_dir))
        vcp_ml.load_models()

        # Verify that models are actually loaded for regression, surge, and VCP ML
        regression_loaded = any(len(mkt_dict) > 0 for mkt_dict in model.models.values()) or any(len(mkt_dict) > 0 for mkt_dict in model.lgb_models.values())
        surge_loaded = any(len(mkt_dict) > 0 for mkt_dict in model.surge_models.values())
        vcp_loaded = any(len(mkt_dict) > 0 for mkt_dict in vcp_ml.models.values()) or any(len(mkt_dict) > 0 for mkt_dict in vcp_ml.lgb_models.values())

        # PRESEED_MODE: data-cache-only runs (e.g. preseed.yml) must NEVER trigger
        # a full training pass when the model cache is empty — that would turn the
        # daily preseed into a 6-hour training job and blow the timeout.
        if os.environ.get("PRESEED_MODE", "false").lower() == "true":
            logger.info("PRESEED_MODE active: forcing skip training (cache-only data run).")
            should_skip = True
        elif os.environ.get("SKIP_TRAINING", "").lower() in ("true", "1", "yes"):
            logger.info("SKIP_TRAINING environment variable is explicitly set. Forcing skip training phase for inference run.")
            should_skip = True
        elif regression_loaded or surge_loaded or vcp_loaded:
            logger.info("Pre-trained models found on disk. Skipping model training phase.")
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

    # Safety: initialise df_train to empty so it is always bound regardless of
    # which code path is taken below (prevents UnboundLocalError if an exception
    # occurs inside the else-branch before the assignment at prepare_training_data).
    df_train = pd.DataFrame()
    market_dfs: dict = {m: pd.DataFrame() for m in ['sp500', 'nasdaq', 'russell2000', 'kospi', 'kosdaq']}

    if should_skip:
        logger.info("Fetching global indicator history for inference only...")
        indicator_infer = fetch_indicator_history(start_date_infer, price_db, freshness)
        train_data_dict: dict[str, Any] = {}
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

        def _stratified_sample(population, k, universe_df=None):
            if not population or k <= 0:
                return []
            if k >= len(population):
                return list(population)
            if universe_df is not None and not universe_df.empty and 'symbol' in universe_df.columns:
                sub_univ = universe_df[universe_df['symbol'].isin(population)]
                strat_col = 'sector' if ('sector' in sub_univ.columns and sub_univ['sector'].notna().sum() > 0) else ('market' if 'market' in sub_univ.columns else None)
                if strat_col:
                    groups = sub_univ.groupby(strat_col)['symbol'].apply(list).to_dict()
                    sampled = []
                    total_pop = len(population)
                    for grp, grp_syms in groups.items():
                        grp_k = max(1, round(k * len(grp_syms) / total_pop))
                        sampled.extend(random.sample(grp_syms, min(grp_k, len(grp_syms))))
                    if len(sampled) > k:
                        sampled = random.sample(sampled, k)
                    elif len(sampled) < k:
                        remaining = [s for s in population if s not in set(sampled)]
                        if remaining:
                            sampled.extend(random.sample(remaining, min(k - len(sampled), len(remaining))))
                    return sampled
            return random.sample(population, k)

        train_krx_overall = _stratified_sample(active_krx_symbols, krx_sample, universe_df=universe) if active_krx_symbols else []
        train_krx_set = set(train_krx_overall)
        train_us_overall = _stratified_sample(active_us_symbols, sp500_sample, universe_df=universe) if active_us_symbols else []
        train_symbols = train_us_overall + train_krx_overall

        # Per-market breakdown for training (preserve market proportions)
        train_sp500 = [s for s in train_symbols if s in sp500_symbols]
        train_nasdaq = [s for s in train_symbols if s in nasdaq_symbols]
        train_russell = [s for s in train_symbols if s in russell_symbols]
        train_kospi = [s for s in train_krx_set if s in kospi_symbols]
        train_kosdaq = [s for s in train_krx_set if s in kosdaq_symbols]

        # 6. Fetch corporate fundamentals in background (non-blocking)
        if train_symbols:
            t = threading.Thread(target=_bg_fundamentals, args=(train_symbols, "training"), daemon=True)
            t.start()

        # Prefetch training data in batches to optimize performance
        prefetch_prices_batch(train_symbols, symbol_market, start_date_train, price_db, freshness)

        logger.info(f"Fetching training data for {len(train_symbols)} sampled symbols (update_interval={update_interval}s)...")
        train_data_dict = {}

        with ThreadPoolExecutor(max_workers=_IO_WORKERS) as executor:
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
                            f64_cols = df.select_dtypes(include=['float64']).columns
                            if len(f64_cols) > 0:
                                df[f64_cols] = df[f64_cols].astype(np.float32)
                            train_data_dict[sym] = df
                    except TimeoutError:
                        logger.warning(f"[{done_count+1}/{len(train_symbols)}] Skipping {sym}: timeout (>={_PER_SYMBOL_TIMEOUT}s)")
                        future.cancel()
                    except Exception as e:
                        logger.debug(f"Skipping {sym}: {e}")
                    done_count += 1
                    pbar.update(1)
                    pbar.set_postfix({"loaded": len(train_data_dict), "sym": sym[:10]})
                    if done_count % 100 == 0:
                        logger.info(f"Training data fetch progress: {done_count}/{len(train_symbols)} ({len(train_data_dict)} loaded)")

            executor.shutdown(wait=False, cancel_futures=True)

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

        # Merge fundamentals
        def _merge_sym(sym, df):
            try:
                return sym, model.merge_fundamentals(sym, df, storage, fundamentals_cache=train_fund_cache)
            except Exception as e:
                logger.debug(f"Failed to merge fundamentals for {sym}: {e}")
                return sym, None

        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
            futures = {pool.submit(_merge_sym, sym, train_data_dict[sym]): sym for sym in list(train_data_dict.keys())}
            for future in as_completed(futures):
                sym = futures[future]
                merged = future.result()
                if merged[1] is not None:
                    m_df = merged[1]
                    f64_cols = m_df.select_dtypes(include=['float64']).columns
                    if len(f64_cols) > 0:
                        m_df[f64_cols] = m_df[f64_cols].astype(np.float32)
                    train_data_dict[sym] = m_df
                else:
                    train_data_dict.pop(sym, None)

        try:
            df_train = model.prepare_training_data(train_data_dict, indicator_train, storage=storage)
        except Exception as _e:
            logger.error(f"prepare_training_data failed: {_e}. Proceeding with empty df_train.")
            df_train = pd.DataFrame()

        # [Moved] 7d. Train VCP ML surge models before XGBoost to release memory
        vcp_ml = VCPSurgePredictor(model_dir=str(model.model_dir))
        if 'train_data_dict' in locals() and train_data_dict:
            try:
                logger.info("Training VCP ML surge models across markets...")
                vcp_ml.train(train_data_dict, indicator_train, universe)
                vcp_ml.save_models()
                logger.info("VCP ML surge models trained and saved successfully.")
            except Exception as _vcp_err:
                logger.error(f"VCP ML training failed: {_vcp_err}")
                _notify_telegram(f"⚠️ VCP ML 모델 학습 실패: {_vcp_err}")
            del train_data_dict
            gc.collect()

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
        # Limit worker count to min(4, _CPU_WORKERS) to prevent XGBoost thread oversubscription.
        # Dynamically compute intra_n_jobs per worker to eliminate OpenMP thread thrashing.
        _train_workers = max(1, min(4, _CPU_WORKERS))
        _intra_n_jobs = max(1, _CPU_WORKERS // _train_workers)
        logger.info(f"ML Parallel Training: {_train_workers} market workers with intra_n_jobs={_intra_n_jobs} per model")

        with storage.pipeline_stage("train_regression"):
            _train_failures = []
            with ThreadPoolExecutor(max_workers=_train_workers) as pool:
                futures = {}
                for m_name, m_df in market_dfs.items():
                    if not m_df.empty:
                        logger.info(f"Training {m_name.upper()} regression model ({len(m_df)} rows, intra_n_jobs={_intra_n_jobs})...")
                        futures[pool.submit(model.train, m_df, market=m_name, save_after=True, n_jobs=_intra_n_jobs)] = m_name
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        logger.error(f"Regression training failed for {futures[fut]}: {e}")
                        _train_failures.append(f"{futures[fut]}: {e}")
            if _train_failures:
                _notify_telegram(f"⚠️ 회귀 모델 학습 실패 ({len(_train_failures)}/{len(market_dfs)}): " + " | ".join(_train_failures[:5]))
        model.load_models()

        with storage.pipeline_stage("train_surge"):
            _surge_failures = []
            with ThreadPoolExecutor(max_workers=_train_workers) as pool:
                futures = {}
                for m_name, m_df in market_dfs.items():
                    if not m_df.empty:
                        futures[pool.submit(model.train_surge, m_df, market=m_name, save_after=True, n_jobs=_intra_n_jobs)] = m_name
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as e:
                        logger.error(f"Surge training failed for {futures[fut]}: {e}")
                        _surge_failures.append(f"{futures[fut]}: {e}")
            if _surge_failures:
                _notify_telegram(f"⚠️ Surge 모델 학습 실패 ({len(_surge_failures)}/{len(market_dfs)}): " + " | ".join(_surge_failures[:5]))
        model.load_surge_models()

        # 7c. Compute lead-lag correlation matrix (which stocks follow which)
        with storage.pipeline_stage("train_lead_lag_vcp"):
            if not df_train.empty and len(df_train) > 1000:
                model.compute_lead_lag(df_train, indicator_df=indicator_train, symbol_to_market=symbol_market)
        
        # 7e. Fit Isotonic Regression calibrators on training data for score alignment
        if not df_train.empty and 'Close' in df_train.columns:
            try:
                import joblib
                scorer_calib = EnsembleScoringEngine(config=cfg)
                logger.info("Fitting Isotonic Regression calibrators on training dataset...")
                df_calib_base = df_train.copy()
                if 'date' in df_calib_base.columns:
                    df_calib_base = df_calib_base.sort_values('date')
                
                # Split chronologically to avoid overfitting calibrator on same data
                split_idx = int(len(df_calib_base) * 0.8)
                df_calib_base = df_calib_base.iloc[split_idx:].copy()
                
                df_calib_base['future_return_20d'] = df_calib_base.groupby('symbol')['Close'].transform(lambda x: x.shift(-20) / x.replace(0, np.nan) - 1)
                valid_calib_df = df_calib_base.dropna(subset=['future_return_20d'])
                if len(valid_calib_df) > 200 and 'symbol' in valid_calib_df.columns:
                    holdout_symbols = valid_calib_df['symbol'].unique()
                    # Feed full historical time-series per symbol to compute indicators cleanly
                    _val_dict = {sym: grp for sym, grp in df_calib_base[df_calib_base['symbol'].isin(holdout_symbols)].groupby('symbol')}
                    if _val_dict:
                        reg_preds, surge_preds = model.predict_all(
                            _val_dict, indicator_train, symbol_market,
                            storage=storage, fundamentals_cache=train_fund_cache if 'train_fund_cache' in locals() else None)
                    else:
                        reg_preds, surge_preds = pd.DataFrame(), pd.DataFrame()
                    
                    val_holdout_latest = valid_calib_df.groupby('symbol').last().reset_index()
                    common_syms = [s for s in val_holdout_latest['symbol'] if s in reg_preds.index and s in surge_preds.index] if not reg_preds.empty and not surge_preds.empty else []
                    if len(common_syms) >= 20:
                        y_eval_df = val_holdout_latest.set_index('symbol').loc[common_syms]
                        y_true = (y_eval_df['future_return_20d'] >= 0.15).astype(float).values
                        calib_scores = {
                            'regression': reg_preds.loc[common_syms].get(20, pd.Series(0.5, index=common_syms)).values,
                            'surge': surge_preds.loc[common_syms].get('surge_20d', pd.Series(0.5, index=common_syms)).values,
                        }
                        scorer_calib.fit_calibrators(calib_scores, y_true)
                        calib_path = Path(model.model_dir) / "calibrators.pkl"
                        joblib.dump(scorer_calib._calibrators, str(calib_path))
                        logger.info(f"Fitted and saved Isotonic calibrators on out-of-sample holdout ({len(common_syms)} symbols) to {calib_path}")
            except Exception as _calib_e:
                logger.warning(f"Isotonic calibration fitting skipped: {_calib_e}")
        del df_train
        gc.collect()

    # 8. Fetch fundamentals for all inference symbols (non-blocking background)
    # Universe has already been filtered by INFERENCE_TARGET at the beginning of the pipeline.
    # Derive all_symbols directly from the active universe to support all 16 global markets
    # (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ, CHINA, JAPAN, INDIA, EUROPE, VIETNAM, TAIWAN, AUSTRALIA, BRAZIL, HKEX, SINGAPORE, CANADA).
    all_symbols = universe['symbol'].tolist() if not universe.empty else []
    if not all_symbols:
        logger.warning("Active universe symbol list is empty. Falling back to default symbols.")
        all_symbols = sp500_symbols + nasdaq_symbols + russell_symbols + krx_symbols

    # Exclude halted (거래정지) and administrative (관리종목) KRX stocks from all predictions
    excluded_krx = _get_excluded_krx_symbols()
    if excluded_krx:
        before = len(all_symbols)
        all_symbols = [s for s in all_symbols if s not in excluded_krx]
        logger.info(f"Excluded {before - len(all_symbols)} halted/admin KRX stocks from inference")

    if cfg.debug_mode:
        debug_symbols = []
        for mkt, grp in universe.groupby('market'):
            active_m = [s for s in grp['symbol'].tolist() if s in all_symbols]
            debug_symbols.extend(active_m[:3])
        if debug_symbols:
            all_symbols = debug_symbols
        logger.info(f"[DEBUG MODE] Sampled {len(all_symbols)} symbols across {len(set(universe['market']))} markets for fast pipeline dry run")

    # Do not start inference fundamentals thread when skipping inference
    # (avoids orphaned non-daemon thread that would keep the process alive after early return)
    t2 = None
    if all_symbols and not cfg.skip_inference:
        t2 = threading.Thread(target=_bg_fundamentals, args=(all_symbols, "inference"), daemon=True)
        t2.start()

    # Prefetch inference data in batches to optimize performance
    prefetch_prices_batch(all_symbols, symbol_market, start_date_infer, price_db, freshness)

    # 9. Fetch recent data for ALL symbols to run inference
    logger.info(f"Fetching inference data for ALL {len(all_symbols)} symbols (update_interval={update_interval}s)...")
    infer_data_dict = {}
    with ThreadPoolExecutor(max_workers=_IO_WORKERS) as executor:
        future_to_sym = {}
        for sym in all_symbols:
            sym_market = symbol_market.get(sym, 'SP500')
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
                        f64_cols = df.select_dtypes(include=['float64']).columns
                        if len(f64_cols) > 0:
                            df[f64_cols] = df[f64_cols].astype(np.float32)
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
        try:
            storage.close()
            price_db.close()
        except Exception:
            pass
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
        for fut in as_completed(futures):
            sym, merged = fut.result()
            if merged is not None:
                f64_cols = merged.select_dtypes(include=['float64']).columns
                if len(f64_cols) > 0:
                    merged[f64_cols] = merged[f64_cols].astype(np.float32)
                infer_data_dict[sym] = merged
            else:
                infer_data_dict.pop(sym, None)

    # 10. Run predictions (regression + surge, shared feature computation)
    logger.info("Running inference (regression + surge)...")
    symbol_to_market_lower = {sym: mkt.lower() for sym, mkt in symbol_market.items()}
    with storage.pipeline_stage("inference_regression_surge"):
        res_df, surge_df = model.predict_all(infer_data_dict, indicator_infer, symbol_to_market_lower, storage=storage, fundamentals_cache=infer_fund_cache)

    if res_df.empty:
        # Live-money guard: a completely empty inference day must FAIL loudly.
        # Previously this returned (None, None) and __main__ still sent a
        # "pipeline complete" Telegram SUCCESS, publishing an empty release.
        raise RuntimeError(
            "Inference produced NO predictions (empty result). Aborting pipeline - "
            "refusing to publish an empty prediction day."
        )
    logger.info(f"Regression: {len(res_df)} symbols, Surge: {len(surge_df) if not surge_df.empty else 0} symbols")
    if surge_df is None or surge_df.empty:
        logger.warning("Surge predictions are empty - surge strategy will be inactive this run.")

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
        except Exception as e:
            logger.debug(f"VCP detection failed for {sym}: {e}")
        return None

    vcp_results = []
    with ThreadPoolExecutor(max_workers=_CPU_WORKERS * 2) as pool:
        futures = {pool.submit(_detect_vcp, sym, df): sym for sym, df in infer_data_dict.items()}
        for fut in as_completed(futures):
            try:
                r = fut.result()
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

        pred_limit = _get_effective_limit(cfg)
        valid_stat_arb_pairs = list(stat_arb_pairs) if stat_arb_pairs else []
        valid_stat_arb_pairs.sort(key=lambda x: abs(x.get('z_score', 0.0)), reverse=True)
        top_stat_arb_pairs = _slice_top_list(valid_stat_arb_pairs, pred_limit if _is_all_limit(pred_limit) else 200)

        def _write_stat_arb_file(f_out, pairs_list):
            f_out.write("=== Statistical Arbitrage Pairs & Signals ===\n")
            f_out.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f_out.write(f"Total cointegrated pairs found: {len(pairs_list)}\n\n")
            if not pairs_list:
                f_out.write("데이터 없음 (유의미한 공적분 페어 미발견)\n")
                return
            f_out.write(f"{'Pair':<25}{'Z-Score':<10}{'Correlation':<15}{'Beta/Hedge':<12}{'Signal':<20}\n")
            f_out.write("-" * 80 + "\n")
            for p in _slice_top_list(pairs_list, pred_limit):
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
        for _m in _get_target_markets_to_save(universe=universe):
            _m_pairs = [p for p in top_stat_arb_pairs if p.get('market') == _m or p['pair'][0] in set(universe[universe['market'] == _m]['symbol'])]
            _mkt_path = os.path.join(result_dir, f"stat_arb_predictions_{_m}.txt")
            with open(_mkt_path, "w", encoding="utf-8") as _mf:
                _write_stat_arb_file(_mf, _m_pairs)
        _written_cnt_str = f"All {len(top_stat_arb_pairs)}" if _is_all_limit(pred_limit) else f"Top {len(top_stat_arb_pairs)}"
        logger.info(f"Saved Statistical Arbitrage pairs (Total: {len(stat_arb_pairs)}, {_written_cnt_str} written) to {stat_arb_output_path}")
    except Exception as _stat_arb_e:
        logger.warning(f"Statistical Arbitrage calculation error: {_stat_arb_e}")


    # 11. Save predictions to DB
    try:
        storage.save_predictions(res_df, date_str)
        logger.info(f"Saved predictions to database table 'ai_predictions' for {date_str}.")
    except Exception as _save_pred_e:
        logger.warning(f"Initial attempt to save predictions to DB failed: {_save_pred_e}. Retrying after 1s...")
        try:
            time.sleep(1.0)
            storage.save_predictions(res_df, date_str)
            logger.info(f"Saved predictions to database on retry for {date_str}.")
        except Exception as _retry_save_e:
            logger.error(f"Permanent error saving predictions to DB for {date_str}: {_retry_save_e}")

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

    decoupling_info = regime_detector.predict_dual_market_regime(indicator_infer)
    us_2d_regime = decoupling_info['us_regime']['combo_2d_label']
    kr_2d_regime = decoupling_info['kr_regime']['combo_2d_label']
    decoupling_status = decoupling_info.get('decoupling_status', 'COUPLED')
    logger.info(f"==> CURRENT MARKET REGIME DETECTED: {current_regime_label} (Code: {current_regime}), 2D: {current_2d_regime} | US: {us_2d_regime}, KR: {kr_2d_regime} ({decoupling_status})")

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
    pred_limit = _get_effective_limit(cfg)
    is_all_pred = _is_all_limit(pred_limit)
    _TOP_N = 100 if is_all_pred else int(pred_limit)
    _HEADER_LABEL = "ALL" if is_all_pred else f"TOP{_TOP_N}"

    def _fmt_pct(row, h) -> str:
        try:
            v = float(row[h])
            if not np.isfinite(v):
                return "n/a"
            return f"{v*100:+.2f}%"
        except Exception:
            return "n/a"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"=== Pipeline Inference Summary ({_HEADER_LABEL} per Market) ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total symbols analyzed: {len(res_df)}\n")
        f.write(f"Showing: {'All' if is_all_pred else f'Top {_TOP_N}'} per market | Horizons: {', '.join(str(h)+'d' for h in _SUMMARY_HORIZONS)}\n")
        f.write("Full data: pipeline_result.csv / pipeline_result.jsonl\n\n")
        if res_df.empty:
            f.write("데이터 없음\n")
        all_pred_mkts = [m for m in _get_target_markets_to_save(universe=universe) if market_syms.get(m)]
        if not all_pred_mkts:
            all_pred_mkts = [m for m, syms in market_syms.items() if syms] or ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']
        for h in _SUMMARY_HORIZONS:
            sorted_df = res_df.sort_values(by=h, ascending=False)
            f.write(f"{'='*60}\n")
            f.write(f"Horizon: {h}d\n\n")
            for m in all_pred_mkts:
                m_set = market_syms.get(m, set())
                m_df = _slice_top_df(sorted_df[sorted_df['symbol'].isin(m_set)], pred_limit)
                if m_df.empty:
                    continue
                f.write(f"--- {m} {'ALL' if is_all_pred else f'TOP {_TOP_N}'} ---\n")
                for rank, (_, row) in enumerate(m_df.iterrows(), 1):
                    name = symbol_to_name.get(row['symbol'], "Unknown")
                    f.write(f"  {rank}. {row['symbol']} ({name}): {_fmt_pct(row, h)}\n")
                f.write("\n")
    logger.info(f"Saved summarized pipeline result ({_HEADER_LABEL}, {len(_SUMMARY_HORIZONS)} horizons) to {output_path}")

    # Per-market suffix files for pipeline_result (Strategy 1 / Regression)
    for _m in _get_target_markets_to_save(universe=universe):
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
                _m_h_sliced = _slice_top_df(_m_h_sorted, pred_limit)
                _mf_sec_title = f"--- {_m} ALL ({len(_m_h_sliced)}) (Horizon: {h}d) ---\n" if is_all_pred else f"--- {_m} TOP {len(_m_h_sliced)} (Horizon: {h}d) ---\n"
                _mf.write(_mf_sec_title)
                for _rank, (_, _row) in enumerate(_m_h_sliced.iterrows(), 1):
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

            all_surge_mkts = _get_target_markets_to_save(df=surge_df, universe=universe)
            for h in model.surge_horizons:
                col = f'surge_{h}d'
                if col not in surge_df.columns:
                    continue
                for m in all_surge_mkts:
                    m_df = surge_df[surge_df['market'] == m].sort_values(by=col, ascending=False)
                    if m_df.empty:
                        continue
                    m_df_sliced = _slice_top_df(m_df, pred_limit)
                    _surge_title = f"[{h}일] {m} All Surge Candidates ({len(m_df_sliced)})\n" if is_all_pred else f"[{h}일] {m} Top {_TOP_N} Surge Candidates\n"
                    f.write(f"{'='*60}\n")
                    f.write(_surge_title)
                    f.write(f"{'='*60}\n")
                    for rank, (_, row) in enumerate(m_df_sliced.iterrows(), 1):
                        name = row.get('name', 'Unknown')
                        prob = row[col] * 100
                        f.write(f"  {rank}. [{m}] {row['symbol']} ({name}): {prob:.1f}%\n")
                    f.write("\n")
    logger.info(f"Saved surge predictions ({len(surge_df)} symbols) to {surge_output_path}")

    # Also save per-market suffix files for surge predictions
    if not surge_df.empty:
        for _m in _get_target_markets_to_save(df=surge_df, universe=universe):
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
                    m_sorted_sliced = _slice_top_df(m_sorted, pred_limit)
                    _mkt_surge_title = f"[{h}일] {_m} All Surge Candidates ({len(m_sorted_sliced)})\n" if is_all_pred else f"[{h}일] {_m} Top {_TOP_N} Surge Candidates\n"
                    _mf.write(f"{'='*60}\n")
                    _mf.write(_mkt_surge_title)
                    _mf.write(f"{'='*60}\n")
                    for rank, (_, row) in enumerate(m_sorted_sliced.iterrows(), 1):
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
            all_ll_mkts = _get_target_markets_to_save(df=lead_lag_df, universe=universe)
            for m in all_ll_mkts:
                m_df = lead_lag_df[lead_lag_df['market'] == m].sort_values(by='lead_lag_score', ascending=False)
                if m_df.empty:
                    continue
                m_df_sliced = _slice_top_df(m_df, pred_limit)
                _ll_title = f"--- {m} All ({len(m_df_sliced)}) ---\n" if is_all_pred else f"--- {m} Top {_TOP_N} ---\n"
                f.write(_ll_title)
                for rank, (_, row) in enumerate(m_df_sliced.iterrows(), 1):
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
        for _m in _get_target_markets_to_save(df=_ll_merged, universe=universe):
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
                _m_df_sliced = _slice_top_df(_m_df, pred_limit)
                _m_ll_title = f"--- {_m} All ({len(_m_df_sliced)}) ---\n" if is_all_pred else f"--- {_m} Top {_TOP_N} ---\n"
                _mf.write(_m_ll_title)
                for _rank, (_, _row) in enumerate(_m_df_sliced.iterrows(), 1):
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
    def _write_vcp_file(f_out, res_list, target_mkt=None):
        f_out.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
        f_out.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f_out.write(f"Total symbols evaluated: {len(res_list)}\n\n")

        all_vcp_mkts = _get_target_markets_to_save(universe=universe)
        mkts = [target_mkt] if target_mkt else all_vcp_mkts
        for m in mkts:
            m_results = [r for r in res_list if vcp_universe_map.get(r['symbol'], ('', ''))[1] == m]
            if not m_results:
                continue
            confirmed = [r for r in m_results if r.get('is_vcp')]
            if confirmed:
                display_list = _slice_top_list(confirmed, pred_limit)
                vcp_title = f"--- {m} All ({len(confirmed)}) (Confirmed VCP Patterns) ---\n" if is_all_pred else f"--- {m} Top {len(display_list)} (Confirmed VCP Patterns) ---\n"
                f_out.write(vcp_title)
            else:
                display_list = _slice_top_list(m_results, pred_limit if is_all_pred else 10)
                vcp_title = f"--- {m} All ({len(m_results)}) VCP Candidates (Strict Pattern Unmet, Score Order) ---\n" if is_all_pred else f"--- {m} Top {len(display_list)} VCP Candidates (Strict Pattern Unmet, Score Order) ---\n"
                f_out.write(vcp_title)

            for rank, r in enumerate(display_list, 1):
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
    for _m in _get_target_markets_to_save(universe=universe):
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

        all_vcp_ml_mkts = _get_target_markets_to_save(df=vcp_ml_df, universe=universe)
        for h in SURGE_HORIZONS:
            for market in all_vcp_ml_mkts:
                if not vcp_ml_df.empty and 'market' in vcp_ml_df.columns and f'vcp_{h}d' in vcp_ml_df.columns:
                    m_df = vcp_ml_df[vcp_ml_df['market'] == market].sort_values(by=f'vcp_{h}d', ascending=False)
                else:
                    m_df = pd.DataFrame()

                if m_df.empty:
                    f.write(f"[{h}일] {market} - (no symbols) 0.0%\n\n")
                    continue
                m_df_sliced = _slice_top_df(m_df, pred_limit)
                vcp_ml_title = f"[{h}일] {market} All ({len(m_df_sliced)})\n" if is_all_pred else f"[{h}일] {market} TOP {len(m_df_sliced)}\n"
                f.write(vcp_ml_title)
                for rank, (_, row) in enumerate(m_df_sliced.iterrows(), 1):
                    name = row.get('name', 'Unknown')
                    prob = row[f'vcp_{h}d'] * 100
                    f.write(f"  {rank}. [{market}] {row['symbol']} ({name}): {prob:.1f}%\n")
                f.write("\n")
    logger.info(f"Saved VCP ML predictions to {vcp_ml_output_path}")

    # Per-market suffix files for VCP ML (Strategy 5)
    for _m in _get_target_markets_to_save(df=vcp_ml_df, universe=universe):
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
                m_df_sliced = _slice_top_df(m_df, pred_limit)
                _vcp_ml_title = f"[{h}일] {_m} All ({len(m_df_sliced)})\n" if is_all_pred else f"[{h}일] {_m} TOP {len(m_df_sliced)}\n"
                _mf.write(_vcp_ml_title)
                for _rank, (_, _row) in enumerate(m_df_sliced.iterrows(), 1):
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
        _proj_dir = os.path.dirname(os.path.abspath(__file__))
        db_path_trade = os.environ.get("TRADE_LOGS_DB_PATH", os.path.normpath(os.path.join(_proj_dir, "..", "trade_logs.db")))
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
                if hasattr(scorer, 'strategy_cols') and isinstance(scorer.strategy_cols, dict):
                    _strategy_cols = dict(scorer.strategy_cols)
                elif hasattr(scorer, 'strategy_cols') and isinstance(scorer.strategy_cols, (list, tuple)):
                    _strategy_cols = dict(scorer.strategy_cols)
                else:
                    try:
                        from src.ai.correlation_monitor import STRATEGY_SCORE_COL_MAP
                        _strategy_cols = dict(STRATEGY_SCORE_COL_MAP)
                    except Exception:
                        _strategy_cols = {
                            'regression': 'reg_score',
                            'surge': 'surge_score',
                            'lead_lag': 'll_score',
                            'vcp_rule': 'vcp_rule_score',
                            'vcp_ml': 'vcp_ml_score',
                            'lstm': 'lstm_score',
                            'stat_arb': 'stat_arb_score',
                            'sector_rotation': 'sector_score',
                            'rim_valuation': 'rim_score',
                            'event_driven': 'event_score',
                            'mq_factor': 'mq_score',
                            'iv_skew': 'iv_skew_score',
                            'order_flow': 'order_flow_score',
                            'short_term_reversal': 'reversal_score',
                            'arm_factor': 'arm_score',
                            'card_factor': 'card_score',
                            'latr_factor': 'latr_score',
                            'inst_foreign_sector': 'inst_foreign_sector_score',
                            'supply_chain': 'supply_chain_score',
                            'sentiment': 'sentiment_score',
                            'factor_neutralized': 'factor_neutralized_score',
                            'vol_target': 'vol_target_score',
                            'microstructure': 'microstructure_score',
                            'accruals_quality': 'accruals_quality_score',
                            'short_squeeze': 'short_squeeze_score',
                            'valueup_catalyst': 'valueup_catalyst_score',
                            'trend_efficiency': 'trend_efficiency_score',
                            'gamma_squeeze': 'gamma_squeeze_score',
                            'insider_buying': 'insider_buying_score',
                            'darkpool': 'darkpool_score',
                            'earnings_tone_drift': 'earnings_tone_drift_score',
                            'cross_asset_spillover': 'cross_asset_spillover_score',
                            'supply_chain_gnn': 'supply_chain_gnn_score',
                            'range_expansion_breakout': 'range_expansion_score',
                            'dual_correction': 'dual_correction_score',
                            'index_rebalance': 'index_rebalance_score',
                            'overnight_gap_reversal': 'overnight_gap_score',
                        }
                _strat_scores = {}
                for _sname, _scol in _strategy_cols.items():
                    if _scol in _hist_df.columns:
                        _strat_scores[_sname] = _hist_df[_scol].values
                _true_labels = _hist_df['outcome_label'].values
                if _strat_scores:
                    scorer.fit_calibrators(_strat_scores, _true_labels)
                    joblib.dump(scorer._calibrators, str(_calibrator_path))
                    logger.info(f"[5-B] Fitted and saved Isotonic calibrators "
                                f"({len(_true_labels)} samples, {len(scorer._calibrators)} strategies) → {_calibrator_path}")
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
        if 'market' in universe.columns and 'symbol' in universe.columns:
            _krx_mask = universe['market'].isin(['KOSPI', 'KOSDAQ']) & universe['symbol'].astype(str).str.isdigit()
            _krx_universe_syms = universe.loc[_krx_mask, 'symbol'].astype(str).tolist()
        else:
            _krx_universe_syms = []
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
                except Exception as _eval_e:
                    logger.debug(f"Sentiment evaluation skipped for {_sym}: {_eval_e}")
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
                for rank, (_, row) in enumerate(_slice_top_df(df_sect, pred_limit).iterrows(), 1):
                    name_str = str(row['name'])[:18] if pd.notna(row['name']) else "Unknown"
                    sec_str = str(row.get('sector', 'General'))[:23]
                    mkt_str = str(row.get('market', 'KRX'))
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<20}{mkt_str:<10}{sec_str:<25}{row['sector_score']*100:>13.1f}%\n")

            with open(sector_output_path, "w", encoding="utf-8") as f:
                _write_sector_file(f, sector_df_merged)
            logger.info(f"Saved sector rotation predictions ({len(sector_df_merged)} symbols) to {sector_output_path}")

            # Per-market suffix files for GHA artifact merge
            for _m in _get_target_markets_to_save(df=sector_df_merged, universe=universe):
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
                    fund_df['date'] = pd.to_datetime(fund_df['date'])
                    if 'date_available' not in fund_df.columns:
                        lag_days = fund_df['symbol'].map(lambda s: 45 if (str(s).isdigit() or str(s).endswith(('.KS', '.KQ'))) else 40)
                        fund_df['date_available'] = fund_df['date'] + pd.to_timedelta(lag_days, unit='D')
                    else:
                        fund_df['date_available'] = pd.to_datetime(fund_df['date_available'])
                    cutoff_date = pd.to_datetime(date_str)
                    fund_df_avail = fund_df[fund_df['date_available'] <= cutoff_date]
                    if fund_df_avail.empty and not fund_df.empty:
                        # Fallback to latest records if statutory filing lag window excludes newly listed or lagged symbols
                        fund_df_avail = fund_df
                    fund_df = fund_df_avail.sort_values('date').groupby('symbol').last().reset_index()

                    # Fallback shares from universe if missing in fundamental data
                    if 'universe' in locals() and universe is not None and not universe.empty:
                        if 'shares_outstanding' in universe.columns:
                            u_shares = universe.set_index('symbol')['shares_outstanding'].to_dict()
                            if 'shares_outstanding' in fund_df.columns:
                                fund_df['shares_outstanding'] = fund_df['shares_outstanding'].replace(0, np.nan).fillna(fund_df['symbol'].map(u_shares)).fillna(0)
                            else:
                                fund_df['shares_outstanding'] = fund_df['symbol'].map(u_shares).fillna(0)

                    # Compute BPS and ROE from genuine fundamentals
                    if 'bps' in fund_df.columns:
                        fund_df['bps'] = pd.to_numeric(fund_df['bps'], errors='coerce').replace([float('inf'), float('-inf'), 0], None)
                        calc_bps = (fund_df['book_value'] / fund_df['shares_outstanding']).replace([float('inf'), float('-inf'), 0], None)
                        fund_df['bps'] = fund_df['bps'].fillna(calc_bps)
                    else:
                        calc_bps = (fund_df['book_value'] / fund_df['shares_outstanding']).replace([float('inf'), float('-inf'), 0], None)
                        fund_df['bps'] = calc_bps

                    if 'roe' in fund_df.columns:
                        fund_df['roe'] = pd.to_numeric(fund_df['roe'], errors='coerce').replace([float('inf'), float('-inf')], None)
                        calc_roe = (fund_df['net_income'] / fund_df['book_value']).replace([float('inf'), float('-inf')], None)
                        fund_df['roe'] = fund_df['roe'].fillna(calc_roe)
                    else:
                        calc_roe = (fund_df['net_income'] / fund_df['book_value']).replace([float('inf'), float('-inf')], None)
                        fund_df['roe'] = calc_roe

                    # Merge into rim_input:
                    # - operating_income/net_income: earnings quality filter
                    # - book_value: normalize_roe() needs book_value for op_income/book_value ratio
                    # - total_debt, cash_equivalents, shares_outstanding: holding-co net-debt deduction
                    merge_cols = ['symbol', 'bps', 'roe', 'operating_income', 'net_income', 'book_value']
                    for _extra_col in ['total_debt', 'cash_equivalents', 'shares_outstanding', 'eps_growth_1y', 'revenue_growth_1y']:
                        if _extra_col in fund_df.columns:
                            merge_cols.append(_extra_col)
                    merge_cols = list(dict.fromkeys(merge_cols))  # deduplicate, preserve order

                    # Cleanly drop existing overlapping columns from df_rim_input before merge to avoid _x/_y suffixes
                    cols_to_merge = [c for c in merge_cols if c in fund_df.columns]
                    for c in cols_to_merge:
                        if c != 'symbol' and c in df_rim_input.columns:
                            df_rim_input = df_rim_input.drop(columns=[c])

                    df_rim_input = df_rim_input.merge(
                        fund_df[cols_to_merge], on='symbol', how='left'
                    )
                    # Pass name for holding-company name-pattern detection (지주·홀딩스 등)
                    if 'name' not in df_rim_input.columns and 'name' in universe.columns:
                        df_rim_input = df_rim_input.merge(universe[['symbol', 'name']], on='symbol', how='left')
                    # Pass sector_code for GICS/KRX holding-company sector classification
                    if 'sector_code' not in df_rim_input.columns and 'sector_code' in universe.columns:
                        df_rim_input = df_rim_input.merge(universe[['symbol', 'sector_code']], on='symbol', how='left')
                    logger.info(f"Merged fundamental BPS/ROE for RIM: {fund_df['bps'].notna().sum()}/{len(df_rim_input)} symbols have BPS")
            except Exception as _fund_e:
                logger.warning(f"Fundamental data merge for RIM skipped: {_fund_e}")
        rim_df = rim_engine.compute_rim_scores(
            df_rim_input,
            symbol_market_map=symbol_market,
            prices_dict=infer_data_dict if ('infer_data_dict' in locals() and infer_data_dict) else None,
            allow_price_proxy=True
        )
        rim_output_path = os.path.join(result_dir, "rim_predictions.txt")
        if not rim_df.empty:
            # Merge name for display (may already be present if 'name' was passed to RIM engine)
            rim_merged = rim_df.merge(universe[['symbol', 'name']], on='symbol', how='left', suffixes=('', '_u'))
            if 'name_u' in rim_merged.columns:
                rim_merged['name'] = rim_merged['name'].fillna(rim_merged.pop('name_u'))
            rim_merged = rim_merged.sort_values(by='rim_score', ascending=False)

            def _write_rim_file(f_out, df_rim):
                f_out.write("=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===\n")
                f_out.write(f"Date: {date_str}\n")
                valid_rim = df_rim[df_rim['rim_score'].notna() & (df_rim['rim_score'] > 0)] if ('rim_score' in df_rim.columns and not df_rim.empty) else pd.DataFrame()
                f_out.write(f"Total symbols evaluated: {len(df_rim)} (Valid: {len(valid_rim)})\n")
                f_out.write("Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount | [PROXY]=Price trend proxy\n\n")

                if valid_rim.empty:
                    f_out.write("데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)\n")
                    return

                f_out.write(
                    f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Market':<10}"
                    f"{'Price':<12}{'Intrinsic V0':<14}{'Discount %':<12}"
                    f"{'ROE_raw':<9}{'ROE_adj':<9}{'EQ':<6}{'Filter':<32}{'RIM Score':<12}\n"
                )
                f_out.write("-" * 142 + "\n")
                for rank, (_, row) in enumerate(_slice_top_df(valid_rim, pred_limit).iterrows(), 1):
                    name_str = str(row.get('name', 'Unknown'))[:18] if pd.notna(row.get('name')) else "Unknown"
                    price_val = row.get('Close', np.nan)
                    price_str = f"{price_val:<12.2f}" if pd.notna(price_val) and np.isfinite(price_val) else f"{'N/A':<12}"

                    intrinsic = row.get('intrinsic_value', np.nan)
                    intrinsic_str = f"{intrinsic:<14.2f}" if pd.notna(intrinsic) and np.isfinite(intrinsic) else f"{'N/A':<14}"

                    disc_val = row.get('discount_ratio', np.nan)
                    disc_str = f"{disc_val*100:>9.1f}%" if pd.notna(disc_val) and np.isfinite(disc_val) else "      N/A"

                    roe_raw = row.get('roe_raw', np.nan)
                    roe_adj = row.get('roe', np.nan)
                    roe_raw_str = f"{roe_raw*100:>7.1f}%" if pd.notna(roe_raw) and np.isfinite(roe_raw) else "    N/A"
                    roe_adj_str = f"{roe_adj*100:>7.1f}%" if pd.notna(roe_adj) and np.isfinite(roe_adj) else "    N/A"

                    eq = row.get('earnings_quality', np.nan)
                    eq_str = f"{eq*100:>5.0f}%" if pd.notna(eq) and np.isfinite(eq) else "  N/A"

                    filter_reason = str(row.get('rim_filter_reason', ''))
                    hc_flag = bool(row.get('holding_co_flag', False))
                    tag_parts = []
                    if 'PRICE_TREND_PROXY' in filter_reason:
                        tag_parts.append('[PROXY]')
                    if 'ROE_NORMALIZED' in filter_reason or 'QUALITY_ADJUSTED' in filter_reason:
                        tag_parts.append('[ADJ]')
                    if hc_flag:
                        tag_parts.append('[HC]')
                    if filter_reason and filter_reason not in ('', 'QUALITY_ADJUSTED', 'EXTREME_ROE_NORMALIZED', 'QUALITY_ADJUSTED+ROE_NORMALIZED', 'PRICE_TREND_PROXY'):
                        tag_parts.append(filter_reason[:22])
                    filter_str = ' '.join(tag_parts)[:30]

                    rim_score_val = row.get('rim_score', np.nan)
                    rim_score_str = f"{rim_score_val*100:>9.1f}%" if pd.notna(rim_score_val) and np.isfinite(rim_score_val) else "      N/A"

                    f_out.write(
                        f"{rank:<5}{row['symbol']:<10}{name_str:<20}{row['market']:<10}"
                        f"{price_str}{intrinsic_str}{disc_str}"
                        f" {roe_raw_str} {roe_adj_str} {eq_str}  {filter_str:<32}{rim_score_str}\n"
                    )

            with open(rim_output_path, "w", encoding="utf-8") as f:
                _write_rim_file(f, rim_merged)
            logger.info(f"Saved RIM valuation predictions ({len(rim_merged)} symbols) to {rim_output_path}")

            # Per-market suffix files
            for _m in _get_target_markets_to_save(df=rim_merged, universe=universe):
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

    def _save_strategy_predictions_report(
        df_strat: pd.DataFrame,
        score_col: str,
        title: str,
        output_filename: str,
        score_header: str = "Score",
        header_width: int = 14
    ) -> None:
        if df_strat is None or df_strat.empty or score_col not in df_strat.columns:
            return

        merged = df_strat.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left') if 'market' not in df_strat.columns else df_strat.copy()
        if 'name' not in merged.columns and 'name' in universe.columns:
            merged = merged.merge(universe[['symbol', 'name']], on='symbol', how='left')
        merged['symbol'] = merged['symbol'].astype(str)
        merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')
        if merged[score_col].isna().all():
            logger.warning(f"[REPORT FALLBACK] Strategy '{title}' has all-NaN scores. Imputing baseline neutral score 0.50.")
            merged[score_col] = 0.50
        else:
            col_median = merged[score_col].median()
            fallback_val = col_median if (pd.notna(col_median) and np.isfinite(col_median)) else 0.50
            merged[score_col] = merged[score_col].fillna(fallback_val)
        merged = merged.sort_values(by=score_col, ascending=False)

        def _write_content(f_out, df_sub, market_label=None):
            f_out.write(f"=== {title} ===\n")
            f_out.write(f"Date: {kst_now_str}\n")
            f_out.write(f"Total symbols evaluated: {len(df_sub)}\n\n")
            f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{score_header:<{header_width}}\n")
            f_out.write("-" * (43 + header_width) + "\n")
            for rank, (_, row) in enumerate(_slice_top_df(df_sub, pred_limit).iterrows(), 1):
                name_str = str(row.get('name', 'Unknown'))[:16] if pd.notna(row.get('name')) else "Unknown"
                mkt_str = str(row.get('market', 'KRX'))
                sc_raw = float(row[score_col])
                sc_val = sc_raw * 100.0 if sc_raw <= 1.0 else sc_raw
                f_out.write(f"{rank:<5}{str(row['symbol']):<10}{name_str:<18}{mkt_str:<10}{sc_val:>{header_width-2}.1f}%\n")

        main_path = os.path.join(result_dir, output_filename)
        with open(main_path, "w", encoding="utf-8") as f:
            _write_content(f, merged)
        logger.info(f"Saved {title} ({len(merged)} symbols) to {main_path}")

        base_name = output_filename.replace(".txt", "")
        for _m in _get_target_markets_to_save(df=merged, universe=universe):
            _m_df = merged[merged['market'] == _m]
            if _m_df.empty:
                continue
            with open(os.path.join(result_dir, f"{base_name}_{_m}.txt"), "w", encoding="utf-8") as _mf:
                _write_content(_mf, _m_df, market_label=_m)

    # =========================================================================
    # Phase 10-Parallel: Concurrent Multi-Factor Strategy Scoring Engine
    # =========================================================================

    # 1. Pre-compute shared contexts & inputs
    symbols_list = universe['symbol'].tolist() if 'symbol' in universe.columns else list(infer_data_dict.keys())
    _fund_input = df_rim_input if ('df_rim_input' in locals() and df_rim_input is not None and not df_rim_input.empty) else None

    # Pre-fetch DART filings & LLM sentiment once for all sentiment-dependent strategies
    eff_filings = []
    sentiment_map = {}
    m5_sentiment_metrics_list = []
    try:
        from src.core.event_driven import EventDrivenEngine
        from src.core.llm_sentiment_engine import LLMSentimentEngine, DARTSECSentimentEngine
        _dart_key = getattr(cfg, 'dart_api_key', '') or ''
        if not _dart_key or _dart_key == 'your_dart_api_key_here':
            logger.warning("[S-2 WARNING] DART_API_KEY is not configured. Event-Driven and Insider Buying "
                           "will fall back to volume-breakout-only mode for Korean stocks. Set DART_API_KEY in .env for full coverage.")
        event_engine_init = EventDrivenEngine(dart_api_key=_dart_key)
        sentiment_engine_init = LLMSentimentEngine(db_storage=storage if 'storage' in locals() else None)
        eff_filings = event_engine_init.fetch_recent_dart_filings()
        if eff_filings:
            sentiment_map = sentiment_engine_init.batch_analyze_filings(eff_filings)
            m5_sentiment_metrics_list = list(sentiment_map.values())
        else:
            # Generate offline filing sentiment analysis for active universe symbols
            sample_syms = symbols_list[:min(len(symbols_list), 100)] if symbols_list else []
            for _sym in sample_syms:
                _res = sentiment_engine_init.analyze_filing_text(str(_sym), f"Corporate operations and financial guidance for {_sym}")
                sentiment_map[str(_sym)] = _res
                m5_sentiment_metrics_list.append(_res)
    except Exception as _init_ev_e:
        logger.warning(f"[PARALLEL SCORING] Pre-fetching DART filings/sentiment skipped: {_init_ev_e}")

    # Build filings_map for NLP Sentiment
    filings_map: dict[str, str] = {}
    if eff_filings:
        for item in eff_filings:
            if isinstance(item, dict):
                _sym = str(item.get('stock_code') or item.get('symbol') or '').strip()
                _txt = str(item.get('report_nm') or item.get('title') or item.get('content') or '').strip()
                if _sym and _txt:
                    filings_map[_sym] = (filings_map.get(_sym, '') + ' ' + _txt).strip()

    # Build transcript_map for Earnings Tone Drift
    tone_transcript_map = {}
    if sentiment_map:
        for s_k, s_val in sentiment_map.items():
            s_score = s_val if isinstance(s_val, (int, float)) else getattr(s_val, 'sentiment_score', 0.5)
            tone_transcript_map[s_k] = {'previous_quarter_tone': 0.5, 'current_quarter_tone': s_score}

    # Build ARM fundamental dictionary with dynamic filing lag (KRX 45d, US 40d)
    _arm_fund = {}
    if 'infer_fund_cache' in locals() and infer_fund_cache:
        for _sym, _fd in infer_fund_cache.items():
            if _fd is None or len(_fd) == 0:
                continue
            _cur_dt = pd.to_datetime(date_str) if 'date_str' in locals() and date_str else pd.Timestamp.now()
            if 'date_available' in _fd.columns:
                _fd_valid = _fd[pd.to_datetime(_fd['date_available']) <= _cur_dt]
            elif 'date' in _fd.columns:
                is_krx = str(_sym).isdigit() or str(_sym).endswith(('.KS', '.KQ'))
                fund_dts = pd.to_datetime(_fd['date'])
                lags = fund_dts.apply(lambda dt: pd.Timedelta(days=90 if is_krx else 60) if getattr(dt, 'month', 0) == 12 else pd.Timedelta(days=45 if is_krx else 40))
                _fd_valid = _fd[fund_dts + lags <= _cur_dt]
            else:
                _fd_valid = _fd

            if _fd_valid.empty:
                continue

            _fd_sorted = _fd_valid.sort_values('date') if 'date' in _fd_valid.columns else _fd_valid
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

            # V8-HIGH-05 Fix: Extract analyst target price revision and consensus EPS revision if available
            _tp_rev = None
            _eps_rev = None
            _per = None
            if isinstance(_last, (pd.Series, dict)):
                _tp_rev = _last.get('tp_revision_pct') or _last.get('target_price_change_pct')
                _eps_rev = _last.get('eps_revision_pct') or _last.get('eps_consensus_change_pct')
                _per = _last.get('per') or _last.get('pe_ratio')

            if _tp_rev is None and isinstance(_last, (pd.Series, dict)) and 'target_price' in _last and _sym in infer_data_dict:
                tp_val = float(_last.get('target_price') or 0.0)
                px_df = infer_data_dict[_sym]
                if tp_val > 0 and px_df is not None and not px_df.empty:
                    cur_px = float(px_df['Close'].iloc[-1])
                    if cur_px > 0:
                        _tp_rev = float((tp_val / cur_px - 1.0) * 100.0)

            _arm_fund[_sym] = {
                'eps_revision_pct': _eps_rev,
                'tp_revision_pct': _tp_rev,
                'eps_growth': _eps_g,
                'revenue_growth': _rev_g,
                'per': _per,
            }

    sector_mapping = dict(zip(universe['symbol'], universe.get('sector', universe.get('industry', 'DEFAULT')))) if 'symbol' in universe.columns else {}

    # 2. Define Strategy Task Functions
    def _eval_event_driven() -> pd.DataFrame:
        from src.core.event_driven import EventDrivenEngine
        _dart_key = getattr(cfg, 'dart_api_key', '') or ''
        eng = EventDrivenEngine(dart_api_key=_dart_key)
        return eng.compute_event_scores(symbols=symbols_list, prices_dict=infer_data_dict, filings=eff_filings, sentiment_map=sentiment_map)

    def _eval_mq_factor() -> pd.DataFrame:
        from src.core.mq_factor import MQFactorEngine
        return MQFactorEngine().compute_mq_scores(prices_dict=infer_data_dict, features_df=_fund_input)

    def _eval_iv_skew() -> pd.DataFrame:
        from src.core.iv_skew import IVSkewEngine
        return IVSkewEngine().compute_iv_skew_scores(symbols=symbols_list, prices_dict=infer_data_dict)

    def _eval_order_flow() -> pd.DataFrame:
        from src.core.order_flow import OrderFlowEngine
        return OrderFlowEngine().compute_order_flow_scores(prices_dict=infer_data_dict)

    def _eval_short_term_reversal() -> pd.DataFrame:
        from src.core.short_term_reversal import ShortTermReversalEngine
        return ShortTermReversalEngine().compute_reversal_scores(prices_dict=infer_data_dict, features_df=_fund_input)

    def _eval_arm_factor() -> pd.DataFrame:
        from src.core.arm_factor import ARMFactorEngine
        res = ARMFactorEngine().compute_scores(prices_dict=infer_data_dict, fundamentals_dict=_arm_fund)
        if isinstance(res, dict):
            return pd.DataFrame([{'symbol': k, 'arm_score': v} for k, v in res.items()])
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

    def _eval_card_factor() -> pd.DataFrame:
        from src.core.card_factor import CARDFactorEngine
        res = CARDFactorEngine().compute_scores(prices_dict=infer_data_dict, indicators_df=indicator_infer if 'indicator_infer' in locals() else pd.DataFrame(), sector_map=sector_mapping)
        if isinstance(res, dict):
            return pd.DataFrame([{'symbol': k, 'card_score': v} for k, v in res.items()])
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

    def _eval_latr_factor() -> pd.DataFrame:
        from src.core.latr_factor import LATRFactorEngine
        res = LATRFactorEngine().compute_scores(infer_data_dict)
        if isinstance(res, dict):
            return pd.DataFrame([{'symbol': k, 'latr_score': v} for k, v in res.items()])
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

    def _eval_inst_foreign_sector() -> pd.DataFrame:
        from src.core.inst_foreign_sector import InstForeignSectorEngine
        return InstForeignSectorEngine(accumulation_days=40).compute_scores(infer_data_dict, flow_data_dict=None, sector_mapping=sector_mapping)

    def _eval_supply_chain() -> pd.DataFrame:
        from src.core.supply_chain import SupplyChainEngine
        return SupplyChainEngine().compute_scores(infer_data_dict, universe)

    def _eval_sentiment() -> pd.DataFrame:
        from src.core.llm_sentiment_engine import DARTSECSentimentEngine
        eng = DARTSECSentimentEngine(db_storage=storage if 'storage' in locals() else None)
        return eng.compute_scores(
            universe=universe, filings_map=filings_map,
            sentiment_map=sentiment_map if sentiment_map else None,
            filings=eff_filings if eff_filings else None,
            prices_dict=infer_data_dict
        )

    def _eval_factor_neutralized() -> pd.DataFrame:
        from src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine
        return MultiFactorNeutralizerEngine().compute_scores(
            prices_dict=infer_data_dict, universe=universe,
            raw_scores=res_df if ('res_df' in locals() and res_df is not None and not res_df.empty) else None,
            fundamentals_dict=infer_fund_cache if ('infer_fund_cache' in locals() and infer_fund_cache) else None
        )

    def _eval_vol_target() -> pd.DataFrame:
        from src.core.vol_target import VolTargetingEngine
        return VolTargetingEngine().compute_scores(infer_data_dict, universe)

    def _eval_microstructure() -> pd.DataFrame:
        from src.core.hft_engine import MicrostructureImbalanceEngine
        return MicrostructureImbalanceEngine().compute_scores(infer_data_dict, universe)

    def _eval_accruals_quality() -> pd.DataFrame:
        from src.core.accruals_quality import AccrualsQualityEngine
        return AccrualsQualityEngine(cfg).calculate_scores(symbols_list, features_df=_fund_input, prices_dict=infer_data_dict)

    def _eval_short_squeeze() -> pd.DataFrame:
        from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
        return ShortInterestSqueezeEngine(cfg).calculate_scores(symbols_list, prices_dict=infer_data_dict, features_df=_fund_input)

    def _eval_valueup_catalyst() -> pd.DataFrame:
        from src.core.valueup_catalyst import ValueUpCatalystEngine
        return ValueUpCatalystEngine(cfg).calculate_scores(symbols_list, features_df=_fund_input, prices_dict=infer_data_dict)

    def _eval_trend_efficiency() -> pd.DataFrame:
        from src.core.trend_efficiency import TrendEfficiencyEngine
        return TrendEfficiencyEngine(cfg).calculate_scores(symbols_list, prices_dict=infer_data_dict, features_df=_fund_input)

    def _eval_gamma_squeeze() -> pd.DataFrame:
        from src.core.gamma_squeeze import OptionsGammaSqueezeEngine
        return OptionsGammaSqueezeEngine(cfg).calculate_scores(symbols_list, prices_dict=infer_data_dict)

    def _eval_insider_buying() -> pd.DataFrame:
        from src.core.insider_buying import InsiderBuyingEngine
        return InsiderBuyingEngine(cfg).calculate_scores(symbols_list, prices_dict=infer_data_dict, insider_filings=eff_filings if eff_filings else None)

    def _eval_earnings_tone_drift() -> pd.DataFrame:
        from src.core.earnings_tone_drift import EarningsToneDriftEngine
        return EarningsToneDriftEngine(cfg).calculate_scores(symbols_list, prices_dict=infer_data_dict, transcript_map=tone_transcript_map if tone_transcript_map else None, features_df=_fund_input)

    def _eval_darkpool() -> pd.DataFrame:
        from src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
        return DarkPoolTrackerEngine(cfg).calculate_scores(symbols_list, prices_dict=infer_data_dict)

    def _eval_dual_correction() -> pd.DataFrame:
        from src.core.dual_correction import DualCorrectionEngine
        return DualCorrectionEngine(cfg).compute_scores(prices_dict=infer_data_dict, regime=current_2d_regime)

    def _eval_index_rebalance() -> pd.DataFrame:
        from src.core.index_rebalance import IndexRebalanceEngine
        return IndexRebalanceEngine().compute_scores(prices_dict=infer_data_dict, universe=universe)

    def _eval_overnight_gap_reversal() -> pd.DataFrame:
        from src.core.overnight_gap_reversal import OvernightGapReversalEngine
        return OvernightGapReversalEngine(cfg).calculate_scores(symbols_list, prices_dict=infer_data_dict)

    def _eval_cross_asset_spillover() -> pd.DataFrame:
        from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
        return CrossAssetSpilloverEngine().compute_scores(prices_dict=infer_data_dict, indicators_df=indicator_infer if 'indicator_infer' in locals() else None)

    def _eval_supply_chain_gnn() -> pd.DataFrame:
        from src.core.supply_chain_gnn import SupplyChainGNNEngine
        return SupplyChainGNNEngine().compute_scores(prices_dict=infer_data_dict)

    def _eval_range_expansion_breakout() -> pd.DataFrame:
        from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine
        return RangeExpansionBreakoutEngine(cfg).compute_scores(prices_dict=infer_data_dict)

    def _eval_lstm() -> pd.DataFrame:
        if hasattr(model, "predict_lstm"):
            return model.predict_lstm(infer_data_dict, horizon=20)
        else:
            from src.ai.ml_strategy_adapters import LSTMStrategyAdapter
            return LSTMStrategyAdapter(model_instance=model, config=cfg).compute_scores(infer_data_dict)

    # Strategy Configuration Registry
    STRATEGY_REGISTRY = [
        {'key': 'lstm', 'fn': _eval_lstm, 'col': 'lstm_score', 'title': 'Strategy 6: Strict Causal LSTM Predictions', 'file': 'lstm_predictions.txt', 'hdr': 'LSTM Score', 'w': 14},
        {'key': 'event', 'fn': _eval_event_driven, 'col': 'event_score', 'title': 'Strategy 10: Event-Driven Disclosure Catalyst Predictions', 'file': 'event_driven_predictions.txt', 'hdr': 'Event Score', 'w': 14},
        {'key': 'mq', 'fn': _eval_mq_factor, 'col': 'mq_score', 'title': 'Strategy 11: Momentum Quality (MQ) Factor Predictions', 'file': 'mq_factor_predictions.txt', 'hdr': 'MQ Score', 'w': 14},
        {'key': 'iv_skew', 'fn': _eval_iv_skew, 'col': 'iv_skew_score', 'title': 'Strategy 12: Options Put/Call IV Skew Predictions', 'file': 'iv_skew_predictions.txt', 'hdr': 'IV Skew Score', 'w': 14},
        {'key': 'order_flow', 'fn': _eval_order_flow, 'col': 'order_flow_score', 'title': 'Strategy 13: Order Flow Imbalance (MFI) Predictions', 'file': 'order_flow_predictions.txt', 'hdr': 'Order Flow Score', 'w': 16},
        {'key': 'reversal', 'fn': _eval_short_term_reversal, 'col': 'reversal_score', 'title': 'Strategy 14: Short-Term Mean Reversal Predictions', 'file': 'short_term_reversal_predictions.txt', 'hdr': 'Reversal Score', 'w': 16},
        {'key': 'arm', 'fn': _eval_arm_factor, 'col': 'arm_score', 'title': 'Strategy 15: Analyst Revision Momentum (ARM) Factor Predictions', 'file': 'arm_factor_predictions.txt', 'hdr': 'ARM Score', 'w': 12},
        {'key': 'card', 'fn': _eval_card_factor, 'col': 'card_score', 'title': 'Strategy 16: Cross-Asset Regime Divergence (CARD) Factor Predictions', 'file': 'card_factor_predictions.txt', 'hdr': 'CARD Score', 'w': 14},
        {'key': 'latr', 'fn': _eval_latr_factor, 'col': 'latr_score', 'title': 'Strategy 17: Liquidity-Adjusted Tail Risk (LATR) Factor Predictions', 'file': 'latr_factor_predictions.txt', 'hdr': 'LATR Score', 'w': 14},
        {'key': 'inst_foreign_sector', 'fn': _eval_inst_foreign_sector, 'col': 'inst_foreign_sector_score', 'title': 'Strategy 18: Inst & Foreign 2-Month Accumulation & Sector Correlation Predictions', 'file': 'inst_foreign_sector_predictions.txt', 'hdr': 'IFS Score', 'w': 14},
        {'key': 'supply_chain', 'fn': _eval_supply_chain, 'col': 'supply_chain_score', 'title': 'Strategy 19: Supply Chain Lead-Lag Momentum Predictions', 'file': 'supply_chain_predictions.txt', 'hdr': 'SC Score', 'w': 14},
        {'key': 'sentiment', 'fn': _eval_sentiment, 'col': 'sentiment_score', 'title': 'Strategy 20: NLP & FinBERT Sentiment Catalyst Predictions', 'file': 'sentiment_predictions.txt', 'hdr': 'Sent Score', 'w': 14},
        {'key': 'factor_neutralized', 'fn': _eval_factor_neutralized, 'col': 'factor_neutralized_score', 'title': 'Strategy 21: Multi-Factor Style Neutralized Pure Alpha Predictions', 'file': 'factor_neutralized_predictions.txt', 'hdr': 'FN Score', 'w': 14},
        {'key': 'vol_target', 'fn': _eval_vol_target, 'col': 'vol_target_score', 'title': 'Strategy 22: Dynamic Volatility Targeting Risk Parity Predictions', 'file': 'vol_target_predictions.txt', 'hdr': 'VT Score', 'w': 14},
        {'key': 'microstructure', 'fn': _eval_microstructure, 'col': 'microstructure_score', 'title': 'Strategy 23: Order Book Microstructure Imbalance Predictions', 'file': 'microstructure_predictions.txt', 'hdr': 'Micro Score', 'w': 14},
        {'key': 'accruals_quality', 'fn': _eval_accruals_quality, 'col': 'accruals_quality_score', 'title': 'Strategy 24: Accruals Quality Anomaly Predictions', 'file': 'accruals_quality_predictions.txt', 'hdr': 'Accruals Score', 'w': 16},
        {'key': 'short_squeeze', 'fn': _eval_short_squeeze, 'col': 'short_squeeze_score', 'title': 'Strategy 25: Short Interest & Squeeze Catalyst Predictions', 'file': 'short_squeeze_predictions.txt', 'hdr': 'Squeeze Score', 'w': 16},
        {'key': 'valueup_catalyst', 'fn': _eval_valueup_catalyst, 'col': 'valueup_catalyst_score', 'title': 'Strategy 26: Value-Up & Shareholder Yield Predictions', 'file': 'valueup_catalyst_predictions.txt', 'hdr': 'ValueUp Score', 'w': 16},
        {'key': 'trend_efficiency', 'fn': _eval_trend_efficiency, 'col': 'trend_efficiency_score', 'title': 'Strategy 27: Kaufman Trend Efficiency Predictions', 'file': 'trend_efficiency_predictions.txt', 'hdr': 'Trend Score', 'w': 16},
        {'key': 'gamma_squeeze', 'fn': _eval_gamma_squeeze, 'col': 'gamma_squeeze_score', 'title': 'Strategy 28: Options Gamma Squeeze Predictions', 'file': 'gamma_squeeze_predictions.txt', 'hdr': 'Gamma Score', 'w': 16},
        {'key': 'insider_buying', 'fn': _eval_insider_buying, 'col': 'insider_buying_score', 'title': 'Strategy 29: Insider Buying Catalyst Predictions', 'file': 'insider_buying_predictions.txt', 'hdr': 'Insider Score', 'w': 16},
        {'key': 'darkpool', 'fn': _eval_darkpool, 'col': 'darkpool_score', 'title': 'Strategy 30: HFT Order Flow & Dark Pool Predictions', 'file': 'darkpool_predictions.txt', 'hdr': 'Darkpool Score', 'w': 16},
        {'key': 'earnings_tone_drift', 'fn': _eval_earnings_tone_drift, 'col': 'earnings_tone_drift_score', 'title': 'Strategy 31: Earnings Tone Drift NLP Predictions', 'file': 'earnings_tone_drift_predictions.txt', 'hdr': 'Tone Score', 'w': 16},
        {'key': 'dual_correction', 'fn': _eval_dual_correction, 'col': 'dual_correction_score', 'title': 'Strategy 32: Dual Correction Predictions', 'file': 'dual_correction_predictions.txt', 'hdr': 'Dual Score', 'w': 16},
        {'key': 'index_rebalance', 'fn': _eval_index_rebalance, 'col': 'index_rebalance_score', 'title': 'Strategy 33: Index Rebalance Predictions', 'file': 'index_rebalance_predictions.txt', 'hdr': 'Rebal Score', 'w': 16},
        {'key': 'overnight_gap_reversal', 'fn': _eval_overnight_gap_reversal, 'col': 'overnight_gap_score', 'title': 'Strategy 34: Overnight Gap Reversal Predictions', 'file': 'overnight_gap_predictions.txt', 'hdr': 'Gap Score', 'w': 16},
        {'key': 'cross_asset_spillover', 'fn': _eval_cross_asset_spillover, 'col': 'cross_asset_spillover_score', 'title': 'Strategy 35: Cross-Asset Spillover Momentum Predictions', 'file': 'cross_asset_spillover_predictions.txt', 'hdr': 'Spillover Score', 'w': 16},
        {'key': 'supply_chain_gnn', 'fn': _eval_supply_chain_gnn, 'col': 'supply_chain_gnn_score', 'title': 'Strategy 36: Supply Chain GNN & Sector Flow Predictions', 'file': 'supply_chain_gnn_predictions.txt', 'hdr': 'SC GNN Score', 'w': 16},
        {'key': 'range_expansion_breakout', 'fn': _eval_range_expansion_breakout, 'col': 'range_expansion_score', 'title': 'Strategy 37: Range Expansion Breakout Predictions', 'file': 'range_expansion_predictions.txt', 'hdr': 'Breakout Score', 'w': 16},
    ]

    # 3. Concurrent Execution via ThreadPoolExecutor
    _score_workers = max(1, min(8, getattr(cfg, 'strategy_scoring_workers', os.cpu_count() or 4)))
    logger.info(f"[PARALLEL FACTOR SCORING] Evaluating {len(STRATEGY_REGISTRY)} factor strategies concurrently with {_score_workers} worker threads...")

    def _execute_single_strat(strat_spec: dict):
        _s_key = strat_spec['key']
        try:
            _res = strat_spec['fn']()
            if not isinstance(_res, pd.DataFrame):
                _res = pd.DataFrame()
            return _s_key, _res
        except Exception as _err:
            logger.warning(f"[PARALLEL SCORING] Strategy '{_s_key}' computation failed: {_err}")
            return _s_key, pd.DataFrame()

    _raw_strat_outputs = {}
    with ThreadPoolExecutor(max_workers=_score_workers) as executor:
        _future_map = {executor.submit(_execute_single_strat, s): s['key'] for s in STRATEGY_REGISTRY}
        for future in as_completed(_future_map):
            _s_key, _df_res = future.result()
            _raw_strat_outputs[_s_key] = _df_res

    # 4. Deterministic Report Generation & Local Variable Assignment
    for spec in STRATEGY_REGISTRY:
        _k = spec['key']
        _df_s = _raw_strat_outputs.get(_k, pd.DataFrame())
        _scol = spec['col']
        if _df_s is not None and not _df_s.empty:
            if _scol not in _df_s.columns:
                # Handle alternative score column names (e.g. neutralized_score, lstm_return_20d)
                for alt_c in ['neutralized_score', 'lstm_return_20d', 'score']:
                    if alt_c in _df_s.columns:
                        _scol = alt_c
                        break
            if _scol in _df_s.columns:
                _save_strategy_predictions_report(
                    _df_s, _scol, str(spec['title']), str(spec['file']),
                    score_header=str(spec.get('hdr', 'Score')), header_width=int(str(spec.get('w', 14)))
                )

    # Assign local DataFrame variables for downstream pipeline compatibility
    event_df = _raw_strat_outputs.get('event', pd.DataFrame())
    mq_df = _raw_strat_outputs.get('mq', pd.DataFrame())
    iv_skew_df = _raw_strat_outputs.get('iv_skew', pd.DataFrame())
    order_flow_df = _raw_strat_outputs.get('order_flow', pd.DataFrame())
    reversal_df = _raw_strat_outputs.get('reversal', pd.DataFrame())
    arm_df = _raw_strat_outputs.get('arm', pd.DataFrame())
    card_df = _raw_strat_outputs.get('card', pd.DataFrame())
    latr_df = _raw_strat_outputs.get('latr', pd.DataFrame())
    inst_foreign_sector_df = _raw_strat_outputs.get('inst_foreign_sector', pd.DataFrame())
    supply_chain_df = _raw_strat_outputs.get('supply_chain', pd.DataFrame())
    sentiment_df = _raw_strat_outputs.get('sentiment', pd.DataFrame())
    factor_neutralized_df = _raw_strat_outputs.get('factor_neutralized', pd.DataFrame())
    vol_target_df = _raw_strat_outputs.get('vol_target', pd.DataFrame())
    microstructure_df = _raw_strat_outputs.get('microstructure', pd.DataFrame())
    accruals_quality_df = _raw_strat_outputs.get('accruals_quality', pd.DataFrame())
    short_squeeze_df = _raw_strat_outputs.get('short_squeeze', pd.DataFrame())
    valueup_catalyst_df = _raw_strat_outputs.get('valueup_catalyst', pd.DataFrame())
    trend_efficiency_df = _raw_strat_outputs.get('trend_efficiency', pd.DataFrame())
    gamma_squeeze_df = _raw_strat_outputs.get('gamma_squeeze', pd.DataFrame())
    insider_buying_df = _raw_strat_outputs.get('insider_buying', pd.DataFrame())
    earnings_tone_drift_df = _raw_strat_outputs.get('earnings_tone_drift', pd.DataFrame())
    darkpool_df = _raw_strat_outputs.get('darkpool', pd.DataFrame())
    dual_correction_df = _raw_strat_outputs.get('dual_correction', pd.DataFrame())
    index_rebalance_df = _raw_strat_outputs.get('index_rebalance', pd.DataFrame())
    overnight_gap_df = _raw_strat_outputs.get('overnight_gap_reversal', pd.DataFrame())
    cross_asset_spillover_df = _raw_strat_outputs.get('cross_asset_spillover', pd.DataFrame())
    supply_chain_gnn_df = _raw_strat_outputs.get('supply_chain_gnn', pd.DataFrame())
    range_expansion_breakout_df = _raw_strat_outputs.get('range_expansion_breakout', pd.DataFrame())
    lstm_df_for_ens = _raw_strat_outputs.get('lstm', pd.DataFrame())

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
        hist_df = storage.get_ensemble_predictions_history(days=90)
        if hist_df is not None and not hist_df.empty:
            for strat, col in [
                ('regression', 'reg_score'), ('surge', 'surge_score'), ('lead_lag', 'll_score'),
                ('vcp_rule', 'vcp_rule_score'), ('vcp_ml', 'vcp_ml_score'), ('lstm', 'lstm_score'),
                ('stat_arb', 'stat_arb_score'), ('sector_rotation', 'sector_score'),
                ('rim_valuation', 'rim_score'), ('event_driven', 'event_score'),
                ('mq_factor', 'mq_score'), ('iv_skew', 'iv_skew_score'),
                ('order_flow', 'order_flow_score'), ('short_term_reversal', 'reversal_score'),
                ('arm_factor', 'arm_score'),
                ('card_factor', 'card_score'),
                ('latr_factor', 'latr_score'),
                ('inst_foreign_sector', 'inst_foreign_sector_score'),
                ('supply_chain', 'supply_chain_score'),
                ('sentiment', 'sentiment_score'),
                ('factor_neutralized', 'factor_neutralized_score'),
                ('vol_target', 'vol_target_score'),
                ('microstructure', 'microstructure_score'),
                ('accruals_quality', 'accruals_quality_score'),
                ('short_squeeze', 'short_squeeze_score'),
                ('valueup_catalyst', 'valueup_catalyst_score'),
                ('trend_efficiency', 'trend_efficiency_score'),
                ('gamma_squeeze', 'gamma_squeeze_score'),
                ('insider_buying', 'insider_buying_score'),
                ('darkpool', 'darkpool_score'),
                ('earnings_tone_drift', 'earnings_tone_drift_score'),
                ('cross_asset_spillover', 'cross_asset_spillover_score'),
                ('supply_chain_gnn', 'supply_chain_gnn_score'),
                ('range_expansion_breakout', 'range_expansion_score'),
                ('dual_correction', 'dual_correction_score'),
                ('index_rebalance', 'index_rebalance_score'),
                ('overnight_gap_reversal', 'overnight_gap_score'),
            ]:
                if col in hist_df.columns and 'outcome_return' in hist_df.columns:
                    valid_sub = hist_df[hist_df[col].notna() & hist_df['outcome_return'].notna()]
                    if not valid_sub.empty:
                        strat_series = valid_sub.groupby('date').apply(lambda d: (d[col] * d['outcome_return']).mean(), include_groups=False)
                        strategy_returns[strat] = strat_series
    except Exception as _sr_e:
        logger.debug(f"Strategy returns computation for Sharpe weighting: {_sr_e}")

    rolling_sharpes = scorer.compute_rolling_sharpe(strategy_returns) if strategy_returns else None

    # Force Garbage Collection before heavy Ensemble Scoring
    gc.collect()
    # Strategy Execution Health Gate: Check non-empty strategies
    _all_strategy_dfs = {
        'regression': res_df, 'surge': surge_df, 'lead_lag': lead_lag_df, 'vcp_rule': vcp_results,
        'vcp_ml': vcp_ml_df, 'lstm': lstm_df_for_ens, 'stat_arb': stat_arb_df, 'sector': sector_df,
        'rim': rim_df, 'event': event_df, 'mq': mq_df, 'iv_skew': iv_skew_df, 'order_flow': order_flow_df,
        'reversal': reversal_df, 'arm': arm_df, 'card': card_df, 'latr': latr_df,
        'inst_foreign_sector': inst_foreign_sector_df, 'supply_chain': supply_chain_df,
        'sentiment': sentiment_df, 'factor_neutralized': factor_neutralized_df, 'vol_target': vol_target_df,
        'microstructure': microstructure_df, 'accruals_quality': accruals_quality_df,
        'short_squeeze': short_squeeze_df, 'valueup_catalyst': valueup_catalyst_df,
        'trend_efficiency': trend_efficiency_df, 'gamma_squeeze': gamma_squeeze_df,
        'insider_buying': insider_buying_df, 'darkpool': darkpool_df,
        'earnings_tone_drift': earnings_tone_drift_df,
        'dual_correction': dual_correction_df,
        'index_rebalance': index_rebalance_df,
        'overnight_gap_reversal': overnight_gap_df,
        'cross_asset_spillover': cross_asset_spillover_df,
        'supply_chain_gnn': supply_chain_gnn_df,
        'range_expansion_breakout': range_expansion_breakout_df,
    }
    _active_strats = [name for name, df in _all_strategy_dfs.items() if df is not None and not (isinstance(df, pd.DataFrame) and df.empty)]
    _strat_coverage = len(_active_strats) / len(_all_strategy_dfs)
    logger.info(f"[STRATEGY HEALTH GATE] Active strategies: {len(_active_strats)}/{len(_all_strategy_dfs)} ({_strat_coverage:.1%})")
    if _strat_coverage < 0.20:
        _notify_telegram(f"🚨 [경고] 활성 전략 수 심각한 부족: {len(_active_strats)}/{len(_all_strategy_dfs)} ({_strat_coverage:.1%})", "CRITICAL")

    # default target horizon is 20d (31-Strategy Ensemble)
    ensemble_df = scorer.calculate_ensemble_score(
        regime=current_2d_regime,
        us_regime=us_2d_regime if 'us_2d_regime' in locals() else current_2d_regime,
        kr_regime=kr_2d_regime if 'kr_2d_regime' in locals() else current_2d_regime,
        decoupling_status=decoupling_status if 'decoupling_status' in locals() else 'COUPLED',
        dual_regimes=decoupling_info if 'decoupling_info' in locals() else None,
        regression_df=res_df,
        surge_df=surge_df,
        lead_lag_df=lead_lag_df,
        vcp_rule_df=vcp_results,
        vcp_ml_df=vcp_ml_df,
        lstm_df=lstm_df_for_ens,
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
        supply_chain_df=supply_chain_df,
        sentiment_df=sentiment_df,
        factor_neutralized_df=factor_neutralized_df,
        vol_target_df=vol_target_df,
        microstructure_df=microstructure_df,
        accruals_quality_df=accruals_quality_df,
        short_squeeze_df=short_squeeze_df,
        valueup_catalyst_df=valueup_catalyst_df,
        trend_efficiency_df=trend_efficiency_df,
        gamma_squeeze_df=gamma_squeeze_df,
        insider_buying_df=insider_buying_df,
        darkpool_df=darkpool_df,
        earnings_tone_drift_df=earnings_tone_drift_df,
        cross_asset_spillover_df=cross_asset_spillover_df,
        supply_chain_gnn_df=supply_chain_gnn_df,
        range_expansion_breakout_df=range_expansion_breakout_df,
        dual_correction_df=dual_correction_df,
        index_rebalance_df=index_rebalance_df,
        overnight_gap_df=overnight_gap_df,
        rolling_sharpes=rolling_sharpes,
        target_horizon=20,
        prices_dict=infer_data_dict if 'infer_data_dict' in locals() else None
    )

    # Pre-Market Overnight Gap Shifter calibration for KRX markets
    try:
        from src.data_layer.overnight_gap_shifter import OvernightGapShifter
        gap_shifter = OvernightGapShifter()
        on_indicator_df = indicator_infer if 'indicator_infer' in locals() else locals().get('indicator_df', None)
        on_factors = gap_shifter.fetch_overnight_factors(on_indicator_df)
        krx_gap = gap_shifter.compute_opening_gap_estimate(on_factors)
        if abs(krx_gap) >= 0.20 and ensemble_df is not None and not ensemble_df.empty:
            logger.info(f"[OVERNIGHT GAP SHIFTER] Estimated KRX opening gap: {krx_gap:+.2f}% (SPY: {on_factors.get('spy_return', 0.0):+.2f}%, USD/KRW: {on_factors.get('usdkrw_change', 0.0):+.2f}%)")
            ensemble_df = gap_shifter.apply_gap_shift_to_scores(ensemble_df, krx_gap, market='KRX')
    except Exception as _ge:
        logger.debug(f"[OVERNIGHT GAP SHIFTER] Bypassed: {_ge}")


    try:
        if ensemble_df is not None and not ensemble_df.empty and storage is not None:
            storage.save_ensemble_predictions(ensemble_df, date_str)
            logger.info(f"[ENSEMBLE DB] Saved {len(ensemble_df)} ensemble prediction rows for {date_str}.")

            # Save multi-run prediction history & strategy weights for cross-run tracking
            if 'current_run_id' in locals() and current_run_id:
                storage.save_ensemble_history(current_run_id, ensemble_df, date_str)
                weights_dict = getattr(scorer, '_prev_weights', {}) or getattr(scorer, 'strategy_weights', {})
                if not weights_dict and hasattr(scorer, 'strategy_cols'):
                    weights_dict = {col[0]: 1.0 / len(scorer.strategy_cols) for col in scorer.strategy_cols}
                storage.save_strategy_weights(current_run_id, weights_dict, regime=current_2d_regime if 'current_2d_regime' in locals() else '')

                # Generate cross-run comparison report if previous run exists
                if 'previous_run_id' in locals() and previous_run_id:
                    try:
                        comparison = storage.compare_runs(previous_run_id, current_run_id, top_n=20)
                        cmp_report = storage.generate_comparison_report(comparison)
                        logger.info("\n" + cmp_report)

                        _res_dir = Path(__file__).parent / "result"
                        _res_dir.mkdir(exist_ok=True)
                        with open(_res_dir / "run_comparison.txt", "w", encoding="utf-8") as _cmp_f:
                            _cmp_f.write(cmp_report)
                        logger.info(f"[RUN HISTORY] Saved run_comparison.txt comparing {previous_run_id} vs {current_run_id}")
                    except Exception as _cmp_e:
                        logger.warning(f"[RUN HISTORY] Failed to generate run comparison report: {_cmp_e}")
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
        """Parse yield safely, rejecting only NaN, infinite, or out-of-bound values."""
        try:
            v = float(val)
            if pd.isna(v) or np.isnan(v) or np.isinf(v) or v < -10.0 or v > 100.0:
                return default
            return v
        except Exception:
            return default

    db_macro = storage.get_latest_global_indicators() if storage is not None else {}

    def _compute_20d_ret_vol(col_name: str, default_ret: float, default_vol: float) -> tuple:
        if 'indicator_infer' in locals() and indicator_infer is not None and col_name in indicator_infer.columns:
            series = indicator_infer[col_name].dropna().tail(20)
            if not series.empty:
                ret = _safe_float(series.mean(), default_ret)
                vol = _safe_float(series.std(), default_vol) if len(series) > 1 else default_vol
                # Auto-scale raw decimal returns/volatilities to percentage representation (x 100.0)
                # In financial markets, daily volatility in percent is typically >= 0.20%, and daily return in decimal is <= 0.05
                is_decimal = (len(series) > 1 and vol <= 0.10 and abs(ret) <= 0.20 and (vol > 1e-7 or abs(ret) > 1e-7)) or (len(series) == 1 and 1e-7 < abs(ret) <= 0.02)
                if is_decimal:
                    ret *= 100.0
                    vol *= 100.0
                return ret, vol
        return default_ret, default_vol

    sp500_ret_20d, sp500_vol_20d = _compute_20d_ret_vol('sp500_change', 0.05, 1.0)
    kospi_ret_20d, kospi_vol_20d = _compute_20d_ret_vol('kospi_change', 0.05, 1.2)

    def _extract_macro_indicator(
        name: str,
        raw_val: float,
        ticker: str,
        db_macro_key: str,
        default_val: float,
        min_val: float = 0.0,
        max_val: float = 1000.0,
        is_yield: bool = False
    ) -> float:
        val = raw_val
        if (pd.isna(val) or val <= min_val or val > max_val) and price_db is not None:
            try:
                _df = price_db.get_prices(ticker, start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'))
                if _df is not None and not _df.empty and 'Close' in _df.columns:
                    _c = float(_df['Close'].dropna().iloc[-1])
                    val = _c / 10.0 if (is_yield and _c > 20) else _c
            except Exception as e:
                logger.warning(f"Failed price_db lookup for macro indicator {name} ({ticker}): {e}")
        if (pd.isna(val) or val <= min_val or val > max_val) and db_macro_key in db_macro:
            try:
                _c = float(db_macro[db_macro_key])
                val = _c / 10.0 if (is_yield and _c > 20) else _c
            except Exception as e:
                logger.warning(f"Failed db_macro lookup for macro indicator {name} ({db_macro_key}): {e}")
        return _safe_yield(val, default_val) if is_yield else _safe_float(val, default_val)

    # 1. VIX
    vix_raw = float(indicator_infer['vix_raw'].dropna().iloc[-1]) if ('vix_raw' in indicator_infer.columns and not indicator_infer['vix_raw'].dropna().empty) else np.nan
    vix_val = _extract_macro_indicator('VIX', vix_raw, '^VIX', '^VIX', getattr(cfg, 'default_vix', 18.5), min_val=0.0, max_val=150.0)

    # 2. USD/KRW
    usdkrw_raw = float(indicator_infer['usdkrw_raw'].dropna().iloc[-1]) if ('usdkrw_raw' in indicator_infer.columns and not indicator_infer['usdkrw_raw'].dropna().empty) else np.nan
    usdkrw_val = _extract_macro_indicator('USDKRW', usdkrw_raw, 'USDKRW=X', 'USDKRW=X', getattr(cfg, 'default_usdkrw', 1380.0), min_val=500.0, max_val=3000.0)

    # 3. US 10Y
    us10y_raw = float(indicator_infer['us10y'].dropna().iloc[-1]) if ('us10y' in indicator_infer.columns and not indicator_infer['us10y'].dropna().empty) else np.nan
    us10y_val = _extract_macro_indicator('US10Y', us10y_raw, '^TNX', '^TNX', getattr(cfg, 'default_us10y', 4.25), min_val=0.0, max_val=25.0, is_yield=True)

    # 4. KR 10Y
    kr10y_raw = float(indicator_infer['kr10y'].dropna().iloc[-1]) if ('kr10y' in indicator_infer.columns and not indicator_infer['kr10y'].dropna().empty) else np.nan
    kr10y_val = _extract_macro_indicator('KR10Y', kr10y_raw, 'FRED:IRLTLT01KRM156N', 'FRED:IRLTLT01KRM156N', getattr(cfg, 'default_kr10y', 3.15), min_val=0.0, max_val=25.0, is_yield=True)

    # WTI Crude Oil
    wti_val = _extract_macro_indicator('WTI', np.nan, 'CL=F', 'CL=F', getattr(cfg, 'default_wti', 75.0), min_val=10.0, max_val=300.0)

    # Gold
    gold_val = _extract_macro_indicator('Gold', np.nan, 'GLD', 'GLD', getattr(cfg, 'default_gold', 220.0), min_val=10.0, max_val=5000.0)

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


    ensemble_weights = scorer.compute_dynamic_weights_from_sharpe(rolling_sharpes or {}, current_2d_regime, vix_val=vix_report)

    # ── RiskManager & CrisisDetector Integration ──
    try:
        from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
        risk_mgr = RiskManager()
        crisis_detector = CrisisDetector(risk_mgr)
        state_restored = crisis_detector.load_state()
        if not state_restored and 'indicator_infer' in locals() and indicator_infer is not None and not indicator_infer.empty:
            crisis_detector.seed_history_from_dataframe(indicator_infer)

        crisis_lvl = crisis_detector.evaluate(
            vix=vix_report,
            usdkrw=usdkrw_report,
            oil=wti_report,
            tnx=us10y_report
        )
        crisis_detector.save_state()
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
        logger.warning(f"RiskManager evaluation failed: {_rm_e}. Applying conservative VIX crisis fallback (scaling expected returns by 0.50).")
        if 'ensemble_df' in locals() and ensemble_df is not None and not ensemble_df.empty:
            if 'ensemble_expected_return' in ensemble_df.columns:
                ensemble_df['ensemble_expected_return'] = ensemble_df['ensemble_expected_return'] * 0.50

    # Milestone 3: CPCV & Historical Stress Testing Engine
    m3_report_str = ""
    try:
        from src.ai.cpcv_stress_tester import CPCVStressTester
        cpcv_tester = CPCVStressTester(n_splits=6, n_test_splits=2, purge_window=5, embargo_window=10)

        # Strategy matrix for PBO
        raw_scores_df = getattr(scorer, 'raw_scores', None)

        # C6 FIX: Use actual historical market returns for stress testing,
        # NOT the current-point expected return snapshot (which is all positive and
        # produces MDD=0, VaR=0, CVaR=0 — meaningless stress test results).
        # Retrieve historical daily returns from market index data for realistic stress simulation.
        ens_returns = None
        try:
            # Try to get historical market index returns (S&P500 proxy) from indicator history
            hist_indicators = indicator_train if ('indicator_train' in locals() and indicator_train is not None and not indicator_train.empty) else None
            if hist_indicators is not None and 'sp500_return' in hist_indicators.columns:
                ens_returns = hist_indicators['sp500_return'].dropna().values
            elif hist_indicators is not None and 'sp500_close' in hist_indicators.columns:
                sp500 = hist_indicators['sp500_close'].dropna()
                if len(sp500) >= 20:
                    ens_returns = sp500.pct_change().dropna().values
        except Exception as _hist_e:
            logger.debug(f"Historical returns retrieval for stress test: {_hist_e}")

        # Fallback: apply scenario-specific synthetic stress shocks
        scenarios = ["2008_CRISIS", "2020_COVID", "2022_FED_HIKE"]
        stress_reports = {}
        if ens_returns is None or len(ens_returns) < 20:
            logger.warning("[STRESS TEST] No historical returns available. Using synthetic scenario-based stress vectors.")
            np.random.seed(42)
            # Generate synthetic crisis return series based on scenario characteristics
            synthetic_returns = {
                "2008_CRISIS": np.concatenate([
                    np.random.normal(-0.02, 0.04, 60),   # 3-month crash phase
                    np.random.normal(-0.005, 0.03, 120),  # 6-month extended bear
                    np.random.normal(0.005, 0.02, 72),    # partial recovery
                ]),
                "2020_COVID": np.concatenate([
                    np.random.normal(-0.04, 0.06, 25),    # 1-month sharp crash
                    np.random.normal(0.01, 0.03, 100),    # V-shaped recovery
                ]),
                "2022_FED_HIKE": np.concatenate([
                    np.random.normal(-0.005, 0.02, 180),  # prolonged grinding bear
                    np.random.normal(0.002, 0.015, 72),   # slow recovery
                ]),
            }
            for sc in scenarios:
                stress_reports[sc] = cpcv_tester.run_historical_stress_test(
                    synthetic_returns.get(sc, np.random.normal(-0.01, 0.03, 252)),
                    scenario=sc
                )
        else:
            for sc in scenarios:
                stress_reports[sc] = cpcv_tester.run_historical_stress_test(ens_returns, scenario=sc)

        if raw_scores_df is not None and isinstance(raw_scores_df, pd.DataFrame) and not raw_scores_df.empty:
            pbo_res = cpcv_tester.compute_pbo(raw_scores_df)
        else:
            score_cols = [c for c in ensemble_df.columns if c.endswith('_score') or c.endswith('_return')]
            if len(score_cols) >= 2:
                pbo_res = cpcv_tester.compute_pbo(ensemble_df[score_cols])
            else:
                pbo_res = cpcv_tester.compute_pbo(ensemble_df[['ensemble_expected_return']])


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
    try:
        if 'regime_detector' in locals() and indicator_infer is not None and not indicator_infer.empty:
            decoupling_info = regime_detector.predict_dual_market_regime(indicator_infer)
    except Exception as _dec_e:
        logger.warning(f"Dual market decoupling info computation skipped: {_dec_e}")
    decision_rationale_text = scorer.get_regime_reasoning_summary(current_2d_regime, rolling_sharpes, decoupling_info=decoupling_info)

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

        # Generate detailed Symbol Exclusion Diagnostics (JSON & Text Summary)
        try:
            import json
            from src.analysis.symbol_inspector import SymbolInspector
            sym_inspector = SymbolInspector(
                price_db=locals().get('price_db'),
                indicator_storage=locals().get('storage'),
                oms_engine=locals().get('oms_engine')
            )
            diag_batch = sym_inspector.generate_batch_diagnostics(
                universe_df=locals().get('universe'),
                ensemble_df=locals().get('ensemble_df'),
                order_plans_df=locals().get('order_plans'),
            )

            diag_json_path = os.path.join(result_dir, "symbol_exclusion_diagnostics.json")
            with open(diag_json_path, "w", encoding="utf-8") as f_dj:
                json.dump(diag_batch, f_dj, ensure_ascii=False, indent=2)

            diag_txt_path = os.path.join(result_dir, "symbol_exclusion_diagnostics.txt")
            with open(diag_txt_path, "w", encoding="utf-8") as f_dt:
                f_dt.write(f"=== Symbol Exclusion Diagnostics Summary ({kst_now_str}) ===\n")
                f_dt.write(f"Total Evaluated: {diag_batch.get('total_symbols_evaluated', 0):,} symbols\n\n")
                f_dt.write("Stage Breakdown:\n")
                for stg, cnt in diag_batch.get("stage_breakdown", {}).items():
                    f_dt.write(f"  - {stg:<16}: {cnt:>5,} symbols\n")
                f_dt.write("\nTop Exclusion Reasons:\n")
                for r_k, r_v in list(diag_batch.get("top_exclusion_reasons", {}).items())[:10]:
                    f_dt.write(f"  - {r_k:<30}: {r_v:>5,} symbols\n")
            logger.info(f"Saved Symbol Exclusion Diagnostics to {diag_json_path} and {diag_txt_path}")
        except Exception as _diag_e:
            logger.warning(f"Symbol Exclusion Diagnostics generation skipped: {_diag_e}")
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
        attr_analyzer = StrategyAttributionAnalyzer(output_dir=Path(result_dir))
        attr_analyzer.analyze_attribution(ensemble_df, weights=ensemble_weights if 'ensemble_weights' in locals() else None)
    except Exception as _attr_e:
        logger.warning(f"Strategy Attribution analysis skipped: {_attr_e}")

    # ── Task 3: Black-Litterman Portfolio Allocation Output ──
    try:
        from src.risk.position_sizing import PortfolioAllocator
        allocator = PortfolioAllocator()
        top_preds = ensemble_df.head(20).set_index('symbol')['ensemble_expected_return'].to_dict()
        bl_alloc_df = allocator.allocate_black_litterman(
            prices_dict=infer_data_dict, 
            predicted_returns=top_preds,
            total_portfolio_value=getattr(cfg, 'portfolio_capital_krw', 100_000_000.0)
        )
        if not bl_alloc_df.empty:
            bl_path = os.path.join(result_dir, "portfolio_allocation_black_litterman.txt")
            with open(bl_path, "w", encoding="utf-8") as f_bl:
                f_bl.write("=== Black-Litterman Optimal Asset Allocation ===\n")
                f_bl.write(f"Date: {kst_now_str}\n\n")
                f_bl.write(f"{'Rank':<5}{'Symbol':<10}{'Shares':<10}{'Lot':<6}{'Weight (%)':<15}{'Allocation (KRW)':<20}\n")
                f_bl.write("-" * 66 + "\n")
                for rank, (_, row) in enumerate(bl_alloc_df.iterrows(), 1):
                    sh_val = int(row.get('shares', 0)) if pd.notna(row.get('shares')) else 0
                    lot_val = int(row.get('lot_size', 1)) if pd.notna(row.get('lot_size')) else 1
                    f_bl.write(f"{rank:<5}{row['symbol']:<10}{sh_val:>8,d}  {lot_val:>4d}  {row['weight']*100:>12.2f}%   {row['allocation_amount']:>18,.0f}\n")
            logger.info(f"Saved Black-Litterman portfolio allocation to {bl_path}")
    except Exception as _bl_e:
        logger.warning(f"Black-Litterman portfolio allocation output skipped: {_bl_e}")

    ensemble_output_path = os.path.join(result_dir, "ensemble_predictions.txt")
    target_cols = [c for c in ['name', 'market'] if c in universe.columns]
    cols_to_drop = [c for c in target_cols if c in ensemble_df.columns]
    ensemble_clean = ensemble_df.drop(columns=cols_to_drop) if cols_to_drop else ensemble_df
    univ_cols = ['symbol'] + target_cols
    ensemble_df_merged = ensemble_clean.merge(universe[univ_cols], on='symbol', how='left')

    target_env = os.environ.get("INFERENCE_TARGET", "").strip().upper()
    if target_env and target_env not in ['ALL', 'CORE_5', 'ASIA_DEV', 'ASIA_EMG', 'COMMODITY'] and ',' not in target_env:
        ensemble_df_merged['market'] = ensemble_df_merged['market'].fillna(target_env)

    def _infer_market_from_symbol(sym: str) -> str:
        s = str(sym)
        if s.isdigit() or s.endswith(('.KS', '.KQ')):
            return 'KOSPI'
        if s.endswith('.T'):
            return 'JAPAN_TSE'
        if s.endswith(('.TW', '.TWO')):
            return 'TAIWAN_TWSE'
        if s.endswith(('.SS', '.SZ')):
            return 'CHINA_SSE'
        if s.endswith(('.NS', '.BO')):
            return 'INDIA_NSE'
        if s.endswith(('.PA', '.DE', '.AS', '.MC', '.MI', '.BR')):
            return 'EUROPE_STOXX'
        if s.endswith('.VN'):
            return 'VIETNAM_HOSE'
        if s.endswith('.AX'):
            return 'AUSTRALIA_ASX'
        if s.endswith('.SA'):
            return 'BRAZIL_B3'
        if s.endswith('.HK'):
            return 'HKEX'
        if s.endswith('.SI'):
            return 'SINGAPORE_SGX'
        if s.endswith('.TO'):
            return 'CANADA_TSX'
        return 'SP500'

    if 'market' not in ensemble_df_merged.columns or ensemble_df_merged['market'].isna().all():
        ensemble_df_merged['market'] = ensemble_df_merged['symbol'].map(_infer_market_from_symbol)
    else:
        ensemble_df_merged['market'] = ensemble_df_merged['market'].fillna(ensemble_df_merged['symbol'].map(_infer_market_from_symbol))
    if 'name' not in ensemble_df_merged.columns:
        ensemble_df_merged['name'] = ensemble_df_merged['symbol']

    # ── Institutional Portfolio Optimization (Unified Multi-Model Allocator) ──
    unified_alloc_df = pd.DataFrame()
    try:
        from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
        unified_allocator = UnifiedPortfolioAllocator(
            target_volatility=0.12,
            default_max_total_allocation=max_alloc if 'max_alloc' in locals() else 0.90,
            target_horizon=20
        )
        curr_holdings_dict = {}
        try:
            from src.execution.oms_engine import ExecutionOMSEngine
            _temp_oms = ExecutionOMSEngine(db_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_logs.db"))
            curr_holdings_dict = _temp_oms.get_current_holdings_from_db()
        except Exception:
            pass

        unified_alloc_df = unified_allocator.allocate(
            predictions_df=ensemble_df_merged,
            prices_dict=infer_data_dict,
            total_portfolio_value=getattr(cfg, 'portfolio_capital_krw', 100_000_000.0),
            regime=current_2d_regime if 'current_2d_regime' in locals() else "BULL_LOW_VOL",
            current_holdings=curr_holdings_dict,
            top_n=30,
            base_currency="KRW",
            usd_krw=float(usdkrw_report if 'usdkrw_report' in locals() and usdkrw_report else 1350.0),
        )
        if not unified_alloc_df.empty:
            weight_map = dict(zip(unified_alloc_df['symbol'].astype(str), unified_alloc_df['weight'].astype(float)))
            ensemble_df_merged['portfolio_weight'] = ensemble_df_merged['symbol'].astype(str).map(weight_map).fillna(0.0)
            # Re-sort by portfolio_weight so top picks correspond to actual optimized allocations!
            sort_cols = ['portfolio_weight']
            for extra_col in ['ensemble_expected_return', 'ensemble_score']:
                if extra_col in ensemble_df_merged.columns:
                    sort_cols.append(extra_col)
            ensemble_df_merged = ensemble_df_merged.sort_values(by=sort_cols, ascending=[False] * len(sort_cols)).reset_index(drop=True)
            logger.info(f"[PORTFOLIO OPTIMIZATION] Injected {len(weight_map)} institutional multi-model weights and re-sorted ensemble_df_merged")
    except Exception as _p_opt_e:
        logger.warning(f"[PORTFOLIO OPTIMIZATION] UnifiedPortfolioAllocator execution skipped: {_p_opt_e}")

    # ── Execution OMS Order Plan Generation & DB Logging ──
    try:
        from src.execution.oms_engine import ExecutionOMSEngine
        oms_engine = ExecutionOMSEngine(
            db_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_logs.db"),
            lot_size_krx=1
        )
        # Select all positive weight allocations first (up to top 30), or fallback to top 20
        if 'portfolio_weight' in ensemble_df_merged.columns:
            pos_weight_df = ensemble_df_merged[ensemble_df_merged['portfolio_weight'] > 0.0]
            if len(pos_weight_df) >= 3:
                top_picks_dicts = pos_weight_df.head(30).to_dict(orient="records")
            else:
                top_picks_dicts = ensemble_df_merged.head(20).to_dict(orient="records")
        else:
            top_picks_dicts = ensemble_df_merged.head(20).to_dict(orient="records")

        # Enrich top picks with the latest observed close price so order plans
        # carry a real reference price (never the 1.0 fallback).
        _last_close_map = {}
        if 'infer_data_dict' in locals() and infer_data_dict:
            for _sym, _sdf in infer_data_dict.items():
                try:
                    _cl = _sdf['Close']
                    if isinstance(_cl, pd.DataFrame):
                        _cl = _cl.iloc[:, 0]
                    _last_close_map[str(_sym)] = float(_cl.iloc[-1])
                except Exception:
                    continue
        for _pick in top_picks_dicts:
            _p_sym = _pick.get('symbol')
            if _pick.get('close_price') is None and _p_sym is not None:
                _pick['close_price'] = _last_close_map.get(str(_p_sym), _pick.get('close'))
        _crisis_lvl_str = "NORMAL"
        if 'crisis_lvl' in locals() and crisis_lvl is not None:
            _crisis_lvl_str = getattr(crisis_lvl, 'value', str(crisis_lvl))
        p_weights = ensemble_df_merged['portfolio_weight'] if 'portfolio_weight' in ensemble_df_merged.columns else pd.Series(0.05, index=ensemble_df_merged.index)
        weight_dict = dict(zip(ensemble_df_merged['symbol'], p_weights))
        curr_holdings = oms_engine.get_current_holdings_from_db()

        # UnifiedPortfolioAllocator already performed Leland dynamic buffer bands on target weights.
        # If unified allocator succeeded, use_leland_buffer=False prevents redundant double-buffering.
        _applied_leland_in_alloc = ('unified_alloc_df' in locals() and not unified_alloc_df.empty)
        order_plans = oms_engine.generate_order_plan(
            top_picks_dicts, weight_dict,
            total_capital=cfg.portfolio_capital_krw,
            crisis_level=_crisis_lvl_str,
            current_holdings=curr_holdings,
            use_leland_buffer=(not _applied_leland_in_alloc)
        )
        logger.info(f"[OMS ENGINE] Generated & saved {len(order_plans)} order execution plans to trade_logs.db (crisis_level={_crisis_lvl_str}, current_holdings={len(curr_holdings)})")
    except Exception as _oms_e:
        logger.warning(f"[OMS ENGINE] Order plan generation skipped: {_oms_e}")

    def _format_strategy_pct(val, default: float = 0.0, width: int = 4) -> str:
        if pd.isna(val):
            v = default
        else:
            try:
                v = float(val)
            except Exception:
                v = default
        pct = v * 100.0 if abs(v) <= 1.0 else v
        return f"{pct:>{width}.0f}%"

    with open(ensemble_output_path, "w", encoding="utf-8") as f:
        f.write(f"=== Dynamic Multi-Strategy Ensemble Predictions ({len(ensemble_weights)} Strategies) ===\n")
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

        us_weights_map = getattr(scorer, 'us_strategy_weights', ensemble_weights) or ensemble_weights
        kr_weights_map = getattr(scorer, 'kr_strategy_weights', ensemble_weights) or ensemble_weights

        f.write(f"--- Applied US Strategy Weights ({len(us_weights_map)} Strategies) [US: {us_2d_regime}] ---\n")
        _STRAT_DISPLAY_MAP = [
            ("regression", "XGBoost Regression Fundamentals"),
            ("surge", "Surge Classifier (XGBoost)"),
            ("lead_lag", "Index & Sector Lead-Lag Flow"),
            ("vcp_rule", "VCP Rule Pattern Detector"),
            ("vcp_ml", "VCP Machine Learning Predictor"),
            ("lstm", "Strict Causal LSTM Deep Learning"),
            ("stat_arb", "Stat-Arb Cointegration Mean Rev"),
            ("sector_rotation", "Sector Rotation Relative Momentum"),
            ("rim_valuation", "RIM Valuation (Residual Income)"),
            ("event_driven", "Event-Driven Disclosure Catalyst"),
            ("mq_factor", "Momentum Quality (MQ) Factor"),
            ("iv_skew", "Options Put/Call IV Skew"),
            ("order_flow", "Order Flow Imbalance (MFI)"),
            ("short_term_reversal", "Short-Term Mean Reversal"),
            ("arm_factor", "Analyst Revision Momentum (ARM)"),
            ("card_factor", "Cross-Asset Regime Divergence(CARD)"),
            ("latr_factor", "Liq-Adj Tail Risk (LATR)"),
            ("inst_foreign_sector", "Inst & Foreign Sector Flow"),
            ("supply_chain", "Supply Chain Spillover Momentum"),
            ("sentiment", "NLP FinBERT Sentiment Catalyst"),
            ("factor_neutralized", "Multi-Factor Style Neutral Alpha"),
            ("vol_target", "Dynamic Volatility Targeting"),
            ("microstructure", "Microstructure Order Imbalance"),
            ("accruals_quality", "Accruals Quality Accounting Pure"),
            ("short_squeeze", "Short Interest & Squeeze Catalyst"),
            ("valueup_catalyst", "Value-Up & Shareholder Yield"),
            ("trend_efficiency", "Kaufman Trend Efficiency Filter"),
            ("gamma_squeeze", "Options Gamma & Delta Squeeze"),
            ("insider_buying", "Executive & Insider Buying Catalyst"),
            ("darkpool", "HFT Order Flow & Dark Pool"),
            ("earnings_tone_drift", "Earnings Tone Drift NLP Quant"),
            ("cross_asset_spillover", "Cross-Asset Spillover Momentum"),
            ("supply_chain_gnn", "Supply Chain GNN & Sector Flow"),
            ("range_expansion_breakout", "Range Expansion Breakout"),
            ("dual_correction", "Dual Price & Time Correction"),
            ("index_rebalance", "Index Rebalance Structural Flow"),
            ("overnight_gap_reversal", "Overnight Gap Reversal"),
        ]
        us_vals = [us_weights_map.get(_skey, 0.0) for _skey, _ in _STRAT_DISPLAY_MAP]
        us_rounded = largest_remainder_round(us_vals, target_sum=100.0, decimals=1)
        for (_skey, _sname), _w_pct in zip(_STRAT_DISPLAY_MAP, us_rounded):
            f.write(f"  {_sname:<36}: {_w_pct:.1f}%\n")
        f.write("\n")

        kr_vals = [kr_weights_map.get(_skey, 0.0) for _skey, _ in _STRAT_DISPLAY_MAP]
        kr_rounded = largest_remainder_round(kr_vals, target_sum=100.0, decimals=1)
        f.write(f"--- Applied KR Strategy Weights ({len(kr_weights_map)} Strategies) [KR: {kr_2d_regime}] ---\n")
        for (_skey, _sname), _w_pct in zip(_STRAT_DISPLAY_MAP, kr_rounded):
            f.write(f"  {_sname:<36}: {_w_pct:.1f}%\n")
        f.write("\n")

        ens_vals = [ensemble_weights.get(_skey, 0.0) for _skey, _ in _STRAT_DISPLAY_MAP]
        ens_rounded = largest_remainder_round(ens_vals, target_sum=100.0, decimals=1)
        f.write(f"--- Applied Ensemble Strategy Weights ({len(ensemble_weights)} Strategies) ---\n")
        for (_skey, _sname), _w_pct in zip(_STRAT_DISPLAY_MAP, ens_rounded):
            f.write(f"  {_sname:<36}: {_w_pct:.1f}%\n")
        f.write("\n")

        # 2. Recommendations per market
        f.write("--- Top Recommendations by Market ---\n")
        all_ens_mkts = _get_target_markets_to_save(df=ensemble_df_merged, universe=universe)
        for market in all_ens_mkts:
            m_df = ensemble_df_merged[ensemble_df_merged['market'] == market].sort_values(by='ensemble_score', ascending=False)
            if m_df.empty:
                continue
            f.write("\n=========================================\n")
            _ens_header = f"[{market}] All Ensemble Picks ({len(m_df)} symbols) (Target Horizon: 20D Expected Return)\n" if is_all_pred else f"[{market}] Top {_TOP_N} Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            f.write(_ens_header)
            f.write("=========================================\n")
            f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Exp Ret(20D)':<14}{'Reg':<5}{'Srg':<5}{'L-L':<5}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<5}{'S-Arb':<6}{'Sec-R':<6}{'RIM':<5}{'Event':<6}{'MQ':<5}{'IV-Sk':<6}{'Flow':<5}{'Rev':<5}{'ARM':<5}{'CARD':<6}{'LATR':<5}{'IFS':<5}{'Supply':<7}{'NLP':<5}{'Neutral':<8}{'Vol-T':<6}{'Micro':<6}{'Accrual':<8}{'S-Sq':<5}{'ValueUp':<8}{'TrendEff':<9}{'GammaSq':<8}{'Insider':<8}{'Darkpool':<9}{'ToneDrift':<10}{'Spillover':<10}{'SC-GNN':<8}{'RangeExp':<9}{'DualCorr':<9}{'IdxRebal':<9}{'OverGap':<8}\n")
            f.write("-" * 333 + "\n")
            for rank, (_, row) in enumerate(_slice_top_df(m_df, pred_limit).iterrows(), 1):
                name_val = row.get('name', 'Unknown')
                name_str = str(name_val)[:16] if pd.notna(name_val) else "Unknown"

                _reg_s = _format_strategy_pct(row.get('reg_score', 0.0), 0.0, 4)
                _srg_s = _format_strategy_pct(row.get('surge_score', 0.0), 0.0, 4)
                _ll_s  = _format_strategy_pct(row.get('ll_score', 0.0), 0.0, 4)
                _vcpr_s = _format_strategy_pct(row.get('vcp_rule_score', 0.0), 0.0, 5)
                _vcpm_s = _format_strategy_pct(row.get('vcp_ml_score', 0.0), 0.0, 5)
                _lstm_s = _format_strategy_pct(row.get('lstm_score', 0.0), 0.0, 4)
                _sa_s  = _format_strategy_pct(row.get('stat_arb_score', 0.0), 0.0, 5)
                _sec_s = _format_strategy_pct(row.get('sector_score', 0.0), 0.0, 5)
                _rim_s = _format_strategy_pct(row.get('rim_score', 0.0), 0.0, 4)
                _ev_s  = _format_strategy_pct(row.get('event_score', 0.0), 0.0, 5)
                _mq_s  = _format_strategy_pct(row.get('mq_score', 0.0), 0.0, 4)
                _iv_s  = _format_strategy_pct(row.get('iv_skew_score', 0.0), 0.0, 5)
                _of_s  = _format_strategy_pct(row.get('order_flow_score', 0.0), 0.0, 4)
                _rev_s = _format_strategy_pct(row.get('reversal_score', 0.0), 0.0, 4)
                _arm_s = _format_strategy_pct(row.get('arm_score', 0.0), 0.0, 4)
                _crd_s = _format_strategy_pct(row.get('card_score', 0.0), 0.0, 5)
                _lat_s = _format_strategy_pct(row.get('latr_score', 0.0), 0.0, 4)
                _ifs_s = _format_strategy_pct(row.get('inst_foreign_sector_score', 0.0), 0.0, 4)
                _sc_s  = _format_strategy_pct(row.get('supply_chain_score', 0.0), 0.0, 6)
                _nlp_s = _format_strategy_pct(row.get('sentiment_score', 0.0), 0.0, 4)
                _fn_s  = _format_strategy_pct(row.get('factor_neutralized_score', row.get('neutralized_score', 0.0)), 0.0, 7)
                _vt_s  = _format_strategy_pct(row.get('vol_target_score', 0.0), 0.0, 5)
                _mic_s = _format_strategy_pct(row.get('microstructure_score', 0.0), 0.0, 5)
                _aq_s  = _format_strategy_pct(row.get('accruals_quality_score', 0.0), 0.0, 7)
                _sq_s  = _format_strategy_pct(row.get('short_squeeze_score', 0.0), 0.0, 4)
                _vu_s  = _format_strategy_pct(row.get('valueup_catalyst_score', 0.0), 0.0, 7)
                _te_s  = _format_strategy_pct(row.get('trend_efficiency_score', 0.0), 0.0, 8)
                _gs_s  = _format_strategy_pct(row.get('gamma_squeeze_score', 0.0), 0.0, 7)
                _ib_s  = _format_strategy_pct(row.get('insider_buying_score', 0.0), 0.0, 7)
                _dp_s  = _format_strategy_pct(row.get('darkpool_score', row.get('hft_score', 0.0)), 0.0, 8)
                _et_s  = _format_strategy_pct(row.get('earnings_tone_drift_score', 0.0), 0.0, 9)
                _cas_s = _format_strategy_pct(row.get('cross_asset_spillover_score', 0.0), 0.0, 9)
                _scg_s = _format_strategy_pct(row.get('supply_chain_gnn_score', 0.0), 0.0, 7)
                _reb_s = _format_strategy_pct(row.get('range_expansion_score', 0.0), 0.0, 8)
                _dc_s  = _format_strategy_pct(row.get('dual_correction_score', 0.0), 0.0, 8)
                _ir_s  = _format_strategy_pct(row.get('index_rebalance_score', 0.0), 0.0, 8)
                _og_s  = _format_strategy_pct(row.get('overnight_gap_score', 0.0), 0.0, 7)

                f.write(
                    f"{rank:<5}{row['symbol']:<10}{name_str:<18}"
                    f"{row['ensemble_score']*100:>10.1f}%{row['ensemble_expected_return']:>12.2f}%"
                    f"{_reg_s}{_srg_s}{_ll_s}{_vcpr_s}{_vcpm_s}{_lstm_s}{_sa_s}{_sec_s}{_rim_s}{_ev_s}{_mq_s}{_iv_s}{_of_s}{_rev_s}{_arm_s}{_crd_s}{_lat_s}{_ifs_s}"
                    f"{_sc_s}{_nlp_s}{_fn_s}{_vt_s}{_mic_s}{_aq_s}{_sq_s}{_vu_s}{_te_s}{_gs_s}{_ib_s}{_dp_s}{_et_s}{_cas_s}{_scg_s}{_reb_s}{_dc_s}{_ir_s}{_og_s}\n"
                )
            f.write("\n")
        if macro_warnings:
            f.write("--- Data Quality Notes (auto-detected) ---\n")
            for _dw in macro_warnings:
                f.write(f"  [WARN] {_dw}\n")
            f.write("  All sanitized values shown above; raw fallback defaults applied for corrupted series.\n")
            f.write("  Run: trading_system/validate_macro.py for offline DB cross-check.\n")
    logger.info(f"Saved ensemble predictions ({len(ensemble_df)} symbols) to {ensemble_output_path}")

    # Per-market suffix files for GHA artifact merge (merge_ensemble_predictions reads ensemble_predictions_{MARKET}.txt)
    for _m in _get_target_markets_to_save(df=ensemble_df_merged, universe=universe):
        _m_df = ensemble_df_merged[ensemble_df_merged['market'] == _m].sort_values(by='ensemble_score', ascending=False)
        if _m_df.empty:
            continue
        _mkt_ens_path = os.path.join(result_dir, f"ensemble_predictions_{_m}.txt")
        with open(_mkt_ens_path, "w", encoding="utf-8") as _mf:
            _mf.write(f"=== Dynamic Multi-Strategy Ensemble Predictions ({len(ensemble_weights)} Strategies) ===\n")
            _mf.write(f"Date: {kst_now_str}\n\n")
            _mf.write("\n=========================================\n")
            _m_ens_header = f"[{_m}] All Ensemble Picks ({len(_m_df)} symbols) (Target Horizon: 20D Expected Return)\n" if is_all_pred else f"[{_m}] Top {_TOP_N} Ensemble Picks (Target Horizon: 20D Expected Return)\n"
            _mf.write(_m_ens_header)
            _mf.write("=========================================\n")
            _mf.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Exp Ret(20D)':<14}{'Reg':<5}{'Srg':<5}{'L-L':<5}{'VCP-R':<6}{'VCP-M':<6}{'LSTM':<5}{'S-Arb':<6}{'Sec-R':<6}{'RIM':<5}{'Event':<6}{'MQ':<5}{'IV-Sk':<6}{'Flow':<5}{'Rev':<5}{'ARM':<5}{'CARD':<6}{'LATR':<5}{'IFS':<5}{'Supply':<7}{'NLP':<5}{'Neutral':<8}{'Vol-T':<6}{'Micro':<6}{'Accrual':<8}{'S-Sq':<5}{'ValueUp':<8}{'TrendEff':<9}{'GammaSq':<8}{'Insider':<8}{'Darkpool':<9}{'ToneDrift':<10}{'Spillover':<10}{'SC-GNN':<8}{'RangeExp':<9}{'DualCorr':<9}{'IdxRebal':<9}{'OverGap':<8}\n")
            _mf.write("-" * 333 + "\n")
            for _rank, (_, _row) in enumerate(_slice_top_df(_m_df, pred_limit).iterrows(), 1):
                _name_str = str(_row['name'])[:16] if pd.notna(_row['name']) else "Unknown"

                _reg_s = _format_strategy_pct(_row.get('reg_score', 0.0), 0.0, 4)
                _srg_s = _format_strategy_pct(_row.get('surge_score', 0.0), 0.0, 4)
                _ll_s  = _format_strategy_pct(_row.get('ll_score', 0.0), 0.0, 4)
                _vcpr_s = _format_strategy_pct(_row.get('vcp_rule_score', 0.0), 0.0, 5)
                _vcpm_s = _format_strategy_pct(_row.get('vcp_ml_score', 0.0), 0.0, 5)
                _lstm_s = _format_strategy_pct(_row.get('lstm_score', 0.0), 0.0, 4)
                _sa_s  = _format_strategy_pct(_row.get('stat_arb_score', 0.0), 0.0, 5)
                _sec_s = _format_strategy_pct(_row.get('sector_score', 0.0), 0.0, 5)
                _rim_s = _format_strategy_pct(_row.get('rim_score', 0.0), 0.0, 4)
                _ev_s  = _format_strategy_pct(_row.get('event_score', 0.0), 0.0, 5)
                _mq_s  = _format_strategy_pct(_row.get('mq_score', 0.0), 0.0, 4)
                _iv_s  = _format_strategy_pct(_row.get('iv_skew_score', 0.0), 0.0, 5)
                _of_s  = _format_strategy_pct(_row.get('order_flow_score', 0.0), 0.0, 4)
                _rev_s = _format_strategy_pct(_row.get('reversal_score', 0.0), 0.0, 4)
                _arm_s = _format_strategy_pct(_row.get('arm_score', 0.0), 0.0, 4)
                _crd_s = _format_strategy_pct(_row.get('card_score', 0.0), 0.0, 5)
                _lat_s = _format_strategy_pct(_row.get('latr_score', 0.0), 0.0, 4)
                _ifs_s = _format_strategy_pct(_row.get('inst_foreign_sector_score', 0.0), 0.0, 4)
                _sc_s  = _format_strategy_pct(_row.get('supply_chain_score', 0.0), 0.0, 6)
                _nlp_s = _format_strategy_pct(_row.get('sentiment_score', 0.0), 0.0, 4)
                _fn_s  = _format_strategy_pct(_row.get('factor_neutralized_score', _row.get('neutralized_score', 0.0)), 0.0, 7)
                _vt_s  = _format_strategy_pct(_row.get('vol_target_score', 0.0), 0.0, 5)
                _mic_s = _format_strategy_pct(_row.get('microstructure_score', 0.0), 0.0, 5)
                _aq_s  = _format_strategy_pct(_row.get('accruals_quality_score', 0.0), 0.0, 7)
                _sq_s  = _format_strategy_pct(_row.get('short_squeeze_score', 0.0), 0.0, 4)
                _vu_s  = _format_strategy_pct(_row.get('valueup_catalyst_score', 0.0), 0.0, 7)
                _te_s  = _format_strategy_pct(_row.get('trend_efficiency_score', 0.0), 0.0, 8)
                _gs_s  = _format_strategy_pct(_row.get('gamma_squeeze_score', 0.0), 0.0, 7)
                _ib_s  = _format_strategy_pct(_row.get('insider_buying_score', 0.0), 0.0, 7)
                _dp_s  = _format_strategy_pct(_row.get('darkpool_score', _row.get('hft_score', 0.0)), 0.0, 8)
                _et_s  = _format_strategy_pct(_row.get('earnings_tone_drift_score', 0.0), 0.0, 9)
                _cas_s = _format_strategy_pct(_row.get('cross_asset_spillover_score', 0.0), 0.0, 9)
                _scg_s = _format_strategy_pct(_row.get('supply_chain_gnn_score', 0.0), 0.0, 7)
                _reb_s = _format_strategy_pct(_row.get('range_expansion_score', 0.0), 0.0, 8)
                _dc_s  = _format_strategy_pct(_row.get('dual_correction_score', 0.0), 0.0, 8)
                _ir_s  = _format_strategy_pct(_row.get('index_rebalance_score', 0.0), 0.0, 8)
                _og_s  = _format_strategy_pct(_row.get('overnight_gap_score', 0.0), 0.0, 7)

                _mf.write(
                    f"{_rank:<5}{_row['symbol']:<10}{_name_str:<18}"
                    f"{_row['ensemble_score']*100:>10.1f}%{_row['ensemble_expected_return']:>12.2f}%"
                    f"{_reg_s}{_srg_s}{_ll_s}{_vcpr_s}{_vcpm_s}{_lstm_s}{_sa_s}{_sec_s}{_rim_s}{_ev_s}{_mq_s}{_iv_s}{_of_s}{_rev_s}{_arm_s}{_crd_s}{_lat_s}{_ifs_s}"
                    f"{_sc_s}{_nlp_s}{_fn_s}{_vt_s}{_mic_s}{_aq_s}{_sq_s}{_vu_s}{_te_s}{_gs_s}{_ib_s}{_dp_s}{_et_s}{_cas_s}{_scg_s}{_reb_s}{_dc_s}{_ir_s}{_og_s}\n"
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
                for rank, (_, row) in enumerate(_slice_top_df(df_lstm, pred_limit).iterrows(), 1):
                    name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                    f_out.write(f"{rank:<5}{row['symbol']:<10}{name_str:<18}{str(row['market']):<10}{row['lstm_score']*100:>12.1f}%\n")

            with open(lstm_output_path, "w", encoding="utf-8") as f:
                _write_lstm_file(f, lstm_merged)
            logger.info(f"Saved LSTM deep learning predictions ({len(lstm_merged)} symbols) to {lstm_output_path}")

            for _m in _get_target_markets_to_save(df=lstm_merged, universe=universe):
                _m_df = lstm_merged[lstm_merged['market'] == _m]
                if _m_df.empty:
                    continue
                with open(os.path.join(result_dir, f"lstm_predictions_{_m}.txt"), "w", encoding="utf-8") as _mf:
                    _write_lstm_file(_mf, _m_df)
    except Exception as _lstm_e:
        logger.warning(f"LSTM prediction standalone file save skipped: {_lstm_e}")


    logger.info("Running Portfolio Position Sizing allocation on Ensemble expectancies...")
    # Prepare the input DataFrame expected by PortfolioAllocator: ['symbol', 'market', 20]
    # NOTE: 'market' must be included so the Layer-1 Market Budget is applied per
    # market; without it every symbol defaulted to KOSPI and the top-down layer
    # silently degenerated into a single-market budget.
    src_ens = ensemble_df_merged if 'ensemble_df_merged' in locals() and not ensemble_df_merged.empty else ensemble_df
    ensemble_for_alloc = src_ens[['symbol', 'market', 'ensemble_expected_return']].rename(
        columns={'ensemble_expected_return': 20}
    )
    if 'unified_alloc_df' in locals() and isinstance(unified_alloc_df, pd.DataFrame) and not unified_alloc_df.empty:
        alloc_df = unified_alloc_df.copy()
        logger.info("[Portfolio Allocation] Using Unified Institutional Multi-Model Allocator results for reporting")
    else:
        allocator = PortfolioAllocator(target_horizon=20, max_total_allocation=max_alloc)
        alloc_df = allocator.allocate(ensemble_for_alloc, infer_data_dict, total_portfolio_value=cfg.portfolio_capital_krw, use_hrp=True, regime=current_2d_regime)

    if not alloc_df.empty:
        cols_to_drop = [c for c in ['name', 'market'] if c in alloc_df.columns]
        alloc_df_clean = alloc_df.drop(columns=cols_to_drop) if cols_to_drop else alloc_df
        target_cols = [c for c in ['name', 'market'] if c in universe.columns]
        alloc_df = alloc_df_clean.merge(universe[['symbol'] + target_cols], on='symbol', how='left')
        if 'market' not in alloc_df.columns:
            alloc_df['market'] = alloc_df['symbol'].map(lambda s: 'KOSPI' if str(s).isdigit() else 'SP500')
        if 'name' not in alloc_df.columns:
            alloc_df['name'] = alloc_df['symbol']
        alloc_output_path = os.path.join(result_dir, "portfolio_allocation.txt")
        with open(alloc_output_path, "w", encoding="utf-8") as f:
            f.write("=== Portfolio Allocation Recommendations (Ensemble Kelly/Sharpe Optimized) ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Total Capital: {cfg.portfolio_capital_krw:,.0f} KRW\n")
            f.write("Target Horizon: 20d\n\n")
            f.write(f"Current Market Regime Detected: {current_regime_label} (Code: {current_regime})\n")
            f.write(f"Maximum Total Allocation Allowed: {max_alloc*100:.1f}%\n\n")

            f.write(f"{'No.':<4} {'Symbol':<12} {'Name':<18} {'Market':<12} {'Shares':<9} {'Lot':<5} {'Return':<8} {'Vol':<8} {'Weight':<9} {'Amount':<14}\n")
            f.write("-" * 105 + "\n")
            for rank, (_, row) in enumerate(alloc_df.iterrows(), 1):
                name_str = str(row['name'])[:16] if pd.notna(row['name']) else "Unknown"
                sh_val = int(row.get('shares', 0)) if pd.notna(row.get('shares')) else 0
                lot_val = int(row.get('lot_size', 1)) if pd.notna(row.get('lot_size')) else 1
                f.write(f"{rank:<4} {row['symbol']:<12} {name_str:<18} {str(row['market']):<12} {sh_val:>8,d} {lot_val:>4d} {row['predicted_return']:>7.2f}% {row['volatility']*100:>7.2f}% {row['weight']*100:>8.2f}% {row['allocation_amount']:>13,.0f}\n")

            allocated_weight = alloc_df['weight'].sum()
            cash_weight = 1.0 - allocated_weight
            cash_amount = cash_weight * cfg.portfolio_capital_krw
            f.write("-" * 105 + "\n")
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

        # ── Phase 6-E: Dispatch Telegram Signal Card Alert ───────────────────
        try:
            from src.execution.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier()
            if notifier.is_enabled() and 'ensemble_df' in locals() and ensemble_df is not None and not ensemble_df.empty:
                sent_ok = notifier.send_top_recommendations_card(
                    ensemble_df,
                    regime_name=str(current_2d_regime),
                    date_str=date_str
                )
                if sent_ok:
                    logger.info("[6-E] Dispatched Telegram Signal Cards for TOP 5 recommendations.")
        except Exception as _tg_e:
            logger.warning(f"[6-E] Telegram signal card dispatch skipped: {_tg_e}")
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
        "lstm_predictions.txt",
        "stat_arb_predictions.txt",
        "sector_predictions.txt",
        "rim_predictions.txt",
        "event_driven_predictions.txt",
        "mq_factor_predictions.txt",
        "iv_skew_predictions.txt",
        "order_flow_predictions.txt",
        "short_term_reversal_predictions.txt",
        "arm_factor_predictions.txt",
        "card_factor_predictions.txt",
        "latr_factor_predictions.txt",
        "inst_foreign_sector_predictions.txt",
        "supply_chain_predictions.txt",
        "sentiment_predictions.txt",
        "factor_neutralized_predictions.txt",
        "vol_target_predictions.txt",
        "microstructure_predictions.txt",
        "accruals_quality_predictions.txt",
        "short_squeeze_predictions.txt",
        "valueup_catalyst_predictions.txt",
        "trend_efficiency_predictions.txt",
        "gamma_squeeze_predictions.txt",
        "insider_buying_predictions.txt",
        "darkpool_predictions.txt",
        "earnings_tone_drift_predictions.txt",
        "ensemble_predictions.txt",
        "strategy_data_coverage_report.txt",
        "portfolio_allocation.txt",
    ]
    critical_files = ["pipeline_result.txt", "surge_predictions.txt", "ensemble_predictions.txt"]
    _verification_failures = []
    for filename in verification_files:
        filepath = os.path.join(result_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Verification failed: Output file {filename} does not exist.")
            if filename in critical_files:
                _verification_failures.append(f"Critical output file {filename} was not generated.")
        elif os.path.getsize(filepath) == 0:
            logger.warning(f"Verification failed: Output file {filename} is empty.")
            if filename in critical_files:
                _verification_failures.append(f"Critical output file {filename} is 0 bytes.")
        else:
            logger.info(f"Verification check: Output file {filename} exists and is not empty.")
    if _verification_failures:
        raise RuntimeError(f"Pipeline verification failed: {'; '.join(_verification_failures)}")

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
                    # Live-money guard: exactly-zero expected returns for every
                    # horizon/symbol is a model-failure signature, not a market
                    # condition. Fail loudly so the day is not released.
                    raise RuntimeError("Pipeline verification failed: All expected returns in pipeline_result.txt are 0.0.")
                else:
                    logger.info("Verification check: Found non-zero expected returns in pipeline_result.txt.")
            else:
                logger.warning("Verification failed: Could not parse expected returns from pipeline_result.txt.")
        except Exception as e:
            logger.warning(f"Verification failed: Error reading/parsing pipeline_result.txt: {e}")

        # Finalize pipeline run tracking in DB
        if current_run_id and storage is not None:
            try:
                total_syms = len(universe) if 'universe' in locals() and universe is not None else 0
                dur_secs = time.time() - _pipeline_start_time if '_pipeline_start_time' in locals() else 0.0
                active_mkts = list(universe['market'].unique()) if 'universe' in locals() and universe is not None and 'market' in universe.columns else []
                regime_name = current_2d_regime if 'current_2d_regime' in locals() else ""
                storage.finish_pipeline_run(
                    run_id=current_run_id,
                    status="SUCCESS",
                    markets=active_mkts,
                    total_symbols=total_syms,
                    duration_seconds=dur_secs,
                    regime_detected=regime_name
                )
                storage.prune_old_history(keep_days=180)
                logger.info(f"[RUN HISTORY] Finalized run_id={current_run_id} (duration={dur_secs:.1f}s, symbols={total_syms})")
            except Exception as _fin_e:
                logger.warning(f"[RUN HISTORY] Failed to finalize pipeline run history: {_fin_e}")

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
        default=None,
        metavar="MARKET",
        help="Market to run inference/preseed on: SP500 / NASDAQ / RUSSELL2000 / KOSPI / KOSDAQ / CHINA / JAPAN / INDIA / EUROPE / VIETNAM / TAIWAN / AUSTRALIA / BRAZIL / HKEX / SINGAPORE / CANADA / ASIA_DEV / ASIA_EMG / COMMODITY / ALL "
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
    parser.add_argument(
        "--prediction-limit",
        "--output-limit",
        default=None,
        metavar="LIMIT",
        help="Number of predictions to output per strategy/market ('100', 'all', or integer. Default: 100)",
    )
    args = parser.parse_args()

    # Apply CLI overrides to environment (pipeline reads from os.environ)
    if args.target:
        os.environ["INFERENCE_TARGET"] = args.target
        logger.info(f"[CLI] INFERENCE_TARGET overridden to: {args.target}")
    if args.prediction_limit:
        os.environ["PREDICTION_OUTPUT_LIMIT"] = str(args.prediction_limit).strip()
        logger.info(f"[CLI] PREDICTION_OUTPUT_LIMIT overridden to: {args.prediction_limit}")
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

    _buttons = [[{"text": "📊 GHA 결과 보기", "url": _gha_url}]] if _gha_url else None

    try:
        execute_prediction_pipeline()
        _elapsed = time.time() - _start

        _cmp_msg = ""
        try:
            _cmp_path = Path(__file__).parent / "result" / "run_comparison.txt"
            if _cmp_path.exists():
                _cmp_raw = _cmp_path.read_text(encoding="utf-8", errors="replace")
                import re
                _new_lines = [l.strip() for l in _cmp_raw.splitlines() if "NEW" in l or "UP" in l or "DOWN" in l][:4]
                if _new_lines:
                    _cmp_msg = "\n\n📈 *이전 대비 TOP 종목 변동 요약:*\n" + "\n".join([f"• {l}" for l in _new_lines])
        except Exception as _cmp_e:
            logger.debug(f"Could not parse run comparison: {_cmp_e}")

        _perf_msg = ""
        _st = None
        try:
            from src.data_layer.indicator_storage import MarketIndicatorStorage
            _db_p = Path(__file__).parent / "market_indicators.db"
            if _db_p.exists():
                _st = MarketIndicatorStorage(db_path=str(_db_p))
                _perf = _st.get_outcome_performance_summary(days=60)
                if _perf.get("evaluated_5d", 0) > 0:
                    _perf_msg = f"\n🎯 *과거 예측 5D 적중률:* {_perf['hit_rate_5d']}% (평균 {'+' if _perf['avg_ret_5d'] > 0 else ''}{_perf['avg_ret_5d']}%)"
        except Exception as _perf_e:
            logger.debug(f"Could not load outcome performance summary: {_perf_e}")
        finally:
            if _st is not None:
                try:
                    _st.close()
                except Exception:
                    pass

        _notify_telegram(
            f"✅ 파이프라인 완료\n"
            f"⏱ 소요시간: {_elapsed / 60:.1f}분\n"
            f"📅 실행시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            f"{_perf_msg}"
            f"{_cmp_msg}",
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

        _notify_telegram(
            f"🚨 파이프라인 실패\n"
            f"⏱ 소요시각: {_elapsed / 60:.1f}분\n"
            f"❌ 오류: {type(_exc).__name__}: {_exc}\n\n"
            f"```\n{_tb_tail}\n```",
            "CRITICAL",
            buttons=_buttons,
        )
        sys.exit(1)

