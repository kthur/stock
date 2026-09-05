"""Fetch corporate earnings/fundamental data from Yahoo Finance."""

import logging
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result, retry_if_exception_type
from src.utils.rate_limiter import get_global_rate_limiter
import os
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


def _to_safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if type(val).__name__ == 'MagicMock':
        return default
    try:
        f = float(val)
        return f if np.isfinite(f) else default
    except (ValueError, TypeError):
        return default


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
    for attr in ['quarterly_income_stmt', 'quarterly_financials', 'income_stmt', 'financials']:
        try:
            val = getattr(ticker, attr, None)
            if val is not None and isinstance(val, pd.DataFrame) and not val.empty:
                financials = val
                is_quarterly = 'quarter' in attr
                break
        except Exception as _q_err:
            logger.debug(f"Income statement attribute {attr} fetch failed for {yf_sym}: {_q_err}")
            financials = None

    if financials is None or not isinstance(financials, pd.DataFrame) or financials.empty:
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
    rev_cols = [c for c in ['Total Revenue', 'Revenue', 'Operating Revenue'] if c in fin.columns]
    result['revenue'] = (fin[rev_cols[0]] * scale_factor) if rev_cols else 0.0

    oi_cols = [c for c in ['Operating Income', 'Operating Income (Loss)', 'Operating Profit', 'Pretax Income'] if c in fin.columns]
    if oi_cols:
        result['operating_income'] = (fin[oi_cols[0]] * scale_factor)
    else:
        # For financial firms / banks where operating income is not separated, fallback to Net Income or Revenue
        ni_temp = [c for c in ['Net Income', 'Net Income (Loss)', 'Net Income Common Stockholders'] if c in fin.columns]
        result['operating_income'] = (fin[ni_temp[0]] * scale_factor) if ni_temp else 0.0

    ni_cols = [c for c in ['Net Income', 'Net Income (Loss)', 'Net Income Common Stockholders', 'Net Income Continuous Operations'] if c in fin.columns]
    result['net_income'] = (fin[ni_cols[0]] * scale_factor) if ni_cols else 0.0

    eps_cols = [c for c in ['Diluted EPS', 'Basic EPS', 'Diluted Continuous Operations EPS'] if c in fin.columns]
    if eps_cols:
        result['eps'] = fin[eps_cols[0]] * (1.0 if is_quarterly else 0.25)
    else:
        result['eps'] = 0.0

    # Fetch Cash Flow Statement for OCF
    try:
        cf_data = None
        for cf_attr in ['quarterly_cash_flow', 'quarterly_cashflow', 'cash_flow', 'cashflow']:
            try:
                cval = getattr(ticker, cf_attr, None)
                if cval is not None and isinstance(cval, pd.DataFrame) and not cval.empty:
                    cf_data = cval
                    break
            except Exception:
                pass
        if cf_data is not None and not cf_data.empty:
            cf_cols_map = {
                'Total Cash From Operating Activities': 'operating_cash_flow',
                'Operating Cash Flow': 'operating_cash_flow',
                'Cash Flow From Continuing Operating Activities': 'operating_cash_flow',
                'Cash Flow From Continuing Operations': 'operating_cash_flow',
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

    shares_outstanding = _to_safe_float(info.get('sharesOutstanding', None), 0.0)

    # Fast info shares fallback
    if shares_outstanding <= 0 and hasattr(ticker, 'fast_info'):
        f_info = ticker.fast_info
        if f_info is not None:
            for f_attr in ['shares', 'shares_outstanding']:
                f_val = getattr(f_info, f_attr, None)
                f_num = _to_safe_float(f_val, 0.0)
                if f_num > 0:
                    shares_outstanding = f_num
                    break

    price_raw = info.get('regularMarketPrice', info.get('previousClose', None))
    current_price = _to_safe_float(price_raw, 0.0)
    if current_price <= 0 and hasattr(ticker, 'fast_info'):
        current_price = _to_safe_float(getattr(ticker.fast_info, 'last_price', None), 0.0)

    div_yield = _to_safe_float(info.get('dividendYield', None), 0.0)
    div_rate = _to_safe_float(info.get('dividendRate', None), div_yield * current_price)
    result['dividend_per_share'] = max(0.0, div_rate)

    # Fetch book value (Total Stockholder Equity) from balance sheet for RIM BPS calculation
    bs_t = pd.DataFrame()
    try:
        bs = None
        for bs_attr in ['quarterly_balance_sheet', 'quarterly_balancesheet', 'balance_sheet', 'balancesheet']:
            try:
                bval = getattr(ticker, bs_attr, None)
                if bval is not None and isinstance(bval, pd.DataFrame) and not bval.empty:
                    bs = bval
                    break
            except Exception:
                pass
        if bs is not None and not bs.empty:
            bs_t = bs.T
            bs_t.index = pd.to_datetime(bs_t.index)
            bs_t = bs_t.sort_index()
            bv_cols = [c for c in ['Total Stockholder Equity', 'Stockholders Equity', 'Total Equity Gross Minority Interest', 'Common Stock Equity'] if c in bs_t.columns]
            if bv_cols:
                bv_series = bs_t[bv_cols[0]].reindex(result.index).ffill()
                result['book_value'] = bv_series
            else:
                result['book_value'] = 0.0

            # Shares from Balance Sheet if still missing
            if shares_outstanding <= 0:
                sh_cols = [c for c in ['Ordinary Shares Number', 'Share Issued', 'Common Stock Shares Outstanding'] if c in bs_t.columns]
                if sh_cols:
                    last_sh = bs_t[sh_cols[0]].dropna()
                    if not last_sh.empty and last_sh.iloc[-1] > 0:
                        shares_outstanding = float(last_sh.iloc[-1])

            # Add cash extraction
            cash_cols = [c for c in ['Cash And Cash Equivalents', 'Cash', 'Cash And Equivalents', 'Cash Financial'] if c in bs_t.columns]
            if cash_cols:
                result['cash_equivalents'] = bs_t[cash_cols[0]].reindex(result.index).ffill()
            else:
                result['cash_equivalents'] = 0.0

            # Add debt extraction
            debt_cols = [c for c in ['Total Debt'] if c in bs_t.columns]
            if debt_cols:
                result['total_debt'] = bs_t[debt_cols[0]].reindex(result.index).ffill()
            else:
                lt_cols = [c for c in ['Long Term Debt'] if c in bs_t.columns]
                st_cols = [c for c in ['Current Debt', 'Short Long Term Debt'] if c in bs_t.columns]
                lt_debt = bs_t[lt_cols[0]].fillna(0.0) if lt_cols else pd.Series(0.0, index=bs_t.index)
                st_debt = bs_t[st_cols[0]].fillna(0.0) if st_cols else pd.Series(0.0, index=bs_t.index)
                result['total_debt'] = (lt_debt + st_debt).reindex(result.index).ffill()
        else:
            result['book_value'] = 0.0
            result['cash_equivalents'] = 0.0
            result['total_debt'] = 0.0
    except Exception:
        result['book_value'] = 0.0
        result['cash_equivalents'] = 0.0
        result['total_debt'] = 0.0

    result['shares_outstanding'] = shares_outstanding

    bv_val = pd.to_numeric(result.get('book_value', 0.0), errors='coerce').fillna(0.0)
    if shares_outstanding > 0:
        bps_raw = np.where(bv_val > 0, bv_val / shares_outstanding, 0.0)
        result['bps'] = np.where(np.isfinite(bps_raw), bps_raw, 0.0)
    else:
        # Fallback to info bookValue (which is BPS in Yahoo Finance)
        bv_per_share = float(info.get('bookValue', 0.0) or 0.0)
        if bv_per_share > 0:
            result['bps'] = bv_per_share
            if (bv_val == 0.0).all():
                result['book_value'] = bv_per_share
        else:
            result['bps'] = 0.0

    for col in ['revenue', 'operating_income', 'net_income', 'eps', 'book_value', 'bps', 'operating_cash_flow', 'cash_equivalents', 'total_debt']:
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
            np.nan
        )
        result['operating_margin'] = np.clip(np.where(np.isfinite(raw_op_m), raw_op_m, np.nan), -10.0, 10.0)
    if 'ttm_revenue' in result.columns and 'ttm_net_income' in result.columns:
        raw_np_m = np.where(
            result['ttm_revenue'] > 0,
            result['ttm_net_income'] / np.maximum(result['ttm_revenue'], 1e-6),
            np.nan
        )
        result['net_profit_margin'] = np.clip(np.where(np.isfinite(raw_np_m), raw_np_m, np.nan), -10.0, 10.0)
    if 'ttm_eps' in result.columns:
        raw_eps_g = result['ttm_eps'].pct_change(4).replace([np.inf, -np.inf], np.nan)
        result['eps_growth_1y'] = np.clip(np.where(np.isfinite(raw_eps_g), raw_eps_g, np.nan), -10.0, 10.0)

    return result


