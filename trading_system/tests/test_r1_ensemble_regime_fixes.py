"""
trading_system/tests/test_r1_ensemble_regime_fixes.py
Comprehensive unit tests for Requirement R1 fixes and enhancements:
1. Valid 0.0 prediction scores are not discarded as missing data in EnsembleScoringEngine.
2. Raw un-mutated strategy scores with NaNs are exposed on scorer.raw_scores and ensemble_df.attrs['raw_scores'] for StrategyCoverageAnalyzer.
3. Global macro indicator retrieval (VIX, US 10Y Yield, USD/KRW FX) returns non-NaN valid values.
4. Market-specific transaction costs (KONEX 0.8%, KOSDAQ 0.5%, KOSPI 0.35%, SP500 0.10% + 0.5% slippage) and liquidity gates apply consistently.
"""

import pytest
import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
from src.data_layer.indicator_storage import MarketIndicatorStorage


def test_valid_zero_scores_not_discarded():
    """Verify that a valid 0.0 prediction score is NOT treated as missing data."""
    scorer = EnsembleScoringEngine()

    reg_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 20: [0.0, 0.20]})
    surge_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 'surge_20d': [0.0, 0.80]})

    weights = {'regression': 0.50, 'surge': 0.50}
    res = scorer.combine_predictions(
        reg_df=reg_df,
        s_df=surge_df,
        ll_df=pd.DataFrame(),
        weights=weights,
        target_horizon=20
    )

    # STOCK_A has reg_score=0.0 and surge_score=0.0.
    # Both are valid, so total_weight = 0.5 + 0.5 = 1.0.
    # ensemble_score for STOCK_A should be (0.0*0.5 + 0.0*0.5) / 1.0 = 0.0.
    # It must NOT divide by zero or become NaN.
    stock_a = res[res['symbol'] == 'STOCK_A'].iloc[0]
    assert stock_a['ensemble_score'] == 0.0
    assert not pd.isna(stock_a['ensemble_score'])

    # STOCK_B has reg_score = 0.20/0.25 = 0.80, surge_score = 0.80.
    # ensemble_score for STOCK_B should be 0.80.
    stock_b = res[res['symbol'] == 'STOCK_B'].iloc[0]
    assert pytest.approx(stock_b['ensemble_score'], abs=1e-3) == 0.80


def test_raw_scores_preserves_nans_for_coverage_analyzer():
    """Verify raw un-mutated strategy scores with NaNs are accessible for StrategyCoverageAnalyzer."""
    scorer = EnsembleScoringEngine()

    # Regression available for both stocks, Surge missing (NaN) for STOCK_B
    reg_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 20: [0.15, 0.10]})
    surge_df = pd.DataFrame({'symbol': ['STOCK_A'], 'surge_20d': [0.70]})

    ensemble_df = scorer.combine_predictions(
        reg_df=reg_df,
        s_df=surge_df,
        ll_df=pd.DataFrame(),
        target_horizon=20
    )

    # 1. Check raw_scores attribute on scorer and ensemble_df.attrs
    assert hasattr(scorer, 'raw_scores')
    raw_df = scorer.raw_scores
    assert 'raw_scores' in ensemble_df.attrs

    # 2. In raw_df, surge_score for STOCK_B must be NaN
    stock_b_raw = raw_df[raw_df['symbol'] == 'STOCK_B'].iloc[0]
    assert pd.isna(stock_b_raw['surge_score'])

    # 3. In formatted ensemble_df, surge_score is formatted to 0.0 for report display
    stock_b_formatted = ensemble_df[ensemble_df['symbol'] == 'STOCK_B'].iloc[0]
    assert stock_b_formatted['surge_score'] == 0.0

    # 4. StrategyCoverageAnalyzer using raw_scores correctly computes valid_count = 1, missing_count = 1 for surge
    cov_analyzer = StrategyCoverageAnalyzer()
    stats = cov_analyzer.analyze_coverage(ensemble_df, raw_scores=raw_df)
    surge_stats = stats['strategies']['surge']
    assert surge_stats['valid_count'] == 1
    assert surge_stats['missing_count'] == 1
    assert surge_stats['coverage_pct'] == 50.0


