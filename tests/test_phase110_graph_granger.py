"""
tests/test_phase110_graph_granger.py — Comprehensive Test Suite for Phase 110 Milestone M1.

Tests the High-Dimensional Graph Granger Causality Spillover Network (Feature F520):
1. Module exports, version metadata, and backward-compatibility alias trees.
2. Directed adjacency asymmetry and non-negativity (C[j, i] != C[i, j], C >= 0).
3. Zero self-loops invariant (C[i, i] == 0.0 for all i).
4. Centrality bounds (in-degree, out-degree, net spillover, simplex normalization).
5. Directed PageRank convergence (d=0.85, positive components, exact sum = 1.000000).
6. Companion matrix multi-horizon propagation velocities and transmission matrices (1D, 3D, 5D).
7. Forward-looking shock impulse response vectors (no NaN/Inf, finite bounds).
8. Dynamic sector-macro sensitivity matrix generation and sector name alias expansion.
9. KRX timezone 1-day lag shift enforcement (zero lookahead bias).
10. Spillover momentum scoring logistic bounding ([0.05, 0.95]).
11. Integration with CrossAssetSpilloverEngine (Strategy 32).
12. Integration with EnsembleScoringEngine (dynamic weight modulation under macro spillover).
13. Dual-placement mirror hash integrity (SHA-256 equivalence across src/ and trading_system/src/).
14. Dual-tree import equivalence.
15. Edge cases: short history fallback, dangling nodes, reset functionality.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.ai.graph_granger_causality import (
    GrangerNetworkNode,
    NetworkTopologyMetrics,
    SystemicImpulseResponse,
    GrangerFitSummary,
    GraphGrangerCausalityNetwork,
    HighDimensionalGrangerNetwork,
    Phase110GrangerSpilloverEngine,
    GraphGrangerSpilloverNetwork,
    GrangerCausalityNetwork,
    DirectedMacroSpilloverNetwork,
    DEFAULT_MACRO_NODES,
    DEFAULT_SECTOR_NODES,
    US_MACRO_ALIASES,
    SECTOR_NAME_TO_ETF,
    compute_directed_pagerank,
)
import trading_system.src.ai.graph_granger_causality as ts_granger
from trading_system.src.core.cross_asset_spillover import CrossAssetSpilloverEngine
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


@pytest.fixture
def synthetic_macro_sector_returns() -> pd.DataFrame:
    """
    Creates deterministic synthetic returns for 8 macro indicators and 3 sector ETFs
    with a known causal lead-lag structure:
    SOX(t-1) -> XLK(t)
    VIX(t-1) -> XLF(t)
    WTI(t-1) -> XLE(t)
    """
    np.random.seed(42)
    n_bars = 120
    dates = pd.date_range("2026-01-01", periods=n_bars, freq="B")

    # Autonomous macro shocks
    sox = np.random.normal(0.0005, 0.02, n_bars)
    vix = np.random.normal(-0.0002, 0.04, n_bars)
    wti = np.random.normal(0.0001, 0.025, n_bars)
    tnx = np.random.normal(0.0000, 0.015, n_bars)
    usdkrw = np.random.normal(0.0001, 0.008, n_bars)
    gold = np.random.normal(0.0002, 0.012, n_bars)
    dxy = np.random.normal(0.0000, 0.006, n_bars)
    sp500 = 0.40 * sox + np.random.normal(0.0004, 0.012, n_bars)

    # Sector returns with directed lagged responses
    xlk = np.zeros(n_bars)
    xlf = np.zeros(n_bars)
    xle = np.zeros(n_bars)

    for t in range(2, n_bars):
        # Directed lag 1 and lag 2 transmissions
        xlk[t] = 0.50 * sox[t - 1] + 0.25 * sp500[t - 1] - 0.20 * vix[t - 1] + np.random.normal(0, 0.005)
        xlf[t] = 0.40 * tnx[t - 1] - 0.30 * vix[t - 1] + 0.20 * sp500[t - 1] + np.random.normal(0, 0.005)
        xle[t] = 0.60 * wti[t - 1] + 0.15 * dxy[t - 1] + np.random.normal(0, 0.005)

    data = {
        "SOX": sox,
        "VIX": vix,
        "WTI": wti,
        "TNX": tnx,
        "USDKRW": usdkrw,
        "GOLD": gold,
        "DXY": dxy,
        "SP500": sp500,
        "XLK": xlk,
        "XLF": xlf,
        "XLE": xle,
    }
    return pd.DataFrame(data, index=dates)


class TestGraphGrangerExportsAndAliases:
    """Verifies class exports, metadata, and full alias trees."""

    def test_version_metadata(self):
        net = GraphGrangerCausalityNetwork()
        assert net.VERSION == 117
        assert net.version == 117

    def test_module_level_aliases(self):
        assert HighDimensionalGrangerNetwork is GraphGrangerCausalityNetwork
        assert Phase110GrangerSpilloverEngine is GraphGrangerCausalityNetwork
        assert GraphGrangerSpilloverNetwork is GraphGrangerCausalityNetwork
        assert GrangerCausalityNetwork is GraphGrangerCausalityNetwork
        assert DirectedMacroSpilloverNetwork is GraphGrangerCausalityNetwork

    def test_class_level_aliases(self):
        assert GraphGrangerCausalityNetwork.HighDimensionalGrangerNetwork is GraphGrangerCausalityNetwork
        assert GraphGrangerCausalityNetwork.Phase110GrangerSpilloverEngine is GraphGrangerCausalityNetwork
        assert GraphGrangerCausalityNetwork.GraphGrangerSpilloverNetwork is GraphGrangerCausalityNetwork
        assert GraphGrangerCausalityNetwork.GrangerCausalityNetwork is GraphGrangerCausalityNetwork
        assert GraphGrangerCausalityNetwork.DirectedMacroSpilloverNetwork is GraphGrangerCausalityNetwork

    def test_default_constants(self):
        assert len(DEFAULT_MACRO_NODES) == 8
        assert "SOX" in DEFAULT_MACRO_NODES
        assert "VIX" in DEFAULT_MACRO_NODES
        assert "XLK" in DEFAULT_SECTOR_NODES
        assert "XLF" in DEFAULT_SECTOR_NODES
        assert "Semiconductor" in SECTOR_NAME_TO_ETF
        assert "Tech" in SECTOR_NAME_TO_ETF


class TestGrangerNetworkFittingAndTopology:
    """Verifies econometric VAR fitting and topological graph invariants."""

    def test_directed_adjacency_asymmetry_and_non_negativity(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork(lag_order=2, alpha_penalty=0.01)
        summary = net.fit(synthetic_macro_sector_returns)

        C = summary.causal_adjacency_matrix
        K = len(summary.nodes)
        assert C.shape == (K, K)

        # Causal weights must be strictly non-negative
        assert np.all(C >= 0.0)

        # Econometric Granger causality is inherently asymmetric: C != C.T
        assert not np.allclose(C, C.T, atol=1e-5)

        # Directed causal link from SOX to XLK should be significantly stronger than XLK to SOX
        sox_idx = summary.nodes.index("SOX")
        xlk_idx = summary.nodes.index("XLK")
        assert C[sox_idx, xlk_idx] > C[xlk_idx, sox_idx]

    def test_zero_self_loops_invariant(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork(lag_order=2)
        summary = net.fit(synthetic_macro_sector_returns)
        C = summary.causal_adjacency_matrix
        K = len(summary.nodes)

        for i in range(K):
            assert C[i, i] == 0.0, f"Node {summary.nodes[i]} has non-zero self-loop: {C[i, i]}"

    def test_centrality_simplex_bounds(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork(lag_order=2)
        summary = net.fit(synthetic_macro_sector_returns)
        metrics = summary.topology

        # Verify all centralities non-negative
        for node in summary.nodes:
            assert metrics.in_degree_centrality[node] >= 0.0
            assert metrics.out_degree_centrality[node] >= 0.0
            assert metrics.net_spillover_centrality[node] == pytest.approx(
                metrics.out_degree_centrality[node] - metrics.in_degree_centrality[node], abs=1e-9
            )

        # Simplex normalization: sum of normalized in-degrees and out-degrees must equal 1.0
        assert sum(metrics.normalized_in_degree.values()) == pytest.approx(1.0, abs=1e-6)
        assert sum(metrics.normalized_out_degree.values()) == pytest.approx(1.0, abs=1e-6)

        # Diagnostics
        for node in summary.nodes:
            logger_val = f"{node:8s}: in={metrics.in_degree_centrality[node]:.3f}, out={metrics.out_degree_centrality[node]:.3f}, net={metrics.net_spillover_centrality[node]:.3f}"
            assert metrics.in_degree_centrality[node] >= 0.0
            assert metrics.out_degree_centrality[node] >= 0.0

    def test_directed_pagerank_convergence(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork(pagerank_damping=0.85)
        summary = net.fit(synthetic_macro_sector_returns)
        pr = summary.topology.directed_pagerank

        # Every node must have strictly positive PageRank
        for node, score in pr.items():
            assert score > 0.0, f"Node {node} has non-positive PageRank: {score}"

        # Exact simplex sum = 1.000000
        assert sum(pr.values()) == pytest.approx(1.000000, abs=1e-6)


class TestCompanionPropagationAndShockImpulses:
    """Verifies companion matrix impulse response and forward-looking shock vectors."""

    def test_multi_horizon_propagation_velocities(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork(horizons=(1, 3, 5))
        summary = net.fit(synthetic_macro_sector_returns)
        metrics = summary.topology

        for h in [1, 3, 5]:
            assert h in metrics.propagation_velocities
            assert h in metrics.systemic_transmission_matrix
            T_h = metrics.systemic_transmission_matrix[h]
            assert T_h.shape == (len(summary.nodes), len(summary.nodes))
            assert np.all(np.isfinite(T_h))

            # Velocities must be non-negative
            for (src, dst), vel in metrics.propagation_velocities[h].items():
                assert vel >= 0.0
                assert np.isfinite(vel)

    def test_compute_shock_impulse_response(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork(horizons=(1, 3, 5))
        net.fit(synthetic_macro_sector_returns)

        shocks = {"SOX": 0.05, "VIX": 0.10, "WTI": -0.03}
        resp = net.compute_shock_impulse(shocks, horizon=3)

        assert resp.horizon == 3
        assert len(resp.projected_impulse) == len(net.nodes)
        for node, imp in resp.projected_impulse.items():
            assert np.isfinite(imp)
            assert not np.isnan(imp)

        # XLK should receive positive impulse from SOX surge
        assert resp.projected_impulse["XLK"] > 0.0

    def test_target_nodes_filtering(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork()
        net.fit(synthetic_macro_sector_returns)
        shocks = {"SOX": 0.04}
        resp = net.compute_shock_impulse(shocks, horizon=1, target_nodes=["XLK", "XLE"])
        assert set(resp.projected_impulse.keys()) == {"XLK", "XLE"}


class TestSectorSensitivityMatrixAndTimezoneCausality:
    """Verifies dynamic sector-macro sensitivity matrix and KRX 1-day lag shift."""

    def test_get_sector_macro_sensitivity_matrix(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork()
        net.fit(synthetic_macro_sector_returns)

        dyn_sens = net.get_sector_macro_sensitivity_matrix(horizon=3)
        assert isinstance(dyn_sens, pd.DataFrame)
        assert not dyn_sens.empty

        # Macro factors must be represented as columns
        assert "sox" in dyn_sens.columns
        assert "vix" in dyn_sens.columns
        assert "wti" in dyn_sens.columns

        # Sector ETF tickers and human-readable aliases must be in rows
        assert "XLK" in dyn_sens.index
        assert "Semiconductor" in dyn_sens.index
        assert "Tech" in dyn_sens.index
        assert "Market" in dyn_sens.index

        # Dynamic sensitivity of XLK to SOX should be positive
        assert dyn_sens.loc["XLK", "sox"] > 0.0

    def test_krx_timezone_causality_lag_shift(self, synthetic_macro_sector_returns):
        net_us = GraphGrangerCausalityNetwork(lag_order=2)
        summary_us = net_us.fit(synthetic_macro_sector_returns, is_krx=False)

        net_krx = GraphGrangerCausalityNetwork(lag_order=2)
        summary_krx = net_krx.fit(synthetic_macro_sector_returns, is_krx=True)

        # Adjacency matrix under KRX 1-day lag shift should differ from US zero-lag shift
        C_us = summary_us.causal_adjacency_matrix
        C_krx = summary_krx.causal_adjacency_matrix

        assert not np.allclose(C_us, C_krx, atol=1e-4)

    def test_evaluate_spillover_momentum_score_bounds(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork()
        net.fit(synthetic_macro_sector_returns)

        shocks = {"SOX": 0.04, "VIX": -0.05, "USDKRW": 0.01}
        stock_rets = {"005930": 0.015, "000660": -0.02, "AAPL": 0.03}
        sec_map = {"005930": "Semiconductor", "000660": "Semiconductor", "AAPL": "Tech"}

        scores = net.evaluate_spillover_momentum_score(shocks, stock_rets, sec_map, horizon=3)
        assert len(scores) == 3
        for sym, sc in scores.items():
            assert 0.05 <= sc <= 0.95


class TestEngineIntegrations:
    """Verifies downstream integration hooks in Strategy 32 and EnsembleScoringEngine."""

    def test_cross_asset_spillover_engine_integration(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork()
        net.fit(synthetic_macro_sector_returns)

        engine = CrossAssetSpilloverEngine()
        assert engine.GraphGrangerCausalityNetwork is GraphGrangerCausalityNetwork
        assert engine.granger_network is None

        # Inject fitted Granger network
        engine.granger_network = net

        prices_dict = {
            "005930": pd.DataFrame({
                "Close": [70000, 70500, 71000, 71200, 72000, 72500],
            }),
            "NVDA": pd.DataFrame({
                "Close": [120, 122, 125, 127, 130, 132],
            }),
        }
        macro_dict = {"sox": 0.03, "usdkrw": 0.005, "vix": -0.02}
        sec_map = {"005930": "Semiconductor", "NVDA": "Information Technology"}

        res_df = engine.compute_scores(
            prices_dict=prices_dict,
            indicators_df=macro_dict,
            sector_map=sec_map,
        )
        assert not res_df.empty
        assert "cross_asset_spillover_score" in res_df.columns
        assert len(res_df) == 2
        for sc in res_df["cross_asset_spillover_score"]:
            assert 0.05 <= sc <= 0.95

    def test_ensemble_scorer_integration(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork()
        net.fit(synthetic_macro_sector_returns)

        # Force a high VIX out-degree centrality to trigger systemic risk modulation
        net.topology_metrics.out_degree_centrality["VIX"] = 0.45

        class MockConfig:
            version = 117
            ensemble_return_multiplier = 20.0

        scorer = EnsembleScoringEngine(config=MockConfig())
        assert scorer.is_phase110 is True
        assert scorer.GraphGrangerCausalityNetwork in (GraphGrangerCausalityNetwork, ts_granger.GraphGrangerCausalityNetwork)

        # Compute unmodulated dynamic weights without granger network
        scorer_unmod = EnsembleScoringEngine(config=MockConfig())
        scorer_unmod._prev_weights_dict.clear()
        unmod_weights = scorer_unmod.compute_dynamic_weights_from_sharpe(
            rolling_sharpes={"regression": 1.0, "surge": 1.0, "rim_valuation": 1.0, "accruals_quality": 1.0, "mq_factor": 1.0},
            regime="BULL_LOW_VOL",
            granger_network=None,
        )
        # Compute dynamic weights with granger network
        scorer_mod = EnsembleScoringEngine(config=MockConfig())
        scorer_mod._prev_weights_dict.clear()
        mod_weights = scorer_mod.compute_dynamic_weights_from_sharpe(
            rolling_sharpes={"regression": 1.0, "surge": 1.0, "rim_valuation": 1.0, "accruals_quality": 1.0, "mq_factor": 1.0},
            regime="BULL_LOW_VOL",
            granger_network=net,
        )

        assert sum(mod_weights.values()) == pytest.approx(1.000000, abs=1e-5)
        # Quality factors should have received a 1.15x boost relative to non-quality factors
        quality_ratio_rim = (mod_weights["rim_valuation"] / mod_weights["regression"]) / (
            unmod_weights["rim_valuation"] / unmod_weights["regression"]
        )
        assert quality_ratio_rim == pytest.approx(1.15, rel=1e-3)

        quality_ratio_acc = (mod_weights["accruals_quality"] / mod_weights["surge"]) / (
            unmod_weights["accruals_quality"] / unmod_weights["surge"]
        )
        assert quality_ratio_acc == pytest.approx(1.15, rel=1e-3)

        assert mod_weights["rim_valuation"] > unmod_weights["rim_valuation"]
        assert mod_weights["accruals_quality"] > unmod_weights["accruals_quality"]
        assert mod_weights["mq_factor"] > unmod_weights["mq_factor"]


class TestMirrorIntegrityAndEdgeCases:
    """Verifies dual-placement SHA-256 integrity and boundary handling."""

    def test_dual_placement_sha256_hash_identity(self):
        root_path = Path("src/ai/graph_granger_causality.py")
        ts_path = Path("trading_system/src/ai/graph_granger_causality.py")

        assert root_path.exists(), f"Missing {root_path}"
        assert ts_path.exists(), f"Missing {ts_path}"

        h_root = hashlib.sha256(root_path.read_bytes()).hexdigest()
        h_ts = hashlib.sha256(ts_path.read_bytes()).hexdigest()

        assert h_root == h_ts, f"SHA-256 mismatch: {h_root} != {h_ts}"

    def test_dual_tree_import_equivalence(self):
        assert GraphGrangerCausalityNetwork.VERSION == ts_granger.GraphGrangerCausalityNetwork.VERSION
        assert len(DEFAULT_MACRO_NODES) == len(ts_granger.DEFAULT_MACRO_NODES)
        assert len(DEFAULT_SECTOR_NODES) == len(ts_granger.DEFAULT_SECTOR_NODES)

    def test_reset_functionality(self, synthetic_macro_sector_returns):
        net = GraphGrangerCausalityNetwork()
        net.fit(synthetic_macro_sector_returns)
        assert net.is_fitted is True
        assert len(net.nodes) > 0

        net.reset()
        assert net.is_fitted is False
        assert len(net.nodes) == 0
        assert net.topology_metrics is None

    def test_dangling_nodes_pagerank(self):
        # Directed graph with 1 dangling node (no outgoing edges)
        C = np.array([
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],  # dangling node
        ])
        pr = compute_directed_pagerank(C, damping=0.85)
        assert len(pr) == 3
        assert np.all(pr > 0.0)
        assert sum(pr) == pytest.approx(1.000000, abs=1e-6)

    def test_short_history_graceful_fallback(self):
        tiny_df = pd.DataFrame({
            "SOX": [0.01, 0.02, -0.01],
            "XLK": [0.015, 0.025, -0.005],
        })
        net = GraphGrangerCausalityNetwork(lag_order=2)
        summary = net.fit(tiny_df)
        assert summary.causal_adjacency_matrix.shape == (2, 2)
        assert np.all(np.isfinite(summary.causal_adjacency_matrix))
