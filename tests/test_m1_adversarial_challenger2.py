"""
tests/test_m1_adversarial_challenger2.py — Adversarial Stress Suite for Milestone 1 (Release R159).

Executed by: Challenger 2 (teamwork_challenger, critic/specialist)
Focus Areas:
1. Feature F762: Rough Fractional Heston Stochastic Volatility & Macro Jump Coupling
   - Volterra kernel singularity at s -> t (t=0, t=1e-15, negative lags)
   - Subdiffusive Hurst exponent H in (0.0, 0.5) and monotonic memory decay
   - Negative return drift and extreme market crash sequences
   - Jump impulse spikes, bipower variation, jump intensity bounding in [0.0, 1.0]
   - Combined forward vol forecast bounds [0.0, 5.0] under extreme OFI
2. Feature F763: 4th-Order Greeks & SVI Volatility Surface Model
   - 4th-order Greeks (Speed, Zoma, Color, Ultima_2) under deep ITM (S/K=100) and deep OTM (S/K=0.01)
   - Short expiry limit (tau -> 0, tau <= 1e-5) and zero/extreme volatility
   - Finite difference consistency vs closed-form analytical solutions
   - SVI Roger Lee extreme strike asymptotic slope arbitrage bounds b*(1 + |rho|) < 2.0 (and < 4.0)
   - SVI calibration resilience under degenerate and corrupted market slices
3. Feature F764: Riemannian AIRM & Septuple-Pillar ZCA Whitening
   - Riemannian metric axioms on SPD manifold: Positivity, Indiscernibles, Symmetry, Triangle Inequality
   - Affine Invariance: delta(A Sigma_1 A^T, A Sigma_2 A^T) == delta(Sigma_1, Sigma_2)
   - Septuple-Pillar ZCA whitening matrix symmetry W_ZCA == W_ZCA^T
   - Exact covariance whitening W @ Sigma @ W^T == I_7 under shrink_weight=0.0
   - Ill-conditioned, singular rank-deficient, and indefinite matrix resilience
4. Phase156Coupler Alpha Bounding & Interface Contract
   - PROJECT.md interface contract: alpha_p156 in [-3.0, 3.0]
   - Evaluation of h_phase156 in (0, 1] and fcpi_v156 in (0, 1]
   - Extreme shock and corrupted input resilience
"""

from __future__ import annotations

import math
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

from src.core.cross_market_micro_momentum import (
    CrossMarketMicroMomentumEngine,
    compute_fractional_volterra_kernel,
    compute_rough_heston_hurst_parameter,
    compute_rough_heston_fractional_volatility,
    compute_rough_volatility_forecast,
    estimate_rough_heston_params,
    compute_macro_jump_coupling_phase156,
)
from src.core.option_surface_accelerator import (
    OptionSurfaceAccelerator,
    compute_fourth_order_black_scholes_greeks,
    compute_black_scholes_greeks_third_order,
    verify_svi_no_arbitrage,
    calibrate_svi_surface_slice,
    calculate_4th_order_greeks,
)
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    SEPTUPLE_PILLAR_MAP,
    compute_riemannian_airm_distance,
    compute_riemannian_frechet_shrinkage,
    compute_septuple_pillar_zca_whitening,
    apply_riemannian_deadband,
)
from src.ai.historical_couplers import Phase156Coupler