_dart_fetcher_instance: Optional[Any] = None


def _get_global_dart_fetcher():
    global _dart_fetcher_instance
    if _dart_fetcher_instance is None:
        try:
            from src.data_layer.dart_fundamental_fetcher import DARTFundamentalFetcher
            _dart_fetcher_instance = DARTFundamentalFetcher()
        except Exception as _e:
            logger.debug(f"Could not initialize DARTFundamentalFetcher: {_e}")
            _dart_fetcher_instance = False
    return _dart_fetcher_instance if _dart_fetcher_instance is not False else None


def fetch_fundamentals(
    symbol: str,
    market: Optional[str] = None,
    max_retries: int = 3,
    shares_outstanding: Optional[float] = None,
) -> Optional[pd.DataFrame]:
    """
    Fetch annual/quarterly fundamental data.
    For Korean stocks (KOSPI/KOSDAQ), uses OpenDartReader (OpenDART API) as primary source,
    falling back to Yahoo Finance if unavailable.
    For US and other global markets, uses Yahoo Finance.

    Returns DataFrame with columns:
        date (index), date_available, period_type, revenue, operating_income,
        net_income, eps, shares_outstanding, book_value, bps, total_debt,
        cash_equivalents, dividend_per_share, etc.
    """
    cleaned_sym = str(symbol).strip().upper().split('.')[0]
    mkt_upper = str(market).strip().upper() if market else ''
    is_kr = mkt_upper in ('KOSPI', 'KOSDAQ', 'KRX') or cleaned_sym.isdigit() or str(symbol).strip().upper().endswith(('.KS', '.KQ'))

    if is_kr:
        dart_fetcher = _get_global_dart_fetcher()
        if dart_fetcher is not None:
            try:
                dart_df = dart_fetcher.fetch_fundamentals(symbol=symbol, years_back=3, shares_outstanding=shares_outstanding)
                if dart_df is not None and not dart_df.empty:
                    return dart_df
            except Exception as e:
                logger.debug(f"OpenDART fundamental fetch fallback to yfinance for {symbol}: {e}")

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

                    # Extract cash and debt
                    cash_equivalents = 0.0
                    total_debt = 0.0
                    bs_key = "balanceSheetHistoryQuarterly" if is_quarterly else "balanceSheetHistory"
                    bs_statements = data.get(bs_key, {}).get("balanceSheetStatements", [])
                    if not bs_statements:
                        bs_statements = data.get("balanceSheetHistory", {}).get("balanceSheetStatements", [])
                    if bs_statements:
                        latest_bs = bs_statements[0]
                        cash_obj = latest_bs.get("cashAndCashEquivalents", latest_bs.get("cash", {}))
                        cash_equivalents = float(cash_obj.get("raw", 0.0)) if isinstance(cash_obj, dict) else 0.0

                        debt_obj = latest_bs.get("totalDebt", {})
                        if debt_obj and isinstance(debt_obj, dict) and "raw" in debt_obj:
                            total_debt = float(debt_obj.get("raw", 0.0))
                        else:
                            lt_debt = float(latest_bs.get("longTermDebt", {}).get("raw", 0.0)) if isinstance(latest_bs.get("longTermDebt"), dict) else 0.0
                            st_debt = float(latest_bs.get("shortLongTermDebt", {}).get("raw", 0.0)) if isinstance(latest_bs.get("shortLongTermDebt"), dict) else 0.0
                            total_debt = lt_debt + st_debt

                    df['cash_equivalents'] = cash_equivalents
                    df['total_debt'] = total_debt

                    for col in ['revenue', 'operating_income', 'net_income', 'eps', 'book_value', 'bps', 'shares_outstanding', 'dividend_per_share', 'operating_cash_flow', 'cash_equivalents', 'total_debt']:
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


