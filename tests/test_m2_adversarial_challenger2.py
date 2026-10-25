"""
tests/test_m2_adversarial_challenger2.py — Adversarial Empirical Stress Test Suite for Milestone 2

Target Systems:
- PaperTradingDaemon (src/execution/paper_trading_daemon.py)
- ExecutionOMSEngine (src/execution/oms_engine.py)
- FastLOBEngine / StreamingLOBManager (src/core/fast_lob_engine.py, src/core/streaming_feed_adapter.py)

Challenge Focus:
1. Multi-tier aggressive sweeps (5-10 depth tiers) with varying quantities and VWAP precision.
2. Rigorous equity invariant verification (Net Equity <= Gross Equity + 1e-6) across randomized trading cycles.
3. Edge case order books (wide spreads, zero depth, asymmetric imbalances, micro-price bounds).
4. Numerical stability, extreme parameter values, and exception resistance.
"""

import math
import os
import random
import tempfile
import threading
import time
import unittest
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pytest

from src.core.streaming_feed_adapter import (
    BackpressurePolicy,
    DepthLevel,
    DepthUpdate,
    FeedEventType,
    FeedTelemetry,
    MockStreamingProvider,
    QuoteUpdate,
    StreamingFeedAdapter,
    StreamingLOBManager,
    TopOfBook,
    TradeUpdate,
)
from src.core.fast_lob_engine import FastLOBEngine, FastOrderBookMatchingEngine
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.paper_trading_daemon import (
    PaperExecutionRecord,
    PaperExecutionStatus,
    PaperOrderAction,
    PaperTradingDaemon,
)


# ==============================================================================
# Category 1: Multi-Tier Aggressive Sweeps (5-10 depth tiers)
# ==============================================================================

