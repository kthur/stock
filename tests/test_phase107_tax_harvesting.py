"""
tests/test_phase107_tax_harvesting.py — Unit, Integration & Invariant Tests for Tax-Loss Harvesting

Phase 107 / Feature F508 / Release R123 (v114 Production Master)
Milestone 4: Dynamic Tax-Loss Harvesting & Wash-Sale Optimizer

Test Categories:
- Category 1: Module Exports, Class Signatures & Alias Trees (TC01~TC03)
- Category 2: TaxLot Data Structure, Holding Period & Tax Rates (TC04~TC08)
- Category 3: WashSaleTracker & US IRC § 1091 30-Day Window Enforcement (TC09~TC16)
- Category 4: Gross Tax Alpha & Round-Trip Switching Friction Modeling (TC17~TC21)
- Category 5: Economic Hurdle Evaluation (Net Tax Alpha > Friction) (TC22~TC25)
- Category 6: Surrogate Asset Selection (rho >= 0.85, Same Sector, ADV Bound) (TC26~TC31)
- Category 7: Portfolio-Level Harvesting Optimization & HIFO Ordering (TC32~TC36)
- Category 8: Edge Cases, Numerical Robustness & Order Generation (TC37~TC40)
"""

from __future__ import annotations

import sys
import datetime
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Path setup: Ensure repo root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from trading_system.src.risk.tax_loss_harvesting_optimizer import (  # noqa: E402
    TaxLot,
    TaxHarvestingPlan,
    WashSaleTracker,
    TaxConfig,
    DynamicTaxLossHarvestingOptimizer,
    TaxLossHarvestingEngine,
    InstitutionalTaxOptimizer,
    Phase107TaxOptimizer,
    parse_date,
    format_date,
)


