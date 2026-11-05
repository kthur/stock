"""
tests/test_f720_f721_adversarial_stress.py — Adversarial Stress Test Suite for Features F720 and F721.

Executed by Challenger 1 (Phase 148 / Milestone 1).
Stress tests:
1. F720 Extreme Price & Volume Shocks (+1,000%, -95%, oscillation, constant prices, zero volume).
2. F720 Lookback & Series Degeneracies (empty, N < 5 bars, N = 1 bar, corrupt NaNs/infs).
3. F720 Mathematical & Component-level Edge Cases (convolve_atrous, deadband, coherence, energy density).
4. F721 Extreme Price Shocks & Degenerate Market Inputs.
5. F721 Graph Topology Stress (isolated nodes, self-loops, 2-cycles, 3-cycles, zero/massive/negative weights, star graph, complete graph).
6. F721 GATv2 Attention Simplex & Curvature Multiplier Stability.
7. Latency SLA Verification (single-symbol latency < 2.0 ms).
8. Output Invariant Verification (finite, strictly bounded in [0.05, 0.95], synthetic_rows == 0).
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.spectral_wavelet_decomposition import (
    SpectralWaveletDecompositionEngine,
    convolve_atrous,
    upsample_filter,
    apply_hyperbolic_noise_deadband,
    get_wavelet_filters,
    HAAR_LP,
    HAAR_HP,
    DB2_LP,
    DB2_HP,
)
from src.core.value_chain_curvature_gnn import (
    ValueChainCurvatureGNNEngine,
    TIER1_SYMBOLS,
    TIER2_SYMBOLS,
    TIER3_SYMBOLS,
)
from src.core.supply_chain_gnn_v2 import bullwhip_transform


class TestAdversarialF720F721(unittest.TestCase):
    """Adversarial challenger test suite stress-testing F720 and F721."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.wavelet_engine = SpectralWaveletDecompositionEngine(wavelet="db2", levels=3)
        self.gnn_engine = ValueChainCurvatureGNNEngine()

    def _make_df(self, close_series: np.ndarray, vol_series: np.ndarray = None) -> pd.DataFrame:
        n = len(close_series)
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        if vol_series is None:
            vol_series = np.full(n, 10000.0)
        return pd.DataFrame({
            "Open": close_series * 0.99,
            "High": close_series * 1.01,
            "Low": close_series * 0.98,
            "Close": close_series,
            "Volume": vol_series,
        }, index=dates)

    # =========================================================================
    # 1. F720 Extreme Price & Volume Shocks
    # =========================================================================

    def test_f720_extreme_positive_shock_1000_percent(self) -> None:
        """F720: Massive +1,000% price spike on final bar."""
        close = np.full(30, 100.0)
        close[-1] = 1100.0  # +1000%
        df = self._make_df(close)
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)
        # Check detail values are finite
        self.assertTrue(np.isfinite(feats["d1_raw"]))
        self.assertTrue(np.isfinite(feats["d2"]))
        self.assertTrue(np.isfinite(feats["d3"]))
        self.assertTrue(np.isfinite(feats["a3"]))

    def test_f720_extreme_negative_shock_95_percent(self) -> None:
        """F720: Catastrophic -95% price crash on final bar."""
        close = np.full(30, 100.0)
        close[-1] = 5.0  # -95%
        df = self._make_df(close)
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)
        self.assertTrue(np.isfinite(feats["d1_raw"]))
        self.assertTrue(np.isfinite(feats["d2"]))

    def test_f720_alternating_violent_oscillations(self) -> None:
        """F720: Alternating violent +1000% / -95% spikes across multiple bars."""
        close = np.array([100.0, 1000.0, 50.0, 600.0, 20.0, 300.0, 10.0, 500.0] * 4, dtype=np.float64)
        df = self._make_df(close)
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)

    def test_f720_constant_prices_zero_returns(self) -> None:
        """F720: Constant prices (100% zero returns) over 50 bars. Division-by-zero check."""
        close = np.full(50, 42.0)
        df = self._make_df(close)
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        # With zero returns, signal is 0 -> sigmoid(0) = 0.50
        self.assertAlmostEqual(score, 0.50, delta=0.01)
        self.assertEqual(feats["d1_raw"], 0.0)
        self.assertEqual(feats["d2"], 0.0)
        self.assertEqual(feats["d3"], 0.0)
        self.assertEqual(feats["coherence_d1"], 0.0)

    def test_f720_zero_volume_all_bars(self) -> None:
        """F720: Volume is zero for all bars. Volume normalization check."""
        close = np.linspace(100.0, 150.0, 30)
        vol = np.zeros(30)
        df = self._make_df(close, vol)
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)

    def test_f720_extreme_volume_spike_1e12(self) -> None:
        """F720: Gigantic volume spike (1e12) on crash bar."""
        close = np.full(30, 100.0)
        close[-1] = 50.0
        vol = np.full(30, 1000.0)
        vol[-1] = 1e12  # 1 trillion
        df = self._make_df(close, vol)
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)

    def test_f720_missing_volume_column(self) -> None:
        """F720: DataFrame missing 'Volume' column entirely."""
        close = np.linspace(50.0, 100.0, 20)
        df = pd.DataFrame({"Close": close, "Open": close, "High": close, "Low": close})
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)

    def test_f720_corrupt_nans_infs_in_data(self) -> None:
        """F720: Injected NaNs and +/- Infs in Close and Volume series."""
        close = np.array([100.0, np.nan, 105.0, np.inf, -np.inf, 110.0, np.nan, 120.0, 125.0, 130.0])
        vol = np.array([np.nan, 1000.0, np.inf, 2000.0, -100.0, np.nan, 1500.0, 2500.0, 3000.0, 3500.0])
        df = pd.DataFrame({"Close": close, "Volume": vol})
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)

    # =========================================================================
    # 2. F720 Lookback & Series Degeneracies
    # =========================================================================

    def test_f720_empty_and_short_lookbacks(self) -> None:
        """F720: Series with N = 0, 1, 2, 3, 4 bars must safely fallback to score 0.50."""
        for n in [0, 1, 2, 3, 4]:
            close = np.linspace(100.0, 110.0, n) if n > 0 else np.array([])
            df = self._make_df(close) if n > 0 else pd.DataFrame(columns=["Close", "Volume"])
            feats = self.wavelet_engine.extract_spectral_features(df)
            self.assertEqual(feats["score"], 0.50, f"Failed fallback for N={n}")
            self.assertEqual(feats["d1_raw"], 0.0)
            self.assertEqual(feats["coherence_d1"], 0.0)

    def test_f720_exact_minimum_lookback_5_bars(self) -> None:
        """F720: Exactly N = 5 bars (minimum operational lookback boundary)."""
        close = np.array([100.0, 102.0, 101.0, 103.0, 105.0])
        df = self._make_df(close)
        feats = self.wavelet_engine.extract_spectral_features(df)
        score = feats["score"]
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.05)
        self.assertLessEqual(score, 0.95)

    def test_f720_compute_scores_malformed_inputs(self) -> None:
        """F720: compute_scores with empty dict, None, non-dict, and mixed corrupt data."""
        # Non-dict
        res1 = self.wavelet_engine.compute_scores(None)
        self.assertEqual(len(res1), 0)
        self.assertIn("spectral_wavelet_score", res1.columns)

        # Empty dict
        res2 = self.wavelet_engine.compute_scores({})
        self.assertEqual(len(res2), 0)

        # Mixed dictionary
        valid_df = self._make_df(np.linspace(100.0, 120.0, 20))
        short_df = self._make_df(np.array([100.0, 101.0]))  # < 5 bars
        empty_df = pd.DataFrame()
        corrupt_dict = {
            "VALID": valid_df,
            "SHORT": short_df,
            "EMPTY": empty_df,
            "NONE": None,
        }
        res3 = self.wavelet_engine.compute_scores(corrupt_dict)
        self.assertEqual(len(res3), 4)
        for _, row in res3.iterrows():
            sc = row["spectral_wavelet_score"]
            self.assertTrue(np.isfinite(sc))
            self.assertGreaterEqual(sc, 0.05)
            self.assertLessEqual(sc, 0.95)
        self.assertEqual(res3.loc[res3["symbol"] == "SHORT", "spectral_wavelet_score"].iloc[0], 0.50)
        self.assertEqual(res3.loc[res3["symbol"] == "EMPTY", "spectral_wavelet_score"].iloc[0], 0.50)
        self.assertEqual(res3.loc[res3["symbol"] == "NONE", "spectral_wavelet_score"].iloc[0], 0.50)

    # =========================================================================
    # 3. F720 Mathematical & Component-level Edge Cases
    # =========================================================================

    def test_f720_convolve_atrous_boundary_lengths(self) -> None:
        """F720: convolve_atrous with 0, 1, 2, 3, 4, 100 elements."""
        for n in [0, 1, 2, 3, 4, 5, 20, 100]:
            x = np.random.randn(n)
            out_haar = convolve_atrous(x, HAAR_LP)
            out_db2 = convolve_atrous(x, DB2_LP)
            self.assertEqual(len(out_haar), n)
            self.assertEqual(len(out_db2), n)
            if n > 0:
                self.assertTrue(np.all(np.isfinite(out_haar)))
                self.assertTrue(np.all(np.isfinite(out_db2)))

    def test_f720_hyperbolic_noise_deadband_edge_cases(self) -> None:
        """F720: apply_hyperbolic_noise_deadband under boundary conditions."""
        # Exactly 0.0
        self.assertEqual(apply_hyperbolic_noise_deadband(0.0), 0.0)
        # Deep noise (ratio < 0.85)
        self.assertEqual(apply_hyperbolic_noise_deadband(0.010, delta=0.035), 0.0)
        self.assertEqual(apply_hyperbolic_noise_deadband(-0.010, delta=0.035), 0.0)
        # Full transmission (ratio >= 1.05) -> |z| >= 0.03675
        val_pos = 0.050
        val_neg = -0.050
        self.assertEqual(apply_hyperbolic_noise_deadband(val_pos, delta=0.035), val_pos)
        self.assertEqual(apply_hyperbolic_noise_deadband(val_neg, delta=0.035), val_neg)
        # Transition zone |z| in [0.030, 0.036]
        z_trans = 0.034
        res_trans = apply_hyperbolic_noise_deadband(z_trans, delta=0.035)
        self.assertTrue(0.0 < res_trans <= z_trans)
        # Extremely huge input: 1e15
        self.assertEqual(apply_hyperbolic_noise_deadband(1e15), 1e15)

    def test_f720_coherence_and_energy_density_zero_division(self) -> None:
        """F720: compute_wavelet_coherence & compute_energy_density with all zeros."""
        zeros_arr = np.zeros(20)
        coh = self.wavelet_engine.compute_wavelet_coherence(zeros_arr, zeros_arr, window=10)
        self.assertEqual(coh, 0.0)
        self.assertTrue(np.isfinite(coh))

        ed = self.wavelet_engine.compute_energy_density([zeros_arr, zeros_arr, zeros_arr], zeros_arr, window=10)
        for k, v in ed.items():
            self.assertTrue(np.isfinite(v))
            self.assertGreaterEqual(v, 0.0)

    # =========================================================================
    # 4. F721 Extreme Price Shocks & Degenerate Market Inputs
    # =========================================================================

    def test_f721_downstream_oem_extreme_shock(self) -> None:
        """F721: Tier 1 OEM (NVDA) suffers extreme shock (-95% crash and +1000% spike)."""
        # Crash
        prices = {}
        for s in (TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS):
            prices[s] = self._make_df(np.full(10, 100.0))
        prices["NVDA"] = self._make_df(np.array([100.0, 100.0, 100.0, 100.0, 5.0]))
        res_crash = self.gnn_engine.compute_scores(prices)
        self.assertEqual(len(res_crash), len(prices))
        for sc in res_crash["value_chain_curvature_gnn_score"]:
            self.assertTrue(np.isfinite(sc))
            self.assertGreaterEqual(sc, 0.05)
            self.assertLessEqual(sc, 0.95)

        # Spike
        prices["NVDA"] = self._make_df(np.array([100.0, 100.0, 100.0, 100.0, 1100.0]))
        res_spike = self.gnn_engine.compute_scores(prices)
        self.assertEqual(len(res_spike), len(prices))
        for sc in res_spike["value_chain_curvature_gnn_score"]:
            self.assertTrue(np.isfinite(sc))
            self.assertGreaterEqual(sc, 0.05)
            self.assertLessEqual(sc, 0.95)

    def test_f721_upstream_supplier_extreme_shock(self) -> None:
        """F721: Tier 2 (TSM, ASML) supplier undergoes extreme +1,000% shock."""
        prices = {}
        for s in (TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS):
            prices[s] = self._make_df(np.full(10, 100.0))
        prices["TSM"] = self._make_df(np.array([100.0, 100.0, 100.0, 100.0, 1100.0]))
        prices["ASML"] = self._make_df(np.array([100.0, 100.0, 100.0, 100.0, 1100.0]))
        res = self.gnn_engine.compute_scores(prices)
        self.assertEqual(len(res), len(prices))
        for sc in res["value_chain_curvature_gnn_score"]:
            self.assertTrue(np.isfinite(sc))
            self.assertGreaterEqual(sc, 0.05)
            self.assertLessEqual(sc, 0.95)

    def test_f721_all_constant_prices_zero_returns(self) -> None:
        """F721: All 185 symbols have zero returns. Scores must remain strictly bounded."""
        prices = {s: self._make_df(np.full(10, 50.0)) for s in (TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS)}
        res = self.gnn_engine.compute_scores(prices)
        self.assertEqual(len(res), len(prices))
        for sc in res["value_chain_curvature_gnn_score"]:
            self.assertTrue(np.isfinite(sc))
            self.assertGreaterEqual(sc, 0.05)
            self.assertLessEqual(sc, 0.95)

    def test_f721_extreme_fx_momentum(self) -> None:
        """F721: Extreme FX momentum values (+1000.0, -1000.0, corrupt dictionary)."""
        prices = {s: self._make_df(np.linspace(100.0, 110.0, 10)) for s in (TIER1_SYMBOLS + TIER2_SYMBOLS)[:20]}
        for fx in [1000.0, -1000.0, {"USDKRW": 500.0, "USDJPY": -500.0}, None]:
            res = self.gnn_engine.compute_scores(prices, fx_momentum=fx)
            self.assertEqual(len(res), len(prices))
            for sc in res["value_chain_curvature_gnn_score"]:
                self.assertTrue(np.isfinite(sc))
                self.assertGreaterEqual(sc, 0.05)
                self.assertLessEqual(sc, 0.95)

    def test_f721_empty_and_minimal_universe(self) -> None:
        """F721: Empty universe, 1-symbol universe, and non-value-chain symbols."""
        # Empty
        res_empty = self.gnn_engine.compute_scores({})
        self.assertEqual(len(res_empty), 0)

        # Single unknown symbol
        single_dict = {"UNKNOWN_XYZ": self._make_df(np.linspace(100.0, 105.0, 10))}
        res_single = self.gnn_engine.compute_scores(single_dict)
        self.assertEqual(len(res_single), 1)
        sc = res_single["value_chain_curvature_gnn_score"].iloc[0]
        self.assertTrue(np.isfinite(sc))
        self.assertGreaterEqual(sc, 0.05)
        self.assertLessEqual(sc, 0.95)

    # =========================================================================
    # 5. F721 Graph Topology Stress
    # =========================================================================

    def test_f721_disconnected_isolated_nodes(self) -> None:
        """F721: Custom graph with completely isolated nodes (no edges)."""
        isolated_engine = ValueChainCurvatureGNNEngine(custom_edges=[])
        self.assertEqual(len(isolated_engine.edge_weights), 0)
        self.assertEqual(len(isolated_engine.compute_all_edge_curvatures()), 0)

        # Curvature query on non-existent edge
        ric = isolated_engine.compute_directed_forman_ricci_curvature("A", "B")
        self.assertEqual(ric, 4.0)  # 4 - 0 - 0 + 0 = 4.0
        fw = isolated_engine.compute_continuous_weighted_ricci_curvature("A", "B")
        self.assertEqual(fw, 0.0)

        # Scoring with isolated graph
        prices = {"NVDA": self._make_df(np.linspace(100.0, 110.0, 10))}
        res = isolated_engine.compute_scores(prices)
        self.assertEqual(len(res), 1)
        self.assertTrue(0.05 <= res["value_chain_curvature_gnn_score"].iloc[0] <= 0.95)

    def test_f721_self_loops_and_cycles(self) -> None:
        """F721: Custom graph containing self-loops, 2-cycles, and 3-cycles."""
        pathological_edges = [
            ("A", "A", 0.5, 30.0),  # self-loop
            ("A", "B", 0.8, 30.0),  # 2-cycle A <-> B
            ("B", "A", 0.7, 30.0),
            ("B", "C", 0.6, 30.0),  # 3-cycle A -> B -> C -> A
            ("C", "A", 0.9, 30.0),
        ]
        cycle_engine = ValueChainCurvatureGNNEngine(custom_edges=pathological_edges)
        curvs = cycle_engine.compute_all_edge_curvatures()
        self.assertEqual(len(curvs), len(pathological_edges))
        for (u, v), ric in curvs.items():
            self.assertTrue(np.isfinite(ric))
            mult = cycle_engine.compute_curvature_multiplier(u, v)
            self.assertTrue(np.isfinite(mult))
            self.assertGreater(mult, 0.0)

    def test_f721_zero_and_massive_edge_weights(self) -> None:
        """F721: Zero weight edges, negative weight edges, and 1e6 weight edges."""
        edge_cases = [
            ("A", "B", 0.0, 30.0),      # Zero weight
            ("B", "C", -1.0, 30.0),     # Negative weight
            ("C", "D", 1e6, 30.0),      # Massive weight
            ("D", "A", 0.00000001, 0.0) # Tiny weight, tau=0
        ]
        stress_engine = ValueChainCurvatureGNNEngine(custom_edges=edge_cases)
        for (u, v, _, _) in edge_cases:
            fw = stress_engine.compute_continuous_weighted_ricci_curvature(u, v)
            self.assertTrue(np.isfinite(fw))
            dyn_w = stress_engine.compute_curvature_dynamic_edge_weight(u, v, 1.0, 30.0)
            self.assertTrue(np.isfinite(dyn_w))
            self.assertGreaterEqual(dyn_w, 0.001)
            self.assertLessEqual(dyn_w, 10.0)

    def test_f721_star_graph_extreme_bottleneck(self) -> None:
        """F721: Star graph: 1 central hub connected to 50 leaf nodes (extreme fan-in/fan-out)."""
        edges = []
        for i in range(50):
            leaf = f"LEAF_{i}"
            edges.append(("HUB", leaf, 0.5, 30.0))
            edges.append((leaf, "TARGET", 0.5, 30.0))
        star_engine = ValueChainCurvatureGNNEngine(custom_edges=edges)
        curvs = star_engine.compute_all_edge_curvatures()
        self.assertEqual(len(curvs), 100)
        for edge, ric in curvs.items():
            self.assertTrue(np.isfinite(ric))
            mult = star_engine.compute_curvature_multiplier(edge[0], edge[1])
            self.assertTrue(np.isfinite(mult))
            self.assertGreater(mult, 0.0)

    # =========================================================================
    # 6. F721 GATv2 Attention Simplex & Curvature Multiplier Stability
    # =========================================================================

    def test_f721_gatv2_attention_under_extreme_activations(self) -> None:
        """F721: GATv2 propagation under extreme node momentum (+/-10.0)."""
        node_mom = {s: 10.0 if i % 2 == 0 else -10.0 for i, s in enumerate(TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS)}
        h1, h2, h3 = self.gnn_engine.propagate_curvature_gatv2(node_mom)
        for hop_dict in [h1, h2, h3]:
            for s, val in hop_dict.items():
                self.assertTrue(np.isfinite(val))
                self.assertGreaterEqual(val, -1.0)
                self.assertLessEqual(val, 1.0)

    def test_f721_bullwhip_transform_extreme_values(self) -> None:
        """F721: bullwhip_transform under massive surges and collapse across hops 1, 2, 3."""
        for hop in [1, 2, 3]:
            # Non-finite
            self.assertEqual(bullwhip_transform(np.nan, hop=hop), 0.0)
            self.assertEqual(bullwhip_transform(np.inf, hop=hop), 0.0)
            # Extreme positive: 100.0
            pos = bullwhip_transform(100.0, hop=hop)
            self.assertTrue(np.isfinite(pos))
            self.assertGreater(pos, 0.0)
            # Extreme negative: -100.0
            neg = bullwhip_transform(-100.0, hop=hop)
            self.assertTrue(np.isfinite(neg))
            self.assertLess(neg, -100.0)  # Downside amplification

    # =========================================================================
    # 7. Latency SLA Verification (Single-Symbol Latency < 2.0 ms)
    # =========================================================================

    def test_f720_f721_latency_sla_under_2ms(self) -> None:
        """Profile single-symbol execution latency: both F720 and F721 must be < 2.0 ms per symbol."""
        # F720 Latency Benchmark (100 symbols)
        f720_prices = {f"SYM_{i}": self._make_df(np.linspace(100.0, 110.0 + i, 30)) for i in range(100)}
        t0 = time.perf_counter()
        res_f720 = self.wavelet_engine.compute_scores(f720_prices)
        t_f720 = (time.perf_counter() - t0) / 100.0 * 1000.0  # ms per symbol

        self.assertEqual(len(res_f720), 100)
        self.assertLess(t_f720, 2.0, f"F720 single-symbol latency exceeded SLA: {t_f720:.4f} ms >= 2.0 ms")

        # F721 Latency Benchmark across 185 Value Chain symbols
        f721_prices = {s: self._make_df(np.linspace(100.0, 120.0, 30)) for s in (TIER1_SYMBOLS + TIER2_SYMBOLS + TIER3_SYMBOLS)}
        t0 = time.perf_counter()
        res_f721 = self.gnn_engine.compute_scores(f721_prices)
        t_f721 = (time.perf_counter() - t0) / len(f721_prices) * 1000.0  # ms per symbol

        self.assertEqual(len(res_f721), len(f721_prices))
        self.assertLess(t_f721, 2.0, f"F721 single-symbol latency exceeded SLA: {t_f721:.4f} ms >= 2.0 ms")

    # =========================================================================
    # 8. Output Invariant Verification & Zero Synthetic Rows
    # =========================================================================

    def test_output_bounds_strictly_in_005_to_095(self) -> None:
        """Verify all outputs from F720 and F721 are strictly bounded in [0.05, 0.95]."""
        test_prices = {s: self._make_df(np.random.uniform(50.0, 200.0, 40)) for s in (TIER1_SYMBOLS + TIER2_SYMBOLS)[:30]}

        df_wavelet = self.wavelet_engine.compute_scores(test_prices)
        for sc in df_wavelet["spectral_wavelet_score"]:
            self.assertTrue(np.isfinite(sc))
            self.assertGreaterEqual(sc, 0.05)
            self.assertLessEqual(sc, 0.95)

        df_gnn = self.gnn_engine.compute_scores(test_prices)
        for sc in df_gnn["value_chain_curvature_gnn_score"]:
            self.assertTrue(np.isfinite(sc))
            self.assertGreaterEqual(sc, 0.05)
            self.assertLessEqual(sc, 0.95)

    def test_zero_synthetic_rows_invariant(self) -> None:
        """Verify synthetic_rows == 0 strictly integer type across authoritative benchmarks."""
        status_file = os.path.join(self.root_dir, "benchmarks", "30year", "status.json")
        summary_file = os.path.join(self.root_dir, "benchmarks", "30year", "stock_universe_summary.json")

        self.assertTrue(os.path.exists(status_file), f"Missing {status_file}")
        with open(status_file, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        self.assertIn("synthetic_rows", status_data)
        self.assertIsInstance(status_data["synthetic_rows"], int)
        self.assertNotIsInstance(status_data["synthetic_rows"], bool)
        self.assertEqual(status_data["synthetic_rows"], 0)

        self.assertTrue(os.path.exists(summary_file), f"Missing {summary_file}")
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
        self.assertIn("synthetic_rows", summary_data["metadata"])
        self.assertIsInstance(summary_data["metadata"]["synthetic_rows"], int)
        self.assertNotIsInstance(summary_data["metadata"]["synthetic_rows"], bool)
        self.assertEqual(summary_data["metadata"]["synthetic_rows"], 0)


if __name__ == "__main__":
    unittest.main()
