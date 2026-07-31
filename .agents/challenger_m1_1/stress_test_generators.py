"""
Synthetic Price/Volume Series Generators and Stress Testing Suite for IntradayStopLossEngine
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add stock root to path
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossResult

def generate_volatile_spike_series(length=50, spike_index=20, spike_mult=5.0, crash_index=25, drop_pct=-0.10):
    """
    Generates a price series with a massive spike followed by a collapse.
    """
    prices = np.ones(length) * 100.0
    highs = np.ones(length) * 100.5
    lows = np.ones(length) * 99.5
    volumes = np.ones(length) * 1000.0

    # Apply spike
    prices[spike_index:crash_index] = 100.0 * spike_mult
    highs[spike_index:crash_index] = 100.0 * spike_mult * 1.05
    lows[spike_index:crash_index] = 100.0 * spike_mult * 0.95

    # Apply collapse after crash_index
    prices[crash_index:] = 100.0 * (1.0 + drop_pct)
    highs[crash_index:] = 100.0 * (1.0 + drop_pct) * 1.01
    lows[crash_index:] = 100.0 * (1.0 + drop_pct) * 0.99

    dates = pd.date_range("2026-07-31 09:00", periods=length, freq="1min")
    return pd.DataFrame({'open': prices, 'high': highs, 'low': lows, 'close': prices, 'volume': volumes}, index=dates)

def generate_illiquid_gap_down_series(length=30, gap_index=15, gap_drop=-0.10, volume=10.0):
    """
    Generates a series with steady price then a sudden -10% gap-down in 1 tick with tiny volume.
    """
    prices = np.ones(length) * 100.0
    volumes = np.ones(length) * volume

    prices[gap_index:] = 100.0 * (1.0 + gap_drop)

    dates = pd.date_range("2026-07-31 09:00", periods=length, freq="1min")
    return pd.DataFrame({
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': volumes
    }, index=dates)

def generate_flat_low_volume_series(length=30, spike_index=20, panic_vol=1000.0, drop_pct=-0.05):
    """
    Generates a series with 0 volume for 20 periods, then a panic volume surge on tick 21 with price drop.
    """
    prices = np.ones(length) * 100.0
    volumes = np.zeros(length)  # 0 volume initially

    prices[spike_index:] = 100.0 * (1.0 + drop_pct)
    volumes[spike_index:] = panic_vol

    dates = pd.date_range("2026-07-31 09:00", periods=length, freq="1min")
    return pd.DataFrame({
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': volumes
    }, index=dates)

def generate_extreme_volatility_series(length=100, mean_price=100.0, volatility=0.05, seed=42):
    """
    Generates high volatility random walk / Brownian motion series with high tick noise.
    """
    np.random.seed(seed)
    returns = np.random.normal(0, volatility, length)
    price_path = mean_price * np.exp(np.cumsum(returns))
    volumes = np.random.poisson(1000, length).astype(float)

    highs = price_path * (1.0 + np.abs(np.random.normal(0, volatility/2, length)))
    lows = price_path * (1.0 - np.abs(np.random.normal(0, volatility/2, length)))

    dates = pd.date_range("2026-07-31 09:00", periods=length, freq="1min")
    return pd.DataFrame({
        'open': price_path,
        'high': highs,
        'low': lows,
        'close': price_path,
        'volume': volumes
    }, index=dates)

def generate_nan_and_corrupted_data():
    """
    Generates test cases with NaN, Inf, negative prices, and invalid inputs.
    """
    return [
        {"name": "NaN current_price", "data": {'current_price': np.nan, 'peak_price': 100.0, 'volume': 1000}},
        {"name": "Inf current_price", "data": {'current_price': np.inf, 'peak_price': 100.0, 'volume': 1000}},
        {"name": "Negative price", "data": {'current_price': -50.0, 'peak_price': 100.0, 'volume': 1000}},
        {"name": "Zero price", "data": {'current_price': 0.0, 'peak_price': 100.0, 'volume': 1000}},
        {"name": "NaN ATR", "data": {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000, 'atr': np.nan}},
        {"name": "Negative ATR", "data": {'current_price': 95.0, 'peak_price': 100.0, 'volume': 1000, 'atr': -2.0}},
        {"name": "NaN in DataFrame close", "data": pd.DataFrame({'close': [100.0, np.nan], 'volume': [1000, 1000]})},
        {"name": "Empty DataFrame", "data": pd.DataFrame()},
    ]

if __name__ == '__main__':
    print("Stress test generators module created successfully.")
