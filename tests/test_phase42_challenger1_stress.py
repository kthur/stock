import os
os.environ['BYPASS_TORCH'] = '1'
import math
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from trading_system.src.ai.factor_suppression import (
    apply_centatetracontatetragonal_hyperbolic_deadband,
    compute_phase42_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v42,
    REGIME_GAMMA_TOP_V42,
    apply_smooth_deadband_attenuation,
)
from trading_system.src.ai.ensemble_scorer import (
    BeilinsonDrinfeldChiralKacMoodyCoupler,
    BeilinsonDrinfeldChiralKacMoodyFactorCoupler,
    BeilinsonDrinfeldCoupler,
    ChiralKacMoodyCoupler,
    QuantumAffineCoupler,
    KacMoodyVertexAlgebraCoupler,
    BeilinsonDrinfeldChiralCoupler,
    Phase42Coupler,
    BeilinsonKacMoodyCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator

class TestPhase42Challenger1Stress:
    # 1. 144th-Order Centatetracontatetragonal Hyperbolic Deadband Adversarial Tests
    def test_deadband_sub_microscopic_leakage_and_precision(self):
        micro_vals = np.array([1e-6, -1e-6, 1e-7, -1e-7, 1e-9, -1e-9, 1e-15, -1e-15, 1e-30, -1e-30, 1e-100, -1e-100, 1e-200, -1e-200, 0.0, -0.0])
        denoised_micro = apply_centatetracontatetragonal_hyperbolic_deadband(micro_vals, delta_noise=0.035, alpha_pos=144.0)
        for v, orig in zip(denoised_micro, micro_vals):
            assert abs(v) < 1e-80 or v == 0.0, f'Noise leakage {v} for input {orig} exceeds 1e-80 threshold'

        noise_vals = np.array([0.0001, -0.0001, 0.0002, -0.0002, 0.0003, -0.0003, 0.00035, -0.00035, 0.0004, -0.0004])
        denoised_noise = apply_centatetracontatetragonal_hyperbolic_deadband(noise_vals, delta_noise=0.035, alpha_pos=144.0)
        for v, orig in zip(denoised_noise, noise_vals):
            assert abs(v) < 1e-80, f'Noise leakage {v} for noise-band input {orig} exceeds 1e-80 threshold'

    def test_deadband_extreme_inputs(self):
        extreme_z = np.array([1000.0, -1000.0, 500.0, -500.0, 1e6, -1e6, 1e30, -1e30])
        denoised_extreme = apply_centatetracontatetragonal_hyperbolic_deadband(extreme_z, delta_noise=0.035, alpha_pos=144.0)
        np.testing.assert_allclose(denoised_extreme, extreme_z, rtol=1e-7)

        assert apply_centatetracontatetragonal_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=144.0) == 0.0
        z_submicro = 1e-150
        denoised_submicro = apply_centatetracontatetragonal_hyperbolic_deadband(z_submicro, delta_noise=0.035, alpha_pos=144.0)
        assert abs(denoised_submicro) < 1e-150 or denoised_submicro == 0.0

        z_nan_inf = np.array([np.nan, np.inf, -np.inf, 0.20])
        denoised_nan_inf = apply_centatetracontatetragonal_hyperbolic_deadband(z_nan_inf, delta_noise=0.035, alpha_pos=144.0)
        assert np.isnan(denoised_nan_inf[0])
        assert np.isposinf(denoised_nan_inf[1])
        assert np.isneginf(denoised_nan_inf[2])
        assert math.isclose(denoised_nan_inf[3], 0.20, rel_tol=1e-7)

    def test_deadband_signal_transmission_high_conviction(self):
        sig_vals = np.array([0.15, -0.15, 0.20, -0.20, 0.50, -0.50, 1.0, -1.0, 2.0, -2.0, 5.0, -5.0, 10.0, -10.0])
        denoised = apply_centatetracontatetragonal_hyperbolic_deadband(sig_vals, delta_noise=0.035, alpha_pos=144.0)
        np.testing.assert_allclose(denoised, sig_vals, rtol=1e-9, atol=1e-12)

    def test_deadband_odd_symmetry(self):
        z_grid = np.linspace(0.0001, 0.5, 1000)
        pos_out = apply_centatetracontatetragonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=144.0)
        neg_out = apply_centatetracontatetragonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=144.0)
        np.testing.assert_allclose(pos_out, -neg_out, rtol=1e-9, atol=1e-15)

    def test_deadband_strict_rank_monotonicity(self):
        z_dense = np.linspace(-1.5, 1.5, 5000)
        denoised = apply_centatetracontatetragonal_hyperbolic_deadband(z_dense, delta_noise=0.035, alpha_pos=144.0)
        diffs = np.diff(denoised)
        assert (diffs >= -1e-15).all(), 'Deadband output violated non-decreasing monotonicity'
        corr, _ = stats.spearmanr(z_dense, denoised)
        assert math.isclose(corr, 1.0, abs_tol=1e-4), f'Spearman rank correlation {corr} < 1.0000'

    def test_deadband_version_routing_consistency(self):
        z_test = np.array([0.0004])
        out_v42 = apply_smooth_deadband_attenuation(z_test, version=42)
        out_v41 = apply_smooth_deadband_attenuation(z_test, version=41)
        out_v40 = apply_smooth_deadband_attenuation(z_test, version=40)
        assert abs(out_v42[0]) < 1e-80
        assert abs(out_v41[0]) < 1e-74
        assert abs(out_v40[0]) < 1e-68
        assert abs(out_v42[0]) < abs(out_v41[0])

    # =========================================================================
    # 2. 37th-Order Ultra-Convex Rank Modulation Adversarial Tests
    # =========================================================================

    def test_rank_modulation_dense_grid_monotonicity(self):
        r_grid = np.linspace(0.0, 1.0, 10000)
        for gamma in [1.0, 2.5, 3.8, 4.1, 4.3, 4.6]:
            g_vals = compute_phase42_hyperconvex_rank_modulation(r_grid, gamma_top=gamma)
            diffs = np.diff(g_vals)
            assert (diffs >= 0.0).all(), f'Rank modulation violated monotonicity for gamma={gamma}'

    def test_rank_modulation_convexity_explosion_at_unity(self):
        gamma_top = 4.60
        r_00 = compute_phase42_hyperconvex_rank_modulation(0.0, gamma_top=gamma_top)
        r_50 = compute_phase42_hyperconvex_rank_modulation(0.50, gamma_top=gamma_top)
        r_70 = compute_phase42_hyperconvex_rank_modulation(0.70, gamma_top=gamma_top)
        r_90 = compute_phase42_hyperconvex_rank_modulation(0.90, gamma_top=gamma_top)
        r_95 = compute_phase42_hyperconvex_rank_modulation(0.95, gamma_top=gamma_top)
        r_99 = compute_phase42_hyperconvex_rank_modulation(0.99, gamma_top=gamma_top)
        r_100 = compute_phase42_hyperconvex_rank_modulation(1.0, gamma_top=gamma_top)

        assert math.isclose(r_00, 0.50, abs_tol=1e-6)
        assert r_50 < 1.30, f'At r=0.50, rank modulation {r_50} is too aggressive'
        assert r_70 < 1.56, f'At r=0.70, rank modulation {r_70} should be modest (< 1.56)'
        assert r_90 < 2.0, f'At r=0.90, rank modulation {r_90} should remain modest (< 2.0)'
        assert r_95 > 3.0, f'At r=0.95, rank modulation {r_95} should start accelerating (> 3.0)'
        assert r_99 > 30.0, f'At r=0.99, rank modulation {r_99} should exhibit massive convexity (> 30.0)'
        expected_top = 0.50 + 1.50 * math.exp(gamma_top)
        assert math.isclose(r_100, expected_top, rel_tol=1e-5)
        assert r_100 > 140.0, f'At r=1.0, convexity explosion {r_100} should exceed 140.0'

        r_tail = np.linspace(0.80, 1.0, 1000)
        g_tail = compute_phase42_hyperconvex_rank_modulation(r_tail, gamma_top=gamma_top)
        d2 = np.diff(np.diff(g_tail))
        assert (d2 >= 0.0).all(), 'Second derivative of rank modulation must be non-negative (strictly convex)'

    def test_rank_modulation_all_regimes(self):
        expected_regimes = {
            'BULL_LOW_VOL': 4.60,
            'BULL_HIGH_VOL': 4.30,
            'SIDEWAYS': 4.10,
            'BEAR': 3.80,
            'CRISIS': 1.30,
            'UNKNOWN_REGIME': 4.60,
        }
        for regime, exp_gamma in expected_regimes.items():
            g = get_regime_adaptive_gamma_top_v42(regime)
            assert math.isclose(g, exp_gamma, abs_tol=1e-5)
            val_100 = compute_phase42_hyperconvex_rank_modulation(1.0, gamma_top=g)
            exp_top = 0.50 + 1.50 * math.exp(exp_gamma)
            assert math.isclose(val_100, exp_top, rel_tol=1e-5)

    def test_rank_modulation_negative_signal_branch(self):
        r_grid = np.linspace(0.0, 1.0, 1000)
        z_neg = np.full_like(r_grid, -0.05)
        g_neg = compute_phase42_hyperconvex_rank_modulation(r_grid, gamma_top=4.60, z_denoised=z_neg)
        assert math.isclose(g_neg[0], 1.35, abs_tol=1e-6)
        assert math.isclose(g_neg[-1], 0.35, abs_tol=1e-6)
        diffs = np.diff(g_neg)
        assert (diffs <= 0.0).all(), 'Negative signal branch must be monotonically non-increasing'

    def test_rank_modulation_boundary_and_type_stress(self):
        r_oob = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
        g_oob = compute_phase42_hyperconvex_rank_modulation(r_oob, gamma_top=4.60)
        assert math.isclose(g_oob[0], g_oob[1], abs_tol=1e-6)
        assert math.isclose(g_oob[-1], g_oob[-2], abs_tol=1e-6)

        s_in = pd.Series([0.1, 0.5, 0.9], index=['x', 'y', 'z'])
        s_out = compute_phase42_hyperconvex_rank_modulation(s_in, gamma_top=4.60)
        assert isinstance(s_out, pd.Series)
        assert list(s_out.index) == ['x', 'y', 'z']
        assert s_out['x'] < s_out['y'] < s_out['z']

    # =========================================================================
    # 3. Beilinson-Drinfeld Chiral and Quantum Affine Kac-Moody Coupler Robustness
    # =========================================================================

    def test_coupler_identical_pillar_scores(self):
        coupler = BeilinsonDrinfeldChiralKacMoodyCoupler()
        for c in [0.0, 0.25, 0.50, 0.75, 1.0, 0.9999]:
            vec = np.array([c, c, c, c, c])
            res = coupler(vec)
            assert math.isclose(res['e_chiral'], 0.0, abs_tol=1e-7)
            assert math.isclose(res['z_kac_moody'], 1.0, abs_tol=1e-7)
            assert math.isclose(res['h_chiral'], 1.0, abs_tol=1e-7)
            assert math.isclose(res['FERI_v42'], 1.0, abs_tol=1e-7)

    def test_coupler_high_dispersion_and_extremes(self):
        coupler = BeilinsonDrinfeldChiralKacMoodyCoupler()
        high_disp = np.array([[0.0, 1.0, 0.0, 1.0, 0.0], [0.01, 0.99, 0.02, 0.98, 0.01]])
        res = coupler(high_disp)
        for h, z, e, feri in zip(res['h_chiral'], res['z_kac_moody'], res['e_chiral'], res['FERI_v42']):
            assert e > 1.0, 'Obstruction energy must be substantial for polarized pillars'
            assert z < 0.5, 'Topological defect must suppress invariant Z_kac_moody'
            assert h < 0.05, 'High dispersion must strongly penalize coupling factor'
            assert feri < 0.5, 'Factor Entanglement Robustness Index must reflect high dispersion'

    def test_coupler_extreme_magnitude_inputs(self):
        coupler = BeilinsonDrinfeldChiralKacMoodyCoupler()
        extreme_vecs = np.array([
            [10.0, 20.0, 30.0, 40.0, 50.0],
            [-10.0, -20.0, -30.0, -40.0, -50.0],
            [100.0, 100.0, 100.0, 100.0, 100.0],
        ])
        res = coupler(extreme_vecs)
        assert np.all(np.isfinite(res['h_chiral']))
        assert np.all(np.isfinite(res['z_kac_moody']))
        assert np.all(np.isfinite(res['e_chiral']))
        assert np.all(res['h_chiral'] >= 0.0)
        assert np.all(res['h_chiral'] <= 1.0)
        assert math.isclose(res['h_chiral'][2], 1.0, abs_tol=1e-7)

    def test_coupler_nan_and_inf_handling(self):
        coupler = BeilinsonDrinfeldChiralKacMoodyCoupler()
        nan_matrix = np.array([
            [np.nan, 0.5, 0.5, 0.5, 0.5],
            [np.nan, np.nan, np.nan, np.nan, np.nan],
            [0.2, np.nan, 0.4, np.nan, 0.6],
        ])
        res = coupler(nan_matrix)
        assert np.all(np.isfinite(res['h_chiral']))
        assert np.all(np.isfinite(res['z_kac_moody']))
        assert np.all(np.isfinite(res['e_chiral']))
        assert math.isclose(res['h_chiral'][1], 1.0, abs_tol=1e-7)

    def test_coupler_all_aliases_and_class_bindings(self):
        aliases = [
            BeilinsonDrinfeldChiralKacMoodyFactorCoupler,
            BeilinsonDrinfeldCoupler,
            ChiralKacMoodyCoupler,
            QuantumAffineCoupler,
            KacMoodyVertexAlgebraCoupler,
            BeilinsonDrinfeldChiralCoupler,
            Phase42Coupler,
            BeilinsonKacMoodyCoupler,
        ]
        for a in aliases:
            assert a is BeilinsonDrinfeldChiralKacMoodyCoupler
            inst = a()
            res = inst(np.array([0.5, 0.5, 0.5, 0.5, 0.5]))
            assert math.isclose(res['h_chiral'], 1.0, abs_tol=1e-7)

    # =========================================================================
    # 4. Fisher-Rao Barycenter Robustness Adversarial Tests
    # =========================================================================

    def test_barycenter_degenerate_distributions(self):
        alloc = UnifiedPortfolioAllocator()
        corners = [
            {'bl': 1.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0},
            {'bl': 0.0, 'herc': 1.0, 'rp': 0.0, 'cvar': 0.0},
            {'bl': 0.0, 'herc': 0.0, 'rp': 1.0, 'cvar': 0.0},
            {'bl': 0.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 1.0},
        ]
        for c in corners:
            res = alloc.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(c)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5), 'Simplex sum != 1.0'
            for k, v in res.items():
                assert 0.0 < v < 1.0, f'Weight {k}={v} out of interior bounds (0, 1)'

        half_and_half = {'bl': 0.5, 'herc': 0.5, 'rp': 0.0, 'cvar': 0.0}
        res_hh = alloc.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(half_and_half)
        assert math.isclose(sum(res_hh.values()), 1.0, rel_tol=1e-5)
        assert res_hh['bl'] > res_hh['herc'], 'BL metric weight (3.20) > HERC (2.55)'

    def test_barycenter_extreme_boundary_points(self):
        alloc = UnifiedPortfolioAllocator()
        boundary_inputs = [
            {'bl': 0.9997, 'herc': 0.0001, 'rp': 0.0001, 'cvar': 0.0001},
            {'bl': 1e-12, 'herc': 1e-12, 'rp': 1e-12, 'cvar': 1.0},
            {'bl': 1e-8, 'herc': 1e-8, 'rp': 1e-8, 'cvar': 1.0},
            np.array([1e-15, 1e-15, 1e-15, 1.0]),
        ]
        for inp in boundary_inputs:
            res = alloc.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(inp)
            assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
            assert all(v > 0.0 for v in res.values())

    def test_barycenter_disparate_conflicting_inputs(self):
        alloc = UnifiedPortfolioAllocator()
        conflicting = [
            {'bl': 1.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0},
            {'bl': 0.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 1.0},
        ]
        res = alloc.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(conflicting)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
        assert res['cvar'] > res['bl']
        assert res['bl'] > res['herc']
        assert res['herc'] > res['rp']

    def test_barycenter_metric_weights_strict_ordering(self):
        alloc = UnifiedPortfolioAllocator()
        equal_w = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}
        res = alloc.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(equal_w)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-5)
        assert res['cvar'] > res['bl'] > res['herc'] > res['rp']

    def test_barycenter_all_15_aliases(self):
        alloc = UnifiedPortfolioAllocator()
        w = {'bl': 0.25, 'herc': 0.25, 'rp': 0.25, 'cvar': 0.25}
        ref = alloc.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend(w)
        aliases = [
            alloc.compute_lurie_beilinson_drinfeld_barycenter,
            alloc.compute_lurie_drinfeld_beilinson_barycenter,
            alloc.compute_beilinson_drinfeld_fisher_rao_barycenter,
            alloc.compute_beilinson_drinfeld_barycenter,
            alloc.compute_drinfeld_fisher_rao_barycenter,
            alloc.compute_drinfeld_barycenter,
            alloc.compute_phase42_fisher_rao_barycenter,
            alloc.compute_phase42_barycenter_blend,
            alloc.compute_beilinson_drinfeld_fisher_rao_barycenter_blend,
            alloc.compute_motivic_beilinson_drinfeld_barycenter_blend,
            alloc.compute_analytic_beilinson_drinfeld_barycenter_blend,
            alloc.compute_chiral_beilinson_drinfeld_barycenter_blend,
            alloc.compute_kac_moody_beilinson_drinfeld_barycenter_blend,
            alloc.compute_vertex_algebra_beilinson_drinfeld_barycenter_blend,
            alloc.compute_chiral_oper_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_lurie_beilinson_drinfeld_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_lurie_beilinson_drinfeld_barycenter,
            PortfolioAllocator.compute_lurie_drinfeld_beilinson_barycenter,
            PortfolioAllocator.compute_beilinson_drinfeld_fisher_rao_barycenter,
            PortfolioAllocator.compute_beilinson_drinfeld_barycenter,
            PortfolioAllocator.compute_drinfeld_fisher_rao_barycenter,
            PortfolioAllocator.compute_drinfeld_barycenter,
            PortfolioAllocator.compute_phase42_fisher_rao_barycenter,
            PortfolioAllocator.compute_phase42_barycenter_blend,
            PortfolioAllocator.compute_beilinson_drinfeld_fisher_rao_barycenter_blend,
            PortfolioAllocator.compute_motivic_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_analytic_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_chiral_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_kac_moody_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_vertex_algebra_beilinson_drinfeld_barycenter_blend,
            PortfolioAllocator.compute_chiral_oper_beilinson_drinfeld_barycenter_blend,
        ]
        for fn in aliases:
            out = fn(w)
            for k in ['bl', 'herc', 'rp', 'cvar']:
                assert math.isclose(out[k], ref[k], rel_tol=1e-5)

    # =========================================================================
    # 5. 38th-Cumulant EVaR Tail Risk Measure Adversarial Stress Tests
    # =========================================================================

    def test_evar_heavy_tailed_distributions_monotonicity(self):
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(1337)

        distributions = {
            'normal': np.random.normal(loc=-0.01, scale=0.04, size=1000),
            'laplace': np.random.laplace(loc=-0.01, scale=0.03, size=1000),
            'student_t_df3': np.random.standard_t(df=3, size=1000) * 0.03 - 0.01,
            'student_t_df4': np.random.standard_t(df=4, size=1000) * 0.03 - 0.01,
            'exponential': -np.random.exponential(scale=0.03, size=1000),
            'cauchy': np.clip(np.random.standard_cauchy(size=1000) * 0.02 - 0.01, -0.99, 0.99),
            'dirac_delta_zero': np.zeros(500),
            'dirac_delta_neg': np.full(500, -0.05),
            'mixture_flash_crash': np.concatenate([
                np.random.normal(0.001, 0.01, size=950),
                np.random.normal(-0.25, 0.08, size=50),
            ]),
        }

        for dist_name, returns in distributions.items():
            res_v42 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(returns, alpha=0.05)
            res_v41 = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_risk_measure(returns, alpha=0.05)

            val_v42 = res_v42['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value']
            val_v41 = res_v41['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_evar_value']

            assert val_v42 >= val_v41 - 1e-6, (
                f'Monotonicity violation on {dist_name}: EVaR_38 ({val_v42}) < EVaR_37 ({val_v41})'
            )
            assert res_v42['order'] == 38
            assert math.isclose(res_v42['xi_beilinson'], 0.999998, abs_tol=1e-5)

    def test_evar_alpha_sensitivity(self):
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        alphas = [0.10, 0.05, 0.01, 0.001]
        evars = []
        for a in alphas:
            res = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(returns, alpha=a)
            evars.append(res['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value'])

        for i in range(len(evars) - 1):
            assert evars[i + 1] >= evars[i] - 1e-4, f'EVaR at alpha={alphas[i+1]} ({evars[i+1]}) < alpha={alphas[i]} ({evars[i]})'

    def test_evar_nan_and_inf_handling(self):
        alloc = UnifiedPortfolioAllocator()
        dirty_returns = np.array([np.nan, 0.02, -0.05, np.inf, -np.inf, 0.01, -0.03, np.nan])
        res = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(dirty_returns)
        val = res['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value']
        assert np.isfinite(val)
        assert res['order'] == 38

    def test_evar_all_21_aliases(self):
        alloc = UnifiedPortfolioAllocator()
        np.random.seed(42)
        returns = np.random.normal(-0.01, 0.05, 500)
        ref = alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure(returns)
        ref_val = ref['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value']

        aliases = [
            alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            alloc.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_blend,
            alloc.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            alloc.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            alloc.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_phase42,
            alloc.compute_38th_cumulant_evar,
            alloc.compute_phase42_evar,
            alloc.compute_trans_beilinson_evar_risk_measure,
            alloc.compute_trans_fargues_beilinson_evar_risk_measure,
            alloc.compute_trans_deligne_fargues_beilinson_evar_risk_measure,
            alloc.compute_trans_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            alloc.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            alloc.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            alloc.compute_clausen_scholze_deligne_fargues_beilinson_evar,
            alloc.compute_deligne_fargues_beilinson_evar,
            alloc.compute_fargues_beilinson_evar,
            alloc.compute_beilinson_drinfeld_evar,
            alloc.compute_beilinson_evar,
            alloc.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar,
            alloc.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_blend,
            PortfolioAllocator.compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_phase42,
            PortfolioAllocator.compute_38th_cumulant_evar,
            PortfolioAllocator.compute_phase42_evar,
            PortfolioAllocator.compute_trans_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_trans_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_risk_measure,
            PortfolioAllocator.compute_clausen_scholze_deligne_fargues_beilinson_evar,
            PortfolioAllocator.compute_deligne_fargues_beilinson_evar,
            PortfolioAllocator.compute_fargues_beilinson_evar,
            PortfolioAllocator.compute_beilinson_drinfeld_evar,
            PortfolioAllocator.compute_beilinson_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar,
            PortfolioAllocator.compute_eternal_omni_cosmic_infinite_supreme_transcendent_beilinson_evar_risk_measure,
        ]
        for fn in aliases:
            res = fn(returns)
            val = res['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_fargues_beilinson_evar_value']
            assert math.isclose(val, ref_val, rel_tol=1e-5)

    # =========================================================================
    # 6. End-to-End Ensemble Pipeline Integration Adversarial Stress Tests
    # =========================================================================

    def test_ensemble_pipeline_version_42_stress(self):
        engine = EnsembleScoringEngine()
        n = 20

        df_conflicting = pd.DataFrame({
            'symbol': [f'SYM_{i}' for i in range(n)],
            'regression': pd.Series([1.0 if i % 2 == 0 else 0.0 for i in range(n)]),
            'surge': pd.Series([0.0 if i % 2 == 0 else 1.0 for i in range(n)]),
            'vcp': pd.Series(np.zeros(n)),
            'vcp_ml': pd.Series(np.ones(n)),
            'lstm': pd.Series(np.full(n, 0.5)),
            'stat_arb': pd.Series(np.linspace(0.0, 1.0, n)),
            'sector_rotation': pd.Series(np.linspace(1.0, 0.0, n)),
            'factor_neutralized': pd.Series(np.full(n, np.nan)),
            'order_flow': pd.Series(np.full(n, 0.5)),
            'event_driven': pd.Series(np.zeros(n)),
        })

        res_v42 = engine.combine_predictions(df_conflicting, regime='BULL_LOW_VOL', version=42)
        assert isinstance(res_v42, pd.DataFrame)
        assert not res_v42.empty
        assert 'ensemble_score' in res_v42.columns
        assert np.all(np.isfinite(res_v42['ensemble_score'].values))
        assert np.all(res_v42['ensemble_score'].values >= 0.0)
        assert np.all(res_v42['ensemble_score'].values <= 1.0)

        df_nan = pd.DataFrame({
            'symbol': [f'SYM_{i}' for i in range(5)],
            'regression': pd.Series(np.full(5, np.nan)),
            'surge': pd.Series(np.full(5, np.nan)),
        })
        res_nan = engine.combine_predictions(df_nan, regime='CRISIS', version=42)
        assert isinstance(res_nan, pd.DataFrame)
        assert not res_nan.empty
        assert np.all(np.isfinite(res_nan['ensemble_score'].values))
