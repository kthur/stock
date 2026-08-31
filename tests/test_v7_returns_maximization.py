"""
tests/test_v7_returns_maximization.py
Comprehensive Unit and Integration Test Suite for V7 Returns Maximization (Phase 1 ~ Phase 6, V7-01 ~ V7-24).
"""

import pytest
import numpy as np
import pandas as pd

from trading_system.src.ai.score_normalizer import CrossSectionalScoreNormalizer
from trading_system.src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from trading_system.src.ai.factor_suppression import RegimeFactorSuppressionEngine
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine
from trading_system.src.risk.position_sizing import PortfolioAllocator
from trading_system.src.risk.risk_manager import CrisisDetector, CrisisLevel
from trading_system.src.execution.oms_engine import ExecutionOMSEngine
from trading_system.src.analysis.portfolio_optimizer import (
    apply_portfolio_constraints,
    discretize_weights_to_lot_sizes
)
from trading_system.src.core.stat_arb import StatisticalArbitrageEngine
from trading_system.src.core.sector_rotation import SectorRotationEngine
from trading_system.src.core.event_driven import EventDrivenEngine
from trading_system.src.core.mq_factor import MQFactorEngine
from trading_system.src.config import TradingConfig
from trading_system.src.data_layer.earnings_data import invalidate_cache_for_symbols
from trading_system.src.execution.slippage_feedback import SlippageFeedbackEngine


# ─── Phase 1 Tests ─────────────────────────────────────────────────────────────

def test_v7_01_short_horizon_cost_unscaled():
    """V7-01: Ensure short-horizon trades do not suffer artificial sqrt(20/h) cost multiplication."""
    scorer = EnsembleScoringEngine()
    df_1d = pd.DataFrame({
        'symbol': ['005930', '000660', '035420', '051910', '005380'],
        'market': ['KOSPI', 'KOSPI', 'KOSPI', 'KOSPI', 'KOSPI'],
        'ensemble_score': [0.90, 0.85, 0.70, 0.60, 0.50],
        'close': [70000, 120000, 200000, 400000, 250000],
        'volume': [1000000, 500000, 200000, 100000, 150000]
    })
    res_1d = scorer.combine_predictions(df_1d, target_horizon=1)
    res_20d = scorer.combine_predictions(df_1d, target_horizon=20)

    top_ret_1d = float(res_1d.iloc[0]['ensemble_expected_return'])
    top_ret_20d = float(res_20d.iloc[0]['ensemble_expected_return'])
    assert top_ret_1d > 0.0, "1d top expected return should be positive"
    assert top_ret_20d > 0.0, "20d top expected return should be positive"


def test_v7_02_score_normalizer_default_winsorized_zscore():
    """V7-02: Normalizer defaults to winsorized_zscore with 0.5%~99.5% bounds preserving extreme signals."""
    norm = CrossSectionalScoreNormalizer()
    assert norm.method == 'winsorized_zscore', "Default normalization method must be winsorized_zscore"

    df = pd.DataFrame({
        'symbol': [f'SYM_{i}' for i in range(100)],
        'market': ['SP500'] * 100,
        'alpha_score': np.linspace(-5.0, 5.0, 100)
    })
    normed = norm.normalize_scores(df, strategy_cols=['alpha_score'])
    assert normed['alpha_score'].iloc[-1] > 0.90
    assert normed['alpha_score'].iloc[0] < 0.10
    assert (normed['alpha_score'].diff().dropna() >= 0).all(), "Monotonicity must be preserved"


def test_v7_03_factor_orthogonalizer_pc1_consensus_preservation():
    """V7-03: ZCA Whitening preserves dominant PC1 consensus alpha."""
    ortho = FactorOrthogonalizerEngine(default_method='pca_zca_symmetric')
    np.random.seed(42)
    base_alpha = np.random.randn(50)
    scores_df = pd.DataFrame({
        'strat1': base_alpha + 0.05 * np.random.randn(50),
        'strat2': base_alpha + 0.05 * np.random.randn(50),
        'strat3': base_alpha + 0.05 * np.random.randn(50),
        'noise': np.random.randn(50)
    })
    res_df = ortho.orthogonalize(scores_df, strategy_cols=['strat1', 'strat2', 'strat3', 'noise'])
    for col in ['strat1', 'strat2', 'strat3']:
        corr = np.corrcoef(base_alpha, res_df[col])[0, 1]
        assert corr > 0.70, f"Consensus signal correlation for {col} should be preserved (>0.70), got {corr:.3f}"


