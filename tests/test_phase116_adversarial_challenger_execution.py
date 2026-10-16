"""
tests/test_phase116_adversarial_challenger_execution.py
=======================================================
Adversarial Stress, Boundary Fuzzing, Invariant Verification, and Mathematical Stability Suite for:
Feature F552: High-Frequency Avellaneda-Stoikov Inventory Risk Controller (src/risk/avellaneda_stoikov_controller.py)
Feature F553: Dynamic Dark Pool Conditional Liquidity Seeker (src/execution/darkpool_liquidity_seeker.py)
Phase 116 (Release R132 / v123 Production Master).

Adversarial Attack Vectors & Empirical Challenges:
1. Vector 1: Extreme Inventory Boundaries & Unilateral Quote Suppression
   - q = +Q_max (hard positive capacity: bid strictly suppressed to 0.0, can_bid=False, can_ask=True)
   - q = -Q_max (hard negative capacity: ask strictly suppressed to +inf, can_ask=False, can_bid=True)
   - q = +/- 10*Q_max, +/- 100*Q_max (out-of-bounds inventory: ratio clamping prevents float overflow)
   - Zero & negative volatility (sigma <= 0.0), extreme risk aversion (gamma -> inf, gamma -> 0)
   - Session horizon boundaries: T -> inf, T -> 0, elapsed_sec >= T (expired tranche), elapsed_sec < 0
   - Discrete tick snapping across all 5 markets (US $0.01, KRX 100 KRW, 50 KRW) preventing inverted quotes

2. Vector 2: Extreme Toxic Flow & Runaway Adverse Selection
   - Maximum quote toxicity (T_quote = 1.0, and overshot T_quote > 1.0)
   - Maximum Hawkes arrival imbalance (I_Hawkes = +/- 1.0, and out-of-range +/- 10.0)
   - Runaway unilateral adverse selection: 100 continuous hostile BUY/SELL fills
   - Monotonic reservation price decay and half-spread repulsion
   - Hawkes-coupled snapshot integration under high volatility

3. Vector 3: Dark Pool Predatory Sniffing & Anti-Gaming Defense
   - Micro-slice probing below MEQ: predatory 1-share pings rejected with REJECTED_MEQ
   - Zero-liquidity IOC sweeps: instant MISSED return, zero lit footprint, WalkPhase.WALK_AWAY
   - Ping-and-walk state machine: walk-in expansion on hit, walk-away retreat on miss
   - Dynamic terminal tranche MEQ adaptation preventing stranded residual shares
   - Front-running & information leakage audit detection on retreat
   - Hostile post-trade adverse selection markouts across discrete horizons (100ms, 500ms, 1s, 5s)
   - Hawkes quote toxicity abort gate (T_quote >= toxicity_threshold)

4. Vector 4: Volume Conservation Invariant & Monte Carlo Fuzzing
   - Strict invariant: filled_dark_shares + residual_lit_shares == parent_quantity across 1,000 randomized sweeps
   - 1,000-iteration Monte Carlo fuzzing of AvellanedaStoikovController parameters
   - Zero uncaught exceptions, zero NaNs, zero unexpected infinities, zero volume leakage
"""

from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.hawkes_microstructure_engine import HawkesIntensitySnapshot
from src.risk.avellaneda_stoikov_controller import (
    FEATURE as AS_FEATURE,
    MARKET_AS_PROFILES,
    RELEASE as AS_RELEASE,
    VERSION as AS_VERSION,
    ASInventoryController,
    ASQuoteRecommendation,
    AvellanedaStoikovConfig,
    AvellanedaStoikovController,
    InventoryRiskReport,
)
from src.execution.darkpool_liquidity_seeker import (
    FEATURE as DP_FEATURE,
    MARKET_DARKPOOL_PROFILES,
    RELEASE as DP_RELEASE,
    VERSION as DP_VERSION,
    DarkPoolLiquiditySeeker,
    DarkPoolSeekerConfig,
    DarkPoolTelemetrySummary,
    DarkSweepResult,
    ProbeOrder,
    ProbeResult,
    ProbeStatus,
    WalkPhase,
)


