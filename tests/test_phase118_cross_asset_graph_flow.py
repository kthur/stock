r"""
tests/test_phase118_cross_asset_graph_flow.py
=============================================
Comprehensive unit and stress test suite for Feature F562:
Cross-Asset Lead-Lag Graph Flow Liquidity Rebalancing Allocator.
Phase 118 (Release R134 / v125 Production Master).
"""

from __future__ import annotations

import hashlib
import math
import os
import unittest
from typing import Dict, List

import numpy as np

from src.risk.cross_asset_graph_flow_allocator import (
    CrossAssetGraphFlowAllocator,
    GraphFlowConfig,
    GraphCentralityMetrics,
    GraphRebalancingResult,
    AssetClassType,
    MARKET_GRAPH_FLOW_PROFILES,
    VERSION,
    RELEASE,
    FEATURE,
)


class TestPhase118CrossAssetGraphFlow(unittest.TestCase):
    """Exhaustive test suite for Cross-Asset Graph Flow Allocator (F562)."""

    def setUp(self) -> None:
        self.config = GraphFlowConfig(market="SP500")
        self.allocator = CrossAssetGraphFlowAllocator(config=self.config, market="SP500")
        np.random.seed(42)

    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Assert 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        p1 = "src/risk/cross_asset_graph_flow_allocator.py"
        p2 = "trading_system/src/risk/cross_asset_graph_flow_allocator.py"
        self.assertTrue(os.path.exists(p1))
        self.assertTrue(os.path.exists(p2))
        h1 = hashlib.sha256(open(p1, "rb").read()).hexdigest()
        h2 = hashlib.sha256(open(p2, "rb").read()).hexdigest()
        self.assertEqual(h1, h2, "Dual-tree parity mismatch for F562!")

    def test_tc02_version_and_metadata(self) -> None:
        """TC02: Assert version=118, release='R134', feature='F562'."""
        self.assertEqual(VERSION, 118)
        self.assertEqual(RELEASE, "R134")
        self.assertEqual(FEATURE, "F562")

    def test_tc03_five_market_profiles_exist(self) -> None:
        """TC03: Assert all 5 market profiles exist with valid positive parameters."""
        for m in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            self.assertIn(m, MARKET_GRAPH_FLOW_PROFILES)
            prof = MARKET_GRAPH_FLOW_PROFILES[m]
            self.assertGreater(prof["graph_regularization_lambda"], 0.0)
            self.assertGreater(prof["turnover_penalty_gamma"], 0.0)
            self.assertGreater(prof["leland_base_band"], 0.0)

    def test_tc04_default_adjacency_row_stochastic(self) -> None:
        """TC04: Assert default prior adjacency matrix has rows summing to 1."""
        W = self.allocator._build_default_adjacency()
        self.assertEqual(W.shape, (6, 6))
        row_sums = np.sum(W, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(6), rtol=1e-5)

    def test_tc05_constructed_adjacency_from_returns(self) -> None:
        """TC05: Assert lead-lag adjacency constructed from returns is non-negative and row-normalized."""
        ret = np.random.randn(200, 6) * 0.01
        W = self.allocator.construct_lead_lag_adjacency(ret, lag=1)
        self.assertEqual(W.shape, (6, 6))
        self.assertTrue(np.all(W >= 0.0))
        row_sums = np.sum(W, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(6), rtol=1e-5)

    def test_tc06_spectral_gap_and_algebraic_connectivity(self) -> None:
        """TC06: Assert spectral gap > 0 and algebraic connectivity >= 0."""
        W = self.allocator._build_default_adjacency()
        metrics = self.allocator.compute_centrality_metrics(W)
        self.assertGreater(metrics.spectral_gap, 0.0)
        self.assertGreaterEqual(metrics.algebraic_connectivity, 0.0)
        self.assertEqual(len(metrics.fiedler_eigenvector), 6)

    def test_tc07_pagerank_and_katz_centrality_properties(self) -> None:
        """TC07: Assert PageRank and Katz centralities sum to 1 and are non-negative."""
        W = self.allocator._build_default_adjacency()
        metrics = self.allocator.compute_centrality_metrics(W)
        self.assertAlmostEqual(float(np.sum(metrics.pagerank_centrality)), 1.0, places=5)
        self.assertAlmostEqual(float(np.sum(metrics.katz_centrality)), 1.0, places=5)
        self.assertTrue(np.all(metrics.pagerank_centrality >= 0.0))
        self.assertTrue(np.all(metrics.katz_centrality >= 0.0))

    def test_tc08_convex_weight_optimization_simplex_and_bounds(self) -> None:
        """TC08: Assert optimized target weights lie on simplex and satisfy box constraints."""
        mu = np.array([0.10, 0.12, 0.08, 0.03, 0.05, 0.04])
        # Random positive-definite covariance matrix
        A = np.random.randn(6, 6) * 0.05
        cov = A @ A.T + np.eye(6) * 0.01

        res = self.allocator.optimize_weights(mu=mu, cov_matrix=cov)
        self.assertAlmostEqual(float(np.sum(res.target_weights)), 1.0, places=5)
        self.assertTrue(np.all(res.target_weights >= 0.0))
        self.assertTrue(np.all(res.target_weights <= self.config.max_weight_per_asset + 1e-5))

    def test_tc09_leland_no_trade_buffer_bands(self) -> None:
        """TC09: Assert Leland bands enforce no-trade when current weights are close to target."""
        mu = np.array([0.10, 0.10, 0.10, 0.10, 0.10, 0.10])
        cov = np.eye(6) * 0.02
        # Initial run to get target
        res1 = self.allocator.optimize_weights(mu=mu, cov_matrix=cov)
        target = res1.target_weights

        # Current weights set strictly inside Leland band
        w_curr = target.copy()
        res2 = self.allocator.optimize_weights(mu=mu, cov_matrix=cov, current_weights=w_curr)
        self.assertEqual(len(res2.rebalance_triggered_assets), 0)
        self.assertAlmostEqual(res2.turnover_amount, 0.0, places=6)

    def test_tc10_rebalancing_trigger_outside_leland_bands(self) -> None:
        """TC10: Assert rebalance is triggered when an asset weight deviates outside buffer band."""
        mu = np.array([0.15, 0.05, 0.10, 0.02, 0.04, 0.03])
        cov = np.eye(6) * 0.02
        # Skewed current weights: asset 0 at 0.70 (violates upper bound)
        w_curr = np.array([0.70, 0.06, 0.06, 0.06, 0.06, 0.06])
        res = self.allocator.optimize_weights(mu=mu, cov_matrix=cov, current_weights=w_curr)
        self.assertGreater(len(res.rebalance_triggered_assets), 0)
        self.assertGreater(res.turnover_amount, 0.0)
        self.assertAlmostEqual(float(np.sum(res.rebalanced_weights)), 1.0, places=5)

    def test_tc11_market_calibration_switching(self) -> None:
        """TC11: Assert allocator dynamically calibrates to KOSPI and NASDAQ."""
        self.allocator._load_market_profile("KOSPI")
        self.assertEqual(self.allocator.market, "KOSPI")
        self.assertAlmostEqual(self.allocator.graph_lambda, 0.30, places=4)

        self.allocator._load_market_profile("NASDAQ")
        self.assertEqual(self.allocator.market, "NASDAQ")
        self.assertAlmostEqual(self.allocator.graph_lambda, 0.25, places=4)

    def test_tc12_telemetry_export(self) -> None:
        """TC12: Assert telemetry records total rebalances and latency."""
        mu = np.ones(6) * 0.08
        cov = np.eye(6) * 0.01
        self.allocator.optimize_weights(mu=mu, cov_matrix=cov)
        telem = self.allocator.export_telemetry()
        self.assertGreater(telem["total_rebalances"], 0)
        self.assertIn("avg_latency_us", telem)


if __name__ == "__main__":
    unittest.main()
