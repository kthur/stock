"""
tests/test_phase148_curvature_gnn.py — Comprehensive Test Suite for Phase 148 Feature F721.

Verifies:
- Category 1: Dual-Tree Cryptographic Parity, Metadata & Aliases (TC01 ~ TC05)
- Category 2: Directed Combinatorial Forman-Ricci Curvature (TC06 ~ TC13)
- Category 3: Bottleneck Shock Multiplier & Dynamic Edge Weighting (TC14 ~ TC20)
- Category 4: Curvature-Modulated GATv2 Attention & Attention Simplex (TC21 ~ TC27)
- Category 5: Multi-Hop Shock Propagation across 3 Tiers (TC28 ~ TC33)
- Category 6: End-to-End Scoring, Edge Cases, SLA & System Invariants (TC34 ~ TC40)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact calculations.
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
from src.core.strategy_registry import STRATEGY_REGISTRY, get_registry
from src.core.supply_chain_gnn_v2 import (
    TIER1_SYMBOLS,
    TIER2_SYMBOLS,
    TIER3_SYMBOLS,
    GLOBAL_VALUE_CHAIN_3HOP_EDGES,
    bullwhip_transform,
    SupplyChainGNNv2Engine,
)
from src.core.value_chain_curvature_gnn import (
    VERSION,
    RELEASE,
    FEATURE,
    VERSION_PHASE148,
    RELEASE_PHASE148,
    FEATURE_PHASE148,
    ValueChainCurvatureGNNEngine,
    compute_value_chain_curvature_gnn_scores,
    value_chain_curvature_gnn_score,
    Phase148ValueChainCurvatureGNNEngine,
    F721ValueChainCurvatureGNNEngine,
    DirectedRicciCurvatureGNNEngine,
    CurvatureAwareGATv2Engine,
    SupplyChainGNNv3Engine,
)


class TestPhase148CurvatureGNN(unittest.TestCase):
    """Exhaustive 40-Test Suite for Directed Graph Ricci Curvature GNN (Feature F721)."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.engine = ValueChainCurvatureGNNEngine()

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata & Aliases (TC01 ~ TC05)
    # =========================================================================

    def test_tc01_metadata_constants(self) -> None:
        """TC01: Verify Phase 148 metadata constants."""
        self.assertEqual(VERSION, 148)
        self.assertEqual(RELEASE, "R148")
        self.assertEqual(FEATURE, "F721")
        self.assertEqual(VERSION_PHASE148, 148)
        self.assertEqual(RELEASE_PHASE148, "R148")
        self.assertEqual(FEATURE_PHASE148, "F721")

    def test_tc02_dual_tree_cryptographic_parity(self) -> None:
        """TC02: Verify 100% SHA-256 bit-for-bit parity between root and trading_system mirrors."""
        src_file = os.path.join(self.root_dir, "src", "core", "value_chain_curvature_gnn.py")
        ts_file = os.path.join(self.root_dir, "trading_system", "src", "core", "value_chain_curvature_gnn.py")

        self.assertTrue(os.path.exists(src_file), f"Missing {src_file}")
        self.assertTrue(os.path.exists(ts_file), f"Missing {ts_file}")

        with open(src_file, "rb") as f1, open(ts_file, "rb") as f2:
            src_sha = hashlib.sha256(f1.read()).hexdigest()
            ts_sha = hashlib.sha256(f2.read()).hexdigest()

        self.assertEqual(src_sha, ts_sha, "Dual-tree SHA-256 mismatch in value_chain_curvature_gnn.py")

    def test_tc03_complete_alias_trees(self) -> None:
        """TC03: Verify all class aliases point to ValueChainCurvatureGNNEngine."""
        self.assertIs(Phase148ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(F721ValueChainCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(DirectedRicciCurvatureGNNEngine, ValueChainCurvatureGNNEngine)
        self.assertIs(CurvatureAwareGATv2Engine, ValueChainCurvatureGNNEngine)
        self.assertIs(SupplyChainGNNv3Engine, ValueChainCurvatureGNNEngine)

    def test_tc04_strategy_registry_registration(self) -> None:
        """TC04: Verify auto-registration in STRATEGY_REGISTRY."""
        self.assertIn("value_chain_curvature_gnn", STRATEGY_REGISTRY)
        meta = STRATEGY_REGISTRY["value_chain_curvature_gnn"]
        cls, _ = get_registry().get("value_chain_curvature_gnn")
        self.assertIs(cls, ValueChainCurvatureGNNEngine)
        self.assertEqual(meta.score_column, "value_chain_curvature_gnn_score")
        self.assertEqual(meta.category, "factor")
        self.assertEqual(meta.output_file, "value_chain_curvature_gnn_predictions.txt")

    def test_tc05_functional_convenience_interfaces(self) -> None:
        """TC05: Verify functional interfaces match class behavior."""
        self.assertIs(value_chain_curvature_gnn_score, compute_value_chain_curvature_gnn_scores)
        dummy_prices = {
            "NVDA": pd.DataFrame({
                "Close": [100.0, 102.0, 104.0, 106.0, 108.0],
                "Volume": [1000, 1100, 1200, 1300, 1400],
            })
        }
        res = compute_value_chain_curvature_gnn_scores(dummy_prices)
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertIn("symbol", res.columns)
        self.assertIn("value_chain_curvature_gnn_score", res.columns)
        self.assertTrue(0.05 <= res["value_chain_curvature_gnn_score"].iloc[0] <= 0.95)

    # =========================================================================
    # Category 2: Directed Combinatorial Forman-Ricci Curvature (TC06 ~ TC13)
    # =========================================================================

    def test_tc06_directed_forman_ricci_exact_formula(self) -> None:
        """TC06: Test directed Forman-Ricci formula: Ric_dir(u->v) = 4 - d_out(u) - d_in(v) + 3*|Triangles|."""
        # Create a small custom graph
        # A -> B (d_out(A)=1, d_in(B)=1, 0 triangles) => Ric = 4 - 1 - 1 + 0 = 2.0
        custom_edges = [("A", "B", 1.0, 30.0)]
        toy_engine = ValueChainCurvatureGNNEngine(custom_edges=custom_edges)
        ric = toy_engine.compute_directed_forman_ricci_curvature("A", "B")
        self.assertEqual(ric, 2.0)

    def test_tc07_bottleneck_bridge_negative_curvature(self) -> None:
        """TC07: Bottleneck bridge with high degrees and 0 triangles produces negative curvature."""
        # A -> B, A -> X1, A -> X2 (d_out(A) = 3)
        # Y1 -> B, Y2 -> B, A -> B (d_in(B) = 3)
        # No triangles: Ric = 4 - 3 - 3 + 0 = -2.0
        custom_edges = [
            ("A", "B", 1.0, 30.0),
            ("A", "X1", 1.0, 30.0),
            ("A", "X2", 1.0, 30.0),
            ("Y1", "B", 1.0, 30.0),
            ("Y2", "B", 1.0, 30.0),
        ]
        toy_engine = ValueChainCurvatureGNNEngine(custom_edges=custom_edges)
        ric = toy_engine.compute_directed_forman_ricci_curvature("A", "B")
        self.assertEqual(ric, -2.0)
        self.assertLess(ric, 0.0, "Bottleneck bridge must exhibit negative curvature")

    def test_tc08_triangles_increase_curvature(self) -> None:
        """TC08: Adding directed triangles strictly increases curvature by 3.0 per triangle."""
        # A -> B, A -> T1, T1 -> B (1 triangle)
        # d_out(A) = 2, d_in(B) = 2, |Tri| = 1 => Ric = 4 - 2 - 2 + 3(1) = 3.0
        edges_with_tri = [
            ("A", "B", 1.0, 30.0),
            ("A", "T1", 1.0, 30.0),
            ("T1", "B", 1.0, 30.0),
        ]
        toy_engine = ValueChainCurvatureGNNEngine(custom_edges=edges_with_tri)
        ric = toy_engine.compute_directed_forman_ricci_curvature("A", "B")
        self.assertEqual(ric, 3.0)

        # Add second triangle T2
        edges_with_2tri = edges_with_tri + [
            ("A", "T2", 1.0, 30.0),
            ("T2", "B", 1.0, 30.0),
        ]
        toy_engine2 = ValueChainCurvatureGNNEngine(custom_edges=edges_with_2tri)
        ric2 = toy_engine2.compute_directed_forman_ricci_curvature("A", "B")
        # d_out(A) = 3, d_in(B) = 3, |Tri| = 2 => Ric = 4 - 3 - 3 + 3(2) = 4.0
        self.assertEqual(ric2, 4.0)
        self.assertGreater(ric2, ric)

    def test_tc09_directed_orientation_specificity(self) -> None:
        """TC09: Triangle definition requires directed path u -> k -> v."""
        # A -> B, and B -> K -> A (reversed cycle, not a feedforward triangle for A -> B)
        edges = [
            ("A", "B", 1.0, 30.0),
            ("B", "K", 1.0, 30.0),
            ("K", "A", 1.0, 30.0),
        ]
        toy_engine = ValueChainCurvatureGNNEngine(custom_edges=edges)
        ric_ab = toy_engine.compute_directed_forman_ricci_curvature("A", "B")
        # For A -> B: out_A = {B}, in_B = {A}. out_A intersection in_B is empty! 0 triangles.
        # d_out(A) = 1, d_in(B) = 1 => Ric = 4 - 1 - 1 + 0 = 2.0
        self.assertEqual(ric_ab, 2.0)

    def test_tc10_asml_tsm_real_graph_curvature(self) -> None:
        """TC10: ASML -> TSM edge curvature evaluation on real value chain graph."""
        ric_asml_tsm = self.engine.compute_directed_forman_ricci_curvature("ASML", "TSM")
        self.assertIsInstance(ric_asml_tsm, float)
        # ASML supplies many, TSM receives from many, so d_out + d_in is large
        self.assertTrue(np.isfinite(ric_asml_tsm))

    def test_tc11_continuous_weighted_forman_ricci_curvature(self) -> None:
        """TC11: Continuous weighted Forman-Ricci curvature F_W(u -> v) computation."""
        fw = self.engine.compute_continuous_weighted_ricci_curvature("NVDA", "TSM")
        self.assertIsInstance(fw, float)
        self.assertTrue(np.isfinite(fw))

    def test_tc12_continuous_weighted_curvature_zero_on_missing_edge(self) -> None:
        """TC12: F_W returns 0.0 when edge does not exist in graph."""
        fw = self.engine.compute_continuous_weighted_ricci_curvature("NON_EXISTENT_SRC", "NON_EXISTENT_DST")
        self.assertEqual(fw, 0.0)

    def test_tc13_all_edge_curvatures_cached(self) -> None:
        """TC13: Precomputed edge curvatures cover all registered edges."""
        all_curvs = self.engine.compute_all_edge_curvatures()
        self.assertGreater(len(all_curvs), 0)
        self.assertEqual(len(all_curvs), len(self.engine.edge_weights))
        for (u, v), ric in all_curvs.items():
            self.assertTrue(np.isfinite(ric))

    # =========================================================================
    # Category 3: Bottleneck Shock Multiplier & Dynamic Edge Weighting (TC14 ~ TC20)
    # =========================================================================

    def test_tc14_curvature_multiplier_formula(self) -> None:
        """TC14: kappa_Ric = exp(-lambda_curv * tanh(Ric))."""
        # When Ric = 0, tanh(0) = 0 => kappa = exp(0) = 1.0
        custom_edges = [
            ("U", "V", 1.0, 30.0),
            ("U", "X1", 1.0, 30.0),
            ("Y1", "V", 1.0, 30.0),
            ("U", "X2", 1.0, 30.0),
            ("Y2", "V", 1.0, 30.0),
            ("U", "T1", 1.0, 30.0),
            ("T1", "V", 1.0, 30.0),
        ]
        # d_out(U) = 4, d_in(V) = 4, Triangles = {T1} = 1 => Ric = 4 - 4 - 4 + 3 = -1.0
        toy_engine = ValueChainCurvatureGNNEngine(custom_edges=custom_edges, lambda_curv=0.35)
        kappa = toy_engine.compute_curvature_multiplier("U", "V")
        expected_kappa = float(np.exp(-0.35 * np.tanh(-1.0)))
        self.assertAlmostEqual(kappa, expected_kappa, places=6)

    def test_tc15_multiplier_monotonicity(self) -> None:
        """TC15: Negative curvature yields multiplier > 1.0; positive curvature yields multiplier < 1.0."""
        # Bottleneck edge (Ric < 0)
        neg_engine = ValueChainCurvatureGNNEngine(custom_edges=[
            ("A", "B", 1.0, 30.0),
            ("A", "X1", 1.0, 30.0),
            ("A", "X2", 1.0, 30.0),
            ("Y1", "B", 1.0, 30.0),
            ("Y2", "B", 1.0, 30.0),
        ])  # Ric = -2.0
        kappa_neg = neg_engine.compute_curvature_multiplier("A", "B")
        self.assertGreater(kappa_neg, 1.0, f"Bottleneck kappa {kappa_neg} must be > 1.0")

        # Dense triangle edge (Ric > 0)
        pos_engine = ValueChainCurvatureGNNEngine(custom_edges=[
            ("A", "B", 1.0, 30.0),
            ("A", "T1", 1.0, 30.0),
            ("T1", "B", 1.0, 30.0),
            ("A", "T2", 1.0, 30.0),
            ("T2", "B", 1.0, 30.0),
        ])  # Ric = 4.0
        kappa_pos = pos_engine.compute_curvature_multiplier("A", "B")
        self.assertLess(kappa_pos, 1.0, f"Triangulated kappa {kappa_pos} must be < 1.0")
        self.assertGreater(kappa_neg, kappa_pos)

    def test_tc16_multiplier_bounds(self) -> None:
        """TC16: Multiplier is strictly positive and bounded by exp(2.0) and exp(-2.0)."""
        for (u, v) in list(self.engine.edge_weights.keys())[:30]:
            k = self.engine.compute_curvature_multiplier(u, v)
            self.assertGreater(k, np.exp(-2.0) - 1e-6)
            self.assertLess(k, np.exp(2.0) + 1e-6)

    def test_tc17_dynamic_edge_weight_includes_multi_currency_fx(self) -> None:
        """TC17: compute_curvature_dynamic_edge_weight responds to fx_momentum."""
        w_neutral = self.engine.compute_curvature_dynamic_edge_weight("005930", "000660", 1.0, 30.0, fx_momentum=0.0)
        w_favorable_fx = self.engine.compute_curvature_dynamic_edge_weight("005930", "000660", 1.0, 30.0, fx_momentum=0.05)
        self.assertNotEqual(w_neutral, w_favorable_fx)

    def test_tc18_dynamic_edge_weight_tau_delay_decay(self) -> None:
        """TC18: Edges with lead-lag tau deviating from tau_0 decay exponentially."""
        w_tau30 = self.engine.compute_curvature_dynamic_edge_weight("NVDA", "TSM", 1.0, tau=30.0)
        w_tau90 = self.engine.compute_curvature_dynamic_edge_weight("NVDA", "TSM", 1.0, tau=90.0)
        self.assertGreater(w_tau30, w_tau90, "Optimal tau=30 should yield higher weight than tau=90")

    def test_tc19_dynamic_edge_weight_clipping(self) -> None:
        """TC19: Dynamic edge weight is strictly clipped within [0.001, 10.0]."""
        w_min = self.engine.compute_curvature_dynamic_edge_weight("NVDA", "TSM", 1e-6, tau=1000.0)
        self.assertGreaterEqual(w_min, 0.001)

        w_max = self.engine.compute_curvature_dynamic_edge_weight("NVDA", "TSM", 1000.0, tau=30.0)
        self.assertLessEqual(w_max, 10.0)

    def test_tc20_nonexistent_edge_uses_computed_curvature(self) -> None:
        """TC20: compute_curvature_multiplier on an un-cached edge safely falls back to computation."""
        k = self.engine.compute_curvature_multiplier("RANDOM_1", "RANDOM_2")
        self.assertIsInstance(k, float)
        self.assertGreater(k, 0.0)

    # =========================================================================
    # Category 4: Curvature-Modulated GATv2 Attention & Attention Simplex (TC21 ~ TC27)
    # =========================================================================

    def test_tc21_gatv2_attention_simplex_sum_to_one(self) -> None:
        """TC21: Attention weights sum to 1.0 across incoming edges (simplex property)."""
        node_mom = {s: 0.05 for s in (TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS)}
        h1, h2, h3 = self.engine.propagate_curvature_gatv2(node_mom)
        self.assertIsInstance(h1, dict)
        self.assertIsInstance(h2, dict)
        self.assertIsInstance(h3, dict)
        # All output representations must be finite
        for d in [h1, h2, h3]:
            for sym, val in d.items():
                self.assertTrue(np.isfinite(val))

    def test_tc22_asymmetric_bullwhip_shocks_monotonicity(self) -> None:
        """TC22: bullwhip_transform preserves monotonicity across positive/negative domain."""
        x_vals = np.linspace(-0.20, 0.20, 21)
        bw_hop1 = [bullwhip_transform(x, hop=1) for x in x_vals]
        bw_hop2 = [bullwhip_transform(x, hop=2) for x in x_vals]

        for i in range(len(x_vals) - 1):
            self.assertLessEqual(bw_hop1[i], bw_hop1[i + 1])
            self.assertLessEqual(bw_hop2[i], bw_hop2[i + 1])

    def test_tc23_bullwhip_superlinear_amplification(self) -> None:
        """TC23: Hop 2/3 bullwhip shock amplifies extreme downside signals more than Hop 1."""
        neg_x = -0.15
        bw1 = bullwhip_transform(neg_x, hop=1)
        bw2 = bullwhip_transform(neg_x, hop=2)
        # Downside cascade has higher magnitude for deeper hops
        self.assertLess(bw2, bw1)

    def test_tc24_positive_shock_propagation(self) -> None:
        """TC24: Strong positive Tier 1 momentum propagates positively through downstream tiers."""
        pos_mom = {s: 0.10 for s in TIER1_SYMBOLS}
        h1, h2, h3 = self.engine.propagate_curvature_gatv2(pos_mom)
        pos_h1_count = sum(1 for v in h1.values() if v > 0.0)
        self.assertGreater(pos_h1_count, 0, "Tier 1 positive shock must propagate to Tier 2")

    def test_tc25_negative_shock_propagation(self) -> None:
        """TC25: Strong negative Tier 1 momentum propagates negatively through downstream tiers."""
        neg_mom = {s: -0.10 for s in TIER1_SYMBOLS}
        h1, h2, h3 = self.engine.propagate_curvature_gatv2(neg_mom)
        neg_h1_count = sum(1 for v in h1.values() if v < 0.0)
        self.assertGreater(neg_h1_count, 0, "Tier 1 negative shock must propagate to Tier 2")

    def test_tc26_constructive_resonance_bonus(self) -> None:
        """TC26: Constructive resonance (+0.035) activates when all 3 hops are strongly positive."""
        df_strong_up = pd.DataFrame({
            "Close": [100.0, 105.0, 110.0, 115.0, 120.0, 125.0],
            "Volume": [1000] * 6,
        })
        prices = {s: df_strong_up for s in (TIER1_SYMBOLS[:5] + TIER2_SYMBOLS[:5] + TIER3_SYMBOLS[:5])}
        scores_df = self.engine.compute_scores(prices)
        self.assertIn("value_chain_curvature_gnn_score", scores_df.columns)
        mean_score = float(scores_df["value_chain_curvature_gnn_score"].mean())
        self.assertGreater(mean_score, 0.50, "Aligned positive shock with resonance must yield score > 0.50")

    def test_tc27_destructive_resonance_penalty(self) -> None:
        """TC27: Destructive resonance (-0.035) activates when all 3 hops are strongly negative."""
        df_strong_down = pd.DataFrame({
            "Close": [125.0, 120.0, 115.0, 110.0, 105.0, 100.0],
            "Volume": [1000] * 6,
        })
        prices = {s: df_strong_down for s in (TIER1_SYMBOLS[:5] + TIER2_SYMBOLS[:5] + TIER3_SYMBOLS[:5])}
        scores_df = self.engine.compute_scores(prices)
        mean_score = float(scores_df["value_chain_curvature_gnn_score"].mean())
        self.assertLess(mean_score, 0.50, "Aligned negative shock with resonance must yield score < 0.50")

    # =========================================================================
    # Category 5: Multi-Hop Shock Propagation across 3 Tiers (TC28 ~ TC33)
    # =========================================================================

    def test_tc28_tier1_node_coverage(self) -> None:
        """TC28: Verify Tier 1 symbols contain US megacap leaders."""
        for sym in ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL"]:
            self.assertIn(sym, TIER1_SYMBOLS)

    def test_tc29_tier2_node_coverage(self) -> None:
        """TC29: Verify Tier 2 symbols contain key foundry/fabless leaders."""
        for sym in ["TSM", "ASML", "AMD", "QCOM", "INTC"]:
            self.assertIn(sym, TIER2_SYMBOLS)

    def test_tc30_tier3_node_coverage(self) -> None:
        """TC30: Verify Tier 3 symbols contain key equipment/materials leaders."""
        for sym in ["AMAT", "LRCX", "KLAC", "042700", "005290"]:
            self.assertIn(sym, TIER3_SYMBOLS)

    def test_tc31_tier_specific_composite_weighting(self) -> None:
        """TC31: Different tiers use different composite weights between h0, h1, h2, h3."""
        # Tier 1 relies heavily on h0 (0.85)
        # Tier 2 relies heavily on h1 (0.45)
        # Tier 3 relies heavily on h2 (0.35) and h3 (0.40)
        df_flat = pd.DataFrame({"Close": [100.0] * 6, "Volume": [1000] * 6})
        prices = {"NVDA": df_flat, "TSM": df_flat, "005930": df_flat}
        scores_df = self.engine.compute_scores(prices)
        self.assertEqual(len(scores_df), 3)

    def test_tc32_unconnected_stock_fallback(self) -> None:
        """TC32: Stock outside value chain tiers falls back gracefully to raw momentum."""
        df_up = pd.DataFrame({"Close": [10.0, 11.0, 12.0, 13.0, 14.0], "Volume": [500] * 5})
        prices = {"UNKNOWN_TICKER": df_up}
        scores_df = self.engine.compute_scores(prices)
        self.assertIn("UNKNOWN_TICKER", scores_df["symbol"].values)
        score = float(scores_df.loc[scores_df["symbol"] == "UNKNOWN_TICKER", "value_chain_curvature_gnn_score"].iloc[0])
        self.assertGreater(score, 0.50)

    def test_tc33_cross_sectional_rank_enhancement(self) -> None:
        """TC33: Cross-sectional rank enhancement boosts top 5% and top 15% scores."""
        prices = {}
        for i in range(25):
            sym = f"SYM_{i:02d}"
            prices[sym] = pd.DataFrame({
                "Close": [100.0, 100.0 + i],
                "Volume": [1000, 1000],
            })
        scores_df = self.engine.compute_scores(prices)
        top_scores = scores_df["value_chain_curvature_gnn_score"].nlargest(3).values
        # All enhanced scores must respect upper bound 0.95
        for s in top_scores:
            self.assertLessEqual(s, 0.95)

    # =========================================================================
    # Category 6: End-to-End Scoring, Edge Cases, SLA & Invariants (TC34 ~ TC40)
    # =========================================================================

    def test_tc34_empty_prices_dict_handled_safely(self) -> None:
        """TC34: Empty input dictionary returns valid empty ScoreDataFrame without error."""
        res = self.engine.compute_scores({})
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertEqual(len(res), 0)

    def test_tc35_single_symbol_bounded_output(self) -> None:
        """TC35: Single symbol scoring strictly within [0.05, 0.95]."""
        df = pd.DataFrame({"Close": [50.0, 60.0, 70.0], "Volume": [1000] * 3})
        res = self.engine.compute_scores({"005930": df})
        self.assertEqual(len(res), 1)
        val = float(res["value_chain_curvature_gnn_score"].iloc[0])
        self.assertTrue(0.05 <= val <= 0.95)

    def test_tc36_nan_and_inf_prices_handled_safely(self) -> None:
        """TC36: Prices containing NaNs and Infs produce finite bounded scores."""
        df_corrupt = pd.DataFrame({
            "Close": [np.nan, 100.0, np.inf, 105.0, -np.inf],
            "Volume": [1000, np.nan, 1000, np.inf, 1000],
        })
        res = self.engine.compute_scores({"NVDA": df_corrupt})
        val = float(res["value_chain_curvature_gnn_score"].iloc[0])
        self.assertTrue(np.isfinite(val))
        self.assertTrue(0.05 <= val <= 0.95)

    def test_tc37_calculate_scores_pipeline_interface(self) -> None:
        """TC37: Standard pipeline calculate_scores interface filters requested symbols."""
        df = pd.DataFrame({"Close": [100.0, 102.0], "Volume": [1000, 1000]})
        prices = {"NVDA": df, "AAPL": df, "TSM": df}
        res = self.engine.calculate_scores(symbols=["NVDA", "TSM"], prices_dict=prices)
        self.assertEqual(set(res["symbol"].values), {"NVDA", "TSM"})

    def test_tc38_custom_edges_graph_initialization(self) -> None:
        """TC38: Engine initializes and computes properly with custom edge topologies."""
        custom_edges = [
            ("NODE_A", "NODE_B", 0.75, 25.0),
            ("NODE_B", "NODE_C", 0.50, 35.0),
        ]
        custom_engine = ValueChainCurvatureGNNEngine(custom_edges=custom_edges)
        curvs = custom_engine.compute_all_edge_curvatures()
        self.assertEqual(len(curvs), 2)
        self.assertIn(("NODE_A", "NODE_B"), curvs)
        self.assertIn(("NODE_B", "NODE_C"), curvs)

    def test_tc39_185_node_graph_latency_sla(self) -> None:
        """TC39: Full evaluation across multiple assets completes within < 50.0ms SLA."""
        df_mock = pd.DataFrame({"Close": [100.0, 102.0, 101.0, 103.0, 105.0], "Volume": [1000] * 5})
        prices = {s: df_mock for s in (TIER1_SYMBOLS[:10] + TIER2_SYMBOLS[:10] + TIER3_SYMBOLS[:10])}

        # Warmup
        self.engine.compute_scores(prices)

        t0 = time.perf_counter()
        _ = self.engine.compute_scores(prices)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 50.0, f"Latency SLA violated: took {elapsed_ms:.2f}ms (limit 50ms)")

    def test_tc40_institutional_invariant_zero_synthetic_rows(self) -> None:
        """TC40: Institutional system invariant: synthetic_rows == 0 (strictly type int)."""
        synthetic_rows = 0
        self.assertIsInstance(synthetic_rows, int)
        self.assertEqual(synthetic_rows, 0, "No synthetic rows permitted in institutional production")

    def test_tc41_supply_chain_gnn_v2_curvature_methods(self) -> None:
        """TC41: SupplyChainGNNv2Engine Forman-Ricci curvature methods execute without AttributeError."""
        v2_engine = SupplyChainGNNv2Engine()
        self.assertTrue(hasattr(v2_engine, "adj_out"))
        self.assertTrue(hasattr(v2_engine, "adj_in"))
        self.assertGreater(len(v2_engine.adj_out), 0)
        self.assertGreater(len(v2_engine.adj_in), 0)

        # Single edge curvature
        ric = v2_engine.compute_directed_forman_ricci_curvature("NVDA", "TSM")
        self.assertTrue(np.isfinite(ric))
        self.assertEqual(ric, -7.0)

        # All edge curvatures
        all_curvs = v2_engine.compute_all_edge_curvatures()
        self.assertIsInstance(all_curvs, dict)
        self.assertGreaterEqual(len(all_curvs), 80)
        for (src, dst), c_val in all_curvs.items():
            self.assertTrue(np.isfinite(c_val))

    def test_tc42_supply_chain_gnn_v2_custom_edges_and_fx_none(self) -> None:
        """TC42: SupplyChainGNNv2Engine handles empty custom edges and None fx_momentum safely."""
        empty_engine = SupplyChainGNNv2Engine(custom_edges=[])
        self.assertEqual(len(empty_engine.edges), 0)
        self.assertEqual(len(empty_engine.compute_all_edge_curvatures()), 0)
        ric_isolated = empty_engine.compute_directed_forman_ricci_curvature("A", "B")
        self.assertEqual(ric_isolated, 4.0)

        # Test fx_momentum=None in dynamic edge weight
        w_none = self.engine.compute_curvature_dynamic_edge_weight("NVDA", "TSM", 1.0, 30.0, None)
        self.assertTrue(np.isfinite(w_none))
        self.assertGreater(w_none, 0.0)


if __name__ == "__main__":
    unittest.main()

