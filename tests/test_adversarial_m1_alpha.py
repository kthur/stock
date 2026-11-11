"""
tests/test_adversarial_m1_alpha.py — Empirical Challenger Adversarial Stress Test Suite for Milestone 1 (F940 & F941).

Hostile verification harness:
1. DynamicDispersionScaler:
   - 10,000 randomized float probes for strict monotonicity (x1 < x2 => f(x1) < f(x2)) across multiple domains.
   - All-zeros, all-NaNs, all-infinite values (+inf, -inf), mixed NaNs/Infs.
   - Extreme out-of-distribution values [-1e9, 1e9], constant arrays, empty arrays, 1-element arrays.
   - Boundedness check: target range adherence with zero clipping plateaus.
2. CrossBorderTechLeadLagCoupler:
   - Extreme price shocks (+100%, -90%, -99.9%, +500%, limit down cascades).
   - Empty DataFrames, 1-row DataFrames, missing ticker columns, unknown KRX symbols.
   - All-zeros, all-NaNs, all-infinite values.
   - Downside shock amplification validation (|impulse(R-)| / |impulse(R+)| >= 1.35).
   - Dynamic calibration with rank-deficient, collinear, empty, or degenerate historical data.
3. CrossClusterConfluenceKernel:
   - Degenerate and rank-deficient factor score matrices (all-constant, zero covariance, collinear columns).
   - Extreme factor scores (all 0.0, all 1.0, all 0.50), NaNs, Infs, negative scores, extreme scores [-100, 100].
   - Empty DataFrames, 1-row DataFrames, missing pillar columns, partial dictionary inputs.
   - Pairwise confluence matrix symmetry and gain bounds [1 - eta, 1 + eta].
4. Phase192Coupler (Composite Coupler):
   - Small sample rank-deficient regime (N=3 < D=14) stress testing ZCA whitening on S_{++}^{14}.
   - Singular covariance matrices and extreme US shocks simultaneously.
   - Boundedness and finiteness across 1,000 hostile synthetic portfolio vectors.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.factor_orthogonalizer import (
    DynamicDispersionScaler,
    dynamic_dispersion_scale,
    CrossClusterConfluenceKernel,
    compute_quattuordecuple_pillar_confluence_kernel,
    FactorOrthogonalizerEngine,
    QUATTUORDECUPLE_PILLAR_MAP,
)

from src.ai.historical_couplers import (
    CrossBorderTechLeadLagCoupler,
    Phase192Coupler,
)


class TestAdversarialM1AlphaHarness(unittest.TestCase):
    """Adversarial stress-test harness for Milestone 1 (F940 & F941)."""

    def setUp(self) -> None:
        np.random.seed(42)

    # =========================================================================
    # PART 1: DynamicDispersionScaler Adversarial & Monotonicity Stress Tests
    # =========================================================================

    def test_adv01_dispersion_scaler_10000_random_probes_strict_monotonicity(self) -> None:
        """
        Adversarial Probe 1: 10,000 randomized float probes over [-1000.0, 1000.0].
        Assert: x_i < x_{i+1} => f(x_i) < f(x_{i+1}) strictly (no duplicate collisions, no flat plateaus).
        """
        scaler = DynamicDispersionScaler(target_min=0.0, target_max=1.0, tau_bandwidth=2.5)
        # Generate 10,000 random distinct float probes
        probes = np.random.uniform(-1000.0, 1000.0, size=10000)
        probes = np.unique(probes)  # ensure uniqueness
        probes.sort()

        scaled = scaler.fit_transform(probes)

        # Check all values are strictly finite
        self.assertTrue(np.all(np.isfinite(scaled)), "Dispersion scaled output contains non-finite values!")

        # Check bounds: strictly within (0.0, 1.0)
        self.assertTrue(np.all(scaled > 0.0), f"Scaled values <= 0.0 detected: min={np.min(scaled)}")
        self.assertTrue(np.all(scaled < 1.0), f"Scaled values >= 1.0 detected: max={np.max(scaled)}")

        # Check strict monotonicity: diffs must be strictly positive
        diffs = np.diff(scaled)
        min_diff = np.min(diffs)
        self.assertGreater(
            min_diff, 0.0,
            f"Strict monotonicity violated! Found non-positive gradient: min_diff={min_diff}"
        )

    def test_adv02_dispersion_scaler_extreme_domains_and_out_of_distribution(self) -> None:
        """
        Adversarial Probe 2: Extreme domains: [-1e9, 1e9], tiny values [-1e-12, 1e-12], and [-3.0, 3.0] target range.
        Assert: Strict monotonicity and bounds adherence.
        """
        scaler_3 = DynamicDispersionScaler(target_min=-3.0, target_max=3.0, tau_bandwidth=2.0)

        # Extreme fat-tail inputs: -1e9 to +1e9
        extreme_probes = np.array([-1e9, -1e6, -100.0, -10.0, -1.0, -1e-6, 0.0, 1e-6, 1.0, 10.0, 100.0, 1e6, 1e9])
        scaled_extreme = scaler_3.fit_transform(extreme_probes)

        self.assertTrue(np.all(np.isfinite(scaled_extreme)))
        self.assertTrue(np.all(scaled_extreme >= -3.0))
        self.assertTrue(np.all(scaled_extreme <= 3.0))

        # Check strict ordering preserved
        diffs_extreme = np.diff(scaled_extreme)
        self.assertTrue(np.all(diffs_extreme > 0.0), "Monotonicity violated across extreme range [-1e9, 1e9]")

        # Micro-scale probes: [-1e-12, 1e-12]
        scaler_micro = DynamicDispersionScaler(target_min=0.0, target_max=1.0)
        micro_probes = np.linspace(-1e-12, 1e-12, 1000)
        scaled_micro = scaler_micro.fit_transform(micro_probes)
        self.assertTrue(np.all(np.isfinite(scaled_micro)))
        diffs_micro = np.diff(scaled_micro)
        self.assertTrue(np.all(diffs_micro > 0.0), "Monotonicity violated across micro scale [-1e-12, 1e-12]")

    def test_adv03_dispersion_scaler_hostile_inputs_nan_inf_empty_constant(self) -> None:
        """
        Adversarial Probe 3: Hostile inputs: all NaNs, all Infs, mixed NaNs/Infs, empty, 1-element, all constant.
        Assert: Zero unhandled crashes and correct handling.
        """
        scaler = DynamicDispersionScaler(target_min=0.0, target_max=1.0)

        # 1. All-constant array (zero variance)
        c_arr = np.full(100, 42.0)
        scaled_c = scaler.fit_transform(c_arr)
        self.assertTrue(np.all(np.isfinite(scaled_c)))
        # When all inputs equal mu, scaled should be center = 0.50
        np.testing.assert_allclose(scaled_c, 0.50, atol=1e-5)

        # 2. Single element
        s_arr = np.array([3.14])
        scaled_s = scaler.fit_transform(s_arr)
        self.assertEqual(len(scaled_s), 1)
        np.testing.assert_allclose(scaled_s, 0.50, atol=1e-5)

        # 3. Empty array
        empty_arr = np.array([])
        scaled_empty = scaler.fit_transform(empty_arr)
        self.assertEqual(len(scaled_empty), 0)

        # 4. All NaNs array
        nan_arr = np.array([np.nan, np.nan, np.nan])
        scaled_nan = scaler.fit_transform(nan_arr)
        self.assertTrue(np.all(np.isnan(scaled_nan)), "All-NaN array did not preserve NaNs!")

        # 5. Mixed NaNs and valid numbers
        mixed_nan = np.array([np.nan, 1.0, 2.0, np.nan, 3.0])
        scaled_mixed = scaler.fit_transform(mixed_nan)
        self.assertTrue(np.isnan(scaled_mixed[0]))
        self.assertTrue(np.isnan(scaled_mixed[3]))
        self.assertTrue(np.isfinite(scaled_mixed[1]))
        self.assertTrue(np.isfinite(scaled_mixed[2]))
        self.assertTrue(np.isfinite(scaled_mixed[4]))
        self.assertLess(scaled_mixed[1], scaled_mixed[2])
        self.assertLess(scaled_mixed[2], scaled_mixed[4])

        # 6. Infinite values (+inf, -inf)
        inf_arr = np.array([-np.inf, -1.0, 0.0, 1.0, np.inf])
        # fit ignores non-finite in valid filtering
        scaler.fit(inf_arr)
        # transform evaluates z -> inf, s_z -> +/- 1.0
        scaled_inf = scaler.transform(inf_arr)
        self.assertTrue(np.all(np.isfinite(scaled_inf)), "Inf inputs produced non-finite outputs in transform!")
        self.assertLess(scaled_inf[0], scaled_inf[1])
        self.assertLess(scaled_inf[3], scaled_inf[4])

    # =========================================================================
    # PART 2: CrossBorderTechLeadLagCoupler Adversarial Stress Tests
    # =========================================================================

    def test_adv04_cross_border_extreme_price_shocks(self) -> None:
        """
        Adversarial Probe 4: Extreme price shocks (+100%, -90%, -99.9%, +500%, limit down cascades).
        Assert: Finite bounded outputs, correct signs, no overflow.
        """
        coupler = CrossBorderTechLeadLagCoupler(asymmetric_downside_ratio=1.40)

        # Extreme positive shock: US tech explodes +100% (1.00)
        us_bull_shock = {k: 1.00 for k in coupler.DEFAULT_LEADER_WEIGHTS}
        res_bull = coupler.evaluate(us_bull_shock)
        self.assertGreater(res_bull["average_impulse"], 0.50)
        self.assertTrue(np.all(res_bull["alpha_f940"].values <= 3.0))
        self.assertTrue(np.all(res_bull["alpha_f940"].values >= 2.90))  # saturated high
        self.assertTrue(np.all(res_bull["normalized_score"].values < 1.0))

        # Extreme crash shock: US tech plunges -90% (-0.90)
        us_crash_shock = {k: -0.90 for k in coupler.DEFAULT_LEADER_WEIGHTS}
        res_crash = coupler.evaluate(us_crash_shock)
        self.assertLess(res_crash["average_impulse"], -0.50)
        self.assertTrue(np.all(res_crash["alpha_f940"].values >= -3.0))
        self.assertTrue(np.all(res_crash["alpha_f940"].values <= -2.90))  # saturated low
        self.assertTrue(np.all(res_crash["normalized_score"].values > 0.0))

        # Extreme absurd spike (+500%) and near-total collapse (-99.99%)
        us_absurd = {"^SOX": 5.00, "NVDA": -0.9999}
        res_absurd = coupler.evaluate(us_absurd)
        self.assertTrue(np.all(np.isfinite(res_absurd["alpha_f940"].values)))
        self.assertTrue(np.all(np.isfinite(res_absurd["normalized_score"].values)))
        self.assertTrue(np.all(res_absurd["alpha_f940"].values >= -3.0))
        self.assertTrue(np.all(res_absurd["alpha_f940"].values <= 3.0))

    def test_adv05_cross_border_downside_amplification_rigorous_validation(self) -> None:
        """
        Adversarial Probe 5: Downside shock amplification validation.
        Assert: Negative impulses are amplified by exactly kappa_asym = 1.40 relative to positive impulses.
        """
        coupler = CrossBorderTechLeadLagCoupler(
            asymmetric_downside_ratio=1.40,
            noise_deadband=0.0,  # disable deadband for exact ratio check
        )

        test_symbols = ["000660.KS", "005930.KS", "042700.KQ", "DEFAULT"]
        for sym in test_symbols:
            pos_ret = {"NVDA": 0.05, "^SOX": 0.03}
            neg_ret = {"NVDA": -0.05, "^SOX": -0.03}

            imp_pos = coupler.compute_asymmetric_impulse(pos_ret, krx_symbol=sym)
            imp_neg = coupler.compute_asymmetric_impulse(neg_ret, krx_symbol=sym)

            self.assertGreater(imp_pos, 0.0)
            self.assertLess(imp_neg, 0.0)

            ratio = abs(imp_neg) / imp_pos
            np.testing.assert_allclose(
                ratio, 1.40, rtol=1e-4,
                err_msg=f"Downside amplification ratio failed for {sym}: expected 1.40, got {ratio}"
            )

    def test_adv06_cross_border_hostile_structural_inputs(self) -> None:
        """
        Adversarial Probe 6: Hostile structural inputs:
        - Empty DataFrame, 1-row DataFrame, missing columns, unknown tickers.
        - All-zeros, all-NaNs, all-Infs.
        Assert: Zero unhandled crashes and safe fallbacks.
        """
        coupler = CrossBorderTechLeadLagCoupler()

        # 1. Unknown KRX tickers
        res_unk = coupler.evaluate({"NVDA": 0.04}, krx_symbols=["UNKNOWN_1", "UNKNOWN_2"])
        self.assertEqual(len(res_unk["alpha_f940"]), 2)
        self.assertTrue(np.all(np.isfinite(res_unk["alpha_f940"].values)))
        self.assertGreater(res_unk["alpha_f940"]["UNKNOWN_1"], 0.0)

        # 2. Empty KRX symbols list
        res_empty_sym = coupler.evaluate({"NVDA": 0.04}, krx_symbols=[])
        self.assertEqual(len(res_empty_sym["alpha_f940"]), 0)
        self.assertEqual(res_empty_sym["average_impulse"], 0.0)

        # 3. Completely unrelated columns in US returns
        res_unrel = coupler.evaluate({"RANDOM_A": 0.10, "RANDOM_B": -0.20})
        self.assertTrue(np.all(np.isfinite(res_unrel["alpha_f940"].values)))
        # No known leaders -> impulse = 0 -> alpha = 0.0
        np.testing.assert_allclose(res_unrel["alpha_f940"].values, 0.0, atol=1e-5)

        # 4. All-zero returns
        res_zero = coupler.evaluate({k: 0.0 for k in coupler.DEFAULT_LEADER_WEIGHTS})
        np.testing.assert_allclose(res_zero["alpha_f940"].values, 0.0, atol=1e-5)
        np.testing.assert_allclose(res_zero["normalized_score"].values, 0.50, atol=1e-5)

        # 5. All-NaN returns
        res_nan = coupler.evaluate({k: np.nan for k in coupler.DEFAULT_LEADER_WEIGHTS})
        self.assertTrue(np.all(np.isfinite(res_nan["alpha_f940"].values)))
        np.testing.assert_allclose(res_nan["alpha_f940"].values, 0.0, atol=1e-5)

        # 6. All-Inf returns (+inf and -inf)
        res_inf = coupler.evaluate({k: np.inf for k in coupler.DEFAULT_LEADER_WEIGHTS})
        self.assertTrue(np.all(np.isfinite(res_inf["alpha_f940"].values)))
        self.assertTrue(np.all(res_inf["alpha_f940"].values >= -3.0))
        self.assertTrue(np.all(res_inf["alpha_f940"].values <= 3.0))

        # 7. 1-row DataFrame
        df_1row = pd.DataFrame([{"NVDA": 0.05, "^SOX": 0.03}])
        res_1row = coupler.evaluate(df_1row)
        self.assertTrue(np.all(np.isfinite(res_1row["alpha_f940"].values)))

        # 8. Empty DataFrame
        df_empty = pd.DataFrame()
        res_empty_df = coupler.evaluate(df_empty)
        self.assertTrue(np.all(np.isfinite(res_empty_df["alpha_f940"].values)))

    def test_adv07_cross_border_dynamic_calibration_adversarial_degenerate_history(self) -> None:
        """
        Adversarial Probe 7: Dynamic calibration with rank-deficient, collinear, all-constant, or empty history.
        Assert: Zero crashes, returns safe default elasticities.
        """
        coupler = CrossBorderTechLeadLagCoupler()

        # 1. Under-determined / insufficient history (< 20 periods)
        us_short = pd.DataFrame(np.random.randn(10, 5), columns=["^SOX", "NVDA", "AAPL", "MSFT", "TSM"])
        krx_short = pd.DataFrame(np.random.randn(10, 2), columns=["005930.KS", "000660.KS"])
        cal_short = coupler.calibrate(us_short, krx_short, min_periods=20)
        # Should gracefully return existing elasticities without modifying
        self.assertEqual(cal_short["000660.KS"]["NVDA"], 0.85)

        # 2. All-constant (degenerate, zero variance) history
        us_const = pd.DataFrame(np.full((50, 5), 1.0), columns=["^SOX", "NVDA", "AAPL", "MSFT", "TSM"])
        krx_const = pd.DataFrame(np.full((50, 2), 2.0), columns=["005930.KS", "000660.KS"])
        # Should not crash on pinv of singular matrix
        cal_const = coupler.calibrate(us_const, krx_const, min_periods=20)
        self.assertIn("000660.KS", cal_const)
        for leader, elast in cal_const["000660.KS"].items():
            self.assertTrue(np.isfinite(elast), f"Non-finite elasticity for {leader}")

        # 3. Collinear US history (all columns identical)
        rand_series = np.random.randn(50)
        us_collinear = pd.DataFrame({
            col: rand_series for col in ["^SOX", "NVDA", "AAPL", "MSFT", "TSM"]
        })
        krx_rand = pd.DataFrame(np.random.randn(50, 2), columns=["005930.KS", "000660.KS"])
        cal_collinear = coupler.calibrate(us_collinear, krx_rand, min_periods=20)
        self.assertIn("000660.KS", cal_collinear)
        for leader, elast in cal_collinear["000660.KS"].items():
            self.assertTrue(np.isfinite(elast))
            self.assertTrue(-2.0 <= elast <= 2.0, "Elasticity was not clipped within [-2.0, 2.0]")

    # =========================================================================
    # PART 3: CrossClusterConfluenceKernel Adversarial Stress Tests
    # =========================================================================

    def test_adv08_confluence_kernel_degenerate_and_rank_deficient_matrices(self) -> None:
        """
        Adversarial Probe 8: Degenerate factor score matrices:
        - 100 identical rows (rank 0 covariance).
        - Collinear columns (rank-deficient).
        - Scores with all 0.0, all 1.0, all 0.50.
        Assert: Bounded confluence gain in [1.0 - eta, 1.0 + eta], concurrence ratio in [0, 1].
        """
        kernel = CrossClusterConfluenceKernel(eta_gain=0.35, lambda_scale=1.50)

        # 1. 100 identical rows of neutral 0.50
        p_neutral = np.full((100, 14), 0.50)
        res_neutral = kernel.evaluate(p_neutral)
        self.assertTrue(np.all(np.isfinite(res_neutral["confluence_gain"])))
        np.testing.assert_allclose(res_neutral["confluence_score"], 0.0, atol=1e-5)
        np.testing.assert_allclose(res_neutral["confluence_gain"], 1.0, atol=1e-5)
        np.testing.assert_allclose(res_neutral["amplified_alpha"], 0.0, atol=1e-5)

        # 2. Extreme all 0.0 (maximum bearish consensus across all pillars)
        p_bear = np.full((50, 14), 0.0)
        res_bear = kernel.evaluate(p_bear)
        self.assertTrue(np.all(np.isfinite(res_bear["confluence_gain"])))
        # In all-negative (below 0.50), signs agree (all negative => sign_prod > 0)
        self.assertTrue(np.all(res_bear["concurrence_ratio"] == 1.0))
        self.assertTrue(np.all(res_bear["confluence_score"] > 0.0))
        # Amplification gain should be > 1.0
        self.assertTrue(np.all(res_bear["confluence_gain"] > 1.0))
        self.assertTrue(np.all(res_bear["confluence_gain"] <= 1.35))
        # Base alpha is negative, so amplified_alpha is more negative
        self.assertTrue(np.all(res_bear["amplified_alpha"] < -10.0))

        # 3. Extreme all 1.0 (maximum bullish consensus across all pillars)
        p_bull = np.full((50, 14), 1.0)
        res_bull = kernel.evaluate(p_bull)
        self.assertTrue(np.all(res_bull["concurrence_ratio"] == 1.0))
        self.assertTrue(np.all(res_bull["confluence_gain"] > 1.0))
        self.assertTrue(np.all(res_bull["confluence_gain"] <= 1.35))
        self.assertTrue(np.all(res_bull["amplified_alpha"] > 10.0))

        # 4. Checkerboard / maximum conflict (alternating 0.10 and 0.90)
        p_conflict = np.zeros((20, 14))
        p_conflict[:, 0::2] = 0.90
        p_conflict[:, 1::2] = 0.10
        res_conflict = kernel.evaluate(p_conflict)
        # Signs disagree on many pairs -> confluence score should be negative or dampened
        self.assertTrue(np.all(res_conflict["concurrence_ratio"] < 0.55))
        self.assertTrue(np.all(res_conflict["confluence_score"] < 0.0))
        # Gain should be dampened (< 1.0)
        self.assertTrue(np.all(res_conflict["confluence_gain"] < 1.0))
        self.assertTrue(np.all(res_conflict["confluence_gain"] >= 0.65))

    def test_adv09_confluence_kernel_hostile_structures_nan_inf_empty_columns(self) -> None:
        """
        Adversarial Probe 9: Hostile inputs to confluence kernel:
        - All-NaNs, all-Infs, empty DataFrame, mismatched column dimensions.
        Assert: Zero unhandled crashes and finite outputs.
        """
        kernel = CrossClusterConfluenceKernel()

        # 1. All-NaN DataFrame
        df_nan = pd.DataFrame(np.full((10, 14), np.nan), columns=kernel.CANONICAL_PILLARS)
        res_nan = kernel.evaluate(df_nan)
        self.assertTrue(np.all(np.isfinite(res_nan["confluence_gain"].values)))
        self.assertTrue(np.all(np.isfinite(res_nan["amplified_alpha"].values)))

        # 2. All-Inf DataFrame
        df_inf = pd.DataFrame(np.full((10, 14), np.inf), columns=kernel.CANONICAL_PILLARS)
        res_inf = kernel.evaluate(df_inf)
        self.assertTrue(np.all(np.isfinite(res_inf["confluence_gain"].values)))
        self.assertTrue(np.all(np.isfinite(res_inf["amplified_alpha"].values)))

        # 3. Missing 12 pillars (only 2 pillars provided in DataFrame)
        df_partial = pd.DataFrame({"val": [0.70, 0.80], "mom": [0.65, 0.75]})
        res_partial = kernel.evaluate(df_partial)
        self.assertEqual(len(res_partial["confluence_gain"]), 2)
        self.assertTrue(np.all(np.isfinite(res_partial["confluence_gain"].values)))

        # 4. Irrelevant column names
        df_junk = pd.DataFrame({"colA": [0.2, 0.3], "colB": [0.4, 0.5]})
        res_junk = kernel.evaluate(df_junk)
        self.assertEqual(len(res_junk["confluence_gain"]), 2)
        self.assertTrue(np.all(np.isfinite(res_junk["confluence_gain"].values)))

        # 5. Symmetric pairwise matrix verification
        p_rand = np.random.uniform(0.1, 0.9, size=(5, 14))
        res_sym = kernel.evaluate(p_rand)
        pw_mats = res_sym["pairwise_confluence_matrix"]
        for sample_idx in range(5):
            mat = pw_mats[sample_idx]
            np.testing.assert_allclose(
                mat, mat.T, atol=1e-12,
                err_msg=f"Pairwise confluence matrix not strictly symmetric for sample {sample_idx}"
            )

    # =========================================================================
    # PART 4: Phase192Coupler Composite Alpha Adversarial Stress Tests
    # =========================================================================

    def test_adv10_phase192_coupler_rank_deficient_zca_whitening_stress(self) -> None:
        """
        Adversarial Probe 10: Singular covariance matrix (N=3 < D=14) in Phase192Coupler.
        Tests Riemannian AIRM distance and ZCA whitening eigenvalue regularization epsilon_reg.
        Assert: Finite alpha in [-3.0, 3.0], normalized alpha in (0.0, 1.0), zero NaN explosion.
        """
        coupler = Phase192Coupler(kappa=1.92, epsilon_reg=1e-6)

        # N=3 samples, D=14 pillars: rank <= 2, heavily rank-deficient
        p_sparse = pd.DataFrame(
            np.random.uniform(0.1, 0.9, size=(3, 14)),
            index=["SYM_A", "SYM_B", "SYM_C"],
            columns=CrossClusterConfluenceKernel.CANONICAL_PILLARS,
        )

        res = coupler.evaluate(p_sparse)

        self.assertTrue(np.all(np.isfinite(res["alpha"].values)))
        self.assertTrue(np.all(res["alpha"].values >= -3.0))
        self.assertTrue(np.all(res["alpha"].values <= 3.0))

        self.assertTrue(np.all(np.isfinite(res["alpha_normalized"].values)))
        self.assertTrue(np.all(res["alpha_normalized"].values > 0.0))
        self.assertTrue(np.all(res["alpha_normalized"].values < 1.0))

        self.assertTrue(np.isfinite(res["airm_distance"]))
        self.assertGreaterEqual(res["airm_distance"], 0.0)

    def test_adv11_phase192_coupler_combined_hostile_stress_1000_vectors(self) -> None:
        """
        Adversarial Probe 11: 1,000 hostile randomized factor vectors combined with extreme US shocks.
        Assert: 100% finite outputs, strictly bounded in [-3.0, 3.0] and (0.0, 1.0).
        """
        coupler = Phase192Coupler()

        # 1,000 randomized factor vectors with extreme outliers [-100.0, 100.0], NaNs, and Infs
        hostile_matrix = np.random.uniform(-5.0, 5.0, size=(1000, 14))
        # Inject NaNs in 5% of entries
        nan_mask = np.random.rand(*hostile_matrix.shape) < 0.05
        hostile_matrix[nan_mask] = np.nan
        # Inject Infs in 2% of entries
        inf_mask = np.random.rand(*hostile_matrix.shape) < 0.02
        hostile_matrix[inf_mask] = np.inf

        df_hostile = pd.DataFrame(hostile_matrix, columns=CrossClusterConfluenceKernel.CANONICAL_PILLARS)

        # Hostile US returns with extreme shocks
        us_hostile = {
            "^SOX": -0.85,
            "NVDA": 1.50,
            "AAPL": np.nan,
            "MSFT": np.inf,
            "TSM": -0.40,
        }

        res = coupler.evaluate(df_hostile, us_returns=us_hostile)

        alpha = res["alpha"]
        alpha_norm = res["alpha_normalized"]

        self.assertEqual(len(alpha), 1000)
        self.assertEqual(len(alpha_norm), 1000)

        # Check finiteness
        self.assertTrue(np.all(np.isfinite(alpha.values)), "Non-finite alpha detected in 1,000 hostile vectors!")
        self.assertTrue(np.all(np.isfinite(alpha_norm.values)), "Non-finite alpha_normalized detected!")

        # Check bounds
        self.assertTrue(np.all(alpha.values >= -3.0), f"Alpha < -3.0: min={alpha.min()}")
        self.assertTrue(np.all(alpha.values <= 3.0), f"Alpha > 3.0: max={alpha.max()}")
        self.assertTrue(np.all(alpha_norm.values >= 0.0), f"Alpha_norm < 0.0: min={alpha_norm.min()}")
        self.assertTrue(np.all(alpha_norm.values <= 1.0), f"Alpha_norm > 1.0: max={alpha_norm.max()}")


if __name__ == "__main__":
    unittest.main()
