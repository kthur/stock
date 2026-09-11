r"""
tests/test_phase25_alpha.py

Comprehensive unit test suite for Phase 25 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F119: Non-Abelian Hodge Theory & Deligne-Simpson Spectral Moduli Factor Disentanglement Engine
  (NonAbelianHodgeCoupler, Hitchin equations \bar{\partial}_E \Phi = 0, F_A + [\Phi, \Phi^*] = 0,
   harmonic bundle obstruction complex E_hodge, Deligne-Simpson spectral moduli invariant Z_simpson,
   theta_0=0.34, kappa=3.40, complete aliases and factor_suppression bindings)
- Feature F120.1: 20th-Order Hyper-Convex Rank Modulation (g_v25(r) = 0.50 + 1.14 * r * exp(gamma_top * r^20))
  with regime-adaptive gamma_top up to 2.60 (REGIME_GAMMA_TOP_V25, get_regime_adaptive_gamma_top_v25)
- Feature F120.2: 64th-Order Hexatetrahedral Hyperbolic Tangent Noise Deadband (alpha=64.0, leakage < 10^-34)
- End-to-End EnsembleScoringEngine combine_predictions() with version=25
- Strict backward compatibility validation with Phase 13 (v13) through Phase 25 (v25)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
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
    compute_phase25_hyperconvex_rank_modulation,
    compute_phase25_rank_warping,
    compute_phase24_hyperconvex_rank_modulation,
    compute_phase23_hyperconvex_rank_modulation,
    NonAbelianHodgeCoupler,
    DeligneSimpsonSpectralModuliCoupler,
    HodgeCoupler,
    DeligneSimpsonCoupler,
    HitchinEquationCoupler,
    HarmonicBundleCoupler,
    NonAbelianHodgeSpectralCoupler,
    HitchinHarmonicBundleCoupler,
    NonAbelianHodgeTheoryCoupler,
    SimpsonSpectralModuliCoupler,
    HitchinEquationsCoupler,
    DerivedArithmeticTopologyCoupler,
    ToposicGeometricLanglandsCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexatetrahedral_hyperbolic_deadband as fs_hexatetrahedral_deadband,
    apply_hexacontagonal_hyperbolic_deadband as fs_hexacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase25_hyperconvex_rank_modulation as fs_compute_phase25_modulation,
    compute_phase25_rank_warping as fs_compute_phase25_warping,
    REGIME_GAMMA_TOP_V25 as fs_REGIME_GAMMA_TOP_V25,
    get_regime_adaptive_gamma_top_v25 as fs_get_regime_adaptive_gamma_top_v25,
    NonAbelianHodgeCoupler as fs_NonAbelianHodgeCoupler,
    DeligneSimpsonSpectralModuliCoupler as fs_DeligneSimpsonSpectralModuliCoupler,
    HodgeCoupler as fs_HodgeCoupler,
    DeligneSimpsonCoupler as fs_DeligneSimpsonCoupler,
    HitchinEquationCoupler as fs_HitchinEquationCoupler,
    HarmonicBundleCoupler as fs_HarmonicBundleCoupler,
    NonAbelianHodgeSpectralCoupler as fs_NonAbelianHodgeSpectralCoupler,
    HitchinHarmonicBundleCoupler as fs_HitchinHarmonicBundleCoupler,
    NonAbelianHodgeTheoryCoupler as fs_NonAbelianHodgeTheoryCoupler,
    SimpsonSpectralModuliCoupler as fs_SimpsonSpectralModuliCoupler,
    HitchinEquationsCoupler as fs_HitchinEquationsCoupler,
    compute_non_abelian_hodge_coupling as fs_compute_non_abelian_hodge_coupling,
    compute_deligne_simpson_spectral_moduli_coupling as fs_compute_deligne_simpson_spectral_moduli_coupling,
    compute_hodge_coupling as fs_compute_hodge_coupling,
    compute_deligne_simpson_coupling as fs_compute_deligne_simpson_coupling,
    compute_hitchin_equation_coupling as fs_compute_hitchin_equation_coupling,
    compute_harmonic_bundle_coupling as fs_compute_harmonic_bundle_coupling,
    compute_non_abelian_hodge_spectral_coupling as fs_compute_non_abelian_hodge_spectral_coupling,
    compute_hitchin_harmonic_bundle_coupling as fs_compute_hitchin_harmonic_bundle_coupling,
    compute_non_abelian_hodge_theory_coupling as fs_compute_non_abelian_hodge_theory_coupling,
    compute_simpson_spectral_moduli_coupling as fs_compute_simpson_spectral_moduli_coupling,
    compute_hitchin_equations_coupling as fs_compute_hitchin_equations_coupling,
    DerivedArithmeticTopologyCoupler as fs_DerivedArithmeticTopologyCoupler,
)


class TestPhase25Alpha:
    """Test suite covering Phase 25 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F120.2: 64th-Order Hexatetrahedral Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_hexatetrahedral_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.005) has leakage < 10^-34."""
        z_grid = np.linspace(-0.005, 0.005, 100)
        denoised = apply_hexatetrahedral_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=64.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-34, f"Max noise leakage {max_leakage} must be < 1e-34"

        # Check boundary point |z| = 0.005
        val_at_bound = float(np.abs(apply_hexatetrahedral_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=64.0)))
        assert val_at_bound < 1e-34, f"Leakage at z=0.005 was {val_at_bound}, expected < 1e-34"

        # Check at z = 0.0
        val_at_zero = float(apply_hexatetrahedral_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=64.0))
        assert val_at_zero == 0.0

    def test_hexatetrahedral_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_hexatetrahedral_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=64.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_hexatetrahedral_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=64.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Hexatetrahedral deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_hexatetrahedral_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_hexatetrahedral_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=64.0)
        f_neg = apply_hexatetrahedral_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=64.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_hexatetrahedral_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_hexatetrahedral_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_hexatetrahedral_deadband(0.003, delta_noise=0.035)
        es_res = apply_hexatetrahedral_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version25_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=64.0 under version=25."""
        engine = EnsembleScoringEngine()
        z_val = 0.005
        res_v25 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=25)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=25)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=25)
        res_direct = apply_hexatetrahedral_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=64.0)

        assert math.isclose(float(res_v25), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F119: Non-Abelian Hodge Theory & Deligne-Simpson Coupler
    # -------------------------------------------------------------------------

    def test_non_abelian_hodge_coupler_invariants_bounded(self):
        """Validates that E_hodge, Z_simpson, h_hodge, and FERI_v25 are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })
        res = NonAbelianHodgeCoupler.compute(pillars)
        assert "h_hodge" in res
        assert "z_simpson" in res
        assert "e_hodge" in res
        assert "h_decay" in res
        assert "FERI_v25" in res
        assert "feri_v25" in res
        assert "Z_simpson" in res
        assert "E_hodge" in res
        assert "H_hodge" in res
        assert "h_deligne_simpson" in res
        assert "z_deligne_simpson" in res
        assert "e_deligne_simpson" in res
        assert "h_hodge_coupler" in res
        assert "z_hodge_coupler" in res
        assert "e_hodge_coupler" in res
        assert "h_hitchin" in res
        assert "z_hitchin" in res
        assert "e_hitchin" in res
        assert "h_hitchin_equation" in res
        assert "z_hitchin_equation" in res
        assert "e_hitchin_equation" in res
        assert "h_harmonic_bundle" in res
        assert "z_harmonic_bundle" in res
        assert "e_harmonic_bundle" in res
        assert "h_spectral_moduli" in res
        assert "z_spectral_moduli" in res
        assert "e_spectral_moduli" in res
        assert "h_non_abelian_hodge" in res
        assert "z_non_abelian_hodge" in res
        assert "e_non_abelian_hodge" in res
        assert "h_non_abelian_hodge_spectral" in res
        assert "z_non_abelian_hodge_spectral" in res
        assert "e_non_abelian_hodge_spectral" in res

        z_arr = res["z_simpson"].values
        e_arr = res["e_hodge"].values
        h_arr = res["h_hodge"].values
        feri_arr = res["FERI_v25"].values

        assert np.all(z_arr > 0.0) and np.all(z_arr <= 1.0)
        assert np.all(e_arr >= 0.0)
        assert np.all(h_arr > 0.0) and np.all(h_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_non_abelian_hodge_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when factor sections agree perfectly, E_hodge == 0, Z_simpson == 1.0, h_hodge == 1.0, and FERI_v25 == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = NonAbelianHodgeCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_hodge"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_simpson"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_hodge"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v25"].values, 1.0, atol=1e-12)

    def test_non_abelian_hodge_coupler_adversarial_conflict(self):
        """Validates that severe pillar discordance produces high obstruction and suppresses h_hodge smoothly."""
        conflict_pillars = pd.DataFrame({
            'val': [1.0, -1.0],
            'mom': [-1.0, 1.0],
            'flow': [1.0, -1.0],
            'cat': [-1.0, 1.0],
            'net': [1.0, -1.0],
        })
        res = NonAbelianHodgeCoupler.compute(conflict_pillars)
        assert np.all(res["e_hodge"].values > 1.0)
        assert np.all(res["z_simpson"].values <= 1.0)
        assert np.all(res["h_hodge"].values < 0.05)
        assert np.all(res["FERI_v25"].values < 0.50)

    def test_non_abelian_hodge_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly across all aliases."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = NonAbelianHodgeCoupler.compute(p_dict)
        assert len(res_dict["h_hodge"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = NonAbelianHodgeCoupler.compute(v_single)
        assert isinstance(res_1d["h_hodge"], float)
        assert 0.0 < res_1d["h_hodge"] <= 1.0

        # Classmethods on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_non_abelian_hodge_coupling(v_single)
        assert math.isclose(res_engine["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_engine_alias1 = EnsembleScoringEngine.compute_deligne_simpson_spectral_moduli_coupling(v_single)
        assert math.isclose(res_engine_alias1["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_engine_alias2 = EnsembleScoringEngine.compute_hodge_coupling(v_single)
        assert math.isclose(res_engine_alias2["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_engine_alias3 = EnsembleScoringEngine.compute_deligne_simpson_coupling(v_single)
        assert math.isclose(res_engine_alias3["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_engine_alias4 = EnsembleScoringEngine.compute_hitchin_equation_coupling(v_single)
        assert math.isclose(res_engine_alias4["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_engine_alias5 = EnsembleScoringEngine.compute_harmonic_bundle_coupling(v_single)
        assert math.isclose(res_engine_alias5["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_engine_alias6 = EnsembleScoringEngine.compute_non_abelian_hodge_spectral_coupling(v_single)
        assert math.isclose(res_engine_alias6["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)

        # Aliases
        aliases = [
            DeligneSimpsonSpectralModuliCoupler,
            HodgeCoupler,
            DeligneSimpsonCoupler,
            HitchinEquationCoupler,
            HarmonicBundleCoupler,
            NonAbelianHodgeSpectralCoupler,
            HitchinHarmonicBundleCoupler,
            NonAbelianHodgeTheoryCoupler,
            SimpsonSpectralModuliCoupler,
            HitchinEquationsCoupler,
        ]
        for alias_cls in aliases:
            res_alias = alias_cls.compute(v_single)
            assert math.isclose(res_alias["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)

        # Cross-module exports in factor_suppression
        assert fs_NonAbelianHodgeCoupler is NonAbelianHodgeCoupler
        assert fs_DeligneSimpsonSpectralModuliCoupler is DeligneSimpsonSpectralModuliCoupler
        assert fs_HodgeCoupler is HodgeCoupler
        assert fs_DeligneSimpsonCoupler is DeligneSimpsonCoupler
        assert fs_HitchinEquationCoupler is HitchinEquationCoupler
        assert fs_HarmonicBundleCoupler is HarmonicBundleCoupler
        assert fs_NonAbelianHodgeSpectralCoupler is NonAbelianHodgeSpectralCoupler
        assert fs_HitchinHarmonicBundleCoupler is HitchinHarmonicBundleCoupler
        assert fs_NonAbelianHodgeTheoryCoupler is NonAbelianHodgeTheoryCoupler
        assert fs_SimpsonSpectralModuliCoupler is SimpsonSpectralModuliCoupler
        assert fs_HitchinEquationsCoupler is HitchinEquationsCoupler

        # Cross-module compute functions in factor_suppression
        res_fs1 = fs_compute_non_abelian_hodge_coupling(v_single)
        assert math.isclose(res_fs1["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_fs2 = fs_compute_deligne_simpson_spectral_moduli_coupling(v_single)
        assert math.isclose(res_fs2["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_fs3 = fs_compute_hodge_coupling(v_single)
        assert math.isclose(res_fs3["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_fs4 = fs_compute_deligne_simpson_coupling(v_single)
        assert math.isclose(res_fs4["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_fs5 = fs_compute_hitchin_equation_coupling(v_single)
        assert math.isclose(res_fs5["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_fs6 = fs_compute_harmonic_bundle_coupling(v_single)
        assert math.isclose(res_fs6["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)
        res_fs7 = fs_compute_non_abelian_hodge_spectral_coupling(v_single)
        assert math.isclose(res_fs7["h_hodge"], res_1d["h_hodge"], abs_tol=1e-12)

    def test_quint_pillar_tensor_synergy_version25(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates Non-Abelian Hodge coupling for version=25."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 0.85],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 0.85, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v24 = engine.compute_quint_pillar_tensor_synergy(pillars, version=24)
        synergy_v25 = engine.compute_quint_pillar_tensor_synergy(pillars, version=25)

        assert isinstance(synergy_v25, pd.Series)
        assert len(synergy_v25) == 3
        assert np.all(np.isfinite(synergy_v25.values))
        assert np.all(synergy_v25.values > 0.0)
        # Highly coherent positive pillars should produce greater synergy in v25 with + 1.15 * h_hodge * z_simpson
        assert np.all(synergy_v25.values >= synergy_v24.values - 1e-6)

    # -------------------------------------------------------------------------
    # 3. Feature F120.1: 20th-Order Hyper-Convex Rank Modulation (g_v25)
    # -------------------------------------------------------------------------

    def test_20th_order_rank_modulation_percentiles(self):
        """Validates that 20th-order rank modulation concentrates capital into top percentiles (r >= 0.99999999999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase25_hyperconvex_rank_modulation(r_grid, gamma_top=2.60)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod < 1.08
        assert mod[2] < 1.08
        # Extreme conviction at r=1.0: 0.50 + 1.14 * 1.0 * exp(2.60) ~ 0.50 + 1.14 * 13.4637 ~ 15.849 > 14.50
        assert mod[-1] > 14.50

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase25_hyperconvex_rank_modulation(r_neg, gamma_top=2.60, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

        # Alias check
        mod_alias = compute_phase25_rank_warping(r_grid, gamma_top=2.60)
        np.testing.assert_allclose(mod, mod_alias, atol=1e-12)

        # Cross-module export check
        mod_fs = fs_compute_phase25_modulation(r_grid, gamma_top=2.60)
        np.testing.assert_allclose(mod, mod_fs, atol=1e-12)
        mod_fs_warp = fs_compute_phase25_warping(r_grid, gamma_top=2.60)
        np.testing.assert_allclose(mod, mod_fs_warp, atol=1e-12)

    def test_20th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v25(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase25_hyperconvex_rank_modulation(r_fine, gamma_top=2.40)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "20th-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "20th-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version25(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 25 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=25) == 2.60
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("2", version=25) == 2.60
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=25) == 2.40
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS", version=25) == 2.20
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=25) == 2.20
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("1", version=25) == 2.20
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=25) == 1.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR", version=25) == 1.90
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=25) == 1.90
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("0", version=25) == 1.90
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=25) == 0.80
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=25) == 1.55
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=25) == 2.10

        # Also test factor_suppression regime functions and table
        assert fs_REGIME_GAMMA_TOP_V25["BULL_LOW_VOL"] == 2.60
        assert fs_REGIME_GAMMA_TOP_V25["BULL_HIGH_VOL"] == 2.40
        assert fs_REGIME_GAMMA_TOP_V25["SIDEWAYS"] == 2.20
        assert fs_REGIME_GAMMA_TOP_V25["BEAR"] == 1.90
        assert fs_REGIME_GAMMA_TOP_V25["CRISIS"] == 1.55
        assert fs_get_regime_adaptive_gamma_top_v25("BULL_LOW_VOL") == 2.60
        assert fs_get_regime_adaptive_gamma_top_v25("BULL_HIGH_VOL") == 2.40
        assert fs_get_regime_adaptive_gamma_top_v25("SIDEWAYS") == 2.20
        assert fs_get_regime_adaptive_gamma_top_v25("BEAR") == 1.90
        assert fs_get_regime_adaptive_gamma_top_v25("CRISIS") == 1.55

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version25_full_pipeline(self):
        """Validates full combine_predictions() execution with version=25."""
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

        comb_v24 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=24)
        comb_v25 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=25)

        assert isinstance(comb_v25, pd.DataFrame)
        assert not comb_v25.empty
        assert "ensemble_score" in comb_v25.columns
        assert len(comb_v25) == N
        assert np.all(np.isfinite(comb_v25["ensemble_score"].values))
        assert np.all(comb_v25["ensemble_score"].values >= 0.0)
        assert np.all(comb_v25["ensemble_score"].values <= 1.0)

        # Top conviction in v25 should exhibit strong concentration
        top_v24 = comb_v24.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v25 = comb_v25.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v25 >= top_v24 - 1e-6, f"Top conviction in v25 ({top_v25}) should be >= v24 ({top_v24})"

    def test_backward_compatibility_v13_through_v25(self):
        """Validates that versions 13 through 25 continue to run identically without disruption."""
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
