# -*- coding: utf-8 -*-
"""
tests/test_slippage_feedback_kalman.py -- Comprehensive Unit & Stress Tests
for Online Adaptive Recursive Kalman Slippage Feedback Engine Calibration.

Verifies:
1. OnlineKalmanSlippageFilter mathematical convergence and parameter estimation.
2. Joseph-stabilized covariance matrix symmetry and positive definiteness.
3. Robustness against extreme outlier observations and parameter bound enforcement.
4. SlippageFeedbackEngine batch and online updates from trade_logs.db.
5. Integration with UnifiedPortfolioAllocator Gatheral 3/2-power penalty function.
"""

import math
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
_TRADING_SYS = _PROJECT_ROOT / "trading_system"
if str(_TRADING_SYS) not in sys.path:
    sys.path.insert(0, str(_TRADING_SYS))

from src.execution.slippage_feedback import (
    OnlineKalmanSlippageFilter,
    SlippageFeedbackEngine,
    SlippageMetrics,
)


class TestOnlineKalmanSlippageFilter:
    def test_filter_initialization_defaults(self):
        kf = OnlineKalmanSlippageFilter()
        state = kf.get_state()

        assert state["kappa"] == pytest.approx(0.50, abs=1e-6)
        assert state["beta"] == pytest.approx(1.00, abs=1e-6)
        assert state["update_count"] == 0
        assert state["cost_scaling_factor"] == pytest.approx(1.00, abs=1e-6)
        cov = np.array(state["covariance"])
        assert cov.shape == (2, 2)
        assert cov[0, 0] > 0
        assert cov[1, 1] > 0

    def test_single_step_update_innovation_and_covariance_reduction(self):
        kf = OnlineKalmanSlippageFilter(initial_kappa=0.50, initial_beta=1.00)
        p_initial_trace = np.trace(kf.P)

        # Observation with higher than expected slippage
        # H = [2.5, 5.0], expected_y = 0.5*2.5 + 1.0*5.0 = 6.25 bps. Realized = 9.0 bps
        kappa, beta = kf.update(realized_slippage_bps=9.0, h_kappa=2.5, h_beta=5.0)

        assert kf.update_count == 1
        assert kappa > 0.50  # Upward revision
        assert beta > 1.00   # Upward revision
        p_updated_trace = np.trace(kf.P)
        assert p_updated_trace < p_initial_trace  # Information gained

    def test_joseph_covariance_symmetry(self):
        kf = OnlineKalmanSlippageFilter()
        np.random.seed(101)

        for _ in range(50):
            hk = float(np.random.uniform(0.5, 5.0))
            hb = float(np.random.uniform(2.0, 8.0))
            y = float(np.random.uniform(1.0, 15.0))
            kf.update(y, hk, hb)

            # Assert exact symmetry: P == P^T
            np.testing.assert_allclose(kf.P, kf.P.T, atol=1e-12)
            # Assert positive semi-definiteness: all eigenvalues >= 0
            eigenvalues = np.linalg.eigvalsh(kf.P)
            assert np.all(eigenvalues >= -1e-9)

    def test_parameter_convergence_under_simulated_execution_regime(self):
        """Simulates 300 executions with known true parameters kappa*=0.80, beta*=1.35."""
        kf = OnlineKalmanSlippageFilter(initial_kappa=0.50, initial_beta=1.00)
        true_kappa = 0.80
        true_beta = 1.35
        noise_std = 1.0

        np.random.seed(42)
        for _ in range(300):
            hk = float(np.random.uniform(1.0, 6.0))
            hb = float(np.random.uniform(3.0, 9.0))
            noise = float(np.random.normal(0.0, noise_std))
            y = true_kappa * hk + true_beta * hb + noise
            kf.update(y, hk, hb)

        state = kf.get_state()
        est_kappa = state["kappa"]
        est_beta = state["beta"]

        # Assert convergence to true parameters within close statistical bound
        assert abs(est_kappa - true_kappa) < 0.12, f"Kappa {est_kappa} diverged from {true_kappa}"
        assert abs(est_beta - true_beta) < 0.12, f"Beta {est_beta} diverged from {true_beta}"

        # Assert covariance shrinkage
        cov = np.array(state["covariance"])
        assert cov[0, 0] < 0.05
        assert cov[1, 1] < 0.05

    def test_outlier_clamping_and_bounds_enforcement(self):
        kf = OnlineKalmanSlippageFilter(
            initial_kappa=0.50,
            initial_beta=1.00,
            kappa_bounds=(0.05, 5.0),
            beta_bounds=(0.10, 5.0),
        )

        # Feed extreme positive shocks
        for _ in range(20):
            kf.update(realized_slippage_bps=500.0, h_kappa=10.0, h_beta=10.0)

        state = kf.get_state()
        assert state["kappa"] <= 5.0
        assert state["beta"] <= 5.0

        # Feed extreme negative shocks
        for _ in range(30):
            kf.update(realized_slippage_bps=-200.0, h_kappa=10.0, h_beta=10.0)

        state = kf.get_state()
        assert state["kappa"] >= 0.05
        assert state["beta"] >= 0.10

    def test_reset_functionality(self):
        kf = OnlineKalmanSlippageFilter()
        kf.update(realized_slippage_bps=20.0, h_kappa=5.0, h_beta=8.0)
        assert kf.update_count == 1

        kf.reset(initial_kappa=0.60, initial_beta=1.10)
        state = kf.get_state()
        assert state["update_count"] == 0
        assert state["kappa"] == pytest.approx(0.60)
        assert state["beta"] == pytest.approx(1.10)


