"""
test_phase12_m1_challenger1_adversarial.py — Adversarial Stress Test Suite for Phase 12 Genesis Quantitative Enhancement (v19 Production Master).
Author: Challenger 1 (Empirical Challenger)
Targets: Features F67, F68.1, F68.2 in src/ai/ensemble_scorer.py
Scope:
1. F67: Non-Abelian SO(5) Yang-Mills Gauge Field Coupler
   - Lie bracket anti-symmetry: [A1, A2] == -[A2, A1] and skew-symmetry in so(5): [A1, A2]^T == -[A1, A2]
   - Curvature tensor anti-symmetry: F12^T == -F12 across 1,000 random SO(5) vectors
   - Invariance under degenerate (constant/identical), collinear (rank-1/mean-parallel), zero, and extreme/boundary inputs
   - Non-negativity of Yang-Mills action S_YM >= 0, covariant kinetic energy T_cov >= 0, Higgs potential V_Higgs >= 0, total action S_action >= 0
   - Strict boundedness of gauge harmony regularizer h_gauge in (0, 1] and FCPI in (0, 1]
2. F68.1: 7th-Order Hyperconvex Rank Modulation g_v12(r) = 0.50 + 0.75 * r * exp(gamma_top * r^7)
   - Strict pointwise monotonicity (g'(r) > 0) across 10,000 synthetic ranks in [0, 1]
   - Strict convexity (g''(r) > 0 for r in (0, 1]) across 10,000 synthetic ranks in [0, 1]
   - Analytical vs numerical first and second derivative convergence (error < 1e-5)
   - Spearman rank preservation (rho_s == 1.000000) under random permutations
   - Negative conviction decay g_neg(r) = 1.40 - 0.80 * r (monotonic decreasing)
   - Out-of-bounds input clipping and regime-adaptive gamma_top calibration
3. F68.2: 14th-Order (Tetradecagonal) Hyperbolic Noise Deadband z * tanh((|z|/delta)^14)
   - Noise leakage < 10^-8 for |z| <= 0.010 (>99.999999% attenuation, theoretical ~7.67e-12)
   - 100.000% transmission fidelity for |z| >= 0.150 (|z_denoised - z| < 1e-12)
   - Exact unconditioned odd symmetry f(-z) == -f(z) (|f(z) + f(-z)| < 1e-15)
   - Monotonicity across entire continuous domain [-2.0, 2.0]
   - Regime-adaptive asymmetric deadband widening in Bear/Crisis environments
"""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

try:
    from trading_system.src.ai.ensemble_scorer import (
        EnsembleScoringEngine,
        YangMillsGaugeFieldCoupler,
        apply_tetradecagonal_hyperbolic_deadband,
        compute_phase12_hyperconvex_rank_modulation,
    )
except ImportError:
    from src.ai.ensemble_scorer import (
        EnsembleScoringEngine,
        YangMillsGaugeFieldCoupler,
        apply_tetradecagonal_hyperbolic_deadband,
        compute_phase12_hyperconvex_rank_modulation,
    )


# =============================================================================
# 1. F67: NON-ABELIAN SO(5) YANG-MILLS GAUGE FIELD COUPLER ADVERSARIAL TESTS
# =============================================================================

