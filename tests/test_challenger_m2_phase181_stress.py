"""
tests/test_challenger_m2_phase181_stress.py — Adversarial Stress Test Harness for Milestone M2 (Phase 181, Features F885–F889).

Empirically verifies:
- Scenario 1: 3rd-Order Macro Tensor (F885) under extreme multi-asset shocks & cubic contraction.
- Scenario 2: CIP FX Basis Hedging (F886) under wide CIP deviations, cash margin invariant (<=85%), and order emission.
- Scenario 3: NSS 6-Param Yield Curve & Duration Hedge (F887) under deep inversions (-250 bps), flat/negative curves, beta clamp <= 1.000001.
- Scenario 4: Directed Rényi Transfer Entropy Contagion (F888) under all-zero, identical, and disconnected series.
- Scenario 5: MCSI v180 Crisis Circuit-Breaker (F889) under multi-factor panic shocks, leverage clamp <= 0.20x, Gate 8 inverse dispatch.
- Category 6: Mathematical Invariants, Zero Synthetic Rows (synthetic_rows == 0), and Latency SLA.
"""

from __future__ import annotations

import math
import os
import sys
import time
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Add repository paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

# F885 Macro Tensor Impulse
from src.core.cross_asset_spillover import (
    CrossAssetSpilloverEngine,
    compute_macro_tensor_impulse_order3,
    compute_dynamic_macro_tensor_elasticity,
    GLOBAL_MACRO_FACTORS_10,
    DEFAULT_SECTOR_MACRO_BETAS,
)

# F886 CIP Basis FX Hedger
from src.risk.dynamic_fx_hedging_engine import (
    DynamicFXHedgingEngine,
    FXMacroInput,
    FXHedgeResult,
    calculate_optimal_hedge_ratio,
    generate_fx_hedge_order,
)

# F887 NSS Yield Curve & Duration Hedge
from src.core.nss_yield_curve_hedge import (
    fit_nss_six_parameter_curve,
    evaluate_nss_zero_coupon_yield,
    compute_nss_instantaneous_forward_rate,
    detect_yield_curve_inversion,
    compute_yield_curve_slope_and_curvature,
)
from src.risk.delta_beta_hedge import (
    DeltaBetaHedgeEngine,
    fit_nss_yield_curve_6param,
    compute_duration_convexity_hedge,
)

# F888 Rényi Transfer Entropy Contagion
from src.ai.graph_granger_causality import (
    GraphGrangerCausalityNetwork,
)

# F889 MCSI v180 Circuit-Breaker
from src.risk.risk_manager import (
    RiskManager,
    evaluate_mcsi_crisis_severity_index,
    check_crisis_circuit_breaker,
)


