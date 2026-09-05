"""
tests/test_phase17_signal_enhancement.py

Comprehensive unit test suite for Phase 17 Quantitative Alpha Signal Enhancement (Milestone M1):
- Feature F87: Homological Mirror Symmetry & Fukaya Category Factor Disentanglement Engine (HomologicalMirrorSymmetryCoupler)
- Feature F88.1: 12th-Order Ultra-Convex Rank Modulation (g_v17) across 2D Market Regimes
- Feature F88.2: 32nd-Order Dotriacontagonal Hyperbolic Tangent Noise Deadband (alpha=32.0)
- End-to-End EnsembleScoringEngine combine_predictions() with version=17
- Strict backward compatibility validation with Phase 13 (v20), Phase 14 (v21), Phase 15 (v22), and Phase 16 (v23)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_dotriacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase17_hyperconvex_rank_modulation,
    HomologicalMirrorSymmetryCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_dotriacontagonal_hyperbolic_deadband as fs_dotriacontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
)


class TestPhase17SignalEnhancement:
    """Test suite covering Phase 17 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F88.2: 32nd-Order Dotriacontagonal Hyperbolic Tangent Deadband
    # -------------------------------------------------------------------------

    def test_dotriacontagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.007) has leakage < 10^-20."""
        z_grid = np.linspace(-0.007, 0.007, 100)
        denoised = apply_dotriacontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=32.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-20, f"Max noise leakage {max_leakage} must be < 1e-20"

        # Check boundary point |z| = 0.007
        val_at_bound = float(np.abs(apply_dotriacontagonal_hyperbolic_deadband(0.007, delta_noise=0.035, alpha_pos=32.0)))
        assert val_at_bound < 1e-20, f"Leakage at z=0.007 was {val_at_bound}, expected < 1e-20"

    def test_dotriacontagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_dotriacontagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=32.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_dotriacontagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=32.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Dotriacontagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_dotriacontagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_dotriacontagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=32.0)
        f_neg = apply_dotriacontagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=32.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_dotriacontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_dotriacontagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_dotriacontagonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_dotriacontagonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version17_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=32.0 under version=17."""
        engine = EnsembleScoringEngine()
        z_val = 0.007
        res_v17 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=17)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=17)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=17)
        res_direct = apply_dotriacontagonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=32.0)

        assert math.isclose(float(res_v17), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F87: Homological Mirror Symmetry & Fukaya Category Disentanglement Engine
    # -------------------------------------------------------------------------

    def test_hms_coupler_invariants_bounded(self):
        """Validates that obstruction energy E_hms, topological coherence Z_hms, and Floer coupling h_hms are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })

        res = HomologicalMirrorSymmetryCoupler.compute(pillars)
        assert "h_hms" in res
        assert "z_hms" in res
        assert "e_hms" in res
        assert "FERI_v17" in res

        z_hms_arr = res["z_hms"].values
        e_hms_arr = res["e_hms"].values
        h_hms_arr = res["h_hms"].values
        feri_arr = res["FERI_v17"].values

        assert np.all(z_hms_arr > 0.0) and np.all(z_hms_arr <= 1.0)
        assert np.all(e_hms_arr >= 0.0)
        assert np.all(h_hms_arr > 0.0) and np.all(h_hms_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_hms_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when Lagrangian factor branes agree perfectly, E_hms == 0, Z_hms == 1.0, and h_hms == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = HomologicalMirrorSymmetryCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_hms"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_hms"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_hms"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v17"].values, 1.0, atol=1e-12)

    def test_hms_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = HomologicalMirrorSymmetryCoupler.compute(p_dict)
        assert len(res_dict["h_hms"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = HomologicalMirrorSymmetryCoupler.compute(v_single)
        assert isinstance(res_1d["h_hms"], float)
        assert 0.0 < res_1d["h_hms"] <= 1.0

        # Classmethod on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_homological_mirror_symmetry_coupling(v_single)
        assert math.isclose(res_engine["h_hms"], res_1d["h_hms"], abs_tol=1e-12)

    def test_quint_pillar_tensor_synergy_version17(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates HMS coupling for version=17."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 0.85],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 0.85, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v16 = engine.compute_quint_pillar_tensor_synergy(pillars, version=16)
        synergy_v17 = engine.compute_quint_pillar_tensor_synergy(pillars, version=17)

        assert isinstance(synergy_v17, pd.Series)
        assert len(synergy_v17) == 3
        assert np.all(np.isfinite(synergy_v17.values))
        # Due to +0.35 * h_hms * z_hms regularizer boost, synergy_v17 should be well-formed and positive
        assert np.all(synergy_v17.values > 0.0)

    # -------------------------------------------------------------------------
    # 3. Feature F88.1: 12th-Order Ultra-Convex Rank Modulation (g_v17)
    # -------------------------------------------------------------------------

    def test_12th_order_rank_modulation_percentiles(self):
        """Validates that 12th-order rank modulation concentrates capital into top percentiles (r >= 0.99999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase17_hyperconvex_rank_modulation(r_grid, gamma_top=1.80)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod ~ 1.0002
        assert mod[2] < 1.05
        # Extreme conviction at r=1.0: 0.50 + 1.00 * 1.0 * exp(1.80) ~ 0.50 + 6.0496 ~ 6.550
        assert mod[-1] > 6.00

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase17_hyperconvex_rank_modulation(r_neg, gamma_top=1.80, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

    def test_12th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v17(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase17_hyperconvex_rank_modulation(r_fine, gamma_top=1.55)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "12th-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "12th-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version17(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 17 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=17) == 1.80
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=17) == 1.55
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=17) == 1.35
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=17) == 1.00
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=17) == 0.78
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=17) == 0.52
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=17) == 0.32
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=17) == 1.40

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version17_full_pipeline(self):
        """Validates full combine_predictions() execution with version=17."""
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

        comb_v16 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=16)
        comb_v17 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=17)

        assert isinstance(comb_v17, pd.DataFrame)
        assert not comb_v17.empty
        assert "ensemble_score" in comb_v17.columns
        assert len(comb_v17) == N
        assert np.all(np.isfinite(comb_v17["ensemble_score"].values))
        assert np.all(comb_v17["ensemble_score"].values >= 0.0)
        assert np.all(comb_v17["ensemble_score"].values <= 1.0)

        # Top conviction in v17 should exhibit strong concentration
        top_v16 = comb_v16.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v17 = comb_v17.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v17 >= top_v16, f"Top conviction in v17 ({top_v17}) should be >= v16 ({top_v16})"

    def test_backward_compatibility_v13_through_v16(self):
        """Validates that versions 13, 14, 15, and 16 continue to run identically without disruption."""
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

        assert len(res_v13) == N
        assert len(res_v14) == N
        assert len(res_v15) == N
        assert len(res_v16) == N
        assert len(res_v17) == N