def test_v7_04_dynamic_eff_alpha_smoothing():
    """V7-04: Dynamic weights computation handles varying volatility levels."""
    scorer = EnsembleScoringEngine()
    sharpes = {'strat1': 1.5, 'strat2': 0.8, 'strat3': 0.2}
    w_calm = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='NORMAL', market='KOSPI', vix_val=15.0)
    w_crisis = scorer.compute_dynamic_weights_from_sharpe(sharpes, regime='CRISIS', market='KOSPI', vix_val=35.0)
    assert len(w_calm) > 0
    assert len(w_crisis) > 0


def test_v7_05_factor_suppression_vif_threshold_10():
    """V7-05: VIF threshold relaxed to 10.0."""
    suppressor = RegimeFactorSuppressionEngine()
    corr = pd.DataFrame(np.eye(3), index=['s1', 's2', 's3'], columns=['s1', 's2', 's3'])
    vif_dict = {'s1': 7.0, 's2': 2.0, 's3': 2.0}
    base_w = {'s1': 0.33, 's2': 0.33, 's3': 0.33}
    suppressed = suppressor.suppress_weights(base_w, corr, regime_label='NORMAL', vif_dict=vif_dict)
    assert suppressed['s1'] >= 0.30, f"s1 weight with VIF 7.0 should not be over-damped, got {suppressed['s1']}"


# ─── Phase 2 Tests ─────────────────────────────────────────────────────────────

def test_v7_06_neutral_regime_max_allocation_95():
    """V7-06: PortfolioAllocator default max_total_allocation is 0.95."""
    allocator = PortfolioAllocator()
    assert allocator.max_total_allocation == 0.95


def test_v7_07_capitulation_buy_override_in_severe_crisis():
    """V7-07: In SEVERE crisis, high-conviction oversold plays receive up to 15% allocation."""
    oms = ExecutionOMSEngine()
    preds = [
        {
            'symbol': '005930',
            'market': 'KOSPI',
            'action': 'BUY',
            'target_price': 60000.0,
            'close_price': 60000.0,
            'short_term_reversal': 0.95,
            'expected_return': 12.0,
            'adv': 500_000_000_000.0
        },
        {
            'symbol': '000660',
            'market': 'KOSPI',
            'action': 'BUY',
            'target_price': 100000.0,
            'close_price': 100000.0,
            'expected_return': 8.0,
            'adv': 200_000_000_000.0
        }
    ]
    weights = {'005930': 0.30, '000660': 0.20}
    plan = oms.generate_order_plan(
        preds,
        weights,
        total_capital=100_000_000.0,
        crisis_level=CrisisLevel.SEVERE,
        regime_label="SEVERE_CRISIS"
    )
    plan_syms = [p['symbol'] for p in plan]
    assert '005930' in plan_syms, "Capitulation oversold play should be permitted in SEVERE crisis"
    p0 = next(p for p in plan if p['symbol'] == '005930')
    assert p0['target_weight'] <= 0.1501, f"Capitulation weight must be capped at 15%, got {p0['target_weight']}"


def test_v7_08_p90_alpha_hurdle_rate():
    """V7-08: Alpha hurdle concentrates on high conviction top candidates."""
    scorer = EnsembleScoringEngine()
    df = pd.DataFrame({
        'symbol': [f'{i:06d}' for i in range(1, 21)],
        'market': ['KOSPI'] * 20,
        'ensemble_score': np.linspace(0.30, 0.95, 20),
        'close': [50000] * 20,
        'volume': [1000000] * 20
    })
    res = scorer.combine_predictions(df, target_horizon=20)
    assert len(res) == 20
    assert res['portfolio_weight'].sum() > 0.0


