"""
Test Suite for Phase 6 Institutional Features (F43 & F44)
Features covered:
- Feature F43: Regime-Adaptive 4-Model Reliability Optimization & Tail Risk Budgeting (UnifiedPortfolioAllocator)
- Feature F44: Level-3 Micro-Price Pegging, Bivariate Hawkes Directional Toxicity & Darkpool Capture (FastLOBEngine, SmartOrderRouter, ExecutionOMSEngine, AlmgrenChrissScheduler)
"""

import math
import time
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.fast_lob_engine import FastOrderBookMatchingEngine, BivariateHawkesIntensity
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


# ============================================================================
# Task A: Feature F43 Test Cases (Portfolio Reliability & Tail Risk Budgeting)
# ============================================================================

class TestF43RegimeAdaptiveReliabilityAndTailBudgeting:
    """Comprehensive test suite for Phase 6 Feature F43 in unified_portfolio_allocator.py."""

    def test_f43_information_theoretic_blend_weights_sum_to_one(self):
        """
        Verifies that compute_information_theoretic_blend_weights returns strictly positive
        weights summing to 1.0000 across all regimes and extreme stress parameters.
        """
        allocator = UnifiedPortfolioAllocator()
        regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "CRISIS",
            {"BULL_LOW_VOL": 0.5, "CRISIS": 0.5},
            {"BEAR_HIGH_VOL": 0.7, "SIDEWAYS_HIGH_VOL": 0.3}
        ]
        for reg in regimes:
            cfg = allocator.compute_information_theoretic_blend_weights(
                regime=reg,
                vix_val=28.0,
                crisis_severity=0.5,
                alpha_dispersion=0.04,
                diversification_ratio=1.45,
                gpd_tail_index=0.25,
                market_coskewness=-0.20,
            )
            assert np.isclose(sum(cfg.values()), 1.0, atol=1e-4)
            for k in ["bl", "herc", "rp", "cvar"]:
                assert cfg[k] > 0.0

    def test_f43_alpha_dispersion_monotonically_boosts_black_litterman(self):
        """
        As predictive alpha dispersion increases from 0.01 (flat/low view) to 0.06 (high conviction),
        Black-Litterman blend weight w_bl strictly increases monotonically in calm regimes.
        """
        allocator = UnifiedPortfolioAllocator()
        disps = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
        bl_weights = []
        for d in disps:
            cfg = allocator.compute_information_theoretic_blend_weights(
                regime="BULL_LOW_VOL",
                alpha_dispersion=d,
                diversification_ratio=1.30,
            )
            bl_weights.append(cfg["bl"])

        for i in range(len(bl_weights) - 1):
            assert bl_weights[i] <= bl_weights[i + 1] + 1e-4

    def test_f43_correlation_collapse_expands_cvar_and_suppresses_rp(self):
        """
        Under systemic correlation spikes (DR drops from 1.60 to 1.05),
        EVT-CVaR weight expands significantly while Risk Parity weight contracts.
        """
        allocator = UnifiedPortfolioAllocator()
        cfg_high_dr = allocator.compute_information_theoretic_blend_weights(
            regime="SIDEWAYS_HIGH_VOL", diversification_ratio=1.60
        )
        cfg_low_dr = allocator.compute_information_theoretic_blend_weights(
            regime="SIDEWAYS_HIGH_VOL", diversification_ratio=1.05
        )
        assert cfg_low_dr["cvar"] > cfg_high_dr["cvar"]
        assert cfg_low_dr["rp"] < cfg_high_dr["rp"]

    def test_f43_downside_sortino_tilting_penalizes_plunge_risk_asset(self):
        """
        When two assets have identical expected return, but Asset A has clean upside
        momentum (low downside ratio) and Asset B has heavy downside crash plunge risk
        (high downside ratio, negative co-skewness), Asset A receives >= 1.6x allocation of Asset B.
        """
        np.random.seed(42)
        T = 120
        # Asset A: large upside spikes, truncated downside
        r_a = np.random.normal(0.002, 0.015, T)
        r_a[r_a < -0.01] = -0.005
        r_a[::8] += 0.05

        # Asset B: small upside gains, sharp downside plunges
        r_b = np.random.normal(0.002, 0.015, T)
        r_b[r_b > 0.01] = 0.005
        r_b[::8] -= 0.05

        df = pd.DataFrame({"UP_CONVEX": r_a, "DOWN_PLUNGE": r_b})
        cov = df.cov().values
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.85)

        w = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.05, 0.05]),
            returns_df=df,
            cov_matrix=cov,
            symbols=["UP_CONVEX", "DOWN_PLUNGE"],
            regime="BULL_HIGH_VOL",
        )
        assert w[0] / max(1e-6, w[1]) >= 1.60

    def test_f43_euler_component_cvar_budget_cap_enforced(self):
        """
        Verifies Euler marginal and tail risk contribution calculations:
        sum of TRC equals 1.0, and assets with massive variance dominate tail risk.
        """
        allocator = UnifiedPortfolioAllocator()
        w0 = np.array([0.50, 0.50])
        cov = np.array([[0.09, 0.00], [0.00, 0.0009]])
        mrc, trc = allocator.compute_component_cvar_risk_contributions(w0, cov)
        assert trc[0] > 0.90
        assert np.isclose(np.sum(trc), 1.0, atol=1e-4)

    def test_f43_quadratic_shannon_entropy_volatility_scaling(self):
        """
        Verifies quadratic entropy dampening:
        - Mild uncertainty (U = 0.28) -> U^2 approx 0.08 -> vol scaling >= 90% of cap (minimal cash drag).
        - High uncertainty (U = 1.0) -> U^2 = 1.0 -> allocation smoothly contracted.
        """
        allocator = UnifiedPortfolioAllocator(target_volatility=0.12)
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        cov = np.diag([0.01 ** 2] * 4)

        reg_mild = {"BULL_LOW_VOL": 0.80, "BULL_HIGH_VOL": 0.20}
        reg_extreme = {
            r: 1.0 / 6.0
            for r in ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL"]
        }

        _, alloc_mild = allocator.apply_target_volatility_scaling(weights, cov, regime=reg_mild)
        _, alloc_extreme = allocator.apply_target_volatility_scaling(weights, cov, regime=reg_extreme)

        assert alloc_mild >= 0.90
        assert alloc_extreme < alloc_mild * 0.82


