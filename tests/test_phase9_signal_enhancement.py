"""
test_phase9_signal_enhancement.py — Unit & Empirical Test Suite for Phase 9 Imperial Signal Enhancement
Covers Features F55 and F56:
- F55.1: Symplectic Hamiltonian Energy-Conserving Momentum Dynamics
- F55.2: 4th-Order Super-Convex Hyperexponential Rank Modulation (g_v9(r) = r * exp(gamma_top * r^4))
- F56.1: Rough Path Signature Tensor Embedding
- F56.2: Asymmetric Nonic (9th-Order) Hyperbolic Wavelet Noise Deadband
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import (
    apply_nonic_hyperbolic_deadband,
    apply_quintic_hyperbolic_deadband,
    apply_asymmetric_wavelet_deadband,
)


class TestPhase9SignalEnhancement:
    """Test suite for Phase 9 Imperial Signal Enhancement (Features F55 and F56)."""

    def test_symplectic_hamiltonian_momentum_conservation(self):
        """Test F55.1: Symplectic Integrator preserves Hamiltonian energy."""
        q = np.array([0.20, 0.40, -0.30, 0.50])
        p = np.array([0.15, -0.25, 0.35, -0.45])

        res = EnsembleScoringEngine.compute_symplectic_hamiltonian_momentum(
            q_pos=q,
            p_mom=p,
            mass=1.0,
            stiffness=1.0,
            dt=0.05,
            steps=5
        )

        assert "q_symplectic" in res
        assert "p_symplectic" in res
        assert "hamiltonian_energy" in res
        assert "energy_conservation_ratio" in res

        assert 0.90 <= res["energy_conservation_ratio"] <= 1.10
        assert len(res["q_symplectic"]) == 4
        assert len(res["p_symplectic"]) == 4

    def test_rough_path_signature_tensor_embedding(self):
        """Test F56.1: Truncated Rough Path Signature of level 1 and 2."""
        np.random.seed(42)
        paths = np.cumsum(np.random.normal(0, 0.05, size=(10, 3)), axis=0)

        sig_l1 = EnsembleScoringEngine.compute_rough_path_signature_embedding(paths, level=1)
        assert len(sig_l1) == 3
        np.testing.assert_allclose(sig_l1, paths[-1] - paths[0], atol=1e-6)

        sig_l2 = EnsembleScoringEngine.compute_rough_path_signature_embedding(paths, level=2)
        assert len(sig_l2) == 12
        s2_matrix = sig_l2[3:].reshape(3, 3)
        assert not np.isclose(s2_matrix[0, 1], s2_matrix[1, 0])

    def test_nonic_hyperbolic_deadband_leakage_and_transmission(self):
        """Test F56.2: 9th-order hyperbolic deadband squashes noise and transmits signals."""
        noise_z = np.array([0.002, 0.005, 0.008, 0.010, -0.005, -0.010])
        denoised_noise = apply_nonic_hyperbolic_deadband(noise_z, delta_noise=0.045, alpha_pos=9.0)
        max_noise_leakage = np.max(np.abs(denoised_noise)) / 0.010
        assert max_noise_leakage < 0.001, f"Noise leakage {max_noise_leakage} exceeds 0.1%"

        conviction_z = np.array([0.150, 0.200, 0.350, -0.150, -0.250])
        denoised_conv = apply_nonic_hyperbolic_deadband(conviction_z, delta_noise=0.045, alpha_pos=9.0)
        transmission = np.abs(denoised_conv) / np.abs(conviction_z)
        np.testing.assert_allclose(transmission, np.ones_like(transmission), atol=1e-4)

        sweep_z = np.linspace(-0.40, 0.40, 201)
        denoised_sweep = apply_nonic_hyperbolic_deadband(sweep_z, delta_noise=0.045, alpha_pos=9.0)
        diffs = np.diff(denoised_sweep)
        assert np.all(diffs >= 0.0), "Denoised function is not strictly monotonically non-decreasing"

    def test_regime_adaptive_gamma_top_version9(self):
        """Test F55.2: Regime-adaptive gamma_top parameter for version=9."""
        gamma_bull_low = EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=9)
        gamma_bull_high = EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=9)
        gamma_crisis = EnsembleScoringEngine.get_regime_adaptive_gamma_top("CRISIS", version=9)

        assert gamma_bull_low == 0.95
        assert gamma_bull_high == 0.80
        assert gamma_crisis == 0.20
        assert EnsembleScoringEngine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=8) == 0.85

    def test_symplectic_riemannian_manifold_synergy_version9(self):
        """Test F55.1: Symplectic Hamiltonian Energy regularizer in Riemannian synergy."""
        engine = EnsembleScoringEngine()
        N = 20
        data = {
            "rim_score": np.full(N, 0.75),
            "surge_score": np.full(N, 0.80),
            "order_flow_score": np.full(N, 0.70),
            "event_score": np.full(N, 0.65),
            "supply_chain_score": np.full(N, 0.60),
        }
        df_scores = pd.DataFrame(data)

        mult_v8 = engine.compute_riemannian_manifold_synergy(df_scores, regime="BULL_LOW_VOL", version=8)
        mult_v9 = engine.compute_riemannian_manifold_synergy(df_scores, regime="BULL_LOW_VOL", version=9)

        assert np.all(mult_v9 >= mult_v8)
        assert np.all(mult_v9 <= 1.280)

    def test_combine_predictions_version9_rank_modulation(self):
        """Test F55.2: combine_predictions with version=9 generates sharper top decile separation."""
        engine = EnsembleScoringEngine()
        N = 30
        symbols = [f"SYM_{i:02d}" for i in range(N)]
        scores = np.linspace(0.20, 0.80, N)
        df_in = pd.DataFrame({
            "symbol": symbols,
            "ensemble_score": scores,
            "pred_score": scores,
            "reg_score": scores,
            "market": ["SP500"] * N
        })

        pred_dfs = {"regression": df_in}
        res_v8 = engine.combine_predictions(pred_dfs, regime="BULL_LOW_VOL", version=8)
        res_v9 = engine.combine_predictions(pred_dfs, regime="BULL_LOW_VOL", version=9)

        top_ret_v8 = res_v8.iloc[0]["ensemble_expected_return"] if "ensemble_expected_return" in res_v8.columns else res_v8.iloc[0]["ensemble_score"]
        top_ret_v9 = res_v9.iloc[0]["ensemble_expected_return"] if "ensemble_expected_return" in res_v9.columns else res_v9.iloc[0]["ensemble_score"]

        assert top_ret_v9 >= top_ret_v8

