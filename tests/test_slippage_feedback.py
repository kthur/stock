"""
Unit Tests for Slippage Feedback Engine & Ensemble Microstructure Cost Integration
"""

import sqlite3
import datetime
import pytest
import pandas as pd

from trading_system.src.execution.slippage_feedback import (
    SlippageFeedbackEngine,
    SlippageMetrics,
)
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


def test_slippage_metrics_defaults():
    metrics = SlippageMetrics()
    assert metrics.avg_slippage_bps == 5.0
    assert metrics.market_impact_alpha == 0.50
    assert metrics.sample_count == 0
    assert metrics.cost_scaling_factor == 1.0
    assert "KOSPI" in metrics.market_slippage_map
    assert metrics.market_slippage_map["KOSPI"] == 5.0


def test_empty_or_missing_db_graceful_fallback(tmp_path):
    missing_db = str(tmp_path / "non_existent_trade_logs.db")
    engine = SlippageFeedbackEngine(db_path=missing_db, default_slippage_bps=5.0)

    metrics = engine.calculate_realized_slippage()
    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0
    assert metrics.cost_scaling_factor == 1.0
    assert metrics.market_impact_alpha == 0.50


def test_realized_slippage_calculation_single_and_multi_orders(tmp_path):
    db_file = str(tmp_path / "test_trade_logs.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE order_plans (
            order_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            name TEXT,
            market TEXT,
            action TEXT NOT NULL,
            target_weight REAL NOT NULL,
            target_amount REAL NOT NULL,
            target_price REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            target_price REAL NOT NULL,
            executed_price REAL NOT NULL,
            slippage_bps REAL NOT NULL,
            executed_volume INTEGER NOT NULL,
            executed_at TEXT NOT NULL
        )
    """)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Order 1: target=10000, executed=10010 -> slippage = |10010 - 10000| / 10000 * 10000 = 10 bps
    cursor.execute("""
        INSERT INTO order_plans VALUES ('ORD_1', '005930.KS', 'Samsung', 'KOSPI', 'BUY', 0.1, 100000, 10000.0, 'EXECUTED', ?)
    """, (now_str,))
    cursor.execute("""
        INSERT INTO execution_logs (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at)
        VALUES ('ORD_1', '005930.KS', 10000.0, 10010.0, 10.0, 10, ?)
    """, (now_str,))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 1
    assert pytest.approx(metrics.avg_slippage_bps, abs=0.01) == 10.0
    assert pytest.approx(metrics.cost_scaling_factor, abs=0.01) == 2.0  # 10.0 / 5.0
    assert pytest.approx(metrics.market_slippage_map["KOSPI"], abs=0.01) == 10.0


def test_market_grouping_and_alpha_tiering(tmp_path):
    db_file = str(tmp_path / "test_multi_market.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE order_plans (
            order_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, name TEXT, market TEXT, action TEXT,
            target_weight REAL, target_amount REAL, target_price REAL, status TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL, symbol TEXT NOT NULL,
            target_price REAL NOT NULL, executed_price REAL NOT NULL, slippage_bps REAL NOT NULL,
            executed_volume INTEGER NOT NULL, executed_at TEXT NOT NULL
        )
    """)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    records = [
        ('ORD_KOSPI', '005930.KS', 'KOSPI', 50000.0, 50050.0, 100),   # 10 bps, size 5.005M
        ('ORD_KOSDAQ', '035720.KQ', 'KOSDAQ', 10000.0, 10030.0, 100), # 30 bps, size 1.003M
        ('ORD_SP500', 'AAPL', 'SP500', 100.0, 100.02, 100),           # 2 bps, size 10,002
    ]

    for ord_id, sym, mkt, t_price, e_price, vol in records:
        cursor.execute("INSERT INTO order_plans VALUES (?, ?, '', ?, 'BUY', 0.1, 1000, ?, 'EXECUTED', ?)", (ord_id, sym, mkt, t_price, now_str))
        cursor.execute("INSERT INTO execution_logs (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at) VALUES (?, ?, ?, ?, 0.0, ?, ?)",
                       (ord_id, sym, t_price, e_price, vol, now_str))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 3
    assert pytest.approx(metrics.market_slippage_map['KOSPI'], abs=0.01) == 10.0
    assert pytest.approx(metrics.market_slippage_map['KOSDAQ'], abs=0.01) == 30.0
    assert pytest.approx(metrics.market_slippage_map['SP500'], abs=0.01) == 2.0


