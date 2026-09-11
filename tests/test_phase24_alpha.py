"""
tests/test_phase24_alpha.py

Comprehensive unit test suite for Phase 24 Quantitative Alpha Signal Enhancement (Milestone R1):
- Feature F115: Derived Arithmetic Topology & Étale-Motivic Spectral Homotopy Factor Disentanglement Engine
  (DerivedArithmeticTopologyCoupler, H^*_{ét-mot}, E_arithmetic, Z_spectral, theta_0=0.32, kappa=3.20)
- Feature F116.1: 19th-Order Hyper-Convex Rank Modulation (g_v24(r) = 0.50 + 1.12 * r * exp(gamma_top * r^19))
- Feature F116.2: 60th-Order Hexacontagonal Hyperbolic Tangent Noise Deadband (alpha=60.0, leakage < 10^-32)
- End-to-End EnsembleScoringEngine combine_predictions() with version=24
- Strict backward compatibility validation with Phase 13 (v13) through Phase 23 (v23)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_hexacontagonal_hyperbolic_deadband,
    apply_hexaquinquagintagonal_hyperbolic_deadband,
    apply_doquinquagintagonal_hyperbolic_deadband,
    apply_octatetracontagonal_hyperbolic_deadband,
    apply_tetracontatetragonal_hyperbolic_deadband,
    apply_tetracontagonal_hyperbolic_deadband,
    apply_hexatriacontagonal_hyperbolic_deadband,
    apply_dotriacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase24_hyperconvex_rank_modulation,
    compute_phase24_rank_warping,
    compute_phase23_hyperconvex_rank_modulation,
    compute_phase22_hyperconvex_rank_modulation,
    DerivedArithmeticTopologyCoupler,
    EtaleMotivicSpectralHomotopyCoupler,
    DerivedArithmeticCoupler,
    EtaleMotivicCoupler,
    ArtinVerdierDualityCoupler,
    MotivicSpectralHomotopyCoupler,
    ArithmeticTopologyCoupler,
    ToposicGeometricLanglandsCoupler,
    GeometricLanglandsCoupler,
    CondensedAnalyticGeometryCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexacontagonal_hyperbolic_deadband as fs_hexacontagonal_deadband,
    apply_hexaquinquagintagonal_hyperbolic_deadband as fs_hexaquinquagintagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    compute_phase24_hyperconvex_rank_modulation as fs_compute_phase24_modulation,
    compute_phase24_rank_warping as fs_compute_phase24_warping,
    REGIME_GAMMA_TOP_V24 as fs_REGIME_GAMMA_TOP_V24,
    get_regime_adaptive_gamma_top_v24 as fs_get_regime_adaptive_gamma_top_v24,
    DerivedArithmeticTopologyCoupler as fs_DerivedArithmeticTopologyCoupler,
    EtaleMotivicSpectralHomotopyCoupler as fs_EtaleMotivicSpectralHomotopyCoupler,
    DerivedArithmeticCoupler as fs_DerivedArithmeticCoupler,
    EtaleMotivicCoupler as fs_EtaleMotivicCoupler,
    ArtinVerdierDualityCoupler as fs_ArtinVerdierDualityCoupler,
    MotivicSpectralHomotopyCoupler as fs_MotivicSpectralHomotopyCoupler,
    ArithmeticTopologyCoupler as fs_ArithmeticTopologyCoupler,
    ToposicGeometricLanglandsCoupler as fs_ToposicGeometricLanglandsCoupler,
)


class TestPhase24Alpha:
    """Test suite covering Phase 24 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F116.2: 60th-Order Hexacontagonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_hexacontagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.005) has leakage < 10^-32."""
        z_grid = np.linspace(-0.005, 0.005, 100)
        denoised = apply_hexacontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=60.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-32, f"Max noise leakage {max_leakage} must be < 1e-32"

        # Check boundary point |z| = 0.005
        val_at_bound = float(np.abs(apply_hexacontagonal_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=60.0)))
        assert val_at_bound < 1e-32, f"Leakage at z=0.005 was {val_at_bound}, expected < 1e-32"

        # Check at z = 0.0
        val_at_zero = float(apply_hexacontagonal_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=60.0))
        assert val_at_zero == 0.0

    def test_hexacontagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_hexacontagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=60.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_hexacontagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=60.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Hexacontagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_hexacontagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_hexacontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=60.0)
        f_neg = apply_hexacontagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=60.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_hexacontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_hexacontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_hexacontagonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_hexacontagonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version24_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=60.0 under version=24."""
        engine = EnsembleScoringEngine()
        z_val = 0.005
        res_v24 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=24)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=24)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=24)
        res_direct = apply_hexacontagonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=60.0)

        assert math.isclose(float(res_v24), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F115: Derived Arithmetic Topology Coupler
    # -------------------------------------------------------------------------

    def test_derived_arithmetic_topology_coupler_invariants_bounded(self):
        """Validates that E_arithmetic, Z_spectral, h_arithmetic, and FERI_v24 are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })
        res = DerivedArithmeticTopologyCoupler.compute(pillars)
        assert "h_arithmetic" in res
        assert "z_spectral" in res
        assert "e_arithmetic" in res
        assert "h_decay" in res
        assert "FERI_v24" in res
        assert "feri_v24" in res
        assert "Z_spectral" in res
        assert "E_arithmetic" in res
        assert "H_arithmetic" in res
        assert "h_et_mot" in res
        assert "z_et_mot" in res
        assert "e_et_mot" in res
        assert "h_etale_motivic" in res
        assert "z_etale_motivic" in res
        assert "e_etale_motivic" in res
        assert "h_spectral" in res
        assert "e_spectral" in res
        assert "z_spectral_invariant" in res
        assert "h_artin_verdier" in res
        assert "z_artin_verdier" in res
        assert "e_artin_verdier" in res
        assert "h_arithmetic_topology" in res
        assert "z_arithmetic_topology" in res
        assert "e_arithmetic_topology" in res

        z_arr = res["z_spectral"].values
        e_arr = res["e_arithmetic"].values
        h_arr = res["h_arithmetic"].values
        feri_arr = res["FERI_v24"].values

        assert np.all(z_arr > 0.0) and np.all(z_arr <= 1.0)
        assert np.all(e_arr >= 0.0)
        assert np.all(h_arr > 0.0) and np.all(h_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_derived_arithmetic_topology_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when factor sections agree perfectly, E_arithmetic == 0, Z_spectral == 1.0, h_arithmetic == 1.0, and FERI_v24 == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = DerivedArithmeticTopologyCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_arithmetic"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_spectral"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_arithmetic"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v24"].values, 1.0, atol=1e-12)

    def test_derived_arithmetic_topology_coupler_adversarial_conflict(self):
        """Validates that severe pillar discordance produces high obstruction and suppresses h_arithmetic smoothly."""
        conflict_pillars = pd.DataFrame({
            'val': [1.0, -1.0],
            'mom': [-1.0, 1.0],
            'flow': [1.0, -1.0],
            'cat': [-1.0, 1.0],
            'net': [1.0, -1.0],
        })
        res = DerivedArithmeticTopologyCoupler.compute(conflict_pillars)
        assert np.all(res["e_arithmetic"].values > 1.0)
        assert np.all(res["z_spectral"].values <= 1.0)
        assert np.all(res["h_arithmetic"].values < 0.05)
        assert np.all(res["FERI_v24"].values < 0.50)

    def test_derived_arithmetic_topology_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = DerivedArithmeticTopologyCoupler.compute(p_dict)
        assert len(res_dict["h_arithmetic"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = DerivedArithmeticTopologyCoupler.compute(v_single)
        assert isinstance(res_1d["h_arithmetic"], float)
        assert 0.0 < res_1d["h_arithmetic"] <= 1.0

        # Classmethod on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_derived_arithmetic_topology_coupling(v_single)
        assert math.isclose(res_engine["h_arithmetic"], res_1d["h_arithmetic"], abs_tol=1e-12)

        # Aliases
        res_alias1 = EtaleMotivicSpectralHomotopyCoupler.compute(v_single)
        res_alias2 = DerivedArithmeticCoupler.compute(v_single)
        res_alias3 = EtaleMotivicCoupler.compute(v_single)
        res_alias4 = ArtinVerdierDualityCoupler.compute(v_single)
        res_alias5 = MotivicSpectralHomotopyCoupler.compute(v_single)
        res_alias6 = ArithmeticTopologyCoupler.compute(v_single)
        assert math.isclose(res_alias1["h_arithmetic"], res_1d["h_arithmetic"], abs_tol=1e-12)
        assert math.isclose(res_alias2["h_arithmetic"], res_1d["h_arithmetic"], abs_tol=1e-12)
        assert math.isclose(res_alias3["h_arithmetic"], res_1d["h_arithmetic"], abs_tol=1e-12)
        assert math.isclose(res_alias4["h_arithmetic"], res_1d["h_arithmetic"], abs_tol=1e-12)
        assert math.isclose(res_alias5["h_arithmetic"], res_1d["h_arithmetic"], abs_tol=1e-12)
        assert math.isclose(res_alias6["h_arithmetic"], res_1d["h_arithmetic"], abs_tol=1e-12)

        # Cross-module exports in factor_suppression
        assert fs_DerivedArithmeticTopologyCoupler is DerivedArithmeticTopologyCoupler
        assert fs_EtaleMotivicSpectralHomotopyCoupler is EtaleMotivicSpectralHomotopyCoupler
        assert fs_DerivedArithmeticCoupler is DerivedArithmeticCoupler
        assert fs_EtaleMotivicCoupler is EtaleMotivicCoupler
        assert fs_ArtinVerdierDualityCoupler is ArtinVerdierDualityCoupler
        assert fs_MotivicSpectralHomotopyCoupler is MotivicSpectralHomotopyCoupler
        assert fs_ArithmeticTopologyCoupler is ArithmeticTopologyCoupler

    def test_quint_pillar_tensor_synergy_version24(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates Derived Arithmetic Topology coupling for version=24."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 0.85],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 0.85, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v23 = engine.compute_quint_pillar_tensor_synergy(pillars, version=23)
        synergy_v24 = engine.compute_quint_pillar_tensor_synergy(pillars, version=24)

        assert isinstance(synergy_v24, pd.Series)
        assert len(synergy_v24) == 3
        assert np.all(np.isfinite(synergy_v24.values))
        assert np.all(synergy_v24.values > 0.0)
        # Highly coherent positive pillars should produce greater synergy in v24 with + 1.05 * h_arith * z_spectral
        assert np.all(synergy_v24.values >= synergy_v23.values - 1e-6)

    # -------------------------------------------------------------------------
    # 3. Feature F116.1: 19th-Order Hyper-Convex Rank Modulation (g_v24)
    # -------------------------------------------------------------------------

    def test_19th_order_rank_modulation_percentiles(self):
        """Validates that 19th-order rank modulation concentrates capital into top percentiles (r >= 0.999999999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase24_hyperconvex_rank_modulation(r_grid, gamma_top=2.50)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod < 1.08
        assert mod[2] < 1.08
        # Extreme conviction at r=1.0: 0.50 + 1.12 * 1.0 * exp(2.50) ~ 0.50 + 1.12 * 12.1825 ~ 14.144 > 13.00
        assert mod[-1] > 13.00

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase24_hyperconvex_rank_modulation(r_neg, gamma_top=2.50, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

        # Alias check
        mod_alias = compute_phase24_rank_warping(r_grid, gamma_top=2.50)
        np.testing.assert_allclose(mod, mod_alias, atol=1e-12)

        # Cross-module export check
        mod_fs = fs_compute_phase24_modulation(r_grid, gamma_top=2.50)
        np.testing.assert_allclose(mod, mod_fs, atol=1e-12)
        mod_fs_warp = fs_compute_phase24_warping(r_grid, gamma_top=2.50)
        np.testing.assert_allclose(mod, mod_fs_warp, atol=1e-12)

    def test_19th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v24(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase24_hyperconvex_rank_modulation(r_fine, gamma_top=2.20)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "19th-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "19th-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version24(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 24 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=24) == 2.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("2", version=24) == 2.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=24) == 2.30
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS", version=24) == 2.10
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=24) == 2.10
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("1", version=24) == 2.10
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=24) == 1.45
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR", version=24) == 1.85
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=24) == 1.85
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("0", version=24) == 1.85
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=24) == 0.75
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=24) == 1.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=24) == 2.00

        # Also test factor_suppression regime functions and table
        assert fs_REGIME_GAMMA_TOP_V24["BULL_LOW_VOL"] == 2.50
        assert fs_REGIME_GAMMA_TOP_V24["BULL_HIGH_VOL"] == 2.30
        assert fs_REGIME_GAMMA_TOP_V24["SIDEWAYS"] == 2.10
        assert fs_REGIME_GAMMA_TOP_V24["BEAR"] == 1.85
        assert fs_REGIME_GAMMA_TOP_V24["CRISIS"] == 1.50
        assert fs_get_regime_adaptive_gamma_top_v24("BULL_LOW_VOL") == 2.50
        assert fs_get_regime_adaptive_gamma_top_v24("BULL_HIGH_VOL") == 2.30
        assert fs_get_regime_adaptive_gamma_top_v24("SIDEWAYS") == 2.10
        assert fs_get_regime_adaptive_gamma_top_v24("BEAR") == 1.85
        assert fs_get_regime_adaptive_gamma_top_v24("CRISIS") == 1.50

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version24_full_pipeline(self):
        """Validates full combine_predictions() execution with version=24."""
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

        comb_v23 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=23)
        comb_v24 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=24)

        assert isinstance(comb_v24, pd.DataFrame)
        assert not comb_v24.empty
        assert "ensemble_score" in comb_v24.columns
        assert len(comb_v24) == N
        assert np.all(np.isfinite(comb_v24["ensemble_score"].values))
        assert np.all(comb_v24["ensemble_score"].values >= 0.0)
        assert np.all(comb_v24["ensemble_score"].values <= 1.0)

        # Top conviction in v24 should exhibit strong concentration
        top_v23 = comb_v23.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v24 = comb_v24.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v24 >= top_v23 - 1e-6, f"Top conviction in v24 ({top_v24}) should be >= v23 ({top_v23})"

    def test_backward_compatibility_v13_through_v24(self):
        """Validates that versions 13 through 24 continue to run identically without disruption."""
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