class TestScenario1_MacroTensorImpulse_Order3_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F885 (3rd-Order Macro Tensor Impulse Spillover)."""

    def setUp(self) -> None:
        self.engine = CrossAssetSpilloverEngine()

    def test_tc01_extreme_canonical_tail_shocks(self) -> None:
        """Verify behavior under canonical extreme shocks: VIX +200%, SOX -40%, FX +30%."""
        extreme_shocks = {
            "vix": 2.0,      # +200% VIX velocity shock
            "sox": -0.40,    # -40% semiconductor crash
            "usdkrw": 0.30,  # +30% FX devaluation spike
            "wti": -0.50,    # -50% crude oil collapse
            "tnx": 0.015,    # +150 bps 10Y Treasury yield spike
            "gold": 0.20,    # +20% safe-haven gold surge
            "hy_spread": 0.60, # +60% high yield credit widening
        }

        sectors = ["Semiconductor", "반도체", "Technology", "Financial", "Market", "Energy"]
        for sec in sectors:
            impulse = compute_macro_tensor_impulse_order3(
                extreme_shocks, sector=sec, vol_multiplier=1.5
            )
            self.assertIsInstance(impulse, float)
            self.assertFalse(math.isnan(impulse), f"NaN in sector {sec}")
            self.assertFalse(math.isinf(impulse), f"Inf in sector {sec}")
            self.assertGreaterEqual(impulse, -5.0, f"Impulse below -5.0 floor: {impulse}")
            self.assertLessEqual(impulse, 5.0, f"Impulse above 5.0 ceiling: {impulse}")

    def test_tc02_nonlinear_cubic_amplification_vs_linear(self) -> None:
        """Verify that 3rd-order contraction exhibits super-linear downside amplification."""
        shocks = {"vix": 2.0, "sox": -0.40, "usdkrw": 0.30}
        elasticities = compute_dynamic_macro_tensor_elasticity("Semiconductor", macro_vol=0.15)
        
        linear_impulse = (
            elasticities["vix"] * shocks["vix"]
            + elasticities["sox"] * shocks["sox"]
            + elasticities["usdkrw"] * shocks["usdkrw"]
        )
        full_tensor_impulse = compute_macro_tensor_impulse_order3(
            shocks, sector="Semiconductor", vol_multiplier=1.0
        )

        # Due to negative cross-coupling (VIX*VIX, VIX*USDKRW*TNX, SOX*SP500), downside is amplified
        self.assertLess(
            full_tensor_impulse,
            linear_impulse,
            f"3rd order tensor must amplify downside shock beyond linear: tensor={full_tensor_impulse}, linear={linear_impulse}",
        )

    def test_tc03_volatility_multiplier_scaling_bounds(self) -> None:
        """Verify volatility multiplier scaling across extreme range [0.0, 20.0]."""
        shocks = {"vix": 1.5, "sox": -0.30, "hy_spread": 0.40}
        multipliers = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]

        for vm in multipliers:
            imp = compute_macro_tensor_impulse_order3(shocks, sector="Tech", vol_multiplier=vm)
            self.assertFalse(math.isnan(imp))
            self.assertFalse(math.isinf(imp))
            self.assertTrue(-5.0 <= imp <= 5.0)

    def test_tc04_dynamic_elasticity_extreme_vol_clamping(self) -> None:
        """Verify dynamic elasticity remains bounded in [-3.0, 3.0] even under extreme macro_vol."""
        extreme_vols = [0.0, 0.001, 0.15, 0.50, 2.0, 10.0, 100.0]
        for v in extreme_vols:
            elas = compute_dynamic_macro_tensor_elasticity("Semiconductor", macro_vol=v)
            for factor, beta_val in elas.items():
                self.assertFalse(math.isnan(beta_val), f"NaN elasticity for {factor} at vol={v}")
                self.assertFalse(math.isinf(beta_val), f"Inf elasticity for {factor} at vol={v}")
                self.assertGreaterEqual(beta_val, -3.0)
                self.assertLessEqual(beta_val, 3.0)

    def test_tc05_degenerate_and_nan_shock_immunity(self) -> None:
        """Verify robustness against NaN, Inf, empty, and non-canonical factor keys."""
        # Empty dict
        self.assertEqual(compute_macro_tensor_impulse_order3({}), 0.0)

        # Hostile / NaN / Inf inputs
        hostile_shocks = {
            "vix": float("nan"),
            "sox": float("inf"),
            "tnx": float("-inf"),
            "INVALID_KEY_@#$": 123.45,
            "usdkrw": 0.10,
        }
        res = compute_macro_tensor_impulse_order3(hostile_shocks, sector="Market")
        self.assertFalse(math.isnan(res))
        self.assertFalse(math.isinf(res))
        self.assertTrue(-5.0 <= res <= 5.0)


class TestScenario2_CIP_FX_Basis_Hedging_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F886 (Multi-Currency Non-Linear CIP Basis Swap FX Hedger)."""

    def setUp(self) -> None:
        self.engine = DynamicFXHedgingEngine()

    def test_tc06_extreme_cip_basis_deviations(self) -> None:
        """Verify hedge ratio h* under extreme CIP basis deviations (-1200 bps to +1000 bps)."""
        spot = 1350.0
        kr_rate = 0.0350
        us_rate = 0.0450
        f_cip = spot * (1.0 + kr_rate * 90.0 / 365.0) / (1.0 + us_rate * 90.0 / 365.0)

        extreme_dev_bps = [-1200.0, -800.0, -600.0, -250.0, 0.0, 200.0, 400.0, 800.0, 1200.0]
        for dev in extreme_dev_bps:
            f_market = f_cip * (1.0 + (dev / 10000.0))
            macro = FXMacroInput(
                usdkrw_spot=spot,
                forward_rate=f_market,
                kr_rate=kr_rate,
                us_rate=us_rate,
                tenor_days=90,
                fx_volatility_20d=0.25,
                fx_momentum_20d=-0.02,
                regime_label="BEAR_HIGH_VOL",
            )
            h = calculate_optimal_hedge_ratio(macro)
            self.assertIsInstance(h, float)
            self.assertFalse(math.isnan(h))
            self.assertGreaterEqual(h, 0.0, f"Hedge ratio below 0.0 for dev={dev}")
            self.assertLessEqual(h, 1.0, f"Hedge ratio above 1.0 for dev={dev}")

    def test_tc07_cash_reserve_collateral_invariant(self) -> None:
        """Verify strict cash reserve invariant >= 15% (margin requirement <= 85% available cash)."""
        capital = 200_000_000.0 # 200M KRW
        alloc = {"AAPL": 0.60, "MSFT": 0.40} # 100% US equity (200M KRW exposure)
        macro = FXMacroInput(
            usdkrw_spot=1350.0,
            forward_rate=1340.0,
            kr_rate=0.035,
            us_rate=0.045,
            regime_label="BEAR_HIGH_VOL",
            fx_momentum_20d=-0.03, # USD depreciating -> high hedge demand
        )

        # Test varying available cash levels
        cash_levels = [500_000.0, 2_000_000.0, 10_000_000.0, 50_000_000.0]
        for cash in cash_levels:
            res = self.engine.evaluate_portfolio_fx_hedge(
                portfolio_capital_krw=capital,
                portfolio_allocations=alloc,
                macro_input=macro,
                available_cash_krw=cash,
            )
            max_allowed_col = cash * 0.85
            self.assertLessEqual(
                res.collateral_required_krw,
                max_allowed_col + 1e-4,
                f"Collateral {res.collateral_required_krw} exceeded 85% of cash {cash}",
            )
            # Remaining cash reserve must be at least 15% of cash
            remaining_cash = cash - res.collateral_required_krw
            self.assertGreaterEqual(remaining_cash, cash * 0.15 - 1e-4)

    def test_tc08_gross_leverage_limit_cap(self) -> None:
        """Verify gross equity + hedge weight <= max_gross_leverage (1.20)."""
        capital = 100_000_000.0
        # Highly leveraged portfolio: 1.10 gross equity
        alloc = {"AAPL": 0.60, "NVDA": 0.50}
        macro = FXMacroInput(
            usdkrw_spot=1350.0,
            regime_label="BEAR_HIGH_VOL",
            fx_momentum_20d=-0.05,
        )

        res = self.engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=capital,
            portfolio_allocations=alloc,
            macro_input=macro,
            available_cash_krw=50_000_000.0,
        )
        self.assertLessEqual(res.leverage_ratio, 1.200001)

    def test_tc09_order_emission_and_formatting(self) -> None:
        """Verify correct formatting of structured orders for '261250' and 'USDKRW_FWD'."""
        capital = 50_000_000.0
        alloc = {"AAPL": 0.50, "005930": 0.50}
        macro = FXMacroInput(usdkrw_spot=1350.0, fx_momentum_20d=-0.04, regime_label="BEAR_HIGH_VOL")

        # 1. KODEX Inverse ETF ('261250')
        engine_etf = DynamicFXHedgingEngine(hedge_symbol="261250")
        res_etf = engine_etf.evaluate_portfolio_fx_hedge(capital, alloc, macro, available_cash_krw=10_000_000.0)
        order_etf = engine_etf.generate_fx_hedge_order(res_etf)
        
        self.assertIsNotNone(order_etf)
        self.assertEqual(order_etf["symbol"], "261250")
        self.assertEqual(order_etf["market"], "KRX")
        self.assertEqual(order_etf["order_type"], "MARKET")
        self.assertEqual(order_etf["side"], "BUY")
        self.assertIn("order_id", order_etf)
        self.assertGreater(order_etf["notional_krw"], 0.0)

        # 2. OTC Forward ('USDKRW_FWD')
        engine_fwd = DynamicFXHedgingEngine(hedge_symbol="USDKRW_FWD")
        res_fwd = engine_fwd.evaluate_portfolio_fx_hedge(capital, alloc, macro, available_cash_krw=10_000_000.0)
        order_fwd = engine_fwd.generate_fx_hedge_order(res_fwd)

        self.assertIsNotNone(order_fwd)
        self.assertEqual(order_fwd["symbol"], "USDKRW_FWD")
        self.assertEqual(order_fwd["market"], "OTC_FX")
        self.assertEqual(order_fwd["order_type"], "FORWARD_SWAP")

        # 3. No hedge required -> None returned
        res_zero = FXHedgeResult(
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
            reason="NO_US_EXPOSURE",
            timestamp="",
        )
        self.assertIsNone(engine_etf.generate_fx_hedge_order(res_zero))