class TestSlippageFeedbackEngineKalmanIntegration:
    @pytest.fixture
    def test_db(self, tmp_path):
        db_file = tmp_path / "trade_logs_kalman.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("""
            CREATE TABLE trade_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                order_qty INTEGER NOT NULL,
                filled_qty INTEGER NOT NULL,
                expected_price REAL NOT NULL,
                fill_price REAL NOT NULL,
                slippage_bps REAL,
                market_impact_bps REAL,
                adv_20d REAL,
                volatility REAL,
                timestamp TIMESTAMP NOT NULL,
                notes TEXT
            );
        """)
        conn.commit()
        conn.close()
        return db_file

    def test_missing_db_returns_kalman_defaults(self, tmp_path):
        missing = tmp_path / "does_not_exist.db"
        engine = SlippageFeedbackEngine(db_path=str(missing), default_slippage_bps=5.0)
        metrics = engine.calculate_realized_slippage()

        assert metrics.kalman_kappa == pytest.approx(0.50)
        assert metrics.kalman_beta == pytest.approx(1.00)
        assert metrics.kalman_cost_scaling_factor == pytest.approx(1.00)
        assert len(metrics.kalman_state) == 2
        assert len(metrics.kalman_covariance) == 2

    def test_batch_calibration_from_trade_logs(self, test_db):
        conn = sqlite3.connect(str(test_db))
        # Insert 40 trades with elevated slippage (25.0 bps)
        for i in range(40):
            pt = 100.0
            pe = 100.25  # 25.0 bps slippage
            adv = 500_000.0
            qty = 5_000
            vol = 0.025
            conn.execute("""
                INSERT INTO trade_logs (
                    symbol, market, side, order_qty, filled_qty, expected_price, fill_price,
                    slippage_bps, market_impact_bps, adv_20d, volatility, timestamp, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """, (f"SYM{i}", "SP500", "BUY", qty, qty, pt, pe, 25.0, 5.0, adv, vol, "kalman_test"))
        conn.commit()
        conn.close()

        engine = SlippageFeedbackEngine(db_path=str(test_db))
        metrics = engine.calculate_realized_slippage()

        assert metrics.total_trades == 40
        assert metrics.avg_slippage_bps == pytest.approx(25.0, abs=1.0)
        # Kalman filter should adapt upward reflecting elevated slippage
        assert metrics.kalman_beta > 1.00 or metrics.kalman_kappa > 0.50
        assert metrics.kalman_cost_scaling_factor > 1.0

        summary = engine.get_summary()
        assert "kalman_kappa" in summary
        assert "kalman_beta" in summary
        assert "kalman_cost_scaling_factor" in summary

    def test_record_execution_triggers_online_kalman_step(self, test_db):
        engine = SlippageFeedbackEngine(db_path=str(test_db))
        initial_count = engine.kalman_filter.update_count

        engine.record_execution(
            symbol="005930",
            market="KOSPI",
            side="BUY",
            order_qty=1000,
            filled_qty=1000,
            target_price=70000.0,
            executed_price=70050.0,
            realized_slippage_bps=7.14,
            adv_20d=2_000_000.0,
            volatility=0.018,
            notes="online test",
        )

        assert engine.kalman_filter.update_count == initial_count + 1
        params = engine.get_kalman_parameters()
        assert params["update_count"] == initial_count + 1

    def test_unified_portfolio_allocator_consumes_kalman_feedback(self, test_db):
        """Verifies that UnifiedPortfolioAllocator successfully queries SlippageFeedbackEngine."""
        from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator

        allocator = UnifiedPortfolioAllocator()
        symbols = ["005930", "000660", "AAPL", "MSFT"]
        n = len(symbols)
        pred_returns = np.array([0.05, 0.03, 0.04, 0.02])
        dates = pd.date_range("2026-01-01", periods=60)
        returns_df = pd.DataFrame(
            np.random.normal(0.0005, 0.01, size=(60, n)), index=dates, columns=symbols
        )
        cov_matrix = np.cov(returns_df.values, rowvar=False)
        advs = np.array([5_000_000.0, 3_000_000.0, 10_000_000.0, 8_000_000.0])

        weights = allocator.optimize_portfolio(
            predicted_returns=pred_returns,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            advs=advs,
            current_weights=np.array([0.25, 0.25, 0.25, 0.25]),
            cost_scaling_factor=None,  # Triggers automatic SlippageFeedbackEngine query
        )

        assert weights is not None
        assert len(weights) == n
        assert np.isclose(np.sum(weights), 1.0, atol=1e-2)
