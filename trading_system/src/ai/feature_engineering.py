import os
import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

# Canonical list of VCP feature column names produced by compute_vcp_features()
VCP_FEATURES = [
    'range_5v20', 'range_10v20', 'range_20v40', 'range_40v60',
    'vol_20v60', 'dist_ma50', 'dist_ma200',
    'range_pos_10d', 'range_pos_20d', 'atr_14d_norm', 'monotonic', 'vcp_score',
]

def get_scaler_path(model_dir: str, market: str, horizon: int) -> str:
    return os.path.join(model_dir, f"scaler_{market}_{horizon}d.joblib")

def fit_scaler(df: pd.DataFrame, features: list, model_dir: str, market: str, horizon: int) -> StandardScaler:
    scaler = StandardScaler()
    # Fill remaining NaNs with 0 before scaling to ensure safety
    X = df[features].fillna(0.0)
    scaler.fit(X)

    os.makedirs(model_dir, exist_ok=True)
    scaler_path = get_scaler_path(model_dir, market, horizon)
    joblib.dump(scaler, scaler_path)
    logger.info(f"Saved feature scaler for {market} {horizon}d to {scaler_path}")
    return scaler

def load_scaler(model_dir: str, market: str, horizon: int) -> StandardScaler:
    scaler_path = get_scaler_path(model_dir, market, horizon)
    if os.path.exists(scaler_path):
        return joblib.load(scaler_path)
    logger.warning(f"Scaler not found at {scaler_path}. Returning default StandardScaler.")
    return StandardScaler()

def apply_scaler(df: pd.DataFrame, features: list, scaler: StandardScaler) -> pd.DataFrame:
    if df.empty:
        return df
    df_copy = df.copy()
    X = df_copy[features].fillna(0.0)
    # Handle scaler not fitted yet
    try:
        scaled_values = scaler.transform(X)
        df_copy[features] = scaled_values
    except Exception as e:
        logger.warning(f"Failed to apply scaling: {e}. Using raw features.")
    return df_copy

def compute_vcp_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized computation of 11 VCP (Volatility Contraction Pattern) features.
    
    Expected input df contains columns (capitalized): ['High', 'Low', 'Close', 'Volume']
    Returns DataFrame with added columns:
      ['range_5v20', 'range_10v20', 'range_20v40', 'range_40v60', 'vol_20v60',
       'dist_ma50', 'dist_ma200', 'range_pos_10d', 'range_pos_20d', 'atr_14d_norm',
       'monotonic', 'vcp_score']
    """
    import numpy as np
    df = df.copy()

    # Align casing
    df.columns = [str(c).capitalize() if str(c).lower() in ['open', 'high', 'low', 'close', 'volume'] else str(c) for c in df.columns]

    high = df['High'].astype(float) if 'High' in df.columns else df['Close'].astype(float)
    low = df['Low'].astype(float) if 'Low' in df.columns else df['Close'].astype(float)
    close = df['Close'].astype(float)
    volume = df['Volume'].astype(float)

    # Guard: return empty DataFrame if key columns are all NaN
    if high.isna().all() or close.isna().all():
        return pd.DataFrame()

    # 1. Range ratios
    range_pct = (high - low) / (close + 1e-9) * 100
    r5 = range_pct.rolling(5, min_periods=1).max()
    r10 = range_pct.rolling(10, min_periods=1).max()
    r20 = range_pct.rolling(20, min_periods=1).max()
    r40 = range_pct.rolling(40, min_periods=1).max()
    r60 = range_pct.rolling(60, min_periods=1).max()

    df['range_5v20'] = (r5 / r20.replace(0, 1e-10)).fillna(0.0)
    df['range_10v20'] = (r10 / r20.replace(0, 1e-10)).fillna(0.0)
    df['range_20v40'] = (r20 / r40.replace(0, 1e-10)).fillna(0.0)
    df['range_40v60'] = (r40 / r60.replace(0, 1e-10)).fillna(0.0)

    # 2. Volume ratio
    vol_20d = volume.rolling(20, min_periods=1).mean()
    vol_60d = volume.rolling(60, min_periods=1).mean()
    df['vol_20v60'] = (vol_20d / vol_60d.replace(0, 1e-10)).fillna(0.0)

    # 3. Distance from moving averages
    sma50 = close.rolling(50, min_periods=1).mean()
    sma200 = close.rolling(200, min_periods=1).mean()
    df['dist_ma50'] = ((close - sma50) / sma50.abs().replace(0, 1e-10)).fillna(0.0)
    df['dist_ma200'] = ((close - sma200) / sma200.abs().replace(0, 1e-10)).fillna(0.0)

    # 4. Position within range
    high_10d = high.rolling(10, min_periods=1).max()
    low_10d = low.rolling(10, min_periods=1).min()
    high_20d = high.rolling(20, min_periods=1).max()
    low_20d = low.rolling(20, min_periods=1).min()
    df['range_pos_10d'] = ((close - low_10d) / (high_10d - low_10d).replace(0, 1e-10)).fillna(0.0)
    df['range_pos_20d'] = ((close - low_20d) / (high_20d - low_20d).replace(0, 1e-10)).fillna(0.0)

    # 5. Normalized ATR
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr_val = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_14 = tr_val.rolling(14, min_periods=1).mean()
    df['atr_14d_norm'] = ((atr_14 / close.replace(0, 1e-10)) * 100).fillna(0.0)

    # 6. Contraction Monotonicity
    monotonic = (r5 < r10) & (r10 < r20) & (r20 < r40) & (r40 < r60)
    df['monotonic'] = monotonic.astype(float)

    # 7. VCP Score calculation
    score = pd.Series(0.0, index=df.index)
    score += np.where(monotonic, 25.0, 0.0)
    score += np.where(vol_20d < vol_60d * 0.85, 15.0, 0.0)
    score += np.where(close > sma50, 15.0, 0.0)
    score += np.where(close > sma200, 15.0, 0.0)
    score += np.where(df['range_pos_10d'] > 0.6, 15.0, 0.0)
    score += np.where(close > close.shift(10), 15.0, 0.0)
    score += np.where(r5 < 4.0, 20.0,
                      np.where(r5 < 7.0, 12.0,
                               np.where(r5 < 10.0, 6.0, 0.0)))
    df['vcp_score'] = score.clip(upper=100.0) / 100.0

    return df
