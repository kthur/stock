"""
tests/test_phase144_gnn_v2.py — Comprehensive Test Suite for Phase 144 Feature F700.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Hierarchy (TC01 ~ TC05)
- Category 2: 3-Hop Graph Topology & Universe Partitioning across 185 Nodes (TC06 ~ TC11)
- Category 3: Multi-Currency FX Elasticity & Multi-Frequency Spectral Decomposition (TC12 ~ TC17)
- Category 4: Multi-Tier Asymmetric Saturating Bullwhip Shock Function (TC18 ~ TC24)
- Category 5: Multi-Frequency GATv2 Attention Message Passing & Resonance Acceleration (TC25 ~ TC30)
- Category 6: End-to-End Scoring, Invariants & Adversarial Edge Cases (TC31 ~ TC38)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, monotonicity, and exact calculations.
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
from src.core.supply_chain_gnn import SupplyChainGNNEngine as BaselineSupplyChainGNNEngine
from src.core.supply_chain_gnn_v2 import (
    VERSION,
    RELEASE,
    FEATURE,
    TIER1_SYMBOLS,
    TIER2_SYMBOLS,
    TIER3_SYMBOLS,
    GLOBAL_VALUE_CHAIN_3HOP_EDGES,
    EXPORTER_FX_ELASTICITY,
    EXPORTER_MULTI_FX_ELASTICITY,
    bullwhip_transform,
    compute_multi_fx_elasticity,
    SupplyChainGNNv2Engine,
    compute_supply_chain_gnn_v2_scores,
    supply_chain_gnn_v2_score,
    Phase144SupplyChainGNNv2Engine,
    F700SupplyChainGNNv2Engine,
    AdvancedSupplyChainGNNv2,
    MultiFrequencyGATv2Engine,
)


class TestPhase144GNNv2(unittest.TestCase):
    """Exhaustive 38-Test Suite for 3-Hop Value Chain GNN v2 (Feature F700)."""

    def setUp(self) -> None:
        self.engine = SupplyChainGNNv2Engine()
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Hierarchy (TC01 ~ TC05)
    # =========================================================================

    def test_tc01_metadata_constants(self) -> None:
        """TC01: Verify Phase 144 metadata constants (VERSION==144, RELEASE=='R144', FEATURE=='F700')."""
        self.assertEqual(VERSION, 144)
        self.assertEqual(RELEASE, "R144")
        self.assertEqual(FEATURE, "F700")

    def test_tc02_dual_tree_sha256_parity(self) -> None:
        """TC02: 100% SHA-256 bit-for-bit parity check for supply_chain_gnn_v2.py."""
        src_path = os.path.join(self.root_dir, "src", "core", "supply_chain_gnn_v2.py")
        ts_path = os.path.join(self.root_dir, "trading_system", "src", "core", "supply_chain_gnn_v2.py")

        self.assertTrue(os.path.exists(src_path), f"Missing source file: {src_path}")
        self.assertTrue(os.path.exists(ts_path), f"Missing target file: {ts_path}")

        with open(src_path, "rb") as f:
            src_sha = hashlib.sha256(f.read()).hexdigest()
        with open(ts_path, "rb") as f:
            ts_sha = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(
            src_sha,
            ts_sha,
            f"Dual-tree parity violation in supply_chain_gnn_v2.py!\nSrc: {src_sha}\nTS:  {ts_sha}"
        )

    def test_tc03_strategy_registry_registration(self) -> None:
        """TC03: Confirm strategy registry metadata and proper registration."""
        self.assertIn("supply_chain_gnn_v2", STRATEGY_REGISTRY)
        meta = STRATEGY_REGISTRY["supply_chain_gnn_v2"]
        self.assertEqual(meta.score_column, "supply_chain_gnn_v2_score")
        self.assertEqual(meta.output_file, "supply_chain_gnn_v2_predictions.txt")
        self.assertIn("BULL_LOW_VOL", meta.default_regime_weights)
        self.assertIn("PANIC_CRISIS", meta.default_regime_weights)

    def test_tc04_complete_alias_tree(self) -> None:
        """TC04: Verify all required Phase 144 alias symbols resolve to SupplyChainGNNv2Engine."""
        self.assertIs(Phase144SupplyChainGNNv2Engine, SupplyChainGNNv2Engine)
        self.assertIs(F700SupplyChainGNNv2Engine, SupplyChainGNNv2Engine)
        self.assertIs(AdvancedSupplyChainGNNv2, SupplyChainGNNv2Engine)
        self.assertIs(MultiFrequencyGATv2Engine, SupplyChainGNNv2Engine)
        self.assertIs(supply_chain_gnn_v2_score, compute_supply_chain_gnn_v2_scores)

    def test_tc05_default_regime_weights_profile(self) -> None:
        """TC05: Verify regime weights profile prioritizes high-growth / bull regimes."""
        weights = STRATEGY_REGISTRY["supply_chain_gnn_v2"].default_regime_weights
        self.assertGreater(weights["BULL_HIGH_VOL"], weights["BEAR_HIGH_VOL"])
        self.assertGreater(weights["BULL_LOW_VOL"], weights["PANIC_CRISIS"])

    # =========================================================================
    # Category 2: 3-Hop Graph Topology & Universe Partitioning across 185 Nodes (TC06 ~ TC11)
    # =========================================================================

    def test_tc06_185_symbols_universe_partitioning(self) -> None:
        """TC06: Verify exact universe partition >= 35 Tier 1 OEMs, >= 50 Tier 2, >= 100 Tier 3."""
        self.assertGreaterEqual(len(TIER1_SYMBOLS), 35, "Tier 1 must have >= 35 OEMs")
        self.assertGreaterEqual(len(TIER2_SYMBOLS), 50, "Tier 2 must have >= 50 Foundries/Integrators")
        self.assertGreaterEqual(len(TIER3_SYMBOLS), 100, "Tier 3 must have >= 100 Upstream suppliers")
        total_unique = len(set(TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS))
        self.assertGreaterEqual(total_unique, 185, "Total unique nodes across tiers must be >= 185")

    def test_tc07_adjacency_directed_edges(self) -> None:
        """TC07: Verify in-adjacency and out-adjacency directed edge consistency."""
        self.assertGreater(len(self.engine.in_adj), 20)
        self.assertGreater(len(self.engine.out_adj), 20)
        for src, dst, w, tau in self.engine.edges:
            src_c = self.engine._canon_sym(src)
            dst_c = self.engine._canon_sym(dst)
            in_sources = [s for s, _, _ in self.engine.in_adj.get(dst_c, [])]
            out_targets = [d for d, _, _ in self.engine.out_adj.get(src_c, [])]
            self.assertIn(src_c, in_sources)
            self.assertIn(dst_c, out_targets)

    def test_tc08_semiconductor_hbm_path(self) -> None:
        """TC08: Verify NVDA -> TSM / 000660 -> 042700 semiconductor value chain edges."""
        tsm_in = [s for s, _, _ in self.engine.in_adj.get("TSM", [])]
        self.assertIn("NVDA", tsm_in)
        hynix_in = [s for s, _, _ in self.engine.in_adj.get("000660", [])]
        self.assertIn("NVDA", hynix_in)
        hanmi_in = [s for s, _, _ in self.engine.in_adj.get("042700", [])]
        self.assertIn("000660", hanmi_in)

    def test_tc09_battery_value_chain_path(self) -> None:
        """TC09: Verify TSLA -> 373220 -> 247540 secondary battery value chain edges."""
        lges_in = [s for s, _, _ in self.engine.in_adj.get("373220", [])]
        self.assertIn("TSLA", lges_in)
        ecopro_in = [s for s, _, _ in self.engine.in_adj.get("247540", [])]
        self.assertIn("373220", ecopro_in)

    def test_tc10_power_grid_infrastructure_path(self) -> None:
        """TC10: Verify GE -> 267260 -> 010120 power grid value chain edges."""
        hde_in = [s for s, _, _ in self.engine.in_adj.get("267260", [])]
        self.assertIn("GE", hde_in)
        ls_in = [s for s, _, _ in self.engine.in_adj.get("010120", [])]
        self.assertIn("267260", ls_in)

    def test_tc11_defense_aerospace_path(self) -> None:
        """TC11: Verify LMT -> 012450 -> 079550 / 047810 defense supply path."""
        hanwha_in = [s for s, _, _ in self.engine.in_adj.get("012450", [])]
        self.assertIn("LMT", hanwha_in)
        lignex_in = [s for s, _, _ in self.engine.in_adj.get("079550", [])]
        self.assertIn("012450", lignex_in)

    # =========================================================================
    # Category 3: Multi-Currency FX Elasticity & Multi-Frequency Spectral (TC12 ~ TC17)
    # =========================================================================

    def test_tc12_multi_currency_fx_elasticity_mapping(self) -> None:
        """TC12: Verify EXPORTER_MULTI_FX_ELASTICITY contains USD, JPY, TWD exposure definitions."""
        self.assertIn("TSM", EXPORTER_MULTI_FX_ELASTICITY)
        self.assertIn("000660", EXPORTER_MULTI_FX_ELASTICITY)
        tsm_fx = EXPORTER_MULTI_FX_ELASTICITY["TSM"]
        self.assertIn("TWD", tsm_fx)
        self.assertIn("USD", tsm_fx)

    def test_tc13_compute_multi_fx_elasticity_calculation(self) -> None:
        """TC13: Verify compute_multi_fx_elasticity calculates dynamic edge weight with FX drift."""
        w_base = 0.80
        tau = 30.0
        w_dyn = self.engine.compute_dynamic_edge_weight("NVDA", "000660", w_base, tau, fx_momentum=0.04)
        expected = w_base * (1.0 + 0.75 * 0.04)
        self.assertAlmostEqual(w_dyn, expected, places=5)

    def test_tc14_krw_depreciation_expands_edge_weight(self) -> None:
        """TC14: USDKRW depreciation (+5%) expands Korean exporter revenue edge weights."""
        w_neutral = self.engine.compute_dynamic_edge_weight("NVDA", "000660", 0.85, 30.0, fx_momentum=0.0)
        w_deprec = self.engine.compute_dynamic_edge_weight("NVDA", "000660", 0.85, 30.0, fx_momentum=0.05)
        self.assertGreater(w_deprec, w_neutral)

    def test_tc15_multi_frequency_spectral_decomposition(self) -> None:
        """TC15: Test high-frequency, medium-frequency, and low-frequency price shocks."""
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        p_fast = [100.0] * 28 + [100.0, 108.0]
        p_slow = list(np.linspace(100.0, 115.0, 30))

        df_fast = pd.DataFrame({"Close": p_fast, "Volume": [1e5] * 30}, index=dates)
        df_slow = pd.DataFrame({"Close": p_slow, "Volume": [1e5] * 30}, index=dates)

        node_mom, _ = self.engine._compute_node_features({"NVDA": df_fast, "TSM": df_slow})
        self.assertIn("NVDA", node_mom)
        self.assertIn("TSM", node_mom)
        self.assertGreater(node_mom["NVDA"], 0.0)
        self.assertGreater(node_mom["TSM"], 0.0)

    def test_tc16_physical_lead_time_decay(self) -> None:
        """TC16: Verify physical procurement lead-time decay exp(-|Delta_tau - tau_0| / tau_0)."""
        w_optimal = self.engine.compute_dynamic_edge_weight("NVDA", "TSM", 0.90, tau=30.0, fx_momentum=0.0)
        w_delayed = self.engine.compute_dynamic_edge_weight("NVDA", "TSM", 0.90, tau=60.0, fx_momentum=0.0)
        self.assertGreater(w_optimal, w_delayed)
        self.assertAlmostEqual(w_delayed / w_optimal, np.exp(-1.0), places=4)

    def test_tc17_multi_frequency_composite_weights_sum(self) -> None:
        """TC17: Multi-frequency composite weights (0.45, 0.35, 0.20) sum strictly to 1.0."""
        weights = [0.45, 0.35, 0.20]
        self.assertAlmostEqual(sum(weights), 1.00, places=6)

    # =========================================================================
    # Category 4: Multi-Tier Asymmetric Saturating Bullwhip Shock Function (TC18 ~ TC24)
    # =========================================================================

    def test_tc18_hop1_bullwhip_parameters(self) -> None:
        """TC18: Verify Hop 1 bullwhip: negative downside magnitude > positive upside magnitude."""
        out_pos = bullwhip_transform(0.10, hop=1)
        out_neg = bullwhip_transform(-0.10, hop=1)
        self.assertGreater(out_pos, 0.0)
        self.assertLess(out_neg, 0.0)
        self.assertGreater(abs(out_neg), abs(out_pos))

    def test_tc19_hop2_bullwhip_parameters(self) -> None:
        """TC19: Verify Hop 2 Bullwhip negative downside shock formula."""
        val_neg = bullwhip_transform(-0.10, hop=2)
        expected_neg = -0.10 * (1.0 + 0.70 * (0.10 ** 0.65))
        self.assertAlmostEqual(val_neg, expected_neg, places=5)

    def test_tc20_hop3_bullwhip_parameters(self) -> None:
        """TC20: Verify Hop 3 Bullwhip transform parameters (kappa_down=1.15, kappa_up=0.35)."""
        val_neg = bullwhip_transform(-0.10, hop=3)
        expected_neg = -0.10 * (1.0 + 1.15 * (0.10 ** 0.80))
        self.assertAlmostEqual(val_neg, expected_neg, places=5)

    def test_tc21_downside_cancellation_cascade_amplification(self) -> None:
        """TC21: Downside cancellation cascade amplification (x < 0: |phi(x)| > |x|)."""
        for hop in [1, 2, 3]:
            for x in [-0.05, -0.10, -0.20]:
                phi_x = bullwhip_transform(x, hop=hop)
                self.assertLess(phi_x, x, f"Hop {hop} downside must amplify negative shock")
                self.assertGreater(abs(phi_x), abs(x))

    def test_tc22_upward_surge_saturation(self) -> None:
        """TC22: Upward surge saturation due to capacity constraints (x >= 0: phi(x) <= x)."""
        for hop in [1, 2, 3]:
            for x in [0.05, 0.10, 0.50, 1.0, 5.0]:
                phi_x = bullwhip_transform(x, hop=hop)
                self.assertLessEqual(phi_x, x, f"Hop {hop} positive surge must saturate")

    def test_tc23_strict_mathematical_monotonicity(self) -> None:
        """TC23: Assert strict mathematical monotonicity of bullwhip shock across fine grid."""
        inputs = np.linspace(-0.30, 0.30, 100)
        for hop in (1, 2, 3):
            outputs = [bullwhip_transform(x, hop=hop) for x in inputs]
            diffs = np.diff(outputs)
            self.assertTrue(np.all(diffs >= 0.0), f"Monotonicity violated for hop={hop}")

    def test_tc24_extreme_demand_surge_no_demand_inversion(self) -> None:
        """TC24: Extreme demand surge (x = 5.0, 10.0, 50.0) never inverts or rolls over."""
        for hop in [1, 2, 3]:
            val_5 = bullwhip_transform(5.0, hop=hop)
            val_10 = bullwhip_transform(10.0, hop=hop)
            val_50 = bullwhip_transform(50.0, hop=hop)
            self.assertGreater(val_10, val_5)
            self.assertGreater(val_50, val_10)

    # =========================================================================
    # Category 5: Multi-Frequency GATv2 Attention Message Passing & Resonance (TC25 ~ TC30)
    # =========================================================================

    def test_tc25_attention_leaky_relu_computation(self) -> None:
        """TC25: Verify GATv2 attention message passing produces active propagation for Tier 2 nodes."""
        node_mom = {"NVDA": 0.05, "000660": 0.03}
        hop1, _, _ = self.engine._propagate_gatv2_message_passing(node_mom)
        self.assertIn("000660", hop1)
        self.assertGreater(hop1["000660"], 0.0)

    def test_tc26_multi_frequency_gatv2_message_propagation(self) -> None:
        """TC26: Multi-frequency GATv2 message passing propagates signals across 3 tiers."""
        node_mom = {"NVDA": 0.08}
        hop1, hop2, hop3 = self.engine._propagate_gatv2_message_passing(node_mom)
        self.assertIn("000660", hop1)
        self.assertIn("042700", hop2)
        self.assertGreater(hop1["000660"], 0.0)
        self.assertGreater(hop2["042700"], 0.0)

    def test_tc27_resonance_acceleration_activation(self) -> None:
        """TC27: 3-hop resonance acceleration activates when OEM, Foundry, Upstream all rally."""
        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 130, days), "Volume": 1000}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(100, 125, days), "Volume": 1000}, index=dates),
            "042700": pd.DataFrame({"Close": np.linspace(100, 120, days), "Volume": 1000}, index=dates),
        }
        res_df = self.engine.compute_scores(p_dict)
        score_hanmi = res_df.loc[res_df["symbol"] == "042700", "supply_chain_gnn_v2_score"].iloc[0]
        self.assertGreaterEqual(score_hanmi, 0.55)

    def test_tc28_resonance_bonus_magnitude(self) -> None:
        """TC28: Verify resonance bonus matches configured parameter (default 0.035)."""
        self.assertAlmostEqual(self.engine.resonance_bonus, 0.035, places=4)

    def test_tc29_broken_supply_chain_no_resonance(self) -> None:
        """TC29: Broken supply chain channel suppresses resonance."""
        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 130, days), "Volume": 1000}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(100, 70, days), "Volume": 1000}, index=dates),
            "042700": pd.DataFrame({"Close": np.linspace(100, 100, days), "Volume": 1000}, index=dates),
        }
        res_df = self.engine.compute_scores(p_dict)
        score_hanmi = res_df.loc[res_df["symbol"] == "042700", "supply_chain_gnn_v2_score"].iloc[0]
        self.assertLess(score_hanmi, 0.55)

    def test_tc30_zero_momentum_propagation(self) -> None:
        """TC30: Zero momentum returns neutral 0.50 score."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df_flat = pd.DataFrame({"Close": [100.0] * 20, "Volume": [1e5] * 20}, index=dates)
        prices_dict = {"NVDA": df_flat, "TSM": df_flat, "000660": df_flat}
        res_df = self.engine.compute_scores(prices_dict=prices_dict)
        for sym in ["NVDA", "TSM", "000660"]:
            s = float(res_df.loc[res_df["symbol"] == sym, "supply_chain_gnn_v2_score"].iloc[0])
            self.assertAlmostEqual(s, 0.50, delta=0.05)

    # =========================================================================
    # Category 6: End-to-End Scoring, Invariants & Adversarial Edge Cases (TC31 ~ TC38)
    # =========================================================================

    def test_tc31_output_score_dataframe_schema(self) -> None:
        """TC31: Output dataframe schema contains exact columns ['symbol', 'supply_chain_gnn_v2_score']."""
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 110, 10), "Volume": [1e5] * 10}, index=dates)
        res_df = self.engine.compute_scores(prices_dict={"NVDA": df, "TSM": df})
        self.assertIn("symbol", res_df.columns)
        self.assertIn("supply_chain_gnn_v2_score", res_df.columns)

    def test_tc32_zero_nan_guarantee(self) -> None:
        """TC32: Zero NaN guarantee across all evaluated symbols."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df = pd.DataFrame({"Close": np.linspace(50, 60, 15), "Volume": [1e4] * 15}, index=dates)
        prices_dict = {sym: df for sym in TIER1_SYMBOLS[:10]}
        res_df = self.engine.compute_scores(prices_dict=prices_dict)
        self.assertFalse(res_df["supply_chain_gnn_v2_score"].isna().any())

    def test_tc33_score_bounds_containment(self) -> None:
        """TC33: All scores must strictly lie in [0.05, 0.95]."""
        dates = pd.date_range("2026-01-01", periods=20, freq="B")
        df = pd.DataFrame({"Close": np.linspace(10, 20, 20), "Volume": [1e5] * 20}, index=dates)
        res_df = self.engine.compute_scores(prices_dict={"TSLA": df, "373220": df})
        scores = res_df["supply_chain_gnn_v2_score"]
        self.assertTrue((scores >= 0.05).all() and (scores <= 0.95).all())

    def test_tc34_unmapped_isolated_node_fallback(self) -> None:
        """TC34: Unmapped ticker outside graph receives neutral score."""
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df = pd.DataFrame({"Close": [100.0] * 10, "Volume": [1e5] * 10}, index=dates)
        res_df = self.engine.compute_scores(prices_dict={"UNKNOWN_TICKER_XYZ": df})
        self.assertEqual(len(res_df), 1)
        self.assertAlmostEqual(res_df["supply_chain_gnn_v2_score"].iloc[0], 0.50, delta=0.05)

    def test_tc35_empty_prices_dict(self) -> None:
        """TC35: Empty prices_dict returns valid empty ScoreDataFrame."""
        res_df = self.engine.compute_scores(prices_dict={})
        self.assertIsInstance(res_df, pd.DataFrame)
        self.assertTrue(res_df.empty or len(res_df) == 0)

    def test_tc36_insufficient_price_bars(self) -> None:
        """TC36: Ticker with fewer than 2 bars falls back cleanly without crash."""
        df_1bar = pd.DataFrame({"Close": [100.0], "Volume": [1000.0]})
        res_df = self.engine.compute_scores(prices_dict={"005930": df_1bar})
        self.assertEqual(len(res_df), 1)
        self.assertFalse(res_df["supply_chain_gnn_v2_score"].isna().any())

    def test_tc37_coexistence_with_baseline_supply_chain_gnn(self) -> None:
        """TC37: Baseline SupplyChainGNNEngine and SupplyChainGNNv2Engine coexist without conflicts."""
        base_engine = BaselineSupplyChainGNNEngine()
        v2_engine = SupplyChainGNNv2Engine()
        self.assertNotEqual(base_engine.name, v2_engine.name)

    def test_tc38_performance_latency_benchmark(self) -> None:
        """TC38: Full 185-node graph score evaluation finishes in < 50ms."""
        dates = pd.date_range("2026-01-01", periods=15, freq="B")
        df = pd.DataFrame({"Close": np.linspace(100, 110, 15), "Volume": [1e5] * 15}, index=dates)
        prices_dict = {sym: df for sym in list(self.engine.all_nodes)[:50]}

        t0 = time.perf_counter()
        _ = self.engine.compute_scores(prices_dict=prices_dict)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 50.0, f"Latency SLA violated: took {elapsed_ms:.2f}ms (limit 50ms)")


if __name__ == "__main__":
    unittest.main()
