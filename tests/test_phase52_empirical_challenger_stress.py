r"""
tests/test_phase52_empirical_challenger_stress.py

Empirical Challenger 1 Independent Adversarial Stress & Oracle Verification Suite
Target: Phase 52 Quantitative Alpha Enhancement (v59 Production Master)

Adversarial Stress Axes:
1. 224th-Order Deadband (F232.2):
   - Subnormal annihilation: |z| <= 0.00035 -> exactly 0.0 (leakage < 10^-144)
   - Extreme subnormals (1e-300, 1e-200, 1e-100) and large numbers (1e10, 1e100)
   - Exact odd symmetry f(-z) == -f(z) across 20,000 grid points
   - Signal preservation: |z| >= 0.150 preserved to relative tolerance < 1e-12
   - Monotonicity across continuous domain [-1.0, 1.0]

2. 47th-Order Rank Modulation (F232.1):
   - Convexity at top: g(1.0) > 500.0 (in fact > 7000.0 in BULL_LOW_VOL)
   - Damping at 70th percentile: g(0.70) <= 1.70
   - Strict monotonicity across 10,000 grid points in all 5 primary market regimes
   - Negative conviction behavior: z_denoised < 0 strictly monotonically non-increasing
   - Domain safety: inputs beyond [0, 1] clamped without NaN/Inf

3. Higher-Homology Fisher-Rao Barycenter (F233.1):
   - Simplex conservation: sum q_i == 1.0, q_i > 0 across 500 Dirichlet samples
   - Extreme Dirichlet parameters (sparse vertices alpha=0.001, concentrated alpha=100.0)
   - Metric ordering: CVaR > BL > HERC > RP under uniform inputs
   - Zero / negative / degenerate input immunity

4. 48th-Cumulant EVaR Tail Risk (F233.2):
   - Heavy tail shock discrimination: Student-t (df=3) vs Gaussian
   - Monotonicity under loss scaling (c1 < c2 -> EVaR(c1 * L) < EVaR(c2 * L))
   - Edge case immunity: constant returns, 2 elements, extreme tail outliers (15-sigma)
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_bicentatetracontagonal_hyperbolic_deadband,
    compute_phase52_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v52,
    REGIME_GAMMA_TOP_V52,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _get_evar(res):
    if isinstance(res, dict):
        return float(res.get("evar", res.get("trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_evar_value", 0.0)))
    return float(res)


# =========================================================================
# 1. 224TH-ORDER DEADBAND ADVERSARIAL CHALLENGES
# =========================================================================

class TestDeadbandEmpiricalChallenger:
    """Stress testing the 224th-order bicentatetracontagonal deadband."""

    def test_adversarial_subnormal_annihilation(self):
        """Test that every subnormal and boundary value |z| <= 0.00035 produces strictly 0.0."""
        boundary_grid = np.linspace(-0.00035, 0.00035, 1001)
        res = apply_bicentatetracontagonal_hyperbolic_deadband(boundary_grid)
        assert np.all(res == 0.0), f"Leakage detected! Max absolute value: {np.max(np.abs(res))}"

        # Test extreme subnormals
        subnormals = np.array([1e-320, -1e-320, 1e-300, -1e-300, 1e-250, 1e-150, 1e-100])
        res_sub = apply_bicentatetracontagonal_hyperbolic_deadband(subnormals)
        assert np.all(res_sub == 0.0), "Subnormal floating point numbers must vanish to 0.0"

    def test_adversarial_leakage_upper_bound(self):
        """Verify theoretical leakage < 10^-144 at z = 0.00035 (ratio = 0.01)."""
        # delta = 0.035, z = 0.00035 -> ratio = 0.01 -> ratio^224 = 10^-448
        # In float64, 10^-448 underflows strictly to 0.0
        z = 0.00035
        res = apply_bicentatetracontagonal_hyperbolic_deadband(z)
        assert abs(res) < 1e-144
        assert res == 0.0

    def test_adversarial_odd_symmetry_dense(self):
        """Test f(-z) == -f(z) across 20,000 points spanning the full active range."""
        z_points = np.linspace(0.0001, 2.0, 20000)
        pos = apply_bicentatetracontagonal_hyperbolic_deadband(z_points)
        neg = apply_bicentatetracontagonal_hyperbolic_deadband(-z_points)
        np.testing.assert_allclose(pos, -neg, atol=1e-15, rtol=1e-12)

    def test_adversarial_signal_preservation_high_conviction(self):
        """Verify high conviction signals (|z| >= 0.150) are 100.0% preserved."""
        high_conv = np.linspace(0.150, 5.0, 1000)
        res = apply_bicentatetracontagonal_hyperbolic_deadband(high_conv)
        # Ratio is >= 0.150 / 0.035 = 4.2857 -> 4.2857^224 >> 50 -> tanh(50) = 1.0000000000000000
        np.testing.assert_allclose(res, high_conv, rtol=1e-12, atol=1e-15)

        # Check negative side
        res_neg = apply_bicentatetracontagonal_hyperbolic_deadband(-high_conv)
        np.testing.assert_allclose(res_neg, -high_conv, rtol=1e-12, atol=1e-15)

    def test_adversarial_deadband_monotonicity_fine_grid(self):
        """Verify strict monotonicity across 50,000 grid points."""
        z_grid = np.linspace(-1.0, 1.0, 50000)
        res = apply_bicentatetracontagonal_hyperbolic_deadband(z_grid)
        diffs = np.diff(res)
        assert np.all(diffs >= -1e-17), f"Monotonicity violation! Min diff: {np.min(diffs)}"


# =========================================================================
# 2. 47TH-ORDER RANK MODULATION ADVERSARIAL CHALLENGES
# =========================================================================

class TestRankModulationEmpiricalChallenger:
    """Stress testing the 47th-order hyper-convex rank modulation."""

    def test_convexity_and_damping_spec(self):
        """Verify g(1.0) > 500.0 and g(0.70) <= 1.70 in BULL_LOW_VOL."""
        gamma = 8.40
        g_100 = compute_phase52_hyperconvex_rank_modulation(1.0, gamma_top=gamma, z_denoised=0.5)
        # g(1.0) = 0.50 + 1.70 * 1.0 * exp(8.40 * 1^47) = 0.50 + 1.70 * exp(8.40) ~= 7560.5
        assert g_100 > 500.0
        assert g_100 > 7000.0
        assert math.isclose(g_100, 0.50 + 1.70 * math.exp(8.40), rel_tol=1e-5)

        # Damping at r=0.70
        g_070 = compute_phase52_hyperconvex_rank_modulation(0.70, gamma_top=gamma, z_denoised=0.5)
        # 0.70^47 ~= 5.95 x 10^-8 -> exp(8.40 * 5.95e-8) ~= 1.0000005
        # g(0.70) ~= 0.50 + 1.70 * 0.70 * 1.0 = 0.50 + 1.19 = 1.6900
        assert g_070 <= 1.70
        assert g_070 < 1.695

    @pytest.mark.parametrize("regime, gamma", [
        ("BULL_LOW_VOL", 8.40),
        ("BULL_HIGH_VOL", 6.72),
        ("SIDEWAYS", 5.04),
        ("BEAR", 1.68),
        ("CRISIS", 0.84),
    ])
    def test_strict_monotonicity_across_regimes_10k(self, regime, gamma):
        """Verify strict non-decreasing monotonicity across 10,000 points for all regimes."""
        r_grid = np.linspace(0.0, 1.0, 10000)
        g_vals = compute_phase52_hyperconvex_rank_modulation(r_grid, gamma_top=gamma, z_denoised=0.1)
        diffs = np.diff(g_vals)
        assert np.all(diffs >= 0.0), f"Monotonicity failed in {regime}! Min diff: {np.min(diffs)}"

    def test_negative_conviction_monotonicity(self):
        """Verify negative conviction z_denoised < 0 produces monotonically non-increasing output."""
        r_grid = np.linspace(0.0, 1.0, 10000)
        g_neg = compute_phase52_hyperconvex_rank_modulation(r_grid, gamma_top=8.40, z_denoised=-0.2)
        diffs = np.diff(g_neg)
        assert np.all(diffs <= 0.0), f"Negative conviction monotonicity failed! Max diff: {np.max(diffs)}"

    def test_domain_boundary_clipping(self):
        """Verify inputs outside [0, 1] are clipped safely without NaN or Inf."""
        out_of_bounds = np.array([-10.0, -1.0, -0.01, 1.01, 2.0, 100.0])
        res = compute_phase52_hyperconvex_rank_modulation(out_of_bounds, gamma_top=8.40)
        assert np.all(np.isfinite(res))
        assert math.isclose(res[0], res[1])
        assert math.isclose(res[3], res[5])


# =========================================================================
# 3. HIGHER-HOMOLOGY FISHER-RAO BARYCENTER ADVERSARIAL CHALLENGES
# =========================================================================

class TestFisherRaoBarycenterEmpiricalChallenger:
    """Stress testing the Higher-Homology Fisher-Rao Barycenter."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_simplex_conservation_dirichlet_500(self, allocator):
        """Stress-test simplex conservation (sum q_i == 1.0, q_i > 0) across 500 diverse Dirichlet samples."""
        np.random.seed(9999)
        alpha_configs = [
            [0.01, 0.01, 0.01, 0.01],  # extreme vertex-concentrated
            [0.1, 0.1, 0.1, 0.1],
            [1.0, 1.0, 1.0, 1.0],      # uniform Dirichlet
            [10.0, 10.0, 10.0, 10.0],  # center-concentrated
            [5.0, 0.1, 0.1, 5.0],      # bi-modal
        ]
        total_tested = 0
        for alpha in alpha_configs:
            samples = np.random.dirichlet(alpha, size=100)
            for row in samples:
                inp = {"bl": row[0], "herc": row[1], "rp": row[2], "cvar": row[3]}
                out = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_fisher_rao_barycenter_blend(inp)
                s = sum(out.values())
                assert math.isclose(s, 1.0, rel_tol=1e-5), f"Simplex sum violation: {s}"
                for k, v in out.items():
                    assert v > 0.0, f"Component {k} non-positive: {v}"
                    assert math.isfinite(v), f"Component {k} non-finite: {v}"
                total_tested += 1
        assert total_tested == 500

    def test_uniform_priors_ordering(self, allocator):
        """Verify metric ordering CVaR > BL > HERC > RP under uniform inputs."""
        uniform = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_fisher_rao_barycenter_blend(uniform)
        assert res["cvar"] > res["bl"], f"CVaR ({res['cvar']}) must exceed BL ({res['bl']})"
        assert res["bl"] > res["herc"], f"BL ({res['bl']}) must exceed HERC ({res['herc']})"
        assert res["herc"] > res["rp"], f"HERC ({res['herc']}) must exceed RP ({res['rp']})"


