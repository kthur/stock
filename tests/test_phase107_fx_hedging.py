"""
tests/test_phase107_fx_hedging.py — Comprehensive Unit, Integration & Adversarial Test Harness.

Phase 107 / Feature F506 / Release R123 (v114 Production Master)
Milestone 2: Global Cross-Market FX Hedging Engine.

Test Categories Covered:
- Category 1: Class Instantiation, Config, Attributes & Alias Trees (TC01~TC03)
- Category 2: Covered Interest Parity (CIP) Math & Forward Pricing (TC04~TC08)
- Category 3: Optimal Hedge Ratio Dynamics across 2D Market Regimes (TC09~TC13)
- Category 4: USD Depreciation Momentum & FX Volatility Scaling (TC14~TC17)
- Category 5: Carry Cost Drag & Interest Rate Differential Impact (TC18~TC20)
- Category 6: Cash Collateral Limit Enforcement (TC21~TC23)
- Category 7: Gross Portfolio Leverage Cap Enforcement (TC24~TC26)
- Category 8: Multi-Asset Portfolio Evaluation & Symbol Classification (TC27~TC30)
- Category 9: Structured Order Generation & OMS/Paper Trading Compatibility (TC31~TC33)
- Category 10: Backward-Compatible Legacy Overlay Interface (TC34~TC35)
- Category 11: Adversarial Monte Carlo Fuzzing & Numerical Boundary Continuity (TC36~TC38)
"""

from __future__ import annotations

import math
import os
import random
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# ---------------------------------------------------------------------------
# Path setup: Ensure repo root and trading_system are on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.risk.dynamic_fx_hedging_engine import (
    FXMacroInput,
    FXHedgeResult,
    DynamicFXHedgingEngine,
    GlobalCrossMarketFXHedgingEngine,
    Phase107DynamicFXHedgingEngine,
    FXHedgingEngine,
    CurrencyOverlayHedgingEngine,
)


