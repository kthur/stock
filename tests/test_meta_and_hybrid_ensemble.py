"""
Unit tests for MetaEnsembleLearner, Hybrid Probability Calibration, and Turnover Hysteresis Buffer.
"""

import numpy as np
import pandas as pd
from src.ai.meta_ensemble_learner import MetaEnsembleLearner, STRATEGY_SCORE_COLS
from src.ai.ensemble_scorer import EnsembleScoringEngine

def test_meta_ensemble_learner_init_and_fallback(tmp_path):
    learner = MetaEnsembleLearner(model_dir=tmp_path)
    assert learner.is_fitted is False

    # Synthetic strategy score inputs
    df = pd.DataFrame({
        'reg_score': [0.8, 0.2, 0.5],
        'surge_score': [0.7, 0.1, 0.6],
        'vcp_ml_score': [0.9, 0.3, 0.4]
    })
    preds = learner.predict(df)
    assert len(preds) == 3
    assert np.all((preds >= 0.0) & (preds <= 1.0))

def test_meta_ensemble_learner_fit_save_load(tmp_path):
    learner = MetaEnsembleLearner(model_dir=tmp_path)
    df = pd.DataFrame({col: np.random.uniform(0, 1, 50) for col in STRATEGY_SCORE_COLS})
    target_returns = 0.5 * df['reg_score'] + 0.5 * df['surge_score'] + np.random.normal(0, 0.05, 50)

    learner.fit(df, target_returns, alpha=1.0)
    assert learner.is_fitted is True

    # Test prediction
    preds = learner.predict(df)
    assert len(preds) == 50

    # Test loading saved model
    learner2 = MetaEnsembleLearner(model_dir=tmp_path)
    assert learner2.is_fitted is True
    preds2 = learner2.predict(df)
    np.testing.assert_allclose(preds, preds2)

def test_hybrid_calibration():
    scorer = EnsembleScoringEngine()

    # Test Platt Scaling (N < 50)
    scores_small = np.random.uniform(0, 1, 30)
    labels_small = (scores_small > 0.5).astype(int)
    scorer.fit_calibrators({'surge': scores_small}, labels_small)
    assert 'surge' in scorer._calibrators
    cal_type, _ = scorer._calibrators['surge']
    assert cal_type == 'platt'

    # Test Isotonic (N >= 50)
    scores_large = np.random.uniform(0, 1, 60)
    labels_large = (scores_large > 0.5).astype(int)
    scorer.fit_calibrators({'regression': scores_large}, labels_large)
    assert 'regression' in scorer._calibrators
    cal_type2, _ = scorer._calibrators['regression']
    assert cal_type2 == 'isotonic'

def test_turnover_hysteresis_buffer():
    scorer = EnsembleScoringEngine()
    reg_df = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'market': ['SP500', 'SP500', 'SP500'],
        20: [0.15, 0.10, 0.05]
    })
    s_df = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'surge_20d': [0.6, 0.4, 0.2]
    })
    ll_df = pd.DataFrame(columns=['symbol', 'll_score'])
    vcp_ml_df = pd.DataFrame(columns=['symbol', 'vcp_ml_score'])

    res_no_held = scorer.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_df,
        surge_df=s_df,
        lead_lag_df=ll_df,
        vcp_ml_df=vcp_ml_df,
        held_symbols=None
    )

    res_with_held = scorer.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_df,
        surge_df=s_df,
        lead_lag_df=ll_df,
        vcp_ml_df=vcp_ml_df,
        held_symbols={'GOOGL'}
    )

    score_googl_normal = res_no_held.loc[res_no_held['symbol'] == 'GOOGL', 'ensemble_score'].values[0]
    score_googl_held = res_with_held.loc[res_with_held['symbol'] == 'GOOGL', 'ensemble_score'].values[0]

    assert score_googl_held >= score_googl_normal
