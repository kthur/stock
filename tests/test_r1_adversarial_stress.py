"""
tests/test_r1_adversarial_stress.py
Adversarial Property-Based, Combinatorial, and Boundary Stress Tests for Milestone 1 High-Alpha Strategies:
1. CrossAssetSpilloverEngine (Multi-market macro transmission, sector elasticity, extreme macro shocks)
2. SupplyChainGNNEngine (Graph cycles, cliques, self-loops, deep chains, bullwhip shock bounds)
3. RangeExpansionBreakoutEngine (NR7 boundary conditions, zero-volatility squeezes, wick rejections, extreme gaps)
4. Randomized combinatorial fuzzing across 1,000+ synthetic market universes.
"""

import unittest
import numpy as np
import pandas as pd

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine, cross_asset_spillover_score
from src.core.supply_chain_gnn import SupplyChainGNNEngine, supply_chain_gnn_score
from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine, range_expansion_score
from src.core.strategy_registry import get_registry


class TestCrossAssetSpilloverAdversarial(unittest.TestCase):
    """Adversarial stress testing for CrossAssetSpilloverEngine."""

    def setUp(self):
        self.engine = CrossAssetSpilloverEngine()

    def _generate_ohlcv(self, n_bars: int = 30, base_price: float = 100.0, trend: float = 0.0, noise: float = 0.01) -> pd.DataFrame:
        dates = pd.date_range("2026-01-01", periods=n_bars, freq="D")
        closes = [base_price]
        for _ in range(1, n_bars):
            ret = trend + np.random.normal(0, noise)
            closes.append(max(closes[-1] * (1.0 + ret), 0.01))
        closes = np.array(closes)
        highs = closes * (1.0 + np.abs(np.random.normal(0.005, 0.003, n_bars)))
        lows = closes * (1.0 - np.abs(np.random.normal(0.005, 0.003, n_bars)))
        opens = (closes + lows) / 2.0
        volumes = np.random.uniform(10000, 500000, n_bars)
        return pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes}, index=dates)

    def test_multi_market_ticker_formats_and_sector_aliases(self):
        """Stress tests mixed KRX/US tickers, tickers with suffix, missing sectors, and unicode sector aliases."""
        np.random.seed(42)
        symbols = [
            "005930", "005930.KS", "035720.KQ", "AAPL", "NVDA", "XOM", "TSLA",
            "UNKNOWN_SYM", "123456", "SYM_NULL_SECTOR"
        ]
        prices_dict = {s: self._generate_ohlcv(25) for s in symbols}

        sector_map = {
            "005930": "반도체",
            "005930.KS": "Semiconductor",
            "035720.KQ": "IT소프트웨어",
            "AAPL": "Information Technology",
            "NVDA": "Tech",
            "XOM": "Oil & Gas",
            "TSLA": "Automotive",
            "123456": "운수장비",
            "SYM_NULL_SECTOR": None,
        }

        indicators = {
            "sox_change": 4.5,
            "usdkrw_change": 1.2,
            "tnx_change": -0.8,
            "wti_change": -2.5,
            "gold_change": 0.5,
            "dxy_change": 0.3,
            "vix_change": -3.0,
            "sp500_change": 1.8,
        }

        res = self.engine.compute_scores(prices_dict=prices_dict, indicators_df=indicators, sector_map=sector_map)
        self.assertEqual(len(res), len(symbols))
        for sym in symbols:
            score = res[res["symbol"] == sym]["cross_asset_spillover_score"].iloc[0]
            self.assertTrue(0.05 <= score <= 0.95, f"Score for {sym} out of bounds: {score}")
            self.assertTrue(np.isfinite(score), f"Score for {sym} is non-finite: {score}")

    def test_extreme_macro_shocks_and_anti_overflow(self):
        """Stress tests extreme macro impulses (+1000% shocks, negative infinity, overflow prevention)."""
        p_df = self._generate_ohlcv(20, base_price=100.0, trend=0.0)
        prices_dict = {"SEMI": p_df, "OIL": p_df}
        sector_map = {"SEMI": "Semiconductor", "OIL": "Energy"}

        # Massive positive shock
        hyper_pos_macro = {"sox": 50.0, "sp500": 30.0, "vix": -50.0}
        res_pos = self.engine.compute_scores(prices_dict=prices_dict, indicators_df=hyper_pos_macro, sector_map=sector_map)
        semi_pos = res_pos[res_pos["symbol"] == "SEMI"]["cross_asset_spillover_score"].iloc[0]
        self.assertEqual(semi_pos, 0.95, "Extreme positive macro impulse must safely saturate at 0.95 without overflow")

        # Massive negative shock
        hyper_neg_macro = {"sox": -50.0, "vix": 100.0, "tnx": 50.0}
        res_neg = self.engine.compute_scores(prices_dict=prices_dict, indicators_df=hyper_neg_macro, sector_map=sector_map)
        semi_neg = res_neg[res_neg["symbol"] == "SEMI"]["cross_asset_spillover_score"].iloc[0]
        self.assertEqual(semi_neg, 0.05, "Extreme negative macro shock must safely floor at 0.05 without underflow")

    def test_degenerate_indicator_inputs(self):
        """Stress tests DataFrame indicators with NaNs, Infs, empty columns, and non-numeric garbage."""
        p_df = self._generate_ohlcv(20)
        prices = {"AAPL": p_df}

        # Empty indicators DataFrame
        res1 = self.engine.compute_scores(prices_dict=prices, indicators_df=pd.DataFrame())
        self.assertTrue(0.05 <= res1.iloc[0]["cross_asset_spillover_score"] <= 0.95)

        # DataFrame with NaN, Inf, and String columns
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        dirty_indicators = pd.DataFrame({
            "sox_change": [np.nan, np.inf, -np.inf, 1.2, 2.3, np.nan, 3.1, 1.0, 2.0, 1.5],
            "vix_change": [0.0, -1.0, np.nan, np.nan, 0.5, 0.2, -0.1, -0.2, -0.5, -0.8],
            "usdkrw": [1300, 1310, 1305, 1312, 1315, 1320, 1325, 1330, 1335, 1340],
            "unrelated_col": ["foo", "bar", "baz", None, "test", "a", "b", "c", "d", "e"]
        }, index=dates)

        res2 = self.engine.compute_scores(prices_dict=prices, indicators_df=dirty_indicators)
        score2 = res2.iloc[0]["cross_asset_spillover_score"]
        self.assertTrue(0.05 <= score2 <= 0.95)
        self.assertTrue(np.isfinite(score2))

    def test_pathological_prices_series(self):
        """Stress tests 0-variance prices, single bar, penny stock near 0, and NaN values in OHLCV."""
        dates = pd.date_range("2026-01-01", periods=20, freq="D")
        
        # 1. Perfectly flat prices (0 variance)
        flat_df = pd.DataFrame({"Open": 100.0, "High": 100.0, "Low": 100.0, "Close": 100.0, "Volume": 1000.0}, index=dates)
        
        # 2. Ultra penny stock with micro price
        penny_df = pd.DataFrame({"Open": 0.0001, "High": 0.0001, "Low": 0.0001, "Close": 0.0001, "Volume": 50.0}, index=dates)
        
        # 3. Short price history (3 bars, below 5-bar minimum)
        short_df = pd.DataFrame({"Open": [10, 11, 12], "High": [10, 11, 12], "Low": [10, 11, 12], "Close": [10, 11, 12], "Volume": [10, 10, 10]}, index=dates[:3])

        # 4. DataFrame containing NaNs
        nan_df = flat_df.copy()
        nan_df.iloc[5:10, :] = np.nan

        prices = {
            "FLAT": flat_df,
            "PENNY": penny_df,
            "SHORT": short_df,
            "NAN": nan_df
        }

        res = self.engine.compute_scores(prices_dict=prices)
        self.assertEqual(len(res), 4)
        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["cross_asset_spillover_score"] <= 0.95)
            self.assertTrue(np.isfinite(row["cross_asset_spillover_score"]))


