"""
Empirical Slippage Feedback Engine Stress & Edge Case Test Suite
Target: SlippageFeedbackEngine, SlippageMetrics, EnsembleScoringEngine integration
"""

import os
import sqlite3
import datetime
import math
import pytest
import numpy as np
import pandas as pd

from trading_system.src.execution.slippage_feedback import (
    SlippageFeedbackEngine,
    SlippageMetrics,
)
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


# ------------------------------------------------------------------
# Test Category 1: Non-existent or corrupt SQLite database paths
# ------------------------------------------------------------------

def test_stress_non_existent_db_path(tmp_path):
    """Test when db path does not exist."""
    non_existent = str(tmp_path / "does_not_exist_12345.db")
    engine = SlippageFeedbackEngine(db_path=non_existent, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0
    assert metrics.cost_scaling_factor == 1.0
    assert metrics.market_impact_alpha == 0.50
    assert isinstance(metrics.market_slippage_map, dict)


def test_stress_corrupt_text_file_db(tmp_path):
    """Test when db path points to a corrupt text file instead of sqlite database."""
    corrupt_db = str(tmp_path / "corrupt_text.db")
    with open(corrupt_db, "w", encoding="utf-8") as f:
        f.write("THIS IS NOT A VALID SQLITE DATABASE FILE. CORRUPT CONTENT 12345\n" * 10)

    engine = SlippageFeedbackEngine(db_path=corrupt_db, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0
    assert metrics.cost_scaling_factor == 1.0
    assert metrics.market_impact_alpha == 0.50


def test_stress_corrupt_truncated_binary_db(tmp_path):
    """Test when db path points to a truncated/corrupt binary file."""
    corrupt_bin = str(tmp_path / "corrupt_bin.db")
    with open(corrupt_bin, "wb") as f:
        f.write(b"SQLite format 3\x00" + b"\xFF" * 50)  # Header truncated/corrupted bytes

    engine = SlippageFeedbackEngine(db_path=corrupt_bin, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0
    assert metrics.cost_scaling_factor == 1.0


def test_stress_directory_path_as_db(tmp_path):
    """Test when a directory path is passed as db_path."""
    dir_path = str(tmp_path / "a_directory_db")
    os.makedirs(dir_path, exist_ok=True)

    engine = SlippageFeedbackEngine(db_path=dir_path, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


# ------------------------------------------------------------------
# Test Category 2: Empty execution_logs or order_plans tables
# ------------------------------------------------------------------

def test_stress_empty_sqlite_db_no_tables(tmp_path):
    """Test sqlite database with zero tables."""
    empty_db = str(tmp_path / "empty_schema.db")
    conn = sqlite3.connect(empty_db)
    conn.close()

    engine = SlippageFeedbackEngine(db_path=empty_db)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


def test_stress_missing_execution_logs_table(tmp_path):
    """Test sqlite database containing order_plans table but missing execution_logs table."""
    db_file = str(tmp_path / "missing_exec_logs.db")
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE order_plans (
            order_id TEXT PRIMARY KEY, symbol TEXT, market TEXT, target_price REAL, target_amount REAL
        )
    """)
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


def test_stress_missing_order_plans_table(tmp_path):
    """Test sqlite database containing execution_logs table but missing order_plans table."""
    db_file = str(tmp_path / "missing_order_plans.db")
    conn = sqlite3.connect(db_file)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
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
    conn.execute("""
        INSERT INTO execution_logs (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at)
        VALUES ('ORD_1', '005930.KS', 10000.0, 10010.0, 10.0, 10, ?)
    """, (now_str,))
    conn.commit()
    conn.close()

    # LEFT JOIN order_plans on missing table order_plans will cause sqlite3.OperationalError: no such table: order_plans
    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


def test_stress_both_tables_exist_execution_logs_empty(tmp_path):
    """Test both tables exist but execution_logs has 0 rows."""
    db_file = str(tmp_path / "empty_exec_logs.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE order_plans (order_id TEXT PRIMARY KEY, symbol TEXT, market TEXT, target_amount REAL)")
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, symbol TEXT,
            target_price REAL, executed_price REAL, slippage_bps REAL, executed_volume INTEGER, executed_at TEXT
        )
    """)
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


def test_stress_records_outside_window_cutoff(tmp_path):
    """Test execution records older than window_days cutoff (e.g. 45 days ago)."""
    db_file = str(tmp_path / "old_records.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE order_plans (order_id TEXT PRIMARY KEY, market TEXT, target_amount REAL)")
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, symbol TEXT,
            target_price REAL, executed_price REAL, slippage_bps REAL, executed_volume INTEGER, executed_at TEXT
        )
    """)
    old_date_str = (datetime.datetime.now() - datetime.timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO execution_logs (order_id, symbol, target_price, executed_price, slippage_bps, executed_volume, executed_at)
        VALUES ('ORD_OLD', '005930.KS', 10000.0, 10050.0, 50.0, 10, ?)
    """, (old_date_str,))
    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, window_days=30)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


