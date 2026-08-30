import numpy as np
import pandas as pd
from src.data_layer.pipeline_data_filter import filter_training_data

def test_filter_training_data_volume_and_outliers():
    np.random.seed(42)
    n_rows = 200
    
    # Create DataFrame with normal data + 1 zero volume + 1 extreme outlier
    df = pd.DataFrame({
        'symbol': ['AAA'] * 100 + ['BBB'] * 100,
        'Volume': [1000.0] * 199 + [0.0],  # 1 zero volume row
        'ret_1d': np.random.normal(0, 0.02, n_rows),
        'target_1d': np.random.normal(0, 0.02, n_rows)
    })
    
    # Insert extreme outlier (+1.0 return when std ~0.02)
    df.loc[10, 'ret_1d'] = 1.0
    
    filtered_df = filter_training_data(df, min_volume=0.0, min_history_days=50, sigma_threshold=4.0)
    
    # Extreme outlier and zero volume should be filtered out
    assert len(filtered_df) < n_rows
    assert 1.0 not in filtered_df['ret_1d'].values
    assert 0.0 not in filtered_df['Volume'].values

def test_filter_training_data_insufficient_history():
    df = pd.DataFrame({
        'symbol': ['MANY_DAYS'] * 100 + ['FEW_DAYS'] * 10,
        'Volume': [500.0] * 110,
        'target_1d': [0.01] * 110
    })
    
    filtered_df = filter_training_data(df, min_volume=0.0, min_history_days=50)
    
    # 'FEW_DAYS' should be removed, leaving only 'MANY_DAYS'
    assert 'FEW_DAYS' not in filtered_df['symbol'].values
    assert 'MANY_DAYS' in filtered_df['symbol'].values
    assert len(filtered_df) == 100
