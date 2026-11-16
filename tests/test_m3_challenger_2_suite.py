"""
tests/test_m3_challenger_2_suite.py
Empirical Optimization & Convergence Challenger Suite for Milestone 3 (M3: Factor Risk Parity).
Target Module: src/risk/unified_portfolio_allocator.py -> calculate_factor_risk_parity_weights, compute_factor_risk_contributions, optimize_multi_model_blend
Authored by: Challenger 2 (Portfolio Optimization & Convergence Challenger)

Quantitative Verification Criteria:
1. Factor Risk Parity Convergence: 100 random multi-asset universes (N=20, K=5 to 15), SLSQP converges in <= 100 iterations.
2. PFRC Dispersion Reduction Proof: Dispersion(w_FRP) < 0.50 * Dispersion(w_Asset_RP) for lambda_FRP = 10.0.
3. Multi-Model Blend Integration & Telemetry: verify self.last_factor_risk_decomposition (mfrc, pfrc, irr, frp_imbalance) and Euler sum == 1.0.
4. Latency Benchmark: Assert calculate_factor_risk_parity_weights completes in < 35 ms on standard candidate universes (N <= 25, K <= 10).
5. Invariant Integrity: synthetic_rows == 0 (native int 0).
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    calculate_factor_risk_parity_weights,
    compute_factor_risk_contributions,
)
from src.analysis.portfolio_optimizer import calculate_risk_parity_weights


class TestFRPConvergence100Universes(unittest.TestCase):
    """
    Quantitative Verification 1:
    Test calculate_factor_risk_parity_weights across 100 random multi-asset universes
    (N=20, K=5 to K=15) to verify the solver converges without error in <= 100 iterations.
    """

    def setUp(self) -> None:
        np.random.seed(42)

    def test_frp_convergence_100_random_universes(self) -> None:
        """Verify 100/100 random universes converge with valid weights summing to 1.0 within bounds."""
        N = 20
        max_cap = 0.20
        success_count = 0

        for trial in range(100):
            K = np.random.randint(5, 16)  # K from 5 to 15 inclusive
            B = np.random.randn(N, K)
            A = np.random.randn(K, K)
            Omega_F = A.T @ A + np.eye(K) * 1e-3
            D_idio = np.random.uniform(0.01, 0.05, size=N)
            cov = B @ Omega_F @ B.T + np.diag(D_idio)

            w = calculate_factor_risk_parity_weights(
                cov_matrix=cov,
                factor_loadings=B,
                factor_covariance=Omega_F,
                idiosyncratic_vars=D_idio,
                max_single_stock_weight=max_cap,
                lambda_frp=5.0,
                max_iter=100,
            )

            # 1. Output array shape and finiteness
            self.assertEqual(len(w), N, f"Trial {trial}: Expected weight vector length {N}")
            self.assertTrue(np.all(np.isfinite(w)), f"Trial {trial}: Non-finite weights produced: {w}")

            # 2. Probability simplex constraints: sum(w) == 1.0 within 1e-4
            weight_sum = float(np.sum(w))
            self.assertAlmostEqual(
                weight_sum, 1.0, places=4,
                msg=f"Trial {trial}: Portfolio weights sum {weight_sum} != 1.0"
            )

            # 3. Lower and upper bounds: 0 <= w_i <= max_cap
            self.assertTrue(
                np.all(w >= -1e-6),
                f"Trial {trial}: Negative weights encountered: min(w) = {np.min(w)}"
            )
            self.assertTrue(
                np.all(w <= max_cap + 1e-4),
                f"Trial {trial}: Weight cap exceeded: max(w) = {np.max(w)} > {max_cap}"
            )

            success_count += 1

        self.assertEqual(success_count, 100, "Expected all 100 random universes to converge successfully.")

    def test_frp_convergence_varying_universe_sizes(self) -> None:
        """Stress-test solver convergence across heterogeneous dimensions N in [5, 10, 15, 25], K in [2, 5, 8]."""
        for N in [5, 10, 15, 25]:
            for K in [2, 5, 8]:
                if K >= N:
                    continue
                B = np.random.randn(N, K)
                Omega_F = np.eye(K) * 0.04
                D_idio = np.ones(N) * 0.02
                cov = B @ Omega_F @ B.T + np.diag(D_idio)
                cap = max(0.20, 1.0 / N + 0.05)

                w = calculate_factor_risk_parity_weights(
                    cov_matrix=cov,
                    factor_loadings=B,
                    factor_covariance=Omega_F,
                    idiosyncratic_vars=D_idio,
                    max_single_stock_weight=cap,
                    lambda_frp=2.0,
                )
                self.assertEqual(len(w), N)
                self.assertAlmostEqual(float(np.sum(w)), 1.0, places=4)
                self.assertTrue(np.all(w >= -1e-6))


class TestPFRCDispersionReductionProof(unittest.TestCase):
    """
    Quantitative Verification 2:
    PFRC Dispersion Reduction Proof:
    Quantitatively verify that for lambda_FRP = 10.0, the factor risk contribution dispersion:
        Dispersion(w) = sum_{k=1}^K (PFRC_k - 1/K)^2
    is strictly lower than for lambda_FRP = 0.0 (and standard asset-level risk parity):
        Dispersion(w_FRP) < 0.50 * Dispersion(w_Asset_RP)
    """

    def setUp(self) -> None:
        np.random.seed(42)

    def test_dispersion_reduction_heterogeneous_factor_loadings(self) -> None:
        """Deterministic proof on structured heterogeneous factor loadings."""
        N, K = 15, 3
        B = np.array([
            [2.0, 0.1, 0.1],
            [1.8, 0.2, 0.1],
            [1.5, 0.1, 0.2],
            [0.1, 1.5, 0.2],
            [0.2, 1.8, 0.1],
            [0.1, 0.2, 1.9],
            [0.2, 0.1, 1.7],
            [1.0, 0.5, 0.5],
            [0.5, 1.0, 0.5],
            [0.5, 0.5, 1.0],
            [0.3, 0.3, 0.3],
            [0.8, 0.2, 0.2],
            [0.2, 0.8, 0.2],
            [0.2, 0.2, 0.8],
            [1.2, 0.3, 0.3],
        ])

        Omega_F = np.eye(K) * 0.05
        D_idio = np.full(N, 0.02)
        cov = B @ Omega_F @ B.T + np.diag(D_idio)

        # 1. Factor Risk Parity (lambda_FRP = 10.0)
        w_frp = calculate_factor_risk_parity_weights(
            cov_matrix=cov,
            factor_loadings=B,
            factor_covariance=Omega_F,
            idiosyncratic_vars=D_idio,
            lambda_frp=10.0,
            max_single_stock_weight=0.25,
        )

        # 2. Minimum Variance (lambda_FRP = 0.0)
        w_lambda0 = calculate_factor_risk_parity_weights(
            cov_matrix=cov,
            factor_loadings=B,
            factor_covariance=Omega_F,
            idiosyncratic_vars=D_idio,
            lambda_frp=0.0,
            max_single_stock_weight=0.25,
        )

        # 3. Standard Asset-Level Risk Parity
        w_asset_rp = calculate_risk_parity_weights(cov)

        _, pfrc_frp, _ = compute_factor_risk_contributions(w_frp, B, Omega_F, D_idio)
        _, pfrc_l0, _ = compute_factor_risk_contributions(w_lambda0, B, Omega_F, D_idio)
        _, pfrc_arp, _ = compute_factor_risk_contributions(w_asset_rp, B, Omega_F, D_idio)

        target = 1.0 / K
        disp_frp = float(np.sum((pfrc_frp - target) ** 2))
        disp_l0 = float(np.sum((pfrc_l0 - target) ** 2))
        disp_arp = float(np.sum((pfrc_arp - target) ** 2))

        # Proof: Dispersion(w_FRP) < 0.50 * Dispersion(w_Asset_RP)
        ratio_arp = disp_frp / disp_arp
        ratio_l0 = disp_frp / disp_l0

        self.assertLess(
            disp_frp, 0.50 * disp_arp,
            f"FRP Dispersion ({disp_frp:.6e}) is not < 0.50 * Asset RP Dispersion ({disp_arp:.6e}), ratio={ratio_arp:.4f}"
        )
        self.assertLess(
            disp_frp, 0.50 * disp_l0,
            f"FRP Dispersion ({disp_frp:.6e}) is not < 0.50 * Lambda=0 Dispersion ({disp_l0:.6e}), ratio={ratio_l0:.4f}"
        )

    def test_dispersion_reduction_multi_trial_proof(self) -> None:
        """Monte Carlo proof across 25 random multi-asset universes (N=20, K=5)."""
        N = 20
        K = 5
        ratios_arp = []
        ratios_l0 = []

        for trial in range(25):
            B = np.random.randn(N, K)
            # Induce factor loading asymmetry
            B[:, 0] *= 2.5
            B[:, 1] *= 1.8
            Omega_F = np.eye(K) * 0.04
            D_idio = np.random.uniform(0.01, 0.04, size=N)
            cov = B @ Omega_F @ B.T + np.diag(D_idio)

            w_frp = calculate_factor_risk_parity_weights(
                cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio,
                lambda_frp=10.0, max_single_stock_weight=0.20
            )
            w_l0 = calculate_factor_risk_parity_weights(
                cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio,
                lambda_frp=0.0, max_single_stock_weight=0.20
            )
            w_arp = calculate_risk_parity_weights(cov)

            _, pfrc_frp, _ = compute_factor_risk_contributions(w_frp, B, Omega_F, D_idio)
            _, pfrc_l0, _ = compute_factor_risk_contributions(w_l0, B, Omega_F, D_idio)
            _, pfrc_arp, _ = compute_factor_risk_contributions(w_arp, B, Omega_F, D_idio)

            target = 1.0 / K
            disp_frp = float(np.sum((pfrc_frp - target) ** 2))
            disp_l0 = float(np.sum((pfrc_l0 - target) ** 2))
            disp_arp = float(np.sum((pfrc_arp - target) ** 2))

            r_arp = disp_frp / max(1e-12, disp_arp)
            r_l0 = disp_frp / max(1e-12, disp_l0)

            ratios_arp.append(r_arp)
            ratios_l0.append(r_l0)

            # Strict assertion per trial
            self.assertLess(
                r_arp, 0.50,
                f"Trial {trial}: Ratio vs Asset RP {r_arp:.4f} >= 0.50 (Disp FRP={disp_frp:.6e}, Disp ARP={disp_arp:.6e})"
            )
            self.assertLess(
                r_l0, 0.50,
                f"Trial {trial}: Ratio vs Lambda=0 {r_l0:.4f} >= 0.50 (Disp FRP={disp_frp:.6e}, Disp L0={disp_l0:.6e})"
            )

        mean_reduction_arp = float(np.mean(ratios_arp))
        self.assertLess(
            mean_reduction_arp, 0.10,
            f"Mean dispersion ratio {mean_reduction_arp:.4f} indicates insufficient factor equalization."
        )

    def test_dispersion_monotonic_lambda_response(self) -> None:
        """Verifies that increasing lambda_FRP monotonically drives factor risk dispersion down."""
        N, K = 15, 3
        B = np.random.randn(N, K)
        B[:, 0] *= 3.0
        Omega_F = np.eye(K) * 0.05
        D_idio = np.ones(N) * 0.02
        cov = B @ Omega_F @ B.T + np.diag(D_idio)

        lambdas = [0.0, 0.5, 2.0, 10.0, 30.0]
        dispersions = []

        for lam in lambdas:
            w = calculate_factor_risk_parity_weights(
                cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio,
                lambda_frp=lam, max_single_stock_weight=0.25
            )
            _, pfrc, _ = compute_factor_risk_contributions(w, B, Omega_F, D_idio)
            disp = float(np.sum((pfrc - 1.0 / K) ** 2))
            dispersions.append(disp)

        # Dispersion at lambda=30 must be strictly less than at lambda=0
        self.assertLess(dispersions[-1], dispersions[0] * 0.10)
        # Check overall downward trend
        self.assertLess(dispersions[3], dispersions[1])


class TestMultiModelBlendIntegrationAndTelemetry(unittest.TestCase):
    """
    Quantitative Verification 3:
    Integration in optimize_multi_model_blend:
    Test full blend optimization with factor_loadings provided vs factor_loadings=None.
    Verify telemetry on self.last_factor_risk_decomposition.
    """

    def setUp(self) -> None:
        np.random.seed(42)
        self.symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        self.n = len(self.symbols)
        dates = pd.date_range("2025-01-01", periods=60)
        rets_data = np.random.randn(60, self.n) * 0.015
        self.returns_df = pd.DataFrame(rets_data, index=dates, columns=self.symbols)
        self.cov_matrix = np.cov(rets_data.T)
        self.predicted_returns = np.array([0.02 + 0.005 * i for i in range(self.n)])
        self.K = 3
        self.B = np.random.randn(self.n, self.K)

    def test_blend_with_factor_loadings_populates_telemetry(self) -> None:
        """When factor_loadings is supplied, allocator records valid decomposition telemetry."""
        allocator = UnifiedPortfolioAllocator()
        self.assertIsNone(allocator.last_factor_risk_decomposition)

        w_blend = allocator.optimize_multi_model_blend(
            symbols=self.symbols,
            predicted_returns=self.predicted_returns,
            cov_matrix=self.cov_matrix,
            returns_df=self.returns_df,
            factor_loadings=self.B,
            enable_factor_risk_parity=True,
        )

        # 1. Output weights validation
        self.assertEqual(len(w_blend), self.n)
        self.assertTrue(np.all(np.isfinite(w_blend)))
        self.assertTrue(np.all(w_blend >= -1e-6))
        self.assertLessEqual(float(np.sum(w_blend)), 1.0001)

        # 2. Telemetry structure validation
        telemetry = allocator.last_factor_risk_decomposition
        self.assertIsNotNone(telemetry, "last_factor_risk_decomposition must be populated when factor_loadings provided")
        self.assertIsInstance(telemetry, dict)
        for key in ["mfrc", "pfrc", "irr", "frp_imbalance"]:
            self.assertIn(key, telemetry, f"Missing telemetry key: {key}")

        # 3. Euler Homogeneous Decomposition Identity: sum(pfrc) + irr == 1.0
        pfrc = telemetry["pfrc"]
        irr = telemetry["irr"]
        euler_sum = float(np.sum(pfrc) + irr)
        self.assertAlmostEqual(
            euler_sum, 1.0, places=5,
            msg=f"Euler risk decomposition identity violated: sum(pfrc) + irr = {euler_sum}"
        )

        # 4. frp_imbalance correctness
        expected_imbalance = float(np.sum((pfrc - (1.0 / self.K)) ** 2))
        self.assertAlmostEqual(telemetry["frp_imbalance"], expected_imbalance, places=6)

    def test_blend_without_factor_loadings_telemetry_remains_none(self) -> None:
        """When factor_loadings=None, telemetry remains None and asset-level RP executes without error."""
        allocator = UnifiedPortfolioAllocator()
        self.assertIsNone(allocator.last_factor_risk_decomposition)

        w_blend = allocator.optimize_multi_model_blend(
            symbols=self.symbols,
            predicted_returns=self.predicted_returns,
            cov_matrix=self.cov_matrix,
            returns_df=self.returns_df,
            factor_loadings=None,
        )

        self.assertEqual(len(w_blend), self.n)
        self.assertTrue(np.all(np.isfinite(w_blend)))
        self.assertTrue(np.all(w_blend >= -1e-6))
        self.assertIsNone(
            allocator.last_factor_risk_decomposition,
            "last_factor_risk_decomposition must remain None when factor_loadings=None"
        )

    def test_blend_with_enable_factor_risk_parity_flag_toggle(self) -> None:
        """Toggling enable_factor_risk_parity=False reverts Model C to asset-level RP."""
        allocator = UnifiedPortfolioAllocator()
        w_disabled = allocator.optimize_multi_model_blend(
            symbols=self.symbols,
            predicted_returns=self.predicted_returns,
            cov_matrix=self.cov_matrix,
            returns_df=self.returns_df,
            factor_loadings=self.B,
            enable_factor_risk_parity=False,
        )
        self.assertEqual(len(w_disabled), self.n)
        self.assertTrue(np.all(np.isfinite(w_disabled)))


class TestLatencyBenchmark(unittest.TestCase):
    """
    Quantitative Verification 4:
    Latency benchmark: Assert that calculate_factor_risk_parity_weights completes in < 35 ms
    on standard candidate universes (N <= 25, K <= 10).
    """

    def setUp(self) -> None:
        np.random.seed(42)

    def test_latency_candidate_universe_n10_k3(self) -> None:
        """Assert < 35 ms average execution time on standard candidate universe N=10, K=3."""
        N, K = 10, 3
        B = np.random.randn(N, K)
        Omega_F = np.eye(K) * 0.04
        D_idio = np.ones(N) * 0.02
        cov = B @ Omega_F @ B.T + np.diag(D_idio)

        # Warm-up call
        _ = calculate_factor_risk_parity_weights(cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio)

        latencies = []
        for _ in range(25):
            t0 = time.perf_counter()
            _ = calculate_factor_risk_parity_weights(cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        mean_ms = float(np.mean(latencies))
        p95_ms = float(np.percentile(latencies, 95))
        min_ms = float(np.min(latencies))

        self.assertLess(
            mean_ms, 35.0,
            f"Mean latency {mean_ms:.2f} ms exceeded SLA threshold of 35 ms (p95={p95_ms:.2f}ms, min={min_ms:.2f}ms)"
        )

    def test_latency_candidate_universe_n10_k5(self) -> None:
        """Assert < 35 ms average execution time on candidate universe N=10, K=5."""
        N, K = 10, 5
        B = np.random.randn(N, K)
        Omega_F = np.eye(K) * 0.04
        D_idio = np.ones(N) * 0.02
        cov = B @ Omega_F @ B.T + np.diag(D_idio)

        _ = calculate_factor_risk_parity_weights(cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio)

        latencies = []
        for _ in range(25):
            t0 = time.perf_counter()
            _ = calculate_factor_risk_parity_weights(cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        mean_ms = float(np.mean(latencies))
        self.assertLess(
            mean_ms, 35.0,
            f"Mean latency {mean_ms:.2f} ms exceeded 35 ms threshold for N=10, K=5"
        )

    def test_latency_profile_logging(self) -> None:
        """Records latency profile across candidate sizes N in [5, 8, 10, 12]."""
        results = {}
        for N in [5, 8, 10, 12]:
            for K in [2, 3]:
                B = np.random.randn(N, K)
                Omega_F = np.eye(K) * 0.04
                D_idio = np.ones(N) * 0.02
                cov = B @ Omega_F @ B.T + np.diag(D_idio)

                # Warm-up call
                _ = calculate_factor_risk_parity_weights(cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio)

                times = []
                for _ in range(10):
                    t0 = time.perf_counter()
                    _ = calculate_factor_risk_parity_weights(cov, B, factor_covariance=Omega_F, idiosyncratic_vars=D_idio)
                    times.append((time.perf_counter() - t0) * 1000.0)

                key = f"N{N}_K{K}"
                results[key] = {
                    "mean_ms": round(float(np.mean(times)), 2),
                    "min_ms": round(float(np.min(times)), 2),
                }
                # Assert standard candidate universe sizes N <= 10 complete in < 35 ms
                if N <= 10:
                    self.assertLess(
                        results[key]["mean_ms"], 35.0,
                        f"Mean latency {results[key]['mean_ms']} ms exceeded SLA threshold of 35 ms for {key}"
                    )


class TestAdversarialStressAndBoundaryConditions(unittest.TestCase):
    """
    Adversarial Stress Testing & Edge Cases:
    Tests singular matrices, zero loadings, custom tilts, single asset, and system invariants.
    """

    def setUp(self) -> None:
        np.random.seed(42)

    def test_zero_factor_loadings_pure_idiosyncratic_portfolio(self) -> None:
        """When B = 0, calculate_factor_risk_parity_weights returns valid weights and IRR = 1.0."""
        N, K = 12, 3
        B = np.zeros((N, K))
        cov = np.eye(N) * 0.04
        w = calculate_factor_risk_parity_weights(cov, B)

        self.assertEqual(len(w), N)
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=5)
        self.assertTrue(np.all(w >= -1e-6))

        mfrc, pfrc, irr = compute_factor_risk_contributions(w, B, cov_matrix=cov)
        np.testing.assert_allclose(mfrc, np.zeros(K), atol=1e-12)
        np.testing.assert_allclose(pfrc, np.zeros(K), atol=1e-12)
        self.assertAlmostEqual(irr, 1.0, places=9)

    def test_collinear_factor_loadings_robustness(self) -> None:
        """Factor loadings with duplicate columns (rank deficient) do not cause crash or NaN."""
        N, K = 15, 4
        B = np.random.randn(N, K)
        B[:, 2] = B[:, 0]  # Column 2 identical to Column 0
        cov = B @ np.eye(K) @ B.T + np.eye(N) * 0.02

        w = calculate_factor_risk_parity_weights(cov, B, lambda_frp=2.0)
        self.assertEqual(len(w), N)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertAlmostEqual(float(np.sum(w)), 1.0, places=4)

    def test_custom_target_pfrc_factor_tilting(self) -> None:
        """Custom target_pfrc vector guides risk contributions toward asymmetric targets."""
        N, K = 12, 2
        B = np.random.randn(N, K)
        cov = B @ np.eye(K) @ B.T + np.eye(N) * 0.02
        custom_target = np.array([0.70, 0.30])

        w = calculate_factor_risk_parity_weights(
            cov, B, lambda_frp=15.0, target_pfrc=custom_target, max_single_stock_weight=0.25
        )
        _, pfrc, _ = compute_factor_risk_contributions(w, B, cov_matrix=cov)

        # Factor 0 should have higher risk contribution than Factor 1
        self.assertGreater(pfrc[0], pfrc[1], "Custom target tilting failed: PFRC[0] <= PFRC[1]")

    def test_single_asset_limit(self) -> None:
        """Single asset N=1 returns [1.0]."""
        cov = np.array([[0.04]])
        B = np.array([[1.0]])
        w = calculate_factor_risk_parity_weights(cov, B)
        np.testing.assert_array_equal(w, np.array([1.0]))

    def test_empty_asset_limit(self) -> None:
        """Empty input returns empty array."""
        w = calculate_factor_risk_parity_weights(np.zeros((0, 0)), np.zeros((0, 0)))
        self.assertEqual(len(w), 0)

    def test_system_invariant_zero_synthetic_rows(self) -> None:
        """Invariant: synthetic_rows == 0 strictly confirmed as native Python int 0."""
        status_path = "benchmarks/30year/status.json"
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        synth = status.get("synthetic_rows")
        self.assertTrue(
            isinstance(synth, int) and not isinstance(synth, bool) and synth == 0,
            f"synthetic_rows invariant violated: {synth} (type: {type(synth)})"
        )


if __name__ == "__main__":
    unittest.main()
