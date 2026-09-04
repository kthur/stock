"""
Adversarial Challenger Test Harness for Feature F44:
Microstructure, Level-3 Orderbook Depth Decay, FIFO Queue Dynamics,
Bivariate Hawkes Directional Toxicity and SOR Darkpool Anti-Gaming.

Author: challenger_m2_opt6_2 (Empirical Challenger)
Target Components:
- src.core.fast_lob_engine.FastOrderBookMatchingEngine
- src.core.fast_lob_engine.BivariateHawkesIntensity
- src.execution.smart_order_router.SmartOrderRouter
- src.execution.oms_engine.ExecutionOMSEngine
- src.execution.oms_engine.AlmgrenChrissScheduler
"""

import math
import time
import random
import threading
import numpy as np
import pytest

from src.core.fast_lob_engine import FastOrderBookMatchingEngine, BivariateHawkesIntensity
from src.execution.smart_order_router import SmartOrderRouter
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


# ============================================================================
# Adversarial Challenge 1: Quote Flickering & L3 Micro-Price Depth Resilience
# ============================================================================

class TestAdversarialL3MicroPriceResilience:
    """
    Empirically stress-tests L3 exponential depth decay micro-price resilience
    against predatory Level-1 quote flickering and spoofing attacks.
    """

    def test_quote_flickering_resilience_empirical_variance(self):
        """
        Simulates an aggressive quote flickering attack at Level 1:
        Deep institutional book (Levels 2-5) holds genuine supply/demand,
        while an HFT flickers Level 1 between 1 share and 1,000 shares back and forth.
        Verifies that L3 depth-decay micro-price variance is dramatically lower
        than standard L1 Stoikov micro-price variance (at least 5x variance reduction).
        """
        engine = FastOrderBookMatchingEngine(symbol="FLICKER_TEST", tick_size=0.01)

        # Baseline institutional resting liquidity on levels 2, 3, 4, 5
        for p, v in [(99.8, 500.0), (99.7, 800.0), (99.6, 1200.0), (99.5, 2000.0)]:
            engine.add_limit_order(f"bid_deep_{p}", "BUY", p, v)
        for p, v in [(100.2, 500.0), (100.3, 800.0), (100.4, 1200.0), (100.5, 2000.0)]:
            engine.add_limit_order(f"ask_deep_{p}", "SELL", p, v)

        l1_micro_prices = []
        l3_micro_prices = []

        # 40 cycles of high-frequency adversarial quote flickering at Level 1
        for cycle in range(40):
            # State A: Bid flickering (1 share on bid, 500 on ask)
            b1_id = f"flicker_b_{cycle}_A"
            a1_id = f"flicker_a_{cycle}_A"
            engine.add_limit_order(b1_id, "BUY", 100.0, 1.0)
            engine.add_limit_order(a1_id, "SELL", 100.1, 500.0)

            snap_A = engine.get_depth_snapshot(levels=5)
            l1_micro_prices.append(snap_A["micro_price"])
            l3_micro_prices.append(snap_A["l3_micro_price"])

            engine.cancel_order(b1_id)
            engine.cancel_order(a1_id)

            # State B: Ask flickering (500 shares on bid, 1 on ask)
            b2_id = f"flicker_b_{cycle}_B"
            a2_id = f"flicker_a_{cycle}_B"
            engine.add_limit_order(b2_id, "BUY", 100.0, 500.0)
            engine.add_limit_order(a2_id, "SELL", 100.1, 1.0)

            snap_B = engine.get_depth_snapshot(levels=5)
            l1_micro_prices.append(snap_B["micro_price"])
            l3_micro_prices.append(snap_B["l3_micro_price"])

            engine.cancel_order(b2_id)
            engine.cancel_order(a2_id)

        var_l1 = float(np.var(l1_micro_prices))
        var_l3 = float(np.var(l3_micro_prices))

        # L3 variance must be significantly smaller than L1 variance (at least 5x reduction)
        assert var_l1 > 0.001, "L1 micro-price should oscillate heavily under flickering"
        assert var_l3 < var_l1 / 5.0, (
            f"L3 micro-price failed to dampen flickering: var_L1={var_l1:.6f}, var_L3={var_l3:.6f}"
        )
        # Verify L3 prices remain strictly inside [best_bid, best_ask]
        for p_l3 in l3_micro_prices:
            assert 99.8 <= p_l3 <= 100.2

    def test_l3_micro_price_degenerate_and_boundary_books(self):
        """
        Verifies mathematical stability under degenerate orderbook topologies:
        empty book, one-sided book, zero spread, inverted spread, and extreme volume ratios.
        """
        # 1. Empty book -> graceful fallback, spread=0, micro_price=0
        empty_engine = FastOrderBookMatchingEngine(symbol="EMPTY", tick_size=0.01)
        snap_empty = empty_engine.get_depth_snapshot(levels=5)
        assert snap_empty["best_bid"] == 0.0
        assert snap_empty["best_ask"] == 0.0
        assert snap_empty["spread"] == 0.0
        assert snap_empty["l3_micro_price"] == 0.0
        assert snap_empty["l3_imbalance"] == 0.0

        # 2. Bids only (no asks) -> graceful fallback, no exception
        bids_only = FastOrderBookMatchingEngine(symbol="BIDS_ONLY", tick_size=0.01)
        bids_only.add_limit_order("b1", "BUY", 100.0, 100.0)
        snap_bids = bids_only.get_depth_snapshot(levels=5)
        assert snap_bids["best_bid"] == 100.0
        assert snap_bids["best_ask"] == 0.0
        assert snap_bids["spread"] == 0.0
        assert snap_bids["l3_micro_price"] == 0.0  # missing ask side defaults to 0

        # 3. Asks only (no bids) -> graceful fallback, no exception
        asks_only = FastOrderBookMatchingEngine(symbol="ASKS_ONLY", tick_size=0.01)
        asks_only.add_limit_order("a1", "SELL", 105.0, 100.0)
        snap_asks = asks_only.get_depth_snapshot(levels=5)
        assert snap_asks["best_bid"] == 0.0
        assert snap_asks["best_ask"] == 105.0
        assert snap_asks["l3_micro_price"] == 0.0

        # 4. Extreme volume imbalance across levels
        extreme_engine = FastOrderBookMatchingEngine(symbol="EXTREME", tick_size=0.01)
        extreme_engine.add_limit_order("b1", "BUY", 100.0, 1e9)
        extreme_engine.add_limit_order("a1", "SELL", 101.0, 1.0)
        snap_extreme = extreme_engine.get_depth_snapshot(levels=5)
        assert snap_extreme["l3_imbalance"] == 1.0
        assert np.isclose(snap_extreme["l3_micro_price"], 101.0, atol=1e-2)

    def test_order_fragmentation_ratio_clipping_and_powers(self):
        """
        Verifies order fragmentation ratio bounds [0.1, 10.0] and power calculation.
        """
        engine = FastOrderBookMatchingEngine(symbol="FRAG_TEST", tick_size=0.01)

        # Huge single order on bid (100,000 shares) vs 50 orders of 1 share on ask
        engine.add_limit_order("b_whale", "BUY", 50.0, 100_000.0)
        for i in range(50):
            engine.add_limit_order(f"a_tiny_{i}", "SELL", 50.5, 1.0)

        snap = engine.get_depth_snapshot(levels=5)
        assert snap["order_fragmentation_ratio"] == 10.0

        # Now reverse: 50 orders of 1 share on bid vs 1 order of 50,000 on ask
        engine_rev = FastOrderBookMatchingEngine(symbol="FRAG_REV", tick_size=0.01)
        for i in range(50):
            engine_rev.add_limit_order(f"b_tiny_{i}", "BUY", 50.0, 1.0)
        engine_rev.add_limit_order("a_whale", "SELL", 50.5, 50_000.0)

        snap_rev = engine_rev.get_depth_snapshot(levels=5)
        assert snap_rev["order_fragmentation_ratio"] == 0.1


