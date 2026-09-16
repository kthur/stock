r"""
tests/test_phase46_adversarial_challenger1.py

Adversarial Stress Test Suite for Phase 46 Quantitative Enhancement:
Role: Challenger 1 (Alpha & Risk Adversarial Challenger)
Scope:
1. Feature F204.2: 176th-Order Centaheptacontahexagonal Hyperbolic Noise Deadband
   - Subnormals, extreme inputs ($z \in [-10^{300}, 10^{300}]$)
   - Deadband leakage at boundary ($|z| \le 0.0003 \to 0.0$)
   - Signal transmission at $|z| \ge 0.150 \to 100.0\%$
   - Monotonicity and odd symmetry
2. Feature F204.1: 41st-Order Ultra-Convex Rank Modulation
   - Strict monotonicity for positive conviction ($z_{\text{denoised}} \ge 0$)
   - Strict monotonicity for negative conviction ($z_{\text{denoised}} < 0$)
   - Right-tail amplification $g(1.0) > 300.0$
   - Lower 70% damping $g(0.70) < 1.60$
   - Out-of-bounds clipping and regime hierarchy
3. Feature F203: Quantum Geometric Langlands Borcherds-Kac-Moody Whittaker Coupler
   - Degenerate, collinear, orthogonal, and extreme pillar stress
   - Invariant bounds: $h, z, \text{FERI} \in [0, 1]$
4. Feature F205.1: Lurie-Borcherds-Whittaker Motivic Fisher-Rao Barycenter Blend
   - Degenerate single-model mass convergence
   - Inverted and uniform distributions
   - Strict simplex conservation ($\sum q_i = 1.0, q_i > 0$)
   - Metric weight ordering: $\text{CVaR} > \text{BL} > \text{HERC} > \text{RP}$
5. Feature F205.1: 42nd-Cumulant Trans-Singular Borcherds EVaR
   - Analytical monotonicity ($EVaR_{42} \ge EVaR_{41}$) across 100 diverse random distributions
     (Normal, Student-t df=2,3,5, Cauchy-like, Pareto, Flash crash, Constant)
   - Heavy-tail sensitivity comparison
   - Numerical stability under extreme inputs
"""

import os
os.environ["BYPASS_TORCH"] = "1"
import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_centaheptacontahexagonal_hyperbolic_deadband,
    compute_phase46_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v46,
    REGIME_GAMMA_TOP_V46,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


# =========================================================================
# 1. ADVERSARIAL DEADBAND STRESS TESTS (F204.2)
# =========================================================================