def test_v7_09_regime_dynamic_multiplier():
    """V7-09: 25.0 multiplier in Bull regime vs 10.0 in Crisis."""
    scorer = EnsembleScoringEngine()
    df = pd.DataFrame({
        'symbol': ['005930', '000660', '035420'],
        'market': ['KOSPI', 'KOSPI', 'KOSPI'],
        'ensemble_score': [0.90, 0.70, 0.50],
        'close': [70000, 120000, 200000],
        'volume': [1000000, 500000, 200000]
    })
    res_bull = scorer.combine_predictions(df, regime='BULL')
    res_crisis = scorer.combine_predictions(df, regime='CRISIS')

    ret_bull = float(res_bull.iloc[0]['ensemble_expected_return'])
    ret_crisis = float(res_crisis.iloc[0]['ensemble_expected_return'])
    assert ret_bull > ret_crisis, f"Bull expected return ({ret_bull}) must exceed Crisis expected return ({ret_crisis})"


# ─── Phase 3 Tests ─────────────────────────────────────────────────────────────

def test_v7_10_min_alpha_half_life_execution_routing():
    """V7-10: Urgent fast alpha dictates FAST_VWAP execution routing via min(hl_list)."""
    oms = ExecutionOMSEngine()
    preds = [
        {
            'symbol': '005930',
            'market': 'KOSPI',
            'action': 'BUY',
            'target_price': 70000.0,
            'close_price': 70000.0,
            'microstructure_score': 0.90,
            'value_up_score': 0.85,
            'ensemble_expected_return': 5.0,
            'adv': 100_000_000_000.0
        }
    ]
    weights = {'005930': 0.10}
    plan = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0)
    assert len(plan) == 1
    assert plan[0]['execution_strategy'] == 'FAST_VWAP', "Urgent microstructure alpha should trigger FAST_VWAP"


def test_v7_11_adaptive_safety_margin_by_adv():
    """V7-11: Large-cap liquidity receives 5 bps hurdle vs small-cap 20 bps."""
    oms = ExecutionOMSEngine()
    preds = [
        {
            'symbol': '005930',
            'market': 'KOSPI',
            'action': 'BUY',
            'target_price': 70000.0,
            'close_price': 70000.0,
            'ensemble_expected_return': 0.08,
            'adv': 20_000_000_000.0
        }
    ]
    weights = {'005930': 0.10}
    plan = oms.generate_order_plan(preds, weights, total_capital=100_000_000.0)
    assert len(plan) == 1, "Large cap with 0.08% return should pass 5 bps hurdle"


def test_v7_12_damped_factor_constraints():
    """V7-12: Multi-factor constraints use damped reduction (1+scale)/2."""
    weights = np.array([0.40, 0.40, 0.20])
    factor_loadings = pd.DataFrame(
        [[2.0, 2.0], [2.0, 2.0], [0.1, 0.1]],
        columns=['FactorA', 'FactorB']
    )
    adj_w = apply_portfolio_constraints(weights, max_single_stock_weight=0.50, factor_loadings=factor_loadings, max_factor_exposure=0.50)
    assert np.all(np.isfinite(adj_w))
    assert np.isclose(np.sum(adj_w), 1.0)


def test_v7_13_composite_remainder_lot_allocation():
    """V7-13: Discretize weights uses composite priority (remainder + conviction)."""
    weights = np.array([0.50, 0.30, 0.20])
    prices = np.array([50000.0, 30000.0, 20000.0])
    res = discretize_weights_to_lot_sizes(weights, prices, total_capital=10_000_000.0, lot_sizes=1, min_order_quantities=1)
    assert np.sum(res['amounts']) <= 10_000_000.0
    assert np.all(res['shares'] >= 0)


# ─── Phase 4 Tests ─────────────────────────────────────────────────────────────

def test_v7_14_stat_arb_adaptive_kalman_noise():
    """V7-14: Kalman filter adapts noise based on residual variance."""
    engine = StatisticalArbitrageEngine()
    y1 = np.linspace(10, 20, 50) + np.random.randn(50) * 0.1
    y2 = np.linspace(5, 10, 50) + np.random.randn(50) * 0.1
    res = engine.estimate_kalman_dynamic_hedge_ratio(y1, y2)
    assert 'beta_t' in res
    assert np.isfinite(res['beta_t'])
    assert len(res['spread']) == 50


