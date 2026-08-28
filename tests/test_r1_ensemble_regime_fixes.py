"""
trading_system/tests/test_r1_ensemble_regime_fixes.py
Comprehensive unit tests for Requirement R1 fixes and enhancements:
1. Dynamic weight rescaling for missing strategy scores per symbol (active weights sum to 100%).
2. Valid 0.0 prediction scores are not discarded as missing data in EnsembleScoringEngine.
3. Raw un-mutated strategy scores with NaNs are exposed on scorer.raw_scores and ensemble_df.attrs['raw_scores'] for StrategyCoverageAnalyzer.
4. Precision Order Book Market Impact execution model applied across all markets.
5. Global macro indicator retrieval (VIX, US 10Y Yield, USD/KRW FX) returns non-NaN valid values.
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

    reg_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 'reg_score': [0.0, 0.80]})
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

    # STOCK_B has reg_score = 0.80, surge_score = 0.80.
    # ensemble_score for STOCK_B should be 0.80.
    stock_b = res[res['symbol'] == 'STOCK_B'].iloc[0]
    assert pytest.approx(stock_b['ensemble_score'], abs=1e-3) == 0.80


def test_dynamic_reweighting_partial_missingness():
    """Verify dynamic re-weighting rescales active strategy weights to sum to 1.0 (100%) when data is missing."""
    scorer = EnsembleScoringEngine()

    # Create dataset where STOCK_A has all 3 strategies, STOCK_B has missing (NaN) iv_skew
    reg_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 'reg_score': [0.80, 0.80]})  # reg_score = 0.80
    surge_df = pd.DataFrame({'symbol': ['STOCK_A', 'STOCK_B'], 'surge_20d': [0.60, 0.60]})  # surge_score = 0.60
    iv_skew_df = pd.DataFrame({'symbol': ['STOCK_A'], 'iv_skew_score': [0.40]})  # missing for STOCK_B

    weights = {'regression': 0.40, 'surge': 0.30, 'iv_skew': 0.30}
    res = scorer.combine_predictions(
        reg_df=reg_df,
        s_df=surge_df,
        iv_skew_df=iv_skew_df,
        weights=weights,
        target_horizon=20
    )

    stock_a = res[res['symbol'] == 'STOCK_A'].iloc[0]
    stock_b = res[res['symbol'] == 'STOCK_B'].iloc[0]

    # STOCK_A score: 0.40*(0.80) + 0.30*(0.60) + 0.30*(0.40) = 0.6200
    assert pytest.approx(stock_a['ensemble_score'], abs=1e-3) == 0.620

    # STOCK_B score: Active weights = 0.40 + 0.30 = 0.70. Rescaled reg=0.4/0.7, surge=0.3/0.7 (sum = 1.0)
    # Weighted score = (0.40*0.80 + 0.30*0.60) / 0.70 = 0.50 / 0.70 = 0.7142857
    assert pytest.approx(stock_b['ensemble_score'], abs=1e-3) == 0.7143


def test_dynamic_reweighting_omitted_strategy_dataframes():
    """Verify system rescales present strategy weights to 100% when strategy DataFrames are omitted."""
    scorer = EnsembleScoringEngine()

    reg_df = pd.DataFrame({'symbol': ['STOCK_A'], 'reg_score': [0.80]})  # reg_score = 0.80
    surge_df = pd.DataFrame({'symbol': ['STOCK_A'], 'surge_20d': [0.50]})

    weights = {'regression': 0.60, 'surge': 0.40, 'lstm': 0.20}
    # lstm_df is omitted (None / empty)
    res = scorer.combine_predictions(
        reg_df=reg_df,
        s_df=surge_df,
        weights=weights,
        target_horizon=20
    )

    stock_a = res[res['symbol'] == 'STOCK_A'].iloc[0]
    # Active weights sum = 0.60 + 0.40 = 1.00.
    # Score = (0.60*0.80 + 0.40*0.50) / 1.00 = 0.680
    assert pytest.approx(stock_a['ensemble_score'], abs=1e-3) == 0.680


def test_dynamic_reweighting_full_missing_fallback():
    """Verify fallback to 0.0 when all strategy predictions are NaN for a symbol."""
    scorer = EnsembleScoringEngine()

    reg_df = pd.DataFrame({'symbol': ['NULL_STOCK'], 20: [np.nan]})
    res = scorer.combine_predictions(
        reg_df=reg_df,
        target_horizon=20
    )

    row = res[res['symbol'] == 'NULL_STOCK'].iloc[0]
    assert row['ensemble_score'] == 0.0
    assert not pd.isna(row['ensemble_score'])


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
    """Verify market-specific microstructure execution cost modeling across KOSPI, KOSDAQ, SP500, NASDAQ, and RUSSELL2000."""
    scorer = EnsembleScoringEngine()
    scorer.score_normalizer = None

    # Create dummy predictions for 5 markets with equal turnover & volatility to isolate base spread friction
    df_reg = pd.DataFrame({
        'symbol': ['005930.KS', '035720.KQ', 'AAPL', 'MSFT', 'IWM'],
        'market': ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'],
        'volume': [100_000, 100_000, 100_000, 100_000, 100_000],
        'close': [70_000, 50_000, 100, 100, 100],
        'volatility_20d': [0.015, 0.020, 0.015, 0.015, 0.015],
        20: [0.25, 0.25, 0.25, 0.25, 0.25]
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
    row_sp500 = res[res['symbol'] == 'AAPL'].iloc[0]
    row_nasdaq = res[res['symbol'] == 'MSFT'].iloc[0]
    row_russell = res[res['symbol'] == 'IWM'].iloc[0]

    # Verify all expected returns are positive and properly differentiated by market friction
    assert row_sp500['ensemble_expected_return'] > row_nasdaq['ensemble_expected_return']
    assert row_nasdaq['ensemble_expected_return'] > row_russell['ensemble_expected_return']
    assert row_sp500['ensemble_expected_return'] > row_kospi['ensemble_expected_return']
    assert row_kospi['ensemble_expected_return'] > row_kosdaq['ensemble_expected_return']


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
    assert "Microstructure Execution & Market Impact Model Active" in summary
    assert "Order Size Hypothesis (Q)" in summary


def test_indicator_storage_latest_macro(tmp_path):
    """Verify MarketIndicatorStorage.get_latest_global_indicators retrieves macro data."""
    db_file = tmp_path / "test_macro.db"
    storage = MarketIndicatorStorage(db_path=str(db_file))

    macro_data = {
        'indices': {'^VIX': {'symbol': '^VIX', 'name': 'VIX', 'price': 19.5, 'change_pct': 2.1}},
        'fx_rates': {'USDKRW=X': {'pair': 'USDKRW=X', 'name': 'USD/KRW', 'rate': 1375.5, 'change_pct': 0.1}},
        'macro_commodities': {'^TNX': {'symbol': '^TNX', 'name': 'US10Y', 'price': 4.21, 'change_pct': -0.5}}
    }
    storage.save_indicators(macro_data, date_str="2026-07-29")

    latest = storage.get_latest_global_indicators()
    assert latest.get('^VIX') == 19.5
    assert latest.get('USDKRW=X') == 1375.5
    assert latest.get('^TNX') == 4.21


def test_regime_shift_ema_acceleration():
    """Verify that regime shifts accelerate EMA weight smoothing (alpha=1.0 on regime change)."""
    scorer = EnsembleScoringEngine()
    scorer.alpha_smoothing = 0.2

    # Step 1: Call with BULL regime
    rolling_sharpes = {'regression': 2.0, 'surge': 2.0}
    w1 = scorer.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime='BULL_LOW_VOL')

    # Step 2: Call with BEAR regime (shift detected)
    w2 = scorer.compute_dynamic_weights_from_sharpe(rolling_sharpes, regime='BEAR_HIGH_VOL')

    # On regime shift, eff_alpha is 1.0, so w2 immediately adopts BEAR base weight distribution
    # without lagging behind previous weights.
    assert scorer._prev_regime == 'BEAR_HIGH_VOL'
    assert w2 != w1


def test_vcp_rule_list_of_dicts_keeps_real_symbols():
    """Live-money guard: run_pipeline passes vcp_results as a list of dicts; the old
    code converted each dict via str() producing garbage symbols like
    "{'is_vcp': False, ..., 'symbol': 'MSFT'}". Symbols must be extracted properly."""
    scorer = EnsembleScoringEngine()

    vcp_results = [
        {'symbol': 'MSFT', 'is_vcp': True, 'vcp_score': 85.0},
        {'symbol': '005930', 'is_vcp': False, 'vcp_score': 45.0},
        {'symbol': 'AAPL', 'is_vcp': True, 'vcp_score': 90.0},
    ]
    reg_df = pd.DataFrame({'symbol': ['MSFT', '005930', 'AAPL'], 'reg_score': [0.5, 0.5, 0.5]})

    res = scorer.calculate_ensemble_score(
        regime='BULL_LOW_VOL',
        regression_df=reg_df,
        surge_df=pd.DataFrame(),
        lead_lag_df=pd.DataFrame(),
        vcp_ml_df=pd.DataFrame(),
        vcp_rule_df=vcp_results,
        target_horizon=20,
    )

    assert 'MSFT' in set(res['symbol'])
    assert '005930' in set(res['symbol'])
    assert 'AAPL' in set(res['symbol'])
    assert not any('{' in str(s) for s in res['symbol'])

    msft = res[res['symbol'] == 'MSFT'].iloc[0]
    # Isotonic calibrator may adjust the raw 0.85 score slightly; the key guard is
    # that the score derives from the vcp_score of the SAME symbol (not a dict string).
    assert msft['vcp_rule_score'] == pytest.approx(0.85, abs=0.05)
    aapl = res[res['symbol'] == 'AAPL'].iloc[0]
    assert aapl['vcp_rule_score'] == pytest.approx(0.90, abs=0.05)


def test_krx_indicator_merge_shifts_us_origin_columns():
    """Live-money guard: for KRX symbols, US-origin indicators (vix_change,
    sp500_change, ...) must be lagged by 1 business day so training never sees
    US closes that occur ~14.5h AFTER the KRX close of the same date."""
    from src.ai.prediction_model import OnDevicePredictionModel

    model = OnDevicePredictionModel(model_dir='trading_system/models')

    dates = pd.date_range('2026-01-05', periods=6, freq='B')  # Mon..Mon (5 business days)
    df = pd.DataFrame({'Close': [100 + i for i in range(6)],
                       'Volume': [1000] * 6}, index=dates)
    indicator_df = pd.DataFrame({
        'vix_change': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        'sp500_change': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        'kospi_change': [0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
    }, index=dates)

    # KRX symbol (shift US columns)
    kr_merged = model._merge_indicator_history(df, indicator_df, shift_us_indicators=True)
    # US symbol (no shift)
    us_merged = model._merge_indicator_history(df, indicator_df, shift_us_indicators=False)

    kr_last = kr_merged.iloc[-1]
    us_last = us_merged.iloc[-1]

    # US symbol sees the same-day US close...
    assert us_last['vix_change'] == 6.0
    assert us_last['sp500_change'] == 0.6
    # ...while KRX symbol only sees the PREVIOUS day's US close (shift by 1 row)
    assert kr_last['vix_change'] == 5.0
    assert kr_last['sp500_change'] == 0.5
    # KRX-origin indicators are NOT shifted for KRX symbols
    assert kr_last['kospi_change'] == 0.06
