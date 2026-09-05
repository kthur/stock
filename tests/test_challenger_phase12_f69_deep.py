"""
test_challenger_phase12_f69_deep.py
Deep edge case, fuzzing, and extreme boundary stress tests for Phase 12 Genesis (F69.1, F69.2).
Author: Challenger 2 (Empirical Challenger)
"""

import math
import numpy as np
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.core.fast_lob_engine import DeepHawkesArrivalProcess
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestDeepAdversarialFisherRao:
    """Extreme edge case and degenerate input tests for Fisher-Rao Barycenter on S^3."""

    def test_empty_and_degenerate_model_weights(self):
        """Verify behavior with empty, invalid, or mismatched inputs."""
        allocator = UnifiedPortfolioAllocator()

        # 1. Empty list
        q_empty = allocator.compute_fisher_rao_barycenter_blend([])
        assert np.isclose(sum(q_empty.values()), 1.0)
        for v in q_empty.values():
            assert np.isclose(v, 0.25)

        # 2. Negative weight inputs in dict
        neg_dict = {"bl": -1.0, "herc": 0.5, "rp": 0.3, "cvar": 0.2}
        q_neg = allocator.compute_fisher_rao_barycenter_blend(neg_dict)
        assert np.isclose(sum(q_neg.values()), 1.0, atol=1e-4)
        for v in q_neg.values():
            assert v >= 0.0

        # 3. All zeros dict
        all_zero = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        q_zero = allocator.compute_fisher_rao_barycenter_blend(all_zero)
        assert np.isclose(sum(q_zero.values()), 1.0, atol=1e-4)
        for v in q_zero.values():
            assert np.isclose(v, 0.25, atol=1e-2)

        # 4. 1D array input
        arr_1d = np.array([0.4, 0.3, 0.2, 0.1])
        q_1d = allocator.compute_fisher_rao_barycenter_blend(arr_1d)
        assert np.isclose(sum(q_1d.values()), 1.0, atol=1e-4)
        assert np.isclose(q_1d["bl"], 0.4, atol=1e-2)

        # 5. Invalid shape array
        arr_bad = np.array([0.5, 0.5])
        q_bad = allocator.compute_fisher_rao_barycenter_blend(arr_bad)
        assert np.isclose(sum(q_bad.values()), 1.0, atol=1e-4)

    def test_extreme_step_sizes_and_tolerances(self):
        """Verify algorithm stability under extreme step sizes and tolerances."""
        allocator = UnifiedPortfolioAllocator()
        models = [
            {"bl": 0.60, "herc": 0.20, "rp": 0.10, "cvar": 0.10},
            {"bl": 0.10, "herc": 0.60, "rp": 0.20, "cvar": 0.10},
        ]

        # Tiny step size
        q_tiny = allocator.compute_fisher_rao_barycenter_blend(models, step_size=0.001, max_iter=20)
        assert np.isclose(sum(q_tiny.values()), 1.0, atol=1e-4)

        # Huge step size (clipped in implementation)
        q_huge = allocator.compute_fisher_rao_barycenter_blend(models, step_size=100.0, max_iter=20)
        assert np.isclose(sum(q_huge.values()), 1.0, atol=1e-4)

        # Ultra-tight tolerance
        q_tight = allocator.compute_fisher_rao_barycenter_blend(models, tol=1e-15, max_iter=50)
        assert np.isclose(sum(q_tight.values()), 1.0, atol=1e-4)


class TestDeepAdversarialUltraEVaR:
    """Extreme edge case and boundary tests for Ultra-EVaR."""

    def test_single_sample_return(self):
        """Verify Ultra-EVaR with single sample."""
        allocator = UnifiedPortfolioAllocator()
        res = allocator.compute_ultra_evar_risk_measure(np.array([-0.05]))
        assert math.isfinite(res["ultra_evar_value"])
        assert res["ultra_evar_value"] >= res["super_evar_value"] - 1e-6

    def test_nan_and_inf_returns(self):
        """Verify handling of NaN and Inf return vectors."""
        allocator = UnifiedPortfolioAllocator()
        dirty_rets = np.array([np.nan, 0.02, -0.05, np.inf, -np.inf, 0.01])
        res = allocator.compute_ultra_evar_risk_measure(dirty_rets)
        assert math.isfinite(res["ultra_evar_value"])
        assert res["ultra_evar_value"] >= res["super_evar_value"] - 1e-6

    def test_zero_parameters_reduction_to_evar(self):
        """When xi_jump = 0 and xi_frechet = 0, Ultra-EVaR should closely track EVaR."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(111)
        returns = np.random.normal(-0.01, 0.02, size=500)

        res = allocator.compute_ultra_evar_risk_measure(
            returns, alpha=0.05, xi_jump=0.0, xi_frechet=0.0
        )
        assert math.isfinite(res["ultra_evar_value"])
        assert math.isfinite(res["evar_value"])
        # With zero parameters, ultra_evar should equal super_evar and evar
        assert np.isclose(res["ultra_evar_value"], res["evar_value"], atol=1e-4)


class TestDeepAdversarialExecutionSORAndOMS:
    """Extreme edge case tests for SOR and dual OMS calculate_peg_limit_price."""

    def test_zero_or_negative_quantity_order_plan(self):
        """Verify SOR cleanly handles zero or negative order quantities."""
        sor = SmartOrderRouter()
        plan_zero = {"symbol": "NVDA", "quantity": 0, "target_price": 100.0}
        routed_zero = sor.route_order(plan_zero, version=12)
        assert routed_zero["total_quantity"] == 0
        assert routed_zero["legs"] == []

        plan_neg = {"symbol": "NVDA", "quantity": -50, "target_price": 100.0}
        routed_neg = sor.route_order(plan_neg, version=12)
        assert routed_neg["total_quantity"] == 0

    def test_peg_limit_price_crossed_and_zero_spread(self):
        """Verify dual calculate_peg_limit_price handles degenerate spread and prices."""
        tp = 100.0
        # Zero spread fallback
        px_oms_zero_spr = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=tp, spread=0.0, hawkes_intensity=0.80, version=12
        )
        px_ac_zero_spr = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=tp, spread=0.0, hawkes_intensity=0.80, version=12
        )
        assert math.isfinite(px_oms_zero_spr)
        assert np.isclose(px_oms_zero_spr, px_ac_zero_spr, atol=1e-6)

        # None spread fallback
        px_oms_none_spr = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=tp, spread=None, hawkes_intensity=0.80, version=12
        )
        px_ac_none_spr = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=tp, spread=None, hawkes_intensity=0.80, version=12
        )
        assert np.isclose(px_oms_none_spr, px_ac_none_spr, atol=1e-6)

    def test_peg_limit_price_clipping_bounds(self):
        """Verify peg price never escapes [min(bid, ask), max(bid, ask)] even under massive h."""
        tp = 100.0
        spr = 0.10
        bid = 99.95
        ask = 100.05

        # Massive h = 1000.0
        px_oms_massive_buy = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", hawkes_intensity=1000.0, version=12
        )
        assert px_oms_massive_buy >= bid
        assert px_oms_massive_buy <= ask
        assert np.isclose(px_oms_massive_buy, bid, atol=1e-6)

        px_oms_massive_sell = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
            action="SELL", hawkes_intensity=1000.0, version=12
        )
        assert px_oms_massive_sell >= bid
        assert px_oms_massive_sell <= ask
        assert np.isclose(px_oms_massive_sell, ask, atol=1e-6)