class TestAdversarialAvellanedaInventoryBoundaries(unittest.TestCase):
    """
    Challenge Vector 1: Extreme Inventory Boundaries & Unilateral Quote Suppression.
    Tests physical limits, out-of-bounds inventory, zero volatility, infinite horizon, and discrete tick snapping.
    """

    def setUp(self) -> None:
        self.config = AvellanedaStoikovConfig(
            market="SP500",
            symbol="AAPL",
            gamma=0.10,
            kappa=2.0,
            max_inventory=10_000.0,
            horizon_T_sec=300.0,
            tick_size=0.01,
            base_vol=0.015,
        )
        self.controller = AvellanedaStoikovController(config=self.config)

    def test_adv_as_01_max_positive_inventory_unilateral_quote_suppression(self) -> None:
        """Assert q = +Q_max strictly suppresses bid quote to 0.0 while ask quote remains active."""
        mid = 150.0
        q_max = self.config.max_inventory

        quotes = self.controller.compute_optimal_quotes(mid_price=mid, inventory=q_max)
        self.assertFalse(quotes.can_bid, "can_bid must be False at q = +Q_max")
        self.assertTrue(quotes.can_ask, "can_ask must be True at q = +Q_max")
        self.assertEqual(quotes.bid_price, 0.0, "Bid price must be suppressed to 0.0")
        self.assertGreater(quotes.ask_price, mid, "Ask price must remain active above mid")
        self.assertFalse(math.isnan(quotes.ask_price), "Ask price must not be NaN")
        self.assertFalse(math.isinf(quotes.ask_price), "Ask price must be finite")

    def test_adv_as_02_max_negative_inventory_unilateral_quote_suppression(self) -> None:
        """Assert q = -Q_max strictly suppresses ask quote to inf while bid quote remains active."""
        mid = 150.0
        q_max = self.config.max_inventory

        quotes = self.controller.compute_optimal_quotes(mid_price=mid, inventory=-q_max)
        self.assertTrue(quotes.can_bid, "can_bid must be True at q = -Q_max")
        self.assertFalse(quotes.can_ask, "can_ask must be False at q = -Q_max")
        self.assertGreater(quotes.bid_price, 0.0, "Bid price must remain active above 0.0")
        self.assertLess(quotes.bid_price, mid, "Bid price must be below mid")
        self.assertEqual(quotes.ask_price, float("inf"), "Ask price must be suppressed to +inf")
        self.assertFalse(math.isnan(quotes.bid_price), "Bid price must not be NaN")

    def test_adv_as_03_out_of_bounds_extreme_long_inventory_no_overflow(self) -> None:
        """Assert out-of-bounds inventory (+2*Q_max to +100*Q_max) does not overflow or produce NaN."""
        mid = 150.0
        q_max = self.config.max_inventory

        for multiplier in [2.0, 5.0, 10.0, 50.0, 100.0]:
            q_extreme = multiplier * q_max
            r = self.controller.compute_reservation_price(mid_price=mid, inventory=q_extreme)
            self.assertFalse(math.isnan(r), f"Reservation price was NaN for q = {q_extreme}")
            self.assertFalse(math.isinf(r), f"Reservation price was Inf for q = {q_extreme}")
            self.assertLess(r, mid, f"Reservation price must be heavily depressed below mid for q = {q_extreme}")

            quotes = self.controller.compute_optimal_quotes(mid_price=mid, inventory=q_extreme)
            self.assertFalse(quotes.can_bid, f"can_bid must be False for q = {q_extreme}")
            self.assertEqual(quotes.bid_price, 0.0)
            self.assertTrue(quotes.can_ask)
            self.assertFalse(math.isnan(quotes.ask_price))

            risk = self.controller.evaluate_inventory_risk(mid_price=mid, inventory=q_extreme)
            self.assertTrue(risk.is_inventory_breached)
            self.assertFalse(risk.can_accumulate_long)
            self.assertTrue(risk.can_accumulate_short)
            self.assertEqual(risk.skew_direction, "REDUCE_LONG")

    def test_adv_as_04_out_of_bounds_extreme_short_inventory_no_overflow(self) -> None:
        """Assert out-of-bounds short inventory (-2*Q_max to -100*Q_max) does not overflow or produce NaN."""
        mid = 150.0
        q_max = self.config.max_inventory

        for multiplier in [-2.0, -5.0, -10.0, -50.0, -100.0]:
            q_extreme = multiplier * q_max
            r = self.controller.compute_reservation_price(mid_price=mid, inventory=q_extreme)
            self.assertFalse(math.isnan(r), f"Reservation price was NaN for q = {q_extreme}")
            self.assertFalse(math.isinf(r), f"Reservation price was Inf for q = {q_extreme}")
            self.assertGreater(r, mid, f"Reservation price must be elevated above mid for q = {q_extreme}")

            quotes = self.controller.compute_optimal_quotes(mid_price=mid, inventory=q_extreme)
            self.assertTrue(quotes.can_bid)
            self.assertFalse(quotes.can_ask, f"can_ask must be False for q = {q_extreme}")
            self.assertEqual(quotes.ask_price, float("inf"))

            risk = self.controller.evaluate_inventory_risk(mid_price=mid, inventory=q_extreme)
            self.assertTrue(risk.is_inventory_breached)
            self.assertTrue(risk.can_accumulate_long)
            self.assertFalse(risk.can_accumulate_short)
            self.assertEqual(risk.skew_direction, "REDUCE_SHORT")

    def test_adv_as_05_zero_and_negative_volatility_resilience(self) -> None:
        """Assert zero volatility or negative volatility override is safely clamped without math domain error."""
        mid = 100.0
        for vol_input in [0.0, -0.01, -1.0, 1e-12]:
            r = self.controller.compute_reservation_price(mid_price=mid, inventory=100.0, vol=vol_input)
            self.assertFalse(math.isnan(r), f"NaN reservation price for vol = {vol_input}")
            self.assertLess(r, mid)

            bid_bps, ask_bps, total_bps = self.controller.compute_optimal_spreads(mid_price=mid, vol=vol_input)
            self.assertFalse(math.isnan(bid_bps))
            self.assertFalse(math.isnan(ask_bps))
            self.assertGreaterEqual(total_bps, self.config.min_spread_bps)

    def test_adv_as_06_infinite_and_zero_horizon_stability(self) -> None:
        """Assert T -> inf and T -> 0 do not produce division by zero or NaN."""
        mid = 200.0

        # Extreme large horizon T = 10^9 seconds
        cfg_huge = AvellanedaStoikovConfig(horizon_T_sec=1e9)
        ctrl_huge = AvellanedaStoikovController(config=cfg_huge)
        q_huge = ctrl_huge.compute_optimal_quotes(mid_price=mid, inventory=500.0, elapsed_sec=100.0)
        self.assertFalse(math.isnan(q_huge.reservation_price))
        self.assertFalse(math.isnan(q_huge.bid_price))
        self.assertFalse(math.isnan(q_huge.ask_price))

        # Degenerate zero horizon T = 0.0 (clamped to max(1.0, T))
        cfg_zero = AvellanedaStoikovConfig(horizon_T_sec=0.0)
        ctrl_zero = AvellanedaStoikovController(config=cfg_zero)
        q_zero = ctrl_zero.compute_optimal_quotes(mid_price=mid, inventory=500.0, elapsed_sec=0.0)
        self.assertFalse(math.isnan(q_zero.reservation_price))
        self.assertFalse(math.isnan(q_zero.bid_price))
        self.assertFalse(math.isnan(q_zero.ask_price))

    def test_adv_as_07_expired_and_negative_elapsed_time_handling(self) -> None:
        """Assert elapsed_sec >= T (expired session) and elapsed_sec < 0 clamp time remaining safely."""
        mid = 100.0
        T = self.config.horizon_T_sec

        # Session expired (elapsed = T + 500s)
        quotes_expired = self.controller.compute_optimal_quotes(mid_price=mid, elapsed_sec=T + 500.0)
        self.assertEqual(quotes_expired.time_remaining_sec, 0.0, "time_remaining_sec must clamp to 0.0")
        self.assertFalse(math.isnan(quotes_expired.bid_price))
        self.assertFalse(math.isnan(quotes_expired.ask_price))

        # Negative elapsed time (clock jitter/drift, elapsed = -100s)
        quotes_neg = self.controller.compute_optimal_quotes(mid_price=mid, elapsed_sec=-100.0)
        self.assertEqual(quotes_neg.time_remaining_sec, T, "Negative elapsed_sec must clamp to T")
        self.assertFalse(math.isnan(quotes_neg.bid_price))
        self.assertFalse(math.isnan(quotes_neg.ask_price))

    def test_adv_as_08_degenerate_mid_prices_safe_return(self) -> None:
        """Assert zero and negative mid-prices safely return 0.0 without exception."""
        for bad_mid in [0.0, -1.0, -100.0]:
            r = self.controller.compute_reservation_price(mid_price=bad_mid)
            self.assertEqual(r, 0.0)
            spreads = self.controller.compute_optimal_spreads(mid_price=bad_mid)
            self.assertEqual(spreads, (0.0, 0.0, 0.0))

    def test_adv_as_09_extreme_gamma_and_kappa_hyperparameters(self) -> None:
        """Assert asymptotic stability for extreme gamma (risk aversion) and kappa (elasticity)."""
        mid = 150.0

        # Massive risk aversion gamma = 500.0
        cfg_gamma = AvellanedaStoikovConfig(gamma=500.0)
        ctrl_gamma = AvellanedaStoikovController(config=cfg_gamma)
        quotes = ctrl_gamma.compute_optimal_quotes(mid_price=mid, inventory=100.0)
        self.assertFalse(math.isnan(quotes.bid_price))
        self.assertFalse(math.isnan(quotes.ask_price))

        # Infinitesimal risk aversion gamma = 1e-9 (clamped to 1e-6)
        cfg_small_gamma = AvellanedaStoikovConfig(gamma=1e-9)
        ctrl_small_gamma = AvellanedaStoikovController(config=cfg_small_gamma)
        quotes_sg = ctrl_small_gamma.compute_optimal_quotes(mid_price=mid, inventory=100.0)
        self.assertFalse(math.isnan(quotes_sg.bid_price))
        self.assertFalse(math.isnan(quotes_sg.ask_price))

        # Extreme elasticity kappa = 1e-8 and kappa = 1000.0
        for kappa_val in [1e-8, 1000.0]:
            cfg_k = AvellanedaStoikovConfig(kappa=kappa_val)
            ctrl_k = AvellanedaStoikovController(config=cfg_k)
            quotes_k = ctrl_k.compute_optimal_quotes(mid_price=mid, inventory=50.0)
            self.assertFalse(math.isnan(quotes_k.bid_price))
            self.assertFalse(math.isnan(quotes_k.ask_price))


