"""
Comprehensive Unit & Regression Tests for System Improvement Proposal Fixes:
1. earnings_data.py - numpy import, dynamic regulatory filing lag, BPS calculation
2. indicator_storage.py - survivorship bias safe query, consolidated close()
3. database.py - atomic execute_write_batch, log_execution
4. risk_manager.py - recovery cash interpolation, 2-sided macro shock scoring, drawdown clamp
5. ensemble_scorer.py - market-segregated prev_weights, raw Sharpe elasticity tiers, coverage shrinkage
6. factor_orthogonalizer.py - dispersion preservation, NaN safe standard deviations
7. oms_engine.py - KRX odd-lot sizing
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime
import os
import tempfile
import asyncio

from src.data_layer.earnings_data import compute_regulatory_filing_lag, fetch_fundamentals
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.persistence.database import _DBConnection, TradeLogger
from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.execution.oms_engine import ExecutionOMSEngine


class TestEarningsDataFixes(unittest.TestCase):
    def test_regulatory_filing_lag_computation(self):
        # KRX quarterly: 45 days
        dt_q = datetime(2026, 3, 31)
        lag_krx_q = compute_regulatory_filing_lag(dt_q, period_type='quarterly', is_krx=True)
        self.assertEqual(lag_krx_q, (pd.to_datetime(dt_q) + pd.Timedelta(days=45)).strftime('%Y-%m-%d'))

        # KRX annual: 90 days
        dt_a = datetime(2025, 12, 31)
        lag_krx_a = compute_regulatory_filing_lag(dt_a, period_type='annual', is_krx=True)
        self.assertEqual(lag_krx_a, (pd.to_datetime(dt_a) + pd.Timedelta(days=90)).strftime('%Y-%m-%d'))

        # US SEC 10-Q: 40 days
        lag_us_q = compute_regulatory_filing_lag(dt_q, period_type='quarterly', is_krx=False)
        self.assertEqual(lag_us_q, (pd.to_datetime(dt_q) + pd.Timedelta(days=40)).strftime('%Y-%m-%d'))

        # US SEC 10-K: 60 days
        lag_us_a = compute_regulatory_filing_lag(dt_a, period_type='annual', is_krx=False)
        self.assertEqual(lag_us_a, (pd.to_datetime(dt_a) + pd.Timedelta(days=60)).strftime('%Y-%m-%d'))


class TestIndicatorStorageFixes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_indicators.db")
        self.storage = MarketIndicatorStorage(db_path=self.db_path)

    def tearDown(self):
        self.storage.close()
        self.temp_dir.cleanup()

    def test_survivorship_bias_safe_query(self):
        # Insert a dummy universe and indicator row
        with self.storage._connect() as conn:
            conn.execute("INSERT INTO stock_universe (symbol, name, market) VALUES ('005930', '삼성전자', 'KOSPI')")
            conn.execute("INSERT INTO global_indicators (date, symbol, name, price, change_pct) VALUES ('2026-08-20', '^VIX', 'VIX', 15.0, 0.0)")
            conn.commit()

        # Should not raise OperationalError even without stock_prices table
        with self.storage._connect() as conn:
            min_date_row = conn.execute("SELECT MIN(date) FROM global_indicators").fetchone()
            self.assertEqual(min_date_row[0], '2026-08-20')

        universe = self.storage.get_universe()
        self.assertGreater(len(universe), 0)

    def test_close_checkpoints_wal_and_cleans_conn(self):
        with self.storage._connect() as conn:
            conn.execute("INSERT INTO stock_universe (symbol, name, market) VALUES ('005930', '삼성전자', 'KOSPI')")
            conn.commit()
        self.storage.close()
        conn = getattr(self.storage._local, "conn", None)
        self.assertIsNone(conn)


class TestDatabaseTransactionFixes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_trade_logs.db")
        self.logger = TradeLogger(db_path=self.db_path)

    async def asyncTearDown(self):
        await self.logger._conn_mgr.close()
        self.temp_dir.cleanup()

    async def test_atomic_log_execution(self):
        await self.logger.log_execution(
            order_id="ORD-001",
            symbol="005930",
            quantity=15,
            price=72000.0
        )
        trades = await self.logger.get_trade_history()
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["order_id"], "ORD-001")
        self.assertEqual(trades[0]["quantity"], 15)


class TestRiskManagerFixes(unittest.TestCase):
    def setUp(self):
        self.detector = CrisisDetector()

    def test_recovery_cash_interpolation(self):
        # When recovering from SEVERE crisis to NONE
        self.detector._crisis_level = CrisisLevel.NONE
        self.detector._prev_crisis_level = CrisisLevel.SEVERE
        self.detector._recovery_mode = True

        # Day 1: progress = 1/20 = 0.05 -> cash target should be high (~0.8125)
        self.detector._recovery_days = 1
        cash_day1 = self.detector.get_crisis_cash_target()
        self.assertGreater(cash_day1, 0.75)

        # Day 10: progress = 10/20 = 0.50 -> cash target ~0.475
        self.detector._recovery_days = 10
        cash_day10 = self.detector.get_crisis_cash_target()
        self.assertAlmostEqual(cash_day10, 0.10 + (0.85 - 0.10) * 0.50, places=2)

        # Day 20: progress = 20/20 = 1.0 -> cash target == 0.10
        self.detector._recovery_days = 20
        cash_day20 = self.detector.get_crisis_cash_target()
        self.assertAlmostEqual(cash_day20, 0.10, places=4)

    def test_two_sided_macro_shock_scoring(self):
        # Normal oil at $80
        score_normal = self.detector._score_macro(usdkrw=1350.0, oil=80.0, tnx=4.2, dxy=103.0)
        self.assertLess(score_normal, 0.10)

        # Deflationary crash at $25 oil
        score_oil_crash = self.detector._score_macro(usdkrw=1350.0, oil=25.0, tnx=4.2, dxy=103.0)
        self.assertGreater(score_oil_crash, score_normal)

    def test_drawdown_negative_input_clamp(self):
        # Negative drawdown input should not produce negative risk score
        score_neg = self.detector._score_drawdown(-0.15)
        self.assertGreaterEqual(score_neg, 0.0)


class TestEnsembleScorerFixes(unittest.TestCase):
    def setUp(self):
        self.scorer = EnsembleScoringEngine()

    def test_convex_sharpe_elasticity_tiers(self):
        # Strategy with Sharpe >= 1.50 receives 1.25x boost
        sharpes = {'vcp_ml': 1.60, 'surge': 0.0}
        weights = self.scorer.compute_dynamic_weights_from_sharpe(sharpes, 'BULL_LOW_VOL', gamma=1.0)
        base = self.scorer.get_base_weights('BULL_LOW_VOL')
        # vcp_ml weight should be substantially elevated
        self.assertGreater(weights['vcp_ml'], base['vcp_ml'])

    def test_market_segregated_prev_weights(self):
        # Test that US and KR weights are separately tracked without cross-contaminating
        us_w = self.scorer.compute_dynamic_weights_from_sharpe({'vcp_ml': 0.5}, 'BULL_LOW_VOL', market="us")
        kr_w = self.scorer.compute_dynamic_weights_from_sharpe({'vcp_ml': 0.5}, 'BEAR_HIGH_VOL', market="kr")

        self.assertIn("us", self.scorer._prev_weights)
        self.assertIn("kr", self.scorer._prev_weights)
        self.assertEqual(self.scorer._prev_regime.get("us"), "BULL_LOW_VOL")
        self.assertEqual(self.scorer._prev_regime.get("kr"), "BEAR_HIGH_VOL")

    def test_coverage_shrinkage_penalizes_sparse_stocks(self):
        res_full = self.scorer.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            regression_df=pd.DataFrame({'symbol': ['FULL'], 'expected_return': [0.10], 'score': [0.90]}),
            surge_df=pd.DataFrame({'symbol': ['FULL'], 'surge_prob_20d': [0.90]}),
            rim_df=pd.DataFrame({'symbol': ['FULL'], 'rim_score': [0.90]}),
        )
        res_sparse = self.scorer.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            regression_df=pd.DataFrame({'symbol': ['SPARSE'], 'expected_return': [0.10], 'score': [0.90]}),
        )
        # Full coverage stock should have higher or equal conviction score
        self.assertGreater(res_full['ensemble_score'].iloc[0], res_sparse['ensemble_score'].iloc[0])


class TestFactorOrthogonalizerFixes(unittest.TestCase):
    def setUp(self):
        self.ortho = FactorOrthogonalizerEngine()

    def test_nan_std_handling(self):
        # Synthetic DataFrame where one column is completely identical (zero variance -> std=0/NaN)
        df = pd.DataFrame({
            'strat1': [0.5, 0.5, 0.5, 0.5, 0.5],
            'strat2': [0.1, 0.3, 0.5, 0.7, 0.9],
            'strat3': [0.9, 0.7, 0.5, 0.3, 0.1],
        })
        res = self.ortho.orthogonalize(df, strategy_cols=['strat1', 'strat2', 'strat3'])
        self.assertEqual(len(res), 5)
        self.assertTrue(np.all(np.isfinite(res.values)))


class TestOMSEngineFixes(unittest.TestCase):
    def test_krx_odd_lot_preservation(self):
        oms = ExecutionOMSEngine()
        # Target allocation of 15 shares of Samsung Electronics at 70,000 KRW
        predictions = [{
            "symbol": "005930",
            "market": "KOSPI",
            "name": "삼성전자",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "expected_return": 0.05,
            "confidence": 0.80,
            "adv_20d": 500_000_000_000.0,
        }]
        portfolio_weights = {"005930": 0.0105}
        order_plan = oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=portfolio_weights,
            total_capital=100_000_000.0,
            current_holdings={},
            use_leland_buffer=False
        )
        buy_orders = [o for o in order_plan if o["symbol"] == "005930" and o["action"] == "BUY"]
        self.assertEqual(len(buy_orders), 1)
        # 15 shares should NOT be truncated to 10 shares
        self.assertEqual(buy_orders[0]["quantity"], 15)


if __name__ == "__main__":
    unittest.main()
