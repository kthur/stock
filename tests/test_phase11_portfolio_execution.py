"""
test_phase11_portfolio_execution.py — Unit tests for Phase 11 Singularity Portfolio & Execution Enhancement (F65.1, F65.2)
"""

import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.core.fast_lob_engine import (
    DeepHawkesArrivalProcess,
    compute_deep_order_book_imbalance_hawkes,
)
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine


class TestPhase11PortfolioExecution:
    """Test suite verifying mathematical invariants of Phase 11 Portfolio & Execution components."""

    def test_quantum_relative_entropy_barycenter_convergence(self):
        """Feature F65.1: Verify Quantum Relative Entropy (Umegaki) barycenter convergence and normalization."""
        allocator = UnifiedPortfolioAllocator()

        # Multi-model distributions
        models = [
            {"bl": 0.40, "herc": 0.20, "rp": 0.20, "cvar": 0.20},
            {"bl": 0.10, "herc": 0.50, "rp": 0.20, "cvar": 0.20},
            {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25},
        ]
        q_star = allocator.compute_quantum_relative_entropy_barycenter(models, max_iter=30)

        assert isinstance(q_star, dict)
        assert set(q_star.keys()) == {"bl", "herc", "rp", "cvar"}
        assert np.isclose(sum(q_star.values()), 1.0, atol=1e-5)
        for k, v in q_star.items():
            assert 0.0 < v < 1.0

    def test_super_evar_risk_measure_bounds(self):
        """Feature F65.1: Verify Super-EVaR coherent tail risk ceiling bounds: Super-EVaR >= EVaR >= CVaR >= VaR."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)

        # Generate heavy-tailed jump-diffusion returns
        normal_ret = np.random.normal(0.0005, 0.015, 1000)
        jumps = np.random.binomial(1, 0.05, 1000) * np.random.normal(-0.06, 0.03, 1000)
        returns = normal_ret + jumps

        res = allocator.compute_super_evar_risk_measure(returns, alpha=0.05, xi_jump=0.20)

        assert "super_evar_value" in res
        assert "evar_value" in res
        assert "cvar_value" in res
        assert "var_value" in res

        s_evar = res["super_evar_value"]
        evar = res["evar_value"]
        cvar = res["cvar_value"]
        var = res["var_value"]

        # Strict Chernoff coherent tail risk hierarchy
        assert s_evar >= evar - 1e-6, f"Expected Super-EVaR >= EVaR, got {s_evar} vs {evar}"
        assert evar >= cvar - 1e-6, f"Expected EVaR >= CVaR, got {evar} vs {cvar}"
        assert cvar >= var - 1e-6, f"Expected CVaR >= VaR, got {cvar} vs {var}"

    def test_deep_hawkes_arrival_process(self):
        """Feature F65.2: Verify DeepHawkesArrivalProcess L3 DOBI modulation and 95% dark routing."""
        process = DeepHawkesArrivalProcess(gamma_dobi=0.45)

        # Simulate events at LIT venue
        t0 = 1000.0
        for i in range(5):
            process.update("LIT", timestamp_sec=t0 + 0.1 * i)

        # Set severe DOBI imbalance on Lit venue
        process.update_dobi([0.85, -0.20, 0.10])
        deep_ints = process.get_deep_intensities(t_query_sec=t0 + 0.6)
        routing = process.compute_preemptive_dark_routing()

        assert "LIT" in deep_ints
        assert "ATS" in deep_ints
        assert "DARK" in deep_ints
        # Modulated lit intensity must exceed base intensity
        base_lit = process.get_intensity_at(t_query_sec=t0 + 0.6)[0]
        assert deep_ints["LIT"] > base_lit

        # Dark routing ratio should adapt up towards 0.95
        dark_ratio = routing["preemptive_dark_routing_ratio"]
        assert 0.65 <= dark_ratio <= 0.95
        assert dark_ratio >= 0.85, f"Expected high dark ratio under severe toxicity, got {dark_ratio}"

    def test_smart_order_router_phase11_ninety_five_percent(self):
        """Feature F65.2: Verify SmartOrderRouter v11 reaches 95% dark ATS allocation and 0.01 maker floor."""
        sor = SmartOrderRouter()
        plan = {
            "symbol": "AAPL",
            "market": "NASDAQ",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 180.0,
            "market_spread_bps": 2.0,
            "queue_imbalance": 0.70,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,  # Extreme directional toxicity
            "darkpool_score": 0.80,
            "is_accumulation": True,
            "version": 11,
        }

        routed = sor.route_order(plan, version=11)

        # In Phase 11 with severe queue acceleration and toxicity, dark ratio expands to 95%
        assert routed["effective_dark_ratio"] <= 0.95
        assert routed["effective_dark_ratio"] >= 0.90, f"Expected >= 0.90 dark ratio, got {routed['effective_dark_ratio']}"

        # Maker ratio drops to 0.01 under extreme directional toxicity
        assert routed["maker_ratio"] <= 0.02
        assert routed["maker_ratio"] >= 0.01

        # Anti-gaming min_ratio should reach up to 0.90
        assert routed["min_ratio"] >= 0.80

    def test_oms_engine_deep_hawkes_peg_offset(self):
        """Feature F65.2: Verify ExecutionOMSEngine v11 applies preemptive tick shading at h > 0.30."""
        oms = ExecutionOMSEngine()

        p_base = 100.0
        spr = 0.10
        p_bid = p_base - spr / 2.0
        p_ask = p_base + spr / 2.0

        # Normal hawkes below threshold 0.30
        p_norm = oms.calculate_peg_limit_price(
            target_price=p_base,
            bid_price=p_bid,
            ask_price=p_ask,
            spread=spr,
            action="BUY",
            hawkes_intensity=0.25,
            version=11
        )

        # Elevated hawkes intensity 0.70 (well above 0.30)
        p_elevated = oms.calculate_peg_limit_price(
            target_price=p_base,
            bid_price=p_bid,
            ask_price=p_ask,
            spread=spr,
            action="BUY",
            hawkes_intensity=0.70,
            version=11
        )

        # For BUY, toxic flow causes negative peg shift (stepping back to avoid toxic fill)
        assert p_elevated < p_norm, f"Elevated toxicity peg ({p_elevated}) should be strictly lower than normal ({p_norm})"