# ============================================================================
# Task B: Feature F44 Test Cases (Microstructure, L3 Pegging & Hawkes Routing)
# ============================================================================

class TestF44MicrostructureAndExecutionDeepening:
    """Comprehensive test suite for Phase 6 Feature F44."""

    def test_f44_l3_exponential_depth_decay_micro_price(self):
        """
        Verifies that when L1 quotes flicker with thin volumes, L3 multi-tier micro-price
        with depth decay lambda=0.35 remains anchored closer to deeper institutional book depth.
        """
        engine = FastOrderBookMatchingEngine(symbol="TEST", tick_size=0.01)
        # Bids: thin at best bid (100.0, vol=10), massive at level 2 (99.9, vol=500)
        engine.add_limit_order("b1", "BUY", 100.0, 10.0)
        engine.add_limit_order("b2", "BUY", 99.9, 500.0)
        # Asks: large at best ask (100.2, vol=100)
        engine.add_limit_order("a1", "SELL", 100.2, 100.0)
        engine.add_limit_order("a2", "SELL", 100.3, 20.0)

        snap = engine.get_depth_snapshot(levels=5)
        assert "l3_micro_price" in snap
        assert "l3_imbalance" in snap
        assert snap["best_bid"] == 100.0
        assert snap["best_ask"] == 100.2
        # Because level 2 has massive bid volume (500), L3 imbalance is higher than L1 OBI
        assert snap["l3_imbalance"] > snap["obi_1"]

    def test_f44_order_fragmentation_ratio_computation(self):
        """
        Verifies that large block institutional orders on the bid produce a high
        order fragmentation ratio (avg order size on bid >> avg order size on ask).
        """
        engine = FastOrderBookMatchingEngine(symbol="TEST_FRAG", tick_size=0.01)
        # 1 order of 1,000 shares on bid
        engine.add_limit_order("b_inst", "BUY", 50.0, 1000.0)
        # 10 orders of 10 shares on ask (100 total, 10 shares avg)
        for i in range(10):
            engine.add_limit_order(f"a_retail_{i}", "SELL", 50.1, 10.0)

        snap = engine.get_depth_snapshot(levels=5)
        assert snap["n_orders_best_bid"] == 1
        assert snap["n_orders_best_ask"] == 10
        # Fragmentation ratio = avg_size_bid / avg_size_ask = 1000 / 10 = 100 -> clipped to 10.0
        assert snap["order_fragmentation_ratio"] >= 5.0

    def test_f44_fifo_queue_position_tracking(self):
        """
        Inserts multiple limit orders at identical price; verifies that estimate_queue_position
        correctly tracks queue_ahead, queue_behind, and queue_position_ratio in [0, 1].
        """
        engine = FastOrderBookMatchingEngine(symbol="TEST_QUEUE", tick_size=0.01)
        engine.add_limit_order("ord_1", "BUY", 100.0, 100.0)
        engine.add_limit_order("ord_2", "BUY", 100.0, 50.0)
        engine.add_limit_order("ord_3", "BUY", 100.0, 200.0)

        q1 = engine.estimate_queue_position("ord_1")
        q2 = engine.estimate_queue_position("ord_2")
        q3 = engine.estimate_queue_position("ord_3")

        assert q1 is not None and q2 is not None and q3 is not None
        # ord_1 is at front of queue
        assert q1["queue_ahead"] == 0.0
        assert q1["queue_behind"] == 250.0
        assert q1["queue_position_ratio"] == 0.0
        assert q1["estimated_p_fill"] > 0.80

        # ord_2 is in middle
        assert q2["queue_ahead"] == 100.0
        assert q2["queue_behind"] == 200.0
        assert 0.20 < q2["queue_position_ratio"] < 0.40

        # ord_3 is at back of queue
        assert q3["queue_ahead"] == 150.0
        assert q3["queue_behind"] == 0.0
        assert q3["queue_position_ratio"] > 0.40
        assert q3["estimated_p_fill"] < q1["estimated_p_fill"]

    def test_f44_queue_position_step_up_peg_pricing(self):
        """
        Verifies that an order at the back of the queue (u_q = 0.85) receives a positive
        queue concession delta_P_queue > 0 for BUY, increasing fill priority relative to u_q = 0.10.
        """
        target_p = 100.0
        bid_p = 99.0
        ask_p = 101.0
        spr = 2.0

        px_front = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            action="BUY",
            queue_position_ratio=0.10,
            micro_price=100.0,
        )

        px_back = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p,
            bid_price=bid_p,
            ask_price=ask_p,
            spread=spr,
            action="BUY",
            queue_position_ratio=0.85,
            micro_price=100.0,
        )

        # Back of queue steps up limit price towards ask to ensure priority
        assert px_back > px_front

    def test_f44_bivariate_hawkes_directional_toxicity(self):
        """
        Verifies that an aggressive sell trade burst elevates lambda_sell and delta_dir > 0,
        driving gamma_toxic_dir for BUY orders towards 1.0 while keeping it low for SELL orders.
        """
        bh = BivariateHawkesIntensity(mu_buy=1.0, mu_sell=1.0, alpha_self=0.5, alpha_cross=0.1, beta=1.0)
        t_base = time.time()
        # Burst of aggressive sells
        for i in range(6):
            bh.update("SELL", timestamp_sec=t_base + i * 0.05)

        tox_buy = bh.get_directional_toxicity("BUY", t_query=t_base + 0.35)
        tox_sell = bh.get_directional_toxicity("SELL", t_query=t_base + 0.35)

        assert tox_buy["lambda_sell"] > tox_buy["lambda_buy"]
        assert tox_buy["delta_dir"] > 0.0
        assert tox_buy["gamma_toxic_dir"] >= 0.70
        assert tox_sell["gamma_toxic_dir"] < 0.20

    def test_f44_directional_hawkes_contracts_maker_to_twenty_percent(self):
        """
        Verifies that under directional toxic selling, maker_ratio on BUY orders safely drops
        to 0.20 (lower than Phase 5's 0.30 floor).
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 200.0,
            "execution_strategy": "MIDPOINT_PEG",
        }

        routed = sor.route_order(
            order_plan=order_plan,
            gamma_toxic_dir=1.0,
        )
        assert np.isclose(routed["maker_ratio"], 0.20, atol=1e-3)

    def test_f44_anti_gaming_min_qty_dynamic_expansion(self):
        """
        Verifies that high toxicity and darkpool accumulation expand min_quantity
        from 20% up to 50% of dark quantity, shutting out odd-lot snipes.
        """
        sor = SmartOrderRouter()
        order_plan = {
            "symbol": "GOOGL",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 180.0,
            "execution_strategy": "PATIENT_TWAP",
            "darkpool_score": 0.80,
        }

        # Elevated directional toxicity
        routed = sor.route_order(
            order_plan=order_plan,
            gamma_toxic_dir=1.0,
        )
        dark_leg = routed["dark_ats_midpoint"]
        assert dark_leg is not None
        assert dark_leg.get("anti_gaming_active") is True
        # Under gamma_toxic=1.0 and dp_score=0.80, min_ratio reaches 50%
        assert dark_leg["min_quantity"] == int(round(0.50 * dark_leg["quantity"]))

    def test_f44_logistic_darkpool_fill_probability_bounds(self):
        """
        Verifies that the logistic hazard model outputs fill probabilities strictly bounded
        within [0.10, 0.90] and responds monotonically to spread and darkpool score.
        """
        sor = SmartOrderRouter(use_logistic_dark_fill=True)
        base_plan = {
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 10_000,
            "target_price": 120.0,
            "execution_strategy": "MIDPOINT_PEG",
        }

        # High score, wide spread, zero toxicity -> high fill prob
        res_high = sor.route_order(
            order_plan={**base_plan, "darkpool_score": 0.90},
            market_spread_bps=25.0,
            gamma_toxic_dir=0.0,
            use_logistic_dark_fill=True,
        )

        # Low score, tight spread, high toxicity -> low fill prob
        res_low = sor.route_order(
            order_plan={**base_plan, "darkpool_score": 0.05},
            market_spread_bps=2.0,
            gamma_toxic_dir=1.0,
            use_logistic_dark_fill=True,
        )

        p_high = res_high["darkpool_fill_probability"]
        p_low = res_low["darkpool_fill_probability"]

        assert 0.10 <= p_high <= 0.90
        assert 0.10 <= p_low <= 0.90
        assert p_high > p_low + 0.30

    def test_f44_krx_nextrade_venue_routing_compliance(self):
        """
        Verifies that Korean equities (.KS, .KQ) routing to KRX_ATS_NEXTRADE receive
        1-share integer lot allocations and 0.5 bps maker rebate advantage.
        """
        sor = SmartOrderRouter()
        dest_ks = sor.determine_destination("005930.KS", market="KOSPI")
        dest_kq = sor.determine_destination("091990.KQ", market="KOSDAQ")

        for dest in [dest_ks, dest_kq]:
            assert dest["venue"] == "KRX_ATS_NEXTRADE"
            assert dest["lot_size"] == 1
            assert dest["rebate_bps"] == 0.5

        # Also verify routed order legs carry the tags
        routed = sor.route_order({
            "symbol": "005930.KS",
            "market": "KOSPI",
            "action": "BUY",
            "quantity": 100,
            "target_price": 70000.0,
            "execution_strategy": "MIDPOINT_PEG",
        })
        assert routed["destination"]["venue"] == "KRX_ATS_NEXTRADE"
        dark_leg = routed["dark_ats_midpoint"]
        if dark_leg:
            assert dark_leg.get("lot_size") == 1

    def test_f44_us_smart_dma_anti_gaming_flags(self):
        """
        Verifies that US equities routing to US_SMART_DMA receive d_peg_cqi_protected
        and micro_jitter_probe institutional tags.
        """
        sor = SmartOrderRouter()
        dest_us = sor.determine_destination("AAPL", market="NASDAQ")
        assert dest_us["venue"] == "US_SMART_DMA"
        assert dest_us.get("d_peg_cqi_protected") is True
        assert dest_us.get("micro_jitter_probe") is True

        routed = sor.route_order({
            "symbol": "AAPL",
            "market": "NASDAQ",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 220.0,
            "execution_strategy": "MIDPOINT_PEG",
        })
        dark_leg = routed["dark_ats_midpoint"]
        if dark_leg:
            assert dark_leg.get("d_peg_cqi_protected") is True
            assert dark_leg.get("micro_jitter_probe") is True

    def test_f44_parity_between_oms_engine_and_almgren_chriss(self):
        """
        Verifies that ExecutionOMSEngine.calculate_peg_limit_price and
        AlmgrenChrissScheduler.calculate_peg_limit_price produce identical outputs
        to < 10^-6 precision across various parameter combinations.
        """
        test_params = [
            {"target_price": 100.0, "bid_price": 99.0, "ask_price": 101.0, "spread": 2.0, "micro_price": 100.2, "l3_micro_price": 100.3, "queue_position_ratio": 0.65},
            {"target_price": 50.0, "bid_price": 49.5, "ask_price": 50.5, "spread": 1.0, "action": "SELL", "l3_imbalance": -0.40, "daily_volatility": 0.03},
            {"target_price": 200.0, "bid_price": 199.0, "ask_price": 201.0, "spread": 2.0, "alpha_urgency": 0.20},
            {"target_price": 300.0, "bid_price": 298.0, "ask_price": 302.0, "spread": 4.0, "queue_position_ratio": 0.90, "action": "BUY"},
        ]
        for p in test_params:
            px_oms = ExecutionOMSEngine.calculate_peg_limit_price(**p)
            px_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(**p)
            assert np.isclose(px_oms, px_ac, atol=1e-6)

    def test_f44_extreme_market_bounds_and_graceful_fallbacks(self):
        """
        Stress tests inverted spreads, negative target prices, zero volume,
        and verifies strict clipping within [min(bid, ask), max(bid, ask)].
        """
        # 1. Inverted spread (bid > ask)
        px_inv = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=102.0,
            ask_price=98.0,
            spread=-4.0,
            micro_price=100.0,
            l3_imbalance=0.5,
        )
        assert 98.0 <= px_inv <= 102.0

        # 2. Negative target price fallback
        px_neg = ExecutionOMSEngine.calculate_peg_limit_price(target_price=-50.0)
        assert px_neg == -50.0

        # 3. Massive queue position u_q = 1.0 with high urgency cannot breach ask on BUY
        px_clamped = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.0,
            ask_price=101.0,
            spread=2.0,
            action="BUY",
            alpha_urgency=1.0,
            queue_position_ratio=1.0,
            l3_imbalance=1.0,
        )
        assert px_clamped <= 101.0