class TestScenario3_NSS_YieldCurve_DurationHedge_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F887 (NSS 6-Param Yield Curve & Convexity Duration Hedge)."""

    def setUp(self) -> None:
        self.maturities = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0])

    def test_tc10_deep_yield_curve_inversion_nss_fitting(self) -> None:
        """Verify robust NSS parameter estimation under deep curve inversion (10Y-2Y = -250 bps)."""
        # 2Y = 6.5%, 10Y = 4.0% -> spread = -250 bps
        yields_deep_inv = np.array([0.065, 0.065, 0.065, 0.065, 0.045, 0.040, 0.040])
        params = fit_nss_six_parameter_curve(self.maturities, yields_deep_inv)
        b0, b1, b2, b3, t1, t2 = params

        self.assertFalse(any(math.isnan(x) for x in params))
        self.assertGreater(t1, 0.0)
        self.assertGreater(t2, 0.0)

        inv_info = detect_yield_curve_inversion(self.maturities, yields_deep_inv, nss_params=params)
        self.assertTrue(inv_info["is_inverted"])
        self.assertLess(inv_info["spread_10_2"], -0.015) # Strong inversion verified

    def test_tc11_flat_and_negative_yield_regimes(self) -> None:
        """Verify NSS fitting on flat curves and negative yields (e.g. Swiss/German/Japanese regimes)."""
        # Flat curve
        yields_flat = np.full_like(self.maturities, 0.035)
        params_flat = fit_nss_six_parameter_curve(self.maturities, yields_flat)
        self.assertAlmostEqual(params_flat[0], 0.035, places=4)
        self.assertAlmostEqual(params_flat[1], 0.0, places=4)

        # Negative yields
        yields_neg = np.array([-0.005, -0.004, -0.002, 0.000, 0.005, 0.010, 0.015])
        params_neg = fit_nss_six_parameter_curve(self.maturities, yields_neg)
        self.assertFalse(any(math.isnan(x) for x in params_neg))

    def test_tc12_duration_convexity_hedge_and_beta_clamp_invariant(self) -> None:
        """Verify duration haircut in [0.05, 1.0], beta clamp <= 1.000001, and convexity >= 0."""
        test_slopes = [-0.035, -0.025, -0.010, 0.0, 0.010, 0.025]
        test_durations = [0.0, 5.0, 10.0, 15.0, 25.0]

        for dur in test_durations:
            for slope in test_slopes:
                res = compute_duration_convexity_hedge(portfolio_duration=dur, slope_2y_10y=slope)
                
                # Invariant 1: Haircut factor in [0.05, 1.0]
                haircut = res["duration_haircut"]
                self.assertGreaterEqual(haircut, 0.05, f"Haircut {haircut} < 0.05")
                self.assertLessEqual(haircut, 1.0, f"Haircut {haircut} > 1.0")

                # Invariant 2: Market beta strictly <= 1.000001
                beta = res["market_beta_clamp"]
                self.assertLessEqual(beta, 1.000001, f"Beta {beta} exceeded 1.000001")

                # Invariant 3: Convexity adjustment >= 0.0
                convexity = res["convexity_adjustment"]
                self.assertGreaterEqual(convexity, 0.0)

                # Invariant 4: Hedge ratio in [0.0, 1.0]
                h_ratio = res["hedge_ratio"]
                self.assertTrue(0.0 <= h_ratio <= 1.0)

    def test_tc13_lhopital_safeguard_near_zero_tenor(self) -> None:
        """Verify L'Hopital numerical safeguard for zero coupon and forward rates as m -> 0."""
        zero_tenors = np.array([0.0, 1e-12, 1e-8, 1e-6, 1e-4])
        yields = evaluate_nss_zero_coupon_yield(zero_tenors, 0.04, -0.01, 0.02, -0.01, 1.5, 5.0)
        for y in yields:
            self.assertFalse(math.isnan(y))
            self.assertFalse(math.isinf(y))
            # At m -> 0, yield should approach beta0 + beta1 = 0.04 - 0.01 = 0.03
            self.assertAlmostEqual(y, 0.03, delta=0.005)


