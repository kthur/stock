"""Fetch corporate earnings/fundamental data from Yahoo Finance."""

import logging
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result, retry_if_exception_type
from src.utils.rate_limiter import get_global_rate_limiter
import asyncio
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

_KR_MARKET_SUFFIX = {
    'KOSPI': '.KS',
    'KOSDAQ': '.KQ',
    'KONEX': '.KQ',
    'KRX': '.KS',
}


def _yf_ticker(symbol: str, market: Optional[str] = None) -> str:
    cleaned = symbol.strip().upper().split('.')[0]
    if cleaned.isdigit():
        suffix = _KR_MARKET_SUFFIX.get(market or '', '.KS')
        return f"{cleaned}{suffix}"
    return cleaned


def is_empty_result(result):
    if result is None:
        return True
    if isinstance(result, pd.DataFrame) and result.empty:
        return True
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=False
)
def _fetch_fundamentals_network(yf_sym: str) -> pd.DataFrame:
    # Coordinate fundamental fetch rate limiting
    get_global_rate_limiter().wait()
    ticker = yf.Ticker(yf_sym)
    financials = ticker.financials
    if financials is None or financials.empty:
        raise ValueError(f"No annual financials for {yf_sym}")

    fin = financials.T
    fin.index = pd.to_datetime(fin.index)
    fin = fin.sort_index()

    result = pd.DataFrame(index=fin.index)

    rev_cols = [c for c in ['Total Revenue', 'Revenue'] if c in fin.columns]
    result['revenue'] = fin[rev_cols[0]] if rev_cols else 0.0

    oi_cols = [c for c in ['Operating Income', 'Operating Income (Loss)'] if c in fin.columns]
    result['operating_income'] = fin[oi_cols[0]] if oi_cols else 0.0

    ni_cols = [c for c in ['Net Income', 'Net Income (Loss)'] if c in fin.columns]
    result['net_income'] = fin[ni_cols[0]] if ni_cols else 0.0

    eps_cols = [c for c in ['Diluted EPS', 'Basic EPS'] if c in fin.columns]
    if eps_cols:
        result['eps'] = fin[eps_cols[0]]
    else:
        result['eps'] = 0.0

    info = ticker.info or {}
    result['shares_outstanding'] = info.get('sharesOutstanding', 0)
    current_price = float(info.get('regularMarketPrice', info.get('previousClose', 0.0)) or 0.0)
    div_yield = float(info.get('dividendYield', 0.0) or 0.0)
    div = info.get('dividendRate', div_yield * current_price)
    result['dividend_per_share'] = max(0.0, float(div) if div else 0.0)

    for col in ['revenue', 'operating_income', 'net_income', 'eps']:
        result[col] = result[col].fillna(0).astype(float)

    return result


def fetch_fundamentals(symbol: str, market: Optional[str] = None, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    Fetch annual fundamental data from Yahoo Finance.

    Returns DataFrame with columns:
        date, revenue, operating_income, net_income, eps,
        shares_outstanding, dividend_per_share
    One row per fiscal year, sorted chronologically.
    Returns None if no data is available.
    """
    yf_sym = _yf_ticker(symbol, market)
    try:
        result = _fetch_fundamentals_network(yf_sym)
        return result
    except Exception as e:
        logger.debug(f"Failed to fetch fundamentals for {symbol} ({yf_sym}) after retries: {e}")
        return None


async def async_fetch_fundamentals(symbol: str, market: Optional[str] = None, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    Asynchronously fetch annual fundamental data from Yahoo Finance API with exponential backoff retries.
    """
    from src.utils.http_session import DEFAULT_USER_AGENT

    yf_sym = _yf_ticker(symbol, market)
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{yf_sym}"
    params = {
        "modules": "incomeStatementHistory,defaultKeyStatistics,summaryDetail"
    }
    headers = {
        "User-Agent": DEFAULT_USER_AGENT
    }

    for attempt in range(1, max_retries + 1):
        try:
            # Wait on the global rate limiter
            await get_global_rate_limiter().async_wait()

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status in (429, 500, 502, 503, 504):
                        if attempt < max_retries:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        logger.debug(f"Failed to fetch fundamentals for {symbol} ({yf_sym}) via async API: status {response.status}")
                        return None

                    if response.status != 200:
                        logger.debug(f"Failed to fetch fundamentals for {symbol} ({yf_sym}) via async API: status {response.status}")
                        return None

                    json_data = await response.json()
                    result = json_data.get("quoteSummary", {}).get("result", [])
                    if not result:
                        return None

                    data = result[0]
                    history = data.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])
                    if not history:
                        return None

                    rows = []
                    for item in history:
                        end_date_str = item.get("endDate", {}).get("fmt")
                        if not end_date_str:
                            continue

                        rev = item.get("totalRevenue", {}).get("raw", 0.0)
                        op_inc = item.get("operatingIncome", {}).get("raw", 0.0)
                        net_inc = item.get("netIncome", {}).get("raw", 0.0)
                        eps = item.get("basicEps", {}).get("raw", item.get("dilutedEps", {}).get("raw", 0.0))

                        rows.append({
                            "date_align": pd.to_datetime(end_date_str),
                            "revenue": float(rev),
                            "operating_income": float(op_inc),
                            "net_income": float(net_inc),
                            "eps": float(eps)
                        })

                    if not rows:
                        return None

                    df = pd.DataFrame(rows)
                    df = df.set_index("date_align")
                    df = df.sort_index()

                    stats = data.get("defaultKeyStatistics", {})
                    shares = stats.get("sharesOutstanding", {}).get("raw", 0.0)

                    detail = data.get("summaryDetail", {})
                    div_rate = detail.get("dividendRate", {}).get("raw")
                    if div_rate is None:
                        div_yield = detail.get("dividendYield", {}).get("raw", 0.0)
                        current_price = detail.get("previousClose", {}).get("raw", 0.0)
                        div_rate = div_yield * current_price

                    df['shares_outstanding'] = float(shares)
                    df['dividend_per_share'] = float(max(0.0, div_rate if div_rate else 0.0))

                    for col in ['revenue', 'operating_income', 'net_income', 'eps']:
                        df[col] = df[col].fillna(0).astype(float)

                    return df

        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            logger.debug(f"Async fetch fundamentals exception for {symbol} ({yf_sym}): {e}")
            return None

    return None