# ------------------------------------------------------------------
# Test Category 3: Target price = 0 or executed price = 0
# ------------------------------------------------------------------

def test_stress_zero_or_negative_target_price(tmp_path):
    """Test zero, negative, or None target_price (division by zero protection)."""
    db_file = str(tmp_path / "zero_target.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE order_plans (order_id TEXT PRIMARY KEY, market TEXT, target_amount REAL)")
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, symbol TEXT,
            target_price REAL, executed_price REAL, slippage_bps REAL, executed_volume INTEGER, executed_at TEXT
        )
    """)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Row 1: target_price = 0.0 (Invalid)
    conn.execute("INSERT INTO execution_logs VALUES (1, 'ORD_0', '005930.KS', 0.0, 10000.0, 0.0, 10, ?)", (now_str,))
    # Row 2: target_price = -50.0 (Invalid)
    conn.execute("INSERT INTO execution_logs VALUES (2, 'ORD_NEG', '005930.KS', -50.0, 10000.0, 0.0, 10, ?)", (now_str,))
    # Row 3: target_price = NULL (Invalid)
    conn.execute("INSERT INTO execution_logs VALUES (3, 'ORD_NULL', '005930.KS', NULL, 10000.0, 0.0, 10, ?)", (now_str,))
    # Row 4: Valid row target=10000, executed=10010 (10 bps)
    conn.execute("INSERT INTO execution_logs VALUES (4, 'ORD_VALID', '005930.KS', 10000.0, 10010.0, 10.0, 10, ?)", (now_str,))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    # Query returns 4 rows. Invalid target_price rows are skipped during slippage calculation.
    assert metrics.sample_count == 4
    assert pytest.approx(metrics.avg_slippage_bps, abs=0.01) == 10.0


def test_stress_zero_executed_price(tmp_path):
    """Test executed_price = 0.0 (failed or missing execution price)."""
    db_file = str(tmp_path / "zero_executed.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE order_plans (order_id TEXT PRIMARY KEY, market TEXT, target_amount REAL)")
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, symbol TEXT,
            target_price REAL, executed_price REAL, slippage_bps REAL, executed_volume INTEGER, executed_at TEXT
        )
    """)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Target = 100.0, Executed = 0.0 -> realized_slip = |0 - 100| / 100 * 10000 = 10000 bps
    conn.execute("INSERT INTO execution_logs VALUES (1, 'ORD_ZERO_EXEC', 'AAPL', 100.0, 0.0, 0.0, 10, ?)", (now_str,))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 1
    assert pytest.approx(metrics.avg_slippage_bps, abs=0.01) == 10000.0
    # Cost scaling factor is capped at 3.00
    assert metrics.cost_scaling_factor == 3.00


# ------------------------------------------------------------------
# Test Category 4: Extreme high slippage values
# ------------------------------------------------------------------

