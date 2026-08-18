import pytest
import numpy as np
import pandas as pd
from src.analysis.dsr_validator import DeflatedSharpeRatioValidator


def test_expected_max_sharpe():
    validator = DeflatedSharpeRatioValidator(n_strategies=31, n_horizons=8)
    # Expected max sharpe should increase monotonically with number of trials
    exp_sr_1 = validator.compute_expected_max_sharpe(n_trials=1, var_sharpe=0.5)
    assert exp_sr_1 == 0.0

    exp_sr_10 = validator.compute_expected_max_sharpe(n_trials=10, var_sharpe=0.5)
    exp_sr_100 = validator.compute_expected_max_sharpe(n_trials=100, var_sharpe=0.5)
    exp_sr_248 = validator.compute_expected_max_sharpe(n_trials=248, var_sharpe=0.5)

    assert 0.0 < exp_sr_10 < exp_sr_100 < exp_sr_248


def test_compute_dsr_significance():
    validator = DeflatedSharpeRatioValidator(n_strategies=31, n_horizons=8, confidence_level=0.95)

    # Moderate Sharpe (e.g. 1.0) under 248 trials might not be significant once deflated
    dsr_res_low = validator.compute_dsr(observed_sr=0.8, n_trials=248, var_sharpe=0.5, t_observations=252)
    assert 'dsr_probability' in dsr_res_low
    assert 'is_statistically_significant' in dsr_res_low

    # Very High Sharpe (e.g. 3.5) should be statistically significant even with 248 trials
    dsr_res_high = validator.compute_dsr(observed_sr=3.5, n_trials=248, var_sharpe=0.5, t_observations=252)
    assert dsr_res_high['is_statistically_significant'] is True
    assert dsr_res_high['dsr_probability'] >= 0.95


def test_validate_strategy_alphas():
    validator = DeflatedSharpeRatioValidator(n_strategies=5, n_horizons=1, confidence_level=0.95)

    strategy_sharpes = {
        'strong_alpha': 2.8,
        'moderate_alpha': 1.1,
        'weak_alpha': 0.3,
        'negative_alpha': -0.4
    }

    # Mock daily returns for 252 days
    np.random.seed(42)
    returns_data = {
        'strong_alpha': np.random.normal(0.0015, 0.01, 252),
        'moderate_alpha': np.random.normal(0.0006, 0.01, 252),
        'weak_alpha': np.random.normal(0.0002, 0.01, 252),
        'negative_alpha': np.random.normal(-0.0003, 0.01, 252),
    }
    df_returns = pd.DataFrame(returns_data)

    report = validator.validate_strategy_alphas(strategy_sharpes, strategy_returns_df=df_returns, t_days=252)

    assert 'valid_strategies' in report
    assert 'flagged_strategies' in report
    assert 'strong_alpha' in report['valid_strategies']
    assert 'negative_alpha' in report['flagged_strategies']
