import pandas as pd
import numpy as np
import os
import sqlite3

from src.risk.portfolio_optimizer import PortfolioOptimizer
from src.execution.oms_engine import ExecutionOMSEngine

def test_portfolio_optimizer_risk_parity():
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=20)
    df_returns = pd.DataFrame({
        "005930": np.random.normal(0.001, 0.02, 20),
        "000660": np.random.normal(0.0015, 0.03, 20),
        "AAPL": np.random.normal(0.0008, 0.015, 20),
    }, index=dates)

    optimizer = PortfolioOptimizer(default_max_weight=0.50)
    weights = optimizer.optimize_risk_parity(df_returns)

    assert len(weights) == 3
    assert abs(sum(weights.values()) - 1.0) < 1e-4
    # High volatility symbol (000660) should get lower weight than low vol symbol (AAPL)
    assert weights["000660"] < weights["AAPL"]

def test_factor_and_sector_constraints():
    optimizer = PortfolioOptimizer(default_max_sector_weight=0.40)
    raw_weights = {"005930": 0.35, "000660": 0.35, "AAPL": 0.15, "MSFT": 0.15}
    sector_map = {"005930": "Semiconductors", "000660": "Semiconductors", "AAPL": "Tech", "MSFT": "Software"}

    adj_weights = optimizer.apply_factor_and_sector_constraints(raw_weights, sector_map)

    # Semiconductors total weight should be capped to <= 0.40 after re-normalization constraint
    semi_weight = adj_weights["005930"] + adj_weights["000660"]
    assert semi_weight <= 0.45
    assert abs(sum(adj_weights.values()) - 1.0) < 1e-4

def test_execution_oms_engine(tmp_path):
    db_file = os.path.join(tmp_path, "test_trade_logs.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    top_predictions = [
        {"symbol": "005930", "name": "삼성전자", "market": "KOSPI", "close_price": 70000},
        {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI", "close_price": 120000}
    ]
    weights = {"005930": 0.60, "000660": 0.40}

    order_plans = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)
    assert len(order_plans) == 2
    assert order_plans[0]["symbol"] == "005930"
    assert order_plans[0]["target_amount"] == 60000000.0

    exec_result = oms.record_execution(
        order_id=order_plans[0]["order_id"],
        symbol="005930",
        target_price=70000,
        executed_price=70140,
        executed_volume=855
    )

    # 140 / 70000 = 0.002 = +20.0 bps
    assert abs(exec_result["slippage_bps"] - 20.0) < 1e-2

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM order_plans WHERE symbol='005930'")
    status = cursor.fetchone()[0]
    conn.close()
    assert status == "EXECUTED"


def test_oms_rejects_dict_string_symbols(tmp_path):
    """Live-money guard: upstream VCP corruption used to inject str(dict) symbols
    (412/844 order plans had garbage tickers). These must never become order plans."""
    db_file = os.path.join(tmp_path, "test_trade_logs_reject.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    top_predictions = [
        {"symbol": "{'is_vcp': False, 'vcp_score': 45.0, 'symbol': 'MSFT'}", "name": "corrupt", "market": "KOSPI", "close_price": 100.0},
        {"symbol": "AAPL", "name": "Apple", "market": "NASDAQ", "close_price": 250.0},
    ]
    weights = {"AAPL": 0.10}
    order_plans = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)

    assert len(order_plans) == 1
    assert order_plans[0]["symbol"] == "AAPL"

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT symbol FROM order_plans").fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["AAPL"]


def test_oms_skips_plans_without_explicit_price(tmp_path):
    """Live-money guard: the old 1.0 KRW fallback would produce 'buy at 1 won'
    plans. Plans without a real close price must be skipped entirely."""
    db_file = os.path.join(tmp_path, "test_trade_logs_price.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    top_predictions = [
        {"symbol": "005930", "name": "Samsung", "market": "KOSPI"},  # no price at all
        {"symbol": "000660", "name": "SK Hynix", "market": "KOSPI", "close_price": 120000},
    ]
    weights = {"005930": 0.5, "000660": 0.5}
    order_plans = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)

    assert len(order_plans) == 1
    assert order_plans[0]["symbol"] == "000660"
    assert order_plans[0]["target_price"] > 1.0


