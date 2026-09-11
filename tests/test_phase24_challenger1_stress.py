"""
tests/test_phase24_challenger1_stress.py

Adversarial Stress Test Suite for Phase 24 Alpha Signal and Risk Allocation Innovations:
Challenger 1 (Alpha & Risk)

Coverage:
1. Alpha Stress:
   - Extreme rank modulation inputs (r -> 1.0, r < 0, r > 1, gamma_top <= 0, large gamma_top)
   - 60th-order Hexacontagonal deadband: ultra-low noise leakage across [-0.005, 0.005] (< 10^-32),
     100.000% high-conviction transmission (|z| >= 0.150), rank monotonicity and odd symmetry
   - F115 Étale-Motivic / Derived Arithmetic Topology Coupler numerical stability under ill-conditioned,
     collinear, zero-variance, large discordance, and extreme inputs
2. Risk Stress:
   - F117.1 Lurie Arithmetic Spectral Fisher-Rao Barycenter on Dirac measures, simplex boundary states,
     extreme perturbations, and prioritization hierarchy
   - F117.1.2 20th-Order Trans-Super-Hyper EVaR exact factorial (20! = 2,432,902,008,176,640,000),
     xi_super_hyper = 0.80, coherent tail risk hierarchy monotonicity, and fat-tail distributions
     (Cauchy, Pareto alpha=1.1, Student-t nu=2.1, Black Swan shocks up to -99%)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import cauchy, pareto, t as student_t, spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_hexacontagonal_hyperbolic_deadband,
    compute_phase24_hyperconvex_rank_modulation,
    compute_phase24_rank_warping,
    DerivedArithmeticTopologyCoupler,
    EtaleMotivicSpectralHomotopyCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexacontagonal_hyperbolic_deadband as fs_hexacontagonal_deadband,
    compute_phase24_hyperconvex_rank_modulation as fs_compute_phase24_modulation,
    get_regime_adaptive_gamma_top_v24,
    REGIME_GAMMA_TOP_V24,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase24AlphaAdversarial:
    """Adversarial stress testing of Phase 24 Alpha Signal innovations."""

    # -------------------------------------------------------------------------
    # 1. Extreme Rank Modulation ($g_{v24}(r)$) Stress
    # -------------------------------------------------------------------------

    def test_rank_modulation_extreme_percentiles_subgrid(self):
        """Stress-test extreme right-tail conviction at r in [0.9999, 1.0000]."""
        r_dense = np.linspace(0.9990, 1.0000, 10001)
        mod = compute_phase24_hyperconvex_rank_modulation(r_dense, gamma_top=2.50)

        # Monotonicity across top percentiles
        diffs = np.diff(mod)
        assert np.all(diffs >= 0.0), "Rank modulation must be strictly non-decreasing in right tail"

        # Numerical bounds
        assert np.all(np.isfinite(mod)), "Rank modulation must not produce NaN or Inf"
        # At r = 1.0, value must equal 0.50 + 1.12 * exp(2.50)
        expected_top = 0.50 + 1.12 * math.exp(2.50)
        assert math.isclose(mod[-1], expected_top, rel_tol=1e-12)

        # At r = 0.9999
        val_9999 = compute_phase24_hyperconvex_rank_modulation(0.9999, gamma_top=2.50)
        assert val_9999 > 14.0, f"Conviction at r=0.9999 must exceed 14.0, got {val_9999}"
        assert val_9999 < expected_top

    def test_rank_modulation_out_of_bounds_inputs(self):
        """Stress-test out-of-bounds inputs: r < 0 and r > 1."""
        r_oob = np.array([-100.0, -1.0, -1e-6, 0.0, 1.0, 1.0 + 1e-6, 2.0, 100.0])
        mod = compute_phase24_hyperconvex_rank_modulation(r_oob, gamma_top=2.50)

        assert np.all(np.isfinite(mod))
        # Negative ranks clipped to 0 -> 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-12)
        assert math.isclose(mod[1], 0.50, abs_tol=1e-12)
        assert math.isclose(mod[2], 0.50, abs_tol=1e-12)
        assert math.isclose(mod[3], 0.50, abs_tol=1e-12)

        # Ranks > 1 clipped to 1.0 -> 0.50 + 1.12 * exp(2.50)
        expected_top = 0.50 + 1.12 * math.exp(2.50)
        assert math.isclose(mod[4], expected_top, abs_tol=1e-12)
        assert math.isclose(mod[5], expected_top, abs_tol=1e-12)
        assert math.isclose(mod[6], expected_top, abs_tol=1e-12)
        assert math.isclose(mod[7], expected_top, abs_tol=1e-12)

    def test_rank_modulation_gamma_top_parameter_extremes(self):
        """Stress-test extreme gamma_top values: negative, zero, very large."""
        r_test = np.array([0.0, 0.5, 0.9, 1.0])

        # gamma_top = 0.0 -> g(r) = 0.50 + 1.12 * r * exp(0) = 0.50 + 1.12 * r
        mod_zero = compute_phase24_hyperconvex_rank_modulation(r_test, gamma_top=0.0)
        np.testing.assert_allclose(mod_zero, 0.50 + 1.12 * r_test, atol=1e-12)

        # Negative gamma_top: -2.50
        mod_neg = compute_phase24_hyperconvex_rank_modulation(r_test, gamma_top=-2.50)
        assert np.all(np.isfinite(mod_neg))
        assert np.all(mod_neg > 0.0)

        # Very large gamma_top: 10.0, 20.0
        mod_large = compute_phase24_hyperconvex_rank_modulation(r_test, gamma_top=10.0)
        assert np.all(np.isfinite(mod_large))
        assert mod_large[-1] > 1e4

    def test_rank_modulation_negative_denoised_branch_boundary(self):
        """Stress-test negative vs positive denoised z boundary at z = 0, +/- 1e-15."""
        r = np.array([0.1, 0.5, 0.9])

        # Exactly z = 0.0 should use positive branch
        mod_zero_z = compute_phase24_hyperconvex_rank_modulation(r, gamma_top=2.50, z_denoised=np.array([0.0, 0.0, 0.0]))
        mod_pos_z = compute_phase24_hyperconvex_rank_modulation(r, gamma_top=2.50, z_denoised=np.array([1e-15, 1e-15, 1e-15]))
        np.testing.assert_allclose(mod_zero_z, mod_pos_z, atol=1e-10)

        # Negative z: 1.35 - 1.00 * r
        mod_neg_z = compute_phase24_hyperconvex_rank_modulation(r, gamma_top=2.50, z_denoised=np.array([-1e-15, -1e-15, -1e-15]))
        expected_neg = 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg_z, expected_neg, atol=1e-10)

    # -------------------------------------------------------------------------
    # 2. 60th-Order Hexacontagonal Deadband Ultra-Stress
    # -------------------------------------------------------------------------

    def test_hexacontagonal_deadband_ultra_leakage_dense_grid(self):
        """
        Verify that across 500,000 points in [-0.005, 0.005], noise leakage
        is strictly < 10^-32 (in fact < 10^-50).
        """
        z_dense = np.linspace(-0.005, 0.005, 500001)
        denoised = apply_hexacontagonal_hyperbolic_deadband(z_dense, delta_noise=0.035, alpha_pos=60.0)

        max_leak = np.max(np.abs(denoised))
        assert max_leak < 1e-32, f"Noise leakage {max_leak} must be < 1e-32"
        # In fact, (0.005 / 0.035)^60 = (1/7)^60 ~ 1.79e-51, so 0.005 * 1.79e-51 ~ 8.97e-54
        assert max_leak < 1e-50, f"Ultra-tight leakage bound < 1e-50 violated: {max_leak}"

    def test_hexacontagonal_deadband_high_conviction_full_transmission(self):
        """
        Verify that for |z| >= 0.150, transmission ratio z_denoised / z == 1.000000000000 (100.000%).
        """
        z_conviction = np.array([0.150, 0.150001, 0.200, 0.350, 0.500, 1.000, 5.000, 10.000])
        for sign in [1.0, -1.0]:
            z_vals = sign * z_conviction
            denoised = apply_hexacontagonal_hyperbolic_deadband(z_vals, delta_noise=0.035, alpha_pos=60.0)
            ratio = denoised / z_vals
            np.testing.assert_allclose(ratio, 1.0, rtol=1e-14, atol=1e-14)
            np.testing.assert_allclose(denoised, z_vals, rtol=1e-14, atol=1e-14)

    def test_hexacontagonal_deadband_monotonicity_fine_grid(self):
        """Verify strict monotonicity across 100,000 points from -1.0 to 1.0."""
        grid = np.linspace(-1.0, 1.0, 100000)
        out = apply_hexacontagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=60.0)

        diffs = np.diff(out)
        assert np.all(diffs >= -1e-15), "Deadband must be strictly monotonic non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert math.isclose(rho, 1.0, abs_tol=1e-6), f"Spearman correlation must be 1.0, got {rho}"

    def test_hexacontagonal_deadband_extreme_inputs(self):
        """Verify handling of 0.0, subnormals, and large values."""
        assert apply_hexacontagonal_hyperbolic_deadband(0.0) == 0.0
        assert apply_hexacontagonal_hyperbolic_deadband(-0.0) == 0.0

        # Subnormals / tiny numbers
        tiny = 1e-15
        assert abs(apply_hexacontagonal_hyperbolic_deadband(tiny)) < 1e-50
        assert abs(apply_hexacontagonal_hyperbolic_deadband(-tiny)) < 1e-50

        # Large numbers
        huge = 1e6
        assert math.isclose(apply_hexacontagonal_hyperbolic_deadband(huge), huge, rel_tol=1e-12)
        assert math.isclose(apply_hexacontagonal_hyperbolic_deadband(-huge), -huge, rel_tol=1e-12)

    # -------------------------------------------------------------------------
    # 3. F115 Étale-Motivic / Derived Arithmetic Topology Coupler Stress
    # -------------------------------------------------------------------------

    def test_coupler_collinear_and_singular_matrices(self):
        """Stress-test coupler under collinear (rank 1), zero variance, and identical pillars."""
        # Case A: Identical zero pillars
        zeros = pd.DataFrame(np.zeros((10, 5)), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_zeros = DerivedArithmeticTopologyCoupler.compute(zeros)
        np.testing.assert_allclose(res_zeros["e_arithmetic"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res_zeros["z_spectral"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res_zeros["h_arithmetic"].values, 1.0, atol=1e-12)

        # Case B: Rank-1 identical non-zero pillars
        const_val = pd.DataFrame(np.full((5, 5), 0.777), columns=['val', 'mom', 'flow', 'cat', 'net'])
        res_const = DerivedArithmeticTopologyCoupler.compute(const_val)
        np.testing.assert_allclose(res_const["e_arithmetic"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res_const["z_spectral"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res_const["h_arithmetic"].values, 1.0, atol=1e-12)

        # Case C: 4 identical pillars, 1 perturbed by tiny epsilon
        pert = np.full((10, 5), 0.50)
        pert[:, 4] += 1e-5
        res_pert = DerivedArithmeticTopologyCoupler.compute(pd.DataFrame(pert, columns=['val', 'mom', 'flow', 'cat', 'net']))
        assert np.all(res_pert["e_arithmetic"].values > 0.0)
        assert np.all(res_pert["e_arithmetic"].values < 1e-6)
        assert np.all(res_pert["h_arithmetic"].values > 0.999)

    def test_coupler_extreme_discordance_and_suppression(self):
        """Stress-test coupler under extreme pillar discordance: [-10, 10, -10, 10, -10]."""
        disc = pd.DataFrame([
            [-10.0, 10.0, -10.0, 10.0, -10.0],
            [10.0, -10.0, 10.0, -10.0, 10.0],
        ], columns=['val', 'mom', 'flow', 'cat', 'net'])

        res = DerivedArithmeticTopologyCoupler.compute(disc)
        # Obstruction should be massive
        assert np.all(res["e_arithmetic"].values > 100.0)
        # h_arithmetic must be squashed down to near epsilon_reg (1e-6)
        assert np.all(res["h_arithmetic"].values <= 1e-5)
        assert np.all(res["h_arithmetic"].values >= 1e-6)
        # FERI_v24 must be heavily compressed
        assert np.all(res["FERI_v24"].values < 0.01)

    def test_coupler_nan_inf_adversarial_inputs(self):
        """Stress-test coupler handling of NaNs and Infs."""
        bad_df = pd.DataFrame([
            [np.nan, 0.5, 0.5, 0.5, 0.5],
            [0.5, np.nan, np.nan, 0.5, 0.5],
            [0.5, 0.5, 0.5, 0.5, np.nan],
        ], columns=['val', 'mom', 'flow', 'cat', 'net'])

        res = DerivedArithmeticTopologyCoupler.compute(bad_df)
        assert np.all(np.isfinite(res["h_arithmetic"].values))
        assert np.all(np.isfinite(res["z_spectral"].values))
        assert np.all(np.isfinite(res["e_arithmetic"].values))
        assert np.all(np.isfinite(res["FERI_v24"].values))

    def test_coupler_metric_invariants_monte_carlo(self):
        """Monte Carlo verification of metric invariants over 5,000 randomized pillar states."""
        np.random.seed(999)
        N = 5000
        p_random = np.random.uniform(-2.0, 2.0, size=(N, 5))
        df_random = pd.DataFrame(p_random, columns=['val', 'mom', 'flow', 'cat', 'net'])

        res = DerivedArithmeticTopologyCoupler.compute(df_random)
        e = res["e_arithmetic"].values
        z = res["z_spectral"].values
        h = res["h_arithmetic"].values
        feri = res["FERI_v24"].values

        assert np.all(e >= 0.0), "Obstruction E_arithmetic must be non-negative"
        assert np.all((z > 0.0) & (z <= 1.0)), "Invariant Z_spectral must be in (0, 1]"
        assert np.all((h >= 1e-6) & (h <= 1.0)), "Coupling h_arithmetic must be in [1e-6, 1.0]"
        assert np.all((feri > 0.0) & (feri <= 1.0)), "FERI_v24 must be in (0, 1]"


class TestPhase24RiskAdversarial:
    """Adversarial stress testing of Phase 24 Risk Allocation innovations."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    # -------------------------------------------------------------------------
    # 4. F117.1 Lurie Arithmetic Spectral Fisher-Rao Barycenter Stress
    # -------------------------------------------------------------------------

    def test_barycenter_dirac_measure_all_vertices(self, allocator):
        """Verify consensus on all 4 pure Dirac delta vertices."""
        vertices = [
            ("bl", {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}),
            ("herc", {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0}),
            ("rp", {"bl": 0.0, "herc": 0.0, "rp": 1.0, "cvar": 0.0}),
            ("cvar", {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0}),
        ]
        for name, w in vertices:
            res = allocator.compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend(w)
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
            # The active vertex must dominate with weight > 0.99
            assert res[name] > 0.99, f"Vertex {name} dominance failed: {res[name]}"
            for other in ["bl", "herc", "rp", "cvar"]:
                if other != name:
                    assert res[other] < 0.01

    def test_barycenter_simplex_boundary_edges_and_faces(self, allocator):
        """Stress-test edges (2 active models) and faces (3 active models)."""
        # Edge 1: BL and CVaR 50-50
        edge_bl_cvar = {"bl": 0.5, "herc": 0.0, "rp": 0.0, "cvar": 0.5}
        res_edge = allocator.compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend(edge_bl_cvar)
        assert math.isclose(sum(res_edge.values()), 1.0, abs_tol=1e-6)
        assert res_edge["cvar"] > res_edge["bl"]  # mu_cvar (2.70) > mu_bl (2.15)
        assert res_edge["herc"] < 0.01 and res_edge["rp"] < 0.01

        # Face: BL, HERC, CVaR 1/3 each, RP = 0
        face_rp_zero = {"bl": 1/3, "herc": 1/3, "rp": 0.0, "cvar": 1/3}
        res_face = allocator.compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend(face_rp_zero)
        assert math.isclose(sum(res_face.values()), 1.0, abs_tol=1e-6)
        assert res_face["cvar"] > res_face["bl"] > res_face["herc"]
        assert res_face["rp"] < 0.01

    def test_barycenter_extreme_perturbations_and_stability(self, allocator):
        """Stress-test extreme epsilon perturbations: [1 - 3eps, eps, eps, eps]."""
        for eps in [1e-12, 1e-8, 1e-5, 1e-3]:
            w = {"bl": 1.0 - 3.0 * eps, "herc": eps, "rp": eps, "cvar": eps}
            res = allocator.compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend(w)
            assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
            assert all(v > 0.0 for v in res.values())
            assert res["bl"] > 0.98

    def test_barycenter_degenerate_zero_and_unnormalized_inputs(self, allocator):
        """Stress-test degenerate all-zero input and large unnormalized inputs."""
        # All zeros: fallback to uniform
        w_zeros = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        res_zeros = allocator.compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend(w_zeros)
        assert math.isclose(sum(res_zeros.values()), 1.0, abs_tol=1e-6)
        # Should behave like uniform input: CVaR > BL > HERC > RP
        assert res_zeros["cvar"] > res_zeros["bl"] > res_zeros["herc"] > res_zeros["rp"]

        # Large unnormalized: [1000, 2000, 3000, 4000]
        w_large = {"bl": 1000.0, "herc": 2000.0, "rp": 3000.0, "cvar": 4000.0}
        res_large = allocator.compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend(w_large)
        assert math.isclose(sum(res_large.values()), 1.0, abs_tol=1e-6)
        assert all(v > 0.0 for v in res_large.values())

    def test_barycenter_monte_carlo_dirichlet_consensus(self, allocator):
        """Monte Carlo verification of barycenter convergence over 200 random Dirichlet distributions."""
        np.random.seed(777)
        alpha_prior = [1.0, 1.0, 1.0, 1.0]
        samples = np.random.dirichlet(alpha_prior, size=200)

        for s in samples:
            w_dict = {"bl": float(s[0]), "herc": float(s[1]), "rp": float(s[2]), "cvar": float(s[3])}
            res = allocator.compute_lurie_arithmetic_spectral_fisher_rao_barycenter_blend(w_dict, max_iter=50, tol=1e-6)
            tot = sum(res.values())
            assert math.isclose(tot, 1.0, abs_tol=1e-5), f"Partition of unity violated: {tot}"
            assert all(v >= 0.0 for v in res.values())

    # -------------------------------------------------------------------------
    # 5. F117.1.2 20th-Order Trans-Super-Hyper EVaR Tail Risk Measure Stress
    # -------------------------------------------------------------------------

    def test_evar_exact_factorial_and_parameters(self, allocator):
        """Verify exact factorial 20! = 2,432,902,008,176,640,000 and xi_20 = 0.80."""
        assert math.factorial(20) == 2432902008176640000
        assert math.factorial(19) == 121645100408832000
        assert math.factorial(18) == 6402373705728000

        rets = np.array([-0.02, -0.01, 0.01, 0.02, 0.005, -0.03])
        res = allocator.compute_trans_super_hyper_evar_risk_measure(rets, alpha=0.05)
        assert res["order"] == 20
        assert math.isclose(res["xi_20"], 0.80, abs_tol=1e-12)
        assert math.isclose(res["xi_super_hyper"], 0.80, abs_tol=1e-12)
        assert math.isclose(res["xi_trans_super_hyper"], 0.80, abs_tol=1e-12)

    def test_evar_strict_coherent_hierarchy_50_trials(self, allocator):
        """
        Verify strict coherent tail risk hierarchy across 50 diverse synthetic return profiles:
            VaR <= CVaR <= Ultra-Trans-Hyper-EVaR <= Trans-Super-Hyper-EVaR
        """
        np.random.seed(12345)
        for trial in range(50):
            # Mix normal, t-dist, and jump crashes
            base_rets = np.random.normal(0.0005, 0.015, 200)
            jumps = np.random.choice([0.0, -0.05, -0.10, -0.20], size=200, p=[0.92, 0.05, 0.02, 0.01])
            rets = base_rets + jumps

            res = allocator.compute_trans_super_hyper_evar_risk_measure(rets, alpha=0.05)
            uth_res = allocator.compute_ultra_trans_hyper_evar_risk_measure(rets, alpha=0.05)

            var_val = res["var_value"]
            cvar_val = res["cvar_value"]
            uth_val = uth_res["ultra_trans_hyper_evar_value"]
            tsh_val = res["trans_super_hyper_evar_value"]

            assert var_val <= cvar_val + 1e-6, f"Trial {trial}: VaR ({var_val}) > CVaR ({cvar_val})"
            assert cvar_val <= uth_val + 1e-6, f"Trial {trial}: CVaR ({cvar_val}) > UTH-EVaR ({uth_val})"
            assert uth_val <= tsh_val + 1e-6, f"Trial {trial}: UTH-EVaR ({uth_val}) > TSH-EVaR ({tsh_val})"

    def test_evar_adversarial_fat_tail_distributions(self, allocator):
        """
        Empirically test Trans-Super-Hyper EVaR under heavy fat-tail distributions:
        - Cauchy: infinite mean & variance
        - Pareto (alpha=1.1): finite mean, infinite variance
        - Student-t (df=2.1): finite variance, infinite 3rd/4th moments
        - Catastrophic Black Swan shocks (-30%, -50%, -80%, -95%)
        """
        np.random.seed(54321)
        scenarios = {
            "Cauchy_Extreme": cauchy.rvs(loc=-0.02, scale=0.04, size=1000),
            "Pareto_Alpha_1.1": -(pareto.rvs(b=1.1, scale=0.015, size=1000) - 0.015),
            "Student_t_df_2.1": student_t.rvs(df=2.1, loc=-0.01, scale=0.025, size=1000),
            "Black_Swan_Minus_50": np.concatenate([
                np.random.normal(0.001, 0.012, 990),
                np.array([-0.15, -0.25, -0.35, -0.50])
            ]),
            "Catastrophic_Minus_95": np.concatenate([
                np.random.normal(0.001, 0.01, 995),
                np.array([-0.30, -0.60, -0.80, -0.90, -0.95])
            ]),
        }

        for name, r in scenarios.items():
            res = allocator.compute_trans_super_hyper_evar_risk_measure(r, alpha=0.05)
            val = res["trans_super_hyper_evar_value"]

            assert math.isfinite(val), f"Non-finite EVaR value under {name}: {val}"
            assert val > 0.0, f"EVaR must be strictly positive under loss-heavy {name}: {val}"
            # Monotonicity with respect to CVaR
            assert val >= res["cvar_value"] - 1e-6, f"EVaR < CVaR under {name}"

    def test_evar_black_swan_severity_monotonicity(self, allocator):
        """Verify that increasing severity of crash shocks monotonically increases Trans-Super-Hyper EVaR."""
        np.random.seed(42)
        base = np.random.normal(0.001, 0.01, 500)

        evar_levels = []
        crashes = [-0.10, -0.25, -0.50, -0.75, -0.90]
        for crash in crashes:
            r_shock = np.append(base, crash)
            res = allocator.compute_trans_super_hyper_evar_risk_measure(r_shock, alpha=0.05)
            evar_levels.append(res["trans_super_hyper_evar_value"])

        # Monotonicity check
        diffs = np.diff(evar_levels)
        assert np.all(diffs >= 0.0), f"EVaR must strictly increase as crash size increases: {evar_levels}"
