import os
import sys
import logging
import socket
import time
import threading
from datetime import datetime
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
from src.persistence.database import StockPriceDB

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# yfinance suffix mapping for Korean stock markets
_KR_MARKET_SUFFIX = {
    'KOSPI': '.KS',
    'KOSDAQ': '.KQ',
    'KONEX': '.KQ',
    'KRX': '.KS',
}


def fetch_data_fdr(symbol: str, market: str, start_date: str,
                   price_db: StockPriceDB = None, freshness_days: int = 7,
                   update_interval: int = 0) -> pd.DataFrame:
    """Fetch OHLCV data using adjusted prices (수정주가), with StockPriceDB cache.

    For US stocks (SP500): uses FinanceDataReader (Yahoo Finance, already adjusted).
    For Korean stocks: uses yfinance with split/dividend-adjusted prices.

    Rate limiting: if update_interval > 0, sleeps that many seconds between
    network requests (global across all threads).
    """
    # 0. StockPriceDB 캐시 조회
    if price_db is not None:
        stale = True
        if freshness_days < 0:
            stale = False
        else:
            stale = price_db.needs_update(symbol, max_age_days=freshness_days,
                                          start_date=start_date)
        if not stale:
            df = price_db.get_prices(symbol, start_date=start_date)
            if not df.empty:
                logger.debug(f"Using cached prices for {symbol}")
                return df
            if freshness_days < 0:
                logger.debug(f"No cached data for {symbol} in offline mode (freshness<0)")
                return None
        # stale or empty cache → fall through to network fetch

    # Rate limit before network request
    if update_interval > 0:
        global _last_request_time
        with _rate_lock:
            elapsed = time.time() - _last_request_time
            if elapsed < update_interval:
                sleep_sec = update_interval - elapsed
                logger.debug(f"Rate limit: waiting {sleep_sec:.1f}s before {symbol}")
                time.sleep(sleep_sec)
            _last_request_time = time.time()

    # 1. Fetch data
    result = None
    if market == 'SP500' or market.startswith('NYSE') or market.startswith('NASDAQ'):
        try:
            result = fdr.DataReader(symbol, start=start_date)
        except Exception as e:
            logger.debug(f"Failed to fetch {symbol} via fdr: {e}")
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
            logger.debug(f"Failed to fetch {yf_symbol} via yfinance: {e}")

        # Fallback to FinanceDataReader if yfinance fails
        if result is None:
            try:
                result = fdr.DataReader(symbol, start=start_date)
                if result is not None and not result.empty:
                    logger.warning(f"Falling back to unadjusted KRX data for {symbol}")
            except Exception as e:
                logger.debug(f"Failed to fetch {symbol} via fdr fallback: {e}")

    # 2. Cache the result in StockPriceDB
    if result is not None and not result.empty and price_db is not None:
        try:
            price_db.update_prices(symbol, result)
        except Exception as e:
            logger.debug(f"Failed to cache prices for {symbol}: {e}")

    return result

# 8 Global indicator tickers → feature column names
_INDICATOR_TICKERS = {
    '^VIX': 'vix_change',
    '^TNX': 'us10y',
    'USDKRW=X': 'usdkrw_change',
    '^GSPC': 'sp500_change',
    'DX-Y.NYB': 'dxy_change',
    'CL=F': 'wti_change',
    '^KS11': 'kospi_change',
    '^KQ11': 'kosdaq_change',
}


def fetch_indicator_history(start_date: str, price_db: StockPriceDB = None,
                            freshness_days: int = 7) -> pd.DataFrame:
    """Download 8 global indicator tickers, compute daily change%, return single DataFrame.

    Returns: DataFrame with DatetimeIndex and columns = _INDICATOR_TICKERS.values()
    """
    combined = {}
    for ticker, col_name in _INDICATOR_TICKERS.items():
        df = None
        # Try cache first
        if price_db is not None:
            if freshness_days < 0:
                stale = False
            else:
                stale = price_db.needs_update(ticker, max_age_days=freshness_days,
                                              start_date=start_date)
            if not stale:
                df = price_db.get_prices(ticker, start_date=start_date)
        # If offline mode (freshness<0), skip network fetch
        if freshness_days < 0 and (df is None or df.empty):
            combined[col_name] = pd.Series(dtype=float)
            continue
        # Fetch from yfinance if no cache
        if df is None or df.empty:
            try:
                raw = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
                if raw is not None and not raw.empty:
                    if isinstance(raw.columns, pd.MultiIndex):
                        raw.columns = raw.columns.droplevel(1)
                    df = raw
                    if price_db is not None:
                        try:
                            price_db.update_prices(ticker, df)
                        except Exception as ex:
                            logger.debug(f"Failed to cache indicator {ticker}: {ex}")
            except Exception as e:
                logger.debug(f"Failed to fetch indicator {ticker}: {e}")
        if df is not None and not df.empty:
            if col_name.endswith('_change'):
                combined[col_name] = df['Close'].pct_change().fillna(0.0) * 100
            else:
                combined[col_name] = df['Close'].ffill().fillna(0.0)

    if not combined:
        logger.warning("No indicator data fetched; returning empty DataFrame")
        return pd.DataFrame()

    result = pd.concat(combined, axis=1)
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()
    logger.info(f"Fetched indicator history: {len(result)} rows x {len(result.columns)} cols")
    return result


