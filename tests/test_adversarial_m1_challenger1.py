"""
Adversarial Stress Testing & Empirical Verification Suite for Milestone 1.
Author: Challenger 1 (teamwork_preview_challenger)

Targets under empirical stress testing:
1. StatArbEngine (StatisticalArbitrageEngine):
   - Empty universe
   - All-identical price series
   - Zero-variance series (flat prices)
   - Single symbol universe
   - High correlation without cointegration
   - Extreme Z-scores (|Z| > 10)
2. ShortInterestSqueezeEngine:
   - Empty fundamentals dict
   - All-NaN fundamentals
   - Zero volume
   - Extreme negative momentum (-99% collapse)
   - Extreme volatility (1000x swings / high variance)
   - Boundedness in [0.0, 1.0] and absence of NaNs
3. RIMValuationEngine:
   - Missing BPS
   - Negative BPS (capital impairment)
   - Price column casing ('Close', 'close', 'CLOSE', 'price')
   - Flat price history
   - Fallback validity without crashes
4. AlphaStrategyExecutor:
   - Universe sizes > 100 (e.g. 150, 300) without 100-symbol slicing truncation
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest

# Ensure repo paths are in sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "trading_system"))
sys.path.insert(0, str(root_dir))

from src.core.stat_arb import StatisticalArbitrageEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.rim_valuation import RIMValuationEngine
from src.pipeline.strategy_executor import AlphaStrategyExecutor, PipelineStrategyContext


# =============================================================================
# 1. StatArbEngine Adversarial Stress Suite
# =============================================================================
class TestStatArbAdversarial:

    def setup_method(self):
        np.random.seed(42)
        self.engine = StatisticalArbitrageEngine()

    def test_stat_arb_empty_universe(self):
        """Stress: Empty universe must return valid empty DataFrame without exception."""
        # Test compute_scores
        res = self.engine.compute_scores(prices_dict={})
        assert isinstance(res, pd.DataFrame)
        assert "symbol" in res.columns
        assert "stat_arb_score" in res.columns
        assert len(res) == 0

        # Test find_cointegrated_pairs
        pairs = self.engine.find_cointegrated_pairs(prices_dict={})
        assert isinstance(pairs, list)
        assert len(pairs) == 0

        # Test get_symbol_stat_arb_scores
        scores_df = self.engine.get_symbol_stat_arb_scores(found_pairs=[])
        assert isinstance(scores_df, pd.DataFrame)
        assert len(scores_df) == 0

    def test_stat_arb_single_symbol(self):
        """Stress: Universe with a single symbol cannot cointegrate but must not crash."""
        p = np.linspace(100.0, 150.0, 60)
        prices_dict = {"SYM_ONLY": pd.DataFrame({"Close": p})}

        pairs = self.engine.find_cointegrated_pairs(prices_dict)
        assert pairs == []

        res = self.engine.compute_scores(prices_dict)
        assert isinstance(res, pd.DataFrame)
        assert len(res) == 1
        assert res.iloc[0]["symbol"] == "SYM_ONLY"
        assert res.iloc[0]["stat_arb_score"] == pytest.approx(0.50, abs=1e-3)
        assert not np.isnan(res.iloc[0]["stat_arb_score"])

    def test_stat_arb_all_identical_price_series(self):
        """Stress: Multiple symbols with 100% identical price series (spread variance = 0)."""
        p = np.cumsum(np.random.normal(0.001, 0.02, 100)) + 100.0
        symbols = [f"IDENT_{i}" for i in range(5)]
        prices_dict = {s: pd.DataFrame({"Close": p.copy()}) for s in symbols}

        # Spread std will be 0.0, should skip without divide-by-zero or crash
        pairs = self.engine.find_cointegrated_pairs(prices_dict)
        assert isinstance(pairs, list)

        # All symbols must be scored at neutral 0.50
        res = self.engine.compute_scores(prices_dict)
        assert len(res) == 5
        for s in symbols:
            s_row = res[res["symbol"] == s]
            assert not s_row.empty
            score = float(s_row.iloc[0]["stat_arb_score"])
            assert score == pytest.approx(0.50, abs=1e-2)
            assert np.isfinite(score)

    def test_stat_arb_zero_variance_series(self):
        """Stress: Symbols with completely flat prices (zero variance: std = 0)."""
        symbols = [f"FLAT_{i}" for i in range(4)]
        prices_dict = {s: pd.DataFrame({"Close": np.full(80, 100.0)}) for s in symbols}

        # Zero variance should be handled safely by stds = np.where(stds < 1e-8, 1e-6, stds)
        pairs = self.engine.find_cointegrated_pairs(prices_dict)
        assert isinstance(pairs, list)

        res = self.engine.compute_scores(prices_dict)
        assert len(res) == 4
        for _, row in res.iterrows():
            score = float(row["stat_arb_score"])
            assert score == pytest.approx(0.50, abs=1e-2)
            assert not np.isnan(score)
            assert not np.isinf(score)

    def test_stat_arb_high_correlation_without_cointegration(self):
        """Stress: Highly correlated series with non-stationary wandering spread (corr > 0.95, p > 0.20)."""
        t = np.arange(120)
        # Correlated trends + non-stationary drift
        s1 = 100.0 + 0.5 * t + np.cumsum(np.random.normal(0, 0.2, 120))
        s2 = 100.0 + 0.5 * t + np.cumsum(np.random.normal(0, 1.5, 120))  # Diverging random walk

        prices_dict = {
            "SERIES_1": pd.DataFrame({"Close": s1}),
            "SERIES_2": pd.DataFrame({"Close": s2}),
        }

        # Run pair finding and scoring
        res = self.engine.compute_scores(prices_dict)
        assert len(res) == 2
        for _, row in res.iterrows():
            score = float(row["stat_arb_score"])
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.98

    def test_stat_arb_extreme_z_scores(self):
        """Stress: Synthetic pairs with extreme Z-scores (|Z| > 10) must remain strictly clamped in [0.05, 0.98]."""
        extreme_pairs = [
            {"pair": ("SYM_POS_EXT", "SYM_B"), "s1": "SYM_POS_EXT", "s2": "SYM_B", "z_score": 50.0, "signal": "SHORT_SYM_POS_EXT_LONG_SYM_B", "half_life": 5.0},
            {"pair": ("SYM_NEG_EXT", "SYM_B"), "s1": "SYM_NEG_EXT", "s2": "SYM_B", "z_score": -100.0, "signal": "LONG_SYM_NEG_EXT_SHORT_SYM_B", "half_life": 5.0},
            {"pair": ("SYM_STOP_LOSS", "SYM_B"), "s1": "SYM_STOP_LOSS", "s2": "SYM_B", "z_score": 15.0, "signal": "STOP_LOSS_NEUTRAL", "half_life": 5.0},
            {"pair": ("SYM_BENCH_LONG", "BENCHMARK"), "s1": "SYM_BENCH_LONG", "s2": "BENCHMARK", "z_score": -25.0, "signal": "LONG_SPREAD", "half_life": 5.0},
            {"pair": ("SYM_BENCH_SHORT", "BENCHMARK"), "s1": "SYM_BENCH_SHORT", "s2": "BENCHMARK", "z_score": 35.0, "signal": "SHORT_SPREAD", "half_life": 5.0},
        ]
        res = self.engine.get_symbol_stat_arb_scores(extreme_pairs)
        assert not res.empty
        for _, row in res.iterrows():
            score = float(row["stat_arb_score"])
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.98
            assert not np.isnan(score)


# =============================================================================
# 2. ShortInterestSqueezeEngine Adversarial Stress Suite
# =============================================================================
class TestShortInterestSqueezeAdversarial:

    def setup_method(self):
        np.random.seed(42)
        self.engine = ShortInterestSqueezeEngine()

    def test_short_squeeze_empty_fundamentals_dict(self):
        """Stress: Empty fundamentals dict must activate adaptive microstructure proxy without NaNs."""
        symbols = ["SYM_1", "SYM_2", "SYM_3"]
        prices_dict = {
            s: pd.DataFrame({
                "Close": np.linspace(100.0, 110.0, 30),
                "Volume": np.full(30, 10000.0),
            }) for s in symbols
        }
        res = self.engine.calculate_scores(symbols=symbols, prices_dict=prices_dict, features_df={})
        assert len(res) == 3
        assert res["short_squeeze_score"].notna().all()
        assert ((res["short_squeeze_score"] >= 0.05) & (res["short_squeeze_score"] <= 0.98)).all()

    def test_short_squeeze_all_nan_fundamentals(self):
        """Stress: Fundamentals where all short metrics are NaN must activate proxy."""
        symbols = [f"NAN_SYM_{i}" for i in range(5)]
        nan_fund = pd.DataFrame({
            "symbol": symbols,
            "short_ratio": [np.nan] * 5,
            "days_to_cover": [np.nan] * 5,
            "short_pct": [np.nan] * 5,
        })
        prices_dict = {
            s: pd.DataFrame({
                "Close": np.cumsum(np.random.normal(0, 1, 40)) + 50.0,
                "Volume": np.random.uniform(5000, 20000, 40),
            }) for s in symbols
        }
        res = self.engine.calculate_scores(symbols=symbols, prices_dict=prices_dict, features_df=nan_fund)
        assert len(res) == 5
        assert res["short_squeeze_score"].notna().all()
        assert not res["short_squeeze_score"].isna().any()

    def test_short_squeeze_zero_volume(self):
        """Stress: Zero volume history across all timestamps must not trigger ZeroDivisionError."""
        symbols = ["ZERO_VOL_1", "ZERO_VOL_2"]
        prices_dict = {
            s: pd.DataFrame({
                "Close": np.linspace(50.0, 60.0, 25),
                "Volume": np.zeros(25),  # 0 volume
            }) for s in symbols
        }
        res = self.engine.calculate_scores(symbols=symbols, prices_dict=prices_dict, features_df=None)
        assert len(res) == 2
        for _, row in res.iterrows():
            score = float(row["short_squeeze_score"])
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.98

    def test_short_squeeze_negative_momentum(self):
        """Stress: Extreme negative price collapse (-90% drop) must produce valid bounded scores."""
        symbols = ["COLLAPSE_1", "COLLAPSE_2"]
        prices_dict = {
            s: pd.DataFrame({
                "Close": np.linspace(100.0, 10.0, 30),  # -90% drop
                "Volume": np.full(30, 50000.0),
            }) for s in symbols
        }
        # Explicit high short interest but falling knife
        fund_data = pd.DataFrame({
            "symbol": symbols,
            "short_ratio": [0.35, 0.40],
            "days_to_cover": [10.0, 12.0],
        })
        res = self.engine.calculate_scores(symbols=symbols, prices_dict=prices_dict, features_df=fund_data)
        assert len(res) == 2
        for _, row in res.iterrows():
            score = float(row["short_squeeze_score"])
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.98

    def test_short_squeeze_extreme_volatility(self):
        """Stress: Extreme price jumps (1000x swings) and NaN returns."""
        symbols = ["WILD_1", "WILD_2"]
        prices = [10.0, 10000.0, 5.0, 8000.0, 2.0, 9000.0, 1.0] * 4
        prices_dict = {
            s: pd.DataFrame({
                "Close": np.array(prices, dtype=float),
                "Volume": np.full(len(prices), 10000.0),
            }) for s in symbols
        }
        res = self.engine.calculate_scores(symbols=symbols, prices_dict=prices_dict, features_df=None)
        assert len(res) == 2
        for _, row in res.iterrows():
            score = float(row["short_squeeze_score"])
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.98

    def test_short_squeeze_comprehensive_boundary_grid(self):
        """Stress: Multi-condition grid verify scores are strictly bounded in [0.0, 1.0] and never NaN."""
        symbols = [f"GRID_{i}" for i in range(20)]
        prices_dict = {}
        for i, s in enumerate(symbols):
            if i % 4 == 0:
                p = np.full(30, 50.0)  # flat
                v = np.zeros(30)
            elif i % 4 == 1:
                p = np.linspace(10.0, 100.0, 30)  # +900%
                v = np.random.uniform(1000, 5000, 30)
            elif i % 4 == 2:
                p = np.linspace(100.0, 1.0, 30)  # -99%
                v = np.random.uniform(1000, 5000, 30)
            else:
                p = np.cumsum(np.random.normal(0, 2, 30)) + 50.0
                v = np.random.uniform(10000, 50000, 30)
            prices_dict[s] = pd.DataFrame({"Close": p, "Volume": v})

        res = self.engine.calculate_scores(symbols=symbols, prices_dict=prices_dict, features_df=None)
        assert len(res) == 20
        assert res["short_squeeze_score"].notna().all()
        assert (res["short_squeeze_score"] >= 0.0).all()
        assert (res["short_squeeze_score"] <= 1.0).all()


# =============================================================================
# 3. RIMValuationEngine Adversarial Stress Suite
# =============================================================================
class TestRIMValuationAdversarial:

    def setup_method(self):
        self.engine = RIMValuationEngine(default_required_return=0.08)

    def test_rim_missing_bps_generates_proxy(self):
        """Stress: Missing BPS should activate price-trend proxy when allow_price_proxy=True."""
        symbols = ["MISS_BPS_1", "MISS_BPS_2"]
        prices_dict = {
            s: pd.DataFrame({"Close": np.linspace(100.0, 120.0, 50)}) for s in symbols
        }
        df_input = pd.DataFrame([
            {"symbol": s, "market": "NASDAQ", "Close": 120.0, "bps": np.nan, "roe": np.nan}
            for s in symbols
        ])
        res = self.engine.compute_rim_scores(df_input, prices_dict=prices_dict, allow_price_proxy=True)
        assert len(res) == 2
        assert (res["rim_filter_reason"] == "PRICE_TREND_PROXY").all()
        assert res["rim_score"].notna().all()
        assert ((res["rim_score"] >= 0.05) & (res["rim_score"] <= 0.98)).all()

    def test_rim_negative_bps_capital_impairment(self):
        """Stress: Negative BPS (capital impairment) must be defensively invalidated without crashing."""
        symbols = ["NEG_BPS_1", "NEG_BPS_2"]
        df_input = pd.DataFrame([
            {"symbol": s, "market": "KOSPI", "Close": 50.0, "bps": -1500.0, "roe": -0.20}
            for s in symbols
        ])
        res = self.engine.compute_rim_scores(df_input, allow_price_proxy=True)
        assert len(res) == 2
        assert (res["rim_filter_reason"] == "CAPITAL_IMPAIRMENT").all()
        # Invalidation must set rim_score to NaN defensively (for ensemble reweighting) without raising exception
        assert res["rim_score"].isna().all()

    def test_rim_column_casing_lowercase_and_titlecase(self):
        """Stress: Supports lowercase 'close' and Titlecase 'Close' seamlessly."""
        # 1. Lowercase 'close'
        p_df_lower = pd.DataFrame({"close": np.linspace(100.0, 110.0, 30)})
        res_lower = self.engine.compute_scores(prices_dict={"SYM_LOWER": p_df_lower}, allow_price_proxy=True)
        assert not res_lower.empty
        assert res_lower.iloc[0]["symbol"] == "SYM_LOWER"
        assert res_lower.iloc[0]["rim_score"] == pytest.approx(0.50, abs=1e-2)

        # 2. Titlecase 'Close'
        p_df_title = pd.DataFrame({"Close": np.linspace(100.0, 110.0, 30)})
        res_title = self.engine.compute_scores(prices_dict={"SYM_TITLE": p_df_title}, allow_price_proxy=True)
        assert not res_title.empty
        assert res_title.iloc[0]["symbol"] == "SYM_TITLE"
        assert res_title.iloc[0]["rim_score"] == pytest.approx(0.50, abs=1e-2)

    def test_rim_column_casing_uppercase_behavior(self):
        """Stress: Empirically document uppercase 'CLOSE' behavior: handles gracefully without crashing."""
        p_df_upper = pd.DataFrame({"CLOSE": np.linspace(100.0, 110.0, 30)})
        # Must not throw unhandled exception
        res_upper = self.engine.compute_scores(prices_dict={"SYM_UPPER": p_df_upper}, allow_price_proxy=True)
        assert isinstance(res_upper, pd.DataFrame)
        # Note: 'CLOSE' in prices_dict is ignored by c_col lookup, returning empty features_df gracefully

    def test_rim_flat_price_history(self):
        """Stress: Flat price history (constant 100.0 across all 60 bars) produces valid score."""
        symbols = ["FLAT_RIM_1", "FLAT_RIM_2"]
        prices_dict = {
            s: pd.DataFrame({"Close": np.full(60, 100.0)}) for s in symbols
        }
        res = self.engine.compute_scores(prices_dict=prices_dict, allow_price_proxy=True)
        assert len(res) == 2
        for _, row in res.iterrows():
            score = float(row["rim_score"])
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.98


# =============================================================================
# 4. StrategyExecutor Adversarial Stress Suite
# =============================================================================
class TestStrategyExecutorAdversarial:

    def setup_method(self):
        self.executor = AlphaStrategyExecutor()

    def test_strategy_executor_universe_size_150(self):
        """Stress: Universe size of 150 symbols must NOT be truncated at 100."""
        symbols = [f"SYM_{i:03d}" for i in range(150)]
        infer_data = {
            s: pd.DataFrame({"Close": np.linspace(50.0, 55.0, 20)}) for s in symbols
        }
        cfg = MagicMock()
        cfg.dart_api_key = ""
        universe = pd.DataFrame({"symbol": symbols})
        ctx = PipelineStrategyContext(
            universe=universe,
            infer_data_dict=infer_data,
            cfg=cfg,
            symbols_list=symbols,
            storage=None,
        )
        ctx.eff_filings = []

        self.executor.prepare_shared_context(ctx)

        # Full coverage check
        assert len(ctx.sentiment_map) == 150, f"Expected 150 sentiment entries, got {len(ctx.sentiment_map)}"
        assert len(ctx.tone_transcript_map) == 150, f"Expected 150 tone entries, got {len(ctx.tone_transcript_map)}"

        # Check index 101+ specifically
        for s in symbols[100:]:
            assert s in ctx.sentiment_map
            assert s in ctx.tone_transcript_map
            score = ctx.sentiment_map[s]
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_strategy_executor_universe_size_300_deep_stress(self):
        """Stress: Universe size of 300 symbols (large universe) must have 100% valid sentiment coverage."""
        symbols = [f"LARGE_{i:04d}" for i in range(300)]
        # Mix symbols with price data, empty price data, and missing price data
        infer_data = {}
        for i, s in enumerate(symbols):
            if i % 3 == 0:
                infer_data[s] = pd.DataFrame({"Close": np.linspace(10.0, 20.0, 30)})
            elif i % 3 == 1:
                infer_data[s] = pd.DataFrame({"close": np.linspace(50.0, 40.0, 30)})
            else:
                infer_data[s] = pd.DataFrame()  # empty

        cfg = MagicMock()
        cfg.dart_api_key = ""
        universe = pd.DataFrame({"symbol": symbols})
        ctx = PipelineStrategyContext(
            universe=universe,
            infer_data_dict=infer_data,
            cfg=cfg,
            symbols_list=symbols,
            storage=None,
        )
        ctx.eff_filings = []

        self.executor.prepare_shared_context(ctx)

        assert len(ctx.sentiment_map) == 300
        assert len(ctx.tone_transcript_map) == 300
        for s in symbols:
            assert s in ctx.sentiment_map
            assert 0.0 <= ctx.sentiment_map[s] <= 1.0
            assert s in ctx.tone_transcript_map
            assert 0.0 <= ctx.tone_transcript_map[s]["current_quarter_tone"] <= 1.0
