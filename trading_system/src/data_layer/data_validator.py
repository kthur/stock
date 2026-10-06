"""
data_validator.py — Data Quality Gate & Integrity Validation Module

Centralized validation logic for macro indicators, price data, and financial metrics.
Prevents contaminated cache, bad ticker downloads, extreme outliers, and halt states
from propagating into training, inference, and report generation.
"""

from __future__ import annotations

import math
import re
import logging
from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Numeric plausibility bounds for raw global macro indicators
MACRO_BOUNDS: Dict[str, Tuple[float, float]] = {
    "vix": (8.0, 55.0),
    "us10y": (0.5, 15.0),
    "kr10y": (0.5, 15.0),
    "usdkrw": (950.0, 2200.0),
    "wti": (25.0, 180.0),
    "gold": (100.0, 5000.0),
    "sp500": (0.0, 100.0),
}


def detect_shared_series_corruption(
    vix_val: Any, wti_val: Any, gold_val: Any, us10y_val: Any
) -> bool:
    """P0: Detect shared-series / DB cache contamination on RAW indicator values.

    If several unrelated indicators resolve to (nearly) the same value, the DB
    holds one ticker's Close for every symbol (e.g. 103.478 everywhere). Must be
    evaluated on raw values BEFORE plausibility bounds replace out-of-range
    entries, otherwise the VIX gets defaulted first and the spread widens past
    the detection threshold.
    """
    candidates = []
    for v in (
        vix_val,
        wti_val,
        gold_val,
        (
            us10y_val * 10.0
            if us10y_val is not None
            and not (isinstance(us10y_val, (int, float)) and not math.isfinite(us10y_val))
            and us10y_val < 25
            else us10y_val
        ),
    ):
        try:
            fv = float(v)
            if fv > 0 and math.isfinite(fv):
                candidates.append(fv)
        except (TypeError, ValueError):
            continue
    if len(candidates) < 3:
        return False
    return (max(candidates) - min(candidates)) < 1.0


