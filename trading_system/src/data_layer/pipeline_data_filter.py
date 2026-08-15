"""
Pipeline Data Quality Filter Module

Provides clean data filtering to remove bad rows, extreme volume outliers,
and insufficient history stocks before feature engineering and training.
"""

import numpy as np
import pandas as pd

def filter_training_data(
    df_train: pd.DataFrame,
    min_volume: float = 0.0,
    min_history_days: int = 70,
    sigma_threshold: float = 4.0
) -> pd.DataFrame:
    """
    Filters raw training data:
    1. Removes rows with zero or missing trading volume.
    2. Removes extreme price percentage change outliers (beyond sigma_threshold).
    3. Removes symbols with fewer than min_history_days records.
    """
    if df_train is None or df_train.empty:
        return pd.DataFrame() if df_train is None else df_train

    df = df_train.copy()

    # 1. Filter zero/missing volume if Volume column is available
    vol_col = next((c for c in ['Volume', 'volume', 'norm_volume'] if c in df.columns), None)
    if vol_col:
        num_vol = pd.to_numeric(df[vol_col], errors='coerce').fillna(0.0)
        df = df[num_vol > min_volume]

    # 2. Filter price extreme feature outliers (4-sigma rule on return features; exclude targets to preserve surge labels)
    ret_cols = [c for c in df.columns if c.startswith('ret_') and not c.startswith('target_')]
    for col in ret_cols:
        s = pd.to_numeric(df[col], errors='coerce')
        valid_s = s.dropna()
        if len(valid_s) > 10:
            mu = float(valid_s.mean())
            std = float(valid_s.std())
            if np.isfinite(std) and std > 1e-8:
                mask = (s - mu).abs() <= sigma_threshold * std
                df = df[mask.fillna(True)]

    # 3. Filter symbols with insufficient history
    sym_col = next((c for c in ['symbol', 'Symbol', 'code', 'Code'] if c in df.columns), None)
    if sym_col:
        counts = df.groupby(sym_col)[sym_col].transform('count')
        df = df[counts >= min_history_days]

    return df.reset_index(drop=True)
