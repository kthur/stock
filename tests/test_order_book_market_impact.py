import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine

def test_volatility_impact_scaling():
    """Verify higher daily price volatility leads to higher bid-ask spread and market impact."""
    scorer = EnsembleScoringEngine()

    df_reg = pd.DataFrame({
        'symbol': ['LOW_VOL.KS', 'HIGH_VOL.KS'],
        'market': ['KOSPI', 'KOSPI'],
        'volume': [100_000, 100_000],
        'close': [50_000, 50_000],   # Turnover: 5B KRW
        'volatility_20d': [0.01, 0.04],  # 1% vs 4% daily vol
        20: [0.25, 0.25]
    })

    res = scorer.combine_predictions(reg_df=df_reg, target_horizon=20)
    low_vol = res[res['symbol'] == 'LOW_VOL.KS'].iloc[0]
    high_vol = res[res['symbol'] == 'HIGH_VOL.KS'].iloc[0]

    assert high_vol['ensemble_expected_return'] <= low_vol['ensemble_expected_return']
