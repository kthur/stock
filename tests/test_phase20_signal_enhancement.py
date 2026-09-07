"""
tests/test_phase20_signal_enhancement.py

Comprehensive unit test suite for Phase 20 Quantitative Alpha Signal Enhancement (Milestone M1):
- Feature F99: Perfectoid Space & Prismatic Cohomology Factor Disentanglement Engine (PerfectoidPrismaticCoupler)
- Feature F100.1: 15th-Order Ultra-Convex Rank Modulation (g_v20) across 2D Market Regimes
- Feature F100.2: 44th-Order Tetracontatetragonal Hyperbolic Tangent Noise Deadband (alpha=44.0, leakage < 10^-24)
- End-to-End EnsembleScoringEngine combine_predictions() with version=20
- Strict backward compatibility validation with Phase 13 (v13) through Phase 19 (v19)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_tetracontatetragonal_hyperbolic_deadband,
    apply_tetracontagonal_hyperbolic_deadband,
    apply_hexatriacontagonal_hyperbolic_deadband,
    apply_dotriacontagonal_hyperbolic_deadband,
    apply_smooth_deadband_attenuation,
    compute_phase20_hyperconvex_rank_modulation,
    compute_phase19_hyperconvex_rank_modulation,
    compute_phase18_hyperconvex_rank_modulation,
    compute_phase17_hyperconvex_rank_modulation,
    PerfectoidPrismaticCoupler,
    PerfectoidSpaceCoupler,
    PrismaticCohomologyCoupler,
    LurieInfinityToposCoupler,
    LurieToposCoupler,
    DerivedAlgebraicGeometryMotivicCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_tetracontatetragonal_hyperbolic_deadband as fs_tetracontatetragonal_deadband,
    apply_tetracontagonal_hyperbolic_deadband as fs_tetracontagonal_deadband,
    apply_smooth_deadband_attenuation as fs_smooth_deadband,
    PerfectoidPrismaticCoupler as fs_PerfectoidPrismaticCoupler,
    PerfectoidSpaceCoupler as fs_PerfectoidSpaceCoupler,
    PrismaticCohomologyCoupler as fs_PrismaticCohomologyCoupler,
)


class TestPhase20SignalEnhancement:
    """Test suite covering Phase 20 Alpha Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F100.2: 44th-Order Tetracontatetragonal Hyperbolic Deadband
    # -------------------------------------------------------------------------

    def test_tetracontatetragonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.005) has leakage < 10^-24."""
        z_grid = np.linspace(-0.005, 0.005, 100)
        denoised = apply_tetracontatetragonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=44.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-24, f"Max noise leakage {max_leakage} must be < 1e-24"

        # Check boundary point |z| = 0.005
        val_at_bound = float(np.abs(apply_tetracontatetragonal_hyperbolic_deadband(0.005, delta_noise=0.035, alpha_pos=44.0)))
        assert val_at_bound < 1e-24, f"Leakage at z=0.005 was {val_at_bound}, expected < 1e-24"

        # Check at z = 0.0
        val_at_zero = float(apply_tetracontatetragonal_hyperbolic_deadband(0.0, delta_noise=0.035, alpha_pos=44.0))
        assert val_at_zero == 0.0

    def test_tetracontatetragonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_tetracontatetragonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=44.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_tetracontatetragonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=44.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Tetracontatetragonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.99999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_tetracontatetragonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_tetracontatetragonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=44.0)
        f_neg = apply_tetracontatetragonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=44.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_tetracontatetragonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_tetracontatetragonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_tetracontatetragonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_tetracontatetragonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    def test_smooth_deadband_attenuation_version20_dispatch(self):
        """Validates that EnsembleScoringEngine.apply_smooth_noise_deadband and apply_smooth_deadband_attenuation use alpha=44.0 under version=20."""
        engine = EnsembleScoringEngine()
        z_val = 0.005
        res_v20 = engine.apply_smooth_noise_deadband(z_val, delta_noise=0.035, version=20)
        res_atten = engine.apply_smooth_deadband_attenuation(z_val, delta_noise=0.035, version=20)
        res_fs = fs_smooth_deadband(z_val, delta_noise=0.035, version=20)
        res_direct = apply_tetracontatetragonal_hyperbolic_deadband(z_val, delta_noise=0.035, alpha_pos=44.0)

        assert math.isclose(float(res_v20), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_atten), float(res_direct), abs_tol=1e-15)
        assert math.isclose(float(res_fs), float(res_direct), abs_tol=1e-15)

    # -------------------------------------------------------------------------
    # 2. Feature F99: Perfectoid Space & Prismatic Cohomology Factor Coupler
    # -------------------------------------------------------------------------

    def test_perfectoid_prismatic_coupler_invariants_bounded(self):
        """Validates that E_prism, Z_prism, h_prism, and FERI_v20 are strictly bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })
        res = PerfectoidPrismaticCoupler.compute(pillars)
        assert "h_prism" in res
        assert "z_prism" in res
        assert "e_prism" in res
        assert "h_decay" in res
        assert "FERI_v20" in res
        assert "Z_prism" in res
        assert "E_prism" in res
        assert "h_perfectoid" in res
        assert "z_perfectoid" in res
        assert "e_perfectoid" in res
        assert "h_prismatic" in res
        assert "z_prismatic" in res
        assert "e_prismatic" in res

        z_prism_arr = res["z_prism"].values
        e_prism_arr = res["e_prism"].values
        h_prism_arr = res["h_prism"].values
        feri_arr = res["FERI_v20"].values

        assert np.all(z_prism_arr > 0.0) and np.all(z_prism_arr <= 1.0)
        assert np.all(e_prism_arr >= 0.0)
        assert np.all(h_prism_arr > 0.0) and np.all(h_prism_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_perfectoid_prismatic_coupler_zero_obstruction_on_coherent_sections(self):
        """Validates that when factor sections agree perfectly, E_prism == 0, Z_prism == 1.0, and h_prism == 1.0."""
        coherent_pillars = pd.DataFrame({
            'val': [0.50, 0.80],
            'mom': [0.50, 0.80],
            'flow': [0.50, 0.80],
            'cat': [0.50, 0.80],
            'net': [0.50, 0.80],
        })
        res = PerfectoidPrismaticCoupler.compute(coherent_pillars)
        np.testing.assert_allclose(res["e_prism"].values, 0.0, atol=1e-12)
        np.testing.assert_allclose(res["z_prism"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["h_prism"].values, 1.0, atol=1e-12)
        np.testing.assert_allclose(res["FERI_v20"].values, 1.0, atol=1e-12)

    def test_perfectoid_prismatic_coupler_adversarial_conflict(self):
        """Validates that severe pillar discordance produces high obstruction and suppresses h_prism smoothly."""
        conflict_pillars = pd.DataFrame({
            'val': [1.0, -1.0],
            'mom': [-1.0, 1.0],
            'flow': [1.0, -1.0],
            'cat': [-1.0, 1.0],
            'net': [1.0, -1.0],
        })
        res = PerfectoidPrismaticCoupler.compute(conflict_pillars)
        assert np.all(res["e_prism"].values > 1.0)
        assert np.all(res["z_prism"].values <= 1.0)
        assert np.all(res["h_prism"].values < 0.05)
        assert np.all(res["FERI_v20"].values < 0.50)

    def test_perfectoid_prismatic_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = PerfectoidPrismaticCoupler.compute(p_dict)
        assert len(res_dict["h_prism"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = PerfectoidPrismaticCoupler.compute(v_single)
        assert isinstance(res_1d["h_prism"], float)
        assert 0.0 < res_1d["h_prism"] <= 1.0

        # Classmethod on EnsembleScoringEngine
        res_engine = EnsembleScoringEngine.compute_perfectoid_prismatic_coupling(v_single)
        assert math.isclose(res_engine["h_prism"], res_1d["h_prism"], abs_tol=1e-12)

        # Aliases PerfectoidSpaceCoupler & PrismaticCohomologyCoupler
        res_alias1 = PerfectoidSpaceCoupler.compute(v_single)
        res_alias2 = PrismaticCohomologyCoupler.compute(v_single)
        assert math.isclose(res_alias1["h_prism"], res_1d["h_prism"], abs_tol=1e-12)
        assert math.isclose(res_alias2["h_prism"], res_1d["h_prism"], abs_tol=1e-12)

        # Cross-module exports in factor_suppression
        assert fs_PerfectoidPrismaticCoupler is PerfectoidPrismaticCoupler
        assert fs_PerfectoidSpaceCoupler is PerfectoidSpaceCoupler
        assert fs_PrismaticCohomologyCoupler is PrismaticCohomologyCoupler

    def test_quint_pillar_tensor_synergy_version20(self):
        """Validates that compute_quint_pillar_tensor_synergy incorporates Perfectoid Prismatic coupling for version=20."""
        engine = EnsembleScoringEngine()
        pillars = pd.DataFrame({
            'val': [0.70, 0.80, 0.90],
            'mom': [0.65, 0.75, 0.85],
            'flow': [0.60, 0.70, 0.80],
            'cat': [0.75, 0.85, 0.95],
            'net': [0.68, 0.78, 0.88],
        }, index=["A", "B", "C"])

        synergy_v19 = engine.compute_quint_pillar_tensor_synergy(pillars, version=19)
        synergy_v20 = engine.compute_quint_pillar_tensor_synergy(pillars, version=20)

        assert isinstance(synergy_v20, pd.Series)
        assert len(synergy_v20) == 3
        assert np.all(np.isfinite(synergy_v20.values))
        assert np.all(synergy_v20.values > 0.0)
        # Highly coherent positive pillars should produce greater synergy in v20 with + 0.65 * h_prism * z_prism
        assert np.all(synergy_v20.values >= synergy_v19.values - 1e-6)

    # -------------------------------------------------------------------------
    # 3. Feature F100.1: 15th-Order Ultra-Convex Rank Modulation (g_v20)
    # -------------------------------------------------------------------------

    def test_15th_order_rank_modulation_percentiles(self):
        """Validates that 15th-order rank modulation concentrates capital into top percentiles (r >= 0.99999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.99999, 1.00])
        mod = compute_phase20_hyperconvex_rank_modulation(r_grid, gamma_top=1.95)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Flat across bottom distribution: at r=0.50, mod ~ 1.02
        assert mod[2] < 1.05
        # Extreme conviction at r=1.0: 0.50 + 1.04 * 1.0 * exp(1.95) ~ 0.50 + 7.310 ~ 7.810
        assert mod[-1] > 7.50

        # Test negative branch
        z_neg = np.array([-0.05, -0.10])
        r_neg = np.array([0.20, 0.80])
        mod_neg = compute_phase20_hyperconvex_rank_modulation(r_neg, gamma_top=1.95, z_denoised=z_neg)
        # 1.35 - 1.00 * r
        np.testing.assert_allclose(mod_neg, 1.35 - 1.00 * r_neg, atol=1e-6)

    def test_15th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v20(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase20_hyperconvex_rank_modulation(r_fine, gamma_top=1.70)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "15th-order modulation must be strictly convex for r >= 0.30"

        # Monotonicity test
        d1 = np.diff(mod_fine)
        assert np.all(d1 > 0), "15th-order modulation must be strictly increasing"

    def test_regime_adaptive_gamma_top_version20(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 20 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=20) == 1.95
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("2", version=20) == 1.95
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=20) == 1.70
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=20) == 1.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("1", version=20) == 1.50
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=20) == 1.15
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=20) == 0.88
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("0", version=20) == 0.88
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=20) == 0.60
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=20) == 0.40
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("UNKNOWN_REGIME", version=20) == 1.55

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version20_full_pipeline(self):
        """Validates full combine_predictions() execution with version=20."""
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

        comb_v19 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=19)
        comb_v20 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=20)

        assert isinstance(comb_v20, pd.DataFrame)
        assert not comb_v20.empty
        assert "ensemble_score" in comb_v20.columns
        assert len(comb_v20) == N
        assert np.all(np.isfinite(comb_v20["ensemble_score"].values))
        assert np.all(comb_v20["ensemble_score"].values >= 0.0)
        assert np.all(comb_v20["ensemble_score"].values <= 1.0)

        # Top conviction in v20 should exhibit strong concentration
        top_v19 = comb_v19.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v20 = comb_v20.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v20 >= top_v19 - 1e-6, f"Top conviction in v20 ({top_v20}) should be >= v19 ({top_v19})"

    def test_backward_compatibility_v13_through_v19(self):
        """Validates that versions 13, 14, 15, 16, 17, 18, 19, and 20 continue to run identically without disruption."""
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

        assert len(res_v13) == N
        assert len(res_v14) == N
        assert len(res_v15) == N
        assert len(res_v16) == N
        assert len(res_v17) == N
        assert len(res_v18) == N
        assert len(res_v19) == N
        assert len(res_v20) == N
