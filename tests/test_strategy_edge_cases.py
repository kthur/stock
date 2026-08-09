"""Unit tests for strategy engine edge cases: NaN inputs, empty prices, missing columns."""

import pytest
import pandas as pd
import numpy as np

from trading_system.src.core.arm_factor import ARMFactorEngine
from trading_system.src.core.card_factor import CARDFactorEngine
from trading_system.src.core.latr_factor import LATRFactorEngine
from trading_system.src.core.accruals_quality import AccrualsQualityEngine
from trading_system.src.core.trend_efficiency import TrendEfficiencyEngine
from trading_system.src.core.base_strategy import BaseStrategyEngine


def test_base_strategy_interface():
    """Verify BaseStrategyEngine cannot be instantiated without compute_scores."""
    with pytest.raises(TypeError):
        BaseStrategyEngine()


def test_arm_factor_empty_inputs():
    """ARM factor engine should return empty dict when given empty inputs."""
    engine = ARMFactorEngine()
    res = engine.compute_scores({}, {})
    assert res == {}


def test_arm_factor_nan_handling():
    """ARM factor engine handles NaN metrics gracefully."""
    engine = ARMFactorEngine()
    fund = {
        "005930": {"eps_growth": np.nan, "revenue_growth": np.nan, "per": np.nan}
    }
    res = engine.compute_scores(fund, {})
    assert "005930" in res
    assert 0.0 <= res["005930"] <= 1.0


def test_card_factor_empty_inputs():
    """CARD factor engine should handle empty input data gracefully."""
    engine = CARDFactorEngine()
    res = engine.compute_scores({}, None)
    assert res == {}


def test_latr_factor_empty_inputs():
    """LATR factor engine handles empty input dictionary."""
    engine = LATRFactorEngine()
    res = engine.compute_scores({})
    assert res == {}


def test_accruals_quality_empty_inputs():
    """Accruals quality engine returns empty DataFrame for empty symbols."""
    engine = AccrualsQualityEngine()
    df = engine.calculate_scores([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_accruals_quality_synthetic():
    """Accruals quality engine calculates score correctly with synthetic data."""
    engine = AccrualsQualityEngine()
    features_df = {
        "005930": pd.DataFrame([{
            "net_income": 100.0,
            "operating_cash_flow": 150.0,
            "total_assets": 1000.0
        }])
    }
    df = engine.calculate_scores(["005930"], features_df=features_df)
    assert not df.empty
    assert "accruals_quality_score" in df.columns
    assert 0.0 <= df.iloc[0]["accruals_quality_score"] <= 1.0


def test_trend_efficiency_empty():
    """Trend efficiency engine handles empty prices_dict."""
    engine = TrendEfficiencyEngine()
    df = engine.calculate_scores(["005930"], prices_dict={})
    assert isinstance(df, pd.DataFrame)
    assert df.empty