def test_transaction_costs_and_slippage_all_markets():
    """Verify transaction costs (KONEX 0.8%, KOSDAQ 0.5%, KOSPI 0.35%, SP500 0.10% + 0.5% slippage) apply correctly."""
    scorer = EnsembleScoringEngine()

    # Create dummy predictions for 4 markets
    df_reg = pd.DataFrame({
        'symbol': ['005930.KS', '035720.KQ', '217880.KN', 'AAPL'],
        'market': ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500'],
        20: [0.25, 0.25, 0.25, 0.25]
    })

    # High return score: ensemble_score = 1.0 -> raw expected return = 25.0%
    res = scorer.combine_predictions(
        reg_df=df_reg,
        s_df=pd.DataFrame(),
        ll_df=pd.DataFrame(),
        target_horizon=20
    )

    row_kospi = res[res['symbol'] == '005930.KS'].iloc[0]
    row_kosdaq = res[res['symbol'] == '035720.KQ'].iloc[0]
    row_konex = res[res['symbol'] == '217880.KN'].iloc[0]
    row_sp500 = res[res['symbol'] == 'AAPL'].iloc[0]

    # KOSPI cost: 0.35% + 0.5% slippage = 0.85% -> Net ret = 25.0 - 0.85 = 24.15%
    assert pytest.approx(row_kospi['ensemble_expected_return'], abs=0.05) == 24.15

    # KOSDAQ cost: 0.50% + 0.5% slippage = 1.00% -> Net ret = 25.0 - 1.00 = 24.00%
    assert pytest.approx(row_kosdaq['ensemble_expected_return'], abs=0.05) == 24.00

    # KONEX cost: 0.80% + 0.5% slippage = 1.30% -> Net ret = 25.0 - 1.30 = 23.70%
    assert pytest.approx(row_konex['ensemble_expected_return'], abs=0.05) == 23.70

    # SP500 cost: 0.10% + 0.5% slippage = 0.60% -> Net ret = 25.0 - 0.60 = 24.40%
    assert pytest.approx(row_sp500['ensemble_expected_return'], abs=0.05) == 24.40


def test_liquidity_and_preferred_stock_filter():
    """Verify preferred stocks and SPACs are zero-weighted by the liquidity gate."""
    scorer = EnsembleScoringEngine()

    df_reg = pd.DataFrame({
        'symbol': ['005930.KS', '005930우.KS', '035720.KQ', '352770.KQ'],
        'name': ['삼성전자', '삼성전자우', '카카오', '하나금융25호스팩'],
        20: [0.20, 0.20, 0.20, 0.20]
    })

    res = scorer.combine_predictions(
        reg_df=df_reg,
        s_df=pd.DataFrame(),
        ll_df=pd.DataFrame(),
        target_horizon=20
    )

    pref_stock = res[res['symbol'] == '005930우.KS'].iloc[0]
    spac_stock = res[res['symbol'] == '352770.KQ'].iloc[0]
    normal_stock = res[res['symbol'] == '005930.KS'].iloc[0]

    assert pref_stock['ensemble_score'] == 0.0
    assert spac_stock['ensemble_score'] == 0.0
    assert normal_stock['ensemble_score'] > 0.0


def test_decision_rationale_includes_costs_and_regime():
    """Verify decision rationale text output includes 2D regime and transaction cost details."""
    scorer = EnsembleScoringEngine()
    summary = scorer.get_regime_reasoning_summary('BULL_LOW_VOL', rolling_sharpes={'regression': 1.5})

    assert "[2D Market Regime & Strategy Decision Rationale]" in summary
    assert "BULL_LOW_VOL" in summary
    assert "[Transaction Costs & Liquidity Filter Rationale]" in summary
    assert "KONEX" in summary
    assert "SP500" in summary


def test_indicator_storage_latest_macro(tmp_path):
    """Verify MarketIndicatorStorage.get_latest_global_indicators retrieves macro data."""
    db_file = tmp_path / "test_macro.db"
    storage = MarketIndicatorStorage(db_path=str(db_file))

    macro_data = {
        'indices': {'^VIX': {'symbol': '^VIX', 'name': 'VIX', 'price': 19.5, 'change_pct': 2.1}},
        'fx_rates': {'USDKRW=X': {'pair': 'USDKRW=X', 'name': 'USD/KRW', 'rate': 1375.5, 'change_pct': 0.1}},
        'macro_commodities': {'^TNX': {'symbol': '^TNX', 'name': 'US10Y', 'price': 42.1, 'change_pct': -0.5}}
    }
    storage.save_indicators(macro_data, date_str="2026-07-29")

    latest = storage.get_latest_global_indicators()
    assert latest.get('^VIX') == 19.5
    assert latest.get('USDKRW=X') == 1375.5
    assert latest.get('^TNX') == 42.1
