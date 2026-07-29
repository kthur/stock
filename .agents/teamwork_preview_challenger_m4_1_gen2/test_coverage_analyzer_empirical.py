"""
Pytest suite for empirical stress testing of StrategyCoverageAnalyzer
Location: d:\Finance\code\stock\.agents\teamwork_preview_challenger_m4_1_gen2\test_coverage_analyzer_empirical.py
"""

import pytest
import numpy as np
import pandas as pd
from trading_system.src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


def test_coverage_analyzer_basic_math():
    analyzer = StrategyCoverageAnalyzer()
    df = pd.DataFrame({
        'symbol': ['005930.KS', '000660.KS', '035420.KS', '035720.KS'],
        'reg_score': [0.5, np.nan, 0.7, 0.8],           # 3/4 = 75.0%
        'surge_score': [np.nan, np.nan, 0.6, 0.4],     # 2/4 = 50.0%
        'll_score': [0.1, 0.2, 0.3, 0.4],              # 4/4 = 100.0%
        'vcp_rule_score': [np.nan, np.nan, np.nan, np.nan], # 0/4 = 0.0%
    })
    
    res = analyzer.analyze_coverage(df)
    assert res['total_symbols'] == 4
    assert res['strategies']['regression']['valid_count'] == 3
    assert res['strategies']['regression']['missing_count'] == 1
    assert res['strategies']['regression']['coverage_pct'] == 75.0

    assert res['strategies']['surge']['valid_count'] == 2
    assert res['strategies']['surge']['missing_count'] == 2
    assert res['strategies']['surge']['coverage_pct'] == 50.0

    assert res['strategies']['vcp_rule']['valid_count'] == 0
    assert res['strategies']['vcp_rule']['missing_count'] == 4
    assert res['strategies']['vcp_rule']['coverage_pct'] == 0.0


def test_fundamental_missingness_suppression_when_prices_dict_none():
    """
    CRITICAL EMPIRICAL TEST:
    Verifies that when prices_dict is None (the default when running analyze_coverage with features_df),
    NO_FUNDAMENTAL_DATA is NEVER recorded for rim_valuation or mq_factor missingness.
    Instead, 100% of missingness is classified as INSUFFICIENT_PRICE_HISTORY.
    """
    analyzer = StrategyCoverageAnalyzer()
    symbols = [f"SYM_{i}" for i in range(10)]
    df = pd.DataFrame({
        'symbol': symbols,
        'rim_score': [np.nan] * 10,
        'mq_score': [np.nan] * 10
    })
    
    # features_df has NO fundamental data for all symbols
    features_df = pd.DataFrame({
        'symbol': symbols,
        'bps': [np.nan] * 10,
        'roe': [np.nan] * 10,
        'operating_margin': [np.nan] * 10,
        'net_profit_margin': [np.nan] * 10
    })

    # When prices_dict is None:
    res = analyzer.analyze_coverage(df, features_df=features_df, prices_dict=None)
    rim_reasons = res['strategies']['rim_valuation']['reasons']
    
    # EMPIRICAL OBSERVATION:
    # Because prices_dict is None, has_price evaluates to False,
    # and the code takes 'if not has_price: no_price_cnt += 1'.
    # Thus, NO_FUNDAMENTAL_DATA is 0 and INSUFFICIENT_PRICE_HISTORY is 10.
    assert 'NO_FUNDAMENTAL_DATA' not in rim_reasons
    assert rim_reasons.get('INSUFFICIENT_PRICE_HISTORY') == 10


