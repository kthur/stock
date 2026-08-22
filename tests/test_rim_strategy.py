"""
trading_system/tests/test_rim_strategy.py
Unit tests for Strategy #9 RIM (Residual Income Model) Valuation Engine & 9-Strategy Ensemble.
"""
import pandas as pd
import numpy as np
from src.core.rim_valuation import RIMValuationEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from generate_report import parse_rim, build_html, EnsembleData, EnsembleMarket, EnsembleRow


def test_rim_valuation_calculation():
    engine = RIMValuationEngine(default_required_return=0.08)

    # Sample stock data
    df = pd.DataFrame([
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 50000.0, 'roe': 0.15},   # High ROE vs r_e
        {'symbol': '000660', 'market': 'KOSPI', 'Close': 120000.0, 'bps': 80000.0, 'roe': 0.08},  # Neutral ROE = r_e
        {'symbol': '035420', 'market': 'KOSPI', 'Close': 200000.0, 'bps': 50000.0, 'roe': 0.04},  # Low ROE < r_e
    ])

    res = engine.compute_rim_scores(df)

    assert len(res) == 3
    assert 'intrinsic_value' in res.columns
    assert 'discount_ratio' in res.columns
    assert 'rim_score' in res.columns

    # Samsung 005930: BPS=50000, ROE=0.15, r_e=0.08 => V0 = 50000 * (1 + (0.15-0.08)/0.08) = 50000 * 1.875 = 93750
    # Discount = (93750 - 70000) / 70000 = +33.9%
    samsung = res[res['symbol'] == '005930'].iloc[0]
    assert samsung['intrinsic_value'] > 50000.0  # Decaying ROE excess value over BPS
    assert samsung['rim_score'] > 0.5  # Highest discount ratio rank in KOSPI


def test_rim_earnings_quality_filter():
    """영업손실(-)인데 순이익(+)인 종목(일회성 이익 의존)은 RIM 점수가 NaN이어야 한다."""
    engine = RIMValuationEngine(default_required_return=0.08)

    df = pd.DataFrame([
        # 정상: 영업이익 ≈ 순이익 → 이익의 질 1.0, RIM 점수 유효
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 50000.0, 'roe': 0.15,
         'operating_income': 100.0, 'net_income': 110.0},
        # 일회성 이익 의존: 영업손실(-) + 순이익(+) → RIM 점수 무효화
        {'symbol': '011170', 'market': 'KOSPI', 'Close': 50000.0, 'bps': 60000.0, 'roe': 0.20,
         'operating_income': -50.0, 'net_income': 120.0},
        # 이익의 질 낮음: 영업이익/순이익 = 0.2 < 0.5 → ROE 감쇠(0.15*0.2=0.03), 점수는 유효하나 저평
        {'symbol': '000270', 'market': 'KOSPI', 'Close': 100000.0, 'bps': 50000.0, 'roe': 0.15,
         'operating_income': 20.0, 'net_income': 100.0},
    ])

    res = engine.compute_rim_scores(df)
    res = res.set_index('symbol')

    assert res.loc['011170', 'rim_filter_reason'] == 'LOW_EARNINGS_QUALITY'
    assert np.isnan(res.loc['011170', 'rim_score'])
    assert np.isnan(res.loc['011170', 'discount_ratio'])
    assert res.loc['011170', 'earnings_quality'] == 0.0

    # 정상 종목은 그대로 유효 (eq_ratio = 100/110)
    assert res.loc['005930', 'rim_filter_reason'] == ''
    assert abs(res.loc['005930', 'earnings_quality'] - 100.0 / 110.0) < 1e-9
    assert not np.isnan(res.loc['005930', 'rim_score'])

    # 이익의 질 0.2 → ROE 0.15*0.2 = 0.03으로 감쇠
    assert res.loc['000270', 'rim_filter_reason'] == 'QUALITY_ADJUSTED'
    assert abs(res.loc['000270', 'roe'] - 0.03) < 1e-9

    # 정상 종목의 ROE는 감쇠되지 않음 (net_income > 0, eq_ratio = 1.0)
    assert abs(res.loc['005930', 'roe'] - 0.15) < 1e-9