class TestAdversarialAvellanedaToxicFlowAndRunawayAdverseSelection(unittest.TestCase):
    """
    Challenge Vector 2: Extreme Toxic Flow & Runaway Adverse Selection.
    Tests Hawkes quote toxicity, extreme arrival imbalance, continuous hostile fills, and tick snapping.
    """

    def setUp(self) -> None:
        self.controller = AvellanedaStoikovController(market="SP500", symbol="NVDA")

    def test_adv_as_10_maximum_and_overshot_hawkes_quote_toxicity(self) -> None:
        """Assert T_quote = 1.0 (and overshot T_quote > 1.0) safely widens spread to ceiling without NaN."""
        mid = 120.0
        base_quotes = self.controller.compute_optimal_quotes(mid_price=mid, hawkes_toxicity=0.0)
        max_tox_quotes = self.controller.compute_optimal_quotes(mid_price=mid, hawkes_toxicity=1.0)
        overshot_quotes = self.controller.compute_optimal_quotes(mid_price=mid, hawkes_toxicity=3.5)

        self.assertGreater(max_tox_quotes.total_spread_bps, base_quotes.total_spread_bps)
        self.assertEqual(max_tox_quotes.total_spread_bps, overshot_quotes.total_spread_bps, "Overshot toxicity must clamp to 1.0")
        self.assertLessEqual(max_tox_quotes.total_spread_bps, self.controller.config.max_spread_bps)

    def test_adv_as_11_extreme_hawkes_imbalance_bounds_and_floors(self) -> None:
        """Assert arrival imbalance I_Hawkes = +/- 1.0 and +/- 10.0 respects half-spread floors."""
        mid = 100.0
        min_half = self.controller.config.min_half_spread_bps

        # Massive buy burst (I_Hawkes = +1.0 and overshot +10.0)
        for imb in [1.0, 10.0]:
            quotes_buy = self.controller.compute_optimal_quotes(mid_price=mid, hawkes_imbalance=imb)
            self.assertGreaterEqual(quotes_buy.bid_half_spread_bps, min_half)
            self.assertGreaterEqual(quotes_buy.ask_half_spread_bps, min_half)
            self.assertGreater(quotes_buy.ask_price, quotes_buy.bid_price)

        # Massive sell burst (I_Hawkes = -1.0 and overshot -10.0)
        for imb in [-1.0, -10.0]:
            quotes_sell = self.controller.compute_optimal_quotes(mid_price=mid, hawkes_imbalance=imb)
            self.assertGreaterEqual(quotes_sell.bid_half_spread_bps, min_half)
            self.assertGreaterEqual(quotes_sell.ask_half_spread_bps, min_half)
            self.assertGreater(quotes_sell.ask_price, quotes_sell.bid_price)

    def test_adv_as_12_runaway_hostile_buy_fills_adverse_selection_cascade(self) -> None:
        """
        Simulate 100 continuous hostile BUY fills pushing inventory from 0 to +2*Q_max.
        Assert monotonic reservation price reduction, bid spread widening, and strict quote cutoff at Q_max.
        """
        self.controller.reset()
        mid = 100.0
        q_max = self.controller.config.max_inventory
        fill_slice = q_max / 50.0  # 50 fills to hit Q_max

        last_r = mid
        for step in range(1, 101):
            inv = self.controller.update_fill(fill_side="BUY", fill_qty=fill_slice)
            quotes = self.controller.compute_optimal_quotes(mid_price=mid)

            # Reservation price must strictly decrease as long inventory builds
            self.assertLess(quotes.reservation_price, last_r, f"Step {step}: reservation price failed to decrease")
            last_r = quotes.reservation_price

            if inv < q_max:
                self.assertTrue(quotes.can_bid, f"Step {step}: can_bid should be True below Q_max")
                self.assertTrue(quotes.can_ask)
                self.assertGreater(quotes.bid_price, 0.0)
            else:
                # Reached or breached Q_max: bid strictly suppressed
                self.assertFalse(quotes.can_bid, f"Step {step}: can_bid must be False at/above Q_max (inv={inv})")
                self.assertEqual(quotes.bid_price, 0.0)
                self.assertTrue(quotes.can_ask)

    def test_adv_as_13_runaway_hostile_sell_fills_adverse_selection_cascade(self) -> None:
        """
        Simulate 100 continuous hostile SELL fills pushing inventory from 0 to -2*Q_max.
        Assert monotonic reservation price increase, ask spread widening, and strict quote cutoff at -Q_max.
        """
        self.controller.reset()
        mid = 100.0
        q_max = self.controller.config.max_inventory
        fill_slice = q_max / 50.0

        last_r = mid
        for step in range(1, 101):
            inv = self.controller.update_fill(fill_side="SELL", fill_qty=fill_slice)
            quotes = self.controller.compute_optimal_quotes(mid_price=mid)

            # Reservation price must strictly increase as short inventory builds
            self.assertGreater(quotes.reservation_price, last_r, f"Step {step}: reservation price failed to increase")
            last_r = quotes.reservation_price

            if inv > -q_max:
                self.assertTrue(quotes.can_bid)
                self.assertTrue(quotes.can_ask, f"Step {step}: can_ask should be True above -Q_max")
                self.assertLess(quotes.ask_price, float("inf"))
            else:
                # Reached or breached -Q_max: ask strictly suppressed
                self.assertTrue(quotes.can_bid)
                self.assertFalse(quotes.can_ask, f"Step {step}: can_ask must be False at/below -Q_max (inv={inv})")
                self.assertEqual(quotes.ask_price, float("inf"))

    def test_adv_as_14_tick_snapping_invariance_across_all_five_markets(self) -> None:
        """Verify discrete tick alignment and bid < ask across SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ."""
        for mkt in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            ctrl = AvellanedaStoikovController(market=mkt)
            tick = ctrl.config.tick_size
            mid = 75_000.0 if "KOS" in mkt else 150.0

            for q_ratio in [-0.75, -0.30, 0.0, 0.30, 0.75]:
                inv = q_ratio * ctrl.config.max_inventory
                quotes = ctrl.compute_optimal_quotes(mid_price=mid, inventory=inv)

                if quotes.can_bid and quotes.can_ask:
                    self.assertLess(quotes.bid_price, quotes.ask_price, f"{mkt}: bid must be strictly less than ask")
                    # Check tick alignment
                    bid_remainder = (quotes.bid_price / tick) - round(quotes.bid_price / tick)
                    ask_remainder = (quotes.ask_price / tick) - round(quotes.ask_price / tick)
                    self.assertAlmostEqual(bid_remainder, 0.0, places=4, msg=f"{mkt}: bid {quotes.bid_price} not snapped to tick {tick}")
                    self.assertAlmostEqual(ask_remainder, 0.0, places=4, msg=f"{mkt}: ask {quotes.ask_price} not snapped to tick {tick}")


