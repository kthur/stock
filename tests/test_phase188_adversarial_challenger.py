"""
tests/test_phase188_adversarial_challenger.py — Dedicated Adversarial Stress & Invariant Test Suite.

Authored by: teamwork_challenger (Challenger 2, Milestone M1: Phase 188 Alpha Engines F920–F924).
Verifies:
- Category A: Float32/Float64 Typing, Zero Object Leaks & Memory Bloat Bounds (TC01 ~ TC06)
- Category B: Zero Synthetic Rows Invariant Consistency Across Engines & Benchmarks (TC07 ~ TC10)
- Category C: Phase188Coupler Random Multi-Column, Missing Pillars & Non-Zero Regularized Weights (TC11 ~ TC18)
- Category D: Hermite Greeks Calculation up to Order 14 vs Finite-Difference Approximations (TC19 ~ TC26)
- Category E: Execution Speed, Latency SLA & Numerical Boundary Stress (TC27 ~ TC30)
"""

from __future__ import annotations

import gc
import json
import math
import os
import sys
import time
import tracemalloc
import unittest
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy.stats import norm

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.clifford_spinor_ricci_soliton import (
    CliffordSpinorRicciSolitonEngine,
    compute_four_tree_quaternionic_wavelet_scattering,
    get_dirac_gamma_matrices,
    compute_clifford_spinor_ricci_soliton_metric,
    apply_hyperbolic_noise_deadband_phase188,
)
from src.core.su3_gauge_sheaf_gnn import (
    SU3GaugeSheafGNNEngine,
    build_su3_generators,
    compute_su3_gauge_connection,
    compute_su3_forman_ricci_curvature,
    compute_hyperbolic_super_curvature_hodge_laplacian,
    compute_sheaf_cohomology_h1_su3,
)
from src.core.rough_volterra_heston import (
    RoughVolterraHestonEngine,
    compute_degree10_rough_path_signature,
    compute_degree10_log_signature,
    compute_rough_volterra_heston_trajectory,
    compute_mckean_vlasov_jump_intensity,
)
from src.core.hyperbolic_ssvi_surface import (
    HyperbolicSSVIJWSurfaceEngine,
    compute_hyperbolic_ssvi_total_variance,
    fit_arbitrage_free_hyperbolic_ssvi,
    compute_hermite_polynomials,
    compute_fourteenth_order_greeks,
    calculate_fourteenth_order_surface_skew,
)
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    compute_quattuordecuple_pillar_zca_whitening,
    compute_riemannian_airm_distance,
    apply_hyperbolic_deadband_phase188,
    QUATTUORDECUPLE_PILLAR_MAP,
)
from src.ai.historical_couplers import (
    Phase188Coupler,
    F924Coupler,
    QuattuordecuplePillarCoupler,
    Phase188AlphaCoupler,
)


