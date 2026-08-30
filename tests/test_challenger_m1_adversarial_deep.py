"""
tests/test_challenger_m1_adversarial_deep.py
Adversarial Stress Testing & Empirical Challenger Suite for Milestone 1.
Author: challenger_m1_1 (Teamwork Empirical Challenger)

Exhaustively stress tests the 6 modified strategy engines:
1. RIMValuationEngine (rim_valuation.py)
2. AccrualsQualityEngine (accruals_quality.py)
3. ValueUpCatalystEngine (valueup_catalyst.py)
4. DARTSECSentimentEngine (llm_sentiment_engine.py)
5. InsiderBuyingEngine (insider_buying.py)
6. EarningsToneDriftEngine (earnings_tone_drift.py)
"""

import numpy as np
import pandas as pd
import pytest

from trading_system.src.core.rim_valuation import RIMValuationEngine
from trading_system.src.core.accruals_quality import AccrualsQualityEngine
from trading_system.src.core.valueup_catalyst import ValueUpCatalystEngine
from trading_system.src.core.llm_sentiment_engine import DARTSECSentimentEngine
from trading_system.src.core.insider_buying import InsiderBuyingEngine
from trading_system.src.core.earnings_tone_drift import EarningsToneDriftEngine


def _make_dummy_ohlcv(
    n_bars: int = 250,
    base_price: float = 100.0,
    trend: float = 0.001,
    volatility: float = 0.01,
    volume: float = 10000.0,
    columns_case: str = "title",
    inject_nan: bool = False,
    inject_inf: bool = False,
    flat_price: bool = False,
    zero_volume: bool = False,
) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=n_bars, freq="B")
    if flat_price:
        prices = np.full(n_bars, base_price)
        opens = prices
        highs = prices
        lows = prices
        closes = prices
    else:
        rng = np.random.RandomState(42)
        noise = rng.normal(0, volatility, n_bars)
        price_series = base_price * np.exp(np.cumsum(trend + noise))
        closes = price_series
        opens = price_series * (1 + rng.normal(0, 0.002, n_bars))
        highs = np.maximum(opens, closes) * (1 + abs(rng.normal(0, 0.005, n_bars)))
        lows = np.minimum(opens, closes) * (1 - abs(rng.normal(0, 0.005, n_bars)))

    vols = np.zeros(n_bars) if zero_volume else np.full(n_bars, volume)

    if columns_case == "lower":
        df = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": vols},
            index=dates,
        )
    else:
        df = pd.DataFrame(
            {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols},
            index=dates,
        )

    if inject_nan:
        df.iloc[1:3, :] = np.nan
        df.iloc[10:12, df.columns.get_loc(df.columns[0])] = np.nan

    if inject_inf:
        df.iloc[5, 0] = np.inf
        df.iloc[6, 3] = -np.inf

    return df


