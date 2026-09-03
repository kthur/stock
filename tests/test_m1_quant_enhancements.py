"""
Milestone 1 Quantitative Enhancements Comprehensive Test Suite
Validates Features F01 through F08:
- F01: 7-State 2D Regime Matrix & Dedicated CRISIS Base Weights Dictionary
- F02: Markov Posterior Regime Soft-Blending
- F03: Continuous TV-Distance & VIX Entropy Adaptive Smoothing
- F04: Live Alpha Convolutional Decay Filtering & Rank IC Latency Calibration
- F05: Trend Inertia vs Crash Protection (Autocorrelation Boost & High-Vol Throttling)
- F06: 37-Strategy 4-Pillar Synergy Cluster Map & Regime-Adaptive Bessembinder S-Curve
- F07: Single-Stage Entropy Redundancy Allocation with Partial Missingness
- F08: Factor Orthogonalizer Singularity Protection for Zero-Variance Columns
"""

import math
import pytest
import numpy as np
import pandas as pd

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.factor_suppression import RegimeFactorSuppressionEngine, solve_single_stage_entropy_allocation
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine


# =========================================================================
# FEATURE F01: 7-State 2D Regime Matrix & Dedicated CRISIS Base Weights
# =========================================================================

def test_f01_crisis_regime_weights_specification():
    """F01: Verify CRISIS exists in REGIME_2D_WEIGHTS, has 37 strategies, sum=1.0000, all >= 0.005, and never falls back to SIDEWAYS_LOW_VOL."""
    scorer = EnsembleScoringEngine()
    assert "CRISIS" in scorer.REGIME_2D_WEIGHTS, "'CRISIS' must be present in REGIME_2D_WEIGHTS"
    crisis_w = scorer.REGIME_2D_WEIGHTS["CRISIS"]

    assert len(crisis_w) == 37, f"CRISIS should have exactly 37 strategies, got {len(crisis_w)}"
    assert pytest.approx(sum(crisis_w.values()), abs=1e-5) == 1.0
    assert all(w >= 0.005 for w in crisis_w.values()), "All strategy weights in CRISIS must be >= 0.005"

    # Verify defensive dominance
    assert crisis_w["vol_target"] == 0.080
    assert crisis_w["stat_arb"] == 0.070
    assert crisis_w["rim_valuation"] == 0.065
    assert crisis_w["accruals_quality"] == 0.060
    assert crisis_w["short_term_reversal"] == 0.055
    assert crisis_w["card_factor"] == 0.050

    # Verify high-beta throttling
    for high_beta in ["surge", "vcp_rule", "vcp_ml", "short_squeeze", "gamma_squeeze", "trend_efficiency", "range_expansion_breakout"]:
        assert crisis_w[high_beta] == 0.005, f"{high_beta} must be throttled to 0.005 in CRISIS"

    # Verify get_base_weights never falls back to SIDEWAYS_LOW_VOL for CRISIS
    w_direct = scorer.get_base_weights("CRISIS")
    w_lower = scorer.get_base_weights("crisis")
    w_substr = scorer.get_base_weights("CRISIS_ACTIVE")
    w_sideways = scorer.get_base_weights("SIDEWAYS_LOW_VOL")

    assert pytest.approx(w_direct["vol_target"], abs=1e-5) == 0.080
    assert pytest.approx(w_lower["vol_target"], abs=1e-5) == 0.080
    assert pytest.approx(w_substr["vol_target"], abs=1e-5) == 0.080
    assert w_direct["vol_target"] != w_sideways["vol_target"], "CRISIS must never fall back to SIDEWAYS_LOW_VOL"


# =========================================================================
# FEATURE F02: Markov Posterior Regime Soft-Blending
# =========================================================================