class TestAdversarialDarkPoolPredatorySniffingAndAntiGaming(unittest.TestCase):
    """
    Challenge Vector 3: Dark Pool Predatory Sniffing & Anti-Gaming Defense.
    Tests micro-slice probing below MEQ, zero liquidity fill-or-kill, ping-and-walk retreat, and adverse selection markouts.
    """

    def setUp(self) -> None:
        self.seeker = DarkPoolLiquiditySeeker(market="SP500", symbol="AAPL", random_seed=42)

    def test_adv_dp_15_predatory_micro_slice_sniffing_blocked_by_meq(self) -> None:
        """
        Adversary attempts to sniff dark book by providing small-lot contra liquidity (e.g. 1 share or 5 shares).
        Assert execution is rejected with REJECTED_MEQ, zero shares are filled, and meq_rejections counter increments.
        """
        parent_qty = 10_000
        bid, ask = 150.00, 150.10
        mid = 150.05

        initial_rejections = self.seeker.telemetry.total_meq_rejections

        # Probe with tiny predatory contra liquidity: 1 share, 5 shares, 15 shares (all < MEQ of 100)
        for predatory_liquidity in [1, 5, 15, 49]:
            res = self.seeker.execute_ioc_midpoint_sweep(
                symbol="AAPL",
                side="BUY",
                quantity=1_000,
                bbo_bid=bid,
                bbo_ask=ask,
                counterparty_liquidity=predatory_liquidity,
                meq=100,
            )
            self.assertEqual(res.status, ProbeStatus.REJECTED_MEQ, f"Predatory lot {predatory_liquidity} was not rejected by MEQ")
            self.assertEqual(res.filled_quantity, 0, "No shares should be filled on MEQ rejection")
            self.assertEqual(res.price_improvement_usd, 0.0)
            self.assertTrue(res.counterparty_liquidity_detected, "Contra liquidity should be detected but rejected")

        self.assertGreater(self.seeker.total_meq_rejections, initial_rejections)

    def test_adv_dp_16_zero_liquidity_instant_miss_and_walk_away_retreat(self) -> None:
        """
        Dark venue has zero resting liquidity (counterparty_liquidity = 0).
        Assert instant MISSED status, zero dark fills, zero lit footprint, and transition to WalkPhase.WALK_AWAY.
        """
        parent_qty = 5_000
        bid, ask = 200.00, 200.08

        res = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=bid,
            bbo_ask=ask,
            side="BUY",
            counterparty_liquidity=0,
        )

        self.assertEqual(res.filled_dark_shares, 0, "Zero dark shares should be filled")
        self.assertEqual(res.residual_lit_shares, parent_qty, "Residual lit shares must equal parent quantity")
        self.assertEqual(res.fill_rate, 0.0)
        self.assertEqual(res.total_price_improvement_usd, 0.0)
        self.assertEqual(res.final_walk_phase, WalkPhase.WALK_AWAY, "Seeker must gracefully walk away on miss")
        self.assertEqual(res.probes_dispatched, 1, "Only single initial probe should be fired before retreating")
        self.assertFalse(res.information_leakage_detected)

    def test_adv_dp_17_dynamic_terminal_tranche_meq_adaptation_prevents_stranding(self) -> None:
        """
        When remaining tranche is smaller than default MEQ (e.g. 5 shares left when MEQ=100),
        calculate_meq with is_terminal_order=True must adapt MEQ downward so terminal tranche can fill cleanly.
        """
        mid = 100.0
        # Standard MEQ for 5 shares would be 100 (min_execution_quantity)
        standard_meq = self.seeker.calculate_meq(order_quantity=5, mid_price=mid, is_terminal_order=False)
        self.assertGreaterEqual(standard_meq, self.seeker.config.min_execution_quantity)

        # Terminal order MEQ adapts downward to min(qty, meq)
        terminal_meq = self.seeker.calculate_meq(order_quantity=5, mid_price=mid, is_terminal_order=True)
        self.assertEqual(terminal_meq, 5, "Terminal tranche MEQ must adapt down to remaining quantity 5")

        # Execute sweep with terminal order: fills cleanly without MEQ rejection
        probe_res = self.seeker.execute_ioc_midpoint_sweep(
            symbol="AAPL",
            side="BUY",
            quantity=5,
            bbo_bid=99.95,
            bbo_ask=100.05,
            counterparty_liquidity=5,
            meq=terminal_meq,
        )
        self.assertEqual(probe_res.status, ProbeStatus.FILLED)
        self.assertEqual(probe_res.filled_quantity, 5)

    def test_adv_dp_18_anti_gaming_ping_and_walk_state_machine_flow(self) -> None:
        """
        Verify two-phase anti-gaming ping-and-walk:
        1. On Hit: transitions to WALK_IN and expands allocation up to max_dark_ratio.
        2. On Miss: transitions to WALK_AWAY and terminates without further dark exposure.
        """
        parent_qty = 10_000
        bid, ask = 150.00, 150.10

        # Scenario A: Contra liquidity available -> Walk In
        res_hit = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=bid,
            bbo_ask=ask,
            side="BUY",
            counterparty_liquidity=parent_qty,
        )
        self.assertEqual(res_hit.final_walk_phase, WalkPhase.WALK_IN)
        self.assertGreater(res_hit.filled_dark_shares, 0)
        self.assertGreater(res_hit.total_price_improvement_usd, 0.0)
        self.assertGreaterEqual(res_hit.anti_gaming_walks, 1)

        # Scenario B: Contra liquidity unavailable -> Walk Away
        res_miss = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=bid,
            bbo_ask=ask,
            side="SELL",
            counterparty_liquidity=0,
        )
        self.assertEqual(res_miss.final_walk_phase, WalkPhase.WALK_AWAY)
        self.assertEqual(res_miss.filled_dark_shares, 0)
        self.assertEqual(res_miss.residual_lit_shares, parent_qty)

    def test_adv_dp_19_hawkes_quote_toxicity_hard_abort_gate(self) -> None:
        """Assert T_quote >= toxicity_threshold strictly aborts dark sweep with 0 probes and 0 leakage."""
        parent_qty = 5_000
        bid, ask = 100.00, 100.10

        # Toxic Hawkes flow: T_quote = 0.85 >= threshold 0.65
        res_abort = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=bid,
            bbo_ask=ask,
            hawkes_toxicity=0.85,
            counterparty_liquidity=parent_qty,
        )

        self.assertEqual(res_abort.probes_dispatched, 0, "No probes should be fired under toxic flow")
        self.assertEqual(res_abort.filled_dark_shares, 0)
        self.assertEqual(res_abort.residual_lit_shares, parent_qty)
        self.assertEqual(res_abort.final_walk_phase, WalkPhase.WALK_AWAY)

    def test_adv_dp_20_hostile_post_trade_adverse_selection_markouts(self) -> None:
        """Simulate malicious adverse selection: price collapses 50 bps immediately following BUY fill."""
        parent_qty = 2_000
        bid, ask = 100.00, 100.20  # mid = 100.10
        mid = 100.10

        # Post-trade prices at 100ms, 500ms, 1s, 5s collapse against our BUY
        hostile_marks = {
            100: 100.00,   # -10 bps
            500: 99.80,    # -30 bps
            1000: 99.60,   # -50 bps
            5000: 99.50,   # -60 bps
        }

        init_events = self.seeker.adverse_selection_events
        res = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=bid,
            bbo_ask=ask,
            side="BUY",
            counterparty_liquidity=parent_qty,
            forward_price_marks=hostile_marks,
        )

        self.assertGreater(res.filled_dark_shares, 0)
        self.assertIn(100, res.markout_bps)
        self.assertIn(1000, res.markout_bps)
        self.assertLess(res.markout_bps[1000], -1.0, "Markout at 1s must be significantly negative")
        self.assertGreater(self.seeker.adverse_selection_events, init_events, "Adverse selection event must be recorded")

    def test_adv_dp_21_order_book_crossed_and_zero_spread_normalization(self) -> None:
        """Assert crossed book (bid > ask) and zero spread (bid == ask) normalize gracefully without error."""
        parent_qty = 1_000

        # Crossed book: bid=100.20, ask=100.00
        res_crossed = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=100.20,
            bbo_ask=100.00,
            counterparty_liquidity=parent_qty,
        )
        self.assertGreater(res_crossed.filled_dark_shares, 0)
        self.assertEqual(res_crossed.vwap_fill_price, 100.10)
        self.assertGreaterEqual(res_crossed.total_price_improvement_usd, 0.0)

        # Zero spread: bid=100.00, ask=100.00
        res_zero = self.seeker.seek_liquidity(
            parent_quantity=parent_qty,
            bbo_bid=100.00,
            bbo_ask=100.00,
            counterparty_liquidity=parent_qty,
        )
        self.assertGreater(res_zero.filled_dark_shares, 0)
        self.assertEqual(res_zero.vwap_fill_price, 100.00)
        self.assertEqual(res_zero.total_price_improvement_usd, 0.0)

    def test_adv_dp_22_single_share_parent_order_integrity(self) -> None:
        """Assert single share order (parent_quantity = 1) preserves volume conservation without overfill."""
        res_single = self.seeker.seek_liquidity(
            parent_quantity=1,
            bbo_bid=50.00,
            bbo_ask=50.10,
            counterparty_liquidity=100,
        )
        self.assertLessEqual(res_single.filled_dark_shares, 1, "Dark filled shares cannot exceed parent quantity of 1")
        self.assertGreaterEqual(res_single.residual_lit_shares, 0, "Residual lit shares must be non-negative")
        self.assertEqual(res_single.filled_dark_shares + res_single.residual_lit_shares, 1)