def test_stress_extreme_high_slippage_values(tmp_path):
    """Test extreme high slippage values (e.g. 500 bps, 50,000 bps) and cost scaling capping."""
    db_file = str(tmp_path / "extreme_slippage.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE order_plans (order_id TEXT PRIMARY KEY, market TEXT, target_amount REAL)")
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, symbol TEXT,
            target_price REAL, executed_price REAL, slippage_bps REAL, executed_volume INTEGER, executed_at TEXT
        )
    """)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Order with 500 bps slippage: target 10000.0, executed 10500.0 -> 500 bps
    conn.execute("INSERT INTO execution_logs VALUES (1, 'ORD_500BPS', '005930.KS', 10000.0, 10500.0, 500.0, 100, ?)", (now_str,))
    # Order with 5000 bps slippage: target 100.0, executed 150.0 -> 5000 bps
    conn.execute("INSERT INTO execution_logs VALUES (2, 'ORD_5000BPS', 'AAPL', 100.0, 150.0, 5000.0, 100, ?)", (now_str,))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 2
    expected_avg = (500.0 + 5000.0) / 2.0  # 2750 bps
    assert pytest.approx(metrics.avg_slippage_bps, abs=0.01) == expected_avg
    # Capped strictly at 3.00
    assert metrics.cost_scaling_factor == 3.00


def test_stress_extreme_slippage_ensemble_scorer_integration():
    """Verify that extreme cost scaling factor (3.0x) correctly penalizes returns in EnsembleScoringEngine."""
    scorer = EnsembleScoringEngine()
    extreme_metrics = SlippageMetrics(
        avg_slippage_bps=500.0,
        market_impact_alpha=0.80,
        market_slippage_map={'KOSPI': 500.0, 'SP500': 500.0},
        sample_count=10,
        cost_scaling_factor=3.00
    )
    scorer.update_microstructure_costs(extreme_metrics)

    assert scorer.cost_scaling_factor == 3.00
    assert scorer.realized_market_impact_alpha == 0.80

    df_candidate = pd.DataFrame([{
        'symbol': '005930.KS',
        'market': 'KOSPI',
        'close': 70000.0,
        'volume': 1000000.0,
        'reg_pred': 0.05,  # 5% return
        'volatility_20d': 0.02
    }])

    scored_df = scorer.combine_predictions(reg_df=df_candidate)
    assert 'ensemble_expected_return' in scored_df.columns
    ret_extreme = scored_df['ensemble_expected_return'].iloc[0]

    # Baseline cost
    scorer.update_microstructure_costs(SlippageMetrics(avg_slippage_bps=5.0, cost_scaling_factor=1.0))
    scored_df_normal = scorer.combine_predictions(reg_df=df_candidate)
    ret_normal = scored_df_normal['ensemble_expected_return'].iloc[0]

    assert ret_extreme < ret_normal


# ------------------------------------------------------------------
# Test Category 5: Unrecognized market labels or missing market column
# ------------------------------------------------------------------

def test_stress_missing_market_column_in_order_plans(tmp_path):
    """Test when order_plans table exists but market column is missing."""
    db_file = str(tmp_path / "missing_market_col.db")
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE order_plans (
            order_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, target_price REAL NOT NULL, target_amount REAL
        )
    """)
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL, symbol TEXT NOT NULL,
            target_price REAL NOT NULL, executed_price REAL NOT NULL, slippage_bps REAL NOT NULL,
            executed_volume INTEGER NOT NULL, executed_at TEXT NOT NULL
        )
    """)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO order_plans VALUES ('ORD_1', '005930.KS', 10000.0, 100000.0)")
    conn.execute("INSERT INTO execution_logs VALUES (1, 'ORD_1', '005930.KS', 10000.0, 10010.0, 10.0, 10, ?)", (now_str,))
    conn.commit()
    conn.close()

    # Query tries `p.market`. Missing column triggers sqlite3.OperationalError: no such column: p.market
    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    # Caught by try-except -> fallback to default SlippageMetrics baseline
    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


def test_stress_missing_target_amount_column_in_order_plans(tmp_path):
    """Test vulnerability: order_plans lacking unused target_amount column causes query failure."""
    db_file = str(tmp_path / "missing_target_amount_col.db")
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE order_plans (
            order_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, market TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL, symbol TEXT NOT NULL,
            target_price REAL NOT NULL, executed_price REAL NOT NULL, slippage_bps REAL NOT NULL,
            executed_volume INTEGER NOT NULL, executed_at TEXT NOT NULL
        )
    """)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO order_plans VALUES ('ORD_1', '005930.KS', 'KOSPI')")
    conn.execute("INSERT INTO execution_logs VALUES (1, 'ORD_1', '005930.KS', 10000.0, 10010.0, 10.0, 10, ?)", (now_str,))
    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    # Query fails on p.target_amount -> fallback to default baseline
    assert metrics.sample_count == 0
    assert metrics.avg_slippage_bps == 5.0


