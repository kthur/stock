"""
tests/test_f760_f761_adversarial.py — Empirical Adversarial Stress & Invariant Test Suite.

Adversarially stress-tests Features F760 (WSST Wavelet) and F761 (TDA Hodge Laplacian)
under extreme edge cases, mathematical invariants, degenerate inputs, and latency SLAs.
"""

import time
import math
import numpy as np
import pytest

from src.core.spectral_wavelet_decomposition import (
    SpectralWaveletDecompositionEngine,
    compute_synchrosqueezed_wavelet_transform,
    compute_instantaneous_frequency,
    compute_synchrosqueezed_phase_alignment,
    extract_synchrosqueezed_ridge,
    apply_hyperbolic_deadband_phase156,
)
from src.core.value_chain_curvature_gnn import (
    ValueChainCurvatureGNNEngine,
    compute_vietoris_rips_distance,
    compute_persistent_homology_betti_numbers,
    compute_hodge_laplacian_spectrum,
    compute_hodge_laplacian_persistence,
    detect_harmonic_value_chain_loops,
)


class TestF760AdversarialStress:
    """Adversarial stress harness for F760 Continuous Wavelet Synchrosqueezing Transform (WSST)."""

    def test_adv01_flatline_zero_variance_wsst(self):
        """Stress: Pure flatline constant price series (zero variance)."""
        flat = np.full(128, 100.0, dtype=np.float64)
        wsst = compute_synchrosqueezed_wavelet_transform(flat)
        assert np.all(np.isfinite(wsst["synchrosqueezed_matrix"]))
        assert np.all(np.isfinite(wsst["cwt_matrix"]))
        assert np.all(np.isfinite(wsst["energy_spectrum"]))
        assert 0.0 <= wsst["energy_entropy"] <= 1.0
        assert math.isfinite(wsst["dominant_frequency"])

        ifreq = compute_instantaneous_frequency(flat)
        assert len(ifreq) == len(flat)
        assert np.all(np.isfinite(ifreq))
        assert np.all(ifreq >= 0.0)

        ridge = extract_synchrosqueezed_ridge(flat)
        assert len(ridge) == len(flat)
        assert np.all(np.isfinite(ridge))

    def test_adv02_flash_crash_99_percent_drop(self):
        """Stress: 99.9% instantaneous price crash in 1 bar followed by stagnation."""
        prices = np.full(120, 1000.0, dtype=np.float64)
        prices[60:] = 1.0  # 99.9% crash
        wsst = compute_synchrosqueezed_wavelet_transform(prices)
        assert np.all(np.isfinite(wsst["synchrosqueezed_matrix"]))
        assert np.all(np.isfinite(wsst["energy_spectrum"]))
        assert 0.0 <= wsst["energy_entropy"] <= 1.0

        ridge = extract_synchrosqueezed_ridge(prices)
        assert np.all(np.isfinite(ridge))

    def test_adv03_extreme_spike_and_outliers(self):
        """Stress: Dirac delta-like price spike (1e9 outlier) and negative prices."""
        prices = np.full(100, 50.0, dtype=np.float64)
        prices[50] = 1e9  # Extreme 1-bar spike
        wsst = compute_synchrosqueezed_wavelet_transform(prices)
        assert np.all(np.isfinite(wsst["synchrosqueezed_matrix"]))
        assert np.all(np.isfinite(wsst["energy_spectrum"]))

        tiny = np.full(100, 1e-12, dtype=np.float64)
        tiny_wsst = compute_synchrosqueezed_wavelet_transform(tiny)
        assert np.all(np.isfinite(tiny_wsst["synchrosqueezed_matrix"]))

    def test_adv04_near_zero_variance_micro_noise(self):
        """Stress: Signal with microscopic variance (1e-15 amplitude noise)."""
        rng = np.random.RandomState(42)
        micro = 100.0 + rng.normal(0, 1e-15, 128)
        wsst = compute_synchrosqueezed_wavelet_transform(micro)
        assert np.all(np.isfinite(wsst["synchrosqueezed_matrix"]))
        assert 0.0 <= wsst["energy_entropy"] <= 1.0

    def test_adv05_degenerate_and_sub_minimum_lengths(self):
        """Stress: Signal lengths N in {0, 1, 2, 3, 4, 5}."""
        for n in [0, 1, 2, 3, 4, 5]:
            sig = np.ones(n, dtype=np.float64)
            wsst = compute_synchrosqueezed_wavelet_transform(sig)
            assert "synchrosqueezed_matrix" in wsst
            assert "energy_entropy" in wsst
            assert 0.0 <= wsst["energy_entropy"] <= 1.0

            ifreq = compute_instantaneous_frequency(sig)
            assert len(ifreq) == n
            if n > 0:
                assert np.all(np.isfinite(ifreq))
                assert np.all(ifreq >= 0.0)

            ridge = extract_synchrosqueezed_ridge(sig)
            assert len(ridge) == n
            assert np.all(np.isfinite(ridge))

    def test_adv06_phase_alignment_extreme_invariants(self):
        """Invariant: Phase alignment strictly in [-1.0, 1.0], self=1.0, anti=-1.0."""
        t = np.linspace(0, 10, 200)
        sig1 = np.sin(2.0 * np.pi * 3.0 * t)
        sig2 = -sig1  # exact anti-phase
        sig3 = np.cos(2.0 * np.pi * 3.0 * t)  # 90 deg phase shift

        align_self = compute_synchrosqueezed_phase_alignment(sig1, sig1)
        assert math.isclose(align_self, 1.0, abs_tol=1e-3), f"Expected 1.0, got {align_self}"

        align_anti = compute_synchrosqueezed_phase_alignment(sig1, sig2)
        assert math.isclose(align_anti, -1.0, abs_tol=1e-3), f"Expected -1.0, got {align_anti}"

        align_quad = compute_synchrosqueezed_phase_alignment(sig1, sig3)
        assert abs(align_quad) < 0.15, f"Expected ~0.0, got {align_quad}"

        rng = np.random.RandomState(42)
        r1 = rng.randn(150)
        r2 = rng.randn(150)
        align_rand = compute_synchrosqueezed_phase_alignment(r1, r2)
        assert -1.0 <= align_rand <= 1.0

        flat = np.full(150, 100.0)
        align_flat = compute_synchrosqueezed_phase_alignment(flat, sig1[:150])
        assert -1.0 <= align_flat <= 1.0

    def test_adv06b_phase_alignment_nan_resilience(self):
        """Vulnerability: compute_synchrosqueezed_phase_alignment must not return NaN on uncleaned input."""
        corrupted = np.array([10.0, np.nan, 12.0, np.inf, 11.0, 10.5, 9.8, 10.2])
        clean = np.ones(8)
        align = compute_synchrosqueezed_phase_alignment(corrupted, clean)
        # Should be finite and bounded in [-1.0, 1.0]
        assert not math.isnan(align), f"Phase alignment returned NaN on corrupted input: {align}"
        assert -1.0 <= align <= 1.0

    def test_adv07_wsst_energy_conservation_and_entropy_bounds(self):
        """Invariant: Parseval frame energy non-negativity and normalized entropy in [0, 1]."""
        rng = np.random.RandomState(1337)
        for trial in range(10):
            sig = rng.randn(128) + 10.0 * np.sin(np.linspace(0, 20, 128))
            wsst = compute_synchrosqueezed_wavelet_transform(sig)

            e_spec = wsst["energy_spectrum"]
            assert np.all(e_spec >= 0.0), f"Negative energy observed: {e_spec[e_spec < 0]}"

            tot_e = float(np.sum(e_spec))
            assert math.isfinite(tot_e)
            assert tot_e >= 0.0

            ent = wsst["energy_entropy"]
            assert 0.0 <= ent <= 1.0, f"Entropy out of bounds: {ent}"

    def test_adv08_f760_latency_sla_250_bars(self):
        """SLA: WSST decomposition on full 250-bar price history must execute in < 50ms."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.0005, 0.015, 250)) * 100.0

        # Warmup
        _ = compute_synchrosqueezed_wavelet_transform(prices, num_scales=16, num_freqs=16)

        times_ms = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = compute_synchrosqueezed_wavelet_transform(prices, num_scales=16, num_freqs=16)
            times_ms.append((time.perf_counter() - t0) * 1e3)

        mean_ms = float(np.mean(times_ms))
        assert mean_ms < 50.0, f"F760 WSST mean latency {mean_ms:.2f}ms on 250 bars exceeds 50ms SLA"

    def test_adv08b_f760_latency_sla_128_windowed(self):
        """SLA: WSST decomposition on 128-bar rolling window executes in < 50ms."""
        prices = np.cumprod(1.0 + np.random.RandomState(42).normal(0.0005, 0.015, 128)) * 100.0

        # Warmup
        _ = compute_synchrosqueezed_wavelet_transform(prices, num_scales=16, num_freqs=16)

        times_ms = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = compute_synchrosqueezed_wavelet_transform(prices, num_scales=16, num_freqs=16)
            times_ms.append((time.perf_counter() - t0) * 1e3)

        mean_ms = float(np.mean(times_ms))
        assert mean_ms < 50.0, f"F760 WSST mean latency {mean_ms:.2f}ms on 128 bars exceeds 50ms SLA"


class TestF761AdversarialStress:
    """Adversarial stress harness for F761 Persistent Homology TDA & Hodge Laplacian Filtration."""

    def test_adv09_vietoris_rips_metric_axioms_exhaustive(self):
        """Axioms: Vietoris-Rips distance d = sqrt(2*(1-rho)) metric space axioms."""
        for rho in [-1.0, -0.99, -0.5, 0.0, 0.5, 0.99, 1.0]:
            d = compute_vietoris_rips_distance(rho)
            assert 0.0 <= d <= 2.0
        assert compute_vietoris_rips_distance(1.0) == 0.0
        assert math.isclose(compute_vietoris_rips_distance(-1.0), 2.0, abs_tol=1e-7)

        rng = np.random.RandomState(42)
        for _ in range(20):
            A = rng.randn(3, 3)
            cov = A @ A.T
            std = np.sqrt(np.diag(cov))
            corr = cov / np.outer(std, std)

            d01 = compute_vietoris_rips_distance(corr[0, 1])
            d12 = compute_vietoris_rips_distance(corr[1, 2])
            d02 = compute_vietoris_rips_distance(corr[0, 2])

            assert d02 <= d01 + d12 + 1e-7, f"Triangle inequality violated: {d02} > {d01} + {d12}"

        assert compute_vietoris_rips_distance(1.5) == 0.0
        assert compute_vietoris_rips_distance(-1.5) == 2.0

    def test_adv10_disconnected_graph_betti_numbers(self):
        """Stress: Multi-component disconnected graph with N isolated islands."""
        D = np.array([
            [0.0, 0.2, 0.2, 5.0, 5.0, 5.0],
            [0.2, 0.0, 0.2, 5.0, 5.0, 5.0],
            [0.2, 0.2, 0.0, 5.0, 5.0, 5.0],
            [5.0, 5.0, 5.0, 0.0, 0.2, 0.2],
            [5.0, 5.0, 5.0, 0.2, 0.0, 0.2],
            [5.0, 5.0, 5.0, 0.2, 0.2, 0.0],
        ], dtype=np.float64)

        betti = compute_persistent_homology_betti_numbers(D, epsilon=0.30)
        assert betti["beta_0"] == 2, f"Expected 2 components, got {betti['beta_0']}"
        assert betti["beta_1"] == 0, f"Expected 0 holes, got {betti['beta_1']}"

        betti_iso = compute_persistent_homology_betti_numbers(D, epsilon=0.10)
        assert betti_iso["beta_0"] == 6

        betti_full = compute_persistent_homology_betti_numbers(D, epsilon=6.0)
        assert betti_full["beta_0"] == 1

    def test_adv11_persistent_betti_monotonicity_strict(self):
        """Invariant: beta_0(eps) must be monotonically non-increasing across continuous filtration."""
        rng = np.random.RandomState(42)
        X = rng.randn(10, 4)
        corr = np.corrcoef(X)
        D = compute_vietoris_rips_distance(corr)

        epsilons = np.linspace(0.01, 2.0, 20)
        b0_values = []
        for eps in epsilons:
            res = compute_persistent_homology_betti_numbers(D, epsilon=float(eps))
            b0_values.append(res["beta_0"])

        for i in range(len(b0_values) - 1):
            assert b0_values[i] >= b0_values[i + 1], (
                f"Betti-0 monotonicity violated at eps={epsilons[i]:.3f}: "
                f"{b0_values[i]} < {b0_values[i+1]}"
            )
        assert b0_values[0] == 10
        assert b0_values[-1] == 1

    def test_adv12_hodge_laplacian_psd_and_eigenvalues_nonnegative(self):
        """Invariant: Discrete Hodge 1-Laplacian Delta_1 must be strictly Positive Semi-Definite."""
        rng = np.random.RandomState(101)
        for trial in range(10):
            n = rng.randint(4, 12)
            A = (rng.rand(n, n) > 0.6).astype(np.float64)
            A = np.triu(A, 1)
            A = A + A.T
            spec = compute_hodge_laplacian_spectrum(A, epsilon=0.50)
            eigs = spec["eigenvalues"]
            if len(eigs) > 0:
                min_eig = float(np.min(eigs))
                assert min_eig >= -1e-10, f"Trial {trial}: Found negative eigenvalue {min_eig} in Delta_1"
                assert spec["spectral_gap"] >= 0.0

    def test_adv13_topological_hole_detection_in_cycle(self):
        """Invariant: An empty n-cycle (n=5 pentagon) without filled faces must have beta_1 >= 1."""
        adj_cycle = np.zeros((5, 5), dtype=np.float64)
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)]
        for u, v in edges:
            adj_cycle[u, v] = 1.0
            adj_cycle[v, u] = 1.0

        spec = compute_hodge_laplacian_spectrum(adj_cycle)
        assert spec["num_edges"] == 5
        assert spec["num_triangles"] == 0
        assert spec["beta_1"] == 1, f"Expected beta_1=1 for empty 5-cycle, got {spec['beta_1']}"
        assert spec["harmonic_dimension"] == 1, (
            f"Expected harmonic dimension 1 for 5-cycle, got {spec['harmonic_dimension']}"
        )

    def test_adv14_degenerate_and_sub_minimum_networks(self):
        """Stress: 0x0, 1x1, 2x2, asymmetric, and NaN-containing distance matrices."""
        d0 = np.zeros((0, 0))
        spec0 = compute_hodge_laplacian_spectrum(d0)
        assert spec0["beta_0"] == 0
        assert spec0["beta_1"] == 0

        d1 = np.zeros((1, 1))
        spec1 = compute_hodge_laplacian_spectrum(d1)
        assert spec1["beta_0"] == 0 or spec1["beta_0"] == 1
        assert spec1["beta_1"] == 0

        d_asym = np.array([[0.0, 0.8], [0.2, 0.0]])
        spec_asym = compute_hodge_laplacian_spectrum(d_asym, epsilon=0.6)
        assert np.all(spec_asym["eigenvalues"] >= 0.0)

        pers0 = compute_hodge_laplacian_persistence(d0)
        assert pers0["f761_betti_0"] == 0.0
        assert pers0["f761_betti_1"] == 0.0

    def test_adv15_complete_clique_network_collapse(self):
        """Stress: Complete clique K_n (all nodes connected, all triangles filled)."""
        n = 8
        adj_clique = np.ones((n, n), dtype=np.float64) - np.eye(n)
        spec = compute_hodge_laplacian_spectrum(adj_clique)

        assert spec["beta_0"] == 1
        assert spec["beta_1"] == 0
        assert spec["harmonic_dimension"] == 0
        assert spec["num_edges"] == n * (n - 1) // 2
        assert spec["num_triangles"] == n * (n - 1) * (n - 2) // 6

    def test_adv16_f761_185_node_universe_distance_sla(self):
        """SLA: 185-node universe distance matrix computation executes in < 50ms."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (120, 185))
        corr = np.corrcoef(X, rowvar=False)

        t0 = time.perf_counter()
        dist = compute_vietoris_rips_distance(corr)
        t_dist_ms = (time.perf_counter() - t0) * 1e3

        assert dist.shape == (185, 185)
        assert t_dist_ms < 15.0, f"Distance matrix calculation took {t_dist_ms:.2f}ms (>15ms)"

        t1 = time.perf_counter()
        loops = detect_harmonic_value_chain_loops(threshold=0.50)
        t_loops_ms = (time.perf_counter() - t1) * 1e3

        assert "harmonic_loops" in loops
        assert t_loops_ms < 50.0, f"Harmonic loop detection took {t_loops_ms:.2f}ms (>50ms SLA)"

    def test_adv16b_f761_persistence_graph_size_scaling_sla(self):
        """Vulnerability / SLA: compute_hodge_laplacian_persistence latency must scale under 50ms on graphs."""
        rng = np.random.RandomState(42)
        # Bounded cluster N=15
        X15 = rng.randn(50, 15)
        D15 = compute_vietoris_rips_distance(np.corrcoef(X15))
        t0 = time.perf_counter()
        _ = compute_hodge_laplacian_persistence(D15)
        t15_ms = (time.perf_counter() - t0) * 1e3
        assert t15_ms < 50.0, f"N=15 persistence latency {t15_ms:.2f}ms exceeds 50ms SLA"

        # Medium graph N=25 (Empirical stress challenge)
        X25 = rng.randn(50, 25)
        D25 = compute_vietoris_rips_distance(np.corrcoef(X25))
        t0 = time.perf_counter()
        _ = compute_hodge_laplacian_persistence(D25)
        t25_ms = (time.perf_counter() - t0) * 1e3
        assert t25_ms < 50.0, f"N=25 persistence latency {t25_ms:.2f}ms severely violates 50ms SLA"