def fetch_and_store_fundamentals_batch(
    symbols: List[str],
    symbol_market_map: Dict[str, str],
    storage,
    max_workers: int = 4,
    force_refetch: bool = False,
) -> int:
    """
    Fetch fundamentals for a list of symbols and store in DB.
    Skips symbols that already have fresh fundamentals in DB (based on cache metadata).
    """
    async def _async_batch_fetch_and_store():
        meta_cache = {}
        if hasattr(storage, 'get_fundamental_meta'):
            try:
                meta_cache = storage.get_fundamental_meta()
            except Exception as e:
                logger.warning(f"Failed to load fundamental cache metadata: {e}")

        expiry_days = 90
        try:
            from src.config import TradingConfig
            config = TradingConfig()
            expiry_days = config.fundamental_cache_expiry_days
        except Exception:
            pass

        # Offline mode check (expiry_days < 0): skip network requests entirely
        if expiry_days < 0:
            logger.info("[Offline Mode] Skipping fundamental network fetching (expiry_days < 0). Using existing DB cache.")
            return 0

        current_time = datetime.now()
        skipped = 0
        to_fetch = []

        for sym in symbols:
            if not force_refetch and sym in meta_cache:
                try:
                    last_fetched = datetime.strptime(meta_cache[sym], "%Y-%m-%d")
                    if (current_time - last_fetched).days < expiry_days:
                        skipped += 1
                        continue
                except Exception:
                    pass
            to_fetch.append(sym)

        if skipped > 0:
            logger.info(f"Skipped {skipped}/{len(symbols)} symbols with fresh fundamental cache (within {expiry_days} days)")

        if not to_fetch:
            return 0

        results = {}
        success = 0

        sem = asyncio.Semaphore(5)

        async def _fetch_task(sym):
            async with sem:
                market = symbol_market_map.get(sym, 'SP500')
                df_fun = await async_fetch_fundamentals(sym, market)
                if df_fun is None:
                    loop = asyncio.get_running_loop()
                    df_fun = await loop.run_in_executor(None, fetch_fundamentals, sym, market)
                return sym, df_fun

        tasks = [_fetch_task(sym) for sym in to_fetch]
        total_fetch = len(to_fetch)
        done_count = 0

        for f in asyncio.as_completed(tasks):
            sym, df_fun = await f
            # Save fundamental meta ONLY when data fetch returned valid non-empty results
            if df_fun is not None and not df_fun.empty:
                try:
                    if hasattr(storage, 'save_fundamental_meta'):
                        storage.save_fundamental_meta(sym, current_time.strftime("%Y-%m-%d"))
                except Exception as e:
                    logger.warning(f"Failed to save metadata for {sym}: {e}")
                results[sym] = df_fun
                success += 1
            done_count += 1
            if done_count % 500 == 0 or done_count == total_fetch:
                logger.info(f"Fundamentals progress: {done_count}/{total_fetch} ({success} fetched, {skipped} skipped)")

        logger.info(f"Fetched fundamentals for {success}/{total_fetch} symbols ({skipped} skipped)")

        stored = 0
        for sym, df_fun in results.items():
            try:
                df_fun = df_fun.copy()
                df_fun['symbol'] = sym
                df_fun['date'] = df_fun.index.strftime('%Y-%m-%d')
                df_fun = df_fun.reset_index(drop=True)
                storage.save_fundamentals(df_fun)
                stored += 1
            except Exception as e:
                logger.warning(f"Failed to store fundamentals for {sym}: {e}")

        logger.info(f"Stored fundamentals for {stored}/{success} symbols in DB")
        return stored

    # Run execution with thread safety for event loop context
    import threading
    import queue

    q: queue.Queue = queue.Queue()

    def worker():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            val = loop.run_until_complete(_async_batch_fetch_and_store())
            loop.close()
            q.put((True, val))
        except Exception as e:
            q.put((False, e))

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    success, res = q.get()
    if success:
        return int(res)
    raise res
