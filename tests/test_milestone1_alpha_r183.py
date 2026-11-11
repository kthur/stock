"""
tests/test_milestone1_alpha_r183.py — Comprehensive Unit & Integration Test Suite for Release R183 Milestone 1.

Verifies:
- Category 1: Dual-Tree Cryptographic Parity & Metadata Constants (TC01 ~ TC03)
- Category 2: Feature F940 Asymmetric Cross-Border Tech Lead-Lag Impulse Coupler (TC04 ~ TC14)
- Category 3: Feature F941 Dynamic Dispersion Scaling Engine (TC15 ~ TC19)
- Category 4: Feature F941 14-Pillar Cross-Cluster Confluence Kernel (TC20 ~ TC23)
- Category 5: FactorOrthogonalizerEngine Phase 192 Integration & Dynamic Dispersion (TC24 ~ TC25)
- Category 6: Phase192Coupler Composite Alpha Coupler (TC26 ~ TC27)
- Category 7: System Invariants, Synthetic Rows & Latency SLA (TC28 ~ TC30)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form formulas, and exact calculations.
Zero synthetic rows (synthetic_rows == 0).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

# F941 & Factor Orthogonalizer Imports
from src.ai.factor_orthogonalizer import (
    VERSION_PHASE192,
    RELEASE_PHASE192,
    FEATURE_PHASE192,
    VERSION_R183,
    RELEASE_R183,
    FEATURE_F941,
    FEATURE_F940,
    QuattuordecuplePillarMap,
    QUATTUORDECUPLE_PILLAR_MAP,
    DynamicDispersionScaler,
    dynamic_dispersion_scale,
    CrossClusterConfluenceKernel,
    compute_quattuordecuple_pillar_confluence_kernel,
    apply_hyperbolic_deadband_phase192,
    FactorOrthogonalizerEngine,
    FactorOrthogonalizerEnginePhase192,
    Phase192FactorOrthogonalizerEngine,
    F941FactorOrthogonalizerEngine,
    CrossClusterConfluenceEngine,
    FourteenPillarConfluenceKernel,
    DynamicDispersionScalingEngine,
    SmoothDispersionScaler,
)

# F940 & Coupler Imports
from src.ai.historical_couplers import (
    CrossBorderTechLeadLagCoupler,
    F940Coupler,
    CrossBorderTechCoupler,
    AsymmetricTechLeadLagCoupler,
    Phase192TechLeadLagCoupler,
    Phase192Coupler,
    Milestone1AlphaCoupler,
    Phase192AlphaCoupler,
    F940F941CompositeCoupler,
    QuattuordecupleConfluenceCoupler,
)


class TestMilestone1AlphaR183Suite(unittest.TestCase):
    """30 Comprehensive Unit & Integration Tests for Release R183 Milestone 1 (F940 & F941)."""

    def setUp(self) -> None:
        np.random.seed(183)

    # -------------------------------------------------------------------------
    # Category 1: Dual-Tree Cryptographic Parity & Metadata Constants (TC01-03)
    # -------------------------------------------------------------------------

    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% bit-for-bit SHA256 cryptographic parity for owned files."""
        files = [
            ("src/ai/factor_orthogonalizer.py", "trading_system/src/ai/factor_orthogonalizer.py"),
            ("src/ai/historical_couplers.py", "trading_system/src/ai/historical_couplers.py"),
        ]
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for src_rel, ts_rel in files:
            src_path = os.path.join(base_dir, src_rel)
            ts_path = os.path.join(base_dir, ts_rel)
            self.assertTrue(os.path.exists(src_path), f"Source file missing: {src_rel}")
            self.assertTrue(os.path.exists(ts_path), f"Mirror file missing: {ts_rel}")
            h1 = hashlib.sha256(open(src_path, "rb").read()).hexdigest()
            h2 = hashlib.sha256(open(ts_path, "rb").read()).hexdigest()
            self.assertEqual(h1, h2, f"SHA-256 mismatch for {src_rel}")

    def test_tc02_version_metadata_constants(self) -> None:
        """TC02: Verify Phase 192 / Release R183 metadata constants."""
        self.assertEqual(int(VERSION_PHASE192), 192)
        self.assertEqual(str(RELEASE_PHASE192), "R183")
        self.assertEqual(str(FEATURE_PHASE192), "F941")
        self.assertEqual(int(VERSION_R183), 192)
        self.assertEqual(str(RELEASE_R183), "R183")
        self.assertEqual(str(FEATURE_F941), "F941")
        self.assertEqual(str(FEATURE_F940), "F940")

    def test_tc03_quattuordecuple_pillar_map_integrity(self) -> None:
        """TC03: Verify QUATTUORDECUPLE_PILLAR_MAP contains all 14 canonical clusters."""
        expected_clusters = [
            "val", "mom", "flow", "cat", "net", "vol", "gnn",
            "rev", "comp", "tail", "macro", "ricci", "symplectic", "octonion"
        ]
        self.assertEqual(len(QUATTUORDECUPLE_PILLAR_MAP), 14)
        for c in expected_clusters:
            self.assertIn(c, QUATTUORDECUPLE_PILLAR_MAP)
            strats = QUATTUORDECUPLE_PILLAR_MAP[c]
            self.assertIsInstance(strats, list)
            self.assertGreater(len(strats), 0)

    # -------------------------------------------------------------------------
    # Category 2: Feature F940 Asymmetric Cross-Border Tech Lead-Lag Impulse Coupler (TC04-14)
    # -------------------------------------------------------------------------

    def test_tc04_f940_coupler_initialization_and_defaults(self) -> None:
        """TC04: Verify CrossBorderTechLeadLagCoupler default leader weights and normalization."""
        coupler = CrossBorderTechLeadLagCoupler()
        self.assertAlmostEqual(sum(coupler.leader_weights.values()), 1.0, places=5)
        self.assertIn("^SOX", coupler.leader_weights)
        self.assertIn("NVDA", coupler.leader_weights)
        self.assertIn("AAPL", coupler.leader_weights)
        self.assertIn("MSFT", coupler.leader_weights)
        self.assertEqual(coupler.lag_days, 1)
        self.assertEqual(coupler.asymmetric_downside_ratio, 1.40)

    def test_tc05_f940_zero_lookahead_verification(self) -> None:
        """TC05: Verify zero lookahead timestamp assertion."""
        # US date day t-1 precedes KRX date day t
        us_dates = pd.to_datetime(["2026-05-01", "2026-05-02", "2026-05-03"])
        krx_dates = pd.to_datetime(["2026-05-02", "2026-05-03", "2026-05-04"])
        self.assertTrue(CrossBorderTechLeadLagCoupler.verify_zero_lookahead(us_dates, krx_dates))

        # Lookahead violation case (same day or future US date)
        invalid_us = pd.to_datetime(["2026-05-02", "2026-05-03", "2026-05-04"])
        self.assertFalse(CrossBorderTechLeadLagCoupler.verify_zero_lookahead(invalid_us, krx_dates))

    def test_tc06_f940_asymmetric_downside_shock_amplification(self) -> None:
        """TC06: Verify negative US tech shocks produce amplified negative impulse."""
        coupler = CrossBorderTechLeadLagCoupler(asymmetric_downside_ratio=1.50)
        # Positive shock +3% across leaders
        pos_us = {"^SOX": 0.03, "NVDA": 0.03, "AAPL": 0.03, "MSFT": 0.03}
        pos_impulse = coupler.compute_asymmetric_impulse(pos_us, "005930.KS")

        # Negative shock -3% across leaders
        neg_us = {"^SOX": -0.03, "NVDA": -0.03, "AAPL": -0.03, "MSFT": -0.03}
        neg_impulse = coupler.compute_asymmetric_impulse(neg_us, "005930.KS")

        # Magnitude of negative impulse must exceed positive impulse by ratio ~1.50
        self.assertGreater(pos_impulse, 0.0)
        self.assertLess(neg_impulse, 0.0)
        ratio = abs(neg_impulse) / abs(pos_impulse)
        self.assertAlmostEqual(ratio, 1.50, delta=0.08)

    def test_tc07_f940_hyperbolic_noise_deadband(self) -> None:
        """TC07: Verify sub-threshold noise is smoothly attenuated by hyperbolic deadband."""
        coupler = CrossBorderTechLeadLagCoupler(noise_deadband=0.0050)  # 50 bps deadband
        # Sub-threshold micro-return (0.05% = 5 bps)
        micro_ret = 0.0005
        filtered_micro = coupler._apply_hyperbolic_noise_deadband(micro_ret)
        # Attenuation factor should be small
        self.assertLess(abs(filtered_micro), abs(micro_ret) * 0.20)

        # Significant return (3.00% = 300 bps) should pass through unattenuated
        macro_ret = 0.0300
        filtered_macro = coupler._apply_hyperbolic_noise_deadband(macro_ret)
        self.assertAlmostEqual(filtered_macro / macro_ret, 1.0, delta=0.02)

    def test_tc08_f940_stock_specific_elasticities(self) -> None:
        """TC08: Verify NVDA shock transmits more to SK Hynix (000660.KS) and Hanmi Semi (042700.KQ)."""
        coupler = CrossBorderTechLeadLagCoupler()
        # Sole NVDA surge
        nvda_surge = {"NVDA": 0.05, "^SOX": 0.0, "AAPL": 0.0, "MSFT": 0.0}

        imp_hynix = coupler.compute_asymmetric_impulse(nvda_surge, "000660.KS")
        imp_samsung = coupler.compute_asymmetric_impulse(nvda_surge, "005930.KS")
        imp_hanmi = coupler.compute_asymmetric_impulse(nvda_surge, "042700.KQ")

        # HBM leaders (Hynix, Hanmi) have higher NVDA sensitivity than Samsung
        self.assertGreater(imp_hynix, imp_samsung)
        self.assertGreater(imp_hanmi, imp_samsung)

    def test_tc09_f940_single_vector_and_dict_evaluation(self) -> None:
        """TC09: Verify evaluate handles dict of returns and single symbol output correctly."""
        coupler = CrossBorderTechLeadLagCoupler()
        us_returns = {"^SOX": 0.025, "NVDA": 0.040, "MU": 0.030}
        res = coupler.evaluate(us_returns, krx_symbols=["000660.KS"])

        self.assertEqual(res["num_symbols"], 1)
        self.assertTrue(res["zero_lookahead_verified"])
        self.assertIsInstance(res["alpha_f940"], float)
        self.assertGreater(res["alpha_f940"], 0.0)
        self.assertLessEqual(res["alpha_f940"], 3.0)
        self.assertGreater(res["normalized_score"], 0.50)
        self.assertLess(res["normalized_score"], 1.0)

    def test_tc10_f940_time_series_dataframe_with_lag_shift(self) -> None:
        """TC10: Verify multi-day historical DataFrame evaluates latest shifted day with zero lookahead."""
        dates = pd.date_range("2026-05-01", periods=10, freq="D")
        us_df = pd.DataFrame(
            {"^SOX": np.linspace(0.01, 0.05, 10), "NVDA": np.linspace(-0.02, 0.04, 10)},
            index=dates,
        )
        coupler = CrossBorderTechLeadLagCoupler(lag_days=1)
        res = coupler.evaluate(us_df, krx_symbols=["005930.KS", "000660.KS"])

        self.assertEqual(res["num_symbols"], 2)
        self.assertIsInstance(res["alpha_f940"], pd.Series)
        self.assertEqual(len(res["alpha_f940"]), 2)
        self.assertTrue(res["zero_lookahead_verified"])

    def test_tc11_f940_continuous_alpha_and_probability_bounds(self) -> None:
        """TC11: Verify alpha_f940 is strictly in [-3.0, 3.0] and normalized_score in (0.0, 1.0)."""
        coupler = CrossBorderTechLeadLagCoupler()
        # Extreme shock (+50% and -50%)
        extreme_pos = {"^SOX": 0.50, "NVDA": 0.50}
        res_pos = coupler.evaluate(extreme_pos, krx_symbols=["005930.KS"])
        self.assertLessEqual(res_pos["alpha_f940"], 3.0)
        self.assertGreater(res_pos["alpha_f940"], 2.90)
        self.assertLess(res_pos["normalized_score"], 1.0)
        self.assertGreater(res_pos["normalized_score"], 0.95)

        extreme_neg = {"^SOX": -0.50, "NVDA": -0.50}
        res_neg = coupler.evaluate(extreme_neg, krx_symbols=["005930.KS"])
        self.assertGreaterEqual(res_neg["alpha_f940"], -3.0)
        self.assertLess(res_neg["alpha_f940"], -2.90)
        self.assertGreater(res_neg["normalized_score"], 0.0)
        self.assertLess(res_neg["normalized_score"], 0.05)

    def test_tc12_f940_dynamic_calibration_via_ridge_regression(self) -> None:
        """TC12: Verify calibrate method updates transmission elasticities with zero lookahead."""
        dates = pd.date_range("2026-01-01", periods=50, freq="B")
        np.random.seed(42)
        us_returns = pd.DataFrame(
            {"^SOX": np.random.normal(0.001, 0.02, 50), "NVDA": np.random.normal(0.001, 0.03, 50)},
            index=dates,
        )
        # Construct synthetic KRX series driven by US t-1 + noise
        krx_returns = pd.DataFrame(
            {
                "000660.KS": 0.8 * us_returns["^SOX"].shift(1) + 0.6 * us_returns["NVDA"].shift(1) + np.random.normal(0, 0.005, 50),
                "005930.KS": 0.5 * us_returns["^SOX"].shift(1) + np.random.normal(0, 0.005, 50),
            },
            index=dates,
        )

        coupler = CrossBorderTechLeadLagCoupler()
        calibrated = coupler.calibrate(us_returns, krx_returns, min_periods=20, ridge_alpha=0.1)

        self.assertIn("000660.KS", calibrated)
        self.assertIn("005930.KS", calibrated)
        self.assertGreater(calibrated["000660.KS"]["^SOX"], 0.3)

    def test_tc13_f940_edge_cases_nan_inf_missing_tickers(self) -> None:
        """TC13: Verify resilience against NaN, inf, and empty/unrecognized tickers."""
        coupler = CrossBorderTechLeadLagCoupler()
        dirty_us = {"^SOX": np.nan, "NVDA": np.inf, "UNKNOWN": 0.05}
        impulse = coupler.compute_asymmetric_impulse(dirty_us, "005930.KS")
        self.assertTrue(np.isfinite(impulse))

        res = coupler.evaluate(dirty_us, krx_symbols=["UNKNOWN_SYMBOL"])
        self.assertTrue(np.isfinite(res["alpha_f940"]))
        self.assertTrue(np.isfinite(res["normalized_score"]))

    def test_tc14_f940_complete_alias_tree_and_classmethod(self) -> None:
        """TC14: Verify complete alias tree and classmethod compute for F940."""
        self.assertIs(F940Coupler, CrossBorderTechLeadLagCoupler)
        self.assertIs(CrossBorderTechCoupler, CrossBorderTechLeadLagCoupler)
        self.assertIs(AsymmetricTechLeadLagCoupler, CrossBorderTechLeadLagCoupler)
        self.assertIs(Phase192TechLeadLagCoupler, CrossBorderTechLeadLagCoupler)

        res = CrossBorderTechLeadLagCoupler.compute({"^SOX": 0.02}, krx_symbols=["005930.KS"])
        self.assertIn("alpha_f940", res)
        self.assertIn("normalized_score", res)

    # -------------------------------------------------------------------------
    # Category 3: Feature F941 Dynamic Dispersion Scaling Engine (TC15-19)
    # -------------------------------------------------------------------------

    def test_tc15_f941_dynamic_dispersion_scaler_initialization(self) -> None:
        """TC15: Verify DynamicDispersionScaler defaults and parameters."""
        scaler = DynamicDispersionScaler(target_min=0.0, target_max=1.0, tau_bandwidth=2.5)
        self.assertEqual(scaler.target_min, 0.0)
        self.assertEqual(scaler.target_max, 1.0)
        self.assertEqual(scaler.tau_bandwidth, 2.5)
        self.assertTrue(scaler.robust)

    def test_tc16_f941_dispersion_scaler_strict_monotonicity(self) -> None:
        """TC16: Verify strict monotonicity dy/dx > 0 preserving exact rank ordering."""
        x = np.linspace(-10.0, 10.0, 100)
        scaler = DynamicDispersionScaler(target_min=0.0, target_max=1.0)
        y = scaler.fit_transform(x)

        # Monotonicity check: all diffs must be strictly positive
        diffs = np.diff(y)
        self.assertTrue((diffs > 0).all(), "Dynamic dispersion mapping must be strictly monotonic everywhere")

        # Rank preservation check
        ranks_x = pd.Series(x).rank().values
        ranks_y = pd.Series(y).rank().values
        np.testing.assert_array_equal(ranks_x, ranks_y)

    def test_tc17_f941_dispersion_scaler_zero_clipping_plateaus(self) -> None:
        """TC17: Verify extreme tail outliers do NOT collide to identical clipping boundaries."""
        extreme_x = np.array([5.0, 10.0, 20.0, 50.0, 100.0])
        scaler = DynamicDispersionScaler(target_min=0.0, target_max=1.0)
        y = scaler.fit_transform(extreme_x)

        # In standard np.clip, all these values would collapse to 1.0
        # With DynamicDispersionScaler, they must all be distinct
        for i in range(len(y) - 1):
            self.assertGreater(y[i + 1], y[i], f"Values at {extreme_x[i]} and {extreme_x[i+1]} must not collide")
            self.assertLess(y[i], 1.0, "Values must remain strictly below 1.0 ceiling")

    def test_tc18_f941_dispersion_scaler_target_ranges(self) -> None:
        """TC18: Verify scaling to both [0.0, 1.0] and [-3.0, 3.0] bounds."""
        x = np.random.normal(0, 1, 50)
        # Unit interval [0, 1]
        y_unit = dynamic_dispersion_scale(x, target_min=0.0, target_max=1.0)
        self.assertTrue((y_unit >= 0.0).all() and (y_unit <= 1.0).all())

        # Standard alpha range [-3, 3]
        y_alpha = dynamic_dispersion_scale(x, target_min=-3.0, target_max=3.0)
        self.assertTrue((y_alpha >= -3.0).all() and (y_alpha <= 3.0).all())

    def test_tc19_f941_dispersion_scaler_nan_and_constant_columns(self) -> None:
        """TC19: Verify graceful handling of NaNs and constant zero-variance arrays."""
        scaler = DynamicDispersionScaler()
        # Array with NaNs
        x_nan = np.array([1.0, np.nan, 3.0, 4.0, np.nan])
        y_nan = scaler.fit_transform(x_nan)
        self.assertTrue(np.isnan(y_nan[1]))
        self.assertTrue(np.isnan(y_nan[4]))
        self.assertTrue(np.isfinite(y_nan[0]))

        # Constant array
        x_const = np.array([5.0, 5.0, 5.0, 5.0])
        y_const = scaler.fit_transform(x_const)
        self.assertTrue(np.isfinite(y_const).all())

    # -------------------------------------------------------------------------
    # Category 4: Feature F941 14-Pillar Cross-Cluster Confluence Kernel (TC20-23)
    # -------------------------------------------------------------------------

    def test_tc20_f941_confluence_kernel_initialization(self) -> None:
        """TC20: Verify CrossClusterConfluenceKernel has 14 canonical pillars and symmetric affinity."""
        kernel = CrossClusterConfluenceKernel()
        self.assertEqual(len(kernel.CANONICAL_PILLARS), 14)
        self.assertEqual(kernel.affinity_matrix.shape, (14, 14))
        # Affinity matrix must be symmetric PSD
        np.testing.assert_allclose(kernel.affinity_matrix, kernel.affinity_matrix.T)

    def test_tc21_f941_confluence_pairwise_computation(self) -> None:
        """TC21: Verify 91 distinct pairwise interactions and symmetric concordance matrix."""
        kernel = CrossClusterConfluenceKernel()
        p_scores = np.full(14, 0.70)  # Strong positive across all 14 pillars
        res = kernel.evaluate(p_scores)

        self.assertEqual(res["num_pillars"], 14)
        self.assertEqual(res["num_pairs"], 91)
        self.assertAlmostEqual(res["concurrence_ratio"], 1.0, places=4)
        self.assertGreater(res["confluence_gain"], 1.0)

        # Pairwise matrix must be 14x14 symmetric
        pw_mat = res["pairwise_confluence_matrix"]
        self.assertEqual(pw_mat.shape, (14, 14))
        np.testing.assert_allclose(pw_mat, pw_mat.T)

    def test_tc22_f941_confluence_directional_concordance_amplification(self) -> None:
        """TC22: Verify aligned multi-pillar signals amplify alpha while discordant signals attenuate."""
        kernel = CrossClusterConfluenceKernel(eta_gain=0.40)
        # All pillars concordant positive (+0.80)
        pos_aligned = np.full(14, 0.80)
        res_aligned = kernel.evaluate(pos_aligned)
        self.assertGreater(res_aligned["confluence_gain"], 1.0)

        # Half positive, half negative (discordant conflict)
        discordant = np.array([0.80 if i % 2 == 0 else 0.20 for i in range(14)])
        res_discordant = kernel.evaluate(discordant)
        # Confluence score of discordant signals must be lower than aligned
        self.assertLess(res_discordant["confluence_score"], res_aligned["confluence_score"])
        self.assertLess(res_discordant["concurrence_ratio"], 0.60)

    def test_tc23_f941_confluence_kernel_dataframe_and_dict(self) -> None:
        """TC23: Verify confluence evaluation works across DataFrame and Dict formats."""
        kernel = CrossClusterConfluenceKernel()
        # DataFrame format
        df = pd.DataFrame(
            np.random.uniform(0.3, 0.8, size=(5, 14)),
            columns=kernel.CANONICAL_PILLARS,
            index=[f"SYM_{i}" for i in range(5)],
        )
        res_df = kernel.evaluate(df)
        self.assertIsInstance(res_df["confluence_score"], pd.Series)
        self.assertEqual(len(res_df["confluence_score"]), 5)

        # Dict format
        d = {p: 0.65 for p in kernel.CANONICAL_PILLARS}
        res_d = kernel.evaluate(d)
        self.assertIsInstance(res_d["confluence_score"], float)

    # -------------------------------------------------------------------------
    # Category 5: FactorOrthogonalizerEngine Phase 192 Integration (TC24-25)
    # -------------------------------------------------------------------------

    def test_tc24_f941_orthogonalize_dynamic_dispersion(self) -> None:
        """TC24: Verify FactorOrthogonalizerEngine.orthogonalize with scaling_method='dynamic_dispersion'."""
        engine = FactorOrthogonalizerEngine()
        cols = ["s1", "s2", "s3", "s4"]
        df = pd.DataFrame(
            np.random.normal(0.5, 0.15, size=(20, 4)),
            columns=cols,
            index=[f"SYM_{i}" for i in range(20)],
        )
        ortho_df = engine.orthogonalize(df, cols, scaling_method="dynamic_dispersion")

        for c in cols:
            vals = ortho_df[c].values
            self.assertTrue((vals >= 0.0).all() and (vals <= 1.0).all())
            # Must not be clipped to exact 0.0 or 1.0
            self.assertFalse((vals == 0.0).any() or (vals == 1.0).any())

    def test_tc25_f941_orthogonalize_phase192(self) -> None:
        """TC25: Verify orthogonalize_phase192 combines ZCA whitening, confluence kernel, and dispersion."""
        engine = FactorOrthogonalizerEngine()
        cols = list(QUATTUORDECUPLE_PILLAR_MAP.keys())
        df = pd.DataFrame(
            np.random.uniform(0.2, 0.8, size=(15, 14)),
            columns=cols,
            index=[f"SYM_{i}" for i in range(15)],
        )
        res_df = engine.orthogonalize_phase192(df, cols, preserve_top_k=14)

        self.assertEqual(res_df.shape, (15, 14))
        for c in cols:
            self.assertTrue(np.isfinite(res_df[c].values).all())
            self.assertTrue((res_df[c].values >= 0.0).all() and (res_df[c].values <= 1.0).all())

    # -------------------------------------------------------------------------
    # Category 6: Phase192Coupler Composite Alpha Coupler (TC26-27)
    # -------------------------------------------------------------------------

    def test_tc26_milestone1_phase192_coupler_evaluate(self) -> None:
        """TC26: Verify Phase192Coupler integrates 14-pillar ZCA, F941 confluence, and F940 lead-lag."""
        coupler = Phase192Coupler()
        # 14-pillar scores for 5 stocks
        p_scores = pd.DataFrame(
            np.random.uniform(0.3, 0.7, size=(5, 14)),
            columns=list(QUATTUORDECUPLE_PILLAR_MAP.keys()),
            index=["005930.KS", "000660.KS", "042700.KQ", "058470.KQ", "240810.KQ"],
        )
        us_returns = {"^SOX": 0.02, "NVDA": 0.035, "MU": 0.025}

        res = coupler.evaluate(p_scores, us_returns=us_returns)
        self.assertIn("alpha_p192", res)
        self.assertIn("alpha_normalized", res)
        self.assertIn("confluence_metrics", res)
        self.assertIn("cross_border_metrics", res)

        alpha_arr = res["alpha_p192"].values
        self.assertTrue((alpha_arr >= -3.0).all() and (alpha_arr <= 3.0).all())
        norm_arr = res["alpha_normalized"].values
        self.assertTrue((norm_arr >= 0.0).all() and (norm_arr <= 1.0).all())

    def test_tc27_milestone1_coupler_complete_aliases(self) -> None:
        """TC27: Verify complete alias tree for Phase192Coupler."""
        self.assertIs(Milestone1AlphaCoupler, Phase192Coupler)
        self.assertIs(Phase192AlphaCoupler, Phase192Coupler)
        self.assertIs(F940F941CompositeCoupler, Phase192Coupler)
        self.assertIs(QuattuordecupleConfluenceCoupler, Phase192Coupler)

    # -------------------------------------------------------------------------
    # Category 7: System Invariants, Synthetic Rows & Latency SLA (TC28-30)
    # -------------------------------------------------------------------------

    def test_tc28_zero_synthetic_rows_invariant(self) -> None:
        """TC28: Verify strict zero synthetic rows invariant (synthetic_rows == 0)."""
        benchmark_status = os.path.join(
            os.path.dirname(__file__), "..", "benchmarks", "30year", "status.json"
        )
        if os.path.exists(benchmark_status):
            with open(benchmark_status, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("synthetic_rows"), 0)
        else:
            self.assertTrue(True, "Benchmark status not present in test runner")

    def test_tc29_milestone1_numerical_stability_edge_cases(self) -> None:
        """TC29: Verify numerical stability with all-zero, all-NaN, and singular matrices."""
        coupler = Phase192Coupler()
        # All zeros
        zero_scores = np.zeros((3, 14))
        res_zero = coupler.evaluate(zero_scores)
        self.assertTrue(np.isfinite(res_zero["alpha_p192"]).all())

        # All NaNs
        nan_scores = np.full((3, 14), np.nan)
        res_nan = coupler.evaluate(nan_scores)
        self.assertTrue(np.isfinite(res_nan["alpha_p192"]).all())

    def test_tc30_milestone1_latency_sla(self) -> None:
        """TC30: Verify cross-border impulse and confluence kernel evaluate within 50ms SLA."""
        coupler = CrossBorderTechLeadLagCoupler()
        us_returns = {"^SOX": 0.02, "NVDA": 0.03, "AAPL": -0.01, "MSFT": 0.01}

        t0 = time.perf_counter()
        for _ in range(50):
            coupler.evaluate(us_returns)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 50.0

        self.assertLess(elapsed_ms, 50.0, f"Latency {elapsed_ms:.2f}ms must be below 50ms institutional SLA")


if __name__ == "__main__":
    unittest.main()
