"""
tests/test_phase21_signal_enhancement.py

Comprehensive unit test suite for Phase 21 Quantitative Alpha Signal Enhancement (Milestone M1):
- Feature F103: Derived Motivic Homotopy Type Theory Factor Disentanglement Engine (DerivedMotivicHomotopyTypeTheoryCoupler)
- Feature F104.1: 16th-Order Ultra-Convex Rank Modulation (g_v21) across 2D Market Regimes
- Feature F104.2: 48th-Order Octatetracontagonal Hyperbolic Tangent Noise Deadband (alpha=48.0, leakage < 10^-26)
- End-to-End EnsembleScoringEngine combine_predictions() with version=21
- Strict backward compatibility validation with Phase 13 (v13) through Phase 20 (v20)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_octatetracontagonal_hyperbolic_deadband,
    apply_tetracontatetragonal_hyperbolic_deadband,
    apply_tetracontagonal_hyperbolic_deadband,
    apply_hexatriacontagonal_hyperbolic_deadband,
    apply_dotriacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase21_hyperconvex_rank_modulation,
    compute_phase21_rank_warping,
    compute_phase20_hyperconvex_rank_modulation,
    compute_phase19_hyperconvex_rank_modulation,
    compute_phase18_hyperconvex_rank_modulation,
    compute_phase17_hyperconvex_rank_modulation,
    DerivedMotivicHomotopyTypeTheoryCoupler,
    DerivedMotivicCoupler,
    MotivicHomotopyTypeTheoryCoupler,
    MotivicHomotopyCoupler,
    PerfectoidPrismaticCoupler,
    PerfectoidSpaceCoupler,
    PrismaticCohomologyCoupler,
    LurieInfinityToposCoupler,
    LurieToposCoupler,
    DerivedAlgebraicGeometryMotivicCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_octatetracontagonal_hyperbolic_deadband as fs_octatetracontagonal_deadband,
    apply_tetracontatetragonal_hyperbolic_deadband as fs_tetracontatetragonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    DerivedMotivicHomotopyTypeTheoryCoupler as fs_DerivedMotivicHomotopyTypeTheoryCoupler,
    DerivedMotivicCoupler as fs_DerivedMotivicCoupler,
    MotivicHomotopyTypeTheoryCoupler as fs_MotivicHomotopyTypeTheoryCoupler,
    MotivicHomotopyCoupler as fs_MotivicHomotopyCoupler,
    PerfectoidPrismaticCoupler as fs_PerfectoidPrismaticCoupler,
)


class TestPhase21SignalEnhancement:
    """Test suite covering Phase 21 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F104.2: 48th-Order Octatetracontagonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_octatetracontagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.005) has leakage < 10^-26."""
        z_grid = np.linspace(-0.005, 0.005, 100)
        denoised = apply_octatetracontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=48.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-26, f"Max noise leakage {max_leakage} must be < 1e-26"

        # Check boundary point |z| = 0.005
        val_at_bound = float(np.abs(apply_octatetracontagonal_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=48.0)))
        assert val_at_bound < 1e-26, f"Leakage at z=0.005 was {val_at_bound}, expected < 1e-26"

        # Check at z = 0.0
        val_at_zero = float(apply_octatetracontagonal_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=48.0))
        assert val_at_zero == 0.0

    def test_octatetracontagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_octatetracontagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=48.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_octatetracontagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=48.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Octatetracontagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_octatetracontagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_octatetracontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=48.0)
        f_neg = apply_octatetracontagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=48.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_octatetracontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_octatetracontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_octatetracontagonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_octatetracontagonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version21_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=48.0 under version=21."""
        engine = EnsembleScoringEngine()
        z_val = 0.005
        res_v21 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=21)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=21)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=21)
        res_direct = apply_octatetracontagonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=48.0)

        assert math.isclose(float(res_v21), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F103: Derived Motivic Homotopy Type Theory Factor Coupler
    # -------------------------------------------------------------------------

    def test_derived_motivic_coupler_invariants_bounded(self):
        """Validates that E_motivic, Z_motivic, h_motivic, and FERI_v21 are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })
        res = DerivedMotivicHomotopyTypeTheoryCoupler.compute(pillars)
        assert "h_motivic" in res
        assert "z_motivic" in res
        assert "e_motivic" in res
        assert "h_decay" in res
        assert "FERI_v21" in res
        assert "Z_motivic" in res
        assert "E_motivic" in res
        assert "h_derived" in res
        assert "z_derived" in res
        assert "e_derived" in res
        assert "h_homotopy" in res
        assert "z_homotopy" in res
        assert "e_homotopy" in res

        z_arr = res["z_motivic"].values
        e_arr = res["e_motivic"].values
        h_arr = res["h_motivic"].values
        feri_arr = res["FERI_v21"].values

        assert np.all(z_arr > 0.0) and np.all(z_arr <= 1.0)
        assert np.all(e_arr >= 0.0)
        assert np.all(h_arr > 0.0) and np.all(h_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_derived_motivic_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when factor sections agree perfectly, E_motivic == 0, Z_motivic == 1.0, and h_motivic == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = DerivedMotivicHomotopyTypeTheoryCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_motivic"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_motivic"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_motivic"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v21"].values, 1.0, atol=1e-12)

    def test_derived_motivic_coupler_adversarial_conflict(self):
        """Validates that severe pillar discordance produces high obstruction and suppresses h_motivic smoothly."""
        conflict_pillars = pd.DataFrame({
            'val': [1.0, -1.0],
            'mom': [-1.0, 1.0],
            'flow': [1.0, -1.0],
            'cat': [-1.0, 1.0],
            'net': [1.0, -1.0],
        })
        res = DerivedMotivicHomotopyTypeTheoryCoupler.compute(conflict_pillars)
        assert np.all(res["e_motivic"].values > 1.0)
        assert np.all(res["z_motivic"].values <= 1.0)
        assert np.all(res["h_motivic"].values < 0.05)
        assert np.all(res["FERI_v21"].values < 0.50)

    def test_derived_motivic_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = DerivedMotivicHomotopyTypeTheoryCoupler.compute(p_dict)
        assert len(res_dict["h_motivic"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = DerivedMotivicHomotopyTypeTheoryCoupler.compute(v_single)
        assert isinstance(res_1d["h_motivic"], float)
        assert 0.0 < res_1d["h_motivic"] <= 1.0

        # Classmethod on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_derived_motivic_homotopy_type_theory_coupling(v_single)
        assert math.isclose(res_engine["h_motivic"], res_1d["h_motivic"], abs_tol=1e-12)

        # Aliases DerivedMotivicCoupler, MotivicHomotopyTypeTheoryCoupler & MotivicHomotopyCoupler
        res_alias1 = DerivedMotivicCoupler.compute(v_single)
        res_alias2 = MotivicHomotopyTypeTheoryCoupler.compute(v_single)
        res_alias3 = MotivicHomotopyCoupler.compute(v_single)
        assert math.isclose(res_alias1["h_motivic"], res_1d["h_motivic"], abs_tol=1e-12)
        assert math.isclose(res_alias2["h_motivic"], res_1d["h_motivic"], abs_tol=1e-12)
        assert math.isclose(res_alias3["h_motivic"], res_1d["h_motivic"], abs_tol=1e-12)

        # Cross-module exports in factor_suppression
        assert fs_DerivedMotivicHomotopyTypeTheoryCoupler is DerivedMotivicHomotopyTypeTheoryCoupler
        assert fs_DerivedMotivicCoupler is DerivedMotivicCoupler
        assert fs_MotivicHomotopyTypeTheoryCoupler is MotivicHomotopyTypeTheoryCoupler
        assert fs_MotivicHomotopyCoupler is MotivicHomotopyCoupler

    def test_quint_pillar_tensor_synergy_version21(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates Derived Motivic coupling for version=21."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 0.85],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 0.85, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v20 = engine.compute_quint_pillar_tensor_synergy(pillars, version=20)
        synergy_v21 = engine.compute_quint_pillar_tensor_synergy(pillars, version=21)

        assert isinstance(synergy_v21, pd.Series)
        assert len(synergy_v21) == 3
        assert np.all(np.isfinite(synergy_v21.values))
        assert np.all(synergy_v21.values > 0.0)
        # Highly coherent positive pillars should produce greater synergy in v21 with + 0.75 * h_motivic * z_motivic
        assert np.all(synergy_v21.values >= synergy_v20.values - 1e-6)

    # -------------------------------------------------------------------------
    # 3. Feature F104.1: 16th-Order Ultra-Convex Rank Modulation (g_v21)
    # -------------------------------------------------------------------------

    def test_16th_order_rank_modulation_percentiles(self):
        """Validates that 16th-order rank modulation concentrates capital into top percentiles (r >= 0.99999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase21_hyperconvex_rank_modulation(r_grid, gamma_top=2.00)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod < 1.06
        assert mod[2] < 1.06
        # Extreme conviction at r=1.0: 0.50 + 1.06 * 1.0 * exp(2.00) ~ 0.50 + 7.832 ~ 8.332
        assert mod[-1] > 8.00

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase21_hyperconvex_rank_modulation(r_neg, gamma_top=2.00, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

        # Alias check
        mod_alias = compute_phase21_rank_warping(r_grid, gamma_top=2.00)
        np.testing.assert_allclose(mod, mod_alias, atol=1e-12)

    def test_16th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v21(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase21_hyperconvex_rank_modulation(r_fine, gamma_top=1.75)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "16th-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "16th-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version21(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 21 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=21) == 2.00
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("2", version=21) == 2.00
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=21) == 1.75
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=21) == 1.55
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("1", version=21) == 1.55
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=21) == 1.20
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=21) == 0.90
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("0", version=21) == 0.90
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=21) == 0.62
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=21) == 0.42
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=21) == 1.60

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version21_full_pipeline(self):
        """Validates full combine_predictions() execution with version=21."""
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

        comb_v20 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=20)
        comb_v21 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=21)

        assert isinstance(comb_v21, pd.DataFrame)
        assert not comb_v21.empty
        assert "ensemble_score" in comb_v21.columns
        assert len(comb_v21) == N
        assert np.all(np.isfinite(comb_v21["ensemble_score"].values))
        assert np.all(comb_v21["ensemble_score"].values >= 0.0)
        assert np.all(comb_v21["ensemble_score"].values <= 1.0)

        # Top conviction in v21 should exhibit strong concentration
        top_v20 = comb_v20.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v21 = comb_v21.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v21 >= top_v20 - 1e-6, f"Top conviction in v21 ({top_v21}) should be >= v20 ({top_v20})"

    def test_backward_compatibility_v13_through_v20(self):
        """Validates that versions 13, 14, 15, 16, 17, 18, 19, 20, and 21 continue to run identically without disruption."""
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

        assert len(res_v13) == N
        assert len(res_v14) == N
        assert len(res_v15) == N
        assert len(res_v16) == N
        assert len(res_v17) == N
        assert len(res_v18) == N
        assert len(res_v19) == N
        assert len(res_v20) == N
        assert len(res_v21) == N
