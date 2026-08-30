import pytest
import numpy as np
import pandas as pd

from src.ai.correlation_monitor import StrategyCorrelationMonitor, ALL_17_STRATEGIES
from src.ai.factor_suppression import RegimeFactorSuppressionEngine
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.ai.optuna_tuner import OptunaStrategyTuner

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


def _create_sample_17_strategy_df() -> pd.DataFrame:
    """Generates synthetic stock dataset with 50 rows and 17 strategy score columns."""
    np.random.seed(42)
    n_stocks = 50
    data = {'symbol': [f'STOCK_{i:03d}' for i in range(n_stocks)]}

    # Generate correlated base factors
    base_momentum = np.random.randn(n_stocks)
    base_reversal = np.random.randn(n_stocks)
    base_quality = np.random.randn(n_stocks)

    # 1. Momentum cluster (highly correlated)
    data['reg_score'] = np.clip(0.5 + 0.3 * base_momentum + 0.1 * np.random.randn(n_stocks), 0.0, 1.0)
    data['surge_score'] = np.clip(0.5 + 0.35 * base_momentum + 0.05 * np.random.randn(n_stocks), 0.0, 1.0)
    data['vcp_ml_score'] = np.clip(0.5 + 0.33 * base_momentum + 0.08 * np.random.randn(n_stocks), 0.0, 1.0)
    data['sector_score'] = np.clip(0.5 + 0.28 * base_momentum + 0.12 * np.random.randn(n_stocks), 0.0, 1.0)
    data['arm_score'] = np.clip(0.5 + 0.25 * base_momentum + 0.15 * np.random.randn(n_stocks), 0.0, 1.0)

    # 2. Reversal cluster
    data['stat_arb_score'] = np.clip(0.5 + 0.3 * base_reversal + 0.1 * np.random.randn(n_stocks), 0.0, 1.0)
    data['reversal_score'] = np.clip(0.5 + 0.32 * base_reversal + 0.08 * np.random.randn(n_stocks), 0.0, 1.0)
    data['vcp_rule_score'] = np.clip(0.5 + 0.25 * base_reversal + 0.15 * np.random.randn(n_stocks), 0.0, 1.0)
    data['card_score'] = np.clip(0.5 + 0.20 * base_reversal + 0.20 * np.random.randn(n_stocks), 0.0, 1.0)

    # 3. Valuation & Quality
    data['rim_score'] = np.clip(0.5 + 0.3 * base_quality + 0.1 * np.random.randn(n_stocks), 0.0, 1.0)
    data['mq_score'] = np.clip(0.5 + 0.28 * base_quality + 0.12 * np.random.randn(n_stocks), 0.0, 1.0)

    # 4. Microstructure & Flow
    data['ll_score'] = np.clip(np.random.rand(n_stocks), 0.0, 1.0)
    data['lstm_score'] = np.clip(np.random.rand(n_stocks), 0.0, 1.0)
    data['event_score'] = np.clip(np.random.rand(n_stocks), 0.0, 1.0)
    data['iv_skew_score'] = np.clip(np.random.rand(n_stocks), 0.0, 1.0)
    data['order_flow_score'] = np.clip(np.random.rand(n_stocks), 0.0, 1.0)
    data['latr_score'] = np.clip(np.random.rand(n_stocks), 0.0, 1.0)
    data['inst_foreign_sector_score'] = np.clip(np.random.rand(n_stocks), 0.0, 1.0)

    return pd.DataFrame(data)


@pytest.fixture
def sample_17_strategy_df() -> pd.DataFrame:
    return _create_sample_17_strategy_df()