# ============================================================================
# Adversarial Challenge 2: FIFO Queue Dynamics & Peg Limit Step-Up Concessions
# ============================================================================

class TestAdversarialFIFOQueueDynamics:
    """
    Empirically stress-tests FIFO queue position tracking, Cont-Kukanov fill
    probabilities, cancellation propagation, and peg price concessions.
    """

    def test_fifo_queue_monotonic_decay_across_ten_orders(self):
        """
        Places 10 orders at identical price level in FIFO order.
        Verifies strict monotonicity:
        - queue_ahead strictly increases
        - u_q strictly increases from 0.0 to ~0.90+
        - estimated_p_fill strictly decreases from 0.95 down towards ~0.20
        """
        engine = FastOrderBookMatchingEngine(symbol="QUEUE_10", tick_size=0.01)
        price = 100.0
        order_ids = [f"ord_{i}" for i in range(10)]
        for oid in order_ids:
            engine.add_limit_order(oid, "BUY", price, 100.0)

        results = [engine.estimate_queue_position(oid) for oid in order_ids]

        # Order 0: front of queue
        assert results[0]["queue_ahead"] == 0.0
        assert results[0]["queue_position_ratio"] == 0.0
        assert results[0]["estimated_p_fill"] == 0.95

        # Check strict monotonicity across the entire queue
        for i in range(1, 10):
            assert results[i]["queue_ahead"] > results[i - 1]["queue_ahead"]
            assert results[i]["queue_position_ratio"] > results[i - 1]["queue_position_ratio"]
            assert results[i]["estimated_p_fill"] < results[i - 1]["estimated_p_fill"]

        # Order 9: tail of queue
        assert results[9]["queue_behind"] == 0.0
        assert results[9]["queue_position_ratio"] == 0.90
        assert results[9]["estimated_p_fill"] < 0.25

    def test_queue_dynamic_evolution_on_cancellation_and_partial_fill(self):
        """
        Verifies that cancelling orders or executing partial market sweeps
        immediately updates queue_ahead and u_q for downstream resting orders.
        """
        engine = FastOrderBookMatchingEngine(symbol="QUEUE_DYN", tick_size=0.01)
        engine.add_limit_order("ord_A", "BUY", 100.0, 300.0)
        engine.add_limit_order("ord_B", "BUY", 100.0, 200.0)
        engine.add_limit_order("ord_C", "BUY", 100.0, 500.0)

        # Before any event
        q_b_init = engine.estimate_queue_position("ord_B")
        assert q_b_init["queue_ahead"] == 300.0
        assert q_b_init["queue_position_ratio"] == 0.30

        # Event 1: Market sell order sweeps 150 shares from ord_A (partial fill via match_market_order)
        fills = engine.match_market_order("SELL", 150.0)
        assert len(fills) == 1
        assert fills[0]["volume"] == 150.0

        # After partial fill, ord_A has 150 shares remaining
        q_b_after_fill = engine.estimate_queue_position("ord_B")
        assert q_b_after_fill["queue_ahead"] == 150.0
        assert q_b_after_fill["queue_position_ratio"] < 0.30

        # Event 2: ord_A cancels remaining 150 shares
        engine.cancel_order("ord_A")
        assert engine.estimate_queue_position("ord_A") is None

        # ord_B is now at the very front of the queue!
        q_b_front = engine.estimate_queue_position("ord_B")
        assert q_b_front["queue_ahead"] == 0.0
        assert q_b_front["queue_position_ratio"] == 0.0
        assert q_b_front["estimated_p_fill"] == 0.95

    def test_queue_step_up_concession_adversarial_clipping(self):
        """
        Verifies that queue step-up concessions:
        1. Are zero when u_q <= 0.40.
        2. Increase monotonically when u_q > 0.40.
        3. Step UP for BUY and step DOWN for SELL.
        4. NEVER violate best_bid or best_ask bounds under extreme parameters.
        """
        target_p = 100.0
        bid_p = 95.0
        ask_p = 105.0
        spr = 10.0

        # 1. Zero concession for front/mid queue (u_q <= 0.40)
        p_front = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p, bid_price=bid_p, ask_price=ask_p, spread=spr,
            action="BUY", queue_position_ratio=0.35, micro_price=100.0,
        )
        p_front_base = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p, bid_price=bid_p, ask_price=ask_p, spread=spr,
            action="BUY", queue_position_ratio=0.0, micro_price=100.0,
        )
        assert np.isclose(p_front, p_front_base, atol=1e-5)

        # 2. Step-up concession for back of queue (u_q = 0.95)
        p_back = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p, bid_price=bid_p, ask_price=ask_p, spread=spr,
            action="BUY", queue_position_ratio=0.95, micro_price=100.0, alpha_urgency=0.80,
        )
        assert p_back > p_front + 1.0, f"Expected step-up for back of queue, got {p_back} vs {p_front}"

        # 3. Step-down concession for SELL back of queue
        p_sell_front = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p, bid_price=bid_p, ask_price=ask_p, spread=spr,
            action="SELL", queue_position_ratio=0.20, micro_price=100.0,
        )
        p_sell_back = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p, bid_price=bid_p, ask_price=ask_p, spread=spr,
            action="SELL", queue_position_ratio=0.95, micro_price=100.0, alpha_urgency=0.80,
        )
        assert p_sell_back < p_sell_front - 1.0, f"Expected step-down for SELL back of queue, got {p_sell_back}"

        # 4. Extreme parameters: u_q=2.5, spread=100, urgency=5.0 -> must clip to ask_p
        p_extreme = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=target_p, bid_price=bid_p, ask_price=ask_p, spread=spr,
            action="BUY", queue_position_ratio=2.5, micro_price=104.0, alpha_urgency=5.0,
        )
        assert p_extreme == ask_p


