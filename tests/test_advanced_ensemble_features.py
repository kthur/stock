"""
Unit tests for 4 Advanced Ensemble Features:
1. HMM Regime Transition Probabilities
2. Meta-Learner Auto Rolling Retrain
3. Black-Litterman Portfolio Allocation
4. Strategy Attribution Analyzer
"""

import numpy as np
import pandas as pd
from src.analysis.regime_detector import MarketRegimeDetector
from src.ai.meta_ensemble_learner import MetaEnsembleLearner, STRATEGY_SCORE_COLS
from src.risk.position_sizing import PortfolioAllocator
from src.analysis.attribution_analyzer import StrategyAttributionAnalyzer

def test_hmm_regime_transition_probabilities():
    detector = MarketRegimeDetector()
    df_ind = pd.DataFrame({
        'sp500_change': np.random.normal(0, 1, 30),
        'vix_change': np.full(30, 18.0),
        'us10y': np.full(30, 4.2),
        'usdkrw_change': np.zeros(30)
    })
    probs = detector.predict_regime_transition_probabilities(df_ind)
    assert 'p_bear' in probs
    assert 'p_sideways' in probs
    assert 'p_bull' in probs
    assert 'bear_shock_risk' in probs
    assert 0.0 <= probs['p_bear'] <= 1.0

def test_meta_learner_auto_rolling_retrain(tmp_path):
    learner = MetaEnsembleLearner(model_dir=tmp_path)
    hist_df = pd.DataFrame({col: np.random.uniform(0, 1, 40) for col in STRATEGY_SCORE_COLS})
    hist_df['outcome_label'] = (hist_df['reg_score'] > 0.5).astype(float)

    success = learner.auto_rolling_retrain(hist_df, target_col='outcome_label')
    assert success is True

def test_black_litterman_portfolio_allocation():
    allocator = PortfolioAllocator()
    dates = pd.date_range("2025-01-01", periods=30, freq="D")
    prices_dict = {
        'AAPL': pd.DataFrame({'Close': 150.0 + np.cumsum(np.random.normal(0, 1, 30))}, index=dates),
        'MSFT': pd.DataFrame({'Close': 300.0 + np.cumsum(np.random.normal(0, 1, 30))}, index=dates)
    }
    preds = {'AAPL': 0.12, 'MSFT': 0.08}
    res = allocator.allocate_black_litterman(prices_dict=prices_dict, predicted_returns=preds)

    assert not res.empty
    assert 'symbol' in res.columns
    assert 'weight' in res.columns
    assert np.isclose(res['weight'].sum(), 1.0, atol=1e-5)

def test_strategy_attribution_analyzer(tmp_path):
    analyzer = StrategyAttributionAnalyzer(output_dir=tmp_path)
    ens_df = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'ensemble_expected_return': [15.0, 12.0, 8.0],
        'reg_score': [0.8, 0.6, 0.4],
        'surge_score': [0.7, 0.5, 0.3]
    })
    res = analyzer.analyze_attribution(ens_df)
    assert res['status'] == 'SUCCESS'
    assert (tmp_path / "strategy_attribution_report.txt").exists()
