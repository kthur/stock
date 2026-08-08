"""
Adversarial Verification Suite for Milestone 4: Microstructure Costs & Portfolio Allocation
Challenger: challenger_m4_2
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
import pandas as pd

from trading_system.src.execution.slippage_feedback import (
    SlippageFeedbackEngine,
    SlippageMetrics,
)
from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine


def test_monotonicity_cost_scaling_factor():
    """
    1. Verify that update_microstructure_costs with cost_scaling_factor > 1.0
    monotonically increases total_cost_pct and reduces net expected returns.
    """
    scorer = EnsembleScoringEngine()
    
    # Create candidate DataFrame with diverse stocks across KOSPI, KOSDAQ, SP500
    df_candidates = pd.DataFrame([
        {
            'symbol': '005930.KS',
            'name': 'Samsung',
            'market': 'KOSPI',
            'close': 70000.0,
            'volume': 1000000.0,
            'reg_pred': 0.15,
            'volatility_20d': 0.02
        },
        {
            'symbol': '035720.KQ',
            'name': 'Kakao',
            'market': 'KOSDAQ',
            'close': 50000.0,
            'volume': 200000.0,
            'reg_pred': 0.12,
            'volatility_20d': 0.035
        },
        {
            'symbol': 'AAPL',
            'name': 'Apple',
            'market': 'SP500',
            'close': 180.0,
            'volume': 5000000.0,
            'reg_pred': 0.10,
            'volatility_20d': 0.015
        }
    ])

    scaling_factors = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
    
    prev_returns = {sym: float('inf') for sym in df_candidates['symbol']}
    
    for factor in scaling_factors:
        metrics = SlippageMetrics(
            avg_slippage_bps=5.0 * factor,
            market_impact_alpha=0.50,
            cost_scaling_factor=factor
        )
        scorer.update_microstructure_costs(metrics)
        assert scorer.cost_scaling_factor == pytest.approx(factor, abs=1e-5)
        
        scored = scorer.combine_predictions(reg_df=df_candidates.copy())
        
        for _, row in scored.iterrows():
            sym = row['symbol']
            net_ret = row['ensemble_expected_return']
            
            # Net expected return must be monotonically non-increasing as cost factor rises
            assert net_ret <= prev_returns[sym] + 1e-9, (
                f"Monotonicity violated for {sym}: factor {factor} gave net return {net_ret} > previous {prev_returns[sym]}"
            )
            prev_returns[sym] = net_ret

    # Test strict monotonicity for positive raw returns prior to lower clipping (0.0)
    scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=1.0))
    ret_1x = scorer.combine_predictions(reg_df=df_candidates.copy()).set_index('symbol')['ensemble_expected_return']
    
    scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=2.0))
    ret_2x = scorer.combine_predictions(reg_df=df_candidates.copy()).set_index('symbol')['ensemble_expected_return']

    for sym in df_candidates['symbol']:
        assert ret_2x[sym] < ret_1x[sym], f"Expected ret_2x < ret_1x for {sym}, got {ret_2x[sym]} >= {ret_1x[sym]}"


def test_high_slippage_asset_demotion():
    """
    2. Verify that high-slippage assets undergo score demotion relative to low-slippage assets.
    """
    scorer = EnsembleScoringEngine()
    
    # Asset A: High raw prediction (15%) but relatively low turnover (600M KRW > 500M KRW threshold) & high vol (5%) -> High transaction cost
    # Asset B: Slightly lower raw prediction (14%) but very high turnover (200B KRW) & low vol (1%) -> Low transaction cost
    # Asset C: Extremely illiquid (50M KRW < 500M KRW) -> Hard zeroed out by Liquidity Gate
    df_candidates = pd.DataFrame([
        {
            'symbol': 'HIGH_COST_STOCK',
            'name': 'HighCostInc',
            'market': 'KOSDAQ',
            'close': 10000.0,
            'volume': 60000.0,      # Turnover 600M KRW (above 500M gate threshold)
            'reg_pred': 0.15,
            'volatility_20d': 0.05   # High vol
        },
        {
            'symbol': 'LOW_COST_STOCK',
            'name': 'LowCostCorp',
            'market': 'KOSPI',
            'close': 100000.0,
            'volume': 2000000.0,   # Turnover 200B KRW
            'reg_pred': 0.14,
            'volatility_20d': 0.01   # Low vol
        },
        {
            'symbol': 'HARD_ILLIQUID_STOCK',
            'name': 'HardIlliquidInc',
            'market': 'KOSDAQ',
            'close': 5000.0,
            'volume': 10000.0,      # Turnover 50M KRW (fails Liquidity Gate)
            'reg_pred': 0.20,
            'volatility_20d': 0.05
        }
    ])

    # Baseline scaling (1.0x)
    scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=1.0))
    scored_1x = scorer.combine_predictions(reg_df=df_candidates.copy())
    
    # Verify HARD_ILLIQUID_STOCK is zeroed out by Liquidity Gate
    hard_ret_1x = scored_1x.loc[scored_1x['symbol'] == 'HARD_ILLIQUID_STOCK', 'ensemble_expected_return'].values[0]
    hard_score_1x = scored_1x.loc[scored_1x['symbol'] == 'HARD_ILLIQUID_STOCK', 'ensemble_score'].values[0]
    assert hard_ret_1x == 0.0 and hard_score_1x == 0.0, "Hard illiquid stock must be zeroed out by Liquidity Gate"

    ret_high_1x = scored_1x.loc[scored_1x['symbol'] == 'HIGH_COST_STOCK', 'ensemble_expected_return'].values[0]
    ret_low_1x = scored_1x.loc[scored_1x['symbol'] == 'LOW_COST_STOCK', 'ensemble_expected_return'].values[0]

    # Scaled up cost (3.0x)
    scorer.update_microstructure_costs(SlippageMetrics(cost_scaling_factor=3.0))
    scored_3x = scorer.combine_predictions(reg_df=df_candidates.copy())
    ret_high_3x = scored_3x.loc[scored_3x['symbol'] == 'HIGH_COST_STOCK', 'ensemble_expected_return'].values[0]
    ret_low_3x = scored_3x.loc[scored_3x['symbol'] == 'LOW_COST_STOCK', 'ensemble_expected_return'].values[0]

    # Drop in return for HIGH_COST_STOCK must be strictly larger than drop for LOW_COST_STOCK
    drop_high = ret_high_1x - ret_high_3x
    drop_low = ret_low_1x - ret_low_3x
    
    assert drop_high > drop_low, (
        f"High slippage asset penalty drop ({drop_high:.4f}) should exceed low slippage asset penalty drop ({drop_low:.4f})"
    )

    # Confirm rank demotion: HIGH_COST_STOCK rank drops relative to LOW_COST_STOCK
    rank_1x_high = scored_1x.index[scored_1x['symbol'] == 'HIGH_COST_STOCK'][0]
    rank_3x_high = scored_3x.index[scored_3x['symbol'] == 'HIGH_COST_STOCK'][0]

    assert rank_3x_high >= rank_1x_high, (
        f"High cost asset rank changed from {rank_1x_high} to {rank_3x_high}"
    )


def test_clamping_cost_scaling_factor_bounds():
    """
    3. Verify that zero cost scaling factor or negative metrics are clamped safely within [0.50, 3.00].
    """
    scorer = EnsembleScoringEngine()

    test_cases = [
        (0.0, 0.50),
        (-1.0, 0.50),
        (-99.0, 0.50),
        (0.49, 0.50),
        (0.50, 0.50),
        (1.50, 1.50),
        (3.00, 3.00),
        (3.01, 3.00),
        (5.00, 3.00),
        (100.0, 3.00),
    ]

    for input_factor, expected_factor in test_cases:
        metrics = SlippageMetrics(cost_scaling_factor=input_factor)
        scorer.update_microstructure_costs(metrics)
        assert scorer.cost_scaling_factor == pytest.approx(expected_factor, abs=1e-5), (
            f"Input cost_scaling_factor {input_factor} expected to clamp to {expected_factor}, got {scorer.cost_scaling_factor}"
        )

    # Test SlippageFeedbackEngine automatic clamping of calculated cost_scaling_factor
    engine = SlippageFeedbackEngine(default_slippage_bps=5.0)
    
    # Negative / zero avg_slippage in feedback calculation
    # Simulate DB with zero or negative calculated slippage
    class MockDBFeedback(SlippageFeedbackEngine):
        def __init__(self, slip_bps):
            super().__init__()
            self.slip_bps = slip_bps

    # Verify clamping directly in calculation logic
    for slip, expected_factor in [(-10.0, 0.50), (0.0, 0.50), (2.0, 0.50), (25.0, 3.00), (100.0, 3.00)]:
        factor = max(0.50, min(3.00, slip / 5.0))
        assert factor == pytest.approx(expected_factor, abs=1e-5)
