import os
import sqlite3
import pytest
import numpy as np
import pandas as pd
from trading_system.src.data_layer.feature_store import FeatureStore
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def test_feature_store_save_load_and_parallel_inference(tmp_path):
    """Verify FeatureStore saves compressed Parquet, loads columnar features, and runs parallel inference."""
    store = FeatureStore(store_dir=tmp_path)
    
    date_str = "2026-08-08"
    market = "SP500"
    
    mock_features = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'reg_score': [0.80, 0.70, 0.60],
        'surge_score': [0.10, 0.20, 0.30],
        'volume': [1000000, 2000000, 1500000]
    })

    # 1. Save Strategy Features
    saved_path = store.save_strategy_features(date_str, market, mock_features)
    assert saved_path.exists()
    assert store.has_features(date_str, market)

    # 2. Load Strategy Features
    loaded_df = store.load_strategy_features(date_str, market)
    assert len(loaded_df) == 3
    assert 'reg_score' in loaded_df.columns
    assert loaded_df['symbol'].tolist() == ['AAPL', 'MSFT', 'GOOGL']

    # 3. Parallel Strategy Inference
    def mock_strat_a(multiplier=1.0):
        return pd.DataFrame({'symbol': ['AAPL'], 'score': [0.8 * multiplier]})

    def mock_strat_b(multiplier=1.0):
        return pd.DataFrame({'symbol': ['MSFT'], 'score': [0.7 * multiplier]})

    task_map = {
        'strat_a': (mock_strat_a, {'multiplier': 1.0}),
        'strat_b': (mock_strat_b, {'multiplier': 1.2})
    }

    parallel_res = store.run_parallel_strategy_inference(task_map, max_workers=2)
    assert 'strat_a' in parallel_res
    assert 'strat_b' in parallel_res
    assert parallel_res['strat_a']['score'].iloc[0] == 0.8
    assert pytest.approx(parallel_res['strat_b']['score'].iloc[0], abs=1e-3) == 0.84


def test_oms_slippage_calibration_and_atr_trailing_stop(tmp_path):
    """Verify OMS Slippage Feedback calibration and ATR Trailing Stop computation."""
    allocator = PortfolioAllocator()
    
    # 1. Test ATR Trailing Stop
    atr_res = allocator.calculate_atr_trailing_stop(
        symbol='AAPL',
        current_price=100.0,
        atr_20d=2.0,
        is_long=True,
        multiplier=2.5
    )
    
    assert atr_res['stop_loss'] == 95.0       # 100 - (2.5 * 2) = 95
    assert atr_res['take_profit'] == 107.5    # 100 + (1.5 * 5) = 107.5
    assert pytest.approx(atr_res['risk_pct'], abs=1e-3) == 0.05

    # 2. Test OMS Slippage Calibration from DB
    db_path = tmp_path / "trade_logs.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE trade_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            order_price REAL,
            executed_price REAL
        );
    """)
    # Insert 10 trades with 0.15% (15 bps) average slippage
    for _ in range(10):
        cursor.execute("INSERT INTO trade_logs (symbol, order_price, executed_price) VALUES ('AAPL', 100.0, 100.15);")
    conn.commit()
    conn.close()

    calibrated_factor = allocator.calibrate_slippage_from_trade_logs(db_path=str(db_path))
    # 15 bps / 10 bps benchmark = 1.5x
    assert pytest.approx(calibrated_factor, abs=1e-2) == 1.50
