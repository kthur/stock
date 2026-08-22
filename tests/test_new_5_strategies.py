"""
tests/test_new_5_strategies.py
Unit and Integration tests for 5 new strategy core engines:
- EventDrivenEngine (src/core/event_driven.py)
- MQFactorEngine (src/core/mq_factor.py)
- IVSkewEngine (src/core/iv_skew.py)
- OrderFlowEngine (src/core/order_flow.py)
- ShortTermReversalEngine (src/core/short_term_reversal.py)
- EnsembleScoringEngine 14-strategy integration (src/ai/ensemble_scorer.py)
"""
import pytest
import numpy as np
import pandas as pd
from src.core.event_driven import EventDrivenEngine
from src.core.mq_factor import MQFactorEngine
from src.core.iv_skew import IVSkewEngine
from src.core.order_flow import OrderFlowEngine
from src.core.short_term_reversal import ShortTermReversalEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine


@pytest.fixture
def sample_prices_dict():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)

    dict_data = {}
    for sym in ["005930.KS", "000660.KS", "AAPL", "MSFT"]:
        base_p = 70000.0 if "KS" in sym else 150.0
        ret = np.random.normal(0.001, 0.02, size=len(dates))
        prices = base_p * np.exp(np.cumsum(ret))
        vols = np.random.randint(100000, 1000000, size=len(dates))

        df = pd.DataFrame({
            "Date": dates,
            "Close": prices,
            "Volume": vols
        }).set_index("Date")
        dict_data[sym] = df
    return dict_data


def test_event_driven_engine(sample_prices_dict):
    engine = EventDrivenEngine(dart_api_key="")
    symbols = list(sample_prices_dict.keys())

    res = engine.compute_event_scores(symbols, sample_prices_dict)
    assert not res.empty
    assert "symbol" in res.columns
    assert "event_score" in res.columns
    assert len(res) == len(symbols)
    assert (res["event_score"] >= 0.0).all() and (res["event_score"] <= 1.0).all()


def test_mq_factor_engine(sample_prices_dict):
    engine = MQFactorEngine()
    res = engine.compute_mq_scores(sample_prices_dict)

    assert not res.empty
    assert "symbol" in res.columns
    assert "mq_score" in res.columns
    assert len(res) == len(sample_prices_dict)
    assert (res["mq_score"] >= 0.0).all() and (res["mq_score"] <= 1.0).all()


def test_iv_skew_engine(sample_prices_dict):
    engine = IVSkewEngine()
    symbols = list(sample_prices_dict.keys())

    res = engine.compute_iv_skew_scores(symbols, sample_prices_dict)
    assert not res.empty
    assert "symbol" in res.columns
    assert "iv_skew_score" in res.columns
    assert len(res) == len(symbols)
    assert (res["iv_skew_score"] >= 0.0).all() and (res["iv_skew_score"] <= 1.0).all()


def test_order_flow_engine(sample_prices_dict):
    engine = OrderFlowEngine()
    res = engine.compute_order_flow_scores(sample_prices_dict)

    assert not res.empty
    assert "symbol" in res.columns
    assert "order_flow_score" in res.columns
    assert len(res) == len(sample_prices_dict)
    assert (res["order_flow_score"] >= 0.0).all() and (res["order_flow_score"] <= 1.0).all()


def test_short_term_reversal_engine(sample_prices_dict):
    engine = ShortTermReversalEngine()
    res = engine.compute_reversal_scores(sample_prices_dict)

    assert not res.empty
    assert "symbol" in res.columns
    assert "reversal_score" in res.columns
    assert len(res) == len(sample_prices_dict)
    assert (res["reversal_score"] >= 0.0).all() and (res["reversal_score"] <= 1.0).all()


def test_14_strategy_ensemble_integration(sample_prices_dict):
    scorer = EnsembleScoringEngine()
    symbols = list(sample_prices_dict.keys())

    # Build dummy strategy inputs
    reg_df = pd.DataFrame({"symbol": symbols, 20: [0.05, 0.02, 0.08, -0.01]})
    surge_df = pd.DataFrame({"symbol": symbols, "surge_20d": [0.8, 0.3, 0.9, 0.1]})
    lead_lag_df = pd.DataFrame({"symbol": symbols, "lead_lag_score": [0.6, 0.5, 0.7, 0.4]})
    vcp_ml_df = pd.DataFrame({"symbol": symbols, "vcp_20d": [0.7, 0.4, 0.8, 0.2]})

    ev_df = EventDrivenEngine().compute_event_scores(symbols, sample_prices_dict)
    mq_df = MQFactorEngine().compute_mq_scores(sample_prices_dict)
    iv_df = IVSkewEngine().compute_iv_skew_scores(symbols, sample_prices_dict)
    of_df = OrderFlowEngine().compute_order_flow_scores(sample_prices_dict)
    rev_df = ShortTermReversalEngine().compute_reversal_scores(sample_prices_dict)

    ens_df = scorer.calculate_ensemble_score(
        regime="BULL_LOW_VOL",
        regression_df=reg_df,
        surge_df=surge_df,
        lead_lag_df=lead_lag_df,
        vcp_ml_df=vcp_ml_df,
        event_df=ev_df,
        mq_df=mq_df,
        iv_skew_df=iv_df,
        order_flow_df=of_df,
        reversal_df=rev_df,
        target_horizon=20,
    )

    assert not ens_df.empty
    assert "symbol" in ens_df.columns
    assert "ensemble_score" in ens_df.columns
    assert "ensemble_expected_return" in ens_df.columns
    assert len(ens_df) == len(symbols)
    assert (ens_df["ensemble_score"] >= 0.0).all() and (ens_df["ensemble_score"] <= 1.0).all()


def test_iv_skew_live_options_priority_when_enabled(monkeypatch, sample_prices_dict):
    """V6-19: Verify that when ENABLE_LIVE_OPTIONS_FETCH=true, live options chain takes priority for US tickers."""
    engine = IVSkewEngine()
    monkeypatch.setenv("ENABLE_LIVE_OPTIONS_FETCH", "true")

    # Mock compute_skew_for_ticker to return 0.88 for AAPL
    def mock_compute_skew(ticker):
        if ticker == "AAPL":
            return 0.88
        return 0.50

    monkeypatch.setattr(engine, "compute_skew_for_ticker", mock_compute_skew)

    res = engine.compute_iv_skew_scores(["AAPL"], prices_dict=sample_prices_dict)
    assert not res.empty
    aapl_row = res[res['symbol'] == 'AAPL'].iloc[0]
    assert abs(aapl_row['iv_skew_score'] - 0.88) < 1e-6

