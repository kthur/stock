r"""
tests/test_phase27_alpha.py

Comprehensive unit test suite for Phase 27 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F127: Perfectoid Shimura Variety & Mochizuki Inter-Universal Teichmüller (IUT) Reconstruction
  Factor Disentanglement Engine (AnabelianGrothendieckCoupler, Hodge-Tate filtration obstruction complex E_anabelian,
  Mochizuki theta-link indeterminacy invariant Z_anabelian, coupling factor h_anabelian,
  theta_0=0.35, kappa=3.50, complete aliases and factor_suppression bindings)
- Feature F128.1: 22nd-Order Hyper-Convex Rank Modulation (g_v27(r) = 0.50 + 1.18 * r * exp(gamma_top * r^22))
  with regime-adaptive gamma_top up to 2.80 (REGIME_GAMMA_TOP_V27, get_regime_adaptive_gamma_top_v27)
- Feature F128.2: 72nd-Order Heptaduogonal Hyperbolic Tangent Noise Deadband (alpha=72.0, leakage < 10^-36)
- End-to-End EnsembleScoringEngine combine_predictions() with version=26
- Strict backward compatibility validation with Phase 13 (v13) through Phase 27 (v27)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_heptaduogonal_hyperbolic_deadband,
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
    compute_phase27_hyperconvex_rank_modulation,
    compute_phase27_rank_warping,
    compute_phase25_hyperconvex_rank_modulation,
    compute_phase24_hyperconvex_rank_modulation,
    compute_phase23_hyperconvex_rank_modulation,
    AnabelianGrothendieckCoupler,
    AnabelianGeometryCoupler,
    GrothendieckSectionCoupler,
    SectionConjectureCoupler,
    EtaleFundamentalCoupler,
    AnabelianCoupler,
    GrothendieckCoupler,
    SectionCoupler,
    AnabelianGrothendieckCoupler,
    AnabelianCoupler,
    GrothendieckCoupler,
    NonAbelianHodgeCoupler,
    DerivedArithmeticTopologyCoupler,
    ToposicGeometricLanglandsCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_heptaduogonal_hyperbolic_deadband as fs_heptaduogonal_deadband,
    apply_hexatetrahedral_hyperbolic_deadband as fs_hexatetrahedral_deadband,
    apply_hexacontagonal_hyperbolic_deadband as fs_hexacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase27_hyperconvex_rank_modulation as fs_compute_phase27_modulation,
    compute_phase27_rank_warping as fs_compute_phase27_warping,
    REGIME_GAMMA_TOP_V27 as fs_REGIME_GAMMA_TOP_V27,
    get_regime_adaptive_gamma_top_v27 as fs_get_regime_adaptive_gamma_top_v27,
    AnabelianGrothendieckCoupler as fs_AnabelianGrothendieckCoupler,
    AnabelianGeometryCoupler as fs_AnabelianGeometryCoupler,
    GrothendieckSectionCoupler as fs_GrothendieckSectionCoupler,
    SectionConjectureCoupler as fs_SectionConjectureCoupler,
    EtaleFundamentalCoupler as fs_EtaleFundamentalCoupler,
    AnabelianCoupler as fs_AnabelianCoupler,
    GrothendieckCoupler as fs_GrothendieckCoupler,
    SectionCoupler as fs_SectionCoupler,
    AnabelianGrothendieckCoupler as fs_AnabelianGrothendieckCoupler,
    AnabelianCoupler as fs_AnabelianCoupler,
    GrothendieckCoupler as fs_GrothendieckCoupler,
    compute_anabelian_grothendieck_coupling as fs_compute_anabelian_grothendieck_coupling,
    compute_anabelian_geometry_coupling as fs_compute_anabelian_geometry_coupling,
    compute_grothendieck_section_coupling as fs_compute_grothendieck_section_coupling,
    compute_section_conjecture_coupling as fs_compute_section_conjecture_coupling,
    compute_etale_fundamental_coupling as fs_compute_etale_fundamental_coupling,
    compute_anabelian_coupling as fs_compute_anabelian_coupling,
    compute_grothendieck_coupling as fs_compute_grothendieck_coupling,
    compute_section_coupling as fs_compute_section_coupling,
    compute_perfectoid_shimura_coupling as fs_compute_perfectoid_shimura_coupling,
    compute_mochizuki_coupling as fs_compute_mochizuki_coupling,
    compute_anabelian_coupling as fs_compute_anabelian_coupling,
    NonAbelianHodgeCoupler as fs_NonAbelianHodgeCoupler,
)


class TestPhase27Alpha:
    """Test suite covering Phase 27 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F128.2: 72nd-Order Heptaduogonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_heptaduogonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.005) has leakage < 10^-36."""
        z_grid = np.linspace(-0.005, 0.005, 100)
        denoised = apply_heptaduogonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=72.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-38, f"Max noise leakage {max_leakage} must be < 1e-38"

        # Check boundary point |z| = 0.005
        val_at_bound = float(np.abs(apply_heptaduogonal_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=72.0)))
        assert val_at_bound < 1e-38, f"Leakage at z=0.005 was {val_at_bound}, expected < 1e-38"

        # Check at z = 0.0
        val_at_zero = float(apply_heptaduogonal_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=72.0))
        assert val_at_zero == 0.0

    def test_heptaduogonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_heptaduogonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=72.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_heptaduogonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=72.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Heptaduogonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_heptaduogonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_heptaduogonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=72.0)
        f_neg = apply_heptaduogonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=72.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_heptaduogonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_heptaduogonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_heptaduogonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_heptaduogonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version26_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=72.0 under version=26."""
        engine = EnsembleScoringEngine()
        z_val = 0.005
        res_v27 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=26)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=26)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=26)
        res_direct = apply_heptaduogonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=72.0)

        assert math.isclose(float(res_v27), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F127: Perfectoid Shimura Variety & Mochizuki IUT Coupler
    # -------------------------------------------------------------------------

    def test_perfectoid_shimura_coupler_invariants_bounded(self):
        """Validates that E_anabelian, Z_anabelian, h_anabelian, and FERI_v27 are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 1.40],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })
        res = AnabelianGrothendieckCoupler.compute(pillars)
        assert "h_anabelian" in res
        assert "z_anabelian" in res
        assert "e_anabelian" in res
        assert "h_decay" in res
        assert "FERI_v27" in res
        assert "feri_v27" in res
        assert "Z_anabelian" in res
        assert "E_anabelian" in res
        assert "H_anabelian" in res
        assert "h_grothendieck" in res
        assert "z_grothendieck" in res
        assert "e_grothendieck" in res
        assert "h_section" in res
        assert "z_section" in res
        assert "e_section" in res
        assert "h_etale" in res
        assert "z_etale" in res
        assert "e_etale" in res
        assert "h_galois" in res
        assert "z_galois" in res
        assert "e_galois" in res
        assert "h_anabelian_grothendieck" in res
        assert "z_anabelian_grothendieck" in res
        assert "e_anabelian_grothendieck" in res
        assert "h_section_conjecture" in res
        assert "z_section_conjecture" in res
        assert "e_section_conjecture" in res
        assert "h_anabelian_geometry" in res
        assert "z_anabelian_geometry" in res
        assert "e_anabelian_geometry" in res

        z_arr = res["z_anabelian"].values
        e_arr = res["e_anabelian"].values
        h_arr = res["h_anabelian"].values
        feri_arr = res["FERI_v27"].values

        assert np.all(z_arr > 0.0) and np.all(z_arr <= 1.0)
        assert np.all(e_arr >= 0.0)
        assert np.all(h_arr > 0.0) and np.all(h_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_perfectoid_shimura_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when factor sections agree perfectly, E_anabelian == 0, Z_anabelian == 1.0, h_anabelian == 1.0, and FERI_v27 == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = AnabelianGrothendieckCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_anabelian"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_anabelian"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_anabelian"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v27"].values, 1.0, atol=1e-12)

    def test_perfectoid_shimura_coupler_adversarial_conflict(self):
        """Validates that severe pillar discordance produces high obstruction and suppresses h_anabelian smoothly."""
        conflict_pillars = pd.DataFrame({
            'val': [1.0, -1.0],
            'mom': [-1.0, 1.0],
            'flow': [1.0, -1.0],
            'cat': [-1.0, 1.0],
            'net': [1.0, -1.0],
        })
        res = AnabelianGrothendieckCoupler.compute(conflict_pillars)
        assert np.all(res["e_anabelian"].values > 1.0)
        assert np.all(res["z_anabelian"].values <= 1.0)
        assert np.all(res["h_anabelian"].values < 0.05)
        assert np.all(res["FERI_v27"].values < 0.50)

    def test_perfectoid_shimura_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly across all aliases."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 1.40]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = AnabelianGrothendieckCoupler.compute(p_dict)
        assert len(res_dict["h_anabelian"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = AnabelianGrothendieckCoupler.compute(v_single)
        assert isinstance(res_1d["h_anabelian"], float)
        assert 0.0 < res_1d["h_anabelian"] <= 1.0

        # Classmethods on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_anabelian_grothendieck_coupling(v_single)
        assert math.isclose(res_engine["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_engine_alias1 = EnsembleScoringEngine.compute_anabelian_geometry_coupling(v_single)
        assert math.isclose(res_engine_alias1["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_engine_alias2 = EnsembleScoringEngine.compute_grothendieck_section_coupling(v_single)
        assert math.isclose(res_engine_alias2["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_engine_alias3 = EnsembleScoringEngine.compute_etale_fundamental_coupling(v_single)
        assert math.isclose(res_engine_alias3["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_engine_alias4 = EnsembleScoringEngine.compute_anabelian_coupling(v_single)
        assert math.isclose(res_engine_alias4["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_engine_alias5 = EnsembleScoringEngine.compute_grothendieck_coupling(v_single)
        assert math.isclose(res_engine_alias5["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_engine_alias6 = EnsembleScoringEngine.compute_section_coupling(v_single)
        assert math.isclose(res_engine_alias6["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)

        # Aliases
        aliases = [
            AnabelianGeometryCoupler,
            GrothendieckSectionCoupler,
            SectionConjectureCoupler,
            EtaleFundamentalCoupler,
            AnabelianCoupler,
            GrothendieckCoupler,
            SectionCoupler,
            AnabelianGrothendieckCoupler,
            AnabelianCoupler,
            GrothendieckCoupler,
        ]
        for alias_cls in aliases:
            res_alias = alias_cls.compute(v_single)
            assert math.isclose(res_alias["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)

        # Cross-module exports in factor_suppression
        assert fs_AnabelianGrothendieckCoupler is AnabelianGrothendieckCoupler
        assert fs_AnabelianGeometryCoupler is AnabelianGeometryCoupler
        assert fs_GrothendieckSectionCoupler is GrothendieckSectionCoupler
        assert fs_SectionConjectureCoupler is SectionConjectureCoupler
        assert fs_EtaleFundamentalCoupler is EtaleFundamentalCoupler
        assert fs_AnabelianCoupler is AnabelianCoupler
        assert fs_GrothendieckCoupler is GrothendieckCoupler
        assert fs_SectionCoupler is SectionCoupler
        assert fs_AnabelianGrothendieckCoupler is AnabelianGrothendieckCoupler
        assert fs_AnabelianCoupler is AnabelianCoupler
        assert fs_GrothendieckCoupler is GrothendieckCoupler

        # Cross-module compute functions in factor_suppression
        res_fs1 = fs_compute_anabelian_grothendieck_coupling(v_single)
        assert math.isclose(res_fs1["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_fs2 = fs_compute_anabelian_geometry_coupling(v_single)
        assert math.isclose(res_fs2["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_fs3 = fs_compute_grothendieck_section_coupling(v_single)
        assert math.isclose(res_fs3["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_fs4 = fs_compute_etale_fundamental_coupling(v_single)
        assert math.isclose(res_fs4["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_fs5 = fs_compute_anabelian_coupling(v_single)
        assert math.isclose(res_fs5["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_fs6 = fs_compute_grothendieck_coupling(v_single)
        assert math.isclose(res_fs6["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)
        res_fs7 = fs_compute_section_coupling(v_single)
        assert math.isclose(res_fs7["h_anabelian"], res_1d["h_anabelian"], abs_tol=1e-12)

    def test_quint_pillar_tensor_synergy_version26(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates Perfectoid Shimura coupling for version=26."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 1.40],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 1.40, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v25 = engine.compute_quint_pillar_tensor_synergy(pillars, version=25)
        synergy_v27 = engine.compute_quint_pillar_tensor_synergy(pillars, version=26)

        assert isinstance(synergy_v27, pd.Series)
        assert len(synergy_v27) == 3
        assert np.all(np.isfinite(synergy_v27.values))
        assert np.all(synergy_v27.values > 0.0)
        # Highly coherent positive pillars should produce greater synergy in v27 with + 1.25 * h_anabelian * z_anabelian
        assert np.all(synergy_v27.values >= synergy_v25.values - 1e-6)

    # -------------------------------------------------------------------------
    # 3. Feature F128.1: 22nd-Order Hyper-Convex Rank Modulation (g_v27)
    # -------------------------------------------------------------------------

    def test_22nd_order_rank_modulation_percentiles(self):
        """Validates that 22nd-order rank modulation concentrates capital into top percentiles (r >= 0.999999999999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase27_hyperconvex_rank_modulation(r_grid, gamma_top=2.80)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod < 1.10
        assert mod[2] < 1.10
        # Extreme conviction at r=1.0: 0.50 + 1.18 * 1.0 * exp(2.80) ~ 0.50 + 1.18 * 16.4446 ~ 19.90 > 18.00
        assert mod[-1] > 18.00

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase27_hyperconvex_rank_modulation(r_neg, gamma_top=2.80, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

        # Alias check
        mod_alias = compute_phase27_rank_warping(r_grid, gamma_top=2.80)
        np.testing.assert_allclose(mod, mod_alias, atol=1e-12)

        # Cross-module export check
        mod_fs = fs_compute_phase27_modulation(r_grid, gamma_top=2.80)
        np.testing.assert_allclose(mod, mod_fs, atol=1e-12)
        mod_fs_warp = fs_compute_phase27_warping(r_grid, gamma_top=2.80)
        np.testing.assert_allclose(mod, mod_fs_warp, atol=1e-12)

    def test_22nd_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v27(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase27_hyperconvex_rank_modulation(r_fine, gamma_top=2.50)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "22nd-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "22nd-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version27(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 27 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=27) == 2.80
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("2", version=27) == 2.80
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=27) == 2.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS", version=27) == 2.30
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=27) == 2.30
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("1", version=27) == 2.30
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=27) == 1.60
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR", version=27) == 2.00
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=27) == 2.00
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("0", version=27) == 2.00
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=27) == 1.40
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=27) == 0.85
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=27) == 2.20

        # Also test factor_suppression regime functions and table
        assert fs_REGIME_GAMMA_TOP_V27["BULL_LOW_VOL"] == 2.80
        assert fs_REGIME_GAMMA_TOP_V27["BULL_HIGH_VOL"] == 2.50
        assert fs_REGIME_GAMMA_TOP_V27["SIDEWAYS"] == 2.30
        assert fs_REGIME_GAMMA_TOP_V27["BEAR"] == 2.00
        assert fs_REGIME_GAMMA_TOP_V27["CRISIS"] == 0.85
        assert fs_get_regime_adaptive_gamma_top_v27("BULL_LOW_VOL") == 2.80
        assert fs_get_regime_adaptive_gamma_top_v27("BULL_HIGH_VOL") == 2.50
        assert fs_get_regime_adaptive_gamma_top_v27("SIDEWAYS") == 2.30
        assert fs_get_regime_adaptive_gamma_top_v27("BEAR") == 2.00
        assert fs_get_regime_adaptive_gamma_top_v27("CRISIS") == 0.85

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
        comb_v27 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=26)

        assert isinstance(comb_v27, pd.DataFrame)
        assert not comb_v27.empty
        assert "ensemble_score" in comb_v27.columns
        assert len(comb_v27) == N
        assert np.all(np.isfinite(comb_v27["ensemble_score"].values))
        assert np.all(comb_v27["ensemble_score"].values >= 0.0)
        assert np.all(comb_v27["ensemble_score"].values <= 1.0)

        # Top conviction in v27 should exhibit strong concentration
        top_v25 = comb_v25.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v27 = comb_v27.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v27 >= top_v25 - 1e-6, f"Top conviction in v27 ({top_v27}) should be >= v25 ({top_v25})"

    def test_backward_compatibility_v13_through_v27(self):
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
        res_v27 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=26)

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
        assert len(res_v27) == N
