import pytest
import os
import sqlite3
import pandas as pd
import numpy as np
from src.data_layer.overnight_gap_shifter import OvernightGapShifter
from src.execution.oms_engine import ExecutionOMSEngine


def test_overnight_gap_shifter_estimates():
    """Verify overnight opening gap computation and scoring shift."""
    shifter = OvernightGapShifter()

    # Positive US market move: SPY +1.5%, QQQ +2.0%, VIX -5%, USD/KRW -0.5%
    pos_factors = {
        'spy_return': 1.5,
        'qqq_return': 2.0,
        'vix_change': -5.0,
        'usdkrw_change': -0.5
    }
    pos_gap = shifter.compute_opening_gap_estimate(pos_factors)
    assert pos_gap > 0.5

    # Negative US market move: SPY -2.0%, QQQ -2.5%, VIX +15%, USD/KRW +1.2%
    neg_factors = {
        'spy_return': -2.0,
        'qqq_return': -2.5,
        'vix_change': 15.0,
        'usdkrw_change': 1.2
    }
    neg_gap = shifter.compute_opening_gap_estimate(neg_factors)
    assert neg_gap < -0.5

    # Apply to dummy DataFrame
    df = pd.DataFrame({
        'symbol': ['005930', '000660'],
        'surge_score': [0.50, 0.60],
        'rim_score': [0.50, 0.60]
    })
    shifted_pos = shifter.apply_gap_shift_to_scores(df, pos_gap, market='KOSPI')
    assert shifted_pos['surge_score'].iloc[0] > 0.50

    shifted_neg = shifter.apply_gap_shift_to_scores(df, neg_gap, market='KOSPI')
    assert shifted_neg['rim_score'].iloc[0] > 0.50


def test_oms_gate7_krx_hurdle_and_price_limit(tmp_path):
    """Verify OMS Gate #7 friction hurdle rate, limit-up lock, and synthetic short handling."""
    db_file = tmp_path / "test_trade_logs.db"
    oms = ExecutionOMSEngine(db_path=str(db_file))

    predictions = [
        # 1. Normal high return stock -> Should PASS
        {
            "symbol": "005930",
            "name": "Samsung",
            "market": "KOSPI",
            "close_price": 70000.0,
            "target_price": 70000.0,
            "expected_return": 15.0,  # 15% return >> friction
            "action": "BUY",
            "change_pct": 0.02
        },
        # 2. Low return stock below friction hurdle -> Should be PRUNED (Gate 7.3)
        {
            "symbol": "000660",
            "name": "SK Hynix",
            "market": "KOSPI",
            "close_price": 120000.0,
            "target_price": 120000.0,
            "expected_return": 0.15,  # 0.15% return < (STT + spread + margin)
            "action": "BUY",
            "change_pct": 0.01
        },
        # 3. Limit-up locked stock (+29.9%) -> Should be SKIPPED (Gate 7.2)
        {
            "symbol": "035420",
            "name": "NAVER",
            "market": "KOSPI",
            "close_price": 200000.0,
            "target_price": 200000.0,
            "expected_return": 20.0,
            "action": "BUY",
            "change_pct": 0.299
        },
        # 4. Short signal on KRX stock -> Converted to CASH_OVERLAY (Gate 7.1)
        {
            "symbol": "051910",
            "name": "LG Chem",
            "market": "KOSPI",
            "close_price": 300000.0,
            "target_price": 300000.0,
            "expected_return": 10.0,
            "action": "SHORT",
            "change_pct": -0.02
        }
    ]

    weights = {
        "005930": 0.20,
        "000660": 0.10,
        "035420": 0.10,
        "051910": 0.10
    }

    plans = oms.generate_order_plan(predictions, weights, total_capital=100_000_000.0)

    syms_planned = [p["symbol"] for p in plans]
    # Samsung should pass
    assert "005930" in syms_planned

    # SK Hynix (below hurdle) should be pruned
    assert "000660" not in syms_planned

    # NAVER (limit-up locked) should be skipped
    assert "035420" not in syms_planned

    # LG Chem (short) should be CASH_OVERLAY hedge flag
    lg_plan = next((p for p in plans if p["symbol"] == "051910"), None)
    assert lg_plan is not None
    assert lg_plan["action"] == "CASH_OVERLAY"
    assert lg_plan["status"] == "HEDGE_FLAG"