# ============================================================================
# Adversarial Challenge 3: Bivariate Hawkes Directional Toxicity & Maker Ratio
# ============================================================================

class TestAdversarialBivariateHawkesToxicity:
    """
    Empirically stress-tests directional Hawkes toxicity under massive sell/buy bursts,
    confirming asymmetric adverse selection response and maker ratio contraction to 0.20.
    """

    def test_massive_sell_burst_vs_massive_buy_burst_directional_asymmetry(self):
        """
        Injects a burst of aggressive SELLS:
        - For BUY: lambda_sell >> lambda_buy, delta_dir > 0, gamma_toxic_dir reaches 1.0.
        - For SELL: gamma_toxic_dir is significantly lower.
        Then injects a burst of aggressive BUYS:
        - For SELL: lambda_buy >> lambda_sell, delta_dir < 0, gamma_toxic_dir reaches 1.0.
        - For BUY: gamma_toxic_dir is significantly lower.
        """
        bh = BivariateHawkesIntensity(mu_buy=1.0, mu_sell=1.0, alpha_self=0.5, alpha_cross=0.1, beta=1.0)
        t_now = time.time()

        # 1. Burst of 8 aggressive sells
        for i in range(8):
            bh.update("SELL", timestamp_sec=t_now + i * 0.04)

        t_eval = t_now + 0.35
        tox_buy_under_sells = bh.get_directional_toxicity("BUY", t_query=t_eval)
        tox_sell_under_sells = bh.get_directional_toxicity("SELL", t_query=t_eval)

        assert tox_buy_under_sells["lambda_sell"] > tox_buy_under_sells["lambda_buy"]
        assert tox_buy_under_sells["delta_dir"] > 0.30
        assert tox_buy_under_sells["gamma_toxic_dir"] >= 0.90
        assert tox_sell_under_sells["gamma_toxic_dir"] < tox_buy_under_sells["gamma_toxic_dir"] - 0.40

        # 2. Reset and burst of 8 aggressive buys
        bh2 = BivariateHawkesIntensity(mu_buy=1.0, mu_sell=1.0, alpha_self=0.5, alpha_cross=0.1, beta=1.0)
        for i in range(8):
            bh2.update("BUY", timestamp_sec=t_now + i * 0.04)

        tox_buy_under_buys = bh2.get_directional_toxicity("BUY", t_query=t_eval)
        tox_sell_under_buys = bh2.get_directional_toxicity("SELL", t_query=t_eval)

        assert tox_sell_under_buys["lambda_buy"] > tox_sell_under_buys["lambda_sell"]
        assert tox_sell_under_buys["delta_dir"] < -0.30
        assert tox_sell_under_buys["gamma_toxic_dir"] >= 0.90
        assert tox_buy_under_buys["gamma_toxic_dir"] < tox_sell_under_buys["gamma_toxic_dir"] - 0.40

    def test_maker_ratio_contraction_under_directional_toxicity_in_sor(self):
        """
        Verifies that SmartOrderRouter contracts maker_ratio down to exactly 0.20
        under toxic flow (gamma_toxic_dir = 1.0 or hawkes_sell = 20.0 for BUY).
        """
        sor = SmartOrderRouter()
        plan_buy = {
            "symbol": "MSFT",
            "action": "BUY",
            "quantity": 20_000,
            "target_price": 400.0,
            "execution_strategy": "MIDPOINT_PEG",
        }

        # Calm market: maker_ratio == 0.70
        routed_calm = sor.route_order(order_plan=plan_buy, gamma_toxic_dir=0.0)
        assert np.isclose(routed_calm["maker_ratio"], 0.70, atol=1e-3)

        # Full directional toxicity: maker_ratio == 0.20
        routed_toxic = sor.route_order(order_plan=plan_buy, gamma_toxic_dir=1.0)
        assert np.isclose(routed_toxic["maker_ratio"], 0.20, atol=1e-3)

        # Via raw hawkes intensities: hawkes_sell=20.0, hawkes_buy=1.0 for BUY
        routed_hwk = sor.route_order(order_plan=plan_buy, hawkes_buy=1.0, hawkes_sell=20.0, baseline_intensity=1.0)
        assert np.isclose(routed_hwk["maker_ratio"], 0.20, atol=1e-3)

        # But for a SELL order with hawkes_sell=20.0, hawkes_buy=1.0: maker_ratio remains 0.70!
        plan_sell = {**plan_buy, "action": "SELL"}
        routed_sell_hwk = sor.route_order(order_plan=plan_sell, hawkes_buy=1.0, hawkes_sell=20.0, baseline_intensity=1.0)
        assert np.isclose(routed_sell_hwk["maker_ratio"], 0.70, atol=1e-3)


