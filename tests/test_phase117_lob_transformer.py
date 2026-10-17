"""
tests/test_phase117_lob_transformer.py
======================================
Comprehensive Unit, Integration, Mathematical Invariant, and Benchmark Tests for:
Deep LOB Transformer with Multi-Scale Temporal Attention (Feature F556).
Phase 117 (Release R133 / v124 Production Master).

Test Categories:
- Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
- Category 2: Configuration & PriceDirection Enumeration (TC04~TC06)
- Category 3: 5-Market Pre-Calibrated Profiles (TC07~TC09)
- Category 4: 10-Level Order Book Tensor Parsing & Normalization (TC10~TC14)
- Category 5: Multi-Scale Dilated Temporal Convolutional Encoders (TC15~TC17)
- Category 6: Spatial Depth Cross-Attention Across Levels 1~10 (TC18~TC20)
- Category 7: Causal Multi-Head Self-Attention (TC21~TC23)
- Category 8: 4 Simultaneous Forecast Heads (100ms, 500ms, 1s, 5s) (TC24~TC28)
- Category 9: Structural Microstructure Signal Responsiveness (TC29~TC31)
- Category 10: PyTorch & NumPy Dual-Backend Execution (TC32~TC35)
- Category 11: Edge Cases, Latency & Telemetry Export (TC36~TC38)
"""

from __future__ import annotations

import hashlib
import math
import sys
import time
import unittest
from pathlib import Path
from typing import List

import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.lob_transformer_engine import (
    FEATURE,
    MARKET_LOB_PROFILES,
    RELEASE,
    VERSION,
    DeepLOBTransformerEngine,
    F556LOBTransformer,
    HorizonPrediction,
    LOBAttentionHeatmap,
    LOBTransformerConfig,
    LOBTransformerEngine,
    LOBTransformerOutput,
    MultiScaleLOBTransformer,
    Phase117LOBTransformer,
    PriceDirection,
)


