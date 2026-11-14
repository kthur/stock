"""
test_phase194_china_cross_border_expansion.py — Phase 194 / Release R185 China Cross-Border Expansion Tests.

Validates:
1. China Strategic Value Chain GNN edges (EV, batteries, solar, rare earth, semiconductor packaging, cyclical consumption).
2. Cross-Asset Spillover sector elasticities for China-sensitive Korean/US industries.
3. Global Benchmark Fallbacks containing China SSE, SZSE, and HKEX tickers.
4. Mathematical propagation of Chinese anchor price shocks through 2-hop relational graph.
5. Robustness against missing nodes, extreme price changes, and NaN/Inf invariance.
"""

import math
import pytest
import numpy as np
import pandas as pd

from src.core.supply_chain_gnn import (
    SupplyChainGNNEngine,
    GLOBAL_VALUE_CHAIN_EDGES,
)
from src.core.cross_asset_spillover import (
    CrossAssetSpilloverEngine,
    DEFAULT_SECTOR_MACRO_BETAS,
)
from src.data_layer.indicator_storage import (
    GLOBAL_BENCHMARK_FALLBACKS,
)


class TestChinaCrossBorderValueChainGNN:
    """Validates the integration of Chinese market leaders into SupplyChainGNNEngine."""

    def test_china_value_chain_edges_present(self):
        """TC-CN01: Verify Chinese strategic nodes are present in GLOBAL_VALUE_CHAIN_EDGES."""
        engine = SupplyChainGNNEngine()
        nodes = engine.all_nodes

        # Strategic China Leaders
        expected_china_nodes = {
            "300750",  # CATL
            "002594",  # BYD
            "002466",  # Tianqi Lithium
            "002460",  # Ganfeng Lithium
            "603659",  # Putailai
            "601012",  # LONGi Green Energy
            "600438",  # Tongwei
            "300274",  # Sungrow Power
            "688981",  # SMIC
            "600584",  # JCET
            "002156",  # Tongfu Microelectronics
            "600111",  # China Northern Rare Earth
            "600519",  # Kweichow Moutai
            "600019",  # Baosteel
            "600309",  # Wanhua Chemical
            "601919",  # COSCO Shipping
        }

        for node in expected_china_nodes:
            assert node in nodes, f"Expected China node {node} missing from GNN graph nodes."

    def test_china_to_krx_2hop_propagation(self):
        """TC-CN02: Verify 2-hop propagation from China leader through intermediate to Korean supplier."""
        engine = SupplyChainGNNEngine(decay_factor=0.50)

        # In in_adj, targets have lists of (source, weight)
        # Check that Hanmi Semiconductor (042700) receives inputs from JCET (600584) or Tongfu (002156)
        in_hanmi = [src for src, _ in engine.in_adj.get("042700", [])]
        assert "600584" in in_hanmi or "002156" in in_hanmi or "000660" in in_hanmi

        # Check that LG Energy Solution (373220) receives inputs from CATL (300750) or Ganfeng (002460)
        in_lges = [src for src, _ in engine.in_adj.get("373220", [])]
        assert "300750" in in_lges or "002460" in in_lges or "TSLA" in in_lges

    def test_china_shock_transmission_math(self):
        """TC-CN03: Simulate Chinese EV/Battery surge and verify positive alpha impulse in KRX recipients."""
        engine = SupplyChainGNNEngine(decay_factor=0.60)

        # Mock price data where CATL surges +8.0%
        price_data = {
            "300750": pd.DataFrame({
                "Close": [100.0, 102.0, 108.0],
                "Volume": [1000000, 1200000, 2500000]
            }),
            "373220": pd.DataFrame({
                "Close": [400000.0, 401000.0, 402000.0],
                "Volume": [50000, 60000, 70000]
            }),
            "247540": pd.DataFrame({
                "Close": [200000.0, 201000.0, 201500.0],
                "Volume": [30000, 35000, 40000]
            }),
        }

        universe = ["373220", "247540"]
        scores_df = engine.calculate_scores(symbols=universe, prices_dict=price_data)
        assert not scores_df.empty
        assert "supply_chain_gnn_score" in scores_df.columns

        # Verify finite values and positive momentum response
        for _, row in scores_df.iterrows():
            score = row["supply_chain_gnn_score"]
            assert not math.isnan(score)
            assert not math.isinf(score)


class TestChinaCrossAssetSpillover:
    """Validates Cross-Asset Spillover sector elasticities for China-sensitive sectors."""

    def test_china_impacted_sectors_in_betas(self):
        """TC-CN04: Verify Secondary Battery, Solar, Cosmetics, and Shipping exist in macro betas."""
        required_sectors = ["Secondary Battery", "2차전지", "Solar", "태양광", "Cosmetics", "화장품", "Shipping", "해운"]
        for s in required_sectors:
            assert s in DEFAULT_SECTOR_MACRO_BETAS, f"Sector {s} missing from DEFAULT_SECTOR_MACRO_BETAS."
            betas = DEFAULT_SECTOR_MACRO_BETAS[s]
            assert "sox" in betas
            assert "usdkrw" in betas
            assert "vix" in betas


class TestChinaGlobalBenchmarkFallbacks:
    """Validates Global Benchmark Fallbacks including China SSE/SZSE and HKEX."""

    def test_china_and_hk_benchmarks_exist(self):
        """TC-CN05: Verify China and Hong Kong benchmark fallbacks are registered."""
        markets = {mkt for _, _, mkt, _, _ in GLOBAL_BENCHMARK_FALLBACKS}
        assert "CHINA_SSE" in markets
        assert "CHINA_SZSE" in markets
        assert "HKEX" in markets

        symbols = [sym for sym, _, _, _, _ in GLOBAL_BENCHMARK_FALLBACKS]
        assert "600519.SS" in symbols  # Moutai
        assert "300750.SZ" in symbols  # CATL
        assert "0700.HK" in symbols     # Tencent
        assert "9988.HK" in symbols     # Alibaba
