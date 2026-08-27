import pytest
import numpy as np
import pandas as pd

from src.ai.target_transform import transform_sharpe, inverse_transform_sharpe
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.risk.risk_manager import CrisisDetector, CrisisLevel
from src.analysis.portfolio_optimizer import calculate_hrp_weights


def test_target_transform_horizon_scaling():
    """Verify that horizon-aware inverse transform correctly scales returns by sqrt(h)."""
    sharpe_pred = pd.Series([1.0, 2.0, -1.0])
    vol_scale = pd.Series([0.02, 0.02, 0.02])

    ret_1d = inverse_transform_sharpe(sharpe_pred, vol_scale, horizon=1)
    ret_20d = inverse_transform_sharpe(sharpe_pred, vol_scale, horizon=20)
    ret_60d = inverse_transform_sharpe(sharpe_pred, vol_scale, horizon=60)

    assert np.allclose(ret_20d.values, ret_1d.values * np.sqrt(20.0), rtol=1e-5)
    assert np.allclose(ret_60d.values, ret_1d.values * np.sqrt(60.0), rtol=1e-5)


def test_regime_2d_weights_coverage_and_sum():
    """Verify all 6 2D regimes have non-zero weights for the 6 unblocked alpha engines and sum to 1.00."""
    engine = EnsembleScoringEngine()
    weights_matrix = engine.REGIME_2D_WEIGHTS

    unblocked_strategies = ['iv_skew', 'arm_factor', 'microstructure', 'short_squeeze', 'gamma_squeeze', 'darkpool']

    for regime_name, w_dict in weights_matrix.items():
        total = sum(w_dict.values())
        assert abs(total - 1.00) < 1e-4, f"{regime_name} sum is {total} != 1.00"

        for s in unblocked_strategies:
            assert s in w_dict, f"{s} missing in {regime_name}"
            assert w_dict[s] > 0.0, f"{s} has 0.0 weight in {regime_name}"


def test_kinematic_momentum_recovery_cooldown():
    """Verify CrisisDetector dynamically speeds up recovery during rapid V-shaped market recoveries."""
    cd = CrisisDetector()

    cd.evaluate(vix=42.0)
    assert cd.crisis_level in (CrisisLevel.SEVERE, CrisisLevel.ACTIVE)

    cd._vix_history = [42.0, 38.0, 30.0, 22.0, 18.0]
    cd._dd_history = [0.15, 0.12, 0.08, 0.04, 0.02]

    period = cd._get_dynamic_recovery_period()
    assert period <= 6, f"Expected fast recovery <= 6 days, got {period}"
    assert period >= 3, f"Expected minimum 3 days, got {period}"


def test_return_tilted_hrp_weights():
    """Verify Return-Tilted HRP allocates higher capital to higher-conviction expected return assets."""
    np.random.seed(42)
    n_assets = 10
    cov = np.eye(n_assets) * 0.04

    hrp_standard = calculate_hrp_weights(cov)
    assert np.isclose(np.sum(hrp_standard), 1.0)

    # Return-Tilted HRP: Assets 0 & 1 have strong positive expected return (+30%)
    exp_returns = np.array([0.30, 0.30, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01])
    r_hrp = calculate_hrp_weights(cov, expected_returns=exp_returns, alpha_tilt_exponent=1.0)

    assert r_hrp[0] > hrp_standard[0]
    assert r_hrp[1] > hrp_standard[1]
    assert r_hrp[0] > r_hrp[4]
    assert r_hrp[1] > r_hrp[5]
    assert np.isclose(np.sum(r_hrp), 1.0)


def test_adaptive_microstructure_friction_and_expected_return():
    """Verify combine_predictions produces realistic expected return and handles mid/small caps reasonably."""
    engine = EnsembleScoringEngine()

    df_preds = pd.DataFrame({
        'symbol': ['005930', '000660', '058470'],
        'market': ['KOSPI', 'KOSPI', 'KOSDAQ'],
        'regression_score': [0.85, 0.65, 0.90],
        'surge_score': [0.80, 0.60, 0.85],
        'vcp_ml_score': [0.75, 0.55, 0.80],
        'close': [70000.0, 180000.0, 45000.0],
        'volume': [1000000.0, 500000.0, 50000.0],
        'volatility_20d': [0.015, 0.022, 0.035],
    })

    combined = engine.combine_predictions(df_preds, regime='BULL_LOW_VOL', target_horizon='20d')
    assert 'ensemble_expected_return' in combined.columns
    assert len(combined) == 3
    # Top score should have positive expected return
    assert combined['ensemble_expected_return'].iloc[0] > 0.0
    # Small cap (058470) with strong score (0.90) should not be destroyed by fixed 50M order sizing
    assert combined[combined['symbol'] == '058470']['ensemble_expected_return'].iloc[0] > 0.0