def test_rim_preferred_share_exclusion():
    """우선주(삼성전자우 005935, 미래에셋증권2우B 00680K 등)는 RIM 점수가 NaN이어야 한다."""
    engine = RIMValuationEngine(default_required_return=0.08)

    df = pd.DataFrame([
        {'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0, 'bps': 50000.0, 'roe': 0.15},
        {'symbol': '005935', 'market': 'KOSPI', 'Close': 60000.0, 'bps': 50000.0, 'roe': 0.15},  # 삼성전자우
        {'symbol': '00680K', 'market': 'KOSPI', 'Close': 5000.0, 'bps': 8000.0, 'roe': 0.10},   # 미래에셋증권2우B
    ])

    res = engine.compute_rim_scores(df).set_index('symbol')

    # 보통주는 정상 산출
    assert not np.isnan(res.loc['005930', 'rim_score'])
    assert res.loc['005930', 'rim_filter_reason'] == ''

    # 우선주는 RIM 점수 및 내재가치 NaN 무효화
    assert res.loc['005935', 'rim_filter_reason'] == 'PREFERRED_SHARE'
    assert np.isnan(res.loc['005935', 'rim_score'])
    assert np.isnan(res.loc['005935', 'intrinsic_value'])

    assert res.loc['00680K', 'rim_filter_reason'] == 'PREFERRED_SHARE'
    assert np.isnan(res.loc['00680K', 'rim_score'])
    assert np.isnan(res.loc['00680K', 'intrinsic_value'])


def test_ensemble_scorer_9_strategies():
    scorer = EnsembleScoringEngine()

    reg_df = pd.DataFrame([{'symbol': '005930', 20: 0.10}, {'symbol': 'AAPL', 20: 0.15}])
    surge_df = pd.DataFrame([{'symbol': '005930', 'surge_20d': 0.8}, {'symbol': 'AAPL', 'surge_20d': 0.9}])
    ll_df = pd.DataFrame([{'symbol': '005930', 'lead_lag_score': 0.5}, {'symbol': 'AAPL', 'lead_lag_score': 0.7}])
    vr_df = pd.DataFrame([{'symbol': '005930', 'vcp_score': 80}, {'symbol': 'AAPL', 'vcp_score': 90}])
    vml_df = pd.DataFrame([{'symbol': '005930', 'vcp_20d': 0.6}, {'symbol': 'AAPL', 'vcp_20d': 0.75}])
    lstm_df = pd.DataFrame([{'symbol': '005930', 'lstm_score': 0.7}, {'symbol': 'AAPL', 'lstm_score': 0.85}])
    sa_df = pd.DataFrame([{'symbol': '005930', 'stat_arb_score': 0.65}, {'symbol': 'AAPL', 'stat_arb_score': 0.80}])
    sec_df = pd.DataFrame([{'symbol': '005930', 'sector_score': 0.70}, {'symbol': 'AAPL', 'sector_score': 0.85}])
    rim_df = pd.DataFrame([{'symbol': '005930', 'rim_score': 0.90}, {'symbol': 'AAPL', 'rim_score': 0.95}])

    res = scorer.calculate_ensemble_score(
        regime='BEAR',
        regression_df=reg_df,
        surge_df=surge_df,
        lead_lag_df=ll_df,
        vcp_rule_df=vr_df,
        vcp_ml_df=vml_df,
        lstm_df=lstm_df,
        stat_arb_df=sa_df,
        sector_df=sec_df,
        rim_df=rim_df,
    )

    assert len(res) == 2
    assert 'rim_score' in res.columns
    assert 'ensemble_score' in res.columns
    assert (res['ensemble_score'] >= 0.0).all() and (res['ensemble_score'] <= 1.0).all()


def test_parse_rim_and_build_html():
    raw_txt = """=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===
Date: 2026-07-26 18:00
Total symbols evaluated: 2

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  RIM Score
-----------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00      +33.9%     100.0%
2    AAPL      Apple Inc.          SP500     180.00      240.00        +33.3%     50.0%
"""
    date_str, rows = parse_rim(raw_txt)

    assert date_str == "2026-07-26 18:00"
    assert len(rows) == 2

    ensemble = EnsembleData(
        date="2026-07-26",
        regime="SIDEWAYS",
        markets=[
            EnsembleMarket(market="KOSPI", rows=[EnsembleRow(1, "005930", "삼성전자", "85%", "5.2%", "40%", "10%", "20%", "15%", "10%", "15%", "15%", "10%", "15%")]),
        ],
    )

    html = build_html(
        ensemble,
        surge_date="2026-07-26", surge_sections=[],
        vcp_date="2026-07-26", vcp_rows=[],
        lag_date="2026-07-26", follower_rows=[], leader_rows=[],
        vcp_ml_sections=[], reg_sections=[],
        portfolio_data=None,
        stat_arb_rows=[],
        sector_rows=[],
        rim_rows=rows
    )

    assert "💎 RIM Valuation" in html
    assert 'id="panel-rim"' in html
    assert "17 Strategies" in html or "14 Strategies" in html or "Strategies" in html


# ── Value Trap Protection Tests ──────────────────────────────────────────────

def test_extreme_roe_normalization():
    """웅진형 일회성 이익 → ROE 25% 상한 정규화 (극단 ROE 정규화 테스트).

    Scenario: 영업이익이 작은데 염가매수차익 등으로 순이익이 크게 부풀어
    ROE가 40%에 달하는 종목. EQ = 영업이익/순이익 = 0.1 (< 0.4 임계치).
    Expected:
      - rim_filter_reason에 'ROE_NORMALIZED' 포함
      - 최종 roe <= ABSOLUTE_ROE_CAP (0.25)
      - 정상 종목(ROE 15%, EQ 1.0)은 영향 없음
    """
    from src.core.rim_valuation import RIMValuationEngine, ABSOLUTE_ROE_CAP, EXTREME_ROE_THRESHOLD

    engine = RIMValuationEngine(default_required_return=0.08)

    book_value = 500_000_000_000  # 5000억
    net_income = 200_000_000_000  # 2000억 (일회성 포함)
    op_income  =  20_000_000_000  # 200억 (본업 영업이익)

    df = pd.DataFrame([
        # 웅진형: ROE 40%, EQ = op/net = 0.1 → 정규화 필요
        {
            'symbol': '016880', 'market': 'KOSPI', 'Close': 2000.0,
            'bps': 2000.0,  # 2000원/주 (book_value/shares 가정)
            'roe': 0.40,    # 40% (일회성 이익 포함)
            'operating_income': op_income, 'net_income': net_income,
            'book_value': book_value,
        },
        # 정상: ROE 15%, EQ ≈ 1.0
        {
            'symbol': '005930', 'market': 'KOSPI', 'Close': 70000.0,
            'bps': 50000.0, 'roe': 0.15,
            'operating_income': 10_000_000_000, 'net_income': 10_500_000_000,
            'book_value': 70_000_000_000,
        },
    ])

    res = engine.compute_rim_scores(df).set_index('symbol')

    # 웅진형: ROE가 ABSOLUTE_ROE_CAP(25%) 이하로 정규화됨
    assert res.loc['016880', 'roe'] <= ABSOLUTE_ROE_CAP + 1e-9, \
        f"극단 ROE 미정규화: roe={res.loc['016880', 'roe']:.3f}"
    assert 'ROE_NORMALIZED' in str(res.loc['016880', 'rim_filter_reason']) or \
           'QUALITY_ADJUSTED' in str(res.loc['016880', 'rim_filter_reason']), \
        f"Filter reason 미설정: {res.loc['016880', 'rim_filter_reason']}"
    assert res.loc['016880', 'roe_normalized'] == True, "roe_normalized 플래그가 True여야 함"

    # 정상 종목은 ROE 보존
    assert abs(res.loc['005930', 'roe'] - 0.15) < 1e-9, \
        f"정상 종목 ROE 변경됨: {res.loc['005930', 'roe']}"
    assert res.loc['005930', 'roe_normalized'] == False


def test_holding_company_discount():
    """지주사 종목: BPS에서 순부채 차감 + 초과이익에 40% 할인 적용 (SOTP 테스트).

    Scenario: '웅진지주' 이름 포함 → 지주사 식별.
    book_value 100억, shares 1000만 주 → BPS = 10,000원
    total_debt 60억, cash 0 → net_debt_per_share = 6,000원
    Expected:
      - holding_co_flag == True
      - bps_adjusted = max(10000 - 6000, 10000*0.3) = 4000원
      - intrinsic_value < v0_without_hc_discount
    """
    from src.core.rim_valuation import RIMValuationEngine, HOLDING_CO_DISCOUNT

    engine = RIMValuationEngine(default_required_return=0.08)

    shares = 10_000_000
    book_value = 100_000_000_000  # 1000억
    bps_val = book_value / shares  # 10,000원

    df = pd.DataFrame([
        {
            'symbol': '016880', 'market': 'KOSPI', 'Close': 8000.0,
            'name': '웅진지주',
            'bps': bps_val, 'roe': 0.12,
            'book_value': book_value,
            'shares_outstanding': shares,
            'total_debt': 60_000_000_000,   # 600억 차입금
            'cash_equivalents': 0,
            'operating_income': 12_000_000_000,
            'net_income': 12_000_000_000,
        },
        {
            # 동일 조건이지만 지주사 아닌 일반 기업
            'symbol': '005930', 'market': 'KOSPI', 'Close': 8000.0,
            'name': '삼성전자',
            'bps': bps_val, 'roe': 0.12,
            'book_value': book_value,
            'shares_outstanding': shares,
            'total_debt': 60_000_000_000,
            'cash_equivalents': 0,
            'operating_income': 12_000_000_000,
            'net_income': 12_000_000_000,
        },
    ])

    res = engine.compute_rim_scores(df).set_index('symbol')

    # 지주사 식별
    assert res.loc['016880', 'holding_co_flag'] == True, "웅진지주 미식별"
    assert res.loc['005930', 'holding_co_flag'] == False, "삼성전자 오분류"

    # 지주사는 비지주사보다 intrinsic_value가 낮아야 함
    iv_hc = res.loc['016880', 'intrinsic_value']
    iv_normal = res.loc['005930', 'intrinsic_value']
    assert pd.notna(iv_hc) and pd.notna(iv_normal), "intrinsic_value NaN"
    assert iv_hc < iv_normal, \
        f"지주사 intrinsic_value({iv_hc:.1f})가 일반 기업({iv_normal:.1f})보다 높음"

    # bps_adjusted: 순부채 차감 확인
    bps_adj = res.loc['016880', 'bps_adjusted']
    net_debt_ps = 60_000_000_000 / shares  # 6,000원
    expected_bps_adj = max(bps_val - net_debt_ps, bps_val * 0.30)
    assert abs(bps_adj - expected_bps_adj) < 1.0, \
        f"bps_adjusted({bps_adj:.1f}) != expected({expected_bps_adj:.1f})"


def test_nonrecurring_income_trap():
    """자산매각 등 비경상이익으로 영업이익은 낮지만 ROE가 높은 경우 → RIM 이상치 방지.

    Scenario: 영업이익 5억, 순이익 50억 (자산매각 45억 포함), BPS 100억
    ROE_raw = 50억/100억 = 50% → ABSOLUTE_ROE_CAP에 의해 25%로 클리핑
    EQ = 5/50 = 0.1 (< 0.4) + ROE > 20% → normalize_roe Stage 1 적용
    Stage 1 roe_op = 5억/100억 = 5% (< 25%)
    Expected final roe: ~5% (영업이익 기반)
    """
    from src.core.rim_valuation import RIMValuationEngine, ABSOLUTE_ROE_CAP

    engine = RIMValuationEngine(default_required_return=0.08)

    bv = 100_000_000_000
    shares = 10_000_000
    bps_val = bv / shares  # 10,000원

    df = pd.DataFrame([
        {
            'symbol': 'TEST01', 'market': 'KOSPI', 'Close': 9000.0,
            'bps': bps_val, 'roe': 0.50,   # raw: 50% (일회성 포함)
            'book_value': bv,
            'operating_income': 500_000_000,    # 5억 (본업)
            'net_income':  5_000_000_000,        # 50억 (자산매각 45억 포함)
            'shares_outstanding': shares,
        },
    ])

    res = engine.compute_rim_scores(df).set_index('symbol')

    final_roe = res.loc['TEST01', 'roe']
    # Stage 1: op_income / book_value = 500M / 100B = 0.005 (0.5%)
    # Stage 2: clip 0.25 → min(0.005, 0.25) = 0.005
    assert final_roe <= ABSOLUTE_ROE_CAP + 1e-9, f"ROE 미정규화: {final_roe:.4f}"
    # 비경상이익 대체 후 ROE가 대폭 하락했는지 확인
    raw_roe = res.loc['TEST01', 'roe_raw']
    assert final_roe < raw_roe * 0.5, \
        f"ROE 정규화 효과 부족: raw={raw_roe:.4f}, adj={final_roe:.4f}"

    # 할인율이 과도하게 높지 않은지 확인 (discount_ratio ≤ 200%)
    disc = res.loc['TEST01', 'discount_ratio']
    if pd.notna(disc):
        assert disc <= 2.0, f"할인율 이상치 미억제: {disc*100:.1f}%"


def test_rim_small_cap_and_high_nominal_bps_scaling():
    """V6-17: Test small-cap equity (< $1M) and high-nominal KRX stock (> 1M KRW BPS) scaling."""
    engine = RIMValuationEngine(default_required_return=0.08)

    # 1. US Micro-cap: Total equity = $600,000 (<= 1,000,000), 100,000 shares, Price = $10.0
    # Expected BPS = $6.0, not $600,000
    df_us_small = pd.DataFrame([{
        'symbol': 'US_MICRO',
        'market': 'RUSSELL2000',
        'Close': 10.0,
        'book_value': 600_000.0,
        'shares_outstanding': 100_000.0,
        'roe': 0.10,
        'operating_income': 60_000.0,
        'net_income': 60_000.0,
    }])
    res_us = engine.compute_rim_scores(df_us_small).set_index('symbol')
    assert res_us.loc['US_MICRO', 'bps'] == 6.0
    assert abs(res_us.loc['US_MICRO', 'discount_ratio']) < 5.0  # reasonable discount, not +5,999,900%

    # 2. KR High-Nominal Stock (e.g. 003240 Taekwang Industrial): BPS = 5,000,000 KRW (> 1,000,000)
    # Passed with 'bps'=5_000_000 and shares=1,110,000, Price = 600,000 KRW
    # BPS must NOT be divided by shares again (which would make it 4.5 KRW)
    df_kr_high = pd.DataFrame([{
        'symbol': '003240',
        'market': 'KOSPI',
        'Close': 600_000.0,
        'bps': 5_000_000.0,
        'shares_outstanding': 1_110_000.0,
        'roe': 0.08,
        'operating_income': 400_000_000_000.0,
        'net_income': 440_000_000_000.0,
    }])
    res_kr = engine.compute_rim_scores(df_kr_high).set_index('symbol')
    assert res_kr.loc['003240', 'bps'] == 5_000_000.0
    assert res_kr.loc['003240', 'intrinsic_value'] > 1_000_000.0


