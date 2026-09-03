# -*- coding: utf-8 -*-
"""
Tests for Phase 1 & 2 Architectural Fixes:
1. Black-Litterman scale alignment (C-01)
2. Cross-Asset Spillover timezone lag / lookahead bias elimination (C-03)
3. Whitening filter amplification capping (C-05)
4. Target volatility cash drag elimination (C-06)
5. TurnoverOptimizer relative shift rebalancing (C-07)
6. OMS Gate 7.4 sell order gap bypass (H-01)
7. Supply Chain GNN message passing non-explosion (H-05)
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.portfolio_optimizer import calculate_black_litterman_weights
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
from src.core.supply_chain_gnn import SupplyChainGNNEngine
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.turnover_optimizer import TurnoverOptimizer


def test_black_litterman_percentage_and_decimal_alignment():
    """Verify BL weights do not blow up or collapse when returns are in percentage vs decimal."""
    np.random.seed(42)
    n = 5
    vols = np.array([0.015, 0.020, 0.018, 0.022, 0.016])
    corr = np.eye(n) * 0.6 + 0.4
    cov = np.outer(vols, vols) * corr

    q_pct = np.array([15.0, 10.0, 5.0, -2.0, 8.0])
    w_pct = calculate_black_litterman_weights(cov, q_pct, returns_are_percentage=True)

    q_dec = q_pct / 100.0
    w_dec = calculate_black_litterman_weights(cov, q_dec, returns_are_percentage=False)

    np.testing.assert_allclose(w_pct, w_dec, atol=1e-4)
    assert np.isclose(np.sum(w_pct), 1.0, atol=1e-4)
    assert np.all(w_pct >= 0.0)


def test_target_volatility_cash_drag_eliminated():
    """Verify apply_target_volatility_scaling achieves target allocation without double scaling."""
    allocator = UnifiedPortfolioAllocator(target_volatility=0.12, default_max_total_allocation=0.90)
    
    n = 4
    weights = np.full(n, 1.0 / n)
    daily_var = (0.12 / np.sqrt(252.0)) ** 2
    cov_matrix = np.eye(n) * daily_var

    scaled_weights, effective_alloc = allocator.apply_target_volatility_scaling(
        weights, cov_matrix, regime="BULL"
    )

    assert effective_alloc >= 0.95
    assert np.isclose(np.sum(scaled_weights), effective_alloc, atol=1e-4)


def test_cross_asset_spillover_krx_timezone_lag():
    """Verify US macro series gets lagged by 1 day when evaluating KRX symbols to eliminate lookahead bias."""
    engine = CrossAssetSpilloverEngine()

    dates = pd.date_range("2026-01-01", periods=10, freq="B")
    macro_df = pd.DataFrame({
        "sp500": [4800, 4850, 4900, 4920, 4950, 4980, 5000, 5000, 5000, 5500],
        "usdkrw": [1300] * 10,
        "vix": [15.0] * 10,
        "sox": [3000] * 10,
        "tnx": [4.0] * 10,
        "wti": [75.0] * 10,
        "gold": [2000.0] * 10,
        "dxy": [104.0] * 10,
    }, index=dates)

    vec_us = engine._extract_macro_vector(macro_df, is_krx=False)
    vec_krx = engine._extract_macro_vector(macro_df, is_krx=True)

    assert vec_us["sp500"] > vec_krx["sp500"]
    assert np.isclose(vec_krx["sp500"], 0.0076, atol=0.01)


def test_supply_chain_gnn_hop2_bounded():
    """Verify Hop 2 message passing does not compound bullwhip non-linear multiplier exponentially."""
    engine = SupplyChainGNNEngine()
    engine.in_adj = {
        "B": [("A", 1.0)],
        "C": [("B", 1.0)],
    }
    node_mom = {"A": -0.10}
    hop1, hop2 = engine._propagate_message_passing(node_mom)

    assert np.isclose(hop1["B"], -0.135, atol=1e-4)
    assert np.isclose(hop2["C"], -0.135, atol=1e-4)


def test_oms_gate_7_4_sell_bypass():
    """Verify Gate 7.4 skips adverse gap for BUY orders, but allows SELL orders through."""
    oms = ExecutionOMSEngine()

    pred = [
        {"symbol": "005930.KS", "close_price": 70000, "change_pct": -15.0, "volatility_20d": 0.02, "market": "KOSPI", "expected_return": 0.10}
    ]

    # BUY: should be skipped by Gate 7.4 (-15% gap down)
    plans_buy = oms.generate_order_plan(
        top_predictions=pred,
        portfolio_weights={"005930.KS": 0.05},
        total_capital=100000000.0,
        current_holdings={}
    )
    assert len(plans_buy) == 0

    # SELL: current holding 5%, target weight 0%: should NOT be blocked by Gate 7.4
    plans_sell = oms.generate_order_plan(
        top_predictions=pred,
        portfolio_weights={"005930.KS": 0.0},
        total_capital=100000000.0,
        current_holdings={"005930.KS": 0.05}
    )
    assert len(plans_sell) == 1
    assert plans_sell[0]["action"] == "SELL"


def test_turnover_optimizer_large_relative_shift():
    """Verify TurnoverOptimizer allows significant relative position shift (e.g. 2% -> 5%) to rebalance."""
    opt = TurnoverOptimizer(turnover_threshold_pct=0.05, min_rebalance_delta_krw=50000.0)

    res_minor = opt.optimize_allocations(
        current_holdings={"005930.KS": 0.10},
        target_allocations={"005930.KS": 0.12},
        total_capital=100000000.0
    )
    assert res_minor["005930.KS"]["action"] == "HOLD"

    res_major = opt.optimize_allocations(
        current_holdings={"005930.KS": 0.02},
        target_allocations={"005930.KS": 0.05},
        total_capital=100000000.0
    )
    assert res_major["005930.KS"]["action"] == "BUY"
    assert res_major["005930.KS"]["target_weight"] > 0.02
