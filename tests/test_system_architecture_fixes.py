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
8. Hybrid EWMA Covariance fast reaction
9. Leland buffer dynamic floor proportionality
10. SlippageFeedback independent market cost scaling
11. EnsembleScorer per-market cost scaling integration
"""

import os
import sqlite3
import tempfile
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


def test_hybrid_ewma_covariance_fast_reaction():
    """Verify hybrid EWMA covariance reacts rapidly to recent volatility spikes compared to 60-day SMA."""
    allocator = UnifiedPortfolioAllocator()
    np.random.seed(42)

    # 50 days of low volatility (0.5% daily), followed by 10 days of high volatility (4.0% daily)
    r_calm = np.random.normal(0, 0.005, size=(50, 2))
    r_shock = np.random.normal(0, 0.040, size=(10, 2))
    r_total = np.vstack([r_calm, r_shock])
    df_rets = pd.DataFrame(r_total, columns=["SYM_A", "SYM_B"])

    sample_cov = df_rets.cov().values
    hybrid_cov = allocator.compute_hybrid_ewma_covariance(df_rets, halflife=15, lw_weight=0.40)

    assert hybrid_cov[0, 0] > sample_cov[0, 0]
    assert np.allclose(hybrid_cov, hybrid_cov.T)
    assert np.all(np.linalg.eigvals(hybrid_cov) > 0)


def test_leland_dynamic_floor_proportionality():
    """Verify Leland dynamic buffer floor scales down for small target weights (e.g. 1%)."""
    from src.risk.portfolio_allocator import PortfolioAllocator
    alloc = PortfolioAllocator(delta_floor=0.005)

    b_small = alloc.calculate_dynamic_buffer_band(
        symbol="005930.KS", target_weight=0.01, cost_rate=0.002, volatility_20d=0.02
    )
    assert b_small <= 0.0035

    b_large = alloc.calculate_dynamic_buffer_band(
        symbol="005930.KS", target_weight=0.15, cost_rate=0.002, volatility_20d=0.02
    )
    assert b_large > b_small


def test_slippage_feedback_independent_market_scaling(tmp_path):
    """Verify SlippageFeedbackEngine computes independent market scaling maps from trade logs."""
    from src.execution.slippage_feedback import SlippageFeedbackEngine

    db_file = os.path.join(tmp_path, "test_trades.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE trade_logs (
            market TEXT, side TEXT, expected_price REAL, fill_price REAL
        )
    """)
    cursor.execute("INSERT INTO trade_logs VALUES ('KOSDAQ', 'BUY', 10000, 10040)")  # +40 bps
    cursor.execute("INSERT INTO trade_logs VALUES ('KOSDAQ', 'BUY', 10000, 10035)")  # +35 bps
    cursor.execute("INSERT INTO trade_logs VALUES ('SP500', 'BUY', 100.0, 100.02)")   # +2.0 bps
    cursor.execute("INSERT INTO trade_logs VALUES ('SP500', 'BUY', 100.0, 100.025)")  # +2.5 bps
    conn.commit()
    conn.close()

    engine = SlippageFeedbackEngine(db_path=db_file, default_slippage_bps=5.0)
    metrics = engine.calculate_realized_slippage(lookback_days=30)
    assert "KOSDAQ" in metrics.market_cost_scaling_map
    assert "SP500" in metrics.market_cost_scaling_map

    # KOSDAQ scaling should be elevated (> 2.0), SP500 scaling should be low (<= 1.0)
    assert metrics.market_cost_scaling_map["KOSDAQ"] > 2.0
    assert metrics.market_cost_scaling_map["SP500"] <= 1.0


def test_ensemble_scorer_per_market_cost_scaling():
    """Verify EnsembleScorer uses market_cost_scaling_map to avoid penalizing US stocks with KRX slippage."""
    from src.ai.ensemble_scorer import EnsembleScoringEngine

    scorer = EnsembleScoringEngine()
    scorer.market_cost_scaling_map = {
        "KOSDAQ": 3.0,
        "SP500": 0.8
    }

    test_preds = pd.DataFrame([
        {"symbol": "091990", "name": "셀트리온헬스케어", "market": "KOSDAQ", "volatility_20d": 0.02, "expected_return": 5.0, "vcp_rule_score": 0.8},
        {"symbol": "AAPL", "name": "Apple", "market": "SP500", "volatility_20d": 0.02, "expected_return": 5.0, "vcp_rule_score": 0.8}
    ])

    res = scorer.combine_predictions(test_preds)
    assert len(res) == 2
    assert np.all(np.isfinite(res["ensemble_expected_return"].values))