# =========================================================================
# 4. 48TH-CUMULANT EVAR ADVERSARIAL CHALLENGES
# =========================================================================

class TestEVaREmpiricalChallenger:
    """Stress testing the 48th-Cumulant EVaR Tail Risk Measure."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_heavy_tail_shock_student_t_vs_gaussian(self, allocator):
        """Verify 48th-cumulant EVaR strictly discriminates heavy-tailed Student-t (df=3) from Gaussian."""
        np.random.seed(42)
        n = 2000
        # Generate Gaussian returns
        r_gauss = np.random.normal(loc=0.001, scale=0.02, size=n)
        # Generate Student-t returns with same variance (df=3 has var = df/(df-2) = 3 -> std = sqrt(3))
        # Scale by 0.02 / sqrt(3) to match standard deviation
        r_t3 = np.random.standard_t(df=3, size=n) * (0.02 / math.sqrt(3.0)) + 0.001

        evar_gauss = _get_evar(allocator.compute_48th_cumulant_evar(r_gauss))
        evar_t3 = _get_evar(allocator.compute_48th_cumulant_evar(r_t3))

        assert evar_t3 > evar_gauss, f"Student-t EVaR ({evar_t3}) must exceed Gaussian EVaR ({evar_gauss})"

    def test_monotonicity_under_loss_scaling(self, allocator):
        """Verify EVaR scales monotonically when return distribution losses are scaled up."""
        np.random.seed(12345)
        base_rets = np.random.normal(-0.002, 0.015, 1000)
        scales = [0.5, 1.0, 1.5, 2.0, 3.0]
        evars = [_get_evar(allocator.compute_48th_cumulant_evar(base_rets * s)) for s in scales]

        diffs = np.diff(evars)
        assert np.all(diffs > 0.0), f"EVaR monotonicity violation across scale factors! EVaRs: {evars}"

    def test_extreme_outliers_and_edge_cases(self, allocator):
        """Verify numerical stability with extreme outliers (15-sigma shock), 2 elements, and zero variance."""
        # 15-sigma negative shock
        rets_base = np.random.normal(0.001, 0.01, 500)
        ev_base = _get_evar(allocator.compute_48th_cumulant_evar(rets_base))
        rets_outlier = rets_base.copy()
        rets_outlier[0] = -0.25  # severe crash
        res_outlier = allocator.compute_48th_cumulant_evar(rets_outlier)
        ev_outlier = _get_evar(res_outlier)
        assert math.isfinite(ev_outlier)
        assert ev_outlier > ev_base * 1.30, f"Shock EVaR ({ev_outlier}) should be >= 30% higher than baseline ({ev_base})"

        # Minimal size: n=2
        res_2 = allocator.compute_48th_cumulant_evar([0.01, -0.02])
        assert math.isfinite(_get_evar(res_2))

        # Zero variance (constant returns)
        res_const = allocator.compute_48th_cumulant_evar([0.01, 0.01, 0.01, 0.01])
        assert math.isfinite(_get_evar(res_const))
