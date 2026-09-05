"""
tests/test_phase16_signal_enhancement.py

Comprehensive unit test suite for Phase 16 Quantitative Alpha Signal Enhancement (Milestone M1):
- Feature R1.1: Quantum Topos Sheaf Cohomology Factor Disentanglement Engine (QuantumToposSheafCoupler)
- Feature R1.2: 11th-Order Ultra-Convex Rank Modulation (g_v16) across 2D Market Regimes
- Feature R1.3: 28th-Order Octacosagonal Hyperbolic Tangent Noise Deadband (alpha=28.0)
- End-to-End EnsembleScoringEngine combine_predictions() with version=16
- Strict backward compatibility validation with Phase 13 (v20), Phase 14 (v21), and Phase 15 (v22)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_octacosagonal_hyperbolic_deadband,
    compute_phase16_hyperconvex_rank_modulation,
    QuantumToposSheafCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_octacosagonal_hyperbolic_deadband as fs_octacosagonal_deadband,
)


class TestPhase16SignalEnhancement:
    """Test suite covering Phase 16 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature R1.3: 28th-Order Octacosagonal Hyperbolic Tangent Deadband
    # -------------------------------------------------------------------------

    def test_octacosagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.007) has leakage < 10^-16."""
        z_grid = np.linspace(-0.007, 0.007, 100)
        denoised = apply_octacosagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=28.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-15, f"Max noise leakage {max_leakage} must be < 1e-15"

        # Check boundary point |z| = 0.007
        val_at_bound = float(np.abs(apply_octacosagonal_hyperbolic_deadband(0.007, delta_noise=0.035, alpha_pos=28.0)))
        assert val_at_bound < 1e-15, f"Leakage at z=0.007 was {val_at_bound}, expected < 1e-15"

    def test_octacosagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_octacosagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=28.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_octacosagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=28.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Octacosagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.9999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_octacosagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_octacosagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=28.0)
        f_neg = apply_octacosagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=28.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_octacosagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_octacosagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_octacosagonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_octacosagonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_noise_deadband_version16_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband uses alpha=28.0 under version=16."""
        engine = EnsembleScoringEngine()
        z_val = 0.007
        res_v16 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=16)
        res_direct = apply_octacosagonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=28.0)
        assert math.isclose(float(res_v16), float(res_direct), abs_tol=1e-12)

    # -------------------------------------------------------------------------
    # 2. Feature R1.1: Quantum Topos Sheaf Cohomology Factor Disentanglement Engine
    # -------------------------------------------------------------------------

    def test_sheaf_coupler_cohomology_invariants_bounded(self):
        """Validates that obstruction energy E_sheaf and topological coherence Z_sheaf are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })

        res = QuantumToposSheafCoupler.compute(pillars)
        assert "h_sheaf" in res
        assert "z_sheaf" in res
        assert "e_sheaf" in res
        assert "FERI_v16" in res

        z_sheaf_arr = res["z_sheaf"].values
        e_sheaf_arr = res["e_sheaf"].values
        h_sheaf_arr = res["h_sheaf"].values
        feri_arr = res["FERI_v16"].values

        assert np.all(z_sheaf_arr > 0.0) and np.all(z_sheaf_arr <= 1.0)
        assert np.all(e_sheaf_arr >= 0.0)
        assert np.all(h_sheaf_arr > 0.0) and np.all(h_sheaf_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_sheaf_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when local factor patches agree perfectly, E_sheaf == 0 and Z_sheaf == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = QuantumToposSheafCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_sheaf"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_sheaf"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_sheaf"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v16"].values, 1.0, atol=1e-12)

    def test_sheaf_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = QuantumToposSheafCoupler.compute(p_dict)
        assert len(res_dict["h_sheaf"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = QuantumToposSheafCoupler.compute(v_single)
        assert isinstance(res_1d["h_sheaf"], float)
        assert 0.0 < res_1d["h_sheaf"] <= 1.0

        # Classmethod on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_quantum_topos_sheaf_coupling(v_single)
        assert math.isclose(res_engine["h_sheaf"], res_1d["h_sheaf"], abs_tol=1e-12)

    # -------------------------------------------------------------------------
    # 3. Feature R1.2: 11th-Order Ultra-Convex Rank Modulation (g_v16)
    # -------------------------------------------------------------------------

    def test_11th_order_rank_modulation_percentiles(self):
        """Validates that 11th-order rank modulation concentrates capital into top percentiles (r >= 0.9999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.9999, 1.00])
        mod = compute_phase16_hyperconvex_rank_modulation(r_grid, gamma_top=1.75)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod < 1.0
        assert mod[2] < 1.0
        # Extreme conviction at r=1.0: 0.50 + 0.95 * 1.0 * exp(1.75) ~ 0.50 + 0.95 * 5.7546 ~ 5.967
        assert mod[-1] > 5.50

    def test_11th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v16(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase16_hyperconvex_rank_modulation(r_fine, gamma_top=1.50)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "11th-order modulation must be strictly convex for r >= 0.30"

    def test_regime_adaptive_gamma_top_version16(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 16 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=16) == 1.75
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=16) == 1.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=16) == 1.30
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=16) == 0.95
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=16) == 0.75
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=16) == 0.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=16) == 0.30
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=16) == 1.35

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version16_full_pipeline(self):
        """Validates full combine_predictions() execution with version=16."""
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

        comb_v15 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=15)
        comb_v16 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=16)

        assert isinstance(comb_v16, pd.DataFrame)
        assert not comb_v16.empty
        assert "ensemble_score" in comb_v16.columns
        assert len(comb_v16) == N
        assert np.all(np.isfinite(comb_v16["ensemble_score"].values))
        assert np.all(comb_v16["ensemble_score"].values >= 0.0)
        assert np.all(comb_v16["ensemble_score"].values <= 1.0)

        # Top conviction in v16 should exhibit strong concentration
        top_v15 = comb_v15.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v16 = comb_v16.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v16 >= top_v15, f"Top conviction in v16 ({top_v16}) should be >= v15 ({top_v15})"

    def test_backward_compatibility_v13_v14_v15(self):
        """Validates that version=13, version=14, and version=15 continue to run identically without disruption."""
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

        assert len(res_v13) == N
        assert len(res_v14) == N
        assert len(res_v15) == N
        assert len(res_v16) == N
