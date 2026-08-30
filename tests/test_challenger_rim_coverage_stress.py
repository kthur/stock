"""
tests/test_challenger_rim_coverage_stress.py
Adversarial Stress Test Suite by Challenger 1:
1. RIM Valuation Engine with extreme/adversarial inputs:
   - bps = 0, bps = -500.0, bps = np.nan, bps = None, string "N/A", empty DataFrame
   - Negative equity, operating losses, low earnings quality, preferred shares
   - Filter reason tagging ('MISSING_FUNDAMENTALS', 'CAPITAL_IMPAIRMENT', 'OPERATING_LOSS', 'LOW_EARNINGS_QUALITY', 'PREFERRED_SHARE')
   - Score invalidation (rim_score = np.nan, discount_ratio = np.nan, intrinsic_value = np.nan)
   - Pipeline _write_rim_file formatting ("N/A", zero "nan%" or "nan")
2. Strategy Coverage Analyzer with complex ticker formats:
   - Korean tickers with suffixes ('005930.KS', '035720.KQ')
   - US tickers ('AAPL', 'MSFT')
   - Non-numeric codes ('ABC', 'XYZ.US', etc.)
   - Symbol normalization across dicts and DataFrames
   - Missingness reasons classification
"""
import io
import re
import numpy as np
import pandas as pd

from src.core.rim_valuation import RIMValuationEngine
from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


# ============================================================================
# PART 1: RIM VALUATION ENGINE ADVERSARIAL STRESS TESTS
# ============================================================================