# ---------------------------------------------------------------------------
# 1. RIM Valuation Engine Stress Tests
# ---------------------------------------------------------------------------
class TestRIMValuationAdversarial:
    @pytest.fixture
    def engine(self):
        return RIMValuationEngine()

    def test_rim_empty_and_none_inputs(self, engine):
        res1 = engine.compute_scores(prices_dict={})
        assert isinstance(res1, pd.DataFrame)
        res2 = engine.compute_scores(prices_dict=None)
        assert isinstance(res2, pd.DataFrame)
        res3 = engine.compute_rim_scores(None)
        assert isinstance(res3, pd.DataFrame)
        assert res3.empty
        res4 = engine.compute_rim_scores(pd.DataFrame())
        assert isinstance(res4, pd.DataFrame)
        assert res4.empty

    def test_rim_pure_missing_data_returns_nan(self, engine):
        feat = pd.DataFrame({
            "symbol": ["005930", "000660", "AAPL"],
            "market": ["KOSPI", "KOSPI", "SP500"],
            "bps": [np.nan, np.nan, np.nan],
            "roe": [np.nan, np.nan, np.nan],
        })
        res = engine.compute_rim_scores(feat, prices_dict=None, allow_price_proxy=False)
        assert "rim_score" in res.columns
        assert res["rim_score"].isna().all()
        assert not (res["rim_score"] == 0.50).any()

    def test_rim_price_trend_proxy_valid(self, engine):
        p_dict = {
            "005930": _make_dummy_ohlcv(250, base_price=70000),
            "000660": _make_dummy_ohlcv(250, base_price=120000),
            "035420": _make_dummy_ohlcv(250, base_price=200000),
        }
        feat = pd.DataFrame({
            "symbol": ["005930", "000660", "035420"],
            "market": ["KOSPI", "KOSPI", "KOSPI"],
            "bps": [np.nan, np.nan, np.nan],
            "roe": [np.nan, np.nan, np.nan],
        })
        res = engine.compute_rim_scores(feat, prices_dict=p_dict, allow_price_proxy=True)
        assert "rim_score" in res.columns
        valid_scores = res["rim_score"].dropna()
        assert len(valid_scores) == 3
        assert (valid_scores >= 0.0).all() and (valid_scores <= 1.0).all()

    def test_rim_corner_cases_ohlcv(self, engine):
        p_dict = {
            "SYM_1BAR": _make_dummy_ohlcv(1, base_price=50.0),
            "SYM_FLAT": _make_dummy_ohlcv(250, base_price=100.0, flat_price=True),
            "SYM_ZERO_VOL": _make_dummy_ohlcv(250, base_price=100.0, zero_volume=True),
            "SYM_NANS": _make_dummy_ohlcv(250, base_price=100.0, inject_nan=True),
            "SYM_INFS": _make_dummy_ohlcv(250, base_price=100.0, inject_inf=True),
            "SYM_LOWER": _make_dummy_ohlcv(250, base_price=100.0, columns_case="lower"),
        }
        feat = pd.DataFrame({
            "symbol": ["SYM_1BAR", "SYM_FLAT", "SYM_ZERO_VOL", "SYM_NANS", "SYM_INFS", "SYM_LOWER"],
            "market": ["SP500"] * 6,
            "bps": [np.nan] * 6,
            "roe": [np.nan] * 6,
        })
        res = engine.compute_rim_scores(feat, prices_dict=p_dict, allow_price_proxy=True)
        assert len(res) == 6
        for score in res["rim_score"].dropna():
            assert np.isfinite(score)
            assert 0.0 <= score <= 1.0

    def test_rim_capital_impairment_exclusion(self, engine):
        feat = pd.DataFrame({
            "symbol": ["DISTRESSED", "HEALTHY"],
            "market": ["KOSPI", "KOSPI"],
            "bps": [-5000.0, np.nan],
            "roe": [-0.50, np.nan],
            "total_equity": [-1000000, np.nan],
        })
        p_dict = {
            "DISTRESSED": _make_dummy_ohlcv(250, base_price=5000),
            "HEALTHY": _make_dummy_ohlcv(250, base_price=50000),
        }
        res = engine.compute_rim_scores(feat, prices_dict=p_dict, allow_price_proxy=True)
        distressed_row = res[res["symbol"] == "DISTRESSED"].iloc[0]
        assert distressed_row["rim_filter_reason"] == "CAPITAL_IMPAIRMENT"
        assert pd.isna(distressed_row["rim_score"])


