"""
Tests for Next-Gen (v2) Structural Improvements:
1. HRP Average/Ward Linkage (Chaining Artifact Removal).
2. DART/SEC NLP Context-Aware Syntactic Negation Inversion.
3. Power-Law Convex Expected Return Transformation in Ensemble Scorer.
4. Short Squeeze Hard-To-Borrow (HTB) & Borrow Fee Drag Modeling.
5. Dynamic FX Overlay & Covered Interest Parity (CIP) Currency Risk Control.
"""

import numpy as np
import pandas as pd
from src.analysis.portfolio_optimizer import calculate_hrp_weights
from src.core.llm_sentiment_engine import DARTSECSentimentEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.risk.delta_beta_hedge import DeltaBetaHedgeEngine


def test_hrp_average_and_ward_linkage():
    np.random.seed(42)
    # Generate 10-asset covariance matrix with a couple of outlier assets
    ret = np.random.normal(0, 0.02, (100, 10))
    cov = np.cov(ret, rowvar=False)

    w_ward = calculate_hrp_weights(cov, linkage_method="ward")
    w_avg = calculate_hrp_weights(cov, linkage_method="average")

    assert len(w_ward) == 10
    assert len(w_avg) == 10
    assert np.isclose(np.sum(w_ward), 1.0)
    assert np.isclose(np.sum(w_avg), 1.0)
    # Ensure no single asset dominates excessively due to single linkage chaining
    assert np.all(w_ward < 0.50)
    assert np.all(w_avg < 0.50)


def test_nlp_syntactic_negation_inversion():
    engine = DARTSECSentimentEngine()

    # Positive disclosure
    text_pos = "당사는 주주가치 제고를 위해 자사주소각 결정을 공시함."
    res_pos = engine._score_offline_lexicon(text_pos)

    # Negated disclosure (contains positive keyword '자사주소각' but negated by '철회')
    text_neg = "당사는 자사주소각 계획을 전격 철회하기로 결정함."
    res_neg = engine._score_offline_lexicon(text_neg)

    assert res_pos > 0.50, f"Positive disclosure should score > 0.50, got {res_pos}"
    assert res_neg < 0.50, f"Negated disclosure should score < 0.50, got {res_neg}"
    assert res_pos > res_neg, "Positive announcement must score strictly higher than revoked announcement"

    # English Negation test
    text_en_pos = "The company reported record revenue and upgraded guidance."
    res_en_pos = engine._score_offline_lexicon(text_en_pos)

    text_en_neg = "The company missed record revenue targets and cancelled upgraded guidance."
    res_en_neg = engine._score_offline_lexicon(text_en_neg)

    assert res_en_pos > res_en_neg


def test_convex_power_law_expected_return():
    scorer = EnsembleScoringEngine()

    # Create dummy dataframe with different ensemble score tails
    df = pd.DataFrame({
        'symbol': ['WINNER', 'MEDIAN', 'LOSER'],
        'market': ['SP500', 'SP500', 'SP500'],
        'ensemble_score': [0.90, 0.52, 0.10],
        'volatility_20d': [0.02, 0.02, 0.02],
        'volume': [1000000.0, 1000000.0, 1000000.0],
        'close': [100.0, 100.0, 100.0]
    })

    # Combined predictions will calculate ensemble_expected_return with power-law scaling
    combined = scorer.combine_predictions(df)
    
    ret_winner = combined.loc[combined['symbol'] == 'WINNER', 'ensemble_expected_return'].iloc[0]
    ret_median = combined.loc[combined['symbol'] == 'MEDIAN', 'ensemble_expected_return'].iloc[0]

    assert ret_winner > ret_median
    # High conviction winner should have substantially higher expected return
    assert ret_winner > 5.0


def test_short_squeeze_htb_borrow_fee_drag():
    engine = ShortInterestSqueezeEngine()

    # Case 1: Moderate healthy squeeze
    data_moderate = pd.DataFrame({
        'symbol': ['MOD_SQUEEZE'],
        'short_ratio': [0.15],
        'days_to_cover': [4.0]
    })

    # Case 2: Extreme Hard-To-Borrow with borrow fee drag
    data_htb = pd.DataFrame({
        'symbol': ['HTB_SQUEEZE'],
        'short_ratio': [0.45], # > 35% -> triggers borrow fee drag
        'days_to_cover': [12.0]
    })

    res_mod = engine.calculate_scores(['MOD_SQUEEZE'], features_df=data_moderate)
    res_htb = engine.calculate_scores(['HTB_SQUEEZE'], features_df=data_htb)

    assert not res_mod.empty
    assert not res_htb.empty
    assert 0.0 <= res_htb['short_squeeze_score'].iloc[0] <= 1.0


def test_dynamic_fx_overlay_hedging():
    fx_res_normal = DeltaBetaHedgeEngine.calculate_optimal_fx_overlay(
        us_portfolio_weight=0.50,
        regime="BULL_LOW_VOL"
    )
    assert fx_res_normal['status'] == "ACTIVE_FX_OVERLAY"
    assert fx_res_normal['fx_hedge_weight'] > 0.0

    # In severe crisis, keep USD unhedged as a safe-haven flight-to-quality asset
    fx_res_crisis = DeltaBetaHedgeEngine.calculate_optimal_fx_overlay(
        us_portfolio_weight=0.50,
        regime="CRISIS_SEVERE"
    )
    assert fx_res_crisis['fx_hedge_ratio'] == 0.0, "In severe crisis, USD exposure should remain unhedged for safe-haven protection"