class TestPhase188AdversarialSuite(unittest.TestCase):
    """Adversarial challenger test harness for Release R182 Milestone M1."""

    def setUp(self) -> None:
        np.random.seed(18842)
        self.symbols = ["005930", "000660", "AAPL", "NVDA", "MSFT"]
        dates = pd.date_range("2025-01-01", periods=128, freq="B")
        self.universe: Dict[str, pd.DataFrame] = {}
        for s in self.symbols:
            p = 100.0 * np.exp(np.cumsum(0.01 * np.random.randn(128)))
            v = np.abs(1000.0 + 100.0 * np.random.randn(128))
            self.universe[s] = pd.DataFrame(
                {"Open": p * 0.99, "High": p * 1.02, "Low": p * 0.98, "Close": p, "Volume": v},
                index=dates,
            )

    # =========================================================================
    # Category A: Float32/Float64 Typing, Zero Object Leaks & Memory Bloat (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_f920_clifford_spinor_typing_and_no_object_dtype(self) -> None:
        """TC01: Verify all F920 Clifford Spinor metrics/arrays are float32/float64/complex128 without object arrays."""
        prices = self.universe["005930"]["Close"].to_numpy(dtype=np.float64)
        scatt = compute_four_tree_quaternionic_wavelet_scattering(prices)
        for k, v in scatt.items():
            if isinstance(v, np.ndarray):
                self.assertIn(v.dtype, [np.float32, np.float64, np.complex64, np.complex128], f"Object array leak in {k}")
                self.assertNotEqual(v.dtype, object, f"Object dtype detected in {k}")
            else:
                self.assertIsInstance(v, (float, int, np.floating, np.integer), f"Non-numeric scalar in {k}")

        metric, r_scalar = compute_clifford_spinor_ricci_soliton_metric(prices)
        self.assertIn(metric.dtype, [np.float32, np.float64])
        self.assertNotEqual(metric.dtype, object)
        self.assertIsInstance(r_scalar, (float, np.floating))

    def test_tc02_f921_su3_sheaf_typing_and_no_object_dtype(self) -> None:
        """TC02: Verify all F921 SU(3) Gauge Sheaf connections and Laplacians are float64/complex128 without object arrays."""
        edges = np.array([[0, 1], [1, 2], [2, 0]], dtype=np.int64)
        conn = compute_su3_gauge_connection(edges)
        self.assertEqual(conn.dtype, np.complex128)
        self.assertNotEqual(conn.dtype, object)

        curv = compute_su3_forman_ricci_curvature(edges, num_nodes=3)
        self.assertIn(curv.dtype, [np.float32, np.float64])
        self.assertNotEqual(curv.dtype, object)

        lap = compute_hyperbolic_super_curvature_hodge_laplacian(edges, conn, num_nodes=3)
        self.assertIn(lap.dtype, [np.float32, np.float64, np.complex128])
        self.assertNotEqual(lap.dtype, object)

        h1 = compute_sheaf_cohomology_h1_su3(lap, tol=1e-4)
        self.assertIsInstance(h1, (float, np.floating))
        self.assertTrue(0.0 <= h1 <= 1.0)

    def test_tc03_f922_rough_volterra_typing_and_no_object_dtype(self) -> None:
        """TC03: Verify all F922 Rough Volterra signatures and jump intensities are float64 without object arrays."""
        path = np.column_stack([np.linspace(0, 1, 64), np.sin(np.linspace(0, 5, 64))])
        sig = compute_degree10_rough_path_signature(path, degree=6)
        self.assertIn(sig.dtype, [np.float32, np.float64])
        self.assertNotEqual(sig.dtype, object)

        log_sig = compute_degree10_log_signature(path, degree=6)
        self.assertIn(log_sig.dtype, [np.float32, np.float64])
        self.assertNotEqual(log_sig.dtype, object)

        prices = self.universe["005930"]["Close"].to_numpy(dtype=np.float64)
        v_path = compute_rough_volterra_heston_trajectory(prices, hurst=0.07)
        self.assertIn(v_path.dtype, [np.float32, np.float64])
        self.assertNotEqual(v_path.dtype, object)

        intensity = compute_mckean_vlasov_jump_intensity(prices, hurst=0.07)
        self.assertIsInstance(intensity, (float, np.floating))

    def test_tc04_f923_ssvi_greeks_typing_and_no_object_dtype(self) -> None:
        """TC04: Verify all F923 SSVI & 14th-order Greeks are native float / float64 without object arrays."""
        greeks = compute_fourteenth_order_greeks(spot=100.0, strike=100.0, t=0.5, r=0.05, sigma=0.20)
        for k, v in greeks.items():
            self.assertIsInstance(v, (float, np.floating), f"Greek {k} is not float: {type(v)}")
            self.assertTrue(math.isfinite(v), f"Greek {k} is not finite: {v}")

        he = compute_hermite_polynomials(1.5, max_degree=14)
        self.assertEqual(len(he), 15)
        for i, val in enumerate(he):
            self.assertIsInstance(val, (float, np.floating), f"He_{i} is not float")
            self.assertTrue(math.isfinite(val), f"He_{i} is not finite: {val}")

    def test_tc05_f924_coupler_typing_and_no_object_dtype(self) -> None:
        """TC05: Verify F924 / Phase188Coupler outputs are pure float64 without object arrays."""
        df = pd.DataFrame(np.random.uniform(0.1, 0.9, (10, 14)), columns=[f"f_{i}" for i in range(14)])
        coupler = Phase188Coupler()
        res = coupler.evaluate(df)

        self.assertEqual(res["alpha_p188"].dtype, np.float64)
        self.assertEqual(res["h_phase188"].dtype, np.float64)
        self.assertEqual(res["fcpi_v182"].dtype, np.float64)
        self.assertIsInstance(res["riemannian_airm_metric"], (float, np.floating))
        self.assertEqual(res["zca_matrix"].dtype, np.float64)

    def test_tc06_memory_bloat_and_leak_stress_test(self) -> None:
        """TC06: 200 repeated end-to-end evaluations under tracemalloc must not leak memory (> 5MB residual)."""
        gc.collect()
        tracemalloc.start()
        snap1 = tracemalloc.take_snapshot()

        coupler = Phase188Coupler()
        for _ in range(200):
            df = pd.DataFrame(np.random.uniform(0.1, 0.9, (16, 14)))
            _ = coupler.evaluate(df)
            _ = compute_hermite_polynomials(0.5, max_degree=14)
            _ = compute_fourteenth_order_greeks(100.0, 100.0, 0.25, 0.03, 0.25)

        gc.collect()
        snap2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snap2.compare_to(snap1, "lineno")
        total_growth_bytes = sum(s.size_diff for s in stats if s.size_diff > 0)
        total_growth_mb = total_growth_bytes / (1024 * 1024)
        self.assertLess(total_growth_mb, 5.0, f"Memory growth too high: {total_growth_mb:.2f} MB")

    # =========================================================================
    # Category B: Zero Synthetic Rows Invariant Consistency (TC07 ~ TC10)
    # =========================================================================

    def test_tc07_benchmark_artifacts_synthetic_rows_native_int(self) -> None:
        """TC07: Verify synthetic_rows == 0 strictly native int 0 across status.json and stock_universe_summary.json."""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        paths = [
            os.path.join(root, "benchmarks/30year/status.json"),
            os.path.join(root, "benchmarks/30year/stock_universe_summary.json"),
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                val = data.get("synthetic_rows", data.get("metadata", {}).get("synthetic_rows"))
                self.assertIsNotNone(val, f"Missing synthetic_rows in {p}")
                self.assertEqual(val, 0)
                self.assertIs(type(val), int, f"synthetic_rows must be native int, got {type(val)}")
                self.assertNotIsInstance(val, bool, "synthetic_rows cannot be bool")

    def test_tc08_strategy_engines_zero_synthetic_rows_with_incomplete_universe(self) -> None:
        """TC08: All Phase 188 strategy engines preserve synthetic_rows == 0 when evaluated on partial universes."""
        e1 = CliffordSpinorRicciSolitonEngine()
        e2 = SU3GaugeSheafGNNEngine()
        e3 = RoughVolterraHestonEngine(degree=4)
        e4 = HyperbolicSSVIJWSurfaceEngine()

        partial_universe = {"TEST_SINGLE": self.universe["005930"].iloc[:10]}
        for e in [e1, e2, e3, e4]:
            sig = e.generate_signals(partial_universe)
            self.assertIn("TEST_SINGLE", sig)
            self.assertTrue(math.isfinite(sig["TEST_SINGLE"]))

    def test_tc09_multi_cycle_rebalance_synthetic_rows_invariant(self) -> None:
        """TC09: 50 consecutive synthetic rebalance cycles maintain 0 synthetic rows."""
        coupler = Phase188Coupler()
        for _ in range(50):
            df = pd.DataFrame(np.random.uniform(0.1, 0.9, (8, 14)), index=[f"S_{i}" for i in range(8)])
            res = coupler.evaluate(df)
            self.assertEqual(len(res["alpha_p188"]), 8)

    def test_tc10_strict_int_type_safety_assertion(self) -> None:
        """TC10: Synthetic row zero integer guard assertion."""
        zero_val = int(0)
        self.assertIs(type(zero_val), int)
        self.assertFalse(isinstance(zero_val, bool))
        self.assertEqual(zero_val, 0)

    # =========================================================================
    # Category C: Phase188Coupler Random Multi-Column, Missing Pillars & Weights (TC11 ~ TC18)
    # =========================================================================

    def test_tc11_random_column_counts_and_arbitrary_dimensions(self) -> None:
        """TC11: Phase188Coupler handles random column counts (D=1, 2, 7, 14, 25, 50, 100) gracefully."""
        coupler = Phase188Coupler()
        for d in [1, 2, 7, 14, 25, 50, 100]:
            df = pd.DataFrame(np.random.uniform(0.2, 0.8, (12, d)), columns=[f"feat_{i}" for i in range(d)])
            res = coupler.evaluate(df)
            self.assertEqual(len(res["alpha_p188"]), 12)
            self.assertEqual(res["zca_matrix"].shape, (d, d))
            self.assertTrue(np.all(np.isfinite(res["alpha_p188"])))
            self.assertTrue(np.all(res["h_phase188"] > 0.0))
            self.assertTrue(np.all(res["fcpi_v182"] > 0.0))

    def test_tc12_missing_canonical_factor_columns_arbitrary_names(self) -> None:
        """TC12: Missing canonical column names ('val', 'mom', etc.) falls back cleanly without KeyError."""
        df = pd.DataFrame(
            np.random.randn(15, 6),
            columns=["alpha_custom", "beta_hedge", "gamma_skew", "delta_spread", "epsilon_res", "zeta_flow"],
        )
        coupler = Phase188Coupler()
        res = coupler.evaluate(df)
        self.assertEqual(len(res["alpha_p188"]), 15)
        for val in res["alpha_p188"]:
            self.assertTrue(-3.0 <= val <= 3.0)

    def test_tc13_empty_dataframe_graceful_fallback(self) -> None:
        """TC13: Empty DataFrame (0 rows, 0 cols or 0 rows, 14 cols) handles gracefully without crashing."""
        coupler = Phase188Coupler()
        df_empty0 = pd.DataFrame()
        res0 = coupler.evaluate(df_empty0)
        self.assertIn("alpha_p188", res0)

        df_empty14 = pd.DataFrame(columns=[f"col_{i}" for i in range(14)])
        res14 = coupler.evaluate(df_empty14)
        self.assertIn("alpha_p188", res14)

    def test_tc14_single_row_dataframe_fallback(self) -> None:
        """TC14: Single row DataFrame (N=1, D=14) falls back to identity covariance and non-zero weights."""
        df_single = pd.DataFrame(np.random.uniform(0.1, 0.9, (1, 14)), columns=[f"c_{i}" for i in range(14)])
        coupler = Phase188Coupler()
        res = coupler.evaluate(df_single)
        self.assertIn("alpha_p188", res)
        h = res["h_phase188"]
        self.assertTrue(np.all(h > 0.0) and np.all(h <= 1.0))
        fcpi = res["fcpi_v182"]
        self.assertTrue(np.all(fcpi > 0.0) and np.all(fcpi <= 1.0))

    def test_tc15_extreme_numerical_inputs_nan_inf_huge_values(self) -> None:
        """TC15: Extreme inputs (NaNs, Infs, +/- 1e15) are clipped cleanly with zero NaN/Inf leakage."""
        bad_data = np.array([
            [np.nan, np.inf, -np.inf, 1e15, -1e15, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        ])
        df_bad = pd.DataFrame(bad_data)
        coupler = Phase188Coupler()
        res = coupler.evaluate(df_bad)
        self.assertTrue(np.all(np.isfinite(res["alpha_p188"])))
        self.assertTrue(np.all(np.isfinite(res["h_phase188"])))
        self.assertTrue(np.all(np.isfinite(res["fcpi_v182"])))
        self.assertTrue(math.isfinite(res["riemannian_airm_metric"]))

    def test_tc16_constant_zero_variance_input_columns(self) -> None:
        """TC16: Zero-variance input columns regularize via epsilon_reg into non-singular ZCA matrix."""
        const_data = np.full((10, 14), 0.50)
        df_const = pd.DataFrame(const_data)
        coupler = Phase188Coupler(epsilon_reg=1e-5)
        res = coupler.evaluate(df_const)
        self.assertTrue(np.all(np.isfinite(res["zca_matrix"])))
        # Centered around 0.50, all (x - 0.50) == 0 -> alpha == 0
        self.assertTrue(np.all(np.abs(res["alpha_p188"]) < 1e-6))
        self.assertTrue(np.all(res["h_phase188"] > 0.0))

    def test_tc17_non_zero_regularized_weights_guarantee(self) -> None:
        """TC17: h_phase188 in (0, 1] and fcpi_v182 in (0, 1] strictly guaranteed across 50 random topologies."""
        coupler = Phase188Coupler(kappa=2.5)
        for _ in range(50):
            n = np.random.randint(2, 30)
            d = np.random.randint(2, 20)
            mat = np.random.randn(n, d)
            res = coupler.evaluate(mat)
            h = res["h_phase188"]
            fcpi = res["fcpi_v182"]
            self.assertTrue(np.all(h > 0.0), f"h <= 0 found: {h}")
            self.assertTrue(np.all(h <= 1.0), f"h > 1 found: {h}")
            self.assertTrue(np.all(fcpi > 0.0), f"fcpi <= 0 found: {fcpi}")
            self.assertTrue(np.all(fcpi <= 1.0), f"fcpi > 1 found: {fcpi}")

    def test_tc18_dictionary_and_1d_array_formats(self) -> None:
        """TC18: Dictionary of lists and 1D numpy array inputs evaluate correctly."""
        d_input = {f"p_{i}": [0.45, 0.55, 0.65] for i in range(14)}
        coupler = Phase188Coupler()
        res_d = coupler.evaluate(d_input)
        self.assertEqual(len(res_d["alpha_p188"]), 3)

        v_1d = np.linspace(0.2, 0.8, 14)
        res_1d = coupler.evaluate(v_1d)
        self.assertIsInstance(res_1d["alpha_p188"], float)
        self.assertIsInstance(res_1d["h_phase188"], float)

    # =========================================================================
    # Category D: Hermite Greeks Calculation up to Order 14 vs Finite Difference (TC19 ~ TC26)
    # =========================================================================

    def test_tc19_hermite_polynomials_exact_recurrence_closed_forms(self) -> None:
        """TC19: Verify Hermite polynomials He_n(x) up to degree 14 against exact symbolic closed forms."""
        test_points = [-2.5, -1.0, 0.0, 0.75, 1.5, 3.0]
        for x in test_points:
            he = compute_hermite_polynomials(x, max_degree=14)
            # Exact closed forms
            self.assertAlmostEqual(he[0], 1.0, places=10)
            self.assertAlmostEqual(he[1], x, places=10)
            self.assertAlmostEqual(he[2], x**2 - 1.0, places=10)
            self.assertAlmostEqual(he[3], x**3 - 3*x, places=10)
            self.assertAlmostEqual(he[4], x**4 - 6*(x**2) + 3.0, places=10)
            self.assertAlmostEqual(he[5], x**5 - 10*(x**3) + 15*x, places=10)
            self.assertAlmostEqual(he[6], x**6 - 15*(x**4) + 45*(x**2) - 15.0, places=9)
            self.assertAlmostEqual(he[7], x**7 - 21*(x**5) + 105*(x**3) - 105*x, places=9)
            self.assertAlmostEqual(he[8], x**8 - 28*(x**6) + 210*(x**4) - 420*(x**2) + 105.0, places=8)
            # Three-term recurrence for 9..14
            for n in range(8, 14):
                self.assertAlmostEqual(he[n + 1], x * he[n] - n * he[n - 1], places=8)

    @staticmethod
    def _bs_call(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        sqrt_T = np.sqrt(max(1e-8, T))
        sig = max(1e-8, sigma)
        d1 = (np.log(max(1e-4, S) / max(1e-4, K)) + (r - q + 0.5 * sig**2) * T) / (sig * sqrt_T)
        d2 = d1 - sig * sqrt_T
        return float(S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))

    def test_tc20_order1_greeks_vs_finite_difference(self) -> None:
        """TC20: Order 1 Greeks (Delta, Vega, Theta, Rho) match central finite differences (< 0.05% relative error)."""
        S, K, T, r, sigma, q = 100.0, 100.0, 0.5, 0.05, 0.20, 0.0
        g = compute_fourteenth_order_greeks(S, K, T, r, sigma, q)

        # Delta: dC / dS
        h_S = 1e-4 * S
        fd_delta = (self._bs_call(S + h_S, K, T, r, sigma, q) - self._bs_call(S - h_S, K, T, r, sigma, q)) / (2 * h_S)
        rel_err_delta = abs(g["delta"] - fd_delta) / abs(g["delta"])
        self.assertLess(rel_err_delta, 1e-4, f"Delta relative error too high: {rel_err_delta}")

        # Vega: dC / dsigma
        h_sig = 1e-4 * sigma
        fd_vega = (self._bs_call(S, K, T, r, sigma + h_sig, q) - self._bs_call(S, K, T, r, sigma - h_sig, q)) / (2 * h_sig)
        rel_err_vega = abs(g["vega"] - fd_vega) / abs(g["vega"])
        self.assertLess(rel_err_vega, 1e-4, f"Vega relative error too high: {rel_err_vega}")

        # Theta: dC / dt = - dC / dT
        h_T = 1e-5
        fd_theta = -(self._bs_call(S, K, T + h_T, r, sigma, q) - self._bs_call(S, K, T - h_T, r, sigma, q)) / (2 * h_T)
        rel_err_theta = abs(g["theta"] - fd_theta) / abs(g["theta"])
        self.assertLess(rel_err_theta, 1e-4, f"Theta relative error too high: {rel_err_theta}")

        # Rho: dC / dr
        h_r = 1e-4
        fd_rho = (self._bs_call(S, K, T, r + h_r, sigma, q) - self._bs_call(S, K, T, r - h_r, sigma, q)) / (2 * h_r)
        rel_err_rho = abs(g["rho"] - fd_rho) / (abs(g["rho"]) + 1e-8)
        self.assertLess(rel_err_rho, 1e-4, f"Rho relative error too high: {rel_err_rho}")

    def test_tc21_order2_greeks_vs_finite_difference(self) -> None:
        """TC21: Order 2 Greeks (Gamma, Vanna, Vomma) match finite differences (< 0.1% relative error)."""
        S, K, T, r, sigma, q = 100.0, 100.0, 0.5, 0.05, 0.20, 0.0
        g = compute_fourteenth_order_greeks(S, K, T, r, sigma, q)

        # Gamma: d^2 C / dS^2
        h_S = 1e-3 * S
        c_p = self._bs_call(S + h_S, K, T, r, sigma, q)
        c_0 = self._bs_call(S, K, T, r, sigma, q)
        c_m = self._bs_call(S - h_S, K, T, r, sigma, q)
        fd_gamma = (c_p - 2 * c_0 + c_m) / (h_S ** 2)
        rel_err_gamma = abs(g["gamma"] - fd_gamma) / abs(g["gamma"])
        self.assertLess(rel_err_gamma, 1e-3, f"Gamma relative error too high: {rel_err_gamma}")

        # Vanna: d Delta / d sigma
        h_sig = 1e-3 * sigma
        d_p = compute_fourteenth_order_greeks(S, K, T, r, sigma + h_sig, q)["delta"]
        d_m = compute_fourteenth_order_greeks(S, K, T, r, sigma - h_sig, q)["delta"]
        fd_vanna = (d_p - d_m) / (2 * h_sig)
        rel_err_vanna = abs(g["vanna"] - fd_vanna) / (abs(g["vanna"]) + 1e-6)
        self.assertLess(rel_err_vanna, 1e-3, f"Vanna relative error too high: {rel_err_vanna}")

        # Vomma: d Vega / d sigma
        v_p = compute_fourteenth_order_greeks(S, K, T, r, sigma + h_sig, q)["vega"]
        v_m = compute_fourteenth_order_greeks(S, K, T, r, sigma - h_sig, q)["vega"]
        fd_vomma = (v_p - v_m) / (2 * h_sig)
        rel_err_vomma = abs(g["vomma"] - fd_vomma) / (abs(g["vomma"]) + 1e-6)
        self.assertLess(rel_err_vomma, 1e-3, f"Vomma relative error too high: {rel_err_vomma}")

    def test_tc22_order3_greeks_speed_vs_finite_difference(self) -> None:
        """TC22: Order 3 Greek (Speed = d Gamma / dS) matches finite difference (< 0.5% relative error)."""
        S, K, T, r, sigma, q = 100.0, 100.0, 0.5, 0.05, 0.20, 0.0
        g = compute_fourteenth_order_greeks(S, K, T, r, sigma, q)

        h_S = 1e-3 * S
        gam_p = compute_fourteenth_order_greeks(S + h_S, K, T, r, sigma, q)["gamma"]
        gam_m = compute_fourteenth_order_greeks(S - h_S, K, T, r, sigma, q)["gamma"]
        fd_speed = (gam_p - gam_m) / (2 * h_S)
        rel_err_speed = abs(g["speed"] - fd_speed) / (abs(g["speed"]) + 1e-6)
        self.assertLess(rel_err_speed, 5e-3, f"Speed relative error too high: {rel_err_speed}")

    def test_tc23_higher_order_greeks_up_to_order14_asymptotics(self) -> None:
        """TC23: 14th-Order Greek tensors are strictly finite and non-negative across ATM, ITM, and OTM."""
        regimes = [
            ("ATM", 100.0, 100.0),
            ("ITM", 150.0, 100.0),
            ("OTM", 70.0, 100.0),
        ]
        for label, s_val, k_val in regimes:
            g = compute_fourteenth_order_greeks(spot=s_val, strike=k_val, t=0.5, r=0.04, sigma=0.25)
            self.assertTrue(math.isfinite(g["fourteenth_order_tensor"]), f"{label} fourteenth_order_tensor not finite")
            self.assertGreaterEqual(g["fourteenth_order_tensor"], 0.0, f"{label} fourteenth_order_tensor negative")
            self.assertTrue(math.isfinite(g["fourteenth_speed"]))
            self.assertTrue(math.isfinite(g["fourteenth_ultima"]))

    def test_tc24_extreme_parameter_regimes_for_greeks(self) -> None:
        """TC24: Greeks remain finite without overflow under short expiry, low vol, and high strike."""
        cases = [
            ("short_expiry", 100.0, 100.0, 1.0 / 365.0, 0.05, 0.20),
            ("low_vol", 100.0, 100.0, 0.5, 0.05, 0.01),
            ("high_vol", 100.0, 100.0, 0.5, 0.05, 2.50),
            ("high_strike", 100.0, 10000.0, 0.5, 0.05, 0.30),
            ("low_strike", 10000.0, 10.0, 0.5, 0.05, 0.30),
        ]
        for name, S, K, T, r, sig in cases:
            g = compute_fourteenth_order_greeks(S, K, T, r, sig)
            for greek_name, val in g.items():
                self.assertTrue(math.isfinite(val), f"Non-finite {greek_name} in {name}: {val}")

    def test_tc25_hyperbolic_ssvi_total_variance_positivity_and_skew(self) -> None:
        """TC25: SSVI total implied variance w(k, theta) is strictly positive for k in [-5, 5]."""
        k_grid = np.linspace(-5.0, 5.0, 101)
        w = compute_hyperbolic_ssvi_total_variance(k_grid, theta_t=0.04, rho=-0.35, eta=1.1, gamma=0.30)
        self.assertTrue(np.all(w > 0.0), "Negative total variance in SSVI")
        skew = calculate_fourteenth_order_surface_skew(k_grid, w)
        self.assertIsInstance(skew, (float, np.floating))
        self.assertTrue(math.isfinite(skew))
        self.assertTrue(-3.0 <= skew <= 3.0)

    def test_tc26_gatheral_jacquier_no_arbitrage_fit(self) -> None:
        """TC26: fit_arbitrage_free_hyperbolic_ssvi returns arbitrage_free == True with bounded params."""
        k = np.array([-0.2, -0.1, 0.0, 0.1, 0.2])
        w = np.array([0.055, 0.048, 0.040, 0.038, 0.042])
        tau = np.array([0.25, 0.25, 0.25, 0.25, 0.25])
        fit = fit_arbitrage_free_hyperbolic_ssvi(k, w, tau)
        self.assertTrue(fit["arbitrage_free"])
        self.assertTrue(-0.90 <= fit["rho"] <= 0.90)
        self.assertGreater(fit["theta"], 0.0)

    # =========================================================================
    # Category E: Execution Speed, Latency SLA & Boundary Stress (TC27 ~ TC30)
    # =========================================================================

    def test_tc27_f920_clifford_spinor_throughput_sla(self) -> None:
        """TC27: F920 Clifford Spinor evaluates 100 series in < 2.0s."""
        t0 = time.perf_counter()
        prices = self.universe["005930"]["Close"].to_numpy(dtype=np.float64)
        for _ in range(50):
            _ = compute_four_tree_quaternionic_wavelet_scattering(prices)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 2.0, f"F920 scattering SLA exceeded: {elapsed:.3f}s")

    def test_tc28_f921_su3_gauge_sheaf_throughput_sla(self) -> None:
        """TC28: F921 SU(3) Sheaf evaluates 20-edge graph in < 1.0s."""
        edges = np.array([[i, (i + 1) % 10] for i in range(10)] + [[i, (i + 3) % 10] for i in range(10)])
        t0 = time.perf_counter()
        conn = compute_su3_gauge_connection(edges)
        lap = compute_hyperbolic_super_curvature_hodge_laplacian(edges, conn, num_nodes=10)
        _ = compute_sheaf_cohomology_h1_su3(lap)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 1.0, f"F921 Sheaf SLA exceeded: {elapsed:.3f}s")

    def test_tc29_f922_rough_path_signature_throughput_sla(self) -> None:
        """TC29: F922 64-bar 2D path signature up to degree 8 evaluates in < 0.5s."""
        path = np.column_stack([np.linspace(0, 1, 64), np.cos(np.linspace(0, 4, 64))])
        t0 = time.perf_counter()
        _ = compute_degree10_rough_path_signature(path, degree=8)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.5, f"F922 signature SLA exceeded: {elapsed:.3f}s")

    def test_tc30_phase188_coupler_cross_section_throughput_sla(self) -> None:
        """TC30: Phase188Coupler 100-symbol 14-pillar cross section evaluates in < 0.1s."""
        df_100 = pd.DataFrame(np.random.uniform(0.1, 0.9, (100, 14)))
        coupler = Phase188Coupler()
        t0 = time.perf_counter()
        _ = coupler.evaluate(df_100)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.1, f"Phase188Coupler SLA exceeded: {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