# ---------------------------------------------------------------------------
# 2. Accruals Quality Engine Stress Tests
# ---------------------------------------------------------------------------
class TestAccrualsQualityAdversarial:
    @pytest.fixture
    def engine(self):
        return AccrualsQualityEngine()

    def test_accruals_empty_and_none_inputs(self, engine):
        res1 = engine.calculate_scores([])
        assert res1.empty
        res2 = engine.compute_scores(prices_dict={})
        assert res2.empty
        res3 = engine.compute_scores(prices_dict=None)
        assert res3.empty

    def test_accruals_missing_data_returns_nan(self, engine):
        res = engine.calculate_scores(["005930", "AAPL"], features_df=None, prices_dict=None)
        assert len(res) == 2
        assert res["accruals_quality_score"].isna().all()
        assert not (res["accruals_quality_score"] == 0.50).any()

    def test_accruals_price_proxy_when_fundamentals_absent(self, engine):
        p_dict = {
            "005930": _make_dummy_ohlcv(60, base_price=70000),
            "000660": _make_dummy_ohlcv(60, base_price=120000),
            "035420": _make_dummy_ohlcv(60, base_price=200000),
        }
        res = engine.calculate_scores(["005930", "000660", "035420"], features_df=None, prices_dict=p_dict)
        assert len(res) == 3
        scores = res["accruals_quality_score"].dropna()
        assert len(scores) == 3
        assert (scores >= 0.05).all() and (scores <= 0.95).all()

    def test_accruals_corner_cases_ohlcv(self, engine):
        p_dict = {
            "SYM_1BAR": _make_dummy_ohlcv(1, base_price=50.0),
            "SYM_4BAR": _make_dummy_ohlcv(4, base_price=50.0),
            "SYM_FLAT": _make_dummy_ohlcv(30, base_price=100.0, flat_price=True),
            "SYM_ZERO_VOL": _make_dummy_ohlcv(30, base_price=100.0, zero_volume=True),
            "SYM_NANS": _make_dummy_ohlcv(30, base_price=100.0, inject_nan=True),
            "SYM_INFS": _make_dummy_ohlcv(30, base_price=100.0, inject_inf=True),
            "SYM_LOWER": _make_dummy_ohlcv(30, base_price=100.0, columns_case="lower"),
        }
        symbols = list(p_dict.keys())
        res = engine.calculate_scores(symbols, features_df=None, prices_dict=p_dict)
        assert len(res) == len(symbols)
        res_map = dict(zip(res["symbol"], res["accruals_quality_score"]))
        assert pd.isna(res_map["SYM_1BAR"])
        assert pd.isna(res_map["SYM_4BAR"])
        assert pd.notna(res_map["SYM_FLAT"])
        assert pd.notna(res_map["SYM_ZERO_VOL"])
        assert pd.notna(res_map["SYM_LOWER"])

    def test_accruals_mixed_symbols_and_formats(self, engine):
        p_dict = {
            "005930": _make_dummy_ohlcv(30, base_price=70000),
            "000660.KS": _make_dummy_ohlcv(30, base_price=120000),
        }
        res = engine.calculate_scores([5930, "005930", "000660.KS"], features_df=None, prices_dict=p_dict)
        assert len(res) == 3
        assert res["accruals_quality_score"].notna().sum() >= 2


# ---------------------------------------------------------------------------
# 3. Value-Up Catalyst Engine Stress Tests
# ---------------------------------------------------------------------------
class TestValueUpCatalystAdversarial:
    @pytest.fixture
    def engine(self):
        return ValueUpCatalystEngine()

    def test_valueup_empty_and_none_inputs(self, engine):
        res1 = engine.calculate_scores([])
        assert res1.empty
        res2 = engine.compute_scores(prices_dict={})
        assert res2.empty
        res3 = engine.compute_scores(prices_dict=None)
        assert res3.empty

    def test_valueup_missing_data_returns_nan(self, engine):
        res = engine.calculate_scores(["005930", "AAPL"], features_df=None, prices_dict=None)
        assert len(res) == 2
        assert res["valueup_catalyst_score"].isna().all()
        assert not (res["valueup_catalyst_score"] == 0.50).any()

    def test_valueup_price_proxy_when_fundamentals_absent(self, engine):
        p_dict = {
            "005930": _make_dummy_ohlcv(250, base_price=70000),
            "000660": _make_dummy_ohlcv(250, base_price=120000),
            "035420": _make_dummy_ohlcv(250, base_price=200000),
        }
        res = engine.calculate_scores(["005930", "000660", "035420"], features_df=None, prices_dict=p_dict)
        assert len(res) == 3
        scores = res["valueup_catalyst_score"].dropna()
        assert len(scores) == 3
        assert (scores >= 0.0).all() and (scores <= 1.0).all()

    def test_valueup_corner_cases_ohlcv(self, engine):
        p_dict = {
            "SYM_1BAR": _make_dummy_ohlcv(1, base_price=50.0),
            "SYM_FLAT": _make_dummy_ohlcv(250, base_price=100.0, flat_price=True),
            "SYM_ZERO_VOL": _make_dummy_ohlcv(250, base_price=100.0, zero_volume=True),
            "SYM_NANS": _make_dummy_ohlcv(250, base_price=100.0, inject_nan=True),
            "SYM_INFS": _make_dummy_ohlcv(250, base_price=100.0, inject_inf=True),
            "SYM_LOWER": _make_dummy_ohlcv(250, base_price=100.0, columns_case="lower"),
        }
        symbols = list(p_dict.keys())
        res = engine.calculate_scores(symbols, features_df=None, prices_dict=p_dict)
        assert len(res) == len(symbols)
        for score in res["valueup_catalyst_score"].dropna():
            assert np.isfinite(score)
            assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# 4. LLM Sentiment Engine Stress Tests
