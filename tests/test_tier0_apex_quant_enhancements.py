import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk.rough_volatility import RoughVolatilityEstimator
from src.analysis.macro_yield_curve import NelsonSiegelYieldCurveEngine
from src.execution.cross_impact import CrossAssetImpactEngine
from src.risk.spectral_covariance import NonLinearSpectralCovarianceEngine
from src.execution.smart_order_router import SmartOrderRouter


class TestTier0ApexQuantEnhancements(unittest.TestCase):

    def setUp(self):
        self.rough_vol = RoughVolatilityEstimator(hurst_parameter=0.10)
        self.yield_curve = NelsonSiegelYieldCurveEngine()
        self.cross_impact = CrossAssetImpactEngine()
        self.spectral_cov = NonLinearSpectralCovarianceEngine()
        self.sor = SmartOrderRouter()

    # -------------------------------------------------------------------------
    # 1. Rough Fractional Volatility & Bates Jump-Diffusion
    # -------------------------------------------------------------------------
    def test_rough_volatility_and_jump_detection(self):
        """Verify RoughVolatilityEstimator captures jumps and fractional volatility scaling."""
        np.random.seed(42)
        # Normal returns with sudden 4-sigma jump on last day
        rets = np.random.normal(0, 0.01, 30)
        rets[-1] = -0.06  # Flash shock

        jump_res = self.rough_vol.detect_poisson_jumps(rets)
        self.assertTrue(jump_res["has_jump"])
        self.assertGreater(jump_res["jump_magnitude"], 0.05)

        # Rough volatility forecast should spike immediately
        forecast_vol = self.rough_vol.forecast_rough_volatility(rets, current_volatility=0.15)
        self.assertGreater(forecast_vol, 0.15)

        # Deleveraging factor should scale down capital
        deleveraging = self.rough_vol.compute_rough_deleveraging_factor(rets, target_annual_vol=0.12)
        self.assertLess(deleveraging, 0.80)
        self.assertGreaterEqual(deleveraging, 0.15)

    # -------------------------------------------------------------------------
    # 2. Nelson-Siegel Yield Curve Macro Regime Engine
    # -------------------------------------------------------------------------
    def test_nelson_siegel_macro_regime_prediction(self):
        """Verify NelsonSiegelYieldCurveEngine fits term structure and predicts recession pivots."""
        # Inverted yield curve: 3M = 5.2%, 2Y = 4.8%, 10Y = 4.0%, 30Y = 4.2%
        yields_dict = {"3m": 5.20, "2y": 4.80, "5y": 4.20, "10y": 4.00, "30y": 4.20}
        
        fit_res = self.yield_curve.predict_macro_regime_transition(
            yield_curve_dict=yields_dict,
            previous_slope=0.20
        )

        self.assertIn("macro_regime", fit_res)
        self.assertIn("LATE_CYCLE_INVERSION", fit_res["macro_regime"])
        self.assertGreaterEqual(fit_res["recession_probability"], 0.60)
        self.assertLessEqual(fit_res["defensive_tilt_mult"], 0.75)

    # -------------------------------------------------------------------------
    # 3. Multi-Asset Cross-Impact Propagator Engine
    # -------------------------------------------------------------------------
    def test_cross_asset_impact_basket_calculation(self):
        """Verify CrossAssetImpactEngine calculates compound thematic basket impact."""
        # 3 semiconductor stocks with high mutual correlation
        orders = {"005930": 500_000_000.0, "000660": 500_000_000.0, "042700": 200_000_000.0}
        adv_map = {"005930": 10_000_000_000.0, "000660": 10_000_000_000.0, "042700": 2_000_000_000.0}
        vol_map = {"005930": 0.02, "000660": 0.025, "042700": 0.035}
        corr = np.array([
            [1.0, 0.80, 0.75],
            [0.80, 1.0, 0.70],
            [0.75, 0.70, 1.0]
        ])

        impact_res = self.cross_impact.compute_basket_price_impact(
            order_values_krw=orders,
            adv_map=adv_map,
            vol_map=vol_map,
            correlation_matrix=corr
        )

        self.assertGreater(impact_res["total_impact_bps"], 0.0)
        # Cross-impact should be amplified due to correlation
        self.assertGreater(impact_res["cross_impact_multiplier"], 1.0)
        self.assertEqual(len(impact_res["per_symbol_impact_bps"]), 3)

    # -------------------------------------------------------------------------
    # 4. Non-Linear Spectral Covariance Denoising (Ledoit-Péché)
    # -------------------------------------------------------------------------
    def test_nonlinear_spectral_covariance_denoising(self):
        """Verify NonLinearSpectralCovarianceEngine filters eigenvalues and computes shrunk weights."""
        np.random.seed(42)
        T, N = 60, 10
        # Simulated returns matrix
        rets = np.random.normal(0, 0.015, (T, N))
        df_rets = pd.DataFrame(rets, columns=[f"SYM_{i}" for i in range(N)])

        clean_cov = self.spectral_cov.denoise_covariance_matrix(df_rets)
        self.assertEqual(clean_cov.shape, (N, N))
        # Symmetric positive semi-definite check
        self.assertTrue(np.allclose(clean_cov, clean_cov.T))
        evals = np.linalg.eigvalsh(clean_cov)
        self.assertTrue((evals >= -1e-6).all())

        # Optimal weights check
        mu = pd.Series(np.random.uniform(0.05, 0.20, N), index=df_rets.columns)
        weights = self.spectral_cov.compute_spectral_shrunk_weights(mu, df_rets)
        self.assertEqual(len(weights), N)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=4)

    # -------------------------------------------------------------------------
    # 5. Smart Order Router (SOR) Lit/Dark Split Execution
    # -------------------------------------------------------------------------
    def test_smart_order_router_lit_dark_split(self):
        """Verify SmartOrderRouter splits patient orders into ATS Midpoint and Maker legs."""
        order_plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "execution_strategy": "MIDPOINT_PEG"
        }

        routed = self.sor.route_order(order_plan, ats_available=True, market_spread_bps=20.0)
        self.assertEqual(routed["symbol"], "005930")
        self.assertEqual(routed["total_quantity"], 1000)
        self.assertGreater(len(routed["legs"]), 1)
        
        # Check that Dark ATS Midpoint probe is priority 1
        leg_types = [leg["venue_type"] for leg in routed["legs"]]
        self.assertIn("DARK_ATS_MIDPOINT", leg_types)
        self.assertIn("PRIMARY_EXCHANGE_MAKER", leg_types)
        # Expected cost savings should be positive
        self.assertGreater(routed["expected_cost_saving_bps"], 0.0)


if __name__ == "__main__":
    unittest.main()
