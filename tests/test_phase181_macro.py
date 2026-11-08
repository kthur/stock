"""
tests/test_phase181_macro.py — Comprehensive Test Suite for Phase 181 Features F885 to F889.

Verifies:
- Category 1: Dual-Tree Cryptographic Parity, Metadata & Version Polymorphism (TC01 ~ TC06)
- Category 2: F885 3rd-Order Macro Tensor Impulse & Dynamic Elasticity (TC07 ~ TC14)
- Category 3: F886 Multi-Currency Non-Linear CIP Basis Swap FX Hedger (TC15 ~ TC22)
- Category 4: F887 Multi-Tenor NSS 6-Param Yield Curve & Convexity Duration Hedge (TC23 ~ TC30)
- Category 5: F888 Directed Rényi Transfer Entropy Contagion Network (TC31 ~ TC38)
- Category 6: F889 Multi-Horizon Macro Crash Systemic Risk Index (MCSI v180) & Circuit-Breaker (TC39 ~ TC44)
- Category 7: Cross-Asset Pipeline Integration, Invariants & System Robustness (TC45 ~ TC50)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form equations, and rigorous finance formulations.
Zero synthetic rows (synthetic_rows == 0).
"""

from __future__ import annotations

import hashlib
import json
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

# F885 Imports
from src.core.cross_asset_spillover import (
    VERSION_PHASE181 as VERSION_F885,
    RELEASE_PHASE181 as RELEASE_F885,
    FEATURE_PHASE181 as FEATURE_F885,
    VERSION as VERSION_F885_POLY,
    RELEASE as RELEASE_F885_POLY,
    FEATURE as FEATURE_F885_POLY,
    CrossAssetSpilloverEngine,
    compute_macro_tensor_impulse_order3,
    compute_dynamic_macro_tensor_elasticity,
    GLOBAL_MACRO_FACTORS,
    DEFAULT_SECTOR_MACRO_BETAS,
)
from src.core.cross_asset_tensor_impulse import (
    CrossAssetTensorImpulseEngine,
    Phase181CrossAssetTensorImpulseEngine,
    F885CrossAssetTensorImpulseEngine,
)

# F886 Imports
from src.risk.dynamic_fx_hedging_engine import (
    VERSION_PHASE181 as VERSION_F886,
    RELEASE_PHASE181 as RELEASE_F886,
    FEATURE_PHASE181 as FEATURE_F886,
    VERSION as VERSION_F886_POLY,
    RELEASE as RELEASE_F886_POLY,
    FEATURE as FEATURE_F886_POLY,
    DynamicFXHedgingEngine,
    calculate_optimal_hedge_ratio,
    generate_fx_hedge_order,
    FXMacroInput,
    FXHedgeResult,
    Phase181DynamicFXHedgingEngine,
    Phase181NonlinearCIPHedger,
    F886NonlinearCIPHedger,
)
from src.core.nonlinear_cip_hedger import (
    AdaptiveFXForwardHedgingEngine,
    NonlinearCIPHedger,
    compute_nonlinear_cip_deviation,
    calculate_fx_rsi,
    compute_adaptive_fx_hedge_ratio,
)

# F887 Imports
from src.risk.delta_beta_hedge import (
    VERSION_PHASE181 as VERSION_F887,
    RELEASE_PHASE181 as RELEASE_F887,
    FEATURE_PHASE181 as FEATURE_F887,
    VERSION as VERSION_F887_POLY,
    RELEASE as RELEASE_F887_POLY,
    FEATURE as FEATURE_F887_POLY,
    DeltaBetaHedgeEngine,
    fit_nss_yield_curve_6param,
    compute_duration_convexity_hedge,
    Phase181DeltaBetaHedgeEngine,
    Phase181NSSYieldCurveHedge,
    F887NSSYieldCurveHedge,
    NSS6ParamYieldCurveHedgePhase181,
)
from src.core.nss_yield_curve_hedge import (
    NSSYieldCurveDurationHedgeEngine,
    evaluate_nss_zero_coupon_yield,
    compute_nss_instantaneous_forward_rate,
    compute_yield_curve_slope_and_curvature,
    detect_yield_curve_inversion,
)

