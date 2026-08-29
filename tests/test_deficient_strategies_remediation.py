import numpy as np, pandas as pd, pytest
from trading_system.src.core.rim_valuation import RIMValuationEngine
from trading_system.src.core.accruals_quality import AccrualsQualityEngine
from trading_system.src.core.valueup_catalyst import ValueUpCatalystEngine
from trading_system.src.core.insider_buying import InsiderBuyingEngine
from trading_system.src.core.llm_sentiment_engine import DARTSECSentimentEngine
from trading_system.src.core.earnings_tone_drift import EarningsToneDriftEngine
from trading_system.src.core.dual_correction import DualCorrectionEngine
from trading_system.src.core.index_rebalance import IndexRebalanceEngine
from trading_system.src.core.overnight_gap_reversal import OvernightGapReversalEngine
from trading_system.src.ai.prediction_model import OnDevicePredictionModel

@pytest.fixture
def mock_stock_universe():
    return pd.DataFrame([
        {'symbol': '005930', 'name': 'Samsung', 'market': 'KOSPI', 'sector_code': 'IT'},
        {'symbol': '000660', 'name': 'SK Hynix', 'market': 'KOSPI', 'sector_code': 'IT'},
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market': 'NASDAQ', 'sector_code': 'IT'}
    ])

@pytest.fixture
def mock_prices_dict():
    dates = pd.date_range('2026-01-01', periods=60)
    res = {}
    for sym in ['005930', '000660', 'AAPL']:
        base_p = 70000.0 if sym.isdigit() else 150.0
        prices = base_p + np.cumsum(np.random.normal(0, 1.0, size=len(dates)))
        res[sym] = pd.DataFrame({
            'Open': prices * 0.99, 'High': prices * 1.02, 'Low': prices * 0.98, 'Close': prices,
            'Volume': np.random.randint(100000, 1000000, size=len(dates))
        }, index=dates)
    return res

@pytest.fixture
def mock_fundamentals_df():
    return pd.DataFrame([
        {
            'symbol': '005930', 'bps': 50000.0, 'roe': 0.12,
            'operating_income': 30_000_000_000_000.0, 'net_income': 25_000_000_000_000.0,
            'book_value': 350_000_000_000_000.0, 'total_debt': 10_000_000_000_000.0,
            'cash_equivalents': 80_000_000_000_000.0, 'shares_outstanding': 6_000_000_000.0,
            'Close': 70000.0, 'market': 'KOSPI', 'name': 'Samsung', 'eps_growth_1y': 0.15, 'revenue_growth_1y': 0.08
        },
        {
            'symbol': '000660', 'bps': 85000.0, 'roe': 0.18,
            'operating_income': 15_000_000_000_000.0, 'net_income': 12_000_000_000_000.0,
            'book_value': 70_000_000_000_000.0, 'total_debt': 20_000_000_000_000.0,
            'cash_equivalents': 15_000_000_000_000.0, 'shares_outstanding': 728_000_000.0,
            'Close': 160000.0, 'market': 'KOSPI', 'name': 'SK Hynix', 'eps_growth_1y': 0.25, 'revenue_growth_1y': 0.12
        },
        {
            'symbol': 'AAPL', 'bps': 4.5, 'roe': 0.45,
            'operating_income': 115_000_000_000.0, 'net_income': 95_000_000_000.0,
            'book_value': 65_000_000_000.0, 'total_debt': 100_000_000_000.0,
            'cash_equivalents': 30_000_000_000.0, 'shares_outstanding': 15_500_000_000.0,
            'Close': 190.0, 'market': 'NASDAQ', 'name': 'Apple Inc.', 'eps_growth_1y': 0.10, 'revenue_growth_1y': 0.05
        }
    ])

def test_rim_valuation(mock_fundamentals_df):
    engine = RIMValuationEngine()
    res = engine.compute_rim_scores(mock_fundamentals_df)
    assert not res.empty
    assert len(res['rim_score'].dropna()) == 3

def test_accruals_quality(mock_fundamentals_df, mock_prices_dict):
    engine = AccrualsQualityEngine()
    res = engine.calculate_scores(['005930', '000660', 'AAPL'], features_df=mock_fundamentals_df, prices_dict=mock_prices_dict)
    assert not res.empty
    assert len(res['accruals_quality_score'].dropna()) == 3

def test_valueup_catalyst(mock_fundamentals_df, mock_prices_dict):
    engine = ValueUpCatalystEngine()
    res = engine.calculate_scores(['005930', '000660', 'AAPL'], features_df=mock_fundamentals_df, prices_dict=mock_prices_dict)
    assert not res.empty
    assert len(res['valueup_catalyst_score'].dropna()) == 3

def test_insider_buying(mock_prices_dict):
    engine = InsiderBuyingEngine()
    filings = [{'stock_code': '005930', 'report_nm': '장내매수', 'trans_type': 'BUY', 'insider_role': 'CEO'}]
    res = engine.calculate_scores(['005930', '000660'], prices_dict=mock_prices_dict, insider_filings=filings)
    assert not res.empty
    assert 'insider_buying_score' in res.columns

def test_llm_sentiment(mock_stock_universe, mock_prices_dict):
    engine = DARTSECSentimentEngine()
    res = engine.compute_scores(universe=mock_stock_universe, prices_dict=mock_prices_dict)
    assert not res.empty
    assert len(res['sentiment_score'].dropna()) == 3

def test_earnings_tone_drift(mock_fundamentals_df, mock_prices_dict):
    engine = EarningsToneDriftEngine()
    res = engine.calculate_scores(['005930', '000660', 'AAPL'], prices_dict=mock_prices_dict, features_df=mock_fundamentals_df)
    assert not res.empty
    assert len(res['earnings_tone_drift_score'].dropna()) == 3

def test_lead_lag_universe_coverage(mock_prices_dict):
    model = OnDevicePredictionModel()
    model.lead_lag_matrix = {'005930': [('000660', 0.85)]}
    res = model.predict_lead_lag(prices_dict=mock_prices_dict)
    assert not res.empty
    assert len(res) == len(mock_prices_dict)

def test_extended_strategies(mock_stock_universe, mock_prices_dict):
    dc_res = DualCorrectionEngine().compute_scores(prices_dict=mock_prices_dict, regime='SIDEWAYS_LOW_VOL')
    assert not dc_res.empty
    ir_res = IndexRebalanceEngine().compute_scores(prices_dict=mock_prices_dict, universe=mock_stock_universe)
    assert not ir_res.empty
    ogr_res = OvernightGapReversalEngine().calculate_scores(symbols=list(mock_prices_dict.keys()), prices_dict=mock_prices_dict)
    assert not ogr_res.empty