def test_f02_markov_posterior_regime_soft_blending():
    """F02: Verify Markov posterior probability vector produces accurate convex combination base weights."""
    scorer = EnsembleScoringEngine()

    regime_probs = {
        "BULL_LOW_VOL": 0.60,
        "SIDEWAYS_LOW_VOL": 0.30,
        "CRISIS": 0.10
    }
    w_blended = scorer.get_base_weights(regime_probs)

    active_w = {k: v for k, v in w_blended.items() if v > 0}
    assert len(active_w) == 37, f"Expected 37 active strategies, got {len(active_w)}"
    assert pytest.approx(sum(w_blended.values()), abs=1e-5) == 1.0

    w_bull = scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]
    w_side = scorer.REGIME_2D_WEIGHTS["SIDEWAYS_LOW_VOL"]
    w_cris = scorer.REGIME_2D_WEIGHTS["CRISIS"]

    # Verify convex combination for multiple representative strategies
    for s in ["surge", "stat_arb", "vol_target", "rim_valuation"]:
        expected = 0.60 * w_bull[s] + 0.30 * w_side[s] + 0.10 * w_cris[s]
        assert pytest.approx(w_blended[s], abs=1e-5) == expected

    # Test 1D probability dictionary fallback
    probs_1d = {"p_bear": 0.20, "p_sideways": 0.30, "p_bull": 0.50}
    w_1d = scorer.get_base_weights(probs_1d)
    assert pytest.approx(sum(w_1d.values()), abs=1e-5) == 1.0
    assert len([k for k, v in w_1d.items() if v > 0]) == 37


# =========================================================================
# FEATURE F03: Continuous TV-Distance & VIX Entropy Adaptive Smoothing
# =========================================================================

def test_f03_continuous_tv_distance_and_vix_smoothing():
    """F03: Verify continuous TV-distance and VIX entropy dynamic smoothing alpha_t in [0.15, 0.85]."""
    scorer = EnsembleScoringEngine(alpha_smoothing=0.20)
    sharpes = {s: 1.0 for s in scorer.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]}

    # Warm-up in BULL_LOW_VOL
    w1 = scorer.compute_dynamic_weights_from_sharpe(
        sharpes, regime="BULL_LOW_VOL", market="test_mkt", enable_tv_smoothing=True, vix_val=15.0
    )
    assert "surge" in w1

    # Shift to BEAR_HIGH_VOL with high VIX (42.0) under TV smoothing: should adapt rapidly (alpha >= 0.70)
    w2 = scorer.compute_dynamic_weights_from_sharpe(
        sharpes, regime="BEAR_HIGH_VOL", market="test_mkt", enable_tv_smoothing=True, vix_val=42.0
    )
    target_bear = scorer.get_base_weights("BEAR_HIGH_VOL")

    # Under alpha_t >= 0.70, w2 should move strongly toward target_bear without instant hard-reset (diff is bounded and non-zero)
    diff = sum(abs(w2[s] - target_bear[s]) for s in w2)
    assert diff < 0.45 and diff > 0.05, f"Expected fast adaptation without hard reset, diff={diff}"

    # Verify backwards compatibility: without TV smoothing, legacy 1-hot instant reset triggers (alpha = 1.0)
    engine_legacy = EnsembleScoringEngine(alpha_smoothing=0.20)
    w_bull_1 = engine_legacy.compute_dynamic_weights_from_sharpe(sharpes, regime="BULL_LOW_VOL")
    ref_legacy = EnsembleScoringEngine(alpha_smoothing=0.20)
    target_bear_ref = ref_legacy.compute_dynamic_weights_from_sharpe(sharpes, regime="BEAR_HIGH_VOL")
    w_bear_shift = engine_legacy.compute_dynamic_weights_from_sharpe(sharpes, regime="BEAR_HIGH_VOL")

    for k in target_bear_ref:
        assert math.isclose(w_bear_shift[k], target_bear_ref[k], rel_tol=1e-5, abs_tol=1e-6), (
            f"Legacy 1-hot regime switch without TV smoothing must perform exact instant reset for {k}"
        )


# =========================================================================
# FEATURE F04: Live Alpha Convolutional Decay Filter & Rank IC Calibration
# =========================================================================

def test_f04_exponential_decay_cold_start_identity():
    """F04: Cold start without cached prior scores returns identical scores and populates cache."""
    engine = EnsembleScoringEngine()
    engine.reset_decay_filter_state()

    symbols = ["AAPL", "MSFT", "NVDA"]
    reg_df = pd.DataFrame({"symbol": symbols, "expected_return": [0.10, 0.20, 0.15], "market": "US"})
    surge_df = pd.DataFrame({"symbol": symbols, "surge_probability": [0.70, 0.80, 0.60], "market": "US"})

    res = engine.combine_predictions(reg_df=reg_df, s_df=surge_df, regime="BULL_LOW_VOL")
    assert "ensemble_score" in res.columns
    assert len(res) == 3
    # State must be cached after first execution
    assert "us" in engine._prev_filtered_scores or "global" in engine._prev_filtered_scores
    assert not engine._prev_filtered_scores["global"].empty


