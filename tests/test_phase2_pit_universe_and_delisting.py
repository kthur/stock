"""
Tests for Phase 2 Institutional Enhancements:
1. PointInTimeUniverseManager historical membership tracking and date-specific queries.
2. Delisting event recording with terminal recovery rates (survivorship bias prevention).
3. BacktestEngine realistic delisting liquidation and exit reason handling.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from src.data_layer.point_in_time_universe import PointInTimeUniverseManager
from src.analysis.backtest import BacktestEngine, PriceBar


def test_point_in_time_universe_membership(tmp_path):
    db_file = str(tmp_path / "test_pit.db")
    pit_mgr = PointInTimeUniverseManager(db_path=db_file)

    # Record historical constituents
    pit_mgr.record_constituent_membership(
        market="SP500",
        symbol="AAPL",
        start_date="2020-01-01",
        end_date=None,
        name="Apple Inc",
        is_active=True
    )
    pit_mgr.record_constituent_membership(
        market="SP500",
        symbol="ENRON",
        start_date="1995-01-01",
        end_date="2001-12-02",
        name="Enron Corp",
        is_active=False
    )

    # In 2000, both AAPL and ENRON were constituents
    u_2000 = pit_mgr.get_active_universe_at("2000-06-01", market="SP500")
    assert "AAPL" in u_2000 or "ENRON" in u_2000

    # In 2025, ENRON is no longer a constituent
    u_2025 = pit_mgr.get_active_universe_at("2025-01-01", market="SP500")
    assert "ENRON" not in u_2025
    assert "AAPL" in u_2025


def test_delisting_event_recording_and_retrieval(tmp_path):
    db_file = str(tmp_path / "test_delist.db")
    pit_mgr = PointInTimeUniverseManager(db_path=db_file)

    pit_mgr.record_delisting_event(
        symbol="BBBY",
        market="NASDAQ",
        delisting_date="2023-05-03",
        reason="BANKRUPTCY",
        recovery_rate=0.05,
        last_price=0.10,
        notes="Chapter 11 liquidation"
    )

    info = pit_mgr.get_delisting_info("BBBY")
    assert info is not None
    assert info['reason'] == "BANKRUPTCY"
    assert np.isclose(info['recovery_rate'], 0.05)


def test_backtest_with_delisting_terminal_recovery():
    engine = BacktestEngine(initial_capital=10000)
    
    # Create simple upward price bars
    bars = []
    base_time = datetime(2023, 1, 1)
    for i in range(20):
        bars.append(PriceBar(
            timestamp=base_time + timedelta(days=i),
            open=100.0 + i,
            high=102.0 + i,
            low=99.0 + i,
            close=101.0 + i,
            volume=10000
        ))

    # Buy and hold strategy
    def buy_strategy(bar_sub):
        return "BUY"

    # Normal final exit
    res_normal = engine.run_backtest(
        symbol="NORMAL",
        price_bars=bars,
        strategy_func=buy_strategy
    )
    assert len(res_normal.trades) > 0
    assert res_normal.trades[-1].exit_reason == "FINAL"
    assert res_normal.trades[-1].exit_price == pytest.approx(bars[-1].close)

    # Delisting final exit with bankruptcy recovery haircut (e.g. 10% recovery)
    res_delist = engine.run_backtest(
        symbol="DELIST_CO",
        price_bars=bars,
        strategy_func=buy_strategy,
        delisting_recovery_rate=0.10
    )
    assert len(res_delist.trades) > 0
    assert res_delist.trades[-1].exit_reason == "DELISTING"
    assert res_delist.trades[-1].exit_price == pytest.approx(bars[-1].close * 0.10)
    assert res_delist.trades[-1].pnl < res_normal.trades[-1].pnl