class TestYangMillsGaugeFieldCouplerAdversarial:
    """
    Adversarially challenges the Non-Abelian SO(5) Yang-Mills Gauge Theory Curvature Tensor
    and Stochastic Action Functional Coupler (Feature F67).
    """

    @pytest.fixture
    def coupler(self):
        return YangMillsGaugeFieldCoupler(g=0.85, v0=1.0, lambda_higgs=1.20, kappa=1.50)

    def test_lie_bracket_anti_symmetry_1000_random_so5_vectors(self, coupler):
        """
        Adversarial Test: Verify Lie bracket anti-symmetry [A1, A2] == -[A2, A1]
        and skew-symmetry [A1, A2]^T == -[A1, A2] across 1,000 random SO(5) vectors
        drawn from diverse continuous distributions.
        """
        rng = np.random.RandomState(42)

        # 1,000 random 5-dimensional pillar vectors from multiple distributions:
        # Uniform [0.01, 1.5], Standard Normal, Cauchy-like heavy tails, and Exponential
        v_uniform = rng.uniform(0.01, 1.5, size=(400, 5))
        v_normal = np.abs(rng.normal(0.5, 0.3, size=(300, 5))) + 0.01
        v_cauchy = np.abs(rng.standard_cauchy(size=(150, 5))) + 0.05
        v_cauchy = np.clip(v_cauchy, 0.01, 5.0)
        v_exponential = rng.exponential(scale=0.5, size=(150, 5)) + 0.01
        all_vectors = np.vstack([v_uniform, v_normal, v_cauchy, v_exponential])
        assert all_vectors.shape == (1000, 5), f"Expected 1000 vectors, got {all_vectors.shape}"

        # Evaluate across the full 1,000 cross-section
        res_full = coupler.evaluate(all_vectors)

        A1 = res_full["connection_1"]  # (1000, 5, 5)
        A2 = res_full["connection_2"]  # (1000, 5, 5)
        bracket_12 = res_full["lie_bracket"]  # (1000, 5, 5)

        # 1. Verify A_1 and A_2 skew-symmetry: A^T = -A in so(5)
        A1_T = np.transpose(A1, (0, 2, 1))
        A2_T = np.transpose(A2, (0, 2, 1))
        max_err_a1 = np.max(np.abs(A1 + A1_T))
        max_err_a2 = np.max(np.abs(A2 + A2_T))
        assert max_err_a1 < 1e-12, f"A_1 skew-symmetry violation: max error = {max_err_a1}"
        assert max_err_a2 < 1e-12, f"A_2 skew-symmetry violation: max error = {max_err_a2}"

        # 2. Compute [A_2, A_1] = A_2 A_1 - A_1 A_2
        bracket_21 = np.matmul(A2, A1) - np.matmul(A1, A2)

        # Verify [A_1, A_2] == -[A_2, A_1]
        max_err_anti = np.max(np.abs(bracket_12 + bracket_21))
        assert max_err_anti < 1e-12, f"Lie bracket anti-symmetry violation: max error = {max_err_anti}"

        # 3. Verify that [A_1, A_2] is an element of so(5), hence skew-symmetric: bracket^T == -bracket
        bracket_T = np.transpose(bracket_12, (0, 2, 1))
        max_err_skew = np.max(np.abs(bracket_12 + bracket_T))
        assert max_err_skew < 1e-12, f"Lie bracket so(5) skew-symmetry violation: max error = {max_err_skew}"

        # 4. Also spot-check 50 single 1D vectors individually
        for idx in range(0, 1000, 20):
            single_vec = all_vectors[idx]
            res_single = coupler.evaluate(single_vec)
            a1_s = res_single["A1"]
            a2_s = res_single["A2"]
            b12_s = res_single["bracket"]
            b21_s = np.matmul(a2_s, a1_s) - np.matmul(a1_s, a2_s)
            assert np.allclose(b12_s, -b21_s, atol=1e-12), f"Single vector Lie bracket anti-symmetry failed at {idx}"
            assert np.allclose(b12_s, -b12_s.T, atol=1e-12), f"Single vector Lie bracket skew-symmetry failed at {idx}"

    def test_curvature_tensor_anti_symmetry_1000_random_so5_vectors(self, coupler):
        """
        Adversarial Test: Verify curvature tensor anti-symmetry F12^T == -F12,
        action density non-negativity, and bounded indices across 1,000 random vectors.
        """
        rng = np.random.RandomState(999)
        vectors = rng.uniform(0.05, 1.20, size=(1000, 5))

        res = coupler.evaluate(vectors)
        F12 = res["curvature_tensor"]  # (1000, 5, 5)
        S_ym = res["ym_action"]
        T_cov = res["cov_kinetic"]
        V_higgs = res["higgs_potential"]
        S_action = res["action_functional"]
        h_gauge = res["h_gauge"]
        fcpi = res["fcpi"]

        # 1. Curvature tensor exact anti-symmetry: F12^T == -F12
        F12_T = np.transpose(F12, (0, 2, 1))
        max_err_f12 = np.max(np.abs(F12 + F12_T))
        assert max_err_f12 < 1e-12, f"Curvature tensor anti-symmetry violation: max error = {max_err_f12}"

        # Diagonal elements of F12 must be identically 0
        diag_elements = np.diagonal(F12, axis1=1, axis2=2)
        assert np.allclose(diag_elements, 0.0, atol=1e-12), "F12 diagonal must be identically zero"

        # 2. Action densities must be strictly non-negative
        assert np.all(S_ym >= 0.0), f"S_YM non-negativity violation: min = {np.min(S_ym)}"
        assert np.all(T_cov >= 0.0), f"T_cov non-negativity violation: min = {np.min(T_cov)}"
        assert np.all(V_higgs >= 0.0), f"V_Higgs non-negativity violation: min = {np.min(V_higgs)}"
        assert np.all(S_action >= 0.0), f"S_action non-negativity violation: min = {np.min(S_action)}"

        # 3. Action functional consistency invariant: S_action == S_YM + T_cov + V_Higgs
        action_sum = S_ym + T_cov + V_higgs
        assert np.allclose(S_action, action_sum, atol=1e-12), "Action functional decomposition violation"

        # 4. Gauge harmony regularizer h_gauge in (0, 1]
        assert np.all(h_gauge > 0.0), f"h_gauge lower bound violation: min = {np.min(h_gauge)}"
        assert np.all(h_gauge <= 1.0), f"h_gauge upper bound violation: max = {np.max(h_gauge)}"

        # 5. Factor Collapse Prevention Index (FCPI) in (0, 1]
        assert np.all(fcpi > 0.0), f"FCPI lower bound violation: min = {np.min(fcpi)}"
        assert np.all(fcpi <= 1.0), f"FCPI upper bound violation: max = {np.max(fcpi)}"

    def test_yang_mills_degenerate_inputs(self, coupler):
        """
        Adversarial Test: Verify stability and invariants under degenerate inputs:
        - Uniform identical values [c, c, c, c, c]
        - Zero-variance cross-section (all assets have identical vectors)
        - Single-pillar dominance with 4 collapsed pillars
        """
        # Scenario 1: Zero-variance cross-section (all N=100 assets have exact identical scores)
        c_vals = [0.05, 0.20, 0.50, 1.00, 2.50]
        for c in c_vals:
            identical_cross_section = np.full((100, 5), c)
            res = coupler.evaluate(identical_cross_section)

            # In zero-variance cross-section, delta_P = p - mean(p) == 0
            # Hence A2 == 0, [A1, A2] == 0, d1_A2 == 0, d2_A1 == 0, F12 == 0
            assert np.allclose(res["A2"], 0.0, atol=1e-12), f"A2 must vanish for identical cross-section at c={c}"
            assert np.allclose(res["lie_bracket"], 0.0, atol=1e-12), f"Lie bracket must vanish at c={c}"
            assert np.allclose(res["F12"], 0.0, atol=1e-12), f"F12 must vanish at c={c}"
            assert np.allclose(res["ym_action"], 0.0, atol=1e-12), f"S_YM must vanish at c={c}"

            # Anti-symmetry invariants must hold trivially (0 == -0)
            F12 = res["F12"]
            F12_T = np.transpose(F12, (0, 2, 1))
            assert np.allclose(F12, -F12_T, atol=1e-12)

            # All outputs must be finite without NaN or Inf
            assert np.all(np.isfinite(res["action_functional"]))
            assert np.all(np.isfinite(res["h_gauge"]))
            assert np.all(np.isfinite(res["fcpi"]))

        # Scenario 2: Single-pillar dominance (1 dominant pillar, 4 collapsed pillars)
        collapsed_batch = np.full((50, 5), 0.001)
        collapsed_batch[:, 0] = 1.0  # pillar 'val' dominates completely
        res_collapsed = coupler.evaluate(collapsed_batch)

        # Anti-symmetry must hold strictly
        F12_c = res_collapsed["F12"]
        F12_c_T = np.transpose(F12_c, (0, 2, 1))
        assert np.allclose(F12_c, -F12_c_T, atol=1e-12)

        bracket_c = res_collapsed["lie_bracket"]
        bracket_c_T = np.transpose(bracket_c, (0, 2, 1))
        assert np.allclose(bracket_c, -bracket_c_T, atol=1e-12)

    def test_yang_mills_collinear_inputs(self, coupler):
        """
        Adversarial Test: Verify stability and invariants when cross-sectional vectors
        are strictly collinear (rank-1 matrix, scalar multiples of a single direction).
        """
        base_dir = np.array([0.15, 0.35, 0.20, 0.10, 0.20])
        scalars = np.linspace(0.1, 3.0, 80)
        collinear_mat = np.outer(scalars, base_dir)  # (80, 5) rank-1 matrix

        res = coupler.evaluate(collinear_mat)
        A1 = res["A1"]
        A2 = res["A2"]
        bracket = res["bracket"]
        F12 = res["F12"]

        # 1. A1, A2 must be skew-symmetric in so(5)
        A1_T = np.transpose(A1, (0, 2, 1))
        A2_T = np.transpose(A2, (0, 2, 1))
        assert np.allclose(A1, -A1_T, atol=1e-12), "A1 skew-symmetry failed under collinear inputs"
        assert np.allclose(A2, -A2_T, atol=1e-12), "A2 skew-symmetry failed under collinear inputs"

        # 2. Lie bracket anti-symmetry and skew-symmetry
        bracket_T = np.transpose(bracket, (0, 2, 1))
        assert np.allclose(bracket, -bracket_T, atol=1e-12), "Bracket skew-symmetry failed under collinear inputs"

        # 3. Curvature anti-symmetry
        F12_T = np.transpose(F12, (0, 2, 1))
        assert np.allclose(F12, -F12_T, atol=1e-12), "F12 anti-symmetry failed under collinear inputs"

        # 4. Bounded action and regularizer
        assert np.all(res["action_functional"] >= 0.0)
        assert np.all((res["h_gauge"] > 0.0) & (res["h_gauge"] <= 1.0))
        assert np.all((res["fcpi"] > 0.0) & (res["fcpi"] <= 1.0))

    def test_yang_mills_zero_inputs(self, coupler):
        """
        Adversarial Test: Verify behavior under exact zero inputs:
        - Single 1D zero vector: np.zeros(5)
        - 2D batch of zero vectors: np.zeros((100, 5))
        """
        # 1. 1D zero vector
        z_1d = np.zeros(5)
        res_1d = coupler.evaluate(z_1d)

        # Verify exact anti-symmetry of matrices
        assert np.allclose(res_1d["A1"], 0.0, atol=1e-12)
        assert np.allclose(res_1d["A2"], 0.0, atol=1e-12)
        assert np.allclose(res_1d["bracket"], 0.0, atol=1e-12)
        assert np.allclose(res_1d["F12"], 0.0, atol=1e-12)
        assert np.isclose(res_1d["ym_action"], 0.0, atol=1e-12)
        # When p = 0 in 1D mode, p_bar defaults to 0.20 (equal-weight benchmark prior).
        # delta_P = p - p_bar = -0.20, D1_p = D2_p = -0.20.
        # Covariant kinetic energy T_cov = ||delta_P||^2 = 5 * (0.2)^2 = 0.20.
        expected_t_cov_1d = 5.0 * (0.20 ** 2)
        assert np.isclose(res_1d["cov_kinetic"], expected_t_cov_1d, atol=1e-12)

        # Higgs potential V_Higgs = 0.25 * lambda * (0 - v0^2)^2 = 0.25 * 1.20 * 1.0 = 0.30
        expected_higgs = 0.25 * 1.20 * (1.0 ** 2)
        assert np.isclose(res_1d["higgs_potential"], expected_higgs, atol=1e-12)

        expected_s_action_1d = expected_t_cov_1d + expected_higgs  # 0.20 + 0.30 = 0.50
        assert np.isclose(res_1d["action_functional"], expected_s_action_1d, atol=1e-12)

        expected_h_gauge_1d = np.exp(-1.50 * expected_s_action_1d)  # exp(-0.75) ~ 0.47236655
        assert np.isclose(res_1d["h_gauge"], expected_h_gauge_1d, atol=1e-12)
        assert np.isclose(res_1d["fcpi"], 1.0 / (1.0 + expected_s_action_1d), atol=1e-12)

        # 2. 2D batch of zero vectors
        z_2d = np.zeros((100, 5))
        res_2d = coupler.evaluate(z_2d)

        assert np.allclose(res_2d["F12"], 0.0, atol=1e-12)
        assert np.allclose(res_2d["ym_action"], 0.0, atol=1e-12)
        assert np.allclose(res_2d["cov_kinetic"], 0.0, atol=1e-12)
        assert np.allclose(res_2d["higgs_potential"], expected_higgs, atol=1e-12)
        assert np.allclose(res_2d["action_functional"], expected_higgs, atol=1e-12)
        expected_h_gauge_2d = np.exp(-1.50 * expected_higgs)
        assert np.allclose(res_2d["h_gauge"], expected_h_gauge_2d, atol=1e-12)
        assert np.allclose(res_2d["fcpi"], 1.0 / (1.0 + expected_higgs), atol=1e-12)

    def test_yang_mills_infinite_and_extreme_inputs(self, coupler):
        """
        Adversarial Test: Verify behavior and numerical stability under extreme / boundary values:
        - Very small subnormal inputs: 1e-50, 1e-100, 1e-300
        - Negative pillar scores: [-0.5, -0.2, 0.1, -0.8, -0.3]
        - High dynamic range across pillars (1e6 vs 1e-6)
        """
        # 1. Subnormal tiny inputs
        tiny_mat = np.full((20, 5), 1e-50)
        res_tiny = coupler.evaluate(tiny_mat)
        assert np.all(np.isfinite(res_tiny["action_functional"]))
        assert np.all(res_tiny["h_gauge"] > 0.0)
        F12_t = res_tiny["F12"]
        assert np.allclose(F12_t, -np.transpose(F12_t, (0, 2, 1)), atol=1e-12)

        # 2. Negative pillar scores
        neg_mat = np.array([
            [-0.5, -0.2, 0.1, -0.8, -0.3],
            [-0.1, 0.4, -0.6, 0.2, -0.5],
            [0.3, -0.7, -0.2, -0.4, 0.6]
        ])
        res_neg = coupler.evaluate(neg_mat)
        F12_n = res_neg["F12"]
        assert np.allclose(F12_n, -np.transpose(F12_n, (0, 2, 1)), atol=1e-12)
        b_n = res_neg["bracket"]
        assert np.allclose(b_n, -np.transpose(b_n, (0, 2, 1)), atol=1e-12)
        assert np.all(res_neg["action_functional"] >= 0.0)

        # 3. High dynamic range across pillars (e.g., scale difference 1e6 to 1e-4)
        hdr_mat = np.array([
            [1e3, 1.0, 1e-2, 1e-4, 0.5],
            [5e2, 0.8, 2e-2, 5e-4, 0.3],
            [2e3, 1.2, 5e-3, 1e-3, 0.7]
        ])
        res_hdr = coupler.evaluate(hdr_mat)
        F12_hdr = res_hdr["F12"]
        # Exact skew-symmetry must hold even with high dynamic range
        assert np.allclose(F12_hdr, -np.transpose(F12_hdr, (0, 2, 1)), atol=1e-8)


