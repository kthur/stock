"""
Smoke test: 금융 전문가 제언 2가지 구현 검증
① US10Y-US5Y 장단기 금리 역전 → YIELD_INVERSION 감지
② WTI + USD/KRW 동시 상승 → INFLATION_SHOCK 감지
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from src.analysis.regime_detector import MarketRegimeDetector

def make_base_df(n=60) -> pd.DataFrame:
    """기본 지표 데이터프레임 생성."""
    idx = pd.date_range('2024-01-01', periods=n, freq='B')
    return pd.DataFrame({
        'sp500_change': np.random.normal(0.05, 1.0, n),
        'vix_change': np.random.normal(2.0, 1.0, n),
        'vix_raw': np.full(n, 18.0),
        'us10y': np.full(n, 4.0),
        'us5y': np.full(n, 3.8),
        'us3m_yield': np.full(n, 5.2),
        'usdkrw_change': np.random.normal(0.0, 0.3, n),
        'wti_change': np.random.normal(0.0, 1.5, n),
        'kr10y': np.full(n, 3.5),
        'kr3y': np.full(n, 3.0),
        'us10y_us5y_spread': np.full(n, 0.2),
        'kr_us_10y_spread': np.full(n, -0.5),
        'kr_yield_curve': np.full(n, 0.5),
        'inflation_shock_index': np.full(n, 0.5),
    }, index=idx)


def test_normal_expansion():
    """정상 확장 환경 → NEUTRAL_EXPANSION"""
    rd = MarketRegimeDetector()
    df = make_base_df()
    rd.train(df)
    result = rd.predict_3d_macro_regime(df)
    assert result['macro_label'] in ('NEUTRAL_EXPANSION', 'HIGH_YIELD_BULL', 'HIGH_YIELD_BEAR'), \
        f"Expected expansion regime, got {result['macro_label']}"
    print(f"✅ NORMAL_EXPANSION test: macro_label={result['macro_label']}")


def test_yield_inversion():
    """US10Y < US5Y (역전) → YIELD_INVERSION 감지"""
    rd = MarketRegimeDetector()
    df = make_base_df()
    # 금리 역전: US10Y 3.8% < US5Y 4.2%
    df['us10y'] = 3.8
    df['us5y'] = 4.2
    df['us10y_us5y_spread'] = 3.8 - 4.2  # -0.4 (역전)
    rd.train(df)
    result = rd.predict_3d_macro_regime(df)
    assert result['macro_label'] == 'YIELD_INVERSION', \
        f"Expected YIELD_INVERSION, got {result['macro_label']}"
    print(f"✅ YIELD_INVERSION test: macro_label={result['macro_label']}, "
          f"combo_3d={result['combo_3d_label']}")


def test_us2y_yield_inversion():
    """US10Y < US2Y (2년물 정석 역전) → YIELD_INVERSION 감지"""
    rd = MarketRegimeDetector()
    df = make_base_df()
    df['us10y'] = 3.8
    df['us2y'] = 4.3  # 2년물 금리 높음 (역전)
    df['us10y_us2y_spread'] = 3.8 - 4.3  # -0.5
    rd.train(df)
    result = rd.predict_3d_macro_regime(df)
    assert result['macro_label'] == 'YIELD_INVERSION', \
        f"Expected YIELD_INVERSION via US2Y, got {result['macro_label']}"
    print(f"✅ US2Y YIELD_INVERSION test: macro_label={result['macro_label']}")


def test_inflation_shock():
    """WTI + USD/KRW 동시 상승 → INFLATION_SHOCK 감지"""
    rd = MarketRegimeDetector()
    df = make_base_df()
    # 유가 +3%, 원달러 +2% → 인플레이션 충격 지수 > 2.0
    df['wti_change'] = 3.0
    df['usdkrw_change'] = 2.0
    df['inflation_shock_index'] = 5.0  # 유가 + 환율 동시 급등
    rd.train(df)
    result = rd.predict_3d_macro_regime(df)
    assert result['macro_label'] == 'INFLATION_SHOCK', \
        f"Expected INFLATION_SHOCK, got {result['macro_label']}"
    print(f"✅ INFLATION_SHOCK test: macro_label={result['macro_label']}, "
          f"combo_3d={result['combo_3d_label']}")


def test_gmm_feature_count():
    """GMM Feature 개수: 기존 6 → 10개로 확장 확인"""
    rd = MarketRegimeDetector()
    df = make_base_df()
    features = rd._prepare_features(df)
    expected_features = [
        'sp500_ret_roll', 'sp500_vol_roll',
        'vix_level', 'us10y_level', 'us_yield_spread',
        'usdkrw_ret_roll', 'kr_us_spread', 'kr_yield_curve',
        'wti_ret_roll', 'inflation_shock'
    ]
    for feat in expected_features:
        assert feat in features.columns, f"Feature '{feat}' missing! Actual: {list(features.columns)}"
    print(f"✅ GMM Feature count test: {len(features.columns)} features: {list(features.columns)}")


def test_ensemble_macro_modifier_keys():
    """앙상블 MACRO_WEIGHT_MODIFIERS에 INFLATION_SHOCK, YIELD_INVERSION 포함 확인"""
    from src.ai.ensemble_scorer import EnsembleScoringEngine
    eng = EnsembleScoringEngine()
    assert 'INFLATION_SHOCK' in eng.MACRO_WEIGHT_MODIFIERS, "INFLATION_SHOCK modifier missing!"
    assert 'YIELD_INVERSION' in eng.MACRO_WEIGHT_MODIFIERS, "YIELD_INVERSION modifier missing!"
    print(f"✅ Ensemble macro modifiers: {list(eng.MACRO_WEIGHT_MODIFIERS.keys())}")


def test_inflation_shock_modifier_direction():
    """INFLATION_SHOCK 레짐에서 MQ Factor 가중치가 하락해야 함"""
    from src.ai.ensemble_scorer import EnsembleScoringEngine
    eng = EnsembleScoringEngine()
    base_w = eng.get_base_weights('BULL_LOW_VOL')
    shocked_w = eng.get_base_weights('BULL_LOW_VOL', macro_label='INFLATION_SHOCK')
    assert shocked_w.get('mq_factor', 0) < base_w.get('mq_factor', 0), \
        "INFLATION_SHOCK: mq_factor should decrease"
    assert shocked_w.get('rim_valuation', 0) > base_w.get('rim_valuation', 0), \
        "INFLATION_SHOCK: rim_valuation should increase"
    print(f"✅ INFLATION_SHOCK weight shift: mq_factor {base_w['mq_factor']:.3f} → {shocked_w['mq_factor']:.3f}, "
          f"rim_valuation {base_w['rim_valuation']:.3f} → {shocked_w['rim_valuation']:.3f}")


def test_yield_inversion_modifier_direction():
    """YIELD_INVERSION 레짐에서 Surge가 하락, RIM Valuation이 상승해야 함"""
    from src.ai.ensemble_scorer import EnsembleScoringEngine
    eng = EnsembleScoringEngine()
    base_w = eng.get_base_weights('BULL_LOW_VOL')
    inverted_w = eng.get_base_weights('BULL_LOW_VOL', macro_label='YIELD_INVERSION')
    assert inverted_w.get('surge', 0) < base_w.get('surge', 0), \
        "YIELD_INVERSION: surge should decrease"
    assert inverted_w.get('rim_valuation', 0) > base_w.get('rim_valuation', 0), \
        "YIELD_INVERSION: rim_valuation should increase"
    print(f"✅ YIELD_INVERSION weight shift: surge {base_w['surge']:.3f} → {inverted_w['surge']:.3f}, "
          f"rim_valuation {base_w['rim_valuation']:.3f} → {inverted_w['rim_valuation']:.3f}")


def test_dual_market_decoupling():
    """미국(SP500 BULL) - 한국(KOSPI BEAR) 디커플링 감지 검증"""
    rd = MarketRegimeDetector()
    df = make_base_df(n=60)
    df['sp500_change'] = 0.3   # 미국 상승 추세 (20일 누적 +6.0%)
    df['kospi_change'] = -0.3  # 한국 하락 추세 (20일 누적 -6.0%)
    res = rd.predict_dual_market_regime(df)
    assert res['decoupling_status'] == 'DECOUPLING_US_BULL_KR_BEAR', \
        f"Expected DECOUPLING_US_BULL_KR_BEAR, got {res['decoupling_status']}"
    print(f"✅ Dual Market Decoupling test: status={res['decoupling_status']}, corr_20d={res['correlation_20d']:.2f}")


if __name__ == '__main__':
    print("=" * 60)
    print("금융 전문가 제언 구현 검증 스모크 테스트")
    print("=" * 60)
    tests = [
        test_gmm_feature_count,
        test_ensemble_macro_modifier_keys,
        test_normal_expansion,
        test_yield_inversion,
        test_us2y_yield_inversion,
        test_inflation_shock,
        test_inflation_shock_modifier_direction,
        test_yield_inversion_modifier_direction,
        test_dual_market_decoupling,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"❌ {t.__name__}: FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  {t.__name__}: ERROR — {e}")
            import traceback; traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"결과: {passed}/{passed+failed} 통과 | {failed} 실패")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
