import os
import sys
import logging
import socket
import time
import threading
from datetime import datetime
from typing import Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import FinanceDataReader as fdr
import yfinance as yf
import warnings

_CPU_WORKERS = max(1, (os.cpu_count() or 4))
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
from src.ai.vcp_ml_predictor import SURGE_HORIZONS
from src.persistence.database import StockPriceDB
from src.risk.position_sizing import PortfolioAllocator
from src.analysis.regime_detector import MarketRegimeDetector
from src.utils.rate_limiter import get_global_rate_limiter
from src.utils.technical_cache import DataFrameCache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result, retry_if_exception_type

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    if market == 'SP500' or market.startswith('NYSE') or market.startswith('NASDAQ'):
        try:
            result = fdr.DataReader(symbol, start=start_date)
        except Exception as e:
            logger.debug(f"Network fetch failed for {symbol} via fdr: {e}")
            raise e
    else:
        # Korean stock: fetch from yfinance with adjusted prices
        suffix = _KR_MARKET_SUFFIX.get(market, '.KS')
        yf_symbol = f"{symbol}{suffix}"
        try:
            df = yf.download(yf_symbol, start=start_date, progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                result = df
        except Exception as e:
            logger.debug(f"Network fetch failed for {yf_symbol} via yfinance: {e}")
            raise e

        # Fallback to FinanceDataReader if yfinance fails
        if result is None or result.empty:
            try:
                result = fdr.DataReader(symbol, start=start_date)
                if result is not None and not result.empty:
                    logger.warning(f"Falling back to unadjusted KRX data for {symbol}")
            except Exception as e:
                logger.debug(f"Network fetch failed for {symbol} via fdr fallback: {e}")
                raise e

    if result is None or result.empty:
        raise ValueError(f"Fetched data for {symbol} is empty or None")

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

            # Wait to respect global rate limit
            get_global_rate_limiter().wait()

            try:
                df = yf.download(yf_tickers, start=fetch_start, progress=False, auto_adjust=True, group_by='ticker')
                if df is not None and not df.empty:
                    for yf_ticker in yf_tickers:
                        sym = ticker_to_sym[yf_ticker]
                        ticker_df = None
                        if len(yf_tickers) == 1:
                            ticker_df = df
                        elif yf_ticker in df.columns.levels[0]:
                            ticker_df = df[yf_ticker].dropna(how='all')

                        if ticker_df is not None and not ticker_df.empty:
                            if isinstance(ticker_df.columns, pd.MultiIndex):
                                ticker_df.columns = ticker_df.columns.droplevel(1)
                            price_db.update_prices(sym, ticker_df)
            except Exception as e:
                logger.warning(f"Failed to download batch: {e}")


def fetch_data_fdr(symbol: str, market: str, start_date: str,
                   price_db: Optional[StockPriceDB] = None, freshness_days: int = 7,
                   update_interval: int = 0) -> pd.DataFrame:
    """Fetch OHLCV data using adjusted prices (수정주가), with caching via TechnicalCache.

    This function first checks the global ``technical_cache`` for a recent DataFrame.
    If a cache miss occurs, it falls back to the DB cache and finally to a network request.
    """
    def _fetch_fallback(s: str, d: str) -> pd.DataFrame:
        global _last_request_time
        # 1. DB cache fallback (if provided)
        if price_db is not None:
            stale = True
            if freshness_days < 0:
                stale = False
            else:
                stale = price_db.needs_update(s, max_age_days=freshness_days, start_date=d)
            if not stale:
                df = price_db.get_prices(s, start_date=d)
                if df is not None and not df.empty:
                    logger.debug(f"Using StockPriceDB cached prices for {s}")
                    return df

            # If it is stale but we already have some cached data, attempt incremental fetch
            if stale:
                cached_df = price_db.get_prices(s, start_date=d)
                if cached_df is not None and not cached_df.empty:
                    latest_date_str = cached_df.index.max().strftime("%Y-%m-%d")
                    # If latest_date is today or later, we don't need to fetch
                    if latest_date_str >= datetime.now().strftime("%Y-%m-%d"):
                        logger.debug(f"Cache for {s} is up to date (latest: {latest_date_str}). Skipping network fetch.")
                        return cached_df

                    logger.debug(f"Fetching incremental prices for {s} from {latest_date_str} to present...")
                    try:
                        # Rate limit
                        if update_interval > 0:
                            now = time.time()
                            with _rate_lock:
                                scheduled = max(_last_request_time + update_interval, now)
                                sleep_sec = scheduled - now
                                _last_request_time = scheduled
                            if sleep_sec > 0:
                                logger.debug(f"Rate limit: waiting {sleep_sec:.1f}s before {s}")
                                time.sleep(sleep_sec)

                        new_df = _fetch_data_fdr_network(s, market, latest_date_str)
                        if new_df is not None and not new_df.empty:
                            price_db.update_prices(s, new_df)
                            merged_df = pd.concat([cached_df, new_df])
                            merged_df = merged_df[~merged_df.index.duplicated(keep='last')].sort_index()
                            logger.debug(f"Successfully updated cache and merged for {s}")
                            return merged_df
                    except Exception as e:
                        logger.warning(f"Failed to fetch incremental data for {s}, falling back to full fetch: {e}")

        # 2. Rate limit before network request (global)
        if update_interval > 0:
            now = time.time()
            with _rate_lock:
                scheduled = max(_last_request_time + update_interval, now)
                sleep_sec = scheduled - now
                _last_request_time = scheduled
            if sleep_sec > 0:
                logger.debug(f"Rate limit: waiting {sleep_sec:.1f}s before {s}")
                time.sleep(sleep_sec)

        # 3. Network fetch
        try:
            result = _fetch_data_fdr_network(s, market, d)
        except Exception as e:
            logger.warning(f"Failed to fetch data for {s} after retries: {e}")
            result = None

        # 4. Store in DB cache
        if result is not None and not result.empty and price_db is not None:
            try:
                price_db.update_prices(s, result)
            except Exception as e:
                logger.debug(f"Failed to cache prices for {s}: {e}")
        return result

    # 0. TechnicalCache lookup (TTL based)
    result = technical_cache.get_or_compute(
        symbol,
        start_date,
        _fetch_fallback
    )
    return result


# 16 Global indicator & Sector ETF tickers → feature column names
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
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=False
)
def _download_indicator_network(ticker: str, start_date: str) -> pd.DataFrame:
    # Coordinate indicator fetch rate limiting
    get_global_rate_limiter().wait()
    try:
        raw = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.droplevel(1)
            return raw
    except Exception as e:
        logger.debug(f"Network error downloading indicator {ticker}: {e}")
        raise e
    raise ValueError(f"Downloaded indicator {ticker} is empty or None")