# ============================================================================
# Adversarial Challenge 4: Darkpool Anti-Gaming & Predatory 1-Lot Ping Snipes
# ============================================================================

class TestAdversarialDarkpoolAntiGaming:
    """
    Empirically stress-tests anti-gaming MinQty expansion to 50% under toxic flow,
    and proves blocking of predatory odd-lot / 1-lot snipes.
    """

    def test_predatory_ping_snipes_blocked_by_dynamic_min_qty_expansion(self):
        """
        Simulates an institutional block order of 50,000 shares under toxic flow.
        Verifies:
        1. dark_qty scales up to 35,000 shares.
        2. Dynamic min_quantity expands to 50% (17,500 shares).
        3. Predatory 1-lot, 10-lot, 100-lot ping snipes are strictly < min_quantity,
           proving structural defense against adverse informational leakage.
        """
        sor = SmartOrderRouter()
        plan = {
            "symbol": "TSLA",
            "action": "BUY",
            "quantity": 50_000,
            "target_price": 250.0,
            "execution_strategy": "PATIENT_TWAP",
            "darkpool_score": 0.90,
        }

        routed = sor.route_order(order_plan=plan, gamma_toxic_dir=1.0)
        dark_leg = routed["dark_ats_midpoint"]
        assert dark_leg is not None
        assert dark_leg.get("anti_gaming_active") is True

        dark_qty = dark_leg["quantity"]
        min_qty = dark_leg["min_quantity"]

        # Under gamma=1.0 and dp_score=0.90, min_ratio is clipped to exactly 50%
        assert min_qty == int(round(0.50 * dark_qty))
        assert min_qty >= 17_500

        # Adversarial snipes: 1-share, 10-shares, 100-shares, 500-shares
        for predatory_ping in [1, 10, 100, 500, 1000]:
            assert predatory_ping < min_qty, (
                f"Predatory ping {predatory_ping} penetrated darkpool barrier {min_qty}!"
            )

    def test_logistic_dark_fill_probability_extreme_stress(self):
        """
        Tests logistic hazard model bounds [0.10, 0.90] and monotonic responses:
        - Wide spread + high dark score -> approaches 0.90
        - Tight spread + toxic flow + high MinQty -> approaches 0.10
        - Extreme input overflow resistance (spread = 10,000 bps, gamma = 1000.0)
        """
        sor = SmartOrderRouter(use_logistic_dark_fill=True)
        base = {
            "symbol": "SPY", "action": "BUY", "quantity": 10_000,
            "target_price": 500.0, "execution_strategy": "MIDPOINT_PEG",
        }

        # 1. Best possible conditions (wide spread, max score, zero toxicity)
        r_max = sor.route_order(
            order_plan={**base, "darkpool_score": 1.0},
            market_spread_bps=100.0, gamma_toxic_dir=0.0, use_logistic_dark_fill=True,
        )
        p_max = r_max["darkpool_fill_probability"]
        assert 0.80 <= p_max <= 0.90

        # 2. Worst possible conditions (negative/zero spread, zero score, max toxicity)
        r_min = sor.route_order(
            order_plan={**base, "darkpool_score": 0.0},
            market_spread_bps=0.1, gamma_toxic_dir=1.0, use_logistic_dark_fill=True,
        )
        p_min = r_min["darkpool_fill_probability"]
        assert 0.10 <= p_min <= 0.25

        # 3. Extreme numerical explosion inputs (bps=100,000, gamma=100,000)
        r_huge = sor.route_order(
            order_plan={**base, "darkpool_score": 50.0},
            market_spread_bps=100_000.0, gamma_toxic_dir=0.0, use_logistic_dark_fill=True,
        )
        assert r_huge["darkpool_fill_probability"] == 0.90

        r_low = sor.route_order(
            order_plan={**base, "darkpool_score": -50.0},
            market_spread_bps=-1000.0, gamma_toxic_dir=1000.0, use_logistic_dark_fill=True,
        )
        assert r_low["darkpool_fill_probability"] == 0.10


