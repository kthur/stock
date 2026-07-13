import numpy as np
import pandas as pd


def transform_return(ret_series: pd.Series) -> pd.Series:
    """Apply clipping and log1p transformation to returns to stabilize targets."""
    # Clip returns to extreme range [-0.5, 0.5] before transformation
    clipped = np.clip(ret_series, -0.5, 0.5)
    return np.log1p(clipped)


def transform_sharpe(sharpe_series: pd.Series) -> pd.Series:
    """Apply clipping and log1p transformation to Sharpe-scaled returns.

    Sharpe values (raw_ret / vol_20d) are typically in [-10, 10] range,
    so the clip window is expanded vs. raw returns.
    We map via: sign(x) * log1p(|x|) to preserve sign and compress extremes.
    """
    clipped = np.clip(sharpe_series, -10.0, 10.0)
    return np.sign(clipped) * np.log1p(np.abs(clipped))


def inverse_transform(pred_series: pd.Series) -> pd.Series:
    """Invert the log1p transform back to normal expected returns."""
    return np.expm1(pred_series)


def inverse_transform_sharpe(pred_series: pd.Series,
                              vol_scale: pd.Series) -> pd.Series:
    """Invert Sharpe-scaled predictions back to raw expected returns.

    1. Invert sign * log1p(|x|)  →  Sharpe-scaled value
    2. Multiply by current vol_20d  →  raw return

    Args:
        pred_series: Model output in sign-log1p(Sharpe) space.
        vol_scale:   Per-symbol 20-day realised volatility (same index).

    Returns:
        pd.Series of expected raw returns.
    """
    # Invert sign * log1p(|pred|) → Sharpe value
    sharpe = np.sign(pred_series) * (np.expm1(np.abs(pred_series)))
    # Scale back to raw return
    raw_ret = sharpe * vol_scale.values
    return pd.Series(raw_ret, index=pred_series.index)
