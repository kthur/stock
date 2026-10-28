"""
tests/test_adversarial_phase140_gnn_micro.py — Adversarial Stress Test Suite for Phase 140 Features F680 and F681.

Author: Challenger 1 (Empirical Challenger & Adversarial Reviewer)
Target Modules:
- src/core/supply_chain_gnn_v2.py (Feature F680: 3-Hop Global Value Chain GNN v2)
- src/core/cross_market_micro_momentum.py (Feature F681: Timezone Lead-Lag & Level-2 OFI Velocity)

Adversarial Verification Dimensions:
1. Mathematical Monotonicity & Zero Demand Inversion: dphi/dx > 0 on x in [-10.0, +10.0] across all hops.
2. Topological Extremes: Cyclic dependencies (2-node & 3-node feedback loops), disconnected subgraphs, orphan graphs.
3. Severe Data Corruption: Zero volume, zero/negative prices, Inf/NaN inputs, extreme FX shocks (+-500%).
4. Microstructure Order Book Corruptions: Crossed spreads, zero liquidity, NaN/Inf sizes, mismatched queue depths.
5. Invariants & SLAs: Zero NaNs, strict score bounding in [0.05, 0.95], execution latency < 100ms for 185 nodes.
6. Dual-Tree Cryptographic SHA-256 Parity across src/ and trading_system/src/.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame
from src.core.strategy_registry import STRATEGY_REGISTRY

from src.core.supply_chain_gnn_v2 import (
    bullwhip_transform,
    SupplyChainGNNv2Engine,
    GLOBAL_VALUE_CHAIN_3HOP_EDGES,
    TIER1_SYMBOLS,
    TIER2_SYMBOLS,
    TIER3_SYMBOLS,
    compute_supply_chain_gnn_v2_scores,
)

from src.core.cross_market_micro_momentum import (
    compute_overnight_tailwind_delta,
    compute_level2_ofi_velocity,
    compute_ohlcv_ofi_proxy,
    CrossMarketMicroMomentumEngine,
    compute_cross_market_micro_momentum_scores,
)


class TestAdversarialGNNv2AndMicroMomentum(unittest.TestCase):
    """Adversarial stress harness for Phase 140 Features F680 and F681."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.gnn_engine = SupplyChainGNNv2Engine()
        self.micro_engine = CrossMarketMicroMomentumEngine()

    # =========================================================================
    # Section 1: Mathematical Monotonicity & Extreme Demand Shocks ([-10, +10])
    # =========================================================================

    def test_adv01_bullwhip_monotonicity_fine_grid(self) -> None:
        """ADV01: Assert strict monotonicity dphi/dx > 0 across fine grid [-10.0, +10.0] for all hops."""
        # 4,000-point fine grid spanning [-10.0, +10.0] (step = 0.005)
        x_grid = np.linspace(-10.0, 10.0, 4001)

        for hop in [1, 2, 3, 4]:
            phi_vals = np.array([bullwhip_transform(x, hop=hop) for x in x_grid], dtype=np.float64)
            diffs = np.diff(phi_vals)

            # Assert every single step is strictly positive (no flatlines, no rollover)
            self.assertTrue(
                np.all(diffs > 0.0),
                f"Hop {hop}: Non-positive difference detected! Min diff = {np.min(diffs)} at x = {x_grid[np.argmin(diffs)]}"
            )
            # Assert minimum derivative is bounded strictly away from zero
            min_slope = np.min(diffs / 0.005)
            self.assertGreater(min_slope, 0.0, f"Hop {hop}: Minimum slope must be strictly positive")

    def test_adv02_bullwhip_analytical_derivative_matching(self) -> None:
        """ADV02: Verify finite-difference derivative matches analytical formula for x >= 0."""
        # For x >= 0: dphi/dx = (1 + kappa * (1 - alpha) * x^alpha) / (1 + kappa * x^alpha)^2
        h = 1e-6
        test_points = [0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

        for hop, (k_up, a_up) in [(1, (0.15, 0.50)), (2, (0.25, 0.65)), (3, (0.35, 0.80))]:
            for x in test_points:
                numerical_deriv = (bullwhip_transform(x + h, hop=hop) - bullwhip_transform(x - h, hop=hop)) / (2.0 * h)
                denom = (1.0 + k_up * (x ** a_up)) ** 2
                analytical_deriv = (1.0 + k_up * (1.0 - a_up) * (x ** a_up)) / denom

                self.assertAlmostEqual(
                    numerical_deriv,
                    analytical_deriv,
                    places=4,
                    msg=f"Hop {hop} at x={x}: Numerical derivative {numerical_deriv} != analytical {analytical_deriv}"
                )
                self.assertGreater(analytical_deriv, 0.0)

    def test_adv03_bullwhip_extreme_demand_surges_no_inversion(self) -> None:
        """ADV03: Challenge massive demand surges x in [10.0, 100.0, 1000.0, 10000.0]: zero demand inversion."""
        surges = [10.0, 20.0, 50.0, 100.0, 500.0, 1000.0, 10000.0]
        for hop in [1, 2, 3]:
            vals = [bullwhip_transform(s, hop=hop) for s in surges]
            for i in range(len(vals) - 1):
                self.assertGreater(
                    vals[i + 1],
                    vals[i],
                    f"Hop {hop}: Demand inversion detected at x={surges[i]} -> {surges[i+1]}! {vals[i+1]} <= {vals[i]}"
                )

    def test_adv04_bullwhip_downside_cancellation_cascade_extremes(self) -> None:
        """ADV04: Downside order cancellation cascade (|phi(x)| > |x|) across extreme negative shocks [-10, -0.01]."""
        # Ascending order: -10.0 < -5.0 < -1.0 < -0.50 < -0.10 < -0.05 < -0.01
        crashes = [-10.0, -5.0, -1.0, -0.50, -0.10, -0.05, -0.01]
        for hop in [1, 2, 3]:
            vals = [bullwhip_transform(c, hop=hop) for c in crashes]
            # Must be strictly monotonic: crashes[i] < crashes[i+1] -> vals[i] < vals[i+1]
            for i in range(len(vals) - 1):
                self.assertLess(
                    vals[i],
                    vals[i + 1],
                    f"Hop {hop}: Downside monotonicity violated at x={crashes[i]} vs {crashes[i+1]}"
                )
            # Must amplify negative shocks: |phi(c)| > |c|
            for c, v in zip(crashes, vals):
                self.assertLess(v, c, f"Hop {hop}: Shock {c} must amplify downward, got {v}")
                self.assertGreater(abs(v), abs(c))

    def test_adv05_bullwhip_non_finite_inputs(self) -> None:
        """ADV05: Robustness against non-finite inputs (NaN, Inf, -Inf) returning 0.0."""
        for val in [np.nan, np.inf, -np.inf, float("nan"), float("inf"), float("-inf")]:
            for hop in [1, 2, 3]:
                res = bullwhip_transform(val, hop=hop)
                self.assertEqual(res, 0.0)
                self.assertTrue(np.isfinite(res))

    # =========================================================================
    # Section 2: Graph Topologies: Cyclic Dependencies & Disconnected Subgraphs
    # =========================================================================

    def test_adv06_cyclic_2node_oscillator(self) -> None:
        """ADV06: 2-node mutual cyclic feedback loop (A <-> B) with extreme opposing shocks."""
        cyclic_edges = [
            ("SYM_A", "SYM_B", 0.95, 10.0),
            ("SYM_B", "SYM_A", 0.95, 10.0),
        ]
        engine = SupplyChainGNNv2Engine(custom_edges=cyclic_edges)

        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        # SYM_A surges +100%, SYM_B crashes -90%
        p_dict = {
            "SYM_A": pd.DataFrame({"Close": np.linspace(100, 200, days), "Volume": 1000}, index=dates),
            "SYM_B": pd.DataFrame({"Close": np.linspace(100, 10, days), "Volume": 1000}, index=dates),
        }

        # Must execute without infinite recursion or deadlock
        res_df = engine.compute_scores(p_dict)
        self.assertEqual(len(res_df), 2)
        self.assertFalse(res_df["supply_chain_gnn_v2_score"].isna().any())

        score_a = res_df.loc[res_df["symbol"] == "SYM_A", "supply_chain_gnn_v2_score"].iloc[0]
        score_b = res_df.loc[res_df["symbol"] == "SYM_B", "supply_chain_gnn_v2_score"].iloc[0]

        # Scores must be bounded strictly in [0.05, 0.95]
        self.assertGreaterEqual(score_a, 0.05)
        self.assertLessEqual(score_a, 0.95)
        self.assertGreaterEqual(score_b, 0.05)
        self.assertLessEqual(score_b, 0.95)

    def test_adv07_cyclic_3node_feedback_loop(self) -> None:
        """ADV07: 3-node directed cyclic loop (A -> B -> C -> A) with compounding extreme shocks."""
        cyclic_edges = [
            ("NODE_A", "NODE_B", 0.90, 15.0),
            ("NODE_B", "NODE_C", 0.90, 15.0),
            ("NODE_C", "NODE_A", 0.90, 15.0),
        ]
        engine = SupplyChainGNNv2Engine(custom_edges=cyclic_edges)

        days = 20
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "NODE_A": pd.DataFrame({"Close": np.linspace(50, 150, days), "Volume": 1000}, index=dates),
            "NODE_B": pd.DataFrame({"Close": np.linspace(50, 150, days), "Volume": 1000}, index=dates),
            "NODE_C": pd.DataFrame({"Close": np.linspace(50, 150, days), "Volume": 1000}, index=dates),
        }

        res_df = engine.compute_scores(p_dict)
        self.assertEqual(len(res_df), 3)
        self.assertTrue(np.all(res_df["supply_chain_gnn_v2_score"] >= 0.05))
        self.assertTrue(np.all(res_df["supply_chain_gnn_v2_score"] <= 0.95))
        self.assertFalse(res_df["supply_chain_gnn_v2_score"].isna().any())

    def test_adv08_disconnected_clusters_and_isolated_singletons(self) -> None:
        """ADV08: Disconnected components: Cluster 1 (A->B), Cluster 2 (C->D), and isolated singleton E."""
        disconnected_edges = [
            ("CLUST1_A", "CLUST1_B", 0.85, 20.0),
            ("CLUST2_C", "CLUST2_D", 0.85, 20.0),
        ]
        engine = SupplyChainGNNv2Engine(custom_edges=disconnected_edges)

        days = 20
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        # Cluster 1 bullish, Cluster 2 bearish, Singleton flat
        p_dict = {
            "CLUST1_A": pd.DataFrame({"Close": np.linspace(100, 130, days), "Volume": 1000}, index=dates),
            "CLUST1_B": pd.DataFrame({"Close": np.linspace(100, 120, days), "Volume": 1000}, index=dates),
            "CLUST2_C": pd.DataFrame({"Close": np.linspace(100, 70, days), "Volume": 1000}, index=dates),
            "CLUST2_D": pd.DataFrame({"Close": np.linspace(100, 80, days), "Volume": 1000}, index=dates),
            "SINGLETON_E": pd.DataFrame({"Close": np.full(days, 100.0), "Volume": 1000}, index=dates),
        }

        res_df = engine.compute_scores(p_dict)
        self.assertEqual(len(res_df), 5)

        s_c1 = res_df.loc[res_df["symbol"] == "CLUST1_B", "supply_chain_gnn_v2_score"].iloc[0]
        s_c2 = res_df.loc[res_df["symbol"] == "CLUST2_D", "supply_chain_gnn_v2_score"].iloc[0]
        s_e = res_df.loc[res_df["symbol"] == "SINGLETON_E", "supply_chain_gnn_v2_score"].iloc[0]

        self.assertGreater(s_c1, s_c2, "Bullish cluster must outscore bearish cluster")
        self.assertAlmostEqual(s_e, 0.50, delta=0.06, msg="Flat isolated singleton must be neutral ~0.50")

    def test_adv09_empty_custom_graph(self) -> None:
        """ADV09: Engine initialized with completely empty edges list gracefully processes inputs."""
        engine = SupplyChainGNNv2Engine(custom_edges=[])
        p_dict = {"STOCK_X": pd.DataFrame({"Close": [100.0, 102.0, 104.0, 106.0, 108.0]})}
        res = engine.compute_scores(p_dict)
        self.assertEqual(len(res), 1)
        self.assertFalse(res["supply_chain_gnn_v2_score"].isna().any())

    # =========================================================================
    # Section 3: Severe Data Corruption, Zero Volumes & FX Shocks in GNN
    # =========================================================================

    def test_adv10_zero_volume_flatline_universe(self) -> None:
        """ADV10: 185 symbols with strictly zero volume and flat prices produce zero NaNs and neutral scores."""
        days = 25
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {}
        for s in list(self.gnn_engine.all_nodes)[:185]:
            p_dict[s] = pd.DataFrame({"Close": np.full(days, 100.0), "Volume": np.zeros(days)}, index=dates)

        res_df = self.gnn_engine.compute_scores(p_dict)
        self.assertEqual(len(res_df), 185)
        self.assertFalse(res_df["supply_chain_gnn_v2_score"].isna().any())
        scores = res_df["supply_chain_gnn_v2_score"].values
        # All flatline symbols with zero volume must hover near neutral 0.50
        self.assertTrue(np.all(np.abs(scores - 0.50) < 0.05))

    def test_adv11_corrupted_prices_nan_inf_negative(self) -> None:
        """ADV11: Resilient handling of degenerate/corrupted price inputs (NaN, Inf, negative, zero prices)."""
        days = 20
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "ALL_NAN": pd.DataFrame({"Close": [np.nan] * days, "Volume": [np.nan] * days}, index=dates),
            "ALL_INF": pd.DataFrame({"Close": [np.inf] * days, "Volume": [np.inf] * days}, index=dates),
            "NEG_INF": pd.DataFrame({"Close": [-np.inf] * days, "Volume": [1000] * days}, index=dates),
            "ZERO_PRICE": pd.DataFrame({"Close": np.zeros(days), "Volume": np.zeros(days)}, index=dates),
            "NEG_PRICES": pd.DataFrame({"Close": np.linspace(-10, -50, days), "Volume": np.full(days, -100)}, index=dates),
            "MIXED_CORRUPT": pd.DataFrame({"Close": [100, np.nan, 102, np.inf, -50, 105], "Volume": [0, np.nan, 100, np.inf, -1, 100]}),
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 130, days), "Volume": 1000}, index=dates),
        }

        res_df = self.gnn_engine.compute_scores(p_dict)
        self.assertEqual(len(res_df), len(p_dict))
        self.assertFalse(res_df["supply_chain_gnn_v2_score"].isna().any())
        scores = res_df["supply_chain_gnn_v2_score"].values
        self.assertTrue(np.all(scores >= 0.05))
        self.assertTrue(np.all(scores <= 0.95))

    def test_adv12_extreme_fx_devaluation_and_appreciation_shocks(self) -> None:
        """ADV12: Extreme FX shocks (+-500% USD/KRW) preserve finite non-negative dynamic edge weights."""
        # Test extreme currency collapse (+500% USD/KRW surge)
        w_hyper_deval = self.gnn_engine.compute_dynamic_edge_weight("NVDA", "000660", 0.90, 30.0, fx_momentum=5.0)
        self.assertTrue(np.isfinite(w_hyper_deval))
        self.assertGreater(w_hyper_deval, 0.90)

        # Test extreme currency appreciation (-500% USD/KRW crash)
        w_hyper_apprec = self.gnn_engine.compute_dynamic_edge_weight("NVDA", "000660", 0.90, 30.0, fx_momentum=-5.0)
        self.assertTrue(np.isfinite(w_hyper_apprec))
        # max(0, 1 + eta * Delta_FX) must clamp to zero without becoming negative
        self.assertEqual(w_hyper_apprec, 0.0)

    def test_adv13_extreme_supplier_crashes_downstream_score_collapse(self) -> None:
        """ADV13: Upstream titan crash (-90% NVDA) cascades to Tier 2/3 suppliers, depressing scores."""
        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 10, days), "Volume": 5000}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(100, 50, days), "Volume": 5000}, index=dates),
            "042700": pd.DataFrame({"Close": np.linspace(100, 60, days), "Volume": 5000}, index=dates),
        }
        res_df = self.gnn_engine.compute_scores(p_dict)
        score_hanmi = res_df.loc[res_df["symbol"] == "042700", "supply_chain_gnn_v2_score"].iloc[0]
        # Should be deeply bearish due to multi-hop crash cascade
        self.assertLess(score_hanmi, 0.40)
        self.assertGreaterEqual(score_hanmi, 0.05)

    # =========================================================================
    # Section 4: Adversarial Stress Testing of CrossMarketMicroMomentum
    # =========================================================================

    def test_adv14_extreme_overnight_jumps_and_cross_deltas(self) -> None:
        """ADV14: Extreme overnight gap jumps (US +1000%, KRX -1000% and vice versa)."""
        # Case A: Massive tailwind
        delta_huge_pos = compute_overnight_tailwind_delta(r_us_overnight=10.0, r_krx_preopen=-1.0, beta=1.5)
        self.assertEqual(delta_huge_pos, 16.0)

        # Case B: Massive headwind
        delta_huge_neg = compute_overnight_tailwind_delta(r_us_overnight=-1.0, r_krx_preopen=10.0, beta=1.5)
        self.assertEqual(delta_huge_neg, -11.5)

        # Case C: Non-finite inputs
        delta_nan = compute_overnight_tailwind_delta(r_us_overnight=np.nan, r_krx_preopen=np.nan, beta=np.nan)
        self.assertEqual(delta_nan, 0.0)

        delta_inf = compute_overnight_tailwind_delta(r_us_overnight=np.inf, r_krx_preopen=-np.inf, beta=1.0)
        self.assertEqual(delta_inf, 0.0)

    def test_adv15_level2_ofi_order_book_edge_cases(self) -> None:
        """ADV15: Corrupted Level-2 order books: empty depth, crossed spread, 0 size, mismatched depth."""
        # 1. Empty arrays -> must return 0.0
        vel_empty = compute_level2_ofi_velocity(np.array([]), np.array([]), np.array([]), np.array([]))
        self.assertEqual(vel_empty, 0.0)

        # 2. Crossed order book (bid > ask)
        bp_crossed = np.array([105.0, 104.0, 103.0])
        ap_crossed = np.array([100.0, 101.0, 102.0])
        bs = np.array([100.0, 100.0, 100.0])
        as_ = np.array([100.0, 100.0, 100.0])
        vel_crossed = compute_level2_ofi_velocity(bp_crossed, bs, ap_crossed, as_)
        self.assertTrue(np.isfinite(vel_crossed))

        # 3. Strictly zero sizes (zero liquidity at all levels) -> must return 0.0
        bs_zero = np.zeros(5)
        as_zero = np.zeros(5)
        bp = np.array([100, 99, 98, 97, 96], dtype=float)
        ap = np.array([101, 102, 103, 104, 105], dtype=float)
        vel_zero_liq = compute_level2_ofi_velocity(bp, bs_zero, ap, as_zero)
        self.assertEqual(vel_zero_liq, 0.0)

        # 4. Mismatched queue lengths
        vel_mismatch = compute_level2_ofi_velocity(bp[:3], bs[:3], ap[:5], as_[:5])
        self.assertTrue(np.isfinite(vel_mismatch))

        # 5. std_ofi <= 0 or zero variance
        vel_zero_std = compute_level2_ofi_velocity(bp, bs, ap, as_, std_ofi=0.0)
        self.assertTrue(np.isfinite(vel_zero_std))

    def test_adv15b_level2_ofi_nan_size_propagation_audit(self) -> None:
        """ADV15B: Audit behavior when Level-2 order book contains corrupted NaN sizes.
        Documents empirical vulnerability: compute_level2_ofi_velocity returns NaN if raw sizes contain NaN,
        which could wipe out overnight delta in compute_scores if unhandled at the outer layer.
        """
        bp = np.array([100, 99, 98, 97, 96], dtype=float)
        ap = np.array([101, 102, 103, 104, 105], dtype=float)
        bs_nan = np.array([np.nan, 100, 200, 300, 400])
        as_clean = np.array([100, 200, 300, 400, 500], dtype=float)

        vel_nan = compute_level2_ofi_velocity(bp, bs_nan, ap, as_clean)
        # Note: Worker M1's helper returns NaN when passed raw NaNs.
        # This test documents the empirical observation.
        is_nan_result = np.isnan(vel_nan)
        # Verify compute_scores absorbs this NaN gracefully and falls back to bounded [0.05, 0.95]
        days = 10
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "SYM_TEST": pd.DataFrame({"Close": np.linspace(100, 110, days)}, index=dates)
        }
        l2_dict = {
            "SYM_TEST": {
                "bid_prices": bp,
                "bid_sizes": bs_nan,
                "ask_prices": ap,
                "ask_sizes": as_clean,
            }
        }
        res_df = self.micro_engine.compute_scores(p_dict, level2_dict=l2_dict)
        self.assertFalse(res_df["cross_market_micro_mom_score"].isna().any())
        score_val = res_df["cross_market_micro_mom_score"].iloc[0]
        self.assertGreaterEqual(score_val, 0.05)
        self.assertLessEqual(score_val, 0.95)

    def test_adv16_ohlcv_ofi_proxy_corrupted_inputs(self) -> None:
        """ADV16: OHLCV OFI proxy under zero volume, zero prices, negative prices, NaN/Inf."""
        # Zero volume & zero SMA
        p1 = compute_ohlcv_ofi_proxy(open_price=105.0, prev_close=100.0, volume=0.0, volume_sma20=0.0)
        self.assertTrue(np.isfinite(p1))

        # Zero prev_close (ZeroDivision protection)
        p2 = compute_ohlcv_ofi_proxy(open_price=100.0, prev_close=0.0, volume=1000.0, volume_sma20=1000.0)
        self.assertEqual(p2, 0.0)

        # Negative prev_close
        p3 = compute_ohlcv_ofi_proxy(open_price=100.0, prev_close=-50.0, volume=1000.0, volume_sma20=1000.0)
        self.assertEqual(p3, 0.0)

        # Non-finite inputs
        p4 = compute_ohlcv_ofi_proxy(open_price=np.nan, prev_close=100.0, volume=100.0, volume_sma20=100.0)
        self.assertEqual(p4, 0.0)

        p5 = compute_ohlcv_ofi_proxy(open_price=100.0, prev_close=np.inf, volume=100.0, volume_sma20=100.0)
        self.assertEqual(p5, 0.0)

    def test_adv17_micro_momentum_composite_adversarial_matrix(self) -> None:
        """ADV17: Micro-Momentum end-to-end evaluation with corrupted feeds, extreme jumps, and L2 feeds."""
        days = 20
        dates = pd.date_range("2026-01-01", periods=days, freq="D")

        # Mix of valid and heavily corrupted inputs
        p_dict = {
            "000660": pd.DataFrame({"Open": np.linspace(100, 120, days), "Close": np.linspace(100, 120, days), "Volume": 1000}, index=dates),
            "005930": pd.DataFrame({"Open": np.linspace(100, 80, days), "Close": np.linspace(100, 80, days), "Volume": 1000}, index=dates),
            "NVDA": pd.DataFrame({"Open": np.linspace(100, 200, days), "Close": np.linspace(100, 200, days)}, index=dates),
            "CORRUPT_A": pd.DataFrame({"Open": [np.nan] * days, "Close": [np.nan] * days}, index=dates),
            "CORRUPT_B": pd.DataFrame({"Close": [0.0] * days}, index=dates),
            "CORRUPT_C": pd.DataFrame({"Open": [-100] * days, "Close": [-100] * days}, index=dates),
        }

        # Level 2 dictionary with one good book, one corrupted book
        l2_dict = {
            "000660": {
                "bid_prices": np.array([120, 119, 118, 117, 116], dtype=float),
                "bid_sizes": np.array([5000, 3000, 2000, 1000, 500], dtype=float),
                "ask_prices": np.array([121, 122, 123, 124, 125], dtype=float),
                "ask_sizes": np.array([500, 500, 500, 500, 500], dtype=float),
            },
            "CORRUPT_A": {
                "bid_prices": np.array([]),
                "bid_sizes": np.array([]),
                "ask_prices": np.array([]),
                "ask_sizes": np.array([]),
            },
        }

        res_df = self.micro_engine.compute_scores(p_dict, level2_dict=l2_dict)
        self.assertEqual(len(res_df), len(p_dict))
        self.assertFalse(res_df["cross_market_micro_mom_score"].isna().any())

        scores = res_df["cross_market_micro_mom_score"].values
        self.assertTrue(np.all(scores >= 0.05))
        self.assertTrue(np.all(scores <= 0.95))

        # 000660 has strong US leader NVDA tailwind + strong bid OFI -> high bullish score
        s_hynix = res_df.loc[res_df["symbol"] == "000660", "cross_market_micro_mom_score"].iloc[0]
        self.assertGreater(s_hynix, 0.60)

    # =========================================================================
    # Section 5: Execution Latency SLAs Under Full 185-Node Topologies
    # =========================================================================

    def test_adv18_gnn_v2_latency_sla_under_185_nodes(self) -> None:
        """ADV18: GNN v2 3-Hop message passing on full 185 nodes executes strictly under 100.0 ms SLA."""
        days = 25
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {}
        for s in list(self.gnn_engine.all_nodes)[:185]:
            p_dict[s] = pd.DataFrame({"Close": np.linspace(100, 110, days), "Volume": 1000}, index=dates)

        # Warm-up run
        _ = self.gnn_engine.compute_scores(p_dict)

        # Benchmark 5 runs
        latencies_ms = []
        for _ in range(5):
            t0 = time.perf_counter()
            res = self.gnn_engine.compute_scores(p_dict)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(elapsed_ms)
            self.assertEqual(len(res), 185)

        avg_latency = float(np.mean(latencies_ms))
        max_latency = float(np.max(latencies_ms))

        self.assertLess(avg_latency, 100.0, f"Average latency {avg_latency:.2f}ms exceeds 100.0ms SLA target!")
        self.assertLess(max_latency, 120.0, f"Max latency {max_latency:.2f}ms exceeds 120.0ms boundary!")

    def test_adv19_micro_momentum_latency_sla_185_symbols(self) -> None:
        """ADV19: CrossMarketMicroMomentum latency on 185 symbols executes under 600.0 ms."""
        days = 25
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {}
        for s in list(self.gnn_engine.all_nodes)[:185]:
            p_dict[s] = pd.DataFrame({
                "Open": np.linspace(100, 105, days),
                "Close": np.linspace(100, 106, days),
                "Volume": 1000
            }, index=dates)

        # Benchmark
        t0 = time.perf_counter()
        res = self.micro_engine.compute_scores(p_dict)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res), 185)
        self.assertLess(elapsed_ms, 600.0, f"Micro-momentum latency {elapsed_ms:.2f}ms exceeds 600.0ms threshold!")

    # =========================================================================
    # Section 6: Dual-Tree SHA-256 Parity & Registry Integrity
    # =========================================================================

    def test_adv20_dual_tree_sha256_cryptographic_parity(self) -> None:
        """ADV20: 100% SHA-256 bit-for-bit cryptographic parity for both source files."""
        pairs = [
            ("src/core/supply_chain_gnn_v2.py", "trading_system/src/core/supply_chain_gnn_v2.py"),
            ("src/core/cross_market_micro_momentum.py", "trading_system/src/core/cross_market_micro_momentum.py"),
        ]

        for p_src, p_ts in pairs:
            full_src = os.path.join(self.root_dir, p_src)
            full_ts = os.path.join(self.root_dir, p_ts)

            self.assertTrue(os.path.exists(full_src), f"Missing: {full_src}")
            self.assertTrue(os.path.exists(full_ts), f"Missing: {full_ts}")

            with open(full_src, "rb") as f1, open(full_ts, "rb") as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()

            self.assertEqual(h1, h2, f"SHA-256 mismatch between {p_src} and {p_ts}!")

    def test_adv21_strategy_registry_contracts(self) -> None:
        """ADV21: Strategy registry contract validation for both strategies."""
        self.assertIn("supply_chain_gnn_v2", STRATEGY_REGISTRY)
        self.assertIn("cross_market_micro_momentum", STRATEGY_REGISTRY)

        meta_gnn = STRATEGY_REGISTRY["supply_chain_gnn_v2"]
        self.assertEqual(meta_gnn.strategy_id, "supply_chain_gnn_v2")
        self.assertEqual(meta_gnn.score_column, "supply_chain_gnn_v2_score")
        self.assertEqual(meta_gnn.category, "network")

        meta_micro = STRATEGY_REGISTRY["cross_market_micro_momentum"]
        self.assertEqual(meta_micro.strategy_id, "cross_market_micro_momentum")
        self.assertEqual(meta_micro.score_column, "cross_market_micro_mom_score")
        self.assertEqual(meta_micro.category, "microstructure")


if __name__ == "__main__":
    unittest.main()
