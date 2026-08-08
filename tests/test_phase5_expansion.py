import pytest
import numpy as np
import pandas as pd
from trading_system.src.core.gamma_squeeze import OptionsGammaSqueezeEngine
from trading_system.src.core.insider_buying import InsiderBuyingEngine
from trading_system.src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
from trading_system.src.risk.delta_beta_hedge import DeltaBetaHedgeEngine
from trading_system.src.core.earnings_tone_drift import EarningsToneDriftEngine


def test_gamma_squeeze_engine():
    """Verify Strategy #28 (Options Gamma Squeeze) scores Call Wall proximity & volume surge."""
    engine = OptionsGammaSqueezeEngine()
    
    dates = pd.date_range('2026-08-01', periods=20)
    prices_dict = {
        'AAPL': pd.DataFrame({
            'Close': np.linspace(100, 150, 20),
            'Volume': [1000] * 19 + [5000]  # Massive 5x volume spike near high
        }, index=dates)
    }

    df_res = engine.compute_gamma_squeeze_scores(symbols=['AAPL'], prices_dict=prices_dict)
    assert len(df_res) == 1
    score = df_res['gamma_squeeze_score'].iloc[0]
    assert score > 0.60


def test_insider_buying_engine():
    """Verify Strategy #29 (Insider Net Buying) boosts score upon CEO/Executive purchase disclosures."""
    engine = InsiderBuyingEngine()
    
    symbols = ['005930', '000660']
    filings = [
        {'stock_code': '005930', 'report_nm': '임원주요주주소유상황보고서 (CEO 1만주 장내매수)', 'insider_role': 'CEO', 'trans_type': 'BUY'}
    ]

    df_res = engine.compute_insider_buying_scores(symbols=symbols, insider_filings=filings)
    assert len(df_res) == 2
    
    # 005930 CEO Buy -> boosted to 0.85
    s_5930 = df_res[df_res['symbol'] == '005930']['insider_buying_score'].iloc[0]
    assert s_5930 == 0.85
    
    # 000660 -> neutral 0.50
    s_0660 = df_res[df_res['symbol'] == '000660']['insider_buying_score'].iloc[0]
    assert s_0660 == 0.50


def test_darkpool_tracker_engine():
    """Verify Strategy #30 (Dark Pool Divergence) detects institutional accumulation during flat price."""
    engine = DarkPoolTrackerEngine()
    
    dates = pd.date_range('2026-08-01', periods=10)
    prices_dict = {
        'MSFT': pd.DataFrame({
            'Close': [100.0] * 10,  # Flat price
            'Volume': [1000] * 9 + [3000]  # 3x Volume spike
        }, index=dates)
    }

    df_res = engine.compute_darkpool_scores(symbols=['MSFT'], prices_dict=prices_dict)
    assert len(df_res) == 1
    score = df_res['darkpool_score'].iloc[0]
    assert score > 0.60


def test_delta_beta_hedge_engine():
    """Verify Delta & Beta Inverse Hedge Engine calculates Inverse ETF allocation in severe/bear market."""
    engine = DeltaBetaHedgeEngine()
    
    port_weights = {'005930': 0.40, '000660': 0.40, '035420': 0.20}
    symbol_betas = {'005930': 1.20, '000660': 1.50, '035420': 1.00}
    
    # 1. BULL Market -> No hedge required
    res_bull = engine.calculate_optimal_hedge_allocation(port_weights, symbol_betas, crisis_level="NONE", regime="BULL_LOW_VOL")
    assert res_bull['hedge_weight'] == 0.0

    # 2. SEVERE Crisis -> Allocates Inverse ETF (KODEX 200 선물인버스2X - 252670.KS)
    res_crisis = engine.calculate_optimal_hedge_allocation(port_weights, symbol_betas, crisis_level="SEVERE", regime="BEAR_HIGH_VOL")
    assert res_crisis['hedge_weight'] > 0.0
    assert '252670.KS' in res_crisis['net_asset_weights']
    assert res_crisis['target_beta'] == 0.0


def test_earnings_tone_drift_engine():
    """Verify LLM Earnings Tone Drift Engine calculates sentiment acceleration score."""
    engine = EarningsToneDriftEngine()
    
    transcript_map = {
        'NVDA': {
            'previous_quarter_tone': 0.40,
            'current_quarter_tone': 0.80,
            'confidence': 1.0
        }
    }

    df_res = engine.compute_tone_drift_scores(symbols=['NVDA'], transcript_map=transcript_map)
    assert len(df_res) == 1
    score = df_res['tone_drift_score'].iloc[0]
    assert score > 0.80  # Upward tone drift acceleration