def clean_macro_value(val_str: str, fallback_str: str, kind: str) -> str:
    """Clean and validate macro value string against MACRO_BOUNDS."""
    if not val_str:
        return fallback_str
    lowered = val_str.lower().strip()
    if "nan" in lowered or "none" in lowered or "n/a" in lowered:
        return fallback_str

    m_num = re.search(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[-+]?\d+(?:\.\d+)?", lowered)
    if m_num:
        try:
            num = float(m_num.group(0).replace(",", ""))
            inverted = False
            if kind == "usdkrw":
                if 0.0001 <= num <= 0.005:
                    num = 1.0 / num  # Auto-invert KRW/USD to USD/KRW
                    inverted = True
                elif abs(num - 1.0) < 1e-3:
                    logger.warning(
                        "[DataValidator] USDKRW rate 1.0 is an invalid unit rate. Applying fallback."
                    )
                    return fallback_str
            lo, hi = MACRO_BOUNDS.get(kind, (0.0, 1e9))
            if not (lo <= num <= hi):
                logger.warning(
                    f"[DataValidator] Macro indicator '{kind}' value {num} out of bounds [{lo}, {hi}]. Fallback applied."
                )
                return fallback_str
            if kind == "usdkrw" and inverted:
                return f"{num:.1f}"
            return val_str.strip()
        except ValueError:
            return fallback_str
    return val_str.strip()


def validate_price_data(sym: str, df: pd.DataFrame) -> bool:
    """Return True if OHLCV data passes quality checks, False if it should be rejected.

    Checks:
      1. Close column exists and non-empty
      2. Close <= 0 or NaN ratio > 50% -> reject
      3. Abnormal corporate action price spikes (single-day return magnitude > 300% or unadjusted splits) -> reject
      4. Extreme daily return ratio > 100% on more than 5% of rows -> suspicious/corrupted
      5. Volume == 0 ratio > 90% -> likely halted/suspended ticker
    """
    if df is None or df.empty:
        return False

    # Normalize column casing
    cols_lower = {str(c).lower(): c for c in df.columns}
    close_col = cols_lower.get("close")
    volume_col = cols_lower.get("volume")

    if close_col is None:
        logger.warning(f"[DataValidator] {sym}: missing Close column, skipping")
        return False

    try:
        close = df[close_col].astype(float)
    except Exception as e:
        logger.warning(f"[DataValidator] {sym}: failed to parse Close column: {e}")
        return False

    total_rows = len(close)
    if total_rows == 0:
        return False

    # 1. Close zero/negative or too many NaN
    nan_ratio = close.isna().sum() / total_rows
    valid_close = close.dropna()
    non_positive = (valid_close <= 0).sum()
    if nan_ratio > 0.5:
        logger.warning(f"[DataValidator] {sym}: Close NaN ratio={nan_ratio:.1%} > 50%, skipping")
        return False
    if len(valid_close) > 0 and (non_positive / len(valid_close)) > 0.5:
        logger.warning(f"[DataValidator] {sym}: Close non-positive ratio > 50%, skipping")
        return False

    # 2. Extreme daily returns & corporate action price spikes (> 300% change magnitude)
    if len(valid_close) >= 2:
        prev_close = valid_close.shift(1)
        valid_mask = (prev_close > 0) & np.isfinite(prev_close) & (valid_close > 0) & np.isfinite(valid_close)
        if valid_mask.sum() > 0:
            ratios = (valid_close[valid_mask] / prev_close[valid_mask]).dropna()
            if len(ratios) > 0:
                mags = ratios.apply(lambda r: (max(r, 1.0 / r) - 1.0) if (pd.notna(r) and np.isfinite(r) and r > 0) else 0.0)
                max_mag = float(mags.max()) if len(mags) > 0 else 0.0
                if max_mag > 3.0:
                    logger.warning(
                        f"[DataValidator] {sym}: single-day price return/split spike max_magnitude={max_mag:.1%} > 300% (unadjusted split/corrupted), skipping"
                    )
                    return False

                extreme_ratio = float((mags > 1.0).sum() / len(mags))
                if extreme_ratio > 0.05:
                    logger.warning(
                        f"[DataValidator] {sym}: extreme return ratio={extreme_ratio:.1%} > 5%, skipping"
                    )
                    return False

    # 3. Volume zero ratio (suspended / halted ticker)
    if volume_col is not None:
        try:
            volume = df[volume_col].astype(float)
            zero_vol_ratio = (volume == 0).sum() / total_rows
            if zero_vol_ratio > 0.90:
                logger.debug(
                    f"[DataValidator] {sym}: Volume zero ratio={zero_vol_ratio:.1%} > 90% (halted), skipping"
                )
                return False
        except Exception:
            pass

    return True


def sanitize_and_validate_price_data(
    sym_or_df: str | pd.DataFrame,
    df_or_sym: pd.DataFrame | str | None = None,
) -> Tuple[bool, pd.DataFrame]:
    """Applies CorporateActionAdjuster and filter_price_spikes to backward-adjust stock splits and clean spikes,
    then validates the resulting price data using validate_price_data.

    Returns:
        (is_valid: bool, adjusted_df: pd.DataFrame)
    """
    if isinstance(sym_or_df, pd.DataFrame):
        df = sym_or_df
        sym = str(df_or_sym) if df_or_sym is not None else "UNKNOWN"
    elif isinstance(df_or_sym, pd.DataFrame):
        sym = str(sym_or_df)
        df = df_or_sym
    else:
        return False, pd.DataFrame()

    if df is None or df.empty:
        return False, df if df is not None else pd.DataFrame()

    adjusted_df = filter_price_spikes(df)
    is_valid = validate_price_data(sym, adjusted_df)
    return is_valid, adjusted_df


def filter_price_spikes(df: pd.DataFrame, max_return: float = 3.0) -> pd.DataFrame:
    """Filter, clean, or adjust single-day abnormal price spikes (>300% change magnitude) or unadjusted splits."""
    if df is None or df.empty:
        return df

    from src.data_layer.price_adjuster import CorporateActionAdjuster
    try:
        adjusted = CorporateActionAdjuster().adjust_ohlcv(df)
    except Exception as e:
        logger.debug(f"[DataValidator] CorporateActionAdjuster error in filter_price_spikes: {e}")
        adjusted = df.copy()

    cols_lower = {str(c).lower(): c for c in adjusted.columns}
    close_col = cols_lower.get("close")
    if close_col is None or len(adjusted) < 2:
        return adjusted

    try:
        close = pd.to_numeric(adjusted[close_col], errors='coerce')
        prev_close = close.shift(1).replace(0, np.nan)
        ratios = (close / prev_close).fillna(1.0)
        mags = ratios.apply(lambda r: (max(r, 1.0 / r) - 1.0) if (pd.notna(r) and r > 0) else 0.0)

        if (mags > max_return).any():
            logger.warning(
                f"[DataValidator] filter_price_spikes: handling price spike/split anomalies (> {max_return:.0%})"
            )
            n = len(adjusted)
            price_cols = [cols_lower[k] for k in ["open", "high", "low", "close"] if k in cols_lower]
            for pc in price_cols:
                adjusted[pc] = pd.to_numeric(adjusted[pc], errors='coerce')

            close_arr = adjusted[close_col].to_numpy(dtype=np.float64, copy=True)

            for i in range(1, n):
                r = float(ratios.iloc[i])
                if r <= 0 or pd.isna(r):
                    continue
                mag = max(r, 1.0 / r) - 1.0
                if mag > max_return:
                    idx_curr = adjusted.index[i]
                    p_prev = float(close_arr[i - 1])

                    is_isolated = False
                    if i + 1 < n:
                        p_next = float(close_arr[i + 1])
                        r_next = p_next / p_prev if p_prev > 0 else 1.0
                        mag_next = max(r_next, 1.0 / r_next) - 1.0 if (pd.notna(r_next) and r_next > 0) else 0.0
                        if mag_next <= max_return:
                            is_isolated = True

                    if is_isolated:
                        p_next_val = float(close_arr[i + 1]) if (i + 1 < n and math.isfinite(float(close_arr[i + 1]))) else p_prev
                        p_fill = (p_prev + p_next_val) / 2.0 if (p_prev > 0 and math.isfinite(p_prev)) else p_next_val
                        p_fill = p_fill if math.isfinite(p_fill) else p_prev
                        for pc in price_cols:
                            adjusted.loc[idx_curr, pc] = p_fill
                        close_arr[i] = p_fill
                    elif i + 1 == n:
                        for pc in price_cols:
                            adjusted.loc[idx_curr, pc] = p_prev
                        close_arr[i] = p_prev
                    else:
                        if r > 0 and math.isfinite(r):
                            prior_mask = adjusted.index < idx_curr
                            for pc in price_cols:
                                adjusted.loc[prior_mask, pc] = adjusted.loc[prior_mask, pc] * r
                            volume_col = cols_lower.get("volume")
                            if volume_col is not None:
                                adjusted.loc[prior_mask, volume_col] = adjusted.loc[prior_mask, volume_col] / r
                            close_arr = adjusted[close_col].to_numpy(dtype=np.float64, copy=True)
                            close_s = pd.Series(close_arr)
                            ratios = (close_s / close_s.shift(1).replace(0, np.nan)).fillna(1.0)
    except Exception as e:
        logger.warning(f"[DataValidator] filter_price_spikes failed: {e}")

    return adjusted


class DataValidator:
    """Centralized Data Quality Gate Manager."""

    MACRO_BOUNDS = MACRO_BOUNDS

    @staticmethod
    def detect_shared_series_corruption(
        vix_val: Any, wti_val: Any, gold_val: Any, us10y_val: Any
    ) -> bool:
        return detect_shared_series_corruption(vix_val, wti_val, gold_val, us10y_val)

    @staticmethod
    def clean_macro_value(val_str: str, fallback_str: str, kind: str) -> str:
        return clean_macro_value(val_str, fallback_str, kind)

    @staticmethod
    def validate_price_data(sym: str, df: pd.DataFrame) -> bool:
        return validate_price_data(sym, df)

    @staticmethod
    def sanitize_and_validate_price_data(
        sym_or_df: str | pd.DataFrame,
        df_or_sym: pd.DataFrame | str | None = None,
    ) -> Tuple[bool, pd.DataFrame]:
        return sanitize_and_validate_price_data(sym_or_df, df_or_sym)

    @staticmethod
    def filter_price_spikes(df: pd.DataFrame, max_return: float = 3.0) -> pd.DataFrame:
        return filter_price_spikes(df, max_return)

    @staticmethod
    def validate_and_clean_price_series(df: pd.DataFrame, max_daily_jump: float = 0.65) -> pd.DataFrame:
        """
        Validates price series for unadjusted split anomalies or erroneous data feeds.
        Interpolates transient spikes/drops > max_daily_jump (65%) across all OHLC columns
        and enforces strict OHLC boundary invariants (Low <= Open, Close <= High).
        D3 / D7: Reconciled canonical implementation with float64 Volume protection.
        """
        if df.empty or len(df) < 5 or 'Close' not in df.columns:
            return df

        df_clean = df.copy()

        # D3 Fix: Ensure Volume column is converted to float64 to prevent LossySetitemError on in-place slice division
        if 'Volume' in df_clean.columns:
            df_clean['Volume'] = pd.to_numeric(df_clean['Volume'], errors='coerce').astype(np.float64)

        close = df_clean['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        pct_chg = close.pct_change().abs()
        anomalies = pct_chg > max_daily_jump
        transient_spikes = pd.Series(False, index=df_clean.index)
        if anomalies.any():
            # V8-HIGH-13 Fix: Causal isolation for real-time / current bar (eliminate pct_change(-1) lookahead)
            if len(close) >= 3:
                next_pct_chg = close.pct_change(-1).abs()
                is_transient = anomalies.iloc[:-1] & (next_pct_chg.iloc[:-1] > (max_daily_jump * 0.8))
                transient_spikes.iloc[:-1] = is_transient

                # Causal guard for current bar: check against causal rolling median without looking forward
                if bool(anomalies.iloc[-1]):
                    rolling_med = close.iloc[-21:-1].median() if len(close) >= 21 else close.iloc[:-1].median()
                    if rolling_med > 0 and abs(close.iloc[-1] / rolling_med - 1.0) > (max_daily_jump * 2.0):
                        transient_spikes.iloc[-1] = True
            if transient_spikes.any():
                logger.warning(f"Detected {transient_spikes.sum()} transient price anomalies. Interpolating clean OHLC values.")
                for col in ['Close', 'Open', 'High', 'Low']:
                    if col in df_clean.columns:
                        df_clean.loc[transient_spikes, col] = np.nan
                        df_clean[col] = df_clean[col].interpolate(method='linear').ffill().bfill()

        # Detect reverse stock splits (permanent upward jumps > 50% that don't revert) with volume contraction
        rev_split_candidates = (close.pct_change(fill_method=None) > 0.50) & (~transient_spikes)
        if rev_split_candidates.any():
            rev_dates = rev_split_candidates[rev_split_candidates].index
            for date in rev_dates:
                idx = df_clean.index.get_loc(date)
                if isinstance(idx, slice):
                    idx = idx.start
                elif isinstance(idx, np.ndarray):
                    idx = np.where(idx)[0][0]
                if idx > 0:
                    prev_close = df_clean['Close'].iloc[idx-1]
                    curr_close = df_clean['Close'].iloc[idx]
                    if prev_close > 0:
                        rev_ratio = curr_close / prev_close
                        if any(abs(rev_ratio - r) / r < 0.08 for r in [1.5, 2.0, 3.0, 4.0, 5.0, 10.0, 20.0, 50.0, 100.0]):
                            logger.warning(f"Detected reverse stock split around {date} with ratio {rev_ratio:.4f}. Adjusting historical data.")
                            for col in ['Open', 'High', 'Low', 'Close']:
                                if col in df_clean.columns:
                                    df_clean.iloc[:idx, df_clean.columns.get_loc(col)] *= rev_ratio
                            if 'Volume' in df_clean.columns:
                                df_clean.iloc[:idx, df_clean.columns.get_loc('Volume')] /= rev_ratio

        # Detect stock splits (permanent drops > 25% that don't revert) with crash guard & volume confirmation
        split_candidates = (close.pct_change(fill_method=None) < -0.25) & (~transient_spikes)
        if split_candidates.any():
            split_dates = split_candidates[split_candidates].index
            for date in split_dates:
                # Get index of the date
                idx = df_clean.index.get_loc(date)
                if isinstance(idx, slice):
                    idx = idx.start
                elif isinstance(idx, np.ndarray):
                    idx = np.where(idx)[0][0]

                if idx > 0:
                    prev_close = df_clean['Close'].iloc[idx-1]
                    curr_close = df_clean['Close'].iloc[idx]
                    if prev_close > 0:
                        ratio = curr_close / prev_close
                        # Standard split ratio check (e.g. 1:2, 1:3, 1:4, 1:5, 1:10, 2:3, 3:4)
                        is_standard_split_ratio = any(abs(ratio - r) / r < 0.08 for r in [0.5, 0.3333, 0.25, 0.2, 0.1, 0.05, 0.6667, 0.75])

                        # Volume expansion confirmation (>1.25x volume expansion or zero-volume recovery)
                        has_vol_confirmation = True
                        if 'Volume' in df_clean.columns and len(df_clean['Volume']) > idx:
                            vol_prev = float(df_clean['Volume'].iloc[idx-1])
                            vol_curr = float(df_clean['Volume'].iloc[idx])
                            if vol_prev > 0 and vol_curr > 0:
                                has_vol_confirmation = (vol_curr / vol_prev) >= 1.25

                        if is_standard_split_ratio and has_vol_confirmation:
                            logger.warning(f"Detected stock split around {date} with ratio {ratio:.4f}. Adjusting historical data.")
                            for col in ['Open', 'High', 'Low', 'Close']:
                                if col in df_clean.columns:
                                    df_clean.iloc[:idx, df_clean.columns.get_loc(col)] *= ratio
                            if 'Volume' in df_clean.columns:
                                df_clean.iloc[:idx, df_clean.columns.get_loc('Volume')] /= ratio

        # Enforce OHLC consistency invariants
        if 'High' in df_clean.columns and 'Low' in df_clean.columns and 'Close' in df_clean.columns:
            open_series = df_clean['Open'] if 'Open' in df_clean.columns else df_clean['Close']
            df_clean['High'] = np.fmax(df_clean['High'], np.fmax(open_series, df_clean['Close']))
            df_clean['Low'] = np.fmin(df_clean['Low'], np.fmin(open_series, df_clean['Close']))
            df_clean['Low'] = df_clean['Low'].clip(lower=1e-4)

        return df_clean