def test_empirical_impact_alpha_calculation(tmp_path):
    db_file = str(tmp_path / "test_alpha.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE order_plans (
            order_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, name TEXT, market TEXT, action TEXT,
            target_weight REAL, target_amount REAL, target_price REAL, status TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL, symbol TEXT NOT NULL,
            target_price REAL NOT NULL, executed_price REAL NOT NULL, slippage_bps REAL NOT NULL,
            executed_volume INTEGER NOT NULL, executed_at TEXT NOT NULL
        )
    """)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sizes_and_slips = [
        (100, 10.0, 10.04),     # Size 1,004, slip 4 bps
        (100, 10.0, 10.04),     # Size 1,004, slip 4 bps
        (500, 10.0, 10.12),     # Size 5,060, slip 12 bps
        (500, 10.0, 10.12),     # Size 5,060, slip 12 bps
        (10000, 10.0, 10.40),   # Size 104,000, slip 40 bps
        (10000, 10.0, 10.40),   # Size 104,000, slip 40 bps
    ]

    for idx, (vol, t_p, e_p) in enumerate(sizes_and_slips):
        ord_id = f"ORD_A_{idx}"
        cursor.execute("INSERT INTO order_plans VALUES (?, '005930.KS', '', 'KOSPI', 'BUY', 0.1, 1000, ?, 'EXECUTED', ?)", (ord_id, t_p, now_str))
        cursor.execute("INSERT INTO execution_logs (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at) VALUES (?, '005930.KS', ?, ?, 0.0, ?, ?)",
                       (ord_id, t_p, e_p, vol, now_str))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 6
    assert 0.30 <= metrics.market_impact_alpha <= 1.00


def test_ensemble_scorer_cost_update_integration():
    scorer = EnsembleScoringEngine()
    assert scorer.cost_scaling_factor == 1.0
    assert scorer.realized_market_impact_alpha == 0.50

    mock_metrics = SlippageMetrics(
        avg_slippage_bps=15.0,
        market_impact_alpha=0.65,
        market_slippage_map={'KOSPI': 15.0},
        sample_count=20,
        cost_scaling_factor=3.0
    )

    scorer.update_microstructure_costs(mock_metrics)

    assert scorer.cost_scaling_factor == 3.0
    assert scorer.realized_market_impact_alpha == 0.65
    assert scorer.market_slippage_bps_map == {'KOSPI': 15.0}

    df_candidate = pd.DataFrame([{
        'symbol': '005930.KS',
        'market': 'KOSPI',
        'close': 70000.0,
        'volume': 1000000.0,
        'reg_pred': 0.10,
        'volatility_20d': 0.02
    }])

    scored_df = scorer.combine_predictions(reg_df=df_candidate)
    assert 'ensemble_expected_return' in scored_df.columns
    expected_ret_with_high_cost = scored_df['ensemble_expected_return'].iloc[0]

    scorer.update_microstructure_costs(SlippageMetrics(avg_slippage_bps=5.0, cost_scaling_factor=1.0, market_impact_alpha=0.50))
    scored_df_normal = scorer.combine_predictions(reg_df=df_candidate)
    expected_ret_normal = scored_df_normal['ensemble_expected_return'].iloc[0]

    assert expected_ret_with_high_cost <= expected_ret_normal


def test_forwarder_imports():
    from src.execution.slippage_feedback import SlippageFeedbackEngine as FwdEngine, SlippageMetrics as FwdMetrics
    from trading_system.src.execution.slippage_feedback import SlippageFeedbackEngine as OrigEngine, SlippageMetrics as OrigMetrics

    assert FwdEngine.__name__ == OrigEngine.__name__
    assert FwdMetrics.__name__ == OrigMetrics.__name__

    fwd_inst = FwdEngine()
    orig_inst = OrigEngine()
    assert type(fwd_inst.calculate_realized_slippage()) is FwdMetrics
    assert type(orig_inst.calculate_realized_slippage()) is OrigMetrics


def test_v6_30_buy_hedge_slippage_sign_and_db_closure(tmp_path):
    db_file = str(tmp_path / "test_buy_hedge_slippage.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE order_plans (
            order_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, name TEXT, market TEXT, action TEXT,
            target_weight REAL, target_amount REAL, target_price REAL, status TEXT, created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL, symbol TEXT NOT NULL,
            target_price REAL NOT NULL, executed_price REAL NOT NULL, slippage_bps REAL NOT NULL,
            executed_volume INTEGER NOT NULL, executed_at TEXT NOT NULL
        )
    """)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # BUY_HEDGE: target=10000, executed=10050 -> adverse slippage = +50 bps
    cursor.execute("INSERT INTO order_plans VALUES ('ORD_H1', '252670.KS', 'KODEX 200선물인버스2X', 'KOSPI', 'BUY_HEDGE', 0.1, 100000, 10000.0, 'EXECUTED', ?)", (now_str,))
    cursor.execute("INSERT INTO execution_logs (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at) VALUES ('ORD_H1', '252670.KS', 10000.0, 10050.0, 0.0, 100, ?)", (now_str,))

    # SELL: target=10000, executed=9950 -> adverse slippage = +50 bps
    cursor.execute("INSERT INTO order_plans VALUES ('ORD_S1', '005930.KS', 'Samsung', 'KOSPI', 'SELL', 0.1, 100000, 10000.0, 'EXECUTED', ?)", (now_str,))
    cursor.execute("INSERT INTO execution_logs (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at) VALUES ('ORD_S1', '005930.KS', 10000.0, 9950.0, 0.0, 100, ?)", (now_str,))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 2
    assert pytest.approx(metrics.avg_slippage_bps, abs=0.1) == 50.0
    assert metrics.cost_scaling_factor >= 2.5


def test_v6_30_trade_logs_buy_hedge_sign(tmp_path):
    db_file = str(tmp_path / "test_trade_logs_hedge.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE trade_logs (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            market TEXT,
            side TEXT,
            expected_price REAL,
            fill_price REAL
        )
    """)
    cursor.execute("INSERT INTO trade_logs (market, side, expected_price, fill_price) VALUES ('KOSPI', 'BUY_HEDGE', 10000.0, 10030.0)")
    cursor.execute("INSERT INTO trade_logs (market, side, expected_price, fill_price) VALUES ('SP500', 'BUY', 100.0, 100.20)")
    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 2
    assert metrics.market_slippage_map['KOSPI'] == pytest.approx(30.0, abs=0.1)
    assert metrics.market_slippage_map['SP500'] == pytest.approx(20.0, abs=0.1)

