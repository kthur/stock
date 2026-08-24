import numpy as np
import pandas as pd


def transform_return(ret_series: pd.Series) -> pd.Series:
    """Apply clipping and log1p transformation to returns to stabilize targets."""
    s_clean = pd.to_numeric(pd.Series(ret_series), errors='coerce').fillna(0.0)
    # Clip returns to extreme range [-0.5, 0.5] before transformation
    clipped = np.clip(s_clean, -0.5, 0.5)
    return np.log1p(clipped)


def transform_sharpe(sharpe_series: pd.Series) -> pd.Series:
    """Apply clipping and log1p transformation to Sharpe-scaled returns.

    Sharpe values (raw_ret / vol_20d) are typically in [-10, 10] range,
    so the clip window is expanded vs. raw returns.
    We map via: sign(x) * log1p(|x|) to preserve sign and compress extremes.
    """
    s_clean = pd.to_numeric(pd.Series(sharpe_series), errors='coerce').fillna(0.0)
    clipped = np.clip(s_clean, -10.0, 10.0)
    return np.sign(clipped) * np.log1p(np.abs(clipped))


def inverse_transform(pred_series: pd.Series) -> pd.Series:
    """Invert the log1p transform back to normal expected returns."""
    s_clean = pd.to_numeric(pd.Series(pred_series), errors='coerce').fillna(0.0)
    clipped = np.clip(s_clean, -20.0, 20.0)
    return pd.Series(np.expm1(clipped), index=s_clean.index)


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
    p_clean = pd.to_numeric(pd.Series(pred_series), errors='coerce').fillna(0.0)
    p_clipped = np.clip(np.abs(p_clean), 0.0, 20.0)
    # Invert sign * log1p(|pred|) → Sharpe value with expm1 overflow prevention
    sharpe = np.sign(p_clean) * np.expm1(p_clipped)
    # Scale back to raw return with a floor on vol_scale so zero vol doesn't zero returns
    if hasattr(vol_scale, 'values'):
        v_vals = vol_scale.values
    else:
        v_vals = np.array(vol_scale)
    v_vals = np.nan_to_num(pd.to_numeric(pd.Series(v_vals.ravel() if hasattr(v_vals, 'ravel') else v_vals), errors='coerce').fillna(0.01).values, nan=0.01)
    floored_vol = np.maximum(v_vals, 0.005)
    raw_ret = np.nan_to_num(sharpe.values * floored_vol, nan=0.0)
    return pd.Series(raw_ret, index=p_clean.index)
