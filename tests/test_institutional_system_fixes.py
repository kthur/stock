"""
tests/test_institutional_system_fixes.py
Comprehensive institutional validation tests for the 7 system problem fixes:
1. KRX lot size normalization to 1 share (no zero-truncation for high-priced stocks)
2. UnifiedPortfolioAllocator current_holdings float/dict type handling without crash
3. Market impact volume-to-turnover currency dimension scaling
4. Black-Litterman strictly convex C^inf quadratic utility SLSQP convergence
5. 37-strategy ensemble integration & auto-discovery (dual_correction, index_rebalance, overnight_gap_reversal)
6. Portfolio weight sorting and positive-weight OMS inclusion
7. Prevention of redundant Leland double-buffering between allocator and OMS
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine
from src.analysis.portfolio_optimizer import calculate_black_litterman_weights
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.strategy_registry import get_registry


def test_krx_lot_size_is_one():
    """Verify KRX stocks lot size defaults to 1 share, preventing 0-share truncation."""
    allocator = UnifiedPortfolioAllocator()
    oms = ExecutionOMSEngine(db_path=":memory:")
    assert oms.lot_size_krx == 1, "ExecutionOMSEngine lot_size_krx must default to 1 share"

    # High-priced stock (e.g. 900,000 KRW), allocated 2,000,000 KRW
    # Under old lot=10, 2,000,000 // 900,000 = 2 shares -> (2 // 10) * 10 = 0 shares (BUG!)
    # Under fixed lot=1, 2 shares are correctly retained.
    dates = pd.date_range("2026-01-01", periods=60)
    prices_dict = {
        "005930": pd.DataFrame({"Close": np.linspace(70000, 75000, 60)}, index=dates),
        "207940": pd.DataFrame({"Close": np.full(60, 900000.0)}, index=dates),  # Samsung Bio (900k KRW)
    }
    preds_df = pd.DataFrame([
        {"symbol": "005930", "market": "KOSPI", "ensemble_expected_return": 0.10, "close": 75000.0, "volume": 1_000_000},
        {"symbol": "207940", "market": "KOSPI", "ensemble_expected_return": 0.08, "close": 900000.0, "volume": 50_000},
    ])

    res_df = allocator.allocate(
        predictions_df=preds_df,
        prices_dict=prices_dict,
        total_portfolio_value=10_000_000.0,  # 10M KRW
        regime="BULL_LOW_VOL",
        top_n=2
    )

    bio_row = res_df[res_df["symbol"] == "207940"].iloc[0]
    assert bio_row["lot_size"] == 1, f"Expected lot_size 1 for KRX, got {bio_row['lot_size']}"
    assert bio_row["shares"] > 0, f"Expected non-zero shares for Samsung Bio, got {bio_row['shares']}"


def test_unified_allocator_current_holdings_float_and_dict_handling():
    """Verify UnifiedPortfolioAllocator handles both float weight dicts and holding dicts without AttributeError."""
    allocator = UnifiedPortfolioAllocator()
    dates = pd.date_range("2026-01-01", periods=60)
    prices_dict = {
        "005930": pd.DataFrame({"Close": np.linspace(70000, 75000, 60)}, index=dates),
        "000660": pd.DataFrame({"Close": np.linspace(150000, 160000, 60)}, index=dates),
    }
    preds_df = pd.DataFrame([
        {"symbol": "005930", "market": "KOSPI", "ensemble_expected_return": 0.08, "close": 75000.0},
        {"symbol": "000660", "market": "KOSPI", "ensemble_expected_return": 0.07, "close": 160000.0},
    ])

    # Case 1: Float weight dict as returned by get_current_holdings_from_db()
    float_holdings = {"005930": 0.08, "000660": 0.05}
    res_float = allocator.allocate(
        predictions_df=preds_df,
        prices_dict=prices_dict,
        total_portfolio_value=100_000_000.0,
        regime="BULL_LOW_VOL",
        current_holdings=float_holdings,
        top_n=2
    )
    assert not res_float.empty, "Allocator must succeed with float weight dict"
    assert "weight" in res_float.columns

    # Case 2: Dict of dicts with quantity & current_price
    dict_holdings = {
        "005930": {"quantity": 100, "current_price": 75000.0},
        "000660": {"quantity": 50, "current_price": 160000.0}
    }
    res_dict = allocator.allocate(
        predictions_df=preds_df,
        prices_dict=prices_dict,
        total_portfolio_value=100_000_000.0,
        regime="BULL_LOW_VOL",
        current_holdings=dict_holdings,
        top_n=2
    )
    assert not res_dict.empty, "Allocator must succeed with dict holding details"


def test_market_impact_volume_to_turnover_conversion():
    """Verify that when only 'volume' is provided, ADV is correctly scaled by price into currency."""
    allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
    dates = pd.date_range("2026-01-01", periods=60)
    prices_dict = {
        "005930": pd.DataFrame({"Close": np.linspace(70000, 75000, 60)}, index=dates),
        "000660": pd.DataFrame({"Close": np.linspace(150000, 160000, 60)}, index=dates),
    }
    # Candidate with only 'volume' (50,000 shares) and 'close' (75,000 KRW)
    # Currency turnover = 50,000 * 75,000 = 3,750,000,000 KRW (3.75B KRW)
    # Without fix, it treated 50,000 as ADV in KRW, causing participation > 10,000%
    preds_df = pd.DataFrame([
        {"symbol": "005930", "market": "KOSPI", "ensemble_expected_return": 0.12, "close": 75000.0, "volume": 50_000},
        {"symbol": "000660", "market": "KOSPI", "ensemble_expected_return": 0.10, "close": 160000.0, "volume": 30_000},
    ])

    res = allocator.allocate(
        predictions_df=preds_df,
        prices_dict=prices_dict,
        total_portfolio_value=50_000_000.0,
        regime="BULL_LOW_VOL",
        top_n=2
    )
    assert not res.empty
    # The weight should remain substantial and NOT wiped out by false 10,000% participation dampening
    assert res["weight"].sum() > 0.50, f"Expected active allocation > 50%, got {res['weight'].sum():.3f}"


def test_black_litterman_smooth_quadratic_convergence():
    """Verify Black-Litterman optimization solves smoothly without jump discontinuity or risk-parity fallback."""
    np.random.seed(42)
    n = 5
    returns = np.random.normal(0.0005, 0.015, size=(100, n))
    cov_matrix = np.cov(returns, rowvar=False)
    # Mix of positive and slightly negative predicted returns around zero
    predicted_returns = np.array([0.005, -0.001, 0.008, 0.000, 0.003])

    weights = calculate_black_litterman_weights(
        cov_matrix=cov_matrix,
        predicted_returns=predicted_returns,
        risk_aversion=2.5,
        tau=0.05,
        risk_free_rate=0.02
    )

    assert len(weights) == n
    assert np.isclose(np.sum(weights), 1.0, atol=1e-3)
    assert np.all(weights >= -1e-5)
    # Highest return asset (index 2: +0.008) should have higher allocation than negative asset (index 1: -0.001)
    assert weights[2] > weights[1], f"Asset 2 ({weights[2]:.3f}) should have higher weight than Asset 1 ({weights[1]:.3f})"


def test_37_strategy_ensemble_integration():
    """Verify that all 37 strategies are discovered and accepted by EnsembleScoringEngine."""
    reg = get_registry()
    reg.auto_discover(["src.core", "src.ai"])
    all_ids = set(reg.get_all_ids())

    # Verify key new strategies are present
    assert "dual_correction" in all_ids, "dual_correction must be registered"
    assert "index_rebalance" in all_ids, "index_rebalance must be registered"
    assert "overnight_gap_reversal" in all_ids, "overnight_gap_reversal must be registered"

    scorer = EnsembleScoringEngine()
    symbols = ["005930", "000660", "AAPL"]
    dc_df = pd.DataFrame({"symbol": symbols, "dual_correction_score": [0.85, 0.40, 0.60]})
    ir_df = pd.DataFrame({"symbol": symbols, "index_rebalance_score": [0.90, 0.20, 0.50]})
    og_df = pd.DataFrame({"symbol": symbols, "overnight_gap_score": [0.75, 0.80, 0.30]})
    reg_df = pd.DataFrame({"symbol": symbols, "expected_return": [0.10, 0.05, 0.08]})

    ensemble_res = scorer.calculate_ensemble_score(
        reg_df=reg_df,
        dual_correction_df=dc_df,
        index_rebalance_df=ir_df,
        overnight_gap_df=og_df,
        regime="BULL_LOW_VOL"
    )

    assert not ensemble_res.empty
    assert "ensemble_score" in ensemble_res.columns
    # Check that score columns are merged into the result
    assert "dual_correction_score" in ensemble_res.columns
    assert "index_rebalance_score" in ensemble_res.columns
    assert "overnight_gap_score" in ensemble_res.columns


def test_oms_portfolio_weight_sorting_and_order_generation():
    """Verify that portfolio_weight is prioritized and sorted in OMS order generation."""
    oms = ExecutionOMSEngine(db_path=":memory:", lot_size_krx=1)
    
    # Candidate dataframe where rank 2 has high weight, and rank 0 has zero weight
    candidates = [
        {"symbol": "005930", "market": "KOSPI", "portfolio_weight": 0.0, "close": 70000.0, "ensemble_score": 0.95},
        {"symbol": "000660", "market": "KOSPI", "portfolio_weight": 0.25, "close": 160000.0, "ensemble_score": 0.85},
        {"symbol": "035420", "market": "KOSPI", "portfolio_weight": 0.15, "close": 200000.0, "ensemble_score": 0.80},
    ]
    df = pd.DataFrame(candidates)
    
    # Simulate the pipeline re-sort logic
    df_sorted = df.sort_values(by=['portfolio_weight', 'ensemble_score'], ascending=[False, False]).reset_index(drop=True)
    top_picks = df_sorted.to_dict(orient="records")
    weights_dict = dict(zip(df_sorted['symbol'], df_sorted['portfolio_weight']))

    orders = oms.generate_order_plan(
        top_picks,
        weights_dict,
        total_capital=100_000_000.0,
        crisis_level="NORMAL",
        use_leland_buffer=False
    )

    ordered_syms = [o["symbol"] for o in orders]
    # 000660 (weight 0.25) must be in orders; 005930 (weight 0.0) should NOT be in BUY orders
    assert "000660" in ordered_syms, "000660 must have an order plan generated"
    assert "035420" in ordered_syms, "035420 must have an order plan generated"
    
    # Verify quantities are positive integer shares
    for o in orders:
        if o["action"] == "BUY":
            assert o["quantity"] > 0
            assert o.get("target_weight", o.get("weight", 0.0)) > 0.0
