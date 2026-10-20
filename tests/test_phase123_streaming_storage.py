"""
tests/test_phase123_streaming_storage.py
========================================
Verification Test Suite for:
Multi-Tier Streaming Ingest & Adaptive Storage Manager (Feature F586).
Phase 123 (Release R139 / v130 Production Master).
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.data_layer.streaming_ingest_engine import (
    VERSION,
    RELEASE,
    FEATURE,
    StreamEventType,
    StreamTickEvent,
    StreamingIngestEngine,
    IngestTelemetry,
)
from src.data_layer.tiered_storage_manager import (
    TieredStorageManager,
    StorageTier,
    PriceRecord,
)


class TestPhase123StreamingStorage:
    """Comprehensive test suite for Feature F586."""

    def test_tc01_version_and_metadata(self):
        """Verifies metadata constants."""
        assert VERSION == 123
        assert RELEASE == "R139"
        assert FEATURE == "F586"

    def test_tc02_dual_tree_sha256_parity_ingest(self):
        """Verifies 100% bit-for-bit SHA-256 parity for streaming_ingest_engine.py."""
        f1 = PROJECT_ROOT / "src" / "data_layer" / "streaming_ingest_engine.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "data_layer" / "streaming_ingest_engine.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc03_dual_tree_sha256_parity_storage(self):
        """Verifies 100% bit-for-bit SHA-256 parity for tiered_storage_manager.py."""
        f1 = PROJECT_ROOT / "src" / "data_layer" / "tiered_storage_manager.py"
        f2 = TRADING_SYSTEM_DIR / "src" / "data_layer" / "tiered_storage_manager.py"
        assert f1.exists(), f"File {f1} does not exist"
        assert f2.exists(), f"File {f2} does not exist"
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 mismatch: {h1} != {h2}"

    def test_tc04_package_exports(self):
        """Verifies exports from src.data_layer package."""
        import src.data_layer as dl_pkg
        assert hasattr(dl_pkg, "StreamingIngestEngine")
        assert hasattr(dl_pkg, "TieredStorageManager")
        assert hasattr(dl_pkg, "StreamTickEvent")

    def test_tc05_tick_ingestion_and_telemetry(self):
        """Verifies normal tick ingestion and telemetry metrics."""
        engine = StreamingIngestEngine(buffer_capacity=100)
        t_now = time.perf_counter_ns()
        tick = StreamTickEvent(
            seq_num=1,
            symbol="AAPL",
            event_type=StreamEventType.TRADE_TICK,
            price=180.5,
            volume=100.0,
            timestamp_ns=t_now,
            source_venue="NASDAQ",
        )
        assert engine.ingest_tick(tick) is True
        assert engine.telemetry.total_received == 1
        assert engine.telemetry.total_processed == 1
        assert engine.telemetry.duplicates_dropped == 0

    def test_tc06_duplicate_sequence_rejection(self):
        """Verifies duplicate packets from same venue are dropped."""
        engine = StreamingIngestEngine(buffer_capacity=100)
        tick = StreamTickEvent(
            seq_num=42,
            symbol="NVDA",
            event_type=StreamEventType.TRADE_TICK,
            price=120.0,
            volume=50.0,
            timestamp_ns=time.perf_counter_ns(),
            source_venue="NASDAQ",
        )
        assert engine.ingest_tick(tick) is True
        assert engine.ingest_tick(tick) is False
        assert engine.telemetry.duplicates_dropped == 1
        assert engine.telemetry.total_processed == 1

    def test_tc07_gap_detection(self):
        """Verifies sequence jump triggers gap detection."""
        engine = StreamingIngestEngine(buffer_capacity=100, enable_gap_detection=True)
        t1 = StreamTickEvent(1, "005930.KS", StreamEventType.TRADE_TICK, 70000, 10, time.perf_counter_ns(), "KRX")
        t2 = StreamTickEvent(5, "005930.KS", StreamEventType.TRADE_TICK, 70100, 20, time.perf_counter_ns(), "KRX")
        engine.ingest_tick(t1)
        engine.ingest_tick(t2)
        assert engine.telemetry.gaps_detected == 3  # Missing seq 2, 3, 4

    def test_tc08_batch_ingest_and_retrieval(self):
        """Verifies batch tick ingestion and ring buffer retrieval."""
        engine = StreamingIngestEngine(buffer_capacity=10)
        ticks = [
            StreamTickEvent(i, "SPY", StreamEventType.BBO_QUOTE, 500.0 + i, 10, time.perf_counter_ns(), "CBOE")
            for i in range(15)
        ]
        processed = engine.ingest_batch(ticks)
        assert processed == 15
        latest = engine.get_latest_ticks(5)
        assert len(latest) == 5
        assert latest[-1].seq_num == 14

    def test_tc09_tiered_storage_hot_to_warm_demotion(self):
        """Verifies hot tier overflow properly demotes to warm tier."""
        storage = TieredStorageManager(hot_capacity_per_symbol=5, warm_capacity_per_symbol=20)
        for i in range(10):
            storage.store_price("AAPL", timestamp=float(i * 60), price=150.0 + i, volume=1000)

        stats = storage.get_tier_stats()
        assert stats["hot_items"] == 5
        assert stats["warm_items"] == 5
        assert stats["cold_items"] == 0

    def test_tc10_tiered_storage_warm_to_cold_demotion(self):
        """Verifies warm tier overflow properly demotes to cold SQLite tier."""
        storage = TieredStorageManager(hot_capacity_per_symbol=4, warm_capacity_per_symbol=6)
        for i in range(20):
            storage.store_price("TSLA", timestamp=float(i * 100), price=200.0 + i, volume=500)

        stats = storage.get_tier_stats()
        assert stats["hot_items"] == 4
        assert stats["cold_items"] > 0

    def test_tc11_federated_query_across_tiers(self):
        """Verifies query_price_history seamlessly merges and sorts all 3 tiers."""
        storage = TieredStorageManager(hot_capacity_per_symbol=3, warm_capacity_per_symbol=5)
        for i in range(15):
            storage.store_price("MSFT", timestamp=float(i * 10), price=400.0 + i, volume=100)

        df = storage.query_price_history("MSFT")
        assert not df.empty
        assert len(df) == 15
        # Must be monotonically sorted ascending by timestamp
        assert (df["timestamp"].diff().dropna() > 0).all()

    def test_tc12_flush_and_tier_stats(self):
        """Verifies manual flush moves warm records to cold tier immediately."""
        storage = TieredStorageManager(hot_capacity_per_symbol=10, warm_capacity_per_symbol=50)
        # Force a record to warm
        for i in range(15):
            storage.store_price("GOOG", timestamp=float(i * 50), price=170.0 + i, volume=200)

        assert storage.get_tier_stats()["warm_items"] == 5
        flushed = storage.flush_to_cold("GOOG")
        assert flushed == 5
        assert storage.get_tier_stats()["warm_items"] == 0
        assert storage.get_tier_stats()["cold_items"] >= 5

    def test_tc13_storage_lifecycle_and_empty_query(self):
        """Verifies empty query returns correct schema and close does not fail."""
        storage = TieredStorageManager()
        empty_df = storage.query_price_history("NONEXISTENT")
        assert empty_df.empty
        assert "symbol" in empty_df.columns
        assert "price" in empty_df.columns
        storage.close()
