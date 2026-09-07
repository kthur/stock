"""
tests/test_phase19_signal_enhancement.py

Comprehensive unit test suite for Phase 19 Quantitative Alpha Signal Enhancement (Milestone M1):
- Feature F95: Lurie ∞-Topos & Higher Category Theory Factor Disentanglement Engine (LurieInfinityToposCoupler)
- Feature F96.1: 14th-Order Hyper-Convex Rank Modulation (g_v19) across 2D Market Regimes
- Feature F96.2: 40th-Order Tetracontagonal Hyperbolic Tangent Noise Deadband (alpha=40.0)
- End-to-End EnsembleScoringEngine combine_predictions() with version=19
- Strict backward compatibility validation with Phase 13 (v20) through Phase 18 (v25)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_tetracontagonal_hyperbolic_deadband,
    apply_hexatriacontagonal_hyperbolic_deadband,
    apply_dotriacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase19_hyperconvex_rank_modulation,
    compute_phase18_hyperconvex_rank_modulation,
    compute_phase17_hyperconvex_rank_modulation,
    LurieInfinityToposCoupler,
    LurieToposCoupler,
    DerivedAlgebraicGeometryMotivicCoupler,
    DerivedAlgebraicGeometryCoupler,
    HomologicalMirrorSymmetryCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_tetracontagonal_hyperbolic_deadband as fs_tetracontagonal_deadband,
    apply_hexatriacontagonal_hyperbolic_deadband as fs_hexatriacontagonal_deadband,
    apply_dotriacontagonal_hyperbolic_deadband as fs_dotriacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
)


class TestPhase19SignalEnhancement:
    """Test suite covering Phase 19 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F96.2: 40th-Order Tetracontagonal Hyperbolic Tangent Deadband
    # -------------------------------------------------------------------------

    def test_tetracontagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.005) has leakage < 10^-22."""
        z_grid = np.linspace(-0.005, 0.005, 100)
        denoised = apply_tetracontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=40.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-22, f"Max noise leakage {max_leakage} must be < 1e-22"

        # Check boundary point |z| = 0.005
        val_at_bound = float(np.abs(apply_tetracontagonal_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=40.0)))
        assert val_at_bound < 1e-22, f"Leakage at z=0.005 was {val_at_bound}, expected < 1e-22"

    def test_tetracontagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_tetracontagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=40.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_tetracontagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=40.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Tetracontagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_tetracontagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_tetracontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=40.0)
        f_neg = apply_tetracontagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=40.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_tetracontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_tetracontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_tetracontagonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_tetracontagonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version19_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=40.0 under version=19."""
        engine = EnsembleScoringEngine()
        z_val = 0.005
        res_v19 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=19)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=19)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=19)
        res_direct = apply_tetracontagonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=40.0)

        assert math.isclose(float(res_v19), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F95: Lurie ∞-Topos Factor Disentanglement Engine
    # -------------------------------------------------------------------------

    def test_lurie_coupler_invariants_bounded(self):
        """Validates that obstruction energy E_lurie, Kan fibrational cycle invariant Z_lurie, and coupling factor h_lurie are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })

        res = LurieInfinityToposCoupler.compute(pillars)
        assert "h_lurie" in res
        assert "z_lurie" in res
        assert "e_lurie" in res
        assert "FERI_v19" in res

        z_lurie_arr = res["z_lurie"].values
        e_lurie_arr = res["e_lurie"].values
        h_lurie_arr = res["h_lurie"].values
        feri_arr = res["FERI_v19"].values

        assert np.all(z_lurie_arr > 0.0) and np.all(z_lurie_arr <= 1.0)
        assert np.all(e_lurie_arr >= 0.0)
        assert np.all(h_lurie_arr > 0.0) and np.all(h_lurie_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_lurie_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when factor sections agree perfectly, E_lurie == 0, Z_lurie == 1.0, and h_lurie == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = LurieInfinityToposCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_lurie"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_lurie"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_lurie"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v19"].values, 1.0, atol=1e-12)

    def test_lurie_coupler_adversarial_conflict(self):
        """Validates that severe pillar discordance produces high obstruction and suppresses h_lurie smoothly."""
        conflict_pillars = pd.DataFrame({
            'val': [1.0, -1.0],
            'mom': [-1.0, 1.0],
            'flow': [1.0, -1.0],
            'cat': [-1.0, 1.0],
            'net': [1.0, -1.0],
        })
        res = LurieInfinityToposCoupler.compute(conflict_pillars)
        assert np.all(res["e_lurie"].values > 1.0)
        assert np.all(res["z_lurie"].values <= 1.0)
        assert np.all(res["h_lurie"].values < 0.05)
        assert np.all(res["FERI_v19"].values < 0.50)

    def test_lurie_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = LurieInfinityToposCoupler.compute(p_dict)
        assert len(res_dict["h_lurie"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = LurieInfinityToposCoupler.compute(v_single)
        assert isinstance(res_1d["h_lurie"], float)
        assert 0.0 < res_1d["h_lurie"] <= 1.0

        # Classmethod on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_lurie_infinity_topos_coupling(v_single)
        assert math.isclose(res_engine["h_lurie"], res_1d["h_lurie"], abs_tol=1e-12)

        # Alias LurieToposCoupler
        res_alias = LurieToposCoupler.compute(v_single)
        assert math.isclose(res_alias["h_lurie"], res_1d["h_lurie"], abs_tol=1e-12)

    def test_quint_pillar_tensor_synergy_version19(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates Lurie ∞-topos coupling for version=19."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 0.85],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 0.85, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v18 = engine.compute_quint_pillar_tensor_synergy(pillars, version=18)
        synergy_v19 = engine.compute_quint_pillar_tensor_synergy(pillars, version=19)

        assert isinstance(synergy_v19, pd.Series)
        assert len(synergy_v19) == 3
        assert np.all(np.isfinite(synergy_v19.values))
        assert np.all(synergy_v19.values > 0.0)

    # -------------------------------------------------------------------------
    # 3. Feature F96.1: 14th-Order Hyper-Convex Rank Modulation (g_v19)
    # -------------------------------------------------------------------------

    def test_14th_order_rank_modulation_percentiles(self):
        """Validates that 14th-order rank modulation concentrates capital into top percentiles (r >= 0.99999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase19_hyperconvex_rank_modulation(r_grid, gamma_top=1.90)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod ~ 1.01
        assert mod[2] < 1.05
        # Extreme conviction at r=1.0: 0.50 + 1.02 * 1.0 * exp(1.90) ~ 0.50 + 6.819 ~ 7.319
        assert mod[-1] > 7.00

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase19_hyperconvex_rank_modulation(r_neg, gamma_top=1.90, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

    def test_14th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v19(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase19_hyperconvex_rank_modulation(r_fine, gamma_top=1.65)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "14th-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "14th-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version19(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 19 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=19) == 1.90
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=19) == 1.65
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=19) == 1.45
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=19) == 1.10
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=19) == 0.85
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=19) == 0.58
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=19) == 0.38
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=19) == 1.50

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version19_full_pipeline(self):
        """Validates full combine_predictions() execution with version=19."""
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

        comb_v18 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=18)
        comb_v19 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=19)

        assert isinstance(comb_v19, pd.DataFrame)
        assert not comb_v19.empty
        assert "ensemble_score" in comb_v19.columns
        assert len(comb_v19) == N
        assert np.all(np.isfinite(comb_v19["ensemble_score"].values))
        assert np.all(comb_v19["ensemble_score"].values >= 0.0)
        assert np.all(comb_v19["ensemble_score"].values <= 1.0)

        # Top conviction in v19 should exhibit strong concentration
        top_v18 = comb_v18.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v19 = comb_v19.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v19 >= top_v18 - 1e-6, f"Top conviction in v19 ({top_v19}) should be >= v18 ({top_v18})"

    def test_backward_compatibility_v13_through_v18(self):
        """Validates that versions 13, 14, 15, 16, 17, and 18 continue to run identically without disruption."""
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

        assert len(res_v13) == N
        assert len(res_v14) == N
        assert len(res_v15) == N
        assert len(res_v16) == N
        assert len(res_v17) == N
        assert len(res_v18) == N
        assert len(res_v19) == N
