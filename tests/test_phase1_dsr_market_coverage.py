import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.dsr_validator import DeflatedSharpeRatioValidator
from src.ai.prediction_model import OnDevicePredictionModel


def test_dsr_validator_basic_properties():
    validator = DeflatedSharpeRatioValidator(n_strategies=31, n_horizons=8)
    exp_max = validator.compute_expected_max_sharpe(n_trials=31*8, var_sharpe=0.50)
    assert exp_max > 0.0, "Expected max Sharpe across 248 trials should be positive"

    # High observed Sharpe vs expected max
    res_high = validator.compute_dsr(observed_sr=3.5, n_trials=248, var_sharpe=0.50, t_observations=252)
    assert res_high['dsr_probability'] > 0.90
    assert res_high['is_statistically_significant'] is True

    # Low observed Sharpe (statistically indistinguishable from noise)
    res_low = validator.compute_dsr(observed_sr=0.3, n_trials=248, var_sharpe=0.50, t_observations=252)
    assert res_low['dsr_probability'] < 0.50
    assert res_low['is_statistically_significant'] is False


def test_ensemble_scorer_dsr_gating_integration():
    engine = EnsembleScoringEngine()
    assert hasattr(engine, '_dsr_validator')

    sharpes = {
        'stat_arb': 3.5,
        'regression': 0.2,
        'surge': 0.0,
    }
    weights = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='SIDEWAYS_LOW_VOL')
    assert weights['stat_arb'] > 0.0
    assert weights['regression'] >= 0.0
    assert np.isclose(sum(weights.values()), 1.0)


def test_market_aware_coverage_ratio_fairness():
    engine = EnsembleScoringEngine()
    
    data = {
        'symbol': ['005930', 'AAPL'],
        'market': ['KOSPI', 'SP500'],
        'reg_score': [0.65, 0.65],
        'surge_score': [0.60, 0.60],
        'll_score': [0.55, 0.55],
        'vcp_rule_score': [0.70, 0.70],
        'vcp_ml_score': [0.65, 0.65],
        'lstm_score': [0.58, 0.58],
        'stat_arb_score': [0.52, 0.52],
        'sector_score': [0.60, 0.60],
        'reversal_score': [0.55, 0.55],
        'trend_efficiency_score': [0.62, 0.62],
    }
    df = pd.DataFrame(data)

    res = engine.combine_predictions(df, regime='SIDEWAYS_LOW_VOL')
    assert 'ensemble_score' in res.columns
    assert res.loc[res['symbol'] == '005930', 'ensemble_score'].values[0] > 0.0
    assert res.loc[res['symbol'] == 'AAPL', 'ensemble_score'].values[0] > 0.0


def test_triple_barrier_targets_in_prediction_model():
    model = OnDevicePredictionModel()
    n_bars = 100
    dates = pd.date_range('2025-01-01', periods=n_bars, freq='B')
    np.random.seed(42)
    close_prices = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.01, n_bars)))
    high_prices = close_prices * (1.0 + np.random.uniform(0.001, 0.02, n_bars))
    low_prices = close_prices * (1.0 - np.random.uniform(0.001, 0.02, n_bars))
    
    df = pd.DataFrame({
        'Open': close_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices,
        'Volume': np.random.randint(1000, 100000, n_bars)
    }, index=dates)

    targets_df = model._create_targets(df)
    assert 'target_20d' in targets_df.columns
    assert 'tb_target_20d' in targets_df.columns