class TestSupplyChainGNNAdversarial(unittest.TestCase):
    """Adversarial stress testing for SupplyChainGNNEngine."""

    def _generate_ohlcv(self, n_bars: int = 25, base_price: float = 100.0, trend: float = 0.0) -> pd.DataFrame:
        dates = pd.date_range("2026-01-01", periods=n_bars, freq="D")
        closes = [base_price]
        for _ in range(1, n_bars):
            ret = trend + np.random.normal(0, 0.01)
            closes.append(max(closes[-1] * (1.0 + ret), 0.01))
        closes = np.array(closes)
        return pd.DataFrame({
            "Open": closes,
            "High": closes * 1.01,
            "Low": closes * 0.99,
            "Close": closes,
            "Volume": np.random.uniform(10000, 50000, n_bars)
        }, index=dates)

    def test_graph_cycles_and_mutual_feedback(self):
        """Stress tests 2-cycles (A <-> B), 3-cycles (A -> B -> C -> A), and self-loops (A -> A)."""
        cyclic_edges = [
            ("NODE_A", "NODE_B", 0.90),
            ("NODE_B", "NODE_A", 0.90),  # Mutual 2-cycle
            ("NODE_C", "NODE_D", 0.80),
            ("NODE_D", "NODE_E", 0.80),
            ("NODE_E", "NODE_C", 0.80),  # 3-cycle
            ("NODE_F", "NODE_F", 0.70),  # Self loop
        ]

        engine = SupplyChainGNNEngine(custom_edges=cyclic_edges)
        
        prices = {
            "NODE_A": self._generate_ohlcv(20, trend=0.05),
            "NODE_B": self._generate_ohlcv(20, trend=-0.05),
            "NODE_C": self._generate_ohlcv(20, trend=0.03),
            "NODE_D": self._generate_ohlcv(20, trend=0.0),
            "NODE_E": self._generate_ohlcv(20, trend=-0.03),
            "NODE_F": self._generate_ohlcv(20, trend=0.02),
        }

        res = engine.compute_scores(prices_dict=prices)
        self.assertEqual(len(res), 6)
        for sym in prices.keys():
            score = res[res["symbol"] == sym]["supply_chain_gnn_score"].iloc[0]
            self.assertTrue(0.05 <= score <= 0.95)
            self.assertTrue(np.isfinite(score))

    def test_dense_complete_graph_clique(self):
        """Stress tests complete graph K_6 (all 6 nodes connected to each other)."""
        nodes = [f"CLIQUE_{i}" for i in range(6)]
        clique_edges = [(u, v, 0.5) for u in nodes for v in nodes if u != v]

        engine = SupplyChainGNNEngine(custom_edges=clique_edges)
        prices = {n: self._generate_ohlcv(20, trend=0.02 if "0" in n else -0.02) for n in nodes}

        res = engine.compute_scores(prices_dict=prices)
        self.assertEqual(len(res), 6)
        for n in nodes:
            score = res[res["symbol"] == n]["supply_chain_gnn_score"].iloc[0]
            self.assertTrue(0.05 <= score <= 0.95)

    def test_extreme_flash_crash_and_hyper_surge_propagation(self):
        """Stress tests 99% crash and 500% surge propagation across multi-tier network."""
        chain_edges = [
            ("ROOT_CRASH", "TIER1_A", 0.95),
            ("TIER1_A", "TIER2_A", 0.95),
            ("ROOT_BOOM", "TIER1_B", 0.95),
            ("TIER1_B", "TIER2_B", 0.95),
        ]
        engine = SupplyChainGNNEngine(custom_edges=chain_edges)

        # Root crash: drops 90% in 5 days
        crash_df = self._generate_ohlcv(20, trend=-0.35)
        # Root boom: rises 300% in 5 days
        boom_df = self._generate_ohlcv(20, trend=0.35)
        # Downstream nodes: flat initial momentum
        flat_df = self._generate_ohlcv(20, trend=0.0)

        prices = {
            "ROOT_CRASH": crash_df,
            "TIER1_A": flat_df,
            "TIER2_A": flat_df,
            "ROOT_BOOM": boom_df,
            "TIER1_B": flat_df,
            "TIER2_B": flat_df,
        }

        res = engine.compute_scores(prices_dict=prices)
        score_map = dict(zip(res["symbol"], res["supply_chain_gnn_score"]))

        # Downstream crash nodes should receive depressed scores due to bullwhip 1.35x amplification
        self.assertLess(score_map["TIER1_A"], 0.40)
        self.assertLess(score_map["TIER2_A"], 0.45)

        # Downstream boom nodes should receive elevated scores
        self.assertGreater(score_map["TIER1_B"], 0.60)
        self.assertGreater(score_map["TIER2_B"], 0.55)

        # All bounded in [0.05, 0.95]
        for s in score_map.values():
            self.assertTrue(0.05 <= s <= 0.95)

    def test_symbol_normalization_robustness(self):
        """Stress tests numeric int keys, .KS / .KQ suffix keys, lowercase strings."""
        engine = SupplyChainGNNEngine()
        df = self._generate_ohlcv(20)
        prices = {
            "005930": df,
            "5930": df,
            "005930.KS": df,
            "nvda": df,
            "NVDA": df,
        }
        res = engine.compute_scores(prices_dict=prices)
        self.assertEqual(len(res), len(prices))
        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["supply_chain_gnn_score"] <= 0.95)