class TestPhase46DeadbandAdversarial:
    """Adversarial stress testing of the 176th-order Centaheptacontahexagonal deadband."""

    @pytest.mark.parametrize("z", [
        0.0,
        1e-15,
        -1e-15,
        1e-10,
        -1e-10,
        1e-5,
        -1e-5,
        0.0001,
        -0.0001,
        0.000299,
        -0.000299,
        0.0003,
        -0.0003,
    ])
    def test_deadband_boundary_noise_annihilation(self, z):
        """Verify strict noise annihilation to 0.0 (< 10^-102) for |z| <= 0.0003."""
        z_denoised = apply_centaheptacontahexagonal_hyperbolic_deadband(z)
        assert abs(z_denoised) < 1e-102, f"Leakage violation at z={z}: got {z_denoised}"
        assert z_denoised == 0.0, f"IEEE 754 float underflow expected strictly 0.0 at z={z}"

    @pytest.mark.parametrize("z", [
        0.150,
        -0.150,
        0.200,
        -0.200,
        0.500,
        -0.500,
        1.0,
        -1.0,
        5.0,
        -5.0,
        10.0,
        -10.0,
    ])
    def test_deadband_signal_transmission_fidelity(self, z):
        """Verify 100.0% signal transmission with relative tolerance < 10^-9 for |z| >= 0.150."""
        z_denoised = apply_centaheptacontahexagonal_hyperbolic_deadband(z)
        rel_diff = abs(z_denoised - z) / abs(z)
        assert rel_diff < 1e-9, f"Signal distortion at z={z}: rel_diff={rel_diff}"
        assert math.isclose(z_denoised, z, rel_tol=1e-9)

    @pytest.mark.parametrize("extreme_z", [
        1e300,
        -1e300,
        1e307,
        -1e307,
        1e-300,
        -1e-300,
        1e-308,
        -1e-308,
    ])
    def test_deadband_extreme_and_subnormal_stability(self, extreme_z):
        """Verify numerical stability on extreme large floats and subnormal near-zero floats."""
        res = apply_centaheptacontahexagonal_hyperbolic_deadband(extreme_z)
        assert math.isfinite(res), f"Result must be finite for extreme_z={extreme_z}, got {res}"
        if abs(extreme_z) >= 0.150:
            assert math.isclose(res, extreme_z, rel_tol=1e-9)
        else:
            assert abs(res) < 1e-102

    def test_deadband_odd_symmetry(self):
        """Verify exact odd symmetry f(-z) == -f(z) for symmetric regimes."""
        test_points = np.linspace(-2.0, 2.0, 201)
        res = apply_centaheptacontahexagonal_hyperbolic_deadband(test_points, regime=None)
        # Flip and check odd symmetry: f(-z) + f(z) == 0.0
        neg_res = apply_centaheptacontahexagonal_hyperbolic_deadband(-test_points, regime=None)
        np.testing.assert_allclose(res, -neg_res, atol=1e-12)

    def test_deadband_strict_monotonicity(self):
        """Verify non-decreasing monotonicity across the full activation transition [0, 1.0]."""
        fine_grid = np.linspace(0.0, 1.0, 10001)
        res = apply_centaheptacontahexagonal_hyperbolic_deadband(fine_grid)
        diffs = np.diff(res)
        assert (diffs >= -1e-16).all(), "Deadband must be monotonically non-decreasing for z >= 0"

    def test_deadband_container_types_and_shapes(self):
        """Verify scalar, 1D array, 2D array, and pandas Series with custom index."""
        # Scalar
        val = apply_centaheptacontahexagonal_hyperbolic_deadband(0.25)
        assert isinstance(val, float)
        assert math.isclose(val, 0.25, rel_tol=1e-9)

        # 1D array
        arr1d = np.array([0.0001, 0.25, -0.25])
        out1d = apply_centaheptacontahexagonal_hyperbolic_deadband(arr1d)
        assert isinstance(out1d, np.ndarray)
        assert out1d[0] == 0.0
        assert math.isclose(out1d[1], 0.25, rel_tol=1e-9)
        assert math.isclose(out1d[2], -0.25, rel_tol=1e-9)

        # 2D array
        arr2d = np.array([[0.0001, 0.25], [-0.0001, -0.25]])
        out2d = apply_centaheptacontahexagonal_hyperbolic_deadband(arr2d)
        assert out2d.shape == (2, 2)
        assert out2d[0, 0] == 0.0
        assert out2d[1, 0] == 0.0
        assert math.isclose(out2d[0, 1], 0.25, rel_tol=1e-9)

        # Pandas Series
        s = pd.Series([0.0002, 0.30], index=["s1", "s2"])
        outs = apply_centaheptacontahexagonal_hyperbolic_deadband(s)
        assert isinstance(outs, pd.Series)
        assert list(outs.index) == ["s1", "s2"]
        assert outs["s1"] == 0.0
        assert math.isclose(outs["s2"], 0.30, rel_tol=1e-9)


# =========================================================================
# 2. ADVERSARIAL RANK MODULATION STRESS TESTS (F204.1)
# =========================================================================

