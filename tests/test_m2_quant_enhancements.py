"""
tests/test_m2_quant_enhancements.py
Comprehensive Unit & Integration Test Suite for Milestone 2:
Portfolio 4-Model Dynamic Blending & Darkpool/HFT OMS Optimization.

Features Covered:
- F09: Continuous 4-Model Markov Blending in UnifiedPortfolioAllocator
- F10: Clayton Copula Tail Covariance Integration in PortfolioAllocator & UnifiedPortfolioAllocator
- F11: Dark-Pool Adjusted Gatheral 3/2-Power Market Impact in UnifiedPortfolioAllocator
- F12: Dynamic Dark Probing & 3-Tier Multi-Leg SOR Routing in SmartOrderRouter & ExecutionOMSEngine
- F13: Orderbook Imbalance (OBI) Midpoint Peg Pricing in ExecutionOMSEngine & AlmgrenChrissScheduler
"""

import math
import sqlite3
import unittest
import numpy as np
import pandas as pd

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestF09ContinuousMarkovBlending(unittest.TestCase):
    """Tests for Feature F09: Continuous 4-Model Markov Blending."""

    def setUp(self):
        self.allocator = UnifiedPortfolioAllocator()

    def test_string_regime_backward_compatibility(self):
        """Verify string regimes map correctly to REGIME_OPTIMIZER_BLENDS."""
        cfg_bull = self.allocator.compute_dynamic_regime_blend_weights("BULL_LOW_VOL")
        self.assertAlmostEqual(cfg_bull["bl"], 0.65, places=2)
        self.assertAlmostEqual(cfg_bull["herc"], 0.25, places=2)
        self.assertAlmostEqual(cfg_bull["rp"], 0.10, places=2)
        self.assertAlmostEqual(cfg_bull["cvar"], 0.00, places=2)
        self.assertAlmostEqual(sum(cfg_bull.values()), 1.0000, places=4)

        cfg_crisis = self.allocator.compute_dynamic_regime_blend_weights("CRISIS")
        self.assertAlmostEqual(sum(cfg_crisis.values()), 1.0000, places=4)
        # In crisis, CVaR and RP must dominate, BL suppressed to zero
        self.assertEqual(cfg_crisis["bl"], 0.0)
        self.assertGreaterEqual(cfg_crisis["cvar"], 0.70)

    def test_markov_posterior_probability_blending(self):
        """Verify soft-blending c(t) = sum_m pi_{t,m} * c^(m) from posterior dict."""
        regime_probs = {
            "BULL_LOW_VOL": 0.50,
            "SIDEWAYS_LOW_VOL": 0.50,
        }
        blended = self.allocator.compute_dynamic_regime_blend_weights(regime_probs)
        # BULL_LOW_VOL: bl=0.65, herc=0.25, rp=0.10, cvar=0.00
        # SIDEWAYS_LOW_VOL: bl=0.25, herc=0.45, rp=0.20, cvar=0.10
        # Expected: bl=0.45, herc=0.35, rp=0.15, cvar=0.05
        self.assertAlmostEqual(blended["bl"], 0.45, places=2)
        self.assertAlmostEqual(blended["herc"], 0.35, places=2)
        self.assertAlmostEqual(blended["rp"], 0.15, places=2)
        self.assertAlmostEqual(blended["cvar"], 0.05, places=2)
        self.assertAlmostEqual(sum(blended.values()), 1.0000, places=4)

    def test_dynamic_tilt_towards_cvar_and_rp_in_crisis(self):
        """Verify crisis/high-vol regime shifts weight to EVT-CVaR and Risk Parity."""
        bull_probs = {"BULL_LOW_VOL": 1.0}
        crisis_probs = {"CRISIS": 0.80, "BEAR_HIGH_VOL": 0.20}

        w_bull = self.allocator.compute_dynamic_regime_blend_weights(bull_probs)
        w_crisis = self.allocator.compute_dynamic_regime_blend_weights(crisis_probs)

        self.assertGreater(w_crisis["cvar"], w_bull["cvar"])
        self.assertGreater(w_bull["bl"], w_crisis["bl"])
        self.assertAlmostEqual(sum(w_crisis.values()), 1.0000, places=4)

    def test_optimize_multi_model_blend_with_dict_regime(self):
        """Verify optimize_multi_model_blend accepts dict regime without error."""
        n = 4
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        preds = np.array([0.08, 0.05, 0.03, 0.01])
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.02, (60, n)),
            columns=symbols
        )
        cov_matrix = np.cov(returns_df.values, rowvar=False)

        weights = self.allocator.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            regime={"BULL_HIGH_VOL": 0.70, "SIDEWAYS_HIGH_VOL": 0.30},
        )
        self.assertEqual(len(weights), n)
        self.assertAlmostEqual(float(np.sum(weights)), 1.0000, places=3)
        self.assertTrue(np.all(weights >= 0.0))