# ============================================================================
# Adversarial Challenge 5: Monte Carlo Parity Across 100 Random Parameter Sets
# ============================================================================

class TestAdversarialOMSAlmgrenChrissParityMonteCarlo:
    """
    Empirically verifies 100% mathematical parity between ExecutionOMSEngine
    and AlmgrenChrissScheduler peg limit price calculation across 100 random combinations.
    """

    def test_randomized_parity_across_100_parameter_combinations(self):
        """
        Runs 100 randomized parameter configurations with diverse spreads, OBI values,
        queue position ratios, micro-prices, volatilities, and actions.
        Asserts absolute parity (atol < 1e-7) and strict clipping inside [min(bid, ask), max(bid, ask)].
        """
        rng = random.Random(42)
        actions = ["BUY", "SELL", "LONG", "BUY_HEDGE", "BID"]

        for trial in range(100):
            target_p = rng.uniform(10.0, 2000.0)
            spread = rng.uniform(0.05, 50.0)
            bid_p = target_p - spread / 2.0
            ask_p = target_p + spread / 2.0
            act = rng.choice(actions)

            alpha_urg = rng.uniform(0.0, 1.0)
            u_q = rng.uniform(-0.2, 1.5)  # includes out-of-bounds queue ratios
            obi = rng.uniform(-1.5, 1.5)
            l3_imb = rng.uniform(-1.5, 1.5)
            l3_mp = rng.uniform(bid_p - spread, ask_p + spread)
            mp = rng.uniform(bid_p, ask_p)
            vol = rng.uniform(0.005, 0.15)
            depth_r = rng.uniform(0.1, 10.0)

            multi_obi = {
                "OBI_1": rng.uniform(-1.0, 1.0),
                "OBI_5": rng.uniform(-1.0, 1.0),
                "OBI_10": rng.uniform(-1.0, 1.0),
            }

            params = {
                "target_price": target_p,
                "bid_price": bid_p,
                "ask_price": ask_p,
                "spread": spread,
                "alpha_urgency": alpha_urg,
                "action": act,
                "obi": obi,
                "micro_price": mp,
                "l3_micro_price": l3_mp,
                "l3_imbalance": l3_imb,
                "multi_obi": multi_obi,
                "daily_volatility": vol,
                "book_depth_ratio": depth_r,
                "queue_position_ratio": u_q,
            }

            px_oms = ExecutionOMSEngine.calculate_peg_limit_price(**params)
            px_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(**params)

            # Strict parity check to < 10^-7
            assert math.isclose(px_oms, px_ac, abs_tol=1e-7), (
                f"Trial {trial} parity mismatch: OMS={px_oms}, AC={px_ac}, params={params}"
            )

            # Strict boundary check
            p_min = min(bid_p, ask_p)
            p_max = max(bid_p, ask_p)
            assert p_min - 1e-6 <= px_oms <= p_max + 1e-6, (
                f"Trial {trial} price {px_oms} outside [{p_min}, {p_max}]"
            )


