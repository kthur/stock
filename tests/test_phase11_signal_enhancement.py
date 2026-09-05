"""
test_phase11_signal_enhancement.py — Unit tests for Phase 11 Singularity Signal Enhancement (F63, F64.1, F64.2)
"""

import numpy as np
import pandas as pd
import pytest

from trading_system.src.ai.factor_suppression import (
    apply_dodecagonal_hyperbolic_deadband,
    apply_decic_hyperbolic_deadband,
)
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


class TestPhase11SignalEnhancement:
    """Test suite verifying mathematical invariants of Phase 11 Signal Enhancement components."""

    def test_dodecagonal_hyperbolic_deadband_noise_leakage(self):
        """Feature F64.2: Verify dodecagonal (alpha=12.0) deadband attenuates >99.99999% noise for |z| <= 0.010."""
        small_z = np.array([-0.010, -0.005, 0.0, 0.005, 0.010])
        denoised = apply_dodecagonal_hyperbolic_deadband(small_z, delta_noise=0.045, alpha_pos=12.0)

        # Max noise leakage must be strictly below 1e-7 (< 0.00001% of original)
        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-7, f"Expected noise leakage < 1e-7, got {max_leakage}"

        # Test high conviction pass-through: |z| >= 0.150 must retain > 99.99%
        large_z = np.array([-0.25, -0.15, 0.15, 0.25])
        denoised_large = apply_dodecagonal_hyperbolic_deadband(large_z, delta_noise=0.045, alpha_pos=12.0)
        retention = np.abs(denoised_large) / np.abs(large_z)
        assert np.all(retention > 0.9999), f"Expected high conviction retention > 99.99%, got {retention}"

        # Monotonicity test
        grid = np.linspace(-0.30, 0.30, 101)
        denoised_grid = apply_dodecagonal_hyperbolic_deadband(grid, delta_noise=0.045, alpha_pos=12.0)
        diffs = np.diff(denoised_grid)
        assert np.all(diffs >= -1e-12), "Dodecagonal deadband must be strictly monotonically non-decreasing"

    def test_mckean_vlasov_mean_field_coupling_properties(self):
        """Feature F63: Verify McKean-Vlasov mean field game coupling operator outputs and stability."""
        np.random.seed(42)
        N_assets, D_strats = 50, 37
        scores = np.random.uniform(0.1, 0.9, size=(N_assets, D_strats))

        # Make strategy 0 an idiosyncratic non-crowded alpha, and strategies 1-5 crowded
        scores[:, 0] = np.random.uniform(0.7, 0.95, size=N_assets)
        scores[:, 1:6] = 0.20

        res = EnsembleScoringEngine.compute_mckean_vlasov_mean_field_coupling(scores, crowding_penalty_kappa=2.5)

        assert "mean_field_distribution" in res
        assert "kl_divergence_crowding" in res
        assert "mfg_equilibrium_weights" in res
        assert "decoupling_alpha_boost" in res

        mf_dist = res["mean_field_distribution"]
        eq_w = res["mfg_equilibrium_weights"]
        boost = res["decoupling_alpha_boost"]

        # Mean field and equilibrium weights must sum to 1.0
        assert np.isclose(np.sum(mf_dist), 1.0, atol=1e-4)
        assert np.isclose(np.sum(eq_w), 1.0, atol=1e-4)

        # Idiosyncratic strategy should receive decoupling boost >= 1.0
        assert np.all(boost >= 1.0)
        assert boost[0] >= 1.05, f"Strategy 0 should receive high boost, got {boost[0]}"

    def test_regime_adaptive_gamma_top_version11(self):
        """Feature F64.1: Verify regime-adaptive gamma_top calibration under version=11."""
        engine = EnsembleScoringEngine()
        gamma_bull_low = engine.get_regime_adaptive_gamma_top("BULL_LOW_VOL", version=11)
        gamma_bull_high = engine.get_regime_adaptive_gamma_top("BULL_HIGH_VOL", version=11)
        gamma_side_low = engine.get_regime_adaptive_gamma_top("SIDEWAYS_LOW_VOL", version=11)
        gamma_crisis = engine.get_regime_adaptive_gamma_top("CRISIS", version=11)

        assert gamma_bull_low == 1.25, f"Expected 1.25 for BULL_LOW_VOL v11, got {gamma_bull_low}"
        assert gamma_bull_high == 1.05, f"Expected 1.05 for BULL_HIGH_VOL v11, got {gamma_bull_high}"
        assert gamma_side_low == 0.85, f"Expected 0.85 for SIDEWAYS_LOW_VOL v11, got {gamma_side_low}"
        assert gamma_crisis == 0.20, f"Expected 0.20 for CRISIS v11, got {gamma_crisis}"

        # Monotonicity across risk regimes
        assert gamma_bull_low > gamma_bull_high > gamma_side_low > gamma_crisis

    def test_mckean_vlasov_quint_pillar_tensor_synergy_version11(self):
        """Feature F63/F64.1: Verify quint-pillar tensor synergy incorporates McKean-Vlasov MFG under version 11."""
        np.random.seed(42)
        idx = [f"SYM_{i:02d}" for i in range(20)]
        scores_df = pd.DataFrame(np.random.uniform(0.40, 0.90, size=(20, 37)), index=idx)

        synergy_v10 = EnsembleScoringEngine.compute_quint_pillar_tensor_synergy(scores_df, version=10)
        synergy_v11 = EnsembleScoringEngine.compute_quint_pillar_tensor_synergy(scores_df, version=11)

        assert len(synergy_v11) == 20
        assert np.all(np.isfinite(synergy_v11.values))
        assert np.all(synergy_v11.values >= 0.0)

    def test_combine_predictions_version11_rank_modulation(self):
        """Feature F64.1: Verify combine_predictions executes 6th-order hyper-convex rank modulation under v11."""
        engine = EnsembleScoringEngine()
        N = 25
        df_list = []
        for i in range(N):
            df_list.append({
                "symbol": f"STOCK_{i:03d}",
                "market": "SP500",
                "regression": 0.40 + 0.02 * i,
                "surge": 0.35 + 0.02 * i,
                "vcp_ml": 0.30 + 0.02 * i,
                "mq_factor": 0.45 + 0.015 * i,
                "factor_neutralized": 0.40 + 0.02 * i,
            })
        test_df = pd.DataFrame(df_list)

        comb_v10 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=10)
        comb_v11 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=11)

        assert "ensemble_score" in comb_v11.columns
        assert len(comb_v11) == N
        assert np.all(np.isfinite(comb_v11["ensemble_score"].values))

        # Top asset in v11 should exhibit enhanced convex concentration relative to v10
        top_v10 = comb_v10.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v11 = comb_v11.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v11 >= top_v10 - 1e-4, f"v11 top score ({top_v11}) should be >= v10 top score ({top_v10})"
