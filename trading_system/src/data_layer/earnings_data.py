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

    # Fetch book value (Total Stockholder Equity) from balance sheet for RIM BPS calculation
    try:
        bs = ticker.balance_sheet
        if bs is not None and not bs.empty:
            bs_t = bs.T
            bs_t.index = pd.to_datetime(bs_t.index)
            bs_t = bs_t.sort_index()
            bv_cols = [c for c in ['Total Stockholder Equity', 'Stockholders Equity', 'Total Equity Gross Minority Interest'] if c in bs_t.columns]
            if bv_cols:
                bv_series = bs_t[bv_cols[0]].reindex(result.index).ffill()
                result['book_value'] = bv_series
            else:
                result['book_value'] = 0.0
        else:
            result['book_value'] = 0.0
    except Exception:
        result['book_value'] = 0.0

    for col in ['revenue', 'operating_income', 'net_income', 'eps', 'book_value']:
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


async def async_fetch_fundamentals(symbol: str, market: str, session: Optional[aiohttp.ClientSession] = None, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """Async variant using aiohttp with connection pooling & rate limit checks."""
    from src.utils.http_session import DEFAULT_USER_AGENT

    yf_sym = _yf_ticker(symbol, market)
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{yf_sym}"
    params = {
        "modules": "incomeStatementHistory,defaultKeyStatistics,summaryDetail"
    }
    headers = {
        "User-Agent": DEFAULT_USER_AGENT
    }

    async def _do_request(sess: aiohttp.ClientSession):
        for attempt in range(1, max_retries + 1):
            try:
                # Wait on the global rate limiter
                await get_global_rate_limiter().async_wait()

                async with sess.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
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

                    stats = data.get("defaultKeyStatistics") or {}
                    shares_obj = stats.get("sharesOutstanding") or {}
                    shares = shares_obj.get("raw", 0.0) if isinstance(shares_obj, dict) else 0.0

                    detail = data.get("summaryDetail") or {}
                    div_rate_obj = detail.get("dividendRate") or {}
                    div_rate = div_rate_obj.get("raw") if isinstance(div_rate_obj, dict) else None

                    if div_rate is None:
                        div_yield_obj = detail.get("dividendYield") or {}
                        div_yield = div_yield_obj.get("raw", 0.0) if isinstance(div_yield_obj, dict) else 0.0
                        prev_close_obj = detail.get("previousClose") or {}
                        current_price = prev_close_obj.get("raw", 0.0) if isinstance(prev_close_obj, dict) else 0.0
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

    if session is not None:
        return await _do_request(session)
    else:
        async with aiohttp.ClientSession() as new_session:
            return await _do_request(new_session)


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

        stored = 0
        success = 0
        sem = asyncio.Semaphore(10)

        async with aiohttp.ClientSession() as shared_session:
            async def _fetch_task(sym):
                async with sem:
                    market = symbol_market_map.get(sym, 'SP500')
                    df_fun = await async_fetch_fundamentals(sym, market, session=shared_session)
                    if df_fun is None:
                        loop = asyncio.get_running_loop()
                        df_fun = await loop.run_in_executor(None, fetch_fundamentals, sym, market)
                    return sym, df_fun

            tasks = [_fetch_task(sym) for sym in to_fetch]
            total_fetch = len(to_fetch)
            done_count = 0

            for f in asyncio.as_completed(tasks):
                sym, df_fun = await f
                if df_fun is not None and not df_fun.empty:
                    try:
                        # Stream save fundamental data immediately to DB to save RAM
                        df_fun_copy = df_fun.copy()
                        df_fun_copy['symbol'] = sym
                        df_fun_copy['date'] = df_fun_copy.index.strftime('%Y-%m-%d')
                        df_fun_copy = df_fun_copy.reset_index(drop=True)
                        storage.save_fundamentals(df_fun_copy)
                        stored += 1

                        if hasattr(storage, 'save_fundamental_meta'):
                            storage.save_fundamental_meta(sym, current_time.strftime("%Y-%m-%d"))
                        success += 1
                    except Exception as e:
                        logger.warning(f"Failed to store fundamentals for {sym}: {e}")
                done_count += 1
                if done_count % 500 == 0 or done_count == total_fetch:
                    logger.info(f"Fundamentals progress: {done_count}/{total_fetch} ({success} fetched, {skipped} skipped)")

        logger.info(f"Streamed and stored fundamentals for {stored}/{total_fetch} symbols in DB")
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
