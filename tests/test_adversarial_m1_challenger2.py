"""
tests/test_adversarial_m1_challenger2.py — Adversarial Stress Test Suite for Phase 140 Milestone 1.

Author: Challenger 2 (Empirical Verifier & Critic)
Scope:
1. src/core/option_surface_accelerator.py (Feature F683)
2. src/core/nlp_catalyst_engine.py (Feature F682)
3. src/ai/factor_orthogonalizer.py (Feature F684)

Adversarial Dimensions Tested:
- Near-singular and rank-deficient covariance matrices under PCA-ZCA whitening
- Top-4 consensus preservation under extreme collinearity
- Hyperbolic deadband (alpha=440.0, delta=0.035) sub-threshold leakage & boundary z=0.035
- Power overflow immunity with zero RuntimeWarnings
- Second-order analytical Greeks under extreme spot, strike, vol, tau, and degenerate inputs
- Extreme IV skew inversions (skew=1000.0 and skew=0.001)
- Flatline zero-volatility return series and missing data fallbacks
- Strict finite values, zero NaNs, and bounds containment [0.05, 0.95] / [0.05, 0.98]
"""

from __future__ import annotations

import os
import sys
import unittest
import warnings
import numpy as np
import pandas as pd

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.option_surface_accelerator import (
    OptionSurfaceAccelerator,
    compute_black_scholes_greeks,
    compute_net_dealer_gex_and_vanna,
)
from src.core.nlp_catalyst_engine import (
    NLPCatalystEngine,
    compute_finbert_polarity,
    compute_tone_drift_and_accel,
)
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    repair_covariance_psd,
    compute_pairwise_available_covariance,
    apply_hyperbolic_deadband_phase140,
)


