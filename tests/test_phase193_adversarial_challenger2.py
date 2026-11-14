"""
tests/test_phase193_adversarial_challenger2.py
=============================================
Milestone 1 (Release R184 / Phase 193 Features F949, F950, F951)
Adversarial Challenge Test Harness — Challenger 2 (Mathematical Invariants & Latency SLA).

Mathematical Invariants & Properties Under Challenge:
  1. APS Eta Invariant Symmetry & Dirac Spectrum Hermiticity:
     - Hermiticity of Dirac operator D: D = D^dagger, with purely real spectrum.
     - Parity reflection antisymmetry of APS eta invariant: eta(-D) = -eta(D).
     - Exact zero eta invariant for symmetric spectrum D.
     - Hyperbolic deadband filter monotonicity and boundary suppression.
  2. SQA Transverse Ising Energy Minimization:
     - Ground state energy minimization against random spin ensembles:
       E(sigma*) <= mu(E_random) - 1.5 * sigma(E_random).
     - Deterministic spin alignment under dominant external fields (+h -> +1, -h -> -1).
     - Valid spin configurations sigma* in {-1, +1}^N, magnetization <sigma> in [-1, 1]^N.
  3. Persistent Sheaf Laplacian Positive Semi-Definiteness:
     - Quadratic form non-negativity: x^T L_F x >= 0 for all x in R^{N*k}.
     - Strictly non-negative spectrum: min_i lambda_i(L_F) >= 0.
     - Orthogonal projection idempotence P_harm^2 = P_harm and kernel annihilator L_F V_0 = 0.
  4. Monte Carlo 500-Stock Latency Benchmarks (100 Ticks):
     - P95 execution latency strictly < 15.0ms across all 3 engines (F949, F950, F951).
     - Scalability stress testing across N=1000 assets.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# F949 Non-Commutative Dirac Operator Spectral Flow
from src.core.non_commutative_dirac_spectral import (
    get_dirac_gamma_matrices,
    get_hermitian_dirac_generators,
    apply_hyperbolic_noise_deadband,
    compute_dirac_operator,
    compute_aps_eta_invariant,
    compute_spectral_flow,
    compute_spectral_flow_alpha,
    NonCommutativeDiracSpectralFlowEngine,
)

# F950 Quantum Annealing Combinatorial Arbitrage
from src.core.quantum_annealing_arbitrage import (
    build_qubo_coupling_matrix,
    solve_simulated_quantum_annealing,
    compute_quantum_arbitrage_weights,
    QuantumAnnealingCombinatorialArbitrageEngine,
)

# F951 Persistent Sheaf Cohomology Liquidity Transport
from src.core.persistent_sheaf_liquidity import (
    build_cellular_sheaf,
    compute_sheaf_laplacian,
    compute_persistent_sheaf_cohomology,
    compute_sheaf_cohomology_transport,
    PersistentSheafCohomologyLiquidityEngine,
)


class TestDiracSpectralAdversarial(unittest.TestCase):
    """Adversarial stress tests for F949 Dirac spectral invariants."""

    def test_adv_dirac_spectrum_hermiticity_and_real_eigenvalues(self):
        """Verify D = D^dagger and eigenvalues are strictly real across 100 adversarial inputs."""
        rng = np.random.default_rng(101)
        for i in range(100):
            T = rng.integers(5, 50)
            # Create adversarial price curves: random walks, spikes, extreme jumps
            if i % 5 == 0:
                # Extreme spikes
                prices = np.exp(rng.normal(0, 0.5, T).cumsum()) * 1e5
            elif i % 5 == 1:
                # Sub-penny stocks
                prices = np.exp(rng.normal(0, 0.2, T).cumsum()) * 1e-4
            elif i % 5 == 2:
                # Nan / inf contaminated
                prices = np.abs(rng.normal(100, 10, T))
                prices[rng.integers(0, T)] = np.nan
            elif i % 5 == 3:
                # Flat prices (zero returns)
                prices = np.full(T, 50.0)
            else:
                prices = np.abs(rng.normal(100, 15, T)) + 1.0

            volumes = np.abs(rng.normal(1e6, 5e5, T)) + 100.0
            gauge = rng.normal(0, 2.0, 4)

            D = compute_dirac_operator(prices=prices, volumes=volumes, gauge_potential=gauge)

            # 1. Hermiticity check: D - D^dagger == 0
            diff = D - D.conj().T
            max_herm_err = np.max(np.abs(diff))
            self.assertLess(max_herm_err, 1e-12, f"Dirac operator is not Hermitian at iter {i}: {max_herm_err}")

            # 2. Eigenvalues must have zero imaginary part
            raw_eigs = np.linalg.eigvals(D)
            max_imag = np.max(np.abs(np.imag(raw_eigs)))
            self.assertLess(max_imag, 1e-12, f"Eigenvalues have non-zero imaginary parts at iter {i}: {max_imag}")

    def test_adv_aps_eta_invariant_antisymmetry_under_negation(self):
        """Verify mathematical theorem: eta(-D) = -eta(D), i.e., eta(D) + eta(-D) == 0."""
        rng = np.random.default_rng(202)
        for dim in [4, 8, 16, 32]:
            for _ in range(20):
                # Generate random Hermitian matrix
                M = rng.normal(0, 1.0, (dim, dim)) + 1j * rng.normal(0, 1.0, (dim, dim))
                D = 0.5 * (M + M.conj().T)

                eta_pos = compute_aps_eta_invariant(D, s_param=0.50)
                eta_neg = compute_aps_eta_invariant(-D, s_param=0.50)

                sum_eta = eta_pos + eta_neg
                self.assertAlmostEqual(
                    sum_eta, 0.0, places=9,
                    msg=f"Antisymmetry violation: eta(D)={eta_pos}, eta(-D)={eta_neg}, sum={sum_eta}"
                )

    def test_adv_aps_eta_invariant_exact_zero_on_symmetric_spectrum(self):
        """Verify eta(D) == 0.0 for matrices with strictly symmetric spectrum {+lambda, -lambda}."""
        rng = np.random.default_rng(303)
        for m in [2, 4, 8]:
            for _ in range(15):
                # Block anti-diagonal matrix D = [[0, A], [A^dagger, 0]] has symmetric spectrum
                A = rng.normal(0, 1.0, (m, m)) + 1j * rng.normal(0, 1.0, (m, m))
                zeros = np.zeros((m, m), dtype=np.complex128)
                D = np.block([[zeros, A], [A.conj().T, zeros]])

                eta_val = compute_aps_eta_invariant(D, s_param=0.50)
                self.assertAlmostEqual(
                    eta_val, 0.0, places=9,
                    msg=f"Symmetric spectrum did not yield eta=0: {eta_val}"
                )

    def test_adv_hyperbolic_deadband_monotonicity_and_suppression(self):
        """Verify deadband filter is strictly monotonically non-decreasing and zero at origin."""
        x = np.linspace(-1.0, 1.0, 1000)
        y = apply_hyperbolic_noise_deadband(x, delta=0.030, alpha=600.0)

        # Monotonicity
        diffs = np.diff(y)
        self.assertTrue(np.all(diffs >= -1e-12), "Deadband filter violated monotonicity")

        # Zero at origin
        self.assertAlmostEqual(apply_hyperbolic_noise_deadband(0.0), 0.0, places=10)

        # Symmetry: deadband(-x) == -deadband(x)
        y_neg = apply_hyperbolic_noise_deadband(-x, delta=0.030, alpha=600.0)
        np.testing.assert_allclose(y, -y_neg, atol=1e-10)

        # Sub-threshold micro-noise suppression
        self.assertLess(abs(apply_hyperbolic_noise_deadband(0.015, delta=0.030, alpha=600.0)), 1e-4)


class TestQuantumAnnealingAdversarial(unittest.TestCase):
    """Adversarial stress tests for F950 Quantum Annealing Ising invariants."""

    def test_adv_sqa_transverse_ising_energy_minimization_vs_random(self):
        """Verify SQA finds ground state spins with significantly lower energy than random spin ensembles."""
        rng = np.random.default_rng(404)
        z_scores_list = []

        for trial in range(30):
            N = rng.integers(15, 60)
            # Create synthetic price matrix with correlated structure
            T = 80
            factors = rng.normal(0, 0.01, (T, 3))
            loadings = rng.normal(0, 1.0, (3, N))
            returns = factors @ loadings + rng.normal(0, 0.005, (T, N))
            prices = np.exp(returns.cumsum(axis=0)) * 100.0

            J, h = build_qubo_coupling_matrix(prices, lambda_budget=1.0)

            # Solve SQA
            best_spins, magnetization = solve_simulated_quantum_annealing(
                J_matrix=J,
                h_vector=h,
                trotter_slices=8,
                num_sweeps=100,
                seed=42 + trial,
            )

            # Calculate SQA classical Ising energy: E = -0.5 * sigma @ J @ sigma - h @ sigma
            E_sqa = -0.5 * float(best_spins @ J @ best_spins) - float(h @ best_spins)

            # Sample 300 random spin configurations
            rand_spins = rng.choice([-1.0, 1.0], size=(300, N))
            # Batch energy evaluation
            E_rands = -0.5 * np.sum((rand_spins @ J) * rand_spins, axis=1) - rand_spins @ h

            mean_rand = np.mean(E_rands)
            std_rand = np.std(E_rands) + 1e-8
            z_score = (E_sqa - mean_rand) / std_rand
            z_scores_list.append(z_score)

            # SQA energy MUST be lower than the random mean
            self.assertLess(
                E_sqa, mean_rand,
                f"Trial {trial}: SQA energy {E_sqa} was not lower than random mean {mean_rand}"
            )

        # Average energy z-score across 30 trials should be strongly negative (e.g. < -2.0)
        avg_z = np.mean(z_scores_list)
        self.assertLess(
            avg_z, -2.0,
            f"SQA energy z-score average {avg_z} is not sufficiently below random distribution"
        )

    def test_adv_sqa_extreme_magnetic_field_deterministic_alignment(self):
        """Under overwhelming magnetic field |h| >> ||J||, spins must align deterministically with sign(h)."""
        rng = np.random.default_rng(505)
        N = 30
        J = rng.normal(0, 0.1, (N, N))
        J = 0.5 * (J + J.T)
        np.fill_diagonal(J, 0.0)

        # Extreme positive field -> all +1 spins
        h_pos = np.full(N, 500.0)
        spins_pos, mag_pos = solve_simulated_quantum_annealing(J, h_pos, trotter_slices=8, num_sweeps=50)
        np.testing.assert_array_equal(spins_pos, np.ones(N))
        np.testing.assert_allclose(mag_pos, np.ones(N), atol=1e-3)

        # Extreme negative field -> all -1 spins
        h_neg = np.full(N, -500.0)
        spins_neg, mag_neg = solve_simulated_quantum_annealing(J, h_neg, trotter_slices=8, num_sweeps=50)
        np.testing.assert_array_equal(spins_neg, -np.ones(N))
        np.testing.assert_allclose(mag_neg, -np.ones(N), atol=1e-3)

        # Alternating field -> alternating spins
        h_alt = np.array([500.0 if i % 2 == 0 else -500.0 for i in range(N)])
        expected_spins = np.array([1.0 if i % 2 == 0 else -1.0 for i in range(N)])
        spins_alt, _ = solve_simulated_quantum_annealing(J, h_alt, trotter_slices=8, num_sweeps=50)
        np.testing.assert_array_equal(spins_alt, expected_spins)

    def test_adv_quantum_arbitrage_weights_bounds_and_dtype(self):
        """Verify compute_quantum_arbitrage_weights output is strictly bounded in [-3.0, 3.0] and float32."""
        rng = np.random.default_rng(606)
        for N in [10, 50, 150, 500]:
            # Generate ill-conditioned correlation matrix
            X = rng.normal(0, 1.0, (100, N))
            corr = np.corrcoef(X, rowvar=False)
            spread = rng.normal(0, 5.0, N)

            weights = compute_quantum_arbitrage_weights(corr, spread)

            self.assertEqual(len(weights), N)
            self.assertEqual(weights.dtype, np.float32)
            self.assertTrue(np.all(np.isfinite(weights)))
            self.assertTrue(np.all(weights >= -3.0))
            self.assertTrue(np.all(weights <= 3.0))


class TestPersistentSheafLaplacianAdversarial(unittest.TestCase):
    """Adversarial stress tests for F951 Sheaf Laplacian PSD and cohomology invariants."""

    def test_adv_sheaf_laplacian_psd_random_quadratic_forms(self):
        """Verify positive semi-definiteness: x^T L_F x >= 0 for all x across diverse graph topologies."""
        rng = np.random.default_rng(707)

        # Test on 10 distinct topological graphs
        topologies = [
            ("complete_k8", np.ones((8, 8)) - np.eye(8)),
            ("star_10", self._make_star_graph(10)),
            ("cycle_12", self._make_cycle_graph(12)),
            ("disconnected_16", self._make_disconnected_graph(16)),
            ("random_dense_20", (rng.uniform(0, 1, (20, 20)) > 0.3).astype(float)),
            ("random_sparse_25", (rng.uniform(0, 1, (25, 25)) > 0.85).astype(float)),
        ]

        for name, adj in topologies:
            # Symmetrize adjacency
            adj = 0.5 * (adj + adj.T)
            np.fill_diagonal(adj, 0.0)
            N = adj.shape[0]

            for stalk_dim in [1, 2, 3]:
                node_feats = rng.normal(0, 2.0, (N, stalk_dim))
                L, _ = build_cellular_sheaf(adj, node_feats, stalk_dim=stalk_dim)

                dim = N * stalk_dim
                # 1. Eigenvalues must all be >= 0 (strictly positive with regularization)
                evals = np.linalg.eigvalsh(L)
                min_eval = float(np.min(evals))
                self.assertGreaterEqual(
                    min_eval, 0.0,
                    f"Topological graph {name} with stalk_dim {stalk_dim} has negative eigenvalue: {min_eval}"
                )

                # 2. Quadratic forms x^T L x >= 0 for 200 random vectors
                X_rand = rng.normal(0, 1.0, (200, dim))
                # Normalize vectors
                X_rand /= np.linalg.norm(X_rand, axis=1, keepdims=True)
                quad_forms = np.sum((X_rand @ L) * X_rand, axis=1)

                min_quad = float(np.min(quad_forms))
                self.assertGreaterEqual(
                    min_quad, -1e-9,
                    f"Topological graph {name} with stalk_dim {stalk_dim} violated PSD quadratic form: min={min_quad}"
                )

    def test_adv_sheaf_cohomology_harmonic_projector_idempotence(self):
        """Verify harmonic kernel projection P_harm = V_0 V_0^T satisfies P^2 = P and P^T = P."""
        rng = np.random.default_rng(808)
        adj = np.ones((6, 6)) - np.eye(6)
        node_feats = rng.normal(0, 1.0, (6, 2))
        L, _ = build_cellular_sheaf(adj, node_feats, stalk_dim=2)

        cohom = compute_persistent_sheaf_cohomology(L, num_nodes=6, stalk_dim=2, tol=1e-3)
        P = cohom["harmonic_projection"]

        # Symmetry: P == P.T
        np.testing.assert_allclose(P, P.T, atol=1e-10)

        # Idempotence: P @ P == P
        np.testing.assert_allclose(P @ P, P, atol=1e-8)

    def test_adv_sheaf_transport_bounds_and_dtype(self):
        """Verify compute_sheaf_cohomology_transport output is strictly in [-3.0, 3.0] and float32."""
        rng = np.random.default_rng(909)
        for N in [10, 64, 128, 500]:
            depth = np.abs(rng.normal(1e5, 5e4, (N, 2))) + 1.0
            turnover = np.abs(rng.normal(0, 0.5, (N, N)))
            turnover = 0.5 * (turnover + turnover.T)
            np.fill_diagonal(turnover, 0.0)

            alpha = compute_sheaf_cohomology_transport(depth, turnover)

            self.assertEqual(len(alpha), N)
            self.assertEqual(alpha.dtype, np.float32)
            self.assertTrue(np.all(np.isfinite(alpha)))
            self.assertTrue(np.all(alpha >= -3.0))
            self.assertTrue(np.all(alpha <= 3.0))

    @staticmethod
    def _make_star_graph(n: int) -> np.ndarray:
        adj = np.zeros((n, n))
        adj[0, 1:] = 1.0
        adj[1:, 0] = 1.0
        return adj

    @staticmethod
    def _make_cycle_graph(n: int) -> np.ndarray:
        adj = np.zeros((n, n))
        for i in range(n):
            adj[i, (i + 1) % n] = 1.0
            adj[(i + 1) % n, i] = 1.0
        return adj

    @staticmethod
    def _make_disconnected_graph(n: int) -> np.ndarray:
        adj = np.zeros((n, n))
        half = n // 2
        adj[:half, :half] = 1.0
        adj[half:, half:] = 1.0
        np.fill_diagonal(adj, 0.0)
        return adj


class TestMonteCarloLatencySLA(unittest.TestCase):
    """
    Monte Carlo Latency SLA Verification:
    Executes 100 Monte Carlo ticks across 500 stocks.
    Requires strictly P95 < 15.0ms for all 3 engines.
    """

    def test_adv_monte_carlo_500_stocks_100_ticks_dirac_sla(self):
        """Measure F949 Non-Commutative Dirac Spectral Flow latency across 100 ticks of 500 stocks."""
        rng = np.random.default_rng(1001)
        N = 500
        T = 30
        latencies_ms = []

        # Warm-up tick
        w_rets = rng.normal(0, 0.01, (T, N))
        w_vols = np.abs(rng.normal(0.2, 0.05, N))
        _ = compute_spectral_flow_alpha(w_rets, w_vols)

        for tick in range(100):
            rets = rng.normal(0, 0.01, (T, N))
            vols = np.abs(rng.normal(0.2, 0.05, N))

            t0 = time.perf_counter()
            alpha = compute_spectral_flow_alpha(rets, vols)
            t1 = time.perf_counter()

            dt_ms = (t1 - t0) * 1000.0
            latencies_ms.append(dt_ms)
            self.assertEqual(len(alpha), N)

        lat_arr = np.array(latencies_ms)
        p50 = float(np.percentile(lat_arr, 50))
        p90 = float(np.percentile(lat_arr, 90))
        p95 = float(np.percentile(lat_arr, 95))
        p99 = float(np.percentile(lat_arr, 99))
        mean_lat = float(np.mean(lat_arr))

        print(f"\n[F949 Dirac Spectral Flow SLA 500 Stocks / 100 Ticks]: Mean={mean_lat:.2f}ms, P50={p50:.2f}ms, P90={p90:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        self.assertLess(p95, 15.0, f"F949 P95 latency {p95:.2f}ms exceeded 15.0ms SLA")

    def test_adv_monte_carlo_500_stocks_100_ticks_quantum_annealing_sla(self):
        """Measure F950 Quantum Annealing Arbitrage latency across 100 ticks of 500 stocks."""
        rng = np.random.default_rng(1002)
        N = 500
        latencies_ms = []

        # Warm-up tick
        w_corr = np.eye(N, dtype=np.float64)
        w_spread = rng.normal(0, 1.0, N)
        _ = compute_quantum_arbitrage_weights(w_corr, w_spread)

        for tick in range(100):
            # Generate random 5-factor correlation matrix for 500 stocks
            K = 5
            loadings = rng.normal(0, 1.0, (N, K))
            cov = loadings @ loadings.T + np.eye(N) * 0.2
            std_diag = np.sqrt(np.diag(cov))
            corr = cov / np.outer(std_diag, std_diag)
            spread = rng.normal(0, 2.0, N)

            t0 = time.perf_counter()
            weights = compute_quantum_arbitrage_weights(corr, spread)
            t1 = time.perf_counter()

            dt_ms = (t1 - t0) * 1000.0
            latencies_ms.append(dt_ms)
            self.assertEqual(len(weights), N)

        lat_arr = np.array(latencies_ms)
        p50 = float(np.percentile(lat_arr, 50))
        p90 = float(np.percentile(lat_arr, 90))
        p95 = float(np.percentile(lat_arr, 95))
        p99 = float(np.percentile(lat_arr, 99))
        mean_lat = float(np.mean(lat_arr))

        print(f"\n[F950 Quantum Annealing SLA 500 Stocks / 100 Ticks]: Mean={mean_lat:.2f}ms, P50={p50:.2f}ms, P90={p90:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        self.assertLess(p95, 15.0, f"F950 P95 latency {p95:.2f}ms exceeded 15.0ms SLA")

    def test_adv_monte_carlo_500_stocks_100_ticks_persistent_sheaf_sla(self):
        """Measure F951 Persistent Sheaf Cohomology latency across 100 ticks of 500 stocks."""
        rng = np.random.default_rng(1003)
        N = 500
        latencies_ms = []

        # Warm-up tick
        w_depth = np.abs(rng.normal(1e5, 1e4, (N, 2)))
        w_turnover = np.abs(rng.normal(0, 0.1, (N, N)))
        _ = compute_sheaf_cohomology_transport(w_depth, w_turnover)

        for tick in range(100):
            depth = np.abs(rng.normal(1e5, 2e4, (N, 2))) + 1.0
            turnover = np.abs(rng.normal(0, 0.2, (N, N)))
            turnover = 0.5 * (turnover + turnover.T)

            t0 = time.perf_counter()
            alpha = compute_sheaf_cohomology_transport(depth, turnover)
            t1 = time.perf_counter()

            dt_ms = (t1 - t0) * 1000.0
            latencies_ms.append(dt_ms)
            self.assertEqual(len(alpha), N)

        lat_arr = np.array(latencies_ms)
        p50 = float(np.percentile(lat_arr, 50))
        p90 = float(np.percentile(lat_arr, 90))
        p95 = float(np.percentile(lat_arr, 95))
        p99 = float(np.percentile(lat_arr, 99))
        mean_lat = float(np.mean(lat_arr))

        print(f"\n[F951 Persistent Sheaf SLA 500 Stocks / 100 Ticks]: Mean={mean_lat:.2f}ms, P50={p50:.2f}ms, P90={p90:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        self.assertLess(p95, 15.0, f"F951 P95 latency {p95:.2f}ms exceeded 15.0ms SLA")

    def test_adv_monte_carlo_1000_stocks_scalability_stress(self):
        """Stress-test scalability across 1000 stocks for 10 ticks."""
        rng = np.random.default_rng(2001)
        N = 1000
        T = 20

        # F949
        rets = rng.normal(0, 0.01, (T, N))
        vols = np.abs(rng.normal(0.2, 0.05, N))
        t0 = time.perf_counter()
        alpha_f949 = compute_spectral_flow_alpha(rets, vols)
        t_f949 = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(len(alpha_f949), N)

        # F950
        K = 5
        loadings = rng.normal(0, 1.0, (N, K))
        cov = loadings @ loadings.T + np.eye(N) * 0.2
        std_diag = np.sqrt(np.diag(cov))
        corr = cov / np.outer(std_diag, std_diag)
        spread = rng.normal(0, 2.0, N)
        t0 = time.perf_counter()
        alpha_f950 = compute_quantum_arbitrage_weights(corr, spread)
        t_f950 = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(len(alpha_f950), N)

        # F951
        depth = np.abs(rng.normal(1e5, 2e4, (N, 2))) + 1.0
        turnover = np.abs(rng.normal(0, 0.2, (N, N)))
        turnover = 0.5 * (turnover + turnover.T)
        t0 = time.perf_counter()
        alpha_f951 = compute_sheaf_cohomology_transport(depth, turnover)
        t_f951 = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(len(alpha_f951), N)

        print(f"\n[1000 Stocks Scalability]: F949={t_f949:.2f}ms, F950={t_f950:.2f}ms, F951={t_f951:.2f}ms")
        # Ensure finite, bounded
        self.assertTrue(np.all(np.isfinite(alpha_f949)))
        self.assertTrue(np.all(np.isfinite(alpha_f950)))
        self.assertTrue(np.all(np.isfinite(alpha_f951)))


if __name__ == "__main__":
    unittest.main()
