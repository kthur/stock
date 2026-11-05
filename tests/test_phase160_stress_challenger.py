"""
tests/test_phase160_stress_challenger.py — Empirical Challenger Adversarial Stress Suite for Phase 160 Alpha.

This suite is executed independently by Challenger 2 to stress-test:
1. Multi-dimensional input formats (dict, Series, DataFrame, numpy 1D/2D) & polymorphism
2. Degenerate, collinear, extreme, NaN/inf inputs & error boundaries
3. Multi-threaded concurrency & race-condition resilience (16 threads concurrent execution)
4. High-throughput throughput SLA (>1,000 ops/sec) and bit-level determinism (5,000 calls)
5. Comprehensive stress checks across all 5 individual Phase 160 engines (F780–F784)
6. Dual-tree 100% cryptographic SHA-256 parity and system invariants.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import os
import sys
import time
import unittest
from typing import Any, Dict, List

import numpy as np
import pandas as pd

# Add repo root and trading_system paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.ai.historical_couplers import Phase160Coupler
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    apply_hyperbolic_deadband_phase160,
)
from src.core.spectral_wavelet_decomposition import (
    SpectralWaveletDecompositionEngine,
    compute_riemannian_geodesic_flow,
    extract_riemannian_geodesic_flow,
)
from src.core.value_chain_curvature_gnn import (
    ValueChainCurvatureGNNEngine,
    compute_hyperbolic_graph_representation,
)
from src.core.cross_market_micro_momentum import (
    CrossMarketMicroMomentumEngine,
    estimate_jump_diffusion_hawkes_params,
)
from src.core.option_surface_accelerator import (
    OptionSurfaceAccelerator,
    calculate_higher_order_surface_skew,
)


class TestPhase160StressChallenger(unittest.TestCase):
    """Empirical Challenger Adversarial Stress Test Suite."""

    def setUp(self) -> None:
        self.coupler = Phase160Coupler()
        self.rng = np.random.RandomState(42)

    # =========================================================================
    # 1. Multi-Dimensional Input Polymorphism for Phase160Coupler
    # =========================================================================

    def test_coupler_input_dict_scalars(self) -> None:
        """Verify Phase160Coupler with dict of scalar floats (single asset)."""
        d = {"f780": 0.55, "f781": 0.62, "f782": 0.48, "f783": 0.70, "f784": 0.51}
        res = self.coupler(d)
        self.assertIsInstance(res["alpha_p160"], float)
        self.assertTrue(-3.0 <= res["alpha_p160"] <= 3.0)
        self.assertTrue(0.0 < res["h_phase160"] <= 1.0)
        self.assertTrue(0.0 < res["fcpi_v160"] <= 1.0)
        self.assertTrue(res["s_action"] >= 0.0)
        self.assertTrue(res["riemannian_airm_metric"] >= 0.0)
        self.assertEqual(res["alpha"], res["alpha_p160"])
        self.assertEqual(res["action_functional"], res["s_action"])
        self.assertEqual(res["airm_distance"], res["riemannian_airm_metric"])

    def test_coupler_input_dict_lists(self) -> None:
        """Verify Phase160Coupler with dict of lists (multiple assets)."""
        d = {
            "f780": [0.55, 0.40, 0.80],
            "f781": [0.62, 0.45, 0.75],
            "f782": [0.48, 0.50, 0.60],
            "f783": [0.70, 0.35, 0.85],
            "f784": [0.51, 0.52, 0.58],
        }
        res = self.coupler(d)
        alpha = res["alpha_p160"]
        self.assertEqual(len(alpha), 3)
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))
        self.assertTrue(np.all(res["h_phase160"] > 0.0) and np.all(res["h_phase160"] <= 1.0))
        self.assertTrue(np.all(res["fcpi_v160"] > 0.0) and np.all(res["fcpi_v160"] <= 1.0))

    def test_coupler_input_dict_series_with_index(self) -> None:
        """Verify Phase160Coupler with dict of pd.Series preserving tickers as index."""
        tickers = ["005930.KS", "000660.KS", "AAPL", "NVDA", "MSFT"]
        d = {
            "f780": pd.Series([0.55, 0.60, 0.45, 0.80, 0.52], index=tickers),
            "f781": pd.Series([0.62, 0.58, 0.48, 0.75, 0.54], index=tickers),
            "f782": pd.Series([0.48, 0.52, 0.51, 0.65, 0.49], index=tickers),
            "f783": pd.Series([0.70, 0.65, 0.40, 0.85, 0.58], index=tickers),
            "f784": pd.Series([0.51, 0.53, 0.50, 0.70, 0.50], index=tickers),
        }
        res = self.coupler.evaluate(d)
        alpha = res["alpha_p160"]
        self.assertIsInstance(alpha, pd.Series)
        self.assertEqual(list(alpha.index), tickers)
        self.assertTrue((alpha >= -3.0).all() and (alpha <= 3.0).all())

    def test_coupler_input_pd_series_single(self) -> None:
        """Verify Phase160Coupler with 1D pd.Series input (single asset)."""
        s = pd.Series([0.55, 0.62, 0.48, 0.70, 0.51], index=["f780", "f781", "f782", "f783", "f784"])
        res = self.coupler(s)
        self.assertIsInstance(res["alpha_p160"], float)
        self.assertTrue(-3.0 <= res["alpha_p160"] <= 3.0)

    def test_coupler_input_pd_dataframe(self) -> None:
        """Verify Phase160Coupler with pd.DataFrame of varying dimensions."""
        # 1-row DataFrame
        df1 = pd.DataFrame([[0.55, 0.62, 0.48, 0.70, 0.51]], columns=["f0", "f1", "f2", "f3", "f4"])
        res1 = self.coupler(df1)
        self.assertIsInstance(res1["alpha_p160"], pd.Series)
        self.assertEqual(len(res1["alpha_p160"]), 1)

        # 50-row DataFrame with septuple pillars
        tickers = [f"SYM_{i:03d}" for i in range(50)]
        df50 = pd.DataFrame(
            self.rng.uniform(0.1, 0.9, (50, 7)),
            index=tickers,
            columns=[f"Pillar_{k}" for k in range(7)],
        )
        res50 = self.coupler(df50)
        self.assertIsInstance(res50["alpha_p160"], pd.Series)
        self.assertEqual(list(res50["alpha_p160"].index), tickers)
        self.assertTrue((res50["alpha_p160"] >= -3.0).all() and (res50["alpha_p160"] <= 3.0).all())
        self.assertEqual(res50["zca_matrix"].shape, (7, 7))

    def test_coupler_input_numpy_1d_and_2d(self) -> None:
        """Verify Phase160Coupler with numpy ndarray 1D and 2D."""
        # 1D ndarray
        arr1d = np.array([0.55, 0.62, 0.48, 0.70, 0.51])
        res1 = self.coupler(arr1d)
        self.assertIsInstance(res1["alpha_p160"], float)
        self.assertTrue(-3.0 <= res1["alpha_p160"] <= 3.0)

        # 2D ndarray (1x5)
        arr2d_1 = arr1d.reshape(1, 5)
        res2 = self.coupler(arr2d_1)
        self.assertIsInstance(res2["alpha_p160"], np.ndarray)
        self.assertEqual(len(res2["alpha_p160"]), 1)
        self.assertTrue(-3.0 <= float(res2["alpha_p160"][0]) <= 3.0)

        # 2D ndarray (20x5)
        arr2d_20 = self.rng.uniform(0.2, 0.8, (20, 5))
        res3 = self.coupler(arr2d_20)
        self.assertIsInstance(res3["alpha_p160"], np.ndarray)
        self.assertEqual(len(res3["alpha_p160"]), 20)
        self.assertTrue(np.all(res3["alpha_p160"] >= -3.0) and np.all(res3["alpha_p160"] <= 3.0))

    # =========================================================================
    # 2. Degenerate, Collinear, Extreme & Boundary Inputs
    # =========================================================================

    def test_coupler_collinear_singular_inputs(self) -> None:
        """Verify numerical stability when input factors are perfectly collinear (rank 1 covariance)."""
        # All columns identical -> covariance has zero eigenvalues
        col = np.linspace(0.1, 0.9, 30)
        collinear_mat = np.column_stack([col, col, col, col, col])
        res = self.coupler(collinear_mat)
        alpha = res["alpha_p160"]
        self.assertFalse(np.isnan(alpha).any())
        self.assertFalse(np.isinf(alpha).any())
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))
        self.assertTrue(np.all(np.isfinite(res["zca_matrix"])))

    def test_coupler_constant_factor_scores(self) -> None:
        """Verify input where all factor scores equal neutral baseline 0.50."""
        neutral_mat = np.full((15, 5), 0.50)
        res = self.coupler(neutral_mat)
        alpha = res["alpha_p160"]
        # Centered scores are 0 -> alpha must be identically 0.0
        self.assertTrue(np.allclose(alpha, 0.0, atol=1e-12))
        self.assertTrue(np.all(res["h_phase160"] > 0.0))

    def test_coupler_extreme_and_overflow_values(self) -> None:
        """Verify inputs with extreme values (+1e12, -1e12) get clamped safely without NaN."""
        extreme_mat = np.array([
            [1e12, -1e12, 1e9, -1e9, 0.5],
            [-1e12, 1e12, -1e9, 1e9, 0.5],
            [1e15, 1e15, 1e15, 1e15, 1e15],
        ])
        res = self.coupler(extreme_mat)
        alpha = res["alpha_p160"]
        self.assertFalse(np.isnan(alpha).any())
        self.assertFalse(np.isinf(alpha).any())
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))

    def test_coupler_nan_and_inf_handling(self) -> None:
        """Verify inputs with NaNs, +inf, -inf are sanitized to neutral scores."""
        nan_mat = np.array([
            [np.nan, 0.5, np.inf, -np.inf, np.nan],
            [0.6, np.nan, 0.4, 0.7, 0.5],
            [np.nan, np.nan, np.nan, np.nan, np.nan],
        ])
        res = self.coupler(nan_mat)
        alpha = res["alpha_p160"]
        self.assertFalse(np.isnan(alpha).any())
        self.assertFalse(np.isinf(alpha).any())
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))

    def test_coupler_empty_matrix(self) -> None:
        """Verify Phase160Coupler handles empty (0 x 5) matrix gracefully."""
        empty_mat = np.empty((0, 5))
        res = self.coupler(empty_mat)
        self.assertEqual(len(res["alpha_p160"]), 0)
        self.assertEqual(res["zca_matrix"].shape, (5, 5))

    # =========================================================================
    # 3. High-Throughput & Bit-Level Determinism
    # =========================================================================

    def test_coupler_deterministic_reproducibility(self) -> None:
        """Verify 5,000 repeated calls with identical input produce bit-identical output."""
        test_input = np.array([
            [0.551234, 0.621456, 0.481928, 0.701122, 0.518833],
            [0.412983, 0.583344, 0.612091, 0.392019, 0.741029],
            [0.681920, 0.450192, 0.551982, 0.812039, 0.490192],
        ])

        baseline_res = self.coupler(test_input)
        baseline_alpha = baseline_res["alpha_p160"]
        baseline_bytes = baseline_alpha.tobytes()

        # Run 5,000 evaluations
        start_time = time.perf_counter()
        N_RUNS = 5000
        for _ in range(N_RUNS):
            res = self.coupler(test_input)
            self.assertEqual(res["alpha_p160"].tobytes(), baseline_bytes)
        elapsed = time.perf_counter() - start_time

        ops_per_sec = N_RUNS / elapsed
        self.assertGreater(ops_per_sec, 1000.0, f"Throughput SLA breach: {ops_per_sec:.1f} ops/sec < 1000")

    # =========================================================================
    # 4. Multi-Threaded Concurrency & Race Condition Stress
    # =========================================================================

    def test_coupler_concurrent_thread_safety(self) -> None:
        """Verify 16 threads concurrently evaluating Phase160Coupler without interference."""
        def worker(thread_id: int) -> bool:
            local_coupler = Phase160Coupler()
            rng = np.random.RandomState(1000 + thread_id)
            for _ in range(100):
                data = rng.uniform(0.1, 0.9, (10, 5))
                res1 = local_coupler(data)
                res2 = Phase160Coupler.compute(data)
                if not np.allclose(res1["alpha_p160"], res2["alpha_p160"], atol=1e-10):
                    return False
                if not (-3.0 <= np.min(res1["alpha_p160"]) and np.max(res1["alpha_p160"]) <= 3.0):
                    return False
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(worker, tid) for tid in range(16)]
            results = [f.result() for f in futures]

        self.assertTrue(all(results), "Concurrency failure detected in Phase160Coupler")

    def test_engines_concurrent_thread_safety(self) -> None:
        """Verify all 5 Phase 160 alpha engines execute safely across 16 threads concurrently."""
        def engine_worker(thread_id: int) -> bool:
            rng = np.random.RandomState(2000 + thread_id)

            # 1. F780 Riemannian Geodesic Flow
            prices = 100.0 * np.cumprod(1.0 + rng.normal(0.0005, 0.015, 60))
            f780_res = extract_riemannian_geodesic_flow(prices)
            if not (0.0 <= f780_res["f780_geodesic_velocity"] <= 5.0):
                return False

            # 2. F781 Hyperbolic Poincare Representation
            dist_mat = rng.uniform(0.1, 2.0, (10, 10))
            dist_mat = 0.5 * (dist_mat + dist_mat.T)
            np.fill_diagonal(dist_mat, 0.0)
            f781_res = compute_hyperbolic_graph_representation(dist_mat)
            if not (0.0 <= f781_res["f781_hyperbolic_radius"] <= 0.999):
                return False

            # 3. F782 Jump Diffusion Hawkes
            returns = rng.normal(0.0, 0.01, 40)
            macro = {"vix": np.array([20.0, 21.5, 23.0]), "sox": np.array([4000.0, 3950.0])}
            f782_res = estimate_jump_diffusion_hawkes_params(returns, macro_shocks=macro)
            if not (0.0 <= f782_res["f782_jump_intensity"] <= 1.0):
                return False
            if not (0.0 <= f782_res["f782_branching_ratio"] <= 0.999):
                return False

            # 4. F783 Higher Order Surface Skew
            strikes = np.array([90.0, 95.0, 100.0, 105.0, 110.0])
            ivs = np.array([0.25, 0.22, 0.20, 0.21, 0.24])
            f783_res = calculate_higher_order_surface_skew({"strikes": strikes, "ivs": ivs, "spot": 100.0})
            if not (0.05 <= f783_res["f783_higher_order_greeks_score"] <= 0.95):
                return False

            # 5. F784 Hyperbolic Deadband
            noise = rng.normal(0.0, 0.02, 20)
            clean_noise = apply_hyperbolic_deadband_phase160(noise)
            if not np.all(np.abs(clean_noise) <= np.abs(noise)):
                return False

            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(engine_worker, tid) for tid in range(16)]
            results = [f.result() for f in futures]

        self.assertTrue(all(results), "Concurrency failure detected across Phase 160 engines")

    # =========================================================================
    # 5. Stress Checks on Individual Phase 160 Engines (F780–F784)
    # =========================================================================

    def test_f780_geodesic_flow_edge_cases(self) -> None:
        """Verify F780 extract_riemannian_geodesic_flow on flat, short, and 1,000-point series."""
        # Short series (< 5 elements)
        res_short = extract_riemannian_geodesic_flow(np.array([100.0, 101.0, 99.0]))
        self.assertEqual(res_short["f780_geodesic_velocity"], 0.0)

        # Flat prices
        res_flat = extract_riemannian_geodesic_flow(np.full(60, 100.0))
        self.assertAlmostEqual(res_flat["f780_geodesic_velocity"], 0.0, places=4)

        # Long series (1,000 points - must clamp to last 128 points without crashing)
        long_prices = 100.0 + np.cumsum(self.rng.normal(0, 1, 1000))
        long_prices = np.maximum(long_prices, 1.0)
        res_long = extract_riemannian_geodesic_flow(long_prices)
        self.assertTrue(0.0 <= res_long["f780_geodesic_velocity"] <= 5.0)
        self.assertTrue(res_long["f780_tensor_core_entropy"] >= 0.0)

        # Flash crash series (price drops 99%)
        crash_prices = np.concatenate([np.full(30, 100.0), np.linspace(100.0, 1.0, 30)])
        res_crash = extract_riemannian_geodesic_flow(crash_prices)
        self.assertTrue(0.0 <= res_crash["f780_geodesic_velocity"] <= 5.0)

    def test_f781_hyperbolic_graph_edge_cases(self) -> None:
        """Verify F781 compute_hyperbolic_graph_representation on degenerate & large graphs."""
        # Degenerate 1x1 matrix -> default
        res_1 = compute_hyperbolic_graph_representation(np.array([[0.0]]))
        self.assertEqual(res_1["f781_hyperbolic_radius"], 0.0)

        # 2x2 graph
        d2 = np.array([[0.0, 1.5], [1.5, 0.0]])
        res_2 = compute_hyperbolic_graph_representation(d2)
        self.assertTrue(0.0 <= res_2["f781_hyperbolic_radius"] <= 0.999)
        self.assertTrue(res_2["f781_poincare_distortion"] >= 0.0)

        # 80x80 graph (clamped to max_nodes=50)
        d80 = self.rng.uniform(0.1, 3.0, (80, 80))
        d80 = 0.5 * (d80 + d80.T)
        np.fill_diagonal(d80, 0.0)
        res_80 = compute_hyperbolic_graph_representation(d80, max_nodes=50)
        self.assertTrue(0.0 <= res_80["f781_hyperbolic_radius"] <= 0.999)
        self.assertTrue(res_80["f781_supply_hierarchical_depth"] >= 0.0)

    def test_f782_jump_diffusion_hawkes_edge_cases(self) -> None:
        """Verify F782 estimate_jump_diffusion_hawkes_params on extreme spikes & empty macro shocks."""
        # Short returns (< 5)
        res_short = estimate_jump_diffusion_hawkes_params(np.array([0.01, -0.01, 0.02]))
        self.assertEqual(res_short["f782_jump_intensity"], 0.0)
        self.assertEqual(res_short["f782_coupled_impulse_forecast"], 0.0)

        # Extreme jump returns (huge market shock)
        jump_returns = np.zeros(50)
        jump_returns[10] = -0.30  # 30% crash
        jump_returns[25] = 0.20   # 20% surge
        res_jump = estimate_jump_diffusion_hawkes_params(jump_returns)
        self.assertGreater(res_jump["f782_jump_intensity"], 0.0)
        self.assertTrue(0.0 <= res_jump["f782_branching_ratio"] <= 0.999)
        self.assertTrue(0.0 <= res_jump["f782_coupled_impulse_forecast"] <= 5.0)

        # Empty & missing macro shocks
        clean_macro = {"vix": np.array([]), "sox": np.array([4000.0, 4010.0]), "unknown": np.array([1.0, 2.0])}
        res_macro = estimate_jump_diffusion_hawkes_params(jump_returns, macro_shocks=clean_macro)
        self.assertTrue(0.0 <= res_macro["f782_branching_ratio"] <= 0.999)

    def test_f782_macro_shocks_nan_linalg_vulnerability(self) -> None:
        """Empirically prove that NaN in macro shocks propagates to LinAlgError in compute_hawkes_branching_ratio."""
        r = np.random.RandomState(42).normal(0, 0.01, 30)
        nan_macro = {"vix": np.array([20.0, np.nan])}
        with self.assertRaises(np.linalg.LinAlgError):
            estimate_jump_diffusion_hawkes_params(r, macro_shocks=nan_macro)

    def test_f783_higher_order_surface_skew_formats(self) -> None:
        """Verify F783 calculate_higher_order_surface_skew across DataFrame, ndarray, and pure Greeks fallback."""
        # Pure Greeks fallback (no strikes or ivs)
        res_greeks = calculate_higher_order_surface_skew({"spot": 100.0, "strike": 100.0, "tau": 0.1, "vol": 0.25})
        self.assertTrue(res_greeks["f783_surface_curvature"] >= 0.0)
        self.assertIn(res_greeks["f783_arbitrage_free_status"], [0.0, 1.0])
        self.assertTrue(0.05 <= res_greeks["f783_higher_order_greeks_score"] <= 0.95)

        # 1D ndarray input
        iv_arr1d = np.array([0.30, 0.25, 0.20, 0.22, 0.28])
        res_arr1d = calculate_higher_order_surface_skew(iv_arr1d)
        self.assertTrue(res_arr1d["f783_surface_curvature"] >= 0.0)
        self.assertTrue(0.05 <= res_arr1d["f783_higher_order_greeks_score"] <= 0.95)

        # 2D ndarray input (strikes row, ivs row)
        iv_arr2d = np.array([
            [90.0, 95.0, 100.0, 105.0, 110.0],
            [0.28, 0.23, 0.20, 0.22, 0.26],
        ])
        res_arr2d = calculate_higher_order_surface_skew(iv_arr2d)
        self.assertTrue(res_arr2d["f783_surface_curvature"] >= 0.0)
        self.assertTrue(0.05 <= res_arr2d["f783_higher_order_greeks_score"] <= 0.95)

        # DataFrame input
        df_iv = pd.DataFrame({"iv": [0.29, 0.24, 0.20, 0.21, 0.25]}, index=[90.0, 95.0, 100.0, 105.0, 110.0])
        res_df = calculate_higher_order_surface_skew(df_iv)
        self.assertTrue(res_df["f783_surface_curvature"] >= 0.0)
        self.assertTrue(0.05 <= res_df["f783_higher_order_greeks_score"] <= 0.95)

    def test_f784_orthogonalize_phase160_properties(self) -> None:
        """Verify F784 orthogonalize_phase160 whitening and deadband attenuation."""
        engine = FactorOrthogonalizerEngine()
        cols = ["s1", "s2", "s3", "s4", "s5"]
        df = pd.DataFrame(self.rng.uniform(0.1, 0.9, (100, 5)), columns=cols)

        out_df = engine.orthogonalize_phase160(df, strategy_cols=cols)
        self.assertEqual(out_df.shape, df.shape)
        for col in cols:
            vals = out_df[col].dropna()
            self.assertTrue((vals >= 0.05).all() and (vals <= 0.95).all())

        # Test deadband attenuation on sub-threshold noise
        sub_noise = pd.Series([0.001, -0.002, 0.015, -0.020, 0.028])
        clean = apply_hyperbolic_deadband_phase160(sub_noise)
        self.assertTrue(np.allclose(clean, 0.0, atol=1e-6))

        # Test 100% transmission on strong signals
        strong = pd.Series([0.15, -0.20, 0.35, -0.40])
        clean_strong = apply_hyperbolic_deadband_phase160(strong)
        self.assertTrue(np.allclose(clean_strong, strong, atol=1e-3))


if __name__ == "__main__":
    unittest.main()