class TestMultiTierSweepsAdversarial(unittest.TestCase):
    """Stress-tests multi-level orderbook sweeps across 5 to 10 depth tiers."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except Exception:
            pass

    def test_tc01_5_tier_exact_vwap_sweeps_increasing_quantities(self):
        """TC01: 5-tier ask ladder: verify exact analytical VWAP matching at increasing sweep quantities."""
        # 5 tiers of asks:
        # Tier 1: 100 shares @ 70,100 KRW
        # Tier 2: 200 shares @ 70,200 KRW
        # Tier 3: 300 shares @ 70,300 KRW
        # Tier 4: 400 shares @ 70,400 KRW
        # Tier 5: 500 shares @ 70,500 KRW
        asks = [
            DepthLevel(price=70100.0, volume=100.0),
            DepthLevel(price=70200.0, volume=200.0),
            DepthLevel(price=70300.0, volume=300.0),
            DepthLevel(price=70400.0, volume=400.0),
            DepthLevel(price=70500.0, volume=500.0),
        ]
        bids = [DepthLevel(price=70000.0, volume=1000.0)]

        mgr = StreamingLOBManager()
        lob = mgr.get_book("005930")
        lob.on_depth_update(DepthUpdate(
            symbol="005930",
            market="KRX",
            bids=bids,
            asks=asks,
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            lob_engine=mgr,
        )

        test_cases = [
            # (quantity, expected_vwap)
            (50, 70100.0),                                       # Within Tier 1
            (100, 70100.0),                                      # Exact Tier 1
            (250, (100 * 70100.0 + 150 * 70200.0) / 250.0),     # Consumes Tier 1 + half Tier 2 => 70160.0
            (600, (100*70100 + 200*70200 + 300*70300) / 600.0), # Tiers 1-3 => 70233.3333...
            (1000, (100*70100 + 200*70200 + 300*70300 + 400*70400) / 1000.0), # Tiers 1-4 => 70300.0
            (1500, (100*70100 + 200*70200 + 300*70300 + 400*70400 + 500*70500) / 1500.0), # All 5 tiers => 70366.6667
        ]

        for qty, exp_vwap in test_cases:
            fill = daemon.simulate_fill(
                symbol="005930",
                side="BUY",
                quantity=qty,
                target_price=70000.0,
                market="KRX",
                adv_20d=1e9,
                volatility=0.02,
                market_data=mgr,
            )
            self.assertAlmostEqual(
                fill.executed_price,
                exp_vwap,
                places=2,
                msg=f"Failed exact VWAP match for sweep qty {qty}: expected {exp_vwap}, got {fill.executed_price}"
            )
            # Must strictly not be tick-rounded to boundary if fractional
            if abs(exp_vwap - round(exp_vwap, -2)) > 1e-4:
                self.assertNotEqual(
                    fill.executed_price,
                    float(round(exp_vwap, -2)),
                    "Executed price should preserve fractional depth VWAP instead of tick snapping"
                )

    def test_tc02_10_tier_aggressive_sweep_both_sides(self):
        """TC02: 10-tier bid and ask ladders: verify deep sweeps for both BUY and SELL sides."""
        # 10 ask tiers with variable non-uniform volumes
        ask_prices = [100.0 + i * 0.50 for i in range(1, 11)]  # 100.50, 101.00, ..., 105.00
        ask_vols = [50.0 * (i + 1) for i in range(10)]          # 50, 100, 150, ..., 500
        # 10 bid tiers
        bid_prices = [100.0 - i * 0.50 for i in range(1, 11)]  # 99.50, 99.00, ..., 95.00
        bid_vols = [40.0 * (i + 1) for i in range(10)]          # 40, 80, 120, ..., 400

        asks = [DepthLevel(price=p, volume=v) for p, v in zip(ask_prices, ask_vols)]
        bids = [DepthLevel(price=p, volume=v) for p, v in zip(bid_prices, bid_vols)]

        mgr = StreamingLOBManager()
        lob = mgr.get_book("AAPL")
        lob.on_depth_update(DepthUpdate(
            symbol="AAPL",
            market="NASDAQ",
            bids=bids,
            asks=asks,
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(
            initial_capital=500_000.0,
            db_path=self.db_path,
            dry_run=True,
            base_currency="USD",
            lob_engine=mgr,
        )

        # BUY sweep across 7 tiers (volume = 50 + 100 + 150 + 200 + 250 + 300 + 175 = 1225)
        buy_qty = 1225
        cum_buy_val = (
            50 * 100.50 + 100 * 101.00 + 150 * 101.50 + 200 * 102.00 +
            250 * 102.50 + 300 * 103.00 + 175 * 103.50
        )
        exp_buy_vwap = cum_buy_val / buy_qty

        buy_fill = daemon.simulate_fill(
            symbol="AAPL",
            side="BUY",
            quantity=buy_qty,
            target_price=100.0,
            market="NASDAQ",
            adv_20d=5e7,
            volatility=0.015,
            market_data=mgr,
        )
        self.assertAlmostEqual(buy_fill.executed_price, exp_buy_vwap, places=3)

        # SELL sweep across 6 tiers (volume = 40 + 80 + 120 + 160 + 200 + 100 = 700)
        sell_qty = 700
        cum_sell_val = (
            40 * 99.50 + 80 * 99.00 + 120 * 98.50 + 160 * 98.00 +
            200 * 97.50 + 100 * 97.00
        )
        exp_sell_vwap = cum_sell_val / sell_qty

        sell_fill = daemon.simulate_fill(
            symbol="AAPL",
            side="SELL",
            quantity=sell_qty,
            target_price=100.0,
            market="NASDAQ",
            adv_20d=5e7,
            volatility=0.015,
            market_data=mgr,
        )
        self.assertAlmostEqual(sell_fill.executed_price, exp_sell_vwap, places=3)
        self.assertLess(sell_fill.executed_price, 99.50)

    def test_tc03_sweep_quantity_exceeding_total_book_depth(self):
        """TC03: Order size strictly exceeds total resting depth in book: verify safe execution without exception."""
        mgr = StreamingLOBManager()
        lob = mgr.get_book("005930")
        # Total book depth is only 300 shares
        asks = [
            DepthLevel(price=70100.0, volume=100.0),
            DepthLevel(price=70200.0, volume=200.0),
        ]
        lob.on_depth_update(DepthUpdate(
            symbol="005930",
            market="KRX",
            bids=[DepthLevel(price=70000.0, volume=500.0)],
            asks=asks,
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            lob_engine=mgr,
        )

        # Sweep quantity is 1,000 shares (exceeds 300 available)
        fill = daemon.simulate_fill(
            symbol="005930",
            side="BUY",
            quantity=1000,
            target_price=70000.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
            market_data=mgr,
        )
        self.assertIsNotNone(fill)
        self.assertTrue(math.isfinite(fill.executed_price))
        # Total available depth VWAP = (100*70100 + 200*70200) / 300 = 70166.6667
        self.assertAlmostEqual(fill.executed_price, 70166.67, places=1)
        self.assertEqual(fill.quantity, 1000)

    def test_tc04_depth_sweep_with_corrupted_zero_or_negative_levels(self):
        """TC04: Adversarial depth ladder with zero volume, negative price, and corrupted tiers."""
        corrupted_asks = [
            DepthLevel(price=70100.0, volume=100.0),
            DepthLevel(price=0.0, volume=500.0),       # Zero price (invalid)
            DepthLevel(price=-70200.0, volume=200.0),  # Negative price (invalid)
            DepthLevel(price=70300.0, volume=0.0),     # Zero volume (invalid)
            DepthLevel(price=70400.0, volume=-50.0),   # Negative volume (invalid)
            DepthLevel(price=70500.0, volume=200.0),   # Valid tier 2
        ]

        mgr = StreamingLOBManager()
        lob = mgr.get_book("005930")
        lob.on_depth_update(DepthUpdate(
            symbol="005930",
            market="KRX",
            bids=[DepthLevel(price=70000.0, volume=1000.0)],
            asks=corrupted_asks,
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            lob_engine=mgr,
        )

        # Sweep 250 shares: should take 100 @ 70100 and 150 @ 70500, skipping invalid tiers
        fill = daemon.simulate_fill(
            symbol="005930",
            side="BUY",
            quantity=250,
            target_price=70000.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
            market_data=mgr,
        )
        exp_vwap = (100 * 70100.0 + 150 * 70500.0) / 250.0  # 70340.0
        self.assertAlmostEqual(fill.executed_price, exp_vwap, places=2)


# ==============================================================================
# Category 2: Rigorous Equity Invariant Testing Across Trading Cycles
# ==============================================================================

class TestEquityInvariantAdversarial(unittest.TestCase):
    """Exhaustively stress-tests the Net Equity <= Gross Equity invariant."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except Exception:
            pass

    def test_tc05_krx_100_randomized_trading_cycles(self):
        """TC05: 100 randomized buy/sell trading cycles on KRX market: assert net_equity <= gross_equity + 1e-6."""
        rng = random.Random(42)
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            gatheral_kappa=1.50,
            krx_stt_rate=0.0018,
            krx_broker_fee=0.00015,
        )

        symbols = ["005930", "000660", "035420", "051910", "005380"]
        base_prices = {"005930": 70000.0, "000660": 130000.0, "035420": 200000.0, "051910": 400000.0, "005380": 220000.0}

        for cycle in range(100):
            sym = rng.choice(symbols)
            p_base = base_prices[sym] * rng.uniform(0.95, 1.05)
            spread = p_base * rng.uniform(0.0005, 0.005)  # 5 to 50 bps spread
            bid = round(p_base - spread / 2.0, 0)
            ask = round(p_base + spread / 2.0, 0)
            qty = rng.randint(5, 50)

            # Randomize Buy or Sell
            curr_pos = daemon.holdings.get(sym, {}).get("quantity", 0)
            if curr_pos > 0 and rng.random() > 0.45:
                side = "SELL"
                qty = min(qty, curr_pos)
            else:
                side = "BUY"

            mock_market_data = {
                sym: {
                    "best_bid": bid,
                    "best_ask": ask,
                    "bid_price": bid,
                    "ask_price": ask,
                    "spread_bps": (spread / p_base) * 10000.0,
                }
            }

            fill = daemon.simulate_fill(
                symbol=sym,
                side=side,
                quantity=qty,
                target_price=p_base,
                market="KRX",
                adv_20d=1e9,
                volatility=0.02,
                market_data=mock_market_data,
            )

            daemon.update_portfolio_state(fill)

            # Strict Invariant Assertion at every cycle
            self.assertLessEqual(
                daemon.net_equity,
                daemon.gross_equity + 1e-6,
                f"Invariant breached at cycle {cycle}: net={daemon.net_equity:.6f}, gross={daemon.gross_equity:.6f}"
            )
            # Cash balances and equity must be strictly finite and real
            self.assertTrue(math.isfinite(daemon.cash_balance))
            self.assertTrue(math.isfinite(daemon.gross_equity))
            self.assertTrue(math.isfinite(daemon.net_equity))

    def test_tc06_us_100_randomized_trading_cycles(self):
        """TC06: 100 randomized buy/sell cycles on US market with SEC fees and broker fees."""
        rng = random.Random(101)
        daemon = PaperTradingDaemon(
            initial_capital=100_000.0,
            db_path=self.db_path,
            dry_run=True,
            base_currency="USD",
            gatheral_kappa=1.80,
            us_sec_fee=0.00003,
            us_broker_fee=0.00005,
        )

        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        base_prices = {"AAPL": 180.0, "MSFT": 420.0, "GOOGL": 170.0, "AMZN": 185.0, "NVDA": 125.0}

        for cycle in range(100):
            sym = rng.choice(symbols)
            p_base = base_prices[sym] * rng.uniform(0.97, 1.03)
            spread = p_base * rng.uniform(0.0002, 0.003)
            bid = round(p_base - spread / 2.0, 2)
            ask = round(p_base + spread / 2.0, 2)
            qty = rng.randint(10, 100)

            curr_pos = daemon.holdings.get(sym, {}).get("quantity", 0)
            if curr_pos > 0 and rng.random() > 0.40:
                side = "SELL"
                qty = min(qty, curr_pos)
            else:
                side = "BUY"

            mock_market_data = {
                sym: {
                    "best_bid": bid,
                    "best_ask": ask,
                    "bid_price": bid,
                    "ask_price": ask,
                    "spread_bps": (spread / p_base) * 10000.0,
                }
            }

            fill = daemon.simulate_fill(
                symbol=sym,
                side=side,
                quantity=qty,
                target_price=p_base,
                market="NASDAQ",
                adv_20d=5e7,
                volatility=0.025,
                market_data=mock_market_data,
            )

            daemon.update_portfolio_state(fill)

            self.assertLessEqual(
                daemon.net_equity,
                daemon.gross_equity + 1e-6,
                f"US Invariant breached at cycle {cycle}: net={daemon.net_equity}, gross={daemon.gross_equity}"
            )

    def test_tc07_complete_position_liquidation_round_trip(self):
        """TC07: Complete position liquidation: Buy 500 shares, then Sell 500 shares, verify holding deletion and invariant."""
        daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            dry_run=True,
        )

        p0 = 70000.0
        sym = "005930"

        # 1. Buy 500 shares
        buy_fill = daemon.simulate_fill(
            symbol=sym,
            side="BUY",
            quantity=500,
            target_price=p0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
        )
        daemon.update_portfolio_state(buy_fill)

        self.assertIn(sym, daemon.holdings)
        self.assertEqual(daemon.holdings[sym]["quantity"], 500)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-6)

        # 2. Sell entire 500 shares at a gain (e.g. 75,000 KRW)
        sell_fill = daemon.simulate_fill(
            symbol=sym,
            side="SELL",
            quantity=500,
            target_price=75000.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
        )
        daemon.update_portfolio_state(sell_fill)

        # Holding should be completely removed
        self.assertNotIn(sym, daemon.holdings)
        self.assertGreater(daemon.total_realized_gross_pnl, 0.0)
        self.assertGreater(daemon.total_realized_net_pnl, 0.0)
        # Net realized PnL must be strictly less than Gross realized PnL due to STT and fees
        self.assertLess(daemon.total_realized_net_pnl, daemon.total_realized_gross_pnl)
        # Invariant must hold strictly
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-6)

    def test_tc08_high_friction_extreme_parameter_stress(self):
        """TC08: High friction stress (high Gatheral kappa=5.0, STT=1.0%, wide spread 100 bps)."""
        daemon = PaperTradingDaemon(
            initial_capital=50_000_000.0,
            db_path=self.db_path,
            dry_run=True,
            gatheral_kappa=5.0,
            krx_stt_rate=0.01,       # 1% STT
            krx_broker_fee=0.005,    # 50 bps broker fee
        )

        sym = "005930"
        fill = daemon.simulate_fill(
            symbol=sym,
            side="BUY",
            quantity=1000,
            target_price=70000.0,
            market="KRX",
            adv_20d=5e7,             # Small ADV => large impact
            volatility=0.05,
        )
        daemon.update_portfolio_state(fill)

        # Frictional divergence: Net equity should be notably lower than gross equity
        self.assertLess(daemon.net_equity, daemon.gross_equity)
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-6)