def test_spearman_rank_correlation(sample_17_strategy_df):
    """Verifies StrategyCorrelationMonitor produces valid symmetric NxN Spearman matrix."""
    monitor = StrategyCorrelationMonitor(alpha_corr=0.20)
    corr_matrix = monitor.update_correlation(sample_17_strategy_df)
    n_strats = len(ALL_17_STRATEGIES)

    assert isinstance(corr_matrix, pd.DataFrame)
    assert corr_matrix.shape == (n_strats, n_strats)
    assert set(corr_matrix.columns) == set(ALL_17_STRATEGIES)
    assert set(corr_matrix.index) == set(ALL_17_STRATEGIES)

    # Test diagonal is 1.0
    diag_vals = np.diag(corr_matrix.values)
    np.testing.assert_allclose(diag_vals, 1.0, atol=1e-5)

    # Test symmetry R == R^T
    np.testing.assert_allclose(corr_matrix.values, corr_matrix.values.T, atol=1e-5)

    # Test range [-1.0, 1.0]
    assert (corr_matrix.values >= -1.0).all()
    assert (corr_matrix.values <= 1.0).all()

    # Test momentum cluster correlation is high (surge vs vcp_ml)
    rho_surge_vcp = corr_matrix.loc['surge', 'vcp_ml']
    assert rho_surge_vcp > 0.60, f"Expected high surge vs vcp_ml correlation, got {rho_surge_vcp}"

    # Test rolling update
    corr_matrix_2 = monitor.update_correlation(sample_17_strategy_df)
    assert corr_matrix_2.shape == (n_strats, n_strats)


def test_vif_and_effective_strategy_count():
    """Verifies VIF calculation and Effective Strategy Count (N_eff)."""
    monitor = StrategyCorrelationMonitor()
    n_strats = len(ALL_17_STRATEGIES)

    # Baseline 1: Identity correlation matrix (orthogonal strategies)
    id_matrix = pd.DataFrame(np.eye(n_strats), index=ALL_17_STRATEGIES, columns=ALL_17_STRATEGIES)
    vifs_id = monitor.compute_vif(id_matrix)
    for s in ALL_17_STRATEGIES:
        assert abs(vifs_id[s] - 1.0) < 1e-3, f"Expected VIF ~ 1.0 for {s}, got {vifs_id[s]}"

    n_eff_id = monitor.compute_effective_strategy_count(corr_matrix=id_matrix)
    assert abs(n_eff_id - float(n_strats)) < 1e-3, f"Expected N_eff = {n_strats}, got {n_eff_id}"

    # Baseline 2: High correlation matrix (e.g. surge and vcp_ml with rho = 0.90)
    high_corr_mat = np.eye(n_strats)
    idx_surge = ALL_17_STRATEGIES.index('surge')
    idx_vcp = ALL_17_STRATEGIES.index('vcp_ml')
    high_corr_mat[idx_surge, idx_vcp] = 0.90
    high_corr_mat[idx_vcp, idx_surge] = 0.90

    high_corr_df = pd.DataFrame(high_corr_mat, index=ALL_17_STRATEGIES, columns=ALL_17_STRATEGIES)
    vifs_high = monitor.compute_vif(high_corr_df)
    assert vifs_high['surge'] > 4.0, f"Expected high VIF for surge, got {vifs_high['surge']}"
    assert vifs_high['vcp_ml'] > 4.0, f"Expected high VIF for vcp_ml, got {vifs_high['vcp_ml']}"

    n_eff_high = monitor.compute_effective_strategy_count(corr_matrix=high_corr_df)
    assert n_eff_high < float(n_strats), f"Expected N_eff < {n_strats} under collinearity, got {n_eff_high}"

    # Top collinear pairs extraction
    pairs = monitor.get_top_collinear_pairs(threshold=0.50, corr_matrix=high_corr_df)
    assert len(pairs) >= 1
    assert pairs[0][0] in ['surge', 'vcp_ml']
    assert pairs[0][1] in ['surge', 'vcp_ml']
    assert abs(pairs[0][2] - 0.90) < 1e-3


