"""
tests/test_adversarial_m1_distribution_sanity.py
Adversarial Stress Test Suite for Milestone 1 (Strategy Defect & Fallback Remediation).

Focus Areas:
1. Fallback scores centered around 0.50 (neutral distribution sanity).
2. Fallback scores preserve monotonic ranking with underlying signals.
3. Neutral baseline fill (0.50) in run_pipeline.py prevents NaN propagation into raw_scores and ensemble_scorer.
4. Execution speed checks to ensure fallbacks do not introduce performance bottlenecks.
"""

import time
import unittest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock
from scipy.stats import spearmanr

from src.core.stat_arb import StatisticalArbitrageEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.rim_valuation import RIMValuationEngine
from src.pipeline.strategy_executor import AlphaStrategyExecutor, PipelineStrategyContext
from src.ai.ensemble_scorer import EnsembleScoringEngine as EnsembleScorer
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


class TestAdversarialM1DistributionSanity(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)

    # ──────────────────────────────────────────────────────────────────────────
    # AREA 1: Fallback Scores Centering around 0.50 (Neutrality)
    # ──────────────────────────────────────────────────────────────────────────

    def test_01_stat_arb_neutral_equilibrium_centering(self):
        """Pairs with equilibrium Z-scores (|Z| < 1.2) must produce exactly 0.50 neutral scores."""
        equilibrium_pairs = [
            {"pair": ("SYM_A", "SYM_B"), "s1": "SYM_A", "s2": "SYM_B", "z_score": 0.00, "signal": "NEUTRAL"},
            {"pair": ("SYM_C", "SYM_D"), "s1": "SYM_C", "s2": "SYM_D", "z_score": 0.50, "signal": "NEUTRAL"},
            {"pair": ("SYM_E", "SYM_F"), "s1": "SYM_E", "s2": "SYM_F", "z_score": -0.80, "signal": "NEUTRAL"},
            {"pair": ("SYM_G", "SYM_H"), "s1": "SYM_G", "s2": "SYM_H", "z_score": 1.19, "signal": "NEUTRAL"},
        ]
        res_df = StatisticalArbitrageEngine.get_symbol_stat_arb_scores(equilibrium_pairs)
        self.assertFalse(res_df.empty)
        for _, row in res_df.iterrows():
            self.assertAlmostEqual(row['stat_arb_score'], 0.50, places=4,
                                   msg=f"Symbol {row['symbol']} did not receive neutral 0.50 score: got {row['stat_arb_score']}")

    def test_02_stat_arb_market_residual_neutral_fallback(self):
        """Market index residual fallback with small residual (|Z| < entry) must emit NEUTRAL and 0.50 score."""
        engine = StatisticalArbitrageEngine()
        steps = 60
        # Create series identical to market index (zero residual spread)
        market = np.cumsum(np.random.normal(0, 1.0, steps)) + 100.0
        prices_dict = {
            f"SYM_{i}": list(market + np.random.normal(0, 0.0001, steps))
            for i in range(4)
        }
        pairs = engine.find_cointegrated_pairs(prices_dict, min_correlation=0.999999)
        # Even if min_correlation is impossible, market residual fallback runs
        if not pairs:
            # force zero correlation so fallback is triggered
            pairs = engine.find_cointegrated_pairs(prices_dict, min_correlation=1.5)

        self.assertTrue(len(pairs) > 0, "Market residual fallback must produce pairs")
        res_df = StatisticalArbitrageEngine.get_symbol_stat_arb_scores(pairs)
        self.assertFalse(res_df.empty)
        # Check all symbols have valid non-NaN finite scores in [0.05, 0.98]
        self.assertTrue(res_df['stat_arb_score'].notna().all())
        self.assertTrue((res_df['stat_arb_score'] >= 0.05).all())
        self.assertTrue((res_df['stat_arb_score'] <= 0.98).all())

    def test_03_short_squeeze_flat_price_centering(self):
        """Microstructure squeeze proxy on flat price series must center around 0.50."""
        engine = ShortInterestSqueezeEngine()
        symbols = [f"FLAT_{i}" for i in range(20)]
        prices_dict = {}
        for s in symbols:
            # Completely flat price and constant volume
            prices_dict[s] = pd.DataFrame({
                "Close": [100.0] * 30,
                "Volume": [10000.0] * 30
            })
        empty_fund = pd.DataFrame({"symbol": symbols})
        res_df = engine.calculate_scores(symbols, prices_dict=prices_dict, features_df=empty_fund)
        self.assertEqual(len(res_df), len(symbols))
        self.assertTrue(res_df['short_squeeze_score'].notna().all())
        # For tied identical flat inputs, mean and median should be ~0.50
        mean_score = res_df['short_squeeze_score'].mean()
        self.assertAlmostEqual(mean_score, 0.50, delta=0.03,
                               msg=f"Mean score on flat series was {mean_score}, expected ~0.50")

    def test_04_short_squeeze_missing_price_centering(self):
        """When prices_dict has no data at all, short squeeze fallback must return exactly 0.50."""
        engine = ShortInterestSqueezeEngine()
        symbols = ["NO_DATA_1", "NO_DATA_2", "NO_DATA_3"]
        empty_fund = pd.DataFrame({"symbol": symbols})
        res_df = engine.calculate_scores(symbols, prices_dict={}, features_df=empty_fund)
        self.assertEqual(len(res_df), 3)
        for _, row in res_df.iterrows():
            self.assertAlmostEqual(row['short_squeeze_score'], 0.50, places=4)

    def test_05_rim_single_stock_and_flat_proxy_centering(self):
        """Single stock RIM with missing BPS must evaluate to exactly 0.50."""
        engine = RIMValuationEngine(default_required_return=0.08)
        prices_dict = {"SINGLE": pd.DataFrame({"Close": [50.0] * 30})}
        df_input = pd.DataFrame([{"symbol": "SINGLE", "market": "NASDAQ", "Close": 50.0, "bps": np.nan, "roe": np.nan}])
        res = engine.compute_rim_scores(df_input, prices_dict=prices_dict, allow_price_proxy=True)
        self.assertEqual(len(res), 1)
        self.assertAlmostEqual(float(res['rim_score'].iloc[0]), 0.50, places=2)

    def test_06_sentiment_and_tone_flat_momentum_centering(self):
        """Technical momentum proxy for flat price series must evaluate to exactly 0.50."""
        executor = AlphaStrategyExecutor()
        symbols = ["FLAT_SYM_1", "FLAT_SYM_2"]
        infer_data_dict = {
            s: pd.DataFrame({"Close": [100.0] * 20}) for s in symbols
        }
        ctx = PipelineStrategyContext(
            universe=pd.DataFrame({"symbol": symbols}),
            infer_data_dict=infer_data_dict,
            cfg=MagicMock(dart_api_key=""),
            symbols_list=symbols,
            storage=None
        )
        ctx.eff_filings = []
        executor.prepare_shared_context(ctx)

        for s in symbols:
            self.assertAlmostEqual(ctx.sentiment_map[s], 0.50, places=4,
                                   msg=f"Sentiment for flat price was {ctx.sentiment_map[s]}, expected 0.50")
            tone = ctx.tone_transcript_map[s]
            self.assertAlmostEqual(tone['previous_quarter_tone'], 0.50, places=4)
            self.assertAlmostEqual(tone['current_quarter_tone'], 0.50, places=4)

    # ──────────────────────────────────────────────────────────────────────────
    # AREA 2: Monotonic Ranking Preservation with Underlying Signals
    # ──────────────────────────────────────────────────────────────────────────

    def test_07_stat_arb_monotonic_ranking_with_zscore(self):
        """As spread Z-score increases from negative (underpriced) to positive (overpriced),
        stat_arb_score must monotonically decrease (higher expected return for long undervalued stocks)."""
        z_scores = [-3.0, -2.5, -2.0, -1.5, 0.0, 1.5, 2.0, 2.5, 3.0]
        pairs = []
        for i, z in enumerate(z_scores):
            sym = f"SYM_{i:02d}"
            sig = f"LONG_{sym}" if z <= -1.2 else (f"SHORT_{sym}" if z >= 1.2 else "NEUTRAL")
            pairs.append({
                "pair": (sym, "BENCHMARK"),
                "s1": sym,
                "s2": "BENCHMARK",
                "z_score": z,
                "signal": sig,
            })
        res_df = StatisticalArbitrageEngine.get_symbol_stat_arb_scores(pairs)
        self.assertEqual(len(res_df), len(z_scores))
        merged = pd.merge(pd.DataFrame({"symbol": [f"SYM_{i:02d}" for i in range(len(z_scores))], "z_score": z_scores}),
                          res_df, on="symbol")

        # Spearman rank correlation between z_score and stat_arb_score must be strongly negative (-1.0)
        corr, _ = spearmanr(merged['z_score'], merged['stat_arb_score'])
        self.assertAlmostEqual(corr, -1.0, places=2,
                               msg=f"Stat-Arb score is not monotonically decreasing with Z-score: Spearman r = {corr}")

    def test_08_short_squeeze_monotonic_ranking_with_5d_momentum(self):
        """Microstructure squeeze proxy must be monotonically increasing with 5d price momentum."""
        engine = ShortInterestSqueezeEngine()
        n_stocks = 12
        symbols = [f"MOM_{i:02d}" for i in range(n_stocks)]
        # Strictly increasing 5d returns: -10% to +20%
        ret_5ds = np.linspace(-0.10, 0.20, n_stocks)
        prices_dict = {}
        for s, r5 in zip(symbols, ret_5ds):
            # 30 bars with constant price then step change in last 5 bars
            p = [100.0] * 25 + [100.0 * (1.0 + r5 * (step / 5.0)) for step in range(1, 6)]
            prices_dict[s] = pd.DataFrame({"Close": p, "Volume": [20000.0] * 30})

        empty_fund = pd.DataFrame({"symbol": symbols})
        res_df = engine.calculate_scores(symbols, prices_dict=prices_dict, features_df=empty_fund)
        merged = pd.merge(pd.DataFrame({"symbol": symbols, "ret_5d": ret_5ds}), res_df, on="symbol")

        corr, _ = spearmanr(merged['ret_5d'], merged['short_squeeze_score'])
        self.assertGreaterEqual(corr, 0.95,
                                msg=f"Short squeeze score is not monotonically increasing with 5D return: Spearman r = {corr}")

    def test_09_rim_monotonic_ranking_with_price_discount(self):
        """RIM price-trend proxy must assign higher scores to stocks with larger discounts (P < SMA)."""
        engine = RIMValuationEngine(default_required_return=0.08)
        n_stocks = 10
        symbols = [f"RIM_PROXY_{i:02d}" for i in range(n_stocks)]
        # Price ranging from 50 to 140 with SMA constant at 100
        # Discount ratio (SMA*1.05 - P) / P: strictly decreasing as P increases
        prices = np.linspace(50.0, 140.0, n_stocks)
        prices_dict = {}
        for s, p_last in zip(symbols, prices):
            c_hist = [100.0] * 29 + [p_last]
            prices_dict[s] = pd.DataFrame({"Close": c_hist})

        df_input = pd.DataFrame([
            {"symbol": s, "market": "NASDAQ", "Close": p_last, "bps": np.nan, "roe": np.nan}
            for s, p_last in zip(symbols, prices)
        ])

        res = engine.compute_rim_scores(df_input, prices_dict=prices_dict, allow_price_proxy=True)
        merged = pd.merge(pd.DataFrame({"symbol": symbols, "price": prices}), res, on="symbol")

        # More discounted stocks (lower price relative to SMA 100) should have HIGHER rim_score
        corr, _ = spearmanr(merged['price'], merged['rim_score'])
        self.assertLessEqual(corr, -0.95,
                             msg=f"RIM score did not decrease monotonically with price: Spearman r = {corr}")

    def test_10_sentiment_monotonic_ranking_with_14d_momentum(self):
        """Sentiment proxy must strictly monotonically increase with 14-day price momentum."""
        executor = AlphaStrategyExecutor()
        n_stocks = 10
        symbols = [f"MOM14_{i:02d}" for i in range(n_stocks)]
        returns_14 = np.linspace(-0.25, 0.25, n_stocks)
        infer_data_dict = {}
        for s, r14 in zip(symbols, returns_14):
            # 20 bars with start at 100 and last bar at 100 * (1 + r14)
            prices = [100.0] * 6 + list(np.linspace(100.0, 100.0 * (1.0 + r14), 14))
            infer_data_dict[s] = pd.DataFrame({"Close": prices})

        ctx = PipelineStrategyContext(
            universe=pd.DataFrame({"symbol": symbols}),
            infer_data_dict=infer_data_dict,
            cfg=MagicMock(dart_api_key=""),
            symbols_list=symbols,
            storage=None
        )
        ctx.eff_filings = []
        executor.prepare_shared_context(ctx)

        scores = [ctx.sentiment_map[s] for s in symbols]
        corr, _ = spearmanr(returns_14, scores)
        self.assertGreaterEqual(corr, 0.98,
                                msg=f"Sentiment proxy is not monotonic with 14d return: Spearman r = {corr}")

    # ──────────────────────────────────────────────────────────────────────────
    # AREA 3: Pipeline Neutral Baseline Fill Prevents NaN Propagation
    # ──────────────────────────────────────────────────────────────────────────

    def test_11_run_pipeline_baseline_fill_eliminates_nans_in_ensemble(self):
        """Verify that run_pipeline.py baseline alignment fills absent symbols with 0.50
        and completely prevents NaN propagation into raw_scores and EnsembleScorer."""
        n_universe = 500
        all_symbols = [f"SYM_{i:04d}" for i in range(n_universe)]
        universe = pd.DataFrame({"symbol": all_symbols, "market": ["SP500"] * n_universe})

        # Simulate sparse activations
        # 1. VCP rule: only 8 stocks active
        vcp_results = [{'symbol': all_symbols[i], 'vcp_score': 85.0 + i} for i in range(8)]

        # 2. Lead-lag: only 12 stocks active
        lead_lag_df = pd.DataFrame([
            {'symbol': all_symbols[i], 'll_score': 0.70 + i * 0.01}
            for i in range(12)
        ])

        # 3. Stat-arb: only 6 stocks active
        stat_arb_df = pd.DataFrame([
            {'symbol': all_symbols[i], 'stat_arb_score': 0.65 + i * 0.02, 'long_only_mode': False}
            for i in range(6)
        ])

        # Execute EXACT run_pipeline.py baseline logic (lines 3130-3185):
        all_u_symbols = universe['symbol'].astype(str).tolist()

        # Align vcp_rule
        vcp_dict = {}
        if vcp_results:
            if isinstance(vcp_results, list):
                for r in vcp_results:
                    if isinstance(r, dict) and 'symbol' in r:
                        s_val = r.get('vcp_score', 50.0)
                        try:
                            s_float = float(s_val) / 100.0 if float(s_val) > 1.0 else float(s_val)
                            vcp_dict[str(r['symbol'])] = float(np.clip(s_float, 0.05, 0.98))
                        except (ValueError, TypeError):
                            vcp_dict[str(r['symbol'])] = 0.50
        vcp_rule_df = pd.DataFrame([
            {'symbol': s, 'vcp_rule_score': vcp_dict.get(s, 0.50)}
            for s in all_u_symbols
        ])

        # Align lead_lag
        if lead_lag_df is None or lead_lag_df.empty:
            lead_lag_df = pd.DataFrame([{'symbol': s, 'll_score': 0.50} for s in all_u_symbols])
        else:
            ll_col = 'll_score' if 'll_score' in lead_lag_df.columns else ('lead_lag_score' if 'lead_lag_score' in lead_lag_df.columns else None)
            if ll_col and ll_col != 'll_score':
                lead_lag_df = lead_lag_df.rename(columns={ll_col: 'll_score'})
            if 'll_score' not in lead_lag_df.columns:
                lead_lag_df['ll_score'] = 0.50
            ll_dict = dict(zip(lead_lag_df['symbol'].astype(str), pd.to_numeric(lead_lag_df['ll_score'], errors='coerce').fillna(0.50)))
            lead_lag_df = pd.DataFrame([
                {'symbol': s, 'll_score': float(np.clip(ll_dict.get(s, 0.50), 0.05, 0.98))}
                for s in all_u_symbols
            ])

        # Align stat_arb
        if stat_arb_df is None or stat_arb_df.empty:
            stat_arb_df = pd.DataFrame([{'symbol': s, 'stat_arb_score': 0.50, 'long_only_mode': False} for s in all_u_symbols])
        else:
            sa_dict = dict(zip(stat_arb_df['symbol'].astype(str), pd.to_numeric(stat_arb_df['stat_arb_score'], errors='coerce').fillna(0.50)))
            stat_arb_df = pd.DataFrame([
                {'symbol': s, 'stat_arb_score': float(np.clip(sa_dict.get(s, 0.50), 0.05, 0.98)), 'long_only_mode': False}
                for s in all_u_symbols
            ])

        # Assert all 3 DataFrames have 500 rows and 0 NaNs
        self.assertEqual(len(vcp_rule_df), 500)
        self.assertEqual(len(lead_lag_df), 500)
        self.assertEqual(len(stat_arb_df), 500)
        self.assertTrue(vcp_rule_df['vcp_rule_score'].notna().all())
        self.assertTrue(lead_lag_df['ll_score'].notna().all())
        self.assertTrue(stat_arb_df['stat_arb_score'].notna().all())

        # Assert non-active symbols got neutral 0.50
        self.assertEqual(vcp_rule_df.loc[vcp_rule_df['symbol'] == all_symbols[50], 'vcp_rule_score'].iloc[0], 0.50)
        self.assertEqual(lead_lag_df.loc[lead_lag_df['symbol'] == all_symbols[50], 'll_score'].iloc[0], 0.50)
        self.assertEqual(stat_arb_df.loc[stat_arb_df['symbol'] == all_symbols[50], 'stat_arb_score'].iloc[0], 0.50)

        # Assert active symbols preserved their signals
        self.assertGreater(vcp_rule_df.loc[vcp_rule_df['symbol'] == all_symbols[0], 'vcp_rule_score'].iloc[0], 0.80)
        self.assertGreater(lead_lag_df.loc[lead_lag_df['symbol'] == all_symbols[0], 'll_score'].iloc[0], 0.65)
        self.assertGreater(stat_arb_df.loc[stat_arb_df['symbol'] == all_symbols[0], 'stat_arb_score'].iloc[0], 0.60)

        # Feed into EnsembleScorer and verify raw_scores and final ensemble_df
        scorer = EnsembleScorer()
        reg_df = pd.DataFrame({'symbol': all_symbols, 'expected_return': [0.05] * n_universe, 'market': ['SP500'] * n_universe})
        ensemble_df = scorer.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            regression_df=reg_df,
            vcp_rule_df=vcp_rule_df,
            lead_lag_df=lead_lag_df,
            stat_arb_df=stat_arb_df,
            target_horizon=20,
            version=15
        )

        self.assertFalse(ensemble_df.empty)
        self.assertEqual(len(ensemble_df), n_universe)
        self.assertTrue(ensemble_df['ensemble_score'].notna().all())
        self.assertTrue(np.isfinite(ensemble_df['ensemble_score']).all())

        # Check raw_scores preservation
        raw_scores = getattr(scorer, 'raw_scores', None)
        self.assertIsNotNone(raw_scores)
        self.assertEqual(len(raw_scores), n_universe)
        self.assertTrue(raw_scores['vcp_rule_score'].notna().all())
        self.assertTrue(raw_scores['ll_score'].notna().all())
        self.assertTrue(raw_scores['stat_arb_score'].notna().all())

        # Check Coverage Analyzer: coverage must be 100.0% for these 3 strategies
        analyzer = StrategyCoverageAnalyzer()
        report = analyzer.analyze_coverage(ensemble_df, raw_scores=raw_scores)
        metrics = report.get('strategies', report)
        self.assertIn('vcp_rule', metrics)
        self.assertIn('lead_lag', metrics)
        self.assertIn('stat_arb', metrics)
        self.assertEqual(metrics['vcp_rule']['valid_count'], n_universe)
        self.assertEqual(metrics['lead_lag']['valid_count'], n_universe)
        self.assertEqual(metrics['stat_arb']['valid_count'], n_universe)
        self.assertAlmostEqual(metrics['vcp_rule']['coverage_pct'], 100.0, places=1)
        self.assertAlmostEqual(metrics['lead_lag']['coverage_pct'], 100.0, places=1)
        self.assertAlmostEqual(metrics['stat_arb']['coverage_pct'], 100.0, places=1)

    # ──────────────────────────────────────────────────────────────────────────
    # AREA 4: Execution Speed & Scalability Checks
    # ──────────────────────────────────────────────────────────────────────────

    def test_12_stat_arb_execution_speed_benchmark(self):
        """Stat-Arb pair scanning + market residual fallback for 100 stocks must execute in < 3.0s."""
        engine = StatisticalArbitrageEngine()
        steps = 60
        n_stocks = 100
        symbols = [f"STK_{i:03d}" for i in range(n_stocks)]
        # Generate random walk prices
        prices_dict = {
            s: list(np.cumsum(np.random.normal(0, 1.0, steps)) + 100.0)
            for s in symbols
        }
        t0 = time.perf_counter()
        pairs = engine.find_cointegrated_pairs(prices_dict, max_pvalue=0.05, min_correlation=0.90)
        res_df = StatisticalArbitrageEngine.get_symbol_stat_arb_scores(pairs)
        elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 3.0,
                        msg=f"Stat-Arb execution took {elapsed:.2f}s, exceeding 3.0s benchmark limit")
        print(f"\n[BENCHMARK] Stat-Arb 100-stock scanning + fallback completed in {elapsed:.3f}s ({len(pairs)} pairs found)")

    def test_13_short_squeeze_execution_speed_benchmark(self):
        """Short Squeeze adaptive proxy for 500 stocks must execute in < 0.5s."""
        engine = ShortInterestSqueezeEngine()
        n_stocks = 500
        symbols = [f"SQ_{i:04d}" for i in range(n_stocks)]
        prices_dict = {
            s: pd.DataFrame({
                "Close": np.random.uniform(50, 150, 30),
                "Volume": np.random.uniform(10000, 100000, 30)
            })
            for s in symbols
        }
        empty_fund = pd.DataFrame({"symbol": symbols})

        t0 = time.perf_counter()
        res_df = engine.calculate_scores(symbols, prices_dict=prices_dict, features_df=empty_fund)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(res_df), n_stocks)
        self.assertLess(elapsed, 0.5,
                        msg=f"Short Squeeze proxy took {elapsed:.2f}s, exceeding 0.5s benchmark limit")
        print(f"[BENCHMARK] Short Squeeze proxy 500-stock calculation completed in {elapsed:.3f}s ({n_stocks/elapsed:.1f} sym/s)")

    def test_14_rim_valuation_execution_speed_benchmark(self):
        """RIM Valuation with price-trend proxy for 500 stocks must execute in < 0.5s."""
        engine = RIMValuationEngine(default_required_return=0.08)
        n_stocks = 500
        symbols = [f"RIM_{i:04d}" for i in range(n_stocks)]
        prices_dict = {
            s: pd.DataFrame({"Close": np.random.uniform(50, 150, 30)})
            for s in symbols
        }
        df_input = pd.DataFrame([
            {"symbol": s, "market": "NASDAQ", "Close": 100.0, "bps": np.nan, "roe": np.nan}
            for s in symbols
        ])

        t0 = time.perf_counter()
        res_df = engine.compute_rim_scores(df_input, prices_dict=prices_dict, allow_price_proxy=True)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(res_df), n_stocks)
        self.assertLess(elapsed, 0.5,
                        msg=f"RIM Valuation proxy took {elapsed:.2f}s, exceeding 0.5s benchmark limit")
        print(f"[BENCHMARK] RIM Valuation proxy 500-stock calculation completed in {elapsed:.3f}s ({n_stocks/elapsed:.1f} sym/s)")

    def test_15_strategy_executor_speed_benchmark(self):
        """StrategyExecutor shared context preparation for 500 stocks must execute in < 1.0s."""
        executor = AlphaStrategyExecutor()
        n_stocks = 500
        symbols = [f"EXEC_{i:04d}" for i in range(n_stocks)]
        infer_data_dict = {
            s: pd.DataFrame({"Close": np.random.uniform(50, 150, 20)})
            for s in symbols
        }
        ctx = PipelineStrategyContext(
            universe=pd.DataFrame({"symbol": symbols}),
            infer_data_dict=infer_data_dict,
            cfg=MagicMock(dart_api_key=""),
            symbols_list=symbols,
            storage=None
        )
        ctx.eff_filings = []

        t0 = time.perf_counter()
        executor.prepare_shared_context(ctx)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(ctx.sentiment_map), n_stocks)
        self.assertEqual(len(ctx.tone_transcript_map), n_stocks)
        self.assertLess(elapsed, 1.0,
                        msg=f"StrategyExecutor shared context took {elapsed:.2f}s, exceeding 1.0s benchmark limit")
        print(f"[BENCHMARK] StrategyExecutor 500-stock shared context completed in {elapsed:.3f}s ({n_stocks/elapsed:.1f} sym/s)")

    def test_16_pipeline_full_universe_alignment_speed_benchmark(self):
        """Baseline alignment and EnsembleScoringEngine merge for 2000 stocks (Russell 2000) must execute in < 5.0s."""
        n_stocks = 2000
        all_symbols = [f"R2K_{i:04d}" for i in range(n_stocks)]
        universe = pd.DataFrame({"symbol": all_symbols, "market": ["RUSSELL2000"] * n_stocks})

        vcp_results = [{'symbol': all_symbols[i], 'vcp_score': 80.0} for i in range(15)]
        lead_lag_df = pd.DataFrame([{'symbol': all_symbols[i], 'll_score': 0.75} for i in range(20)])
        stat_arb_df = pd.DataFrame([{'symbol': all_symbols[i], 'stat_arb_score': 0.65, 'long_only_mode': False} for i in range(10)])

        t0 = time.perf_counter()

        # Baseline alignment
        all_u_symbols = universe['symbol'].astype(str).tolist()
        vcp_dict = {str(r['symbol']): float(r['vcp_score'])/100.0 for r in vcp_results}
        vcp_rule_df = pd.DataFrame([{'symbol': s, 'vcp_rule_score': vcp_dict.get(s, 0.50)} for s in all_u_symbols])

        ll_dict = dict(zip(lead_lag_df['symbol'].astype(str), lead_lag_df['ll_score']))
        lead_lag_df_aligned = pd.DataFrame([{'symbol': s, 'll_score': ll_dict.get(s, 0.50)} for s in all_u_symbols])

        sa_dict = dict(zip(stat_arb_df['symbol'].astype(str), stat_arb_df['stat_arb_score']))
        stat_arb_df_aligned = pd.DataFrame([{'symbol': s, 'stat_arb_score': sa_dict.get(s, 0.50), 'long_only_mode': False} for s in all_u_symbols])

        scorer = EnsembleScorer()
        reg_df = pd.DataFrame({'symbol': all_symbols, 'expected_return': [0.05] * n_stocks, 'market': ['RUSSELL2000'] * n_stocks})
        ensemble_df = scorer.calculate_ensemble_score(
            regime='BULL_LOW_VOL',
            regression_df=reg_df,
            vcp_rule_df=vcp_rule_df,
            lead_lag_df=lead_lag_df_aligned,
            stat_arb_df=stat_arb_df_aligned,
            target_horizon=20,
            version=15
        )
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(ensemble_df), n_stocks)
        self.assertLess(elapsed, 5.0,
                        msg=f"Pipeline 2000-stock baseline alignment + ensemble took {elapsed:.2f}s, exceeding 5.0s limit")
        print(f"[BENCHMARK] Full 2000-stock universe alignment + ensemble scoring completed in {elapsed:.3f}s ({n_stocks/elapsed:.1f} sym/s)")


if __name__ == '__main__':
    unittest.main()
