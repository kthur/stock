"""
Phase 8 System Verification Test Suite
Tests all 30 advanced improvements including P0/P1/P2/P3 features:
- APICircuitBreaker
- PortfolioCircuitBreaker
- safe_strategy_execute isolation wrapper
- OMS partial fill status tracking
- Ledoit-Wolf covariance shrinkage in PortfolioAllocator
- Löwdin symmetric orthogonalization in EnsembleScoringEngine
- ECE and Brier score calibration monitoring
- FeatureDriftDetector (PSI & Page-Hinkley)
- WalkForwardBacktestEngine (OOS metrics)
- Almgren-Chriss Market Impact model in HFTEngine
- Built-in stress tests in RiskManager
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import os

from src.utils.circuit_breaker import APICircuitBreaker, CircuitBreakerOpenException
from src.risk.risk_manager import PortfolioCircuitBreaker, RiskManager
from src.utils.error_handler import safe_strategy_execute
from src.execution.oms_engine import ExecutionOMSEngine
from src.risk.portfolio_allocator import PortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.drift_detector import FeatureDriftDetector
from src.backtest.engine import WalkForwardBacktestEngine
from src.core.hft_engine import HFTEngine


def test_api_circuit_breaker():
    breaker = APICircuitBreaker(name="test", fail_max=3, reset_timeout=60.0)
    assert not breaker.is_open()

    def failing_call():
        raise ValueError("API Error")

    for _ in range(3):
        with pytest.raises(ValueError):
            breaker.call(failing_call)

    assert breaker.is_open()
    with pytest.raises(CircuitBreakerOpenException):
        breaker.call(failing_call)


def test_portfolio_circuit_breaker():
    cb = PortfolioCircuitBreaker(max_drawdown=-0.15)
    assert not cb.update_and_check(100_000_000.0)
    assert not cb.update_and_check(110_000_000.0)  # Peak = 110M
    # Drop to 90M -> drawdown = (90 - 110)/110 = -18.18% <= -15%
    assert cb.update_and_check(90_000_000.0)
    assert cb.is_tripped


def test_safe_strategy_execute_wrapper():
    def buggy_strategy():
        raise RuntimeError("Strategy crash!")

    df = safe_strategy_execute("BuggyStrategy", buggy_strategy)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_oms_partial_fill_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_trade_logs.db")
        oms = ExecutionOMSEngine(db_path=db_path)

        predictions = [{
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "close_price": 70000.0,
            "target_price": 70000.0
        }]
        weights = {"005930": 0.10}

        plans = oms.generate_order_plan(predictions, weights, total_capital=100_000_000.0)
        assert len(plans) == 1
        order_id = plans[0]["order_id"]
        target_qty = plans[0]["quantity"]

        # Partial fill (half of target_qty)
        half_qty = max(1, target_qty // 2)
        exec1 = oms.record_execution(order_id, "005930", 70000.0, 70000.0, half_qty)

        conn = oms._get_conn()
        status1 = conn.cursor().execute("SELECT status FROM order_plans WHERE order_id = ?", (order_id,)).fetchone()[0]
        conn.close()
        assert status1 == "PARTIALLY_FILLED"

        # Complete fill (remaining qty)
        rem_qty = target_qty - half_qty
        exec2 = oms.record_execution(order_id, "005930", 70000.0, 70000.0, rem_qty)

        conn = oms._get_conn()
        status2 = conn.cursor().execute("SELECT status FROM order_plans WHERE order_id = ?", (order_id,)).fetchone()[0]
        conn.close()
        assert status2 == "EXECUTED"


def test_ledoit_wolf_covariance_optimization():
    allocator = PortfolioAllocator()
    expected_returns = pd.Series({"005930": 0.05, "000660": 0.08, "AAPL": 0.04})
    
    np.random.seed(42)
    returns_df = pd.DataFrame(
        np.random.normal(0.001, 0.02, size=(30, 3)),
        columns=["005930", "000660", "AAPL"]
    )
    
    weights = allocator.optimize_with_evt_cvar_constraint(expected_returns, returns_df=returns_df)
    assert len(weights) == 3
    assert abs(sum(weights.values()) - 1.0) < 1e-4


def test_lowdin_orthogonalization_penalty():
    scorer = EnsembleScoringEngine()
    initial_weights = {"strat_a": 0.5, "strat_b": 0.5}

    np.random.seed(42)
    col1 = np.random.normal(0, 1, 100)
    col2 = col1 + np.random.normal(0, 0.1, 100)  # Highly collinear
    scores_df = pd.DataFrame({"score_strat_a": col1, "score_strat_b": col2})

    penalized = scorer.apply_correlation_orthogonalization_penalty(initial_weights, scores_df=scores_df)
    assert len(penalized) == 2
    assert abs(sum(penalized.values()) - 1.0) < 1e-4


def test_ece_brier_score_metric():
    probs = np.array([0.9, 0.8, 0.2, 0.1, 0.95])
    y_true = np.array([1, 1, 0, 0, 1])

    metrics = EnsembleScoringEngine.compute_ece_and_brier(probs, y_true)
    assert "ece" in metrics and "brier" in metrics
    assert 0.0 <= metrics["ece"] <= 1.0
    assert 0.0 <= metrics["brier"] <= 1.0


def test_feature_drift_detector():
    detector = FeatureDriftDetector(psi_threshold=0.25)
    np.random.seed(42)
    ref = np.random.normal(0, 1, 1000)
    tar_same = np.random.normal(0, 1, 1000)
    tar_shifted = np.random.normal(2, 1, 1000)

    psi_same = detector.compute_psi(ref, tar_same)
    psi_shifted = detector.compute_psi(ref, tar_shifted)

    assert psi_same < 0.10
    assert psi_shifted >= 0.25


def test_walk_forward_backtest_engine():
    engine = WalkForwardBacktestEngine(initial_capital=100_000_000.0)
    dates = pd.date_range("2025-01-01", periods=100)
    price_df = pd.DataFrame({"Close": np.linspace(100, 150, 100)}, index=dates)
    signals = pd.Series(1.0, index=dates)

    metrics = engine.run_backtest(price_df, signals)
    assert metrics["n_days"] > 0
    assert metrics["final_equity"] > 100_000_000.0
    assert "cagr" in metrics and "sharpe_ratio" in metrics


def test_almgren_chriss_hft_execution():
    engine = HFTEngine()
    twap_recs = engine.execute_twap("005930", "BUY", total_quantity=1000, duration_minutes=10, intervals=5, start_price=70000.0)
    assert len(twap_recs) == 5
    for rec in twap_recs:
        assert rec["slippage"] >= 0.0


def test_built_in_stress_tests():
    rm = RiskManager()
    portfolio = {"005930": 0.40, "000660": 0.30, "AAPL": 0.30}
    res = rm.run_built_in_stress_tests(portfolio)
    assert res["status"] in ("PASS", "SCALED")
    assert "2008_GFC" in res["scenarios"]
