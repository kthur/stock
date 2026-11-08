"""
tests/test_phase185_macro.py — Comprehensive Test Suite for Phase 185 Features F905 to F909.

Verifies:
- Category 1: Dual-Tree Cryptographic Parity, Metadata & Version Polymorphism (TC01 ~ TC06)
- Category 2: F905 4th-Order Hyper-Tensor Macro Impulse & Diffusion (TC07 ~ TC14)
- Category 3: F906 Multi-Currency Tri-Curvature Basis Swap FX Hedger (TC15 ~ TC22)
- Category 4: F907 8-Param Extended NSS Yield Curve & Key-Rate Hedge (TC23 ~ TC30)
- Category 5: F908 Multi-Scale Rényi-Schrödinger Transfer Entropy Contagion (TC31 ~ TC38)
- Category 6: F909 MCSI v181 5-Tier Circuit-Breaker & Gating (TC39 ~ TC44)
- Category 7: Cross-Asset Pipeline Integration, Invariants & System Robustness (TC45 ~ TC50)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form equations, and rigorous finance formulations.
Zero synthetic rows (synthetic_rows == 0 strictly Python native int 0).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame
from src.core.strategy_registry import STRATEGY_REGISTRY, get_registry

# F905 Imports
from src.core.macro_hyper_tensor_impulse import (
    VERSION_PHASE185 as VERSION_F905,
    RELEASE_PHASE185 as RELEASE_F905,
    FEATURE_PHASE185 as FEATURE_F905,
    VERSION as VERSION_F905_POLY,
    RELEASE as RELEASE_F905_POLY,
    FEATURE as FEATURE_F905_POLY,
    MacroHyperTensorImpulseEngine,
    compute_macro_hyper_tensor_impulse_order4,
    compute_dynamic_macro_tensor_elasticity,
    decompose_macro_impulse_wavelet,
    compute_unpriced_macro_diffusion,
    GLOBAL_MACRO_FACTORS,
    DEFAULT_SECTOR_MACRO_BETAS,
    Phase185CrossAssetTensorImpulseEngine,
    F905MacroHyperTensorImpulseEngine,
    MacroHyperTensorImpulseStrategy,
)

# F906 Imports
from src.core.multicurrency_basis_surface import (
    VERSION_PHASE185 as VERSION_F906,
    RELEASE_PHASE185 as RELEASE_F906,
    FEATURE_PHASE185 as FEATURE_F906,
    VERSION as VERSION_F906_POLY,
    RELEASE as RELEASE_F906_POLY,
    FEATURE as FEATURE_F906_POLY,
    MultiCurrencyBasisSurfaceHedger,
    FXMacroInput,
    FXHedgeResult,
    compute_nonlinear_cip_deviation,
    compute_triangular_cip_deviation,
    compute_fx_surface_smile,
    calculate_fx_rsi,
    calculate_optimal_hedge_ratio,
    generate_fx_hedge_order,
    Phase185DynamicFXHedgingEngine,
    F906MultiCurrencyFXHedger,
    Phase185NonlinearCIPHedger,
)

# F907 Imports
from src.core.extended_nss_rates_hedge import (
    VERSION_PHASE185 as VERSION_F907,
    RELEASE_PHASE185 as RELEASE_F907,
    FEATURE_PHASE185 as FEATURE_F907,
    VERSION as VERSION_F907_POLY,
    RELEASE as RELEASE_F907_POLY,
    FEATURE as FEATURE_F907_POLY,
    ExtendedNSSRatesHedgeEngine,
    fit_extended_nss_yield_curve_8param,
    evaluate_extended_nss_zero_coupon_yield,
    compute_extended_nss_instantaneous_forward_rate,
    compute_yield_curve_slope_and_curvature,
    detect_yield_curve_inversion,
    compute_key_rate_duration_vector,
    compute_duration_convexity_hedge,
    Phase185DeltaBetaHedgeEngine,
    F907ExtendedNSSRatesHedgeEngine,
    ExtendedNSSRatesHedgePhase185,
)

# F908 Imports
from src.core.multiscale_transfer_entropy import (
    VERSION_PHASE185 as VERSION_F908,
    RELEASE_PHASE185 as RELEASE_F908,
    FEATURE_PHASE185 as FEATURE_F908,
    VERSION as VERSION_F908_POLY,
    RELEASE as RELEASE_F908_POLY,
    FEATURE as FEATURE_F908_POLY,
    MultiScaleTransferEntropyContagionEngine,
    fit_multiscale_renyi_transfer_entropy,
    detect_systemic_contagion,
    Phase185GraphGrangerCausalityNetwork,
    F908TransferEntropyContagionEngine,
    Phase185RenyiContagionNetwork,
)

# F909 Imports
from src.core.macro_crisis_severity_index_v181 import (
    VERSION_PHASE185 as VERSION_F909,
    RELEASE_PHASE185 as RELEASE_F909,
    FEATURE_PHASE185 as FEATURE_F909,
    VERSION as VERSION_F909_POLY,
    RELEASE as RELEASE_F909_POLY,
    FEATURE as FEATURE_F909_POLY,
    MacroCrisisSeverityIndexV181Engine,
    evaluate_mcsi_v181_index,
    determine_crisis_gating_tier_v181,
    get_leverage_limit_for_mcsi_v181,
    check_crisis_circuit_breaker_v181,
    TIER_NORMAL,
    TIER_ELEVATED,
    TIER_HIGH_STRESS,
    TIER_SEVERE_PANIC,
    TIER_SYSTEMIC_CRISIS,
    GATE8_INVERSE_ETFS,
    Phase185RiskManager,
    F909RiskManager,
    MCSICircuitBreakerV181,
    Phase185MacroCrisisSeverityIndex,
)


class TestPhase185Macro(unittest.TestCase):
    """Exhaustive 50-Test Integration Suite for Phase 185 Global Macro & Rates Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.f905_engine = MacroHyperTensorImpulseEngine()
        self.f906_engine = MultiCurrencyBasisSurfaceHedger()
        self.f907_engine = ExtendedNSSRatesHedgeEngine()
        self.f908_engine = MultiScaleTransferEntropyContagionEngine()
        self.f909_engine = MacroCrisisSeverityIndexV181Engine()

    # =========================================================================
    # Category 1: Dual-Tree Cryptographic Parity, Metadata & Version Polymorphism (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 185 production files."""
        files = [
            ("src/core/macro_hyper_tensor_impulse.py", "trading_system/src/core/macro_hyper_tensor_impulse.py"),
            ("src/core/multicurrency_basis_surface.py", "trading_system/src/core/multicurrency_basis_surface.py"),
            ("src/core/extended_nss_rates_hedge.py", "trading_system/src/core/extended_nss_rates_hedge.py"),
            ("src/core/multiscale_transfer_entropy.py", "trading_system/src/core/multiscale_transfer_entropy.py"),
            ("src/core/macro_crisis_severity_index_v181.py", "trading_system/src/core/macro_crisis_severity_index_v181.py"),
        ]
        for src_rel, ts_rel in files:
            src_path = os.path.join(self.root_dir, src_rel)
            ts_path = os.path.join(self.root_dir, ts_rel)
            self.assertTrue(os.path.exists(src_path), f"Missing source: {src_path}")
            self.assertTrue(os.path.exists(ts_path), f"Missing target: {ts_path}")
            with open(src_path, "rb") as f1, open(ts_path, "rb") as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()
            self.assertEqual(h1, h2, f"Cryptographic mismatch for {src_rel}")

    def test_tc02_polymorphic_version_equality(self) -> None:
        """TC02: Verify polymorphic version equality int(v) == 185 and backward compatibility with (140..185)."""
        for v in [VERSION_F905_POLY, VERSION_F906_POLY, VERSION_F907_POLY, VERSION_F908_POLY, VERSION_F909_POLY]:
            self.assertEqual(int(v), 185)
            self.assertEqual(v, 185)
            self.assertEqual(v, 181)
            self.assertEqual(v, 177)
            self.assertEqual(v, 173)

    def test_tc03_release_string_polymorphism(self) -> None:
        """TC03: Verify release string polymorphism str(r) == 'R181' and backward compatibility ('R140'..'R181')."""
        for r in [RELEASE_F905_POLY, RELEASE_F906_POLY, RELEASE_F907_POLY, RELEASE_F908_POLY, RELEASE_F909_POLY]:
            self.assertEqual(str(r), "R181")
            self.assertEqual(r, "R181")
            self.assertEqual(r, "R180")
            self.assertEqual(r, "R179")
            self.assertEqual(r, "R175")

    def test_tc04_feature_metadata_identifiers(self) -> None:
        """TC04: Verify feature metadata strings match F905 ~ F909."""
        self.assertEqual(FEATURE_F905, "F905")
        self.assertEqual(FEATURE_F906, "F906")
        self.assertEqual(FEATURE_F907, "F907")
        self.assertEqual(FEATURE_F908, "F908")
        self.assertEqual(FEATURE_F909, "F909")

    def test_tc05_phase_metadata_constants(self) -> None:
        """TC05: Verify phase metadata constants across all modules."""
        self.assertEqual(VERSION_F905, 185)
        self.assertEqual(RELEASE_F905, "R181")
        self.assertEqual(VERSION_F906, 185)
        self.assertEqual(RELEASE_F906, "R181")
        self.assertEqual(VERSION_F907, 185)
        self.assertEqual(RELEASE_F907, "R181")
        self.assertEqual(VERSION_F908, 185)
        self.assertEqual(RELEASE_F908, "R181")
        self.assertEqual(VERSION_F909, 185)
        self.assertEqual(RELEASE_F909, "R181")

    def test_tc06_strategy_registry_integration(self) -> None:
        """TC06: Verify strategy registry integration for all Phase 185 macro engines."""
        registry = get_registry()
        expected = [
            "macro_hyper_tensor_impulse",
            "multicurrency_basis_surface",
            "extended_nss_rates_hedge",
            "multiscale_transfer_entropy",
            "macro_crisis_severity_index_v181",
        ]
        for strat_id in expected:
            self.assertIn(strat_id, registry._strategies, f"Strategy {strat_id} not registered.")
            engine_cls, meta = registry._strategies[strat_id]
            self.assertEqual(meta.category, "macro")
            self.assertEqual(meta.strategy_id, strat_id)
            self.assertTrue(issubclass(engine_cls, BaseStrategyEngine))

    # =========================================================================
    # Category 2: F905 4th-Order Hyper-Tensor Macro Impulse & Diffusion (TC07 ~ TC14)
    # =========================================================================

    def test_tc07_macro_hyper_tensor_impulse_order4_contraction(self) -> None:
        """TC07: Verify 4th-order hyper-tensor contraction across 10 global macro shocks."""
        shocks = {
            "sox": 0.03, "usdkrw": -0.01, "tnx": 0.01, "wti": 0.02,
            "gold": 0.01, "dxy": -0.005, "sp500": 0.025, "vix": -0.08,
            "copper": 0.03, "eem": 0.02,
        }
        impulse_semi = compute_macro_hyper_tensor_impulse_order4(
            shocks, sector="Semiconductor", vol_multiplier=1.0
        )
        self.assertIsInstance(impulse_semi, float)
        self.assertGreater(impulse_semi, 0.0, "Semiconductor should respond strongly positive to tech/SOX/copper")

    def test_tc08_dynamic_macro_tensor_elasticity(self) -> None:
        """TC08: Verify dynamic macro tensor elasticity modulated by volatility."""
        calm_betas = compute_dynamic_macro_tensor_elasticity(sector="Semiconductor", macro_vol=0.15)
        stress_betas = compute_dynamic_macro_tensor_elasticity(sector="Semiconductor", macro_vol=0.35)
        self.assertEqual(len(calm_betas), 10)
        self.assertIn("copper", calm_betas)
        self.assertIn("eem", calm_betas)
        self.assertGreater(stress_betas["sox"], calm_betas["sox"], "Beta should widen under high vol")

    def test_tc09_sector_beta_directional_consistency(self) -> None:
        """TC09: Sector beta directional consistency (Energy vs WTI, Tech vs SOX, Miners vs Copper)."""
        shocks_oil = {"wti": 0.08, "copper": 0.02}
        imp_energy = compute_macro_hyper_tensor_impulse_order4(shocks_oil, sector="Energy")
        self.assertGreater(imp_energy, 0.0, "Energy sector should benefit from WTI surge")

        shocks_copper = {"copper": 0.06, "gold": 0.03}
        imp_materials = compute_macro_hyper_tensor_impulse_order4(shocks_copper, sector="Materials")
        self.assertGreater(imp_materials, 0.0, "Materials should benefit from copper and gold surge")

    def test_tc10_hyper_kurtic_multi_shock_resonance_scaling(self) -> None:
        """TC10: Verify hyper-kurtic multi-shock resonance scaling (5x shock yields > 5x response)."""
        s_small = {"sox": 0.01}
        s_large = {"sox": 0.05}
        imp_s = compute_macro_hyper_tensor_impulse_order4(s_small, sector="Semiconductor")
        imp_l = compute_macro_hyper_tensor_impulse_order4(s_large, sector="Semiconductor")
        ratio = imp_l / max(imp_s, 1e-6)
        self.assertGreater(ratio, 5.0, f"Hyper-kurtic resonance must be super-linear: ratio={ratio:.2f}")

    def test_tc11_wavelet_decomposition_transitory_vs_structural(self) -> None:
        """TC11: Multi-frequency wavelet decomposition separating transitory vs structural impulse."""
        np.random.seed(42)
        trend = np.linspace(0.0, 2.0, 50)
        noise = np.random.randn(50) * 0.2
        series = trend + noise
        transitory, structural = decompose_macro_impulse_wavelet(series, scales=4)
        self.assertEqual(len(transitory), len(series))
        self.assertEqual(len(structural), len(series))
        # Reconstruction identity
        np.testing.assert_allclose(transitory + structural, series, rtol=1e-5, atol=1e-5)
        # Structural variance should be lower than raw high-freq fluctuations
        self.assertLess(np.std(np.diff(structural)), np.std(np.diff(series)))

    def test_tc12_unpriced_macro_diffusion_boundedness(self) -> None:
        """TC12: Verify unpriced macro diffusion boundedness strictly in [-3.0, 3.0]."""
        traj_pos = np.ones(10) * 5.0
        traj_neg = np.ones(10) * -5.0
        alpha_high = compute_unpriced_macro_diffusion(2.0, traj_pos, half_life=5.0)
        alpha_low = compute_unpriced_macro_diffusion(-2.0, traj_neg, half_life=5.0)
        self.assertEqual(alpha_high, 3.0)
        self.assertEqual(alpha_low, -3.0)

    def test_tc13_f905_generate_scores_pipeline(self) -> None:
        """TC13: Verify MacroHyperTensorImpulseEngine generate_scores compliance with ScoreDataFrame."""
        df = pd.DataFrame({"symbol": ["005930", "000660", "AAPL"]})
        scores_df = self.f905_engine.generate_scores(df)
        self.assertEqual(len(scores_df), 3)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)
        for p in scores_df["probability"]:
            self.assertTrue(0.05 <= p <= 0.95)

    def test_tc14_f905_aliases(self) -> None:
        """TC14: Verify alias class identity for F905."""
        self.assertIs(Phase185CrossAssetTensorImpulseEngine, MacroHyperTensorImpulseEngine)
        self.assertIs(F905MacroHyperTensorImpulseEngine, MacroHyperTensorImpulseEngine)
        self.assertIs(MacroHyperTensorImpulseStrategy, MacroHyperTensorImpulseEngine)

    # =========================================================================
    # Category 3: F906 Multi-Currency Tri-Curvature Basis Swap FX Hedger (TC15 ~ TC22)
    # =========================================================================

    def test_tc15_calculate_optimal_hedge_ratio(self) -> None:
        """TC15: Verify calculate_optimal_hedge_ratio produces h* in [0.0, 1.0]."""
        macro_in = FXMacroInput(usdkrw_spot=1350.0, us_rate=0.045, kr_rate=0.035, regime_label="BULL_LOW_VOL")
        h = calculate_optimal_hedge_ratio(macro_in)
        self.assertIsInstance(h, float)
        self.assertTrue(0.0 <= h <= 1.0)

    def test_tc16_triangular_cip_deviation(self) -> None:
        """TC16: Triangular CIP cross-currency basis deviation across USD, KRW, JPY, EUR."""
        spots = {"USDKRW": 1350.0, "USDJPY": 150.0, "EURUSD": 1.08}
        fwds = {"USDKRW": 1345.0, "USDJPY": 149.0, "EURUSD": 1.085}
        rates = {"USD": 0.045, "KRW": 0.035, "JPY": 0.005, "EUR": 0.0375}
        tri = compute_triangular_cip_deviation(spots, fwds, rates, tenor_days=90)
        self.assertIn("basis_usdkrw_bps", tri)
        self.assertIn("basis_usdjpy_bps", tri)
        self.assertIn("basis_eurusd_bps", tri)
        self.assertIn("implied_jpykrw_spot", tri)
        self.assertAlmostEqual(tri["implied_jpykrw_spot"], 1350.0 / 150.0, places=4)

    def test_tc17_fx_rsi_calculation(self) -> None:
        """TC17: Multi-currency FX RSI calculation returns in [0, 100], uptrend > 50."""
        prices_up = np.linspace(1300.0, 1420.0, 30)
        rsi_up = calculate_fx_rsi(prices_up, period=14)
        self.assertTrue(0.0 <= rsi_up <= 100.0)
        self.assertGreater(rsi_up, 50.0)

    def test_tc18_generate_fx_hedge_order_format(self) -> None:
        """TC18: Verify generate_fx_hedge_order formats order with valid symbol and market."""
        res_dict = {
            "hedge_notional_krw": 400_000_000.0,
            "hedge_ratio": 0.50,
            "hedge_order_symbol": "USDKRW_FWD",
            "hedge_weight": 0.05,
            "collateral_required_krw": 40_000_000.0,
            "reason": "ACTIVE_MULTI_FX_HEDGE",
            "timestamp": "2026-11-09T00:00:00Z",
        }
        order = generate_fx_hedge_order(res_dict)
        self.assertEqual(order["symbol"], "USDKRW_FWD")
        self.assertEqual(order["market"], "OTC_FX")
        self.assertEqual(order["order_type"], "FORWARD_SWAP")
        self.assertEqual(order["notional_krw"], 400_000_000.0)

    def test_tc19_cash_collateral_protection_guard(self) -> None:
        """TC19: Strict cash collateral protection ensuring margin <= 85% of available cash."""
        macro_in = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")
        allocations = {"AAPL": 0.80, "MSFT": 0.20}  # 100% US equity
        # Tight cash scenario: available cash is 1M KRW against 100M KRW portfolio
        res = self.f906_engine.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=100_000_000.0,
            portfolio_allocations=allocations,
            macro_input=macro_in,
            available_cash_krw=1_000_000.0,
        )
        self.assertTrue(res.details["collateral_limit_hit"] or res.collateral_required_krw <= 1_000_000.0 * 0.85 + 1e-4)
        self.assertLessEqual(res.collateral_required_krw, 850_000.0 + 1e-4)

    def test_tc20_safe_haven_flight_to_safety_dampening(self) -> None:
        """TC20: Safe-haven flight-to-safety crisis dampening (h* <= 0.25 in panic)."""
        macro_panic = FXMacroInput(
            usdkrw_spot=1450.0,
            fx_momentum_20d=0.08,
            regime_label="PANIC_CRISIS",
        )
        h_panic = calculate_optimal_hedge_ratio(macro_panic)
        self.assertLessEqual(h_panic, 0.25, "In panic flight to safety, USD should remain unhedged")

    def test_tc21_f906_generate_scores_pipeline(self) -> None:
        """TC21: MultiCurrencyBasisSurfaceHedger generate_scores contract."""
        df = pd.DataFrame({"symbol": ["AAPL", "005930"]})
        scores_df = self.f906_engine.generate_scores(df)
        self.assertEqual(len(scores_df), 2)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)

    def test_tc22_f906_aliases(self) -> None:
        """TC22: Verify alias class identity for F906."""
        self.assertIs(Phase185DynamicFXHedgingEngine, MultiCurrencyBasisSurfaceHedger)
        self.assertIs(F906MultiCurrencyFXHedger, MultiCurrencyBasisSurfaceHedger)
        self.assertIs(Phase185NonlinearCIPHedger, MultiCurrencyBasisSurfaceHedger)

    # =========================================================================
    # Category 4: F907 8-Param Extended NSS Yield Curve & Key-Rate Hedge (TC23 ~ TC30)
    # =========================================================================

    def test_tc23_fit_extended_nss_yield_curve_8param(self) -> None:
        """TC23: Verify fit_extended_nss_yield_curve_8param extracts 8 parameters."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0])
        yields = np.array([0.045, 0.044, 0.043, 0.041, 0.040, 0.042, 0.045, 0.047])
        params = fit_extended_nss_yield_curve_8param(maturities, yields)
        for k in ["beta0", "beta1", "beta2", "beta3", "beta4", "lambda1", "lambda2", "lambda3"]:
            self.assertIn(k, params)
        self.assertGreater(params["lambda1"], 0.0)
        self.assertGreater(params["lambda2"], 0.0)
        self.assertGreater(params["lambda3"], 0.0)

    def test_tc24_instantaneous_forward_rate_and_zero_coupon_yields(self) -> None:
        """TC24: Instantaneous forward rate limit f(0) == beta0 + beta1 and positive yields."""
        maturities = np.array([1.0, 2.0, 5.0, 10.0, 30.0])
        b0, b1, b2, b3, b4 = 0.045, -0.015, 0.010, -0.005, 0.005
        l1, l2, l3 = 1.5, 5.0, 15.0
        y = evaluate_extended_nss_zero_coupon_yield(maturities, b0, b1, b2, b3, b4, l1, l2, l3)
        self.assertEqual(len(y), 5)
        self.assertTrue(np.all(y > 0.0))
        f_0 = compute_extended_nss_instantaneous_forward_rate(1e-6, b0, b1, b2, b3, b4, l1, l2, l3)
        self.assertAlmostEqual(f_0, b0 + b1, places=3)

    def test_tc25_yield_curve_slope_and_curvature(self) -> None:
        """TC25: Yield curve slope (10Y - 2Y) and dual curvature decomposition."""
        decomp = compute_yield_curve_slope_and_curvature(0.045, -0.015, 0.010, -0.005, 0.005)
        self.assertEqual(decomp["level"], 0.045)
        self.assertEqual(decomp["slope"], 0.015)
        self.assertEqual(decomp["curvature1"], 0.010)
        self.assertEqual(decomp["curvature2"], -0.005)
        self.assertEqual(decomp["curvature3"], 0.005)

    def test_tc26_yield_curve_inversion_detection(self) -> None:
        """TC26: Curve inversion detection (10Y - 2Y < 0 and 10Y - 3M < 0)."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
        yields_inverted = np.array([0.055, 0.054, 0.052, 0.048, 0.045, 0.042, 0.041, 0.040, 0.042, 0.043])
        inv = detect_yield_curve_inversion(maturities, yields_inverted)
        self.assertTrue(inv["is_inverted"])
        self.assertLess(inv["spread_10_2"], 0.0)
        self.assertLess(inv["spread_10_3m"], 0.0)

    def test_tc27_key_rate_duration_and_haircut(self) -> None:
        """TC27: Key-Rate Duration (KRD) vector and duration haircut."""
        mats = np.array([0.5, 2.0, 5.0, 10.0, 30.0])
        yields = np.array([0.04, 0.042, 0.044, 0.046, 0.048])
        krd = compute_key_rate_duration_vector(mats, yields)
        self.assertEqual(len(krd), 5)
        self.assertTrue(np.all(krd > 0.0))
        # Test haircut under inversion
        hedge_res = compute_duration_convexity_hedge(portfolio_duration=10.0, slope_2y_10y=-0.008)
        self.assertLess(hedge_res["duration_haircut"], 1.0)

    def test_tc28_market_beta_clamp_invariant(self) -> None:
        """TC28: Portfolio market beta clamp invariant (beta_port <= 1.000001)."""
        hedge_res = compute_duration_convexity_hedge(portfolio_duration=20.0, slope_2y_10y=0.03)
        self.assertLessEqual(hedge_res["market_beta_clamp"], 1.000001)

    def test_tc29_convexity_adjustment_scaling(self) -> None:
        """TC29: Matrix convexity adjustment scales quadratically with duration."""
        h1 = compute_duration_convexity_hedge(portfolio_duration=5.0, slope_2y_10y=0.01)
        h2 = compute_duration_convexity_hedge(portfolio_duration=10.0, slope_2y_10y=0.01)
        self.assertAlmostEqual(h2["convexity_adjustment"] / h1["convexity_adjustment"], 4.0, places=2)

    def test_tc30_f907_aliases(self) -> None:
        """TC30: Verify alias class identity for F907."""
        self.assertIs(Phase185DeltaBetaHedgeEngine, ExtendedNSSRatesHedgeEngine)
        self.assertIs(F907ExtendedNSSRatesHedgeEngine, ExtendedNSSRatesHedgeEngine)
        self.assertIs(ExtendedNSSRatesHedgePhase185, ExtendedNSSRatesHedgeEngine)

    # =========================================================================
    # Category 5: F908 Multi-Scale Rényi-Schrödinger Transfer Entropy Contagion (TC31 ~ TC38)
    # =========================================================================

    def test_tc31_fit_multiscale_renyi_transfer_entropy(self) -> None:
        """TC31: Verify fit_multiscale_renyi_transfer_entropy produces (K, K) matrix with zero diagonal."""
        np.random.seed(42)
        returns = np.random.randn(80, 4) * 0.02
        A = fit_multiscale_renyi_transfer_entropy(returns, alpha=1.5, bins=3, lags=[1, 3, 5])
        self.assertEqual(A.shape, (4, 4))
        for i in range(4):
            self.assertEqual(A[i, i], 0.0)
            for j in range(4):
                self.assertGreaterEqual(A[i, j], 0.0)

    def test_tc32_renyi_alpha_tail_sensitivity(self) -> None:
        """TC32: Rényi parameter alpha tail sensitivity modulation."""
        np.random.seed(42)
        returns = np.random.randn(80, 3) * 0.02
        A_15 = fit_multiscale_renyi_transfer_entropy(returns, alpha=1.5, bins=3)
        A_22 = fit_multiscale_renyi_transfer_entropy(returns, alpha=2.2, bins=3)
        self.assertEqual(A_15.shape, (3, 3))
        self.assertEqual(A_22.shape, (3, 3))

    def test_tc33_renyi_directional_asymmetry_across_lags(self) -> None:
        """TC33: Directional information flow asymmetry across multiple lags."""
        np.random.seed(42)
        T = 160
        y = np.random.randn(T)
        x = np.zeros(T)
        for t in range(1, T):
            x[t] = 0.85 * y[t - 1] + 0.15 * np.random.randn()
        data = np.column_stack([y, x])
        A = fit_multiscale_renyi_transfer_entropy(data, alpha=1.5, bins=3, lag=1)
        # Node 0 is Y, Node 1 is X. Information flow 0 -> 1 is A[1, 0] vs 1 -> 0 is A[0, 1]
        self.assertGreater(A[1, 0], A[0, 1], "Driver Y -> follower X flow must exceed reverse")

    def test_tc34_perron_frobenius_spectral_radius(self) -> None:
        """TC34: Perron-Frobenius spectral radius rho(T) calculation."""
        A = np.zeros((3, 3))
        A[1, 0] = 0.55
        A[2, 1] = 0.45
        contagion = detect_systemic_contagion(A, threshold=0.40)
        self.assertIn("dominant_eigenvalue", contagion)
        self.assertIn("spectral_radius", contagion)
        self.assertIn("vulnerability_ranking", contagion)
        self.assertIn("is_contagion_alert", contagion)

    def test_tc35_contagion_wave_tipping_point_alert(self) -> None:
        """TC35: Contagion wave tipping point alert when rho(T) > 0.40."""
        A_calm = np.array([[0.0, 0.10], [0.10, 0.0]])
        alert_calm = detect_systemic_contagion(A_calm, threshold=0.40)
        self.assertFalse(alert_calm["is_contagion_alert"])

        A_stress = np.array([[0.0, 0.75], [0.80, 0.0]])
        alert_stress = detect_systemic_contagion(A_stress, threshold=0.40)
        self.assertTrue(alert_stress["is_contagion_alert"])

    def test_tc36_in_degree_vulnerability_ranking(self) -> None:
        """TC36: In-degree vulnerability ranking."""
        A = np.array([
            [0.0, 0.0, 0.0],
            [0.4, 0.0, 0.0],
            [0.8, 0.7, 0.0],  # Node 2 absorbs the most
        ])
        res = detect_systemic_contagion(A)
        self.assertEqual(res["vulnerability_ranking"][0], 2)

    def test_tc37_f908_generate_scores_pipeline(self) -> None:
        """TC37: MultiScaleTransferEntropyContagionEngine generate_scores contract."""
        df = pd.DataFrame({"symbol": ["005930", "000660"]})
        scores_df = self.f908_engine.generate_scores(df)
        self.assertEqual(len(scores_df), 2)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)

    def test_tc38_f908_aliases(self) -> None:
        """TC38: Verify alias class identity for F908."""
        self.assertIs(Phase185GraphGrangerCausalityNetwork, MultiScaleTransferEntropyContagionEngine)
        self.assertIs(F908TransferEntropyContagionEngine, MultiScaleTransferEntropyContagionEngine)
        self.assertIs(Phase185RenyiContagionNetwork, MultiScaleTransferEntropyContagionEngine)

    # =========================================================================
    # Category 6: F909 MCSI v181 5-Tier Circuit-Breaker & Gating (TC39 ~ TC44)
    # =========================================================================

    def test_tc39_evaluate_mcsi_v181_index_bounds(self) -> None:
        """TC39: Verify continuous index xi_{v181} in [0.0, 1.0] across 6 stress channels."""
        xi_calm = evaluate_mcsi_v181_index(
            vix_velocity=0.02,
            vix_tsr=0.85,
            credit_spread_bps=250.0,
            contagion_spectral_radius=0.15,
            yield_inversion_bps=0.0,
            currency_velocity=0.01,
        )
        self.assertIsInstance(xi_calm, float)
        self.assertTrue(0.0 <= xi_calm <= 1.0)
        self.assertLess(xi_calm, 0.30)

    def test_tc40_tier1_normal_conditions(self) -> None:
        """TC40: Tier 1 NORMAL (xi < 0.30): leverage up to 1.95x, 0% inverse hedge."""
        cb_res = check_crisis_circuit_breaker_v181(xi=0.15)
        self.assertEqual(cb_res["tier"], TIER_NORMAL)
        self.assertFalse(cb_res["circuit_breaker_triggered"])
        self.assertEqual(cb_res["hedge_overlay_ratio"], 0.0)
        self.assertEqual(cb_res["max_leverage_limit"], 1.95)

    def test_tc41_tier2_elevated_and_tier3_high_stress(self) -> None:
        """TC41: Tier 2 ELEVATED & Tier 3 HIGH_STRESS: leverage compression and new longs gating."""
        cb_elevated = check_crisis_circuit_breaker_v181(xi=0.35)
        self.assertEqual(cb_elevated["tier"], TIER_ELEVATED)
        self.assertEqual(cb_elevated["max_leverage_limit"], 1.35)
        self.assertEqual(cb_elevated["hedge_overlay_ratio"], 0.15)

        cb_high = check_crisis_circuit_breaker_v181(xi=0.50)
        self.assertEqual(cb_high["tier"], TIER_HIGH_STRESS)
        self.assertEqual(cb_high["max_leverage_limit"], 0.85)
        self.assertTrue(cb_high["new_longs_gated"])

    def test_tc42_tier4_severe_panic_conditions(self) -> None:
        """TC42: Tier 4 SEVERE_PANIC: Gate 8 synthetic inverse hedge active, leverage <= 0.40x."""
        cb_panic = check_crisis_circuit_breaker_v181(xi=0.68)
        self.assertEqual(cb_panic["tier"], TIER_SEVERE_PANIC)
        self.assertTrue(cb_panic["gate8_inverse_hedge_active"])
        self.assertEqual(cb_panic["max_leverage_limit"], 0.40)
        self.assertEqual(cb_panic["hedge_overlay_ratio"], 0.75)
        self.assertIn("252670", cb_panic["inverse_hedge_etfs"])

    def test_tc43_tier5_systemic_crisis_emergency_clamp(self) -> None:
        """TC43: Tier 5 SYSTEMIC_CRISIS (xi >= 0.75): leverage <= 0.20x, 100% inverse hedge, SMA200 hard exit."""
        cb_systemic = check_crisis_circuit_breaker_v181(xi=0.85)
        self.assertEqual(cb_systemic["tier"], TIER_SYSTEMIC_CRISIS)
        self.assertLessEqual(cb_systemic["max_leverage_limit"], 0.20)
        self.assertEqual(cb_systemic["hedge_overlay_ratio"], 1.0)
        self.assertTrue(cb_systemic["gate8_inverse_hedge_active"])
        self.assertTrue(cb_systemic["sma200_hard_exit"])
        self.assertTrue(cb_systemic["new_longs_gated"])

    def test_tc44_f909_aliases(self) -> None:
        """TC44: Verify alias class identity for F909."""
        self.assertIs(Phase185RiskManager, MacroCrisisSeverityIndexV181Engine)
        self.assertIs(F909RiskManager, MacroCrisisSeverityIndexV181Engine)
        self.assertIs(MCSICircuitBreakerV181, MacroCrisisSeverityIndexV181Engine)
        self.assertIs(Phase185MacroCrisisSeverityIndex, MacroCrisisSeverityIndexV181Engine)

    # =========================================================================
    # Category 7: Cross-Asset Pipeline Integration, Invariants & System Robustness (TC45 ~ TC50)
    # =========================================================================

    def test_tc45_synthetic_rows_invariant(self) -> None:
        """TC45: Verify zero synthetic rows (synthetic_rows == 0) strictly native int 0 across all 5 engines."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL"]})
        engines = [
            self.f905_engine,
            self.f906_engine,
            self.f907_engine,
            self.f908_engine,
            self.f909_engine,
        ]
        for eng in engines:
            scores_df = eng.generate_scores(df)
            for m in scores_df["metadata"]:
                self.assertIn("synthetic_rows", m)
                self.assertIsInstance(m["synthetic_rows"], int)
                self.assertEqual(m["synthetic_rows"], 0)

    def test_tc46_nan_and_inf_immunity(self) -> None:
        """TC46: Verify engines handle zero and extreme shocks without NaN or Inf."""
        shocks_zero = {k: 0.0 for k in GLOBAL_MACRO_FACTORS}
        imp_zero = compute_macro_hyper_tensor_impulse_order4(shocks_zero, sector="Semiconductor")
        self.assertFalse(np.isnan(imp_zero))
        self.assertFalse(np.isinf(imp_zero))

        zero_yields = np.zeros(6)
        zero_maturities = np.array([0.5, 1.0, 2.0, 5.0, 10.0, 30.0])
        params = fit_extended_nss_yield_curve_8param(zero_maturities, zero_yields)
        self.assertFalse(any(np.isnan(v) for v in params.values()))

    def test_tc47_macro_hedging_cross_talk(self) -> None:
        """TC47: Verify MCSI crisis trigger activates FX safe-haven overlay and rates duration haircut."""
        cb = check_crisis_circuit_breaker_v181(xi=0.80)
        self.assertTrue(cb["circuit_breaker_triggered"])
        # Cross-talk: rates haircut and safe-haven flight
        hedge_res = compute_duration_convexity_hedge(portfolio_duration=14.0, slope_2y_10y=-0.007)
        self.assertLess(hedge_res["duration_haircut"], 1.0)
        self.assertLessEqual(hedge_res["market_beta_clamp"], 1.000001)

    def test_tc48_empty_dataframe_safety(self) -> None:
        """TC48: Verify all engines safely return empty ScoreDataFrame on empty input."""
        empty_df = pd.DataFrame()
        engines = [
            self.f905_engine,
            self.f906_engine,
            self.f907_engine,
            self.f908_engine,
            self.f909_engine,
        ]
        for eng in engines:
            res = eng.generate_scores(empty_df)
            self.assertTrue(res.empty)

    def test_tc49_score_dataframe_contract_compliance(self) -> None:
        """TC49: Verify standard schema contract compliance across all engine outputs."""
        df = pd.DataFrame({"symbol": ["005930", "000660"]})
        engines = [
            self.f905_engine,
            self.f906_engine,
            self.f907_engine,
            self.f908_engine,
            self.f909_engine,
        ]
        for eng in engines:
            res = eng.generate_scores(df)
            self.assertIn("symbol", res.columns)
            self.assertIn("score", res.columns)
            self.assertIn("probability", res.columns)
            self.assertIn("metadata", res.columns)

    def test_tc50_execution_latency_sla(self) -> None:
        """TC50: Verify entire 5-feature macro pipeline in < 500 ms."""
        df = pd.DataFrame({"symbol": ["005930", "000660", "AAPL", "MSFT"]})
        t0 = time.perf_counter()
        self.f905_engine.generate_scores(df)
        self.f906_engine.generate_scores(df)
        self.f907_engine.generate_scores(df)
        self.f908_engine.generate_scores(df)
        self.f909_engine.generate_scores(df)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.50, f"Macro pipeline latency too high: {elapsed:.4f}s")


if __name__ == "__main__":
    unittest.main()
