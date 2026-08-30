import numpy as np
import pandas as pd
from src.ai.meta_labeler import MetaLabeler
from src.risk.portfolio_allocator import PortfolioAllocator
from src.analysis.portfolio_optimizer import calculate_hrp_weights, compute_tail_stressed_covariance
from src.ai.ensemble_scorer import EnsembleScoringEngine


def test_meta_labeler_conviction_multiplier():
    labeler = MetaLabeler(probability_threshold=0.55)
    X = pd.DataFrame({
        'f1': np.random.randn(100),
        'f2': np.random.randn(100)
    })
    y = pd.Series(np.random.choice([0, 1], size=100))
    labeler.train(X, y)
    assert labeler.is_fitted

    conviction = labeler.predict_conviction_multiplier(X)
    assert len(conviction) == 100
    assert np.all(conviction >= 0.0)

    # Test filter_and_size_predictions
    X.index = [f"SYM_{i}" for i in range(100)]
    preds = [
        {"symbol": "SYM_0", "ensemble_score": 0.80, "expected_return": 15.0, "action": "BUY"},
        {"symbol": "SYM_1", "ensemble_score": 0.60, "expected_return": 10.0, "action": "BUY"}
    ]
    sized = labeler.filter_and_size_predictions(preds, X)
    assert len(sized) == 2
    assert "meta_win_prob" in sized[0]
    assert "meta_conviction" in sized[0]


def test_dynamic_volatility_targeting_cash_overlay():
    allocator = PortfolioAllocator()
    target_w = {"A": 0.4, "B": 0.3, "C": 0.3}

    # Low volatility returns (e.g. 5% annual vol) -> Gross exposure should be 1.0 (0% cash)
    np.random.seed(42)
    low_vol_returns = np.random.normal(0.0005, 0.003, size=(50, 3))
    scaled_w, cash_ratio = allocator.compute_dynamic_volatility_target_weights(
        target_w, returns_matrix=low_vol_returns, target_annual_vol=0.12
    )
    assert cash_ratio == 0.0
    assert np.isclose(sum(scaled_w.values()), 1.0)

    # High volatility returns (e.g. 35% annual vol) -> Gross exposure should drop, cash ratio > 0
    high_vol_returns = np.random.normal(0.0, 0.025, size=(50, 3))
    scaled_w_high, cash_ratio_high = allocator.compute_dynamic_volatility_target_weights(
        target_w, returns_matrix=high_vol_returns, target_annual_vol=0.12
    )
    assert cash_ratio_high > 0.30  # At least 30% cash buffer
    assert sum(scaled_w_high.values()) < 0.75


def test_tail_stressed_hrp_covariance():
    np.random.seed(42)
    N = 40
    K = 4
    # Generate market with lower tail shock
    returns = np.random.normal(0.001, 0.015, size=(N, K))
    # Inject crisis day
    returns[0, :] = -0.08

    base_cov = np.cov(returns, rowvar=False)
    stressed_cov = compute_tail_stressed_covariance(base_cov, returns_matrix=returns, tail_quantile=0.10, stress_blend=0.30)

    assert stressed_cov.shape == (K, K)
    assert np.all(np.isfinite(stressed_cov))

    # Calculate HRP with tail stress
    weights = calculate_hrp_weights(base_cov, returns_matrix=returns, tail_stress=True)
    assert len(weights) == K
    assert np.isclose(np.sum(weights), 1.0)
    assert np.all(weights >= 0.0) and np.all(weights <= 1.0)


def test_leland_no_trade_buffer_bands():
    allocator = PortfolioAllocator()
    delta = allocator.calculate_dynamic_buffer_band(
        symbol="005930",
        target_weight=0.10,
        cost_rate=0.0025,
        volatility_20d=0.02
    )
    assert allocator.delta_floor <= delta <= allocator.delta_cap

    # Test portfolio rebalance with buffer
    current_w = {"005930": 0.102}  # only 0.2% difference from target 0.10 -> within delta band -> HOLD
    target_w = {"005930": 0.100}
    rebal = allocator.compute_portfolio_rebalance(
        current_weights=current_w,
        target_weights=target_w,
        market_map={"005930": "KOSPI"},
        volatility_map={"005930": 0.02},
        adv_map={"005930": 500_000_000_000.0}
    )
    assert rebal["trades"]["005930"]["action"] == "HOLD"
    assert rebal["trades"]["005930"]["trade_weight"] == 0.0


def test_dynamic_tier_weights_from_information_ratio():
    scorer = EnsembleScoringEngine()
    tier_rets = {
        'slow': [0.01, 0.02, 0.015, 0.01, 0.02, 0.018, 0.012, 0.014, 0.016, 0.02],
        'medium': [0.005, -0.002, 0.001, 0.004, -0.001, 0.002, 0.003, 0.001, 0.002, 0.001],
        'fast': [-0.01, -0.02, 0.01, -0.015, 0.005, -0.01, -0.005, 0.002, -0.01, -0.008]
    }
    tier_weights = scorer.compute_dynamic_tier_weights_from_ir(tier_rets)
    assert np.isclose(sum(tier_weights.values()), 1.0)
    # Slow tier had consistent positive returns -> higher IR -> higher weight
    assert tier_weights['slow'] > tier_weights['fast']