def invalidate_cache_for_symbols(storage, symbols: List[str]) -> int:
    """
    V7-20: Immediately invalidates fundamental cache metadata for specific symbols
    upon earnings announcement triggers (PEAD acceleration).
    """
    if not storage or not symbols:
        return 0
    try:
        if hasattr(storage, 'delete_fundamental_meta'):
            return int(storage.delete_fundamental_meta(symbols))
        elif hasattr(storage, '_get_conn'):
            with storage._SHARED_WRITE_LOCK:
                with storage._get_conn() as conn:
                    cursor = conn.cursor()
                    placeholders = ','.join('?' for _ in symbols)
                    cursor.execute(f"DELETE FROM fundamental_cache_meta WHERE symbol IN ({placeholders})", symbols)  # nosec B608
                    conn.commit()
                    return int(cursor.rowcount)
    except Exception as e:
        logger.warning(f"Failed to invalidate fundamental cache for symbols: {e}")
    return 0


def fetch_and_store_fundamentals_batch(
    symbols: List[str],
    symbol_market_map: Dict[str, str],
    storage,
    max_workers: int = 8,
    force_refetch: bool = False,
    shares_map: Optional[Dict[str, float]] = None,
    invalidate_symbols: Optional[List[str]] = None,
) -> int:
    """
    Fetch fundamentals for a list of symbols and store in DB using ThreadPoolExecutor.
    Skips symbols that already have fresh fundamentals in DB (based on cache metadata).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if invalidate_symbols:
        invalidate_cache_for_symbols(storage, invalidate_symbols)

    meta_cache = {}
    if hasattr(storage, 'get_fundamental_meta'):
        try:
            meta_cache = storage.get_fundamental_meta()
        except Exception as e:
            logger.warning(f"Failed to load fundamental cache metadata: {e}")

    # Allow environment override for forcing fundamental re-fetch
    if not force_refetch and os.environ.get("FORCE_FUNDAMENTAL_REFETCH", "false").lower() == "true":
        force_refetch = True
        logger.info("FORCE_FUNDAMENTAL_REFETCH active: bypassing cache for fundamental fetching.")

    valid_bps_symbols = None
    if hasattr(storage, 'get_symbols_with_valid_bps'):
        try:
            valid_bps_symbols = storage.get_symbols_with_valid_bps()
        except Exception as e:
            logger.debug(f"Failed to query valid bps symbols from storage: {e}")

    expiry_days = 90
    try:
        from src.config import TradingConfig
        config = TradingConfig()
        expiry_days = config.fundamental_cache_expiry_days
    except Exception:
        pass

    # Offline mode check (expiry_days < 0 and not force_refetch): skip network requests entirely
    if expiry_days < 0 and not force_refetch:
        logger.info("[Offline Mode] Skipping fundamental network fetching (expiry_days < 0). Using existing DB cache.")
        return 0

    current_time = datetime.now()
    skipped = 0
    to_fetch = []

    for sym in symbols:
        if not force_refetch and sym in meta_cache:
            # If the DB already has valid positive BPS or Book Value for this symbol, respect the cache window.
            # If BPS is missing / 0.0 (e.g. from legacy incomplete fetches), do NOT skip so modern parser re-fetches it.
            has_valid_bps = (sym in valid_bps_symbols) if (valid_bps_symbols is not None and len(valid_bps_symbols) > 0) else False
            if has_valid_bps:
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

    total_fetch = len(to_fetch)
    stored = 0
    success = 0
    done_count = 0

    def _fetch_and_save_one(sym: str) -> tuple[str, bool]:
        market = symbol_market_map.get(sym, 'SP500')
        sh_val = shares_map.get(sym) if shares_map else None
        df_fun = fetch_fundamentals(sym, market, shares_outstanding=sh_val)
        if df_fun is not None and not df_fun.empty:
            try:
                df_fun_copy = df_fun.copy()
                df_fun_copy['symbol'] = sym
                df_fun_copy['date'] = df_fun_copy.index.strftime('%Y-%m-%d')
                df_fun_copy = df_fun_copy.reset_index(drop=True)
                storage.save_fundamentals(df_fun_copy)
                if hasattr(storage, 'save_fundamental_meta'):
                    storage.save_fundamental_meta(sym, current_time.strftime("%Y-%m-%d"))
                return (sym, True)
            except Exception as _save_e:
                logger.warning(f"Failed to store fundamentals for {sym}: {_save_e}")
                return (sym, False)
        return (sym, False)

    workers = max(1, min(max_workers, 12))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_fetch_and_save_one, sym): sym for sym in to_fetch}
        for future in as_completed(futures):
            sym, ok = future.result()
            done_count += 1
            if ok:
                stored += 1
                success += 1
            if done_count % 50 == 0 or done_count == total_fetch:
                logger.info(f"Fundamentals progress: {done_count}/{total_fetch} ({success} fetched, {skipped} skipped)")

    logger.info(f"Streamed and stored fundamentals for {stored}/{total_fetch} symbols in DB")
    return stored