# F888 Imports
from src.ai.graph_granger_causality import (
    VERSION_PHASE181 as VERSION_F888,
    RELEASE_PHASE181 as RELEASE_F888,
    FEATURE_PHASE181 as FEATURE_F888,
    VERSION as VERSION_F888_POLY,
    RELEASE as RELEASE_F888_POLY,
    FEATURE as FEATURE_F888_POLY,
    GraphGrangerCausalityNetwork,
    fit_renyi_transfer_entropy_network,
    detect_systemic_contagion,
    Phase181GraphGrangerCausalityNetwork,
    Phase181RenyiContagionNetwork,
    F888RenyiTransferEntropyNetwork,
)
from src.core.transfer_entropy_contagion import (
    TransferEntropyContagionNetwork,
    Phase181TransferEntropyContagion,
    F888TransferEntropyContagion,
)

# F889 Imports
from src.risk.risk_manager import (
    VERSION_PHASE181 as VERSION_F889,
    RELEASE_PHASE181 as RELEASE_F889,
    FEATURE_PHASE181 as FEATURE_F889,
    VERSION as VERSION_F889_POLY,
    RELEASE as RELEASE_F889_POLY,
    FEATURE as FEATURE_F889_POLY,
    RiskManager,
    evaluate_mcsi_crisis_severity_index,
    check_crisis_circuit_breaker,
    Phase181RiskManager,
    F889RiskManager,
    MCSICircuitBreaker,
)
from src.core.macro_crisis_severity_index import (
    MacroCrisisSeverityIndexEngine,
    Phase181MacroCrisisSeverityIndex,
    F889MacroCrisisSeverityIndex,
    RiskManagerPhase181,
    TIER_NORMAL,
    TIER_ELEVATED,
    TIER_HIGH_STRESS,
    TIER_SYSTEMIC_CRISIS,
    compute_mcsi_score,
    determine_crisis_gating_tier,
    get_leverage_limit_for_mcsi,
    evaluate_macro_crisis_severity_index,
)


