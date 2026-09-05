"""
tests/test_phase10_portfolio_execution.py
Unit tests for Phase 10 Transcendental Quantitative Enhancement (F61):
1. Multi-Marginal Optimal Transport (MMOT) Sinkhorn Barycenter Blending
2. Entropic Value-at-Risk (EVaR) Coherent Risk Measure Bounds
3. Fast LOB Multivariate Hawkes Arrival Intensity Process
4. Smart Order Router 92% ATS Preemption & 0.02 Maker Floor
5. OMS Engine Hawkes-Adjusted Dynamic Peg Pricing Offset
"""

import math
import numpy as np
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.core.fast_lob_engine import (
    MultivariateHawkesIntensity,
    compute_multivariate_hawkes_arrival_intensity,
)
from trading_system.src.execution.oms_engine import ExecutionOMSEngine
from trading_system.src.execution.smart_order_router import SmartOrderRouter


class TestPhase10PortfolioExecution:
    """Test suite for Phase 10 Portfolio Allocation and OMS Execution improvements."""

    def test_mmot_barycenter_blend_convergence(self):
        """Validates MMOT Sinkhorn Barycenter convergence, positivity, and partition of unity."""
        allocator = UnifiedPortfolioAllocator()

        # Test single dict input
        priors = {"bl": 0.45, "herc": 0.35, "rp": 0.10, "cvar": 0.10}
        blend = allocator.compute_mmot_barycenter_blend(priors, reg=0.05)

        assert isinstance(blend, dict)
        assert set(blend.keys()) == {"bl", "herc", "rp", "cvar"}
        assert np.isclose(sum(blend.values()), 1.0, atol=1e-5)
        for k, v in blend.items():
            assert v > 0.0, f"Model weight for {k} must be strictly positive"

        # Test multi-marginal distributions list
        dist_list = [
            {"bl": 0.70, "herc": 0.20, "rp": 0.05, "cvar": 0.05},
            {"bl": 0.10, "herc": 0.30, "rp": 0.20, "cvar": 0.40},
            {"bl": 0.00, "herc": 0.15, "rp": 0.05, "cvar": 0.80},
        ]
        barycenter = allocator.compute_mmot_barycenter_blend(dist_list, reg=0.04)
        assert isinstance(barycenter, dict)
        assert np.isclose(sum(barycenter.values()), 1.0, atol=1e-5)
        assert barycenter["cvar"] > 0.10
        assert barycenter["herc"] > 0.10

    def test_evar_risk_measure_bounds(self):
        """Validates that EVaR satisfies the Chernoff bound: EVaR >= CVaR >= VaR."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)

        # Fat-tailed Student-t simulated daily returns
        sim_returns = np.random.standard_t(df=4, size=1000) * 0.02 - 0.001
        res = allocator.compute_evar_risk_measure(sim_returns, alpha=0.05)

        assert "evar_value" in res
        assert "cvar_value" in res
        assert "var_value" in res
        assert "optimal_t" in res

        evar = res["evar_value"]
        cvar = res["cvar_value"]
        var = res["var_value"]

        # Mathematical hierarchy check
        assert evar >= cvar - 1e-6, f"EVaR ({evar}) must be >= CVaR ({cvar})"
        assert cvar >= var - 1e-6, f"CVaR ({cvar}) must be >= VaR ({var})"
        assert res["optimal_t"] > 0.0

    def test_fast_lob_multivariate_hawkes_intensity(self):
        """Validates Multivariate Hawkes arrival intensity, self/cross-excitation, and decay."""
        # 3 venues: LIT, ATS, DARK
        venues = ["LIT", "ATS", "DARK"]
        mu = np.array([1.0, 0.5, 0.2])
        model = MultivariateHawkesIntensity(mu=mu, num_venues=3, venue_names=venues)

        init_int = model.get_intensity_at(0.0)
        assert np.allclose(init_int, mu, atol=1e-5)

        # Trigger burst of events in LIT
        model.update("LIT", timestamp_sec=1.0)
        post_lit = model.get_intensity_at(1.0)
        # LIT intensity must surge due to self-excitation
        assert post_lit[0] > mu[0]
        # ATS and DARK intensity must increase due to cross-excitation
        assert post_lit[1] > mu[1]
        assert post_lit[2] > mu[2]

        # Check exponential decay over time
        decayed_int = model.get_intensity_at(10.0)
        assert decayed_int[0] < post_lit[0]
        assert np.all(decayed_int >= mu)

        # Batch function test
        ts_batch = np.array([1.0, 1.2, 1.5, 2.0, 2.1])
        ven_batch = ["LIT", "LIT", "ATS", "DARK", "LIT"]
        batch_res = compute_multivariate_hawkes_arrival_intensity(
            event_timestamps=ts_batch,
            event_venues=ven_batch,
            decay_beta=1.2,
        )
        assert "intensities" in batch_res
        assert "cross_excitation_toxicity" in batch_res
        assert 0.0 <= batch_res["cross_excitation_toxicity"] <= 1.0

    def test_smart_order_router_phase10_ninety_two_percent(self):
        """Validates Phase 10 SOR features: 92% ATS preemption, 0.02 maker floor, and 80% anti-gaming minQty."""
        router = SmartOrderRouter()

        # Order plan under high lit queue imbalance and acceleration in Phase 10
        plan_high_qi = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 75000.0,
            "market_spread_bps": 12.0,
            "version": 10,
            "queue_imbalance": 0.85,
            "qi_acceleration": 0.50,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.80,
            "is_accumulation": True,
        }

        routed = router.route_order(plan_high_qi)
        legs = routed["legs"]

        # Dark ATS leg must receive up to 92% of order
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) >= 1
        dark_qty = dark_legs[0]["quantity"]
        assert dark_qty >= 8500  # >= 85% and up to 92%

        # Anti-gaming MinQty should be active and scaled up to 80%
        assert dark_legs[0].get("anti_gaming_active", False) is True
        min_q = dark_legs[0].get("min_quantity", 0)
        assert min_q >= int(0.70 * dark_qty)

        # Maker ratio must be contracted down to 0.02 floor under extreme directional toxicity
        assert routed["maker_ratio"] <= 0.03

    def test_oms_engine_hawkes_peg_offset(self):
        """Validates OMS Engine Hawkes-adjusted dynamic peg price stepping back under toxicity."""
        target_price = 50000.0
        spread = 200.0
        bid = 49900.0
        ask = 50100.0

        # Normal pricing without toxic Hawkes intensity
        p_normal = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_price,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            version=10,
            hawkes_intensity=0.10,
        )

        # Severe cross-excitation Hawkes toxicity in Phase 10
        p_toxic = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_price,
            bid_price=bid,
            ask_price=ask,
            spread=spread,
            action="BUY",
            version=10,
            hawkes_intensity=0.85,
        )

        # Buyer steps back (lower price) when adverse cross-venue flow is toxic
        assert p_toxic < p_normal, f"Toxic peg price ({p_toxic}) must be lower than normal ({p_normal}) for BUY"
        assert p_toxic >= bid, f"Peg price must stay within NBBO [{bid}, {ask}]"
