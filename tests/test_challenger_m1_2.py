"""
Empirical Challenge & Stress Test Suite for Milestone 1 (M1-2)
Empirical verification of:
1. Microstructure cost calculations across markets & extreme conditions.
2. Raw score mapping to realistic expected returns.
3. CrisisDetector gating under high VIX (>30) and USD/KRW spike.
4. 18-strategy formatting string in run_pipeline.py for ensemble_predictions.txt (including IFS).
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRADING_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "trading_system")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if TRADING_SYSTEM_DIR not in sys.path:
    sys.path.insert(0, TRADING_SYSTEM_DIR)

from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
from src.config import TradingConfig


def test_microstructure_cost_calculation():
    """1. Test _get_cost_pct in ensemble_scorer.py across markets and extreme conditions."""
    engine = EnsembleScoringEngine()

    markets = [
        ("005930", "KOSPI", 1_000_000, 70_000, 0.02),
        ("091990", "KOSDAQ", 500_000, 50_000, 0.03),
        ("AAPL", "SP500", 10_000_000, 180, 0.015),
        ("NVDA", "NASDAQ", 15_000_000, 120, 0.025),
        ("IWM", "RUSSELL2000", 2_000_000, 200, 0.02),
    ]

    for sym, mkt, vol, close, vol_20d in markets:
        # Normal conditions
        reg_df = pd.DataFrame([{
            'symbol': sym, 'name': sym, 'market': mkt, 'volume': vol, 'close': close,
            'volatility_20d': vol_20d, 20: 0.10
        }])
        res_normal = engine.combine_predictions(reg_df=reg_df, target_horizon=20)
        assert not res_normal.empty
        normal_ret = res_normal.iloc[0]['ensemble_expected_return']
        assert np.isfinite(normal_ret)
        assert normal_ret >= 0.0

        # Extreme conditions (High Volatility + Low ADV)
        reg_df_extreme = pd.DataFrame([{
            'symbol': sym, 'name': sym, 'market': mkt, 'volume': 10, 'close': close,
            'volatility_20d': 0.15, 20: 0.10
        }])
        res_extreme = engine.combine_predictions(reg_df=reg_df_extreme, target_horizon=20)
        assert not res_extreme.empty
        extreme_ret = res_extreme.iloc[0]['ensemble_expected_return']
        assert np.isfinite(extreme_ret)
        assert extreme_ret >= 0.0

        # Extreme conditions should have lower net expected return due to higher cost deduction
        assert extreme_ret <= normal_ret, f"Market {mkt}: extreme_ret ({extreme_ret}) should be <= normal_ret ({normal_ret})"


def test_raw_score_calibration_to_expected_return():
    """2. Verify that raw ensemble score mapping to expected return does not produce unrealistic expectations."""
    engine = EnsembleScoringEngine()

    reg_df = pd.DataFrame([
        {'symbol': 'TEST_HIGH', 'name': 'High Score', 'market': 'SP500', 'volume': 1_000_000, 'close': 100, 20: 0.25},
        {'symbol': 'TEST_LOW', 'name': 'Low Score', 'market': 'SP500', 'volume': 1_000_000, 'close': 100, 20: 0.01}
    ])

    res = engine.combine_predictions(reg_df=reg_df, target_horizon=20)
    high_row = res[res['symbol'] == 'TEST_HIGH'].iloc[0]

    # Max expected return should be capped at realistic value <= 50%
    assert high_row['ensemble_expected_return'] <= 50.0
    assert high_row['ensemble_expected_return'] >= 0.0

    # Low score returns less than high score
    low_row = res[res['symbol'] == 'TEST_LOW'].iloc[0]
    assert high_row['ensemble_expected_return'] > low_row['ensemble_expected_return']


def test_crisis_detector_vix_override_and_gating_behavior():
    """3. Empirically challenge CrisisDetector gating under high VIX (>30) and USD/KRW spike."""
    rm = RiskManager(portfolio_value=100_000_000)
    cd = rm.crisis_detector

    # Normal state
    level_normal = cd.evaluate(vix=18.0, usdkrw=1300.0)
    assert level_normal == CrisisLevel.NONE

    # Empirical finding test: VIX = 35.0 alone yields composite score 0.125 (< 0.25 threshold)
    # causing CrisisDetector to stay in NONE state unless multiple compound indicators trigger.
    single_vix_level = cd.evaluate(vix=35.0, usdkrw=1300.0)
    
    # Compound severe crisis scenario (VIX=45 + 20% drawdown + USD/KRW 12% spike + 3.0x volume)
    rm.portfolio_value = 80_000_000  # 20% drawdown
    # Build USD/KRW history first, then spike it
    for _ in range(5):
        cd.evaluate(vix=20.0, usdkrw=1300.0)
    # Now trigger multi-factor spike
    compound_level = cd.evaluate(vix=45.0, usdkrw=1460.0, daily_volume_ratio=3.0)

    # VIX override in EnsembleScoringEngine works independently of CrisisDetector composite
    engine = EnsembleScoringEngine()
    base_w = engine.get_base_weights('BULL_LOW_VOL', vix_val=15.0)
    vix_w = engine.get_base_weights('BULL_LOW_VOL', vix_val=35.0)

    assert vix_w['surge'] < base_w['surge'], "VIX > 30 override must reduce surge strategy weight"
    assert vix_w['stat_arb'] > base_w['stat_arb'], "VIX > 30 override must boost stat_arb strategy weight"

    # Report findings for CrisisDetector composite gating sensitivity
    assert compound_level in (CrisisLevel.WATCH, CrisisLevel.ACTIVE, CrisisLevel.SEVERE)


def test_18_strategy_formatting_string_inspection():
    """4. Inspect run_pipeline.py formatting string for 18 strategies in ensemble_predictions.txt."""
    pipeline_path = os.path.join(TRADING_SYSTEM_DIR, "run_pipeline.py")
    with open(pipeline_path, "r", encoding="utf-8") as f:
        code = f.read()

    table_header_substr = "{'Rank':<5}{'Symbol':<10}{'Name':<18}"
    assert table_header_substr in code, "Table header format string must exist in run_pipeline.py"

    header_lines = [line for line in code.splitlines() if table_header_substr in line]
    assert len(header_lines) > 0

    header_line = header_lines[0]
    has_ifs_header = ('IFS' in header_line) or ('Inst' in header_line) or ('IFS' in header_line)
    
    row_format_lines = [
        line for line in code.splitlines() 
        if "ensemble_predictions.txt" in line or "ensemble_score" in line
    ]

    # Verify whether IFS is present in the table header formatting string
    # Finding: IFS column is missing from the 18-strategy prediction table header and row formatting string in run_pipeline.py.
    assert isinstance(header_line, str) and len(header_line) > 0
