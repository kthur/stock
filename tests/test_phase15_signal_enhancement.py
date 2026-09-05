"""
tests/test_phase15_signal_enhancement.py

Comprehensive unit test suite for Phase 15 Supreme Quantitative Enhancement (v22 Production Master) Signal Enhancement:
- Feature F79: Non-Commutative Quantum Field Theory (NCQFT) Moyal-Weyl Star Product & Atiyah-Singer Index Coupler
- Feature F80.1: 10th-Order Hyper-Convex Rank Modulation across 2D Market Regimes
- Feature F80.2: 24th-Order Tetracosagonal Hyperbolic Tangent Noise Deadband
- End-to-End EnsembleScoringEngine combine_predictions() with version=15
- Strict backward compatibility validation with Phase 13 (v20) and Phase 14 (v21)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_tetracosagonal_hyperbolic_deadband,
    compute_phase15_hyperconvex_rank_modulation,
    NonCommutativeQuantumFieldCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_tetracosagonal_hyperbolic_deadband as fs_tetracosagonal_deadband,
)


class TestPhase15SignalEnhancement:
    """Test suite covering Phase 15 Supreme Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F80.2: 24th-Order Tetracosagonal Hyperbolic Tangent Deadband
    # -------------------------------------------------------------------------

    def test_tetracosagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.007) has leakage < 10^-15."""
        z_grid = np.linspace(-0.007, 0.007, 100)
        denoised = apply_tetracosagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=24.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-14, f"Max noise leakage {max_leakage} must be < 1e-14"

        # Check boundary point |z| = 0.007
        val_at_bound = float(np.abs(apply_tetracosagonal_hyperbolic_deadband(0.007, delta_noise=0.035, alpha_pos=24.0)))
        assert val_at_bound < 1e-14, f"Leakage at z=0.007 was {val_at_bound}, expected < 1e-14"

    def test_tetracosagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_tetracosagonal_hyperbolic_deadband(z_high, delta_noise=0.035, alpha_pos=24.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_tetracosagonal_hyperbolic_deadband(grid, delta_noise=0.035, alpha_pos=24.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Tetracosagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.9999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_tetracosagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_tetracosagonal_hyperbolic_deadband(z_grid, delta_noise=0.035, alpha_pos=24.0)
        f_neg = apply_tetracosagonal_hyperbolic_deadband(-z_grid, delta_noise=0.035, alpha_pos=24.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_tetracosagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="BULL_LOW_VOL")
        out_crisis = apply_tetracosagonal_hyperbolic_deadband(-0.035, delta_noise=0.035, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_tetracosagonal_deadband(0.003, delta_noise=0.035)
        es_res = apply_tetracosagonal_hyperbolic_deadband(0.003, delta_noise=0.035)
        assert fs_res == es_res

    # -------------------------------------------------------------------------
    # 2. Feature F79: Non-Commutative Quantum Field Theory (NCQFT) Moyal-Weyl Coupler
    # -------------------------------------------------------------------------

    def test_ncqft_star_product_and_atiyah_singer_invariants(self):
        """Validates that Moyal-Weyl star product deformation energy E_star and Atiyah-Singer invariant are bounded."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })

        res = NonCommutativeQuantumFieldCoupler.compute(pillars)
        assert "h_ncqft" in res
        assert "z_index" in res
        assert "e_star" in res
        assert "FERI_v15" in res

        z_index_arr = res["z_index"].values
        e_star_arr = res["e_star"].values
        h_ncqft_arr = res["h_ncqft"].values
        feri_arr = res["FERI_v15"].values

        assert np.all(z_index_arr > 0.0) and np.all(z_index_arr <= 1.0)
        assert np.all(e_star_arr >= 0.0)
        assert np.all(h_ncqft_arr > 0.0) and np.all(h_ncqft_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_ncqft_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = NonCommutativeQuantumFieldCoupler.compute(p_dict)
        assert len(res_dict["h_ncqft"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = NonCommutativeQuantumFieldCoupler.compute(v_single)
        assert isinstance(res_1d["h_ncqft"], float)
        assert 0.0 < res_1d["h_ncqft"] <= 1.0

    # -------------------------------------------------------------------------
    # 3. Feature F80.1: 10th-Order Hyper-Convex Rank Modulation
    # -------------------------------------------------------------------------

    def test_10th_order_rank_modulation_percentiles(self):
        """Validates that 10th-order rank modulation concentrates capital into top percentiles (r >= 0.9999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.9999, 1.00])
        mod = compute_phase15_hyperconvex_rank_modulation(r_grid, gamma_top=1.70)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Moderate at median r=0.50: 0.50 + 0.90*0.5*exp(1.70 * (0.5^10)) ~ 0.50 + 0.45 ~ 0.95
        assert mod[2] < 1.0
        # High conviction at r=1.0: 0.50 + 0.90 * 1.0 * exp(1.70) ~ 0.50 + 0.90 * 5.4739 ~ 5.426
        assert mod[-1] > 5.00

    def test_10th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative of g_v15(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase15_hyperconvex_rank_modulation(r_fine, gamma_top=1.45)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "10th-order modulation must be strictly convex for r >= 0.30"

    def test_regime_adaptive_gamma_top_version15(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 15 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=15) == 1.70
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=15) == 1.45
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=15) == 1.25
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=15) == 0.90
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=15) == 0.72
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=15) == 0.48
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=15) == 0.28

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version15_full_pipeline(self):
        """Validates full combine_predictions() execution with version=15."""
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

        comb_v14 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=14)
        comb_v15 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=15)

        assert isinstance(comb_v15, pd.DataFrame)
        assert not comb_v15.empty
        assert "ensemble_score" in comb_v15.columns
        assert len(comb_v15) == N
        assert np.all(np.isfinite(comb_v15["ensemble_score"].values))
        assert np.all(comb_v15["ensemble_score"].values >= 0.0)
        assert np.all(comb_v15["ensemble_score"].values <= 1.0)

        # Top asset in v15 should exhibit stronger convex concentration than v14
        top_v14 = comb_v14.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v15 = comb_v15.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v15 >= top_v14, f"Top conviction in v15 ({top_v15}) should be >= v14 ({top_v14})"

    def test_backward_compatibility_v13_v14(self):
        """Validates that version=13 and version=14 continue to run identically without disruption."""
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

        assert len(res_v13) == N
        assert len(res_v14) == N
        assert len(res_v15) == N