class TestAdversarialVolumeConservationMonteCarlo(unittest.TestCase):
    """
    Challenge Vector 4: Volume Conservation Invariant & Monte Carlo Fuzzing.
    Executes 1,000 randomized Monte Carlo sweeps across all 5 markets verifying:
    filled_dark_shares + residual_lit_shares == parent_quantity identically with zero volume leakage.
    """

    def test_adv_mc_23_monte_carlo_volume_conservation_1000_sweeps(self) -> None:
        """
        Fuzzing 1,000 randomized execution configurations:
        Asserts: filled_dark_shares + residual_lit_shares == parent_quantity (STRICT INVARIANT).
        """
        rng = np.random.default_rng(seed=2026116)
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        sides = ["BUY", "SELL"]

        seekers = {mkt: DarkPoolLiquiditySeeker(market=mkt, random_seed=int(rng.integers(1, 100_000))) for mkt in markets}

        for iteration in range(1_000):
            mkt = str(rng.choice(markets))
            seeker = seekers[mkt]
            side = str(rng.choice(sides))

            # Randomize order size from small (1 share) to institutional (500,000 shares)
            if iteration % 10 == 0:
                parent_qty = int(rng.integers(1, 10))  # Micro-orders
            elif iteration % 10 == 1:
                parent_qty = int(rng.integers(100_000, 500_000))  # Block orders
            else:
                parent_qty = int(rng.integers(10, 50_000))

            # Prices
            if "KOS" in mkt:
                base_p = float(rng.uniform(1_000.0, 200_000.0))
                spread = float(rng.uniform(50.0, 1_000.0))
            else:
                base_p = float(rng.uniform(1.0, 2_000.0))
                spread = float(rng.uniform(0.01, 5.0))

            bid = base_p
            ask = base_p + spread

            # Counterparty liquidity pool: 0 to 2x parent
            contra_pool = int(rng.integers(0, int(parent_qty * 2.0) + 1))

            # Hawkes toxicity: [0.0, 1.0]
            toxicity = float(rng.uniform(0.0, 1.0))

            sweep_res = seeker.seek_liquidity(
                parent_quantity=parent_qty,
                bbo_bid=bid,
                bbo_ask=ask,
                side=side,
                counterparty_liquidity=contra_pool,
                hawkes_toxicity=toxicity,
            )

            # Invariant 1: Volume Conservation
            total_accounted = sweep_res.filled_dark_shares + sweep_res.residual_lit_shares
            self.assertEqual(
                total_accounted,
                parent_qty,
                f"Iteration {iteration} [{mkt}]: Volume leakage! "
                f"filled={sweep_res.filled_dark_shares} + residual={sweep_res.residual_lit_shares} != parent={parent_qty}"
            )

            # Invariant 2: Non-negative bounds
            self.assertGreaterEqual(sweep_res.filled_dark_shares, 0)
            self.assertGreaterEqual(sweep_res.residual_lit_shares, 0)
            self.assertLessEqual(sweep_res.filled_dark_shares, parent_qty)

            # Invariant 3: Price improvement non-negativity
            self.assertGreaterEqual(sweep_res.total_price_improvement_usd, 0.0)

            # Invariant 4: No NaNs
            self.assertFalse(math.isnan(sweep_res.fill_rate))
            self.assertFalse(math.isnan(sweep_res.total_price_improvement_bps))
            self.assertFalse(math.isnan(sweep_res.vwap_fill_price))

        # Check telemetry aggregates across all seekers
        for mkt, s in seekers.items():
            telemetry = s.get_telemetry_summary()
            self.assertGreater(telemetry.total_orders_handled, 0)
            self.assertEqual(
                telemetry.total_shares_requested,
                sum(r.parent_quantity for r in s.execution_history),
                f"{mkt}: Cumulative requested shares mismatch"
            )
            self.assertEqual(
                telemetry.total_shares_dark_filled,
                sum(r.filled_dark_shares for r in s.execution_history),
                f"{mkt}: Cumulative filled shares mismatch"
            )