class TestPhase107FXHedgingEngine(unittest.TestCase):
    """Test suite for Phase 107 Global Cross-Market FX Hedging Engine."""

    def setUp(self) -> None:
        """Set up standard test fixtures."""
        self.engine = DynamicFXHedgingEngine(
            base_currency="KRW",
            target_tenor_days=30,
            margin_requirement=0.10,
            max_gross_leverage=1.20,
            max_collateral_ratio=0.85,
            hedge_symbol="261250",
            baseline_hedge_ratio=0.30,
            target_fx_volatility=0.08,
        )

        self.std_macro = FXMacroInput(
            usdkrw_spot=1350.0,
            us_rate=0.045,
            kr_rate=0.035,
            forward_rate=None,
            tenor_days=30,
            fx_volatility_20d=0.08,
            fx_momentum_20d=0.0,
            regime_label="BULL_LOW_VOL",
        )

    # -----------------------------------------------------------------------
    # Category 1: Instantiation, Config, Attributes & Alias Trees
    # -----------------------------------------------------------------------

    def test_tc01_instantiation_and_attributes(self) -> None:
        """TC01: Verify default and custom attributes on engine."""
        eng = DynamicFXHedgingEngine()
        self.assertEqual(eng.base_currency, "KRW")
        self.assertEqual(eng.target_tenor_days, 30)
        self.assertAlmostEqual(eng.margin_requirement, 0.10)
        self.assertAlmostEqual(eng.max_gross_leverage, 1.20)
        self.assertAlmostEqual(eng.max_collateral_ratio, 0.85)
        self.assertEqual(eng.hedge_symbol, "261250")
        self.assertAlmostEqual(eng.baseline_hedge_ratio, 0.30)

    def test_tc02_complete_alias_trees(self) -> None:
        """TC02: Verify all 4 required alias classes are identical to DynamicFXHedgingEngine."""
        aliases = [
            GlobalCrossMarketFXHedgingEngine,
            Phase107DynamicFXHedgingEngine,
            FXHedgingEngine,
            CurrencyOverlayHedgingEngine,
        ]
        for alias in aliases:
            self.assertIs(alias, DynamicFXHedgingEngine)
            instance = alias()
            self.assertIsInstance(instance, DynamicFXHedgingEngine)

    def test_tc03_dataclasses_serialization(self) -> None:
        """TC03: Verify FXMacroInput and FXHedgeResult serialization and properties."""
        macro_in = FXMacroInput(usdkrw_spot=1350.0, tenor_days=365)
        self.assertAlmostEqual(macro_in.tau, 1.0, places=4)
        d_in = macro_in.to_dict()
        self.assertIsInstance(d_in, dict)
        self.assertEqual(d_in["usdkrw_spot"], 1350.0)

        res = FXHedgeResult(
            hedge_ratio=0.50,
            us_exposure_krw=10_000_000.0,
            hedge_notional_krw=5_000_000.0,
            hedge_weight=0.05,
            forward_premium_bps=-10.5,
            cip_deviation_bps=-2.3,
            collateral_required_krw=500_000.0,
            leverage_ratio=1.05,
            hedge_order_symbol="261250",
            hedge_action="BUY_HEDGE",
            reason="TEST_REASON",
            timestamp="2026-10-14T23:00:00Z",
        )
        d_res = res.to_dict()
        self.assertIsInstance(d_res, dict)
        self.assertEqual(d_res["hedge_ratio"], 0.50)
        self.assertEqual(d_res["hedge_action"], "BUY_HEDGE")

    # -----------------------------------------------------------------------
    # Category 2: Covered Interest Parity (CIP) Math & Forward Pricing
    # -----------------------------------------------------------------------

    def test_tc04_cip_forward_rate_calculation(self) -> None:
        """TC04: Verify Covered Interest Parity forward rate formula F = S*(1+r_kr*tau)/(1+r_us*tau)."""
        spot = 1350.0
        r_kr = 0.035
        r_us = 0.045
        tenor_days = 365
        tau = 365 / 365.0

        expected_f = spot * ((1.0 + r_kr * tau) / (1.0 + r_us * tau))
        calculated_f = self.engine.compute_cip_forward_rate(spot, r_kr, r_us, tenor_days)

        self.assertAlmostEqual(calculated_f, expected_f, places=4)
        # Since r_us > r_kr, forward rate must be lower than spot (USD forward discount)
        self.assertLess(calculated_f, spot)

    def test_tc05_cip_forward_rate_equal_interest_rates(self) -> None:
        """TC05: When r_kr == r_us, forward rate must equal spot rate."""
        spot = 1320.0
        r = 0.030
        calculated_f = self.engine.compute_cip_forward_rate(spot, r, r, 90)
        self.assertAlmostEqual(calculated_f, spot, places=4)

    def test_tc06_forward_premium_basis_points(self) -> None:
        """TC06: Verify forward premium in basis points: ((F - S) / S) * 10,000."""
        spot = 1000.0
        forward = 1010.0  # +1.0% = +100 bps
        prem_bps = self.engine.compute_forward_premium(spot, forward, 30)
        self.assertAlmostEqual(prem_bps, 100.0, places=2)

        forward_disc = 995.0  # -0.5% = -50 bps
        disc_bps = self.engine.compute_forward_premium(spot, forward_disc, 30)
        self.assertAlmostEqual(disc_bps, -50.0, places=2)

    def test_tc07_cip_deviation_calculation(self) -> None:
        """TC07: Verify CIP deviation / cross-currency basis in basis points."""
        spot = 1350.0
        r_kr = 0.035
        r_us = 0.045
        f_cip = self.engine.compute_cip_forward_rate(spot, r_kr, r_us, 30)

        # Exact CIP holds in market
        dev_exact = self.engine.compute_cip_deviation(spot, f_cip, r_kr, r_us, 30)
        self.assertAlmostEqual(dev_exact, 0.0, places=4)

        # Market forward is trading at 2 KRW discount relative to CIP
        f_market_disc = f_cip - 2.0
        dev_disc = self.engine.compute_cip_deviation(spot, f_market_disc, r_kr, r_us, 30)
        expected_dev = (-2.0 / spot) * 10000.0
        self.assertAlmostEqual(dev_disc, expected_dev, places=2)

        # None market forward defaults to 0.0 deviation
        self.assertAlmostEqual(self.engine.compute_cip_deviation(spot, None, r_kr, r_us, 30), 0.0)

    def test_tc08_cip_edge_cases_robustness(self) -> None:
        """TC08: Verify non-positive spot, infinite values, and zero tenor handled gracefully."""
        self.assertEqual(self.engine.compute_cip_forward_rate(0.0, 0.03, 0.04, 30), 0.0)
        self.assertEqual(self.engine.compute_cip_forward_rate(-100.0, 0.03, 0.04, 30), 0.0)
        self.assertEqual(self.engine.compute_forward_premium(0.0, 100.0, 30), 0.0)
        self.assertEqual(self.engine.compute_cip_deviation(-1.0, 1300.0, 0.03, 0.04, 30), 0.0)

    # -----------------------------------------------------------------------
    # Category 3: Optimal Hedge Ratio Dynamics across Regimes
    # -----------------------------------------------------------------------

    def test_tc09_optimal_hedge_ratio_boundedness_invariant(self) -> None:
        """TC09: Verify h* is strictly bounded in [0.0, 1.0] across all standard regimes."""
        regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS", "SIDEWAYS_HIGH_VOL",
            "BEAR", "BEAR_HIGH_VOL", "CRISIS", "CRISIS_ACTIVE", "CRISIS_SEVERE",
        ]
        for reg in regimes:
            macro = FXMacroInput(usdkrw_spot=1350.0, regime_label=reg)
            h = self.engine.calculate_optimal_hedge_ratio(macro)
            self.assertTrue(0.0 <= h <= 1.0, f"Violation in {reg}: h={h}")
            self.assertTrue(math.isfinite(h))

    def test_tc10_bear_high_vol_elevation(self) -> None:
        """TC10: BEAR_HIGH_VOL regime must produce significantly higher hedge ratio than BULL_LOW_VOL."""
        macro_bull = FXMacroInput(usdkrw_spot=1350.0, regime_label="BULL_LOW_VOL")
        macro_bear = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")

        h_bull = self.engine.calculate_optimal_hedge_ratio(macro_bull)
        h_bear = self.engine.calculate_optimal_hedge_ratio(macro_bear)

        self.assertGreater(h_bear, h_bull)
        self.assertGreaterEqual(h_bear, 0.50)

    def test_tc11_crisis_safe_haven_appreciation_dynamics(self) -> None:
        """TC11: In CRISIS when USD is appreciating (safe haven flight), hedge ratio drops near 0.0."""
        macro_crisis_usd_rally = FXMacroInput(
            usdkrw_spot=1400.0,
            fx_momentum_20d=0.03,  # USD surged 3% (safe haven flight)
            regime_label="CRISIS",
        )
        h_crisis_rally = self.engine.calculate_optimal_hedge_ratio(macro_crisis_usd_rally)

        # Korean investors benefit from USD rally during global crisis -> hedge stays very low
        self.assertLessEqual(h_crisis_rally, 0.15)
        self.assertGreaterEqual(h_crisis_rally, 0.0)

    def test_tc12_crisis_depreciating_usd_protection(self) -> None:
        """TC12: In CRISIS if USD is depreciating (double whammy), hedge ratio expands aggressively."""
        macro_crisis_usd_drop = FXMacroInput(
            usdkrw_spot=1300.0,
            fx_momentum_20d=-0.03,  # USD weakened 3% during crisis
            regime_label="CRISIS",
        )
        h_crisis_drop = self.engine.calculate_optimal_hedge_ratio(macro_crisis_usd_drop)

        self.assertGreaterEqual(h_crisis_drop, 0.60)
        self.assertLessEqual(h_crisis_drop, 1.0)

    def test_tc13_cip_tightness_increases_hedge_precaution(self) -> None:
        """TC13: Severe negative CIP deviation (FX liquidity freeze) increases hedge ratio."""
        macro_normal = FXMacroInput(
            usdkrw_spot=1350.0,
            forward_rate=None,  # 0 basis
            regime_label="BULL_LOW_VOL",
        )
        # Market forward trades at massive discount (-100 bps)
        f_cip = self.engine.compute_cip_forward_rate(1350.0, 0.035, 0.045, 30)
        macro_stressed = FXMacroInput(
            usdkrw_spot=1350.0,
            forward_rate=f_cip - 13.5,  # -100 bps
            regime_label="BULL_LOW_VOL",
        )

        h_normal = self.engine.calculate_optimal_hedge_ratio(macro_normal)
        h_stressed = self.engine.calculate_optimal_hedge_ratio(macro_stressed)

        self.assertGreater(h_stressed, h_normal)

    # -----------------------------------------------------------------------
    # Category 4: USD Depreciation Momentum & FX Volatility Scaling
    # -----------------------------------------------------------------------

    def test_tc14_usd_depreciation_momentum_monotonicity(self) -> None:
        """TC14: Stronger USD depreciation momentum (more negative return) monotonically increases hedge."""
        h_ratios = []
        # Momentum from +0.02 (appreciating) down to -0.04 (severely depreciating)
        mom_values = [0.02, 0.01, 0.0, -0.01, -0.02, -0.03, -0.04]
        for mom in mom_values:
            macro = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=mom, regime_label="BULL_LOW_VOL")
            h = self.engine.calculate_optimal_hedge_ratio(macro)
            h_ratios.append(h)

        # Verify monotonic non-decreasing as USD depreciation deepens
        for i in range(len(h_ratios) - 1):
            self.assertLessEqual(
                h_ratios[i],
                h_ratios[i + 1] + 1e-6,
                f"Monotonicity break between mom={mom_values[i]} ({h_ratios[i]}) and {mom_values[i+1]} ({h_ratios[i+1]})",
            )

    def test_tc15_fx_volatility_scaling_response(self) -> None:
        """TC15: Elevated FX volatility increases hedge ratio under high-vol regimes."""
        macro_low_vol = FXMacroInput(
            usdkrw_spot=1350.0, fx_volatility_20d=0.04, regime_label="BEAR_HIGH_VOL"
        )
        macro_high_vol = FXMacroInput(
            usdkrw_spot=1350.0, fx_volatility_20d=0.16, regime_label="BEAR_HIGH_VOL"
        )

        h_low = self.engine.calculate_optimal_hedge_ratio(macro_low_vol)
        h_high = self.engine.calculate_optimal_hedge_ratio(macro_high_vol)

        self.assertGreater(h_high, h_low)

    def test_tc16_extreme_momentum_clipping(self) -> None:
        """TC16: Extreme momentum (-100% or +100%) remains strictly bounded in [0.0, 1.0]."""
        macro_extreme_neg = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=-0.99)
        macro_extreme_pos = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=0.99)

        h_neg = self.engine.calculate_optimal_hedge_ratio(macro_extreme_neg)
        h_pos = self.engine.calculate_optimal_hedge_ratio(macro_extreme_pos)

        self.assertTrue(0.0 <= h_neg <= 1.0)
        self.assertTrue(0.0 <= h_pos <= 1.0)

    def test_tc17_extreme_volatility_clipping(self) -> None:
        """TC17: Extreme FX volatility (e.g. 500%) remains strictly bounded in [0.0, 1.0]."""
        macro_vol_100 = FXMacroInput(usdkrw_spot=1350.0, fx_volatility_20d=5.0)
        h = self.engine.calculate_optimal_hedge_ratio(macro_vol_100)
        self.assertTrue(0.0 <= h <= 1.0)

    # -----------------------------------------------------------------------
    # Category 5: Carry Cost Drag & Rate Differential
    # -----------------------------------------------------------------------

    def test_tc18_carry_cost_drag_reduces_hedge_ratio(self) -> None:
        """TC18: High US rate relative to KR rate (negative carry) dampens unnecessary hedging."""
        # US rate = 6.0%, KR rate = 2.0% -> Carry drag is 4.0% * 2.0 = 0.08
        macro_high_carry = FXMacroInput(
            usdkrw_spot=1350.0, us_rate=0.06, kr_rate=0.02, regime_label="BULL_LOW_VOL"
        )
        # US rate = 2.0%, KR rate = 4.0% -> Zero carry drag (positive forward carry)
        macro_pos_carry = FXMacroInput(
            usdkrw_spot=1350.0, us_rate=0.02, kr_rate=0.04, regime_label="BULL_LOW_VOL"
        )

        h_high_carry = self.engine.calculate_optimal_hedge_ratio(macro_high_carry)
        h_pos_carry = self.engine.calculate_optimal_hedge_ratio(macro_pos_carry)

        self.assertLess(h_high_carry, h_pos_carry)

    def test_tc19_zero_negative_interest_rates(self) -> None:
        """TC19: Zero or negative interest rates do not produce NaNs or domain errors."""
        macro_zero_rates = FXMacroInput(usdkrw_spot=1350.0, us_rate=0.0, kr_rate=-0.005)
        h = self.engine.calculate_optimal_hedge_ratio(macro_zero_rates)
        self.assertTrue(0.0 <= h <= 1.0)
        self.assertTrue(math.isfinite(h))

    def test_tc20_extreme_rate_differential_bounds(self) -> None:
        """TC20: Extreme interest rate differentials remain bounded in [0.0, 1.0]."""
        macro_huge_us = FXMacroInput(usdkrw_spot=1350.0, us_rate=0.30, kr_rate=0.01)
        macro_huge_kr = FXMacroInput(usdkrw_spot=1350.0, us_rate=0.01, kr_rate=0.30)

        h_huge_us = self.engine.calculate_optimal_hedge_ratio(macro_huge_us)
        h_huge_kr = self.engine.calculate_optimal_hedge_ratio(macro_huge_kr)

        self.assertTrue(0.0 <= h_huge_us <= 1.0)
        self.assertTrue(0.0 <= h_huge_kr <= 1.0)

    # -----------------------------------------------------------------------
    # Category 6: Cash Collateral Limit Enforcement
    # -----------------------------------------------------------------------

    def test_tc21_collateral_limit_strict_enforcement(self) -> None:
        """TC21: Required collateral must not exceed available_cash * 0.85."""
        capital = 100_000_000.0
        allocations = {"AAPL": 0.50}  # 50M KRW US exposure
        macro = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")  # High hedge ratio

        # Very tight cash: only 2,000,000 KRW available cash (max collateral = 1,700,000 KRW)
        available_cash = 2_000_000.0
        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=macro,
            available_cash_krw=available_cash,
        )

        max_allowed_col = available_cash * 0.85
        self.assertLessEqual(result.collateral_required_krw, max_allowed_col + 1e-4)
        self.assertTrue(result.details["collateral_limit_hit"])
        self.assertIn("COLLATERAL_CAPPED", result.reason)

    def test_tc22_zero_available_cash_collateral_blocks_hedge(self) -> None:
        """TC22: Zero available cash collateral forces hedge ratio and notional to 0.0."""
        capital = 50_000_000.0
        allocations = {"NVDA": 0.60}
        macro = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=macro,
            available_cash_krw=0.0,
        )

        self.assertEqual(result.hedge_ratio, 0.0)
        self.assertEqual(result.hedge_notional_krw, 0.0)
        self.assertEqual(result.collateral_required_krw, 0.0)
        self.assertEqual(result.hedge_action, "NO_HEDGE")

    def test_tc23_sufficient_cash_collateral_not_binding(self) -> None:
        """TC23: Abundant available cash collateral does not trigger collateral cap."""
        capital = 100_000_000.0
        allocations = {"MSFT": 0.40}
        macro = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")
        avail_cash = 50_000_000.0  # Plentiful cash

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=macro,
            available_cash_krw=avail_cash,
        )

        self.assertFalse(result.details["collateral_limit_hit"])
        self.assertAlmostEqual(result.hedge_ratio, result.details["unconstrained_h"], places=4)

    # -----------------------------------------------------------------------
    # Category 7: Gross Portfolio Leverage Cap Enforcement
    # -----------------------------------------------------------------------

    def test_tc24_gross_leverage_cap_strict_enforcement(self) -> None:
        """TC24: Total gross portfolio leverage must not exceed max_gross_leverage (1.20)."""
        capital = 100_000_000.0
        # Highly leveraged portfolio: 115% gross equity weight (1.15)
        # With max_gross_leverage=1.20, max allowable hedge weight is 1.20 - 1.15 = 0.05 (5.0%)
        allocations = {"AAPL": 0.80, "MSFT": 0.35}  # Gross equity = 1.15
        macro = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=macro,
            available_cash_krw=50_000_000.0,
        )

        self.assertLessEqual(result.leverage_ratio, 1.20 + 1e-4)
        self.assertLessEqual(result.hedge_weight, 0.05 + 1e-4)
        self.assertTrue(result.details["leverage_limit_hit"])
        self.assertIn("LEVERAGE_CAPPED", result.reason)

    def test_tc25_gross_equity_at_or_above_limit_blocks_hedge(self) -> None:
        """TC25: If equity allocation already equals or exceeds 1.20 leverage, hedge is 0.0."""
        capital = 100_000_000.0
        allocations = {"AAPL": 0.80, "NVDA": 0.45}  # Gross equity = 1.25 >= 1.20
        macro = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=macro,
            available_cash_krw=50_000_000.0,
        )

        self.assertEqual(result.hedge_ratio, 0.0)
        self.assertEqual(result.hedge_notional_krw, 0.0)
        self.assertEqual(result.hedge_action, "NO_HEDGE")

    def test_tc26_custom_leverage_limit_respected(self) -> None:
        """TC26: Custom max_gross_leverage (e.g. 1.05) is strictly respected."""
        custom_eng = DynamicFXHedgingEngine(max_gross_leverage=1.05)
        capital = 100_000_000.0
        allocations = {"AAPL": 1.00}
        macro = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")

        result = custom_eng.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=macro,
            available_cash_krw=50_000_000.0,
        )

        self.assertLessEqual(result.leverage_ratio, 1.05 + 1e-4)
        self.assertLessEqual(result.hedge_weight, 0.05 + 1e-4)

    # -----------------------------------------------------------------------
    # Category 8: Multi-Asset Portfolio Evaluation & Symbol Classification
    # -----------------------------------------------------------------------

    def test_tc27_is_us_asset_classification(self) -> None:
        """TC27: Verify accurate identification of US assets vs KRX assets."""
        us_tickers = ["AAPL", "MSFT", "NVDA", "SPY", "QQQ", "BRK.B", "GOOGL", "AMZN"]
        kr_tickers = ["005930", "000660", "035720", "261250", "005930.KS", "091990.KQ"]

        for sym in us_tickers:
            self.assertTrue(DynamicFXHedgingEngine.is_us_asset(sym), f"Should be US: {sym}")

        for sym in kr_tickers:
            self.assertFalse(DynamicFXHedgingEngine.is_us_asset(sym), f"Should be KRX: {sym}")

    def test_tc28_pure_krx_portfolio_yields_no_hedge(self) -> None:
        """TC28: Portfolio with 100% KRX assets has 0 USD exposure and requires NO_HEDGE."""
        capital = 100_000_000.0
        allocations = {"005930": 0.40, "000660": 0.30, "035420": 0.20}

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=self.std_macro,
        )

        self.assertEqual(result.us_exposure_krw, 0.0)
        self.assertEqual(result.hedge_ratio, 0.0)
        self.assertEqual(result.hedge_notional_krw, 0.0)
        self.assertEqual(result.hedge_action, "NO_HEDGE")
        self.assertEqual(result.reason, "NO_US_EQUITY_EXPOSURE")

    def test_tc29_mixed_krx_and_us_portfolio(self) -> None:
        """TC29: Mixed portfolio isolates only US equity exposure for hedging."""
        capital = 100_000_000.0
        # 60% KRX (60M KRW), 30% US (30M KRW)
        allocations = {"005930": 0.60, "AAPL": 0.20, "MSFT": 0.10}

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=self.std_macro,
            available_cash_krw=20_000_000.0,
        )

        expected_us_exposure = 30_000_000.0
        self.assertAlmostEqual(result.us_exposure_krw, expected_us_exposure, places=2)
        expected_notional = expected_us_exposure * result.hedge_ratio
        self.assertAlmostEqual(result.hedge_notional_krw, expected_notional, places=2)
        self.assertEqual(result.hedge_action, "BUY_HEDGE")

    def test_tc30_portfolio_allocation_as_monetary_values(self) -> None:
        """TC30: Evaluate portfolio allocations provided as monetary values (KRW) instead of weights."""
        capital = 100_000_000.0
        allocations = {"005930": 50_000_000.0, "AAPL": 30_000_000.0, "NVDA": 10_000_000.0}

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=self.std_macro,
            available_cash_krw=15_000_000.0,
        )

        expected_us_exposure = 40_000_000.0
        self.assertAlmostEqual(result.us_exposure_krw, expected_us_exposure, places=2)
        self.assertAlmostEqual(result.details["w_us"], 0.40, places=4)

    # -----------------------------------------------------------------------
    # Category 9: Structured Order Generation & OMS Compatibility
    # -----------------------------------------------------------------------

    def test_tc31_generate_fx_hedge_order_structure(self) -> None:
        """TC31: Generate structured execution order matching OMS / PaperTradingDaemon specification."""
        capital = 100_000_000.0
        allocations = {"AAPL": 0.50}

        result = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=self.std_macro,
            available_cash_krw=20_000_000.0,
        )

        order = self.engine.generate_fx_hedge_order(result)
        self.assertIsNotNone(order)
        self.assertTrue(order["order_id"].startswith("FX_HEDGE_"))
        self.assertEqual(order["symbol"], "261250")
        self.assertEqual(order["market"], "KRX")
        self.assertEqual(order["side"], "BUY")
        self.assertEqual(order["action"], "BUY_HEDGE")
        self.assertEqual(order["order_type"], "MARKET")
        self.assertAlmostEqual(order["notional_krw"], result.hedge_notional_krw)
        self.assertAlmostEqual(order["hedge_ratio"], result.hedge_ratio)
        self.assertAlmostEqual(order["collateral_required_krw"], result.collateral_required_krw)

    def test_tc32_no_order_emitted_when_hedge_zero(self) -> None:
        """TC32: generate_fx_hedge_order returns None when hedge ratio is 0.0 or exposure is 0.0."""
        zero_res = FXHedgeResult(
            hedge_ratio=0.0,
            us_exposure_krw=0.0,
            hedge_notional_krw=0.0,
            hedge_weight=0.0,
            forward_premium_bps=0.0,
            cip_deviation_bps=0.0,
            collateral_required_krw=0.0,
            leverage_ratio=1.0,
            hedge_order_symbol="261250",
            hedge_action="NO_HEDGE",
            reason="NO_US_EQUITY_EXPOSURE",
            timestamp="2026-10-14T23:00:00Z",
        )
        self.assertIsNone(self.engine.generate_fx_hedge_order(zero_res))

    def test_tc33_custom_hedge_instrument_symbol(self) -> None:
        """TC33: Verify engine respects custom hedge symbol (e.g. synthetic forward or alternate ETF)."""
        custom_eng = DynamicFXHedgingEngine(hedge_symbol="USDKRW_SYNTHETIC_FORWARD")
        capital = 50_000_000.0
        allocations = {"AAPL": 0.40}

        result = custom_eng.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=allocations,
            macro_input=self.std_macro,
        )
        order = custom_eng.generate_fx_hedge_order(result)
        self.assertIsNotNone(order)
        self.assertEqual(order["symbol"], "USDKRW_SYNTHETIC_FORWARD")

    # -----------------------------------------------------------------------
    # Category 10: Backward-Compatible Legacy Interface
    # -----------------------------------------------------------------------

    def test_tc34_legacy_calculate_optimal_fx_overlay_interface(self) -> None:
        """TC34: Verify calculate_optimal_fx_overlay classmethod matches legacy signature & keys."""
        out = DynamicFXHedgingEngine.calculate_optimal_fx_overlay(
            us_portfolio_weight=0.40,
            usdkrw_series=None,
            us_yield=0.045,
            kr_yield=0.035,
            regime="BULL_LOW_VOL",
        )
        expected_keys = {
            "us_portfolio_weight", "fx_hedge_ratio", "fx_hedge_weight",
            "is_usd_downtrend", "rate_diff_bps", "status"
        }
        self.assertTrue(expected_keys.issubset(out.keys()))
        self.assertEqual(out["status"], "ACTIVE_FX_OVERLAY")
        self.assertTrue(0.0 <= out["fx_hedge_ratio"] <= 1.0)
        self.assertAlmostEqual(out["rate_diff_bps"], 100.0, places=2)

    def test_tc35_legacy_overlay_insignificant_weight(self) -> None:
        """TC35: Legacy overlay returns NO_US_EXPOSURE when weight <= 0.01."""
        out = DynamicFXHedgingEngine.calculate_optimal_fx_overlay(us_portfolio_weight=0.005)
        self.assertEqual(out["status"], "NO_US_EXPOSURE")
        self.assertEqual(out["fx_hedge_ratio"], 0.0)

    # -----------------------------------------------------------------------
    # Category 11: Adversarial Monte Carlo Fuzzing & Invariant Guarantees
    # -----------------------------------------------------------------------

    def test_tc36_adversarial_monte_carlo_fuzzing_hedge_ratio(self) -> None:
        """TC36: 1,000 Monte Carlo randomized parameter sets must strictly satisfy h* in [0.0, 1.0]."""
        random.seed(42)
        np.random.seed(42)

        regimes = [
            "BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS", "SIDEWAYS_HIGH_VOL",
            "BEAR", "BEAR_HIGH_VOL", "CRISIS", "UNKNOWN_REGIME",
        ]

        for trial in range(1000):
            spot = random.uniform(500.0, 3000.0)
            us_rate = random.uniform(-0.05, 0.25)
            kr_rate = random.uniform(-0.05, 0.25)
            forward_rate = random.choice([None, random.uniform(500.0, 3000.0)])
            tenor_days = random.randint(1, 365)
            vol_20d = random.uniform(0.001, 1.50)
            mom_20d = random.uniform(-0.50, 0.50)
            regime = random.choice(regimes)

            macro = FXMacroInput(
                usdkrw_spot=spot,
                us_rate=us_rate,
                kr_rate=kr_rate,
                forward_rate=forward_rate,
                tenor_days=tenor_days,
                fx_volatility_20d=vol_20d,
                fx_momentum_20d=mom_20d,
                regime_label=regime,
            )

            h = self.engine.calculate_optimal_hedge_ratio(macro)
            self.assertTrue(
                math.isfinite(h),
                f"Non-finite h={h} on trial {trial} with macro={macro}",
            )
            self.assertTrue(
                0.0 <= h <= 1.0,
                f"Bounds violation h={h} on trial {trial} with macro={macro}",
            )

    def test_tc37_adversarial_monte_carlo_portfolio_evaluation(self) -> None:
        """TC37: 500 Monte Carlo randomized portfolio sweeps verify leverage & collateral bounds."""
        random.seed(1337)

        tickers = ["AAPL", "MSFT", "NVDA", "SPY", "005930", "000660", "035420"]

        for trial in range(500):
            capital = random.uniform(1_000_000.0, 500_000_000.0)
            avail_cash = random.uniform(0.0, capital * 0.5)

            # Generate random allocations
            n_assets = random.randint(1, len(tickers))
            chosen = random.sample(tickers, n_assets)
            allocs = {sym: random.uniform(0.01, 0.40) for sym in chosen}

            macro = FXMacroInput(
                usdkrw_spot=random.uniform(900.0, 1600.0),
                us_rate=random.uniform(0.01, 0.10),
                kr_rate=random.uniform(0.01, 0.10),
                tenor_days=random.choice([15, 30, 60, 90]),
                fx_volatility_20d=random.uniform(0.02, 0.30),
                fx_momentum_20d=random.uniform(-0.10, 0.10),
                regime_label=random.choice(["BULL_LOW_VOL", "BEAR_HIGH_VOL", "CRISIS"]),
            )

            result = self.engine.evaluate_portfolio_fx_hedge(
                portfolio_capital_krw=capital,
                portfolio_allocations=allocs,
                macro_input=macro,
                available_cash_krw=avail_cash,
            )

            # Invariant 1: h* in [0.0, 1.0]
            self.assertTrue(0.0 <= result.hedge_ratio <= 1.0)
            self.assertTrue(math.isfinite(result.hedge_ratio))

            # Invariant 2: Collateral limit guard (req_col <= avail_cash * 0.85 + tolerance)
            max_col = avail_cash * 0.85
            self.assertLessEqual(
                result.collateral_required_krw,
                max_col + 1e-4,
                f"Collateral limit breached on trial {trial}: req={result.collateral_required_krw}, max={max_col}",
            )

            # Invariant 3: Gross leverage cap (leverage <= 1.20 + tolerance)
            # Gross equity may already exceed 1.20 if input allocs were extreme, but hedge cannot push it further
            w_gross_equity = result.details["w_gross_equity"]
            if w_gross_equity <= 1.20:
                self.assertLessEqual(
                    result.leverage_ratio,
                    1.20 + 1e-4,
                    f"Leverage limit breached on trial {trial}: lev={result.leverage_ratio}",
                )

    def test_tc38_extreme_pathological_inputs(self) -> None:
        """TC38: Engine handles NaN, Inf, empty allocations and non-finite floats without raising."""
        pathological_macro = FXMacroInput(
            usdkrw_spot=float("nan"),
            us_rate=float("inf"),
            kr_rate=float("-inf"),
            tenor_days=0,
            fx_volatility_20d=float("nan"),
            fx_momentum_20d=float("inf"),
            regime_label="INVALID_REGIME",
        )

        h = self.engine.calculate_optimal_hedge_ratio(pathological_macro)
        self.assertTrue(0.0 <= h <= 1.0)
        self.assertTrue(math.isfinite(h))

        res = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=-1000.0,
            portfolio_allocations={},
            macro_input=pathological_macro,
            available_cash_krw=-500.0,
        )
        self.assertEqual(res.hedge_ratio, 0.0)
        self.assertEqual(res.hedge_action, "NO_HEDGE")


if __name__ == "__main__":
    unittest.main()
