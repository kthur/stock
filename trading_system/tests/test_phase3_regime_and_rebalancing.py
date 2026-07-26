import numpy as np
import pandas as pd
from src.analysis.regime_detector import MarketRegimeDetector
from src.ai.ensemble_scorer import EnsembleScoringEngine

def test_2d_market_regime_detector():
    detector = MarketRegimeDetector()
    indicator_df = pd.DataFrame({
        'sp500_change': np.random.normal(0.001, 0.01, 50)
    })
    detector.train(indicator_df)
    res_2d = detector.predict_2d_regime(indicator_df)

    assert 'direction_code' in res_2d
    assert 'direction_label' in res_2d
    assert 'volatility_label' in res_2d
    assert 'combo_label' in res_2d
    assert res_2d['direction_label'] in ["BEAR", "SIDEWAYS", "BULL"]
    assert res_2d['volatility_label'] in ["LOW_VOL", "HIGH_VOL"]

def test_dynamic_sharpe_strategy_rebalancing():
    engine = EnsembleScoringEngine()
    rolling_sharpes = {
        'regression': 1.2,
        'surge': 0.8,
        'lead_lag': 0.3,
        'vcp_ml': 1.5
    }

    weights = engine.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime=1)
    assert len(weights) == 9
    assert np.isclose(sum(weights.values()), 1.0)
    # vcp_ml has higher Sharpe so it should receive boosted weight relative to lead_lag
    assert weights['vcp_ml'] > weights['lead_lag']