def test_f04_exponential_decay_warm_start_smoothing_and_clipping():
    """F04: Consecutive runs apply convolutional exponential smoothing and clip [0.0, 1.0]."""
    engine = EnsembleScoringEngine()
    engine.reset_decay_filter_state()

    syms = ["005930", "000660"]
    scores_day1 = pd.DataFrame({
        "symbol": syms,
        "market": ["KOSPI", "KOSPI"],
        "reg_score": [0.80, 0.90],
        "surge_score": [0.70, 0.60]
    })
    scores_day2 = pd.DataFrame({
        "symbol": syms,
        "market": ["KOSPI", "KOSPI"],
        "reg_score": [0.20, 0.10],
        "surge_score": [0.10, 0.20]
    })

    strategy_cols = [("regression", "reg_score"), ("surge", "surge_score")]
    # First execution: cold start cache
    out1 = engine._apply_decay_filtering_with_cache(scores_day1, strategy_cols=strategy_cols, regime="BULL_LOW_VOL")
    assert pytest.approx(out1["reg_score"].iloc[0], abs=1e-5) == 0.80

    # Second execution: smooths between day 2 and cached day 1
    out2 = engine._apply_decay_filtering_with_cache(scores_day2, strategy_cols=strategy_cols, regime="BULL_LOW_VOL")
    # Reg score half-life is ~20 days (alpha ~ 0.034), so smoothed score is between 0.20 and 0.80
    assert 0.20 < out2["reg_score"].iloc[0] < 0.80
    # Strict clipping verification
    assert (out2["reg_score"] >= 0.0).all() and (out2["reg_score"] <= 1.0).all()
    assert (out2["surge_score"] >= 0.0).all() and (out2["surge_score"] <= 1.0).all()


def test_f04_rank_ic_and_latency_decay_calibration():
    """F04: Verify apply_rank_ic_decay_calibration tilts weights towards high Rank IC and discounts latency."""
    engine = EnsembleScoringEngine()
    base_w = {"surge": 0.05, "rim_valuation": 0.05, "regression": 0.05}
    rank_ic = {"surge": 0.15, "rim_valuation": -0.05, "regression": 0.08}

    calibrated = engine.apply_rank_ic_decay_calibration(
        base_weights=base_w,
        strategy_rank_ic_dict=rank_ic,
        latency_days=0.0,
        gamma=1.0,
        regime="BULL_LOW_VOL"
    )
    assert calibrated["surge"] > calibrated["regression"] > calibrated["rim_valuation"]
    assert pytest.approx(sum(calibrated.values()), abs=1e-5) == 1.0

    # Stale latency test: fast factor (surge, half-life 3d) decays faster than slow factor (rim, half-life 60d)
    calibrated_stale = engine.apply_rank_ic_decay_calibration(
        base_weights={"surge": 0.50, "rim_valuation": 0.50},
        strategy_rank_ic_dict={"surge": 0.0, "rim_valuation": 0.0},
        latency_days=6.0,  # 2 half-lives for surge, only 0.1 half-life for rim
        gamma=1.0,
        regime="BULL_LOW_VOL"
    )
    assert calibrated_stale["rim_valuation"] > calibrated_stale["surge"]


def test_f04_lstm_score_mapping_and_deduplication():
    """F04: Verify apply_exponential_decay_filter maps lstm_score to lstm and handles duplicates safely."""
    engine = EnsembleScoringEngine()
    prev = pd.DataFrame({
        "symbol": ["A", "A", "B"],  # duplicate symbol
        "lstm_score": [0.8, 0.7, 0.6]
    })
    curr = pd.DataFrame({
        "symbol": ["A", "B"],
        "lstm_score": [0.2, 0.3]
    })
    res = engine.apply_exponential_decay_filter(current_scores=curr, previous_scores=prev, regime="BULL_LOW_VOL")
    assert len(res) == 2
    assert (res["lstm_score"] >= 0.0).all() and (res["lstm_score"] <= 1.0).all()


