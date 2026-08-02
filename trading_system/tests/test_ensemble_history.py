"""Tests for ensemble prediction history + outcome backfill (P0-2 fix)."""

from pathlib import Path

import pandas as pd
import pytest

from src.data_layer.indicator_storage import MarketIndicatorStorage


def _make_storage(tmp_dir):
    return MarketIndicatorStorage(db_path=str(Path(tmp_dir) / "test_indicators.db"))


def test_save_and_get_ensemble_history(tmp_path):
    storage = _make_storage(str(tmp_path))
    df = pd.DataFrame([
        {"symbol": "AAA", "ensemble_score": 0.9, "ensemble_expected_return": 18.0,
         "reg_score": 0.8, "surge_score": 0.7, "ll_score": 0.6,
         "vcp_rule_score": 0.5, "vcp_ml_score": 0.5, "lstm_score": 0.4,
         "stat_arb_score": 0.4, "sector_score": 0.4, "rim_score": 0.4,
         "event_score": 0.4, "mq_score": 0.4, "iv_skew_score": 0.4,
         "order_flow_score": 0.4, "reversal_score": 0.4, "arm_score": 0.4,
         "card_score": 0.4, "latr_score": 0.4, "inst_foreign_sector_score": 0.4},
        {"symbol": "BBB", "ensemble_score": 0.5, "ensemble_expected_return": 10.0,
         "reg_score": 0.3, "surge_score": 0.2, "ll_score": 0.1,
         "vcp_rule_score": 0.1, "vcp_ml_score": 0.1, "lstm_score": 0.1,
         "stat_arb_score": 0.1, "sector_score": 0.1, "rim_score": 0.1,
         "event_score": 0.1, "mq_score": 0.1, "iv_skew_score": 0.1,
         "order_flow_score": 0.1, "reversal_score": 0.1, "arm_score": 0.1,
         "card_score": 0.1, "latr_score": 0.1, "inst_foreign_sector_score": 0.1},
    ])
    storage.save_ensemble_predictions(df, "2026-07-01")

    hist = storage.get_ensemble_predictions_history(days=365)
    assert hist is not None and len(hist) == 2
    assert "vcp_rule_score" in hist.columns
    assert "arm_score" in hist.columns
    assert "inst_foreign_sector_score" in hist.columns
    assert "outcome_return" in hist.columns
    assert hist[hist["symbol"] == "AAA"]["ensemble_score"].iloc[0] == pytest.approx(0.9)


def test_update_ensemble_outcomes(tmp_path):
    storage = _make_storage(str(tmp_path))
    df = pd.DataFrame([
        {"symbol": "AAA", "ensemble_score": 0.9, "ensemble_expected_return": 18.0,
         "reg_score": 0.8, "surge_score": 0.7, "ll_score": 0.6,
         "vcp_rule_score": 0.5, "vcp_ml_score": 0.5, "lstm_score": 0.4,
         "stat_arb_score": 0.4, "sector_score": 0.4, "rim_score": 0.4,
         "event_score": 0.4, "mq_score": 0.4, "iv_skew_score": 0.4,
         "order_flow_score": 0.4, "reversal_score": 0.4, "arm_score": 0.4,
         "card_score": 0.4, "latr_score": 0.4, "inst_foreign_sector_score": 0.4},
    ])
    storage.save_ensemble_predictions(df, "2026-06-01")

    # 25 business days of prices: close 100 -> 110 over 20 trading days
    idx = pd.bdate_range("2026-06-01", periods=25)
    closes = pd.Series([100.0 + i for i in range(len(idx))], index=idx, name="Close")
    px = pd.DataFrame({"Close": closes.values}, index=idx)
    px.index.name = "date"

    def fake_get_prices(symbol, start_date=None, end_date=None):
        return px

    updated = storage.update_ensemble_outcomes(prices_getter=fake_get_prices, horizon=20, days=365)
    assert updated == 1

    hist = storage.get_ensemble_predictions_history(days=365)
    row = hist[hist["symbol"] == "AAA"].iloc[0]
    # entry 100.0, exit 120.0 -> +20%
    assert row["outcome_return"] == pytest.approx(0.20)
    assert row["outcome_label"] == 1

    # Second call should be a no-op (already filled)
    updated2 = storage.update_ensemble_outcomes(prices_getter=fake_get_prices, horizon=20, days=365)
    assert updated2 == 0
