import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine


def test_alpha_horizon_tiers_integrity():
    """Verify that ALPHA_HORIZON_TIERS covers strategies without overlaps."""
    tiers = EnsembleScoringEngine.ALPHA_HORIZON_TIERS
    assert 'slow' in tiers
    assert 'medium' in tiers
    assert 'fast' in tiers

    all_strats = []
    for tier_name, strats in tiers.items():
        assert len(strats) > 0
        all_strats.extend(strats)

    # Check for no duplicates
    assert len(all_strats) == len(set(all_strats))

    # Check tier weights sum to 1.0
    tier_weights = EnsembleScoringEngine.TIER_WEIGHTS
    assert abs(sum(tier_weights.values()) - 1.0) < 1e-6


def test_multi_horizon_hierarchical_blending_calculation():
    """Verify that combine_predictions generates tier sub-scores and applies fast tilt."""
    scorer = EnsembleScoringEngine()

    n = 20
    np.random.seed(42)
    symbols = [f"SYM_{i:03d}" for i in range(n)]

    # Create dummy DataFrame for regression (slow) and surge (medium) and microstructure (fast)
    reg_df = pd.DataFrame({
        'symbol': symbols,
        'name': [f"Name {s}" for s in symbols],
        'market': ['KOSPI'] * n,
        'close': [50000.0] * n,
        'expected_return': np.random.uniform(5.0, 25.0, n),
        'expected_return_20d': np.random.uniform(5.0, 25.0, n),
        'reg_score': np.random.uniform(0.3, 0.9, n)
    })
    s_df = pd.DataFrame({
        'symbol': symbols,
        'surge_score': np.random.uniform(0.2, 0.8, n)
    })
    micro_df = pd.DataFrame({
        'symbol': symbols,
        'microstructure_score': np.random.uniform(0.1, 0.9, n)
    })
    rim_df = pd.DataFrame({
        'symbol': symbols,
        'rim_score': np.random.uniform(0.4, 0.95, n)
    })

    res = scorer.combine_predictions(
        reg_df=reg_df,
        s_df=s_df,
        microstructure_df=micro_df,
        rim_df=rim_df,
        regime='BULL_LOW_VOL'
    )

    assert not res.empty
    assert 'ensemble_score' in res.columns
    assert 'slow_alpha_score' in res.columns
    assert 'medium_alpha_score' in res.columns
    assert 'fast_alpha_score' in res.columns

    # Verify score bounds
    assert (res['ensemble_score'] >= 0.0).all()
    assert (res['ensemble_score'] <= 1.0).all()
    assert (res['fast_alpha_score'] >= 0.0).all()
    assert (res['fast_alpha_score'] <= 1.0).all()
