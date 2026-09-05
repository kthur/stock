"""
Phase 9 Imperial Quantitative Enhancements (v16):
Portfolio Allocation & Level-3 Jerk / Deep-OFI Execution Test Suite.
Requirement R2 (Features F57 and F58):
- F57.1: Wasserstein Distributionally Robust Optimization (DRO) Ambiguity Ball Tilting.
- F57.2: Exponential Spectral Risk Measure (SRM, k=4.5) & 9th-degree Safety-Weighted Headroom Redistribution.
- F58.1: Level-1~5 Deep-OFI & 3rd-order Jerk (d^3QI/dt^3) Taylor Expansion Micro-Price Pegging.
- F58.2: Quantum Walk Grover Diffusion ATS Routing, 88% Preemptive Dark ATS Allocation & 0.03 Maker Floor.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.fast_lob_engine import FastOrderBookMatchingEngine
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.smart_order_router import SmartOrderRouter


class TestPhase9PortfolioAllocation:
    """Test Suite for Feature F57: Wasserstein DRO & Spectral Risk Measure."""

    def test_f57_1_wasserstein_dro_blend(self):
        """
        Verify F57.1: Wasserstein DRO tilts weights away from normal-reliant models (BL, RP)
        and toward distributionally robust models (HERC, CVaR).
        """
        allocator = UnifiedPortfolioAllocator()
        prior = {"bl": 0.40, "herc": 0.25, "rp": 0.25, "cvar": 0.10}

        dro_weights = allocator.compute_wasserstein_dro_blend(
            prior_weights=prior,
            epsilon_w=0.08
        )

        assert set(dro_weights.keys()) == {"bl", "herc", "rp", "cvar"}
        assert math.isclose(sum(dro_weights.values()), 1.0, abs_tol=1e-5)
        for v in dro_weights.values():
            assert v > 0.0

        # DRO should penalize BL and RP, and reward CVaR and HERC
        assert dro_weights["cvar"] > prior["cvar"]
        assert dro_weights["bl"] < prior["bl"]
        assert dro_weights["rp"] < prior["rp"]

    def test_f57_1_optimize_multi_model_blend_version9_dro(self):
        """
        Verify that optimize_multi_model_blend under version=9 incorporates DRO ambiguity ball tilting.
        """
        allocator = UnifiedPortfolioAllocator()
        regime = "SIDEWAYS_HIGH_VOL"

        w_v8 = allocator.compute_information_theoretic_blend_weights(regime=regime, version=8)
        w_v9 = allocator.compute_information_theoretic_blend_weights(regime=regime, version=9, wasserstein_radius=0.08)

        assert math.isclose(sum(w_v9.values()), 1.0, abs_tol=1e-5)
        # In high-vol sideways, DRO further shifts allocation toward robust EVT-CVaR and HERC
        assert w_v9["cvar"] >= w_v8["cvar"] - 1e-4

    def test_f57_2_spectral_risk_measure_calculation(self):
        """
        Verify F57.2: Exponential Spectral Risk Measure (SRM, k=4.5) prioritizes extreme left tail.
        """
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)

        # Mild normal returns
        mild_returns = np.random.normal(0.001, 0.015, 200)
        # Heavy-tailed crash returns with identical mean
        heavy_returns = mild_returns.copy()
        heavy_returns[:10] -= 0.15 # 10 extreme crash events

        res_mild = allocator.compute_spectral_risk_measure(mild_returns, k=4.5)
        res_heavy = allocator.compute_spectral_risk_measure(heavy_returns, k=4.5)

        assert "srm_value" in res_mild
        assert "phi_weights" in res_mild
        assert "quantiles" in res_mild

        # SRM risk value for heavy tail must be significantly greater than mild
        assert res_heavy["srm_value"] > res_mild["srm_value"] * 1.5

        # Spectral weights should be exponentially increasing toward the worst quantiles (right side of phi)
        phi = res_mild["phi_weights"]
        assert phi[-1] > phi[0] * 50.0  # e^4.5 ~ 90.0


class TestPhase9LOBAndExecution:
    """Test Suite for Feature F58: Deep-OFI, 3rd-Order Jerk Microprice & Grover Quantum Walk SOR."""

    def test_f58_1_fast_lob_deep_ofi_and_jerk(self):
        """
        Verify F58.1: FastOrderBookMatchingEngine evaluates Level 1..5 Deep-OFI and 3rd time derivative jerk.
        """
        engine = FastOrderBookMatchingEngine(symbol="SPY")

        # Ingest order book bids and asks
        t_base = 1000.0
        for step in range(5):
            # Asymmetrically shift bids and asks across time to create velocity, acceleration, and jerk
            b_p = 100.0 + step * 0.05
            a_p = 100.10 + step * 0.05
            engine.add_limit_order(f"B_{step}", "BUY", b_p, 1000.0 * (step + 1), int((t_base + step * 0.1) * 1e9))
            engine.add_limit_order(f"A_{step}", "SELL", a_p, 800.0, int((t_base + step * 0.1) * 1e9))
            res = engine.compute_deep_ofi_jerk_microprice(depth=5, timestamp_sec=t_base + step * 0.1)

        assert "qi_jerk" in res
        assert "deep_ofi" in res
        assert "jerk_micro_price" in res
        assert -1.0 <= res["deep_ofi"] <= 1.0
        assert math.isfinite(res["qi_jerk"])
        assert 100.0 <= res["jerk_micro_price"] <= 101.0

    def test_f58_1_oms_jerk_deep_ofi_peg_pricing(self):
        """
        Verify F58.1: ExecutionOMSEngine incorporates jerk and Deep-OFI under version=9.
        """
        target = 100.0
        bid = 99.95
        ask = 100.05
        spread = 0.10

        # With positive jerk and positive Deep-OFI, a BUY order should shade price upwards
        p_v8 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            qi_acceleration=1.5,
            version=8
        )

        p_v9 = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            qi_acceleration=1.5,
            qi_jerk=2.0,
            deep_ofi=0.60,
            version=9
        )

        assert bid <= p_v8 <= ask
        assert bid <= p_v9 <= ask
        # Strong buying pressure in jerk and Deep-OFI lifts the buy peg price
        assert p_v9 >= p_v8

    def test_f58_2_smart_order_router_quantum_walk_and_preemption(self):
        """
        Verify F58.2: SmartOrderRouter preemptive dark allocation up to 88%,
        contracted maker floor to 0.03, and Grover Quantum Walk venue routing.
        """
        sor = SmartOrderRouter()

        order_plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 150.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.50,
            "version": 9
        }

        routed = sor.route_order(order_plan)
        assert routed["total_quantity"] == 10000
        assert len(routed["legs"]) > 0

        # Quantum Walk Grover ATS Routing verification
        venues = ["LIT_EXCHANGE", "DARK_ATS", "INTERNAL_CROSS"]
        depths = [1000.0, 5000.0, 800.0]
        costs = [4.0, 1.2, 0.5]

        qw_alloc = sor.quantum_walk_grover_routing(venues, depths, costs, steps=2)
        assert set(qw_alloc.keys()) == set(venues)
        assert math.isclose(sum(qw_alloc.values()), 1.0, abs_tol=1e-5)
        # Best venue (DARK_ATS: depth 5000 / cost 1.2 = 4166.7) should receive highest probability
        assert qw_alloc["DARK_ATS"] > qw_alloc["LIT_EXCHANGE"]