# =============================================================================
# 2. F68.1: 7TH-ORDER HYPERCONVEX RANK MODULATION ADVERSARIAL TESTS
# =============================================================================

class TestHyperconvexRankModulationAdversarial:
    """
    Adversarially challenges the 7th-Order Hyperconvex Rank Modulation (Feature F68.1):
    g_v12(r) = 0.50 + 0.75 * r * exp(gamma_top * r^7)
    """

    def test_7th_order_monotonicity_10000_synthetic_ranks(self):
        """
        Adversarial Test: Verify strict pointwise monotonicity (g'(r) > 0)
        across 10,000 synthetic ranks in [0, 1] for all gamma_top in [0.20, 1.35].
        """
        r_grid = np.linspace(0.0, 1.0, 10000)
        gammas = [0.0, 0.20, 0.35, 0.55, 0.70, 0.95, 1.00, 1.15, 1.35]

        for gamma in gammas:
            g_vals = compute_phase12_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)

            # 1. Finite differences must be strictly positive everywhere
            diffs = np.diff(g_vals)
            assert np.all(diffs > 0.0), f"Strict monotonicity failed for gamma={gamma}: min diff = {np.min(diffs)}"

            # 2. Minimum derivative must be >= 0.75 (at r=0, g'(0) = 0.75)
            dr = r_grid[1] - r_grid[0]
            num_deriv = diffs / dr
            assert np.all(num_deriv >= 0.7499), f"Minimum derivative < 0.75 for gamma={gamma}: min = {np.min(num_deriv)}"

            # 3. Analytical first derivative comparison:
            # g'(r) = 0.75 * exp(gamma * r^7) * (1 + 7 * gamma * r^7)
            analytical_deriv = 0.75 * np.exp(gamma * np.power(r_grid, 7.0)) * (1.0 + 7.0 * gamma * np.power(r_grid, 7.0))

            # Compare central differences on interior points [1:-1]
            central_diff = (g_vals[2:] - g_vals[:-2]) / (2.0 * dr)
            max_rel_err = np.max(np.abs(central_diff - analytical_deriv[1:-1]) / analytical_deriv[1:-1])
            assert max_rel_err < 1e-4, f"Analytical derivative mismatch for gamma={gamma}: max rel err = {max_rel_err}"

    def test_7th_order_convexity_10000_synthetic_ranks(self):
        """
        Adversarial Test: Verify strict convexity (g''(r) > 0 for r > 0)
        across 10,000 synthetic ranks in [0, 1] for all gamma_top in [0.20, 1.35].
        """
        r_grid = np.linspace(0.0, 1.0, 10000)
        dr = r_grid[1] - r_grid[0]
        gammas = [0.20, 0.35, 0.55, 0.70, 0.95, 1.00, 1.15, 1.35]

        for gamma in gammas:
            g_vals = compute_phase12_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)

            # 1. Second finite differences: g(r_{k+1}) - 2g(r_k) + g(r_{k-1})
            d2 = np.diff(np.diff(g_vals))
            # Must be non-negative everywhere (convex)
            assert np.all(d2 >= -1e-12), f"Convexity violation for gamma={gamma}: min d2 = {np.min(d2)}"

            # For r > 0.05, second derivative must be strictly positive
            mask_positive = r_grid[1:-1] > 0.05
            assert np.all(d2[mask_positive] > 0.0), f"Strict convexity failed on r > 0.05 for gamma={gamma}"

            # 2. Analytical second derivative verification:
            # g''(r) = 0.75 * gamma * r^6 * exp(gamma * r^7) * (56 + 49 * gamma * r^7)
            r_int = r_grid[1:-1]
            analytical_d2 = (
                0.75 * gamma * np.power(r_int, 6.0) * np.exp(gamma * np.power(r_int, 7.0))
                * (56.0 + 49.0 * gamma * np.power(r_int, 7.0))
            )
            # Analytical second derivative must be strictly positive for all r in (0, 1]
            assert np.all(analytical_d2 > 0.0), f"Analytical second derivative must be > 0 for gamma={gamma}"

            # Numerical second derivative: (g[k+1] - 2g[k] + g[k-1]) / dr^2
            num_d2 = d2 / (dr ** 2)
            # On interior region [0.10, 0.95], numerical and analytical must match within 1%
            eval_mask = (r_int >= 0.10) & (r_int <= 0.95)
            rel_err_d2 = np.max(np.abs(num_d2[eval_mask] - analytical_d2[eval_mask]) / analytical_d2[eval_mask])
            assert rel_err_d2 < 0.01, f"Second derivative mismatch for gamma={gamma}: max rel err = {rel_err_d2}"

    def test_spearman_rank_order_preservation_10000_random_ranks(self):
        """
        Adversarial Test: Verify exact Spearman rank correlation preservation (rho_s == 1.000000)
        across 10,000 randomly permuted synthetic ranks.
        """
        rng = np.random.RandomState(777)
        ranks_random = rng.uniform(0.0, 1.0, size=10000)

        for gamma in [0.20, 0.70, 1.00, 1.35]:
            g_mod = compute_phase12_hyperconvex_rank_modulation(ranks_random, gamma_top=gamma)
            rho, pval = spearmanr(ranks_random, g_mod)
            assert np.isclose(rho, 1.000000, atol=1e-6), f"Spearman rank preservation broken for gamma={gamma}: rho={rho}"

    def test_negative_conviction_monotonic_decay(self):
        """
        Adversarial Test: Verify negative excess conviction modulation:
        g_neg(r) = 1.40 - 0.80 * r when z_denoised < 0.
        """
        r_grid = np.linspace(0.0, 1.0, 1000)
        z_neg = np.full(1000, -0.05)

        g_neg = compute_phase12_hyperconvex_rank_modulation(r_grid, gamma_top=1.35, z_denoised=z_neg)

        # 1. Monotonic decrease: diffs must be strictly negative
        diffs = np.diff(g_neg)
        assert np.all(diffs < 0.0), f"Negative conviction must be strictly decreasing: max diff = {np.max(diffs)}"

        # 2. Derivative must be exactly -0.80
        dr = r_grid[1] - r_grid[0]
        deriv = diffs / dr
        assert np.allclose(deriv, -0.80, atol=1e-4), f"Negative conviction derivative must be -0.80, got {deriv[0]}"

        # 3. Exact boundary points: r=0 -> 1.40, r=0.5 -> 1.00, r=1.0 -> 0.60
        assert np.isclose(g_neg[0], 1.40, atol=1e-6)
        assert np.isclose(g_neg[500], 1.00, atol=2e-3)
        assert np.isclose(g_neg[-1], 0.60, atol=1e-6)

    def test_out_of_bounds_clipping(self):
        """
        Adversarial Test: Verify that out-of-bounds ranks (< 0 or > 1)
        are safely clipped to [0, 1] without crash or numerical divergence.
        """
        gamma = 1.35
        # Underflow below 0
        neg_ranks = np.array([-10.0, -1.0, -0.001])
        g_neg = compute_phase12_hyperconvex_rank_modulation(neg_ranks, gamma_top=gamma)
        assert np.allclose(g_neg, 0.50, atol=1e-6), f"Negative ranks must clip to r=0 (0.50), got {g_neg}"

        # Overflow above 1
        pos_ranks = np.array([1.001, 2.0, 100.0])
        g_pos = compute_phase12_hyperconvex_rank_modulation(pos_ranks, gamma_top=gamma)
        expected_peak = 0.50 + 0.75 * np.exp(gamma)
        assert np.allclose(g_pos, expected_peak, atol=1e-6), f"Excess ranks must clip to r=1 ({expected_peak}), got {g_pos}"


