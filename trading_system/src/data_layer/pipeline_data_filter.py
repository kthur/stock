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
    if df_train.empty:
        return df_train

    df = df_train.copy()

    # 1. Filter zero/missing volume if Volume column is available
    vol_col = next((c for c in ['Volume', 'volume', 'norm_volume'] if c in df.columns), None)
    if vol_col:
        df = df[df[vol_col] > min_volume]

    # 2. Filter price extreme outliers (4-sigma rule on returns if available)
    ret_cols = [c for c in df.columns if c.startswith('ret_') or c.startswith('target_')]
    for col in ret_cols:
        if df[col].dtype in [np.float32, np.float64]:
            mu = df[col].mean()
            std = df[col].std()
            if not np.isnan(std) and std > 0:
                df = df[(df[col] - mu).abs() <= sigma_threshold * std]

    # 3. Filter symbols with insufficient history
    if 'symbol' in df.columns:
        counts = df.groupby('symbol')['symbol'].transform('count')
        df = df[counts >= min_history_days]

    return df.reset_index(drop=True)
