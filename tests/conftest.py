import sys
import os
import pytest
import numpy as np
import pandas as pd

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ts_dir = os.path.join(root_dir, "trading_system")

if ts_dir not in sys.path:
    sys.path.insert(0, ts_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


@pytest.fixture
def temp_model_dir(tmp_path):
    d = tmp_path / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def synthetic_regression_data():
    np.random.seed(42)
    n = 100
    X = pd.DataFrame({
        'feature_1': np.random.randn(n),
        'feature_2': np.random.randn(n),
        'feature_3': np.random.randn(n),
    })
    y = pd.Series(2.0 * X['feature_1'] - 1.0 * X['feature_2'] + np.random.randn(n) * 0.1)
    return X, y


@pytest.fixture
def synthetic_surge_data():
    np.random.seed(42)
    n = 100
    X = pd.DataFrame({
        'ret_1d': np.random.randn(n),
        'vol_20d': np.abs(np.random.randn(n)),
        'rsi_14': np.random.uniform(30, 70, size=n),
    })
    probs = 1 / (1 + np.exp(-X['ret_1d']))
    y = pd.Series((probs > 0.5).astype(int))
    return X, y


@pytest.fixture
def synthetic_prices_dict():
    np.random.seed(42)
    n = 250
    dict_prices = {}
    for sym in ["AAPL", "MSFT", "GOOGL", "005930", "000660"]:
        dates = pd.date_range("2025-01-01", periods=n, freq="D")
        returns = np.random.normal(0.0005, 0.015, size=n)
        price_paths = 100.0 * np.exp(np.cumsum(returns))
        high = price_paths * (1 + np.abs(np.random.normal(0, 0.005, size=n)))
        low = price_paths * (1 - np.abs(np.random.normal(0, 0.005, size=n)))
        volume = np.random.randint(100000, 1000000, size=n)

        df = pd.DataFrame({
            "Open": price_paths,
            "High": high,
            "Low": low,
            "Close": price_paths,
            "Volume": volume
        }, index=dates)
        dict_prices[sym] = df
    return dict_prices

