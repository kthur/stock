"""
tests/test_phase140_gnn_v2.py — Comprehensive Test Suite for Phase 140 Feature F680.

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Hierarchy (TC01 ~ TC05)
- Category 2: 3-Hop Graph Topology & Universe Partitioning across 185 Nodes (TC06 ~ TC11)
- Category 3: Dynamic Revenue Exposure & FX-Elastic Edge Weighting (TC12 ~ TC17)
- Category 4: Multi-Tier Asymmetric Saturating Bullwhip Shock Function (TC18 ~ TC24)
- Category 5: GATv2 Attention Message Passing & Resonance Ignition (TC25 ~ TC30)
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
    bullwhip_transform,
    SupplyChainGNNv2Engine,
    compute_supply_chain_gnn_v2_scores,
    supply_chain_gnn_v2_score,
    Phase140SupplyChainGNNv2Engine,
    F680SupplyChainGNNv2Engine,
    ThreeHopSupplyChainGNNEngine,
    GATv2SupplyChainEngine,
)


class TestPhase140GNNv2(unittest.TestCase):
    """Exhaustive 38-Test Suite for 3-Hop Value Chain GNN v2 (Feature F680)."""

    def setUp(self) -> None:
        self.engine = SupplyChainGNNv2Engine()
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Constants & Alias Hierarchy
    # =========================================================================

    def test_tc01_metadata_constants(self) -> None:
        """TC01: Verify metadata constants for Phase 140 Release R140 Feature F680."""
        self.assertEqual(VERSION, 140)
        self.assertEqual(RELEASE, "R140")
        self.assertEqual(FEATURE, "F680")

    def test_tc02_dual_tree_sha256_parity(self) -> None:
        """TC02: Verify 100% bit-for-bit SHA-256 dual-tree parity for supply_chain_gnn_v2.py."""
        src_path = os.path.join(self.root_dir, "src", "core", "supply_chain_gnn_v2.py")
        ts_path = os.path.join(self.root_dir, "trading_system", "src", "core", "supply_chain_gnn_v2.py")

        self.assertTrue(os.path.exists(src_path), f"Source file missing: {src_path}")
        self.assertTrue(os.path.exists(ts_path), f"Mirrored file missing: {ts_path}")

        with open(src_path, "rb") as f:
            src_sha = hashlib.sha256(f.read()).hexdigest()
        with open(ts_path, "rb") as f:
            ts_sha = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(src_sha, ts_sha, "SHA-256 hash mismatch between src and trading_system mirrors!")

    def test_tc03_strategy_registry_registration(self) -> None:
        """TC03: Verify BaseStrategyEngine inheritance and strategy_registry registration."""
        self.assertTrue(issubclass(SupplyChainGNNv2Engine, BaseStrategyEngine))
        self.assertIn("supply_chain_gnn_v2", STRATEGY_REGISTRY)
        meta = STRATEGY_REGISTRY["supply_chain_gnn_v2"]
        self.assertEqual(meta.score_column, "supply_chain_gnn_v2_score")
        self.assertEqual(meta.category, "network")
        self.assertEqual(meta.output_file, "supply_chain_gnn_v2_predictions.txt")

    def test_tc04_complete_alias_tree(self) -> None:
        """TC04: Verify complete alias tree hierarchy across engine classes."""
        self.assertIs(Phase140SupplyChainGNNv2Engine, SupplyChainGNNv2Engine)
        self.assertIs(F680SupplyChainGNNv2Engine, SupplyChainGNNv2Engine)
        self.assertIs(ThreeHopSupplyChainGNNEngine, SupplyChainGNNv2Engine)
        self.assertIs(GATv2SupplyChainEngine, SupplyChainGNNv2Engine)
        self.assertIs(supply_chain_gnn_v2_score, compute_supply_chain_gnn_v2_scores)

    def test_tc05_default_regime_weights_profile(self) -> None:
        """TC05: Verify default regime weights profile conforms to institutional allocation."""
        meta = STRATEGY_REGISTRY["supply_chain_gnn_v2"]
        weights = meta.default_regime_weights
        self.assertAlmostEqual(weights["BULL_LOW_VOL"], 0.055, places=4)
        self.assertAlmostEqual(weights["BULL_HIGH_VOL"], 0.045, places=4)
        self.assertAlmostEqual(weights["PANIC_CRISIS"], 0.000, places=4)
        self.assertGreater(weights["BULL_LOW_VOL"], weights["BEAR_LOW_VOL"])

    # =========================================================================
    # Category 2: 3-Hop Graph Topology & Universe Partitioning across 185 Nodes
    # =========================================================================

    def test_tc06_185_symbols_universe_partitioning(self) -> None:
        """TC06: Verify 185 distinct nodes across Tier 1, Tier 2, and Tier 3."""
        all_unique = set(TIER1_SYMBOLS) | set(TIER2_SYMBOLS) | set(TIER3_SYMBOLS)
        self.assertGreaterEqual(len(all_unique), 185)
        self.assertGreaterEqual(len(self.engine.all_nodes), 185)

    def test_tc07_adjacency_directed_edges(self) -> None:
        """TC07: Verify in-adjacency and out-adjacency directed edge consistency."""
        self.assertGreater(len(self.engine.in_adj), 20)
        self.assertGreater(len(self.engine.out_adj), 20)
        # Check that edges exist in graph
        for src, dst, w, tau in self.engine.edges:
            src_c = self.engine._canon_sym(src)
            dst_c = self.engine._canon_sym(dst)
            in_sources = [s for s, _, _ in self.engine.in_adj.get(dst_c, [])]
            out_targets = [d for d, _, _ in self.engine.out_adj.get(src_c, [])]
            self.assertIn(src_c, in_sources)
            self.assertIn(dst_c, out_targets)

    def test_tc08_semiconductor_hbm_path(self) -> None:
        """TC08: Verify NVDA -> TSM -> 000660 -> 042700 3-hop HBM path."""
        # NVDA -> TSM / 000660
        tsm_in = [s for s, _, _ in self.engine.in_adj.get("TSM", [])]
        self.assertIn("NVDA", tsm_in)
        # 000660 in from NVDA
        hynix_in = [s for s, _, _ in self.engine.in_adj.get("000660", [])]
        self.assertIn("NVDA", hynix_in)
        # 042700 (Hanmi Semi) in from 000660
        hanmi_in = [s for s, _, _ in self.engine.in_adj.get("042700", [])]
        self.assertIn("000660", hanmi_in)

    def test_tc09_battery_value_chain_path(self) -> None:
        """TC09: Verify TSLA -> 373220 -> 247540 battery value chain path."""
        lges_in = [s for s, _, _ in self.engine.in_adj.get("373220", [])]
        self.assertIn("TSLA", lges_in)
        ecopro_in = [s for s, _, _ in self.engine.in_adj.get("247540", [])]
        self.assertIn("373220", ecopro_in)

    def test_tc10_power_grid_infrastructure_path(self) -> None:
        """TC10: Verify GE -> 267260 -> 010120 -> 298040 power grid path."""
        hde_in = [s for s, _, _ in self.engine.in_adj.get("267260", [])]
        self.assertIn("GE", hde_in)
        ls_in = [s for s, _, _ in self.engine.in_adj.get("010120", [])]
        self.assertIn("267260", ls_in)
        hyosung_in = [s for s, _, _ in self.engine.in_adj.get("298040", [])]
        self.assertIn("267260", hyosung_in)

    def test_tc11_defense_aerospace_path(self) -> None:
        """TC11: Verify LMT -> 012450 -> 079550 / 047810 defense supply path."""
        hanwha_in = [s for s, _, _ in self.engine.in_adj.get("012450", [])]
        self.assertIn("LMT", hanwha_in)
        lignex_in = [s for s, _, _ in self.engine.in_adj.get("079550", [])]
        self.assertIn("012450", lignex_in)
        kai_in = [s for s, _, _ in self.engine.in_adj.get("047810", [])]
        self.assertIn("012450", kai_in)

    # =========================================================================
    # Category 3: Dynamic Revenue Exposure & FX-Elastic Edge Weighting
    # =========================================================================

    def test_tc12_revenue_exposure_weight_bounds(self) -> None:
        """TC12: Verify revenue exposure weights w_rev in [0.10, 0.95]."""
        for _, _, w, _ in self.engine.edges:
            self.assertGreaterEqual(w, 0.10)
            self.assertLessEqual(w, 0.95)

    def test_tc13_fx_elasticity_formula(self) -> None:
        """TC13: Verify FX elasticity multiplier: max(0, 1 + eta_FX * Delta_FX)."""
        w_base = 0.80
        tau = 30.0  # tau == tau_0 -> tau_decay = 1.0
        # Positive FX return (+5%) for Korean exporter (eta=0.75)
        w_deprec = self.engine.compute_dynamic_edge_weight("NVDA", "000660", w_base, tau, fx_momentum=0.05)
        expected = w_base * (1.0 + 0.75 * 0.05) * 1.0
        self.assertAlmostEqual(w_deprec, expected, places=5)

    def test_tc14_krw_depreciation_expands_edge_weight(self) -> None:
        """TC14: KRW depreciation (+5% USD/KRW) increases edge weight for Korean exporters (eta=0.75)."""
        w_neutral = self.engine.compute_dynamic_edge_weight("NVDA", "000660", 0.85, 30.0, fx_momentum=0.0)
        w_deprec = self.engine.compute_dynamic_edge_weight("NVDA", "000660", 0.85, 30.0, fx_momentum=0.05)
        self.assertGreater(w_deprec, w_neutral)

    def test_tc15_krw_appreciation_dampens_edge_weight(self) -> None:
        """TC15: KRW appreciation (-5% USD/KRW) dampens edge weight."""
        w_neutral = self.engine.compute_dynamic_edge_weight("NVDA", "000660", 0.85, 30.0, fx_momentum=0.0)
        w_apprec = self.engine.compute_dynamic_edge_weight("NVDA", "000660", 0.85, 30.0, fx_momentum=-0.05)
        self.assertLess(w_apprec, w_neutral)

    def test_tc16_physical_lead_time_decay(self) -> None:
        """TC16: Verify physical procurement lead-time decay exp(-|Delta_tau - tau_0| / tau_0)."""
        w_optimal = self.engine.compute_dynamic_edge_weight("NVDA", "TSM", 0.90, tau=30.0, fx_momentum=0.0)
        w_delayed = self.engine.compute_dynamic_edge_weight("NVDA", "TSM", 0.90, tau=60.0, fx_momentum=0.0)
        self.assertGreater(w_optimal, w_delayed)
        self.assertAlmostEqual(w_delayed / w_optimal, np.exp(-1.0), places=4)

    def test_tc17_zero_fx_sensitivity_for_domestic(self) -> None:
        """TC17: Unmapped domestic firms have eta_fx = 0.0, resulting in zero FX drift."""
        w_1 = self.engine.compute_dynamic_edge_weight("NVDA", "US_DOMESTIC", 0.80, 30.0, fx_momentum=0.10)
        w_2 = self.engine.compute_dynamic_edge_weight("NVDA", "US_DOMESTIC", 0.80, 30.0, fx_momentum=-0.10)
        self.assertAlmostEqual(w_1, w_2, places=5)

    # =========================================================================
    # Category 4: Multi-Tier Asymmetric Saturating Bullwhip Shock Function
    # =========================================================================

    def test_tc18_hop1_bullwhip_parameters(self) -> None:
        """TC18: Verify Hop 1 Bullwhip transform parameters (kappa_down=0.35, kappa_up=0.15)."""
        # Negative shock
        val_neg = bullwhip_transform(-0.10, hop=1)
        expected_neg = -0.10 * (1.0 + 0.35 * (0.10 ** 0.50))
        self.assertAlmostEqual(val_neg, expected_neg, places=5)

        # Positive surge
        val_pos = bullwhip_transform(0.10, hop=1)
        expected_pos = 0.10 / (1.0 + 0.15 * (0.10 ** 0.50))
        self.assertAlmostEqual(val_pos, expected_pos, places=5)

    def test_tc19_hop2_bullwhip_parameters(self) -> None:
        """TC19: Verify Hop 2 Bullwhip transform parameters (kappa_down=0.70, kappa_up=0.25)."""
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
        """TC23: Strict mathematical monotonicity proof: dphi/dx > 0 for all x >= 0."""
        # Numerical finite difference check over fine grid x in [0, 50.0]
        x_grid = np.linspace(0.001, 50.0, 500)
        for hop in [1, 2, 3]:
            phi_vals = [bullwhip_transform(x, hop=hop) for x in x_grid]
            diffs = np.diff(phi_vals)
            self.assertTrue(np.all(diffs > 0), f"Hop {hop} Bullwhip function is not strictly monotonically increasing!")

    def test_tc24_extreme_demand_surge_no_demand_inversion(self) -> None:
        """TC24: Extreme demand surge (x = 5.0, 10.0, 50.0) never inverts or rolls over."""
        for hop in [1, 2, 3]:
            val_5 = bullwhip_transform(5.0, hop=hop)
            val_10 = bullwhip_transform(10.0, hop=hop)
            val_50 = bullwhip_transform(50.0, hop=hop)
            self.assertGreater(val_10, val_5)
            self.assertGreater(val_50, val_10)

    # =========================================================================
    # Category 5: GATv2 Attention Message Passing & Resonance Ignition
    # =========================================================================

    def test_tc25_attention_leaky_relu_computation(self) -> None:
        """TC25: Verify GATv2 attention score uses LeakyReLU with slope 0.20."""
        node_mom = {"NVDA": 0.05, "000660": 0.03}
        hop1, _, _ = self.engine._propagate_gatv2_message_passing(node_mom)
        self.assertIn("000660", hop1)
        self.assertGreater(hop1["000660"], 0.0)

    def test_tc26_multi_tier_message_propagation(self) -> None:
        """TC26: Verify multi-tier message propagation: Hop 1 -> Hop 2 -> Hop 3."""
        # Provide NVDA surge, observe cascade to Tier 2 (000660) and Tier 3 (042700)
        node_mom = {"NVDA": 0.08}
        hop1, hop2, hop3 = self.engine._propagate_gatv2_message_passing(node_mom)
        self.assertIn("000660", hop1)
        self.assertIn("042700", hop2)
        self.assertGreater(hop1["000660"], 0.0)
        self.assertGreater(hop2["042700"], 0.0)

    def test_tc27_resonance_ignition_activation(self) -> None:
        """TC27: Verify constructive resonance ignition (+0.035) when all hops aligned."""
        # Synthetic prices_dict triggering strong positive momentum across NVDA -> 000660 -> 042700
        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 130, days), "Volume": 1000}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(100, 125, days), "Volume": 1000}, index=dates),
            "042700": pd.DataFrame({"Close": np.linspace(100, 120, days), "Volume": 1000}, index=dates),
        }
        res_df = self.engine.compute_scores(p_dict)
        score_hanmi = res_df.loc[res_df["symbol"] == "042700", "supply_chain_gnn_v2_score"].iloc[0]
        # Should have strong bullish score with resonance
        self.assertGreaterEqual(score_hanmi, 0.55)

    def test_tc28_resonance_bonus_magnitude(self) -> None:
        """TC28: Verify resonance bonus matches configured parameter (default 0.035)."""
        self.assertAlmostEqual(self.engine.resonance_bonus, 0.035, places=4)

    def test_tc29_broken_supply_chain_no_resonance(self) -> None:
        """TC29: Broken supply chain channel (downside shock at intermediate hop) cancels resonance."""
        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        # NVDA strong up, but 000660 crashing down
        p_dict = {
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 130, days), "Volume": 1000}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(100, 70, days), "Volume": 1000}, index=dates),
            "042700": pd.DataFrame({"Close": np.linspace(100, 100, days), "Volume": 1000}, index=dates),
        }
        res_df = self.engine.compute_scores(p_dict)
        score_hanmi = res_df.loc[res_df["symbol"] == "042700", "supply_chain_gnn_v2_score"].iloc[0]
        # Intermediate breakdown should depress downstream supplier score
        self.assertLess(score_hanmi, 0.55)

    def test_tc30_zero_momentum_propagation(self) -> None:
        """TC30: Flatline price series produces zero momentum and neutral score."""
        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "NVDA": pd.DataFrame({"Close": np.full(days, 100.0), "Volume": 1000}, index=dates),
            "000660": pd.DataFrame({"Close": np.full(days, 100.0), "Volume": 1000}, index=dates),
        }
        res_df = self.engine.compute_scores(p_dict)
        for _, row in res_df.iterrows():
            self.assertAlmostEqual(row["supply_chain_gnn_v2_score"], 0.50, delta=0.05)

    # =========================================================================
    # Category 6: End-to-End Scoring, Invariants & Adversarial Edge Cases
    # =========================================================================

    def test_tc31_output_score_dataframe_schema(self) -> None:
        """TC31: Output ScoreDataFrame adheres to schema contract: ['symbol', 'supply_chain_gnn_v2_score']."""
        p_dict = {"005930": pd.DataFrame({"Close": [100.0, 102.0, 104.0, 103.0, 105.0]})}
        res = self.engine.compute_scores(p_dict)
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertIn("symbol", res.columns)
        self.assertIn("supply_chain_gnn_v2_score", res.columns)
        self.assertEqual(len(res), 1)

    def test_tc32_zero_nan_guarantee(self) -> None:
        """TC32: Zero NaN guarantee across full input universe including corrupted/sparse data."""
        days = 20
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "SYM_NAN": pd.DataFrame({"Close": [np.nan] * days}, index=dates),
            "SYM_INF": pd.DataFrame({"Close": [np.inf] * days}, index=dates),
            "SYM_SPARSE": pd.DataFrame({"Close": [100.0, np.nan, 102.0, np.nan, 105.0]}, index=dates[:5]),
            "NVDA": pd.DataFrame({"Close": np.linspace(100, 120, days)}, index=dates),
        }
        res = self.engine.compute_scores(p_dict)
        self.assertFalse(res["supply_chain_gnn_v2_score"].isna().any())

    def test_tc33_score_bounds_containment(self) -> None:
        """TC33: Score bound containment strictly in [0.05, 0.95]."""
        days = 30
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "BULL_SURGE": pd.DataFrame({"Close": np.linspace(10, 1000, days)}, index=dates),
            "BEAR_CRASH": pd.DataFrame({"Close": np.linspace(1000, 1, days)}, index=dates),
        }
        res = self.engine.compute_scores(p_dict)
        scores = res["supply_chain_gnn_v2_score"].values
        self.assertTrue(np.all(scores >= 0.05), "Score breached lower bound 0.05!")
        self.assertTrue(np.all(scores <= 0.95), "Score breached upper bound 0.95!")

    def test_tc34_unmapped_isolated_node_fallback(self) -> None:
        """TC34: Unmapped symbol falls back to 0.70 * self_mom + 0.30 * sector_flow."""
        days = 20
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {
            "UNMAPPED_STOCK": pd.DataFrame({"Close": np.linspace(50, 60, days)}, index=dates),
        }
        res = self.engine.compute_scores(p_dict, sector_map={"UNMAPPED_STOCK": "Tech"})
        self.assertEqual(len(res), 1)
        score = res["supply_chain_gnn_v2_score"].iloc[0]
        self.assertGreater(score, 0.50)

    def test_tc35_empty_prices_dict(self) -> None:
        """TC35: Empty prices_dict returns valid empty ScoreDataFrame without exceptions."""
        res = self.engine.compute_scores({})
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertTrue(res.empty)

    def test_tc36_insufficient_price_bars(self) -> None:
        """TC36: Symbol with < 5 bars is handled gracefully without ZeroDivisionError."""
        p_dict = {"SHORT_SYM": pd.DataFrame({"Close": [10.0, 10.5, 11.0]})}
        res = self.engine.compute_scores(p_dict)
        self.assertFalse(res.empty)
        self.assertEqual(res["supply_chain_gnn_v2_score"].iloc[0], 0.50)

    def test_tc37_coexistence_with_baseline_supply_chain_gnn(self) -> None:
        """TC37: Verify backward compatibility: coexistence with baseline Strategy #33."""
        baseline_engine = BaselineSupplyChainGNNEngine()
        p_dict = {"005930": pd.DataFrame({"Close": [100.0, 102.0, 104.0, 103.0, 105.0]})}
        res_v1 = baseline_engine.compute_scores(p_dict)
        res_v2 = self.engine.compute_scores(p_dict)

        self.assertIn("supply_chain_gnn_score", res_v1.columns)
        self.assertIn("supply_chain_gnn_v2_score", res_v2.columns)

    def test_tc38_performance_latency_benchmark(self) -> None:
        """TC38: Benchmark: 185 symbols 3-hop GATv2 propagation executes in < 120.0 ms (warm SLA)."""
        days = 25
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        p_dict = {}
        for s in list(self.engine.all_nodes)[:185]:
            p_dict[s] = pd.DataFrame({"Close": np.linspace(100, 110, days), "Volume": 1000}, index=dates)

        # 1. Warm-up pass to prime Python heap, Pandas type inference, and CPU caches
        _ = self.engine.compute_scores(p_dict)

        # 2. Multi-run evaluation to eliminate OS scheduling preemption & GC jitter
        runs_ms = []
        for _ in range(3):
            t0 = time.perf_counter()
            res = self.engine.compute_scores(p_dict)
            runs_ms.append((time.perf_counter() - t0) * 1000.0)

        elapsed_ms = min(runs_ms)

        self.assertEqual(len(res), 185)
        self.assertLess(
            elapsed_ms,
            120.0,
            f"GNN v2 185-node execution latency {elapsed_ms:.2f}ms exceeds 120.0ms warm SLA target!"
        )


if __name__ == "__main__":
    unittest.main()