# ---------------------------------------------------------------------------
class TestLLMSentimentAdversarial:
    @pytest.fixture
    def engine(self):
        return DARTSECSentimentEngine()

    def test_sentiment_empty_and_none_inputs(self, engine):
        res1 = engine.compute_scores(prices_dict={})
        assert isinstance(res1, pd.DataFrame)
        assert res1.empty or "sentiment_score" in res1.columns
        res2 = engine.compute_scores(prices_dict=None)
        assert isinstance(res2, pd.DataFrame)
        assert res2.empty or "sentiment_score" in res2.columns

    def test_sentiment_missing_data_returns_nan(self, engine):
        univ = pd.DataFrame({"symbol": ["005930", "AAPL"], "name": ["삼성전자", "Apple"], "market": ["KOSPI", "SP500"]})
        res = engine.compute_scores(prices_dict=None, universe=univ, filings_map=None, sentiment_map=None)
        assert len(res) == 2
        assert res["sentiment_score"].isna().all()
        assert not (res["sentiment_score"] == 0.50).any()

    def test_sentiment_price_proxy_when_text_absent(self, engine):
        p_dict = {
            "005930": _make_dummy_ohlcv(30, base_price=70000),
            "000660": _make_dummy_ohlcv(30, base_price=120000),
        }
        univ = pd.DataFrame({"symbol": ["005930", "000660"], "name": ["삼성전자", "SK하이닉스"], "market": ["KOSPI", "KOSPI"]})
        res = engine.compute_scores(prices_dict=p_dict, universe=univ)
        assert len(res) == 2
        scores = res["sentiment_score"].dropna()
        assert len(scores) == 2
        assert (scores >= 0.05).all() and (scores <= 0.95).all()

    def test_sentiment_corner_cases_ohlcv(self, engine):
        p_dict = {
            "SYM_1BAR": _make_dummy_ohlcv(1, base_price=50.0),
            "SYM_FLAT": _make_dummy_ohlcv(30, base_price=100.0, flat_price=True),
            "SYM_ZERO_VOL": _make_dummy_ohlcv(30, base_price=100.0, zero_volume=True),
            "SYM_NANS": _make_dummy_ohlcv(30, base_price=100.0, inject_nan=True),
            "SYM_INFS": _make_dummy_ohlcv(30, base_price=100.0, inject_inf=True),
            "SYM_LOWER": _make_dummy_ohlcv(30, base_price=100.0, columns_case="lower"),
        }
        univ = pd.DataFrame({"symbol": list(p_dict.keys()), "market": ["SP500"] * len(p_dict)})
        res = engine.compute_scores(prices_dict=p_dict, universe=univ)
        assert len(res) == len(p_dict)
        res_map = dict(zip(res["symbol"], res["sentiment_score"]))
        assert pd.isna(res_map["SYM_1BAR"])
        assert pd.notna(res_map["SYM_FLAT"])
        assert pd.notna(res_map["SYM_ZERO_VOL"])
        assert pd.notna(res_map["SYM_LOWER"])