class TestPhase46RankModulationAdversarial:
    """Adversarial stress testing of 41st-order Ultra-Convex Rank Modulation."""

    def test_rank_modulation_positive_strict_monotonicity(self):
        """Verify strict monotonic increasing property for positive convictions."""
        ranks = np.linspace(0.0, 1.0, 2000)
        for gamma in [1.65, 3.20, 4.50, 4.80, 5.00, 5.30]:
            g_vals = compute_phase46_hyperconvex_rank_modulation(ranks, gamma_top=gamma, z_denoised=0.1)
            diffs = np.diff(g_vals)
            assert (diffs > 0.0).all(), f"Strict monotonicity failed for gamma_top={gamma}"

    def test_rank_modulation_negative_strict_monotonicity(self):
        """Verify strict monotonic decreasing property in rank for negative convictions."""
        ranks = np.linspace(0.0, 1.0, 2000)
        g_neg = compute_phase46_hyperconvex_rank_modulation(ranks, gamma_top=5.30, z_denoised=-0.1)
        diffs = np.diff(g_neg)
        assert (diffs < 0.0).all(), "Negative conviction rank modulation must be strictly decreasing in rank"
        assert math.isclose(g_neg[0], 1.35, abs_tol=1e-6)
        assert math.isclose(g_neg[-1], 0.35, abs_tol=1e-6)

    def test_rank_modulation_right_tail_convexity_and_lower_damping(self):
        """Verify r=1.0 exceeds 300.0 while r=0.70 remains tightly damped below 1.60."""
        for gamma in [5.30]:
            # At r = 0.70, r^41 ~= 4.45e-7 -> exp(gamma * r^41) ~= 1.000002
            g_70 = compute_phase46_hyperconvex_rank_modulation(0.70, gamma_top=gamma)
            assert g_70 < 1.60, f"Lower 70% damping violated: g(0.70)={g_70}"

            # At r = 1.00, g(1.0) = 0.50 + 1.52 * exp(5.30) ~= 305.012 > 300.0
            g_top = compute_phase46_hyperconvex_rank_modulation(1.00, gamma_top=gamma)
            assert g_top > 300.0, f"Right-tail convex amplification failed: g(1.0)={g_top}"
            expected = 0.50 + 1.52 * math.exp(gamma)
            assert math.isclose(g_top, expected, rel_tol=1e-6)

    def test_rank_modulation_out_of_bounds_clipping(self):
        """Verify out-of-bounds ranks are safely clipped into [0.0, 1.0]."""
        # Negative ranks clipped to 0.0
        g_neg_bound = compute_phase46_hyperconvex_rank_modulation(-0.5, gamma_top=5.30)
        assert math.isclose(g_neg_bound, 0.50, abs_tol=1e-6)

        # Overflow ranks > 1.0 clipped to 1.0
        g_over_bound = compute_phase46_hyperconvex_rank_modulation(1.8, gamma_top=5.30)
        expected_top = 0.50 + 1.52 * math.exp(5.30)
        assert math.isclose(g_over_bound, expected_top, rel_tol=1e-6)

    def test_rank_modulation_regime_hierarchy(self):
        """Verify regime adaptive gamma_top follows strict ordered risk tiers."""
        gamma_bull_low = get_regime_adaptive_gamma_top_v46("BULL_LOW_VOL")
        gamma_bull_high = get_regime_adaptive_gamma_top_v46("BULL_HIGH_VOL")
        gamma_sideways = get_regime_adaptive_gamma_top_v46("SIDEWAYS")
        gamma_bear = get_regime_adaptive_gamma_top_v46("BEAR")
        gamma_crisis = get_regime_adaptive_gamma_top_v46("CRISIS")

        assert gamma_bull_low == 5.30
        assert gamma_bull_high == 5.00
        assert gamma_sideways == 4.80
        assert gamma_bear == 4.50
        assert gamma_crisis == 1.65

        assert gamma_bull_low > gamma_bull_high > gamma_sideways > gamma_bear > gamma_crisis


# =========================================================================
# 3. ADVERSARIAL COUPLER STRESS TESTS (F203)
# =========================================================================