def test_regime_factor_noise_suppression_sideways(sample_17_strategy_df):
    """Verifies factor noise suppression dampening in SIDEWAYS_LOW_VOL regime."""
    monitor = StrategyCorrelationMonitor()
    corr_df = monitor.update_correlation(sample_17_strategy_df)
    n_strats = len(ALL_17_STRATEGIES)

    supp_engine = RegimeFactorSuppressionEngine(default_theta=0.55, default_lambda=1.5)

    base_weights = {s: 1.0 / float(n_strats) for s in ALL_17_STRATEGIES}

    suppressed_weights = supp_engine.suppress_weights(
        base_weights=base_weights,
        corr_matrix=corr_df,
        regime_label='SIDEWAYS_LOW_VOL',
        theta=0.55,
        lambda_penalty=1.5
    )

    assert len(suppressed_weights) == n_strats
    assert abs(sum(suppressed_weights.values()) - 1.0) < 1e-4

    # Surge and VCP ML belong to MOMENTUM cluster, which is high-risk in SIDEWAYS
    # Therefore, surge and vcp_ml should be dampened relative to uncorrelated factors like stat_arb or rim_valuation
    w_surge = suppressed_weights['surge']
    w_stat_arb = suppressed_weights['stat_arb']
    w_rim = suppressed_weights['rim_valuation']

    assert w_surge < base_weights['surge'], f"Expected surge weight to be dampened from {base_weights['surge']}, got {w_surge}"
    assert w_stat_arb > suppressed_weights['surge'], f"Expected stat_arb weight ({w_stat_arb}) > surge weight ({w_surge})"
    assert w_rim > suppressed_weights['surge'], f"Expected rim_valuation weight ({w_rim}) > surge weight ({w_surge})"

    report = supp_engine.get_suppression_report(
        base_weights=base_weights,
        corr_matrix=corr_df,
        regime_label='SIDEWAYS_LOW_VOL'
    )
    assert report['regime'] == 'SIDEWAYS_LOW_VOL'
    assert 'MOMENTUM' in report['high_risk_clusters']
    assert report['penalties']['surge'] < 1.0


def test_regime_factor_noise_suppression_bull(sample_17_strategy_df):
    """Verifies factor noise suppression dampening in BULL_LOW_VOL regime."""
    monitor = StrategyCorrelationMonitor()
    n_strats = len(ALL_17_STRATEGIES)

    # Create synthetic correlation matrix with high REVERSAL cluster correlation
    high_rev_mat = np.eye(n_strats)
    idx_sa = ALL_17_STRATEGIES.index('stat_arb')
    idx_rev = ALL_17_STRATEGIES.index('short_term_reversal')
    high_rev_mat[idx_sa, idx_rev] = 0.85
    high_rev_mat[idx_rev, idx_sa] = 0.85
    corr_df = pd.DataFrame(high_rev_mat, index=ALL_17_STRATEGIES, columns=ALL_17_STRATEGIES)

    supp_engine = RegimeFactorSuppressionEngine(default_theta=0.60, default_lambda=1.2)
    base_weights = {s: 1.0 / float(n_strats) for s in ALL_17_STRATEGIES}

    suppressed_weights = supp_engine.suppress_weights(
        base_weights=base_weights,
        corr_matrix=corr_df,
        regime_label='BULL_LOW_VOL',
        theta=0.60,
        lambda_penalty=1.2
    )

    # In BULL_LOW_VOL, REVERSAL cluster (stat_arb, short_term_reversal) is high risk anti-trend noise
    assert suppressed_weights['short_term_reversal'] < base_weights['short_term_reversal']
    assert suppressed_weights['stat_arb'] < base_weights['stat_arb']
    assert suppressed_weights['surge'] > suppressed_weights['short_term_reversal']


