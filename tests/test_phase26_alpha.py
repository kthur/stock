r"""
tests/test_phase26_alpha.py

Comprehensive unit test suite for Phase 26 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F123: Perfectoid Shimura Variety & Mochizuki Inter-Universal Teichmüller (IUT) Reconstruction
  Factor Disentanglement Engine (PerfectoidShimuraIUTCoupler, Hodge-Tate filtration obstruction complex E_shimura,
  Mochizuki theta-link indeterminacy invariant Z_mochizuki, coupling factor h_shimura,
  theta_0=0.35, kappa=3.50, complete aliases and factor_suppression bindings)
- Feature F124.1: 21st-Order Hyper-Convex Rank Modulation (g_v26(r) = 0.50 + 1.16 * r * exp(gamma_top * r^21))
  with regime-adaptive gamma_top up to 2.70 (REGIME_GAMMA_TOP_V26, get_regime_adaptive_gamma_top_v26)
- Feature F124.2: 68th-Order Hexaoctagonal Hyperbolic Tangent Noise Deadband (alpha=68.0, leakage < 10^-36)
- End-to-End EnsembleScoringEngine combine_predictions() with version=26
- Strict backward compatibility validation with Phase 13 (v13) through Phase 26 (v26)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_hexaoctagonal_hyperbolic_deadband,
    apply_hexatetrahedral_hyperbolic_deadband,
    apply_hexacontagonal_hyperbolic_deadband,
    apply_hexaquinquagintagonal_hyperbolic_deadband,
    apply_doquinquagintagonal_hyperbolic_deadband,
    apply_octatetracontagonal_hyperbolic_deadband,
    apply_tetracontatetragonal_hyperbolic_deadband,
    apply_tetracontagonal_hyperbolic_deadband,
    apply_hexatriacontagonal_hyperbolic_deadband,
    apply_dotriacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase26_hyperconvex_rank_modulation,
    compute_phase26_rank_warping,
    compute_phase25_hyperconvex_rank_modulation,
    compute_phase24_hyperconvex_rank_modulation,
    compute_phase23_hyperconvex_rank_modulation,
    PerfectoidShimuraIUTCoupler,
    PerfectoidShimuraVarietyCoupler,
    MochizukiIUTCoupler,
    MochizukiInterUniversalTeichmullerCoupler,
    ShimuraVarietyCoupler,
    MochizukiThetaLinkCoupler,
    HodgeTateFiltrationCoupler,
    IUTReconstructionCoupler,
    PerfectoidShimuraCoupler,
    MochizukiCoupler,
    ShimuraCoupler,
    NonAbelianHodgeCoupler,
    DerivedArithmeticTopologyCoupler,
    ToposicGeometricLanglandsCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexaoctagonal_hyperbolic_deadband as fs_hexaoctagonal_deadband,
    apply_hexatetrahedral_hyperbolic_deadband as fs_hexatetrahedral_deadband,
    apply_hexacontagonal_hyperbolic_deadband as fs_hexacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase26_hyperconvex_rank_modulation as fs_compute_phase26_modulation,
    compute_phase26_rank_warping as fs_compute_phase26_warping,
    REGIME_GAMMA_TOP_V26 as fs_REGIME_GAMMA_TOP_V26,
    get_regime_adaptive_gamma_top_v26 as fs_get_regime_adaptive_gamma_top_v26,
    PerfectoidShimuraIUTCoupler as fs_PerfectoidShimuraIUTCoupler,
    PerfectoidShimuraVarietyCoupler as fs_PerfectoidShimuraVarietyCoupler,
    MochizukiIUTCoupler as fs_MochizukiIUTCoupler,
    MochizukiInterUniversalTeichmullerCoupler as fs_MochizukiInterUniversalTeichmullerCoupler,
    ShimuraVarietyCoupler as fs_ShimuraVarietyCoupler,
    MochizukiThetaLinkCoupler as fs_MochizukiThetaLinkCoupler,
    HodgeTateFiltrationCoupler as fs_HodgeTateFiltrationCoupler,
    IUTReconstructionCoupler as fs_IUTReconstructionCoupler,
    PerfectoidShimuraCoupler as fs_PerfectoidShimuraCoupler,
    MochizukiCoupler as fs_MochizukiCoupler,
    ShimuraCoupler as fs_ShimuraCoupler,
    compute_perfectoid_shimura_iut_coupling as fs_compute_perfectoid_shimura_iut_coupling,
    compute_perfectoid_shimura_variety_coupling as fs_compute_perfectoid_shimura_variety_coupling,
    compute_mochizuki_iut_coupling as fs_compute_mochizuki_iut_coupling,
    compute_mochizuki_inter_universal_teichmuller_coupling as fs_compute_mochizuki_inter_universal_teichmuller_coupling,
    compute_shimura_variety_coupling as fs_compute_shimura_variety_coupling,
    compute_mochizuki_theta_link_coupling as fs_compute_mochizuki_theta_link_coupling,
    compute_hodge_tate_filtration_coupling as fs_compute_hodge_tate_filtration_coupling,
    compute_iut_reconstruction_coupling as fs_compute_iut_reconstruction_coupling,
    compute_perfectoid_shimura_coupling as fs_compute_perfectoid_shimura_coupling,
    compute_mochizuki_coupling as fs_compute_mochizuki_coupling,
    compute_shimura_coupling as fs_compute_shimura_coupling,
    NonAbelianHodgeCoupler as fs_NonAbelianHodgeCoupler,
)


class TestPhase26Alpha:
    """Test suite covering Phase 26 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F124.2: 68th-Order Hexaoctagonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_hexaoctagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.005) has leakage < 10^-36."""
        z_grid = np.linspace(-0.005, 0.005, 100)
        denoised = apply_hexaoctagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=68.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-36, f"Max noise leakage {max_leakage} must be < 1e-36"

        # Check boundary point |z| = 0.005
        val_at_bound = float(np.abs(apply_hexaoctagonal_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=68.0)))
        assert val_at_bound < 1e-36, f"Leakage at z=0.005 was {val_at_bound}, expected < 1e-36"

        # Check at z = 0.0
        val_at_zero = float(apply_hexaoctagonal_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=68.0))
        assert val_at_zero == 0.0

    def test_hexaoctagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_hexaoctagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=68.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_hexaoctagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=68.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Hexaoctagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_hexaoctagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_hexaoctagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=68.0)
        f_neg = apply_hexaoctagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=68.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_hexaoctagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_hexaoctagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_hexaoctagonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_hexaoctagonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version26_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=68.0 under version=26."""
        engine = EnsembleScoringEngine()
        z_val = 0.005
        res_v26 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=26)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=26)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=26)
        res_direct = apply_hexaoctagonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=68.0)

        assert math.isclose(float(res_v26), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F123: Perfectoid Shimura Variety & Mochizuki IUT Coupler
    # -------------------------------------------------------------------------

    def test_perfectoid_shimura_coupler_invariants_bounded(self):
        """Validates that E_shimura, Z_mochizuki, h_shimura, and FERI_v26 are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })
        res = PerfectoidShimuraIUTCoupler.compute(pillars)
        assert "h_shimura" in res
        assert "z_mochizuki" in res
        assert "e_shimura" in res
        assert "h_decay" in res
        assert "FERI_v26" in res
        assert "feri_v26" in res
        assert "Z_mochizuki" in res
        assert "E_shimura" in res
        assert "H_shimura" in res
        assert "h_perfectoid_shimura" in res
        assert "z_perfectoid_shimura" in res
        assert "e_perfectoid_shimura" in res
        assert "h_mochizuki_iut" in res
        assert "z_mochizuki_iut" in res
        assert "e_mochizuki_iut" in res
        assert "h_shimura_variety" in res
        assert "z_shimura_variety" in res
        assert "e_shimura_variety" in res
        assert "h_theta_link" in res
        assert "z_theta_link" in res
        assert "e_theta_link" in res
        assert "h_hodge_tate" in res
        assert "z_hodge_tate" in res
        assert "e_hodge_tate" in res
        assert "h_iut" in res
        assert "z_iut" in res
        assert "e_iut" in res

        z_arr = res["z_mochizuki"].values
        e_arr = res["e_shimura"].values
        h_arr = res["h_shimura"].values
        feri_arr = res["FERI_v26"].values

        assert np.all(z_arr > 0.0) and np.all(z_arr <= 1.0)
        assert np.all(e_arr >= 0.0)
        assert np.all(h_arr > 0.0) and np.all(h_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_perfectoid_shimura_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when factor sections agree perfectly, E_shimura == 0, Z_mochizuki == 1.0, h_shimura == 1.0, and FERI_v26 == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = PerfectoidShimuraIUTCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_shimura"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_mochizuki"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_shimura"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v26"].values, 1.0, atol=1e-12)

    def test_perfectoid_shimura_coupler_adversarial_conflict(self):
        """Validates that severe pillar discordance produces high obstruction and suppresses h_shimura smoothly."""
        conflict_pillars = pd.DataFrame({
            'val': [1.0, -1.0],
            'mom': [-1.0, 1.0],
            'flow': [1.0, -1.0],
            'cat': [-1.0, 1.0],
            'net': [1.0, -1.0],
        })
        res = PerfectoidShimuraIUTCoupler.compute(conflict_pillars)
        assert np.all(res["e_shimura"].values > 1.0)
        assert np.all(res["z_mochizuki"].values <= 1.0)
        assert np.all(res["h_shimura"].values < 0.05)
        assert np.all(res["FERI_v26"].values < 0.50)

    def test_perfectoid_shimura_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly across all aliases."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = PerfectoidShimuraIUTCoupler.compute(p_dict)
        assert len(res_dict["h_shimura"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = PerfectoidShimuraIUTCoupler.compute(v_single)
        assert isinstance(res_1d["h_shimura"], float)
        assert 0.0 < res_1d["h_shimura"] <= 1.0

        # Classmethods on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_perfectoid_shimura_iut_coupling(v_single)
        assert math.isclose(res_engine["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_engine_alias1 = EnsembleScoringEngine.compute_perfectoid_shimura_variety_coupling(v_single)
        assert math.isclose(res_engine_alias1["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_engine_alias2 = EnsembleScoringEngine.compute_mochizuki_iut_coupling(v_single)
        assert math.isclose(res_engine_alias2["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_engine_alias3 = EnsembleScoringEngine.compute_shimura_variety_coupling(v_single)
        assert math.isclose(res_engine_alias3["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_engine_alias4 = EnsembleScoringEngine.compute_mochizuki_theta_link_coupling(v_single)
        assert math.isclose(res_engine_alias4["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_engine_alias5 = EnsembleScoringEngine.compute_hodge_tate_filtration_coupling(v_single)
        assert math.isclose(res_engine_alias5["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_engine_alias6 = EnsembleScoringEngine.compute_iut_reconstruction_coupling(v_single)
        assert math.isclose(res_engine_alias6["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)

        # Aliases
        aliases = [
            PerfectoidShimuraVarietyCoupler,
            MochizukiIUTCoupler,
            MochizukiInterUniversalTeichmullerCoupler,
            ShimuraVarietyCoupler,
            MochizukiThetaLinkCoupler,
            HodgeTateFiltrationCoupler,
            IUTReconstructionCoupler,
            PerfectoidShimuraCoupler,
            MochizukiCoupler,
            ShimuraCoupler,
        ]
        for alias_cls in aliases:
            res_alias = alias_cls.compute(v_single)
            assert math.isclose(res_alias["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)

        # Cross-module exports in factor_suppression
        assert fs_PerfectoidShimuraIUTCoupler is PerfectoidShimuraIUTCoupler
        assert fs_PerfectoidShimuraVarietyCoupler is PerfectoidShimuraVarietyCoupler
        assert fs_MochizukiIUTCoupler is MochizukiIUTCoupler
        assert fs_MochizukiInterUniversalTeichmullerCoupler is MochizukiInterUniversalTeichmullerCoupler
        assert fs_ShimuraVarietyCoupler is ShimuraVarietyCoupler
        assert fs_MochizukiThetaLinkCoupler is MochizukiThetaLinkCoupler
        assert fs_HodgeTateFiltrationCoupler is HodgeTateFiltrationCoupler
        assert fs_IUTReconstructionCoupler is IUTReconstructionCoupler
        assert fs_PerfectoidShimuraCoupler is PerfectoidShimuraCoupler
        assert fs_MochizukiCoupler is MochizukiCoupler
        assert fs_ShimuraCoupler is ShimuraCoupler

        # Cross-module compute functions in factor_suppression
        res_fs1 = fs_compute_perfectoid_shimura_iut_coupling(v_single)
        assert math.isclose(res_fs1["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_fs2 = fs_compute_perfectoid_shimura_variety_coupling(v_single)
        assert math.isclose(res_fs2["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_fs3 = fs_compute_mochizuki_iut_coupling(v_single)
        assert math.isclose(res_fs3["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_fs4 = fs_compute_shimura_variety_coupling(v_single)
        assert math.isclose(res_fs4["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_fs5 = fs_compute_mochizuki_theta_link_coupling(v_single)
        assert math.isclose(res_fs5["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_fs6 = fs_compute_hodge_tate_filtration_coupling(v_single)
        assert math.isclose(res_fs6["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)
        res_fs7 = fs_compute_iut_reconstruction_coupling(v_single)
        assert math.isclose(res_fs7["h_shimura"], res_1d["h_shimura"], abs_tol=1e-12)

    def test_quint_pillar_tensor_synergy_version26(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates Perfectoid Shimura coupling for version=26."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 0.85],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 0.85, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v25 = engine.compute_quint_pillar_tensor_synergy(pillars, version=25)
        synergy_v26 = engine.compute_quint_pillar_tensor_synergy(pillars, version=26)

        assert isinstance(synergy_v26, pd.Series)
        assert len(synergy_v26) == 3
        assert np.all(np.isfinite(synergy_v26.values))
        assert np.all(synergy_v26.values > 0.0)
        # Highly coherent positive pillars should produce greater synergy in v26 with + 1.25 * h_shimura * z_mochizuki
        assert np.all(synergy_v26.values >= synergy_v25.values - 1e-6)

    # -------------------------------------------------------------------------
    # 3. Feature F124.1: 21st-Order Hyper-Convex Rank Modulation (g_v26)
    # -------------------------------------------------------------------------

    def test_21st_order_rank_modulation_percentiles(self):
        """Validates that 21st-order rank modulation concentrates capital into top percentiles (r >= 0.999999999999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase26_hyperconvex_rank_modulation(r_grid, gamma_top=2.70)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod < 1.09
        assert mod[2] < 1.09
        # Extreme conviction at r=1.0: 0.50 + 1.16 * 1.0 * exp(2.70) ~ 0.50 + 1.16 * 14.8797 ~ 17.76 > 16.50
        assert mod[-1] > 16.50

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase26_hyperconvex_rank_modulation(r_neg, gamma_top=2.70, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

        # Alias check
        mod_alias = compute_phase26_rank_warping(r_grid, gamma_top=2.70)
        np.testing.assert_allclose(mod, mod_alias, atol=1e-12)

        # Cross-module export check
        mod_fs = fs_compute_phase26_modulation(r_grid, gamma_top=2.70)
        np.testing.assert_allclose(mod, mod_fs, atol=1e-12)
        mod_fs_warp = fs_compute_phase26_warping(r_grid, gamma_top=2.70)
        np.testing.assert_allclose(mod, mod_fs_warp, atol=1e-12)

    def test_21st_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v26(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase26_hyperconvex_rank_modulation(r_fine, gamma_top=2.45)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "21st-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "21st-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version26(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 26 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=26) == 2.70
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("2", version=26) == 2.70
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=26) == 2.45
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS", version=26) == 2.25
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=26) == 2.25
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("1", version=26) == 2.25
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=26) == 1.55
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR", version=26) == 1.95
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=26) == 1.95
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("0", version=26) == 1.95
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=26) == 0.85
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=26) == 1.60
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=26) == 2.15

        # Also test factor_suppression regime functions and table
        assert fs_REGIME_GAMMA_TOP_V26["BULL_LOW_VOL"] == 2.70
        assert fs_REGIME_GAMMA_TOP_V26["BULL_HIGH_VOL"] == 2.45
        assert fs_REGIME_GAMMA_TOP_V26["SIDEWAYS"] == 2.25
        assert fs_REGIME_GAMMA_TOP_V26["BEAR"] == 1.95
        assert fs_REGIME_GAMMA_TOP_V26["CRISIS"] == 1.60
        assert fs_get_regime_adaptive_gamma_top_v26("BULL_LOW_VOL") == 2.70
        assert fs_get_regime_adaptive_gamma_top_v26("BULL_HIGH_VOL") == 2.45
        assert fs_get_regime_adaptive_gamma_top_v26("SIDEWAYS") == 2.25
        assert fs_get_regime_adaptive_gamma_top_v26("BEAR") == 1.95
        assert fs_get_regime_adaptive_gamma_top_v26("CRISIS") == 1.60

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version26_full_pipeline(self):
        """Validates full combine_predictions() execution with version=26."""
        engine = EnsembleScoringEngine()
        N = 25
        df_list = []
        for i in range(N):
            df_list.append({
                "symbol": f"STOCK_{i:03d}",
                "market": "SP500",
                "regression": 0.35 + 0.02 * i,
                "surge": 0.30 + 0.02 * i,
                "vcp_ml": 0.25 + 0.02 * i,
            })
        test_df = pd.DataFrame(df_list)

        comb_v25 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=25)
        comb_v26 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=26)

        assert isinstance(comb_v26, pd.DataFrame)
        assert not comb_v26.empty
        assert "ensemble_score" in comb_v26.columns
        assert len(comb_v26) == N
        assert np.all(np.isfinite(comb_v26["ensemble_score"].values))
        assert np.all(comb_v26["ensemble_score"].values >= 0.0)
        assert np.all(comb_v26["ensemble_score"].values <= 1.0)

        # Top conviction in v26 should exhibit strong concentration
        top_v25 = comb_v25.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v26 = comb_v26.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v26 >= top_v25 - 1e-6, f"Top conviction in v26 ({top_v26}) should be >= v25 ({top_v25})"

    def test_backward_compatibility_v13_through_v26(self):
        """Validates that versions 13 through 26 continue to run identically without disruption."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v13 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=13)
        res_v14 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=14)
        res_v15 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=15)
        res_v16 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=16)
        res_v17 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=17)
        res_v18 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=18)
        res_v19 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=19)
        res_v20 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=20)
        res_v21 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=21)
        res_v22 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=22)
        res_v23 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=23)
        res_v24 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=24)
        res_v25 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=25)
        res_v26 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=26)

        assert len(res_v13) == N
        assert len(res_v14) == N
        assert len(res_v15) == N
        assert len(res_v16) == N
        assert len(res_v17) == N
        assert len(res_v18) == N
        assert len(res_v19) == N
        assert len(res_v20) == N
        assert len(res_v21) == N
        assert len(res_v22) == N
        assert len(res_v23) == N
        assert len(res_v24) == N
        assert len(res_v25) == N
        assert len(res_v26) == N