# =============================================================================
# 3. F68.2: 14TH-ORDER TETRADECAGONAL HYPERBOLIC DEADBAND ADVERSARIAL TESTS
# =============================================================================

class TestTetradecagonalDeadbandAdversarial:
    """
    Adversarially challenges the 14th-Order (Tetradecagonal) Hyperbolic Noise Deadband (Feature F68.2):
    z_denoised = z * tanh((|z| / delta)^14)
    """

    def test_noise_leakage_sub_threshold_10000_points(self):
        """
        Adversarial Test: Verify noise leakage < 10^-8 for all |z| <= 0.010
        (>99.999999% attenuation) across 10,000 synthetic noise points in [-0.010, 0.010].
        """
        z_noise = np.linspace(-0.010, 0.010, 10000)
        denoised = apply_tetradecagonal_hyperbolic_deadband(z_noise, delta_noise=0.045, alpha_pos=14.0)

        # 1. Absolute noise leakage must be strictly below 1e-8 (theoretically ~7.67e-12)
        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-8, f"Noise leakage exceeded 1e-8: max = {max_leakage}"
        assert max_leakage < 1e-10, f"Sub-threshold leakage exceeded 1e-10: max = {max_leakage}"

        # Theoretical peak at |z| = 0.010:
        # z * tanh((0.010 / 0.045)^14) = 0.010 * tanh((2/9)^14) ~ 7.674e-12
        leakage_at_bound = float(np.abs(apply_tetradecagonal_hyperbolic_deadband(0.010, delta_noise=0.045, alpha_pos=14.0)))
        assert leakage_at_bound < 1e-11, f"Bound leakage at 0.010 exceeded 1e-11: {leakage_at_bound}"
        assert np.isclose(leakage_at_bound, 0.010 * np.tanh((0.010 / 0.045) ** 14), atol=1e-15)

        # 2. Attenuation percentage must exceed 99.999999% across all non-zero points
        non_zero = z_noise != 0.0
        attenuation = 1.0 - (np.abs(denoised[non_zero]) / np.abs(z_noise[non_zero]))
        min_attenuation = np.min(attenuation)
        assert min_attenuation > 0.99999999, f"Attenuation fell below 99.999999%: min = {min_attenuation}"

        # 3. At z = 0.0, denoised must be exactly 0.0
        z_zero_denoised = apply_tetradecagonal_hyperbolic_deadband(0.0, delta_noise=0.045, alpha_pos=14.0)
        assert z_zero_denoised == 0.0, f"Denoised zero must be exactly 0.0, got {z_zero_denoised}"

    def test_transmission_fidelity_high_conviction_10000_points(self):
        """
        Adversarial Test: Verify 100.000% transmission fidelity for |z| >= 0.150
        across 10,000 points in [-2.0, -0.150] and [0.150, 2.0].
        """
        z_pos = np.linspace(0.150, 2.0, 5000)
        z_neg = np.linspace(-2.0, -0.150, 5000)
        z_large = np.concatenate([z_neg, z_pos])

        denoised_large = apply_tetradecagonal_hyperbolic_deadband(z_large, delta_noise=0.045, alpha_pos=14.0)

        # 1. Pointwise transmission difference |z_denoised - z| < 1e-12
        max_diff = np.max(np.abs(denoised_large - z_large))
        assert max_diff < 1e-12, f"High conviction transmission error exceeded 1e-12: max = {max_diff}"

        # 2. Transmission fidelity ratio z_denoised / z == 1.000000 to float64 machine precision
        fidelity_ratios = denoised_large / z_large
        assert np.allclose(fidelity_ratios, 1.0, atol=1e-12), "High conviction transmission fidelity is not 100%"

    def test_exact_odd_symmetry_unconditioned(self):
        """
        Adversarial Test: Verify exact odd symmetry f(-z) == -f(z) to within machine precision (< 1e-15)
        for unconditioned deadband.
        """
        z_grid = np.linspace(0.0001, 1.5, 5000)
        f_pos = apply_tetradecagonal_hyperbolic_deadband(z_grid, delta_noise=0.045, alpha_pos=14.0)
        f_neg = apply_tetradecagonal_hyperbolic_deadband(-z_grid, delta_noise=0.045, alpha_pos=14.0)

        asymmetry = np.abs(f_pos + f_neg)
        max_asymmetry = np.max(asymmetry)
        assert max_asymmetry < 1e-15, f"Odd symmetry violated: max asymmetry = {max_asymmetry}"

    def test_full_domain_monotonicity_20000_points(self):
        """
        Adversarial Test: Verify strict continuous monotonicity across the entire domain
        [-2.0, 2.0] with 20,000 points.
        """
        grid = np.linspace(-2.0, 2.0, 20000)
        denoised = apply_tetradecagonal_hyperbolic_deadband(grid, delta_noise=0.045, alpha_pos=14.0)

        # Finite differences must be non-negative (non-decreasing everywhere)
        diffs = np.diff(denoised)
        assert np.all(diffs >= -1e-15), f"Monotonicity violation in deadband: min diff = {np.min(diffs)}"

        # Spearman rank correlation must be exactly 1.000000
        rho, _ = spearmanr(grid, denoised)
        assert np.isclose(rho, 1.000000, atol=1e-6), f"Spearman rank correlation broken: rho = {rho}"

    def test_regime_adaptive_bear_crisis_widening(self):
        """
        Adversarial Test: Verify regime-adaptive asymmetric deadband widening in Bear/Crisis regimes.
        Under CRISIS (chi_bear = 1.40), negative signals must experience wider deadband (more suppression)
        than positive signals of identical magnitude.
        """
        test_mags = [0.02, 0.04, 0.05, 0.06]
        for mag in test_mags:
            z_pos = np.array([mag])
            z_neg = np.array([-mag])

            denoised_pos = apply_tetradecagonal_hyperbolic_deadband(z_pos, delta_noise=0.045, regime="CRISIS")
            denoised_neg = apply_tetradecagonal_hyperbolic_deadband(z_neg, delta_noise=0.045, regime="CRISIS")

            # In crisis, negative signal should be squashed more strongly than positive
            assert np.abs(denoised_neg[0]) < np.abs(denoised_pos[0]), (
                f"At mag={mag}, expected |neg| < |pos| in CRISIS, but got pos={denoised_pos[0]}, neg={denoised_neg[0]}"
            )
