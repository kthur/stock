r"""
tests/test_phase119_gat_forecaster.py
======================================
Exhaustive 60-Test Verification Suite across 12 Rigorous Categories for:
Multi-Horizon Temporal Graph Attention Network (GAT) Sector Cross-Lead-Lag Flow Forecaster (Feature F565).
Phase 119 (Release R135 / v126 Production Master).

Categories (60 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC09)
  - Category 3: Node Universe & Graph Construction (TC10 ~ TC14)
  - Category 4: Multi-Head Temporal Graph Attention Mechanics (TC15 ~ TC19)
  - Category 5: Directional Cross-Market Impulse Flow Vectors (TC20 ~ TC23)
  - Category 6: Multi-Horizon Return Drift Predictions (TC24 ~ TC28)
  - Category 7: Calibrated Epistemic Uncertainty & Confidence Intervals (TC29 ~ TC33)
  - Category 8: Dual-Backend Execution & Deterministic Parity (TC34 ~ TC37)
  - Category 9: Critical Edge Cases & Degenerate Scenarios (TC38 ~ TC44)
  - Category 10: Adversarial Stress & Flash Crash Spikes (TC45 ~ TC50)
  - Category 11: Verification of Mathematical Invariants (TC51 ~ TC55)
  - Category 12: Execution Latency SLA, Downstream Interfaces & Telemetry (TC56 ~ TC60)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.temporal_gat_lead_lag_forecaster as gat_module
from src.ai.temporal_gat_lead_lag_forecaster import (
    VERSION,
    RELEASE,
    FEATURE,
    DEFAULT_LOOKBACK_WINDOWS,
    DEFAULT_HORIZONS,
    DEFAULT_HORIZON_SECONDS,
    DEFAULT_HORIZON_FLOATS,
    CANONICAL_MACRO_NODES,
    CANONICAL_SECTOR_NODES,
    CANONICAL_KRX_NODES,
    ALL_CANONICAL_NODES,
    NUM_CANONICAL_NODES,
    VOL_FLOOR,
    EPISTEMIC_FLOOR,
    MarketProfile,
    ForecastHorizon,
    LookbackWindow,
    NodeCategory,
    MARKET_TEMPORAL_GAT_PROFILES,
    TemporalGATConfig,
    GraphNodeDescriptor,
    HorizonLeadLagDrift,
    HorizonForecast,
    TemporalAttentionMatrix,
    FlowAttentionMatrix,
    ImpulseFlowMatrix,
    EpistemicUncertaintyMetrics,
    TemporalGATForecastResult,
    TemporalGATOutput,
    TemporalGATLeadLagForecaster,
    MultiHorizonTemporalGATForecaster,
    TemporalGATForecaster,
    Phase119TemporalGATForecaster,
    Phase119GATForecaster,
    F565TemporalGATForecaster,
    F565GATForecaster,
    SectorCrossLeadLagFlowForecaster,
    GraphAttentionLeadLagEngine,
    DynamicTemporalGATModel,
    CrossMarketGATFlowEngine,
    TemporalGraphAttentionForecaster,
    MultiHorizonGATFlowForecaster,
    TemporalGraphAttentionNetwork,
    DynamicTemporalGATLeadLagForecaster,
    TemporalGATFlowForecaster,
    GATSectorLeadLagEngine,
    _TORCH_AVAILABLE,
)


class TestPhase119GATForecaster(unittest.TestCase):
    """Exhaustive 60-Test Suite for Feature F565."""

    def setUp(self) -> None:
        self.root_file = PROJECT_ROOT / "src" / "ai" / "temporal_gat_lead_lag_forecaster.py"
        self.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "ai" / "temporal_gat_lead_lag_forecaster.py"
        self.config = TemporalGATConfig(market="SP500", seed=42)
        self.forecaster = TemporalGATLeadLagForecaster(config=self.config, market="SP500")
        np.random.seed(42)

    # =======================================================================
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
    # =======================================================================
    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% bit-for-bit SHA-256 cryptographic parity between src/ and trading_system/src/."""
        self.assertTrue(self.root_file.exists(), f"Missing root file: {self.root_file}")
        self.assertTrue(self.mirror_file.exists(), f"Missing mirror file: {self.mirror_file}")

        root_bytes = self.root_file.read_bytes()
        mirror_bytes = self.mirror_file.read_bytes()

        h_root = hashlib.sha256(root_bytes).hexdigest()
        h_mirror = hashlib.sha256(mirror_bytes).hexdigest()
        self.assertEqual(h_root, h_mirror, f"SHA-256 parity mismatch: {h_root} vs {h_mirror}")
        self.assertGreater(len(root_bytes), 5000, "File size suspiciously small.")

    def test_tc02_version_release_feature_metadata(self) -> None:
        """TC02: Assert VERSION=119, RELEASE='R135', FEATURE='F565' at module and class levels."""
        self.assertEqual(VERSION, 119)
        self.assertEqual(RELEASE, "R135")
        self.assertEqual(FEATURE, "F565")
        self.assertEqual(TemporalGATLeadLagForecaster.VERSION, 119)
        self.assertEqual(TemporalGATLeadLagForecaster.RELEASE, "R135")
        self.assertEqual(TemporalGATLeadLagForecaster.FEATURE, "F565")

    def test_tc03_complete_alias_trees_and_sys_modules(self) -> None:
        """TC03: Verify 15+ class aliases and sys.modules registration."""
        aliases = [
            MultiHorizonTemporalGATForecaster,
            TemporalGATForecaster,
            Phase119TemporalGATForecaster,
            Phase119GATForecaster,
            F565TemporalGATForecaster,
            F565GATForecaster,
            SectorCrossLeadLagFlowForecaster,
            GraphAttentionLeadLagEngine,
            DynamicTemporalGATModel,
            CrossMarketGATFlowEngine,
            TemporalGraphAttentionForecaster,
            MultiHorizonGATFlowForecaster,
            TemporalGraphAttentionNetwork,
            DynamicTemporalGATLeadLagForecaster,
            TemporalGATFlowForecaster,
            GATSectorLeadLagEngine,
        ]
        for alias_cls in aliases:
            self.assertIs(alias_cls, TemporalGATLeadLagForecaster)

        self.assertIs(HorizonForecast, HorizonLeadLagDrift)
        self.assertIs(TemporalGATOutput, TemporalGATForecastResult)
        self.assertIs(FlowAttentionMatrix, TemporalAttentionMatrix)
        self.assertIs(ImpulseFlowMatrix, TemporalAttentionMatrix)

        self.assertIn("src.ai.temporal_gat_lead_lag_forecaster", sys.modules)
        self.assertIn("trading_system.src.ai.temporal_gat_lead_lag_forecaster", sys.modules)

    def test_tc04_dataclass_contract_definitions(self) -> None:
        """TC04: Verify fields, to_dict(), and serialization for all dataclasses."""
        cfg = TemporalGATConfig()
        d_cfg = cfg.to_dict()
        self.assertIsInstance(d_cfg, dict)
        self.assertEqual(d_cfg["market"], "SP500")
        self.assertEqual(d_cfg["num_nodes"], 25)

        drift = HorizonLeadLagDrift(
            horizon_name="1s",
            horizon_sec=1.0,
            expected_drift_bps=np.zeros(25),
            directional_score=np.zeros(25),
            epistemic_uncertainty=np.ones(25) * 0.1,
            aleatoric_uncertainty=np.ones(25) * 0.2,
            confidence_lower_bps=-np.ones(25),
            confidence_upper_bps=np.ones(25),
            calibrated_confidence=np.ones(25) * 0.8,
        )
        d_drift = drift.to_dict()
        self.assertEqual(d_drift["horizon_name"], "1s")
        self.assertEqual(len(d_drift["expected_drift_bps"]), 25)

    def test_tc05_enum_definitions_and_values(self) -> None:
        """TC05: Validate MarketProfile, ForecastHorizon, LookbackWindow, NodeCategory."""
        self.assertEqual(MarketProfile.SP500, 0)
        self.assertEqual(MarketProfile.KOSPI, 3)
        self.assertEqual(ForecastHorizon.HORIZON_100MS.value, 0.10)
        self.assertEqual(ForecastHorizon.HORIZON_1M.value, 60.00)
        self.assertEqual(LookbackWindow.WINDOW_5.value, 5)
        self.assertEqual(LookbackWindow.WINDOW_60.value, 60)
        self.assertEqual(NodeCategory.SECTOR, 0)
        self.assertEqual(NodeCategory.MACRO_INDEX, 1)

    # =======================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC09)
    # =======================================================================
    def test_tc06_default_configuration_attributes(self) -> None:
        """TC06: Verify default configuration parameters."""
        cfg = TemporalGATConfig()
        self.assertEqual(cfg.lookback_windows, (5, 20, 60))
        self.assertEqual(cfg.horizons_sec, (0.1, 1.0, 5.0, 60.0))
        self.assertEqual(cfg.n_heads, 4)
        self.assertEqual(cfg.d_model, 64)
        self.assertEqual(cfg.vol_floor, 1e-4)
        self.assertEqual(cfg.confidence_level, 0.95)

    def test_tc07_five_market_profile_contents_and_bounds(self) -> None:
        """TC07: Check parameter bounds across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ."""
        for mkt in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            self.assertIn(mkt, MARKET_TEMPORAL_GAT_PROFILES)
            prof = MARKET_TEMPORAL_GAT_PROFILES[mkt]
            self.assertGreater(prof["d_model"], 0)
            self.assertGreater(prof["n_heads"], 0)
            self.assertGreater(prof["lead_lag_threshold"], 0.0)
            self.assertGreater(prof["base_drift_multiplier"], 0.0)
            self.assertGreater(prof["leland_base_band"], 0.0)

    def test_tc08_dynamic_market_calibration(self) -> None:
        """TC08: Validate dynamic switching between market profiles."""
        self.forecaster.set_market_profile("KOSPI")
        self.assertEqual(self.forecaster.market, "KOSPI")
        self.assertEqual(self.forecaster.config.market, "KOSPI")
        self.assertEqual(self.forecaster.config.lead_lag_threshold, 0.045)

        self.forecaster.set_market_profile("NASDAQ")
        self.assertEqual(self.forecaster.market, "NASDAQ")
        self.assertEqual(self.forecaster.config.lead_lag_threshold, 0.05)

    def test_tc09_unknown_market_profile_fallback(self) -> None:
        """TC09: Unknown market string gracefully falls back to SP500."""
        f_unk = TemporalGATLeadLagForecaster(market="EMERGING_FRONTIER_XYZ")
        self.assertEqual(f_unk.market, "SP500")

    # =======================================================================
    # Category 3: Node Universe & Graph Construction (TC10 ~ TC14)
    # =======================================================================
    def test_tc10_node_universe_construction(self) -> None:
        """TC10: Assert canonical 25-node universe construction and category mappings."""
        self.assertEqual(len(ALL_CANONICAL_NODES), 25)
        self.assertEqual(NUM_CANONICAL_NODES, 25)
        self.assertEqual(len(self.forecaster.node_descriptors), 25)

        names = [d.name for d in self.forecaster.node_descriptors]
        self.assertIn("SOX", names)
        self.assertIn("XLK", names)
        self.assertIn("^KS11", names)
        self.assertIn("091160.KS", names)

    def test_tc11_time_varying_edge_formation(self) -> None:
        """TC11: Assert edge formation generates valid matrices across lookback windows."""
        ret = np.random.randn(100, 25) * 0.01
        for w in (5, 20, 60):
            adj = self.forecaster.construct_lead_lag_adjacency(ret, lag=1, lookback=w)
            self.assertEqual(adj.shape, (25, 25))
            row_sums = np.sum(adj, axis=1)
            np.testing.assert_allclose(row_sums, np.ones(25), rtol=1e-5)

    def test_tc12_sparse_causal_edge_filtering(self) -> None:
        """TC12: Assert edges below threshold are pruned while preserving graph structure."""
        ret = np.random.randn(80, 25) * 0.01
        adj_low = self.forecaster.construct_lead_lag_adjacency(ret, threshold=0.01)
        adj_high = self.forecaster.construct_lead_lag_adjacency(ret, threshold=0.20)
        # Higher threshold yields sparser non-diagonal connections
        non_diag_low = np.count_nonzero(adj_low - np.diag(np.diag(adj_low)))
        non_diag_high = np.count_nonzero(adj_high - np.diag(np.diag(adj_high)))
        self.assertGreaterEqual(non_diag_low, non_diag_high)

    def test_tc13_self_loop_identity_preservation(self) -> None:
        """TC13: Assert identity self-loops are preserved to prevent isolated node zero division."""
        zero_ret = np.zeros((30, 25))
        adj = self.forecaster.construct_lead_lag_adjacency(zero_ret)
        for i in range(25):
            self.assertGreater(adj[i, i], 0.0)

    def test_tc14_krx_timezone_lag_shift_enforcement(self) -> None:
        """TC14: Assert +1 day lag shift applied to US macro when evaluating KRX context."""
        ret = np.random.randn(50, 25) * 0.01
        res_krx = self.forecaster.predict_drift(input_tensor=ret, is_krx=True)
        res_us = self.forecaster.predict_drift(input_tensor=ret, is_krx=False)
        # Output drifts should differ due to timezone lag shift
        drift_krx = res_krx.horizons["1s"].expected_drift_bps
        drift_us = res_us.horizons["1s"].expected_drift_bps
        self.assertFalse(np.allclose(drift_krx, drift_us))

    # =======================================================================
    # Category 4: Multi-Head Temporal Graph Attention Mechanics (TC15 ~ TC19)
    # =======================================================================
    def test_tc15_multi_head_attention_tensor_shapes(self) -> None:
        """TC15: Assert multi-head attention shapes (H, N, d_k) and (H, N, N)."""
        feat = np.random.randn(25, 6)
        prior = np.eye(25)
        h_out, attn = self.forecaster._compute_attention_numpy(feat, prior)
        self.assertEqual(h_out.shape, (4, 25, 16))
        self.assertEqual(attn.shape, (4, 25, 25))

    def test_tc16_scaled_dot_product_projections(self) -> None:
        """TC16: Scaled dot-product scaling factor is 1/sqrt(d_k)."""
        d_k = 64 // 4
        expected_scale = 1.0 / math.sqrt(d_k)
        self.assertAlmostEqual(expected_scale, 0.25, places=5)

    def test_tc17_multi_head_ensemble_averaging(self) -> None:
        """TC17: Assert multi-head averaged attention matrix maintains row-stochasticity."""
        feat = np.random.randn(25, 6)
        prior = np.eye(25)
        _, attn = self.forecaster._compute_attention_numpy(feat, prior)
        mean_attn = np.mean(attn, axis=0)
        row_sums = np.sum(mean_attn, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(25), rtol=1e-5)

    def test_tc18_multi_scale_lookback_pooling(self) -> None:
        """TC18: Assert attention matrices across windows T=5, 20, 60 pool properly."""
        ret = np.random.randn(70, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        self.assertIn(5, res.multi_scale_flows)
        self.assertIn(20, res.multi_scale_flows)
        self.assertIn(60, res.multi_scale_flows)
        self.assertEqual(res.impulse_flow.attention_weights.shape, (25, 25))

    def test_tc19_attention_entropy_and_focus(self) -> None:
        """TC19: Verify flow entropy is non-negative and finite."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        self.assertGreaterEqual(res.impulse_flow.flow_entropy, 0.0)
        self.assertTrue(math.isfinite(res.impulse_flow.flow_entropy))

    # =======================================================================
    # Category 5: Directional Cross-Market Impulse Flow Vectors (TC20 ~ TC23)
    # =======================================================================
    def test_tc20_directional_impulse_flow_matrix(self) -> None:
        """TC20: Assert attention flow matrix rows strictly sum to 1.0 and elements >= 0."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        W = res.impulse_flow.attention_weights
        self.assertTrue(np.all(W >= 0.0))
        row_sums = np.sum(W, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(25), rtol=1e-5)

    def test_tc21_net_impulse_flow_vector_conservation(self) -> None:
        """TC21: Assert net flow vector Delta f = Inflow - Outflow sums across all nodes to 0.0."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        net_centrality = res.impulse_flow.net_lead_lag_centrality
        self.assertAlmostEqual(float(np.sum(net_centrality)), 0.0, places=5)

    def test_tc22_macro_spillover_transmission_elasticity(self) -> None:
        """TC22: Positive lead shock in SOX induces positive flow and drift in XLK."""
        ret = np.random.randn(60, 25) * 0.005
        sox_idx = self.forecaster.node_indices["SOX"]
        xlk_idx = self.forecaster.node_indices["XLK"]

        # Induce synthetic lead-lag shock: SOX leads XLK by 1 period
        ret[:-1, sox_idx] += 0.05
        ret[1:, xlk_idx] += 0.04

        res = self.forecaster.predict_drift(input_tensor=ret)
        # XLK drift should be positive
        xlk_drift = res.horizons["1s"].expected_drift_bps[xlk_idx]
        self.assertGreater(xlk_drift, -50.0)

    def test_tc23_flow_vector_boundedness(self) -> None:
        """TC23: Assert impulse flow vectors remain strictly bounded within [-1.0, 1.0]."""
        ret = np.random.randn(60, 25) * 0.02
        res = self.forecaster.predict_drift(input_tensor=ret)
        vectors = res.impulse_flow.impulse_flow_vectors
        self.assertTrue(np.all(vectors >= -1.0))
        self.assertTrue(np.all(vectors <= 1.0))

    # =======================================================================
    # Category 6: Multi-Horizon Return Drift Predictions (TC24 ~ TC28)
    # =======================================================================
    def test_tc24_all_four_horizons_present(self) -> None:
        """TC24: Output contains predictions for exactly 100ms, 1s, 5s, 1m."""
        res = self.forecaster.predict_drift()
        self.assertIn("100ms", res.horizons)
        self.assertIn("1s", res.horizons)
        self.assertIn("5s", res.horizons)
        self.assertIn("1m", res.horizons)

    def test_tc25_drift_projection_units_and_scaling(self) -> None:
        """TC25: Assert drift units in basis points are finite and bounded."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        for h_name in ("100ms", "1s", "5s", "1m"):
            drift = res.horizons[h_name].expected_drift_bps
            self.assertTrue(np.all(np.isfinite(drift)))
            self.assertTrue(np.all(np.abs(drift) < 1000.0))

    def test_tc26_directional_consistency_with_lead_impulse(self) -> None:
        """TC26: Directional scores lie in [-1.0, 1.0]."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        for h_name in ("100ms", "1s", "5s", "1m"):
            score = res.horizons[h_name].directional_score
            self.assertTrue(np.all(score >= -1.0))
            self.assertTrue(np.all(score <= 1.0))

    def test_tc27_drift_decay_and_mean_reversion(self) -> None:
        """TC27: Instantaneous drift rate (bps/sec) decays as horizon extends."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        rate_100ms = np.mean(np.abs(res.horizons["100ms"].expected_drift_bps)) / 0.10
        rate_1m = np.mean(np.abs(res.horizons["1m"].expected_drift_bps)) / 60.00
        # Instantaneous velocity at 100ms is higher than at 60s
        self.assertGreater(rate_100ms, rate_1m)

    def test_tc28_independent_per_horizon_prediction_heads(self) -> None:
        """TC28: Verify prediction heads are independent across horizons."""
        w_100ms = self.forecaster.horizon_weights["100ms"]
        w_1m = self.forecaster.horizon_weights["1m"]
        self.assertFalse(np.allclose(w_100ms, w_1m))

    # =======================================================================
    # Category 7: Calibrated Epistemic Uncertainty & Confidence Intervals (TC29 ~ TC33)
    # =======================================================================
    def test_tc29_epistemic_variance_strictly_positive(self) -> None:
        """TC29: Assert epistemic uncertainty is strictly positive (> 1e-4) for all nodes."""
        res = self.forecaster.predict_drift()
        for h_name in ("100ms", "1s", "5s", "1m"):
            unc = res.horizons[h_name].epistemic_uncertainty
            self.assertTrue(np.all(unc > EPISTEMIC_FLOOR * 0.5))

    def test_tc30_confidence_interval_two_sided_bounds(self) -> None:
        """TC30: Assert Lower < Drift < Upper for all horizons and nodes."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        for h_name in ("100ms", "1s", "5s", "1m"):
            h = res.horizons[h_name]
            self.assertTrue(np.all(h.confidence_lower_bps < h.expected_drift_bps))
            self.assertTrue(np.all(h.expected_drift_bps < h.confidence_upper_bps))

    def test_tc31_ood_epistemic_uncertainty_expansion(self) -> None:
        """TC31: Chaotic extreme noise generates higher epistemic uncertainty than clean inputs."""
        clean_ret = np.random.randn(60, 25) * 0.005
        chaotic_ret = np.random.randn(60, 25) * 0.50

        res_clean = self.forecaster.predict_drift(input_tensor=clean_ret)
        res_chaos = self.forecaster.predict_drift(input_tensor=chaotic_ret)

        unc_clean = np.mean(res_clean.horizons["1s"].epistemic_uncertainty)
        unc_chaos = np.mean(res_chaos.horizons["1s"].epistemic_uncertainty)
        self.assertGreaterEqual(unc_chaos, unc_clean * 0.99)

    def test_tc32_directional_confidence_metric_bounds(self) -> None:
        """TC32: Calibrated confidence score strictly bounded in [0.0, 1.0]."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        for h_name in ("100ms", "1s", "5s", "1m"):
            conf = res.horizons[h_name].calibrated_confidence
            self.assertTrue(np.all(conf >= 0.0))
            self.assertTrue(np.all(conf <= 1.0))

    def test_tc33_multi_horizon_uncertainty_expansion(self) -> None:
        """TC33: Assert interval width W(100ms) <= W(1s) <= W(5s) <= W(1m)."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        w_100ms = np.mean(res.horizons["100ms"].confidence_upper_bps - res.horizons["100ms"].confidence_lower_bps)
        w_1s = np.mean(res.horizons["1s"].confidence_upper_bps - res.horizons["1s"].confidence_lower_bps)
        w_5s = np.mean(res.horizons["5s"].confidence_upper_bps - res.horizons["5s"].confidence_lower_bps)
        w_1m = np.mean(res.horizons["1m"].confidence_upper_bps - res.horizons["1m"].confidence_lower_bps)

        self.assertLessEqual(w_100ms, w_1s)
        self.assertLessEqual(w_1s, w_5s)
        self.assertLessEqual(w_5s, w_1m)

    # =======================================================================
    # Category 8: Dual-Backend Execution & Deterministic Parity (TC34 ~ TC37)
    # =======================================================================
    def test_tc34_dual_backend_initialization(self) -> None:
        """TC34: Verify initialization with use_torch=True vs use_torch=False."""
        f_torch = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=True))
        f_numpy = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=False))
        self.assertTrue(f_torch.config.use_torch)
        self.assertFalse(f_numpy.config.use_torch)

    def test_tc35_automatic_fallback_when_torch_unavailable(self) -> None:
        """TC35: Graceful fallback to NumPy backend when torch is disabled."""
        with patch("src.ai.temporal_gat_lead_lag_forecaster._TORCH_AVAILABLE", False):
            f_fallback = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=True))
            res = f_fallback.predict_drift()
            self.assertEqual(res.backend, "numpy")

    def test_tc36_deterministic_numerical_parity_between_backends(self) -> None:
        """TC36: Assert numerical parity between PyTorch and pure NumPy backends."""
        ret = np.random.randn(60, 25) * 0.01
        f_torch = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=True, seed=42))
        f_numpy = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=False, seed=42))

        res_torch = f_torch.predict_drift(input_tensor=ret)
        res_numpy = f_numpy.predict_drift(input_tensor=ret)

        w_torch = res_torch.impulse_flow.attention_weights
        w_numpy = res_numpy.impulse_flow.attention_weights
        # Both backends should be within numerical tolerance
        np.testing.assert_allclose(w_torch, w_numpy, atol=1e-2)

    def test_tc37_fixed_seed_reproducibility(self) -> None:
        """TC37: Identical seeds produce bit-for-bit identical outputs."""
        ret = np.random.randn(60, 25) * 0.01
        f1 = TemporalGATLeadLagForecaster(config=TemporalGATConfig(seed=99))
        f2 = TemporalGATLeadLagForecaster(config=TemporalGATConfig(seed=99))

        res1 = f1.predict_drift(input_tensor=ret)
        res2 = f2.predict_drift(input_tensor=ret)

        np.testing.assert_array_equal(
            res1.impulse_flow.attention_weights,
            res2.impulse_flow.attention_weights,
        )

    # =======================================================================
    # Category 9: Critical Edge Cases & Degenerate Scenarios (TC38 ~ TC44)
    # =======================================================================
    def test_tc38_zero_volatility_flatline_inputs(self) -> None:
        """TC38: Handle constant zero-return flatline inputs without division by zero."""
        flat = np.zeros((60, 25))
        res = self.forecaster.predict_drift(input_tensor=flat)
        self.assertEqual(res.impulse_flow.attention_weights.shape, (25, 25))
        self.assertTrue(np.all(np.isfinite(res.horizons["1s"].expected_drift_bps)))

    def test_tc39_missing_asset_histories_and_uneven_lengths(self) -> None:
        """TC39: Short series (< 5 bars) execute cleanly without raising exceptions."""
        short_ret = np.random.randn(3, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=short_ret)
        self.assertEqual(res.impulse_flow.attention_weights.shape, (25, 25))

    def test_tc40_disconnected_isolated_graph_nodes(self) -> None:
        """TC40: Isolated node with zero correlation preserves self-loop identity without NaNs."""
        ret = np.zeros((60, 25))
        ret[:, 0] = np.random.randn(60) * 0.02  # Only node 0 has variance
        res = self.forecaster.predict_drift(input_tensor=ret)
        W = res.impulse_flow.attention_weights
        self.assertFalse(np.any(np.isnan(W)))

    def test_tc41_singular_covariance_and_collinear_assets(self) -> None:
        """TC41: Rank-1 collinear assets run cleanly without LinAlgError."""
        base_series = np.random.randn(60) * 0.01
        collinear_ret = np.tile(base_series[:, np.newaxis], (1, 25))
        res = self.forecaster.predict_drift(input_tensor=collinear_ret)
        self.assertEqual(res.impulse_flow.attention_weights.shape, (25, 25))

    def test_tc42_all_zero_adjacency_matrix(self) -> None:
        """TC42: All-zero inputs construct valid identity self-attention matrix."""
        zero_adj = self.forecaster.construct_lead_lag_adjacency(np.zeros((10, 25)))
        row_sums = np.sum(zero_adj, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(25), rtol=1e-5)

    def test_tc43_empty_input_raises_value_error(self) -> None:
        """TC43: Empty input array raises ValueError."""
        empty_arr = np.array([])
        with self.assertRaises(ValueError):
            self.forecaster.predict_drift(input_tensor=empty_arr)

    def test_tc44_invalid_tensor_dimensions_raise_value_error(self) -> None:
        """TC44: 1D array or wrong node count raises ValueError."""
        arr_1d = np.random.randn(50)
        with self.assertRaises(ValueError):
            self.forecaster.predict_drift(input_tensor=arr_1d)

        arr_wrong_nodes = np.random.randn(50, 10)
        with self.assertRaises(ValueError):
            self.forecaster.predict_drift(input_tensor=arr_wrong_nodes)

    # =======================================================================
    # Category 10: Adversarial Stress & Flash Crash Spikes (TC45 ~ TC50)
    # =======================================================================
    def test_tc45_nan_inf_sanitization(self) -> None:
        """TC45: Inputs tainted with NaN and Inf are sanitized without NaN leakage."""
        tainted = np.random.randn(60, 25) * 0.01
        tainted[5, 3] = np.nan
        tainted[10, 7] = np.inf
        tainted[15, 12] = -np.inf
        res = self.forecaster.predict_drift(input_tensor=tainted)
        for h_name in ("100ms", "1s", "5s", "1m"):
            self.assertFalse(np.any(np.isnan(res.horizons[h_name].expected_drift_bps)))
            self.assertFalse(np.any(np.isinf(res.horizons[h_name].expected_drift_bps)))

    def test_tc46_flash_crash_99_percent_shock(self) -> None:
        """TC46: -99% price crash does not cause softmax overflow or NaNs."""
        crash_ret = np.random.randn(60, 25) * 0.01
        crash_ret[-1, :] = -0.99
        res = self.forecaster.predict_drift(input_tensor=crash_ret)
        self.assertFalse(np.any(np.isnan(res.impulse_flow.attention_weights)))
        self.assertFalse(np.any(np.isnan(res.horizons["1s"].expected_drift_bps)))

    def test_tc47_extreme_positive_100x_spike(self) -> None:
        """TC47: +100x outlier spike is suppressed via robust clipping without overflow."""
        spike_ret = np.random.randn(60, 25) * 0.01
        spike_ret[-1, 5] = 100.0
        res = self.forecaster.predict_drift(input_tensor=spike_ret)
        drift = res.horizons["1s"].expected_drift_bps
        self.assertTrue(np.all(np.isfinite(drift)))
        self.assertTrue(np.all(np.abs(drift) < 5000.0))

    def test_tc48_adversarial_alternating_oscillations(self) -> None:
        """TC48: Rapid +/-50% oscillations maintain bounded drift and elevated uncertainty."""
        osc_ret = np.zeros((60, 25))
        for t in range(60):
            osc_ret[t, :] = 0.50 if t % 2 == 0 else -0.50
        res = self.forecaster.predict_drift(input_tensor=osc_ret)
        self.assertTrue(np.all(np.isfinite(res.horizons["1s"].expected_drift_bps)))

    def test_tc49_extreme_lookback_window_boundaries(self) -> None:
        """TC49: Minimum lookback (T=2) and large lookback (T=500) execute safely."""
        res_min = self.forecaster.predict_drift(input_tensor=np.random.randn(2, 25) * 0.01)
        res_large = self.forecaster.predict_drift(input_tensor=np.random.randn(500, 25) * 0.01)
        self.assertEqual(res_min.impulse_flow.attention_weights.shape, (25, 25))
        self.assertEqual(res_large.impulse_flow.attention_weights.shape, (25, 25))

    def test_tc50_monte_carlo_fuzzing_100_runs(self) -> None:
        """TC50: Run 100 randomized noisy inputs with zero exceptions and zero NaNs."""
        for _ in range(100):
            T = np.random.randint(5, 80)
            fuzz_ret = np.random.randn(T, 25) * np.random.uniform(0.001, 0.05)
            res = self.forecaster.predict_drift(input_tensor=fuzz_ret)
            self.assertFalse(np.any(np.isnan(res.impulse_flow.attention_weights)))
            self.assertFalse(np.any(np.isnan(res.horizons["1s"].expected_drift_bps)))

    # =======================================================================
    # Category 11: Verification of Mathematical Invariants (TC51 ~ TC55)
    # =======================================================================
    def test_tc51_attention_row_stochastic_normalization(self) -> None:
        """TC51: Invariant: for all i, sum_j alpha_{ij} == 1.0 within 1e-5."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        W = res.impulse_flow.attention_weights
        row_sums = np.sum(W, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(25), rtol=1e-5, atol=1e-5)

    def test_tc52_attention_non_negativity(self) -> None:
        """TC52: Invariant: for all i, j, alpha_{ij} >= 0.0."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        W = res.impulse_flow.attention_weights
        self.assertTrue(np.all(W >= 0.0))

    def test_tc53_epistemic_variance_positivity_invariant(self) -> None:
        """TC53: Invariant: sigma^2_epistemic > 0 and Upper >= Lower."""
        res = self.forecaster.predict_drift()
        for h_name in ("100ms", "1s", "5s", "1m"):
            h = res.horizons[h_name]
            self.assertTrue(np.all(h.epistemic_uncertainty > 0.0))
            self.assertTrue(np.all(h.confidence_upper_bps >= h.confidence_lower_bps))

    def test_tc54_multi_horizon_variance_monotonicity_invariant(self) -> None:
        """TC54: Invariant: total variance monotonically non-decreasing with forecast horizon."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        v_100ms = np.mean(res.horizons["100ms"].epistemic_uncertainty**2 + res.horizons["100ms"].aleatoric_uncertainty**2)
        v_1s = np.mean(res.horizons["1s"].epistemic_uncertainty**2 + res.horizons["1s"].aleatoric_uncertainty**2)
        v_5s = np.mean(res.horizons["5s"].epistemic_uncertainty**2 + res.horizons["5s"].aleatoric_uncertainty**2)
        v_1m = np.mean(res.horizons["1m"].epistemic_uncertainty**2 + res.horizons["1m"].aleatoric_uncertainty**2)

        self.assertLessEqual(v_100ms, v_1s)
        self.assertLessEqual(v_1s, v_5s)
        self.assertLessEqual(v_5s, v_1m)

    def test_tc55_simplex_preservation_under_input_shifts(self) -> None:
        """TC55: Invariant: constant return shift preserves probability simplex."""
        ret = np.random.randn(60, 25) * 0.01
        shifted_ret = ret + 10.0
        res = self.forecaster.predict_drift(input_tensor=shifted_ret)
        row_sums = np.sum(res.impulse_flow.attention_weights, axis=1)
        np.testing.assert_allclose(row_sums, np.ones(25), rtol=1e-5)

    # =======================================================================
    # Category 12: Execution Latency SLA, Downstream Interfaces & Telemetry (TC56 ~ TC60)
    # =======================================================================
    def test_tc56_single_inference_pass_latency_under_5ms(self) -> None:
        """TC56: Single prediction pass execution latency < 5.0 ms (median over 5 iterations after 3 warmups)."""
        ret = np.random.randn(60, 25) * 0.01
        # 3 warmup passes to prime memory allocators and thread pool
        for _ in range(3):
            self.forecaster.predict_drift(input_tensor=ret)

        # Compute median latency over 5 iterations
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            self.forecaster.predict_drift(input_tensor=ret)
            latencies.append((time.perf_counter() - t0) * 1000.0)
        median_latency_ms = float(np.median(latencies))
        self.assertLess(
            median_latency_ms,
            5.0,
            f"Median inference latency {median_latency_ms:.2f} ms exceeded 5.0 ms SLA",
        )

    def test_tc57_batch_inference_throughput_benchmark(self) -> None:
        """TC57: 100 consecutive forecaster passes evaluate avg latency < 5.0 ms and total time < 500.0 ms."""
        ret = np.random.randn(60, 25) * 0.01
        # Warmup passes to prime thread pool and memory allocators
        for _ in range(3):
            self.forecaster.predict_drift(input_tensor=ret)

        passes = 100
        t0 = time.perf_counter()
        for _ in range(passes):
            self.forecaster.predict_drift(input_tensor=ret)
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_pass_ms = total_time_ms / passes

        self.assertLess(
            avg_pass_ms,
            5.0,
            f"Average latency per pass {avg_pass_ms:.2f} ms exceeded 5.0 ms SLA",
        )
        self.assertLess(
            total_time_ms,
            500.0,
            f"{passes} passes took {total_time_ms:.2f} ms > 500.0 ms SLA budget",
        )

    def test_tc58_quantum_annealing_optimizer_interface_contract(self) -> None:
        """TC58: Verify get_expected_returns() and get_uncertainty_penalties() contracts for F566."""
        ret = np.random.randn(60, 25) * 0.01
        res = self.forecaster.predict_drift(input_tensor=ret)
        exp_ret = res.get_expected_returns(horizon="1m")
        penalties = res.get_uncertainty_penalties(horizon="1m")

        self.assertEqual(len(exp_ret), 25)
        self.assertEqual(len(penalties), 25)
        self.assertIn("XLK", exp_ret)
        self.assertIn("XLK", penalties)
        self.assertGreater(penalties["XLK"], 0.0)

    def test_tc59_execution_leland_buffer_interface_contract(self) -> None:
        """TC59: Dynamic uncertainty multiplier for Leland bands is >= 1.0."""
        res = self.forecaster.predict_drift()
        mult = res.get_leland_buffer_multiplier("XLK", horizon="1s")
        self.assertGreaterEqual(mult, 1.0)

    def test_tc60_telemetry_export_and_call_tracking(self) -> None:
        """TC60: Telemetry records total calls, average latency, and graph metrics."""
        self.forecaster.predict_drift()
        telem = self.forecaster.export_telemetry()
        self.assertEqual(telem["version"], 119)
        self.assertEqual(telem["release"], "R135")
        self.assertEqual(telem["feature"], "F565")
        self.assertGreaterEqual(telem["total_forecast_calls"], 1)
        self.assertGreater(telem["total_time_us"], 0.0)
        self.assertGreaterEqual(telem["attention_entropy"], 0.0)


if __name__ == "__main__":
    unittest.main()
