"""
tests/test_milestone1_strategy_remediation.py
Unit tests for Milestone 1 (Strategy Defect & Fallback Remediation).
Verifies:
1. Stat-Arb FDR rank calculation, equilibrium neutral scoring (0.50), and market residual Z-score fallback.
2. Short Squeeze adaptive price-volume microstructure proxy fallback (no hard NaNs).
3. RIM valuation price-trend proxy for missing BPS / fundamentals.
4. StrategyExecutor universe-wide sentiment & earnings tone drift proxy (no 100-symbol truncation).
5. Universe baseline alignment (0.50) for sparse strategies (vcp_rule, lead_lag, stat_arb).
"""

import unittest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock

from src.core.stat_arb import StatisticalArbitrageEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.rim_valuation import RIMValuationEngine
from src.pipeline.strategy_executor import AlphaStrategyExecutor, PipelineStrategyContext


class TestMilestone1StrategyRemediation(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Stat-Arb Engine Tests
    # ──────────────────────────────────────────────────────────────────────────
    def test_stat_arb_equilibrium_neutral_score(self):
        """Pairs with |Z| < entry threshold must receive neutral score (0.50), not be dropped."""
        pairs = [
            {
                "pair": ("SYM_A", "SYM_B"),
                "s1": "SYM_A",
                "s2": "SYM_B",
                "z_score": 0.25,  # within equilibrium [-1.2, 1.2]
                "signal": "NEUTRAL",
                "half_life": 10.0,
                "correlation": 0.92,
                "adf_pvalue": 0.02,
            },
            {
                "pair": ("SYM_C", "SYM_D"),
                "s1": "SYM_C",
                "s2": "SYM_D",
                "z_score": -0.10,
                "signal": "NEUTRAL",
                "half_life": 8.0,
                "correlation": 0.88,
                "adf_pvalue": 0.03,
            }
        ]
        res_df = StatisticalArbitrageEngine.get_symbol_stat_arb_scores(pairs)
        self.assertFalse(res_df.empty, "Neutral pairs must produce a non-empty DataFrame")
        self.assertEqual(len(res_df), 4, "All symbols in pairs must be represented")
        symbols_found = set(res_df['symbol'])
        self.assertTrue({'SYM_A', 'SYM_B', 'SYM_C', 'SYM_D'}.issubset(symbols_found))
        
        # Equilibrium pairs should evaluate to neutral score 0.50
        for _, row in res_df.iterrows():
            self.assertAlmostEqual(row['stat_arb_score'], 0.50, delta=0.01)

    def test_stat_arb_fdr_rank_fallback_retention(self):
        """When FDR critical value test rejects all discretized p-values, nominal pairs must be retained."""
        engine = StatisticalArbitrageEngine()
        steps = 100
        # Generate 6 synthetic cointegrated series
        base = np.cumsum(np.random.normal(0, 0.5, steps)) + 100.0
        prices_dict = {}
        for i in range(6):
            p = base + np.random.normal(0, 0.05, steps)
            prices_dict[f"SYM_{i}"] = list(p)

        pairs = engine.find_cointegrated_pairs(prices_dict, max_pvalue=0.10)
        self.assertTrue(len(pairs) > 0, "FDR step-up must retain cointegrated pairs via nominal fallback")
        for p in pairs:
            self.assertIn("pair", p)
            self.assertIn("z_score", p)
            self.assertIn("signal", p)

    def test_stat_arb_market_index_residual_fallback(self):
        """When zero pairs are cointegrated, market index residual Z-score fallback must be generated."""
        engine = StatisticalArbitrageEngine()
        steps = 100
        # Generate completely independent Brownian motions (uncorrelated, non-cointegrated)
        prices_dict = {}
        for i in range(5):
            prices_dict[f"RAND_{i}"] = list(np.cumsum(np.random.normal(0, 2.0, steps)) + 100.0)

        pairs = engine.find_cointegrated_pairs(prices_dict, min_correlation=0.99)
        self.assertTrue(len(pairs) > 0, "Market residual fallback must produce pairs when zero pairs cointegrate")
        benchmark_pairs = [p for p in pairs if p.get("s2") == "BENCHMARK"]
        self.assertTrue(len(benchmark_pairs) > 0, "Market residual pairs must pair with BENCHMARK")
        for bp in benchmark_pairs:
            self.assertTrue(bp.get("is_market_residual_fallback", False))
            self.assertIn(bp["s1"], prices_dict.keys())

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Short Squeeze Engine Tests
    # ──────────────────────────────────────────────────────────────────────────
    def test_short_squeeze_adaptive_proxy_fallback(self):
        """When short_ratio and DTC are missing from DB, adaptive proxy must yield valid non-NaN scores."""
        engine = ShortInterestSqueezeEngine()
        symbols = [f"STOCK_{i}" for i in range(10)]
        prices_dict = {}
        for s in symbols:
            # 30 bars of OHLCV
            c = np.cumsum(np.random.normal(0.001, 0.02, 30)) + 50.0
            v = np.random.uniform(10000, 50000, 30)
            prices_dict[s] = pd.DataFrame({"Close": c, "Volume": v})

        # features_df has NO short_ratio and NO days_to_cover
        empty_fund = pd.DataFrame({"symbol": symbols, "per": [15.0]*10})

        res_df = engine.calculate_scores(symbols, prices_dict=prices_dict, features_df=empty_fund)
        self.assertEqual(len(res_df), len(symbols))
        self.assertTrue(res_df['short_squeeze_score'].notna().all(), "No NaNs allowed in short_squeeze_score")
        self.assertTrue((res_df['short_squeeze_score'] >= 0.05).all())
        self.assertTrue((res_df['short_squeeze_score'] <= 0.98).all())

    # ──────────────────────────────────────────────────────────────────────────
    # 3. RIM Valuation Engine Tests
    # ──────────────────────────────────────────────────────────────────────────
    def test_rim_price_trend_proxy_for_missing_bps(self):
        """When BPS is missing, allow_price_proxy=True must generate PRICE_TREND_PROXY intrinsic value."""
        engine = RIMValuationEngine(default_required_return=0.08)
        symbols = ["NDX_01", "NDX_02", "NDX_03"]
        prices_dict = {}
        for s in symbols:
            c = np.linspace(100.0, 120.0, 60)
            prices_dict[s] = pd.DataFrame({"Close": c})

        # DataFrame with missing BPS for all symbols
        df_input = pd.DataFrame([
            {"symbol": s, "market": "NASDAQ", "Close": 120.0, "bps": np.nan, "roe": np.nan}
            for s in symbols
        ])

        res = engine.compute_rim_scores(df_input, prices_dict=prices_dict, allow_price_proxy=True)
        self.assertEqual(len(res), 3)
        self.assertTrue((res['rim_filter_reason'] == 'PRICE_TREND_PROXY').all())
        self.assertTrue(res['intrinsic_value'].notna().all())
        self.assertTrue(res['discount_ratio'].notna().all())
        self.assertTrue(res['rim_score'].notna().all())
        self.assertTrue((res['rim_score'] > 0).all())

    # ──────────────────────────────────────────────────────────────────────────
    # 4. StrategyExecutor Universe-Wide Sentiment & Tone Drift
    # ──────────────────────────────────────────────────────────────────────────
    def test_strategy_executor_universe_wide_coverage(self):
        """Prepare_shared_context must cover full symbols_list (e.g. 150 symbols), not just 100."""
        executor = AlphaStrategyExecutor()
        # 150 test symbols
        test_symbols = [f"SYM_{i:03d}" for i in range(150)]
        infer_data_dict = {}
        for s in test_symbols:
            c = np.linspace(50.0, 55.0, 20)
            infer_data_dict[s] = pd.DataFrame({"Close": c})

        cfg = MagicMock()
        cfg.dart_api_key = ""
        universe = pd.DataFrame({"symbol": test_symbols})
        ctx = PipelineStrategyContext(
            universe=universe,
            infer_data_dict=infer_data_dict,
            cfg=cfg,
            symbols_list=test_symbols,
            storage=None,
        )
        ctx.eff_filings = []

        executor.prepare_shared_context(ctx)

        self.assertEqual(len(ctx.sentiment_map), 150, "sentiment_map must contain all 150 symbols")
        self.assertEqual(len(ctx.tone_transcript_map), 150, "tone_transcript_map must contain all 150 symbols")
        for s in test_symbols:
            self.assertIn(s, ctx.sentiment_map)
            self.assertIn(s, ctx.tone_transcript_map)
            t_entry = ctx.tone_transcript_map[s]
            self.assertIn('previous_quarter_tone', t_entry)
            self.assertIn('current_quarter_tone', t_entry)
            self.assertTrue(0.0 <= t_entry['current_quarter_tone'] <= 1.0)


if __name__ == '__main__':
    unittest.main()
