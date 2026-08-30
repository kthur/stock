"""Unit and Integration Tests for High-Throughput Real-Time Level 2/3 Tick & LOB Store."""

import os
import json
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import pytest
import numpy as np

from src.data_layer.timescale_db import TimescaleDBConnector, RealTimeTickLOBStore
from src.core.lob_obi import LimitOrderBookCalculator
from src.config import TradingConfig


@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite DB path for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_tick_store_")
    db_file = Path(temp_dir) / "test_ticks.db"
    yield str(db_file)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_tick_trades_batch_insert_and_retrieval(temp_db_path):
    """Test batch inserting tick trades and retrieving them within lookback window."""
    store = RealTimeTickLOBStore(fallback_sqlite_path=temp_db_path)

    now = datetime.now()
    records = []
    for i in range(20):
        t_iso = (now - timedelta(seconds=20 - i)).isoformat()
        records.append({
            "time": t_iso,
            "symbol": "005930",
            "market": "KOSPI",
            "price": 70000.0 + i * 100.0,
            "volume": 100.0 + i * 10.0,
            "side": "BUY" if i % 2 == 0 else "SELL",
            "bid_price": 69900.0 + i * 100.0,
            "ask_price": 70100.0 + i * 100.0,
            "trade_id": f"tr_{i}",
        })

    success = store.batch_insert_ticks(records)
    assert success is True

    ticks = store.get_recent_ticks("005930", lookback_seconds=60, limit=50)
    assert len(ticks) == 20
    assert ticks[0]["symbol"] == "005930"
    assert ticks[0]["market"] == "KOSPI"
    assert ticks[0]["side"] in ["BUY", "SELL"]
    assert ticks[-1]["price"] == 70000.0 + 19 * 100.0


def test_lob_depth_snapshots_10_levels(temp_db_path):
    """Test 10-level LOB snapshot insertion, storage of arrays, and multi-depth OBI."""
    store = RealTimeTickLOBStore(fallback_sqlite_path=temp_db_path)

    now = datetime.now()
    snapshots = []
    for i in range(5):
        t_iso = (now - timedelta(seconds=5 - i)).isoformat()
        bids = [{"price": 100.0 - j * 0.1, "volume": 500.0 + j * 50.0} for j in range(10)]
        asks = [{"price": 100.1 + j * 0.1, "volume": 300.0 + j * 30.0} for j in range(10)]
        snapshots.append({
            "time": t_iso,
            "symbol": "AAPL",
            "market": "NASDAQ",
            "bids": bids,
            "asks": asks,
        })

    success = store.batch_insert_lob_snapshots(snapshots)
    assert success is True

    loaded_snaps = store.get_recent_lob_snapshots("AAPL", lookback_seconds=60, limit=10)
    assert len(loaded_snaps) == 5
    last = loaded_snaps[-1]
    assert len(last["bid_prices"]) == 10
    assert len(last["ask_prices"]) == 10
    assert last["micro_price"] > 0
    assert -1.0 <= last["obi_1"] <= 1.0
    assert -1.0 <= last["obi_5"] <= 1.0
    assert -1.0 <= last["obi_10"] <= 1.0


def test_rolling_vpin_calculation(temp_db_path):
    """Test Volume-Synchronized Probability of Toxicity (VPIN) from trade stream."""
    store = RealTimeTickLOBStore(fallback_sqlite_path=temp_db_path)

    now = datetime.now()
    records = []
    # Generate 100 trades with heavy BUY imbalance
    for i in range(100):
        t_iso = (now - timedelta(seconds=100 - i)).isoformat()
        records.append({
            "time": t_iso,
            "symbol": "NVDA",
            "market": "NASDAQ",
            "price": 500.0 + (i * 0.5),
            "volume": 200.0,
            "side": "BUY" if i < 80 else "SELL",
            "trade_id": f"nvda_tr_{i}",
        })

    store.batch_insert_ticks(records)

    vpin = store.compute_rolling_vpin("NVDA", bucket_size_vol=1000.0, num_buckets=10, lookback_seconds=300)
    assert 0.0 <= vpin <= 1.0
    # High toxicity / buy pressure should result in higher VPIN
    assert vpin > 0.40


def test_compute_microstructure_metrics_integration(temp_db_path):
    """Test aggregated microstructure indicators."""
    store = RealTimeTickLOBStore(fallback_sqlite_path=temp_db_path)

    now = datetime.now()
    # 1. Add ticks
    ticks = []
    for i in range(30):
        ticks.append({
            "time": (now - timedelta(seconds=30 - i)).isoformat(),
            "symbol": "TSLA",
            "market": "NASDAQ",
            "price": 200.0 + (i % 5) * 0.2,
            "volume": 50.0,
            "side": "BUY" if i % 2 == 0 else "SELL",
            "trade_id": f"tsla_{i}",
        })
    store.batch_insert_ticks(ticks)

    # 2. Add LOB snapshots
    bids = [{"price": 199.9 - j * 0.1, "volume": 100.0} for j in range(10)]
    asks = [{"price": 200.1 + j * 0.1, "volume": 120.0} for j in range(10)]
    store.batch_insert_lob_snapshots([{
        "time": now.isoformat(),
        "symbol": "TSLA",
        "market": "NASDAQ",
        "bids": bids,
        "asks": asks,
    }])

    metrics = store.compute_microstructure_metrics("TSLA", lookback_seconds=60)
    assert metrics["symbol"] == "TSLA"
    assert metrics["tick_count"] == 30
    assert metrics["lob_snapshot_count"] == 1
    assert metrics["vwap"] > 0
    assert 0.0 <= metrics["buy_volume_ratio"] <= 1.0
    assert 0.0 <= metrics["vpin"] <= 1.0
    assert metrics["micro_price"] > 0


def test_limit_order_book_calculator_multi_depth():
    """Test LimitOrderBookCalculator for 10-level OBI and micro-price."""
    calc = LimitOrderBookCalculator(depth_levels=10)
    bids = [{"price": 1000.0 - i * 10, "volume": 100.0 + i * 10} for i in range(10)]
    asks = [{"price": 1005.0 + i * 10, "volume": 80.0 + i * 5} for i in range(10)]

    res = calc.evaluate_lob_snapshot({"bids": bids, "asks": asks})
    assert "obi" in res
    assert "obi_1" in res
    assert "obi_5" in res
    assert "obi_10" in res
    assert "micro_price" in res
    assert "spread" in res
    assert res["spread"] == 5.0
    assert res["micro_price"] >= 1000.0


def test_timescaledb_config_integration():
    """Verify TradingConfig has TimescaleDB and LOB tick configuration options."""
    cfg = TradingConfig()
    assert hasattr(cfg, "timescaledb_url")
    assert hasattr(cfg, "timescaledb_enabled")
    assert hasattr(cfg, "lob_tick_storage_enabled")
    assert hasattr(cfg, "lob_depth_levels")
    assert hasattr(cfg, "vpin_bucket_size")
    assert cfg.lob_depth_levels == 10
    assert cfg.vpin_bucket_size == 10000.0