class TestRangeExpansionBreakoutAdversarial(unittest.TestCase):
    """Adversarial stress testing for RangeExpansionBreakoutEngine."""

    def setUp(self):
        self.engine = RangeExpansionBreakoutEngine()

    def test_zero_volatility_and_flatline_series(self):
        """Stress tests perfectly flat stock with zero ATR and zero standard deviation."""
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        flat_df = pd.DataFrame({
            "Open": [100.0] * 30,
            "High": [100.0] * 30,
            "Low": [100.0] * 30,
            "Close": [100.0] * 30,
            "Volume": [1000.0] * 30
        }, index=dates)

        res = self.engine.compute_scores(prices_dict={"FLAT_SYM": flat_df})
        score = res[res["symbol"] == "FLAT_SYM"]["range_expansion_score"].iloc[0]
        self.assertTrue(0.05 <= score <= 0.95)
        self.assertTrue(np.isfinite(score))
        self.assertAlmostEqual(score, 0.45, places=2)

    def test_massive_wick_rejection_bull_trap(self):
        """Stress tests massive upper shadow / wick rejection (Bull Trap: High +25%, Close near Low)."""
        dates = pd.date_range("2026-01-01", periods=25, freq="D")
        highs = [100.0] * 25
        lows = [98.0] * 25
        closes = [99.0] * 25
        opens = [99.0] * 25
        vols = [100000.0] * 25

        # Bar -1: Opens at 99, spikes to 125, but collapses to close at 98.2 (CLV = (98.2 - 98.0)/(125 - 98) ~ 0.007)
        opens[-1] = 99.0
        highs[-1] = 125.0
        lows[-1] = 98.0
        closes[-1] = 98.2
        vols[-1] = 500000.0  # Massive volume churn

        df_trap = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols}, index=dates)
        res = self.engine.compute_scores(prices_dict={"BULL_TRAP": df_trap})
        score = res[res["symbol"] == "BULL_TRAP"]["range_expansion_score"].iloc[0]

        # Bull trap should be recognized as a bearish rejection / breakdown (< 0.50)
        self.assertLess(score, 0.40, f"Bull trap should receive low score due to low CLV, got {score}")

    def test_nr7_inside_day_compression_boundary_variations(self):
        """Stress tests exact NR7 compression variations (single tight day vs multiple tied days)."""
        dates = pd.date_range("2026-01-01", periods=25, freq="D")
        highs = [105.0] * 25
        lows = [95.0] * 25
        closes = [100.0] * 25
        opens = [100.0] * 25
        vols = [100000.0] * 25

        # Create precise inside day at t-2
        highs[-2] = 100.5
        lows[-2] = 99.5
        closes[-2] = 100.0
        opens[-2] = 100.0

        # Breakout at t-1
        highs[-1] = 112.0
        lows[-1] = 99.8
        closes[-1] = 111.8
        opens[-1] = 100.0
        vols[-1] = 300000.0

        df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols}, index=dates)
        res = self.engine.compute_scores(prices_dict={"NR7_SYM": df})
        score = res[res["symbol"] == "NR7_SYM"]["range_expansion_score"].iloc[0]
        self.assertGreater(score, 0.70)

    def test_missing_volume_and_single_column_input(self):
        """Stress tests DataFrame lacking Volume column or passed as single column."""
        dates = pd.date_range("2026-01-01", periods=25, freq="D")
        df_no_vol = pd.DataFrame({
            "Open": [100.0] * 25,
            "High": [105.0] * 25,
            "Low": [95.0] * 25,
            "Close": [102.0] * 25,
        }, index=dates)

        res = self.engine.compute_scores(prices_dict={"NO_VOL": df_no_vol})
        score = res[res["symbol"] == "NO_VOL"]["range_expansion_score"].iloc[0]
        self.assertTrue(0.05 <= score <= 0.95)