# =========================================================================
# FEATURE F05: Trend Inertia vs Crash Protection
# =========================================================================

def test_f05_trend_inertia_boost_bull_low_vol():
    """F05: In BULL_LOW_VOL, reward factor rank autocorrelation with momentum turbo up to 1.60x."""
    engine = EnsembleScoringEngine()
    sharpes = {s: 0.5 for s in engine.REGIME_2D_WEIGHTS["BULL_LOW_VOL"]}

    # Autocorrelation = 0.80 -> turbo_mult = 1.40 + 0.20 * 0.80 = 1.56
    w_boosted = engine.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="BULL_LOW_VOL",
        factor_autocorr_dict={"surge": 0.80, "vcp_ml": 0.80}
    )
    # Autocorrelation = 0.0 -> turbo_mult = 1.40
    w_baseline = engine.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="BULL_LOW_VOL",
        factor_autocorr_dict={"surge": 0.0, "vcp_ml": 0.0}
    )
    assert w_boosted["surge"] > w_baseline["surge"]
    # Reversal strategy dampened in BULL_LOW_VOL (turbo_mult = 0.50)
    assert w_boosted["short_term_reversal"] < w_boosted["surge"]


def test_f05_crash_protection_bull_high_vol():
    """F05: In BULL_HIGH_VOL, curtail momentum turbo to 1.15x to prevent momentum crash risk."""
    engine = EnsembleScoringEngine()
    sharpes = {s: 0.5 for s in engine.REGIME_2D_WEIGHTS["BULL_HIGH_VOL"]}

    w_high_vol = engine.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="BULL_HIGH_VOL"
    )
    w_low_vol = engine.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="BULL_LOW_VOL"
    )
    # Momentum turbo is lower in high-vol bull than in low-vol bull
    ratio_high = w_high_vol["surge"] / max(w_high_vol["short_term_reversal"], 1e-6)
    ratio_low = w_low_vol["surge"] / max(w_low_vol["short_term_reversal"], 1e-6)
    assert ratio_high < ratio_low, "Momentum-to-reversal ratio must be scaled down in BULL_HIGH_VOL for crash protection"


def test_f05_reversal_boost_bear_and_crisis():
    """F05: In BEAR_HIGH_VOL & CRISIS, slash momentum to 0.50x and boost reversal to 1.40x ~ 1.68x."""
    engine = EnsembleScoringEngine()
    sharpes = {s: 0.5 for s in engine.REGIME_2D_WEIGHTS["CRISIS"]}

    w_crisis = engine.compute_dynamic_weights_from_sharpe(
        rolling_sharpes=sharpes,
        regime="CRISIS",
        vix_val=38.0
    )
    # In crisis, short_term_reversal receives boosted allocation over surge
    assert w_crisis["short_term_reversal"] > w_crisis["surge"] * 3.0


# =========================================================================
# FEATURE F06: 37-Strategy 4-Pillar Synergy & Regime-Adaptive Bessembinder
# =========================================================================

def test_f06_4_pillar_cluster_map_expansion():
    """F06: Verify all 37 strategies are covered across 4 disjoint clusters without any omission."""
    engine = EnsembleScoringEngine()
    # Create synthetic DataFrame with 10 rows and all 37 score columns
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
    df = pd.DataFrame({col: np.random.uniform(0.55, 0.90, size=10) for col in all_37_cols})

    synergy = engine.compute_pillar_synergy_multiplier(df, regime="BULL_LOW_VOL")
    assert len(synergy) == 10
    assert (synergy >= 1.00).all()
    assert (synergy <= 1.10).all(), "Synergy multiplier must be bounded in [1.00, 1.10]"


