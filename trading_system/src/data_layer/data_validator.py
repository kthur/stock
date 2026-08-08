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
            and not (isinstance(us10y_val, float) and math.isnan(us10y_val))
            and us10y_val < 25
            else us10y_val
        ),
    ):
        try:
            fv = float(v)
            if fv > 0 and not math.isnan(fv):
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
      3. Daily return absolute value > 100% on more than 5% of rows -> suspicious/corrupted
      4. Volume == 0 ratio > 90% -> likely halted/suspended ticker
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

    # 2. Extreme daily returns (> ±100% on more than 5% of rows)
    if len(valid_close) >= 5:
        daily_ret = valid_close.pct_change().abs().dropna()
        if len(daily_ret) > 0:
            extreme_ratio = (daily_ret > 1.0).sum() / len(daily_ret)
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
