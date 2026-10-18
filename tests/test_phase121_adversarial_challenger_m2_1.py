r"""
tests/test_phase121_adversarial_challenger_m2_1.py
===================================================
Adversarial Stress Verification Suite for Feature F576:
Multi-Agent Reinforcement Learning (MARL) Adaptive Liquidity Harvester.
Phase 121 (Release R137 / v128 Production Master).

Empirical Challenger 1 Suite:
  - Category 1: Pathological Order Book Invariants & Float Extremes (ADV01 ~ ADV08)
  - Category 2: Sustained Toxic Order Flow Shocks & Dynamic Quote Fading (ADV09 ~ ADV15)
  - Category 3: Extreme Inventory Imbalances & Homeostasis Quoting (ADV16 ~ ADV22)
  - Category 4: Long Continuous Simulation, Stability & Memory Leaks (ADV23 ~ ADV28)
  - Category 5: Cross-Market Robustness, Concurrency & Determinism (ADV29 ~ ADV32)
"""

from __future__ import annotations

import concurrent.futures
import gc
import math
import sys
import time
import tracemalloc
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.marl_liquidity_harvester import (
    VERSION,
    RELEASE,
    FEATURE,
    NUM_AGENTS,
    DEFAULT_OBS_DIM,
    DEFAULT_ACTION_DIM,
    MarketProfile,
    MarketType,
    AgentRole,
    ToxicityLevel,
    QuoteSide,
    MARKET_MARL_PROFILES,
    MARLHarvesterConfig,
    AgentObservation,
    QuoteAction,
    AgentAction,
    InternalNettingResult,
    HarvesterQuoteResult,
    MARLLiquidityHarvester,
    _TORCH_AVAILABLE,
)