def fetch_indicator_history(start_date: str, price_db: Optional[StockPriceDB] = None,
                            freshness_days: int = 7) -> pd.DataFrame:
    """Download 8 global indicator tickers in parallel, return single DataFrame.

    Returns: DataFrame with DatetimeIndex and columns = _INDICATOR_TICKERS.values()
    """
    def _fetch_one(ticker: str, col_name: str):
        df = None
        if price_db is not None:
            stale = True
            if freshness_days < 0:
                stale = False
            else:
                stale = price_db.needs_update(ticker, max_age_days=freshness_days,
                                              start_date=start_date)
            if not stale:
                df = price_db.get_prices(ticker, start_date=start_date)

            # Incremental fetch for indicator if stale
            if stale:
                cached_df = price_db.get_prices(ticker, start_date=start_date)
                if cached_df is not None and not cached_df.empty:
                    latest_date_str = cached_df.index.max().strftime("%Y-%m-%d")
                    if latest_date_str >= datetime.now().strftime("%Y-%m-%d"):
                        df = cached_df
                    else:
                        logger.debug(f"Fetching incremental indicator {ticker} from {latest_date_str}...")
                        try:
                            new_df = _download_indicator_network(ticker, latest_date_str)
                            if new_df is not None and not new_df.empty:
                                price_db.update_prices(ticker, new_df)
                                merged_df = pd.concat([cached_df, new_df])
                                merged_df = merged_df[~merged_df.index.duplicated(keep='last')].sort_index()
                                df = merged_df
                        except Exception as e:
                            logger.warning(f"Failed to fetch incremental indicator {ticker}, falling back to full fetch: {e}")

        if freshness_days < 0 and (df is None or df.empty):
            return (col_name, pd.Series(dtype=float))
        if df is None or df.empty:
            try:
                df = _download_indicator_network(ticker, start_date)
                if df is not None and not df.empty and price_db is not None:
                    try:
                        price_db.update_prices(ticker, df)
                    except Exception as ex:
                        logger.debug(f"Failed to cache indicator {ticker}: {ex}")
            except Exception as e:
                logger.debug(f"Failed to fetch indicator {ticker} after retries: {e}")
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
    - Volume=0: trading halted (거래정지)
    - KRX-ADMINISTRATIVE: under administration (관리종목)

    Returns empty set on failure (e.g. offline mode).
    """
    excluded = set()
    try:
        try:
            krx = fdr.StockListing('KRX')
            halted = set(krx[krx['Volume'] == 0]['Code'].tolist())
            if halted:
                logger.info(f"Excluding {len(halted)} halted KRX stocks (Volume=0)")
            excluded |= halted
        except Exception as e:
            logger.debug(f"Could not fetch KRX listing: {e}")
        try:
            admin = set(fdr.StockListing('KRX-ADMINISTRATIVE')['Code'].tolist())
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
        from src.ai.vcp_ml_predictor import VCPSurgePredictor
        vcp_ml = VCPSurgePredictor()

        # Verify that models are actually loaded for regression, surge, and VCP ML
        regression_loaded = any(len(mkt_dict) > 0 for mkt_dict in model.models.values()) or any(len(mkt_dict) > 0 for mkt_dict in model.lgb_models.values())
        surge_loaded = any(len(mkt_dict) > 0 for mkt_dict in model.surge_models.values())
        vcp_loaded = any(len(mkt_dict) > 0 for mkt_dict in vcp_ml.models.values()) or any(len(mkt_dict) > 0 for mkt_dict in vcp_ml.lgb_models.values())

        if regression_loaded and surge_loaded and vcp_loaded:
            logger.info("Pre-trained models found and loaded successfully. Skipping model training phase.")
            should_skip = True
        else:
            logger.warning("Missing or incomplete pre-trained models on disk. Falling back to training.")
            model.models = {}
            model.surge_models = {}
            vcp_ml = None

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

        sp500_sample = cfg.resolve_sample_size(cfg.train_sample_sp500, len(sp500_symbols))
        krx_sample = cfg.resolve_sample_size(cfg.train_sample_krx, len(krx_symbols))

        if cfg.debug_mode:
            sp500_sample = min(5, sp500_sample)
            krx_sample = min(5, krx_sample)
            logger.info(f"[DEBUG MODE] Overriding training samples: SP500={sp500_sample}, KRX={krx_sample}")

        def _safe_sample(population, k):
            if k >= len(population):
                return list(population)
            return random.sample(population, k)

        train_krx_overall = _safe_sample(krx_symbols, krx_sample)
        train_krx_set = set(train_krx_overall)
        train_symbols = _safe_sample(sp500_symbols, sp500_sample) + train_krx_overall

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
                if done_count % 100 == 0:
                    logger.info(f"Training data fetch progress: {done_count}/{len(train_symbols)} ({len(train_data_dict)} loaded)")

        # Wait for fundamentals fetch to complete before merging
        if train_symbols:
            logger.info("Waiting for training fundamentals fetch to complete...")
            t.join()

        # Merge fundamentals (parallel)
        threading.Lock()
        def _merge_one(sym: str, df):
            try:
                merged = model.merge_fundamentals(sym, df, storage)
                return (sym, merged)
            except Exception as e:
                logger.debug(f"Failed to merge fundamentals for {sym}: {e}")
                return (sym, None)

        with ThreadPoolExecutor(max_workers=_CPU_WORKERS * 2) as pool:
            futures = {pool.submit(_merge_one, sym, df): sym for sym, df in train_data_dict.items()}
            for f in as_completed(futures):
                sym, merged = f.result()
                if merged is not None:
                    train_data_dict[sym] = merged
                else:
                    train_data_dict.pop(sym, None)

        df_train = model.prepare_training_data(train_data_dict, indicator_train)

        # 7. Train XGBoost models per market (KOSPI/KOSDAQ/KONEX/SP500)
        if not df_train.empty and 'symbol' in df_train.columns:
            train_symbol_set = set(df_train['symbol'])
            # Build per-market train DataFrames from the merged df_train
            market_dfs = {}
            for m_name, m_symbols in [('sp500', train_sp500), ('kospi', train_kospi),
                                       ('kosdaq', train_kosdaq), ('konex', train_konex)]:
                active = [s for s in m_symbols if s in train_symbol_set]
                m_df = df_train[df_train['symbol'].isin(active)] if active else pd.DataFrame()
                if not m_df.empty:
                    logger.info(f"Training data for {m_name}: {len(m_df)} rows, {m_df['symbol'].nunique()} symbols")
                market_dfs[m_name] = m_df
        else:
            market_dfs = {m: pd.DataFrame() for m in ['sp500', 'kospi', 'kosdaq', 'konex']}

        # S8 fix: ThreadPoolExecutor avoids pickle serialization overhead of ProcessPool.
        # XGBoost/LightGBM release the GIL during training, so threads are efficient here.
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
        if not df_train.empty and len(df_train) > 1000:
            model.compute_lead_lag(df_train, indicator_df=indicator_train)

        # 7d. Train VCP ML surge models (4 markets, parallel inside)
        from src.ai.vcp_ml_predictor import VCPSurgePredictor
        vcp_ml = VCPSurgePredictor()
        if train_data_dict:
            vcp_ml.train(train_data_dict, indicator_train, universe)

    # 8. Fetch fundamentals for all inference symbols (non-blocking background)
    all_symbols = sp500_symbols + krx_symbols

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

    if all_symbols:
        t2 = threading.Thread(target=_bg_fundamentals, args=(all_symbols, "inference"))
        t2.start()

    # Prefetch inference data in batches to optimize performance
    prefetch_prices_batch(all_symbols, symbol_market, start_date_infer, price_db, freshness)

    # 9. Fetch recent data for ALL symbols to run inference
    logger.info(f"Fetching inference data for ALL {len(all_symbols)} symbols (update_interval={update_interval}s)...")
    infer_data_dict = {}
    count = 0
    with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
        future_to_sym = {}
        for sym in all_symbols:
            sym_market = symbol_market.get(sym, 'SP500' if sym in sp500_symbols else 'KRX')
            future_to_sym[executor.submit(fetch_data_fdr, sym, sym_market, start_date_infer, price_db, freshness, update_interval)] = sym

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
            if count % 500 == 0:
                logger.info(f"Fetched inference data: {count}/{len(all_symbols)} ({len(infer_data_dict)} loaded)")

    # Filter out symbols with insufficient data (< 200 days)
    before = len(infer_data_dict)
    infer_data_dict = {s: df for s, df in infer_data_dict.items()
                       if df is not None and len(df) >= 200}
    dropped = before - len(infer_data_dict)
    if dropped:
        logger.info(f"Excluded {dropped} symbols with insufficient inference data (< 200 days)")

    # Wait for inference fundamentals fetch to complete before merging
    if all_symbols:
        logger.info("Waiting for inference fundamentals fetch to complete...")
        t2.join()

    # Merge fundamentals (parallel)
    def _merge_infer_one(sym: str, df):
        try:
            merged = model.merge_fundamentals(sym, df, storage)
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
    res_df, surge_df = model.predict_all(infer_data_dict, indicator_infer, symbol_to_market_lower)

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

    # Save Stat-Arb predictions to separate file
    stat_arb_output_path = os.path.join(result_dir, "stat_arb_predictions.txt")
    with open(stat_arb_output_path, "w", encoding="utf-8") as f:
        f.write("=== Statistical Arbitrage Pairs & Signals ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total pairs found: {len(stat_arb_pairs)}\n\n")
        f.write(f"{'Pair':<25}{'Z-Score':<10}{'Correlation':<15}{'Beta':<10}{'Signal':<20}\n")
        f.write("-" * 80 + "\n")
        for p in stat_arb_pairs:
            pair_str = f"{p['pair'][0]}-{p['pair'][1]}"
            f.write(f"{pair_str:<25}{p['z_score']:<10}{p['correlation']:<15}{p['beta']:<10}{p['signal']:<20}\n")
    logger.info(f"Saved Statistical Arbitrage pairs ({len(stat_arb_pairs)}) to {stat_arb_output_path}")

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
    logger.info(f"==> CURRENT MARKET REGIME DETECTED: {current_regime_label} ({current_regime})")

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

    # Save full inference results for ALL symbols to file
    output_path = os.path.join(result_dir, "pipeline_result.txt")
    market_syms = _market_symbols(universe)
    symbol_to_name = dict(zip(universe['symbol'], universe['name']))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== Full Pipeline Inference Results ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total symbols: {len(res_df)}\n\n")
        krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
        for h in [1, 5, 10, 20, 30, 60, 120, 200]:
            if h not in res_df.columns:
                continue
            sorted_df = res_df.sort_values(by=h, ascending=False)
            f.write(f"{'='*60}\n")
            f.write(f"Horizon: {h}d\n\n")
            for m in krx_markets:
                m_set = market_syms.get(m, set())
                m_df = sorted_df[sorted_df['symbol'].isin(m_set)]
                if m_df.empty:
                    continue
                f.write(f"--- {m} (all {len(m_df)} symbols) ---\n")
                for rank, (_, row) in enumerate(m_df.iterrows(), 1):
                    name = symbol_to_name.get(row['symbol'], "Unknown")
                    f.write(f"  {rank}. {row['symbol']} ({name}): {row[h]*100:+.2f}%\n")
                f.write("\n")
            sp500_set = market_syms.get('SP500', set())
            sp500_df = sorted_df[sorted_df['symbol'].isin(sp500_set)]
            if not sp500_df.empty:
                f.write(f"--- S&P 500 (all {len(sp500_df)} symbols) ---\n")
                for rank, (_, row) in enumerate(sp500_df.iterrows(), 1):
                    name = symbol_to_name.get(row['symbol'], "Unknown")
                    f.write(f"  {rank}. {row['symbol']} ({name}): {row[h]*100:+.2f}%\n")
                f.write("\n")
    logger.info(f"Saved full pipeline result ({len(res_df)} symbols) to {output_path}")

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
    if not surge_df.empty:
        surge_output_path = os.path.join(result_dir, "surge_predictions.txt")
        with open(surge_output_path, "w", encoding="utf-8") as f:
            f.write("=== Surge Detection Results (>= 20% return) ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Threshold: >= {model.surge_threshold*100:.0f}%\n")
            f.write(f"Total symbols: {len(surge_df)}\n\n")

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
    if not lead_lag_df.empty:
        lead_lag_output_path = os.path.join(result_dir, "lead_lag_predictions.txt")
        lead_lag_df = lead_lag_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
        with open(lead_lag_output_path, "w", encoding="utf-8") as f:
            f.write("=== Lead-Lag Surge Predictions ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Based on today's top {len(model.lead_lag_leaders)} leader stock movements\n\n")
            krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
            for m in krx_markets + ['SP500']:
                m_df = lead_lag_df[lead_lag_df['market'] == m].sort_values(by='lead_lag_score', ascending=False)
                if m_df.empty:
                    continue
                f.write(f"--- {m} Top 20 ---\n")
                for rank, (_, row) in enumerate(m_df.head(20).iterrows(), 1):
                    name = row.get('name', 'Unknown')
                    score = row['lead_lag_score'] * 100
                    f.write(f"  {rank}. [{m}] {row['symbol']} ({name}): {score:.2f}%\n")
                f.write("\n")
            f.write("--- Leaders with highest today return ---\n")
            leader_returns = []
            for sym in model.lead_lag_leaders:
                df = infer_data_dict.get(sym)
                if df is None or len(df) < 2:
                    continue
                close = df['Close']
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                ret = (close.iloc[-1] / close.iloc[-2]) - 1
                leader_returns.append((sym, ret))
            leader_returns.sort(key=lambda x: -x[1])
            symbol_to_name = dict(zip(universe['symbol'], universe['name']))
            for rank, (sym, ret) in enumerate(leader_returns[:10], 1):
                name = symbol_to_name.get(sym, sym)
                f.write(f"  {rank}. {sym} ({name}): +{ret*100:.2f}%\n")
        logger.info(f"Saved lead-lag predictions ({len(lead_lag_df)} symbols) to {lead_lag_output_path}")

    # Save VCP pattern detection results
    if vcp_results:
        vcp_output_path = os.path.join(result_dir, "vcp_patterns.txt")
        vcp_universe_map = {s: (n, m) for s, n, m in zip(universe['symbol'],
                            universe['name'], universe['market'])}
        krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
        with open(vcp_output_path, "w", encoding="utf-8") as f:
            f.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Total VCP patterns found: {len(vcp_results)}\n\n")
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
    if not vcp_ml_df.empty:
        vcp_ml_df = vcp_ml_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left', suffixes=('', '_univ'))
        vcp_ml_output_path = os.path.join(result_dir, "vcp_ml_predictions.txt")
        with open(vcp_ml_output_path, "w", encoding="utf-8") as f:
            f.write("=== VCP ML Surge Predictions ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

            for h in SURGE_HORIZONS:
                col = f'vcp_{h}d'
                if col not in vcp_ml_df.columns:
                    continue
                for market in ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']:
                    m_df = vcp_ml_df[vcp_ml_df['market'] == market].sort_values(by=col, ascending=False)
                    if m_df.empty:
                        if market in ['KOSPI', 'KOSDAQ', 'KONEX']:
                            f.write(f"[{h}일] {market} - (no symbols)\n\n")
                        continue
                    top_n = min(10, len(m_df))
                    f.write(f"[{h}일] {market} TOP {top_n}\n")
                    for rank, (_, row) in enumerate(m_df.head(top_n).iterrows(), 1):
                        name = row.get('name', 'Unknown')
                        prob = row[col] * 100
                        f.write(f"  {rank}. [{market}] {row['symbol']} ({name}): {prob:.1f}%\n")
                    f.write("\n")
        logger.info(f"Saved VCP ML predictions ({len(vcp_ml_df)} symbols) to {vcp_ml_output_path}")

    # 11d. Run Ensemble Scoring
    logger.info("Running Dynamic Multi-Strategy Ensemble scoring...")
    from src.ai.ensemble_scorer import EnsembleScoringEngine
    scorer = EnsembleScoringEngine()

    # default target horizon is 20d
    ensemble_df = scorer.calculate_ensemble_score(
        regime=current_regime,
        regression_df=res_df,
        surge_df=surge_df,
        lead_lag_df=lead_lag_df,
        vcp_ml_df=vcp_ml_df,
        target_horizon=20
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

    ensemble_weights = EnsembleScoringEngine.REGIME_WEIGHTS.get(current_regime, EnsembleScoringEngine.REGIME_WEIGHTS[1])

    ensemble_output_path = os.path.join(result_dir, "ensemble_predictions.txt")
    ensemble_df_merged = ensemble_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')

    with open(ensemble_output_path, "w", encoding="utf-8") as f:
        f.write("=== Dynamic Multi-Strategy Ensemble Predictions ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        # 1. Executive Summary & Basis
        f.write("--- Executive Market Summary ---\n")
        f.write(f"Current Market Regime Detected: {current_regime_label} (Code: {current_regime})\n")
        f.write(f"Maximum Total Allocation Allowed: {max_alloc*100:.1f}%\n\n")

        f.write("--- Judgment Basis (Global Macro Indicators) ---\n")
        f.write(f"  S&P 500 (20d Rolling Mean Return) : {sp500_ret_20d:+.3f}% / day\n")
        f.write(f"  S&P 500 (20d Rolling Volatility)  : {sp500_vol_20d:.3f}%\n")
        f.write(f"  KOSPI (20d Rolling Mean Return)   : {kospi_ret_20d:+.3f}% / day\n")
        f.write(f"  KOSPI (20d Rolling Volatility)    : {kospi_vol_20d:.3f}%\n")
        f.write(f"  VIX Index (Fear Gauge)            : {vix_val:.2f}\n")
        f.write(f"  USD/KRW FX Rate                   : {usdkrw_val:,.2f} KRW\n")
        f.write(f"  US 10Y Bond Yield (TNX)           : {us10y_val:.2f}%\n\n")

        f.write("--- Applied Ensemble Strategy Weights ---\n")
        f.write(f"  XGBoost Regression Fundamentals   : {ensemble_weights['regression']*100:.1f}%\n")
        f.write(f"  Surge Classifier (XGBoost)        : {ensemble_weights['surge']*100:.1f}%\n")
        f.write(f"  Index & Sector Lead-Lag Flow      : {ensemble_weights['lead_lag']*100:.1f}%\n")
        f.write(f"  VCP Machine Learning Predictor    : {ensemble_weights['vcp_ml']*100:.1f}%\n\n")

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
            f.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Ensemble Score':<16}{'Expected Return':<18}{'Reg':<8}{'Surge':<8}{'L-L':<8}{'VCP':<8}\n")
            f.write("-" * 99 + "\n")
            for rank, (_, row) in enumerate(m_df.head(20).iterrows(), 1):
                name_str = str(row['name'])[:18] if pd.notna(row['name']) else "Unknown"
                f.write(f"{rank:<5}{row['symbol']:<10}{name_str:<20}{row['ensemble_score']*100:>13.1f}%{row['ensemble_expected_return']:>15.1f}%{row['reg_score']*100:>7.0f}%{row['surge_score']*100:>7.0f}%{row['ll_score']*100:>7.0f}%{row['vcp_ml_score']*100:>7.0f}%\n")
            f.write("\n")
    logger.info(f"Saved ensemble predictions ({len(ensemble_df)} symbols) to {ensemble_output_path}")

    # 11g. Run Portfolio Position Sizing (Ensemble Link)
    logger.info("Running Portfolio Position Sizing allocation on Ensemble expectancies...")
    # Prepare the input DataFrame expected by PortfolioAllocator: ['symbol', 20]
    ensemble_for_alloc = ensemble_df[['symbol', 'ensemble_expected_return']].rename(
        columns={'ensemble_expected_return': 20}
    )
    allocator = PortfolioAllocator(target_horizon=20, max_total_allocation=max_alloc)
    alloc_df = allocator.allocate(ensemble_for_alloc, infer_data_dict, total_portfolio_value=1000000000.0)
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

    return res_df, message_text

if __name__ == "__main__":
    execute_prediction_pipeline()
