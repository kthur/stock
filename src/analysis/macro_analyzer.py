"""
Global Macro Correlation Engine
Calculates cross-correlations among major global indices and FX rates.
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.

MACRO_SYMBOLS = ["^GSPC", "^IXIC", "^KS11", "^KQ11", "USDKRW=X", "^TNX", "^VIX"]


def calculate_cross_correlation(indices_data: pd.DataFrame, lags: int = 5) -> pd.DataFrame:
    """
    Aligns timezone-mismatched indices, forward-fills missing values,
    calculates percentage returns, and computes Pearson cross-correlation
    with lags (0 to lags days) for the indices.

    Args:
        indices_data: pd.DataFrame with Date index and ticker columns.
        lags: int, maximum number of lag days (default 5).

    Returns:
        pd.DataFrame: Pearson correlation matrix with columns as MultiIndex (ticker, lag).
    """
    if indices_data is None or indices_data.empty:
        return pd.DataFrame()

    safe_lags = max(0, min(60, int(lags))) if lags is not None else 5
    df = indices_data.copy()

    # 1. Align timezone-mismatched indices: convert index to naive normalized date
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors='coerce')

    # Drop NaT dates from index
    df = df[df.index.notna()]

    # Normalize index to timezone-naive dates
    if df.index.tz is not None:
        try:
            df.index = df.index.tz_convert(None)
        except Exception:
            df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()

    # Handle duplicate dates by taking the mean
    df = df.groupby(df.index).mean()

    # 2. Forward fill and backward fill missing values
    df = df.infer_objects(copy=False).ffill().bfill()

    # 3. Calculate percentage returns
    returns = df.pct_change(fill_method=None).dropna(how="all")

    # 4. Compute Pearson cross-correlation with lags (0 to lags days)
    tickers = [t for t in MACRO_SYMBOLS if t in returns.columns]
    if not tickers:
        tickers = list(returns.columns)

    col_index = pd.MultiIndex.from_product([tickers, range(safe_lags + 1)], names=["ticker", "lag"])
    corr_df = pd.DataFrame(index=tickers, columns=col_index, dtype=float)

    for lag in range(safe_lags + 1):
        shifted = returns.shift(lag)
        for t1 in tickers:
            for t2 in tickers:
                val = returns[t1].corr(shifted[t2])
                if val is not None and np.isfinite(val):
                    corr_df.loc[t1, (t2, lag)] = float(val)
                elif lag == 0 and t1 == t2 and returns[t1].notna().sum() >= 2 and (float(returns[t1].std()) > 1e-8):
                    corr_df.loc[t1, (t2, lag)] = 1.0
                else:
                    corr_df.loc[t1, (t2, lag)] = 0.0

    return corr_df


def get_correlation_matrix_at_lag(corr_df: pd.DataFrame, lag: int = 0) -> pd.DataFrame:
    """Extracts the 2D correlation matrix for a given lag from the multi-lag correlation DataFrame."""
    if corr_df is None or corr_df.empty:
        return pd.DataFrame()
    safe_lag = max(0, int(lag)) if lag is not None else 0
    try:
        return corr_df.xs(safe_lag, axis=1, level="lag")
    except KeyError:
        return pd.DataFrame()


def generate_simulated_macro_data(period: str = "1y") -> dict:
    """Generates realistic simulated historical close prices for macro indices."""
    days_map = {"1mo": 20, "3mo": 60, "6mo": 120, "1y": 250, "2y": 500, "5y": 1250}
    n_days = days_map.get(period, 250)

    dates = pd.date_range(end=datetime.now(), periods=n_days, freq="B")

    starts = {
        "^GSPC": 4500.0,
        "^IXIC": 14000.0,
        "^KS11": 2500.0,
        "^KQ11": 800.0,
        "USDKRW=X": 1300.0,
        "^TNX": 4.0,
        "^VIX": 15.0,
    }

    vols = {
        "^GSPC": 0.01,
        "^IXIC": 0.012,
        "^KS11": 0.011,
        "^KQ11": 0.015,
        "USDKRW=X": 0.006,
        "^TNX": 0.02,
        "^VIX": 0.05,
    }

    drifts = {
        "^GSPC": 0.0003,
        "^IXIC": 0.0004,
        "^KS11": 0.0001,
        "^KQ11": 0.0001,
        "USDKRW=X": 0.00005,
        "^TNX": 0.0001,
        "^VIX": 0.0,
    }

    np.random.seed(42)
    n_symbols = len(starts)
    symbols = list(starts.keys())

    corr_matrix = np.eye(n_symbols)
    sym_to_idx = {s: i for i, s in enumerate(symbols)}

    def set_corr(s1, s2, val):
        i, j = sym_to_idx[s1], sym_to_idx[s2]
        corr_matrix[i, j] = val
        corr_matrix[j, i] = val

    set_corr("^GSPC", "^IXIC", 0.85)
    set_corr("^GSPC", "^KS11", 0.45)
    set_corr("^IXIC", "^KQ11", 0.50)
    set_corr("^KS11", "^KQ11", 0.75)
    set_corr("USDKRW=X", "^KS11", -0.60)
    set_corr("USDKRW=X", "^KQ11", -0.45)
    set_corr("^GSPC", "^VIX", -0.70)
    set_corr("^IXIC", "^VIX", -0.65)
    set_corr("^KS11", "^VIX", -0.35)

    # Project the hardcoded correlation matrix to the nearest positive semi-definite matrix
    w, v = np.linalg.eigh(corr_matrix)
    w = np.maximum(w, 1e-6)
    corr_matrix_psd = v @ np.diag(w) @ v.T
    d = np.sqrt(np.diag(corr_matrix_psd))
    corr_matrix_psd = corr_matrix_psd / np.outer(d, d)
    L = np.linalg.cholesky(corr_matrix_psd)

    rand_normals = np.random.normal(size=(n_days, n_symbols))
    correlated_normals = rand_normals @ L.T

    sim_data = {}
    for i, sym in enumerate(symbols):
        ret = drifts[sym] + correlated_normals[:, i] * vols[sym]
        prices = starts[sym] * np.exp(np.cumsum(ret))
        if sym == "^TNX":
            prices = np.clip(prices, 0.5, 10.0)
        elif sym == "^VIX":
            prices = np.clip(prices, 9.0, 80.0)
        sim_data[sym] = pd.Series(prices, index=dates)

    return sim_data


def fetch_macro_indices_data(period: str = "1y") -> pd.DataFrame:
    """
    Fetches historical data for global macro indices from yfinance.
    If offline or yfinance returns empty/fails, falls back to simulated data.
    """
    data_dict = {}

    try:
        import yfinance as yf

        logger.info("Attempting to fetch global macro data via yfinance...")
        # yf.download handles multiple tickers efficiently
        df = yf.download(MACRO_SYMBOLS, period=period, group_by="ticker", progress=False, timeout=5, auto_adjust=True)

        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                for sym in MACRO_SYMBOLS:
                    if sym in df.columns.levels[0]:
                        close_col = next((c for c in df[sym].columns if str(c).lower() in ('close', 'adj close', 'adjclose')), None)
                        if close_col:
                            close = df[sym][close_col]
                            if not close.dropna().empty:
                                data_dict[sym] = close
            else:
                for sym in MACRO_SYMBOLS:
                    if sym in df.columns:
                        data_dict[sym] = df[sym]
    except Exception as e:
        logger.warning(f"Failed to fetch macro indices data from yfinance: {e}. Falling back to simulation.")

    # If any symbol is missing or all are missing, generate simulated data
    if len(data_dict) < len(MACRO_SYMBOLS):
        logger.info("Generating simulated global macro data due to incomplete yfinance results.")
        data_dict = generate_simulated_macro_data(period=period)

    combined = pd.DataFrame(data_dict)
    # Ensure all MACRO_SYMBOLS are present
    for sym in MACRO_SYMBOLS:
        if sym not in combined.columns:
            combined[sym] = np.nan

    # Shift US symbols forward by 1 day to align US/KR trading sessions and avoid look-ahead bias
    us_symbols = ["^GSPC", "^IXIC", "^TNX", "^VIX"]
    for sym in us_symbols:
        if sym in combined.columns:
            combined[sym] = combined[sym].shift(1)

    return combined
