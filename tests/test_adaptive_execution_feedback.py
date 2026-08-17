import pytest
import sqlite3
import pandas as pd
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.slippage_feedback import SlippageFeedbackEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine


def test_adaptive_execution_feedback_loop(tmp_path):
    """Verify end-to-end execution logging -> slippage feedback -> ensemble scorer cost update."""
    db_file = tmp_path / "test_trade_logs.db"
    oms = ExecutionOMSEngine(db_path=str(db_file))

    # Generate a dummy order plan
    predictions = [{
        "symbol": "005930",
        "name": "Samsung",
        "market": "KOSPI",
        "close_price": 70000.0,
        "target_price": 70000.0,
        "expected_return": 10.0,
        "action": "BUY"
    }]
    weights = {"005930": 0.20}
    plans = oms.generate_order_plan(predictions, weights, total_capital=50_000_000.0)
    assert len(plans) == 1
    order_id = plans[0]["order_id"]

    # Record execution with slippage (target=70000, executed=70140 -> 20 bps slippage)
    exec_res = oms.record_execution(
        order_id=order_id,
        symbol="005930",
        target_price=70000.0,
        executed_price=70140.0,
        executed_volume=plans[0]["quantity"]
    )
    assert exec_res["slippage_bps"] == 20.0

    # Analyze feedback
    feedback_engine = SlippageFeedbackEngine(db_path=str(db_file))
    metrics = feedback_engine.analyze_realized_slippage()
    assert metrics is not None
    assert metrics.sample_count >= 1

    # Update EnsembleScoringEngine
    scorer = EnsembleScoringEngine()
    scorer.update_microstructure_costs(metrics)
    assert scorer.cost_scaling_factor >= 0.50
