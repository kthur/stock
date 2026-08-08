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
