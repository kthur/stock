import pytest
import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine


def test_available_factor_normalization():
    scorer = EnsembleScoringEngine()

    # Create dummy data where Stock A has all 31 strategies and Stock B only has 5 core strategies
    # Stock B should not be arbitrarily penalized by 50% just because auxiliary data is missing
    reg_df = pd.DataFrame([
        {'symbol': 'STOCK_A', 20: 0.15},
        {'symbol': 'STOCK_B', 20: 0.15}
    ])
    surge_df = pd.DataFrame([
        {'symbol': 'STOCK_A', 'surge_20d': 0.80},
        {'symbol': 'STOCK_B', 'surge_20d': 0.80}
    ])
    vcp_df = pd.DataFrame([
        {'symbol': 'STOCK_A', 'vcp_20d': 0.70},
        {'symbol': 'STOCK_B', 'vcp_20d': 0.70}
    ])
    lstm_df = pd.DataFrame([
        {'symbol': 'STOCK_A', 'expected_return': 0.05},
        {'symbol': 'STOCK_B', 'expected_return': 0.05}
    ])
    trend_df = pd.DataFrame([
        {'symbol': 'STOCK_A', 'trend_score': 0.75},
        {'symbol': 'STOCK_B', 'trend_score': 0.75}
    ])

    # Stock A has extra auxiliary data (e.g. IV Skew, Gamma Squeeze), Stock B does not
    iv_df = pd.DataFrame([{'symbol': 'STOCK_A', 'iv_skew_score': 0.50}])

    res = scorer.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_df,
        surge_df=surge_df,
        vcp_ml_df=vcp_df,
        lstm_df=lstm_df,
        trend_efficiency_df=trend_df,
        iv_skew_df=iv_df,
        target_horizon=20
    )

    assert not res.empty
    stock_a = res[res['symbol'] == 'STOCK_A'].iloc[0]
    stock_b = res[res['symbol'] == 'STOCK_B'].iloc[0]

    # Both should have strong positive ensemble scores (> 0.50)
    assert stock_a['ensemble_score'] > 0.50
    assert stock_b['ensemble_score'] > 0.50

    # Stock B's score should be close to Stock A's score because its core signals are identical
    score_diff = abs(stock_a['ensemble_score'] - stock_b['ensemble_score'])
    assert score_diff < 0.15


def test_factor_momentum_and_crowding_damper():
    scorer = EnsembleScoringEngine()

    rolling_sharpes = {
        'surge': 1.8,
        'regression': 1.2,
        'vcp_ml': 0.5,
        'stat_arb': 0.1
    }

    # Factor IC: surge has high momentum (IC=0.15), stat_arb has negative (IC=-0.10)
    factor_ic = {
        'surge': 0.15,
        'stat_arb': -0.10
    }

    # Factor Crowding: regression is crowded (penalty=0.30)
    factor_crowding = {
        'regression': 0.30
    }

    weights_base = scorer.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=rolling_sharpes,
        regime='BULL_LOW_VOL',
        gamma=1.0
    )

    weights_boosted = scorer.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=rolling_sharpes,
        regime='BULL_LOW_VOL',
        gamma=1.0,
        factor_ic_dict=factor_ic,
        factor_crowding_penalties=factor_crowding
    )

    # Surge with high IC should receive higher weight in boosted than in base
    assert weights_boosted['surge'] > weights_base['surge']
    # Regression with crowding penalty should receive lower relative weight in boosted than in base
    assert weights_boosted['regression'] < weights_base['regression']