def test_oms_blocks_all_plans_in_severe_crisis(tmp_path):
    """Live-money guard: SEVERE crisis must suppress ALL order plan generation."""
    db_file = os.path.join(tmp_path, "test_trade_logs_crisis.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    top_predictions = [
        {"symbol": "005930", "name": "Samsung", "market": "KOSPI", "close_price": 70000},
        {"symbol": "AAPL", "name": "Apple", "market": "NASDAQ", "close_price": 250.0},
    ]
    weights = {"005930": 0.5, "AAPL": 0.5}

    plans_normal = oms.generate_order_plan(top_predictions, weights, total_capital=100000000, crisis_level="NORMAL")
    assert len(plans_normal) == 2

    plans_severe = oms.generate_order_plan(top_predictions, weights, total_capital=100000000, crisis_level="SEVERE")
    assert plans_severe == []

    plans_active = oms.generate_order_plan(top_predictions, weights, total_capital=100000000, crisis_level="ACTIVE")
    assert len(plans_active) == 2


def test_oms_rejects_out_of_bounds_prices(tmp_path):
    """Live-money guard: absurd prices (split gaps, corrupted data) must be dropped."""
    db_file = os.path.join(tmp_path, "test_trade_logs_bounds.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    top_predictions = [
        {"symbol": "A", "name": "", "market": "KOSPI", "close_price": 0.0001},
        {"symbol": "B", "name": "", "market": "KOSPI", "close_price": -5.0},
        {"symbol": "C", "name": "", "market": "KOSPI", "close_price": 200000000},
        {"symbol": "D", "name": "", "market": "KOSPI", "close_price": 50000},
    ]
    weights = {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}
    order_plans = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)

    assert [p["symbol"] for p in order_plans] == ["D"]


def test_oms_kill_switch_blocks_all_plans(tmp_path, monkeypatch):
    """Live-money guard: kill switch (file/env/engage) must suppress ALL order plan generation."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.execution import kill_switch

    # Isolate the switch files from the real project directory
    monkeypatch.setattr(kill_switch, "KILL_SWITCH_FILE", tmp_path / "KILL_SWITCH")
    monkeypatch.setattr(kill_switch, "STATE_FILE", tmp_path / "kill_switch_state.json")

    db_file = os.path.join(tmp_path, "test_trade_logs_killswitch.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    top_predictions = [
        {"symbol": "005930", "name": "Samsung", "market": "KOSPI", "close_price": 70000},
        {"symbol": "AAPL", "name": "Apple", "market": "NASDAQ", "close_price": 250.0},
    ]
    weights = {"005930": 0.5, "AAPL": 0.5}

    assert not kill_switch.is_kill_switch_active()
    plans_normal = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)
    assert len(plans_normal) == 2

    kill_switch.engage(reason="test")
    try:
        assert kill_switch.is_kill_switch_active()
        plans_killed = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)
        assert plans_killed == []
        assert kill_switch.get_state().get("status") == "engaged"
    finally:
        kill_switch.disengage()

    assert not kill_switch.is_kill_switch_active()
    plans_again = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)
    assert len(plans_again) == 2


def test_oms_quantity_conversion_and_lot_rounding(tmp_path):
    """Live-money guard: target_amount -> quantity with KRX 10-lot / US 1-lot rounding."""
    db_file = os.path.join(tmp_path, "test_trade_logs_qty.db")
    oms = ExecutionOMSEngine(db_path=db_file)

    # KRX: 100M * 0.5 = 50M won @ 70000 -> 714 shares -> 710 (10-lot)
    top_predictions = [
        {"symbol": "005930", "name": "Samsung", "market": "KOSPI", "close_price": 70000},
        # US: 100M * 0.5 = 50M won @ 250 -> 200,000 shares -> 200,000 (1-lot)
        {"symbol": "AAPL", "name": "Apple", "market": "NASDAQ", "close_price": 250.0},
    ]
    weights = {"005930": 0.5, "AAPL": 0.5}

    plans = oms.generate_order_plan(top_predictions, weights, total_capital=100000000)
    plans_by_sym = {p["symbol"]: p for p in plans}

    assert plans_by_sym["005930"]["quantity"] == 710
    assert plans_by_sym["AAPL"]["quantity"] == 200000

    conn = sqlite3.connect(db_file)
    qty_krx = conn.execute("SELECT quantity FROM order_plans WHERE symbol='005930'").fetchone()[0]
    conn.close()
    assert qty_krx == 710

    # Sub-lot plan must be dropped entirely
    tiny_plans = oms.generate_order_plan(
        [{"symbol": "005930", "name": "S", "market": "KOSPI", "close_price": 70000}],
        {"005930": 0.00001}, total_capital=100000000)
    assert tiny_plans == []