def test_ensemble_scorer_correlation_integration(sample_17_strategy_df):
    """Verifies EnsembleScoringEngine end-to-end integration with correlation monitor & suppression."""
    engine = EnsembleScoringEngine()
    n_strats = len(ALL_17_STRATEGIES)

    df = sample_17_strategy_df.copy()
    # Add required meta columns for combine_predictions
    df['name'] = df['symbol']
    df['market'] = 'KOSPI'
    df['close'] = 50000.0
    df['volume'] = 1_000_000.0

    res_df = engine.combine_predictions(
        reg_df=df,
        s_df=df,
        ll_df=df,
        v_rule_df=df,
        vcp_ml_df=df,
        lstm_df=df,
        stat_arb_df=df,
        sector_df=df,
        rim_df=df,
        event_df=df,
        mq_df=df,
        iv_skew_df=df,
        order_flow_df=df,
        reversal_df=df,
        arm_df=df,
        card_df=df,
        latr_df=df,
        inst_foreign_sector_df=df,
        regime='SIDEWAYS_LOW_VOL'
    )

    assert 'ensemble_score' in res_df.columns
    assert 'ensemble_expected_return' in res_df.columns
    assert len(res_df) == len(sample_17_strategy_df)

    # Verify attrs contains correlation report
    assert hasattr(res_df, 'attrs')
    assert 'correlation_report' in res_df.attrs

    report = res_df.attrs['correlation_report']
    assert 'correlation_matrix' in report
    assert 'vif' in report
    assert 'n_eff' in report
    assert 'suppressed_weights' in report
    assert 'penalties' in report

    assert report['n_eff'] >= 1.0 and report['n_eff'] <= float(len(report['suppressed_weights']))
    assert len(report['suppressed_weights']) >= n_strats

    # Reasoning summary check
    summary = engine.get_regime_reasoning_summary('SIDEWAYS_LOW_VOL')
    assert "[Multicollinearity Monitoring & Regime Noise Suppression]" in summary
    assert "Effective Strategy Count (N_eff)" in summary


def test_optuna_tuner_correlation_suppression():
    """Verifies OptunaStrategyTuner parameter tuning for correlation suppression."""
    tuner = OptunaStrategyTuner()

    # Test default fallback when no returns provided
    res_default = tuner.tune_correlation_suppression_params(n_trials=2)
    assert 'correlation_suppression' in tuner.tuned_params
    assert 'SIDEWAYS_LOW_VOL' in res_default
    assert 'theta' in res_default['SIDEWAYS_LOW_VOL']
    assert 'lambda' in res_default['SIDEWAYS_LOW_VOL']

    # Test tuning with synthetic strategy returns per regime
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=30)
    strats = ['surge', 'vcp_ml', 'stat_arb', 'rim_valuation']
    synthetic_returns = {
        'SIDEWAYS_LOW_VOL': {s: pd.Series(np.random.randn(30) * 0.01, index=dates) for s in strats}
    }

    res_tuned = tuner.tune_correlation_suppression_params(
        strategy_returns_by_regime=synthetic_returns,
        n_trials=3
    )

    assert 'SIDEWAYS_LOW_VOL' in res_tuned
    params = res_tuned['SIDEWAYS_LOW_VOL']
    assert 0.40 <= params['theta'] <= 0.80
    assert 0.20 <= params['lambda'] <= 2.50


import unittest

class TestCorrelationSuppression(unittest.TestCase):
    def test_spearman_rank_correlation(self):
        df = _create_sample_17_strategy_df()
        test_spearman_rank_correlation(df)

    def test_vif_and_effective_strategy_count(self):
        test_vif_and_effective_strategy_count()

    def test_regime_factor_noise_suppression_sideways(self):
        df = _create_sample_17_strategy_df()
        test_regime_factor_noise_suppression_sideways(df)

    def test_regime_factor_noise_suppression_bull(self):
        df = _create_sample_17_strategy_df()
        test_regime_factor_noise_suppression_bull(df)

    def test_ensemble_scorer_correlation_integration(self):
        df = _create_sample_17_strategy_df()
        test_ensemble_scorer_correlation_integration(df)

    def test_optuna_tuner_correlation_suppression(self):
        test_optuna_tuner_correlation_suppression()