class TestAdversarialAvellanedaMonteCarloFuzzing(unittest.TestCase):
    """
    Challenge Vector 5: Avellaneda-Stoikov Monte Carlo Parameter Fuzzing.
    Executes 1,000 randomized parameter sweeps asserting mathematical stability and quote consistency.
    """

    def test_adv_mc_24_avellaneda_fuzzing_1000_sweeps(self) -> None:
        """
        Fuzzing 1,000 randomized market and state configurations:
        Asserts finite floats, quote order consistency (bid < ask), and strict capacity gating.
        """
        rng = np.random.default_rng(seed=2026552)
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

        controllers = {mkt: AvellanedaStoikovController(market=mkt) for mkt in markets}

        for iteration in range(1_000):
            mkt = str(rng.choice(markets))
            ctrl = controllers[mkt]
            q_max = ctrl.config.max_inventory

            # Mid price
            mid = float(rng.uniform(10.0, 100_000.0) if "KOS" in mkt else rng.uniform(0.50, 3_000.0))

            # Inventory q between -5*Q_max and +5*Q_max
            q = float(rng.uniform(-3.0 * q_max, 3.0 * q_max))

            # Elapsed time between -50s and +600s
            elapsed = float(rng.uniform(-50.0, 600.0))

            # Volatility override
            vol = float(rng.uniform(0.0001, 1.0))

            # Hawkes metrics
            imb = float(rng.uniform(-2.0, 2.0))
            tox = float(rng.uniform(-0.5, 2.5))

            quotes = ctrl.compute_optimal_quotes(
                mid_price=mid,
                inventory=q,
                elapsed_sec=elapsed,
                vol=vol,
                hawkes_imbalance=imb,
                hawkes_toxicity=tox,
            )

            # Assert no NaNs
            self.assertFalse(math.isnan(quotes.reservation_price), f"Iter {iteration}: reservation price is NaN")
            self.assertFalse(math.isnan(quotes.total_spread_bps), f"Iter {iteration}: total spread is NaN")

            # Capacity gating invariants
            if q >= q_max:
                self.assertFalse(quotes.can_bid, f"Iter {iteration}: can_bid should be False for q >= Q_max")
                self.assertEqual(quotes.bid_price, 0.0)
            if q <= -q_max:
                self.assertFalse(quotes.can_ask, f"Iter {iteration}: can_ask should be False for q <= -Q_max")
                self.assertEqual(quotes.ask_price, float("inf"))

            # When both quotes are active, bid must be strictly less than ask
            if quotes.can_bid and quotes.can_ask:
                self.assertLess(quotes.bid_price, quotes.ask_price, f"Iter {iteration}: Inverted quote ladder!")
                self.assertFalse(math.isinf(quotes.bid_price))
                self.assertFalse(math.isinf(quotes.ask_price))


if __name__ == "__main__":
    unittest.main()
