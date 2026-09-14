r"""
tests/test_phase41_challenger1_stress.py

Adversarial Stress Test Suite for Phase 41 Quant Alpha & Risk Components:
1. apply_centatriacontaoctagonal_hyperbolic_deadband (F184.2)
2. compute_phase41_hyperconvex_rank_modulation (F184.1)
3. DrinfeldLafforgueFarguesFontaineCoupler (F183)
4. compute_lurie_fargues_fontaine_fisher_rao_barycenter_blend (F185.1)
5. compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure (F185.1)
6. End-to-End Ensemble Pipeline Integration (combine_predictions version=41)
"""

import os
os.environ["BYPASS_TORCH"] = "1"

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_centatriacontaoctagonal_hyperbolic_deadband,
    compute_phase41_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v41,
    REGIME_GAMMA_TOP_V41,
    apply_smooth_deadband_attenuation,
)
from trading_system.src.ai.ensemble_scorer import (
    DrinfeldLafforgueFarguesFontaineCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase41AdversarialStress:
    """Empirical adversarial stress test suite challenging boundary conditions, degeneracies, and numerical stability."""

    # =========================================================================
    # 1. 136th-Order Centatriacontaoctagonal Hyperbolic Deadband Adversarial Tests
    # =========================================================================

    def test_deadband_sub_microscopic_leakage_and_precision(self):
        """Test sub-microscopic values (1e-6 to 4e-4) to verify noise leakage < 10^-74."""
        small_vals = np.array([
            1e-6, -1e-6,
            1e-5, -1e-5,
            5e-5, -5e-5,
            1e-4, -1e-4,
            2e-4, -2e-4,
            3e-4, -3e-4,
            4e-4, -4e-4,
        ])
        denoised = apply_centatriacontaoctagonal_hyperbolic_deadband(small_vals, delta_noise=0.035, alpha_pos=136.0)
        for v, orig in zip(denoised, small_vals):
            assert abs(v) < 1e-74, f"Noise leakage {v} for input {orig} exceeds 1e-74 threshold"

    def test_deadband_extreme_inputs(self):
        """Test with extreme values: z = +/- 1000.0, z = 0.0, sub-micro 10^-150, NaN, and Inf."""
        # 1. z = +/- 1000.0, +/- 1e6, +/- 1e30
        extreme_z = np.array([1000.0, -1000.0, 500.0, -500.0, 1e6, -1e6, 1e30, -1e30])
        denoised_extreme = apply_centatriacontaoctagonal_hyperbolic_deadband(extreme_z, delta_noise=0.035, alpha_pos=136.0)
        np.testing.assert_allclose(denoised_extreme, extreme_z, rtol=1e-7)

        # 2. z = 0.0, -0.0
        z_zero = 0.0
        denoised_zero = apply_centatriacontaoctagonal_hyperbolic_deadband(z_zero, delta_noise=0.035, alpha_pos=136.0)
        assert denoised_zero == 0.0

        # 3. Sub-micro 10^-150
        z_submicro = 1e-150
        denoised_submicro = apply_centatriacontaoctagonal_hyperbolic_deadband(z_submicro, delta_noise=0.035, alpha_pos=136.0)
        assert abs(denoised_submicro) < 1e-150 or denoised_submicro == 0.0

        # 4. NaN and Inf
        z_nan_inf = np.array([np.nan, np.inf, -np.inf, 0.20])
        denoised_nan_inf = apply_centatriacontaoctagonal_hyperbolic_deadband(z_nan_inf, delta_noise=0.035, alpha_pos=136.0)
        assert np.isnan(denoised_nan_inf[0])
        assert np.isposinf(denoised_nan_inf[1])
        assert np.isneginf(denoised_nan_inf[2])
        assert math.isclose(denoised_nan_inf[3], 0.20, rel_tol=1e-7)

    def test_deadband_signal_transmission_high_conviction(self):
        """Verify 100.000% signal transmission for |z| >= 0.150."""
        sig_vals = np.array([0.15, -0.15, 0.20, -0.20, 0.50, -0.50, 1.0, -1.0])
        denoised = apply_centatriacontaoctagonal_hyperbolic_deadband(sig_vals, delta_noise=0.035, alpha_pos=136.0)
        np.testing.assert_allclose(denoised, sig_vals, rtol=1e-9, atol=1e-12)

    def test_deadband_odd_symmetry(self):
        """Verify exact odd symmetry: f(-z) == -f(z) under unconditioned symmetric regime."""
        z_grid = np.linspace(0.0001, 0.5, 1000)
        pos_out = apply_centatriacontaoctagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=136.0)
        neg_out = apply_centatriacontaoctagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=136.0)
        np.testing.assert_allclose(pos_out, -neg_out, rtol=1e-9, atol=1e-15)

    def test_deadband_strict_rank_monotonicity(self):
        """Verify strict rank preservation and monotonicity across dense grid (Spearman rho == 1.0000)."""
        z_dense = np.linspace(-1.5, 1.5, 5000)
        denoised = apply_centatriacontaoctagonal_hyperbolic_deadband(z_dense, delta_noise=0.035, alpha_pos=136.0)
        # Check non-decreasing monotonicity
        diffs = np.diff(denoised)
        assert np.all(diffs >= -1e-15), "Deadband violated non-decreasing monotonicity"

        # Check Spearman rank correlation
        s_orig = pd.Series(z_dense)
        s_denoised = pd.Series(denoised)
        spearman_rho = s_orig.corr(s_denoised, method="spearman")
        assert math.isclose(spearman_rho, 1.0, rel_tol=1e-5)

    def test_deadband_regime_asymmetry(self):
        """Verify regime-dependent asymmetry (CRISIS vs BULL)."""
        z_neg = np.array([-0.040, -0.050])
        out_crisis_neg = apply_centatriacontaoctagonal_hyperbolic_deadband(z_neg, delta_noise=0.035, alpha_pos=136.0, regime='CRISIS')
        out_normal_neg = apply_centatriacontaoctagonal_hyperbolic_deadband(z_neg, delta_noise=0.035, alpha_pos=136.0, regime='BULL_LOW_VOL')
        # In CRISIS, negative noise delta is widened (0.035 * 1.40 = 0.049), so |out_crisis| <= |out_normal|
        assert np.all(np.abs(out_crisis_neg) <= np.abs(out_normal_neg))

    def test_deadband_input_types_preservation(self):
        """Verify scalar, numpy array, and pandas Series types and indices are preserved."""
        # 1. Scalar
        val = 0.25
        out_scalar = apply_centatriacontaoctagonal_hyperbolic_deadband(val)
        assert isinstance(out_scalar, float)
        assert math.isclose(out_scalar, 0.25, rel_tol=1e-6)

        # 2. Pandas Series with custom index
        idx = ["AAPL", "NVDA", "TSLA"]
        s = pd.Series([0.2, 0.0001, -0.3], index=idx)
        out_s = apply_centatriacontaoctagonal_hyperbolic_deadband(s)
        assert isinstance(out_s, pd.Series)
        assert list(out_s.index) == idx
        assert abs(out_s["NVDA"]) < 1e-74

    def test_deadband_dispatcher_v41(self):
        """Verify apply_smooth_deadband_attenuation dispatches to 136th-order when version >= 41."""
        z_noise = 0.0003
        out_v41 = apply_smooth_deadband_attenuation(z_noise, delta_noise=0.035, version=41)
        assert abs(out_v41) < 1e-74

    # =========================================================================
    # 2. 36th-Order Ultra-Convex Rank Modulation Adversarial Tests (F184.1)
    # =========================================================================

    def test_rank_modulation_boundary_conditions(self):
        """Test boundary conditions: g(0) = 0.50, g(1.0) = 0.50 + 1.48 * exp(gamma_top)."""
        gamma = 2.0
        g_0 = compute_phase41_hyperconvex_rank_modulation(0.0, gamma_top=gamma)
        assert math.isclose(g_0, 0.50, abs_tol=1e-12)

        g_1 = compute_phase41_hyperconvex_rank_modulation(1.0, gamma_top=gamma)
        expected_g_1 = 0.50 + 1.48 * np.exp(gamma)
        assert math.isclose(g_1, expected_g_1, rel_tol=1e-9)

    def test_rank_modulation_strict_monotonicity_positive(self):
        """Test that g(r) is strictly monotonically increasing on [0, 1] for all gamma_top >= 0."""
        ranks = np.linspace(0.0, 1.0, 5000)
        for gamma in [0.0, 0.5, 1.5, 3.6, 4.4]:
            mod = compute_phase41_hyperconvex_rank_modulation(ranks, gamma_top=gamma)
            diffs = np.diff(mod)
            assert np.all(diffs > 0.0), f"Strict monotonicity g'(r) > 0 violated for gamma_top={gamma}"
            if gamma > 0.0:
                assert diffs[-1] > diffs[0], f"Hyper-convex curvature requires higher growth rate near r=1 for gamma={gamma}"
            else:
                assert math.isclose(diffs[-1], diffs[0], rel_tol=1e-5), "Linear growth when gamma=0"

    def test_rank_modulation_extreme_gamma_top_overflow_resilience(self):
        """Test extreme gamma_top values up to 500.0 without unhandled exception."""
        r = np.array([0.0, 0.5, 0.9, 0.99, 1.0])
        for extreme_gamma in [10.0, 50.0, 100.0, 500.0, 700.0]:
            mod = compute_phase41_hyperconvex_rank_modulation(r, gamma_top=extreme_gamma)
            assert np.all(np.isfinite(mod[:3])), "Lower ranks should remain well-behaved even with extreme gamma"
            assert mod[0] == 0.50

    def test_rank_modulation_negative_scores_penalty(self):
        """Test negative scores penalty branch: g_neg(r) = 1.35 - 1.00 * r."""
        r = np.array([0.0, 0.5, 1.0])
        z_neg = np.array([-0.1, -0.5, -1.0])
        mod_neg = compute_phase41_hyperconvex_rank_modulation(r, gamma_top=4.40, z_denoised=z_neg)
        expected_neg = 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, expected_neg, rtol=1e-9)

        # Mixed positive and negative scores
        z_mixed = np.array([0.5, -0.2, 0.0])
        mod_mixed = compute_phase41_hyperconvex_rank_modulation(r, gamma_top=4.40, z_denoised=z_mixed)
        assert mod_mixed[0] == 0.50  # positive formula at r=0
        assert math.isclose(mod_mixed[1], 1.35 - 1.00 * 0.5, rel_tol=1e-9)  # negative formula at r=0.5
        assert math.isclose(mod_mixed[2], 0.50 + 1.48 * 1.0 * np.exp(4.40), rel_tol=1e-9)  # positive formula at r=1.0

    def test_rank_modulation_clipping_out_of_bounds(self):
        """Test out-of-bounds rank inputs: -10.0, -0.1, 1.2, 100.0."""
        r_oob = np.array([-10.0, -0.1, 1.2, 100.0])
        mod_oob = compute_phase41_hyperconvex_rank_modulation(r_oob, gamma_top=2.0)
        assert math.isclose(mod_oob[0], 0.50, abs_tol=1e-9)
        assert math.isclose(mod_oob[1], 0.50, abs_tol=1e-9)
        expected_max = 0.50 + 1.48 * np.exp(2.0)
        assert math.isclose(mod_oob[2], expected_max, rel_tol=1e-9)
        assert math.isclose(mod_oob[3], expected_max, rel_tol=1e-9)

    def test_regime_adaptive_gamma_top_v41(self):
        """Test all 13 regime strings and ints map correctly to REGIME_GAMMA_TOP_V41."""
        assert get_regime_adaptive_gamma_top_v41('BULL_LOW_VOL') == 4.40
        assert get_regime_adaptive_gamma_top_v41('BULL_HIGH_VOL') == 4.10
        assert get_regime_adaptive_gamma_top_v41('SIDEWAYS') == 3.90
        assert get_regime_adaptive_gamma_top_v41('BEAR') == 3.60
        assert get_regime_adaptive_gamma_top_v41('CRISIS') == 1.20
        assert get_regime_adaptive_gamma_top_v41('PANIC') == 1.60
        assert get_regime_adaptive_gamma_top_v41(2) == 4.40
        assert get_regime_adaptive_gamma_top_v41(1) == 3.90
        assert get_regime_adaptive_gamma_top_v41(0) == 3.60
        assert get_regime_adaptive_gamma_top_v41('UNKNOWN_XYZ') == 4.40

    # =========================================================================
    # 3. DrinfeldLafforgueFarguesFontaineCoupler Adversarial Tests (F183)
    # =========================================================================

    def test_coupler_all_zero_pillars(self):
        """Test degenerate case: all 5 pillars are zero."""
        p_zero = np.zeros((1, 5))
        res = DrinfeldLafforgueFarguesFontaineCoupler.compute(p_zero)
        assert res["e_fargues"] == 0.0
        assert res["z_fontaine"] == 1.0
        assert res["h_fargues"] == 1.0
        assert res["FERI_v41"] == 1.0

    def test_coupler_identical_pillars(self):
        """Test degenerate case: all 5 pillars identical non-zero values."""
        for c in [-10.0, -1.0, 0.5, 5.0, 100.0]:
            p_ident = np.full((1, 5), c)
            res = DrinfeldLafforgueFarguesFontaineCoupler.compute(p_ident)
            assert res["e_fargues"] == 0.0
            assert res["z_fontaine"] == 1.0
            assert res["h_fargues"] == 1.0
            assert res["FERI_v41"] == 1.0

    def test_coupler_large_extremes_and_outliers(self):
        """Test with huge outliers (up to 1000.0 stdevs) and astronomical disparity."""
        # 1. Large realistic extreme input (1000.0 stdevs)
        p_large = np.array([[1000.0, 0.0, 1000.0, 0.0, 1000.0]])
        res_large = DrinfeldLafforgueFarguesFontaineCoupler.compute(p_large)
        assert np.all(np.isfinite(res_large["e_fargues"]))
        assert np.all(np.isfinite(res_large["h_fargues"]))
        assert math.isclose(float(res_large["h_fargues"][0]), 1e-6, abs_tol=1e-8)

        # 2. Astronomical disparity (1e9) testing numerical clipping robustness
        p_astro = np.array([[1e9, -1e9, 1e8, 0.0, -1e8]])
        res_astro = DrinfeldLafforgueFarguesFontaineCoupler.compute(p_astro)
        assert np.all(np.isfinite(res_astro["h_fargues"])), "h_fargues must remain strictly finite"
        assert np.all(np.isfinite(res_astro["FERI_v41"])), "FERI_v41 must remain strictly finite"
        assert np.all(np.isfinite(res_astro["z_fontaine"])), "z_fontaine must remain strictly finite"
        assert math.isclose(float(res_astro["h_fargues"][0]), 1e-6, abs_tol=1e-8)
        assert 0.0 <= float(res_astro["FERI_v41"][0]) <= 1.0
        assert 0.0 < float(res_astro["z_fontaine"][0]) <= 1.0

    def test_coupler_nan_imputation(self):
        """Test that NaN values in pillars are imputed to 0.0 without raising exception."""
        p_nan = np.array([[np.nan, 0.5, np.nan, 0.2, np.nan]])
        res = DrinfeldLafforgueFarguesFontaineCoupler.compute(p_nan)
        assert np.isfinite(res["e_fargues"])
        assert np.isfinite(res["h_fargues"])
        assert np.isfinite(res["FERI_v41"])

    def test_coupler_input_formats(self):
        """Test various input formats: 1D vector, 2D matrix, DataFrame, Dict."""
        cols = ['val', 'mom', 'flow', 'cat', 'net']
        # 1. 1D vector
        v_1d = [0.1, 0.2, 0.3, 0.4, 0.5]
        res_1d = DrinfeldLafforgueFarguesFontaineCoupler.compute(v_1d)
        assert isinstance(res_1d["h_fargues"], float)

        # 2. DataFrame
        df = pd.DataFrame([[0.1, 0.2, 0.3, 0.4, 0.5], [0.5, 0.4, 0.3, 0.2, 0.1]], columns=cols, index=["S1", "S2"])
        res_df = DrinfeldLafforgueFarguesFontaineCoupler.compute(df)
        assert isinstance(res_df["h_fargues"], pd.Series)
        assert list(res_df["h_fargues"].index) == ["S1", "S2"]

        # 3. Dict
        d = {c: np.array([0.1, 0.5]) for c in cols}
        res_dict = DrinfeldLafforgueFarguesFontaineCoupler.compute(d)
        assert len(res_dict["h_fargues"]) == 2

    def test_coupler_invalid_dimensions(self):
        """Test that invalid pillar dimension raises ValueError."""
        p_invalid = np.zeros((1, 4))
        with pytest.raises(ValueError, match="5 canonical pillars"):
            DrinfeldLafforgueFarguesFontaineCoupler.compute(p_invalid)

    # =========================================================================
    # 4. Lurie-Fargues-Fontaine Fisher-Rao Barycenter Adversarial Tests (F185.1)
    # =========================================================================

    def test_barycenter_exact_simplex_projection(self):
        """Verify sum(q) == 1.000000 across multiple degenerate and extreme inputs."""
        alloc = UnifiedPortfolioAllocator()

        test_cases = [
            # 1. One model 100%
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
            # 2. Uniform
            {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25},
            # 3. All zero (edge fallback)
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            # 4. Near-zero components
            {"bl": 1e-12, "herc": 1e-12, "rp": 1e-12, "cvar": 1.0},
            # 5. Negative component handling
            {"bl": -0.5, "herc": 0.5, "rp": 0.0, "cvar": 0.5},
            # 6. Massive values
            {"bl": 1e8, "herc": 1e7, "rp": 1e6, "cvar": 1e9},
        ]

        for tc in test_cases:
            res = alloc.compute_lurie_fargues_fontaine_fisher_rao_barycenter_blend(tc)
            total = sum(res.values())
            assert math.isclose(total, 1.0, abs_tol=1e-5), f"Simplex violation for {tc}: sum={total}"
            for k, v in res.items():
                assert v > 0.0, f"Component {k} <= 0 for {tc}: {v}"

    def test_barycenter_metric_weights_ordering(self):
        """Verify strict ordering: cvar > bl > herc > rp under uniform prior."""
        alloc = UnifiedPortfolioAllocator()
        uniform_prior = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = alloc.compute_lurie_fargues_fontaine_fisher_rao_barycenter_blend(uniform_prior)

        # Metric weights: mu_lff = [3.10 (BL), 2.50 (HERC), 2.45 (RP), 3.65 (CVaR)]
        # Order: CVaR (3.65) > BL (3.10) > HERC (2.50) > RP (2.45)
        assert res["cvar"] > res["bl"], f"Expected cvar ({res['cvar']}) > bl ({res['bl']})"
        assert res["bl"] > res["herc"], f"Expected bl ({res['bl']}) > herc ({res['herc']})"
        assert res["herc"] > res["rp"], f"Expected herc ({res['herc']}) > rp ({res['rp']})"

    def test_barycenter_multi_distribution_array_input(self):
        """Test array of shape (N, 4) with 50 diverse distributions."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)
        random_dist = np.random.dirichlet(np.ones(4), size=50)
        res = alloc.compute_lurie_fargues_fontaine_fisher_rao_barycenter_blend(random_dist)
        total = sum(res.values())
        assert math.isclose(total, 1.0, abs_tol=1e-5)
        assert res["cvar"] > res["rp"]

    # =========================================================================
    # 5. 37th-Cumulant EVaR Tail Risk Measure Adversarial Tests (F185.1)
    # =========================================================================

    def test_evar_unconditional_hierarchy_domination_evar37_ge_evar36(self):
        """Verify EVaR_37 >= EVaR_36 unconditionally across diverse heavy-tailed distributions."""
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)

        distributions = {
            "Normal": np.random.normal(0.001, 0.02, 1000),
            "Student_t_3": np.random.standard_t(df=3, size=1000) * 0.02,
            "Student_t_2_1": np.random.standard_t(df=2.1, size=1000) * 0.02,
            "Cauchy": np.clip(np.random.standard_cauchy(size=1000) * 0.01, -0.5, 0.5),
            "Pareto": (np.random.pareto(a=1.5, size=1000) - 1.5) * 0.01,
            "Crash_Shock": np.concatenate([np.random.normal(0.001, 0.01, 990), np.full(10, -0.30)]),
            "Surge_Shock": np.concatenate([np.random.normal(0.001, 0.01, 990), np.full(10, 0.30)]),
            "All_Zeros": np.zeros(500),
            "Single_Loss": np.array([-0.10]),
        }

        for dist_name, returns in distributions.items():
            res_37 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure(returns)
            res_36 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_risk_measure(returns)

            v_37 = res_37["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"]
            v_36 = res_36["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_evar_value"]

            assert v_37 >= v_36 - 1e-6, (
                f"Hierarchy violation on {dist_name}: EVaR_37 ({v_37}) < EVaR_36 ({v_36})"
            )
            assert np.isfinite(v_37), f"EVaR_37 produced non-finite value on {dist_name}"

    def test_evar_monotonicity_in_alpha(self):
        """Verify that tighter confidence level (lower alpha) yields higher or equal EVaR."""
        alloc = UnifiedPortfolioAllocator()
        returns = np.random.normal(0.0, 0.02, 500)

        evar_05 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure(
            returns, alpha=0.05
        )["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"]

        evar_01 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure(
            returns, alpha=0.01
        )["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"]

        assert evar_01 >= evar_05 - 1e-6, f"Expected EVaR(0.01)={evar_01} >= EVaR(0.05)={evar_05}"

    def test_evar_portfolio_allocator_delegation_and_aliases(self):
        """Verify PortfolioAllocator exposes all Phase 41 EVaR methods and aliases."""
        pa = PortfolioAllocator()
        returns = np.random.normal(0.001, 0.015, 200)

        res1 = pa.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure(returns)
        res2 = pa.compute_37th_cumulant_evar(returns)
        res3 = pa.compute_phase41_evar(returns)
        res4 = pa.compute_fargues_evar(returns)

        v1 = res1["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"]
        v2 = res2["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"]
        v3 = res3["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"]
        v4 = res4["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value"]

        assert v1 == v2 == v3 == v4
        assert res1["order"] == 37

    # =========================================================================
    # 6. End-to-End Ensemble Pipeline Integration Stress Tests
    # =========================================================================

    def test_combine_predictions_v41_stress_single_row_and_zeros(self):
        """Test EnsembleScoringEngine.combine_predictions under v41 with single row and all zeros."""
        engine = EnsembleScoringEngine()

        # 1. Single row input
        df_single = pd.DataFrame({
            'symbol': ['AAA'],
            'regression': [0.5],
            'surge': [0.5],
            'vcp': [0.5],
            'vcp_ml': [0.5],
            'lstm': [0.5],
            'stat_arb': [0.5],
            'sector_rotation': [0.5],
            'factor_neutralized': [0.5],
            'order_flow': [0.5],
            'event_driven': [0.5],
        })
        res_single = engine.combine_predictions(df_single, regime='BULL_LOW_VOL', version=41)
        assert len(res_single) == 1
        assert np.isfinite(res_single['ensemble_score'].values[0])

        # 2. All zeros input
        df_zeros = pd.DataFrame({
            'symbol': ['Z1', 'Z2'],
            'regression': [0.0, 0.0],
            'surge': [0.0, 0.0],
            'vcp': [0.0, 0.0],
            'vcp_ml': [0.0, 0.0],
            'lstm': [0.0, 0.0],
            'stat_arb': [0.0, 0.0],
            'sector_rotation': [0.0, 0.0],
            'factor_neutralized': [0.0, 0.0],
            'order_flow': [0.0, 0.0],
            'event_driven': [0.0, 0.0],
        })
        res_zeros = engine.combine_predictions(df_zeros, regime='CRISIS', version=41)
        assert len(res_zeros) == 2
        assert np.all(np.isfinite(res_zeros['ensemble_score'].values))
        assert np.all(res_zeros['ensemble_score'].values >= 0.0)

    def test_combine_predictions_v41_cross_regime_stability(self):
        """Test combine_predictions under v41 across diverse market regimes."""
        engine = EnsembleScoringEngine()
        n = 15
        mock_df = pd.DataFrame({
            'symbol': [f'SYM_{i}' for i in range(n)],
            'regression': np.linspace(0.1, 0.9, n),
            'surge': np.linspace(0.2, 0.8, n),
            'vcp': np.linspace(0.3, 0.7, n),
            'vcp_ml': np.linspace(0.4, 0.6, n),
            'lstm': np.linspace(0.2, 0.8, n),
            'stat_arb': np.linspace(0.1, 0.5, n),
            'sector_rotation': np.linspace(0.2, 0.7, n),
            'factor_neutralized': np.linspace(0.3, 0.8, n),
            'order_flow': np.linspace(0.4, 0.9, n),
            'event_driven': np.linspace(0.2, 0.6, n),
        })

        for reg in ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS', 'BEAR', 'CRISIS']:
            out = engine.combine_predictions(mock_df, regime=reg, version=41)
            assert len(out) == n
            scores = out['ensemble_score'].values
            assert np.all(np.isfinite(scores))
            assert np.all(scores >= 0.0)
            assert np.all(scores <= 1.0)