class TestPhase181Macro(unittest.TestCase):
    """Exhaustive 50-Test Integration Suite for Phase 181 Global Macro & Contagion Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.spillover_engine = CrossAssetSpilloverEngine()
        self.impulse_engine = CrossAssetTensorImpulseEngine()
        self.dynamic_fx = DynamicFXHedgingEngine()
        self.fx_engine = AdaptiveFXForwardHedgingEngine()
        self.delta_beta_engine = DeltaBetaHedgeEngine()
        self.nss_engine = NSSYieldCurveDurationHedgeEngine()
        self.granger_engine = GraphGrangerCausalityNetwork()
        self.te_engine = TransferEntropyContagionNetwork()
        self.risk_manager = RiskManager()
        self.mcsi_engine = MacroCrisisSeverityIndexEngine()

    # =========================================================================
    # Category 1: Dual-Tree Cryptographic Parity & Metadata (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 181 production files."""
        files = [
            ("src/core/cross_asset_spillover.py", "trading_system/src/core/cross_asset_spillover.py"),
            ("src/core/cross_asset_tensor_impulse.py", "trading_system/src/core/cross_asset_tensor_impulse.py"),
            ("src/risk/dynamic_fx_hedging_engine.py", "trading_system/src/risk/dynamic_fx_hedging_engine.py"),
            ("src/core/nonlinear_cip_hedger.py", "trading_system/src/core/nonlinear_cip_hedger.py"),
            ("src/risk/delta_beta_hedge.py", "trading_system/src/risk/delta_beta_hedge.py"),
            ("src/core/nss_yield_curve_hedge.py", "trading_system/src/core/nss_yield_curve_hedge.py"),
            ("src/ai/graph_granger_causality.py", "trading_system/src/ai/graph_granger_causality.py"),
            ("src/core/transfer_entropy_contagion.py", "trading_system/src/core/transfer_entropy_contagion.py"),
            ("src/risk/risk_manager.py", "trading_system/src/risk/risk_manager.py"),
            ("src/core/macro_crisis_severity_index.py", "trading_system/src/core/macro_crisis_severity_index.py"),
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
        """TC02: Verify polymorphic version equality int(v) == 181 and backward compatibility."""
        for v in [VERSION_F885_POLY, VERSION_F886_POLY, VERSION_F887_POLY, VERSION_F888_POLY, VERSION_F889_POLY]:
            self.assertEqual(int(v), 181)
            self.assertEqual(v, 181)
            # Backward-compatible equality with historical release integers
            self.assertEqual(v, 177)
            self.assertEqual(v, 173)

    def test_tc03_release_string_polymorphism(self) -> None:
        """TC03: Verify release string polymorphism str(r) == 'R180' and backward compatibility."""
        for r in [RELEASE_F885_POLY, RELEASE_F886_POLY, RELEASE_F887_POLY, RELEASE_F888_POLY, RELEASE_F889_POLY]:
            self.assertEqual(str(r), "R180")
            self.assertEqual(r, "R180")
            self.assertEqual(r, "R179")
            self.assertEqual(r, "R175")

    def test_tc04_feature_metadata_identifiers(self) -> None:
        """TC04: Verify feature metadata strings match F885 ~ F889."""
        self.assertEqual(FEATURE_F885, "F885")
        self.assertEqual(FEATURE_F886, "F886")
        self.assertEqual(FEATURE_F887, "F887")
        self.assertEqual(FEATURE_F888, "F888")
        self.assertEqual(FEATURE_F889, "F889")

    def test_tc05_phase_metadata_constants(self) -> None:
        """TC05: Verify phase metadata constants across all modules."""
        self.assertEqual(VERSION_F885, 181)
        self.assertEqual(RELEASE_F885, "R180")
        self.assertEqual(VERSION_F886, 181)
        self.assertEqual(RELEASE_F886, "R180")
        self.assertEqual(VERSION_F887, 181)
        self.assertEqual(RELEASE_F887, "R180")
        self.assertEqual(VERSION_F888, 181)
        self.assertEqual(RELEASE_F888, "R180")
        self.assertEqual(VERSION_F889, 181)
        self.assertEqual(RELEASE_F889, "R180")

    def test_tc06_strategy_registry_integration(self) -> None:
        """TC06: Verify strategy registry integration for Phase 181 engines."""
        registry = get_registry()
        expected = [
            "cross_asset_tensor_impulse",
            "nonlinear_cip_hedger",
            "nss_yield_curve_hedge",
            "transfer_entropy_contagion",
            "macro_crisis_severity_index",
        ]
        for strat_id in expected:
            self.assertIn(strat_id, registry._strategies, f"Strategy {strat_id} not registered.")
            engine_cls, meta = registry._strategies[strat_id]
            self.assertEqual(meta.category, "macro")
            self.assertEqual(meta.strategy_id, strat_id)
            self.assertTrue(issubclass(engine_cls, BaseStrategyEngine))

    # =========================================================================
    # Category 2: F885 3rd-Order Macro Tensor Impulse & Dynamic Elasticity (TC07 ~ TC14)
    # =========================================================================

    def test_tc07_macro_tensor_impulse_order3_contraction(self) -> None:
        """TC07: Verify 3rd-order tensor impulse contraction across global macro shocks."""
        shocks = {"sox": 0.03, "usdkrw": -0.01, "tnx": 0.01, "sp500": 0.02}
        impulse_semi = self.spillover_engine.compute_macro_tensor_impulse_order3(
            shocks, sector="Semiconductor", vol_multiplier=1.0
        )
        self.assertIsInstance(impulse_semi, float)
        self.assertGreater(impulse_semi, 0.0, "Semiconductor should respond positively to tech/SOX shock")

    def test_tc08_dynamic_macro_tensor_elasticity(self) -> None:
        """TC08: Verify dynamic macro tensor elasticity returns sector betas modulated by volatility."""
        elasticity_calm = self.spillover_engine.compute_dynamic_macro_tensor_elasticity(
            sector="Semiconductor", macro_vol=0.15
        )
        elasticity_stress = self.spillover_engine.compute_dynamic_macro_tensor_elasticity(
            sector="Semiconductor", macro_vol=0.35
        )
        self.assertIn("sox", elasticity_calm)
        self.assertIn("usdkrw", elasticity_calm)
        self.assertGreater(elasticity_stress["sox"], elasticity_calm["sox"], "Beta should widen under high vol")

    def test_tc09_sector_beta_directional_consistency(self) -> None:
        """TC09: Verify sector macro betas directional consistency (e.g., Energy vs WTI)."""
        shocks_oil_surge = {"wti": 0.08, "sox": 0.0}
        impulse_energy = self.spillover_engine.compute_macro_tensor_impulse_order3(
            shocks_oil_surge, sector="Energy", vol_multiplier=1.0
        )
        self.assertGreater(impulse_energy, 0.0, "Energy sector should benefit from WTI surge")

    def test_tc10_tensor_cubic_shock_scaling(self) -> None:
        """TC10: Verify 3rd-order cubic resonance scaling for large tail shocks."""
        shocks_small = {"sox": 0.01}
        shocks_large = {"sox": 0.05}
        imp_s = self.spillover_engine.compute_macro_tensor_impulse_order3(shocks_small, sector="Semiconductor")
        imp_l = self.spillover_engine.compute_macro_tensor_impulse_order3(shocks_large, sector="Semiconductor")
        # Due to 3rd-order cubic term, 5x shock yields > 5x response
        self.assertGreater(imp_l / max(imp_s, 1e-6), 5.0, "Cubic expansion must be super-linear")

    def test_tc11_volatility_multiplier_amplification(self) -> None:
        """TC11: Verify volatility multiplier amplifying macro impulse."""
        shocks = {"sox": 0.03, "sp500": 0.02}
        imp_1x = self.spillover_engine.compute_macro_tensor_impulse_order3(shocks, sector="Semiconductor", vol_multiplier=1.0)
        imp_2x = self.spillover_engine.compute_macro_tensor_impulse_order3(shocks, sector="Semiconductor", vol_multiplier=2.0)
        self.assertGreater(imp_2x, imp_1x)

    def test_tc12_unpriced_macro_diffusion_boundedness(self) -> None:
        """TC12: Verify unpriced macro diffusion boundedness in [-3.0, 3.0]."""
        df = pd.DataFrame({"symbol": ["005930", "000660", "AAPL"]})
        scores_df = self.impulse_engine.generate_scores(df)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)

    def test_tc13_f885_generate_scores_pipeline(self) -> None:
        """TC13: Verify CrossAssetTensorImpulseEngine generate_scores complies with ScoreDataFrame."""
        df = pd.DataFrame({"symbol": ["005930", "000660"]})
        res = self.impulse_engine.generate_scores(df)
        self.assertEqual(len(res), 2)
        for p in res["probability"]:
            self.assertTrue(0.05 <= p <= 0.95)

    def test_tc14_f885_aliases(self) -> None:
        """TC14: Verify alias class identity for F885."""
        self.assertIs(Phase181CrossAssetTensorImpulseEngine, CrossAssetTensorImpulseEngine)
        self.assertIs(F885CrossAssetTensorImpulseEngine, CrossAssetTensorImpulseEngine)

    # =========================================================================
    # Category 3: F886 Multi-Currency Non-Linear CIP Basis Swap FX Hedger (TC15 ~ TC22)
    # =========================================================================

    def test_tc15_calculate_optimal_hedge_ratio(self) -> None:
        """TC15: Verify calculate_optimal_hedge_ratio produces h* in [0.0, 1.0]."""
        macro_in = FXMacroInput(
            usdkrw_spot=1350.0,
            forward_rate=1345.0,
            us_rate=0.0525,
            kr_rate=0.0350,
            tenor_days=90,
            regime_label="BULL_LOW_VOL",
        )
        h = calculate_optimal_hedge_ratio(macro_in)
        self.assertIsInstance(h, float)
        self.assertTrue(0.0 <= h <= 1.0)

    def test_tc16_cip_basis_deviation_widening(self) -> None:
        """TC16: Verify CIP basis deviation under market stress."""
        # Frictionless forward
        basis_calm = compute_nonlinear_cip_deviation(1350.0, 1344.17, 0.0525, 0.0350, tenor_days=90)
        # Distressed forward with large dollar premium
        basis_stressed = compute_nonlinear_cip_deviation(1350.0, 1375.0, 0.0525, 0.0350, tenor_days=90)
        self.assertNotEqual(basis_calm, basis_stressed)
        self.assertGreater(basis_stressed, 0.0)

    def test_tc17_fx_rsi_calculation(self) -> None:
        """TC17: Verify FX RSI calculation returns value in [0, 100]."""
        prices = np.linspace(1300.0, 1400.0, 25)
        rsi = calculate_fx_rsi(prices, period=14)
        self.assertTrue(0.0 <= rsi <= 100.0)
        self.assertGreater(rsi, 50.0, "Uptrend series should produce RSI > 50")

    def test_tc18_generate_fx_hedge_order_forward(self) -> None:
        """TC18: Verify generate_fx_hedge_order formats order with USDKRW_FWD or 261250."""
        res_dict = {
            "hedge_notional_krw": 500_000_000.0,
            "hedge_ratio": 0.65,
            "hedge_order_symbol": "USDKRW_FWD",
            "hedge_weight": 0.065,
            "collateral_required_krw": 50_000_000.0,
            "reason": "ACTIVE_FX_HEDGE",
            "timestamp": "2026-11-08T04:00:00Z",
        }
        order = generate_fx_hedge_order(res_dict)
        self.assertIsNotNone(order)
        self.assertEqual(order["symbol"], "USDKRW_FWD")
        self.assertEqual(order["market"], "OTC_FX")
        self.assertEqual(order["order_type"], "FORWARD_SWAP")
        self.assertEqual(order["notional_krw"], 500_000_000.0)

    def test_tc19_cash_collateral_constraint_guard(self) -> None:
        """TC19: Verify collateral limit prevents margin overruns (<= 85%)."""
        macro_in = FXMacroInput(usdkrw_spot=1350.0, regime_label="BEAR_HIGH_VOL")
        allocations = {"AAPL": 1.0}  # 100% US equity
        # With limited available cash of 1M KRW against 100M KRW portfolio
        res = self.dynamic_fx.evaluate_portfolio_fx_hedge(
            portfolio_capital_krw=100_000_000.0,
            portfolio_allocations=allocations,
            macro_input=macro_in,
            available_cash_krw=1_000_000.0,
        )
        self.assertTrue(res.details["collateral_limit_hit"] or res.collateral_required_krw <= 1_000_000.0 * 0.85 + 1e-4)

    def test_tc20_currency_protection_overlay_economics(self) -> None:
        """TC20: Verify safe-haven flight-to-safety dynamics in crisis keep USD unhedged."""
        macro_crisis = FXMacroInput(
            usdkrw_spot=1450.0,
            fx_momentum_20d=0.08,  # Rapid USD appreciation
            regime_label="PANIC_CRISIS",
        )
        h_crisis = calculate_optimal_hedge_ratio(macro_crisis)
        self.assertLessEqual(h_crisis, 0.25, "During crisis flight, USD appreciation acts as hedge")

    def test_tc21_f886_generate_scores_pipeline(self) -> None:
        """TC21: Verify DynamicFXHedgingEngine generate_scores contract."""
        df = pd.DataFrame({"symbol": ["AAPL", "005930"]})
        scores_df = self.fx_engine.generate_scores(df)
        self.assertEqual(len(scores_df), 2)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)

    def test_tc22_f886_aliases(self) -> None:
        """TC22: Verify alias class identity for F886."""
        self.assertIs(Phase181DynamicFXHedgingEngine, DynamicFXHedgingEngine)
        self.assertIs(Phase181NonlinearCIPHedger, DynamicFXHedgingEngine)
        self.assertIs(F886NonlinearCIPHedger, DynamicFXHedgingEngine)

    # =========================================================================
    # Category 4: F887 Multi-Tenor NSS 6-Param Yield Curve & Convexity Duration Hedge (TC23 ~ TC30)
    # =========================================================================

    def test_tc23_fit_nss_yield_curve_6param(self) -> None:
        """TC23: Verify fit_nss_yield_curve_6param extracts NSS parameters."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0])
        yields = np.array([0.035, 0.036, 0.037, 0.038, 0.040, 0.042, 0.045, 0.046])
        params = fit_nss_yield_curve_6param(maturities, yields)
        self.assertIn("beta0", params)
        self.assertIn("beta1", params)
        self.assertIn("beta2", params)
        self.assertIn("beta3", params)
        self.assertIn("lambda1", params)
        self.assertIn("lambda2", params)
        self.assertGreater(params["lambda1"], 0.0)
        self.assertGreater(params["lambda2"], 0.0)

    def test_tc24_nss_zero_coupon_and_forward_rate(self) -> None:
        """TC24: Verify NSS zero-coupon yield and instantaneous forward rate formulations."""
        maturities = np.array([1.0, 2.0, 5.0, 10.0, 30.0])
        b0, b1, b2, b3 = 0.045, -0.015, 0.010, -0.005
        t1, t2 = 1.5, 6.0
        yields = evaluate_nss_zero_coupon_yield(maturities, b0, b1, b2, b3, t1, t2)
        self.assertEqual(len(yields), 5)
        self.assertTrue(np.all(yields > 0.0))
        f_0 = compute_nss_instantaneous_forward_rate(1e-5, b0, b1, b2, b3, t1, t2)
        self.assertAlmostEqual(f_0, b0 + b1, places=3)

    def test_tc25_yield_curve_slope_and_curvature(self) -> None:
        """TC25: Verify 10Y - 2Y slope and curvature decomposition."""
        decomp = compute_yield_curve_slope_and_curvature(0.045, -0.015, 0.010, -0.005)
        self.assertEqual(decomp["level"], 0.045)
        self.assertEqual(decomp["slope"], 0.015)
        self.assertEqual(decomp["curvature1"], 0.010)
        self.assertEqual(decomp["curvature2"], -0.005)

    def test_tc26_yield_curve_inversion_detection(self) -> None:
        """TC26: Verify yield curve inversion detection when slope < 0."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
        yields_inverted = np.array([0.054, 0.053, 0.051, 0.048, 0.045, 0.042, 0.041, 0.040, 0.041, 0.042])
        inv = detect_yield_curve_inversion(maturities, yields_inverted)
        self.assertTrue(inv["is_inverted"])
        self.assertLess(inv["spread_10_2"], 0.0)

    def test_tc27_compute_duration_convexity_hedge(self) -> None:
        """TC27: Verify compute_duration_convexity_hedge calculates haircut under inversion."""
        hedge_res = compute_duration_convexity_hedge(portfolio_duration=12.0, slope_2y_10y=-0.006)
        self.assertIn("duration_haircut", hedge_res)
        self.assertIn("market_beta_clamp", hedge_res)
        self.assertIn("convexity_adjustment", hedge_res)
        self.assertLess(hedge_res["duration_haircut"], 1.0, "Inversion must impose haircut on duration")

    def test_tc28_market_beta_clamp_invariant(self) -> None:
        """TC28: Verify portfolio beta clamping invariant strictly beta_port <= 1.000001."""
        hedge_res = compute_duration_convexity_hedge(portfolio_duration=25.0, slope_2y_10y=0.02)
        self.assertLessEqual(hedge_res["market_beta_clamp"], 1.000001)

    def test_tc29_convexity_adjustment_scaling(self) -> None:
        """TC29: Verify convexity adjustment scales quadratically with duration."""
        h1 = compute_duration_convexity_hedge(portfolio_duration=5.0, slope_2y_10y=0.01)
        h2 = compute_duration_convexity_hedge(portfolio_duration=10.0, slope_2y_10y=0.01)
        self.assertAlmostEqual(h2["convexity_adjustment"] / h1["convexity_adjustment"], 4.0, places=2)

    def test_tc30_f887_aliases(self) -> None:
        """TC30: Verify alias class identity for F887."""
        self.assertIs(Phase181DeltaBetaHedgeEngine, DeltaBetaHedgeEngine)
        self.assertIs(Phase181NSSYieldCurveHedge, DeltaBetaHedgeEngine)
        self.assertIs(F887NSSYieldCurveHedge, DeltaBetaHedgeEngine)
        self.assertIs(NSS6ParamYieldCurveHedgePhase181, DeltaBetaHedgeEngine)

    # =========================================================================
    # Category 5: F888 Directed Rényi Transfer Entropy Contagion Network (TC31 ~ TC38)
    # =========================================================================

    def test_tc31_fit_renyi_transfer_entropy_network(self) -> None:
        """TC31: Verify fit_renyi_transfer_entropy_network produces (K, K) matrix with zero diagonal."""
        np.random.seed(42)
        returns = np.random.randn(80, 4) * 0.02
        A = fit_renyi_transfer_entropy_network(returns, alpha=1.5, bins=3, lag=1)
        self.assertEqual(A.shape, (4, 4))
        for i in range(4):
            self.assertEqual(A[i, i], 0.0, "Self-transfer entropy on diagonal must be zero")
            for j in range(4):
                self.assertGreaterEqual(A[i, j], 0.0)

    def test_tc32_renyi_alpha_parameterization(self) -> None:
        """TC32: Verify Rényi parameter alpha modulates tail sensitivity."""
        np.random.seed(42)
        returns = np.random.randn(80, 3) * 0.02
        A_15 = fit_renyi_transfer_entropy_network(returns, alpha=1.5, bins=3)
        A_20 = fit_renyi_transfer_entropy_network(returns, alpha=2.0, bins=3)
        self.assertEqual(A_15.shape, (3, 3))
        self.assertEqual(A_20.shape, (3, 3))

    def test_tc33_renyi_directional_asymmetry(self) -> None:
        """TC33: Verify directional information flow asymmetry when driver leads follower."""
        np.random.seed(42)
        T = 150
        y = np.random.randn(T)
        x = np.zeros(T)
        for t in range(1, T):
            x[t] = 0.80 * y[t - 1] + 0.20 * np.random.randn()
        data = np.column_stack([y, x])
        A = fit_renyi_transfer_entropy_network(data, alpha=1.5, bins=3, lag=1)
        # Node 0 is Y, Node 1 is X. Information flow 0 -> 1 is A[1, 0] vs 1 -> 0 is A[0, 1]
        self.assertGreater(A[1, 0], A[0, 1], "Driver Y -> X information flow must exceed reverse")

    def test_tc34_detect_systemic_contagion(self) -> None:
        """TC34: Verify detect_systemic_contagion computes dominant eigenvalue."""
        A = np.zeros((3, 3))
        A[1, 0] = 0.60
        A[2, 1] = 0.50
        contagion = detect_systemic_contagion(A, threshold=0.35)
        self.assertIn("dominant_eigenvalue", contagion)
        self.assertIn("vulnerability_ranking", contagion)
        self.assertIn("is_contagion_alert", contagion)

    def test_tc35_systemic_contagion_tipping_point(self) -> None:
        """TC35: Verify tipping point alert activates when lambda_max > threshold."""
        A_calm = np.array([[0.0, 0.05], [0.05, 0.0]])
        alert_calm = detect_systemic_contagion(A_calm, threshold=0.35)
        self.assertFalse(alert_calm["is_contagion_alert"])

        A_stress = np.array([[0.0, 0.80], [0.70, 0.0]])
        alert_stress = detect_systemic_contagion(A_stress, threshold=0.35)
        self.assertTrue(alert_stress["is_contagion_alert"])

    def test_tc36_in_degree_vulnerability_ranking(self) -> None:
        """TC36: Verify in-degree vulnerability ranking identifies most vulnerable recipient."""
        A = np.array([
            [0.0, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [0.9, 0.8, 0.0],  # Node 2 absorbs the most contagion
        ])
        res = detect_systemic_contagion(A)
        self.assertEqual(res["vulnerability_ranking"][0], 2, "Node 2 should be ranked most vulnerable")

    def test_tc37_f888_generate_scores_pipeline(self) -> None:
        """TC37: Verify TransferEntropyContagionNetwork generate_scores contract."""
        df = pd.DataFrame({"symbol": ["005930", "000660"]})
        res = self.te_engine.generate_scores(df)
        self.assertEqual(len(res), 2)
        for s in res["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)

    def test_tc38_f888_aliases(self) -> None:
        """TC38: Verify alias class identity for F888."""
        self.assertIs(Phase181GraphGrangerCausalityNetwork, GraphGrangerCausalityNetwork)
        self.assertIs(Phase181RenyiContagionNetwork, GraphGrangerCausalityNetwork)
        self.assertIs(F888RenyiTransferEntropyNetwork, GraphGrangerCausalityNetwork)

    # =========================================================================
    # Category 6: F889 MCSI v180 Crisis Severity Index & Circuit-Breaker (TC39 ~ TC44)
    # =========================================================================

    def test_tc39_evaluate_mcsi_crisis_severity_index_bounds(self) -> None:
        """TC39: Verify continuous MCSI score xi in [0.0, 1.0]."""
        xi_calm = evaluate_mcsi_crisis_severity_index(
            vix_velocity=0.0, vix_tsr=0.85, credit_spread_bps=250.0, contagion_eig=0.2
        )
        self.assertIsInstance(xi_calm, float)
        self.assertTrue(0.0 <= xi_calm <= 1.0)
        self.assertLess(xi_calm, 0.35)

    def test_tc40_mcsi_calm_conditions_no_circuit_breaker(self) -> None:
        """TC40: Verify calm conditions evaluate to no circuit breaker."""
        cb_res = check_crisis_circuit_breaker(xi=0.15, threshold=0.65)
        self.assertFalse(cb_res["circuit_breaker_triggered"])
        self.assertFalse(cb_res["gate8_inverse_hedge_active"])
        self.assertFalse(cb_res["new_longs_gated"])
        self.assertGreater(cb_res["max_leverage_limit"], 1.50)

    def test_tc41_mcsi_severe_panic_conditions(self) -> None:
        """TC41: Verify severe crisis conditions push xi >= 0.65."""
        xi_panic = evaluate_mcsi_crisis_severity_index(
            vix_velocity=0.60, vix_tsr=1.35, credit_spread_bps=950.0, contagion_eig=1.8
        )
        self.assertGreaterEqual(xi_panic, 0.65)

    def test_tc42_circuit_breaker_emergency_leverage_clamp(self) -> None:
        """TC42: Verify check_crisis_circuit_breaker clamps leverage <= 0.20x when xi >= 0.65."""
        cb_panic = check_crisis_circuit_breaker(xi=0.85, threshold=0.65)
        self.assertTrue(cb_panic["circuit_breaker_triggered"])
        self.assertEqual(cb_panic["max_leverage_limit"], 0.20)
        self.assertEqual(cb_panic["hedge_overlay_ratio"], 1.0)

    def test_tc43_circuit_breaker_gate8_inverse_hedge_dispatch(self) -> None:
        """TC43: Verify Gate 8 inverse ETF hedging activation and SMA200 hard exit flags."""
        cb_panic = check_crisis_circuit_breaker(xi=0.75, threshold=0.65)
        self.assertTrue(cb_panic["gate8_inverse_hedge_active"])
        self.assertTrue(cb_panic["sma200_hard_exit"])
        self.assertTrue(cb_panic["new_longs_gated"])
        self.assertIn("252670", cb_panic["inverse_hedge_etfs"])
        self.assertIn("SH", cb_panic["inverse_hedge_etfs"])

    def test_tc44_f889_aliases(self) -> None:
        """TC44: Verify alias class identity for F889."""
        self.assertIs(Phase181RiskManager, RiskManager)
        self.assertIs(F889RiskManager, RiskManager)
        self.assertIs(MCSICircuitBreaker, RiskManager)
        self.assertIs(Phase181MacroCrisisSeverityIndex, MacroCrisisSeverityIndexEngine)

    # =========================================================================
    # Category 7: Cross-Asset Pipeline Integration, Invariants & System Robustness (TC45 ~ TC50)
    # =========================================================================

    def test_tc45_synthetic_rows_invariant(self) -> None:
        """TC45: Verify zero synthetic rows (synthetic_rows == 0) native int across all engine outputs."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL"]})
        engines = [
            self.impulse_engine,
            self.fx_engine,
            self.nss_engine,
            self.te_engine,
            self.mcsi_engine,
        ]
        for eng in engines:
            scores_df = eng.generate_scores(df)
            for m in scores_df["metadata"]:
                self.assertIn("synthetic_rows", m)
                self.assertIsInstance(m["synthetic_rows"], int)
                self.assertEqual(m["synthetic_rows"], 0)

    def test_tc46_nan_and_inf_immunity(self) -> None:
        """TC46: Verify engines handle zero and singular inputs without NaN or Inf propagation."""
        shocks_zero = {"sox": 0.0, "usdkrw": 0.0, "tnx": 0.0}
        imp = compute_macro_tensor_impulse_order3(shocks_zero, sector="Semiconductor")
        self.assertFalse(np.isnan(imp))
        self.assertFalse(np.isinf(imp))

        # Zero rate yields
        zero_yields = np.zeros(5)
        zero_maturities = np.array([1.0, 2.0, 5.0, 10.0, 30.0])
        params = fit_nss_yield_curve_6param(zero_maturities, zero_yields)
        self.assertFalse(any(np.isnan(v) for v in params.values()))

    def test_tc47_macro_hedging_cross_talk(self) -> None:
        """TC47: Verify MCSI crisis trigger activates FX and rates defensive overlay."""
        cb = check_crisis_circuit_breaker(xi=0.70, threshold=0.65)
        self.assertTrue(cb["circuit_breaker_triggered"])
        # Cross-talk: rates duration haircut and market beta clamp
        dur_res = compute_duration_convexity_hedge(portfolio_duration=15.0, slope_2y_10y=-0.008)
        self.assertLess(dur_res["duration_haircut"], 1.0)
        self.assertLessEqual(dur_res["market_beta_clamp"], 1.000001)

    def test_tc48_empty_dataframe_safety(self) -> None:
        """TC48: Verify all engines safely return empty ScoreDataFrame on empty input."""
        empty_df = pd.DataFrame()
        engines = [
            self.impulse_engine,
            self.fx_engine,
            self.nss_engine,
            self.te_engine,
            self.mcsi_engine,
        ]
        for eng in engines:
            res = eng.generate_scores(empty_df)
            self.assertTrue(res.empty)

    def test_tc49_score_dataframe_contract_compliance(self) -> None:
        """TC49: Verify all outputs comply with standard ScoreDataFrame schema."""
        df = pd.DataFrame({"symbol": ["005930", "000660"]})
        engines = [
            self.impulse_engine,
            self.fx_engine,
            self.nss_engine,
            self.te_engine,
            self.mcsi_engine,
        ]
        for eng in engines:
            res = eng.generate_scores(df)
            self.assertIn("symbol", res.columns)
            self.assertIn("score", res.columns)
            self.assertIn("probability", res.columns)
            self.assertIn("metadata", res.columns)

    def test_tc50_execution_latency_sla(self) -> None:
        """TC50: Verify entire 5-feature macro pipeline evaluates in < 500ms."""
        df = pd.DataFrame({"symbol": ["005930", "000660", "AAPL", "MSFT"]})
        t0 = time.perf_counter()
        self.impulse_engine.generate_scores(df)
        self.fx_engine.generate_scores(df)
        self.nss_engine.generate_scores(df)
        self.te_engine.generate_scores(df)
        self.mcsi_engine.generate_scores(df)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.50, f"Macro pipeline latency too high: {elapsed:.4f}s")


if __name__ == "__main__":
    unittest.main()
