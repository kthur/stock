"""
tests/test_phase14_signal_enhancement.py

Comprehensive unit test suite for Phase 14 Omnipotent (v21 Production Master) Signal Enhancement:
- Feature F75: Holographic AdS/CFT Bulk-to-Boundary Duality & Non-Hermitian PT-Symmetric Topological Coupler
- Feature F76.1: 9th-Order Hyper-Convex Rank Modulation across 2D Market Regimes
- Feature F76.2: 20th-Order Icosagonal Hyperbolic Tangent Noise Deadband
- End-to-End EnsembleScoringEngine combine_predictions() with version=14
- Strict backward compatibility validation with Phase 12 (v19) and Phase 13 (v20)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_icosagonal_hyperbolic_deadband,
    compute_phase14_hyperconvex_rank_modulation,
    HolographicAdSCFTCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_icosagonal_hyperbolic_deadband as fs_icosagonal_deadband,
)


class TestPhase14SignalEnhancement:
    """Test suite covering Phase 14 Omnipotent Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F76.2: 20th-Order Icosagonal Hyperbolic Tangent Deadband
    # -------------------------------------------------------------------------

    def test_icosagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.008) has leakage < 10^-12."""
        z_grid = np.linspace(-0.008, 0.008, 100)
        denoised = apply_icosagonal_hyperbolic_deadband(z_grid, delta_noise=0.038, alpha_pos=20.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-12, f"Max noise leakage {max_leakage} must be < 1e-12"

        # Check boundary point |z| = 0.008
        val_at_bound = float(np.abs(apply_icosagonal_hyperbolic_deadband(0.008, delta_noise=0.038, alpha_pos=20.0)))
        assert val_at_bound < 1e-12, f"Leakage at z=0.008 was {val_at_bound}, expected < 1e-12"

    def test_icosagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_icosagonal_hyperbolic_deadband(z_high, delta_noise=0.038, alpha_pos=20.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_icosagonal_hyperbolic_deadband(grid, delta_noise=0.038, alpha_pos=20.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Icosagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.9999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_icosagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_icosagonal_hyperbolic_deadband(z_grid, delta_noise=0.038, alpha_pos=20.0)
        f_neg = apply_icosagonal_hyperbolic_deadband(-z_grid, delta_noise=0.038, alpha_pos=20.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_icosagonal_hyperbolic_deadband(-0.038, delta_noise=0.038, regime="BULL_LOW_VOL")
        out_crisis = apply_icosagonal_hyperbolic_deadband(-0.038, delta_noise=0.038, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_icosagonal_deadband(0.004, delta_noise=0.038)
        es_res = apply_icosagonal_hyperbolic_deadband(0.004, delta_noise=0.038)
        assert fs_res == es_res

    # -------------------------------------------------------------------------
    # 2. Feature F75: Holographic AdS/CFT Bulk-to-Boundary & PT-Symmetric Coupler
    # -------------------------------------------------------------------------

    def test_adscft_bulk_radial_and_topological_invariants(self):
        """Validates that bulk radial coordinate z0 and topological invariant Z_topo are strictly bounded in (0, 1]."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.65, 0.25, 0.75],
            'cat': [0.55, 0.15, 0.90],
            'net': [0.50, 0.10, 0.70],
        })

        res = HolographicAdSCFTCoupler.compute(pillars)
        assert "h_holo" in res
        assert "z_topo" in res
        assert "r_ads" in res
        assert "FERI_v14" in res
        assert "z0_bulk" in res

        z0_arr = res["z0_bulk"].values
        z_topo_arr = res["z_topo"].values
        h_holo_arr = res["h_holo"].values
        feri_arr = res["FERI_v14"].values

        assert np.all(z0_arr > 0.0) and np.all(z0_arr <= 1.0)
        assert np.all(z_topo_arr > 0.0) and np.all(z_topo_arr <= 1.0)
        assert np.all(h_holo_arr > 0.0) and np.all(h_holo_arr <= 1.0)
        assert np.all(feri_arr > 0.0) and np.all(feri_arr <= 1.0)

    def test_adscft_coupler_input_formats(self):
        """Validates that DataFrame, Dict, 2D array, and 1D vector formats work seamlessly."""
        p_dict = {
            'val': np.array([0.5, 0.8]),
            'mom': np.array([0.6, 0.9]),
            'flow': np.array([0.4, 0.7]),
            'cat': np.array([0.3, 0.85]),
            'net': np.array([0.5, 0.75]),
        }
        res_dict = HolographicAdSCFTCoupler.compute(p_dict)
        assert len(res_dict["h_holo"]) == 2

        # 1D single vector input
        v_single = np.array([0.5, 0.6, 0.4, 0.3, 0.5])
        res_1d = HolographicAdSCFTCoupler.compute(v_single)
        assert isinstance(res_1d["h_holo"], float)
        assert 0.0 < res_1d["h_holo"] <= 1.0

    # -------------------------------------------------------------------------
    # 3. Feature F76.1: 9th-Order Hyper-Convex Rank Modulation
    # -------------------------------------------------------------------------

    def test_9th_order_rank_modulation_percentiles(self):
        """Validates that 9th-order rank modulation concentrates capital into top percentiles (r >= 0.9999)."""
        r_grid = np.array([0.0, 0.20, 0.50, 0.80, 0.95, 0.99, 0.999, 0.9999, 1.00])
        mod = compute_phase14_hyperconvex_rank_modulation(r_grid, gamma_top=1.65)

        # Baseline at r=0 is 0.50
        assert math.isclose(mod[0], 0.50, abs_tol=1e-5)
        # Moderate at median r=0.50: 0.50 + 0.85*0.5*exp(1.65 * (0.5^9)) ~ 0.50 + 0.425 ~ 0.926
        assert mod[2] < 1.0
        # High conviction at r=1.0: 0.50 + 0.85 * 1.0 * exp(1.65) ~ 0.50 + 0.85 * 5.20698 ~ 4.925
        assert mod[-1] > 4.50

    def test_9th_order_rank_modulation_strict_convexity(self):
        """Validates that the second derivative (discrete second difference) of g_v14(r) is positive for r >= 0.30."""
        r_fine = np.linspace(0.30, 1.00, 1000)
        mod_fine = compute_phase14_hyperconvex_rank_modulation(r_fine, gamma_top=1.40)
        d2 = np.diff(mod_fine, n=2)
        assert np.all(d2 >= -1e-7), "9th-order modulation must be strictly convex for r >= 0.30"

    def test_regime_adaptive_gamma_top_version14(self):
        """Validates that EnsembleScoringEngine.get_regime_adaptive_gamma_top correctly returns Phase 14 parameters."""
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=14) == 1.65
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=14) == 1.40
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=14) == 1.20
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_HIGH_VOL", version=14) == 0.85
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_LOW_VOL", version=14) == 0.68
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BEAR_HIGH_VOL", version=14) == 0.45
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=14) == 0.25

    # -------------------------------------------------------------------------
    # 4. End-to-End Combine Predictions & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_combine_predictions_version14_full_pipeline(self):
        """Validates full combine_predictions() execution with version=14."""
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

        comb_v13 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=13)
        comb_v14 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=14)

        assert isinstance(comb_v14, pd.DataFrame)
        assert not comb_v14.empty
        assert "ensemble_score" in comb_v14.columns
        assert len(comb_v14) == N
        assert np.all(np.isfinite(comb_v14["ensemble_score"].values))
        assert np.all(comb_v14["ensemble_score"].values >= 0.0)
        assert np.all(comb_v14["ensemble_score"].values <= 1.0)

        # Top asset in v14 should exhibit stronger convex concentration than v13
        top_v13 = comb_v13.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v14 = comb_v14.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v14 >= top_v13, f"Top conviction in v14 ({top_v14}) should be >= v13 ({top_v13})"

    def test_backward_compatibility_v12_v13(self):
        """Validates that version=12 and version=13 continue to run identically without disruption."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v12 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=12)
        res_v13 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=13)
        res_v14 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=14)

        assert len(res_v12) == N
        assert len(res_v13) == N
        assert len(res_v14) == N