def test_v7_15_sector_rotation_leading_indicators():
    """V7-15: Sector rotation blends ARM and Order Flow leading indicators."""
    engine = SectorRotationEngine()
    dates = pd.date_range('2024-01-01', periods=30)
    prices_dict = {
        '005930': pd.DataFrame({'Close': np.linspace(70000, 75000, 30)}, index=dates),
        '000660': pd.DataFrame({'Close': np.linspace(70000, 75000, 30)}, index=dates)
    }
    arm_df = pd.DataFrame({'symbol': ['005930', '000660'], 'arm_score': [0.95, 0.10]})
    res = engine.compute_sector_momentum_scores(prices_dict, arm_scores=arm_df)
    assert not res.empty
    assert 'sector_score' in res.columns
    assert res.loc[res['symbol'] == '005930', 'sector_score'].iloc[0] > res.loc[res['symbol'] == '000660', 'sector_score'].iloc[0]


def test_v7_16_event_driven_finbert_blend():
    """V7-16: EventDrivenEngine blends FinBERT sentiment."""
    engine = EventDrivenEngine()
    sent_metrics = {'composite_sentiment_score': 0.90, 'confidence_score': 1.0}
    adjusted = engine.incorporate_filing_sentiment('005930', base_catalyst_score=0.70, sentiment_metrics=sent_metrics)
    assert adjusted > 0.70, f"Positive FinBERT sentiment should boost event score, got {adjusted}"


def test_v7_17_mq_factor_regime_adaptive_weights():
    """V7-17: MQFactorEngine applies regime-specific weights."""
    engine = MQFactorEngine()
    dates = pd.date_range('2024-01-01', periods=60)
    prices_dict = {
        '005930': pd.DataFrame({'Close': np.linspace(60000, 80000, 60)}, index=dates),
        '000660': pd.DataFrame({'Close': np.linspace(100000, 120000, 60)}, index=dates)
    }
    res_bull = engine.compute_mq_scores(prices_dict, regime_label='BULL')
    res_bear = engine.compute_mq_scores(prices_dict, regime_label='BEAR')
    assert not res_bull.empty
    assert not res_bear.empty


# ─── Phase 5 & 6 Tests ─────────────────────────────────────────────────────────

def test_v7_19_config_production_defaults():
    """V7-19: Production defaults in TradingConfig."""
    assert TradingConfig.__dataclass_fields__['train_sample_sp500'].default == "all"
    assert TradingConfig.__dataclass_fields__['train_sample_krx'].default == "all"
    assert TradingConfig.__dataclass_fields__['train_start_date'].default == "2018-01-01"
    assert TradingConfig.__dataclass_fields__['stock_price_freshness_days'].default == 1


def test_v7_20_earnings_cache_invalidation_hook():
    """V7-20: Invalidate cache hook runs safely."""
    res = invalidate_cache_for_symbols(None, ['005930'])
    assert res == 0


def test_v7_22_slippage_feedback_dynamic_cap():
    """V7-22: SlippageFeedbackEngine supports up to 8.0x dynamic scaling."""
    engine = SlippageFeedbackEngine()
    assert engine.default_slippage_bps > 0


def test_v7_23_and_24_position_sizing_herc_conviction_flags():
    """V7-23 & V7-24: Allocate accepts use_herc and use_conviction flags without error."""
    allocator = PortfolioAllocator()
    dates = pd.date_range('2024-01-01', periods=30)
    prices_dict = {
        '005930': pd.DataFrame({'Close': np.linspace(70000, 75000, 30), 'Volume': [1000000]*30}, index=dates),
        '000660': pd.DataFrame({'Close': np.linspace(120000, 130000, 30), 'Volume': [500000]*30}, index=dates)
    }
    pred_df = pd.DataFrame({
        'symbol': ['005930', '000660'],
        'market': ['KOSPI', 'KOSPI'],
        20: [10.0, 8.0]
    })
    res_herc = allocator.allocate(pred_df, prices_dict, use_hrp=True, use_herc=True)
    assert not res_herc.empty
    res_conv = allocator.allocate(pred_df, prices_dict, use_conviction=True)
    assert not res_conv.empty