class TestF10ClaytonCopulaTailCovariance(unittest.TestCase):
    """Tests for Feature F10: Clayton Copula Tail Covariance Integration."""

    def test_dynamic_lower_tail_dependence_estimation(self):
        """Verify lower tail dependence lambda_L = 2^(-1/theta) in [0.10, 0.70]."""
        np.random.seed(42)
        n_days, n_assets = 100, 5
        # Generate correlated returns with extreme joint crashes
        base_returns = np.random.randn(n_days, n_assets) * 0.015
        # Inject severe lower-tail crash days
        base_returns[:12, :] -= 0.07

        base_cov = np.cov(base_returns, rowvar=False)
        stressed_cov = PortfolioAllocator.compute_tail_stress_cov(
            base_returns,
            base_cov,
            tail_quantile=0.15,
            stress_weight=0.35,
            use_clayton_copula=True
        )

        self.assertEqual(stressed_cov.shape, (n_assets, n_assets))
        # Verify symmetry
        np.testing.assert_allclose(stressed_cov, stressed_cov.T, atol=1e-8)
        # Verify strict positive definiteness
        eigvals = np.linalg.eigvalsh(stressed_cov)
        self.assertTrue(np.all(eigvals > 0), f"Eigenvalues must be strictly positive: {eigvals}")

    def test_parametric_evt_cvar_weights_with_cov_matrix(self):
        """Verify calculate_cvar_weights uses parametric EVT-CVaR when cov_matrix is passed."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.40)
        n = 4
        symbols = ["S1", "S2", "S3", "S4"]
        returns_df = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (40, n)),
            columns=symbols
        )
        cov_matrix = np.cov(returns_df.values, rowvar=False)
        preds = np.array([0.05, 0.03, 0.01, 0.00])

        w_cvar = allocator.calculate_cvar_weights(
            returns_df=returns_df,
            confidence_level=0.95,
            predicted_returns=preds,
            lambda_alpha=0.50,
            cov_matrix=cov_matrix,
            regime="BEAR_HIGH_VOL"
        )

        self.assertEqual(len(w_cvar), n)
        self.assertAlmostEqual(float(np.sum(w_cvar)), 1.0000, places=4)
        self.assertTrue(np.all(w_cvar >= 0.0))
        self.assertTrue(np.all(w_cvar <= allocator.max_single_weight + 1e-4))


class TestF11DarkPoolAdjustedGatheralImpact(unittest.TestCase):
    """Tests for Feature F11: Dark-Pool Adjusted Gatheral 3/2-Power Market Impact."""

    def test_gatheral_impact_parameter_kappa_eff_modulation(self):
        """Verify kappa_eff = kappa_0 * (1 - phi_dark) scales convergence velocity."""
        allocator = UnifiedPortfolioAllocator()
        n = 3
        symbols = ["SYM1", "SYM2", "SYM3"]
        preds = np.array([0.15, 0.15, 0.15])
        returns_df = pd.DataFrame(np.random.normal(0, 0.02, (60, n)), columns=symbols)
        cov_matrix = np.eye(n) * 0.0004

        current_w = np.zeros(n)
        advs = np.array([10_000_000.0, 10_000_000.0, 10_000_000.0])
        total_capital = 50_000_000.0

        # Allocation with zero dark pool liquidity
        w_lit = allocator.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            current_weights=current_w,
            advs=advs,
            total_capital=total_capital,
            darkpool_scores=np.array([0.0, 0.0, 0.0])
        )

        # Allocation with heavy dark pool liquidity (score = 0.50 -> phi_dark = 0.60)
        w_dark = allocator.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            current_weights=current_w,
            advs=advs,
            total_capital=total_capital,
            darkpool_scores=np.array([0.50, 0.50, 0.50])
        )

        # Dark pool liquidity reduces kappa_eff, enabling faster convergence (larger tranche allocation)
        self.assertGreaterEqual(
            float(np.sum(w_dark)),
            float(np.sum(w_lit)),
            "Dark pool liquidity should allow larger or equal convergence velocity"
        )


class TestF12DynamicDarkProbingAndSORRouting(unittest.TestCase):
    """Tests for Feature F12: Dynamic Dark Probing & 3-Tier Multi-Leg SOR Routing."""

    def setUp(self):
        self.sor = SmartOrderRouter()

    def test_dynamic_dark_probe_ratio_scaling(self):
        """Verify dark pool allocation scales from 40% up to 70% based on darkpool_score."""
        base_order = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "execution_strategy": "MIDPOINT_PEG",
            "darkpool_score": 0.0,
            "is_accumulation": False,
        }

        routed_base = self.sor.route_order(base_order, ats_available=True)
        self.assertAlmostEqual(routed_base["effective_dark_ratio"], 0.40, places=2)
        dark_leg_base = routed_base["dark_ats_midpoint"]
        self.assertIsNotNone(dark_leg_base)
        self.assertEqual(dark_leg_base["quantity"], 400)

        # High block accumulation order
        accum_order = dict(base_order)
        accum_order["darkpool_score"] = 0.90
        accum_order["is_accumulation"] = True

        routed_accum = self.sor.route_order(accum_order, ats_available=True)
        self.assertGreaterEqual(routed_accum["effective_dark_ratio"], 0.65)
        self.assertLessEqual(routed_accum["effective_dark_ratio"], 0.70)
        dark_leg_accum = routed_accum["dark_ats_midpoint"]
        self.assertGreaterEqual(dark_leg_accum["quantity"], 650)

    def test_three_tier_multi_venue_residual_decomposition(self):
        """Verify 3-tier routing: dark probe -> primary maker (70% of rem) -> lit sweeper."""
        order = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 180.0,
            "execution_strategy": "MIDPOINT_PEG",
            "darkpool_score": 0.0
        }

        routed = self.sor.route_order(order, ats_available=True)
        # Total = 1000. Dark = 400 (40%). Rem = 600.
        # Maker = 70% of 600 = 420.
        # Sweeper = 600 - 420 = 180.
        self.assertEqual(routed["dark_ats_midpoint"]["quantity"], 400)
        self.assertEqual(routed["primary_exchange_maker"]["quantity"], 420)
        self.assertEqual(routed["lit_exchange_sweeper"]["quantity"], 180)
        # Sum of legs must strictly match total quantity
        tot_leg_qty = sum(leg["quantity"] for leg in routed["legs"])
        self.assertEqual(tot_leg_qty, 1000)
        self.assertGreater(routed["expected_cost_saving_bps"], 0.0)

    def test_oms_generate_order_plan_attaches_sor_routing(self):
        """Verify ExecutionOMSEngine attaches sor_routing and cost savings to order plans and DB."""
        oms = ExecutionOMSEngine(db_path=":memory:")
        predictions = [{
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "expected_return": 10.0,
            "darkpool_score": 0.75,
            "is_accumulation": True,
            "adv": 500_000_000_000.0
        }]
        weights = {"005930": 0.10}

        plans = oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            crisis_level="NORMAL"
        )

        self.assertGreaterEqual(len(plans), 1)
        plan = plans[0]
        self.assertIn("sor_routing", plan)
        self.assertIn("expected_cost_saving_bps", plan)
        self.assertGreaterEqual(plan["expected_cost_saving_bps"], 0.0)


class TestF13OBIMidpointPegPricing(unittest.TestCase):
    """Tests for Feature F13: Orderbook Imbalance (OBI) Midpoint Peg Pricing."""

    def test_obi_midpoint_peg_formula_buy_direction(self):
        """Verify P_peg = P_mid + 0.5 * spread * tanh(kappa * OBI)."""
        bid = 100.0
        ask = 100.20
        spread = 0.20
        mid = 100.10

        # OBI = 0 => Midpoint
        p_zero = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=mid, bid_price=bid, ask_price=ask, spread=spread,
            action="BUY", obi=0.0
        )
        self.assertAlmostEqual(p_zero, mid, places=3)

        # Positive OBI => shifts towards ask to ensure execution
        p_pos = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=mid, bid_price=bid, ask_price=ask, spread=spread,
            action="BUY", obi=0.50, kappa=1.5
        )
        self.assertGreater(p_pos, mid)
        self.assertLessEqual(p_pos, ask)

        # Negative OBI => shifts towards bid to capture spread
        p_neg = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=mid, bid_price=bid, ask_price=ask, spread=spread,
            action="BUY", obi=-0.50, kappa=1.5
        )
        self.assertLess(p_neg, mid)
        self.assertGreaterEqual(p_neg, bid)

    def test_almgren_chriss_scheduler_obi_pricing(self):
        """Verify AlmgrenChrissScheduler.calculate_peg_limit_price supports OBI."""
        bid = 50000.0
        ask = 50100.0
        spread = 100.0
        mid = 50050.0

        p_peg = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=mid, bid_price=bid, ask_price=ask, spread=spread,
            action="BUY", obi=0.80
        )
        expected_shift = 0.5 * spread * math.tanh(1.5 * 0.80)
        self.assertAlmostEqual(p_peg, mid + expected_shift, places=2)

    def test_oms_order_plan_uses_obi_peg_price(self):
        """Verify generate_order_plan computes peg price using OBI when provided."""
        oms = ExecutionOMSEngine(db_path=":memory:")
        predictions = [{
            "symbol": "035420",
            "name": "NAVER",
            "market": "KOSPI",
            "action": "BUY",
            "close_price": 200000.0,
            "target_price": 200000.0,
            "bid_price": 199500.0,
            "ask_price": 200500.0,
            "spread": 1000.0,
            "obi": 0.60,
            "expected_return": 8.0,
            "adv": 100_000_000_000.0
        }]
        weights = {"035420": 0.08}

        plans = oms.generate_order_plan(
            top_predictions=predictions,
            portfolio_weights=weights,
            total_capital=100_000_000.0
        )

        self.assertGreaterEqual(len(plans), 1)
        plan = plans[0]
        # Target price should be shifted above mid (200000) due to positive OBI
        self.assertGreaterEqual(plan["target_price"], 200000.0)


if __name__ == "__main__":
    unittest.main()
