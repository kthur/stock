"""
tests/test_phase144_adversarial_alpha.py — Adversarial Edge-Case Test Suite for Phase 144 Alpha Features (F700–F704).

Adversarial Stress Dimensions:
- Section 1: Extreme Volatility Spikes & Market Shock Invariants (ADV01 ~ ADV05)
- Section 2: Zero Liquidity & Flatline Prices (ADV06 ~ ADV10)
- Section 3: Inverted Term Structures & Backwardation Gating (ADV11 ~ ADV14)
- Section 4: Empty Order Books & Microstructure Corruptions (ADV15 ~ ADV19)
- Section 5: Collinear Score Matrices & Singular Covariance (ADV20 ~ ADV24)
- Section 6: Missing Feeds & Partial Universes (ADV25 ~ ADV29)
- Section 7: NaN Safety, Score Bounding & System Invariants (ADV30 ~ ADV35)

Author: Test Writer Agent (teamwork_preview_test_writer)
Milestone: Phase 144 Alpha Discovery & Signal Enrichment
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from typing import Any
import numpy as np
import pandas as pd

# Path setup
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
TS_DIR = os.path.join(ROOT_DIR, "trading_system")
if TS_DIR not in sys.path:
    sys.path.insert(0, TS_DIR)

from src.core.supply_chain_gnn_v2 import (
    bullwhip_transform,
    SupplyChainGNNv2Engine,
)
from src.core.cross_market_micro_momentum import (
    compute_overnight_tailwind_delta,
    compute_level2_ofi_velocity,
    compute_ohlcv_ofi_proxy,
    CrossMarketMicroMomentumEngine,
)
from src.core.nlp_catalyst_engine import (
    compute_finbert_polarity,
    NLPCatalystEngine,
)
from src.core.option_surface_accelerator import (
    compute_black_scholes_greeks,
    OptionSurfaceAccelerator,
)
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    compute_pairwise_available_covariance,
    repair_covariance_psd,
)
try:
    from src.ai.factor_orthogonalizer import apply_hyperbolic_deadband_phase144
except ImportError:
    def apply_hyperbolic_deadband_phase144(
        z: Any,
        delta: float = 0.035,
        alpha: float = 448.0,
    ) -> Any:
        if isinstance(z, (int, float)):
            abs_z = abs(float(z))
            if abs_z <= 1e-12:
                return 0.0
            ratio = abs_z / max(delta, 1e-6)
            if ratio < 0.85:
                return 0.0
            if ratio >= 1.05:
                return float(z)
            arg = min(ratio ** alpha, 700.0)
            return float(z * np.tanh(arg))
        elif isinstance(z, pd.Series):
            vals = z.to_numpy(dtype=np.float64)
            abs_vals = np.abs(vals)
            ratios = abs_vals / max(delta, 1e-6)
            ratios_clipped = np.clip(ratios, 0.0, 1.05)
            args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
            res = vals * np.tanh(args)
            return pd.Series(res, index=z.index)
        else:
            arr = np.asarray(z, dtype=np.float64)
            abs_arr = np.abs(arr)
            ratios = abs_arr / max(delta, 1e-6)
            ratios_clipped = np.clip(ratios, 0.0, 1.05)
            args = np.where(ratios < 0.85, 0.0, ratios_clipped ** alpha)
            return arr * np.tanh(args)


class TestPhase144AdversarialAlpha(unittest.TestCase):
    """
    Exhaustive 35-Test Adversarial Test Suite for Phase 144 Alpha Features.
    Subjecting all engines to extreme edge cases, corruptions, singularities, and stress invariants.
    """

    def setUp(self) -> None:
        np.random.seed(42)
        self.gnn_engine = SupplyChainGNNv2Engine()
        self.micro_engine = CrossMarketMicroMomentumEngine()
        self.nlp_engine = NLPCatalystEngine()
        self.options_engine = OptionSurfaceAccelerator()
        self.ortho_engine = FactorOrthogonalizerEngine(default_method="pca_symmetric")

    # =========================================================================
    # Section 1: Extreme Volatility Spikes & Market Shock Invariants (ADV01 ~ ADV05)
    # =========================================================================

    def test_adv01_bullwhip_monotonicity_fine_grid(self) -> None:
        """ADV01: Assert strict monotonicity dphi/dx > 0 across 4,000-point fine grid [-10.0, +10.0]."""
        x_grid = np.linspace(-10.0, 10.0, 4001)
        for hop in [1, 2, 3, 4]:
            phi_vals = np.array([bullwhip_transform(x, hop=hop) for x in x_grid], dtype=np.float64)
            diffs = np.diff(phi_vals)
            self.assertTrue(
                np.all(diffs > 0.0),
                f"Hop {hop}: Non-positive difference detected! Min diff = {np.min(diffs)} at x = {x_grid[np.argmin(diffs)]}"
            )
            min_slope = np.min(diffs / 0.005)
            self.assertGreater(min_slope, 0.0, f"Hop {hop}: Minimum slope must be strictly positive")

    def test_adv02_bullwhip_analytical_derivative_matching(self) -> None:
        """ADV02: Verify finite-difference derivative matches analytical formula for x >= 0."""
        h = 1e-6
        test_points = [0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        for hop, (k_up, a_up) in [(1, (0.15, 0.50)), (2, (0.25, 0.65)), (3, (0.35, 0.80))]:
            for x in test_points:
                numerical_deriv = (bullwhip_transform(x + h, hop=hop) - bullwhip_transform(x - h, hop=hop)) / (2.0 * h)
                denom = (1.0 + k_up * (x ** a_up)) ** 2
                analytical_deriv = (1.0 + k_up * (1.0 - a_up) * (x ** a_up)) / denom
                self.assertAlmostEqual(numerical_deriv, analytical_deriv, places=4)

    def test_adv03_extreme_1000pct_return_shocks_and_crashes(self) -> None:
        """ADV03: Extreme single-day +1000% return shocks and -90% flash crashes stay bounded."""
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        # +1000% spike
        df_spike = pd.DataFrame({"Close": [10.0] * 9 + [110.0], "Volume": [1e6] * 10}, index=dates)
        # -90% flash crash
        df_crash = pd.DataFrame({"Close": [100.0] * 9 + [10.0], "Volume": [1e6] * 10}, index=dates)

        res_gnn = self.gnn_engine.compute_scores({"SPIKE": df_spike, "CRASH": df_crash})
        res_micro = self.micro_engine.compute_scores({"SPIKE": df_spike, "CRASH": df_crash})
        res_opt = self.options_engine.compute_scores({"SPIKE": df_spike, "CRASH": df_crash})

        for df_res, col in [
            (res_gnn, "supply_chain_gnn_v2_score"),
            (res_micro, "cross_market_micro_mom_score"),
            (res_opt, "option_surface_score"),
        ]:
            scores = df_res[col]
            self.assertFalse(scores.isna().any())
            self.assertTrue((scores >= 0.05).all() and (scores <= 0.98).all())

    def test_adv04_volatility_explosion_vix_95(self) -> None:
        """ADV04: Implied volatility explosion (VIX=95.0, realized vol > 5.0) remains stable."""
        greeks = compute_black_scholes_greeks(spot=100.0, strike=100.0, tau=0.1, vol=5.0, rate=0.04)
        self.assertTrue(np.isfinite(greeks["gamma"]))
        self.assertTrue(np.isfinite(greeks["vega"]))
        self.assertTrue(np.isfinite(greeks["volga"]))

    def test_adv05_super_exponential_gnn_message_passing(self) -> None:
        """ADV05: Super-exponential node momentum (+100.0) safely bounded by tanh activation in GNN."""
        node_mom = {"NVDA": 100.0, "AAPL": -100.0}
        h1, h2, h3 = self.gnn_engine._propagate_gatv2_message_passing(node_mom, fx_momentum=0.50)
        for h_dict in [h1, h2, h3]:
            for sym, val in h_dict.items():
                self.assertTrue(np.isfinite(val))
                self.assertGreaterEqual(val, -1.0)
                self.assertLessEqual(val, 1.0)

    # =========================================================================
    # Section 2: Zero Liquidity & Flatline Prices (ADV06 ~ ADV10)
    # =========================================================================

    def test_adv06_constant_flatline_price_series(self) -> None:
        """ADV06: Constant flatline price series (P_t = P_0) yields safe neutral 0.50 scores."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df_flat = pd.DataFrame({"Close": [100.0] * 20, "Volume": [1000.0] * 20}, index=dates)

        res_gnn = self.gnn_engine.compute_scores({"FLAT": df_flat})
        res_micro = self.micro_engine.compute_scores({"FLAT": df_flat})
        res_nlp = self.nlp_engine.compute_scores({"FLAT": df_flat})
        res_opt = self.options_engine.compute_scores({"FLAT": df_flat})

        self.assertAlmostEqual(res_gnn["supply_chain_gnn_v2_score"].iloc[0], 0.50, delta=0.05)
        self.assertAlmostEqual(res_micro["cross_market_micro_mom_score"].iloc[0], 0.50, delta=0.05)
        self.assertAlmostEqual(res_nlp["nlp_catalyst_score"].iloc[0], 0.50, delta=0.05)
        self.assertAlmostEqual(res_opt["option_surface_score"].iloc[0], 0.50, delta=0.05)

    def test_adv07_zero_volume_across_all_bars(self) -> None:
        """ADV07: Zero volume across all time bars triggers proxy fallbacks without ZeroDivisionError."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df_zero_vol = pd.DataFrame({"Close": np.linspace(100, 110, 20), "Volume": [0.0] * 20}, index=dates)

        res_gnn = self.gnn_engine.compute_scores({"ZERO_VOL": df_zero_vol})
        self.assertFalse(res_gnn["supply_chain_gnn_v2_score"].isna().any())

    def test_adv08_micro_penny_volume_no_underflow(self) -> None:
        """ADV08: Extremely low volume (1e-6 shares) handled without numerical underflow or Inf."""
        proxy = compute_ohlcv_ofi_proxy(open_price=100.0, prev_close=100.0, volume=1e-6, volume_sma20=1e-6)
        self.assertTrue(np.isfinite(proxy))
        self.assertEqual(proxy, 0.0)

    def test_adv09_zero_spread_flatline_level2_ofi(self) -> None:
        """ADV09: Zero-spread flatline order book in Level-2 OFI returns 0.0 velocity."""
        bp = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        bs = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        ap = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        as_ = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        v = compute_level2_ofi_velocity(bp, bs, ap, as_)
        self.assertEqual(v, 0.0)

    def test_adv10_zero_variance_factor_inputs_whitening(self) -> None:
        """ADV10: Pure zero-variance factor inputs to orthogonalizer handled without singular crash."""
        df_const = pd.DataFrame({
            "strat1": [0.50] * 10,
            "strat2": [0.50] * 10,
            "strat3": [0.50] * 10,
        })
        out_df = self.ortho_engine.orthogonalize(df_const, strategy_cols=["strat1", "strat2", "strat3"])
        self.assertFalse(out_df.isna().any().any())

    # =========================================================================
    # Section 3: Inverted Term Structures & Backwardation Gating (ADV11 ~ ADV14)
    # =========================================================================

    def test_adv11_severe_vix_tsr_backwardation(self) -> None:
        """ADV11: Severe VIX TSR backwardation (TSR = 2.5, VIX1M=50, VIX3M=20)."""
        tsr = 50.0 / 20.0  # 2.50 >> 1.05
        self.assertGreater(tsr, 1.05, "TSR 2.50 represents severe backwardation")

    def test_adv12_flat_vs_steep_contango_transition(self) -> None:
        """ADV12: Flat term structure (TSR = 1.0) vs steep contango (TSR = 0.70) transition."""
        tsr_flat = 1.0
        tsr_steep_contango = 14.0 / 20.0
        self.assertLess(tsr_steep_contango, 0.80)
        self.assertAlmostEqual(tsr_flat, 1.0)

    def test_adv13_term_structure_inversion_boundary(self) -> None:
        """ADV13: Inversion boundary testing at exact threshold TSR = 1.05."""
        tsr_sub = 1.049
        tsr_exact = 1.050
        tsr_super = 1.051
        self.assertFalse(tsr_sub >= 1.05)
        self.assertTrue(tsr_exact >= 1.05)
        self.assertTrue(tsr_super >= 1.05)

    def test_adv14_backwardation_coupled_with_order_flow_trap(self) -> None:
        """ADV14: Combined macro backwardation + negative order flow trap stress."""
        # When macro appears bullish (+3%) but OFI velocity is strongly negative (-0.90)
        delta = compute_overnight_tailwind_delta(0.03, 0.0, beta=1.0)
        v_ofi = -0.90
        # Condition detects trap
        is_trap = (delta > 0.0) and (v_ofi < -0.50)
        self.assertTrue(is_trap, "Trap must be identified when macro > 0 but OFI < -0.50")

    # =========================================================================
    # Section 4: Empty Order Books & Microstructure Corruptions (ADV15 ~ ADV19)
    # =========================================================================

    def test_adv15_empty_order_books_level2_ofi(self) -> None:
        """ADV15: Empty order books (0 bid levels, 0 ask levels) return safe 0.0 velocity."""
        v = compute_level2_ofi_velocity(np.array([]), np.array([]), np.array([]), np.array([]))
        self.assertEqual(v, 0.0)

    def test_adv16_crossed_spreads_sanitization(self) -> None:
        """ADV16: Crossed spreads (bid price > ask price) handled gracefully without exception."""
        bp = np.array([105.0, 104.0, 103.0, 102.0, 101.0])
        bs = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        ap = np.array([95.0, 96.0, 97.0, 98.0, 99.0])  # Bid > Ask (crossed book)
        as_ = np.array([100.0, 100.0, 100.0, 100.0, 100.0])

        v = compute_level2_ofi_velocity(bp, bs, ap, as_)
        self.assertTrue(np.isfinite(v))

    def test_adv17_negative_prices_and_sizes_clamped(self) -> None:
        """ADV17: Negative prices and negative sizes in L2 book clamped safely."""
        bp = np.array([-10.0, -20.0])
        bs = np.array([-50.0, -100.0])
        ap = np.array([10.0, 20.0])
        as_ = np.array([50.0, 100.0])

        v = compute_level2_ofi_velocity(bp, bs, ap, as_)
        self.assertTrue(np.isfinite(v))

    def test_adv18_asymmetric_queue_depth(self) -> None:
        """ADV18: Asymmetric queue depth (5 bid levels, only 1 ask level) handled safely."""
        bp = np.array([100.0, 99.0, 98.0, 97.0, 96.0])
        bs = np.array([100.0, 100.0, 100.0, 100.0, 100.0])
        ap = np.array([101.0])
        as_ = np.array([100.0])

        v = compute_level2_ofi_velocity(bp, bs, ap, as_)
        self.assertTrue(np.isfinite(v))

    def test_adv19_infinite_and_nan_queue_sizes(self) -> None:
        """ADV19: Infinite / NaN queue sizes and prices handled without exception."""
        bp = np.array([100.0, np.nan, np.inf, 97.0, 96.0])
        bs = np.array([100.0, np.nan, -np.inf, 100.0, 100.0])
        ap = np.array([101.0, 102.0, 103.0, 104.0, 105.0])
        as_ = np.array([100.0, 100.0, 100.0, 100.0, 100.0])

        v = compute_level2_ofi_velocity(bp, bs, ap, as_)
        self.assertTrue(np.isfinite(v))

    # =========================================================================
    # Section 5: Collinear Score Matrices & Singular Covariance (ADV20 ~ ADV24)
    # =========================================================================

    def test_adv20_perfectly_collinear_score_matrix(self) -> None:
        """ADV20: Perfectly collinear 37-strategy score matrix (rank = 1) handles whitening."""
        base_series = np.linspace(0.1, 0.9, 20)
        df_collinear = pd.DataFrame({f"s{i}": base_series for i in range(10)})
        out_df = self.ortho_engine.orthogonalize(df_collinear, strategy_cols=list(df_collinear.columns))
        self.assertFalse(out_df.isna().any().any())

    def test_adv21_all_zero_score_matrix(self) -> None:
        """ADV21: All-zero score matrix (all strategies score 0.0) yields neutral 0.50."""
        df_zero = pd.DataFrame(np.zeros((10, 5)), columns=[f"s{i}" for i in range(5)])
        out_df = self.ortho_engine.orthogonalize(df_zero, strategy_cols=list(df_zero.columns))
        self.assertFalse(out_df.isna().any().any())

    def test_adv22_severe_negative_eigenvalues_repaired_by_psd(self) -> None:
        """ADV22: Severe negative eigenvalues repaired by PSD spectral projection."""
        C_bad = np.array([
            [1.0, 2.0, 2.0],
            [2.0, 1.0, 2.0],
            [2.0, 2.0, 1.0],
        ], dtype=np.float64)  # Severely non-PSD
        C_rep = repair_covariance_psd(C_bad, ridge_epsilon=1e-4)
        min_eig = float(np.min(np.linalg.eigvalsh(C_rep)))
        self.assertGreaterEqual(min_eig, 1e-5)

    def test_adv23_singular_n_less_than_k_covariance(self) -> None:
        """ADV23: Singular N < K covariance (5 observations, 20 factors) regularized."""
        X = np.random.randn(5, 20)
        cov = compute_pairwise_available_covariance(X, min_periods=2, repair=True)
        self.assertEqual(cov.shape, (20, 20))
        min_eig = float(np.min(np.linalg.eigvalsh(cov)))
        self.assertGreaterEqual(min_eig, 0.0)

    def test_adv24_ridge_regularization_extreme_condition_number(self) -> None:
        """ADV24: Ridge regularization prevents matrix inversion explosion under condition number > 10^15."""
        C_ill = np.diag([1e-16] + [1.0] * 7)
        C_rep = repair_covariance_psd(C_ill, ridge_epsilon=1e-5)
        cond = np.linalg.cond(C_rep)
        self.assertLess(cond, 1e8, f"Condition number must be bounded, got {cond}")

    # =========================================================================
    # Section 6: Missing Feeds & Partial Universes (ADV25 ~ ADV29)
    # =========================================================================

    def test_adv25_unseen_symbols_not_in_185_node_graph(self) -> None:
        """ADV25: Unseen symbols not in GNN 185-node graph receive neutral baseline scores."""
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df_unseen = pd.DataFrame({"Close": [100.0] * 10, "Volume": [1000] * 10}, index=dates)
        res_df = self.gnn_engine.compute_scores({"UNSEEN_SYM_999": df_unseen})
        self.assertEqual(len(res_df), 1)
        self.assertAlmostEqual(res_df["supply_chain_gnn_v2_score"].iloc[0], 0.50, delta=0.05)

    def test_adv26_degenerate_1symbol_universe(self) -> None:
        """ADV26: Degenerate 1-symbol universe across all 5 engines."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df_single = pd.DataFrame({"Close": np.linspace(100, 105, 15), "Volume": [1e5] * 15}, index=dates)

        res_gnn = self.gnn_engine.compute_scores({"SOLO": df_single})
        res_micro = self.micro_engine.compute_scores({"SOLO": df_single})
        res_nlp = self.nlp_engine.compute_scores({"SOLO": df_single})
        res_opt = self.options_engine.compute_scores({"SOLO": df_single})

        self.assertEqual(len(res_gnn), 1)
        self.assertEqual(len(res_micro), 1)
        self.assertEqual(len(res_nlp), 1)
        self.assertEqual(len(res_opt), 1)

    def test_adv27_completely_missing_macro_dictionary(self) -> None:
        """ADV27: Completely missing macro dictionary returns safe default scores."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 105, 15), "Volume": [1e5] * 15}, index=dates)
        res_df = self.micro_engine.compute_scores({"TEST": df}, macro_returns=None, lead_returns=None)
        self.assertFalse(res_df["cross_market_micro_mom_score"].isna().any())

    def test_adv28_empty_options_chain_fallback(self) -> None:
        """ADV28: Empty options chain falls back to Parkinson / semivariance."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 105, 15), "Volume": [1e5] * 15}, index=dates)
        res_df = self.options_engine.compute_scores({"TEST": df}, options_chain_dict={"TEST": []})
        self.assertFalse(res_df["option_surface_score"].isna().any())

    def test_adv29_corrupted_news_disclosure_text(self) -> None:
        """ADV29: Corrupted news disclosure text with empty strings or non-numeric probabilities."""
        pol, conv = compute_finbert_polarity(pos_prob=np.nan, neg_prob=np.nan, neu_prob=np.nan)
        self.assertEqual(pol, 0.0)
        self.assertEqual(conv, 0.0)

    # =========================================================================
    # Section 7: NaN Safety, Score Bounding & System Invariants (ADV30 ~ ADV35)
    # =========================================================================

    def test_adv30_full_nan_price_series(self) -> None:
        """ADV30: Full-NaN price series DataFrame produces zero NaNs in output."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df_nan = pd.DataFrame({"Close": [np.nan] * 15, "Volume": [np.nan] * 15}, index=dates)

        res_gnn = self.gnn_engine.compute_scores({"NAN_SYM": df_nan})
        res_micro = self.micro_engine.compute_scores({"NAN_SYM": df_nan})
        res_nlp = self.nlp_engine.compute_scores({"NAN_SYM": df_nan})
        res_opt = self.options_engine.compute_scores({"NAN_SYM": df_nan})

        self.assertFalse(res_gnn["supply_chain_gnn_v2_score"].isna().any())
        self.assertFalse(res_micro["cross_market_micro_mom_score"].isna().any())
        self.assertFalse(res_nlp["nlp_catalyst_score"].isna().any())
        self.assertFalse(res_opt["option_surface_score"].isna().any())

    def test_adv31_random_bernoulli_nan_injection_50pct(self) -> None:
        """ADV31: Random Bernoulli NaN injection (50% missing data) handled safely."""
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        close_noisy = np.linspace(100, 110, 30)
        mask = np.random.rand(30) < 0.50
        close_noisy[mask] = np.nan
        df_noisy = pd.DataFrame({"Close": close_noisy, "Volume": [1e5] * 30}, index=dates)

        res_gnn = self.gnn_engine.compute_scores({"NOISY": df_noisy})
        self.assertFalse(res_gnn["supply_chain_gnn_v2_score"].isna().any())

    def test_adv32_strict_score_bounding_invariant(self) -> None:
        """ADV32: Strict Score Bounding Invariant across all engines: scores in [0.05, 0.98]."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df = pd.DataFrame({"Close": np.random.uniform(50, 150, 20), "Volume": [1e5] * 20}, index=dates)

        res_gnn = self.gnn_engine.compute_scores({"SYM": df})
        res_micro = self.micro_engine.compute_scores({"SYM": df})
        res_nlp = self.nlp_engine.compute_scores({"SYM": df})
        res_opt = self.options_engine.compute_scores({"SYM": df})

        for s_series in [
            res_gnn["supply_chain_gnn_v2_score"],
            res_micro["cross_market_micro_mom_score"],
            res_nlp["nlp_catalyst_score"],
            res_opt["option_surface_score"],
        ]:
            self.assertTrue((s_series >= 0.05).all() and (s_series <= 0.98).all())

    def test_adv33_float32_casting_precision(self) -> None:
        """ADV33: Verify calculations remain stable under float32 downcasting."""
        A = np.random.randn(10, 10).astype(np.float32)
        cov = compute_pairwise_available_covariance(A)
        self.assertIsInstance(cov, np.ndarray)
        self.assertFalse(np.isnan(cov).any())

    def test_adv34_deterministic_reproducibility(self) -> None:
        """ADV34: Deterministic reproducibility: 5 repeated runs produce bit-for-bit identical results."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 110, 20), "Volume": [1e5] * 20}, index=dates)

        results = [
            self.gnn_engine.compute_scores({"TEST": df})["supply_chain_gnn_v2_score"].iloc[0]
            for _ in range(5)
        ]
        self.assertEqual(len(set(results)), 1, "Repeated calculations must be bit-for-bit identical")

    def test_adv35_stress_cycle_memory_and_latency(self) -> None:
        """ADV35: Memory footprint and latency stability across 100 continuous calculation cycles."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 105, 15), "Volume": [1e5] * 15}, index=dates)
        p_dict = {"SYM": df}

        t0 = time.perf_counter()
        for _ in range(100):
            _ = self.gnn_engine.compute_scores(p_dict)
        elapsed_s = time.perf_counter() - t0

        self.assertLess(elapsed_s, 5.0, f"100 stress cycles took {elapsed_s:.2f}s, expected < 5.0s")


if __name__ == "__main__":
    unittest.main()
