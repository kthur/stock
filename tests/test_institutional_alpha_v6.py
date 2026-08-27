import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk.cppi_allocator import CPPIDrawdownCushionEngine
from src.data_layer.total_return import TotalReturnEngine
from src.execution.hawkes_vpin import HawkesVPINToxicityGate
from src.analysis.particle_filter_regime import BayesianSMCParticleFilter


class TestInstitutionalAlphaV6(unittest.TestCase):

    def setUp(self):
        self.cppi = CPPIDrawdownCushionEngine(max_tolerable_drawdown=0.06, cppi_multiplier=4.0)
        self.tri_engine = TotalReturnEngine()
        self.vpin_gate = HawkesVPINToxicityGate(vpin_toxic_threshold=0.65)
        self.smc_filter = BayesianSMCParticleFilter(n_particles=300)

    # -------------------------------------------------------------------------
    # 1. CPPI Drawdown Cushion Allocator
    # -------------------------------------------------------------------------
    def test_cppi_cushion_and_exposure_scaling(self):
        """Verify CPPI calculates floor, cushion, and asymmetric exposure."""
        peak_nav = 100_000_000.0
        # Scenario 1: Normal NAV near peak
        curr_nav = 98_000_000.0
        cushion_res = self.cppi.compute_cushion(curr_nav, peak_nav)
        self.assertGreater(cushion_res["cushion"], 0.0)
        self.assertEqual(cushion_res["floor_nav"], 94_000_000.0) # 1 - 0.06 = 94%

        exp_normal = self.cppi.calculate_asymmetric_exposure(
            expected_return_annual=0.15,
            annual_volatility=0.10,
            current_nav=curr_nav,
            peak_nav=peak_nav
        )
        self.assertFalse(exp_normal["is_floor_breached"])
        self.assertGreater(exp_normal["target_gross_exposure"], 0.35)

        # Scenario 2: Deep drawdown breaching cushion buffer
        crashed_nav = 94_200_000.0
        exp_crash = self.cppi.calculate_asymmetric_exposure(
            expected_return_annual=0.15,
            annual_volatility=0.10,
            current_nav=crashed_nav,
            peak_nav=peak_nav
        )
        self.assertTrue(exp_crash["is_floor_breached"])
        self.assertEqual(exp_crash["target_gross_exposure"], 0.0)
        self.assertEqual(exp_crash["cash_weight"], 1.0)

        # Volatility drag estimation
        drag_bps = self.cppi.calculate_volatility_drag_loss(annual_volatility=0.20, leverage=1.50)
        self.assertGreater(drag_bps, 0.0)

    # -------------------------------------------------------------------------
    # 2. Total Return Index & Dividend Capture Alpha
    # -------------------------------------------------------------------------
    def test_total_return_series_and_dividend_capture(self):
        """Verify Total Return Index reconstructs cash dividends and captures ex-date mean reversion."""
        prices = pd.Series([100.0, 102.0, 98.0, 99.0, 101.0])
        # On day index 2, stock pays 4.0 dividend and drops from 102 to 98
        dividends = pd.Series([0.0, 0.0, 4.0, 0.0, 0.0])

        tri_series = self.tri_engine.build_total_return_series(prices, dividends)
        self.assertEqual(len(tri_series), 5)
        # Raw price is down on day 2 (98 vs 102), but TRI should stay flat or positive (102.0)
        self.assertGreaterEqual(tri_series.iloc[2], tri_series.iloc[1] * 0.99)

        # False breakdown detection
        raw_drop = pd.Series([100.0, 96.0]) # -4%
        tri_flat = pd.Series([100.0, 100.0]) # +0%
        is_false = self.tri_engine.filter_false_breakdown_signals(raw_drop, tri_flat)
        self.assertTrue(is_false)

        # Dividend capture score
        cap_score = self.tri_engine.compute_dividend_capture_score(
            dividend_yield=0.06,
            days_to_ex_date=0
        )
        self.assertTrue(cap_score["in_capture_window"])
        self.assertGreater(cap_score["dividend_capture_score"], 0.70)

    # -------------------------------------------------------------------------
    # 3. Hawkes Process & VPIN Order Flow Toxicity Gate
    # -------------------------------------------------------------------------
    def test_hawkes_vpin_toxicity_gating(self):
        """Verify Hawkes VPIN computes toxicity and cancels passive limit pegging during aggressive sweeps."""
        # 1. Benign balanced flow
        b_benign = [1000, 1200, 1100, 950, 1050]
        s_benign = [1050, 1150, 1050, 1000, 1000]
        benign_eval = self.vpin_gate.evaluate_order_flow_toxicity(
            buy_volumes=b_benign,
            sell_volumes=s_benign,
            order_plan={"execution_strategy": "MIDPOINT_PEG"}
        )
        self.assertFalse(benign_eval["is_toxic_flow"])
        self.assertFalse(benign_eval["cancel_passive_peg"])
        self.assertEqual(benign_eval["recommended_strategy"], "MIDPOINT_PEG")

        # 2. Heavy toxic sell sweep (huge sell imbalances)
        b_toxic = [100, 150, 80, 120, 90]
        s_toxic = [5000, 8000, 12000, 9000, 11000]
        toxic_eval = self.vpin_gate.evaluate_order_flow_toxicity(
            buy_volumes=b_toxic,
            sell_volumes=s_toxic,
            order_plan={"execution_strategy": "MIDPOINT_PEG"}
        )
        self.assertTrue(toxic_eval["is_toxic_flow"])
        self.assertTrue(toxic_eval["cancel_passive_peg"])
        self.assertEqual(toxic_eval["recommended_strategy"], "DEFENSIVE_VWAP")

    # -------------------------------------------------------------------------
    # 4. Bayesian SMC Continuous Particle Filter
    # -------------------------------------------------------------------------
    def test_bayesian_smc_particle_filter(self):
        """Verify SMC particle filter updates continuous mu, sigma, and crisis probability."""
        np.random.seed(42)
        # 20 days of severe negative returns (crash scenario)
        crash_rets = np.random.normal(-0.03, 0.025, 20)
        
        filter_res = self.smc_filter.filter_returns_stream(crash_rets)
        self.assertIn("filtered_expected_return", filter_res)
        self.assertIn("filtered_volatility", filter_res)
        self.assertIn("crisis_probability", filter_res)
        
        # Volatility should have adjusted upward and crisis probability should be high
        self.assertGreater(filter_res["filtered_volatility"], 0.20)
        self.assertGreater(filter_res["crisis_probability"], 0.50)


if __name__ == "__main__":
    unittest.main()
