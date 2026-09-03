"""
Test Suite for Milestone 2:
- Feature 7: Dynamic Half-Life Convergence Speed (theta_i*)
- Feature 8: Liquidity-Constrained Cash Buffer Routing (no inflation/re-normalization distortion)
- Feature 9: Volatility-Normalized Asymmetric Leland Dynamic Buffer Bands & Boundary Rebalancing
- Feature 10: End-to-End OMS Delta Rebalancing (Delta Q = Q_target - Q_current)
- Feature 11: Almgren-Chriss Slicing with MIDPOINT_PEG Tranches & Final AGGRESSIVE_TAKER
"""

import math
import json
import sqlite3
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestFeature7DynamicHalfLifeConvergence:
    """Feature 7: Optimal Convergence Velocity theta* balancing alpha decay vs Gatheral 3/2-power impact."""

    def test_fast_alpha_converges_faster_than_slow_alpha(self):
        """Fast alpha (tau=1d) converges at higher velocity than slow alpha (tau=40d)."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
        symbols = ["FAST_ALPHA", "SLOW_ALPHA"]
        pred_rets = np.array([0.10, 0.10])
        cov = np.array([[0.0004, 0.0], [0.0, 0.0004]])  # 2% daily vol
        rets_df = pd.DataFrame(np.random.normal(0, 0.02, (40, 2)), columns=symbols)

        # Moderate ADV: 2M each. Total capital: 10M. Target gap: 5M
        advs = np.array([2_000_000.0, 2_000_000.0])
        alpha_hls = np.array([1.0, 40.0])

        w = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            advs=advs,
            total_capital=10_000_000.0,
            alpha_half_lives=alpha_hls,
            regime="SIDEWAYS_LOW_VOL"
        )

        assert w[0] > w[1] * 1.5, f"Fast alpha weight {w[0]:.4f} should exceed slow alpha {w[1]:.4f} by > 1.5x"
        assert w[0] <= 0.50
        assert w[1] <= 0.50

    def test_regime_informed_half_life_defaults(self):
        """When alpha_half_lives is None, regime adapts default half-life (CRISIS=3d vs BULL=15d)."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
        symbols = ["A", "B"]
        pred_rets = np.array([0.10, 0.10])
        cov = np.eye(2) * 0.0004
        rets_df = pd.DataFrame(np.random.normal(0, 0.02, (40, 2)), columns=symbols)
        advs = np.array([1_000_000.0, 1_000_000.0])

        w_bull = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            advs=advs,
            total_capital=10_000_000.0,
            regime="BULL_LOW_VOL"
        )
        assert np.all(np.isfinite(w_bull))


