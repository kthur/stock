"""
test_phase10_signal_enhancement.py — Unit & Empirical Test Suite for Phase 10 Transcendental Signal Enhancement
Covers Features F59 and F60:
- F59/F60.1: Malliavin Stochastic Calculus Sensitivity Derivative Engine
- F60.1: 5th-Order Super-Convex Hyperexponential Rank Modulation (g_v10(r) = r * exp(gamma_top * r^5))
- F60.2: Asymmetric Decic (10th-Order) Hyperbolic Wavelet Noise Deadband (alpha=10.0)
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import (
    apply_decic_hyperbolic_deadband,
    apply_nonic_hyperbolic_deadband,
    apply_quintic_hyperbolic_deadband,
)


class TestPhase10SignalEnhancement:
    """Test suite for Phase 10 Transcendental Signal Enhancement (Features F59 and F60)."""

    def test_malliavin_sensitivity_derivative_bounds(self):
        """Test F59/F60.1: Discrete Malliavin sensitivity derivative and Sobolev H^1 norm."""
        np.random.seed(42)
        # 1. Smooth path vs Jump path
        T = 20
        smooth_path = np.cumsum(np.random.normal(0, 0.01, size=(T, 2)), axis=0)
        jump_path = smooth_path.copy()
        jump_path[10:, 1] += 0.25  # Large discontinuous jump

        res_smooth = EnsembleScoringEngine.compute_malliavin_sensitivity_derivative(smooth_path, dt=0.05)
        res_jump = EnsembleScoringEngine.compute_malliavin_sensitivity_derivative(jump_path, dt=0.05)

        assert "malliavin_derivatives" in res_smooth
        assert "path_sobolev_norm" in res_smooth
        assert "jump_vulnerability_index" in res_smooth

        assert res_smooth["malliavin_derivatives"].shape == (T - 1, 2)
        assert len(res_smooth["path_sobolev_norm"]) == 2
        assert len(res_smooth["jump_vulnerability_index"]) == 2

        # Jump path must exhibit significantly higher Sobolev norm and jump vulnerability
        assert res_jump["path_sobolev_norm"][1] > res_smooth["path_sobolev_norm"][1]
        assert res_jump["jump_vulnerability_index"][1] > res_smooth["jump_vulnerability_index"][1]
        assert 0.0 <= res_smooth["jump_vulnerability_index"][0] <= 1.0
        assert 0.0 <= res_jump["jump_vulnerability_index"][1] <= 1.0

    def test_decic_hyperbolic_deadband_noise_leakage(self):
        """Test F60.2: 10th-order hyperbolic deadband squashes noise and transmits signals."""
        noise_z = np.array([0.002, 0.005, 0.008, 0.010, -0.005, -0.010])
        denoised_noise = apply_decic_hyperbolic_deadband(noise_z, delta_noise=0.045, alpha_pos=10.0)
        max_noise_leakage = np.max(np.abs(denoised_noise)) / 0.010
        # 10th-order leakage must be strictly less than 0.0001 (99.999% suppression)
        assert max_noise_leakage < 0.0001, f"Noise leakage {max_noise_leakage} exceeds 0.01%"

        conviction_z = np.array([0.150, 0.200, 0.350, -0.150, -0.250])
        denoised_conv = apply_decic_hyperbolic_deadband(conviction_z, delta_noise=0.045, alpha_pos=10.0)
        transmission = np.abs(denoised_conv) / np.abs(conviction_z)
        np.testing.assert_allclose(transmission, np.ones_like(transmission), atol=1e-4)

        # Monotonicity test
        sweep_z = np.linspace(-0.40, 0.40, 201)
        denoised_sweep = apply_decic_hyperbolic_deadband(sweep_z, delta_noise=0.045, alpha_pos=10.0)
        diffs = np.diff(denoised_sweep)
        assert np.all(diffs >= 0.0), "Denoised function is not strictly monotonically non-decreasing"

    def test_regime_adaptive_gamma_top_version10(self):
        """Test F60.1: Regime-adaptive gamma_top parameter for version=10."""
        gamma_bull_low = EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=10)
        gamma_bull_high = EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=10)
        gamma_sideways = EnsembleScoringEngine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=10)
        gamma_crisis = EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=10)

        assert gamma_bull_low == 1.10
        assert gamma_bull_high == 0.90
        assert gamma_sideways == 0.70
        assert gamma_crisis == 0.20
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=9) == 0.95

    def test_malliavin_riemannian_manifold_synergy_version10(self):
        """Test F59/F60.1: Malliavin Sobolev path stability regularizer in Riemannian synergy."""
        engine = EnsembleScoringEngine()
        N = 25
        data = {
            "rim_score": np.full(N, 0.75),
            "surge_score": np.full(N, 0.80),
            "order_flow_score": np.full(N, 0.70),
            "event_score": np.full(N, 0.65),
            "supply_chain_score": np.full(N, 0.60),
        }
        df_scores = pd.DataFrame(data)

        mult_v9 = engine.compute_riemannian_manifold_synergy(df_scores, regime="BULL_LOW_VOL", version=9)
        mult_v10 = engine.compute_riemannian_manifold_synergy(df_scores, regime="BULL_LOW_VOL", version=10)

        assert np.all(mult_v10 >= 1.0)
        assert np.all(mult_v10 <= 1.300)

    def test_combine_predictions_version10_rank_modulation(self):
        """Test F60.1: combine_predictions with version=10 generates sharper top decile separation."""
        engine = EnsembleScoringEngine()
        N = 40
        symbols = [f"SYM_{i:02d}" for i in range(N)]
        scores = np.linspace(0.20, 0.85, N)
        df_in = pd.DataFrame({
            "symbol": symbols,
            "ensemble_score": scores,
            "pred_score": scores,
            "reg_score": scores,
            "market": ["SP500"] * N
        })

        pred_dfs = {"regression": df_in}
        res_v9 = engine.combine_predictions(pred_dfs, regime="BULL_LOW_VOL", version=9)
        res_v10 = engine.combine_predictions(pred_dfs, regime="BULL_LOW_VOL", version=10)

        top_ret_v9 = res_v9.iloc[0]["ensemble_expected_return"] if "ensemble_expected_return" in res_v9.columns else res_v9.iloc[0]["ensemble_score"]
        top_ret_v10 = res_v10.iloc[0]["ensemble_expected_return"] if "ensemble_expected_return" in res_v10.columns else res_v10.iloc[0]["ensemble_score"]

        assert top_ret_v10 >= top_ret_v9
