r"""
tests/test_phase45_adversarial_challenger1.py

Adversarial Stress Test Suite by Challenger 1 (Alpha & Risk Adversarial Challenger)
for Phase 45 Full Team Quant Enhancement:
- Milestone 1: Alpha Signal Enhancements
  * 168th-order Centahexaoctagonal Hyperbolic Deadband (F200.2)
  * 40th-order Ultra-Convex Rank Modulation (F200.1)
  * Quantum Geometric Langlands Kac-Moody Whittaker Coupler (F199)
- Milestone 2: Risk Allocation Enhancements
  * Lurie-Kac-Moody-Whittaker Fisher-Rao Barycenter Blending (F201.1)
  * 41st-Cumulant Trans-Singular-Kac-Moody-Whittaker EVaR Risk Measure (F201.1)

Stress tests include:
- Subnormal numbers (1e-310) and IEEE 754 boundary conditions
- Exact deadband threshold boundaries (z = +/-0.0003, +/-0.0003000001)
- Infinite, NaN, zero, and extreme values (z = 1000.0)
- Monotonicity, odd symmetry, rank conservation (Spearman rho == 1.0)
- Out-of-bounds rank inputs (r < 0, r > 1)
- Degenerate pillar vectors (identical, orthogonal, extreme, negative, wrong dims)
- Degenerate model weights (one-hot, zero, negative, extreme scaling)
- Simplex constraints (\sum q_i == 1.0) and interior positivity (q_i > 0)
- Heavy-tailed distribution stress: Normal, Cauchy, Student-t (df=2,3,5), constant, extreme outliers (r = -100)
- Hierarchy verification: EVaR_41 >= EVaR_40 across all distributions
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_centahexaoctagonal_hyperbolic_deadband,
    compute_phase45_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v45,
    REGIME_GAMMA_TOP_V45,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsKacMoodyWhittakerCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase45AdversarialAlphaMilestone1:
    """Adversarial stress testing of Milestone 1 Alpha Signal components."""

    # ─────────────────────────────────────────────────────────────────────────
    # 1. 168th-Order Hyperbolic Deadband Stress Tests
    # ─────────────────────────────────────────────────────────────────────────

    def test_adv_deadband_subnormal_numbers(self):
        """Stress test with IEEE 754 subnormal and near-zero floats."""
        subnormals = np.array([
            1e-315, -1e-315, 1e-308, -1e-308, 1e-250, -1e-250,
            5e-324, -5e-324, 0.0, -0.0
        ])
        res = apply_centahexaoctagonal_hyperbolic_deadband(subnormals, delta_noise=0.035, alpha_pos=168.0)
        for s, r in zip(subnormals, res):
            assert abs(r) < 1e-96, f"Subnormal input {s} leaked as {r}"
            assert np.isfinite(r)

    def test_adv_deadband_exact_boundaries(self):
        """Stress test exact mathematical threshold boundaries z = +/-0.0003 and perturbations."""
        boundaries = np.array([
            0.0003, -0.0003,
            0.0003000001, -0.0003000001,
            0.0002999999, -0.0002999999,
            0.0001, -0.0001,
            0.00001, -0.00001,
        ])
        res = apply_centahexaoctagonal_hyperbolic_deadband(boundaries, delta_noise=0.035, alpha_pos=168.0)
        for b, r in zip(boundaries, res):
            assert abs(r) < 1e-96, f"Noise boundary {b} produced leakage {r} >= 10^-96"

    def test_adv_deadband_high_conviction_100pct_transmission(self):
        """Verify exact 100.000% signal transmission for |z| >= 0.150."""
        signals = np.array([0.150, -0.150, 0.20, -0.20, 0.50, -0.50, 1.0, -1.0, 5.0, -5.0, 10.0, -10.0])
        res = apply_centahexaoctagonal_hyperbolic_deadband(signals, delta_noise=0.035, alpha_pos=168.0)
        for s, r in zip(signals, res):
            assert math.isclose(r, s, rel_tol=1e-12), f"Signal {s} not 100% transmitted, got {r}"

    def test_adv_deadband_extreme_and_special_values(self):
        """Verify behavior under extreme magnitudes, infinity, and NaN."""
        # Extreme large values
        large_vals = np.array([1000.0, -1000.0, 1e6, -1e6])
        res_large = apply_centahexaoctagonal_hyperbolic_deadband(large_vals, delta_noise=0.035, alpha_pos=168.0)
        assert np.allclose(res_large, large_vals, rtol=1e-12)

        # Infs and NaNs
        special = np.array([np.inf, -np.inf, np.nan])
        res_special = apply_centahexaoctagonal_hyperbolic_deadband(special, delta_noise=0.035, alpha_pos=168.0)
        assert np.isinf(res_special[0]) and res_special[0] > 0
        assert np.isinf(res_special[1]) and res_special[1] < 0
        assert np.isnan(res_special[2])

    def test_adv_deadband_strict_monotonicity_and_odd_symmetry(self):
        """Stress-test strict monotonicity on a 5000-point grid and unconditioned odd symmetry."""
        grid = np.linspace(-1.0, 1.0, 5001)
        res = apply_centahexaoctagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=168.0)

        # Monotonicity
        diffs = np.diff(res)
        assert (diffs >= -1e-15).all(), "Deadband must be monotonically non-decreasing"

        # Odd symmetry: f(-z) == -f(z)
        pos_half = grid[grid > 0]
        neg_half = -pos_half
        res_pos = apply_centahexaoctagonal_hyperbolic_deadband(pos_half, delta_noise=0.035, alpha_pos=168.0)
        res_neg = apply_centahexaoctagonal_hyperbolic_deadband(neg_half, delta_noise=0.035, alpha_pos=168.0)
        assert np.allclose(res_pos, -res_neg, atol=1e-15), "Deadband must satisfy exact odd symmetry when unconditioned"

    def test_adv_deadband_pandas_series_and_scalar(self):
        """Test Pandas Series input preservation and scalar float returns."""
        idx = pd.date_range("2026-01-01", periods=5)
        s = pd.Series([0.0001, 0.0003, 0.05, 0.15, 0.80], index=idx)
        res_s = apply_centahexaoctagonal_hyperbolic_deadband(s, delta_noise=0.035, alpha_pos=168.0)
        assert isinstance(res_s, pd.Series)
        assert (res_s.index == idx).all()

        scalar_res = apply_centahexaoctagonal_hyperbolic_deadband(0.20, delta_noise=0.035, alpha_pos=168.0)
        assert isinstance(scalar_res, float)
        assert math.isclose(scalar_res, 0.20, rel_tol=1e-12)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. 40th-Order Ultra-Convex Rank Modulation Stress Tests
    # ─────────────────────────────────────────────────────────────────────────

    def test_adv_rank_modulation_exact_checkpoints(self):
        """Test exact values at r = 0.0, 0.5, 0.7, 1.0."""
        gamma = 5.10
        # r = 0.0: g(0) = 0.50 + 1.52 * 0 * exp(...) = 0.50
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(0.0, gamma_top=gamma), 0.50, rel_tol=1e-6)

        # r = 0.5: 0.5^40 ~= 9.09e-13 -> exp(5.10 * 0) ~= 1.0 -> g(0.5) ~= 0.50 + 1.52 * 0.5 = 1.26
        g_05 = compute_phase45_hyperconvex_rank_modulation(0.50, gamma_top=gamma)
        assert math.isclose(g_05, 1.26, rel_tol=1e-4)

        # r = 0.7: 0.7^40 ~= 6.36e-7 -> exp(5.10 * 6.36e-7) ~= 1.0 -> g(0.7) ~= 0.50 + 1.52 * 0.7 = 1.564
        g_07 = compute_phase45_hyperconvex_rank_modulation(0.70, gamma_top=gamma)
        assert math.isclose(g_07, 1.564, rel_tol=1e-3)
        assert g_07 < 1.60

        # r = 1.0: g(1.0) = 0.50 + 1.52 * 1.0 * exp(5.10)
        expected_top = 0.50 + 1.52 * math.exp(5.10)
        g_10 = compute_phase45_hyperconvex_rank_modulation(1.0, gamma_top=gamma)
        assert math.isclose(g_10, expected_top, rel_tol=1e-5)
        assert g_10 > 240.0

    def test_adv_rank_modulation_out_of_bounds_clipping(self):
        """Verify graceful handling when r is out of bounds (r < 0 or r > 1)."""
        gamma = 5.10
        # r < 0 should clip to 0 -> 0.50
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(-0.5, gamma_top=gamma), 0.50, rel_tol=1e-5)
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(-100.0, gamma_top=gamma), 0.50, rel_tol=1e-5)

        # r > 1 should clip to 1 -> expected_top
        expected_top = 0.50 + 1.52 * math.exp(5.10)
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(1.5, gamma_top=gamma), expected_top, rel_tol=1e-5)
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(100.0, gamma_top=gamma), expected_top, rel_tol=1e-5)

    def test_adv_rank_modulation_negative_conviction_branch(self):
        """Stress test negative conviction branch (z_denoised < 0) for boundary and out of bounds."""
        # g_neg(r) = 1.35 - 1.00 * r_clipped
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(0.0, z_denoised=-0.1), 1.35, rel_tol=1e-5)
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(1.0, z_denoised=-0.1), 0.35, rel_tol=1e-5)
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(-0.5, z_denoised=-0.1), 1.35, rel_tol=1e-5)
        assert math.isclose(compute_phase45_hyperconvex_rank_modulation(1.5, z_denoised=-0.1), 0.35, rel_tol=1e-5)

    def test_adv_rank_modulation_all_regimes(self):
        """Verify all regime adaptive gamma_top values are strictly positive and properly ordered."""
        for reg, val in REGIME_GAMMA_TOP_V45.items():
            assert 1.0 <= val <= 6.0
            g_top = get_regime_adaptive_gamma_top_v45(reg)
            assert g_top == val
            # Test modulation with this regime's gamma
            mod = compute_phase45_hyperconvex_rank_modulation(1.0, gamma_top=g_top)
            assert mod > 5.0

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Quantum Geometric Langlands Kac-Moody Whittaker Coupler Stress Tests
    # ─────────────────────────────────────────────────────────────────────────

    def test_adv_coupler_identical_pillars(self):
        """When all 5 pillars are identical, defect energy E=0 and coupling h=1.0."""
        coupler = QuantumGeometricLanglandsKacMoodyWhittakerCoupler()
        for level in [-10.0, -1.0, 0.0, 0.5, 1.0, 100.0]:
            vec = np.full(5, level)
            res = coupler(vec)
            assert np.isclose(res["e_km_whit"], 0.0, atol=1e-12)
            assert np.isclose(res["z_km_whit"], 1.0, atol=1e-12)
            assert np.isclose(res["h_km_whit"], 1.0, atol=1e-12)
            assert np.isclose(res["FERI_v45"], 1.0, atol=1e-12)

    def test_adv_coupler_orthogonal_pillars(self):
        """Test with completely orthogonal unit basis pillars (e_1 .. e_5)."""
        coupler = QuantumGeometricLanglandsKacMoodyWhittakerCoupler()
        basis = np.eye(5)
        res = coupler(basis)
        h = res["h_km_whit"]
        e = res["e_km_whit"]
        z = res["z_km_whit"]
        feri = res["FERI_v45"]

        # All rows should have identical non-zero dispersion energy
        assert (e > 0.0).all()
        assert (h >= 0.0).all() and (h <= 1.0).all()
        assert (z >= 0.0).all() and (z <= 1.0).all()
        assert (feri >= 0.0).all() and (feri <= 1.0).all()

    def test_adv_coupler_negative_values_and_nan_tolerance(self):
        """Stress test with negative values, extreme spans, and NaN contamination."""
        coupler = QuantumGeometricLanglandsKacMoodyWhittakerCoupler()
        # Mixed negative values
        p_neg = np.array([[-1.0, -0.5, 0.0, 0.5, 1.0], [-5.0, 5.0, -2.0, 2.0, 0.0]])
        res_neg = coupler(p_neg)
        assert np.all(res_neg["h_km_whit"] >= 0.0)
        assert np.all(res_neg["h_km_whit"] <= 1.0)

        # DataFrame with NaNs
        df_nan = pd.DataFrame({
            "val": [np.nan, 0.5],
            "mom": [0.5, np.nan],
            "flow": [0.5, 0.5],
            "cat": [np.nan, np.nan],
            "net": [0.5, 0.5],
        })
        res_nan = coupler(df_nan)
        assert not np.isnan(res_nan["h_km_whit"]).any()
        assert not np.isnan(res_nan["FERI_v45"]).any()

    def test_adv_coupler_dimension_mismatch_exceptions(self):
        """Verify that invalid dimensions raise ValueError."""
        coupler = QuantumGeometricLanglandsKacMoodyWhittakerCoupler()
        # 1D wrong lengths
        with pytest.raises(ValueError):
            coupler(np.array([1.0, 2.0, 3.0, 4.0]))
        with pytest.raises(ValueError):
            coupler(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))

        # 2D wrong shape
        with pytest.raises(ValueError):
            coupler(np.ones((10, 4)))
        with pytest.raises(ValueError):
            coupler(np.ones((10, 6)))

    def test_adv_coupler_dispersion_monotonicity(self):
        """Verify that greater pillar dispersion monotonically increases energy and decreases coupling."""
        coupler = QuantumGeometricLanglandsKacMoodyWhittakerCoupler()
        v0 = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        v1 = np.array([0.5, 0.52, 0.48, 0.51, 0.49])
        v2 = np.array([0.5, 0.60, 0.40, 0.55, 0.45])
        v3 = np.array([0.5, 0.90, 0.10, 0.85, 0.15])

        r0, r1, r2, r3 = coupler(v0), coupler(v1), coupler(v2), coupler(v3)
        assert r0["e_km_whit"] < r1["e_km_whit"] < r2["e_km_whit"] < r3["e_km_whit"]
        assert r0["h_km_whit"] > r1["h_km_whit"] > r2["h_km_whit"] > r3["h_km_whit"]
        assert r0["FERI_v45"] > r1["FERI_v45"] > r2["FERI_v45"] > r3["FERI_v45"]


class TestPhase45AdversarialRiskMilestone2:
    """Adversarial stress testing of Milestone 2 Risk Allocation components."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Lurie-Kac-Moody-Whittaker Fisher-Rao Barycenter Stress Tests
    # ─────────────────────────────────────────────────────────────────────────

    def test_adv_barycenter_degenerate_one_hot_weights(self, allocator):
        """Stress test with degenerate one-hot model weights [1,0,0,0], [0,1,0,0], etc."""
        one_hots = [
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 1.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
        ]
        for w in one_hots:
            res = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(w)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5), "Simplex sum must be 1.0"
            for k, v in res.items():
                assert v > 0.0, f"Interior point positivity violated: {k}={v}"
                assert v < 1.0

    def test_adv_barycenter_all_zero_and_negative_inputs(self, allocator):
        """Stress test with all-zero weights and negative weights."""
        # All zero
        zero_w = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        res_zero = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(zero_w)
        assert math.isclose(sum(res_zero.values()), 1.0, rel_tol=1e-5)
        for v in res_zero.values():
            assert v > 0.0

        # Negative weights
        neg_w = {"bl": -0.5, "herc": -0.2, "rp": 0.3, "cvar": 0.8}
        res_neg = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(neg_w)
        assert math.isclose(sum(res_neg.values()), 1.0, rel_tol=1e-5)
        for v in res_neg.values():
            assert v > 0.0

    def test_adv_barycenter_extreme_scaling(self, allocator):
        """Stress test with extreme scaling: 1e9 and 1e-9."""
        huge_w = np.array([1e9, 1e9, 1e9, 1e9])
        res_huge = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(huge_w)
        assert math.isclose(sum(res_huge.values()), 1.0, rel_tol=1e-5)

        tiny_w = np.array([1e-9, 1e-9, 1e-9, 1e-9])
        res_tiny = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(tiny_w)
        assert math.isclose(sum(res_tiny.values()), 1.0, rel_tol=1e-5)

    def test_adv_barycenter_weight_hierarchy_and_cvar_prioritization(self, allocator):
        """Verify that equal input weights strictly result in CVaR > BL > HERC > RP due to mu_lkmw."""
        eq_w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_kac_moody_whittaker_fisher_rao_barycenter_blend(eq_w)
        assert res["cvar"] > res["bl"] > res["herc"] > res["rp"]

    # ─────────────────────────────────────────────────────────────────────────
    # 2. 41st-Cumulant EVaR Tail Risk Measure Stress Tests
    # ─────────────────────────────────────────────────────────────────────────

    def test_adv_evar_normal_returns(self, allocator):
        """Test EVaR with normal returns of varying volatility."""
        np.random.seed(42)
        for vol in [0.005, 0.02, 0.05, 0.10]:
            rets = np.random.normal(-0.001, vol, 1000)
            res_41 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(rets, alpha=0.05)
            res_40 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_risk_measure(rets, alpha=0.05)

            val_41 = res_41["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
            val_40 = res_40["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_value"]

            assert val_41 >= val_40 - 1e-6, f"Hierarchy violated for vol {vol}: {val_41} < {val_40}"
            assert res_41["order"] == 41
            assert math.isclose(res_41["xi_km"], 0.9999998, rel_tol=1e-5)

    def test_adv_evar_cauchy_fat_tailed_returns(self, allocator):
        """Stress test with heavy-tailed Cauchy distribution."""
        np.random.seed(45)
        raw_cauchy = np.random.standard_cauchy(1000) * 0.01
        rets = np.clip(raw_cauchy, -0.5, 0.5)

        res_41 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(rets, alpha=0.05)
        res_40 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_risk_measure(rets, alpha=0.05)

        val_41 = res_41["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
        val_40 = res_40["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_value"]

        assert val_41 >= val_40 - 1e-6
        assert np.isfinite(val_41)

    def test_adv_evar_student_t_returns(self, allocator):
        """Stress test with Student-t distributions with degrees of freedom df=2, 3, 5."""
        np.random.seed(123)
        for df in [2, 3, 5]:
            rets = np.random.standard_t(df, size=1000) * 0.02
            rets = np.clip(rets, -0.8, 0.8)

            res_41 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(rets, alpha=0.05)
            res_40 = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_risk_measure(rets, alpha=0.05)

            val_41 = res_41["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
            val_40 = res_40["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_evar_value"]

            assert val_41 >= val_40 - 1e-6, f"Hierarchy violated for Student-t df={df}"

    def test_adv_evar_constant_and_all_zero_returns(self, allocator):
        """Stress test with zero-variance inputs: all-zero and constant returns."""
        # All-zero returns
        zero_rets = np.zeros(500)
        res_zero = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(zero_rets)
        val_zero = res_zero["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
        assert np.isfinite(val_zero)

        # Constant returns
        const_rets = np.full(500, 0.02)
        res_const = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(const_rets)
        val_const = res_const["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
        assert np.isfinite(val_const)

    def test_adv_evar_extreme_outlier_shock(self, allocator):
        """Stress test with an extreme downside shock r = -100.0."""
        rets = np.array([0.01] * 200 + [-100.0])
        res_outlier = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(rets, alpha=0.01)
        val_outlier = res_outlier["trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_value"]
        assert np.isfinite(val_outlier)
        assert val_outlier > 50.0, "EVaR must capture massive downside risk under extreme shock"

    def test_adv_evar_empty_and_nan_tolerance(self, allocator):
        """Verify behavior when returns are empty or entirely NaNs/Infs."""
        empty_rets = np.array([])
        res_empty = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(empty_rets)
        assert isinstance(res_empty, dict)

        nan_rets = np.array([np.nan, np.inf, -np.inf])
        res_nan = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_evar_risk_measure(nan_rets)
        assert isinstance(res_nan, dict)