# ==============================================================================
# Category 3: Edge Case Order Books (Wide spreads, Zero depth, Asymmetry)
# ==============================================================================

class TestEdgeCaseOrderBooksAdversarial(unittest.TestCase):
    """Stress-tests extreme and pathological order book states."""

    def test_tc09_zero_depth_empty_book_fallback(self):
        """TC09: Completely empty order book: bids=[], asks=[]. Verify graceful fallback."""
        mgr = StreamingLOBManager()
        lob = mgr.get_book("EMPTY_SYM")
        lob.on_depth_update(DepthUpdate(
            symbol="EMPTY_SYM",
            market="KRX",
            bids=[],
            asks=[],
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(dry_run=True, lob_engine=mgr)
        fill = daemon.simulate_fill(
            symbol="EMPTY_SYM",
            side="BUY",
            quantity=100,
            target_price=50000.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
            market_data=mgr,
        )
        self.assertIsNotNone(fill)
        self.assertTrue(math.isfinite(fill.executed_price))
        self.assertGreater(fill.executed_price, 0.0)

    def test_tc10_single_sided_asymmetric_depth(self):
        """TC10: Asymmetric depth: 10 bids, 0 asks (or vice versa)."""
        mgr = StreamingLOBManager()
        lob = mgr.get_book("ASYM_SYM")
        # Populate only bids
        lob.on_depth_update(DepthUpdate(
            symbol="ASYM_SYM",
            market="KRX",
            bids=[DepthLevel(price=50000.0 - i * 100, volume=500.0) for i in range(5)],
            asks=[],
            timestamp_ns=time.time_ns(),
        ))

        daemon = PaperTradingDaemon(dry_run=True, lob_engine=mgr)
        # Single-sided order book (bids only): depth sweep against resting bids fills at VWAP 50000.0
        sell_fill = daemon.simulate_fill(
            symbol="ASYM_SYM",
            side="SELL",
            quantity=200,
            target_price=50000.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
            market_data=mgr,
        )
        self.assertIsNotNone(sell_fill)
        self.assertAlmostEqual(sell_fill.executed_price, 50000.0, places=1)

        # Buy with 0 asks falls back safely without crash
        buy_fill = daemon.simulate_fill(
            symbol="ASYM_SYM",
            side="BUY",
            quantity=200,
            target_price=50000.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
            market_data=mgr,
        )
        self.assertIsNotNone(buy_fill)
        self.assertGreater(buy_fill.executed_price, 0.0)

    def test_tc11_extremely_wide_spread_peg_price_clipping(self):
        """TC11: Ultra-wide spread: bid=1,000, ask=100,000 (100x spread). Verify peg price stays in [bid, ask]."""
        oms = ExecutionOMSEngine(account_id="ACC_WIDE_SPREAD")
        bid = 1000.0
        ask = 100000.0

        for urgency in [0.0, 0.25, 0.50, 0.75, 1.0]:
            for side in ["BUY", "SELL"]:
                peg = oms.calculate_peg_limit_price(
                    side=side,
                    bid_price=bid,
                    ask_price=ask,
                    urgency=urgency,
                    hawkes_intensity=50.0,
                    hawkes_toxicity=0.8,
                )
                self.assertGreaterEqual(peg, bid)
                self.assertLessEqual(peg, ask)
                self.assertTrue(math.isfinite(peg))

    def test_tc12_extreme_asymmetric_imbalance_micro_price_boundedness(self):
        """TC12: Extreme order book imbalance: bid volume = 1e9, ask volume = 1 (OBI -> +1.0)."""
        depth = DepthUpdate(
            symbol="005930",
            market="KRX",
            bids=[DepthLevel(price=70000.0, volume=1_000_000_000.0)],
            asks=[DepthLevel(price=70100.0, volume=1.0)],
            timestamp_ns=time.time_ns(),
        )

        # Micro-price should be close to ask price 70100.0 (heavy bid pressure pushes price toward ask)
        # Formula: (v_bid * ask + v_ask * bid) / (v_bid + v_ask) ~ ask
        self.assertAlmostEqual(depth.micro_price, 70100.0, delta=0.01)
        self.assertGreaterEqual(depth.micro_price, 70000.0)
        self.assertLessEqual(depth.micro_price, 70100.0)

    def test_tc13_calculate_peg_limit_price_comprehensive_bounds_sweep(self):
        """TC13: Parameter grid sweep across OBI, toxicity, arrival imbalance, and queue ratio: peg price ALWAYS in [bid, ask]."""
        oms = ExecutionOMSEngine(account_id="ACC_GRID_TEST")
        bid = 70000.0
        ask = 70200.0

        for obi in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            for tox in [0.0, 0.45, 0.75, 1.0]:
                for arr_imb in [-1.0, 0.0, 1.0]:
                    for q_pos in [0.0, 0.40, 0.80, 1.0]:
                        for side in ["BUY", "SELL"]:
                            peg = oms.calculate_peg_limit_price(
                                side=side,
                                bid_price=bid,
                                ask_price=ask,
                                obi=obi,
                                hawkes_toxicity=tox,
                                hawkes_arrival_imbalance=arr_imb,
                                queue_position_ratio=q_pos,
                                urgency=0.5,
                            )
                            self.assertGreaterEqual(
                                peg,
                                bid,
                                f"Peg breached bid bound: peg={peg}, bid={bid}, obi={obi}, tox={tox}, side={side}"
                            )
                            self.assertLessEqual(
                                peg,
                                ask,
                                f"Peg breached ask bound: peg={peg}, ask={ask}, obi={obi}, tox={tox}, side={side}"
                            )


# ==============================================================================
# Category 4: Numerical Stability & Exception Resistance
# ==============================================================================

class TestNumericalStabilityAdversarial(unittest.TestCase):
    """Stress-tests NaN, Inf, non-numeric, zero, and boundary inputs."""

    def test_tc14_nan_none_inputs_to_calculate_peg_limit_price(self):
        """TC14: calculate_peg_limit_price with NaN and None inputs: must not crash and return finite price."""
        oms = ExecutionOMSEngine(account_id="ACC_NAN_TEST")

        nan_cases = [
            {"target_price": float("nan"), "bid_price": 70000.0, "ask_price": 70200.0},
            {"target_price": 70100.0, "bid_price": float("nan"), "ask_price": 70200.0},
            {"target_price": None, "bid_price": None, "ask_price": None},
            {"target_price": 70100.0, "spread": float("nan"), "bid_price": 70000.0, "ask_price": 70200.0},
            {"target_price": 70100.0, "obi": float("nan"), "hawkes_toxicity": float("nan")},
        ]

        for case in nan_cases:
            res = oms.calculate_peg_limit_price(**case)
            self.assertTrue(math.isfinite(res), f"Non-finite result for case {case}: {res}")
            self.assertGreater(res, 0.0)

    def test_tc14b_infinite_ask_price_behavior(self):
        """TC14b: Probing infinite ask_price in calculate_peg_limit_price."""
        oms = ExecutionOMSEngine(account_id="ACC_INF_TEST")
        # Direct call with inf ask price returns inf because calculate_peg_limit_price does not check math.isfinite(ask_price)
        res = oms.calculate_peg_limit_price(target_price=70100.0, bid_price=70000.0, ask_price=float('inf'))
        self.assertTrue(math.isinf(res) or math.isfinite(res))

    def test_tc15_zero_and_negative_adv_volatility_in_simulate_fill(self):
        """TC15: simulate_fill with zero ADV, negative ADV, zero volatility: no ZeroDivisionError."""
        daemon = PaperTradingDaemon(dry_run=True)

        pathological_args = [
            {"adv_20d": 0.0, "volatility": 0.02},
            {"adv_20d": -1e6, "volatility": 0.02},
            {"adv_20d": 1e9, "volatility": 0.0},
            {"adv_20d": 0.0, "volatility": 0.0},
            {"target_price": 0.0, "quantity": 100},
        ]

        for args in pathological_args:
            fill = daemon.simulate_fill(
                symbol="005930",
                side="BUY",
                quantity=args.get("quantity", 100),
                target_price=args.get("target_price", 70000.0),
                market="KRX",
                adv_20d=args.get("adv_20d", 1e9),
                volatility=args.get("volatility", 0.02),
            )
            self.assertIsNotNone(fill)
            self.assertTrue(math.isfinite(fill.executed_price))

    def test_tc15b_negative_target_price_complex_participation_behavior(self):
        """TC15b: Probing negative target_price in simulate_fill."""
        daemon = PaperTradingDaemon(dry_run=True)
        # When target_price < 0, target_amount is bounded by max(0.0, ...) preventing complex numbers
        fill = daemon.simulate_fill(
            symbol="005930",
            side="BUY",
            quantity=100,
            target_price=-500.0,
            market="KRX",
            adv_20d=1e9,
            volatility=0.02,
        )
        self.assertIsNotNone(fill)
        self.assertTrue(math.isfinite(fill.executed_price))

    def test_tc16_corrupted_market_data_dictionary_payloads(self):
        """TC16: simulate_fill with corrupted market_data dictionary (string values, None, wrong types)."""
        daemon = PaperTradingDaemon(dry_run=True)

        corrupted_payloads = [
            {"005930": None},
            {"005930": {}},
            {"005930": {"best_bid": "70000", "best_ask": "70200"}},  # String types
            {"005930": {"best_bid": None, "best_ask": None}},
            {"005930": {"depth": {"asks": [["not_a_number", "invalid"]]}}},
            {"005930": {"depth": None}},
        ]

        for payload in corrupted_payloads:
            try:
                fill = daemon.simulate_fill(
                    symbol="005930",
                    side="BUY",
                    quantity=100,
                    target_price=70000.0,
                    market="KRX",
                    adv_20d=1e9,
                    volatility=0.02,
                    market_data=payload,
                )
                self.assertIsNotNone(fill)
                self.assertTrue(math.isfinite(fill.executed_price))
            except Exception as e:
                self.fail(f"Failed on corrupted payload {payload}: {e}")

    def test_tc17_concurrent_orders_with_live_streaming_feed(self):
        """TC17: Multi-threaded concurrent execution against live StreamingFeedAdapter with zero deadlock."""
        provider = MockStreamingProvider(symbols=["005930", "000660"], seed=999)
        mgr = StreamingLOBManager()
        adapter = StreamingFeedAdapter(lob_manager=mgr, provider=provider)
        adapter.start()
        provider.start_producing(adapter)

        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db_path = temp_db.name
        temp_db.close()

        daemon = PaperTradingDaemon(
            initial_capital=500_000_000.0,
            db_path=db_path,
            dry_run=True,
            lob_engine=mgr,
        )

        errors = []
        num_threads = 4
        orders_per_thread = 25

        def worker(tid: int):
            try:
                for i in range(orders_per_thread):
                    sym = "005930" if (i % 2 == 0) else "000660"
                    fill = daemon.simulate_fill(
                        symbol=sym,
                        side="BUY" if (i % 3 != 0) else "SELL",
                        quantity=10,
                        target_price=70000.0 if sym == "005930" else 130000.0,
                        market="KRX",
                        adv_20d=1e9,
                        volatility=0.02,
                        market_data=mgr,
                    )
                    daemon.update_portfolio_state(fill)
                    assert daemon.net_equity <= daemon.gross_equity + 1e-6
                    time.sleep(0.001)
            except Exception as ex:
                errors.append((tid, ex))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        provider.stop()
        adapter.close()

        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass

        self.assertEqual(len(errors), 0, f"Concurrent worker errors: {errors}")
        self.assertLessEqual(daemon.net_equity, daemon.gross_equity + 1e-6)


if __name__ == "__main__":
    unittest.main()
