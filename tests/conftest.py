"""
Global Pytest fixtures for the Stock Trading System test suite.
"""
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))


@pytest.fixture
def temp_db_path(tmp_path):
    """Provides a temporary SQLite database path for isolated database tests."""
    return str(tmp_path / "test_stock_prices.db")


@pytest.fixture
def temp_model_dir(tmp_path):
    d = tmp_path / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def synthetic_regression_data():
    import numpy as np
    import pandas as pd
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
    import numpy as np
    import pandas as pd
    np.random.seed(42)
    n = 100
    X = pd.DataFrame({
        'ret_1d': np.random.randn(n),
        'vol_20d': np.abs(np.random.randn(n)),
        'rsi_14': np.random.uniform(30, 70, size=n),
    })
    y = pd.Series((np.arange(n) % 2).astype(int))
    return X, y


@pytest.fixture
def synthetic_prices_dict():
    import numpy as np
    import pandas as pd
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


@pytest.fixture
def mock_ohlcv_df():
    """Provides a standard mock OHLCV pandas DataFrame for unit tests."""
    import numpy as np
    import pandas as pd
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
    np.random.seed(42)
    prices = 100.0 + np.cumsum(np.random.randn(100) * 0.5)
    df = pd.DataFrame({
        'Open': prices + np.random.randn(100) * 0.1,
        'High': prices + 1.0,
        'Low': prices - 1.0,
        'Close': prices,
        'Volume': np.random.randint(1000, 10000, size=100)
    }, index=dates)
    return df