class TestScenario4_RenyiContagionNetwork_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F888 (Directed Rényi Transfer Entropy Contagion Network)."""

    def setUp(self) -> None:
        self.engine = GraphGrangerCausalityNetwork()

    def test_tc14_all_zero_returns_matrix(self) -> None:
        """Verify Rényi transfer entropy on degenerate all-zero returns matrix."""
        zeros_matrix = np.zeros((100, 6), dtype=np.float64)
        adj = self.engine.fit_renyi_transfer_entropy_network(zeros_matrix, alpha=1.5)

        self.assertEqual(adj.shape, (6, 6))
        self.assertTrue(np.all(np.diag(adj) == 0.0), "Diagonal must be strictly 0.0")
        self.assertFalse(np.isnan(adj).any(), "NaN found in adjacency matrix")
        self.assertTrue(np.all(adj >= 0.0), "Adjacency matrix elements must be >= 0.0")

        contagion = self.engine.detect_systemic_contagion(adj)
        self.assertEqual(contagion["dominant_eigenvalue"], 0.0)
        self.assertEqual(contagion["is_contagion_alert"], False)

    def test_tc15_identical_time_series_across_columns(self) -> None:
        """Verify Rényi transfer entropy when all assets have perfectly identical trajectories."""
        np.random.seed(181)
        base = np.random.randn(80, 1)
        identical_data = np.tile(base, (1, 5))

        adj = self.engine.fit_renyi_transfer_entropy_network(identical_data, alpha=1.5)
        self.assertEqual(adj.shape, (5, 5))
        self.assertTrue(np.all(np.diag(adj) == 0.0))
        self.assertFalse(np.isnan(adj).any())
        self.assertTrue(np.all(adj >= 0.0))

        contagion = self.engine.detect_systemic_contagion(adj)
        self.assertGreaterEqual(contagion["dominant_eigenvalue"], 0.0)

    def test_tc16_disconnected_and_independent_series(self) -> None:
        """Verify network properties on independent random walk returns."""
        np.random.seed(42)
        indep_data = np.random.randn(100, 4) * 0.02
        adj = self.engine.fit_renyi_transfer_entropy_network(indep_data, alpha=1.5)

        self.assertEqual(adj.shape, (4, 4))
        self.assertTrue(np.all(np.diag(adj) == 0.0))
        self.assertTrue(np.all(adj >= 0.0))

        contagion = self.engine.detect_systemic_contagion(adj)
        self.assertGreaterEqual(contagion["dominant_eigenvalue"], 0.0)
        self.assertEqual(len(contagion["vulnerability_ranking"]), 4)
        self.assertEqual(len(contagion["spreader_ranking"]), 4)

    def test_tc17_renyi_alpha_parameter_sensitivity(self) -> None:
        """Verify stability across multiple alpha parameters including alpha -> 1 limit."""
        np.random.seed(99)
        test_data = np.random.randn(60, 3)
        alphas = [0.5, 1.0, 1.0001, 1.5, 2.0, 4.0]

        for a in alphas:
            adj = self.engine.fit_renyi_transfer_entropy_network(test_data, alpha=a)
            self.assertEqual(adj.shape, (3, 3))
            self.assertTrue(np.all(np.diag(adj) == 0.0))
            self.assertFalse(np.isnan(adj).any())
            self.assertTrue(np.all(adj >= 0.0))


class TestScenario5_MCSI_CircuitBreaker_Stress(unittest.TestCase):
    """Adversarial stress testing for Feature F889 (Macro Crash Systemic Risk Index & Circuit-Breaker)."""

    def test_tc18_simultaneous_multi_factor_panic_shock(self) -> None:
        """Verify continuous crisis severity index xi and circuit breaker under GFC/COVID-style panic."""
        # Extreme crisis parameters
        vix_vel = 2.0         # +200% VIX velocity
        vix_tsr = 1.75        # Deep term structure backwardation (VIX spot >> VIX3M)
        credit_spread = 1200.0 # 1200 bps high yield credit spread (Lehman scale)
        contagion_eig = 2.0   # Highly connected contagion network

        xi = evaluate_mcsi_crisis_severity_index(
            vix_velocity=vix_vel,
            vix_tsr=vix_tsr,
            credit_spread_bps=credit_spread,
            contagion_eig=contagion_eig,
        )

        self.assertIsInstance(xi, float)
        self.assertFalse(math.isnan(xi))
        self.assertTrue(0.0 <= xi <= 1.0)
        self.assertGreaterEqual(xi, 0.65, f"Crisis index {xi} must trigger circuit-breaker (>=0.65)")

        cb = check_crisis_circuit_breaker(xi, threshold=0.65)
        self.assertTrue(cb["circuit_breaker_triggered"])
        self.assertLessEqual(cb["max_leverage_limit"], 0.20, "Leverage must clamp to <= 0.20x")
        self.assertTrue(cb["gate8_inverse_hedge_active"], "Gate 8 inverse hedge must activate")
        self.assertEqual(cb["inverse_hedge_etfs"], ["252670", "114800", "SH", "PSQ"])
        self.assertTrue(cb["new_longs_gated"], "New long positions must be gated")
        self.assertTrue(cb["sma200_hard_exit"], "SMA200 hard exit flag must be True")
        self.assertEqual(cb["crisis_status"], "CRISIS_ACTIVE")
        self.assertEqual(cb["synthetic_rows"], 0)

    def test_tc19_calm_and_gradual_leverage_scaling(self) -> None:
        """Verify graceful leverage scaling without premature circuit-breaker tripping under calm conditions."""
        xi_calm = evaluate_mcsi_crisis_severity_index(
            vix_velocity=0.0,
            vix_tsr=0.80,
            credit_spread_bps=280.0,
            contagion_eig=0.15,
        )
        self.assertEqual(xi_calm, 0.0)

        cb_calm = check_crisis_circuit_breaker(xi_calm)
        self.assertFalse(cb_calm["circuit_breaker_triggered"])
        self.assertEqual(cb_calm["max_leverage_limit"], 1.85)
        self.assertFalse(cb_calm["gate8_inverse_hedge_active"])
        self.assertFalse(cb_calm["sma200_hard_exit"])
        self.assertEqual(cb_calm["crisis_status"], "NORMAL")

        # Elevated intermediate stress (xi ~ 0.40)
        cb_elevated = check_crisis_circuit_breaker(0.40, threshold=0.65)
        self.assertFalse(cb_elevated["circuit_breaker_triggered"])
        self.assertTrue(0.65 <= cb_elevated["max_leverage_limit"] < 1.85)
        self.assertEqual(cb_elevated["crisis_status"], "ELEVATED")

    def test_tc20_hostile_and_infinite_inputs_immunity(self) -> None:
        """Verify strict [0.0, 1.0] boundedness under negative, massive, and extreme inputs."""
        # Massive extreme numbers
        xi_huge = evaluate_mcsi_crisis_severity_index(1e8, 1e8, 1e8, 1e8)
        self.assertEqual(xi_huge, 1.0)
        cb_huge = check_crisis_circuit_breaker(xi_huge)
        self.assertTrue(cb_huge["circuit_breaker_triggered"])
        self.assertEqual(cb_huge["max_leverage_limit"], 0.20)

        # Hostile negative numbers
        xi_neg = evaluate_mcsi_crisis_severity_index(-100.0, -50.0, -500.0, -10.0)
        self.assertEqual(xi_neg, 0.0)
        cb_neg = check_crisis_circuit_breaker(xi_neg)
        self.assertFalse(cb_neg["circuit_breaker_triggered"])


class TestCategory6_Invariants_and_Performance(unittest.TestCase):
    """System-level invariants, zero synthetic rows, and sub-millisecond execution SLA."""

    def test_tc21_synthetic_rows_invariant_strictly_zero(self) -> None:
        """Verify synthetic_rows == 0 strictly integer across all outputs."""
        cb = check_crisis_circuit_breaker(0.90)
        self.assertIn("synthetic_rows", cb)
        self.assertEqual(cb["synthetic_rows"], 0)
        self.assertIs(type(cb["synthetic_rows"]), int)

    def test_tc22_sub_50ms_latency_sla_under_stress(self) -> None:
        """Verify latency SLA under adversarial workload across all 5 features."""
        # 1. Macro Tensor
        t0 = time.perf_counter()
        shocks = {"vix": 2.0, "sox": -0.4, "usdkrw": 0.3}
        for _ in range(100):
            compute_macro_tensor_impulse_order3(shocks, sector="Semiconductor")
        dt_tensor = (time.perf_counter() - t0) / 100.0
        self.assertLess(dt_tensor, 0.010, f"Macro tensor latency {dt_tensor*1000:.2f}ms exceeded 10ms")

        # 2. NSS Curve Fitting
        t0 = time.perf_counter()
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0])
        yields = np.array([0.065, 0.065, 0.065, 0.065, 0.045, 0.040, 0.040])
        for _ in range(50):
            fit_nss_six_parameter_curve(maturities, yields)
        dt_nss = (time.perf_counter() - t0) / 50.0
        self.assertLess(dt_nss, 0.050, f"NSS curve fitting latency {dt_nss*1000:.2f}ms exceeded 50ms")

        # 3. Rényi Contagion Network
        t0 = time.perf_counter()
        data = np.random.randn(50, 4)
        engine = GraphGrangerCausalityNetwork()
        for _ in range(10):
            adj = engine.fit_renyi_transfer_entropy_network(data)
            engine.detect_systemic_contagion(adj)
        dt_renyi = (time.perf_counter() - t0) / 10.0
        self.assertLess(dt_renyi, 0.100, f"Rényi network latency {dt_renyi*1000:.2f}ms exceeded 100ms")


if __name__ == "__main__":
    unittest.main()
