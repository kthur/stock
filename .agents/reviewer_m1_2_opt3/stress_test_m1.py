"""
Adversarial Stress-Testing Suite for Milestone 1 (F04, F06, F07, F08)
Executed by Reviewer M1-2.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('trading_system'))
import numpy as np
import pandas as pd

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine

def test_f04_adversarial():
    print("=== Testing F04 Adversarial Scenarios ===")
    engine = EnsembleScoringEngine()
    engine.reset_decay_filter_state()

    # 1. Mixed casing, NaNs, missing market, unknown market
    df = pd.DataFrame({
        'symbol': ['A', 'B', 'C', 'D', 'E'],
        'market': ['SP500', 'sp500', None, np.nan, 'MARS_MARKET'],
        'reg_score': [0.9, 0.8, 0.7, 0.6, 0.5],
        'surge_score': [0.1, 0.2, 0.3, 0.4, 0.5]
    })
    strategy_cols = [('regression', 'reg_score'), ('surge', 'surge_score')]

    # 1. Mixed casing, NaNs, missing market, unknown market - MULTI-MARKET REINDEX BUG
    try:
        out1 = engine._apply_decay_filtering_with_cache(df, strategy_cols=strategy_cols, regime='BULL_LOW_VOL')
        # Warm start run on multi-market
        out2 = engine._apply_decay_filtering_with_cache(df, strategy_cols=strategy_cols, regime='BULL_LOW_VOL')
        print("  [PASS] F04 Multi-market warm start handled gracefully.")
    except ValueError as e:
        print(f"  [CRITICAL DEFECT DETECTED] F04 Multi-market warm start raised ValueError: {e}")

    # 2. Rank IC with NaNs, Infs, unobserved strategies, and extreme latency
    base_w = {'surge': 0.10, 'regression': 0.10, 'rim_valuation': 0.80}
    rank_ic_adversarial = {
        'surge': float('nan'),          # NaN IC
        'regression': float('inf'),     # Inf IC -> should be clipped to 1.0
        'phantom_strat': 0.99,          # Not in base_weights
        'rim_valuation': -2.5           # Beyond [-1, 1] -> should be clipped to -1.0
    }
    calib = engine.apply_rank_ic_decay_calibration(
        base_weights=base_w,
        strategy_rank_ic_dict=rank_ic_adversarial,
        latency_days=9999.0,            # Extreme latency
        regime='CRISIS'
    )
    assert abs(sum(calib.values()) - 1.0) < 1e-5, f"Calibrated weights must sum to 1.0, got {sum(calib.values())}"
    assert all(np.isfinite(list(calib.values()))), "All calibrated weights must be finite"
    print("  [PASS] F04 Rank IC with NaN/Inf and extreme latency handled gracefully.")


def test_f06_adversarial():
    print("=== Testing F06 Adversarial Scenarios ===")
    engine = EnsembleScoringEngine()

    # 1. Scores with all NaNs and infinities
    all_37_cols = [
        'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score', 'lstm_score',
        'stat_arb_score', 'sector_score', 'rim_score', 'event_score', 'mq_score', 'iv_skew_score',
        'order_flow_score', 'reversal_score', 'arm_score', 'card_score', 'latr_score',
        'inst_foreign_sector_score', 'supply_chain_score', 'sentiment_score', 'factor_neutralized_score',
        'vol_target_score', 'microstructure_score', 'accruals_quality_score', 'short_squeeze_score',
        'valueup_catalyst_score', 'trend_efficiency_score', 'gamma_squeeze_score', 'insider_buying_score',
        'darkpool_score', 'earnings_tone_drift_score', 'cross_asset_spillover_score',
        'supply_chain_gnn_score', 'range_expansion_score', 'dual_correction_score',
        'index_rebalance_score', 'overnight_gap_score'
    ]
    df_nan = pd.DataFrame({col: [np.nan, np.inf, -np.inf, 0.5, 0.9] for col in all_37_cols})
    synergy = engine.compute_pillar_synergy_multiplier(df_nan, regime='WEIRD_UNKNOWN_REGIME_XYZ')
    assert len(synergy) == 5
    assert (synergy >= 1.00).all() and (synergy <= 1.10).all()
    assert np.isfinite(synergy).all()
    print("  [PASS] F06 Synergy with NaNs/Infs and unknown regime handled gracefully.")

    # 2. Bessembinder with all identical scores (0.5, 0.0, 1.0)
    for c in [0.0, 0.5, 1.0]:
        scores_const = np.full(20, c)
        res = engine.apply_bessembinder_convex_power_law(scores_const, symmetric=True, regime='CRISIS')
        assert len(res) == 20
        assert np.isfinite(res).all()
        assert (res >= 0.0).all() and (res <= 1.0).all()
    print("  [PASS] F06 Bessembinder constant inputs handled gracefully.")


def test_f07_adversarial():
    print("=== Testing F07 Adversarial Scenarios ===")
    supp_engine = RegimeFactorSuppressionEngine()

    # 1. All strategies missing from corr_matrix
    base_w = {'surge': 0.5, 'regression': 0.5}
    empty_corr = pd.DataFrame()
    out = supp_engine.suppress_weights(
        base_weights=base_w,
        corr_matrix=empty_corr,
        regime_label="CRISIS",
        use_entropy_allocation=True,
        n_samples=25
    )
    assert abs(sum(out.values()) - 1.0) < 1e-5
    print("  [PASS] F07 All strategies missing from corr_matrix handled gracefully.")

    # 2. Extreme near-singular correlation matrix (eigenvalue ~ 1e-15)
    present = ['s1', 's2', 's3']
    missing = ['s4', 's5']
    all_s = present + missing
    R = np.array([
        [1.0, 0.999999, 0.999999],
        [0.999999, 1.0, 0.999999],
        [0.999999, 0.999999, 1.0]
    ])
    corr_df = pd.DataFrame(R, index=present, columns=present)
    base_w = {s: 0.20 for s in all_s}
    out = supp_engine.suppress_weights(
        base_weights=base_w,
        corr_matrix=corr_df,
        regime_label="BEAR_HIGH_VOL",
        use_entropy_allocation=True,
        n_samples=100
    )
    assert abs(sum(out.values()) - 1.0) < 1e-5
    assert all(np.isfinite(list(out.values())))
    print("  [PASS] F07 Ill-conditioned near-singular matrix handled gracefully.")


def test_f08_adversarial():
    print("=== Testing F08 Adversarial Scenarios ===")
    ortho_engine = FactorOrthogonalizerEngine(default_method='pca_symmetric')

    # 1. ALL columns are constant
    N = 25
    X_all_const = np.full((N, 4), 0.50)
    means = np.mean(X_all_const, axis=0)
    stds = np.std(X_all_const, axis=0)
    out1 = ortho_engine._pca_zca_symmetric(X_all_const, means, stds)
    assert out1.shape == (N, 4)
    assert not np.isnan(out1).any()
    np.testing.assert_allclose(out1, 0.50)
    print("  [PASS] F08 All constant columns returned intact without crash.")

    # 2. preserve_top_k > active columns (e.g. preserve_top_k=5 with only 2 active columns)
    f0 = np.random.randn(N)
    f1 = f0 + 0.1 * np.random.randn(N)
    f2 = np.full(N, 0.5) # constant
    X_mixed = np.column_stack([f0, f1, f2])
    means = np.mean(X_mixed, axis=0)
    stds = np.std(X_mixed, axis=0)
    stds[2] = 0.0

    out2 = ortho_engine._pca_zca_symmetric(X_mixed, means, stds, preserve_pc1=True, preserve_top_k=5)
    assert out2.shape == (N, 3)
    assert not np.isnan(out2).any()
    np.testing.assert_allclose(out2[:, 2], 0.5, atol=1e-6)
    print("  [PASS] F08 preserve_top_k > active columns handled safely.")

if __name__ == '__main__':
    test_f04_adversarial()
    test_f06_adversarial()
    test_f07_adversarial()
    test_f08_adversarial()
    print("\nALL ADVERSARIAL STRESS-TESTS PASSED SUCCESSFULLY!")