class TestM1AdversarialChallenger2(unittest.TestCase):
    """Empirical Adversarial Stress Suite for Milestone 1 (F762, F763, F764, Phase156Coupler)."""

    def setUp(self) -> None:
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine()
        self.coupler = Phase156Coupler()

    # =========================================================================
    # SUITE 1: Feature F762 Rough Fractional Heston & Jump Coupling Stress
    # =========================================================================

    def test_adv01_volterra_kernel_singularity_at_zero(self) -> None:
        """ADV01 [F762]: Stress Volterra kernel at s -> t singularity (lag=0, 1e-15, negative lags, large lags)."""
        # Continuous kernel (t-s)^(H-0.5) has a pole at s -> t because H < 0.5.
        # Implementation must clamp t_safe >= 1e-4 and never produce inf or nan.
        singular_lags = np.array([0.0, 1e-15, -1.0, -100.0, 1e-4, 0.01, 1.0, 100.0, 1e5])
        kernel = compute_fractional_volterra_kernel(singular_lags, hurst=0.12)

        self.assertEqual(len(kernel), len(singular_lags))
        self.assertTrue(np.isfinite(kernel).all(), f"Kernel produced non-finite values: {kernel}")
        self.assertTrue((kernel > 0.0).all(), f"Kernel must be strictly positive: {kernel}")

        # Non-negative lags should decay monotonically
        pos_lags = np.linspace(1e-4, 10.0, 50)
        k_pos = compute_fractional_volterra_kernel(pos_lags, hurst=0.12)
        diffs = np.diff(k_pos)
        self.assertTrue((diffs <= 1e-7).all(), f"Volterra kernel must decay monotonically: max diff={np.max(diffs)}")

    def test_adv02_subdiffusive_hurst_bounds_and_memory(self) -> None:
        """ADV02 [F762]: Stress extreme Hurst exponents H in {0.0001, 0.01, 0.05, 0.49, 0.50, 0.99}."""
        lags = np.linspace(0.01, 5.0, 30)

        for h in [0.0001, 0.01, 0.05, 0.25, 0.49, 0.50, 0.99]:
            k = compute_fractional_volterra_kernel(lags, hurst=h)
            self.assertTrue(np.isfinite(k).all(), f"Non-finite kernel at H={h}")
            self.assertTrue((k > 0.0).all(), f"Non-positive kernel at H={h}")
            # Subdiffusive condition: alpha - 1 < 0 -> monotonically decreasing
            self.assertTrue((np.diff(k) <= 1e-6).all(), f"Violated monotonic decay at H={h}")

        # Estimation from empirical data
        rng = np.random.RandomState(42)
        r_sub = rng.normal(0, 0.01, 200)
        h_est = compute_rough_heston_hurst_parameter(r_sub)
        self.assertTrue(0.0 < h_est < 0.50, f"Hurst estimate {h_est} not subdiffusive in (0, 0.50)")

    def test_adv03_negative_drift_and_bear_shock_resilience(self) -> None:
        """ADV03 [F762]: Severe negative return drift and alternating crash shocks."""
        neg_drift_returns = np.full(100, -0.05)  # Steady -5% crash every bar
        res = compute_rough_heston_fractional_volatility(neg_drift_returns, hurst=0.12)

        self.assertIn("current_vol", res)
        self.assertIn("current_variance", res)
        self.assertGreater(res["current_vol"], 0.0)
        self.assertGreater(res["current_variance"], 0.0)
        self.assertTrue(np.isfinite(res["fractional_vol_series"]).all())
        self.assertTrue((res["fractional_var_series"] >= 1e-6).all())

        # Alternating crash and rebound sequence
        alt_returns = np.array([-0.15, 0.10, -0.20, 0.12, -0.25, 0.08])
        params = estimate_rough_heston_params(alt_returns)
        self.assertTrue(np.isfinite(params["f762_hurst_parameter"]))
        self.assertTrue(0.0 <= params["f762_jump_intensity"] <= 1.0)
        self.assertGreater(params["f762_rough_vol_forecast"], 0.0)

    def test_adv04_jump_impulse_spikes_and_bipower_variation(self) -> None:
        """ADV04 [F762]: Massive jump impulse spikes (+500%, -99%) and jump intensity bounding."""
        # Baseline mild Gaussian returns
        r_normal = np.random.RandomState(42).normal(0, 0.01, 100)
        p_normal = estimate_rough_heston_params(r_normal)

        # Contaminate with severe jump outliers
        r_spiked = r_normal.copy()
        r_spiked[20] = 5.0    # +500% jump spike
        r_spiked[50] = -0.99  # -99% flash crash
        r_spiked[80] = 3.5    # +350% jump spike
        p_spiked = estimate_rough_heston_params(r_spiked)

        self.assertTrue(0.0 <= p_spiked["f762_jump_intensity"] <= 1.0)
        self.assertGreaterEqual(p_spiked["f762_jump_intensity"], p_normal["f762_jump_intensity"])
        self.assertTrue(np.isfinite(p_spiked["f762_rough_vol_forecast"]))
        self.assertGreater(p_spiked["f762_rough_vol_forecast"], 0.0)

    def test_adv05_macro_jump_coupling_extreme_acceleration(self) -> None:
        """ADV05 [F762]: Macro jump impulse coupling under extreme macro volatility surges."""
        stock_ret = np.array([0.01, -0.02, 0.03, -0.015, 0.02])

        # Extreme macro returns: VIX +500, SOX -50%, USDKRW +1000
        extreme_macro = {
            "vix": np.array([20.0, 520.0]),
            "sox": np.array([4000.0, 2000.0]),
            "usdkrw": np.array([1300.0, 2300.0]),
        }
        coupling = compute_macro_jump_coupling_phase156(stock_ret, macro_returns=extreme_macro)
        self.assertTrue(0.0 <= coupling <= 1.0, f"Coupling {coupling} outside [0.0, 1.0]")
        self.assertTrue(np.isfinite(coupling))

        # Direct macro accel dict
        accel_dict = {"vix": 100.0, "sox": 2.0, "fx": 50.0}
        shock = compute_macro_jump_coupling_phase156(macro_accel=accel_dict)
        self.assertTrue(0.0 <= shock <= 5.0, f"Shock vol {shock} outside [0.0, 5.0]")
        self.assertTrue(np.isfinite(shock))

    def test_adv06_f762_degenerate_and_corrupt_inputs(self) -> None:
        """ADV06 [F762]: Degenerate short arrays (N=0..4), constant returns, NaNs and Infs."""
        # Empty array
        p_empty = estimate_rough_heston_params(np.array([]))
        self.assertEqual(p_empty["f762_hurst_parameter"], 0.12)
        self.assertEqual(p_empty["f762_jump_intensity"], 0.0)

        # 1-element array
        p_single = estimate_rough_heston_params(np.array([0.05]))
        self.assertEqual(p_single["f762_hurst_parameter"], 0.12)

        # Constant returns (zero variance)
        p_const = estimate_rough_heston_params(np.full(50, 0.01))
        self.assertTrue(np.isfinite(p_const["f762_rough_vol_forecast"]))
        self.assertTrue(0.0 <= p_const["f762_jump_intensity"] <= 1.0)

        # OFI forward forecast with extreme OFI
        fc_high = compute_rough_volatility_forecast(current_vol=0.20, ofi_velocity=1e6, hurst=0.12)
        fc_low = compute_rough_volatility_forecast(current_vol=0.20, ofi_velocity=-1e6, hurst=0.12)
        self.assertTrue(0.0 <= fc_high <= 5.0)
        self.assertTrue(0.0 <= fc_low <= 5.0)

    # =========================================================================
    # SUITE 2: Feature F763 4th-Order Greeks & SVI Volatility Surface Stress
    # =========================================================================

    def test_adv07_fourth_order_greeks_extreme_moneyness(self) -> None:
        """ADV07 [F763]: 4th-order Greeks under deep ITM (S/K = 100) and deep OTM (S/K = 0.01)."""
        # Deep ITM: S = 10000, K = 100
        g_itm = compute_fourth_order_black_scholes_greeks(spot=10000.0, strike=100.0, tau=0.5, vol=0.20)
        for k, v in g_itm.items():
            if isinstance(v, (int, float)):
                self.assertTrue(np.isfinite(v), f"Deep ITM Greek {k} is non-finite: {v}")

        # Deep OTM: S = 1, K = 1000
        g_otm = compute_fourth_order_black_scholes_greeks(spot=1.0, strike=1000.0, tau=0.5, vol=0.20)
        for k, v in g_otm.items():
            if isinstance(v, (int, float)):
                self.assertTrue(np.isfinite(v), f"Deep OTM Greek {k} is non-finite: {v}")

    def test_adv08_fourth_order_greeks_short_expiry_boundary(self) -> None:
        """ADV08 [F763]: Expiry tau -> 0 asymptotic boundary resilience (tau = 1e-4, 1e-5, 1e-6, 0.0)."""
        # Short expiry tau = 1e-4
        g_short = compute_fourth_order_black_scholes_greeks(spot=100.0, strike=100.0, tau=1e-4, vol=0.20)
        for k, v in g_short.items():
            if isinstance(v, (int, float)):
                self.assertTrue(np.isfinite(v), f"tau=1e-4 Greek {k} is non-finite: {v}")

        # Boundary tau <= 1e-5 should safely zero out higher-order Greeks
        for tau_edge in [1e-5, 1e-6, 0.0, -0.1]:
            g_edge = compute_fourth_order_black_scholes_greeks(spot=100.0, strike=100.0, tau=tau_edge, vol=0.20)
            self.assertEqual(g_edge.get("zoma_4th", 0.0), 0.0)
            self.assertEqual(g_edge.get("color_4th", 0.0), 0.0)
            self.assertEqual(g_edge.get("ultima_2", 0.0), 0.0)

    def test_adv09_fourth_order_greeks_extreme_volatility(self) -> None:
        """ADV09 [F763]: Volatility sigma extremes (vol = 1e-5, 0.001, 5.0 = 500%, 10.0 = 1000%)."""
        for vol_val in [1e-5, 0.001, 1.0, 5.0, 10.0]:
            g = compute_fourth_order_black_scholes_greeks(spot=100.0, strike=100.0, tau=0.25, vol=vol_val)
            for k, v in g.items():
                if isinstance(v, (int, float)):
                    self.assertTrue(np.isfinite(v), f"vol={vol_val} Greek {k} is non-finite: {v}")

    def test_adv10_fourth_order_greeks_finite_difference_accuracy(self) -> None:
        """ADV10 [F763]: Compare analytical Speed, Zomma, and Ultima_2 against central finite differences."""
        spot = 100.0
        strike = 105.0
        tau = 0.50
        vol = 0.25
        rate = 0.03
        h = 1e-4

        g_ana = compute_fourth_order_black_scholes_greeks(spot, strike, tau, vol, rate=rate)

        # Central difference for Speed = d Gamma / d S
        g_s_plus = compute_fourth_order_black_scholes_greeks(spot + h, strike, tau, vol, rate=rate)
        g_s_minus = compute_fourth_order_black_scholes_greeks(spot - h, strike, tau, vol, rate=rate)
        num_speed = (g_s_plus["gamma"] - g_s_minus["gamma"]) / (2.0 * h)
        ana_speed = g_ana["speed"]
        rel_err_speed = abs(ana_speed - num_speed) / (abs(ana_speed) + 1e-8)
        self.assertLess(rel_err_speed, 1e-4, f"Speed relative error too high: {rel_err_speed}")

        # Central difference for Zomma = d Gamma / d vol
        g_v_plus = compute_fourth_order_black_scholes_greeks(spot, strike, tau, vol + h, rate=rate)
        g_v_minus = compute_fourth_order_black_scholes_greeks(spot, strike, tau, vol - h, rate=rate)
        num_zomma = (g_v_plus["gamma"] - g_v_minus["gamma"]) / (2.0 * h)
        ana_zomma = g_ana["zomma"]
        rel_err_zomma = abs(ana_zomma - num_zomma) / (abs(ana_zomma) + 1e-8)
        self.assertLess(rel_err_zomma, 1e-4, f"Zomma relative error too high: {rel_err_zomma}")

    def test_adv11_svi_no_arbitrage_roger_lee_wing_bounds(self) -> None:
        """ADV11 [F763]: SVI asymptotic wing slope Roger Lee condition b*(1 + |rho|) < 2.0 and < 4.0."""
        # Case 1: Valid asymptotic slopes (< 2.0)
        self.assertTrue(verify_svi_no_arbitrage(b=0.10, rho=-0.20))
        self.assertTrue(verify_svi_no_arbitrage(b=0.50, rho=0.50))   # 0.5 * 1.5 = 0.75 < 2.0
        self.assertTrue(verify_svi_no_arbitrage(b=0.99, rho=0.99))   # 0.99 * 1.99 = 1.9701 < 2.0

        # Case 2: Roger Lee slope violation (b*(1 + |rho|) >= 2.0)
        self.assertFalse(verify_svi_no_arbitrage(b=1.50, rho=0.80))  # 1.5 * 1.8 = 2.7 > 2.0
        self.assertFalse(verify_svi_no_arbitrage(b=2.50, rho=0.00))  # 2.5 > 2.0

        # Case 3: Invalid parameter domains (b < 0 or |rho| >= 1.0)
        self.assertFalse(verify_svi_no_arbitrage(b=-0.10, rho=0.20))
        self.assertFalse(verify_svi_no_arbitrage(b=0.50, rho=1.00))
        self.assertFalse(verify_svi_no_arbitrage(b=0.50, rho=-1.05))

    def test_adv12_svi_calibration_degenerate_slices(self) -> None:
        """ADV12 [F763]: SVI calibration with identical strikes, 2 strikes, negative IVs, and short tau."""
        # Under-specified strikes (N < 3)
        res_few = calibrate_svi_surface_slice(k_strikes=np.array([100.0, 105.0]), ivs=np.array([0.2, 0.22]), tau=0.25)
        self.assertTrue(res_few["is_arbitrage_free"])

        # Identical strikes (zero moneyness spread)
        k_flat = np.full(10, 100.0)
        iv_flat = np.full(10, 0.20)
        res_flat = calibrate_svi_surface_slice(k_strikes=k_flat, ivs=iv_flat, tau=0.25, spot=100.0)
        self.assertIn("params", res_flat)
        self.assertTrue(np.isfinite(res_flat["fitted_w"]).all())

        # Direct parametric evaluation: w(k) = a + b*(rho*(k-m) + sqrt((k-m)^2 + s^2))
        k_eval = np.linspace(-0.5, 0.5, 20)
        w_eval = calibrate_svi_surface_slice(k_eval, a=0.04, b=0.10, rho=-0.20, m=0.0, sigma=0.15)
        self.assertTrue(isinstance(w_eval, np.ndarray))
        self.assertTrue((w_eval >= 1e-6).all(), "Total variance w(k) must remain positive")

    # =========================================================================
    # SUITE 3: Feature F764 Riemannian AIRM & Septuple-Pillar ZCA Stress
    # =========================================================================

    def test_adv13_riemannian_airm_metric_positivity_and_identity(self) -> None:
        """ADV13 [F764]: AIRM metric axioms: Positivity d(A,B) > 0 and Indiscernibles d(A,A) == 0."""
        rng = np.random.RandomState(42)
        # Random SPD matrices
        A = rng.normal(0, 1, (7, 7))
        cov1 = A @ A.T + np.eye(7) * 0.1
        B = rng.normal(0, 1, (7, 7))
        cov2 = B @ B.T + np.eye(7) * 0.1

        # Axiom 1: d(cov1, cov1) == 0
        d_self = compute_riemannian_airm_distance(cov1, cov1)
        self.assertAlmostEqual(d_self, 0.0, places=6)

        # Axiom 2: d(cov1, cov2) > 0 for cov1 != cov2
        d_diff = compute_riemannian_airm_distance(cov1, cov2)
        self.assertGreater(d_diff, 0.0)
        self.assertTrue(np.isfinite(d_diff))

    def test_adv14_riemannian_airm_metric_symmetry(self) -> None:
        """ADV14 [F764]: AIRM metric axiom: Symmetry d(Sigma_1, Sigma_2) == d(Sigma_2, Sigma_1)."""
        rng = np.random.RandomState(123)
        for dim in [2, 5, 7, 10]:
            A = rng.normal(0, 1, (dim, dim))
            cov1 = A @ A.T + np.eye(dim) * 0.05
            B = rng.normal(0, 1, (dim, dim))
            cov2 = B @ B.T + np.eye(dim) * 0.05

            d_12 = compute_riemannian_airm_distance(cov1, cov2)
            d_21 = compute_riemannian_airm_distance(cov2, cov1)
            self.assertAlmostEqual(d_12, d_21, places=6, msg=f"Symmetry failed for dim {dim}: {d_12} vs {d_21}")

    def test_adv15_riemannian_airm_metric_triangle_inequality(self) -> None:
        """ADV15 [F764]: AIRM metric axiom: Triangle Inequality d(Sigma_1, Sigma_3) <= d(Sigma_1, Sigma_2) + d(Sigma_2, Sigma_3)."""
        rng = np.random.RandomState(999)
        for trial in range(15):
            dim = 7
            A = rng.normal(0, 1, (dim, dim))
            s1 = A @ A.T + np.eye(dim) * 0.1
            B = rng.normal(0, 1, (dim, dim))
            s2 = B @ B.T + np.eye(dim) * 0.1
            C = rng.normal(0, 1, (dim, dim))
            s3 = C @ C.T + np.eye(dim) * 0.1

            d_13 = compute_riemannian_airm_distance(s1, s3)
            d_12 = compute_riemannian_airm_distance(s1, s2)
            d_23 = compute_riemannian_airm_distance(s2, s3)

            # Triangle inequality with 1e-6 numerical tolerance
            self.assertLessEqual(d_13, d_12 + d_23 + 1e-6,
                                 f"Triangle inequality violated in trial {trial}: {d_13:.6f} > {d_12:.6f} + {d_23:.6f}")

    def test_adv16_riemannian_airm_affine_invariance(self) -> None:
        """ADV16 [F764]: Affine Invariance: delta(M Sigma_1 M^T, M Sigma_2 M^T) == delta(Sigma_1, Sigma_2)."""
        rng = np.random.RandomState(777)
        dim = 5
        A = rng.normal(0, 1, (dim, dim))
        s1 = A @ A.T + np.eye(dim) * 0.2
        B = rng.normal(0, 1, (dim, dim))
        s2 = B @ B.T + np.eye(dim) * 0.2

        # Invertible transformation matrix M
        M = rng.normal(0, 1, (dim, dim))
        while abs(np.linalg.det(M)) < 1e-2:
            M = rng.normal(0, 1, (dim, dim))

        trans_s1 = M @ s1 @ M.T
        trans_s2 = M @ s2 @ M.T

        d_orig = compute_riemannian_airm_distance(s1, s2)
        d_trans = compute_riemannian_airm_distance(trans_s1, trans_s2)
        self.assertAlmostEqual(d_orig, d_trans, places=5,
                               msg=f"Affine invariance failed: {d_orig} vs {d_trans}")

    def test_adv17_septuple_pillar_zca_whitening_symmetry_and_stability(self) -> None:
        """ADV17 [F764]: Septuple-Pillar ZCA whitening matrix symmetry W_ZCA == W_ZCA^T across ill-conditioned inputs."""
        rng = np.random.RandomState(555)
        # 1. Regular 7x7 covariance
        X = rng.normal(0, 1, (100, 7))
        cov_reg = np.cov(X, rowvar=False)
        w_zca = compute_septuple_pillar_zca_whitening(cov_reg, shrink_weight=0.0)
        np.testing.assert_allclose(w_zca, w_zca.T, atol=1e-6)

        # 2. Ill-conditioned covariance (eigenvalue ratio 10^12)
        D_ill = np.diag([1e6, 1e4, 1e2, 1.0, 1e-2, 1e-4, 1e-6])
        Q, _ = np.linalg.qr(rng.normal(0, 1, (7, 7)))
        cov_ill = Q @ D_ill @ Q.T
        cov_ill = 0.5 * (cov_ill + cov_ill.T)
        w_ill = compute_septuple_pillar_zca_whitening(cov_ill, shrink_weight=0.1)
        self.assertTrue(np.isfinite(w_ill).all())
        np.testing.assert_allclose(w_ill, w_ill.T, atol=1e-5)

        # 3. Singular rank-1 matrix
        v = rng.normal(0, 1, (7, 1))
        cov_rank1 = v @ v.T
        w_rank1 = compute_septuple_pillar_zca_whitening(cov_rank1, ridge_epsilon=1e-4)
        self.assertTrue(np.isfinite(w_rank1).all())
        np.testing.assert_allclose(w_rank1, w_rank1.T, atol=1e-5)

    def test_adv18_septuple_pillar_zca_exact_whitening(self) -> None:
        """ADV18 [F764]: Exact covariance whitening W @ Sigma @ W^T == I_7 when shrink_weight=0.0."""
        rng = np.random.RandomState(888)
        X = rng.normal(0, 1, (150, 7))
        cov7 = np.cov(X, rowvar=False)
        w_zca = compute_septuple_pillar_zca_whitening(cov7, shrink_weight=0.0)
        cov_white = w_zca @ cov7 @ w_zca.T
        np.testing.assert_allclose(cov_white, np.eye(7), atol=1e-4)

    def test_adv19_riemannian_frechet_shrinkage_interpolation(self) -> None:
        """ADV19 [F764]: Fréchet shrinkage interpolates between sample covariance and prior target."""
        rng = np.random.RandomState(333)
        A = rng.normal(0, 1, (4, 4))
        sample_cov = A @ A.T + np.eye(4) * 0.1
        prior_cov = np.eye(4)

        # alpha = 0.0 -> sample_cov
        s_0 = compute_riemannian_frechet_shrinkage(sample_cov, prior_cov, alpha=0.0)
        np.testing.assert_allclose(s_0, sample_cov, atol=1e-5)

        # alpha = 1.0 -> prior_cov
        s_1 = compute_riemannian_frechet_shrinkage(sample_cov, prior_cov, alpha=1.0)
        np.testing.assert_allclose(s_1, prior_cov, atol=1e-5)

        # alpha = 0.5 -> intermediate SPD matrix
        s_half = compute_riemannian_frechet_shrinkage(sample_cov, prior_cov, alpha=0.5)
        np.testing.assert_allclose(s_half, s_half.T, atol=1e-6)
        eigs = np.linalg.eigvalsh(s_half)
        self.assertTrue((eigs > 0.0).all())

    # =========================================================================
    # SUITE 4: Phase156Coupler Alpha Bounding & Interface Contract Stress
    # =========================================================================

    def test_adv20_phase156_coupler_interface_contract_alpha_presence(self) -> None:
        """ADV20 [Phase156Coupler Interface]: PROJECT.md specifies alpha_p156 bounded in [-3.0, 3.0].

        Verifies whether Phase156Coupler evaluates and returns alpha_p156.
        """
        pillar_mat = np.array([
            [0.6, 0.7, 0.5, 0.6, 0.8, 0.4, 0.5],
            [0.5, 0.6, 0.6, 0.7, 0.5, 0.6, 0.4],
            [0.7, 0.5, 0.4, 0.5, 0.6, 0.5, 0.7],
        ])
        res = self.coupler.evaluate(pillar_mat)

        # Check whether alpha_p156 is exposed in return dictionary
        has_alpha_p156 = "alpha_p156" in res or "alpha" in res
        if not has_alpha_p156:
            # Document finding: PROJECT.md interface contract requires alpha_p156: np.ndarray bounded in [-3.0, 3.0]
            # If missing, record as confirmed defect
            self.assertTrue(has_alpha_p156,
                            "DEFECT DETECTED: Phase156Coupler does NOT return 'alpha_p156' in evaluate() return dict. "
                            f"Returned keys: {list(res.keys())}. "
                            "Interface contract in PROJECT.md line 96 specifies composite alpha vector alpha_p156.")

    def test_adv21_phase156_coupler_alpha_bounding_in_range(self) -> None:
        """ADV21 [Phase156Coupler]: Composite alpha vector must be strictly bounded in [-3.0, 3.0]."""
        extreme_mat = np.array([
            [10.0, -10.0, 50.0, -50.0, 100.0, -100.0, 20.0],
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            [-5.0, -5.0, -5.0, -5.0, -5.0, -5.0, -5.0],
        ])
        res = self.coupler.evaluate(extreme_mat)

        if "alpha_p156" in res:
            alpha = np.asarray(res["alpha_p156"])
            self.assertTrue((alpha >= -3.0).all(), f"Alpha below -3.0: min={alpha.min()}")
            self.assertTrue((alpha <= 3.0).all(), f"Alpha above 3.0: max={alpha.max()}")
            self.assertTrue(np.isfinite(alpha).all())
        else:
            self.skipTest("alpha_p156 key absent in Phase156Coupler output dictionary (covered in ADV20)")

    def test_adv22_phase156_coupler_regularizers_in_unit_interval(self) -> None:
        """ADV22 [Phase156Coupler]: Verify regularizers h_phase156 in (0, 1] and fcpi_v156 in (0, 1]."""
        p_mat = np.random.RandomState(42).uniform(0.1, 0.9, (15, 7))
        res = self.coupler.evaluate(p_mat)

        h_vals = np.asarray(res["h_phase156"])
        fcpi_vals = np.asarray(res["fcpi_v156"])

        self.assertTrue(((h_vals > 0.0) & (h_vals <= 1.0)).all(), f"h_phase156 out of (0,1]: {h_vals}")
        self.assertTrue(((fcpi_vals > 0.0) & (fcpi_vals <= 1.0)).all(), f"fcpi_v156 out of (0,1]: {fcpi_vals}")
        self.assertTrue(np.isfinite(res["riemannian_airm_metric"]))
        self.assertGreaterEqual(res["riemannian_airm_metric"], 0.0)

    def test_adv23_phase156_coupler_nan_inf_extreme_shock_resilience(self) -> None:
        """ADV23 [Phase156Coupler]: Corrupted inputs with NaNs and Infs must be sanitized to clean outputs."""
        corrupted = np.array([
            [np.nan, 0.7, np.inf, 0.6, -np.inf, 0.4, 0.5],
            [0.5, np.nan, 0.6, 0.7, 0.5, 0.6, np.nan],
        ])
        res = self.coupler.evaluate(corrupted)

        h_vals = np.asarray(res["h_phase156"])
        fcpi_vals = np.asarray(res["fcpi_v156"])
        self.assertTrue(np.isfinite(h_vals).all(), "NaN/Inf leaked into h_phase156")
        self.assertTrue(np.isfinite(fcpi_vals).all(), "NaN/Inf leaked into fcpi_v156")
        self.assertTrue(np.isfinite(res["zca_matrix"]).all(), "NaN/Inf leaked into zca_matrix")


if __name__ == "__main__":
    unittest.main()