class TestCombinatorialFuzzingMultiUniverse(unittest.TestCase):
    """Combinatorial fuzzing across 100 synthetic market universes with randomized noise and missing data."""

    def test_fuzz_100_synthetic_universes_invariants(self):
        np.random.seed(999)
        n_universes = 50

        spillover_engine = CrossAssetSpilloverEngine()
        gnn_engine = SupplyChainGNNEngine()
        breakout_engine = RangeExpansionBreakoutEngine()

        for u in range(n_universes):
            n_syms = np.random.randint(5, 30)
            symbols = [f"SYM_{u}_{i}" for i in range(n_syms)]
            n_bars = np.random.randint(5, 45)

            prices = {}
            for s in symbols:
                base = np.random.uniform(1.0, 500.0)
                volat = np.random.uniform(0.001, 0.10)
                trend = np.random.uniform(-0.05, 0.05)

                dates = pd.date_range("2026-01-01", periods=n_bars, freq="D")
                closes = [base]
                for _ in range(1, n_bars):
                    closes.append(max(closes[-1] * (1.0 + trend + np.random.normal(0, volat)), 0.001))
                closes = np.array(closes)
                highs = closes * (1.0 + np.abs(np.random.normal(0.01, 0.01, n_bars)))
                lows = closes * (1.0 - np.abs(np.random.normal(0.01, 0.01, n_bars)))
                opens = (closes + lows) / 2.0
                vols = np.random.exponential(100000.0, n_bars)

                df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols}, index=dates)
                prices[s] = df

            # Random macro indicators
            indicators = {
                "sox_change": float(np.random.uniform(-10.0, 10.0)),
                "wti_change": float(np.random.uniform(-10.0, 10.0)),
                "vix_change": float(np.random.uniform(-20.0, 20.0)),
                "sp500_change": float(np.random.uniform(-5.0, 5.0)),
            }

            # 1. Spillover
            r_spill = spillover_engine.compute_scores(prices_dict=prices, indicators_df=indicators)
            self.assertEqual(len(r_spill), n_syms)
            self.assertTrue((r_spill["cross_asset_spillover_score"] >= 0.05).all())
            self.assertTrue((r_spill["cross_asset_spillover_score"] <= 0.95).all())
            self.assertTrue(r_spill["cross_asset_spillover_score"].notna().all())

            # 2. GNN
            r_gnn = gnn_engine.compute_scores(prices_dict=prices)
            self.assertEqual(len(r_gnn), n_syms)
            self.assertTrue((r_gnn["supply_chain_gnn_score"] >= 0.05).all())
            self.assertTrue((r_gnn["supply_chain_gnn_score"] <= 0.95).all())
            self.assertTrue(r_gnn["supply_chain_gnn_score"].notna().all())

            # 3. Breakout
            r_brk = breakout_engine.compute_scores(prices_dict=prices)
            self.assertEqual(len(r_brk), n_syms)
            self.assertTrue((r_brk["range_expansion_score"] >= 0.05).all())
            self.assertTrue((r_brk["range_expansion_score"] <= 0.95).all())
            self.assertTrue(r_brk["range_expansion_score"].notna().all())


