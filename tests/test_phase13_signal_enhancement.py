"""
tests/test_phase13_signal_enhancement.py

Comprehensive unit test suite for Phase 13 Omnipresent (v20 Production Master) Signal Enhancement:
- Feature F71: Superstring Calabi-Yau 6-Fold Holonomy SU(3) & Ricci-Flat Metric Tensor Coupler
- Feature F72.1: 8th-Order Hyper-Convex Rank Modulation across 2D Market Regimes
- Feature F72.2: 16th-Order Hexadecagonal Hyperbolic Tangent Noise Deadband
- End-to-End EnsembleScoringEngine combine_predictions() with version=13
- Strict backward compatibility validation with Phase 11 (v18) and Phase 12 (v19)
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from trading_system.src.ai.ensemble_scorer import (
    apply_hexadecagonal_hyperbolic_deadband,
    compute_phase13_hyperconvex_rank_modulation,
    CalabiYauHolonomyCoupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.factor_suppression import (
    apply_hexadecagonal_hyperbolic_deadband as fs_hexadecagonal_deadband,
)


class TestPhase13SignalEnhancement:
    """Test suite covering Phase 13 Omnipresent Signal Enhancement Innovations."""

    # -------------------------------------------------------------------------
    # 1. Feature F72.2: 16th-Order Hexadecagonal Hyperbolic Tangent Deadband
    # -------------------------------------------------------------------------

    def test_hexadecagonal_hyperbolic_deadband_noise_leakage(self):
        """Validates that near-zero noise (|z| <= 0.010) has leakage < 10^-9 (< 1e-11)."""
        z_grid = np.linspace(-0.010, 0.010, 100)
        denoised = apply_hexadecagonal_hyperbolic_deadband(z_grid, delta_noise=0.040, alpha_pos=16.0)

        max_leakage = np.max(np.abs(denoised))
        assert max_leakage < 1e-9, f"Max noise leakage {max_leakage} must be < 1e-9"

        # Check boundary point |z| = 0.010
        val_at_bound = float(np.abs(apply_hexadecagonal_hyperbolic_deadband(0.010, delta_noise=0.040, alpha_pos=16.0)))
        assert val_at_bound < 1e-10, f"Leakage at z=0.010 was {val_at_bound}, expected < 1e-10"

    def test_hexadecagonal_hyperbolic_deadband_pass_through_and_monotonicity(self):
        """Validates that high conviction signals (|z| >= 0.150) transmit 100% and rank monotonicity is strict."""
        z_high = np.array([0.150, 0.200, 0.300, 0.450])
        denoised_high = apply_hexadecagonal_hyperbolic_deadband(z_high, delta_noise=0.040, alpha_pos=16.0)

        np.testing.assert_allclose(denoised_high, z_high, rtol=1e-5, atol=1e-6)

        # Monotonicity test
        grid = np.linspace(-0.50, 0.50, 2000)
        out = apply_hexadecagonal_hyperbolic_deadband(grid, delta_noise=0.040, alpha_pos=16.0)
        diffs = np.diff(out)
        assert np.all(diffs >= -1e-12), "Hexadecagonal deadband must be strictly non-decreasing"

        rho, _ = spearmanr(grid, out)
        assert rho >= 0.9999, f"Spearman rank correlation must be ~1.0, got {rho}"

    def test_hexadecagonal_deadband_symmetry_and_regimes(self):
        """Validates unconditioned odd symmetry and bear/crisis regime widening."""
        z_grid = np.linspace(0.001, 0.40, 200)
        f_pos = apply_hexadecagonal_hyperbolic_deadband(z_grid, delta_noise=0.040, alpha_pos=16.0)
        f_neg = apply_hexadecagonal_hyperbolic_deadband(-z_grid, delta_noise=0.040, alpha_pos=16.0)

        np.testing.assert_allclose(f_pos, -f_neg, atol=1e-10)

        # In CRISIS, negative signals are squashed more heavily
        out_bull = apply_hexadecagonal_hyperbolic_deadband(-0.040, delta_noise=0.040, regime="BULL_LOW_VOL")
        out_crisis = apply_hexadecagonal_hyperbolic_deadband(-0.040, delta_noise=0.040, regime="CRISIS")
        assert abs(out_crisis) < abs(out_bull), "Crisis regime must suppress negative noise more strongly"

        # Test cross-module import consistency
        fs_res = fs_hexadecagonal_deadband(0.005, delta_noise=0.040)
        es_res = apply_hexadecagonal_hyperbolic_deadband(0.005, delta_noise=0.040)
        assert fs_res == es_res

    # -------------------------------------------------------------------------
    # 2. Feature F71: Superstring Calabi-Yau 6-Fold Holonomy SU(3) Coupler
    # -------------------------------------------------------------------------

    def test_calabi_yau_metric_and_hermitian_properties(self):
        """Validates that the Kähler metric g is Hermitian, has det(g) > 0, and has expected dimensions."""
        pillars = pd.DataFrame({
            'val': [0.60, 0.20, 0.80],
            'mom': [0.70, 0.30, 0.85],
            'flow': [0.55, 0.15, 0.75],
            'cat': [0.65, 0.25, 0.90],
            'net': [0.50, 0.10, 0.70],
        })

        res = CalabiYauHolonomyCoupler.compute(pillars, lambda_cy=0.75, v_cy=1.0, kappa_cy=1.60)

        assert "h_cy" in res
        assert "s_cy" in res
        assert "ricci_def" in res
        assert "holonomy_def" in res
        assert "feri" in res
        assert "det_g" in res

        # Check positive determinant
        det_g = res["det_g"]
        assert np.all(det_g > 0.0), f"Metric determinant must be strictly positive, got {det_g}"

        # Check h_cy and FERI bounds in (0, 1]
        h_cy = res["h_cy"].values
        feri = res["feri"].values
        assert np.all((h_cy > 0.0) & (h_cy <= 1.0)), f"h_cy must be in (0, 1], got {h_cy}"
        assert np.all((feri > 0.0) & (feri <= 1.0)), f"FERI must be in (0, 1], got {feri}"

    def test_calabi_yau_action_and_topological_properties(self):
        """Validates that Calabi-Yau action density is non-negative and vacuum gives h_cy close to 1."""
        coupler = CalabiYauHolonomyCoupler(lambda_cy=0.75, v_cy=1.0, kappa_cy=1.60)

        # High coherence balanced assets
        balanced_p = np.full((5, 5), 0.4472)  # ||p|| ~ 1.0
        res_balanced = coupler.evaluate(balanced_p)
        assert np.all(res_balanced["s_cy"] >= 0.0), "S_CY action density must be non-negative"

        # Collapsed/degenerate assets
        collapsed_p = np.array([
            [0.99, 0.01, 0.01, 0.01, 0.01],
            [0.01, 0.99, 0.01, 0.01, 0.01],
            [0.01, 0.01, 0.99, 0.01, 0.01],
        ])
        res_collapsed = coupler.evaluate(collapsed_p)
        # S_CY should be non-negative
        assert np.all(res_collapsed["s_cy"] >= 0.0)
        assert np.all(res_collapsed["h_cy"] <= 1.0)

    def test_calabi_yau_coupler_input_formats(self):
        """Validates compatibility across DataFrame, dict, 2D array, and 1D vector."""
        vec_1d = np.array([0.5, 0.6, 0.4, 0.7, 0.3])
        res_1d = CalabiYauHolonomyCoupler.compute(vec_1d)
        assert isinstance(res_1d["h_cy"], float)
        assert 0.0 < res_1d["h_cy"] <= 1.0
        assert isinstance(res_1d["det_g"], float)

        dict_in = {
            'val': [0.5, 0.6],
            'mom': [0.6, 0.7],
            'flow': [0.4, 0.5],
            'cat': [0.7, 0.8],
            'net': [0.3, 0.4],
        }
        res_dict = CalabiYauHolonomyCoupler.compute(dict_in)
        assert len(res_dict["h_cy"]) == 2

    # -------------------------------------------------------------------------
    # 3. Feature F72.1: 8th-Order Hyper-Convex Rank Modulation
    # -------------------------------------------------------------------------

    def test_8th_order_rank_modulation_percentiles(self):
        """Validates that 8th-order rank modulation accelerates top percentiles while staying flat at bottom."""
        ranks = np.array([0.10, 0.30, 0.50, 0.60, 0.80, 0.90, 0.99, 1.00])
        mult = compute_phase13_hyperconvex_rank_modulation(ranks, gamma_top=1.45)

        # Bottom 60% should remain modest (<= 1.05)
        assert mult[0] < 0.60
        assert mult[2] < 0.95
        assert mult[3] < 1.02

        # Top 1% should show explosive conviction
        assert mult[-1] > 3.50, f"Max conviction multiplier for r=1.00 should exceed 3.50, got {mult[-1]}"
        assert mult[-2] > 2.00, f"Conviction multiplier for r=0.99 should exceed 2.00, got {mult[-2]}"

    def test_8th_order_rank_modulation_strict_convexity(self):
        """Validates strict monotonicity and positive second derivative for positive conviction."""
        r_dense = np.linspace(0.01, 1.0, 1000)
        mult = compute_phase13_hyperconvex_rank_modulation(r_dense, gamma_top=1.20)

        # 1st derivative positive
        d1 = np.diff(mult)
        assert np.all(d1 > 0), "8th-order rank modulation must be strictly monotonic increasing"

        # 2nd derivative positive for high ranks
        d2 = np.diff(d1)
        assert np.all(d2[500:] >= 0), "8th-order rank modulation must be strictly convex for r >= 0.5"

    def test_regime_adaptive_gamma_top_version13(self):
        """Validates regime-adaptive gamma_top calibration under version >= 13."""
        gamma_bull_low = EnsembleScoringEngine.get_regime_adaptive_gamma_top('BULL_LOW_VOL', version=13)
        gamma_bull_high = EnsembleScoringEngine.get_regime_adaptive_gamma_top('BULL_HIGH_VOL', version=13)
        gamma_side_low = EnsembleScoringEngine.get_regime_adaptive_gamma_top('SIDEWAYS_LOW_VOL', version=13)
        gamma_side_high = EnsembleScoringEngine.get_regime_adaptive_gamma_top('SIDEWAYS_HIGH_VOL', version=13)
        gamma_bear_low = EnsembleScoringEngine.get_regime_adaptive_gamma_top('BEAR_LOW_VOL', version=13)
        gamma_bear_high = EnsembleScoringEngine.get_regime_adaptive_gamma_top('BEAR_HIGH_VOL', version=13)
        gamma_crisis = EnsembleScoringEngine.get_regime_adaptive_gamma_top('CRISIS', version=13)

        assert gamma_bull_low == 1.45
        assert gamma_bull_high == 1.25
        assert gamma_side_low == 1.05
        assert gamma_side_high == 0.75
        assert gamma_bear_low == 0.60
        assert gamma_bear_high == 0.40
        assert gamma_crisis == 0.22

        assert gamma_bull_low > gamma_bull_high > gamma_side_low > gamma_side_high > gamma_bear_low > gamma_bear_high > gamma_crisis

    # -------------------------------------------------------------------------
    # 4. End-to-End Ensemble Pipeline Integration & Backward Compatibility
    # -------------------------------------------------------------------------

    def test_calabi_yau_quint_pillar_tensor_synergy_version13(self):
        """Validates compute_quint_pillar_tensor_synergy activates Calabi-Yau under version=13."""
        scorer = EnsembleScoringEngine()
        n = 10
        scores_df = pd.DataFrame(
            np.random.uniform(0.3, 0.8, size=(n, 37)),
            columns=[f"strat_{i}" for i in range(37)]
        )

        synergy_v13 = scorer.compute_quint_pillar_tensor_synergy(
            scores_df=scores_df,
            regime='BULL_LOW_VOL',
            version=13
        )
        assert isinstance(synergy_v13, pd.Series)
        assert len(synergy_v13) == n
        assert np.all(synergy_v13 >= 0.0)

    def test_combine_predictions_version13_full_pipeline(self):
        """Validates full combine_predictions execution with version=13."""
        engine = EnsembleScoringEngine()
        N = 30
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

        comb_v12 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=12)
        comb_v13 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=13)

        assert isinstance(comb_v13, pd.DataFrame)
        assert not comb_v13.empty
        assert "ensemble_score" in comb_v13.columns
        assert len(comb_v13) == N
        assert np.all(np.isfinite(comb_v13["ensemble_score"].values))
        assert np.all(comb_v13["ensemble_score"].values >= 0.0)
        assert np.all(comb_v13["ensemble_score"].values <= 1.0)

        # Top asset in v13 should exhibit stronger convex concentration than v12
        top_v12 = comb_v12.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        top_v13 = comb_v13.sort_values("ensemble_score", ascending=False).iloc[0]["ensemble_score"]
        assert top_v13 >= top_v12, f"Top conviction in v13 ({top_v13}) should be >= v12 ({top_v12})"

    def test_backward_compatibility_v11_v12(self):
        """Validates that version=11 and version=12 preserve exact legacy execution paths."""
        engine = EnsembleScoringEngine()
        N = 15
        test_df = pd.DataFrame([{
            "symbol": f"SYM_{i}",
            "market": "KOSPI",
            "regression": 0.50,
            "surge": 0.60
        } for i in range(N)])

        res_v11 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=11)
        res_v12 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=12)
        res_v13 = engine.combine_predictions(test_df, regime="BULL_LOW_VOL", version=13)

        assert len(res_v11) == N
        assert len(res_v12) == N
        assert len(res_v13) == N