# ---------------------------------------------------------------------------
# 5. Insider Buying Engine Stress Tests
# ---------------------------------------------------------------------------
class TestInsiderBuyingAdversarial:
    @pytest.fixture
    def engine(self):
        return InsiderBuyingEngine()

    def test_insider_empty_and_none_inputs(self, engine):
        res1 = engine.compute_insider_buying_scores([])
        assert res1.empty
        res2 = engine.compute_scores(prices_dict={})
        assert res2.empty
        res3 = engine.compute_scores(prices_dict=None)
        assert res3.empty

    def test_insider_missing_data_returns_nan(self, engine):
        res = engine.compute_insider_buying_scores(["005930", "AAPL"], insider_filings=None, prices_dict=None)
        assert len(res) == 2
        assert res["insider_buying_score"].isna().all()
        assert not (res["insider_buying_score"] == 0.50).any()

    def test_insider_price_proxy_when_filings_absent(self, engine):
        p_dict = {
            "005930": _make_dummy_ohlcv(30, base_price=70000),
            "000660": _make_dummy_ohlcv(30, base_price=120000),
        }
        res = engine.compute_insider_buying_scores(["005930", "000660"], insider_filings=None, prices_dict=p_dict)
        assert len(res) == 2
        scores = res["insider_buying_score"].dropna()
        assert len(scores) == 2
        assert (scores >= 0.05).all() and (scores <= 0.95).all()

    def test_insider_corner_cases_ohlcv(self, engine):
        p_dict = {
            "SYM_1BAR": _make_dummy_ohlcv(1, base_price=50.0),
            "SYM_4BAR": _make_dummy_ohlcv(4, base_price=50.0),
            "SYM_FLAT": _make_dummy_ohlcv(30, base_price=100.0, flat_price=True),
            "SYM_ZERO_VOL": _make_dummy_ohlcv(30, base_price=100.0, zero_volume=True),
            "SYM_NANS": _make_dummy_ohlcv(30, base_price=100.0, inject_nan=True),
            "SYM_INFS": _make_dummy_ohlcv(30, base_price=100.0, inject_inf=True),
            "SYM_LOWER": _make_dummy_ohlcv(30, base_price=100.0, columns_case="lower"),
        }
        symbols = list(p_dict.keys())
        res = engine.compute_insider_buying_scores(symbols, insider_filings=None, prices_dict=p_dict)
        assert len(res) == len(symbols)
        res_map = dict(zip(res["symbol"], res["insider_buying_score"]))
        assert pd.isna(res_map["SYM_1BAR"])
        assert pd.isna(res_map["SYM_4BAR"])
        assert pd.notna(res_map["SYM_FLAT"])
        assert pd.notna(res_map["SYM_ZERO_VOL"])
        assert pd.notna(res_map["SYM_LOWER"])

    def test_insider_mixed_symbols_string_coercion(self, engine):
        """Tests that string symbol inputs (including ticker suffixes) work seamlessly."""
        symbols = ["005930", "000660.KS", "AAPL"]
        p_dict = {
            "005930": _make_dummy_ohlcv(30, base_price=70000),
            "000660": _make_dummy_ohlcv(30, base_price=120000),
            "AAPL": _make_dummy_ohlcv(30, base_price=200),
        }
        res = engine.compute_insider_buying_scores(symbols, prices_dict=p_dict)
        assert len(res) == 3
        assert res["insider_buying_score"].notna().all()


# ---------------------------------------------------------------------------
# 6. Earnings Tone Drift Engine Stress Tests
# ---------------------------------------------------------------------------
class TestEarningsToneDriftAdversarial:
    @pytest.fixture
    def engine(self):
        return EarningsToneDriftEngine()

    def test_tone_drift_empty_and_none_inputs(self, engine):
        res1 = engine.compute_tone_drift_scores([])
        assert res1.empty
        res2 = engine.compute_scores(prices_dict={})
        assert res2.empty
        res3 = engine.compute_scores(prices_dict=None)
        assert res3.empty

    def test_tone_drift_missing_data_returns_nan(self, engine):
        res = engine.compute_tone_drift_scores(["005930", "AAPL"], transcript_map=None, prices_dict=None)
        assert len(res) == 2
        assert res["earnings_tone_drift_score"].isna().all()
        assert not (res["earnings_tone_drift_score"] == 0.50).any()

    def test_tone_drift_price_proxy_when_transcripts_absent(self, engine):
        p_dict = {
            "005930": _make_dummy_ohlcv(65, base_price=70000),
            "000660": _make_dummy_ohlcv(65, base_price=120000),
        }
        res = engine.compute_tone_drift_scores(["005930", "000660"], transcript_map=None, prices_dict=p_dict)
        assert len(res) == 2
        scores = res["earnings_tone_drift_score"].dropna()
        assert len(scores) == 2
        assert (scores >= 0.05).all() and (scores <= 0.95).all()

    def test_tone_drift_corner_cases_ohlcv(self, engine):
        p_dict = {
            "SYM_1BAR": _make_dummy_ohlcv(1, base_price=50.0),
            "SYM_4BAR": _make_dummy_ohlcv(4, base_price=50.0),
            "SYM_FLAT": _make_dummy_ohlcv(65, base_price=100.0, flat_price=True),
            "SYM_ZERO_VOL": _make_dummy_ohlcv(65, base_price=100.0, zero_volume=True),
            "SYM_NANS": _make_dummy_ohlcv(65, base_price=100.0, inject_nan=True),
            "SYM_INFS": _make_dummy_ohlcv(65, base_price=100.0, inject_inf=True),
            "SYM_LOWER": _make_dummy_ohlcv(65, base_price=100.0, columns_case="lower"),
        }
        symbols = list(p_dict.keys())
        res = engine.compute_tone_drift_scores(symbols, transcript_map=None, prices_dict=p_dict)
        assert len(res) == len(symbols)
        res_map = dict(zip(res["symbol"], res["earnings_tone_drift_score"]))
        assert pd.isna(res_map["SYM_1BAR"])
        assert pd.isna(res_map["SYM_4BAR"])
        assert pd.notna(res_map["SYM_FLAT"])
        assert pd.notna(res_map["SYM_ZERO_VOL"])
        assert pd.notna(res_map["SYM_LOWER"])


