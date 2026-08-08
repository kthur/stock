import pandas as pd
import numpy as np

def test_arm_factor_engine():
    from src.core.arm_factor import ARMFactorEngine
    engine = ARMFactorEngine()
    fund = {'005930': {'eps_growth': 15.0, 'revenue_growth': 10.0, 'per': 12.0, 'pbr': 1.2}}
    prices = {'005930': pd.DataFrame({'Close': np.linspace(50000, 60000, 30)})}
    scores = engine.compute_scores(fund, prices)
    assert '005930' in scores
    assert 0.0 <= scores['005930'] <= 1.0
    print("✅ ARM Factor Engine test passed.")

def test_card_factor_engine():
    from src.core.card_factor import CARDFactorEngine
    engine = CARDFactorEngine()
    indicator_df = pd.DataFrame({'usdkrw_change': [0.5], 'wti_change': [1.2], 'vix_change': [2.0]})
    prices = {'005930': pd.DataFrame({'Close': np.linspace(60000, 55000, 30)})}
    scores = engine.compute_scores(indicator_df, prices)
    assert '005930' in scores
    assert 0.0 <= scores['005930'] <= 1.0
    print("✅ CARD Factor Engine test passed.")

def test_latr_factor_engine():
    from src.core.latr_factor import LATRFactorEngine
    engine = LATRFactorEngine()
    prices = {'005930': pd.DataFrame({
        'Close': np.linspace(50000, 60000, 260),
        'Volume': np.random.randint(1000, 5000, 260)
    })}
    scores = engine.compute_scores(prices)
    assert '005930' in scores
    assert 0.0 <= scores['005930'] <= 1.0
    print("✅ LATR Factor Engine test passed.")

if __name__ == '__main__':
    test_arm_factor_engine()
    test_card_factor_engine()
    test_latr_factor_engine()
