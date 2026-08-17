import pytest
import numpy as np
import pandas as pd
from src.ai.meta_ensemble_learner import MetaEnsembleLearner, STRATEGY_SCORE_COLS


def test_meta_ensemble_learner_31_strategies(tmp_path):
    """Verify that MetaEnsembleLearner handles all 31 strategy columns and fits/predicts correctly."""
    assert len(STRATEGY_SCORE_COLS) == 31

    learner = MetaEnsembleLearner(model_dir=tmp_path)
    assert not learner.is_fitted

    n_samples = 60
    np.random.seed(42)

    # Generate synthetic scores for all 31 strategies
    data = {col: np.random.uniform(0.1, 0.9, n_samples) for col in STRATEGY_SCORE_COLS}
    df = pd.DataFrame(data)
    target_returns = np.random.uniform(-0.10, 0.25, n_samples)

    # Test unfitted fallback
    fallback_preds = learner.predict(df)
    assert len(fallback_preds) == n_samples
    assert (fallback_preds >= 0.0).all() and (fallback_preds <= 1.0).all()

    # Fit Ridge
    learner.fit(df, target_returns, alpha=1.0)
    assert learner.is_fitted
    assert len(learner.weights) == 31

    preds = learner.predict(df)
    assert len(preds) == n_samples
    assert (preds >= 0.0).all() and (preds <= 1.0).all()


def test_meta_ensemble_learner_blended_mode(tmp_path):
    """Verify that MetaEnsembleLearner works in blended / lgbm mode."""
    learner = MetaEnsembleLearner(model_dir=tmp_path, learner_type='blended')
    n_samples = 60
    np.random.seed(42)

    data = {col: np.random.uniform(0.1, 0.9, n_samples) for col in STRATEGY_SCORE_COLS}
    df = pd.DataFrame(data)
    target_returns = np.random.uniform(-0.10, 0.25, n_samples)

    learner.fit(df, target_returns)
    assert learner.is_fitted

    preds = learner.predict(df)
    assert len(preds) == n_samples
    assert (preds >= 0.0).all() and (preds <= 1.0).all()
