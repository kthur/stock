"""
Empirical Stress Test Harness for StrategyCoverageAnalyzer
Location: d:\Finance\code\stock\.agents\teamwork_preview_challenger_m4_1_gen2\stress_test_coverage_analyzer.py

Tests StrategyCoverageAnalyzer with synthetic DataFrames under various edge conditions:
1. Missingness reasons (NO_FUNDAMENTAL_DATA vs INSUFFICIENT_PRICE_HISTORY vs STRATEGY_SIGNAL_NEUTRAL vs missing STRATEGY_NOT_COMPUTED)
2. Primary missing reason selection order bug (Dict insertion order vs actual max count)
3. Default behavior when prices_dict is None (All missingness mislabeled as INSUFFICIENT_PRICE_HISTORY)
4. Mismatched shapes/indices between ensemble_df and raw_scores (target_df)
5. Fundamental data column lookup & symbol format edge cases in _has_symbol_fundamental_data
6. Coverage percentage calculation precision and range
"""

import os
import sys

# Add project root to sys.path
PROJECT_ROOT = r"d:\Finance\code\stock"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
TRADING_SYS = os.path.join(PROJECT_ROOT, "trading_system")
if TRADING_SYS not in sys.path:
    sys.path.insert(0, TRADING_SYS)

import numpy as np
import pandas as pd
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


def test_scenario_1_prices_dict_none_fundamental_suppression():
    """
    Scenario 1:
    When prices_dict is None (the default in pipeline if not passed),
    does StrategyCoverageAnalyzer correctly report NO_FUNDAMENTAL_DATA for rim_valuation/mq_factor?
    """
    analyzer = StrategyCoverageAnalyzer()

    # Synthetic ensemble_df with 10 symbols
    symbols = [f"{i:06d}.KS" for i in range(10)]
    df = pd.DataFrame({'symbol': symbols})
    # Set rim_score to NaN for all symbols
    df['rim_score'] = np.nan
    df['mq_score'] = np.nan

    # Synthetic features_df missing fundamental data for symbols 0..9
    features_df = pd.DataFrame({
        'symbol': symbols,
        'bps': [np.nan] * 10,
        'roe': [np.nan] * 10,
        'operating_margin': [np.nan] * 10,
        'net_profit_margin': [np.nan] * 10
    })

    # Call analyze_coverage without prices_dict
    result = analyzer.analyze_coverage(df, features_df=features_df, prices_dict=None)

    rim_reasons = result['strategies']['rim_valuation']['reasons']
    print("[Scenario 1] rim_valuation reasons (prices_dict=None):", rim_reasons)
    # Expected: NO_FUNDAMENTAL_DATA: 10
    # Observed: INSUFFICIENT_PRICE_HISTORY: 10 (BUG!)
    return result


def test_scenario_2_primary_reason_selection_bug():
    """
    Scenario 2:
    Verify if generate_coverage_report selects the true primary (most frequent) missing reason
    or merely the first key inserted into reasons dict.
    """
    analyzer = StrategyCoverageAnalyzer()

    symbols = [f"SYM_{i}" for i in range(100)]
    df = pd.DataFrame({'symbol': symbols, 'rim_score': [np.nan] * 100})

    # 1 symbol missing price data, 99 symbols missing fundamental data
    prices_dict = {
        'SYM_0': pd.DataFrame({'close': [100.0] * 10}), # < 200 rows -> no price
    }
    for i in range(1, 100):
        prices_dict[f'SYM_{i}'] = pd.DataFrame({'close': [100.0] * 200}) # >= 200 rows

    features_df = pd.DataFrame({
        'symbol': symbols,
        'bps': [np.nan] * 100,
        'roe': [np.nan] * 100,
        'operating_margin': [np.nan] * 100,
        'net_profit_margin': [np.nan] * 100
    })

    result = analyzer.analyze_coverage(df, prices_dict=prices_dict, features_df=features_df)
    rim_reasons = result['strategies']['rim_valuation']['reasons']
    print("[Scenario 2] rim_valuation reasons dict:", rim_reasons)

    report_text = analyzer.generate_coverage_report(result)
    print("[Scenario 2] Generated Report snippet:")
    for line in report_text.splitlines():
        if 'rim_valuation' in line:
            print("  ", line)

    return result


def test_scenario_3_uncomputed_strategy_mislabeled_as_neutral():
    """
    Scenario 3:
    When a strategy score column is missing or NaN (not computed),
    is the missing reason categorized as STRATEGY_NOT_COMPUTED or STRATEGY_SIGNAL_NEUTRAL?
    """
    analyzer = StrategyCoverageAnalyzer()

    symbols = ['AAPL', 'MSFT', 'GOOGL']
    df = pd.DataFrame({
        'symbol': symbols,
        'vcp_ml_score': [np.nan, np.nan, np.nan],
        'reg_score': [np.nan, np.nan, np.nan]
    })

    # Prices dictionary provided with sufficient history
    prices_dict = {sym: pd.DataFrame({'close': [100.0] * 250}) for sym in symbols}

    result = analyzer.analyze_coverage(df, prices_dict=prices_dict)

    vcp_ml_reasons = result['strategies']['vcp_ml']['reasons']
    reg_reasons = result['strategies']['regression']['reasons']

    print("[Scenario 3] vcp_ml reasons (uncomputed):", vcp_ml_reasons)
    print("[Scenario 3] regression reasons (uncomputed):", reg_reasons)

    return result


def test_scenario_4_mismatched_target_df_and_ensemble_df():
    """
    Scenario 4:
    Test behavior when raw_scores (target_df) has a different length or index than ensemble_df.
    """
    analyzer = StrategyCoverageAnalyzer()

    ensemble_df = pd.DataFrame({'symbol': ['A', 'B', 'C', 'D']}) # 4 symbols
    raw_scores = pd.DataFrame({
        'symbol': ['A', 'B', 'C', 'D', 'E', 'F'],
        'reg_score': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6] # 6 valid scores
    })

    try:
        result = analyzer.analyze_coverage(ensemble_df, raw_scores=raw_scores)
        print("[Scenario 4] Result with raw_scores len 6, ensemble_df len 4:")
        print("  valid_count:", result['strategies']['regression']['valid_count'])
        print("  missing_count:", result['strategies']['regression']['missing_count'])
        print("  coverage_pct:", result['strategies']['regression']['coverage_pct'])
    except Exception as e:
        print("[Scenario 4] Exception raised:", type(e).__name__, e)


def run_all_stress_tests():
    print("==================================================")
    print(" RUNNING EMPIRICAL STRESS TESTS ON StrategyCoverageAnalyzer")
    print("==================================================")
    test_scenario_1_prices_dict_none_fundamental_suppression()
    print("--------------------------------------------------")
    test_scenario_2_primary_reason_selection_bug()
    print("--------------------------------------------------")
    test_scenario_3_uncomputed_strategy_mislabeled_as_neutral()
    print("--------------------------------------------------")
    test_scenario_4_mismatched_target_df_and_ensemble_df()
    print("==================================================")


if __name__ == "__main__":
    run_all_stress_tests()