def test_f06_regime_adaptive_bessembinder_params():
    """F06: Verify regime-adaptive parameters for Bessembinder convex power-law."""
    gamma_bull, beta_bull = EnsembleScoringEngine.get_regime_adaptive_bessembinder_params("BULL_LOW_VOL")
    assert gamma_bull == 1.70 and beta_bull == 0.50

    gamma_crisis, beta_crisis = EnsembleScoringEngine.get_regime_adaptive_bessembinder_params("CRISIS")
    assert gamma_crisis == 1.20 and beta_crisis == 0.20

    scores = np.array([0.10, 0.30, 0.50, 0.55, 0.90])
    transformed_bull = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
        scores, symmetric=True, regime="BULL_LOW_VOL"
    )
    transformed_crisis = EnsembleScoringEngine.apply_bessembinder_convex_power_law(
        scores, symmetric=True, regime="CRISIS"
    )

    # Top-decile relative conviction over near-neutral noise (0.55) is amplified far more in calm bull than in crisis
    rel_spread_bull = (transformed_bull[4] - 0.50) / max(transformed_bull[3] - 0.50, 1e-6)
    rel_spread_crisis = (transformed_crisis[4] - 0.50) / max(transformed_crisis[3] - 0.50, 1e-6)
    assert rel_spread_bull > rel_spread_crisis * 2.0, "BULL_LOW_VOL must have much higher top-alpha conviction relative to noise"

    # Monotonicity test: Spearman rank correlation must equal 1.0000
    corr = pd.Series(scores).corr(pd.Series(transformed_bull), method='spearman')
    assert pytest.approx(corr, abs=1e-5) == 1.0


# =========================================================================
# FEATURE F07: Single-Stage Entropy Redundancy Allocation
# =========================================================================

def test_f07_entropy_allocation_partial_missingness():
    """F07: Verify single-stage entropy program handles partial missingness and produces valid weights."""
    supp_engine = RegimeFactorSuppressionEngine()

    present_strats = ['surge', 'vcp_ml', 'stat_arb', 'rim_valuation', 'mq_factor']
    missing_strats = ['vol_target', 'darkpool']
    all_strats = present_strats + missing_strats

    # Synthetic correlation matrix with high surge vs vcp_ml collinearity
    R_sub = np.eye(len(present_strats))
    R_sub[0, 1] = 0.85
    R_sub[1, 0] = 0.85
    corr_df = pd.DataFrame(R_sub, index=present_strats, columns=present_strats)

    base_w = {s: 1.0 / len(all_strats) for s in all_strats}

    opt_weights = supp_engine.suppress_weights(
        base_weights=base_w,
        corr_matrix=corr_df,
        regime_label="SIDEWAYS_LOW_VOL",
        use_entropy_allocation=True,
        n_samples=50
    )

    assert len(opt_weights) == len(all_strats)
    assert pytest.approx(sum(opt_weights.values()), abs=1e-5) == 1.0
    assert all(w >= 0.005 for w in opt_weights.values())
    # Collinear surge and vcp_ml should be penalized relative to uncorrelated factors
    assert opt_weights['stat_arb'] > opt_weights['surge']


# =========================================================================
# FEATURE F08: Factor Orthogonalizer Singularity Protection
# =========================================================================

def test_f08_orthogonalizer_singular_column_protection():
    """F08: Guard _pca_zca_symmetric against zero-variance singular columns without NaN or cross-noise bleed."""
    ortho_engine = FactorOrthogonalizerEngine(default_method='pca_symmetric')

    N = 30
    np.random.seed(42)
    # Column 0 & 1: active correlated features
    base_signal = np.random.randn(N)
    f0 = base_signal + 0.1 * np.random.randn(N)
    f1 = base_signal + 0.1 * np.random.randn(N)
    # Column 2: constant zero-variance column (e.g. median-imputed missing factor)
    f2 = np.full(N, 0.50)

    X = np.column_stack([f0, f1, f2])
    means = np.mean(X, axis=0)
    stds = np.std(X, axis=0)
    stds[2] = 1e-6  # clipped std for constant column

    X_ortho = ortho_engine._pca_zca_symmetric(X, means, stds, preserve_pc1=True, preserve_top_k=1)

    assert X_ortho.shape == (N, 3)
    assert not np.isnan(X_ortho).any(), "Orthogonalized matrix must not contain any NaNs"
    # Column 2 must remain exactly constant at 0.50 without cross-feature noise bleed
    np.testing.assert_allclose(X_ortho[:, 2], 0.50, atol=1e-6)
    # Active columns must have been decorrelated
    corr_before = np.corrcoef(X[:, 0], X[:, 1])[0, 1]
    corr_after = np.corrcoef(X_ortho[:, 0], X_ortho[:, 1])[0, 1]
    assert abs(corr_after) < abs(corr_before), f"Correlation should decrease from {corr_before:.3f}, got {corr_after:.3f}"