def test_uncomputed_strategy_classified_as_neutral():
    """
    CRITICAL EMPIRICAL TEST:
    Verifies that uncomputed strategies (NaN scores) with sufficient price history
    are classified as STRATEGY_SIGNAL_NEUTRAL rather than STRATEGY_NOT_COMPUTED.
    """
    analyzer = StrategyCoverageAnalyzer()
    symbols = ['AAPL', 'MSFT']
    df = pd.DataFrame({
        'symbol': symbols,
        'vcp_ml_score': [np.nan, np.nan],
        'reg_score': [np.nan, np.nan]
    })
    prices_dict = {sym: pd.DataFrame({'close': [100.0] * 250}) for sym in symbols}

    res = analyzer.analyze_coverage(df, prices_dict=prices_dict)
    
    vcp_reasons = res['strategies']['vcp_ml']['reasons']
    # EMPIRICAL OBSERVATION:
    # STRATEGY_NOT_COMPUTED is not a valid reason in StrategyCoverageAnalyzer.
    # Instead, missing signal is reported as STRATEGY_SIGNAL_NEUTRAL.
    assert 'STRATEGY_NOT_COMPUTED' not in vcp_reasons
    assert vcp_reasons.get('STRATEGY_SIGNAL_NEUTRAL') == 2


def test_primary_reason_first_key_bug():
    """
    CRITICAL EMPIRICAL TEST:
    Verifies that generate_coverage_report picks list(reasons.keys())[0] (insertion order)
    rather than the reason with the maximum count.
    """
    analyzer = StrategyCoverageAnalyzer()
    symbols = [f"SYM_{i}" for i in range(100)]
    df = pd.DataFrame({'symbol': symbols, 'rim_score': [np.nan] * 100})
    
    # SYM_0 has no price (< 200 rows), SYM_1..99 have price (>= 200 rows) but no fundamentals
    prices_dict = {'SYM_0': pd.DataFrame({'close': [10.0] * 10})}
    for i in range(1, 100):
        prices_dict[f'SYM_{i}'] = pd.DataFrame({'close': [10.0] * 200})
        
    features_df = pd.DataFrame({
        'symbol': symbols,
        'bps': [np.nan] * 100,
        'roe': [np.nan] * 100,
        'operating_margin': [np.nan] * 100,
        'net_profit_margin': [np.nan] * 100
    })

    res = analyzer.analyze_coverage(df, prices_dict=prices_dict, features_df=features_df)
    report_text = analyzer.generate_coverage_report(res)

    # EMPIRICAL OBSERVATION:
    # reasons dict is {'INSUFFICIENT_PRICE_HISTORY': 1, 'NO_FUNDAMENTAL_DATA': 99}
    # But generate_coverage_report picks list(reasons.keys())[0], which is INSUFFICIENT_PRICE_HISTORY!
    rim_line = [line for line in report_text.splitlines() if 'rim_valuation' in line][0]
    assert "INSUFFICIENT_PRICE_HISTORY" in rim_line
    assert "NO_FUNDAMENTAL_DATA" not in rim_line


def test_has_symbol_fundamental_data_variations():
    analyzer = StrategyCoverageAnalyzer()
    
    # 1. Empty features_df -> returns False
    assert analyzer._has_symbol_fundamental_data(None, 'AAPL') == False
    assert analyzer._has_symbol_fundamental_data(pd.DataFrame(), 'AAPL') == False

    # 2. Symbol column matching
    df_col = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT'],
        'operating_margin': [0.15, np.nan],
        'roe': [0.20, np.nan]
    })
    assert analyzer._has_symbol_fundamental_data(df_col, 'AAPL') == True
    assert analyzer._has_symbol_fundamental_data(df_col, 'MSFT') == False
    assert analyzer._has_symbol_fundamental_data(df_col, 'GOOGL') == False

    # 3. Index matching
    df_idx = pd.DataFrame({
        'operating_margin': [0.15, np.nan],
        'roe': [0.20, np.nan]
    }, index=['AAPL', 'MSFT'])
    assert analyzer._has_symbol_fundamental_data(df_idx, 'AAPL') == True
    assert analyzer._has_symbol_fundamental_data(df_idx, 'MSFT') == False
    assert analyzer._has_symbol_fundamental_data(df_idx, 'GOOGL') == False