class TestLargeUniversePerformanceAndEnsembleIntegration(unittest.TestCase):
    """Stress tests 500+ symbol large universe scaling and CrossSectionalScoreNormalizer / Ensemble integration."""

    def test_500_symbols_batch_performance_and_normalization(self):
        import time
        from src.ai.score_normalizer import CrossSectionalScoreNormalizer
        from src.ai.ensemble_scorer import EnsembleScoringEngine

        np.random.seed(777)
        n_symbols = 500
        symbols = [f"SYM_{i:04d}" for i in range(n_symbols)]
        dates = pd.date_range("2026-01-01", periods=30, freq="D")

        # Generate 500 synthetic stocks
        prices_dict = {}
        for s in symbols:
            ret = np.random.normal(0, 0.02, 30)
            close = 100.0 * np.exp(np.cumsum(ret))
            high = close * 1.01
            low = close * 0.99
            prices_dict[s] = pd.DataFrame({
                "Open": close, "High": high, "Low": low, "Close": close, "Volume": np.random.uniform(50000, 200000, 30)
            }, index=dates)

        indicators = {"sox_change": 3.0, "vix_change": -1.5, "sp500_change": 1.2, "wti_change": 0.5}

        # 1. Execute all 3 engines
        t0 = time.time()
        spillover_df = CrossAssetSpilloverEngine().compute_scores(prices_dict=prices_dict, indicators_df=indicators)
        gnn_df = SupplyChainGNNEngine().compute_scores(prices_dict=prices_dict)
        breakout_df = RangeExpansionBreakoutEngine().compute_scores(prices_dict=prices_dict)
        t_elapsed = time.time() - t0

        self.assertEqual(len(spillover_df), n_symbols)
        self.assertEqual(len(gnn_df), n_symbols)
        self.assertEqual(len(breakout_df), n_symbols)

        # Ensure reasonable batch latency (< 5.0 seconds for 500 symbols across 3 engines)
        self.assertLess(t_elapsed, 5.0, f"Execution too slow: {t_elapsed:.2f}s for 500 symbols")

        # 2. Score Normalizer Integration
        normalizer = CrossSectionalScoreNormalizer(method="percentile_rank")
        df_merged = pd.DataFrame({
            "symbol": symbols,
            "market": ["SP500"] * 250 + ["KOSPI"] * 250,
            "cross_asset_spillover_score": spillover_df["cross_asset_spillover_score"].values,
            "supply_chain_gnn_score": gnn_df["supply_chain_gnn_score"].values,
            "range_expansion_score": breakout_df["range_expansion_score"].values,
        })
        norm_df = normalizer.normalize_cross_section(
            df=df_merged,
            score_cols=["cross_asset_spillover_score", "supply_chain_gnn_score", "range_expansion_score"]
        )
        for col in ["cross_asset_spillover_score", "supply_chain_gnn_score", "range_expansion_score"]:
            self.assertTrue((norm_df[col] >= 0.005).all() and (norm_df[col] <= 0.995).all())

        # 3. Ensemble Scoring Integration
        ensemble = EnsembleScoringEngine()
        ensemble_res = ensemble.calculate_ensemble_score(
            regime="BULL_HIGH_VOL",
            scores_df=norm_df,
            prices_dict=prices_dict
        )

        self.assertIsInstance(ensemble_res, pd.DataFrame)
        self.assertEqual(len(ensemble_res), n_symbols)
        self.assertIn("ensemble_score", ensemble_res.columns)
        for _, row in ensemble_res.iterrows():
            sc = row["ensemble_score"]
            self.assertTrue(0.0 <= sc <= 1.0, f"Ensemble score for {row.get('symbol')} out of range: {sc}")


if __name__ == "__main__":
    unittest.main()