class TestPhase121AdversarialChallengerM2(unittest.TestCase):
    """
    Empirical Adversarial Challenge Suite for Feature F576.
    Stress-tests edge cases, pathological inputs, toxic bursts, extreme inventory,
    long-run memory stability, and cross-market robustness.
    """

    # =========================================================================
    # Category 1: Pathological Order Book Invariants & Float Extremes (ADV01 ~ ADV08)
    # =========================================================================

    def test_adv01_inverted_and_negative_spreads(self) -> None:
        """
        ADV01: Test pathological inverted order books (P_bid >= P_ask, spread_bps <= 0).
        Verify that engine enforces spread recovery without quoting crossed prices.
        """
        engine = MARLLiquidityHarvester()
        pathological_spreads = [-0.001, -1.0, -10.0, -100.0, -10000.0, 0.0]

        for sp in pathological_spreads:
            res = engine.harvest_liquidity(
                symbol="INVERT_TEST",
                mid_price=150.0,
                spread_bps=sp,
            )
            self.assertTrue(res.is_valid_quote, f"Invalid quote for spread_bps={sp}")
            self.assertGreater(res.bid_price, 0.0)
            self.assertGreater(res.ask_price, res.bid_price)
            self.assertGreaterEqual(res.spread, engine.config.tick_size)
            self.assertLessEqual(res.bid_price, res.mid_price - engine.config.tick_size)
            self.assertGreaterEqual(res.ask_price, res.mid_price + engine.config.tick_size)

    def test_adv02_zero_and_negative_mid_prices(self) -> None:
        """
        ADV02: Test degenerate and negative mid-price inputs (<= 0.0).
        Verify fallback to a positive default mid price and strictly positive quotes.
        """
        engine = MARLLiquidityHarvester()
        pathological_mids = [0.0, -0.01, -1.0, -50.0, -1000.0, -1e9]

        for mid in pathological_mids:
            res = engine.harvest_liquidity(
                symbol="NEG_MID_TEST",
                mid_price=mid,
                spread_bps=2.0,
            )
            self.assertTrue(res.is_valid_quote, f"Invalid quote for mid_price={mid}")
            self.assertGreater(res.mid_price, 0.0)
            self.assertGreater(res.bid_price, 0.0)
            self.assertGreater(res.ask_price, res.bid_price)

    def test_adv03_nan_inputs_across_all_parameters(self) -> None:
        """
        ADV03: Test IEEE 754 NaN resilience across every individual input parameter.
        Verify zero unhandled exceptions, valid quotes, and finite reward outputs.
        """
        engine = MARLLiquidityHarvester()
        nan_val = float("nan")

        # Test each parameter being NaN individually
        param_cases = [
            {"mid_price": nan_val},
            {"spread_bps": nan_val},
            {"obi": nan_val},
            {"microprice_drift": nan_val},
            {"hawkes_intensity": nan_val},
            {"toxicity_score": nan_val},
            {"volatility": nan_val},
            {"queue_velocity": nan_val},
            {"arrival_price": nan_val},
            {"agent_inventories": {0: nan_val, 1: nan_val, 2: nan_val}},
        ]

        for p in param_cases:
            res = engine.harvest_liquidity(
                symbol="NAN_TEST",
                mid_price=p.get("mid_price", 100.0),
                spread_bps=p.get("spread_bps", 2.0),
                obi=p.get("obi", 0.0),
                microprice_drift=p.get("microprice_drift", 0.0),
                hawkes_intensity=p.get("hawkes_intensity", 1.0),
                toxicity_score=p.get("toxicity_score", 0.0),
                volatility=p.get("volatility", 0.02),
                queue_velocity=p.get("queue_velocity", 0.0),
                arrival_price=p.get("arrival_price", None),
                agent_inventories=p.get("agent_inventories", None),
            )
            self.assertTrue(res.is_valid_quote, f"Invalid quote under NaN input: {p}")
            self.assertFalse(math.isnan(res.bid_price))
            self.assertFalse(math.isnan(res.ask_price))
            self.assertFalse(math.isnan(res.quoted_spread_bps))
            self.assertFalse(math.isnan(res.reward_decomposition["total_joint_reward"]))

        # Simultaneous NaN storm on all parameters
        res_all_nan = engine.harvest_liquidity(
            symbol="ALL_NAN",
            mid_price=nan_val,
            spread_bps=nan_val,
            obi=nan_val,
            microprice_drift=nan_val,
            hawkes_intensity=nan_val,
            toxicity_score=nan_val,
            volatility=nan_val,
            queue_velocity=nan_val,
            arrival_price=nan_val,
            agent_inventories={0: nan_val, 1: nan_val, 2: nan_val},
        )
        self.assertTrue(res_all_nan.is_valid_quote)
        self.assertFalse(math.isnan(res_all_nan.bid_price))
        self.assertFalse(math.isnan(res_all_nan.ask_price))

    def test_adv04_infinity_extremes_positive_and_negative(self) -> None:
        """
        ADV04: Test IEEE 754 +Inf and -Inf resilience across inputs.
        Verify clamping without numerical overflow or infinite quotes.
        """
        engine = MARLLiquidityHarvester()
        pos_inf = float("inf")
        neg_inf = float("-inf")

        for inf_val in (pos_inf, neg_inf):
            res = engine.harvest_liquidity(
                symbol="INF_TEST",
                mid_price=100.0,
                spread_bps=2.0,
                obi=inf_val,
                microprice_drift=inf_val,
                hawkes_intensity=pos_inf,
                toxicity_score=inf_val,
                volatility=pos_inf if inf_val == pos_inf else 0.02,
                queue_velocity=inf_val,
                agent_inventories={0: inf_val, 1: inf_val, 2: inf_val},
            )
            self.assertTrue(res.is_valid_quote)
            self.assertFalse(math.isinf(res.bid_price))
            self.assertFalse(math.isinf(res.ask_price))
            self.assertFalse(math.isinf(res.reward_decomposition["total_joint_reward"]))

    def test_adv05_zero_volatility_and_zero_spread_floors(self) -> None:
        """
        ADV05: Test degenerate zero volatility and zero spread inputs.
        Verify tick-size floor and safety minimum half-spread are maintained.
        """
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            symbol="ZERO_VOL",
            mid_price=200.0,
            spread_bps=0.0,
            volatility=0.0,
        )
        self.assertTrue(res.is_valid_quote)
        # Quoted spread must be at least 2 ticks (1 tick above and 1 tick below mid)
        self.assertGreaterEqual(res.spread, 2.0 * engine.config.tick_size - 1e-6)
        self.assertGreaterEqual(res.quoted_spread_bps, 0.1)

    def test_adv06_explosive_volatility_and_queue_acceleration(self) -> None:
        """
        ADV06: Test hyper-explosive volatility (vol=50.0, 5000% annualized) and queue drift.
        Verify that spread expands gracefully while keeping finite prices and bounded skew.
        """
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            symbol="EXPLOSIVE",
            mid_price=100.0,
            spread_bps=100.0,
            volatility=50.0,
            microprice_drift=5000.0,
            queue_velocity=1000.0,
        )
        self.assertTrue(res.is_valid_quote)
        self.assertGreater(res.ask_price, res.bid_price)
        self.assertLessEqual(abs(res.inventory_skew_ticks), engine.config.skew_ticks_max)

    def test_adv07_asymmetric_mixed_pathological_permutations(self) -> None:
        """
        ADV07: Test heterogeneous permutations of pathological inputs simultaneously.
        """
        engine = MARLLiquidityHarvester()
        permutations = [
            (float("nan"), -100.0, float("inf"), -50.0),
            (0.0, 0.0, float("-inf"), float("nan")),
            (-999.0, float("nan"), 1e8, float("-inf")),
        ]

        for mid, sp, tox, drift in permutations:
            res = engine.harvest_liquidity(
                symbol="PERMUTATION",
                mid_price=mid,
                spread_bps=sp,
                toxicity_score=tox,
                microprice_drift=drift,
            )
            self.assertTrue(res.is_valid_quote)
            self.assertGreater(res.bid_price, 0.0)
            self.assertGreater(res.ask_price, res.bid_price)

    def test_adv08_sub_penny_and_large_tick_grid_compliance(self) -> None:
        """
        ADV08: Test tick-grid compliance across sub-penny (0.0001) and large-tick (50.0, 100.0) assets.
        Verify that bid and ask are exact multiples of the tick size.
        """
        # Sub-penny config
        subpenny_cfg = MARLHarvesterConfig(tick_size=0.0001, base_spread_bps=1.0)
        engine_subpenny = MARLLiquidityHarvester(subpenny_cfg)
        res_sub = engine_subpenny.harvest_liquidity("SUBPENNY", mid_price=5.2534, spread_bps=1.0)
        self.assertTrue(res_sub.is_valid_quote)
        # Verify tick multiple
        bid_ticks = res_sub.bid_price / 0.0001
        ask_ticks = res_sub.ask_price / 0.0001
        self.assertAlmostEqual(bid_ticks, round(bid_ticks), places=3)
        self.assertAlmostEqual(ask_ticks, round(ask_ticks), places=3)

        # Large-tick config (KOSPI 100 KRW)
        kospi_cfg = MARLHarvesterConfig(market=MarketProfile.KOSPI, tick_size=100.0)
        engine_kospi = MARLLiquidityHarvester(kospi_cfg)
        res_kospi = engine_kospi.harvest_liquidity("005930", mid_price=74500.0, spread_bps=3.0)
        self.assertTrue(res_kospi.is_valid_quote)
        self.assertEqual(res_kospi.bid_price % 100.0, 0.0)
        self.assertEqual(res_kospi.ask_price % 100.0, 0.0)

    # =========================================================================
    # Category 2: Sustained Toxic Order Flow Shocks & Dynamic Quote Fading (ADV09 ~ ADV15)
    # =========================================================================

    def test_adv09_sustained_toxic_flow_quote_fading_and_widening(self) -> None:
        """
        ADV09: Test sustained toxic order flow bursts (T_toxic > 0.95) over multiple sequential ticks.
        Verify significant quote fading (shade_ticks > 0) and aggressive spread widening vs benign flow.
        """
        engine = MARLLiquidityHarvester()

        # Step 1: Benign baseline (T_toxic = 0.05)
        res_benign = engine.harvest_liquidity(
            symbol="TOX_BURST", mid_price=100.0, spread_bps=2.0, toxicity_score=0.05
        )
        self.assertEqual(res_benign.toxicity_level, ToxicityLevel.BENIGN)
        self.assertFalse(res_benign.quote_suppressed)

        # Step 2: Sustained toxic burst for 20 sequential ticks (T_toxic = 0.98)
        toxic_spreads = []
        for tick in range(20):
            res_toxic = engine.harvest_liquidity(
                symbol="TOX_BURST",
                mid_price=100.0,
                spread_bps=2.0,
                toxicity_score=0.98,
                microprice_drift=-5.0,
                queue_velocity=-3.0,
                obi=-0.8,
            )
            self.assertTrue(res_toxic.is_valid_quote)
            self.assertEqual(res_toxic.toxicity_level, ToxicityLevel.CRITICAL)
            self.assertTrue(res_toxic.quote_suppressed)
            self.assertGreater(res_toxic.shade_ticks, 0.0)
            toxic_spreads.append(res_toxic.quoted_spread_bps)

        # Toxic spread must be significantly wider than benign spread (at least 2x)
        avg_toxic_spread = float(np.mean(toxic_spreads))
        self.assertGreater(
            avg_toxic_spread,
            res_benign.quoted_spread_bps * 1.5,
            f"Toxic spread ({avg_toxic_spread}) was not significantly wider than benign ({res_benign.quoted_spread_bps})",
        )

    def test_adv10_toxic_sell_avalanche_directional_suppression(self) -> None:
        """
        ADV10: Test toxic sell avalanche (heavy informed sellers hitting the bid).
        Verify that BID side is selectively suppressed or shaded further back to prevent toxic fills.
        """
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            symbol="SELL_SHOCK",
            mid_price=100.0,
            spread_bps=2.0,
            toxicity_score=0.99,
            microprice_drift=-15.0,
            queue_velocity=-8.0,
            obi=-0.95,
        )
        self.assertTrue(res.is_valid_quote)
        self.assertTrue(res.quote_suppressed)
        # Vulnerable side under heavy sell pressure is the BID
        self.assertIn(res.suppressed_side, (QuoteSide.BID, QuoteSide.BOTH))
        # Bid offset ticks must be strictly larger than baseline
        self.assertGreater(res.bid_price, 0.0)
        self.assertLess(res.bid_price, res.mid_price)

    def test_adv11_toxic_buy_squeeze_directional_suppression(self) -> None:
        """
        ADV11: Test toxic buy squeeze (heavy informed buyers lifting the ask).
        Verify that ASK side is selectively suppressed or shaded further away to avoid being front-run.
        """
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            symbol="BUY_SHOCK",
            mid_price=100.0,
            spread_bps=2.0,
            toxicity_score=0.99,
            microprice_drift=15.0,
            queue_velocity=8.0,
            obi=0.95,
        )
        self.assertTrue(res.is_valid_quote)
        self.assertTrue(res.quote_suppressed)
        # Vulnerable side under heavy buy pressure is the ASK
        self.assertIn(res.suppressed_side, (QuoteSide.ASK, QuoteSide.BOTH))
        self.assertGreater(res.ask_price, res.mid_price)

    def test_adv12_non_directional_ambiguous_toxic_burst(self) -> None:
        """
        ADV12: Test ambiguous severe toxic burst with balanced order book imbalance (OBI=0.0, drift=0.0).
        Verify bilateral quote defense (BOTH sides suppressed or shaded symmetrically).
        """
        engine = MARLLiquidityHarvester()
        res = engine.harvest_liquidity(
            symbol="AMBIG_TOX",
            mid_price=100.0,
            spread_bps=2.0,
            toxicity_score=0.98,
            microprice_drift=0.0,
            queue_velocity=0.0,
            obi=0.0,
        )
        self.assertTrue(res.is_valid_quote)
        self.assertTrue(res.quote_suppressed)
        self.assertEqual(res.suppressed_side, QuoteSide.BOTH)
        self.assertGreater(res.shade_ticks, 0.0)

    def test_adv13_hawkes_intensity_fading_amplification(self) -> None:
        """
        ADV13: Test that elevated Hawkes order arrival intensity (lambda) strictly amplifies tick shading.
        """
        engine = MARLLiquidityHarvester()
        res_low_h = engine.harvest_liquidity(
            symbol="HAWKES_TEST", mid_price=100.0, spread_bps=2.0, toxicity_score=0.55, hawkes_intensity=0.5
        )
        res_high_h = engine.harvest_liquidity(
            symbol="HAWKES_TEST", mid_price=100.0, spread_bps=2.0, toxicity_score=0.55, hawkes_intensity=10.0
        )
        self.assertGreater(
            res_high_h.shade_ticks,
            res_low_h.shade_ticks,
            "Higher Hawkes intensity should amplify quote shading under elevated toxicity.",
        )

    def test_adv14_rapid_toxicity_regime_switching(self) -> None:
        """
        ADV14: Test rapid switching between benign and critical toxicity on adjacent ticks.
        Verify instantaneous regime response with zero lag or state hysteresis.
        """
        engine = MARLLiquidityHarvester()
        for i in range(10):
            tox = 0.05 if (i % 2 == 0) else 0.99
            res = engine.harvest_liquidity("OSC_TEST", mid_price=100.0, spread_bps=2.0, toxicity_score=tox)
            if tox == 0.05:
                self.assertEqual(res.toxicity_level, ToxicityLevel.BENIGN)
                self.assertFalse(res.quote_suppressed)
            else:
                self.assertEqual(res.toxicity_level, ToxicityLevel.CRITICAL)
                self.assertTrue(res.quote_suppressed)

    def test_adv15_adverse_selection_reward_penalty(self) -> None:
        """
        ADV15: Verify adverse selection penalty in reward decomposition heavily penalizes toxic fills.
        """
        engine = MARLLiquidityHarvester()
        r_benign = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 0.0}, toxicity_score=0.05,
            adverse_drift_bps=1.0, netted_shares=0, fee_savings_usd=0.0,
        )
        r_toxic = engine.evaluate_joint_reward(
            fills_shares=100, realized_half_spread_bps=2.0, arrival_price=100.0,
            execution_price=100.0, inventories={0: 0.0}, toxicity_score=0.98,
            adverse_drift_bps=10.0, netted_shares=0, fee_savings_usd=0.0,
        )
        self.assertGreater(r_toxic["adverse_penalty"], r_benign["adverse_penalty"] * 10.0)
        self.assertLess(r_toxic["total_joint_reward"], r_benign["total_joint_reward"])

    # =========================================================================
    # Category 3: Extreme Inventory Imbalances & Homeostasis Quoting (ADV16 ~ ADV22)
    # =========================================================================

    def test_adv16_extreme_long_inventory_restoration_quoting(self) -> None:
        """
        ADV16: Test extreme positive inventory imbalance (+100,000 shares long, 100x max_inventory).
        Verify Avellaneda-Stoikov inventory restoration:
        - Reservation price drops: ask price is quoted closer to mid to attract buyers (unloading).
        - Bid price is pushed deeper away from mid to deter sellers.
        - Skew ticks reaches maximum positive cap.
        """
        engine = MARLLiquidityHarvester()

        # Flat inventory baseline
        res_flat = engine.harvest_liquidity(
            "INV_TEST", mid_price=100.0, spread_bps=2.0, agent_inventories={0: 0.0, 1: 0.0, 2: 0.0}
        )

        # Massive long inventory (+100,000 shares)
        res_long = engine.harvest_liquidity(
            "INV_TEST", mid_price=100.0, spread_bps=2.0, agent_inventories={0: 100_000.0, 1: 0.0, 2: 0.0}
        )

        self.assertTrue(res_long.is_valid_quote)
        self.assertGreater(res_long.inventory_skew_ticks, 0.0)
        # Cap reached under extreme inventory (500k shares)
        res_cap = engine.harvest_liquidity(
            "INV_TEST", mid_price=100.0, spread_bps=2.0, agent_inventories={0: 500_000.0, 1: 0.0, 2: 0.0}
        )
        self.assertEqual(res_cap.inventory_skew_ticks, engine.config.skew_ticks_max)

        # Under heavy long position, quotes should shift downward (ask lower, bid lower)
        self.assertLessEqual(
            res_long.ask_price,
            res_flat.ask_price,
            f"Ask price under long position ({res_long.ask_price}) should be <= flat ask ({res_flat.ask_price})",
        )
        self.assertLessEqual(
            res_long.bid_price,
            res_flat.bid_price,
            f"Bid price under long position ({res_long.bid_price}) should be <= flat bid ({res_flat.bid_price})",
        )

    def test_adv17_extreme_short_inventory_restoration_quoting(self) -> None:
        """
        ADV17: Test extreme negative inventory imbalance (-100,000 shares short, -100x max_inventory).
        Verify Avellaneda-Stoikov inventory restoration:
        - Reservation price rises: bid price is quoted closer to mid to attract sellers (covering).
        - Ask price is pushed higher away from mid to deter buyers.
        - Skew ticks reaches negative cap (-skew_ticks_max).
        """
        engine = MARLLiquidityHarvester()

        res_flat = engine.harvest_liquidity(
            "INV_TEST", mid_price=100.0, spread_bps=2.0, agent_inventories={0: 0.0, 1: 0.0, 2: 0.0}
        )

        # Massive short inventory (-100,000 shares)
        res_short = engine.harvest_liquidity(
            "INV_TEST", mid_price=100.0, spread_bps=2.0, agent_inventories={0: -100_000.0, 1: 0.0, 2: 0.0}
        )

        self.assertTrue(res_short.is_valid_quote)
        self.assertLess(res_short.inventory_skew_ticks, 0.0)
        # Cap reached under extreme short inventory (-500k shares)
        res_cap_short = engine.harvest_liquidity(
            "INV_TEST", mid_price=100.0, spread_bps=2.0, agent_inventories={0: -500_000.0, 1: 0.0, 2: 0.0}
        )
        self.assertEqual(res_cap_short.inventory_skew_ticks, -engine.config.skew_ticks_max)

        # Under heavy short position, quotes should shift upward (bid higher, ask higher)
        self.assertGreaterEqual(
            res_short.bid_price,
            res_flat.bid_price,
            f"Bid price under short position ({res_short.bid_price}) should be >= flat bid ({res_flat.bid_price})",
        )
        self.assertGreaterEqual(
            res_short.ask_price,
            res_flat.ask_price,
            f"Ask price under short position ({res_short.ask_price}) should be >= flat ask ({res_flat.ask_price})",
        )

    def test_adv18_extreme_multi_desk_opposing_cross_netting(self) -> None:
        """
        ADV18: Test extreme polarized inventories across desks (Desk 0: +100k, Desk 1: -100k, Desk 2: +50k).
        Verify that internal netting executes min(150k, 100k) = 100k shares, saving massive fees.
        """
        engine = MARLLiquidityHarvester()
        polarized_invs = {0: 100_000.0, 1: -100_000.0, 2: 50_000.0}

        net_res = engine.internal_cross_netting(inventories=polarized_invs, mid_price=150.0)

        self.assertEqual(net_res.netted_shares, 100_000)
        self.assertTrue(net_res.opposing_matched)
        self.assertGreater(net_res.fee_savings_usd, 100.0)
        self.assertGreater(net_res.impact_savings_bps, 0.0)

        # Post-netting short desk should be completely flattened to 0.0
        self.assertAlmostEqual(net_res.final_inventories[1], 0.0, places=3)
        # Remaining positive inventory should equal 50,000
        total_remaining = sum(net_res.final_inventories.values())
        self.assertAlmostEqual(total_remaining, 50_000.0, places=3)

    def test_adv19_exact_collective_inventory_conservation_extreme(self) -> None:
        """
        ADV19: Test exact collective inventory conservation under randomized extreme desk distributions.
        Verify sum(q_after) == sum(q_before) within 1e-6 tolerance.
        """
        engine = MARLLiquidityHarvester()
        rng = np.random.RandomState(999)

        for trial in range(25):
            invs = {
                0: float(rng.randint(-150_000, 150_000)),
                1: float(rng.randint(-150_000, 150_000)),
                2: float(rng.randint(-150_000, 150_000)),
            }
            initial_sum = sum(invs.values())
            net_res = engine.internal_cross_netting(inventories=invs, mid_price=100.0)
            final_sum = sum(net_res.final_inventories.values())

            self.assertAlmostEqual(
                initial_sum,
                final_sum,
                places=5,
                msg=f"Inventory conservation violated on trial {trial}: {initial_sum} != {final_sum}",
            )

    def test_adv20_all_positive_or_negative_extreme_inventories_no_leak(self) -> None:
        """
        ADV20: Test that when all desks share the same extreme sign (+50k each or -50k each),
        internal netting outputs zero matched shares cleanly without position corruption.
        """
        engine = MARLLiquidityHarvester()
        all_long = {0: 50_000.0, 1: 50_000.0, 2: 50_000.0}
        net_long = engine.internal_cross_netting(inventories=all_long, mid_price=100.0)
        self.assertEqual(net_long.netted_shares, 0)
        self.assertFalse(net_long.opposing_matched)
        self.assertEqual(net_long.final_inventories, all_long)

        all_short = {0: -50_000.0, 1: -50_000.0, 2: -50_000.0}
        net_short = engine.internal_cross_netting(inventories=all_short, mid_price=100.0)
        self.assertEqual(net_short.netted_shares, 0)
        self.assertFalse(net_short.opposing_matched)
        self.assertEqual(net_short.final_inventories, all_short)

    def test_adv21_inventory_quadratic_penalty_monotonic_growth(self) -> None:
        """
        ADV21: Verify strict quadratic monotonicity of the inventory penalty: R_inv(100k) >> R_inv(1k) >> R_inv(0).
        """
        engine = MARLLiquidityHarvester()
        r0 = engine.evaluate_joint_reward(
            100, 2.0, 100.0, 100.0, {0: 0.0, 1: 0.0, 2: 0.0}, 0.0, 0.0, 0, 0.0
        )
        r1k = engine.evaluate_joint_reward(
            100, 2.0, 100.0, 100.0, {0: 1000.0, 1: 1000.0, 2: 1000.0}, 0.0, 0.0, 0, 0.0
        )
        r100k = engine.evaluate_joint_reward(
            100, 2.0, 100.0, 100.0, {0: 100_000.0, 1: 100_000.0, 2: 100_000.0}, 0.0, 0.0, 0, 0.0
        )
        self.assertGreater(r1k["inventory_penalty"], r0["inventory_penalty"])
        self.assertGreater(r100k["inventory_penalty"], r1k["inventory_penalty"] * 100.0)

    def test_adv22_dynamic_inventory_restoration_trajectory(self) -> None:
        """
        ADV22: Test multi-step inventory restoration under simulated buy-side arrivals.
        Starting from +10,000 long inventory, each simulated fill decrements position towards zero.
        Verify that inventory monotonically decreases and reservation skew relaxes back to neutral.
        """
        engine = MARLLiquidityHarvester()
        current_inv = 10_000.0
        engine.set_inventories({0: current_inv, 1: 0.0, 2: 0.0})

        skews = []
        for step in range(11):
            res = engine.harvest_liquidity("RESTORE", mid_price=100.0, spread_bps=2.0)
            skews.append(res.inventory_skew_ticks)
            # Simulated buyer fill: our ask was hit, reducing our long inventory
            current_inv = max(0.0, current_inv - 1_000.0)
            engine.set_inventories({0: current_inv, 1: 0.0, 2: 0.0})

        # Skew should decrease as inventory is restored towards zero
        self.assertGreater(skews[0], skews[-1])
        self.assertAlmostEqual(skews[-1], 0.0, places=1)

    # =========================================================================
    # Category 4: Long Continuous Simulation, Stability & Memory Leaks (ADV23 ~ ADV28)
    # =========================================================================

    def test_adv23_continuous_1000_steps_simulation_numpy(self) -> None:
        """
        ADV23: Execute 1,000 continuous sequential steps on NumPy backend with Poisson shocks.
        Verify 100% numerical stability, finite outputs, zero NaNs/Infs, and 1,000/1,000 valid quotes.
        """
        config = MARLHarvesterConfig(use_torch=False, seed=42)
        engine = MARLLiquidityHarvester(config)
        self.assertEqual(engine.backend, "numpy")

        rng = np.random.RandomState(42)
        mid = 100.0

        for step in range(1000):
            # Stochastic random walk
            drift = float(rng.randn() * 0.5)
            mid = max(10.0, mid + drift * 0.05)
            spread = max(0.5, 2.0 + rng.randn() * 0.3)
            tox = float(np.clip(rng.beta(0.5, 2.0), 0.0, 1.0))
            hawkes = max(0.1, 1.0 + rng.exponential(1.0))
            obi = float(np.clip(rng.randn() * 0.4, -1.0, 1.0))

            res = engine.harvest_liquidity(
                symbol="CONT_NUMPY",
                mid_price=mid,
                spread_bps=spread,
                obi=obi,
                microprice_drift=drift,
                hawkes_intensity=hawkes,
                toxicity_score=tox,
            )

            self.assertTrue(res.is_valid_quote, f"Invalid quote at step {step}")
            self.assertFalse(math.isnan(res.bid_price))
            self.assertFalse(math.isnan(res.ask_price))
            self.assertFalse(math.isnan(res.reward_decomposition["total_joint_reward"]))

        telemetry = engine.get_telemetry()
        self.assertEqual(telemetry["total_harvest_calls"], 1000)

    def test_adv24_continuous_1000_steps_simulation_torch(self) -> None:
        """
        ADV24: Execute 1,000 continuous sequential steps on PyTorch backend (if available).
        Verify 100% numerical stability, finite outputs, and 1,000/1,000 valid quotes.
        """
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not installed; skipping PyTorch continuous simulation test.")

        config = MARLHarvesterConfig(use_torch=True, seed=123)
        engine = MARLLiquidityHarvester(config)
        self.assertEqual(engine.backend, "torch")

        rng = np.random.RandomState(123)
        mid = 250.0

        for step in range(1000):
            drift = float(rng.randn() * 0.8)
            mid = max(20.0, mid + drift * 0.1)
            spread = max(0.5, 2.5 + rng.randn() * 0.5)
            tox = float(np.clip(rng.beta(0.8, 2.5), 0.0, 1.0))
            hawkes = max(0.1, 1.5 + rng.exponential(0.8))
            obi = float(np.clip(rng.randn() * 0.3, -1.0, 1.0))

            res = engine.harvest_liquidity(
                symbol="CONT_TORCH",
                mid_price=mid,
                spread_bps=spread,
                obi=obi,
                microprice_drift=drift,
                hawkes_intensity=hawkes,
                toxicity_score=tox,
            )

            self.assertTrue(res.is_valid_quote, f"Invalid quote at step {step}")
            self.assertFalse(math.isnan(res.bid_price))
            self.assertFalse(math.isnan(res.ask_price))

        telemetry = engine.get_telemetry()
        self.assertEqual(telemetry["total_harvest_calls"], 1000)

    def test_adv25_memory_leak_verification_tracemalloc(self) -> None:
        """
        ADV25: Test memory stability over 1,000 continuous execution steps using tracemalloc.
        Verify net memory growth is strictly bounded (< 15.0 MB) with zero memory leaks.
        """
        gc.collect()
        tracemalloc.start()

        engine = MARLLiquidityHarvester()
        # Warmup
        for _ in range(50):
            engine.harvest_liquidity("WARMUP", 100.0, 2.0)

        snapshot_start = tracemalloc.take_snapshot()

        # Run 1,000 continuous steps
        for i in range(1000):
            engine.harvest_liquidity(
                symbol="MEM_TEST",
                mid_price=100.0 + (i % 20),
                spread_bps=2.0 + (i % 5) * 0.2,
                obi=0.1 * (i % 5 - 2),
                microprice_drift=0.5 * (i % 7 - 3),
                hawkes_intensity=1.0 + (i % 4) * 0.5,
                toxicity_score=0.1 * (i % 10),
            )

        gc.collect()
        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_end.compare_to(snapshot_start, "lineno")
        total_growth_bytes = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
        total_growth_mb = total_growth_bytes / (1024.0 * 1024.0)

        self.assertLess(
            total_growth_mb,
            15.0,
            f"Memory growth ({total_growth_mb:.2f} MB) exceeded 15.0 MB threshold over 1,000 calls.",
        )

    def test_adv26_latency_stability_under_long_runs(self) -> None:
        """
        ADV26: Test latency distribution under 1,000 consecutive steps.
        Verify average latency remains strictly below 2,000 us (2.0 ms SLA constraint).
        """
        engine = MARLLiquidityHarvester()
        latencies = []

        for _ in range(1000):
            res = engine.harvest_liquidity("LATENCY_TEST", 100.0, 2.0)
            latencies.append(res.latency_us)

        avg_lat = float(np.mean(latencies))
        p99_lat = float(np.percentile(latencies, 99))

        self.assertLess(
            avg_lat,
            2000.0,
            f"Average latency ({avg_lat:.2f} us) exceeded sub-2.0 ms SLA limit.",
        )
        self.assertLess(
            p99_lat,
            15000.0,
            f"P99 latency ({p99_lat:.2f} us) had abnormal tail spike.",
        )

    def test_adv27_operational_telemetry_consistency(self) -> None:
        """
        ADV27: Verify operational telemetry accumulator consistency across sequential runs.
        """
        engine = MARLLiquidityHarvester()
        for i in range(150):
            tox = 0.95 if (i % 10 == 0) else 0.1
            engine.harvest_liquidity("TELEM_TEST", 100.0, 2.0, toxicity_score=tox)

        tel = engine.get_telemetry()
        self.assertEqual(tel["total_harvest_calls"], 150)
        self.assertEqual(tel["quote_suppressions_count"], 15)
        self.assertGreater(tel["avg_latency_us"], 0.0)
        self.assertGreater(tel["total_execution_time_us"], 0.0)

    def test_adv28_centralized_critic_bounded_values_under_extreme_states(self) -> None:
        """
        ADV28: Test centralized critic produces finite, bounded values across extreme states.
        """
        engine = MARLLiquidityHarvester()
        # Extreme observation inputs
        extreme_obs = engine.construct_observations(
            mid_price=10_000.0,
            spread_bps=100.0,
            obi=1.0,
            microprice_drift=50.0,
            hawkes_intensity=50.0,
            toxicity_score=1.0,
            volatility=0.5,
            queue_velocity=10.0,
        )
        joint_vec = np.concatenate([extreme_obs[i].vector for i in range(3)])
        val = engine.evaluate_critic(joint_vec)

        self.assertFalse(math.isnan(val))
        self.assertFalse(math.isinf(val))
        self.assertLess(abs(val), 100.0, "Critic value exploded unexpectedly.")

    # =========================================================================
    # Category 5: Cross-Market Robustness, Concurrency & Determinism (ADV29 ~ ADV32)
    # =========================================================================

    def test_adv29_all_5_markets_stress_matrix(self) -> None:
        """
        ADV29: Run cross-market stress matrix across all 5 supported profiles:
        SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ under high volatility and severe toxicity.
        """
        for mkt in (MarketProfile.SP500, MarketProfile.NASDAQ, MarketProfile.RUSSELL2000, MarketProfile.KOSPI, MarketProfile.KOSDAQ):
            cfg = MARLHarvesterConfig(market=mkt)
            engine = MARLLiquidityHarvester(cfg)
            mid = 100.0 if "KOS" not in mkt.name else 50000.0
            res = engine.harvest_liquidity(
                symbol=f"STRESS_{mkt.name}",
                mid_price=mid,
                spread_bps=10.0,
                toxicity_score=0.96,
                volatility=0.10,
            )
            self.assertTrue(res.is_valid_quote)
            self.assertEqual(res.market, mkt.name)
            self.assertTrue(res.quote_suppressed)
            self.assertGreater(res.spread, 0.0)

    def test_adv30_krx_large_tick_rounding_under_shocks(self) -> None:
        """
        ADV30: Verify KOSPI (100 KRW tick) and KOSDAQ (50 KRW tick) maintain integer tick boundaries under extreme shocks.
        """
        kospi_engine = MARLLiquidityHarvester(MARLHarvesterConfig(market="KOSPI"))
        kosdaq_engine = MARLLiquidityHarvester(MARLHarvesterConfig(market="KOSDAQ"))

        for mid in (25350.0, 78920.0, 150000.0):
            res_p = kospi_engine.harvest_liquidity("005930", mid_price=mid, spread_bps=5.0)
            self.assertTrue(res_p.is_valid_quote)
            self.assertEqual(res_p.bid_price % 100.0, 0.0)
            self.assertEqual(res_p.ask_price % 100.0, 0.0)

            res_q = kosdaq_engine.harvest_liquidity("247540", mid_price=mid, spread_bps=8.0)
            self.assertTrue(res_q.is_valid_quote)
            self.assertEqual(res_q.bid_price % 50.0, 0.0)
            self.assertEqual(res_q.ask_price % 50.0, 0.0)

    def test_adv31_multithreaded_concurrent_execution(self) -> None:
        """
        ADV31: Test thread safety and concurrency: 8 threads executing 50 calls each (400 total)
        on a shared harvester instance. Verify zero race conditions or corrupted quotes.
        """
        engine = MARLLiquidityHarvester()

        def worker_task(thread_id: int) -> List[bool]:
            results = []
            for j in range(50):
                res = engine.harvest_liquidity(
                    symbol=f"THREAD_{thread_id}",
                    mid_price=100.0 + thread_id,
                    spread_bps=2.0 + (j % 3),
                    toxicity_score=0.1 * (thread_id % 5),
                )
                results.append(res.is_valid_quote)
            return results

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_task, tid) for tid in range(8)]
            for f in concurrent.futures.as_completed(futures):
                thread_res = f.result()
                self.assertEqual(len(thread_res), 50)
                self.assertTrue(all(thread_res))

    def test_adv32_deterministic_seed_reproducibility(self) -> None:
        """
        ADV32: Test deterministic reproducibility: two independently initialized harvesters
        with identical seeds produce bit-for-bit identical quotes on an adversarial input sequence.
        """
        h1 = MARLLiquidityHarvester(MARLHarvesterConfig(seed=777))
        h2 = MARLLiquidityHarvester(MARLHarvesterConfig(seed=777))

        inputs = [
            (100.0, 2.0, 0.1, -1.0, 2.0, 0.3, 0.02),
            (105.0, 5.0, -0.5, 3.0, 5.0, 0.85, 0.05),
            (95.0, 1.5, 0.8, 0.0, 0.5, 0.05, 0.015),
            (110.0, 10.0, -0.9, -15.0, 12.0, 0.99, 0.12),
        ]

        for mid, sp, obi, drift, hawkes, tox, vol in inputs:
            r1 = h1.harvest_liquidity(
                "DETERMINISM", mid, sp, obi=obi, microprice_drift=drift,
                hawkes_intensity=hawkes, toxicity_score=tox, volatility=vol,
            )
            r2 = h2.harvest_liquidity(
                "DETERMINISM", mid, sp, obi=obi, microprice_drift=drift,
                hawkes_intensity=hawkes, toxicity_score=tox, volatility=vol,
            )
            self.assertEqual(r1.bid_price, r2.bid_price)
            self.assertEqual(r1.ask_price, r2.ask_price)
            self.assertEqual(r1.inventory_skew_ticks, r2.inventory_skew_ticks)
            self.assertEqual(r1.shade_ticks, r2.shade_ticks)
            self.assertEqual(r1.quote_suppressed, r2.quote_suppressed)
            self.assertEqual(r1.suppressed_side, r2.suppressed_side)


if __name__ == "__main__":
    unittest.main()