def _market_symbols(universe: pd.DataFrame) -> tuple:
    """Return (krx_set, sp500_set) for quick lookup."""
    krx = set(universe[universe['market'] != 'SP500']['symbol'])
    sp500 = set(universe[universe['market'] == 'SP500']['symbol'])
    return krx, sp500

def _fmt_top(df: pd.DataFrame, horizon: int, krx_set: set, sp500_set: set,
             universe: pd.DataFrame, count: int = 10) -> list:
    """Format top-N predictions for a single market segment."""
    lines = []
    for rank, (_, row) in enumerate(df.head(count).iterrows(), 1):
        sym = row['symbol']
        ret = row[horizon] * 100
        name_row = universe[universe['symbol'] == sym]
        name = name_row['name'].values[0] if not name_row.empty else "Unknown"
        marker = name_row['market'].values[0] if not name_row.empty else ""
        lines.append(f"  {rank}. [{marker}] {sym} ({name}): +{ret:.2f}%")
    return lines

def format_prediction_message(res_df: pd.DataFrame, universe: pd.DataFrame) -> str:
    """Format prediction results as a Telegram-friendly message"""
    krx_set, sp500_set = _market_symbols(universe)
    horizons = [1, 5, 10, 20, 30, 60, 120, 200]
    lines = [
        "🤖 *XGBoost 예측 결과*",
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 30,
    ]
    for h in horizons:
        if h not in res_df.columns:
            continue
        sorted_df = res_df.sort_values(by=h, ascending=False)

        krx_df = sorted_df[sorted_df['symbol'].isin(krx_set)]
        sp500_df = sorted_df[sorted_df['symbol'].isin(sp500_set)]

        lines.append(f"\n*{h}일 예상 — KOSPI/KOSDAQ/KONEX TOP 10*")
        lines.extend(_fmt_top(krx_df, h, krx_set, sp500_set, universe, 10))

        lines.append(f"\n*{h}일 예상 — S&P 500 TOP 10*")
        lines.extend(_fmt_top(sp500_df, h, krx_set, sp500_set, universe, 10))

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

    # StockPriceDB 캐시 초기화
    price_db = StockPriceDB(db_path=cfg.stock_price_db_path)
    freshness = cfg.get_freshness_days()

    # 5. Fetch global indicator history for training & inference
    start_date_train = cfg.train_start_date
    start_date_infer = '2025-01-01'
    logger.info("Fetching global indicator history...")
    indicator_train = fetch_indicator_history(start_date_train, price_db, freshness)
    indicator_infer = fetch_indicator_history(start_date_infer, price_db, freshness)
    
    # 6. Prepare Training Data (On-device)
    sp500_symbols = universe[universe['market'] == 'SP500']['symbol'].tolist()
    krx_symbols = universe[universe['market'] != 'SP500']['symbol'].tolist()
    
    # Sample from settings (절대값 / 퍼센트 / "all")
    import random
    seed = cfg.get_train_seed()
    if seed is not None:
        random.seed(seed)

    sp500_sample = cfg.resolve_sample_size(cfg.train_sample_sp500, len(sp500_symbols))
    krx_sample = cfg.resolve_sample_size(cfg.train_sample_krx, len(krx_symbols))

    def _safe_sample(population, k):
        if k >= len(population):
            return list(population)
        return random.sample(population, k)

    train_symbols = _safe_sample(sp500_symbols, sp500_sample) + \
                    _safe_sample(krx_symbols, krx_sample)
    
    # 6. Fetch corporate fundamentals in background (non-blocking)
    import threading
    def _bg_fundamentals(syms, label):
        logger.info(f"[BG] Fetching fundamentals for {label} ({len(syms)} symbols)...")
        try:
            fetch_and_store_fundamentals_batch(syms, symbol_market, storage)
            logger.info(f"[BG] Fundamentals fetch complete for {label}")
        except Exception as e:
            logger.warning(f"[BG] Fundamentals fetch failed for {label}: {e}")
    if train_symbols:
        t = threading.Thread(target=_bg_fundamentals, args=(train_symbols, "training"))
        t.start()
    
    model = OnDevicePredictionModel()
    update_interval = cfg.get_update_interval()
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

    # Merge fundamentals (now DB has real data from background thread)
    for sym in list(train_data_dict.keys()):
        try:
            train_data_dict[sym] = model.merge_fundamentals(sym, train_data_dict[sym], storage)
        except Exception as e:
            logger.debug(f"Failed to merge fundamentals for {sym}: {e}")
            del train_data_dict[sym]

    df_train = model.prepare_training_data(train_data_dict, indicator_train)
    
    # 7. Train XGBoost models per market
    if not df_train.empty and 'symbol' in df_train.columns:
        from src.ai.prediction_model import OnDevicePredictionModel as _OPM
        krx_mask = df_train['symbol'].apply(_OPM.is_krx_symbol)
        sp500_train = df_train[~krx_mask]
        krx_train = df_train[krx_mask]
    else:
        sp500_train = pd.DataFrame()
        krx_train = pd.DataFrame()

    if not sp500_train.empty:
        logger.info(f"Training S&P 500 model ({len(sp500_train)} rows)...")
        model.train(sp500_train, market="sp500")

    if not krx_train.empty:
        logger.info(f"Training KRX model ({len(krx_train)} rows)...")
        model.train(krx_train, market="krx")
    
    # 7b. Train surge detection classifiers (>= 20% return)
    logger.info("Training surge detection models...")
    if not sp500_train.empty:
        model.train_surge(sp500_train, market="sp500")
    if not krx_train.empty:
        model.train_surge(krx_train, market="krx")
    
    # 7c. Compute lead-lag correlation matrix (which stocks follow which)
    if not df_train.empty and len(df_train) > 1000:
        model.compute_lead_lag(df_train, top_leaders=50)
    
    # 8. Fetch fundamentals for all inference symbols (non-blocking background)
    all_symbols = sp500_symbols + krx_symbols
    if all_symbols:
        t2 = threading.Thread(target=_bg_fundamentals, args=(all_symbols, "inference"))
        t2.start()

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

    # Wait for inference fundamentals fetch to complete before merging
    if all_symbols:
        logger.info("Waiting for inference fundamentals fetch to complete...")
        t2.join()

    # Merge fundamentals (now DB has real data from background thread)
    for sym in list(infer_data_dict.keys()):
        try:
            infer_data_dict[sym] = model.merge_fundamentals(sym, infer_data_dict[sym], storage)
        except Exception as e:
            logger.debug(f"Failed to merge fundamentals for {sym}: {e}")
            del infer_data_dict[sym]
                
    # 10. Run predictions (regression + surge, shared feature computation)
    logger.info("Running inference (regression + surge)...")
    res_df, surge_df = model.predict_all(infer_data_dict, indicator_infer)
    
    if res_df.empty:
        logger.error("No predictions made.")
        return None
    logger.info(f"Regression: {len(res_df)} symbols, Surge: {len(surge_df) if not surge_df.empty else 0} symbols")
    
    # 10c. Run lead-lag inference (which stocks may surge based on leader movements)
    logger.info("Running lead-lag inference...")
    lead_lag_df = model.predict_lead_lag(infer_data_dict)
    if not lead_lag_df.empty:
        logger.info(f"Lead-lag predictions generated for {len(lead_lag_df)} symbols")
        
    # 11. Save predictions to DB
    storage.save_predictions(res_df, date_str)
    logger.info(f"Saved predictions to database table 'ai_predictions' for {date_str}.")
    
    # Filter out halted/admin KRX stocks from display output
    excluded_krx = _get_excluded_krx_symbols()
    if excluded_krx:
        before = len(res_df)
        res_df = res_df[~res_df['symbol'].isin(excluded_krx)]
        filtered = before - len(res_df)
        if filtered:
            logger.info(f"Filtered out {filtered} halted/admin KRX stocks from display")
    
    # Build formatted message for Telegram (top-10 per market)
    message_text = format_prediction_message(res_df, universe)
    print(message_text)

    # Save full inference results for ALL symbols to file
    output_path = os.path.join(os.path.dirname(__file__), "pipeline_result.txt")
    krx_set, sp500_set = _market_symbols(universe)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"=== Full Pipeline Inference Results ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total symbols: {len(res_df)}\n\n")
        for h in [1, 5, 10, 20, 30, 60, 120, 200]:
            if h not in res_df.columns:
                continue
            sorted_df = res_df.sort_values(by=h, ascending=False)
            krx_df = sorted_df[sorted_df['symbol'].isin(krx_set)]
            sp500_df = sorted_df[sorted_df['symbol'].isin(sp500_set)]
            f.write(f"{'='*60}\n")
            f.write(f"Horizon: {h}d\n\n")
            f.write(f"--- KOSPI/KOSDAQ/KONEX (all {len(krx_df)} symbols) ---\n")
            for rank, (_, row) in enumerate(krx_df.iterrows(), 1):
                name_row = universe[universe['symbol'] == row['symbol']]
                name = name_row['name'].values[0] if not name_row.empty else "Unknown"
                f.write(f"  {rank}. {row['symbol']} ({name}): {row[h]*100:+.2f}%\n")
            f.write(f"\n--- S&P 500 (all {len(sp500_df)} symbols) ---\n")
            for rank, (_, row) in enumerate(sp500_df.iterrows(), 1):
                name_row = universe[universe['symbol'] == row['symbol']]
                name = name_row['name'].values[0] if not name_row.empty else "Unknown"
                f.write(f"  {rank}. {row['symbol']} ({name}): {row[h]*100:+.2f}%\n")
            f.write("\n")
    logger.info(f"Saved full pipeline result ({len(res_df)} symbols) to {output_path}")

    # Save surge detection results to separate file
    if not surge_df.empty:
        surge_output_path = os.path.join(os.path.dirname(__file__), "surge_predictions.txt")
        with open(surge_output_path, "w", encoding="utf-8") as f:
            f.write("=== Surge Detection Results (>= 20% return) ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Threshold: >= {model.surge_threshold*100:.0f}%\n")
            f.write(f"Total symbols: {len(surge_df)}\n\n")

            # Merge name/market info
            surge_df = surge_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')

            for h in model.surge_horizons:
                col = f'surge_{h}d'
                if col not in surge_df.columns:
                    continue
                sorted_df = surge_df.sort_values(by=col, ascending=False)
                f.write(f"{'='*60}\n")
                f.write(f"[{h}일] Top 20 Surge Candidates\n")
                f.write(f"{'='*60}\n")
                for rank, (_, row) in enumerate(sorted_df.head(20).iterrows(), 1):
                    market_tag = "KRX" if row.get('market', '').startswith('K') else "SP500"
                    name = row.get('name', 'Unknown')
                    prob = row[col] * 100
                    f.write(f"  {rank}. [{market_tag}] {row['symbol']} ({name}): {prob:.1f}%\n")
                f.write("\n")
        logger.info(f"Saved surge predictions ({len(surge_df)} symbols) to {surge_output_path}")

    # Save lead-lag predictions to separate file
    if not lead_lag_df.empty:
        lead_lag_output_path = os.path.join(os.path.dirname(__file__), "lead_lag_predictions.txt")
        lead_lag_df = lead_lag_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
        with open(lead_lag_output_path, "w", encoding="utf-8") as f:
            f.write("=== Lead-Lag Surge Predictions ===\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Based on today's top {len(model.lead_lag_leaders)} leader stock movements\n\n")
            for rank, (_, row) in enumerate(lead_lag_df.head(20).iterrows(), 1):
                market_tag = "KRX" if row.get('market', '').startswith('K') else "SP500"
                name = row.get('name', 'Unknown')
                score = row['lead_lag_score'] * 100
                f.write(f"  {rank}. [{market_tag}] {row['symbol']} ({name}): {score:.2f}%\n")
            f.write(f"\n--- Leaders with highest today return ---\n")
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
            for rank, (sym, ret) in enumerate(leader_returns[:10], 1):
                name_row = universe[universe['symbol'] == sym]
                name = name_row['name'].values[0] if not name_row.empty else sym
                f.write(f"  {rank}. {sym} ({name}): +{ret*100:.2f}%\n")
        logger.info(f"Saved lead-lag predictions ({len(lead_lag_df)} symbols) to {lead_lag_output_path}")

    return res_df, message_text

if __name__ == "__main__":
    execute_prediction_pipeline()