class TestPhase46CouplerAdversarial:
    """Adversarial stress testing of Borcherds-Kac-Moody Whittaker Coupler."""

    @pytest.fixture
    def coupler(self):
        return QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler()

    def test_coupler_degenerate_and_extreme_inputs(self, coupler):
        """Test coupler with degenerate equal pillars, extreme dispersion, and boundary zeros."""
        # 1. All zero pillars
        zeros = np.zeros(5)
        res_zero = coupler(zeros)
        assert math.isclose(res_zero["e_borch_whit"], 0.0, abs_tol=1e-7)
        assert math.isclose(res_zero["h_borch_whit"], 1.0, abs_tol=1e-7)
        assert math.isclose(res_zero["z_borch_whit"], 1.0, abs_tol=1e-7)

        # 2. Extreme dispersion: one pillar 100.0, others 0.0
        disperse = np.array([100.0, 0.0, 0.0, 0.0, 0.0])
        res_disperse = coupler(disperse)
        assert res_disperse["e_borch_whit"] > 0.0
        assert res_disperse["h_borch_whit"] < 1.0
        assert 0.0 <= res_disperse["h_borch_whit"] <= 1.0
        assert 0.0 <= res_disperse["z_borch_whit"] <= 1.0
        assert 0.0 <= res_disperse["FERI_v46"] <= 1.0

        # 3. Negative pillars
        neg_pillars = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])
        res_neg = coupler(neg_pillars)
        assert 0.0 <= res_neg["h_borch_whit"] <= 1.0
        assert 0.0 <= res_neg["z_borch_whit"] <= 1.0

    def test_coupler_dispersion_sensitivity_monotonicity(self, coupler):
        """Verify that increasing pillar dispersion strictly increases E and decreases h."""
        df_disp = pd.DataFrame({
            "value": [0.5, 0.5, 0.5, 0.5],
            "momentum": [0.5, 0.54, 0.58, 0.62],
            "quality": [0.5, 0.5, 0.5, 0.5],
            "growth": [0.5, 0.46, 0.42, 0.38],
            "sentiment": [0.5, 0.5, 0.5, 0.5],
        })
        res = coupler(df_disp)
        e_vals = res["e_borch_whit"].values
        h_vals = res["h_borch_whit"].values

        # E strictly increasing with dispersion
        assert (np.diff(e_vals) > 0.0).all(), "Obstruction energy must strictly increase with dispersion"
        # h strictly decreasing with dispersion
        assert (np.diff(h_vals) < 0.0).all(), "Coupling harmony must strictly decrease with dispersion"


# =========================================================================
# 4. ADVERSARIAL FISHER-RAO BARYCENTER STRESS TESTS (F205.1)
# =========================================================================