class TestPhase107TaxHarvestingOptimizer(unittest.TestCase):
    """Comprehensive test harness for DynamicTaxLossHarvestingOptimizer."""

    def setUp(self):
        """Set up test fixtures and deterministic synthetic data."""
        np.random.seed(42)
        self.config = TaxConfig(
            us_short_term_rate=0.37,
            us_long_term_rate=0.20,
            krx_capital_gains_rate=0.22,
            wash_sale_window_days=30,
            min_net_alpha_hurdle=0.0,
            min_surrogate_correlation=0.85,
            max_adv_participation=0.015,
            gatheral_kappa=1.50,
            kospi_stt_rate=0.0018,
            kosdaq_stt_rate=0.0020,
            us_sec_rate=0.0000278,
            broker_fee_krx=0.00030,
            broker_fee_us=0.00005,
            base_spread_krx=0.0005,
            base_spread_us=0.0005,
        )
        self.optimizer = DynamicTaxLossHarvestingOptimizer(config=self.config)

        # Generate 100 days of synthetic price history
        dates = pd.date_range("2026-01-01", periods=100, freq="B")
        
        # Tech Sector: AAPL, MSFT (correlated rho > 0.90), NVDA (moderate rho)
        base_returns = np.random.normal(0.0005, 0.015, len(dates))
        msft_returns = base_returns * 0.95 + np.random.normal(0.0, 0.003, len(dates))
        aapl_returns = base_returns * 0.92 + np.random.normal(0.0, 0.004, len(dates))
        nvda_returns = base_returns * 0.60 + np.random.normal(0.0, 0.020, len(dates))
        
        # Financials Sector: JPM, BAC (correlated rho > 0.90)
        fin_base = np.random.normal(0.0003, 0.012, len(dates))
        jpm_returns = fin_base * 0.94 + np.random.normal(0.0, 0.003, len(dates))
        bac_returns = fin_base * 0.91 + np.random.normal(0.0, 0.004, len(dates))

        # KRX Semi: 005930 (Samsung), 000660 (SK Hynix) (correlated rho > 0.90)
        krx_base = np.random.normal(0.0004, 0.018, len(dates))
        sec_returns = krx_base * 0.93 + np.random.normal(0.0, 0.004, len(dates))
        hynix_returns = krx_base * 0.90 + np.random.normal(0.0, 0.005, len(dates))

        df_prices = pd.DataFrame(index=dates)
        df_prices["AAPL"] = 150.0 * np.cumprod(1.0 + aapl_returns)
        df_prices["MSFT"] = 300.0 * np.cumprod(1.0 + msft_returns)
        df_prices["NVDA"] = 500.0 * np.cumprod(1.0 + nvda_returns)
        df_prices["JPM"] = 140.0 * np.cumprod(1.0 + jpm_returns)
        df_prices["BAC"] = 35.0 * np.cumprod(1.0 + bac_returns)
        df_prices["005930"] = 70000.0 * np.cumprod(1.0 + sec_returns)
        df_prices["000660"] = 120000.0 * np.cumprod(1.0 + hynix_returns)
        self.price_history_df = df_prices

        self.sector_map = {
            "AAPL": "Information Technology",
            "MSFT": "Information Technology",
            "NVDA": "Information Technology",
            "JPM": "Financials",
            "BAC": "Financials",
            "005930": "Semiconductors",
            "000660": "Semiconductors",
        }

        self.adv_dict = {
            "AAPL": 1e9,
            "MSFT": 8e8,
            "NVDA": 1.2e9,
            "JPM": 5e8,
            "BAC": 4e8,
            "005930": 5e11,
            "000660": 3e11,
        }

    # =======================================================================
    # Category 1: Module Exports, Class Signatures & Alias Trees (TC01~TC03)
    # =======================================================================

    def test_tc01_alias_trees(self):
        """TC01: Verify required aliases are identical to DynamicTaxLossHarvestingOptimizer."""
        self.assertIs(TaxLossHarvestingEngine, DynamicTaxLossHarvestingOptimizer)
        self.assertIs(InstitutionalTaxOptimizer, DynamicTaxLossHarvestingOptimizer)
        self.assertIs(Phase107TaxOptimizer, DynamicTaxLossHarvestingOptimizer)

    def test_tc02_core_dataclass_instantiation(self):
        """TC02: Verify instantiation of core data structures."""
        lot = TaxLot(
            lot_id="LOT_001",
            symbol="AAPL",
            market="NASDAQ",
            acquisition_date="2026-01-15",
            quantity=100,
            cost_basis_per_share=180.0,
            current_price=150.0
        )
        self.assertEqual(lot.lot_id, "LOT_001")
        self.assertEqual(lot.symbol, "AAPL")
        self.assertEqual(lot.quantity, 100.0)
        self.assertEqual(lot.acquisition_date, "2026-01-15")

        tracker = WashSaleTracker(restriction_days=30)
        self.assertEqual(tracker.restriction_days, 30)

    def test_tc03_root_import_forwarder(self):
        """TC03: Verify importing from root `src.risk.tax_loss_harvesting_optimizer` works."""
        from src.risk.tax_loss_harvesting_optimizer import (
            DynamicTaxLossHarvestingOptimizer as RootOptimizer,
            TaxLot as RootTaxLot,
            WashSaleTracker as RootWashSaleTracker
        )
        self.assertIs(RootOptimizer, DynamicTaxLossHarvestingOptimizer)
        self.assertIs(RootTaxLot, TaxLot)
        self.assertIs(RootWashSaleTracker, WashSaleTracker)

    # =======================================================================
    # Category 2: TaxLot Data Structure, Holding Period & Tax Rates (TC04~TC08)
    # =======================================================================

    def test_tc04_holding_days_calculation(self):
        """TC04: Verify holding days correctly computes calendar duration."""
        lot = TaxLot(
            lot_id="L1",
            symbol="AAPL",
            market="NASDAQ",
            acquisition_date="2025-01-01",
            quantity=50,
            cost_basis_per_share=100.0,
            current_price=90.0
        )
        self.assertEqual(lot.holding_days("2025-01-01"), 0)
        self.assertEqual(lot.holding_days("2025-01-31"), 30)
        self.assertEqual(lot.holding_days("2026-01-01"), 365)
        self.assertEqual(lot.holding_days("2026-01-02"), 366)
        # Prior date returns 0 (clamped)
        self.assertEqual(lot.holding_days("2024-12-31"), 0)

    def test_tc05_short_term_vs_long_term(self):
        """TC05: Verify US IRC holding period: <= 365 days is short-term, > 365 is long-term."""
        lot = TaxLot(
            lot_id="L2",
            symbol="MSFT",
            market="NASDAQ",
            acquisition_date="2025-01-01",
            quantity=10,
            cost_basis_per_share=300.0
        )
        # Exactly 365 days -> False
        self.assertFalse(lot.is_long_term("2026-01-01"))
        # 366 days -> True
        self.assertTrue(lot.is_long_term("2026-01-02"))

    def test_tc06_unrealized_pnl_and_return(self):
        """TC06: Verify unrealized PnL and return percentage properties."""
        loss_lot = TaxLot("L3", "AAPL", "NASDAQ", "2026-01-01", 100, 200.0, current_price=160.0)
        self.assertAlmostEqual(loss_lot.market_value, 16000.0)
        self.assertAlmostEqual(loss_lot.unrealized_pnl, -4000.0)
        self.assertAlmostEqual(loss_lot.unrealized_return_pct, -0.20)

        gain_lot = TaxLot("L4", "AAPL", "NASDAQ", "2026-01-01", 100, 150.0, current_price=180.0)
        self.assertAlmostEqual(gain_lot.unrealized_pnl, 3000.0)
        self.assertAlmostEqual(gain_lot.unrealized_return_pct, 0.20)

    def test_tc07_applicable_tax_rates_us_and_krx(self):
        """TC07: Verify applicable tax rate resolution across US (short/long) and KRX."""
        # US short-term lot
        us_st = TaxLot("L_US_ST", "AAPL", "NASDAQ", "2026-01-01", 10, 100.0, current_price=80.0)
        rate_st = us_st.applicable_tax_rate("2026-06-01", self.config)
        self.assertEqual(rate_st, 0.37)  # Short-term US 37%

        # US long-term lot
        us_lt = TaxLot("L_US_LT", "AAPL", "NASDAQ", "2024-01-01", 10, 100.0, current_price=80.0)
        rate_lt = us_lt.applicable_tax_rate("2026-06-01", self.config)
        self.assertEqual(rate_lt, 0.20)  # Long-term US 20%

        # KRX lot
        krx_lot = TaxLot("L_KRX", "005930", "KOSPI", "2026-01-01", 100, 80000.0, current_price=70000.0)
        rate_krx = krx_lot.applicable_tax_rate("2026-06-01", self.config)
        self.assertEqual(rate_krx, 0.22)  # KRX 22%

    def test_tc08_total_cost_basis_with_commission(self):
        """TC08: Verify total cost basis correctly incorporates acquisition commissions."""
        lot = TaxLot("L5", "NVDA", "NASDAQ", "2026-01-01", 50, 400.0, current_price=350.0, commission_paid=15.0)
        self.assertEqual(lot.total_cost, 50 * 400.0 + 15.0)

    # =======================================================================
    # Category 3: WashSaleTracker & US IRC § 1091 30-Day Window Enforcement
    # =======================================================================

    def test_tc09_record_loss_sale_and_window(self):
        """TC09: Verify recording a loss sale establishes a 30-day window."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("AAPL", "2026-03-01", loss_amount=500.0)
        
        w_start, w_end = tracker.get_restriction_window("AAPL", "2026-03-01")
        self.assertEqual(w_start, "2026-01-30")
        self.assertEqual(w_end, "2026-03-31")

    def test_tc10_query_within_30_days_restricted(self):
        """TC10: Verify queries within 30 days of sale date return is_restricted == True."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("AAPL", "2026-03-01", loss_amount=1000.0)

        # Day 0 (same day)
        self.assertTrue(tracker.is_restricted("AAPL", "2026-03-01"))
        # Day 15
        self.assertTrue(tracker.is_restricted("AAPL", "2026-03-16"))
        # Day 30 (exact boundary)
        self.assertTrue(tracker.is_restricted("AAPL", "2026-03-31"))

    def test_tc11_query_after_30_days_unrestricted(self):
        """TC11: Verify queries after 30 days return is_restricted == False."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("AAPL", "2026-03-01", loss_amount=1000.0)

        # Day 31
        self.assertFalse(tracker.is_restricted("AAPL", "2026-04-01"))
        # Day 45
        self.assertFalse(tracker.is_restricted("AAPL", "2026-04-15"))

    def test_tc12_prior_purchase_wash_sale_window(self):
        """TC12: Verify wash-sale window correctly covers 30 days prior to sale date."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("AAPL", "2026-03-15", loss_amount=2000.0)

        # 10 days before sale -> in window
        self.assertTrue(tracker.is_restricted("AAPL", "2026-03-05"))
        # 30 days before sale (2026-02-13) -> in window
        self.assertTrue(tracker.is_restricted("AAPL", "2026-02-13"))
        # 31 days before sale (2026-02-12) -> outside window
        self.assertFalse(tracker.is_restricted("AAPL", "2026-02-12"))

    def test_tc13_repurchase_restricted_helper(self):
        """TC13: Verify is_repurchase_restricted checks forward 30-day window [T_sale, T_sale + 30d]."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("MSFT", "2026-02-01", loss_amount=800.0)

        # Prior date is not a repurchase after sale
        self.assertFalse(tracker.is_repurchase_restricted("MSFT", "2026-01-20"))
        # Sale day itself is restricted
        self.assertTrue(tracker.is_repurchase_restricted("MSFT", "2026-02-01"))
        # 20 days after is restricted
        self.assertTrue(tracker.is_repurchase_restricted("MSFT", "2026-02-21"))
        # 31 days after (2026-03-04) is clean
        self.assertFalse(tracker.is_repurchase_restricted("MSFT", "2026-03-04"))

    def test_tc14_get_restriction_expiry(self):
        """TC14: Verify restriction expiry returns latest T_sale + 30d."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("NVDA", "2026-03-01", loss_amount=500.0)
        tracker.record_loss_sale("NVDA", "2026-03-10", loss_amount=700.0)

        expiry = tracker.get_restriction_expiry("NVDA", as_of_date="2026-03-15")
        # 2026-03-10 + 30 days = 2026-04-09
        self.assertEqual(expiry, "2026-04-09")

    def test_tc15_independent_symbols_tracking(self):
        """TC15: Verify WashSaleTracker isolates symbols without cross-contamination."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("AAPL", "2026-03-01", loss_amount=500.0)

        self.assertTrue(tracker.is_restricted("AAPL", "2026-03-15"))
        self.assertFalse(tracker.is_restricted("MSFT", "2026-03-15"))
        self.assertFalse(tracker.is_restricted("005930", "2026-03-15"))

    def test_tc16_active_restricted_symbols_list(self):
        """TC16: Verify get_active_restricted_symbols filters active cooldowns."""
        tracker = WashSaleTracker(restriction_days=30)
        tracker.record_loss_sale("AAPL", "2026-01-01", loss_amount=500.0)   # Expired by March
        tracker.record_loss_sale("MSFT", "2026-03-01", loss_amount=600.0)   # Active in March
        tracker.record_loss_sale("JPM", "2026-03-10", loss_amount=400.0)    # Active in March

        active = tracker.get_active_restricted_symbols("2026-03-15")
        self.assertEqual(active, ["JPM", "MSFT"])

    # =======================================================================
    # Category 4: Gross Tax Alpha & Round-Trip Switching Friction (TC17~TC21)
    # =======================================================================

    def test_tc17_gross_tax_alpha_calculation(self):
        """TC17: Verify Gross Tax Alpha = tau_i * |Loss| for loss lots, and 0 for gains."""
        loss_lot = TaxLot("L_Loss", "AAPL", "NASDAQ", "2026-01-01", 100, 150.0, current_price=100.0)
        # Loss = (100 - 150) * 100 = -5,000. Short term rate = 0.37
        alpha = self.optimizer.calculate_gross_tax_alpha(loss_lot, "2026-05-01")
        self.assertAlmostEqual(alpha, 0.37 * 5000.0)

        gain_lot = TaxLot("L_Gain", "AAPL", "NASDAQ", "2026-01-01", 100, 100.0, current_price=150.0)
        zero_alpha = self.optimizer.calculate_gross_tax_alpha(gain_lot, "2026-05-01")
        self.assertEqual(zero_alpha, 0.0)

    def test_tc18_krx_friction_calculation(self):
        """TC18: Verify KRX friction incorporates STT (18/20 bps) + broker fee + spread + Gatheral."""
        # KOSPI SELL: STT 0.18% + Broker 0.03% = 0.21% statutory
        # Spread: 5 bps half-spread = 0.05%
        # Impact: kappa * sigma * (P^1.5)
        friction = self.optimizer.calculate_single_leg_friction(
            symbol="005930",
            market="KOSPI",
            price=70000.0,
            quantity=100,
            adv=1e10,
            volatility=0.25,
            is_sell=True
        )
        notional = 100 * 70000.0  # 7,000,000 KRW
        expected_statutory = notional * (0.0018 + 0.00030)
        expected_spread = notional * 0.0005
        self.assertGreater(friction, expected_statutory + expected_spread)

    def test_tc19_us_sell_friction(self):
        """TC19: Verify US sell friction includes SEC fee (0.00278%) + broker fee (0.005%)."""
        notional = 100 * 150.0  # $15,000
        friction = self.optimizer.calculate_single_leg_friction(
            symbol="AAPL",
            market="NASDAQ",
            price=150.0,
            quantity=100,
            adv=1e9,
            volatility=0.25,
            is_sell=True
        )
        expected_statutory = notional * (0.0000278 + 0.00005)
        expected_spread = notional * 0.0005
        self.assertGreater(friction, expected_statutory + expected_spread)

    def test_tc20_buy_leg_excludes_stt_sec(self):
        """TC20: Verify buy leg does NOT charge STT or SEC tax, resulting in lower friction."""
        sell_fric = self.optimizer.calculate_single_leg_friction(
            symbol="AAPL", market="NASDAQ", price=150.0, quantity=100, adv=1e9, is_sell=True
        )
        buy_fric = self.optimizer.calculate_single_leg_friction(
            symbol="AAPL", market="NASDAQ", price=150.0, quantity=100, adv=1e9, is_sell=False
        )
        # Buy leg should be strictly cheaper than sell leg by the SEC fee
        self.assertLess(buy_fric, sell_fric)

    def test_tc21_gatheral_3_2_power_scaling(self):
        """TC21: Verify Gatheral 3/2-power impact scales super-linearly with order size."""
        fric_small = self.optimizer.calculate_single_leg_friction(
            symbol="AAPL", market="NASDAQ", price=100.0, quantity=100, adv=1e6, volatility=0.25, is_sell=False
        )
        fric_large = self.optimizer.calculate_single_leg_friction(
            symbol="AAPL", market="NASDAQ", price=100.0, quantity=1000, adv=1e6, volatility=0.25, is_sell=False
        )
        # 10x quantity increases notional by 10x, but impact rate increases by 10^1.5 ≈ 31.6x
        # Total impact friction increases by 10 * 31.6 = 316x
        self.assertGreater(fric_large, 10.0 * fric_small)

    # =======================================================================
    # Category 5: Economic Hurdle Evaluation (Net Tax Alpha > Friction)
    # =======================================================================

    def test_tc22_economic_hurdle_invariant_pass(self):
        """TC22: Verify lot is eligible when Gross Tax Alpha > Total Friction."""
        # Deep loss: Cost = $200, Current = $100, Q = 500 => Loss = -$50,000.
        # Gross Alpha = 0.37 * 50,000 = $18,500.
        # Total Friction on $50k traded will be under $100.
        lot = TaxLot("L_DeepLoss", "AAPL", "NASDAQ", "2026-01-01", 500, 200.0, current_price=100.0)
        candidate = self.optimizer.evaluate_lot_for_harvesting(
            lot=lot,
            current_price=100.0,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        self.assertTrue(candidate.is_eligible)
        self.assertGreater(candidate.net_tax_alpha, 0.0)
        self.assertEqual(candidate.surrogate_symbol, "MSFT")

    def test_tc23_economic_hurdle_invariant_reject(self):
        """TC23: Verify lot is REJECTED when switching friction exceeds tax alpha."""
        # Tiny loss: Cost = $100.05, Current = $100.00, Q = 100.
        # Loss = $5.00. Gross Alpha = 0.37 * 5.00 = $1.85.
        # Friction on $10,000 round-trip (spread + fees) > $10.00.
        lot = TaxLot("L_TinyLoss", "AAPL", "NASDAQ", "2026-01-01", 100, 100.05, current_price=100.0)
        candidate = self.optimizer.evaluate_lot_for_harvesting(
            lot=lot,
            current_price=100.0,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        self.assertFalse(candidate.is_eligible)
        self.assertIn("ECONOMIC_HURDLE_FAILED", candidate.rejection_reason)
        self.assertLessEqual(candidate.net_tax_alpha, 0.0)

    def test_tc24_profitable_lot_rejected(self):
        """TC24: Verify lot with unrealized gain is rejected with NO_UNREALIZED_LOSS."""
        gain_lot = TaxLot("L_Gain", "AAPL", "NASDAQ", "2026-01-01", 100, 100.0, current_price=150.0)
        candidate = self.optimizer.evaluate_lot_for_harvesting(
            lot=gain_lot,
            current_price=150.0,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        self.assertFalse(candidate.is_eligible)
        self.assertIn("NO_UNREALIZED_LOSS", candidate.rejection_reason)

    def test_tc25_bps_hurdle_threshold(self):
        """TC25: Verify min_net_alpha_bps rejects lots that pass zero hurdle but fail bps hurdle."""
        opt_strict = DynamicTaxLossHarvestingOptimizer(
            config=TaxConfig(min_net_alpha_bps=50.0)  # Requires 50 bps net alpha
        )
        # Moderate loss lot: Notional = $10,000, Loss = $300. Gross alpha = $111.
        # Net alpha ≈ $95 (95 bps). Passes 50 bps hurdle.
        lot1 = TaxLot("L_Mod", "AAPL", "NASDAQ", "2026-01-01", 100, 103.0, current_price=100.0)
        cand1 = opt_strict.evaluate_lot_for_harvesting(
            lot=lot1,
            current_price=100.0,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        self.assertTrue(cand1.is_eligible)

        # Smaller loss lot: Loss = $80. Gross alpha = $29.60. Friction = $12. Net = $17.60 (17.6 bps).
        # Fails 50 bps hurdle!
        lot2 = TaxLot("L_Small", "AAPL", "NASDAQ", "2026-01-01", 100, 100.80, current_price=100.0)
        cand2 = opt_strict.evaluate_lot_for_harvesting(
            lot=lot2,
            current_price=100.0,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        self.assertFalse(cand2.is_eligible)
        self.assertIn("ECONOMIC_HURDLE_FAILED", cand2.rejection_reason)

    # =======================================================================
    # Category 6: Surrogate Asset Selection (rho >= 0.85, Same Sector)
    # =======================================================================

    def test_tc26_surrogate_selection_high_correlation(self):
        """TC26: Verify AAPL selects MSFT (same sector, rho > 0.85)."""
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            min_correlation=0.85
        )
        self.assertIsNotNone(surrogate)
        surr_sym, surr_corr = surrogate
        self.assertEqual(surr_sym, "MSFT")
        self.assertGreaterEqual(surr_corr, 0.85)

    def test_tc27_surrogate_selection_rejects_different_sector(self):
        """TC27: Verify candidates from different sectors are strictly ignored."""
        # Restrict sector map so AAPL has no other Tech peers
        restricted_sector_map = {
            "AAPL": "Information Technology",
            "JPM": "Financials",
            "BAC": "Financials",
        }
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_history_df,
            sector_map=restricted_sector_map,
            min_correlation=0.85
        )
        self.assertIsNone(surrogate)

    def test_tc28_surrogate_selection_rejects_low_correlation(self):
        """TC28: Verify candidate with correlation < 0.85 is rejected."""
        # NVDA has lower correlation with AAPL in our synthetic dataset
        restricted_sector_map = {
            "AAPL": "Information Technology",
            "NVDA": "Information Technology",
        }
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_history_df,
            sector_map=restricted_sector_map,
            min_correlation=0.85
        )
        self.assertIsNone(surrogate)

    def test_tc29_surrogate_selection_excludes_wash_sale_restricted(self):
        """TC29: Verify a symbol currently under wash-sale cooldown cannot be chosen as surrogate."""
        # Put MSFT on wash-sale restriction
        self.optimizer.wash_sale_tracker.record_loss_sale("MSFT", "2026-03-20", loss_amount=500.0)

        # Attempt to find surrogate for AAPL on 2026-03-25
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            min_correlation=0.85,
            as_of_date="2026-03-25"
        )
        # MSFT is restricted, NVDA is < 0.85, so no surrogate qualified
        self.assertIsNone(surrogate)

    def test_tc30_surrogate_adv_liquidity_cap(self):
        """TC30: Verify candidate is rejected if required order exceeds 1.5% of its ADV."""
        # Restrict MSFT ADV to very low
        tight_adv = {"AAPL": 1e9, "MSFT": 10000.0}  # ADV is $10k
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            min_correlation=0.85,
            adv_dict=tight_adv,
            required_notional=50000.0  # 50k / 10k = 500% > 1.5% ADV participation
        )
        self.assertIsNone(surrogate)

    def test_tc31_krx_surrogate_selection(self):
        """TC31: Verify KRX stocks (005930 Samsung) select 000660 (SK Hynix) as surrogate."""
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="005930",
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            min_correlation=0.85
        )
        self.assertIsNotNone(surrogate)
        surr_sym, surr_corr = surrogate
        self.assertEqual(surr_sym, "000660")
        self.assertGreaterEqual(surr_corr, 0.85)

    # =======================================================================
    # Category 7: Portfolio-Level Harvesting & HIFO Ordering (TC32~TC36)
    # =======================================================================

    def test_tc32_hifo_sort_ordering(self):
        """TC32: Verify HIFO sorts lots by highest cost basis per share descending."""
        lot1 = TaxLot("L1", "AAPL", "NASDAQ", "2026-01-01", 100, 150.0)
        lot2 = TaxLot("L2", "AAPL", "NASDAQ", "2026-01-05", 100, 180.0)
        lot3 = TaxLot("L3", "AAPL", "NASDAQ", "2026-01-10", 100, 160.0)

        sorted_lots = DynamicTaxLossHarvestingOptimizer.hifo_sort([lot1, lot2, lot3])
        self.assertEqual([lot.lot_id for lot in sorted_lots], ["L2", "L3", "L1"])

    def test_tc33_fifo_and_lifo_sort(self):
        """TC33: Verify FIFO and LIFO sorting mechanisms."""
        lot1 = TaxLot("L1", "AAPL", "NASDAQ", "2026-01-01", 100, 150.0)
        lot2 = TaxLot("L2", "AAPL", "NASDAQ", "2026-01-15", 100, 180.0)
        lot3 = TaxLot("L3", "AAPL", "NASDAQ", "2026-01-10", 100, 160.0)

        fifo = DynamicTaxLossHarvestingOptimizer.fifo_sort([lot1, lot2, lot3])
        self.assertEqual([lot.lot_id for lot in fifo], ["L1", "L3", "L2"])

        lifo = DynamicTaxLossHarvestingOptimizer.lifo_sort([lot1, lot2, lot3])
        self.assertEqual([lot.lot_id for lot in lifo], ["L2", "L3", "L1"])

    def test_tc34_portfolio_wide_harvesting_execution(self):
        """TC34: Verify full portfolio plan with mixed lots (profitable, harvestable, hurdle-failing)."""
        lots = [
            # 1. Harvestable US tech lot (Deep loss)
            TaxLot("L_AAPL_1", "AAPL", "NASDAQ", "2026-01-01", 200, 220.0, current_price=150.0),
            # 2. Profitable lot (Gain)
            TaxLot("L_MSFT_1", "MSFT", "NASDAQ", "2026-01-01", 100, 200.0, current_price=300.0),
            # 3. Tiny loss lot (Hurdle fail)
            TaxLot("L_JPM_1", "JPM", "NYSE", "2026-01-01", 50, 140.05, current_price=140.0),
            # 4. Harvestable KRX semi lot (Deep loss)
            TaxLot("L_SEC_1", "005930", "KOSPI", "2026-01-01", 100, 90000.0, current_price=70000.0),
        ]

        current_prices = {
            "AAPL": 150.0,
            "MSFT": 300.0,
            "JPM": 140.0,
            "005930": 70000.0
        }

        plan = self.optimizer.optimize_portfolio_harvesting(
            lots=lots,
            current_prices=current_prices,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01",
            auto_record_wash_sale=True
        )

        self.assertEqual(plan.candidates_screened, 4)
        # AAPL and 005930 should be recommended
        rec_ids = [c.lot.lot_id for c in plan.harvest_recommendations]
        self.assertIn("L_AAPL_1", rec_ids)
        self.assertIn("L_SEC_1", rec_ids)
        self.assertEqual(len(plan.harvest_recommendations), 2)

        # MSFT (gain) and JPM (hurdle fail) should be rejected
        rej_ids = [c.lot.lot_id for c in plan.rejected_candidates]
        self.assertIn("L_MSFT_1", rej_ids)
        self.assertIn("L_JPM_1", rej_ids)

        self.assertGreater(plan.total_gross_tax_savings, 0.0)
        self.assertGreater(plan.total_net_tax_alpha, 0.0)

    def test_tc35_auto_record_wash_sale_enforced(self):
        """TC35: Verify auto_record_wash_sale prevents re-harvesting or re-buying immediately."""
        lots = [
            TaxLot("L_AAPL_1", "AAPL", "NASDAQ", "2026-01-01", 200, 220.0, current_price=150.0)
        ]
        plan = self.optimizer.optimize_portfolio_harvesting(
            lots=lots,
            current_prices={"AAPL": 150.0},
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01",
            auto_record_wash_sale=True
        )
        self.assertEqual(len(plan.harvest_recommendations), 1)

        # WashSaleTracker should now restrict AAPL on 2026-04-10
        self.assertTrue(self.optimizer.wash_sale_tracker.is_restricted("AAPL", "2026-04-10"))
        self.assertIn("AAPL", plan.wash_sale_restricted_symbols)

    def test_tc36_generate_rebalance_orders(self):
        """TC36: Verify translation of TaxHarvestingPlan into paired SELL and BUY orders."""
        lot = TaxLot("L_AAPL", "AAPL", "NASDAQ", "2026-01-01", 100, 200.0, current_price=150.0)
        candidate = self.optimizer.evaluate_lot_for_harvesting(
            lot=lot,
            current_price=150.0,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        plan = TaxHarvestingPlan(
            as_of_date="2026-04-01",
            candidates_screened=1,
            harvest_recommendations=[candidate],
            rejected_candidates=[],
            total_gross_tax_savings=candidate.gross_tax_savings,
            total_switching_friction=candidate.switching_friction,
            total_net_tax_alpha=candidate.net_tax_alpha,
            wash_sale_restricted_symbols=[]
        )

        orders = self.optimizer.generate_rebalance_orders(plan)
        self.assertEqual(len(orders), 2)
        
        sell_order = orders[0]
        self.assertEqual(sell_order["action"], "SELL")
        self.assertEqual(sell_order["symbol"], "AAPL")
        self.assertEqual(sell_order["quantity"], 100.0)
        self.assertEqual(sell_order["order_type"], "TAX_HARVEST_LIQUIDATION")

        buy_order = orders[1]
        self.assertEqual(buy_order["action"], "BUY")
        self.assertEqual(buy_order["symbol"], "MSFT")
        self.assertEqual(buy_order["order_type"], "TAX_SURROGATE_REPLACEMENT")
        self.assertAlmostEqual(buy_order["target_notional"], sell_order["target_notional"], delta=100.0)

    # =======================================================================
    # Category 8: Edge Cases, Numerical Robustness & Date Handling (TC37~TC40)
    # =======================================================================

    def test_tc37_zero_quantity_or_price(self):
        """TC37: Verify zero quantity or zero price handled cleanly without exceptions."""
        lot_zero_q = TaxLot("L_ZeroQ", "AAPL", "NASDAQ", "2026-01-01", 0.0, 150.0, current_price=100.0)
        cand_q = self.optimizer.evaluate_lot_for_harvesting(
            lot=lot_zero_q,
            current_price=100.0,
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        self.assertFalse(cand_q.is_eligible)

        fric_zero = self.optimizer.calculate_single_leg_friction(
            "AAPL", "NASDAQ", price=0.0, quantity=100, adv=1e9
        )
        self.assertEqual(fric_zero, 0.0)

    def test_tc38_flat_price_history_zero_variance(self):
        """TC38: Verify flat price history (zero return std) does not trigger ZeroDivisionError."""
        flat_df = self.price_history_df.copy()
        flat_df["AAPL"] = 150.0  # Constant price
        surrogate = self.optimizer.find_surrogate_stock(
            symbol="AAPL",
            price_history_df=flat_df,
            sector_map=self.sector_map,
            min_correlation=0.85
        )
        self.assertIsNone(surrogate)

    def test_tc39_empty_portfolio_plan(self):
        """TC39: Verify empty lot list yields valid empty TaxHarvestingPlan."""
        plan = self.optimizer.optimize_portfolio_harvesting(
            lots=[],
            current_prices={},
            price_history_df=self.price_history_df,
            sector_map=self.sector_map,
            adv_dict=self.adv_dict,
            as_of_date="2026-04-01"
        )
        self.assertEqual(plan.candidates_screened, 0)
        self.assertEqual(len(plan.harvest_recommendations), 0)
        self.assertEqual(plan.total_gross_tax_savings, 0.0)
        self.assertEqual(plan.total_net_tax_alpha, 0.0)

    def test_tc40_date_parsing_formats(self):
        """TC40: Verify parse_date handles strings, dates, datetimes, and timestamps."""
        d1 = parse_date("2026-04-15")
        d2 = parse_date("2026/04/15")
        d3 = parse_date(datetime.date(2026, 4, 15))
        d4 = parse_date(datetime.datetime(2026, 4, 15, 9, 30))
        d5 = parse_date(pd.Timestamp("2026-04-15"))

        self.assertEqual(d1, d2)
        self.assertEqual(d2, d3)
        self.assertEqual(d3, d4)
        self.assertEqual(d4, d5)
        self.assertEqual(format_date(d1), "2026-04-15")


if __name__ == "__main__":
    unittest.main()