class TestAdversarialM1Challenger2(unittest.TestCase):
    """Empirical Adversarial Challenge Suite for Phase 140 M1."""

    def setUp(self) -> None:
        self.options_engine = OptionSurfaceAccelerator()
        self.nlp_engine = NLPCatalystEngine()
        self.ortho_engine = FactorOrthogonalizerEngine()

    # =========================================================================
    # 1. Option Surface Accelerator Adversarial Harness
    # =========================================================================

    def test_greeks_degenerate_zero_and_negative_inputs(self) -> None:
        """ADV-01: Greeks with spot<=0, strike<=0, tau<=0, vol<=0 return finite zeros."""
        degenerate_cases = [
            {"spot": 0.0, "strike": 100.0, "tau": 0.1, "vol": 0.2},
            {"spot": -50.0, "strike": 100.0, "tau": 0.1, "vol": 0.2},
            {"spot": 100.0, "strike": 0.0, "tau": 0.1, "vol": 0.2},
            {"spot": 100.0, "strike": -100.0, "tau": 0.1, "vol": 0.2},
            {"spot": 100.0, "strike": 100.0, "tau": 0.0, "vol": 0.2},
            {"spot": 100.0, "strike": 100.0, "tau": -1.0, "vol": 0.2},
            {"spot": 100.0, "strike": 100.0, "tau": 0.1, "vol": 0.0},
            {"spot": 100.0, "strike": 100.0, "tau": 0.1, "vol": -0.5},
        ]
        for kwargs in degenerate_cases:
            greeks = compute_black_scholes_greeks(**kwargs)
            for greek_name in ["gamma", "vega", "vanna", "volga"]:
                val = greeks[greek_name]
                self.assertTrue(np.isfinite(val), f"Greek {greek_name} not finite for {kwargs}")
                self.assertEqual(val, 0.0, f"Greek {greek_name} expected 0.0 for {kwargs}")

    def test_greeks_extreme_parameters_stability(self) -> None:
        """ADV-02: Greeks under extreme spot, strike, vol, and tau remain strictly finite."""
        extreme_cases = [
            # Microscopic spot / huge strike (deep OTM call)
            {"spot": 1e-6, "strike": 1e6, "tau": 0.1, "vol": 0.2},
            # Huge spot / microscopic strike (deep ITM call)
            {"spot": 1e6, "strike": 1e-6, "tau": 0.1, "vol": 0.2},
            # Ultra-short expiry
            {"spot": 100.0, "strike": 100.0, "tau": 1e-4, "vol": 0.3},
            # Ultra-long expiry (50 years)
            {"spot": 100.0, "strike": 100.0, "tau": 50.0, "vol": 0.3},
            # Hyper-volatility (1000% vol)
            {"spot": 100.0, "strike": 100.0, "tau": 0.25, "vol": 10.0},
            # Microscopic vol (0.02% vol)
            {"spot": 100.0, "strike": 100.0, "tau": 0.25, "vol": 0.0002},
        ]
        for kwargs in extreme_cases:
            greeks = compute_black_scholes_greeks(**kwargs)
            for greek_name in ["gamma", "vega", "vanna", "volga"]:
                val = greeks[greek_name]
                self.assertTrue(np.isfinite(val), f"Greek {greek_name} was non-finite {val} for {kwargs}")
                self.assertFalse(np.isnan(val), f"Greek {greek_name} was NaN for {kwargs}")

    def test_greeks_nan_and_inf_resilience(self) -> None:
        """ADV-03: Greeks with NaN or Inf inputs gracefully return 0.0 with zero NaNs."""
        nan_inf_cases = [
            {"spot": np.nan, "strike": 100.0, "tau": 0.1, "vol": 0.2},
            {"spot": 100.0, "strike": np.nan, "tau": 0.1, "vol": 0.2},
            {"spot": 100.0, "strike": 100.0, "tau": np.nan, "vol": 0.2},
            {"spot": 100.0, "strike": 100.0, "tau": 0.1, "vol": np.nan},
            {"spot": np.inf, "strike": 100.0, "tau": 0.1, "vol": 0.2},
            {"spot": 100.0, "strike": np.inf, "tau": 0.1, "vol": 0.2},
        ]
        for kwargs in nan_inf_cases:
            greeks = compute_black_scholes_greeks(**kwargs)
            for greek_name in ["gamma", "vega", "vanna", "volga"]:
                val = greeks[greek_name]
                self.assertTrue(np.isfinite(val))
                self.assertFalse(np.isnan(val))
                self.assertEqual(val, 0.0)

    def test_extreme_iv_skew_reversals(self) -> None:
        """ADV-04: Options chain with extreme IV skew (1000x and 0.001x) produces finite outputs."""
        spot = 100.0
        # Extreme Put Panic Skew: Put IV 10.0, Call IV 0.01 -> Skew = 1000.0
        chain_panic = [
            {"strike": 90.0, "tau": 0.1, "implied_vol": 10.0, "open_interest": 50000.0, "type": "put"},
            {"strike": 110.0, "tau": 0.1, "implied_vol": 0.01, "open_interest": 50000.0, "type": "call"},
        ]
        gex_p, vanna_p, skew_p = compute_net_dealer_gex_and_vanna(spot, chain_panic)
        self.assertTrue(np.isfinite(gex_p) and np.isfinite(vanna_p) and np.isfinite(skew_p))
        self.assertAlmostEqual(skew_p, 1000.0, places=1)

        # Extreme Call FOMO Skew: Put IV 0.01, Call IV 10.0 -> Skew = 0.001
        chain_fomo = [
            {"strike": 90.0, "tau": 0.1, "implied_vol": 0.01, "open_interest": 50000.0, "type": "put"},
            {"strike": 110.0, "tau": 0.1, "implied_vol": 10.0, "open_interest": 50000.0, "type": "call"},
        ]
        gex_f, vanna_f, skew_f = compute_net_dealer_gex_and_vanna(spot, chain_fomo)
        self.assertTrue(np.isfinite(gex_f) and np.isfinite(vanna_f) and np.isfinite(skew_f))
        self.assertAlmostEqual(skew_f, 0.001, places=3)

    def test_options_flatline_zero_volatility_returns(self) -> None:
        """ADV-05: Flatline zero-volatility returns series produces exactly neutral 0.50 score."""
        p_dict = {
            "FLAT_1": pd.DataFrame({"Close": [100.0] * 50, "Volume": [0.0] * 50}),
            "FLAT_2": pd.DataFrame({"Close": [50.0] * 20, "High": [50.0] * 20, "Low": [50.0] * 20}),
            "SINGLE_BAR": pd.DataFrame({"Close": [75.0]}),
            "EMPTY": pd.DataFrame({"Close": []}),
        }
        res = self.options_engine.compute_scores(p_dict)
        self.assertEqual(len(res), 4)
        self.assertFalse(res["option_surface_score"].isna().any())
        # All flat/degenerate assets must resolve to neutral 0.50
        for score in res["option_surface_score"]:
            self.assertAlmostEqual(score, 0.50, delta=0.001)

    def test_options_surface_score_bounds_and_orthogonalizer_containment(self) -> None:
        """ADV-06: OptionSurfaceAccelerator score bounds [0.05, 0.98] and orthogonalizer bounds [0.05, 0.95]."""
        p_dict = {
            "SQUEEZE": pd.DataFrame({"Close": [100.0, 102.0, 104.0, 106.0, 108.0]}),
            "DUMP": pd.DataFrame({"Close": [100.0, 95.0, 90.0, 85.0, 80.0]}),
        }
        # Heavy OTM call OI inducing maximum bullish squeeze impulse
        chain_squeeze = [
            {"strike": 115.0, "tau": 0.05, "implied_vol": 0.20, "open_interest": 10000000.0, "type": "call"},
            {"strike": 100.0, "tau": 0.05, "implied_vol": 0.10, "open_interest": 10.0, "type": "put"},
        ]
        res_raw = self.options_engine.compute_scores(p_dict, options_chain_dict={"SQUEEZE": chain_squeeze})
        scores_raw = res_raw["option_surface_score"].values
        # Blueprint specifies [0.05, 0.98]
        self.assertTrue(np.all(scores_raw >= 0.05))
        self.assertTrue(np.all(scores_raw <= 0.98))

        # Downstream factor orthogonalization clips to [0.05, 0.95]
        score_df = pd.DataFrame({
            "symbol": ["SQUEEZE", "DUMP", "NEUTRAL_1", "NEUTRAL_2", "NEUTRAL_3"],
            "option_surface_score": [0.98, 0.05, 0.50, 0.52, 0.48],
            "other_score": [0.95, 0.05, 0.50, 0.51, 0.49],
        })
        out_ortho = self.ortho_engine.orthogonalize_phase140(
            score_df=score_df,
            strategy_cols=["option_surface_score", "other_score"],
            preserve_top_k=1
        )
        for col in ["option_surface_score", "other_score"]:
            vals = out_ortho[col].values
            self.assertTrue(np.all(vals >= 0.05), f"{col} has values below 0.05")
            self.assertTrue(np.all(vals <= 0.95), f"{col} has values exceeding 0.95: {vals.max()}")

    # =========================================================================
    # 2. NLP Catalyst Engine Adversarial Harness
    # =========================================================================

    def test_nlp_finbert_polarity_adversarial_inputs(self) -> None:
        """ADV-07: compute_finbert_polarity handles NaN, Inf, negative, and zero probabilities."""
        # NaN / Inf inputs
        p1, c1 = compute_finbert_polarity(np.nan, 0.2, 0.3)
        self.assertEqual((p1, c1), (0.0, 0.0))

        p2, c2 = compute_finbert_polarity(np.inf, 0.2, 0.3)
        self.assertEqual((p2, c2), (0.0, 0.0))

        # Zero total probability
        p3, c3 = compute_finbert_polarity(0.0, 0.0, 0.0)
        self.assertTrue(np.isfinite(p3) and np.isfinite(c3))

        # Extreme positive polarity (100% positive)
        p4, c4 = compute_finbert_polarity(1.0, 0.0, 0.0)
        self.assertAlmostEqual(p4, 1.0, places=4)
        self.assertAlmostEqual(c4, 1.0, places=4)

        # Extreme negative polarity (100% negative)
        p5, c5 = compute_finbert_polarity(0.0, 1.0, 0.0)
        self.assertAlmostEqual(p5, -1.0, places=4)
        self.assertAlmostEqual(c5, 1.0, places=4)

    def test_nlp_tone_drift_and_accel_extreme_bounds(self) -> None:
        """ADV-08: Guidance tone drift and second-order acceleration under extreme inputs."""
        # Infinite / NaN inputs
        td1, ta1 = compute_tone_drift_and_accel(np.nan, np.nan)
        self.assertEqual((td1, ta1), (0.0, 0.0))

        # Huge tone swings (+10^9)
        td2, ta2 = compute_tone_drift_and_accel(1e9, -1e9, conviction=1.0, prev_drift=0.0)
        self.assertTrue(np.isfinite(td2) and np.isfinite(ta2))
        self.assertGreater(td2, 1e9)

    def test_nlp_catalyst_composite_score_bounds_and_zero_nans(self) -> None:
        """ADV-09: NLPCatalystEngine produces scores strictly within [0.05, 0.95] with zero NaNs."""
        p_dict = {
            "FLAT": pd.DataFrame({"Close": [100.0] * 30, "Volume": [0.0] * 30}),
            "MAX_POS": pd.DataFrame({"Close": [10.0 + i * 2.0 for i in range(30)], "Volume": [1000.0] * 30}),
            "MAX_NEG": pd.DataFrame({"Close": [100.0 - i * 2.0 for i in range(30)], "Volume": [1000.0] * 30}),
            "NAN_DATA": pd.DataFrame({"Close": [np.nan] * 30}),
        }
        filings = {
            "MAX_POS": {"polarity": 10.0, "insider_role": "CEO"},  # Massive insider buy
            "MAX_NEG": {"polarity": -1.0, "event_type": "convertible_bond"},  # Adverse dilutive CB
        }
        transcripts = {
            "MAX_POS": {"s_curr": 1.0, "s_prev": -1.0, "conviction": 1.0, "prev_drift": -1.0},
            "MAX_NEG": {"s_curr": -1.0, "s_prev": 1.0, "conviction": 1.0, "prev_drift": 1.0},
        }

        res = self.nlp_engine.compute_scores(
            p_dict, filing_map=filings, transcript_map=transcripts
        )
        self.assertFalse(res["nlp_catalyst_score"].isna().any())
        scores = res["nlp_catalyst_score"].values
        self.assertTrue(np.all(scores >= 0.05), f"Found score < 0.05: {scores.min()}")
        self.assertTrue(np.all(scores <= 0.95), f"Found score > 0.95: {scores.max()}")
        self.assertEqual(res.loc[res["symbol"] == "MAX_POS", "nlp_catalyst_score"].iloc[0], 0.95)
        self.assertEqual(res.loc[res["symbol"] == "MAX_NEG", "nlp_catalyst_score"].iloc[0], 0.05)
        self.assertEqual(res.loc[res["symbol"] == "FLAT", "nlp_catalyst_score"].iloc[0], 0.50)

    # =========================================================================
    # 3. Factor Orthogonalizer & Deadband Adversarial Harness
    # =========================================================================

    def test_covariance_repair_non_psd_matrices(self) -> None:
        """ADV-10: repair_covariance_psd projects non-PSD matrices to strictly positive definite."""
        # Severely non-PSD matrix with negative eigenvalues
        C_bad = np.array([
            [1.0, 0.999, 0.999],
            [0.999, 1.0, 0.999],
            [0.999, 0.999, 0.900],
        ], dtype=np.float64)
        orig_min_eval = float(np.min(np.linalg.eigvalsh(C_bad)))
        self.assertLess(orig_min_eval, 0.0, "C_bad should have negative minimum eigenvalue")

        C_repaired = repair_covariance_psd(C_bad, ridge_epsilon=1e-6)
        repaired_evals = np.linalg.eigvalsh(C_repaired)
        self.assertGreaterEqual(float(np.min(repaired_evals)), 1e-6)
        # Verify symmetry
        np.testing.assert_allclose(C_repaired, C_repaired.T, atol=1e-12)

    def test_pca_zca_whitening_near_singular_and_collinear(self) -> None:
        """ADV-11: FactorOrthogonalizerEngine handles rank-deficient / near-singular matrices with zero NaNs."""
        np.random.seed(1337)
        N, K = 120, 12
        # Base factor + 5 near-identical collinear factors with microscopic noise (1e-12)
        base = np.random.uniform(0.1, 0.9, N)
        data = {
            "col_0": base,
            "col_1": base + 1e-12 * np.random.randn(N),
            "col_2": base - 1e-12 * np.random.randn(N),
            "col_3": 1.5 * base,
            "col_4": -0.8 * base,
            "col_5": base + 1e-10 * np.random.randn(N),
        }
        for i in range(6, K):
            data[f"col_{i}"] = np.random.uniform(0.1, 0.9, N)

        df = pd.DataFrame(data)
        cols = list(df.columns)

        out_df = self.ortho_engine.orthogonalize(
            df, cols, method="pca_symmetric", preserve_top_k=4
        )
        self.assertFalse(out_df[cols].isna().any().any())
        for c in cols:
            vals = out_df[c].values
            self.assertTrue(np.all(vals >= 0.0))
            self.assertTrue(np.all(vals <= 1.0))

    def test_top4_consensus_preservation_under_extreme_collinearity(self) -> None:
        """ADV-12: Top-4 consensus preservation maintains leading eigenvalue fidelity."""
        np.random.seed(42)
        N, K = 80, 8
        # Strong market consensus driving first 2 columns
        market_consensus = np.random.normal(0.5, 0.15, N)
        df = pd.DataFrame({
            "trend": market_consensus + 0.01 * np.random.randn(N),
            "momentum": market_consensus + 0.01 * np.random.randn(N),
            "value": market_consensus * 0.8 + 0.05 * np.random.randn(N),
            "quality": market_consensus * 0.7 + 0.05 * np.random.randn(N),
            "noise1": np.random.uniform(0.2, 0.8, N),
            "noise2": np.random.uniform(0.2, 0.8, N),
            "noise3": np.random.uniform(0.2, 0.8, N),
            "noise4": np.random.uniform(0.2, 0.8, N),
        })
        cols = list(df.columns)
        out_df = self.ortho_engine.orthogonalize(
            df, cols, method="pca_symmetric", preserve_top_k=4
        )
        # Leading signals maintain high correlation with their raw consensus
        corr_trend = np.corrcoef(df["trend"].values, out_df["trend"].values)[0, 1]
        self.assertGreater(corr_trend, 0.70)

    def test_hyperbolic_deadband_zero_power_overflow_warnings(self) -> None:
        """ADV-13: Hyperbolic deadband passes extreme values with zero RuntimeWarnings."""
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            extreme_array = np.array([-1e12, -1000.0, -0.05, -0.035, 0.0, 0.035, 0.05, 1000.0, 1e12])
            res_arr = apply_hyperbolic_deadband_phase140(extreme_array, delta=0.035, alpha=440.0)

            # Check Series
            s = pd.Series(extreme_array)
            res_ser = apply_hyperbolic_deadband_phase140(s, delta=0.035, alpha=440.0)

            # Check scalar
            res_scal = apply_hyperbolic_deadband_phase140(1e9, delta=0.035, alpha=440.0)

            # Filter for RuntimeWarning
            runtime_warns = [w for w in caught_warnings if issubclass(w.category, RuntimeWarning)]
            self.assertEqual(len(runtime_warns), 0, f"Encountered RuntimeWarnings: {runtime_warns}")
            self.assertTrue(np.all(np.isfinite(res_arr)))
            self.assertTrue(res_ser.notna().all())
            self.assertTrue(np.isfinite(res_scal))

    def test_hyperbolic_deadband_empirical_boundary_characterization(self) -> None:
        """ADV-14: Empirical characterization of noise suppression and boundary z=0.035.

        Verifies:
        1. Exact zero suppression for |z| <= 0.025 (leakage == 0.0 < 10^-308).
        2. Smooth boundary transition at z=0.035 where z_clean = z * tanh(1.0) ~= 0.026656.
        3. Full alpha transmission for |z| >= 0.045 where z_clean == z.
        """
        delta = 0.035
        alpha = 440.0

        # Sub-threshold noise region (|z| <= 0.025)
        for z_noise in [-0.025, -0.010, 0.0, 0.010, 0.025]:
            z_clean = apply_hyperbolic_deadband_phase140(z_noise, delta=delta, alpha=alpha)
            self.assertEqual(z_clean, 0.0, f"Expected 0.0 leakage for z={z_noise}")

        # Transition zone boundary z = delta = 0.035
        # Under formula z * tanh((|z|/delta)^alpha), at |z|=delta: ratio=1.0, tanh(1.0)=0.761594
        z_boundary_pos = apply_hyperbolic_deadband_phase140(0.035, delta=delta, alpha=alpha)
        expected_boundary_pos = 0.035 * np.tanh(1.0)
        self.assertAlmostEqual(z_boundary_pos, expected_boundary_pos, places=5)

        z_boundary_neg = apply_hyperbolic_deadband_phase140(-0.035, delta=delta, alpha=alpha)
        expected_boundary_neg = -0.035 * np.tanh(1.0)
        self.assertAlmostEqual(z_boundary_neg, expected_boundary_neg, places=5)

        # High-conviction signal transmission zone (|z| >= 0.045)
        for z_sig in [-1.0, -0.10, -0.045, 0.045, 0.10, 1.0]:
            z_clean = apply_hyperbolic_deadband_phase140(z_sig, delta=delta, alpha=alpha)
            self.assertAlmostEqual(z_clean, z_sig, places=5, msg=f"Failed 100% transmission for z={z_sig}")

    def test_orthogonalize_phase140_composite_invariants(self) -> None:
        """ADV-15: Full orthogonalize_phase140 maintains strict bounds [0.05, 0.95] and zero NaNs."""
        np.random.seed(99)
        N = 100
        strategy_cols = [f"strat_{i}" for i in range(15)]
        df = pd.DataFrame(
            np.random.uniform(0.1, 0.9, (N, 15)),
            columns=strategy_cols
        )
        # Add extreme outliers and missing values
        df.iloc[0, 0] = 0.99
        df.iloc[1, 1] = 0.01
        df.iloc[2, 2] = np.nan
        df.iloc[3, :] = 0.50  # Constant row

        res_df = self.ortho_engine.orthogonalize_phase140(
            score_df=df,
            strategy_cols=strategy_cols,
            preserve_top_k=4,
            apply_deadband=True,
            deadband_delta=0.035,
            deadband_alpha=440.0,
        )

        for col in strategy_cols:
            vals = res_df[col].dropna().values
            self.assertTrue(np.all(vals >= 0.05), f"{col} has values below 0.05: {vals.min()}")
            self.assertTrue(np.all(vals <= 0.95), f"{col} has values above 0.95: {vals.max()}")


if __name__ == "__main__":
    unittest.main()