# ---------------------------------------------------------------------------
# 7. Extreme & Mixed Type Stress Matrix across all 6 engines
# ---------------------------------------------------------------------------
class TestAllSixEnginesAdversarialMatrix:
    @pytest.mark.parametrize("engine_cls,call_fn,score_col", [
        (RIMValuationEngine, "compute_scores", "rim_score"),
        (AccrualsQualityEngine, "calculate_scores", "accruals_quality_score"),
        (ValueUpCatalystEngine, "calculate_scores", "valueup_catalyst_score"),
        (DARTSECSentimentEngine, "compute_scores", "sentiment_score"),
        (InsiderBuyingEngine, "compute_insider_buying_scores", "insider_buying_score"),
        (EarningsToneDriftEngine, "compute_tone_drift_scores", "earnings_tone_drift_score"),
    ])
    def test_extreme_price_scales_no_overflow_or_underflow(self, engine_cls, call_fn, score_col):
        p_dict = {
            "PENNY": _make_dummy_ohlcv(250, base_price=1e-5),
            "MEGA": _make_dummy_ohlcv(250, base_price=1e9),
        }
        engine = engine_cls()

        if engine_cls == RIMValuationEngine:
            feat = pd.DataFrame({
                "symbol": ["PENNY", "MEGA"],
                "market": ["SP500", "SP500"],
                "bps": [np.nan, np.nan],
                "roe": [np.nan, np.nan],
            })
            res = engine.compute_rim_scores(feat, prices_dict=p_dict, allow_price_proxy=True)
        elif engine_cls == DARTSECSentimentEngine:
            univ = pd.DataFrame({"symbol": ["PENNY", "MEGA"], "market": ["SP500", "SP500"]})
            res = engine.compute_scores(prices_dict=p_dict, universe=univ)
        else:
            fn = getattr(engine, call_fn)
            res = fn(["PENNY", "MEGA"], prices_dict=p_dict)

        assert not res.empty
        assert score_col in res.columns
        for s in res[score_col].dropna():
            assert np.isfinite(s)
            assert 0.0 <= s <= 1.0

    @pytest.mark.parametrize("engine_cls,call_fn,score_col", [
        (RIMValuationEngine, "compute_scores", "rim_score"),
        (AccrualsQualityEngine, "calculate_scores", "accruals_quality_score"),
        (ValueUpCatalystEngine, "calculate_scores", "valueup_catalyst_score"),
        (DARTSECSentimentEngine, "compute_scores", "sentiment_score"),
        (InsiderBuyingEngine, "compute_insider_buying_scores", "insider_buying_score"),
        (EarningsToneDriftEngine, "compute_tone_drift_scores", "earnings_tone_drift_score"),
    ])
    def test_mixed_symbol_identifiers_string_list(self, engine_cls, call_fn, score_col):
        symbols = ["005930", "000660.KS", "AAPL.O", "BRK.B"]
        p_dict = {
            "005930": _make_dummy_ohlcv(250, base_price=70000),
            "000660": _make_dummy_ohlcv(250, base_price=120000),
            "AAPL": _make_dummy_ohlcv(250, base_price=200),
            "BRK.B": _make_dummy_ohlcv(250, base_price=400),
        }
        engine = engine_cls()

        if engine_cls == RIMValuationEngine:
            feat = pd.DataFrame({
                "symbol": symbols,
                "market": ["KOSPI", "KOSPI", "SP500", "SP500"],
                "bps": [np.nan] * len(symbols),
                "roe": [np.nan] * len(symbols),
            })
            res = engine.compute_rim_scores(feat, prices_dict=p_dict, allow_price_proxy=True)
        elif engine_cls == DARTSECSentimentEngine:
            univ = pd.DataFrame({"symbol": symbols, "market": ["KOSPI", "KOSPI", "SP500", "SP500"]})
            res = engine.compute_scores(prices_dict=p_dict, universe=univ)
        else:
            fn = getattr(engine, call_fn)
            res = fn(symbols, prices_dict=p_dict)

        assert not res.empty
        assert score_col in res.columns
        assert len(res) == len(symbols)
