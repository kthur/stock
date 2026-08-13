"""
tests/test_indicator_storage.py
Unit tests for MarketIndicatorStorage persistence and batch fundamentals operations.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
create dummy/facade implementations, or circumvent the intended task. A Forensic
Auditor will independently verify your work. Integrity violations WILL be detected
and your work WILL be rejected.
"""

import os
import sys
import shutil
import tempfile
import unittest
import pandas as pd

# Ensure project root and trading_system are in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.data_layer.indicator_storage import MarketIndicatorStorage


class TestMarketIndicatorStorage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_indicators.db")
        self.storage = MarketIndicatorStorage(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_get_fundamentals(self):
        df_fund = pd.DataFrame([
            {
                "symbol": "005930",
                "date": "2024-03-31",
                "revenue": 71920000000000.0,
                "operating_income": 6610000000000.0,
                "net_income": 6750000000000.0,
                "eps": 980.0,
                "shares_outstanding": 5969782550.0,
                "dividend_per_share": 361.0,
                "book_value": 52000.0,
            },
            {
                "symbol": "000660",
                "date": "2024-03-31",
                "revenue": 12430000000000.0,
                "operating_income": 2886000000000.0,
                "net_income": 1917000000000.0,
                "eps": 2640.0,
                "shares_outstanding": 728002365.0,
                "dividend_per_share": 300.0,
                "book_value": 85000.0,
            }
        ])

        self.storage.save_fundamentals(df_fund)
        self.assertTrue(self.storage.fundamentals_exist("005930"))
        self.assertTrue(self.storage.fundamentals_exist("000660"))

        res_single = self.storage.get_fundamentals("005930")
        self.assertEqual(len(res_single), 1)
        self.assertAlmostEqual(res_single.iloc[0]["operating_income"], 6610000000000.0)

        res_batch = self.storage.get_all_fundamentals(["005930", "000660"])
        self.assertEqual(len(res_batch), 2)

    def test_pipeline_stage_logging(self):
        with self.storage.pipeline_stage("test_stage"):
            pass

        # Verify record in DB
        with self.storage._connect() as conn:
            cursor = conn.execute("SELECT stage, status FROM pipeline_runs WHERE stage = ?", ("test_stage",))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "test_stage")
            self.assertEqual(row[1], "SUCCESS")

    def test_market_baselines(self):
        df_base = pd.DataFrame(
            [{"market_cap_sum": 1e12, "floating_value_sum": 5e11, "volume_sum": 1e9}],
            index=["2024-01-02"]
        )
        self.storage.save_daily_global_market_baselines("KOSPI", df_base)
        retrieved = self.storage.get_daily_global_market_baselines("KOSPI")
        self.assertFalse(retrieved.empty)
        self.assertIn("2024-01-02", retrieved.index)


    def test_pipeline_run_history_and_comparison(self):
        # 1. Start run 1
        r1_id = self.storage.start_pipeline_run(trigger_type="schedule", git_sha="abc123456")
        self.assertTrue(r1_id.startswith("run_"))

        # Save run 1 ensemble history
        df1 = pd.DataFrame([
            {'symbol': '005930', 'ensemble_score': 0.85, 'net_expected_return': 0.05, 'regime': 'Bullish-LowVol', 'reg_score': 0.8, 'surge_score': 0.7, 'portfolio_weight': 0.05},
            {'symbol': '000660', 'ensemble_score': 0.80, 'net_expected_return': 0.04, 'regime': 'Bullish-LowVol', 'reg_score': 0.75, 'surge_score': 0.65, 'portfolio_weight': 0.04},
            {'symbol': '035420', 'ensemble_score': 0.75, 'net_expected_return': 0.03, 'regime': 'Bullish-LowVol', 'reg_score': 0.7, 'surge_score': 0.6, 'portfolio_weight': 0.03},
        ])
        self.storage.save_ensemble_history(r1_id, df1, date_str="2026-08-12")
        self.storage.save_strategy_weights(r1_id, {'regression': 0.15, 'surge': 0.10}, regime="Bullish-LowVol")
        self.storage.finish_pipeline_run(r1_id, status="SUCCESS", markets=["KOSPI"], total_symbols=3, duration_seconds=120.0, regime_detected="Bullish-LowVol")

        # 2. Start run 2
        r2_id = self.storage.start_pipeline_run(trigger_type="manual", git_sha="def789012")
        self.assertNotEqual(r1_id, r2_id)

        df2 = pd.DataFrame([
            {'symbol': '005930', 'ensemble_score': 0.89, 'net_expected_return': 0.06, 'regime': 'Bullish-MidVol', 'reg_score': 0.82, 'surge_score': 0.75, 'portfolio_weight': 0.06}, # Improved score
            {'symbol': 'AAPL', 'ensemble_score': 0.82, 'net_expected_return': 0.045, 'regime': 'Bullish-MidVol', 'reg_score': 0.80, 'surge_score': 0.70, 'portfolio_weight': 0.05}, # New entry
            {'symbol': '000660', 'ensemble_score': 0.78, 'net_expected_return': 0.035, 'regime': 'Bullish-MidVol', 'reg_score': 0.70, 'surge_score': 0.60, 'portfolio_weight': 0.03}, # Dropped rank
        ])
        self.storage.save_ensemble_history(r2_id, df2, date_str="2026-08-13")
        self.storage.save_strategy_weights(r2_id, {'regression': 0.12, 'surge': 0.12}, regime="Bullish-MidVol")
        self.storage.finish_pipeline_run(r2_id, status="SUCCESS", markets=["KOSPI", "SP500"], total_symbols=3, duration_seconds=130.0, regime_detected="Bullish-MidVol")

        # 3. Test previous_run_id helper
        prev_id = self.storage.get_previous_run_id(r2_id)
        self.assertEqual(prev_id, r1_id)

        # 4. Compare runs
        cmp_dict = self.storage.compare_runs(r1_id, r2_id, top_n=3)
        self.assertEqual(cmp_dict['run_id_1'], r1_id)
        self.assertEqual(cmp_dict['run_id_2'], r2_id)

        # AAPL should be NEW
        new_entry_syms = [x['symbol'] for x in cmp_dict['top_n_changes'] if x['status'] == 'NEW']
        self.assertIn('AAPL', new_entry_syms)

        # 035420 should be in exited_entries
        self.assertIn('035420', cmp_dict['exited_entries'])

        # Check formatted report text
        report = self.storage.generate_comparison_report(cmp_dict)
        self.assertIn("Pipeline Run Comparison Report", report)
        self.assertIn("005930", report)
        self.assertIn("AAPL", report)
        self.assertIn("NEW", report)

    def test_prune_old_history(self):
        r_old = self.storage.start_pipeline_run(trigger_type="schedule")
        # Manually set run_date to 200 days ago
        with self.storage._write_lock:
            with self.storage._connect() as conn:
                conn.execute("UPDATE pipeline_run_history SET run_date = '2025-01-01' WHERE run_id = ?", (r_old,))
                conn.commit()

        r_new = self.storage.start_pipeline_run(trigger_type="schedule")

        self.storage.prune_old_history(keep_days=180)

        with self.storage._connect() as conn:
            old_count = conn.execute("SELECT COUNT(*) FROM pipeline_run_history WHERE run_id = ?", (r_old,)).fetchone()[0]
            new_count = conn.execute("SELECT COUNT(*) FROM pipeline_run_history WHERE run_id = ?", (r_new,)).fetchone()[0]
            self.assertEqual(old_count, 0)
            self.assertEqual(new_count, 1)


if __name__ == "__main__":
    unittest.main()

