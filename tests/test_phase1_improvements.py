import pytest
import numpy as np
import pandas as pd
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
from trading_system.src.ai.optuna_tuner import OptunaStrategyTuner, AlphaDecayTracker
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


def test_sector_exposure_cap_bear_and_bull():
    """Verify sector exposure cap enforces <=25% in Bear/Sideways and <=35% in Bull market."""
    allocator = PortfolioAllocator()
    
    weights = {
        'STOCK_A1': 0.15, 'STOCK_A2': 0.15, 'STOCK_A3': 0.10,  # Sector A total = 0.40
        'STOCK_B1': 0.20, 'STOCK_B2': 0.20,                    # Sector B total = 0.40
        'STOCK_C1': 0.20                                       # Sector C total = 0.20
    }
    sector_map = {
        'STOCK_A1': 'Semiconductor', 'STOCK_A2': 'Semiconductor', 'STOCK_A3': 'Semiconductor',
        'STOCK_B1': 'Bio', 'STOCK_B2': 'Bio',
        'STOCK_C1': 'Finance'
    }

    # 1. BEAR / SIDEWAYS Market -> Sector Cap <= 25% (0.25)
    bear_res = allocator.apply_sector_and_factor_constraints(
        weights=weights,
        sector_map=sector_map,
        regime='BEAR_LOW_VOL'
    )
    
    semicon_tot_bear = sum(bear_res[s] for s in ['STOCK_A1', 'STOCK_A2', 'STOCK_A3'])
    bio_tot_bear = sum(bear_res[s] for s in ['STOCK_B1', 'STOCK_B2'])
    
    assert semicon_tot_bear <= 0.25 + 1e-3
    assert bio_tot_bear <= 0.25 + 1e-3
    assert sum(bear_res.values()) <= 1.0 + 1e-3
    assert pytest.approx(sum(bear_res.values()), abs=1e-3) == 0.70

    # 2. BULL Market -> Sector Cap <= 35% (0.35)
    bull_res = allocator.apply_sector_and_factor_constraints(
        weights=weights,
        sector_map=sector_map,
        regime='BULL_HIGH_VOL'
    )
    
    semicon_tot_bull = sum(bull_res[s] for s in ['STOCK_A1', 'STOCK_A2', 'STOCK_A3'])
    assert semicon_tot_bull <= 0.35 + 1e-3


def test_alpha_decay_tracker():
    """Verify AlphaDecayTracker reduces weight of degrading strategies."""
    tracker = AlphaDecayTracker(decay_lambda=0.05)
    
    base_weights = {
        'regression': 0.10,
        'surge': 0.10,
        'vcp_ml': 0.10
    }
    sharpes = {
        'regression': 1.5,
        'surge': -0.5,
        'vcp_ml': 0.2
    }
    periods = {
        'regression': 0,
        'surge': 20,   # High decay period
        'vcp_ml': 5
    }

    adj_w = tracker.calculate_decay_adjusted_weights(base_weights, sharpes, periods)
    
    # Regression (high Sharpe, no decay) should have higher weight than surge (negative Sharpe, high decay)
    assert adj_w['regression'] > adj_w['surge']
    assert pytest.approx(sum(adj_w.values()), abs=1e-2) == 1.0


def test_optuna_tuner_27_strategies_support():
    """Verify OptunaStrategyTuner includes all 27 strategies in regime 2d weight optimization."""
    tuner = OptunaStrategyTuner()
    engine = EnsembleScoringEngine()
    
    # Get all 27 strategy names from REGIME_WEIGHTS
    strategy_cols = list(engine.REGIME_WEIGHTS[0].keys())
    assert len(strategy_cols) == 27
    
    dates = pd.date_range('2026-01-01', periods=30)
    mock_returns = {s: pd.Series(np.random.normal(0.001, 0.01, 30), index=dates) for s in strategy_cols}
    returns_by_regime = {'BULL_LOW_VOL': mock_returns}
    
    tuned = tuner.tune_regime_2d_weights(strategy_returns_by_regime=returns_by_regime, n_trials=2)
    assert 'BULL_LOW_VOL' in tuned
    bull_w = tuned['BULL_LOW_VOL']
    assert len(bull_w) == 27
    assert pytest.approx(sum(bull_w.values()), abs=1e-3) == 1.0
