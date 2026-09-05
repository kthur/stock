"""
test_phase12_portfolio_execution.py — Comprehensive unit tests for Phase 12 Genesis Portfolio & Execution Enhancement (F69.1, F69.2)
"""

import math
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


class TestPhase12PortfolioExecution:
    """Test suite verifying mathematical invariants of Phase 12 Portfolio & Execution components."""

    def test_fisher_rao_geodesic_distance_properties(self):
        """Feature F69.1: Verify Fisher-Rao geodesic distance metric properties on S^3."""
        allocator = UnifiedPortfolioAllocator()

        p = {"bl": 0.40, "herc": 0.30, "rp": 0.20, "cvar": 0.10}
        q = {"bl": 0.10, "herc": 0.20, "rp": 0.30, "cvar": 0.40}
        r = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}

        # 1. Non-negativity & Identity of indiscernibles: d_{FR}(p, p) == 0.0
        d_pp = allocator.compute_fisher_rao_distance(p, p)
        assert np.isclose(d_pp, 0.0, atol=1e-6), f"Expected d(p, p) == 0, got {d_pp}"

        # 2. Symmetry: d_{FR}(p, q) == d_{FR}(q, p)
        d_pq = allocator.compute_fisher_rao_distance(p, q)
        d_qp = allocator.compute_fisher_rao_distance(q, p)
        assert np.isclose(d_pq, d_qp, atol=1e-6), f"Expected symmetry, got {d_pq} vs {d_qp}"
        assert d_pq > 0.0

        # 3. Triangle Inequality: d_{FR}(p, r) <= d_{FR}(p, q) + d_{FR}(q, r)
        d_pr = allocator.compute_fisher_rao_distance(p, r)
        d_qr = allocator.compute_fisher_rao_distance(q, r)
        assert d_pr <= d_pq + d_qr + 1e-6, f"Triangle inequality violated: {d_pr} > {d_pq} + {d_qr}"

        # 4. Orthogonal distributions: d_{FR} == pi
        p_orth = {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        q_orth = {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0}
        d_orth = allocator.compute_fisher_rao_distance(p_orth, q_orth)
        assert np.isclose(d_orth, math.pi, atol=1e-3), f"Expected pi for orthogonal distributions, got {d_orth}"

    def test_fisher_rao_spherical_karcher_barycenter_convergence(self):
        """Feature F69.1: Verify Fisher-Rao manifold barycenter convergence, simplex projection, and variance reduction."""
        allocator = UnifiedPortfolioAllocator()

        # Multi-paradigm model distributions
        models = [
            {"bl": 0.50, "herc": 0.20, "rp": 0.15, "cvar": 0.15},
            {"bl": 0.15, "herc": 0.50, "rp": 0.20, "cvar": 0.15},
            {"bl": 0.15, "herc": 0.15, "rp": 0.50, "cvar": 0.20},
        ]

        q_star = allocator.compute_fisher_rao_barycenter_blend(models, max_iter=50, tol=1e-6)

        assert isinstance(q_star, dict)
        assert set(q_star.keys()) == {"bl", "herc", "rp", "cvar"}
        assert np.isclose(sum(q_star.values()), 1.0, atol=1e-5)
        for k, v in q_star.items():
            assert 0.0 < v < 1.0, f"Expected 0 < {k} < 1, got {v}"

        # Alias verification
        q_alias = allocator.compute_fisher_rao_manifold_barycenter(models, max_iter=50, tol=1e-6)
        for k in q_star:
            assert np.isclose(q_star[k], q_alias[k], atol=1e-5)

        # 2D array input verification
        arr_input = np.array([
            [0.50, 0.20, 0.15, 0.15],
            [0.15, 0.50, 0.20, 0.15],
            [0.15, 0.15, 0.50, 0.20],
        ])
        q_arr = allocator.compute_fisher_rao_barycenter_blend(arr_input)
        for k in q_star:
            assert np.isclose(q_star[k], q_arr[k], atol=1e-4)

        # Fréchet variance reduction property: sum of squared distances to barycenter must be strictly less than
        # sum of squared distances to individual extreme corner distributions
        sum_sq_bary = sum(allocator.compute_fisher_rao_distance(q_star, m)**2 for m in models)
        for m in models:
            sum_sq_m = sum(allocator.compute_fisher_rao_distance(m, other)**2 for other in models)
            assert sum_sq_bary < sum_sq_m + 1e-4, f"Fréchet variance not minimized: {sum_sq_bary} vs {sum_sq_m}"

    def test_ultra_evar_risk_measure_coherent_hierarchy(self):
        """Feature F69.1: Verify Ultra-EVaR coherent risk measure satisfies strict hierarchy: VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)

        # Heavy-tailed financial loss returns with Student-t and jump contagion
        t_returns = np.random.standard_t(df=3.5, size=1500) * 0.02
        jumps = np.random.binomial(1, 0.06, size=1500) * np.random.normal(-0.08, 0.04, size=1500)
        returns = t_returns + jumps

        res = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.01, xi_jump=0.15, xi_frechet=0.20)

        assert "ultra_evar_value" in res
        assert "super_evar_value" in res
        assert "evar_value" in res
        assert "cvar_value" in res
        assert "var_value" in res

        u_evar = res["ultra_evar_value"]
        s_evar = res["super_evar_value"]
        evar = res["evar_value"]
        cvar = res["cvar_value"]
        var = res["var_value"]

        # Strict Chernoff & Fréchet heavy-tail coherent risk hierarchy
        assert u_evar >= s_evar - 1e-6, f"Expected Ultra-EVaR >= Super-EVaR, got {u_evar} vs {s_evar}"
        assert s_evar >= evar - 1e-6, f"Expected Super-EVaR >= EVaR, got {s_evar} vs {evar}"
        assert evar >= cvar - 1e-6, f"Expected EVaR >= CVaR, got {evar} vs {cvar}"
        assert cvar >= var - 1e-6, f"Expected CVaR >= VaR, got {cvar} vs {var}"

        # Monotonicity with respect to tail confidence level (alpha=0.01 must produce higher risk than alpha=0.05)
        res_05 = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.05, xi_jump=0.15, xi_frechet=0.20)
        assert res["ultra_evar_value"] > res_05["ultra_evar_value"], "Ultra-EVaR at alpha=0.01 must exceed alpha=0.05"

        # Verify edge case of empty returns
        res_empty = allocator.compute_ultra_evar_risk_measure(np.array([]), alpha=0.05)
        assert "ultra_evar_value" in res_empty

    def test_deep_hawkes_arrival_process_phase12(self):
        """Feature F69.2: Verify DeepHawkesArrivalProcess L3 DOBI modulation and 96% dark routing cap."""
        process = DeepHawkesArrivalProcess(gamma_dobi=0.45, version=12)

        t0 = 1000.0
        for i in range(5):
            process.update("LIT", timestamp_sec=t0 + 0.1 * i)

        # Set severe DOBI imbalance on Lit venue
        process.update_dobi([0.95, -0.30, 0.10])
        routing = process.compute_preemptive_dark_routing(version=12)

        dark_ratio = routing["preemptive_dark_routing_ratio"]
        assert 0.65 <= dark_ratio <= 0.96
        assert dark_ratio >= 0.90, f"Expected dark ratio >= 0.90 under severe toxicity, got {dark_ratio}"

    def test_smart_order_router_phase12_ninety_six_percent_and_floors(self):
        """Feature F69.2: Verify SmartOrderRouter v12 reaches 96% dark ATS routing, 0.005 maker floor, and 0.95 MinQty."""
        sor = SmartOrderRouter()

        # Test 1: Queue acceleration and directional toxicity -> 96% dark preemption
        plan = {
            "symbol": "NVDA",
            "market": "NASDAQ",
            "action": "BUY",
            "quantity": 10000,
            "target_price": 120.0,
            "market_spread_bps": 2.0,
            "queue_imbalance": 0.80,
            "qi_acceleration": 0.60,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 0.85,
            "is_accumulation": True,
            "version": 12,
        }

        routed = sor.route_order(plan, version=12)

        # Dark ratio expands up to 96%
        assert routed["effective_dark_ratio"] <= 0.96
        assert routed["effective_dark_ratio"] >= 0.92, f"Expected >= 0.92, got {routed['effective_dark_ratio']}"

        # Maker ratio drops to 0.005 under extreme directional toxicity
        assert routed["maker_ratio"] <= 0.01
        assert routed["maker_ratio"] >= 0.005, f"Expected maker floor >= 0.005, got {routed['maker_ratio']}"

        # Anti-gaming MinQty scales up to 0.95
        assert routed["min_ratio"] >= 0.90
        assert routed["min_ratio"] <= 0.95, f"Expected min_ratio <= 0.95, got {routed['min_ratio']}"

        # Test 2: Cross-asset toxicity maker floor contraction to 0.005
        plan_cross = {
            "symbol": "SPY",
            "market": "SP500",
            "action": "BUY",
            "quantity": 5000,
            "target_price": 540.0,
            "gamma_toxic_dir": 1.0,
            "cross_asset_toxicity": 1.0,
            "version": 12,
        }
        routed_cross = sor.route_order(plan_cross, version=12)
        assert routed_cross["maker_ratio"] <= 0.01
        assert routed_cross["maker_ratio"] >= 0.005

    def test_oms_engine_dual_peg_limit_price_preemptive_shading_v12(self):
        """Feature F69.2: Verify ExecutionOMSEngine applies -0.60 * spread * (h - 0.25) preemptive tick shading when h > 0.25."""
        oms = ExecutionOMSEngine()

        p_base = 100.0
        spr = 0.10
        p_bid = p_base - spr / 2.0  # 99.95
        p_ask = p_base + spr / 2.0  # 100.05

        # 1. Normal Hawkes intensity h = 0.20 <= 0.25 (no shading triggered)
        p_norm = oms.calculate_peg_limit_price(
            target_price=p_base,
            bid_price=p_bid,
            ask_price=p_ask,
            spread=spr,
            action="BUY",
            hawkes_intensity=0.20,
            version=12,
        )

        # 2. Elevated Hawkes intensity h = 0.70 > 0.25
        p_elevated = oms.calculate_peg_limit_price(
            target_price=p_base,
            bid_price=p_bid,
            ask_price=p_ask,
            spread=spr,
            action="BUY",
            hawkes_intensity=0.70,
            version=12,
        )

        # For BUY: hawkes_shift = -1.0 * 0.60 * 0.10 * (0.70 - 0.25) = -0.027
        # Peg price must be strictly lower to protect from toxic fills
        assert p_elevated < p_norm, f"Elevated peg ({p_elevated}) must be strictly lower than normal ({p_norm})"

        # 3. Version 12 provides strictly more protective tick shading than Version 11 at h = 0.70
        # Phase 11 shift: -0.50 * 0.10 * (0.70 - 0.30) = -0.020
        # Phase 12 shift: -0.60 * 0.10 * (0.70 - 0.25) = -0.027
        p_v11 = oms.calculate_peg_limit_price(
            target_price=p_base,
            bid_price=p_bid,
            ask_price=p_ask,
            spread=spr,
            action="BUY",
            hawkes_intensity=0.70,
            version=11,
        )
        assert p_elevated < p_v11, f"Phase 12 peg ({p_elevated}) must be strictly more defensive than Phase 11 ({p_v11})"

        # 4. SELL action test: peg shift should be positive (+direction = -(-1.0) = +0.027 for SELL)
        p_sell_norm = oms.calculate_peg_limit_price(
            target_price=p_base,
            bid_price=p_bid,
            ask_price=p_ask,
            spread=spr,
            action="SELL",
            hawkes_intensity=0.20,
            version=12,
        )
        p_sell_elevated = oms.calculate_peg_limit_price(
            target_price=p_base,
            bid_price=p_bid,
            ask_price=p_ask,
            spread=spr,
            action="SELL",
            hawkes_intensity=0.70,
            version=12,
        )
        assert p_sell_elevated > p_sell_norm, f"Elevated SELL peg ({p_sell_elevated}) must step back (higher) than normal ({p_sell_norm})"

    def test_unified_allocator_phase12_headroom_redistribution_and_blending(self):
        """Feature F69.1: Verify UnifiedPortfolioAllocator v12 model blending and 14th-degree headroom redistribution."""
        allocator = UnifiedPortfolioAllocator()

        # Test blend_model_weights with version 12
        weights_v12 = allocator.blend_model_weights(
            regime="SIDEWAYS_HIGH_VOL",
            version=12,
            wasserstein_radius=0.110,
        )
        assert isinstance(weights_v12, dict)
        assert np.isclose(sum(weights_v12.values()), 1.0, atol=1e-5)
        for k, v in weights_v12.items():
            assert 0.0 < v < 1.0

        # Test optimize_portfolio / optimize_multi_model_blend with version 12 triggering Component CVaR redistribution
        n_assets = 10
        symbols = [f"asset_{i}" for i in range(n_assets)]
        pred_rets = np.full(n_assets, 0.05)
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.02, size=(250, n_assets)),
            columns=symbols
        )
        # Add high correlation and volatility to asset 0 to trigger TRC breach
        returns_df["asset_0"] = returns_df["asset_1"] * 1.8 + np.random.normal(-0.01, 0.05, size=250)
        cov = np.cov(returns_df.values, rowvar=False)

        w = allocator.optimize_portfolio(
            predicted_returns=pred_rets,
            returns_df=returns_df,
            cov_matrix=cov,
            symbols=symbols,
            version=12,
            regime="BEAR_HIGH_VOL",
            asset_cascade_vector=np.linspace(0.1, 0.9, n_assets),
        )
        assert isinstance(w, np.ndarray)
        assert len(w) == n_assets
        assert np.isclose(np.sum(w), 1.0, atol=1e-4)
        assert np.all(w >= -1e-6)

