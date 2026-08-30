import os
import pytest
import pandas as pd
from src.core.hft_engine import MicrostructureImbalanceEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.sector_rotation import SectorRotationEngine
from src.config import TradingConfig


def test_hft_score_scale():
    engine = MicrostructureImbalanceEngine()
    df_prices = {
        "005930": pd.DataFrame({
            "high": [70000, 71000, 72000, 73000, 74000],
            "low": [69000, 70000, 71000, 72000, 73000],
            "close": [69500, 70500, 71500, 72500, 73800],
            "volume": [100000, 120000, 150000, 180000, 500000],
        })
    }
    universe = pd.DataFrame([{"symbol": "005930", "name": "삼성전자", "market": "KOSPI"}])
    res = engine.compute_scores(df_prices, universe)
    assert not res.empty
    score = res.iloc[0]["microstructure_score"]
    assert 0.0 <= score <= 1.0


def test_ensemble_nan_sharpe_and_zero_division():
    scorer = EnsembleScoringEngine()
    
    # 1. NaN / zero variance return test
    returns = {"reg": [0.01, 0.01, 0.01, 0.01]} # zero std
    sharpes = scorer.compute_rolling_sharpe(returns)
    assert isinstance(sharpes, dict)

    # 2. All pruned dynamic weights test (sharpe < -0.50)
    bad_sharpes = {k: -2.0 for k in scorer.get_base_weights('SIDEWAYS')}
    weights = scorer.compute_dynamic_weights_from_sharpe(bad_sharpes, 'SIDEWAYS')
    assert isinstance(weights, dict)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_sector_rotation_zero_price():
    engine = SectorRotationEngine()
    prices_dict = {
        "TEST": pd.DataFrame({
            "Close": [0.0] * 25
        })
    }
    res = engine.compute_sector_momentum_scores(prices_dict)
    assert isinstance(res, pd.DataFrame)


def test_config_env_int_casting():
    os.environ["STOCK_PRICE_FRESHNESS_DAYS"] = "14"
    os.environ["UPDATE_INTERVAL"] = "60"
    config = TradingConfig()
    assert config.stock_price_freshness_days == 14
    assert config.update_interval == 60
