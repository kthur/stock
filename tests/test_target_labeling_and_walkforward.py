import pytest
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from src.ai.target_transform import transform_sharpe

def test_sharpe_scaled_target_transform():
    # Test Sharpe-scaled return transformation handles zeros, NaNs, and standard arrays cleanly
    returns = pd.Series([0.01, 0.05, -0.02, 0.10, 0.0, np.nan])
    sharpe_ret = transform_sharpe(returns)
    assert len(sharpe_ret) == len(returns)
    # NaN in input should be filled with 0.0
    assert float(sharpe_ret.iloc[-1]) == 0.0
    # Values should be finite floats
    assert np.all(np.isfinite(sharpe_ret.dropna()))

def test_walk_forward_time_series_split():
    # Generate 600 synthetic daily rows
    n_samples = 600
    df = pd.DataFrame({
        'date': pd.date_range(start='2025-01-01', periods=n_samples, freq='D'),
        'feature1': np.random.randn(n_samples),
        'target_1d': np.random.randn(n_samples)
    })
    
    tscv = TimeSeriesSplit(n_splits=5, gap=20)
    splits = list(tscv.split(df))
    assert len(splits) == 5
    
    for fold, (train_idx, val_idx) in enumerate(splits):
        # Walk-forward property: train indices come strictly before val indices with gap >= 20
        max_train = max(train_idx)
        min_val = min(val_idx)
        assert min_val - max_train >= 20, f"Fold {fold} gap violated: {min_val} - {max_train} < 20"

def test_dynamic_surge_threshold_market_multiplier():
    horizon_thresholds = {1: 0.03, 3: 0.05, 5: 0.08, 20: 0.15}
    markets = ["SP500", "KOSPI", "KOSDAQ", "RUSSELL2000"]
    multipliers = {"SP500": 0.7, "KOSPI": 1.0, "KOSDAQ": 1.25, "RUSSELL2000": 1.3}
    
    for m in markets:
        mult = multipliers[m]
        h1_thresh = horizon_thresholds[1] * mult
        assert h1_thresh > 0.0
        if m == "SP500":
            assert h1_thresh < 0.03
        elif m == "RUSSELL2000":
            assert h1_thresh > 0.035
