"""Fetch corporate earnings/fundamental data from Yahoo Finance."""

import logging
from typing import Dict, List, Optional, Any
import numpy as np
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


def compute_regulatory_filing_lag(
    period_end_date: Any,
    period_type: str = 'quarterly',
    is_krx: bool = True
) -> str:
    """
    Computes precise statutory regulatory filing availability date without lookahead bias:
    - KRX (KOSPI/KOSDAQ): 45 calendar days for quarterly reports (1Q/2Q/3Q), 90 calendar days for annual report.
    - SEC (SP500/NASDAQ/RUSSELL2000): 40 calendar days for 10-Q quarterly, 60 calendar days for 10-K annual.
    """
    ts = pd.to_datetime(period_end_date)
    is_year_end = (str(period_type).lower() == 'annual') or (ts.month == 12)
    if is_krx:
        lag_days = 90 if is_year_end else 45
    else:
        lag_days = 60 if is_year_end else 40
    return str((ts + pd.Timedelta(days=lag_days)).strftime('%Y-%m-%d'))


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
    # Prefer quarterly income statement: the most recent quarter is closer to
    # "now" than the last fiscal year end, so RIM / accrual features react
    # faster to fresh earnings. Fall back to annual when quarterly is missing.
    financials = None
    is_quarterly = True
    try:
        financials = ticker.quarterly_financials
    except Exception as _q_err:
        logger.debug(f"Quarterly financials fetch failed for {yf_sym}: {_q_err}. Trying annual financials.")
        financials = None
    if financials is None or (hasattr(financials, 'empty') and financials.empty):
        try:
            financials = ticker.financials
            is_quarterly = False
        except Exception as _a_err:
            logger.debug(f"Annual financials fetch failed for {yf_sym}: {_a_err}.")
            financials = None
    if financials is None or (hasattr(financials, 'empty') and financials.empty):
        raise ValueError(f"No financials available for {yf_sym}")

    fin = financials.T
    fin.index = pd.to_datetime(fin.index)
    fin = fin.sort_index()

    result = pd.DataFrame(index=fin.index)
    # Jurisdiction-Aware Regulatory Filing Lag enforcement (KRX 45d/90d, SEC 40d/60d)
    is_kr = yf_sym.endswith(('.KS', '.KQ'))
    p_type = 'quarterly' if is_quarterly else 'annual'
    result['date_available'] = [
        compute_regulatory_filing_lag(dt, p_type, is_krx=is_kr)
        for dt in fin.index
    ]
    result['period_type'] = p_type

    scale_factor = 1.0 if is_quarterly else 0.25  # Normalize annual flow figures to quarterly run-rate
    rev_cols = [c for c in ['Total Revenue', 'Revenue'] if c in fin.columns]
    result['revenue'] = (fin[rev_cols[0]] * scale_factor) if rev_cols else 0.0

    oi_cols = [c for c in ['Operating Income', 'Operating Income (Loss)'] if c in fin.columns]
    result['operating_income'] = (fin[oi_cols[0]] * scale_factor) if oi_cols else 0.0

    ni_cols = [c for c in ['Net Income', 'Net Income (Loss)'] if c in fin.columns]
    result['net_income'] = (fin[ni_cols[0]] * scale_factor) if ni_cols else 0.0

    eps_cols = [c for c in ['Diluted EPS', 'Basic EPS'] if c in fin.columns]
    if eps_cols:
        result['eps'] = fin[eps_cols[0]] * (1.0 if is_quarterly else 0.25)
    else:
        result['eps'] = 0.0

    # Fetch Cash Flow Statement for OCF
    try:
        if is_quarterly:
            cf_data = ticker.quarterly_cashflow
        else:
            cf_data = ticker.cashflow
        if cf_data is not None and not cf_data.empty:
            cf_cols_map = {
                'Total Cash From Operating Activities': 'operating_cash_flow',
                'Operating Cash Flow': 'operating_cash_flow',
                'Cash Flow From Continuing Operating Activities': 'operating_cash_flow',
            }
            for cf_col, target_col in cf_cols_map.items():
                if cf_col in cf_data.index:
                    ocf_series = cf_data.loc[cf_col]
                    for date_col in ocf_series.index:
                        date_str = date_col.strftime('%Y-%m-%d') if hasattr(date_col, 'strftime') else str(date_col)
                        # Find matching row in results and add OCF
                        for r_idx in result.index:
                            r_date_str = r_idx.strftime('%Y-%m-%d') if hasattr(r_idx, 'strftime') else str(r_idx)
                            if r_date_str == date_str:
                                result.loc[r_idx, 'operating_cash_flow'] = float(ocf_series[date_col]) if pd.notna(ocf_series[date_col]) else 0.0
                    break
    except Exception as e:
        logger.debug(f"Cash flow fetch failed for {yf_sym}: {e}")

    info: Dict[str, Any] = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    try:
        result['shares_outstanding'] = int(info.get('sharesOutstanding', 0) or 0)
    except (ValueError, TypeError):
        result['shares_outstanding'] = 0

    try:
        current_price = float(info.get('regularMarketPrice', info.get('previousClose', 0.0)) or 0.0)
        div_yield = float(info.get('dividendYield', 0.0) or 0.0)
        div = info.get('dividendRate', div_yield * current_price)
        result['dividend_per_share'] = max(0.0, float(div) if div else 0.0)
    except (ValueError, TypeError):
        result['dividend_per_share'] = 0.0

    # Fetch book value (Total Stockholder Equity) from balance sheet for RIM BPS calculation
    try:
        bs = None
        try:
            bs = ticker.quarterly_balance_sheet
        except Exception:
            bs = None
        if bs is None or bs.empty:
            try:
                bs = ticker.balance_sheet
            except Exception:
                bs = None
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

    if 'shares_outstanding' in result.columns:
        shares = pd.to_numeric(result['shares_outstanding'], errors='coerce').fillna(0.0)
        bv = pd.to_numeric(result.get('book_value', 0.0), errors='coerce').fillna(0.0)
        result['bps'] = np.where(shares > 0, bv / np.maximum(shares, 1.0), bv)
    else:
        result['bps'] = result.get('book_value', 0.0)

    for col in ['revenue', 'operating_income', 'net_income', 'eps', 'book_value', 'bps', 'operating_cash_flow']:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0.0).astype(float)
        else:
            result[col] = 0.0

    # TTM (Trailing Twelve Months) aggregation: preserves quarterly seasonality while stabilizing valuation inputs
    if is_quarterly and len(result) >= 1:
        result['ttm_revenue'] = result['revenue'].rolling(4, min_periods=1).sum()
        result['ttm_operating_income'] = result['operating_income'].rolling(4, min_periods=1).sum()
        result['ttm_net_income'] = result['net_income'].rolling(4, min_periods=1).sum()
        result['ttm_eps'] = result['eps'].rolling(4, min_periods=1).sum()
    else:
        # For annual records, annual total is already the full 12-month figure
        result['ttm_revenue'] = (result['revenue'] / scale_factor) if scale_factor > 0 else result['revenue']
        result['ttm_operating_income'] = (result['operating_income'] / scale_factor) if scale_factor > 0 else result['operating_income']
        result['ttm_net_income'] = (result['net_income'] / scale_factor) if scale_factor > 0 else result['net_income']
        result['ttm_eps'] = (result['eps'] / scale_factor) if scale_factor > 0 else result['eps']

    # Compute quality metrics from TTM data
    if 'ttm_revenue' in result.columns and 'ttm_operating_income' in result.columns:
        raw_op_m = np.where(
            result['ttm_revenue'] > 0,
            result['ttm_operating_income'] / np.maximum(result['ttm_revenue'], 1e-6),
            0.0
        )
        result['operating_margin'] = np.clip(np.where(np.isfinite(raw_op_m), raw_op_m, 0.0), -10.0, 10.0)
    if 'ttm_revenue' in result.columns and 'ttm_net_income' in result.columns:
        raw_np_m = np.where(
            result['ttm_revenue'] > 0,
            result['ttm_net_income'] / np.maximum(result['ttm_revenue'], 1e-6),
            0.0
        )
        result['net_profit_margin'] = np.clip(np.where(np.isfinite(raw_np_m), raw_np_m, 0.0), -10.0, 10.0)
    if 'ttm_eps' in result.columns:
        raw_eps_g = result['ttm_eps'].pct_change(4).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        result['eps_growth_1y'] = np.clip(np.where(np.isfinite(raw_eps_g), raw_eps_g, 0.0), -10.0, 10.0)

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
        "modules": "incomeStatementHistoryQuarterly,incomeStatementHistory,balanceSheetHistoryQuarterly,balanceSheetHistory,defaultKeyStatistics,summaryDetail"
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
                    history_q = data.get("incomeStatementHistoryQuarterly", {}).get("incomeStatementHistory", [])
                    history_a = data.get("incomeStatementHistory", {}).get("incomeStatementHistory", [])

                    if history_q:
                        history = history_q
                        is_quarterly = True
                        scale_factor = 1.0
                    elif history_a:
                        history = history_a
                        is_quarterly = False
                        scale_factor = 0.25
                    else:
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

                        dt = pd.to_datetime(end_date_str)
                        is_kr = yf_sym.endswith(('.KS', '.KQ'))
                        p_type = "quarterly" if is_quarterly else "annual"
                        rows.append({
                            "date_align": dt,
                            "date_available": compute_regulatory_filing_lag(dt, p_type, is_krx=is_kr),
                            "period_type": p_type,
                            "revenue": float(rev) * scale_factor,
                            "operating_income": float(op_inc) * scale_factor,
                            "net_income": float(net_inc) * scale_factor,
                            "eps": float(eps) * scale_factor
                        })

                    # Fetch Cash Flow Statement for OCF
                    try:
                        ticker = yf.Ticker(yf_sym)
                        if is_quarterly:
                            cf_data = ticker.quarterly_cashflow
                        else:
                            cf_data = ticker.cashflow
                        if cf_data is not None and not cf_data.empty:
                            cf_cols_map = {
                                'Total Cash From Operating Activities': 'operating_cash_flow',
                                'Operating Cash Flow': 'operating_cash_flow',
                                'Cash Flow From Continuing Operating Activities': 'operating_cash_flow',
                            }
                            for cf_col, target_col in cf_cols_map.items():
                                if cf_col in cf_data.index:
                                    ocf_series = cf_data.loc[cf_col]
                                    for date_col in ocf_series.index:
                                        date_str = date_col.strftime('%Y-%m-%d') if hasattr(date_col, 'strftime') else str(date_col)
                                        # Find matching row in results and add OCF
                                        for r in rows:
                                            r_date_str = r.get('date_align', '').strftime('%Y-%m-%d') if hasattr(r.get('date_align', ''), 'strftime') else str(r.get('date_align', ''))
                                            if r_date_str == date_str:
                                                r['operating_cash_flow'] = float(ocf_series[date_col]) if pd.notna(ocf_series[date_col]) else 0.0
                                    break
                    except Exception as e:
                        logger.debug(f"Cash flow fetch failed for {symbol}: {e}")

                    if not rows:
                        return None

                    df = pd.DataFrame(rows)
                    df = df.set_index("date_align")
                    df = df.sort_index()

                    stats = data.get("defaultKeyStatistics") or {}
                    shares_obj = stats.get("sharesOutstanding") or {}
                    shares = shares_obj.get("raw", 0.0) if isinstance(shares_obj, dict) else 0.0

                    book_val_obj = stats.get("bookValue") or {}
                    book_val = book_val_obj.get("raw", 0.0) if isinstance(book_val_obj, dict) else 0.0
                    total_equity = 0.0
                    if not book_val:
                        bs_statements = data.get("balanceSheetHistory", {}).get("balanceSheetStatements", [])
                        if bs_statements:
                            total_eq = bs_statements[0].get("totalStockholderEquity", {}).get("raw", 0.0)
                            if total_eq and shares > 0:
                                total_equity = float(total_eq)
                                book_val = total_eq / shares
                    elif shares > 0:
                        total_equity = float(book_val) * shares

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
                    df['book_value'] = float(total_equity if total_equity > 0 else (book_val * shares if shares > 0 else book_val))
                    df['bps'] = float(book_val)

                    for col in ['revenue', 'operating_income', 'net_income', 'eps', 'book_value', 'bps', 'shares_outstanding', 'dividend_per_share', 'operating_cash_flow']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).astype(float)
                        else:
                            df[col] = 0.0

                    if is_quarterly and len(df) >= 1:
                        df['ttm_revenue'] = df['revenue'].rolling(4, min_periods=1).sum()
                        df['ttm_operating_income'] = df['operating_income'].rolling(4, min_periods=1).sum()
                        df['ttm_net_income'] = df['net_income'].rolling(4, min_periods=1).sum()
                        df['ttm_eps'] = df['eps'].rolling(4, min_periods=1).sum()
                    else:
                        df['ttm_revenue'] = (df['revenue'] / scale_factor) if scale_factor > 0 else df['revenue']
                        df['ttm_operating_income'] = (df['operating_income'] / scale_factor) if scale_factor > 0 else df['operating_income']
                        df['ttm_net_income'] = (df['net_income'] / scale_factor) if scale_factor > 0 else df['net_income']
                        df['ttm_eps'] = (df['eps'] / scale_factor) if scale_factor > 0 else df['eps']

                    # Compute quality metrics from TTM data
                    if 'ttm_revenue' in df.columns and 'ttm_operating_income' in df.columns:
                        df['operating_margin'] = np.where(
                            df['ttm_revenue'] > 0,
                            df['ttm_operating_income'] / df['ttm_revenue'],
                            0.0
                        )
                    if 'ttm_revenue' in df.columns and 'ttm_net_income' in df.columns:
                        df['net_profit_margin'] = np.where(
                            df['ttm_revenue'] > 0,
                            df['ttm_net_income'] / df['ttm_revenue'],
                            0.0
                        )
                    if 'ttm_eps' in df.columns:
                        df['eps_growth_1y'] = df['ttm_eps'].pct_change(4).replace([np.inf, -np.inf], np.nan).fillna(0.0)

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
                    await asyncio.sleep(0.05)
                    market = symbol_market_map.get(sym, 'SP500')
                    df_fun = await async_fetch_fundamentals(sym, market, session=shared_session)
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

    # Run execution with robust event loop isolation to avoid nested event loop conflicts
    try:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is None:
            return int(asyncio.run(_async_batch_fetch_and_store()))
        else:
            # If an event loop is already active in current thread, execute cleanly in dedicated worker thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(_async_batch_fetch_and_store()))
                return int(future.result(timeout=600))
    except Exception as e:
        logger.error(f"Error in batch fundamental fetch execution: {e}")
        raise
