import numpy as np
import pandas as pd
import pytest
from src.ai.feature_engineering import compute_advanced_alpha_features, ALPHA_FEATURES
from src.ai.purged_cv import PurgedKFold

def test_advanced_alpha_features():
    dates = pd.date_range('2026-01-01', periods=300)
    df = pd.DataFrame({
        'High': np.linspace(100, 200, 300),
        'Low': np.linspace(95, 195, 300),
        'Close': np.linspace(98, 198, 300),
        'Volume': np.random.randint(1000, 50000, size=300),
        'InstNetBuy': np.random.randn(300) * 1000,
        'ForeignerNetBuy': np.random.randn(300) * 1000
    }, index=dates)

    alpha_df = compute_advanced_alpha_features(df)
    for feat in ALPHA_FEATURES:
        assert feat in alpha_df.columns
        assert not alpha_df[feat].isna().all()

def test_purged_kfold_cv():
    X = pd.DataFrame({'f1': np.arange(100)})
    cv = PurgedKFold(n_splits=5, pct_embargo=0.02)
    splits = list(cv.split(X))

    assert len(splits) == 5
    for train_idx, test_idx in splits:
        assert len(train_idx) > 0
        assert len(test_idx) > 0
        # Check no overlap between train and test
        assert len(set(train_idx).intersection(set(test_idx))) == 0
