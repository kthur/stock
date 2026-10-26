"""
tests/test_adversarial_challenger_m2_it2_gate8_fx.py
===================================================
Adversarial Empirical Stress Testing Suite for Milestone 2 Iteration 2:
Gate 8 Synthetic Inverse Beta Hedging under Extreme FX Shocks, Multi-Currency,
Portfolio Compositions, Precise Share Sizing, and Regime Invariance.

Test Coverage:
1. Domain 1: Multi-Currency & Extreme Exchange Rate Shocks (usd_krw in [800.0, 2500.0])
   - Extreme rates: 800, 950, 1100, 1350, 1600, 2000, 2500 KRW/USD
   - Fallback hierarchy: None, 0.0, negative (-1350.0), NaN, Inf, missing attribute -> 1350.0
2. Domain 2: Portfolio Compositions & Threshold Boundary Probing
   - Pure KRX portfolio: strictly generates 114800, 0 US hedges
   - Pure US portfolio (NASDAQ -> PSQ, SP500 -> SH), 0 KRX hedges
   - Mixed 50/50 portfolio: generates both 114800 and PSQ without cross-contamination
   - Exact boundary probing: 4.9% vs 5.1% activation threshold (5.0% hurdle)
3. Domain 3: Inverse Hedge Share Sizing & Pricing Mathematics
   - Integer share count assertion: isinstance(qty, int) and qty > 0
   - Strict 50% hedge weight cap (np.clip(..., 0.0, 0.50))
   - Pricing consistency: 2500.0 KRW for 114800, 50.0 USD for PSQ/SH
   - Zero / negative equity handling: gross_equity <= 0 produces empty hedge list
   - Micro-capital edge case: hedge value < single share price omitted cleanly
4. Domain 4: Regime Gating Invariance
   - Non-defensive regimes: BULL_LOW_VOL, BULL_HIGH_VOL, SIDEWAYS, RECOVERY, NEUTRAL -> 0 hedges
   - Defensive regimes: BEAR, BEAR_LOW_VOL, BEAR_HIGH_VOL, CRISIS, CRISIS_EXTREME -> hedges active
5. Domain 5: Dynamic Multi-Cycle Rebalancing & Regime Shift Unwinding
   - Consecutive CRISIS cycles maintain target hedge without position compounding
   - CRISIS -> BULL_LOW_VOL transition automatically liquidates hedge positions to 0
6. Domain 6: Alternative Base Currency Denomination (base_currency == "USD")
   - Holding conversions via (1.0 / fx_rate) and KRX inverse sizing via tot_cap * h_w * fx_rate
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.execution.paper_trading_daemon import (
    PaperTradingDaemon,
    PaperOrderAction,
    PaperExecutionStatus,
)


class TestGate8FXShocksAndFallbacks(unittest.TestCase):
    """Domain 1: Adversarial Exchange Rate Shocks & Robust Fallback Hierarchy."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_gate8_fx.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_gate8_continuous_fx_rate_shocks(self):
        """Verify exact share sizing across continuous extreme FX rates in [800.0, 2500.0]."""
        test_fx_rates = [800.0, 950.0, 1100.0, 1350.0, 1600.0, 2000.0, 2500.0]

        for fx in test_fx_rates:
            daemon = PaperTradingDaemon(
                initial_capital=100_000_000.0,
                db_path=self.db_path,
                regime_label="CRISIS",
                dry_run=True,
            )
            daemon.usd_krw = fx
            daemon.gross_equity = 100_000_000.0

            # 300 shares of AAPL @ $200 = $60,000 USD
            # Market value in KRW = $60,000 * fx
            daemon.holdings["AAPL"] = {
                "quantity": 300,
                "current_price": 200.0,
                "market": "NASDAQ",
            }

            approved, _ = daemon.evaluate_oms_safety_gates([])
            psq_hedges = [o for o in approved if o.get("symbol") == "PSQ"]
            self.assertEqual(len(psq_hedges), 1, f"Expected 1 PSQ hedge for FX={fx}")

            order = psq_hedges[0]
            qty = order["delta_quantity"]
            self.assertIsInstance(qty, int)
            self.assertGreater(qty, 0)
            self.assertEqual(order["target_price"], 50.0)

            # Mathematical validation:
            # Long USD = $60,000. Portfolio weight = min(1.0, ($60,000 * fx) / 100M).
            # Hedge weight = min(0.50, portfolio_weight).
            # For fx >= 833.33, portfolio_weight >= 0.50, so h_w = 0.50.
            # Target hedge capital in KRW = 100M * 0.50 = 50,000,000 KRW.
            # Target hedge capital in USD = 50,000,000 / fx.
            # Expected shares = int((50,000,000 / fx) / 50.0)
            expected_weight = min(0.50, (60_000.0 * fx) / 100_000_000.0)
            expected_krw_cap = 100_000_000.0 * expected_weight
            expected_usd_cap = expected_krw_cap / fx
            expected_shares = int(expected_usd_cap / 50.0)

            self.assertEqual(
                qty,
                expected_shares,
                f"Shares mismatch for FX={fx}: got {qty}, expected {expected_shares}",
            )

    def test_gate8_robust_fallback_hierarchy(self):
        """Verify graceful fallback to 1350.0 under corrupt, missing, or extreme FX inputs."""
        pathological_fx_inputs = [
            ("none", None),
            ("zero", 0.0),
            ("negative", -1350.0),
            ("nan", float("nan")),
            ("pos_inf", float("inf")),
            ("neg_inf", float("-inf")),
        ]

        # Normal baseline at 1350.0 with 300 sh AAPL @ $200 = 740 shares of PSQ
        baseline_expected_shares = int((50_000_000.0 / 1350.0) / 50.0)  # 740

        for label, val in pathological_fx_inputs:
            daemon = PaperTradingDaemon(
                initial_capital=100_000_000.0,
                db_path=self.db_path,
                regime_label="CRISIS",
                dry_run=True,
            )
            daemon.usd_krw = val
            daemon.gross_equity = 100_000_000.0
            daemon.holdings["AAPL"] = {
                "quantity": 300,
                "current_price": 200.0,
                "market": "NASDAQ",
            }

            approved, _ = daemon.evaluate_oms_safety_gates([])
            psq_hedges = [o for o in approved if o.get("symbol") == "PSQ"]
            self.assertEqual(len(psq_hedges), 1, f"Failed fallback for {label}")
            self.assertEqual(
                psq_hedges[0]["delta_quantity"],
                baseline_expected_shares,
                f"Share count mismatch on fallback for {label}",
            )

    def test_gate8_missing_usd_krw_attribute(self):
        """Verify fallback to 1350.0 when usd_krw attribute is completely deleted."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        delattr(daemon, "usd_krw")
        daemon.gross_equity = 100_000_000.0
        daemon.holdings["AAPL"] = {
            "quantity": 300,
            "current_price": 200.0,
            "market": "NASDAQ",
        }

        approved, _ = daemon.evaluate_oms_safety_gates([])
        psq_hedges = [o for o in approved if o.get("symbol") == "PSQ"]
        self.assertEqual(len(psq_hedges), 1)
        self.assertEqual(psq_hedges[0]["delta_quantity"], 740)


class TestGate8PortfolioCompositions(unittest.TestCase):
    """Domain 2: Portfolio Composition Segregation & 5% Activation Boundary."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_gate8_comp.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pure_krx_portfolio_generates_only_114800(self):
        """Pure KRX portfolio in CRISIS emits 114800 and 0 US inverse hedges."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        daemon.gross_equity = 100_000_000.0
        daemon.holdings["005930"] = {
            "quantity": 1000,
            "current_price": 50000.0,
            "market": "KOSPI",
        }

        approved, _ = daemon.evaluate_oms_safety_gates([])
        hedges = [o for o in approved if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
        self.assertEqual(len(hedges), 1)
        self.assertEqual(hedges[0]["symbol"], "114800")
        self.assertEqual(hedges[0]["market"], "KOSPI")
        self.assertEqual(hedges[0]["delta_quantity"], 10000)
        self.assertEqual(hedges[0]["target_price"], 2500.0)

    def test_pure_us_portfolio_nasdaq_vs_sp500(self):
        """Pure US portfolio emits PSQ for NASDAQ holdings and SH for SP500 holdings."""
        # 1. NASDAQ portfolio -> PSQ
        daemon_nasdaq = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        daemon_nasdaq.gross_equity = 100_000_000.0
        daemon_nasdaq.holdings["AAPL"] = {
            "quantity": 250,
            "current_price": 200.0,
            "market": "NASDAQ",
        }
        app_ndq, _ = daemon_nasdaq.evaluate_oms_safety_gates([])
        hedges_ndq = [o for o in app_ndq if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
        self.assertEqual(len(hedges_ndq), 1)
        self.assertEqual(hedges_ndq[0]["symbol"], "PSQ")
        self.assertEqual(hedges_ndq[0]["market"], "NASDAQ")

        # 2. SP500 portfolio -> SH
        daemon_sp500 = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        daemon_sp500.gross_equity = 100_000_000.0
        daemon_sp500.holdings["SPY"] = {
            "quantity": 100,
            "current_price": 500.0,
            "market": "SP500",
        }
        app_spy, _ = daemon_sp500.evaluate_oms_safety_gates([])
        hedges_spy = [o for o in app_spy if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
        self.assertEqual(len(hedges_spy), 1)
        self.assertEqual(hedges_spy[0]["symbol"], "SH")
        self.assertEqual(hedges_spy[0]["market"], "SP500")

    def test_mixed_50_50_portfolio_clean_decoupling(self):
        """Mixed 50% KRX and 50% US portfolio generates both 114800 and PSQ proportionally."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        daemon.gross_equity = 100_000_000.0

        # KRX: 1,000 sh @ 50,000 KRW = 50,000,000 KRW (50%)
        daemon.holdings["005930"] = {
            "quantity": 1000,
            "current_price": 50000.0,
            "market": "KOSPI",
        }
        # US: 185.185 sh @ $200 * 1350 = 50,000,000 KRW (50%)
        daemon.holdings["AAPL"] = {
            "quantity": 250,
            "current_price": (50_000_000.0 / 1350.0) / 250.0,
            "market": "NASDAQ",
        }

        approved, _ = daemon.evaluate_oms_safety_gates([])
        hedges = [o for o in approved if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
        self.assertEqual(len(hedges), 2, "Must emit exactly 2 hedges (1 KRX, 1 US)")

        h_symbols = {h["symbol"]: h for h in hedges}
        self.assertIn("114800", h_symbols)
        self.assertIn("PSQ", h_symbols)

        # 114800: KRX exposure 50%, -2x leverage -> hedge weight 25% = 25,000,000 KRW
        # 25M / 2500 KRW = 10,000 shares
        self.assertEqual(h_symbols["114800"]["delta_quantity"], 10000)

        # PSQ: US exposure 50%, -1x leverage -> hedge weight 50% = 50,000,000 KRW
        # In USD: $37,037.04 / $50 = 740 shares
        self.assertEqual(h_symbols["PSQ"]["delta_quantity"], 740)

    def test_boundary_exposure_4_9_vs_5_1_percent(self):
        """Boundary test: 4.9% US exposure is unhedged; 5.1% triggers inverse hedge."""
        # Test 4.9% US exposure: 4,900,000 KRW / 100,000,000 KRW = 0.049 <= 0.05
        d_low = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        d_low.gross_equity = 100_000_000.0
        d_low.holdings["AAPL"] = {
            "quantity": 10,
            "current_price": 4_900_000.0 / 1350.0 / 10.0,
            "market": "NASDAQ",
        }
        app_low, _ = d_low.evaluate_oms_safety_gates([])
        hedges_low = [o for o in app_low if o.get("symbol") in ("PSQ", "SH")]
        self.assertEqual(len(hedges_low), 0, "4.9% exposure must not trigger hedge")

        # Test 5.1% US exposure: 5,100,000 KRW / 100,000,000 KRW = 0.051 > 0.05
        d_high = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        d_high.gross_equity = 100_000_000.0
        d_high.holdings["AAPL"] = {
            "quantity": 10,
            "current_price": 5_100_000.0 / 1350.0 / 10.0,
            "market": "NASDAQ",
        }
        app_high, _ = d_high.evaluate_oms_safety_gates([])
        hedges_high = [o for o in app_high if o.get("symbol") in ("PSQ", "SH")]
        self.assertEqual(len(hedges_high), 1, "5.1% exposure must trigger hedge")
        # 5.1M KRW / 1350 = $3,777.78 USD / $50 = 75 shares
        self.assertEqual(hedges_high[0]["delta_quantity"], 75)


class TestGate8InverseHedgeShareSizingAndPricing(unittest.TestCase):
    """Domain 3: Share Sizing Math, Integer Truncation, Pricing, and Caps."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_gate8_sizing.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_strict_50_percent_hedge_weight_cap(self):
        """Even with 200% leveraged long exposure, hedge weight is strictly capped at 50%."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        daemon.gross_equity = 100_000_000.0
        # 1,000 AAPL @ $200 = $200,000 = 270,000,000 KRW (270% gross exposure)
        daemon.holdings["AAPL"] = {
            "quantity": 1000,
            "current_price": 200.0,
            "market": "NASDAQ",
        }

        approved, _ = daemon.evaluate_oms_safety_gates([])
        psq = [o for o in approved if o.get("symbol") == "PSQ"][0]

        # Hedge weight must be strictly clipped to 0.50
        self.assertLessEqual(psq["target_weight"], 0.50)
        self.assertEqual(psq["target_weight"], 0.50)
        # Sized on 50% of 100M KRW = 50M KRW / 1350 / $50 = 740 shares
        self.assertEqual(psq["delta_quantity"], 740)

    def test_zero_and_negative_equity_safety(self):
        """Zero or negative gross equity safely returns empty list without division errors."""
        for bad_equity in [0.0, -100_000.0, -1e9]:
            daemon = PaperTradingDaemon(
                initial_capital=100_000_000.0,
                db_path=self.db_path,
                regime_label="CRISIS",
                dry_run=True,
            )
            daemon.gross_equity = bad_equity
            daemon.holdings["AAPL"] = {
                "quantity": 300,
                "current_price": 200.0,
                "market": "NASDAQ",
            }
            approved, _ = daemon.evaluate_oms_safety_gates([])
            hedges = [o for o in approved if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
            self.assertEqual(len(hedges), 0, f"Expected 0 hedges for gross_equity={bad_equity}")

    def test_micro_capital_no_fractional_shares(self):
        """When total hedge capital is less than 1 share price, 0-share orders are omitted."""
        daemon = PaperTradingDaemon(
            initial_capital=10_000.0,  # 10,000 KRW
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        daemon.gross_equity = 10_000.0
        # 10,000 KRW long KRX stock
        daemon.holdings["005930"] = {
            "quantity": 1,
            "current_price": 10000.0,
            "market": "KOSPI",
        }
        # Target hedge capital = 10,000 * (1.0 / 2.0) = 5,000 KRW.
        # 114800 is 2500 KRW -> 2 shares.
        # What if equity is 1,000 KRW? Hedge capital = 500 KRW < 2500 KRW -> 0 shares
        daemon.gross_equity = 1_000.0
        daemon.holdings["005930"]["current_price"] = 1000.0

        approved, _ = daemon.evaluate_oms_safety_gates([])
        hedges = [o for o in approved if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
        self.assertEqual(len(hedges), 0, "0-share orders must be omitted")


class TestGate8RegimeGatingInvariance(unittest.TestCase):
    """Domain 4: Regime Invariance - Defensive vs Non-Defensive Regimes."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_gate8_regimes.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_non_defensive_regimes_emit_zero_hedges(self):
        """Non-defensive regimes must NEVER emit inverse hedges under any circumstance."""
        non_defensive_regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "RECOVERY",
            "NEUTRAL",
            "ACCUMULATION",
        ]

        for reg in non_defensive_regimes:
            daemon = PaperTradingDaemon(
                initial_capital=100_000_000.0,
                db_path=self.db_path,
                regime_label=reg,
                dry_run=True,
            )
            daemon.gross_equity = 100_000_000.0
            daemon.holdings["005930"] = {
                "quantity": 1000,
                "current_price": 50000.0,
                "market": "KOSPI",
            }
            daemon.holdings["AAPL"] = {
                "quantity": 300,
                "current_price": 200.0,
                "market": "NASDAQ",
            }

            approved, _ = daemon.evaluate_oms_safety_gates([])
            hedges = [o for o in approved if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
            self.assertEqual(
                len(hedges),
                0,
                f"Regime {reg} must emit 0 inverse hedges, got {len(hedges)}",
            )

    def test_all_defensive_regimes_emit_inverse_hedges(self):
        """Defensive regimes (BEAR, CRISIS) must reliably emit inverse hedges."""
        defensive_regimes = [
            "BEAR",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "CRISIS",
            "CRISIS_EXTREME",
        ]

        for reg in defensive_regimes:
            daemon = PaperTradingDaemon(
                initial_capital=100_000_000.0,
                db_path=self.db_path,
                regime_label=reg,
                dry_run=True,
            )
            daemon.gross_equity = 100_000_000.0
            daemon.holdings["AAPL"] = {
                "quantity": 300,
                "current_price": 200.0,
                "market": "NASDAQ",
            }

            approved, _ = daemon.evaluate_oms_safety_gates([])
            hedges = [o for o in approved if o.get("action") == PaperOrderAction.BUY_HEDGE.value]
            self.assertGreater(
                len(hedges),
                0,
                f"Regime {reg} failed to emit inverse hedges",
            )
            self.assertEqual(hedges[0]["symbol"], "PSQ")


class TestGate8MultiCycleAndUSDDenomination(unittest.TestCase):
    """Domain 5 & 6: Multi-Cycle Unwinding & USD Base Currency Operation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_gate8_multicycle.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_multi_cycle_regime_transition_unwinds_hedge(self):
        """Hedge is established in CRISIS and cleanly liquidated when transitioning to BULL."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000_000.0,
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=False,
        )
        daemon.gross_equity = 100_000_000.0
        daemon.cash_balance = 100_000_000.0
        daemon.holdings["AAPL"] = {
            "quantity": 300,
            "current_price": 200.0,
            "avg_cost": 200.0,
            "gross_cost": 200.0,
            "market": "NASDAQ",
        }

        targets = [{
            "symbol": "AAPL",
            "market": "NASDAQ",
            "target_weight": 0.81,
            "target_price": 200.0,
            "volatility": 0.02,
            "adv_20d": 1e9,
            "predicted_return": 0.05,
        }]

        # Cycle 1: CRISIS -> PSQ is bought
        daemon.run_cycle(targets)
        psq_qty_c1 = daemon.holdings.get("PSQ", {}).get("quantity", 0)
        self.assertEqual(psq_qty_c1, 740, "PSQ must be 740 in Cycle 1")

        # Cycle 2: Switch to BULL_LOW_VOL -> PSQ must be liquidated to 0
        daemon.regime_label = "BULL_LOW_VOL"
        daemon.run_cycle(targets)
        psq_qty_c2 = daemon.holdings.get("PSQ", {}).get("quantity", 0)
        self.assertEqual(psq_qty_c2, 0, "PSQ must be 0 after regime transition to BULL_LOW_VOL")

    def test_usd_base_currency_operations(self):
        """When base_currency is USD, verify exact conversion of KRX holdings and sizing."""
        daemon = PaperTradingDaemon(
            initial_capital=100_000.0,
            base_currency="USD",
            db_path=self.db_path,
            regime_label="CRISIS",
            dry_run=True,
        )
        daemon.gross_equity = 100_000.0

        # Long US: $50,000 USD (50% of portfolio)
        daemon.holdings["AAPL"] = {
            "quantity": 250,
            "current_price": 200.0,
            "market": "NASDAQ",
        }
        # Long KRX: 1,000 sh @ 50,000 KRW = 50,000,000 KRW
        # In USD at fx=1350: $37,037.04 USD (37.04% of portfolio)
        daemon.holdings["005930"] = {
            "quantity": 1000,
            "current_price": 50000.0,
            "market": "KOSPI",
        }

        approved, _ = daemon.evaluate_oms_safety_gates([])
        hedges = {o["symbol"]: o for o in approved if o.get("action") == PaperOrderAction.BUY_HEDGE.value}

        self.assertEqual(len(hedges), 2)
        # PSQ: $100,000 * 0.50 = $50,000 USD / $50 = 1,000 shares
        self.assertEqual(hedges["PSQ"]["delta_quantity"], 1000)

        # 114800: weight 0.37037 / 2.0 = 0.185185
        # Capital in USD = $18,518.52 * 1350 = 25,000,000 KRW / 2500 KRW = 10,000 shares
        self.assertEqual(hedges["114800"]["delta_quantity"], 10000)


if __name__ == "__main__":
    unittest.main()
