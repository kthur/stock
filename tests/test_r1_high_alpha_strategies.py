"""
tests/test_r1_high_alpha_strategies.py
Unit and Integration Tests for R1 High-Alpha Strategy Engines:
1. CrossAssetSpilloverEngine (Strategy: cross_asset_spillover)
2. SupplyChainGNNEngine (Strategy: supply_chain_gnn)
3. RangeExpansionBreakoutEngine (Strategy: range_expansion_breakout)
4. StrategyRegistry and Ensemble integration
"""

import unittest
import numpy as np
import pandas as pd

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame
from src.core.strategy_registry import get_registry, StrategyMeta, StrategyRegistry
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine, cross_asset_spillover_score
from src.core.supply_chain_gnn import SupplyChainGNNEngine, supply_chain_gnn_score
from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine, range_expansion_score
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.score_normalizer import CrossSectionalScoreNormalizer


class TestR1HighAlphaStrategies(unittest.TestCase):
    def setUp(self):
        self.registry = get_registry()
        self.registry.auto_discover(["src.core", "src.ai"])

    def _make_dummy_ohlcv(self, n_bars: int = 30, base_price: float = 100.0, trend: float = 0.0) -> pd.DataFrame:
        """Generate synthetic OHLCV bars."""
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=n_bars, freq="D")
        closes = [base_price]
        for i in range(1, n_bars):
            ret = trend + np.random.normal(0, 0.015)
            closes.append(closes[-1] * (1.0 + ret))
        closes = np.array(closes)
        highs = closes * (1.0 + np.abs(np.random.normal(0.008, 0.005, n_bars)))
        lows = closes * (1.0 - np.abs(np.random.normal(0.008, 0.005, n_bars)))
        opens = (closes + lows) / 2.0
        volumes = np.random.uniform(100000, 500000, n_bars)

        df = pd.DataFrame({
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        }, index=dates)
        return df

    # -------------------------------------------------------------------------
    # 1. CrossAssetSpilloverEngine Tests
    # -------------------------------------------------------------------------
    def test_cross_asset_spillover_metadata_and_inheritance(self):
        engine = CrossAssetSpilloverEngine()
        self.assertIsInstance(engine, BaseStrategyEngine)
        item = self.registry.get("cross_asset_spillover")
        self.assertIsNotNone(item, "cross_asset_spillover should be registered in StrategyRegistry")
        _, meta = item
        self.assertEqual(meta.strategy_id, "cross_asset_spillover")
        self.assertEqual(meta.score_column, "cross_asset_spillover_score")
        self.assertTrue(meta.requires_indicators)
        self.assertIn("cross_asset_spillover_predictions.txt", meta.output_file)

    def test_cross_asset_spillover_empty_and_fallback(self):
        engine = CrossAssetSpilloverEngine()
        # Empty prices
        res_empty = engine.compute_scores(prices_dict={})
        self.assertTrue(isinstance(res_empty, (pd.DataFrame, ScoreDataFrame)))
        self.assertIn("cross_asset_spillover_score", res_empty.columns)

        # None indicators fallback
        p_df = self._make_dummy_ohlcv(20, base_price=100.0)
        res_no_macro = engine.compute_scores(prices_dict={"AAPL": p_df}, indicators_df=None)
        self.assertIn("AAPL", res_no_macro["symbol"].values)
        score_val = res_no_macro[res_no_macro["symbol"] == "AAPL"]["cross_asset_spillover_score"].iloc[0]
        self.assertTrue(0.05 <= score_val <= 0.95)

    def test_cross_asset_spillover_macro_impulse_and_bounds(self):
        engine = CrossAssetSpilloverEngine()
        # Create semiconductor stock with lagging price return (flat)
        semi_df = self._make_dummy_ohlcv(30, base_price=100.0, trend=0.0)
        # Create energy stock
        energy_df = self._make_dummy_ohlcv(30, base_price=50.0, trend=0.0)

        prices_dict = {
            "005930": semi_df,
            "XOM": energy_df,
        }
        sector_map = {
            "005930": "Semiconductor",
            "XOM": "Energy",
        }

        # Macro indicators: SOX up 5%, WTI down 3%, TNX down 1%
        indicators = {
            "sox_change": 5.0,
            "wti_change": -3.0,
            "tnx_change": -1.0,
            "usdkrw_change": 0.5,
            "vix_change": -2.0,
        }

        res = engine.compute_scores(prices_dict=prices_dict, indicators_df=indicators, sector_map=sector_map)
        semi_score = res[res["symbol"] == "005930"]["cross_asset_spillover_score"].iloc[0]
        energy_score = res[res["symbol"] == "XOM"]["cross_asset_spillover_score"].iloc[0]

        # Semiconductor should have high positive impulse from SOX +5%
        self.assertGreater(semi_score, 0.55, "Semiconductor should receive high score on SOX surge")
        # Energy should have lower impulse due to WTI -3%
        self.assertLess(energy_score, semi_score, "Semiconductor score should be higher than Energy during SOX boom & oil slump")
        self.assertTrue(0.05 <= semi_score <= 0.95)
        self.assertTrue(0.05 <= energy_score <= 0.95)

        # Test convenience function
        func_res = cross_asset_spillover_score(prices_dict=prices_dict, indicators_df=indicators, sector_map=sector_map)
        self.assertEqual(len(func_res), 2)

    # -------------------------------------------------------------------------
    # 2. SupplyChainGNNEngine Tests
    # -------------------------------------------------------------------------
    def test_supply_chain_gnn_metadata_and_inheritance(self):
        engine = SupplyChainGNNEngine()
        self.assertIsInstance(engine, BaseStrategyEngine)
        item = self.registry.get("supply_chain_gnn")
        self.assertIsNotNone(item, "supply_chain_gnn should be registered in StrategyRegistry")
        _, meta = item
        self.assertEqual(meta.strategy_id, "supply_chain_gnn")
        self.assertEqual(meta.score_column, "supply_chain_gnn_score")
        self.assertEqual(meta.category, "network")

    def test_supply_chain_gnn_2hop_propagation(self):
        engine = SupplyChainGNNEngine()

        # NVDA surges +8%, SK Hynix (000660) flat, Hanmi Semi (042700) flat, isolated stock (XYZ) flat
        nvda_df = self._make_dummy_ohlcv(20, base_price=100.0, trend=0.03)  # Surging
        hynix_df = self._make_dummy_ohlcv(20, base_price=100.0, trend=0.0)  # Hop 1
        hanmi_df = self._make_dummy_ohlcv(20, base_price=50.0, trend=0.0)   # Hop 2
        xyz_df = self._make_dummy_ohlcv(20, base_price=10.0, trend=0.0)     # Isolated

        prices = {
            "NVDA": nvda_df,
            "000660": hynix_df,
            "042700": hanmi_df,
            "XYZ": xyz_df,
        }

        res = engine.compute_scores(prices_dict=prices)
        scores_map = dict(zip(res["symbol"], res["supply_chain_gnn_score"]))

        # NVDA, SK Hynix, Hanmi should receive higher momentum than isolated XYZ
        self.assertIn("042700", scores_map)
        self.assertIn("000660", scores_map)
        self.assertGreater(scores_map["000660"], scores_map["XYZ"])
        self.assertTrue(0.05 <= scores_map["042700"] <= 0.95)

        # Test convenience function
        func_res = supply_chain_gnn_score(prices_dict=prices)
        self.assertEqual(len(func_res), 4)

    def test_supply_chain_gnn_bullwhip_asymmetric_shock(self):
        engine = SupplyChainGNNEngine()

        # Positive customer shock scenario (+6%)
        tsla_pos = self._make_dummy_ohlcv(20, base_price=200.0, trend=0.02)
        lges_pos = self._make_dummy_ohlcv(20, base_price=400.0, trend=0.0)
        res_pos = engine.compute_scores(prices_dict={"TSLA": tsla_pos, "373220": lges_pos})
        lges_pos_score = res_pos[res_pos["symbol"] == "373220"]["supply_chain_gnn_score"].iloc[0]

        # Negative customer shock scenario (-6%)
        tsla_neg = self._make_dummy_ohlcv(20, base_price=200.0, trend=-0.02)
        lges_neg = self._make_dummy_ohlcv(20, base_price=400.0, trend=0.0)
        res_neg = engine.compute_scores(prices_dict={"TSLA": tsla_neg, "373220": lges_neg})
        lges_neg_score = res_neg[res_neg["symbol"] == "373220"]["supply_chain_gnn_score"].iloc[0]

        # Bullwhip asymmetry: downside transmission is amplified (1.35x vs 0.85x)
        pos_delta = abs(lges_pos_score - 0.50)
        neg_delta = abs(lges_neg_score - 0.50)
        self.assertGreater(neg_delta, pos_delta * 0.9, "Negative shocks should transmit aggressively through bullwhip effect")

    # -------------------------------------------------------------------------
    # 3. RangeExpansionBreakoutEngine Tests
    # -------------------------------------------------------------------------
    def test_range_expansion_metadata_and_inheritance(self):
        engine = RangeExpansionBreakoutEngine()
        self.assertIsInstance(engine, BaseStrategyEngine)
        item = self.registry.get("range_expansion_breakout")
        self.assertIsNotNone(item, "range_expansion_breakout should be registered in StrategyRegistry")
        _, meta = item
        self.assertEqual(meta.strategy_id, "range_expansion_breakout")
        self.assertEqual(meta.score_column, "range_expansion_score")
        self.assertEqual(meta.category, "breakout")

    def test_range_expansion_breakout_detection(self):
        engine = RangeExpansionBreakoutEngine()

        # Build 30 bars: 20 bars consolidation, then tight NR7 inside bar, then massive breakout bar
        np.random.seed(123)
        dates = pd.date_range("2026-01-01", periods=25, freq="D")
        closes = [100.0] * 25
        highs = [101.0] * 25
        lows = [99.0] * 25
        opens = [100.0] * 25
        vols = [100000.0] * 25

        # Bar -2 (day before breakout): tight NR7 compression
        highs[-2] = 100.2
        lows[-2] = 99.8
        closes[-2] = 100.0
        opens[-2] = 100.0

        # Bar -1 (today): massive range expansion bar with 3x ATR, 3x volume, closing at high
        opens[-1] = 100.0
        highs[-1] = 108.0
        lows[-1] = 99.5
        closes[-1] = 107.8  # CLV ~ 0.98
        vols[-1] = 350000.0  # RVOL = 3.5x

        df_breakout = pd.DataFrame({
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": vols,
        }, index=dates)

        res = engine.compute_scores(prices_dict={"BREAKOUT_SYM": df_breakout})
        score_val = res[res["symbol"] == "BREAKOUT_SYM"]["range_expansion_score"].iloc[0]
        self.assertGreater(score_val, 0.70, f"Bullish range expansion breakout should score high, got {score_val}")
        self.assertTrue(0.05 <= score_val <= 0.95)

        # Test bearish breakdown bar: open high, collapse, close at low with high volume
        opens[-1] = 100.0
        highs[-1] = 100.5
        lows[-1] = 92.0
        closes[-1] = 92.2  # CLV ~ 0.02
        vols[-1] = 350000.0

        df_breakdown = pd.DataFrame({
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": vols,
        }, index=dates)

        res_down = engine.compute_scores(prices_dict={"BREAKDOWN_SYM": df_breakdown})
        score_down = res_down[res_down["symbol"] == "BREAKDOWN_SYM"]["range_expansion_score"].iloc[0]
        self.assertLess(score_down, 0.35, f"Bearish range breakdown should score low, got {score_down}")

        # Test convenience function
        func_res = range_expansion_score(prices_dict={"BREAKOUT_SYM": df_breakout})
        self.assertEqual(len(func_res), 1)

    # -------------------------------------------------------------------------
    # 4. Registry & Ensemble Integration Tests
    # -------------------------------------------------------------------------
    def test_strategy_registry_integration_all_three(self):
        all_ids = self.registry.get_all_ids()
        self.assertIn("cross_asset_spillover", all_ids)
        self.assertIn("supply_chain_gnn", all_ids)
        self.assertIn("range_expansion_breakout", all_ids)

        score_cols = self.registry.get_all_score_columns()
        self.assertEqual(score_cols["cross_asset_spillover"], "cross_asset_spillover_score")
        self.assertEqual(score_cols["supply_chain_gnn"], "supply_chain_gnn_score")
        self.assertEqual(score_cols["range_expansion_breakout"], "range_expansion_score")

    def test_ensemble_scorer_dynamic_weights_includes_new_strategies(self):
        scorer = EnsembleScoringEngine()
        weights = scorer.get_base_weights(regime="BULL_HIGH_VOL")
        self.assertIn("cross_asset_spillover", weights)
        self.assertIn("supply_chain_gnn", weights)
        self.assertIn("range_expansion_breakout", weights)
        self.assertGreater(weights["cross_asset_spillover"], 0.0)
        self.assertGreater(weights["supply_chain_gnn"], 0.0)
        self.assertGreater(weights["range_expansion_breakout"], 0.0)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)

    def test_extreme_nan_and_flat_data_fallbacks(self):
        # CrossAsset with NaN/Inf
        c_engine = CrossAssetSpilloverEngine()
        nan_df = pd.DataFrame({
            "Open": [np.nan, 100.0],
            "High": [np.nan, 105.0],
            "Low": [np.nan, 95.0],
            "Close": [np.nan, np.inf],
            "Volume": [0, 1000],
        })
        c_res = c_engine.compute_scores(prices_dict={"NAN_SYM": nan_df})
        self.assertIn("NAN_SYM", c_res["symbol"].values)
        c_val = c_res[c_res["symbol"] == "NAN_SYM"]["cross_asset_spillover_score"].iloc[0]
        self.assertTrue(0.0 <= c_val <= 1.0)
        self.assertTrue(np.isfinite(c_val))

        # SupplyChain with unknown isolated ticker
        sc_engine = SupplyChainGNNEngine()
        df = self._make_dummy_ohlcv(20, base_price=50.0)
        sc_res = sc_engine.compute_scores(prices_dict={"ISOLATED_TICKER": df})
        self.assertIn("ISOLATED_TICKER", sc_res["symbol"].values)
        sc_val = sc_res[sc_res["symbol"] == "ISOLATED_TICKER"]["supply_chain_gnn_score"].iloc[0]
        self.assertTrue(0.0 <= sc_val <= 1.0)

        # RangeExpansion with constant zero-volatility prices
        re_engine = RangeExpansionBreakoutEngine()
        flat_df = pd.DataFrame({
            "Open": [100.0] * 25,
            "High": [100.0] * 25,
            "Low": [100.0] * 25,
            "Close": [100.0] * 25,
            "Volume": [10000.0] * 25,
        })
        re_res = re_engine.compute_scores(prices_dict={"FLAT_SYM": flat_df})
        self.assertIn("FLAT_SYM", re_res["symbol"].values)
        re_val = re_res[re_res["symbol"] == "FLAT_SYM"]["range_expansion_score"].iloc[0]
        self.assertTrue(0.0 <= re_val <= 1.0)
        self.assertTrue(np.isfinite(re_val))


if __name__ == "__main__":
    unittest.main()