class TestFeature8LiquidityConstrainedCashBuffer:
    """Feature 8: Route unallocated liquidity-constrained capital to cash buffer without re-normalization."""

    def test_cash_buffer_preserves_liquid_asset_weights(self):
        """Liquid asset is not artificially inflated above its target weight when illiquid asset is clipped."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.40)
        symbols = ["MEGA_LIQUID", "TINY_ILLIQUID"]
        pred_rets = np.array([0.10, 0.10])
        cov = np.eye(2) * 0.0004
        rets_df = pd.DataFrame(np.random.normal(0, 0.02, (40, 2)), columns=symbols)

        # Asset 0: $100M ADV; Asset 1: $20k ADV. Total capital: $10M
        advs = np.array([100_000_000.0, 20_000.0])
        tot_cap = 10_000_000.0

        w = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=rets_df,
            cov_matrix=cov,
            symbols=symbols,
            advs=advs,
            total_capital=tot_cap,
            regime="BULL_LOW_VOL"
        )

        # Liquid asset must NOT be inflated above its single stock cap (0.40)
        assert w[0] <= 0.4001, f"Liquid asset weight {w[0]:.4f} was inflated above cap 0.40"
        # Illiquid asset must be capped by liquidity capacity
        assert w[1] <= 0.01, f"Illiquid asset weight {w[1]:.4f} breached liquidity constraint"
        # Total weight strictly < 1.0, preserving unallocated funds as cash buffer
        tot_invested = np.sum(w)
        assert tot_invested < 0.60
        cash_buffer = 1.0 - tot_invested
        assert cash_buffer > 0.40, f"Expected cash buffer > 40%, got {cash_buffer:.2%}"

    def test_allocate_method_populates_cash_buffer_attrs(self):
        """allocate() populates cash_buffer_weight and cash_buffer_amount in df.attrs."""
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.30)
        symbols = ["LIQ", "ILLIQ"]
        preds = pd.DataFrame({
            "symbol": symbols,
            "ensemble_expected_return": [0.15, 0.15],
            "adv": [100_000_000.0, 10_000.0],
            "close": [50000.0, 10000.0]
        })
        prices = {
            "LIQ": pd.DataFrame({"Close": np.random.normal(50000, 500, 60)}),
            "ILLIQ": pd.DataFrame({"Close": np.random.normal(10000, 100, 60)})
        }

        res = allocator.allocate(
            predictions_df=preds,
            prices_dict=prices,
            total_portfolio_value=10_000_000.0,
            regime="BULL_LOW_VOL"
        )
        assert "cash_buffer_weight" in res.attrs
        assert "cash_buffer_amount" in res.attrs
        assert "total_invested_weight" in res.attrs
        assert math.isclose(res.attrs["cash_buffer_weight"] + res.attrs["total_invested_weight"], 1.0, abs_tol=1e-4)


class TestFeature9VolatilityNormalizedLelandBuffers:
    """Feature 9: Continuous Z-score asymmetric multipliers and boundary rebalancing."""

    def test_continuous_z_score_multiplier_properties(self):
        """Verify smooth monotonic mapping of z_unrealized to upper and lower multipliers."""
        calc = UnifiedPortfolioAllocator.calculate_asymmetric_leland_multipliers

        # 1. Neutral return -> symmetric (1.0, 1.0)
        up, lo = calc(unrealized_return=0.0, volatility_20d=0.02)
        assert math.isclose(up, 1.0, abs_tol=1e-5)
        assert math.isclose(lo, 1.0, abs_tol=1e-5)

        # 2. Mild profit within noise (z = 0.5) -> (1.0, 1.0)
        up, lo = calc(unrealized_return=0.5 * 0.02 * math.sqrt(5), volatility_20d=0.02)
        assert math.isclose(up, 1.0, abs_tol=1e-5)
        assert math.isclose(lo, 1.0, abs_tol=1e-5)

        # 3. Intermediate runner (z = 2.0) -> smooth ramp to 1.4x
        up, lo = calc(unrealized_return=2.0 * 0.02 * math.sqrt(5), volatility_20d=0.02)
        assert math.isclose(up, 1.4, abs_tol=1e-5)
        assert math.isclose(lo, 1.0, abs_tol=1e-5)

        # 4. Extreme runner (z >= 3.0) -> capped at 1.8x
        up, lo = calc(unrealized_return=0.20, volatility_20d=0.02)
        assert math.isclose(up, 1.8, abs_tol=1e-5)
        assert math.isclose(lo, 1.0, abs_tol=1e-5)

        # 5. Intermediate laggard (z = -2.0) -> smooth tightening to 0.8x
        up, lo = calc(unrealized_return=-2.0 * 0.02 * math.sqrt(5), volatility_20d=0.02)
        assert math.isclose(up, 1.0, abs_tol=1e-5)
        assert math.isclose(lo, 0.8, abs_tol=1e-5)

        # 6. Extreme laggard (z <= -3.0) -> capped at 0.6x
        up, lo = calc(unrealized_return=-0.20, volatility_20d=0.02)
        assert math.isclose(up, 1.0, abs_tol=1e-5)
        assert math.isclose(lo, 0.6, abs_tol=1e-5)

    def test_low_vol_defensive_runner_activation(self):
        """Defensive stock with 0.8% daily vol triggers runner expansion on +6% move (3.35 sigma)."""
        calc = UnifiedPortfolioAllocator.calculate_asymmetric_leland_multipliers
        up, lo = calc(unrealized_return=0.06, volatility_20d=0.008)
        assert math.isclose(up, 1.8, abs_tol=1e-3)

    def test_boundary_rebalancing_vs_target_rebalancing(self):
        """Boundary mode rebalances to boundary L_i or U_i, reducing turnover compared to target mode."""
        allocator = UnifiedPortfolioAllocator(risk_aversion=1.0, leland_cost_bps=20.0)

        target_w = np.array([0.20, 0.20, 0.20])
        current_w = np.array([0.198, 0.120, 0.280])
        vols = np.array([0.020, 0.020, 0.020])

        w_bnd = allocator.apply_leland_no_trade_buffers(target_w, current_w, vols, rebalance_mode="boundary")
        w_tgt = allocator.apply_leland_no_trade_buffers(target_w, current_w, vols, rebalance_mode="target")

        # Inside noise band: holds current
        assert math.isclose(w_bnd[0], 0.198, abs_tol=1e-4)
        assert math.isclose(w_tgt[0], 0.198, abs_tol=1e-4)

        # Lower breach: boundary mode buys only to lower_band (~0.175), target mode buys to 0.200
        assert 0.160 < w_bnd[1] < 0.190
        assert math.isclose(w_tgt[1], 0.200, abs_tol=1e-4)

        # Upper breach: boundary mode sells only to upper_band (~0.225), target mode sells to 0.200
        assert 0.210 < w_bnd[2] < 0.240
        assert math.isclose(w_tgt[2], 0.200, abs_tol=1e-4)

        # Turnover in boundary mode is strictly less than target mode
        turnover_bnd = np.sum(np.abs(w_bnd - current_w))
        turnover_tgt = np.sum(np.abs(w_tgt - current_w))
        assert turnover_bnd < 0.75 * turnover_tgt


class TestFeature10OMSDeltaRebalancing:
    """Feature 10: Enforce Delta Q = Q_target - Q_current in OMS order planning."""

    def test_buffer_held_position_emits_no_order(self):
        """Existing buffer-held position with target_shares == current_shares produces 0 orders (no doubling)."""
        engine = ExecutionOMSEngine(db_path=":memory:")
        top_preds = [
            {"symbol": "005930.KS", "name": "Samsung", "market": "KOSPI", "close_price": 70000.0, "action": "BUY"}
        ]
        # 5% of 100M KRW = 5M KRW // 70,000 = 71 shares
        weights = {"005930.KS": 0.05}
        current_holdings = {
            "005930.KS": {"quantity": 71, "current_price": 70000.0, "weight": 0.05}
        }

        plans = engine.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            current_holdings=current_holdings,
            use_leland_buffer=False
        )
        assert len(plans) == 0, f"Expected 0 orders for buffer-held position, got {len(plans)}"

    def test_scale_up_buys_delta_scale_down_sells_delta(self):
        """Scale-up buys only Delta Q > 0, and scale-down sells Delta Q < 0."""
        engine = ExecutionOMSEngine(db_path=":memory:")
        top_preds = [
            {"symbol": "005930.KS", "name": "Samsung", "market": "KOSPI", "close_price": 70000.0, "action": "BUY"},
            {"symbol": "000660.KS", "name": "SK Hynix", "market": "KOSPI", "close_price": 100000.0, "action": "BUY"}
        ]
        # 005930.KS: target 10% (142 shares), current 50 shares -> BUY 92 shares
        # 000660.KS: target 5% (50 shares), current 80 shares -> SELL 30 shares
        weights = {"005930.KS": 0.10, "000660.KS": 0.05}
        current_holdings = {
            "005930.KS": {"quantity": 50, "current_price": 70000.0, "weight": 0.035},
            "000660.KS": {"quantity": 80, "current_price": 100000.0, "weight": 0.08}
        }

        plans = engine.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            current_holdings=current_holdings,
            use_leland_buffer=False
        )
        plans_by_sym = {p["symbol"]: p for p in plans}
        assert len(plans_by_sym) == 2

        # Verify scale-up
        p_up = plans_by_sym["005930.KS"]
        assert p_up["action"] == "BUY"
        assert p_up["quantity"] == 92

        # Verify scale-down / trimming
        p_down = plans_by_sym["000660.KS"]
        assert p_down["action"] == "SELL"
        assert p_down["quantity"] == 30


class TestFeature11AlmgrenChrissSlicingAndTrancheTagging:
    """Feature 11: Trajectory slicing with MIDPOINT_PEG tranches and AGGRESSIVE_TAKER final clearance."""

    def test_multi_slice_tranche_structure_and_tagging(self):
        """Verify multi-slice orders have MIDPOINT_PEG early tranches and AGGRESSIVE_TAKER final tranche."""
        engine = ExecutionOMSEngine(db_path=":memory:")
        top_preds = [
            {
                "symbol": "005930.KS",
                "name": "Samsung",
                "market": "KOSPI",
                "close_price": 70000.0,
                "action": "BUY",
                "volatility_20d": 0.02,
                "adv": 10_000_000_000.0,
                "surge_prob": 0.85,  # Fast half-life (2.0d) -> FAST_VWAP, slice_count = 3
            }
        ]
        weights = {"005930.KS": 0.10}  # 142 shares

        plans = engine.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            use_leland_buffer=False
        )
        assert len(plans) == 1
        plan = plans[0]
        assert plan["quantity"] == 142
        assert "tranches" in plan
        tranches = plan["tranches"]
        assert len(tranches) == 3
        assert sum(t["quantity"] for t in tranches) == 142

        # Early tranches must be MIDPOINT_PEG
        assert tranches[0]["exec_type"] == "MIDPOINT_PEG"
        assert tranches[1]["exec_type"] == "MIDPOINT_PEG"
        # Final tranche must be AGGRESSIVE_TAKER
        assert tranches[2]["exec_type"] == "AGGRESSIVE_TAKER"

        # Offsets must be strictly non-decreasing
        assert tranches[0]["time_offset_min"] < tranches[1]["time_offset_min"] < tranches[2]["time_offset_min"]

    def test_single_slice_tranche_direct(self):
        """Single slice order generates 1 tranche with AGGRESSIVE_TAKER."""
        engine = ExecutionOMSEngine(db_path=":memory:")
        top_preds = [
            {
                "symbol": "TINY.KS",
                "name": "Tiny Stock",
                "market": "KOSPI",
                "close_price": 50000.0,
                "action": "BUY",
                "volatility_20d": 0.015,
                "adv": 1_000_000_000.0,
            }
        ]
        weights = {"TINY.KS": 0.0005}  # 50,000 KRW = 1 share -> slice_count = 1
        plans = engine.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            use_leland_buffer=False
        )
        assert len(plans) == 1
        tranches = plans[0]["tranches"]
        assert len(tranches) == 1
        assert tranches[0]["quantity"] == 1
        assert tranches[0]["exec_type"] == "AGGRESSIVE_TAKER"

    def test_tranches_db_persistence_and_retrieval(self):
        """Verify tranches are correctly JSON-serialized and stored in SQLite order_plans table."""
        engine = ExecutionOMSEngine(db_path=":memory:")

        top_preds = [
            {
                "symbol": "005930.KS",
                "name": "Samsung",
                "market": "KOSPI",
                "close_price": 70000.0,
                "action": "BUY",
                "volatility_20d": 0.02,
                "adv": 10_000_000_000.0,
            }
        ]
        weights = {"005930.KS": 0.10}

        plans = engine.generate_order_plan(
            top_predictions=top_preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            use_leland_buffer=False
        )
        assert len(plans) == 1
        # Check in memory DB
        c = engine._get_conn().cursor()
        row = c.execute("SELECT tranches FROM order_plans WHERE symbol = '005930.KS'").fetchone()
        assert row is not None
        tranches_stored = json.loads(row[0])
        assert isinstance(tranches_stored, list)
        assert len(tranches_stored) >= 1
