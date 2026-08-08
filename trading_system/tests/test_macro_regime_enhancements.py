import numpy as np
import pandas as pd

from src.analysis.regime_detector import MarketRegimeDetector
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.sector_rotation import SectorRotationEngine


def make_dummy_indicator_df(rows=50, vix_val=15.0, sp500_ret=0.1, us10y_val=4.0):
    dates = pd.date_range("2024-01-01", periods=rows, freq="B")
    data = {
        'sp500_change': np.random.normal(sp500_ret, 1.0, rows),
        'vix_change': np.full(rows, vix_val),
        'us10y': np.full(rows, us10y_val),
        'usdkrw_change': np.random.normal(0.0, 0.5, rows),
        'us3m_yield': np.full(rows, 3.5),
        'yield_curve_10y3m': np.full(rows, us10y_val - 3.5),
    }
    return pd.DataFrame(data, index=dates)


def test_multi_variable_gmm_training_and_predict():
    detector = MarketRegimeDetector(n_regimes=3, rolling_window=10)
    df = make_dummy_indicator_df(rows=60, vix_val=18.0, sp500_ret=0.2)
    
    detector.train(df)
    assert detector.is_trained
    assert len(detector.cluster_to_regime) == 3

    regime = detector.predict_regime(df)
    assert regime in (0, 1, 2)


def test_fast_vix_shock_override():
    detector = MarketRegimeDetector(n_regimes=3, rolling_window=10)
    df_normal = make_dummy_indicator_df(rows=40, vix_val=15.0, sp500_ret=0.1)
    detector.train(df_normal)

    # Test extreme VIX shock (> 30.0) -> Forcing BEAR (0)
    df_vix_shock = make_dummy_indicator_df(rows=40, vix_val=35.0, sp500_ret=0.1)
    regime_vix = detector.predict_regime(df_vix_shock)
    assert regime_vix == 0  # BEAR

    # Test extreme S&P500 drawdown (<-3.0%) -> Forcing BEAR (0)
    df_sp_shock = make_dummy_indicator_df(rows=40, vix_val=15.0, sp500_ret=0.1)
    df_sp_shock.iloc[-1, df_sp_shock.columns.get_loc('sp500_change')] = -4.0
    regime_sp = detector.predict_regime(df_sp_shock)
    assert regime_sp == 0  # BEAR


def test_ensemble_vix_override_weights():
    engine = EnsembleScoringEngine()
    
    # Normal VIX (15.0) -> Normal base weights
    base_w = engine.get_base_weights(regime="SIDEWAYS_LOW_VOL", vix_val=15.0)
    
    # High VIX (35.0) -> Surge & Sector Rotation reduced, Regression & Stat-Arb boosted
    vix_w = engine.get_base_weights(regime="SIDEWAYS_LOW_VOL", vix_val=35.0)
    
    assert vix_w['surge'] < base_w['surge']
    assert vix_w['regression'] > base_w['regression']
    assert abs(sum(vix_w.values()) - 1.0) < 1e-5


def test_sector_rotation_macro_adjustments():
    sector_eng = SectorRotationEngine()
    
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    prices_dict = {
        '005930': pd.DataFrame({'Close': np.linspace(50000, 60000, 30)}, index=dates),
        '005380': pd.DataFrame({'Close': np.linspace(150000, 180000, 30)}, index=dates),
        '000660': pd.DataFrame({'Close': np.linspace(100000, 110000, 30)}, index=dates),
    }
    sector_map = {
        '005930': 'IT_SEMICON',
        '005380': 'BATTERY_AUTO',
        '000660': 'BIO_PHARMA'
    }

    # Normal macro
    res_normal = sector_eng.compute_sector_momentum_scores(prices_dict, sector_map=sector_map)
    score_semi_normal = float(res_normal[res_normal['symbol'] == '005930']['sector_score'].iloc[0])

    # USD Surge macro
    macro_usd_surge = pd.DataFrame({'usdkrw_change': [0.8], 'wti_change': [0.0], 'us10y': [4.0]})
    res_usd_surge = sector_eng.compute_sector_momentum_scores(prices_dict, sector_map=sector_map, macro_indicators=macro_usd_surge)
    score_semi_boosted = float(res_usd_surge[res_usd_surge['symbol'] == '005930']['sector_score'].iloc[0])

    assert score_semi_boosted >= score_semi_normal


def test_yield_inversion_3d_regime():
    detector = MarketRegimeDetector(n_regimes=3, rolling_window=10)
    df = make_dummy_indicator_df(rows=50, us10y_val=2.5, vix_val=0.0)
    df['us2y'] = 3.0
    
    detector.train(df)
    res = detector.predict_3d_macro_regime(df)
    assert res['macro_label'] == 'YIELD_INVERSION'


def test_inflation_shock_3d_regime():
    detector = MarketRegimeDetector(n_regimes=3, rolling_window=10)
    df = make_dummy_indicator_df(rows=50, us10y_val=3.5, vix_val=0.0)
    df['wti_change'] = 3.0
    df['usdkrw_change'] = 2.0
    df['inflation_shock_index'] = 5.0

    detector.train(df)
    res = detector.predict_3d_macro_regime(df)
    assert res['macro_label'] == 'INFLATION_SHOCK'