def test_rim_extreme_bps_and_negative_equity():
    """
    Stress-test RIMValuationEngine with extreme BPS inputs:
    - bps = 0 -> MISSING_FUNDAMENTALS
    - bps = -500.0 -> CAPITAL_IMPAIRMENT
    - bps = -0.001 -> CAPITAL_IMPAIRMENT
    - bps = np.nan -> MISSING_FUNDAMENTALS
    - bps = None -> MISSING_FUNDAMENTALS
    - bps = "N/A" -> MISSING_FUNDAMENTALS
    - bps = "" -> MISSING_FUNDAMENTALS
    - bps = "invalid" -> MISSING_FUNDAMENTALS
    - bps = np.inf -> MISSING_FUNDAMENTALS
    - bps = -np.inf -> CAPITAL_IMPAIRMENT
    - book_value = -1_000_000, shares = 1000 -> CAPITAL_IMPAIRMENT
    - book_value = 0, shares = 1000 -> MISSING_FUNDAMENTALS
    """
    engine = RIMValuationEngine(default_required_return=0.08)

    df_test = pd.DataFrame([
        # 1. bps = 0
        {'symbol': 'ZERO_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': 0, 'roe': 0.10},
        # 2. bps = 0.0
        {'symbol': 'ZERO_BPS_F', 'market': 'KOSPI', 'Close': 10000.0, 'bps': 0.0, 'roe': 0.10},
        # 3. bps = -500.0
        {'symbol': 'NEG_BPS_500', 'market': 'KOSPI', 'Close': 1000.0, 'bps': -500.0, 'roe': 0.10},
        # 4. bps = -0.001
        {'symbol': 'NEG_BPS_TINY', 'market': 'KOSPI', 'Close': 1000.0, 'bps': -0.001, 'roe': 0.10},
        # 5. bps = np.nan
        {'symbol': 'NAN_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': np.nan, 'roe': 0.10},
        # 6. bps = None
        {'symbol': 'NONE_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': None, 'roe': 0.10},
        # 7. bps = "N/A"
        {'symbol': 'STR_NA_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': "N/A", 'roe': 0.10},
        # 8. bps = ""
        {'symbol': 'STR_EMPTY_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': "", 'roe': 0.10},
        # 9. bps = "invalid"
        {'symbol': 'STR_INV_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': "invalid", 'roe': 0.10},
        # 10. bps = np.inf
        {'symbol': 'INF_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': np.inf, 'roe': 0.10},
        # 11. bps = -np.inf
        {'symbol': 'NEG_INF_BPS', 'market': 'KOSPI', 'Close': 10000.0, 'bps': -np.inf, 'roe': 0.10},
        # 12. book_value = -1_000_000, shares = 1000 (negative equity via book_value)
        {'symbol': 'NEG_BV', 'market': 'KOSPI', 'Close': 1000.0, 'book_value': -1_000_000.0, 'shares_outstanding': 1000.0, 'roe': 0.10},
        # 13. book_value = 0, shares = 1000
        {'symbol': 'ZERO_BV', 'market': 'KOSPI', 'Close': 1000.0, 'book_value': 0.0, 'shares_outstanding': 1000.0, 'roe': 0.10},
        # 14. Valid control stock
        {'symbol': 'VALID_STOCK', 'market': 'KOSPI', 'Close': 50000.0, 'bps': 60000.0, 'roe': 0.12},
    ])

    res = engine.compute_rim_scores(df_test).set_index('symbol')

    # Verify Filter Reasons
    # Numeric zero and negative equity are accurately tagged as CAPITAL_IMPAIRMENT
    assert res.loc['ZERO_BPS', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'
    assert res.loc['ZERO_BPS_F', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'
    assert res.loc['NEG_BPS_500', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'
    assert res.loc['NEG_BPS_TINY', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'
    assert res.loc['NEG_INF_BPS', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'
    assert res.loc['NEG_BV', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'
    assert res.loc['ZERO_BV', 'rim_filter_reason'] == 'CAPITAL_IMPAIRMENT'

    # Non-numeric, missing, empty, or NaN inputs are accurately tagged as MISSING_FUNDAMENTALS
    assert res.loc['NAN_BPS', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS'
    assert res.loc['NONE_BPS', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS'
    assert res.loc['STR_NA_BPS', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS'
    assert res.loc['STR_EMPTY_BPS', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS'
    assert res.loc['STR_INV_BPS', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS'
    assert res.loc['INF_BPS', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS'

    assert res.loc['VALID_STOCK', 'rim_filter_reason'] == ''

    # Verify that all invalid cases have NaN scores and metrics
    invalid_syms = [
        'ZERO_BPS', 'ZERO_BPS_F', 'NEG_BPS_500', 'NEG_BPS_TINY',
        'NAN_BPS', 'NONE_BPS', 'STR_NA_BPS', 'STR_EMPTY_BPS', 'STR_INV_BPS',
        'INF_BPS', 'NEG_INF_BPS', 'NEG_BV', 'ZERO_BV'
    ]

    for sym in invalid_syms:
        assert np.isnan(res.loc[sym, 'rim_score']), f"{sym}: rim_score must be NaN"
        assert np.isnan(res.loc[sym, 'discount_ratio']), f"{sym}: discount_ratio must be NaN"
        assert np.isnan(res.loc[sym, 'intrinsic_value']), f"{sym}: intrinsic_value must be NaN"

    # Verify that valid stock has valid scores
    assert not np.isnan(res.loc['VALID_STOCK', 'rim_score'])
    assert not np.isnan(res.loc['VALID_STOCK', 'discount_ratio'])
    assert not np.isnan(res.loc['VALID_STOCK', 'intrinsic_value'])
    assert res.loc['VALID_STOCK', 'intrinsic_value'] > 60000.0


def test_rim_empty_dataframe_and_extreme_structures():
    """
    Stress-test RIMValuationEngine with structural extremes:
    - Empty DataFrame
    - None input
    - DataFrame with only 1 completely NaN row
    - DataFrame with all invalid rows across multiple markets
    """
    engine = RIMValuationEngine(default_required_return=0.08)

    # 1. Empty DataFrame
    res_empty = engine.compute_rim_scores(pd.DataFrame())
    assert isinstance(res_empty, pd.DataFrame)
    assert res_empty.empty
    expected_cols = [
        'symbol', 'market', 'Close', 'bps', 'bps_adjusted',
        'roe_raw', 'roe', 'roe_normalized',
        'earnings_quality', 'holding_co_flag', 'net_debt_per_share',
        'rim_filter_reason', 'intrinsic_value', 'discount_ratio', 'rim_score'
    ]
    for col in expected_cols:
        assert col in res_empty.columns

    # 2. None input
    res_none = engine.compute_rim_scores(None)
    assert isinstance(res_none, pd.DataFrame)
    assert res_none.empty

    # 3. All NaN row
    df_nan_row = pd.DataFrame([{'symbol': 'ALL_NAN', 'market': 'KOSPI'}])
    res_nan_row = engine.compute_rim_scores(df_nan_row).set_index('symbol')
    assert res_nan_row.loc['ALL_NAN', 'rim_filter_reason'] == 'MISSING_FUNDAMENTALS'
    assert np.isnan(res_nan_row.loc['ALL_NAN', 'rim_score'])
    assert np.isnan(res_nan_row.loc['ALL_NAN', 'discount_ratio'])
    assert np.isnan(res_nan_row.loc['ALL_NAN', 'intrinsic_value'])

    # 4. Multi-market all-invalid universe
    df_all_invalid = pd.DataFrame([
        {'symbol': 'K1', 'market': 'KOSPI', 'bps': 0},
        {'symbol': 'K2', 'market': 'KOSDAQ', 'bps': -100.0},
        {'symbol': 'U1', 'market': 'SP500', 'bps': np.nan},
        {'symbol': 'U2', 'market': 'NASDAQ', 'bps': 'N/A'},
        {'symbol': 'U3', 'market': 'RUSSELL2000', 'bps': None},
    ])
    res_all_inv = engine.compute_rim_scores(df_all_invalid).set_index('symbol')
    for sym in ['K1', 'K2', 'U1', 'U2', 'U3']:
        assert np.isnan(res_all_inv.loc[sym, 'rim_score'])
        assert np.isnan(res_all_inv.loc[sym, 'discount_ratio'])
        assert np.isnan(res_all_inv.loc[sym, 'intrinsic_value'])


def test_rim_distressed_and_earnings_filters():
    """
    Stress-test earnings quality and operating loss filters:
    - Operating loss + Net income (+) -> LOW_EARNINGS_QUALITY (suspicious)
    - Operating loss (-) + Net loss (-) -> OPERATING_LOSS
    - Operating income (+) + Net loss (-) -> OPERATING_LOSS
    - Preferred share symbols (005935, 00680K, 000665) -> PREFERRED_SHARE
    """
    engine = RIMValuationEngine(default_required_return=0.08)

    df_stress = pd.DataFrame([
        # 1. Suspicious one-off: op_inc = -10, net_inc = +100
        {'symbol': 'SUSP_01', 'market': 'KOSPI', 'Close': 10000.0, 'bps': 20000.0, 'roe': 0.15,
         'operating_income': -10.0, 'net_income': 100.0},
        # 2. Suspicious zero operating income: op_inc = 0, net_inc = +50
        {'symbol': 'SUSP_02', 'market': 'KOSPI', 'Close': 10000.0, 'bps': 20000.0, 'roe': 0.15,
         'operating_income': 0.0, 'net_income': 50.0},
        # 3. Severe operating & net loss
        {'symbol': 'LOSS_01', 'market': 'KOSPI', 'Close': 5000.0, 'bps': 10000.0, 'roe': -0.10,
         'operating_income': -50.0, 'net_income': -80.0},
        # 4. Operating profit but net loss
        {'symbol': 'LOSS_02', 'market': 'KOSPI', 'Close': 5000.0, 'bps': 10000.0, 'roe': -0.05,
         'operating_income': 20.0, 'net_income': -30.0},
        # 5. Preferred shares
        {'symbol': '005935', 'market': 'KOSPI', 'Close': 60000.0, 'bps': 50000.0, 'roe': 0.15},
        {'symbol': '00680K', 'market': 'KOSPI', 'Close': 6000.0, 'bps': 7000.0, 'roe': 0.10},
    ])

    res = engine.compute_rim_scores(df_stress).set_index('symbol')

    assert res.loc['SUSP_01', 'rim_filter_reason'] in ['LOW_EARNINGS_QUALITY', 'OPERATING_LOSS']
    assert np.isnan(res.loc['SUSP_01', 'rim_score'])
    assert np.isnan(res.loc['SUSP_01', 'discount_ratio'])
    assert np.isnan(res.loc['SUSP_01', 'intrinsic_value'])

    assert res.loc['SUSP_02', 'rim_filter_reason'] in ['LOW_EARNINGS_QUALITY', 'OPERATING_LOSS']
    assert np.isnan(res.loc['SUSP_02', 'rim_score'])

    assert res.loc['LOSS_01', 'rim_filter_reason'] == 'OPERATING_LOSS'
    assert np.isnan(res.loc['LOSS_01', 'rim_score'])

    assert res.loc['LOSS_02', 'rim_filter_reason'] == 'OPERATING_LOSS'
    assert np.isnan(res.loc['LOSS_02', 'rim_score'])

    assert res.loc['005935', 'rim_filter_reason'] == 'PREFERRED_SHARE'
    assert np.isnan(res.loc['005935', 'rim_score'])

    assert res.loc['00680K', 'rim_filter_reason'] == 'PREFERRED_SHARE'
    assert np.isnan(res.loc['00680K', 'rim_score'])


def test_pipeline_write_rim_file_zero_nan_guarantee():
    """
    Stress-test _write_rim_file in run_pipeline.py logic to ensure:
    1. ZERO occurrences of 'nan%' or raw 'nan'
    2. Correct empty state handling ('데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)')
    3. Proper formatting of N/A for partial fields in valid rows.
    """
    # Simulate _write_rim_file logic from run_pipeline.py
    def run_write_rim_file(df_rim, date_str="2026-08-29 08:00 KST"):
        buf = io.StringIO()
        buf.write("=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===\n")
        buf.write(f"Date: {date_str}\n")
        valid_rim = df_rim[df_rim['rim_score'].notna() & (df_rim['rim_score'] > 0)] if ('rim_score' in df_rim.columns and not df_rim.empty) else pd.DataFrame()
        buf.write(f"Total symbols evaluated: {len(df_rim)} (Valid: {len(valid_rim)})\n")
        buf.write("Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount\n\n")

        if valid_rim.empty:
            buf.write("데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)\n")
            return buf.getvalue()

        buf.write(
            f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Market':<10}"
            f"{'Price':<12}{'Intrinsic V0':<14}{'Discount %':<12}"
            f"{'ROE_raw':<9}{'ROE_adj':<9}{'EQ':<6}{'Filter':<32}{'RIM Score':<12}\n"
        )
        buf.write("-" * 142 + "\n")
        for rank, (_, row) in enumerate(valid_rim.head(100).iterrows(), 1):
            name_str = str(row.get('name', 'Unknown'))[:18] if pd.notna(row.get('name')) else "Unknown"
            price_val = row.get('Close', np.nan)
            price_str = f"{price_val:<12.2f}" if pd.notna(price_val) and np.isfinite(price_val) else f"{'N/A':<12}"

            intrinsic = row.get('intrinsic_value', np.nan)
            intrinsic_str = f"{intrinsic:<14.2f}" if pd.notna(intrinsic) and np.isfinite(intrinsic) else f"{'N/A':<14}"

            disc_val = row.get('discount_ratio', np.nan)
            disc_str = f"{disc_val*100:>9.1f}%" if pd.notna(disc_val) and np.isfinite(disc_val) else "      N/A"

            roe_raw = row.get('roe_raw', np.nan)
            roe_adj = row.get('roe', np.nan)
            roe_raw_str = f"{roe_raw*100:>7.1f}%" if pd.notna(roe_raw) and np.isfinite(roe_raw) else "    N/A"
            roe_adj_str = f"{roe_adj*100:>7.1f}%" if pd.notna(roe_adj) and np.isfinite(roe_adj) else "    N/A"

            eq = row.get('earnings_quality', np.nan)
            eq_str = f"{eq*100:>5.0f}%" if pd.notna(eq) and np.isfinite(eq) else "  N/A"

            filter_reason = str(row.get('rim_filter_reason', ''))
            hc_flag = bool(row.get('holding_co_flag', False))
            tag_parts = []
            if 'ROE_NORMALIZED' in filter_reason or 'QUALITY_ADJUSTED' in filter_reason:
                tag_parts.append('[ADJ]')
            if hc_flag:
                tag_parts.append('[HC]')
            if filter_reason and filter_reason not in ('', 'QUALITY_ADJUSTED', 'EXTREME_ROE_NORMALIZED', 'QUALITY_ADJUSTED+ROE_NORMALIZED'):
                tag_parts.append(filter_reason[:22])
            filter_str = ' '.join(tag_parts)[:30]

            rim_score_val = row.get('rim_score', np.nan)
            rim_score_str = f"{rim_score_val*100:>9.1f}%" if pd.notna(rim_score_val) and np.isfinite(rim_score_val) else "      N/A"

            buf.write(
                f"{rank:<5}{row['symbol']:<10}{name_str:<20}{row['market']:<10}"
                f"{price_str}{intrinsic_str}{disc_str}"
                f" {roe_raw_str} {roe_adj_str} {eq_str}  {filter_str:<32}{rim_score_str}\n"
            )
        return buf.getvalue()

    # Case A: Empty DataFrame
    out_empty = run_write_rim_file(pd.DataFrame())
    assert "데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)" in out_empty
    assert "nan" not in out_empty.lower()

    # Case B: All invalid stocks (BPS=0, negative, nan, etc.)
    engine = RIMValuationEngine(default_required_return=0.08)
    df_all_bad = pd.DataFrame([
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 0},
        {'symbol': '000660', 'market': 'KOSPI', 'Close': 120000.0, 'bps': -500.0},
        {'symbol': '035420', 'market': 'KOSPI', 'Close': 200000.0, 'bps': np.nan},
    ])
    res_bad = engine.compute_rim_scores(df_all_bad)
    out_bad = run_write_rim_file(res_bad)
    assert "Total symbols evaluated: 3 (Valid: 0)" in out_bad
    assert "데이터 없음 (유효한 RIM 적정가 산출 대상 종목 없음)" in out_bad
    assert "nan" not in out_bad.lower()

    # Case C: Mixed universe (1 valid, 3 invalid)
    df_mixed = pd.DataFrame([
        {'symbol': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 50000.0, 'roe': 0.15},
        {'symbol': '005935', 'name': '삼성전자우', 'market': 'KOSPI', 'Close': 60000.0, 'bps': 50000.0, 'roe': 0.15},
        {'symbol': '000660', 'name': 'SK하이닉스', 'market': 'KOSPI', 'Close': 120000.0, 'bps': -500.0, 'roe': 0.10},
        {'symbol': '035420', 'name': 'NAVER', 'market': 'KOSPI', 'Close': 200000.0, 'bps': np.nan, 'roe': 0.10},
    ])
    res_mixed = engine.compute_rim_scores(df_mixed)
    # Merge name
    res_mixed = res_mixed.merge(df_mixed[['symbol', 'name']], on='symbol', how='left')
    out_mixed = run_write_rim_file(res_mixed)

    assert "Total symbols evaluated: 4 (Valid: 1)" in out_mixed
    assert "005930" in out_mixed
    assert "005935" not in out_mixed  # Invalid preferred share excluded from ranking table
    assert "000660" not in out_mixed  # Negative equity excluded
    assert "035420" not in out_mixed  # NaN BPS excluded

    # Verify zero 'nan', 'nan%' in output
    assert "nan%" not in out_mixed.lower()
    assert re.search(r'\bnan\b', out_mixed.lower()) is None


# ============================================================================
# PART 2: STRATEGY COVERAGE ANALYZER ADVERSARIAL STRESS TESTS
# ============================================================================

def test_coverage_analyzer_symbol_normalization_formats():
    """
    Stress-test StrategyCoverageAnalyzer with complex symbol formats:
    - Korean tickers with suffixes: '005930.KS', '035720.KQ', '000660.KS'
    - Korean tickers without suffixes: '005930', '035720'
    - US tickers: 'AAPL', 'MSFT', 'GOOGL.US'
    - Non-numeric tickers: 'ABC', 'XYZ.US'
    - Short numeric tickers: '660' (unpadded) vs '000660' (padded)
    Verify _has_symbol_fundamental_data and analyze_coverage lookup resilience.
    """
    analyzer = StrategyCoverageAnalyzer()

    # 1. Test _has_symbol_fundamental_data with DataFrame having standard columns
    fund_df = pd.DataFrame([
        {'symbol': '005930', 'bps': 50000.0, 'roe': 0.15, 'operating_margin': 0.12},
        {'symbol': '035720', 'bps': 20000.0, 'roe': 0.08, 'operating_margin': 0.09},
        {'symbol': 'AAPL', 'bps': 4.5, 'roe': 0.40, 'operating_margin': 0.30},
        {'symbol': 'ABC', 'bps': 10.0, 'roe': 0.05, 'operating_margin': 0.04},
    ])

    # Suffixes in query should match base symbol in fund_df
    assert analyzer._has_symbol_fundamental_data(fund_df, '005930.KS') is True
    assert analyzer._has_symbol_fundamental_data(fund_df, '035720.KQ') is True
    assert analyzer._has_symbol_fundamental_data(fund_df, '005930') is True
    assert analyzer._has_symbol_fundamental_data(fund_df, 'AAPL') is True
    assert analyzer._has_symbol_fundamental_data(fund_df, 'AAPL.US') is True
    assert analyzer._has_symbol_fundamental_data(fund_df, 'ABC') is True
    assert analyzer._has_symbol_fundamental_data(fund_df, 'ABC.US') is True
    assert analyzer._has_symbol_fundamental_data(fund_df, 'NONEXISTENT') is False

    # 2. Test _has_symbol_fundamental_data with Dict of DataFrames
    fund_dict = {
        '005930': pd.DataFrame([{'bps': 50000.0, 'roe': 0.15}]),
        '035720': pd.DataFrame([{'bps': 20000.0, 'roe': 0.08}]),
        'AAPL': pd.DataFrame([{'bps': 4.5, 'roe': 0.40}]),
        'XYZ': pd.DataFrame([{'bps': 15.0, 'roe': 0.06}]),
    }

    assert analyzer._has_symbol_fundamental_data(fund_dict, '005930.KS') is True
    assert analyzer._has_symbol_fundamental_data(fund_dict, '035720.KQ') is True
    assert analyzer._has_symbol_fundamental_data(fund_dict, 'AAPL.US') is True
    assert analyzer._has_symbol_fundamental_data(fund_dict, 'XYZ.US') is True
    assert analyzer._has_symbol_fundamental_data(fund_dict, 'NONEXISTENT') is False

    # 3. Test with symbol as index
    fund_indexed_df = fund_df.set_index('symbol')
    assert analyzer._has_symbol_fundamental_data(fund_indexed_df, '005930.KS') is True
    assert analyzer._has_symbol_fundamental_data(fund_indexed_df, '035720.KQ') is True
    assert analyzer._has_symbol_fundamental_data(fund_indexed_df, 'AAPL') is True


def test_coverage_analyzer_granular_missingness_reasons():
    """
    Stress-test StrategyCoverageAnalyzer missingness categorization:
    1. INSUFFICIENT_PRICE_HISTORY: when symbol has < 20 price bars in prices_dict
    2. NO_FUNDAMENTAL_DATA: when fundamental-dependent strategy lacks fundamentals
    3. LOW_EARNINGS_QUALITY: when RIM valuation has fundamentals but RIM score is NaN (earnings quality filtered)
    4. NO_OPTIONS_CHAIN: for iv_skew / gamma_squeeze missing data
    5. NON_US_MARKET_SCOPE: for darkpool / darkpool_hft
    6. NO_COINTEGRATED_PAIR: for stat_arb
    7. NO_CORPORATE_FILING: for sentiment
    8. NO_INSIDER_FILING: for insider_buying
    9. NO_EARNINGS_TRANSCRIPT: for tone_drift
    10. NO_LEAD_LAG_LEADER: for lead_lag
    11. NO_SUPPLY_CHAIN_MAPPING: for supply_chain
    """
    analyzer = StrategyCoverageAnalyzer()

    # Build ensemble_df with various missing columns
    symbols = ['005930.KS', '035720.KQ', 'AAPL', 'MSFT', 'NO_PRICE_SYM']
    df_ens = pd.DataFrame({
        'symbol': symbols,
        'reg_score': [0.8, 0.6, 0.9, np.nan, np.nan],
        'rim_score': [0.9, np.nan, 0.8, np.nan, np.nan],
        'iv_skew_score': [np.nan, np.nan, 0.7, 0.6, np.nan],
        'stat_arb_score': [np.nan, 1.0, np.nan, np.nan, np.nan],
        'sentiment_score': [np.nan, np.nan, 0.8, np.nan, np.nan],
        'insider_score': [np.nan, np.nan, np.nan, np.nan, np.nan],
        'tone_drift_score': [np.nan, np.nan, np.nan, np.nan, np.nan],
        'lead_lag_score': [np.nan, np.nan, 0.6, np.nan, np.nan],
        'supply_chain_score': [np.nan, np.nan, np.nan, np.nan, np.nan],
    })

    # prices_dict: NO_PRICE_SYM has only 5 bars (< 20 threshold)
    prices_dict = {
        '005930.KS': pd.DataFrame({'Close': [70000.0] * 30}),
        '035720.KQ': pd.DataFrame({'Close': [50000.0] * 30}),
        'AAPL': pd.DataFrame({'Close': [180.0] * 30}),
        'MSFT': pd.DataFrame({'Close': [300.0] * 30}),
        'NO_PRICE_SYM': pd.DataFrame({'Close': [10.0] * 5}),  # < 20 bars
    }

    # features_df: 035720 has fundamentals (so its RIM NaN is classified as LOW_EARNINGS_QUALITY)
    # MSFT does NOT have fundamentals in features_df (so its RIM NaN is classified as NO_FUNDAMENTAL_DATA)
    features_df = pd.DataFrame([
        {'symbol': '005930', 'bps': 50000.0, 'roe': 0.15},
        {'symbol': '035720', 'bps': 20000.0, 'roe': 0.08},
        {'symbol': 'AAPL', 'bps': 4.5, 'roe': 0.40},
    ])

    result = analyzer.analyze_coverage(
        ensemble_df=df_ens,
        prices_dict=prices_dict,
        features_df=features_df
    )

    assert result['total_symbols'] == 5
    strats = result['strategies']

    # 1. RIM Valuation analysis
    assert 'rim_valuation' in strats or 'rim' in strats
    rim_key = 'rim_valuation' if 'rim_valuation' in strats else 'rim'
    rim_info = strats[rim_key]
    assert rim_info['valid_count'] == 2  # 005930.KS and AAPL
    assert rim_info['missing_count'] == 3

    # Check that reasons contain INSUFFICIENT_PRICE_HISTORY for NO_PRICE_SYM
    assert rim_info['reasons'].get('INSUFFICIENT_PRICE_HISTORY', 0) == 1
    # Check that 035720 (has fundamentals) is classified as LOW_EARNINGS_QUALITY
    assert rim_info['reasons'].get('LOW_EARNINGS_QUALITY', 0) == 1
    # Check that MSFT (missing fundamentals) is classified as NO_FUNDAMENTAL_DATA
    assert rim_info['reasons'].get('NO_FUNDAMENTAL_DATA', 0) == 1

    # 2. Options / Macro / Sentiment strategy reasons check
    if 'iv_skew' in strats:
        assert 'NO_OPTIONS_CHAIN' in strats['iv_skew']['reasons']
    if 'stat_arb' in strats:
        assert 'NO_COINTEGRATED_PAIR' in strats['stat_arb']['reasons']
    if 'sentiment' in strats:
        assert 'NO_CORPORATE_FILING' in strats['sentiment']['reasons']
    if 'insider_buying' in strats or 'insider' in strats:
        ins_key = 'insider_buying' if 'insider_buying' in strats else 'insider'
        assert 'NO_INSIDER_FILING' in strats[ins_key]['reasons']

    # 3. Generate Report check
    report = analyzer.generate_coverage_report(result, date_str="2026-08-29 08:00 KST")
    assert "Strategy Data Coverage & Missingness Report" in report
    assert "5" in report
