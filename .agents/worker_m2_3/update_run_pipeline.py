from pathlib import Path

path = Path(r"d:\Finance\code\stock\trading_system\run_pipeline.py")

target = """@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=(retry_if_result(is_empty_result) | retry_if_exception_type(Exception)),
    reraise=False
)
def _download_indicator_network(ticker: str, start_date: str) -> pd.DataFrame:
    # Coordinate indicator fetch rate limiting
    get_global_rate_limiter().wait()
    # Tier 1: yfinance
    try:
        raw = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if raw is not None and not raw.empty:
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.droplevel(1)
            return raw
    except Exception as e:
        logger.debug(f"Tier 1 indicator download error for {ticker}: {e}")

    # Tier 2: FinanceDataReader
    try:
        raw = fdr.DataReader(ticker, start=start_date)
        if raw is not None and not raw.empty:
            logger.warning(f"Successfully retrieved Tier 2 indicator data for {ticker} via FDR")
            return raw
    except Exception as e:
        logger.debug(f"Tier 2 indicator download error for {ticker}: {e}")

    raise ValueError(f"Downloaded indicator {ticker} is empty or None across all providers")"""

replacement = """@retry(
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

    raise ValueError(f"Downloaded indicator {ticker} is empty or None across all providers")"""

with open(path, "r+", encoding="utf-8") as f:
    content = f.read()
    assert target in content, "Target pattern not found in run_pipeline.py"
    new_content = content.replace(target, replacement, 1)
    f.seek(0)
    f.write(new_content)
    f.truncate()

print("Successfully updated run_pipeline.py via r+ mode")
