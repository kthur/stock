"""Fetch corporate earnings/fundamental data from Yahoo Finance."""

import logging
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf

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
        suffix = _KR_MARKET_SUFFIX.get(market, '.KS')
        return f"{cleaned}{suffix}"
    return cleaned


def fetch_fundamentals(symbol: str, market: Optional[str] = None, max_retries: int = 3) -> Optional[pd.DataFrame]:
    """
    Fetch annual fundamental data from Yahoo Finance.

    Returns DataFrame with columns:
        date, revenue, operating_income, net_income, eps,
        shares_outstanding, dividend_per_share
    One row per fiscal year, sorted chronologically.
    Returns None if no data is available.
    """
    import time
    yf_sym = _yf_ticker(symbol, market)

    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(yf_sym)
            financials = ticker.financials
            if financials is None or financials.empty:
                if attempt == 0:
                    logger.debug(f"No annual financials for {symbol} ({yf_sym})")
                return None

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
            div = info.get('dividendRate', info.get('dividendYield', 0) * fin.iloc[-1].get('Basic EPS', 1))
            result['dividend_per_share'] = max(0, div if div else 0)

            for col in ['revenue', 'operating_income', 'net_income', 'eps']:
                result[col] = result[col].fillna(0).astype(float)

            # Rate limit prevention: small delay between requests
            time.sleep(0.05)

            return result

        except Exception as e:
            err_msg = str(e)
            if 'Rate limited' in err_msg or '401' in err_msg or 'Unauthorized' in err_msg:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited for {symbol} ({yf_sym}), retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                else:
                    logger.warning(f"Rate limited for {symbol} ({yf_sym}) after {max_retries} attempts, skipping")
            else:
                logger.debug(f"Failed to fetch fundamentals for {symbol} ({yf_sym}): {e}")
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
    Skips symbols that already have fundamentals in DB (unless force_refetch=True).
    Uses sequential requests with delay to avoid Yahoo Finance rate limits.
    Returns count of successfully stored symbols.
    """
    skipped = 0
    results: Dict[str, Optional[pd.DataFrame]] = {}
    success = 0
    total = len(symbols)

    for idx, sym in enumerate(symbols, 1):
        # Skip if already in DB
        if not force_refetch and hasattr(storage, 'fundamentals_exist') and storage.fundamentals_exist(sym):
            skipped += 1
            continue

        market = symbol_market_map.get(sym, 'SP500')
        df_fun = fetch_fundamentals(sym, market)
        if df_fun is not None and not df_fun.empty:
            results[sym] = df_fun
            success += 1

        if idx % 500 == 0 or idx == total:
            logger.info(f"Fundamentals progress: {idx}/{total} ({success} fetched, {skipped} skipped)")

    logger.info(f"Fetched fundamentals for {success} symbols ({skipped} skipped, already in DB)")

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
