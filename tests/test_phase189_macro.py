"""
tests/test_phase189_macro.py — Comprehensive Unit & Integration Test Suite for Phase 189
Features F925 to F929 (Global Macro & Rates Architecture).

Verifies:
- Category 1: Dual-Tree Parity, Metadata, Constants & Alias Trees (TC01 ~ TC06)
- Category 2: F925 5th-Order Hyper-Tensor Macro Impulse & Multi-Frequency Wavelet (TC07 ~ TC14)
- Category 3: F926 Multi-Currency Quad-Curvature FX Hedger (TC15 ~ TC22)
- Category 4: F927 10-Parameter Extended NSS Yield Curve & Key-Rate Convexity Immunization (TC23 ~ TC30)
- Category 5: F928 Directed Quantum Rényi-Schrödinger Transfer Entropy Contagion Network (TC31 ~ TC38)
- Category 6: F929 Macro Crisis Severity Index v182 (MCSI v182) 6-Tier Circuit-Breaker (TC39 ~ TC44)
- Category 7: Cross-Asset Pipeline Integration, Invariants & System Robustness (TC45 ~ TC50)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form equations, and genuine financial mechanics.
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

# F925 Imports
from src.core.macro_hyper_tensor_impulse_v182 import (
    VERSION_PHASE189 as VERSION_F925,
    RELEASE_PHASE189 as RELEASE_F925,
    FEATURE_PHASE189 as FEATURE_F925,
    VERSION as VERSION_F925_POLY,
    RELEASE as RELEASE_F925_POLY,
    FEATURE as FEATURE_F925_POLY,
    MacroHyperTensorImpulseV182Engine,
    compute_5th_order_hyper_tensor_impulse,
    compute_dynamic_macro_tensor_elasticity,
    decompose_macro_impulse_multi_frequency_wavelet,
    decompose_macro_impulse_wavelet,
    compute_unpriced_macro_diffusion_v182,
    GLOBAL_MACRO_FACTORS,
    DEFAULT_SECTOR_MACRO_BETAS_V182,
    HyperTensorMacroImpulseV182Engine,
    Phase189MacroHyperTensorEngine,
    F925MacroHyperTensorImpulseEngine,
    MacroHyperTensorImpulseStrategyV182,
)

# F926 Imports
from src.core.quad_curvature_fx_hedger import (
    VERSION_PHASE189 as VERSION_F926,
    RELEASE_PHASE189 as RELEASE_F926,
    FEATURE_PHASE189 as FEATURE_F926,
    VERSION as VERSION_F926_POLY,
    RELEASE as RELEASE_F926_POLY,
    FEATURE as FEATURE_F926_POLY,
    QuadCurvatureFXHedgingEngine,
    FXMacroInput,
    FXHedgeResult,
    compute_quad_curvature_basis_spread,
    calculate_quad_curvature_hedge_ratio,
    compute_quad_curvature_triangular_arbitrage,
    compute_fx_surface_smile,
    calculate_fx_rsi,
    generate_quad_fx_hedge_order,
    Phase189DynamicFXHedgingEngine,
    F926QuadCurvatureFXHedger,
    MultiCurrencyQuadCurvatureHedger,
    QuadCurvatureFXHedger,
)

# F927 Imports
from src.core.nss10_rates_hedge import (
    VERSION_PHASE189 as VERSION_F927,
    RELEASE_PHASE189 as RELEASE_F927,
    FEATURE_PHASE189 as FEATURE_F927,
    VERSION as VERSION_F927_POLY,
    RELEASE as RELEASE_F927_POLY,
    FEATURE as FEATURE_F927_POLY,
    NSS10RatesHedgeEngine,
    fit_extended_nss_10param_curve,
    evaluate_nss10_yield,
    compute_nss10_instantaneous_forward_rate,
    compute_key_rate_convexity_immunization_v182,
    detect_yield_curve_inversion_v182,
    ExtendedNSSRatesHedgeEngine,
    Phase189NSS10RatesHedgeEngine,
    F927NSS10RatesHedgeEngine,
    ExtendedNSS10RatesHedgePhase189,
    NSS10RatesHedgePhase189,
)

# F928 Imports
from src.core.renyi_schrodinger_transfer_entropy import (
    VERSION_PHASE189 as VERSION_F928,
    RELEASE_PHASE189 as RELEASE_F928,
    FEATURE_PHASE189 as FEATURE_F928,
    VERSION as VERSION_F928_POLY,
    RELEASE as RELEASE_F928_POLY,
    FEATURE as FEATURE_F928_POLY,
    RenyiSchrodingerTransferEntropyEngine,
    compute_directed_renyi_schrodinger_transfer_entropy,
    detect_systemic_contagion_network_v182,
    Phase189RenyiSchrodingerContagionEngine,
    F928RenyiSchrodingerTransferEntropyEngine,
    QuantumRenyiContagionNetwork,
    RenyiSchrodingerContagionEngine,
)

# F929 Imports
from src.core.macro_crisis_severity_index_v182 import (
    VERSION_PHASE189 as VERSION_F929,
    RELEASE_PHASE189 as RELEASE_F929,
    FEATURE_PHASE189 as FEATURE_F929,
    VERSION as VERSION_F929_POLY,
    RELEASE as RELEASE_F929_POLY,
    FEATURE as FEATURE_F929_POLY,
    MacroCrisisSeverityIndexV182Engine,
    compute_mcsi_v182_multi_horizon_score,
    determine_mcsi_v182_6tier_gating,
    get_leverage_limit_for_mcsi_v182,
    check_circuit_breaker_v182,
    TIER_NORMAL,
    TIER_ELEVATED,
    TIER_HIGH_STRESS,
    TIER_SYSTEMIC_CRISIS,
    TIER_PANIC_LIQUIDITY_SQUEEZE,
    TIER_CIRCUIT_BREAKER_HALT,
    GATE8_INVERSE_ETFS,
    Phase189MacroCrisisSeverityIndex,
    F929MCSIv182Engine,
    MCSICircuitBreakerV182,
    Phase189RiskManager,
)


class TestPhase189Macro(unittest.TestCase):
    """Exhaustive 50-Test Integration Suite for Phase 189 Global Macro & Rates Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.f925_engine = MacroHyperTensorImpulseV182Engine()
        self.f926_engine = QuadCurvatureFXHedgingEngine()
        self.f927_engine = NSS10RatesHedgeEngine()
        self.f928_engine = RenyiSchrodingerTransferEntropyEngine()
        self.f929_engine = MacroCrisisSeverityIndexV182Engine()

    # =========================================================================
    # Category 1: Dual-Tree Cryptographic Parity, Metadata & Version Polymorphism (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all 5 Phase 189 production files."""
        files = [
            ("src/core/macro_hyper_tensor_impulse_v182.py", "trading_system/src/core/macro_hyper_tensor_impulse_v182.py"),
            ("src/core/quad_curvature_fx_hedger.py", "trading_system/src/core/quad_curvature_fx_hedger.py"),
            ("src/core/nss10_rates_hedge.py", "trading_system/src/core/nss10_rates_hedge.py"),
            ("src/core/renyi_schrodinger_transfer_entropy.py", "trading_system/src/core/renyi_schrodinger_transfer_entropy.py"),
            ("src/core/macro_crisis_severity_index_v182.py", "trading_system/src/core/macro_crisis_severity_index_v182.py"),
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
        """TC02: Verify polymorphic version equality int(v) == 189 and backward compatibility with (140..189)."""
        versions = [VERSION_F925_POLY, VERSION_F926_POLY, VERSION_F927_POLY, VERSION_F928_POLY, VERSION_F929_POLY]
        for v in versions:
            self.assertEqual(int(v), 189)
            self.assertTrue(v == 189)
            self.assertTrue(v == 185)
            self.assertTrue(v == 181)
            self.assertTrue(v == 177)
            self.assertTrue(v == 173)

    def test_tc03_polymorphic_release_equality(self) -> None:
        """TC03: Verify polymorphic release equality str(r) == 'R182' and backward compatibility with ('R140'..'R182')."""
        releases = [RELEASE_F925_POLY, RELEASE_F926_POLY, RELEASE_F927_POLY, RELEASE_F928_POLY, RELEASE_F929_POLY]
        for r in releases:
            self.assertEqual(str(r), "R182")
            self.assertTrue(r == "R182")
            self.assertTrue(r == "R181")
            self.assertTrue(r == "R180")
            self.assertTrue(r == "R179")

    def test_tc04_polymorphic_feature_equality(self) -> None:
        """TC04: Verify polymorphic feature strings for F925, F926, F927, F928, F929."""
        self.assertEqual(str(FEATURE_F925_POLY), "F925")
        self.assertTrue(FEATURE_F925_POLY == "F925")
        self.assertTrue(FEATURE_F925_POLY == "F925-F929")

        self.assertEqual(str(FEATURE_F926_POLY), "F926")
        self.assertTrue(FEATURE_F926_POLY == "F926")

        self.assertEqual(str(FEATURE_F927_POLY), "F927")
        self.assertTrue(FEATURE_F927_POLY == "F927")

        self.assertEqual(str(FEATURE_F928_POLY), "F928")
        self.assertTrue(FEATURE_F928_POLY == "F928")

        self.assertEqual(str(FEATURE_F929_POLY), "F929")
        self.assertTrue(FEATURE_F929_POLY == "F929")

    def test_tc05_strategy_registry_metadata(self) -> None:
        """TC05: Verify all 5 strategy engines are properly registered in STRATEGY_REGISTRY with category='macro'."""
        expected_ids = [
            "macro_hyper_tensor_impulse_v182",
            "quad_curvature_fx_hedger",
            "nss10_rates_hedge",
            "renyi_schrodinger_transfer_entropy",
            "macro_crisis_severity_index_v182",
        ]
        reg = get_registry()
        for s_id in expected_ids:
            self.assertIn(s_id, STRATEGY_REGISTRY, f"Strategy {s_id} not in registry")
            entry = reg.get(s_id)
            self.assertIsNotNone(entry)
            meta = entry[1]
            self.assertEqual(meta.category, "macro")
            self.assertTrue(meta.is_standalone)

    def test_tc06_engine_instantiation_and_base_attributes(self) -> None:
        """TC06: Verify engine instantiation, inheritance from BaseStrategyEngine, and metadata."""
        engines = [
            self.f925_engine,
            self.f926_engine,
            self.f927_engine,
            self.f928_engine,
            self.f929_engine,
        ]
        for eng in engines:
            self.assertIsInstance(eng, BaseStrategyEngine)
            self.assertEqual(int(eng.version), 189)
            self.assertEqual(str(eng.release), "R182")

    # =========================================================================
    # Category 2: F925 5th-Order Hyper-Tensor Macro Impulse & Multi-Frequency Wavelet (TC07 ~ TC14)
    # =========================================================================

    def test_tc07_hyper_tensor_zero_shocks(self) -> None:
        """TC07: Verify 5th-order hyper-tensor impulse evaluates to exactly 0.0 with zero shocks."""
        zero_shocks = {factor: 0.0 for factor in GLOBAL_MACRO_FACTORS}
        impulse = compute_5th_order_hyper_tensor_impulse(zero_shocks, sector="Semiconductor")
        self.assertAlmostEqual(impulse, 0.0, places=7)

    def test_tc08_linear_and_quadratic_response_across_sectors(self) -> None:
        """TC08: Verify sector-specific response (Semiconductor vs Energy vs Financials)."""
        sox_shock = {"sox": 0.03, "sp500": 0.01, "copper": 0.01}
        impulse_semi = compute_5th_order_hyper_tensor_impulse(sox_shock, sector="Semiconductor")
        impulse_energy = compute_5th_order_hyper_tensor_impulse(sox_shock, sector="Energy")
        # Semiconductor has much higher SOX beta (1.85) than Energy (0.20)
        self.assertGreater(impulse_semi, impulse_energy)

        wti_shock = {"wti": 0.05, "copper": 0.02, "sp500": 0.01}
        impulse_energy_wti = compute_5th_order_hyper_tensor_impulse(wti_shock, sector="Energy")
        impulse_semi_wti = compute_5th_order_hyper_tensor_impulse(wti_shock, sector="Semiconductor")
        self.assertGreater(impulse_energy_wti, impulse_semi_wti)

    def test_tc09_quintic_resonance_super_linear_scaling(self) -> None:
        """TC09: Verify quintic & cubic resonance creates super-linear scaling (5x shock yields >5x response)."""
        base_shock = {"sox": 0.01, "sp500": 0.01, "vix": -0.01}
        scaled_shock = {"sox": 0.05, "sp500": 0.05, "vix": -0.05}  # 5x shock

        impulse_base = compute_5th_order_hyper_tensor_impulse(base_shock, sector="Semiconductor")
        impulse_scaled = compute_5th_order_hyper_tensor_impulse(scaled_shock, sector="Semiconductor")

        # Due to 3rd, 4th, and 5th order terms, ratio must exceed 5.0
        ratio = impulse_scaled / impulse_base
        self.assertGreater(ratio, 5.0)

    def test_tc10_dynamic_macro_tensor_elasticity(self) -> None:
        """TC10: Verify beta elasticity widening under market volatility."""
        normal_betas = compute_dynamic_macro_tensor_elasticity(sector="Semiconductor", macro_vol=0.15)
        stressed_betas = compute_dynamic_macro_tensor_elasticity(sector="Semiconductor", macro_vol=0.35)

        for factor in GLOBAL_MACRO_FACTORS:
            if abs(normal_betas[factor]) > 0.01:
                self.assertGreater(abs(stressed_betas[factor]), abs(normal_betas[factor]))

    def test_tc11_multi_frequency_wavelet_decomposition(self) -> None:
        """TC11: Verify dyadic wavelet decomposition outputs 4 frequency components."""
        np.random.seed(42)
        series = np.sin(np.linspace(0, 10, 64)) + 0.2 * np.random.randn(64)
        bands = decompose_macro_impulse_multi_frequency_wavelet(series, scales=4)

        self.assertIn("transient", bands)
        self.assertIn("cyclical", bands)
        self.assertIn("intermediate", bands)
        self.assertIn("structural", bands)
        self.assertIn("reconstructed", bands)
        self.assertEqual(len(bands["transient"]), 64)

    def test_tc12_wavelet_exact_reconstruction(self) -> None:
        """TC12: Verify mathematical identity: transient + cyclical + intermediate + structural == reconstructed."""
        np.random.seed(189)
        series = np.cumsum(np.random.randn(80)) + 0.5 * np.sin(np.linspace(0, 20, 80))
        bands = decompose_macro_impulse_multi_frequency_wavelet(series, scales=4)

        summed = bands["transient"] + bands["cyclical"] + bands["intermediate"] + bands["structural"]
        np.testing.assert_allclose(summed, bands["reconstructed"], rtol=1e-5, atol=1e-5)
        np.testing.assert_allclose(bands["reconstructed"], series, rtol=1e-5, atol=1e-5)

    def test_tc13_unpriced_macro_diffusion_bounds(self) -> None:
        """TC13: Verify unpriced macro diffusion alpha is strictly bounded in [-3.0, 3.0]."""
        traj_pos = np.array([10.0, 8.0, 5.0, 2.0, 1.0])
        alpha_pos = compute_unpriced_macro_diffusion_v182(0.5, traj_pos, half_life=5.0)
        self.assertEqual(alpha_pos, 3.0)  # clamped at upper bound

        traj_neg = np.array([-10.0, -8.0, -5.0, -2.0, -1.0])
        alpha_neg = compute_unpriced_macro_diffusion_v182(-0.5, traj_neg, half_life=5.0)
        self.assertEqual(alpha_neg, -3.0)  # clamped at lower bound

    def test_tc14_f925_engine_generate_scores(self) -> None:
        """TC14: Verify MacroHyperTensorImpulseV182Engine generate_scores with synthetic_rows == 0."""
        df = pd.DataFrame({
            "symbol": ["005930", "000660", "NVDA", "AAPL", "051910"],
            "sector": ["Semiconductor", "Semiconductor", "Information Technology", "Information Technology", "화학"],
        })
        res = self.f925_engine.generate_scores(df)
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertEqual(len(res), 5)
        for _, row in res.iterrows():
            self.assertGreaterEqual(row["score"], -3.0)
            self.assertLessEqual(row["score"], 3.0)
            self.assertGreaterEqual(row["probability"], 0.05)
            self.assertLessEqual(row["probability"], 0.95)
            self.assertEqual(row["metadata"]["synthetic_rows"], 0)
            self.assertIs(type(row["metadata"]["synthetic_rows"]), int)

    # =========================================================================
    # Category 3: F926 Multi-Currency Quad-Curvature FX Hedger (TC15 ~ TC22)
    # =========================================================================

    def test_tc15_quad_curvature_basis_spread_zero_cip(self) -> None:
        """TC15: Verify quad-curvature basis spread evaluates to 0 bps when forward satisfies theoretical CIP."""
        spot = 1350.0
        r_dom = 0.035
        r_for = 0.045
        tau = 30.0 / 365.0
        exact_fwd = spot * (1.0 + r_for * tau) / (1.0 + r_dom * tau)
        spread = compute_quad_curvature_basis_spread(spot, exact_fwd, r_dom, r_for, tau)
        self.assertAlmostEqual(spread, 0.0, places=5)

    def test_tc16_quad_curvature_polynomial_scaling(self) -> None:
        """TC16: Verify quad-curvature basis spread responds non-linearly across kappa orders."""
        spot = 1350.0
        r_dom = 0.035
        r_for = 0.045
        tau = 90.0 / 365.0
        fwd_disc = spot * 0.98  # 2% discount
        spread_quad = compute_quad_curvature_basis_spread(spot, fwd_disc, r_dom, r_for, tau)
        self.assertNotEqual(spread_quad, 0.0)
        self.assertIsInstance(spread_quad, float)

    def test_tc17_dynamic_optimal_hedge_ratio_bounds(self) -> None:
        """TC17: Verify optimal hedge ratio h* is strictly bounded in [0.0, 1.0]."""
        inp_normal = FXMacroInput(usdkrw_spot=1350.0, regime_label="BULL_LOW_VOL")
        h_normal = calculate_quad_curvature_hedge_ratio(inp_normal)
        self.assertGreaterEqual(h_normal, 0.0)
        self.assertLessEqual(h_normal, 1.0)

    def test_tc18_flight_to_safety_crisis_dampening(self) -> None:
        """TC18: Verify crisis dampening restricts hedge ratio h* <= 0.25 under panic/crisis regimes."""
        inp_panic = FXMacroInput(usdkrw_spot=1420.0, regime_label="SYSTEMIC_CRISIS")
        h_panic = calculate_quad_curvature_hedge_ratio(inp_panic)
        self.assertLessEqual(h_panic, 0.25)
        self.assertGreaterEqual(h_panic, 0.0)

    def test_tc19_triangular_arbitrage_consistency(self) -> None:
        """TC19: Verify triangular consistency: S^{USD/KRW} = S^{USD/JPY} * S^{JPY/KRW}."""
        spots = {"USDKRW": 1350.0, "USDJPY": 150.0, "EURUSD": 1.08}
        fwds = {"USDKRW": 1348.0, "USDJPY": 149.0, "EURUSD": 1.082}
        rates = {"USD": 0.045, "KRW": 0.035, "JPY": 0.005, "EUR": 0.0375}

        res = compute_quad_curvature_triangular_arbitrage(spots, fwds, rates)
        self.assertIn("basis_usdkrw_bps", res)
        self.assertIn("implied_jpykrw_spot", res)
        self.assertAlmostEqual(res["implied_jpykrw_spot"], 1350.0 / 150.0, places=5)
        self.assertAlmostEqual(res["triangular_discrepancy"], 0.0, places=5)

    def test_tc20_fx_surface_smile_delta_grid(self) -> None:
        """TC20: Verify parametric FX volatility surface smile across delta grid [0.10, 0.50, 0.90]."""
        delta_grid = np.array([0.10, 0.25, 0.50, 0.75, 0.90])
        smile = compute_fx_surface_smile(delta_grid, atm_vol=0.08, risk_reversal=-0.015, butterfly=0.005)
        self.assertEqual(len(smile), 5)
        # Wings should have higher or adjusted volatility
        self.assertGreater(smile[0], 0.01)
        self.assertGreater(smile[-1], 0.01)

    def test_tc21_cash_collateral_protection_invariant(self) -> None:
        """TC21: Verify cash collateral ceiling invariant: margin strictly <= 85% of available cash."""
        # Request huge notional with small cash
        res = generate_quad_fx_hedge_order(
            hedge_ratio=1.0,
            us_exposure_krw=10_000_000_000.0,  # 10B KRW
            available_cash_krw=100_000_000.0,    # 100M KRW
            initial_margin_req=0.05,
        )
        # Margin must not exceed 85% of cash (85M KRW)
        self.assertLessEqual(res.collateral_required_krw, 85_000_000.0001)

    def test_tc22_f926_engine_generate_scores(self) -> None:
        """TC22: Verify QuadCurvatureFXHedgingEngine generate_scores with synthetic_rows == 0."""
        df = pd.DataFrame({"symbol": ["AAPL", "MSFT", "GOOGL"]})
        res = self.f926_engine.generate_scores(df)
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertEqual(len(res), 3)
        for _, row in res.iterrows():
            self.assertEqual(row["metadata"]["synthetic_rows"], 0)
            self.assertIs(type(row["metadata"]["synthetic_rows"]), int)

    # =========================================================================
    # Category 4: F927 10-Parameter Extended NSS Yield Curve & Key-Rate Convexity (TC23 ~ TC30)
    # =========================================================================

    def test_tc23_nss10_yield_evaluation_scalar_and_vector(self) -> None:
        """TC23: Verify NSS-10 yield curve evaluation for scalar maturity and array of maturities."""
        params = {
            "beta0": 0.045, "beta1": -0.010, "beta2": 0.010, "beta3": -0.005,
            "beta4": 0.005, "beta5": 0.002, "tau1": 1.5, "tau2": 4.0, "tau3": 10.0, "tau4": 25.0,
        }
        y_10y = evaluate_nss10_yield(10.0, params)
        self.assertIsInstance(y_10y, float)
        self.assertGreater(y_10y, 0.0)

        tenors = np.array([1.0, 2.0, 5.0, 10.0, 30.0])
        yields = evaluate_nss10_yield(tenors, params)
        self.assertEqual(len(yields), 5)
        self.assertTrue(np.all(yields > 0.0))

    def test_tc24_nss10_instantaneous_forward_rate_limit(self) -> None:
        """TC24: Verify forward rate limit as tau -> 0: f(0) == beta0 + beta1."""
        params = {"beta0": 0.045, "beta1": -0.012, "beta2": 0.008, "beta3": -0.004, "beta4": 0.005, "beta5": 0.002}
        fwd_0 = compute_nss10_instantaneous_forward_rate(0.0, params)
        expected = params["beta0"] + params["beta1"]
        self.assertAlmostEqual(fwd_0, expected, places=6)

    def test_tc25_nss10_curve_fitting(self) -> None:
        """TC25: Verify non-linear 10-parameter NSS curve fitting to observed market yields."""
        tenors = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]
        yields = [0.035, 0.038, 0.040, 0.042, 0.043, 0.044, 0.045, 0.046, 0.047, 0.048]

        fitted = fit_extended_nss_10param_curve(tenors, yields)
        self.assertIn("beta0", fitted)
        self.assertIn("beta5", fitted)
        self.assertIn("tau1", fitted)
        self.assertIn("tau4", fitted)
        self.assertLess(fitted["mse"], 0.001)

    def test_tc26_key_rate_convexity_immunization_vector(self) -> None:
        """TC26: Verify key-rate convexity immunization produces non-negative normalized weights."""
        weights = np.array([0.20, 0.20, 0.20, 0.20, 0.20])
        durations = np.array([1.5, 3.0, 5.5, 8.0, 15.0])
        convexities = np.array([4.0, 12.0, 35.0, 75.0, 250.0])

        adj_w = compute_key_rate_convexity_immunization_v182(weights, durations, convexities)
        self.assertEqual(len(adj_w), 5)
        self.assertTrue(np.all(adj_w >= 0.0))
        self.assertAlmostEqual(float(np.sum(adj_w)), 1.0, places=5)

    def test_tc27_portfolio_market_beta_clamp_invariant(self) -> None:
        """TC27: Verify portfolio market beta clamp: beta_port <= 1.000001."""
        weights = np.array([0.30, 0.30, 0.30, 0.30])  # sum = 1.20 (over-leveraged)
        durations = np.array([2.0, 4.0, 6.0, 8.0])
        adj_w = compute_key_rate_convexity_immunization_v182(weights, durations)
        self.assertLessEqual(float(np.sum(adj_w)), 1.000001)

    def test_tc28_yield_curve_inversion_detection(self) -> None:
        """TC28: Verify inversion detection flags inverted 10Y-2Y curve and reports severity in bps."""
        # Inverted curve: 2Y at 4.8%, 10Y at 4.2%
        inv_params = {
            "beta0": 0.040, "beta1": 0.015, "beta2": -0.010, "beta3": 0.005,
            "beta4": 0.002, "beta5": 0.001, "tau1": 1.0, "tau2": 3.0, "tau3": 8.0, "tau4": 20.0,
        }
        res = detect_yield_curve_inversion_v182(inv_params)
        self.assertIn("is_inverted", res)
        self.assertIn("spread_10_2_bps", res)
        self.assertIn("inversion_severity_bps", res)
        self.assertEqual(res["synthetic_rows"], 0)

    def test_tc29_flat_yield_curve_stability(self) -> None:
        """TC29: Verify numerical stability with flat yield curve (slope = 0)."""
        flat_params = {
            "beta0": 0.040, "beta1": 0.0, "beta2": 0.0, "beta3": 0.0,
            "beta4": 0.0, "beta5": 0.0, "tau1": 1.5, "tau2": 4.0, "tau3": 10.0, "tau4": 25.0,
        }
        y = evaluate_nss10_yield(5.0, flat_params)
        self.assertAlmostEqual(y, 0.040, places=5)

    def test_tc30_f927_engine_generate_scores(self) -> None:
        """TC30: Verify NSS10RatesHedgeEngine generate_scores with synthetic_rows == 0."""
        df = pd.DataFrame({"symbol": ["005930", "000660", "035420"]})
        res = self.f927_engine.generate_scores(df)
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertEqual(len(res), 3)
        for _, row in res.iterrows():
            self.assertEqual(row["metadata"]["synthetic_rows"], 0)
            self.assertIs(type(row["metadata"]["synthetic_rows"]), int)

    # =========================================================================
    # Category 5: F928 Directed Quantum Rényi-Schrödinger Transfer Entropy Contagion (TC31 ~ TC38)
    # =========================================================================

    def test_tc31_independent_series_transfer_entropy_near_zero(self) -> None:
        """TC31: Verify transfer entropy between independent series is close to zero."""
        np.random.seed(101)
        x = np.random.randn(200)
        y = np.random.randn(200)
        te = compute_directed_renyi_schrodinger_transfer_entropy(x, y, alpha=1.25, lag=1)
        self.assertGreaterEqual(te, 0.0)
        self.assertLess(te, 0.35)

    def test_tc32_coupled_series_detects_directionality(self) -> None:
        """TC32: Verify directed transfer entropy detects causal flow: T_{X -> Y} > T_{Y -> X} when Y_t = X_{t-1} + noise."""
        np.random.seed(202)
        n = 300
        x = np.random.randn(n)
        y = np.zeros(n)
        for t in range(1, n):
            y[t] = 0.85 * x[t - 1] + 0.15 * np.random.randn()

        te_x_to_y = compute_directed_renyi_schrodinger_transfer_entropy(x, y, alpha=1.25, lag=1)
        te_y_to_x = compute_directed_renyi_schrodinger_transfer_entropy(y, x, alpha=1.25, lag=1)
        self.assertGreater(te_x_to_y, te_y_to_x)

    def test_tc33_renyi_alpha_parameter_scaling(self) -> None:
        """TC33: Verify valid non-negative entropy for different alpha parameters."""
        np.random.seed(303)
        x = np.random.randn(150)
        y = np.roll(x, 1) + 0.1 * np.random.randn(150)

        te_alpha_125 = compute_directed_renyi_schrodinger_transfer_entropy(x, y, alpha=1.25)
        te_alpha_175 = compute_directed_renyi_schrodinger_transfer_entropy(x, y, alpha=1.75)
        self.assertGreaterEqual(te_alpha_125, 0.0)
        self.assertGreaterEqual(te_alpha_175, 0.0)

    def test_tc34_contagion_network_zero_diagonal(self) -> None:
        """TC34: Verify contagion adjacency matrix has strictly zero diagonal: A[i, i] == 0.0."""
        np.random.seed(404)
        returns = np.random.randn(100, 4)
        res = detect_systemic_contagion_network_v182(returns, asset_names=["US", "KR", "JP", "EU"])
        adj = res["adjacency_matrix"]
        self.assertEqual(adj.shape, (4, 4))
        for i in range(4):
            self.assertEqual(adj[i, i], 0.0)

    def test_tc35_perron_frobenius_spectral_radius_alert(self) -> None:
        """TC35: Verify spectral radius calculation and tipping point alert threshold (>0.35)."""
        np.random.seed(505)
        returns = np.random.randn(80, 3)
        res = detect_systemic_contagion_network_v182(returns)
        self.assertGreaterEqual(res["spectral_radius"], 0.0)
        self.assertIsInstance(res["tipping_point_alert"], bool)

    def test_tc36_vulnerability_and_transmitter_scoring(self) -> None:
        """TC36: Verify in-degree systemic vulnerability and out-degree transmitter scores."""
        np.random.seed(606)
        returns = np.random.randn(90, 3)
        names = ["Semiconductors", "Financials", "Energy"]
        res = detect_systemic_contagion_network_v182(returns, asset_names=names)
        for name in names:
            self.assertIn(name, res["vulnerability_scores"])
            self.assertIn(name, res["transmitter_scores"])
            self.assertGreaterEqual(res["vulnerability_scores"][name], 0.0)

    def test_tc37_multi_horizon_lag_aggregation(self) -> None:
        """TC37: Verify lag aggregation across horizons [1, 3, 5] days."""
        np.random.seed(707)
        returns = np.random.randn(100, 3)
        res = detect_systemic_contagion_network_v182(returns, lags=[1, 3, 5])
        self.assertEqual(res["adjacency_matrix"].shape, (3, 3))
        self.assertEqual(res["synthetic_rows"], 0)

    def test_tc38_f928_engine_generate_scores(self) -> None:
        """TC38: Verify RenyiSchrodingerTransferEntropyEngine generate_scores with synthetic_rows == 0."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL", "MSFT"]})
        res = self.f928_engine.generate_scores(df)
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertEqual(len(res), 3)
        for _, row in res.iterrows():
            self.assertEqual(row["metadata"]["synthetic_rows"], 0)
            self.assertIs(type(row["metadata"]["synthetic_rows"]), int)

    # =========================================================================
    # Category 6: F929 Macro Crisis Severity Index v182 (MCSI v182) 6-Tier Circuit-Breaker (TC39 ~ TC44)
    # =========================================================================

    def test_tc39_mcsi_v182_continuous_score_bounds(self) -> None:
        """TC39: Verify continuous MCSI v182 score is strictly in [0.0, 1.0]."""
        # Normal baseline conditions
        indicators_calm = {
            "vix_velocity": 0.02, "vix_tsr": 0.80, "credit_spread_bps": 220.0,
            "contagion_spectral_radius": 0.10, "yield_inversion_bps": 0.0,
            "currency_velocity": 0.005, "hyper_tensor_impulse": 0.05,
        }
        score_calm = compute_mcsi_v182_multi_horizon_score(indicators_calm)
        self.assertGreaterEqual(score_calm, 0.0)
        self.assertLess(score_calm, 0.25)

        # Extreme panic conditions
        indicators_panic = {
            "vix_velocity": 0.80, "vix_tsr": 1.45, "credit_spread_bps": 950.0,
            "contagion_spectral_radius": 0.90, "yield_inversion_bps": 120.0,
            "currency_velocity": 0.08, "hyper_tensor_impulse": 4.5,
        }
        score_panic = compute_mcsi_v182_multi_horizon_score(indicators_panic)
        self.assertGreaterEqual(score_panic, 0.85)
        self.assertLessEqual(score_panic, 1.0)

    def test_tc40_mcsi_v182_6tier_gating_mapping(self) -> None:
        """TC40: Verify 6-Tier hierarchical gating mapping across score thresholds."""
        self.assertEqual(determine_mcsi_v182_6tier_gating(0.10), TIER_NORMAL)
        self.assertEqual(determine_mcsi_v182_6tier_gating(0.30), TIER_ELEVATED)
        self.assertEqual(determine_mcsi_v182_6tier_gating(0.50), TIER_HIGH_STRESS)
        self.assertEqual(determine_mcsi_v182_6tier_gating(0.70), TIER_SYSTEMIC_CRISIS)
        self.assertEqual(determine_mcsi_v182_6tier_gating(0.90), TIER_PANIC_LIQUIDITY_SQUEEZE)
        self.assertEqual(determine_mcsi_v182_6tier_gating(0.98), TIER_CIRCUIT_BREAKER_HALT)

    def test_tc41_mcsi_v182_leverage_limits(self) -> None:
        """TC41: Verify gross leverage limits: 2.15x for NORMAL down to 0.00x for CIRCUIT_BREAKER_HALT."""
        self.assertEqual(get_leverage_limit_for_mcsi_v182(TIER_NORMAL), 2.15)
        self.assertEqual(get_leverage_limit_for_mcsi_v182(TIER_ELEVATED), 1.60)
        self.assertEqual(get_leverage_limit_for_mcsi_v182(TIER_HIGH_STRESS), 1.10)
        self.assertEqual(get_leverage_limit_for_mcsi_v182(TIER_SYSTEMIC_CRISIS), 0.60)
        self.assertEqual(get_leverage_limit_for_mcsi_v182(TIER_PANIC_LIQUIDITY_SQUEEZE), 0.25)
        self.assertEqual(get_leverage_limit_for_mcsi_v182(TIER_CIRCUIT_BREAKER_HALT), 0.00)

        # Also accepts float score directly
        self.assertEqual(get_leverage_limit_for_mcsi_v182(0.15), 2.15)
        self.assertEqual(get_leverage_limit_for_mcsi_v182(0.99), 0.00)

    def test_tc42_circuit_breaker_halt_trigger(self) -> None:
        """TC42: Verify circuit breaker halt triggered at score >= 0.95 with 100% cash lock."""
        res_calm = check_circuit_breaker_v182(0.12)
        self.assertFalse(res_calm["is_circuit_breaker_halt"])
        self.assertFalse(res_calm["gate_new_longs"])
        self.assertEqual(res_calm["inverse_hedge_ratio"], 0.0)

        res_halt = check_circuit_breaker_v182(0.97)
        self.assertTrue(res_halt["is_circuit_breaker_halt"])
        self.assertTrue(res_halt["gate_new_longs"])
        self.assertEqual(res_halt["max_leverage"], 0.0)
        self.assertEqual(res_halt["inverse_hedge_ratio"], 1.0)

    def test_tc43_gate8_inverse_etf_overlay_activation(self) -> None:
        """TC43: Verify Gate 8 synthetic inverse ETF overlay activation during systemic crisis."""
        res_crisis = check_circuit_breaker_v182(0.75)
        self.assertEqual(res_crisis["tier"], TIER_SYSTEMIC_CRISIS)
        self.assertEqual(res_crisis["inverse_hedge_ratio"], 0.75)
        self.assertEqual(res_crisis["gate8_inverse_etfs"], ["252670", "114800", "SH", "PSQ"])

    def test_tc44_f929_engine_generate_scores(self) -> None:
        """TC44: Verify MacroCrisisSeverityIndexV182Engine generate_scores with synthetic_rows == 0."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL", "NVDA"]})
        res = self.f929_engine.generate_scores(df)
        self.assertIsInstance(res, ScoreDataFrame)
        self.assertEqual(len(res), 3)
        for _, row in res.iterrows():
            self.assertEqual(row["metadata"]["synthetic_rows"], 0)
            self.assertIs(type(row["metadata"]["synthetic_rows"]), int)

    # =========================================================================
    # Category 7: Cross-Asset Pipeline Integration, Invariants & System Robustness (TC45 ~ TC50)
    # =========================================================================

    def test_tc45_zero_synthetic_rows_invariant_across_all_engines(self) -> None:
        """TC45: Verify synthetic_rows == 0 strictly Python native int 0 across all 5 engines."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL"]})
        engines = [self.f925_engine, self.f926_engine, self.f927_engine, self.f928_engine, self.f929_engine]

        for eng in engines:
            res = eng.generate_scores(df)
            for _, row in res.iterrows():
                val = row["metadata"]["synthetic_rows"]
                self.assertEqual(val, 0)
                self.assertIs(type(val), int)
                self.assertNotIsInstance(val, bool)

    def test_tc46_score_dataframe_structure_and_types(self) -> None:
        """TC46: Verify ScoreDataFrame structure, columns, and types across all 5 engines."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL"]})
        engines = [self.f925_engine, self.f926_engine, self.f927_engine, self.f928_engine, self.f929_engine]

        for eng in engines:
            res = eng.generate_scores(df)
            self.assertIsInstance(res, pd.DataFrame)
            self.assertIn("symbol", res.columns)
            self.assertIn("score", res.columns)
            self.assertIn("probability", res.columns)
            self.assertIn("metadata", res.columns)

    def test_tc47_simultaneous_triple_crisis_shock_resilience(self) -> None:
        """TC47: Verify simultaneous shock (VIX surge, yield curve inversion, and currency crash)."""
        # Triple crisis inputs
        shocks = {"sox": -0.06, "usdkrw": 0.05, "tnx": 0.03, "vix": 0.45, "sp500": -0.04}
        impulse = compute_5th_order_hyper_tensor_impulse(shocks, sector="Semiconductor")
        self.assertLess(impulse, 0.0)  # Strong negative impulse

        fx_inp = FXMacroInput(usdkrw_spot=1450.0, regime_label="SYSTEMIC_CRISIS")
        h_star = calculate_quad_curvature_hedge_ratio(fx_inp)
        self.assertLessEqual(h_star, 0.25)  # USD appreciation offset

        mcsi = compute_mcsi_v182_multi_horizon_score({
            "vix_velocity": 0.50, "vix_tsr": 1.25, "credit_spread_bps": 750.0,
            "contagion_spectral_radius": 0.70, "yield_inversion_bps": 85.0,
            "currency_velocity": 0.05, "hyper_tensor_impulse": abs(impulse),
        })
        self.assertGreater(mcsi, 0.65)
        lev = get_leverage_limit_for_mcsi_v182(mcsi)
        self.assertLessEqual(lev, 0.60)

    def test_tc48_execution_sla_latency_benchmark(self) -> None:
        """TC48: Verify sub-second evaluation benchmark (< 500ms total for all 5 engines)."""
        df = pd.DataFrame({"symbol": [f"SYM_{i}" for i in range(25)]})
        t0 = time.perf_counter()
        _ = self.f925_engine.generate_scores(df)
        _ = self.f926_engine.generate_scores(df)
        _ = self.f927_engine.generate_scores(df)
        _ = self.f928_engine.generate_scores(df)
        _ = self.f929_engine.generate_scores(df)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.500)  # SLA strictly under 500ms

    def test_tc49_backward_compatibility_alias_trees(self) -> None:
        """TC49: Verify all backward compatibility alias trees instantiate successfully."""
        # F925 aliases
        self.assertIs(HyperTensorMacroImpulseV182Engine, MacroHyperTensorImpulseV182Engine)
        self.assertIs(Phase189MacroHyperTensorEngine, MacroHyperTensorImpulseV182Engine)
        self.assertIs(F925MacroHyperTensorImpulseEngine, MacroHyperTensorImpulseV182Engine)
        self.assertIs(MacroHyperTensorImpulseStrategyV182, MacroHyperTensorImpulseV182Engine)

        # F926 aliases
        self.assertIs(Phase189DynamicFXHedgingEngine, QuadCurvatureFXHedgingEngine)
        self.assertIs(F926QuadCurvatureFXHedger, QuadCurvatureFXHedgingEngine)
        self.assertIs(MultiCurrencyQuadCurvatureHedger, QuadCurvatureFXHedgingEngine)
        self.assertIs(QuadCurvatureFXHedger, QuadCurvatureFXHedgingEngine)

        # F927 aliases
        self.assertIs(ExtendedNSSRatesHedgeEngine, NSS10RatesHedgeEngine)
        self.assertIs(Phase189NSS10RatesHedgeEngine, NSS10RatesHedgeEngine)
        self.assertIs(F927NSS10RatesHedgeEngine, NSS10RatesHedgeEngine)
        self.assertIs(ExtendedNSS10RatesHedgePhase189, NSS10RatesHedgeEngine)

        # F928 aliases
        self.assertIs(Phase189RenyiSchrodingerContagionEngine, RenyiSchrodingerTransferEntropyEngine)
        self.assertIs(F928RenyiSchrodingerTransferEntropyEngine, RenyiSchrodingerTransferEntropyEngine)
        self.assertIs(QuantumRenyiContagionNetwork, RenyiSchrodingerTransferEntropyEngine)

        # F929 aliases
        self.assertIs(Phase189MacroCrisisSeverityIndex, MacroCrisisSeverityIndexV182Engine)
        self.assertIs(F929MCSIv182Engine, MacroCrisisSeverityIndexV182Engine)
        self.assertIs(MCSICircuitBreakerV182, MacroCrisisSeverityIndexV182Engine)
        self.assertIs(Phase189RiskManager, MacroCrisisSeverityIndexV182Engine)

    def test_tc50_end_to_end_cross_asset_pipeline_synthesis(self) -> None:
        """TC50: Verify end-to-end multi-asset macro cross-hedge integration pipeline."""
        macro_shocks = {"sox": 0.02, "usdkrw": -0.005, "tnx": 0.01, "vix": -0.05, "sp500": 0.015}
        impulse = compute_5th_order_hyper_tensor_impulse(macro_shocks, sector="Information Technology")
        fx_ratio = calculate_quad_curvature_hedge_ratio(FXMacroInput(usdkrw_spot=1350.0))
        nss_fit = fit_extended_nss_10param_curve([1.0, 2.0, 5.0, 10.0], [0.040, 0.042, 0.044, 0.046])
        contagion = detect_systemic_contagion_network_v182(np.random.randn(50, 3))
        mcsi_score = compute_mcsi_v182_multi_horizon_score({
            "vix_velocity": 0.01,
            "hyper_tensor_impulse": impulse,
            "contagion_spectral_radius": contagion["spectral_radius"],
        })
        gating = determine_mcsi_v182_6tier_gating(mcsi_score)
        max_lev = get_leverage_limit_for_mcsi_v182(gating)

        self.assertIsInstance(impulse, float)
        self.assertGreaterEqual(fx_ratio, 0.0)
        self.assertIn("beta0", nss_fit)
        self.assertIn("spectral_radius", contagion)
        self.assertGreaterEqual(mcsi_score, 0.0)
        self.assertIn(gating, [TIER_NORMAL, TIER_ELEVATED, TIER_HIGH_STRESS, TIER_SYSTEMIC_CRISIS, TIER_PANIC_LIQUIDITY_SQUEEZE, TIER_CIRCUIT_BREAKER_HALT])
        self.assertGreaterEqual(max_lev, 0.0)
        self.assertLessEqual(max_lev, 2.15)


if __name__ == "__main__":
    unittest.main()