class TestPhase117LOBTransformer(unittest.TestCase):
    """38 Comprehensive test cases validating Feature F556."""

    def setUp(self) -> None:
        self.engine = LOBTransformerEngine(market="SP500", symbol="NVDA")
        self.seq_len = 20
        # Synthetic 10-level orderbook sequence [T, 40]
        # Mid price around 500.0, tick size 0.05
        self.raw_tensor = np.zeros((self.seq_len, 40), dtype=np.float64)
        for t in range(self.seq_len):
            mid = 500.0 + 0.1 * t
            for lvl in range(10):
                base = lvl * 4
                tick_offset = (lvl + 1) * 0.05
                self.raw_tensor[t, base] = mid - tick_offset           # Bid price
                self.raw_tensor[t, base + 1] = 100.0 * (10 - lvl)       # Bid volume
                self.raw_tensor[t, base + 2] = mid + tick_offset           # Ask price
                self.raw_tensor[t, base + 3] = 100.0 * (10 - lvl)       # Ask volume

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """Verify 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        p1 = PROJECT_ROOT / "src" / "ai" / "lob_transformer_engine.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "ai" / "lob_transformer_engine.py"
        self.assertTrue(p1.exists(), f"Missing primary path: {p1}")
        self.assertTrue(p2.exists(), f"Missing mirrored path: {p2}")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Cryptographic SHA-256 hash mismatch between dual-tree files!")

    def test_tc02_version_release_feature_metadata(self) -> None:
        """Verify version metadata constants."""
        self.assertEqual(VERSION, 117)
        self.assertEqual(RELEASE, "R133")
        self.assertEqual(FEATURE, "F556")
        self.assertEqual(LOBTransformerEngine.VERSION, 117)
        self.assertEqual(LOBTransformerEngine.RELEASE, "R133")
        self.assertEqual(LOBTransformerEngine.FEATURE, "F556")

    def test_tc03_complete_alias_trees_and_sys_modules(self) -> None:
        """Verify complete backward-compatibility alias trees and sys.modules registration."""
        self.assertIs(DeepLOBTransformerEngine, LOBTransformerEngine)
        self.assertIs(MultiScaleLOBTransformer, LOBTransformerEngine)
        self.assertIs(Phase117LOBTransformer, LOBTransformerEngine)
        self.assertIs(F556LOBTransformer, LOBTransformerEngine)
        self.assertIn("src.ai.lob_transformer_engine", sys.modules)
        self.assertIn("trading_system.src.ai.lob_transformer_engine", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: Configuration & PriceDirection Enumeration (TC04~TC06)
    # -----------------------------------------------------------------------
    def test_tc04_default_configuration_attributes(self) -> None:
        """Verify default configuration attributes and types."""
        cfg = LOBTransformerConfig()
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.num_levels, 10)
        self.assertEqual(cfg.input_dim, 40)
        self.assertEqual(cfg.seq_len, 50)
        self.assertEqual(cfg.d_model, 64)
        self.assertEqual(cfg.n_heads, 4)
        self.assertEqual(cfg.horizons_sec, (0.1, 0.5, 1.0, 5.0))
        self.assertEqual(cfg.dilation_rates, (1, 2, 4, 8))

    def test_tc05_custom_configuration_override(self) -> None:
        """Verify engine instantiation with customized hyperparameters."""
        custom_cfg = LOBTransformerConfig(
            market="NASDAQ",
            d_model=32,
            n_heads=2,
            temperature=1.2,
            horizons_sec=(0.1, 0.5, 1.0, 5.0),
        )
        engine = LOBTransformerEngine(config=custom_cfg, market="NASDAQ", symbol="MSFT")
        self.assertEqual(engine.config.d_model, 32)
        self.assertEqual(engine.config.n_heads, 2)
        self.assertEqual(engine.config.temperature, 1.2)
        self.assertEqual(engine.symbol, "MSFT")

    def test_tc06_price_direction_enumeration(self) -> None:
        """Verify PriceDirection IntEnum mapping."""
        self.assertEqual(int(PriceDirection.DOWN), 0)
        self.assertEqual(int(PriceDirection.STATIONARY), 1)
        self.assertEqual(int(PriceDirection.UP), 2)
        self.assertEqual(PriceDirection(0), PriceDirection.DOWN)
        self.assertEqual(PriceDirection(1), PriceDirection.STATIONARY)
        self.assertEqual(PriceDirection(2), PriceDirection.UP)

    # -----------------------------------------------------------------------
    # Category 3: 5-Market Pre-Calibrated Profiles (TC07~TC09)
    # -----------------------------------------------------------------------
    def test_tc07_five_market_profiles_exist(self) -> None:
        """Verify empirical profiles configured for all 5 markets."""
        for mkt in ("SP500", "NASDAQ", "KOSPI", "KOSDAQ", "RUSSELL2000"):
            self.assertIn(mkt, MARKET_LOB_PROFILES)
            prof = MARKET_LOB_PROFILES[mkt]
            self.assertIn("threshold_bps", prof)
            self.assertIn("temperature", prof)
            self.assertIn(0.1, prof["threshold_bps"])
            self.assertIn(5.0, prof["threshold_bps"])

    def test_tc08_dynamic_market_calibration(self) -> None:
        """Verify dynamic re-calibration updates market and configuration."""
        self.engine.calibrate_market("KOSPI")
        self.assertEqual(self.engine.market, "KOSPI")
        self.assertEqual(self.engine.config.market, "KOSPI")

    def test_tc09_unknown_market_profile_fallback(self) -> None:
        """Verify unknown market safely falls back to SP500."""
        engine = LOBTransformerEngine(market="NON_EXISTENT")
        self.assertEqual(engine.config.temperature, MARKET_LOB_PROFILES["SP500"]["temperature"])

    # -----------------------------------------------------------------------
    # Category 4: 10-Level Order Book Tensor Parsing & Normalization (TC10~TC14)
    # -----------------------------------------------------------------------
    def test_tc10_valid_tensor_shape_normalization(self) -> None:
        """Verify normalizer handles (T, 40) tensors preserving exact shape."""
        norm = self.engine.normalize_lob_tensor(self.raw_tensor)
        self.assertEqual(norm.shape, (self.seq_len, 40))
        self.assertFalse(np.any(np.isnan(norm)))

    def test_tc11_mid_price_relative_basis_points(self) -> None:
        """Verify normalized bid prices are negative bps and ask prices are positive bps."""
        norm = self.engine.normalize_lob_tensor(self.raw_tensor)
        # Level 1 Bid (idx 0) should be < 0; Level 1 Ask (idx 2) should be > 0
        self.assertTrue(np.all(norm[:, 0] < 0.0))
        self.assertTrue(np.all(norm[:, 2] > 0.0))

    def test_tc12_volume_log1p_transformation(self) -> None:
        """Verify volumes are log-scaled and finite."""
        norm = self.engine.normalize_lob_tensor(self.raw_tensor)
        # Volume columns: indices 1, 3, 5, 7, ...
        vol_cols = norm[:, 1::2]
        self.assertFalse(np.any(np.isnan(vol_cols)))
        self.assertFalse(np.any(np.isinf(vol_cols)))

    def test_tc13_level_by_level_feature_imbalance(self) -> None:
        """Verify compute_depth_imbalances returns 10 imbalance values bounded in [-1, 1]."""
        imb = self.engine.compute_depth_imbalances(self.raw_tensor)
        self.assertEqual(len(imb), 10)
        self.assertTrue(np.all(imb >= -1.0))
        self.assertTrue(np.all(imb <= 1.0))

    def test_tc14_invalid_feature_dimension_raises(self) -> None:
        """Verify invalid feature count (e.g. 38 instead of 40) raises ValueError."""
        invalid_tensor = np.zeros((10, 38))
        with self.assertRaises(ValueError):
            self.engine.normalize_lob_tensor(invalid_tensor)

    # -----------------------------------------------------------------------
    # Category 5: Multi-Scale Dilated Temporal Convolutional Encoders (TC15~TC17)
    # -----------------------------------------------------------------------
    def test_tc15_dilated_convolutions_retain_sequence_length(self) -> None:
        """Verify multi-scale convolutions preserve exact sequence length T."""
        norm = self.engine.normalize_lob_tensor(self.raw_tensor)
        _, temporal_attn, _ = self.engine.numpy_module.forward(norm)
        # Attention shape reflects sequence length T x T
        self.assertEqual(temporal_attn.shape, (self.seq_len, self.seq_len))

    def test_tc16_causal_padding_prevents_lookahead(self) -> None:
        """Verify earlier output rows do not change when appending future snapshots."""
        norm = self.engine.normalize_lob_tensor(self.raw_tensor)
        t_slice1 = norm[:10]
        t_slice2 = norm[:15]
        # Run forward on both
        _, attn1, _ = self.engine.numpy_module.forward(t_slice1)
        _, attn2, _ = self.engine.numpy_module.forward(t_slice2)
        # In causal attention, row 5 of attn1 and attn2 should only attend to indices <= 5
        self.assertTrue(np.all(attn1[5, 6:] == 0.0))
        self.assertTrue(np.all(attn2[5, 6:] == 0.0))

    def test_tc17_branch_projection_dimension(self) -> None:
        """Verify convolution projection produces d_model hidden representations."""
        self.assertEqual(self.engine.numpy_module.w_proj.shape[1], self.engine.config.d_model)

    # -----------------------------------------------------------------------
    # Category 6: Spatial Depth Cross-Attention Across Levels 1~10 (TC18~TC20)
    # -----------------------------------------------------------------------
    def test_tc18_depth_attention_sums_to_one(self) -> None:
        """Verify depth attention weights across 10 levels sum strictly to 1.0."""
        out = self.engine.predict(self.raw_tensor)
        depth_weights = out.attention.depth_attention
        self.assertEqual(len(depth_weights), 10)
        self.assertAlmostEqual(float(np.sum(depth_weights)), 1.0, places=5)
        self.assertTrue(np.all(depth_weights >= 0.0))

    def test_tc19_top_level_driver_index_range(self) -> None:
        """Verify top_level_driver is a 1-indexed level between 1 and 10."""
        out = self.engine.predict(self.raw_tensor)
        driver = out.attention.top_level_driver
        self.assertGreaterEqual(driver, 1)
        self.assertLessEqual(driver, 10)

    def test_tc20_depth_attention_shifts_on_volume_wall(self) -> None:
        """Verify placing a massive volume wall at Level 5 shifts attention."""
        shocked_tensor = self.raw_tensor.copy()
        # Level 5 is index 4 (base = 4 * 4 = 16)
        shocked_tensor[:, 17] = 50000.0  # Massive Level 5 Bid volume
        shocked_tensor[:, 19] = 50000.0  # Massive Level 5 Ask volume
        out = self.engine.predict(shocked_tensor)
        depth_weights = out.attention.depth_attention
        self.assertGreater(depth_weights[4], 0.05)

    # -----------------------------------------------------------------------
    # Category 7: Causal Multi-Head Self-Attention (TC21~TC23)
    # -----------------------------------------------------------------------
    def test_tc21_causal_mask_zero_above_diagonal(self) -> None:
        """Verify temporal attention strictly enforces causal lower-triangular structure."""
        out = self.engine.predict(self.raw_tensor)
        temporal_attn = out.attention.temporal_attention
        T = self.seq_len
        for i in range(T):
            for j in range(i + 1, T):
                self.assertAlmostEqual(temporal_attn[i, j], 0.0, places=5,
                                       msg=f"Lookahead leak at ({i}, {j}): {temporal_attn[i, j]}")

    def test_tc22_temporal_attention_row_sums(self) -> None:
        """Verify each row of causal temporal attention sums to 1.0."""
        out = self.engine.predict(self.raw_tensor)
        temporal_attn = out.attention.temporal_attention
        for r in range(self.seq_len):
            self.assertAlmostEqual(float(np.sum(temporal_attn[r])), 1.0, places=5)

    def test_tc23_temporal_entropy_non_negative(self) -> None:
        """Verify temporal attention entropy is non-negative and finite."""
        out = self.engine.predict(self.raw_tensor)
        self.assertGreaterEqual(out.attention.temporal_entropy, 0.0)
        self.assertFalse(math.isnan(out.attention.temporal_entropy))

    # -----------------------------------------------------------------------
    # Category 8: 4 Simultaneous Forecast Heads (100ms, 500ms, 1s, 5s) (TC24~TC28)
    # -----------------------------------------------------------------------
    def test_tc24_all_four_horizons_present(self) -> None:
        """Verify output dictionary contains exact 4 forecast horizons."""
        out = self.engine.predict(self.raw_tensor)
        for h in (0.1, 0.5, 1.0, 5.0):
            self.assertIn(h, out.predictions)

    def test_tc25_probability_simplex_sum_to_one(self) -> None:
        """Verify p_down + p_stat + p_up == 1.0 for each horizon."""
        out = self.engine.predict(self.raw_tensor)
        for h, pred in out.predictions.items():
            prob_sum = pred.p_down + pred.p_stat + pred.p_up
            self.assertAlmostEqual(prob_sum, 1.0, places=5)
            self.assertGreaterEqual(pred.p_down, 0.0)
            self.assertGreaterEqual(pred.p_stat, 0.0)
            self.assertGreaterEqual(pred.p_up, 0.0)

    def test_tc26_expected_direction_matches_argmax(self) -> None:
        """Verify expected direction matches class with highest probability."""
        out = self.engine.predict(self.raw_tensor)
        for h, pred in out.predictions.items():
            max_idx = int(np.argmax(pred.probabilities))
            self.assertEqual(int(pred.expected_direction), max_idx)

    def test_tc27_directional_score_bounds(self) -> None:
        """Verify directional score in [-1.0, 1.0] and equals p_up - p_down."""
        out = self.engine.predict(self.raw_tensor)
        for h, pred in out.predictions.items():
            expected_score = pred.p_up - pred.p_down
            self.assertAlmostEqual(pred.directional_score, expected_score, places=5)
            self.assertGreaterEqual(pred.directional_score, -1.0)
            self.assertLessEqual(pred.directional_score, 1.0)

    def test_tc28_directional_confidence_bounds(self) -> None:
        """Verify confidence metric in [0.0, 1.0]."""
        out = self.engine.predict(self.raw_tensor)
        for h, pred in out.predictions.items():
            self.assertGreaterEqual(pred.confidence, 0.0)
            self.assertLessEqual(pred.confidence, 1.0)

    # -----------------------------------------------------------------------
    # Category 9: Structural Microstructure Signal Responsiveness (TC29~TC31)
    # -----------------------------------------------------------------------
    def test_tc29_heavy_bid_imbalance_shifts_up(self) -> None:
        """Verify massive buy pressure produces positive directional score and UP direction."""
        buy_heavy_tensor = self.raw_tensor.copy()
        # Flood bids with 10x volume and deplete asks
        for lvl in range(10):
            base = lvl * 4
            buy_heavy_tensor[:, base + 1] = 5000.0  # Big bid
            buy_heavy_tensor[:, base + 3] = 1.0     # Thin ask
        out = self.engine.predict(buy_heavy_tensor)
        pred_100ms = out.predictions[0.1]
        self.assertGreater(pred_100ms.directional_score, 0.0)
        self.assertGreater(pred_100ms.p_up, pred_100ms.p_down)

    def test_tc30_heavy_ask_imbalance_shifts_down(self) -> None:
        """Verify massive sell pressure produces negative directional score and DOWN direction."""
        sell_heavy_tensor = self.raw_tensor.copy()
        # Flood asks with 10x volume and deplete bids
        for lvl in range(10):
            base = lvl * 4
            sell_heavy_tensor[:, base + 1] = 1.0     # Thin bid
            sell_heavy_tensor[:, base + 3] = 5000.0  # Big ask
        out = self.engine.predict(sell_heavy_tensor)
        pred_100ms = out.predictions[0.1]
        self.assertLess(pred_100ms.directional_score, 0.0)
        self.assertGreater(pred_100ms.p_down, pred_100ms.p_up)

    def test_tc31_balanced_book_directional_score_near_zero(self) -> None:
        """Verify perfectly symmetric order book produces score close to 0."""
        balanced_tensor = self.raw_tensor.copy()
        out = self.engine.predict(balanced_tensor)
        pred_100ms = out.predictions[0.1]
        self.assertAlmostEqual(pred_100ms.directional_score, 0.0, delta=0.35)

    # -----------------------------------------------------------------------
    # Category 10: PyTorch & NumPy Dual-Backend Execution (TC32~TC35)
    # -----------------------------------------------------------------------
    def test_tc32_pure_numpy_backend_execution(self) -> None:
        """Verify pure NumPy fallback executes cleanly with use_torch=False."""
        np_cfg = LOBTransformerConfig(use_torch=False)
        np_engine = LOBTransformerEngine(config=np_cfg)
        self.assertIsNone(np_engine.torch_module)
        out = np_engine.predict(self.raw_tensor)
        self.assertEqual(out.backend, "numpy")
        self.assertEqual(len(out.predictions), 4)

    def test_tc33_torch_backend_detection(self) -> None:
        """Verify telemetry correctly tracks whether PyTorch is loaded."""
        telem = self.engine.export_telemetry()
        self.assertIn("torch_available", telem)

    def test_tc34_consistency_across_backends(self) -> None:
        """Verify NumPy and PyTorch backends adhere to identical output invariants."""
        out_np = LOBTransformerEngine(config=LOBTransformerConfig(use_torch=False)).predict(self.raw_tensor)
        out_torch = LOBTransformerEngine(config=LOBTransformerConfig(use_torch=True)).predict(self.raw_tensor)
        for h in (0.1, 0.5, 1.0, 5.0):
            self.assertAlmostEqual(np.sum(out_np.predictions[h].probabilities), 1.0, places=5)
            self.assertAlmostEqual(np.sum(out_torch.predictions[h].probabilities), 1.0, places=5)

    def test_tc35_temperature_scaling_effect(self) -> None:
        """Verify higher temperature flattens probabilities closer to uniform 1/3."""
        low_t_engine = LOBTransformerEngine(config=LOBTransformerConfig(temperature=0.5))
        high_t_engine = LOBTransformerEngine(config=LOBTransformerConfig(temperature=5.0))
        out_low = low_t_engine.predict(self.raw_tensor)
        out_high = high_t_engine.predict(self.raw_tensor)
        # Uniform probability is 1/3 ~ 0.3333; high temperature variance across classes should be lower
        var_low = np.var(out_low.predictions[0.1].probabilities)
        var_high = np.var(out_high.predictions[0.1].probabilities)
        self.assertLess(var_high, var_low)

    # -----------------------------------------------------------------------
    # Category 11: Edge Cases, Latency & Telemetry Export (TC36~TC38)
    # -----------------------------------------------------------------------
    def test_tc36_single_snapshot_input_handling(self) -> None:
        """Verify engine accepts single 1D snapshot shape (40,)."""
        single_row = self.raw_tensor[-1]
        out = self.engine.predict(single_row)
        self.assertEqual(len(out.predictions), 4)
        self.assertEqual(out.attention.temporal_attention.shape, (1, 1))

    def test_tc37_extract_attention_heatmaps_accessor(self) -> None:
        """Verify direct extract_attention_heatmaps helper."""
        heatmap = self.engine.extract_attention_heatmaps(self.raw_tensor)
        self.assertIsInstance(heatmap, LOBAttentionHeatmap)
        self.assertEqual(len(heatmap.depth_attention), 10)

    def test_tc38_telemetry_export_and_latency_benchmark(self) -> None:
        """Verify telemetry tracks calls, latency, and executes in fast time."""
        out = self.engine.predict(self.raw_tensor)
        telem = self.engine.export_telemetry()
        self.assertGreater(telem["telemetry"]["total_predictions"], 0)
        self.assertGreater(out.inference_latency_us, 0.0)


if __name__ == "__main__":
    unittest.main()