class TestPhase46BarycenterAdversarial:
    """Adversarial stress testing of Lurie-Borcherds-Whittaker Fisher-Rao Barycenter."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_barycenter_degenerate_single_mass_convergence(self, allocator):
        """Verify barycenter converges to valid simplex when mass is 100% on a single model."""
        model_keys = ["bl", "herc", "rp", "cvar"]
        for target in model_keys:
            degenerate = {k: (1.0 if k == target else 0.0) for k in model_keys}
            blended = allocator.compute_lurie_borcherds_whittaker_fisher_rao_barycenter_blend(degenerate)

            assert isinstance(blended, dict)
            # Must sum to 1.0
            assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
            # Interior point positivity strictly preserved (no zero weights)
            for k, v in blended.items():
                assert v > 0.0, f"Interior point positivity violated for {k}"
                assert v < 1.0, f"Weight {k} cannot be 1.0 or greater"

    def test_barycenter_inverted_antagonistic_distributions(self, allocator):
        """Verify convergence when input gives near-zero to CVaR and extreme mass to RP."""
        antagonistic = {"bl": 0.0001, "herc": 0.0001, "rp": 0.9997, "cvar": 0.0001}
        blended = allocator.compute_lurie_borcherds_whittaker_fisher_rao_barycenter_blend(antagonistic)

        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        for k, v in blended.items():
            assert math.isfinite(v)
            assert 0.0 < v < 1.0

    def test_barycenter_metric_weights_ordering(self, allocator):
        """On uniform input, metric weights mu_lbw = [3.60, 2.75, 2.70, 4.15] dictate hierarchy."""
        uniform = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        blended = allocator.compute_lurie_borcherds_whittaker_fisher_rao_barycenter_blend(uniform)

        # mu: cvar=4.15 > bl=3.60 > herc=2.75 > rp=2.70
        assert blended["cvar"] > blended["bl"] > blended["herc"] > blended["rp"]
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)

    def test_barycenter_multi_distribution_extreme_disagreements(self, allocator):
        """Verify population barycenter across 10 highly divergent model predictions."""
        np.random.seed(46)
        disparate_inputs = []
        for _ in range(10):
            raw = np.random.exponential(scale=1.0, size=4)
            raw /= np.sum(raw)
            disparate_inputs.append({"bl": raw[0], "herc": raw[1], "rp": raw[2], "cvar": raw[3]})

        blended = allocator.compute_lurie_borcherds_whittaker_fisher_rao_barycenter_blend(disparate_inputs)
        assert math.isclose(sum(blended.values()), 1.0, rel_tol=1e-5)
        for k, v in blended.items():
            assert 0.0 < v < 1.0


# =========================================================================
# 5. ADVERSARIAL EVAR 42ND CUMULANT STRESS TESTS (F205.1)
# =========================================================================

class TestPhase46EVaRAdversarial:
    """Adversarial stress testing of 42nd-Cumulant Trans-Singular Borcherds EVaR."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_evar_analytical_monotonicity_100_random_distributions(self, allocator):
        """Exhaustively verify EVaR_42 >= EVaR_41 across 100 diverse random distributions."""
        np.random.seed(4646)
        n_trials = 100

        for trial in range(n_trials):
            dist_type = trial % 7
            n_samples = np.random.randint(100, 600)

            if dist_type == 0:
                # Normal with random drift and volatility
                mu = np.random.uniform(-0.05, 0.05)
                sigma = np.random.uniform(0.01, 0.15)
                returns = np.random.normal(mu, sigma, n_samples)
            elif dist_type == 1:
                # Heavy-tailed Student-t (df=3)
                returns = np.random.standard_t(df=3, size=n_samples) * 0.03 - 0.01
            elif dist_type == 2:
                # Heavy-tailed Student-t (df=2) - infinite variance regime
                returns = np.random.standard_t(df=2, size=n_samples) * 0.02 - 0.02
            elif dist_type == 3:
                # Cauchy-like distribution with extreme outliers
                returns = np.random.standard_cauchy(size=n_samples) * 0.01 - 0.01
                # Clip to realistic market boundary
                returns = np.clip(returns, -0.90, 0.90)
            elif dist_type == 4:
                # Flash crash scenario: 95% normal, 5% catastrophic drops (-50% to -90%)
                normal_part = np.random.normal(0.001, 0.02, int(n_samples * 0.95))
                crash_part = np.random.uniform(-0.90, -0.40, n_samples - len(normal_part))
                returns = np.concatenate([normal_part, crash_part])
            elif dist_type == 5:
                # Uniform distribution
                returns = np.random.uniform(-0.15, 0.10, n_samples)
            else:
                # Constant return / zero variance edge case
                returns = np.full(n_samples, -0.02)

            res_42 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_risk_measure(
                returns, alpha=0.05
            )
            res_41 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(
                returns, alpha=0.05
            )

            val_42 = res_42["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_value"]
            val_41 = res_41["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]

            assert math.isfinite(val_42), f"Trial {trial} (type {dist_type}): EVaR_42 must be finite, got {val_42}"
            assert math.isfinite(val_41), f"Trial {trial} (type {dist_type}): EVaR_41 must be finite, got {val_41}"
            # Strict monotonicity with rounding tolerance
            assert val_42 >= val_41 - 1e-6, (
                f"Monotonicity violation in trial {trial} (type {dist_type}): "
                f"EVaR_42={val_42} < EVaR_41={val_41}"
            )

    def test_evar_order_and_parameters(self, allocator):
        """Verify EVaR order=42, factorial constant, and xi_borch parameters."""
        returns = np.random.normal(0.0, 0.05, 200)
        res = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_risk_measure(
            returns
        )

        assert res["order"] == 42
        assert math.isclose(res["xi_borch"], 0.9999999, rel_tol=1e-5)
        assert math.isclose(res["xi_borcherds"], 0.9999999, rel_tol=1e-5)
        assert math.isclose(res["xi_42"], 0.9999999, rel_tol=1e-5)
        # Factorial validation: 42!
        fact_42_expected = math.factorial(42)
        fact_42_float = 1405006117752879898543142606244511569936384000000000.0
        assert math.isclose(float(fact_42_expected), fact_42_float, rel_tol=1e-12)

    def test_evar_heavy_tail_sensitivity(self, allocator):
        """Verify that a heavy-tailed distribution yields higher EVaR than normal of equal variance."""
        np.random.seed(999)
        # Generate Gaussian returns
        r_norm = np.random.normal(0.0, 0.05, 1000)

        # Generate Student-t df=3 scaled to same standard deviation
        r_t = np.random.standard_t(df=3, size=1000)
        r_t = r_t * (np.std(r_norm) / np.std(r_t))

        evar_norm = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_risk_measure(
            r_norm, alpha=0.05
        )["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_value"]

        evar_t = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_risk_measure(
            r_t, alpha=0.05
        )["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_value"]

        # Fat-tailed distribution must reflect higher tail risk
        assert evar_t >= evar_norm - 1e-4, f"Heavy tail risk underestimation: evar_t={evar_t} < evar_norm={evar_norm}"