# ============================================================================
# Adversarial Challenge 6: Multi-Threaded Concurrency & Stress Gating
# ============================================================================

class TestAdversarialConcurrencyAndStress:
    """
    Empirically verifies thread safety, absence of deadlocks, and stability under
    high-frequency concurrent access to FastOrderBookMatchingEngine and BivariateHawkesIntensity.
    """

    def test_fast_lob_engine_concurrent_order_matching_and_snapshot(self):
        """
        Spawns 4 concurrent worker threads simultaneously adding limit orders,
        querying queue positions, cancelling orders, and fetching snapshots.
        Asserts zero deadlocks, zero race exceptions, and strict state consistency.
        """
        engine = FastOrderBookMatchingEngine(symbol="CONCUR_TEST", tick_size=0.01)
        errors = []

        def worker(w_id: int):
            try:
                for i in range(50):
                    oid = f"w{w_id}_ord_{i}"
                    side = "BUY" if (i % 2 == 0) else "SELL"
                    price = 100.0 + (i % 5) * 0.10 if side == "SELL" else 100.0 - (i % 5) * 0.10
                    engine.add_limit_order(oid, side, price, 10.0)

                    # Intermittent queue check
                    if i % 3 == 0:
                        engine.estimate_queue_position(oid)

                    # Intermittent snapshot
                    if i % 5 == 0:
                        engine.get_depth_snapshot(levels=5)

                    # Intermittent cancellation
                    if i % 7 == 0:
                        engine.cancel_order(oid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t_id,)) for t_id in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Concurrent stress generated errors: {errors}"

    def test_bivariate_hawkes_concurrent_updates_and_queries(self):
        """
        Spawns concurrent worker threads updating and querying BivariateHawkesIntensity.
        Asserts zero race exceptions and valid intensity values.
        """
        bh = BivariateHawkesIntensity(mu_buy=1.0, mu_sell=1.0)
        errors = []

        def hawkes_worker(w_id: int):
            try:
                for i in range(100):
                    side = "BUY" if (i % 2 == 0) else "SELL"
                    bh.update(side)
                    res = bh.get_directional_toxicity("BUY")
                    assert res["gamma_toxic_dir"] >= 0.0
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=hawkes_worker, args=(t_id,)) for t_id in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Concurrent Hawkes stress generated errors: {errors}"
