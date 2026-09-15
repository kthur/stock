import os
os.environ['BYPASS_TORCH'] = '1'
import math
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from trading_system.src.ai.factor_suppression import (
    apply_centapentacontaduogonal_hyperbolic_deadband,
    compute_phase43_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v43,
    REGIME_GAMMA_TOP_V43,
    apply_smooth_deadband_attenuation,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumLanglandsAffineWAlgebraCoupler,
    QuantumLanglandsAffineWAlgebraFactorCoupler,
    QuantumLanglandsWAlgebraCoupler,
    AffineWAlgebraChiralOperCoupler,
    AffineWAlgebraCoupler,
    QuantumLanglandsCoupler,
    WAlgebraChiralOperCoupler,
    WAlgebraCoupler,
    Phase43Coupler,
    QuantumLanglandsDualityCoupler,
    ChiralOperHomologyCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase43Challenger1Stress:
    """Challenger 1 Stress and Invariant Suite for Phase 43 Alpha & Risk components."""

    # 1. 152nd-Order Centapentacontaduo-gonal Hyperbolic Deadband Adversarial Tests
    def test_deadband_sub_microscopic_leakage_and_precision(self):
        micro_vals = np.array([1e-6, -1e-6, 1e-7, -1e-7, 1e-9, -1e-9, 1e-15, -1e-15, 1e-30, -1e-30, 1e-100, -1e-100, 1e-200, -1e-200, 0.0, -0.0])
        denoised_micro = apply_centapentacontaduogonal_hyperbolic_deadband(micro_vals, delta_noise=0.035, alpha_pos=152.0)
        for v, orig in zip(denoised_micro, micro_vals):
            assert abs(v) < 1e-84 or v == 0.0, f'Noise leakage {v} for input {orig} exceeds 1e-84 threshold'

        noise_vals = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035, 0.0004, -0.0004])
        denoised_noise = apply_centapentacontaduogonal_hyperbolic_deadband(noise_vals, delta_noise=0.035, alpha_pos=152.0)
        for v, orig in zip(denoised_noise, noise_vals):
            assert abs(v) < 1e-84, f'Noise leakage {v} for noise-band input {orig} exceeds 1e-84 threshold'

    def test_deadband_extreme_inputs(self):
        extreme_z = np.array([1000.0, -1000.0, 500.0, -500.0, 1e6, -1e6, 1e30, -1e30])
        denoised_extreme = apply_centapentacontaduogonal_hyperbolic_deadband(extreme_z, delta_noise=0.035, alpha_pos=152.0)
        np.testing.assert_allclose(denoised_extreme, extreme_z, rtol=1e-7)

        assert apply_centapentacontaduogonal_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=152.0) == 0.0
        z_submicro = 1e-150
        denoised_submicro = apply_centapentacontaduogonal_hyperbolic_deadband(z_submicro, delta_noise=0.035, alpha_pos=152.0)
        assert abs(denoised_submicro) < 1e-150 or denoised_submicro == 0.0

        z_nan_inf = np.array([np.nan, np.inf, -np.inf, 0.20])
        denoised_nan_inf = apply_centapentacontaduogonal_hyperbolic_deadband(z_nan_inf, delta_noise=0.035, alpha_pos=152.0)
        assert np.isnan(denoised_nan_inf[0])
        assert np.isposinf(denoised_nan_inf[1])
        assert np.isneginf(denoised_nan_inf[2])
        assert math.isclose(denoised_nan_inf[3], 0.20, rel_tol=1e-7)

    def test_deadband_signal_transmission_high_conviction(self):
        conviction_z = np.array([0.05, 0.10, 0.25, 0.50, 0.80, 1.0, 2.0, 5.0])
        delta_eff = 0.035
        denoised_conv = apply_centapentacontaduogonal_hyperbolic_deadband(conviction_z, delta_noise=delta_eff, alpha_pos=152.0)
        ratio = denoised_conv / conviction_z
        assert (ratio >= 0.999).all(), f'High-conviction attenuation too large: {ratio}'

    def test_deadband_odd_symmetry(self):
        z_grid = np.linspace(-1.0, 1.0, 501)
        denoised = apply_centapentacontaduogonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=152.0)
        sym_diff = denoised + denoised[::-1]
        np.testing.assert_allclose(sym_diff, 0.0, atol=1e-12)

    def test_deadband_strict_rank_monotonicity(self):
        z_grid = np.linspace(0.0, 2.0, 1000)
        denoised = apply_centapentacontaduogonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=152.0)
        diffs = np.diff(denoised)
        assert (diffs >= -1e-15).all(), f'Deadband violated monotonicity at negative diff: {diffs.min()}'

    def test_deadband_version_routing_consistency(self):
        z = np.array([0.0001, 0.0005, 0.05, 0.50])
        out_direct = apply_centapentacontaduogonal_hyperbolic_deadband(z, delta_noise=0.035, alpha_pos=152.0)
        out_routed = apply_smooth_deadband_attenuation(z, delta_noise=0.035, version=43)
        np.testing.assert_allclose(out_direct, out_routed, rtol=1e-12)

    # 2. 38th-Order Hyper-Convex Rank Modulation (g_v43) Adversarial Tests
    def test_rank_modulation_dense_grid_monotonicity(self):
        r_grid = np.linspace(0.0, 1.0, 2000)
        for regime, gamma in REGIME_GAMMA_TOP_V43.items():
            g_vals = compute_phase43_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)
            diffs = np.diff(g_vals)
            assert (diffs >= 0.0).all(), f'Strict monotonicity violated in regime {regime} with gamma={gamma}'

    def test_rank_modulation_convexity_explosion_at_unity(self):
        gamma = 4.70
        r_top1 = 0.9999999999999999
        r_top0 = 0.9999
        g1 = compute_phase43_hyperconvex_rank_modulation(r_top1, gamma_top=gamma)
        g0 = compute_phase43_hyperconvex_rank_modulation(r_top0, gamma_top=gamma)
        assert g1 > g0
        assert math.isclose(g1, 0.50 + 1.52 * 1.0 * math.exp(4.70), rel_tol=1e-5)

    def test_rank_modulation_all_regimes(self):
        for regime in ['BULL_LOW_VOL', 'BULL_HIGH_VOL', 'SIDEWAYS', 'BEAR', 'CRISIS', 'UNKNOWN']:
            gamma = get_regime_adaptive_gamma_top_v43(regime)
            assert 1.30 <= gamma <= 4.70
            g_val = compute_phase43_hyperconvex_rank_modulation(1.0, gamma_top=gamma)
            assert math.isfinite(g_val)
            assert g_val > 1.0

    def test_rank_modulation_negative_signal_branch(self):
        r_grid = np.linspace(0.0, 1.0, 1000)
        z_neg = np.full_like(r_grid, -0.05)
        g_neg = compute_phase43_hyperconvex_rank_modulation(r_grid, gamma_top=4.70, z_denoised=z_neg)
        assert math.isclose(g_neg[0], 1.35, abs_tol=1e-6)
        assert math.isclose(g_neg[-1], 0.35, abs_tol=1e-6)
        diffs = np.diff(g_neg)
        assert (diffs <= 0.0).all(), 'Negative signal branch must be monotonically non-increasing'

    def test_rank_modulation_boundary_and_type_stress(self):
        r_oob = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
        g_oob = compute_phase43_hyperconvex_rank_modulation(r_oob, gamma_top=4.70)
        assert math.isclose(g_oob[0], g_oob[1], abs_tol=1e-6)
        assert math.isclose(g_oob[-1], g_oob[-2], abs_tol=1e-6)

        s_in = pd.Series([0.1, 0.5, 0.9], index=['x', 'y', 'z'])
        s_out = compute_phase43_hyperconvex_rank_modulation(s_in, gamma_top=4.70)
        assert isinstance(s_out, pd.Series)
        assert list(s_out.index) == ['x', 'y', 'z']
        assert s_out['x'] < s_out['y'] < s_out['z']

    # 3. Coupler Tests
    def test_coupler_identical_pillar_scores(self):
        coupler = QuantumLanglandsAffineWAlgebraCoupler()
        for c in [0.0, 0.25, 0.50, 0.75, 1.0, 0.9999]:
            vec = np.array([c, c, c, c, c])
            res = coupler(vec)
            assert math.isclose(res['h_w_algebra'], 1.0, abs_tol=1e-7)
            assert math.isclose(res['z_quant_langlands'], 1.0, abs_tol=1e-7)
            assert math.isclose(res['e_w_algebra'], 0.0, abs_tol=1e-7)
            assert math.isclose(res['FERI_v43'], 1.0, abs_tol=1e-7)

    def test_coupler_high_dispersion_and_extremes(self):
        coupler = QuantumLanglandsAffineWAlgebraCoupler()
        df = pd.DataFrame({
            'val': [0.0, 1.0], 'mom': [1.0, 0.0], 'flow': [0.0, 1.0], 'cat': [1.0, 0.0], 'net': [0.0, 1.0]
        })
        res = coupler(df)
        assert (res['h_w_algebra'] >= 0.0).all()
        assert (res['h_w_algebra'] <= 1.0).all()

    def test_coupler_nan_and_inf_handling(self):
        coupler = QuantumLanglandsAffineWAlgebraCoupler()
        nan_matrix = np.array([
            [np.nan, 0.5, 0.5, 0.5, 0.5],
            [np.nan, np.nan, np.nan, np.nan, np.nan],
            [0.2, np.nan, 0.4, np.nan, 0.6],
        ])
        res = coupler(nan_matrix)
        assert np.all(np.isfinite(res['h_w_algebra']))
        assert np.all(np.isfinite(res['z_quant_langlands']))
        assert np.all(np.isfinite(res['e_w_algebra']))

    def test_coupler_all_aliases_and_class_bindings(self):
        aliases = [
            QuantumLanglandsAffineWAlgebraFactorCoupler,
            QuantumLanglandsWAlgebraCoupler,
            AffineWAlgebraChiralOperCoupler,
            AffineWAlgebraCoupler,
            QuantumLanglandsCoupler,
            WAlgebraChiralOperCoupler,
            WAlgebraCoupler,
            Phase43Coupler,
            QuantumLanglandsDualityCoupler,
            ChiralOperHomologyCoupler,
        ]
        for a in aliases:
            assert a is QuantumLanglandsAffineWAlgebraCoupler
            inst = a()
            res = inst(np.array([0.5, 0.5, 0.5, 0.5, 0.5]))
            assert math.isclose(res['h_w_algebra'], 1.0, abs_tol=1e-7)

    # 4. Lurie-W-Algebra Barycenter Tests
    def test_barycenter_degenerate_distributions(self):
        alloc = UnifiedPortfolioAllocator()
        weights = {"bl": 0.4, "herc": 0.2, "rp": 0.2, "cvar": 0.2}
        res = alloc.compute_lurie_w_algebra_fisher_rao_barycenter_blend(weights)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
        assert (np.array(list(res.values())) > 0).all()

    def test_barycenter_extreme_boundary_points(self):
        alloc = UnifiedPortfolioAllocator()
        weights = {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        res = alloc.compute_lurie_w_algebra_fisher_rao_barycenter_blend(weights)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
        assert (np.array(list(res.values())) > 0.0).all()

    def test_barycenter_metric_weights_strict_ordering(self):
        alloc = UnifiedPortfolioAllocator()
        weights = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = alloc.compute_lurie_w_algebra_fisher_rao_barycenter_blend(weights)
        assert res["cvar"] > res["bl"] > res["herc"] > res["rp"]

    # 5. 39th-Cumulant Trans-Singular-W-Algebra EVaR Tests
    def test_evar_heavy_tailed_distributions_monotonicity(self):
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(1337)
        returns = np.random.standard_t(df=3, size=1000) * 0.03 - 0.01

        res_v43 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure(returns, alpha=0.05)
        res_v42 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(returns, alpha=0.05)

        val_v43 = res_v43['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_value']
        val_v42 = res_v42['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value']

        assert val_v43 >= val_v42 - 1e-6

    def test_evar_nan_and_inf_handling(self):
        alloc = UnifiedPortfolioAllocator()
        dirty_returns = np.array([np.nan, 0.01, -0.05, np.inf, -0.02, -np.inf, 0.03])
        res = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_risk_measure(dirty_returns, alpha=0.05)
        val = res['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_evar_value']
        assert math.isfinite(val)

    # 6. Ensemble Pipeline Integration
    def test_ensemble_pipeline_version_43_stress(self):
        engine = EnsembleScoringEngine()
        n = 10
        mock_scores = {
            'symbol': [f'SYM_{i}' for i in range(n)],
            'regression': pd.Series(np.linspace(0.1, 0.9, n)),
            'surge': pd.Series(np.linspace(0.05, 0.8, n)),
            'vcp': pd.Series(np.linspace(0.1, 0.7, n)),
            'sector': pd.Series(np.linspace(0.3, 0.8, n)),
            'momentum': pd.Series(np.linspace(0.2, 0.9, n)),
            'order_flow': pd.Series(np.linspace(0.4, 0.9, n)),
            'event_driven': pd.Series(np.linspace(0.2, 0.6, n)),
        }
        df_scores = pd.DataFrame(mock_scores)
        comb_v43 = engine.combine_predictions(df_scores, regime='BULL_LOW_VOL', version=43)
        assert isinstance(comb_v43, pd.DataFrame)
        assert not comb_v43.empty
        assert 'ensemble_score' in comb_v43.columns
        assert len(comb_v43) == n
        assert np.all(np.isfinite(comb_v43['ensemble_score'].values))
