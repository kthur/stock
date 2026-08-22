"""
fuzz_stress_test_rim.py
Deep fuzzing & Monte Carlo random stress test for RIMValuationEngine.
"""
import sys
import os
import random
import numpy as np
import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
trading_system_dir = os.path.join(repo_root, "trading_system")
if trading_system_dir not in sys.path:
    sys.path.insert(0, trading_system_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.core.rim_valuation import RIMValuationEngine

def run_fuzz_test(n_samples=2000):
    print(f"Running Monte Carlo Fuzzing on RIMValuationEngine with {n_samples} random records...")
    engine = RIMValuationEngine()

    markets = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000', None, 'UNKNOWN']
    names = ['삼성전자', '카카오홀딩스', 'SK스퀘어지주', 'Apple Inc.', 'Tesla', None, '', 12345]
    sector_codes = ['6020', 'CGLC', '20202020', '1010', None, 9999]

    rows = []
    for i in range(n_samples):
        # Pick random fields
        row = {
            'symbol': f"SYM_{i}" if random.random() > 0.05 else None,
            'market': random.choice(markets),
            'name': random.choice(names),
            'sector_code': random.choice(sector_codes),
        }

        # Random Price
        p_choice = random.random()
        if p_choice < 0.1:
            row['Close'] = np.nan
        elif p_choice < 0.2:
            row['Close'] = random.choice([0.0, -10.0, np.inf, -np.inf])
        else:
            row['Close'] = random.uniform(1.0, 500000.0)

        # Random BPS / book_value / shares
        b_choice = random.random()
        if b_choice < 0.2:
            row['bps'] = np.nan
        elif b_choice < 0.3:
            row['bps'] = random.choice([0.0, -100.0, np.inf, -np.inf])
        elif b_choice < 0.6:
            row['bps'] = random.uniform(1.0, 200000.0)

        if random.random() > 0.4:
            row['book_value'] = random.choice([np.nan, 0.0, -500.0, np.inf, random.uniform(1e5, 1e12)])
        if random.random() > 0.4:
            row['shares_outstanding'] = random.choice([np.nan, 0.0, -1000.0, np.inf, random.uniform(1e4, 1e9)])

        # Random ROE / EPS
        r_choice = random.random()
        if r_choice < 0.2:
            row['roe'] = np.nan
        elif r_choice < 0.3:
            row['roe'] = random.choice([np.inf, -np.inf, 100.0, -50.0])
        else:
            row['roe'] = random.uniform(-0.8, 1.5)

        if random.random() > 0.5:
            row['eps'] = random.choice([np.nan, random.uniform(-5000, 20000)])

        # Operating income / Net income
        if random.random() > 0.3:
            row['operating_income'] = random.choice([np.nan, np.inf, -np.inf, random.uniform(-1e10, 1e11)])
        if random.random() > 0.3:
            row['net_income'] = random.choice([np.nan, np.inf, -np.inf, random.uniform(-1e10, 1e11)])

        # Debt / cash
        if random.random() > 0.5:
            row['total_debt'] = random.choice([np.nan, random.uniform(0, 1e11)])
        if random.random() > 0.5:
            row['cash_equivalents'] = random.choice([np.nan, random.uniform(0, 1e11)])

        rows.append(row)

    df_fuzz = pd.DataFrame(rows)
    print(f"Generated DataFrame with shape {df_fuzz.shape}. Passing into compute_rim_scores...")

    res = engine.compute_rim_scores(df_fuzz)
    assert isinstance(res, pd.DataFrame), "Output is not a DataFrame"
    assert len(res) == n_samples, f"Output length {len(res)} != input {n_samples}"

    # Invariant checks:
    # 1. No discount_ratio should be > 5.0 (clipped to 5.0) or < -0.90
    valid_discs = res['discount_ratio'].dropna()
    assert (valid_discs <= 5.0 + 1e-6).all(), f"Found discount_ratio > 5.0: {valid_discs[valid_discs > 5.0]}"
    assert (valid_discs >= -0.90 - 1e-6).all(), f"Found discount_ratio < -0.90: {valid_discs[valid_discs < -0.90]}"

    # 2. No valid rim_score when bps is NaN or <= 0
    bad_bps_mask = res['bps'].isna() | (res['bps'] <= 0)
    bad_bps_scores = res.loc[bad_bps_mask, 'rim_score'].dropna()
    assert len(bad_bps_scores) == 0, f"Found {len(bad_bps_scores)} scores with invalid BPS: {bad_bps_scores}"

    # 3. No valid rim_score when rim_filter_reason is in ['LOW_EARNINGS_QUALITY', 'PREFERRED_SHARE', 'OPERATING_LOSS']
    invalid_reason_mask = res['rim_filter_reason'].isin(['LOW_EARNINGS_QUALITY', 'PREFERRED_SHARE', 'OPERATING_LOSS'])
    invalid_reason_scores = res.loc[invalid_reason_mask, 'rim_score'].dropna()
    assert len(invalid_reason_scores) == 0, f"Found {len(invalid_reason_scores)} scores with invalid filter reason"

    # 4. Valid rim_score must be between 0.0 and 1.0
    valid_scores = res['rim_score'].dropna()
    assert (valid_scores >= 0.0).all() and (valid_scores <= 1.0).all(), "Score outside [0.0, 1.0]"

    # 5. ROE normalized should never exceed ABSOLUTE_ROE_CAP
    valid_roes = res['roe'].dropna()
    assert (valid_roes <= 0.25 + 1e-6).all(), f"Found roe exceeding ABSOLUTE_ROE_CAP: {valid_roes[valid_roes > 0.25]}"

    print(f"  -> All {n_samples} fuzz records passed strict invariant checks!")


def test_compute_scores_interface():
    print("\nTesting compute_scores polymorphic interface...")
    engine = RIMValuationEngine()

    # 1. prices_dict with dataframe
    prices_dict = {
        '005930': pd.DataFrame({'Close': [68000.0, 69000.0, 70000.0]}),
        'AAPL': pd.DataFrame({'Close': [170.0, 175.0, 180.0]})
    }
    fundamentals_dict = {
        '005930': {'bps': 50000.0, 'roe': 0.15, 'market': 'KOSPI'},
        'AAPL': {'bps': 50.0, 'roe': 0.25, 'market': 'SP500'}
    }
    res1 = engine.compute_scores(prices_dict=prices_dict, fundamentals_dict=fundamentals_dict)
    assert len(res1) == 2
    assert not res1['rim_score'].isna().all()

    # 2. empty/None inputs to compute_scores
    res2 = engine.compute_scores(None)
    assert isinstance(res2, pd.DataFrame)

    res3 = engine.compute_scores(features_df=pd.DataFrame())
    assert isinstance(res3, pd.DataFrame)
    print("  -> compute_scores polymorphic interface passed!")

if __name__ == "__main__":
    run_fuzz_test(2000)
    test_compute_scores_interface()