def test_stress_unrecognized_or_null_market_labels(tmp_path):
    """Test unrecognized, NULL, or empty string market labels and market inference fallback."""
    db_file = str(tmp_path / "unrecognized_markets.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE order_plans (order_id TEXT PRIMARY KEY, symbol TEXT, market TEXT, target_amount REAL)")
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, symbol TEXT,
            target_price REAL, executed_price REAL, slippage_bps REAL, executed_volume INTEGER, executed_at TEXT
        )
    """)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Record 1: market = 'CUSTOM_CRYPTO', symbol = 'BTC-USD' -> market = 'CUSTOM_CRYPTO'
    conn.execute("INSERT INTO order_plans VALUES ('ORD_1', 'BTC-USD', 'CUSTOM_CRYPTO', 1000.0)")
    conn.execute("INSERT INTO execution_logs VALUES (1, 'ORD_1', 'BTC-USD', 50000.0, 50100.0, 20.0, 1, ?)", (now_str,))

    # Record 2: market = None, symbol = '005930.KS' -> inferred as 'KOSPI'
    conn.execute("INSERT INTO order_plans VALUES ('ORD_2', '005930.KS', NULL, 1000.0)")
    conn.execute("INSERT INTO execution_logs VALUES (2, 'ORD_2', '005930.KS', 10000.0, 10020.0, 20.0, 10, ?)", (now_str,))

    # Record 3: market = '', symbol = '035720.KQ' -> inferred as 'KOSDAQ'
    conn.execute("INSERT INTO order_plans VALUES ('ORD_3', '035720.KQ', '', 1000.0)")
    conn.execute("INSERT INTO execution_logs VALUES (3, 'ORD_3', '035720.KQ', 10000.0, 10030.0, 30.0, 10, ?)", (now_str,))

    # Record 4: market = 'NONE', symbol = 'NVDA' -> inferred as 'SP500'
    conn.execute("INSERT INTO order_plans VALUES ('ORD_4', 'NVDA', 'NONE', 1000.0)")
    conn.execute("INSERT INTO execution_logs VALUES (4, 'ORD_4', 'NVDA', 100.0, 100.10, 10.0, 10, ?)", (now_str,))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 4
    assert 'CUSTOM_CRYPTO' in metrics.market_slippage_map
    assert pytest.approx(metrics.market_slippage_map['CUSTOM_CRYPTO'], abs=0.01) == 20.0
    assert pytest.approx(metrics.market_slippage_map['KOSPI'], abs=0.01) == 20.0
    assert pytest.approx(metrics.market_slippage_map['KOSDAQ'], abs=0.01) == 30.0
    assert pytest.approx(metrics.market_slippage_map['SP500'], abs=0.01) == 10.0


# ------------------------------------------------------------------
# Test Category 6: Empirical Impact Alpha Calculation & Boundary Stress
# ------------------------------------------------------------------

def test_stress_alpha_calculation_boundary_and_inverse_slippage(tmp_path):
    """Test market impact alpha calculation with inverse slippage (large order lower slippage) and equal sizes."""
    db_file = str(tmp_path / "alpha_inverse.db")
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE order_plans (order_id TEXT PRIMARY KEY, market TEXT, target_amount REAL)")
    conn.execute("""
        CREATE TABLE execution_logs (
            execution_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, symbol TEXT,
            target_price REAL, executed_price REAL, slippage_bps REAL, executed_volume INTEGER, executed_at TEXT
        )
    """)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 6 executions where large order size has LOWER slippage (e.g. limit order block trade with minimal impact)
    records = [
        (10, 10.0, 10.50),   # Vol 10, size 105, slip 500 bps
        (10, 10.0, 10.50),   # Vol 10, size 105, slip 500 bps
        (100, 10.0, 10.20),  # Vol 100, size 1020, slip 200 bps
        (100, 10.0, 10.20),  # Vol 100, size 1020, slip 200 bps
        (1000, 10.0, 10.01), # Vol 1000, size 10010, slip 10 bps
        (1000, 10.0, 10.01), # Vol 1000, size 10010, slip 10 bps
    ]

    for idx, (vol, t_p, e_p) in enumerate(records):
        conn.execute("INSERT INTO execution_logs VALUES (?, 'ORD_INV', '005930.KS', ?, ?, 0.0, ?, ?)",
                     (idx + 1, t_p, e_p, vol, now_str))

    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file)
    metrics = engine.calculate_realized_slippage()

    assert metrics.sample_count == 6
    # Log slip ratio is negative because slip_large < slip_small. Clamped to minimum alpha 0.30
    assert metrics.market_impact_alpha == 0.30
