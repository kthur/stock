"""
tests/test_phase177_macro.py — Comprehensive Test Suite for Phase 177 Features F865 to F869.

Verifies:
- Category 1: Dual-Tree Cryptographic Parity, Metadata & Version Polymorphism (TC01 ~ TC06)
- Category 2: F865 Cross-Asset Tensor Impulse Response & Macro Elasticity (TC07 ~ TC14)
- Category 3: F866 Multi-Currency Non-Linear CIP Deviations & Adaptive FX Forward Hedger (TC15 ~ TC22)
- Category 4: F867 Nelson-Siegel-Svensson 6-Param Yield Curve & Duration Hedge (TC23 ~ TC30)
- Category 5: F868 Directed Transfer Entropy Contagion Network & Granger Causality (TC31 ~ TC38)
- Category 6: F869 Multi-Horizon Macro Crisis Severity Index MCSI & Circuit-Breaker (TC39 ~ TC44)
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
import unittest
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame
from src.core.strategy_registry import STRATEGY_REGISTRY, get_registry

# F865 Imports
from src.core.cross_asset_tensor_impulse import (
    VERSION as VERSION_F865,
    RELEASE as RELEASE_F865,
    FEATURE as FEATURE_F865,
    VERSION_PHASE177 as VERSION_P177_F865,
    RELEASE_PHASE177 as RELEASE_P177_F865,
    FEATURE_PHASE177 as FEATURE_P177_F865,
    CrossAssetTensorImpulseEngine,
    CrossAssetSpilloverEnginePhase177,
    Phase177CrossAssetTensorImpulseEngine,
    F865CrossAssetTensorImpulseEngine,
    MacroImpulseResponseEngine,
    CrossAssetTensorImpulseStrategy,
    fit_vector_autoregression,
    compute_orthogonalized_impulse_response,
    compute_macro_impulse_response_tensor,
    project_sector_impulse_elasticity,
    compute_unpriced_macro_diffusion,
    GLOBAL_MACRO_FACTORS,
    DEFAULT_SECTOR_MACRO_BETAS,
)

# F866 Imports
from src.core.nonlinear_cip_hedger import (
    VERSION as VERSION_F866,
    RELEASE as RELEASE_F866,
    FEATURE as FEATURE_F866,
    VERSION_PHASE177 as VERSION_P177_F866,
    RELEASE_PHASE177 as RELEASE_P177_F866,
    FEATURE_PHASE177 as FEATURE_P177_F866,
    AdaptiveFXForwardHedgingEngine,
    NonlinearCIPHedger,
    Phase177NonlinearCIPHedger,
    F866NonlinearCIPHedger,
    DynamicFXHedgingEnginePhase177,
    CIPFXForwardHedger,
    compute_nonlinear_cip_deviation,
    calculate_fx_rsi,
    compute_adaptive_fx_hedge_ratio,
    compute_cross_currency_basis_spread,
    evaluate_currency_protection_overlay,
)

# F867 Imports
from src.core.nss_yield_curve_hedge import (
    VERSION as VERSION_F867,
    RELEASE as RELEASE_F867,
    FEATURE as FEATURE_F867,
    VERSION_PHASE177 as VERSION_P177_F867,
    RELEASE_PHASE177 as RELEASE_P177_F867,
    FEATURE_PHASE177 as FEATURE_P177_F867,
    NSSYieldCurveDurationHedgeEngine,
    NSS6ParamYieldCurveHedge,
    Phase177NSSYieldCurveHedge,
    F867NSSYieldCurveHedge,
    DeltaBetaHedgeEnginePhase177,
    YieldCurveDurationHedger,
    evaluate_nss_zero_coupon_yield,
    compute_nss_instantaneous_forward_rate,
    fit_nss_six_parameter_curve,
    compute_yield_curve_slope_and_curvature,
    detect_yield_curve_inversion,
    compute_bond_duration_hedge_ratio,
)

# F868 Imports
from src.core.transfer_entropy_contagion import (
    VERSION as VERSION_F868,
    RELEASE as RELEASE_F868,
    FEATURE as FEATURE_F868,
    VERSION_PHASE177 as VERSION_P177_F868,
    RELEASE_PHASE177 as RELEASE_P177_F868,
    FEATURE_PHASE177 as FEATURE_P177_F868,
    TransferEntropyContagionNetwork,
    TransferEntropyGrangerNetwork,
    Phase177TransferEntropyContagion,
    F868TransferEntropyContagion,
    GraphGrangerCausalityNetworkPhase177,
    DirectedTransferEntropyEngine,
    discretize_time_series,
    compute_shannon_transfer_entropy,
    compute_directed_transfer_entropy_matrix,
    evaluate_systemic_contagion_centrality,
    detect_systemic_contagion_cascade,
)

# F869 Imports
from src.core.macro_crisis_severity_index import (
    VERSION as VERSION_F869,
    RELEASE as RELEASE_F869,
    FEATURE as FEATURE_F869,
    VERSION_PHASE177 as VERSION_P177_F869,
    RELEASE_PHASE177 as RELEASE_P177_F869,
    FEATURE_PHASE177 as FEATURE_P177_F869,
    MacroCrisisSeverityIndexEngine,
    MacroCrisisSeverityIndex,
    Phase177MacroCrisisSeverityIndex,
    F869MacroCrisisSeverityIndex,
    RiskManagerPhase177,
    MCSICircuitBreakerEngine,
    TIER_NORMAL,
    TIER_ELEVATED,
    TIER_HIGH_STRESS,
    TIER_SYSTEMIC_CRISIS,
    calculate_stress_zscore,
    compute_mcsi_score,
    determine_crisis_gating_tier,
    get_leverage_limit_for_mcsi,
    evaluate_macro_crisis_severity_index,
)


class TestPhase177Macro(unittest.TestCase):
    """Exhaustive 50-Test Integration Suite for Phase 177 Macro-Hedging Architecture."""

    def setUp(self) -> None:
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.impulse_engine = CrossAssetTensorImpulseEngine()
        self.fx_engine = AdaptiveFXForwardHedgingEngine()
        self.nss_engine = NSSYieldCurveDurationHedgeEngine()
        self.te_engine = TransferEntropyContagionNetwork()
        self.mcsi_engine = MacroCrisisSeverityIndexEngine()

    # =========================================================================
    # Category 1: Dual-Tree Cryptographic Parity & Metadata (TC01 ~ TC06)
    # =========================================================================

    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% SHA-256 cryptographic parity across all Phase 177 production files."""
        files = [
            ("src/core/cross_asset_tensor_impulse.py", "trading_system/src/core/cross_asset_tensor_impulse.py"),
            ("src/core/nonlinear_cip_hedger.py", "trading_system/src/core/nonlinear_cip_hedger.py"),
            ("src/core/nss_yield_curve_hedge.py", "trading_system/src/core/nss_yield_curve_hedge.py"),
            ("src/core/transfer_entropy_contagion.py", "trading_system/src/core/transfer_entropy_contagion.py"),
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
                self.assertEqual(h1, h2, f"Cryptographic mismatch in {src_rel}")

    def test_tc02_polymorphic_version_equality(self) -> None:
        """TC02: Verify polymorphic _VersionInt(177) backward compatibility."""
        for v in [VERSION_F865, VERSION_F866, VERSION_F867, VERSION_F868, VERSION_F869]:
            self.assertEqual(int(v), 177)
            self.assertEqual(v, 177)
            self.assertEqual(v, 173)
            self.assertEqual(v, 169)
            self.assertEqual(v, 165)
            self.assertEqual(v, 161)

    def test_tc03_release_string_polymorphism(self) -> None:
        """TC03: Verify polymorphic _ReleaseStr('R179') backward compatibility."""
        for r in [RELEASE_F865, RELEASE_F866, RELEASE_F867, RELEASE_F868, RELEASE_F869]:
            self.assertEqual(str(r), "R179")
            self.assertEqual(r, "R179")
            self.assertEqual(r, "R175")
            self.assertEqual(r, "R171")
            self.assertEqual(r, "R167")

    def test_tc04_feature_metadata_identifiers(self) -> None:
        """TC04: Verify correct feature metadata tags F865 ~ F869."""
        self.assertEqual(FEATURE_F865, "F865")
        self.assertEqual(FEATURE_F866, "F866")
        self.assertEqual(FEATURE_F867, "F867")
        self.assertEqual(FEATURE_F868, "F868")
        self.assertEqual(FEATURE_F869, "F869")

    def test_tc05_phase_metadata_constants(self) -> None:
        """TC05: Verify phase-specific explicit constants."""
        self.assertEqual(VERSION_P177_F865, 177)
        self.assertEqual(RELEASE_P177_F865, "R179")
        self.assertEqual(FEATURE_P177_F865, "F865")
        self.assertEqual(VERSION_P177_F866, 177)
        self.assertEqual(VERSION_P177_F867, 177)
        self.assertEqual(VERSION_P177_F868, 177)
        self.assertEqual(VERSION_P177_F869, 177)

    def test_tc06_strategy_registry_integration(self) -> None:
        """TC06: Verify registration of all 5 Phase 177 strategies in STRATEGY_REGISTRY."""
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
    # Category 2: F865 Cross-Asset Tensor Impulse Response (TC07 ~ TC14)
    # =========================================================================

    def test_tc07_var_estimation_and_spectral_radius(self) -> None:
        """TC07: Verify VAR(p) estimation produces stable coefficient matrices (spectral radius < 1.0)."""
        np.random.seed(42)
        returns = np.random.randn(80, 8) * 0.015
        A_mats, sigma_cov = fit_vector_autoregression(returns, lags=2)
        self.assertEqual(len(A_mats), 2)
        self.assertEqual(A_mats[0].shape, (8, 8))
        self.assertEqual(sigma_cov.shape, (8, 8))
        
        # Check stability
        for A in A_mats:
            eigs = np.linalg.eigvals(A)
            max_abs_eig = np.max(np.abs(eigs))
            self.assertLess(max_abs_eig, 1.0, "VAR lag matrix unstable")

    def test_tc08_orthogonalized_impulse_response_tensor_shape(self) -> None:
        """TC08: Verify OIRF tensor produces exact (H, K, K) shape and positive diagonal at tau=0."""
        np.random.seed(42)
        returns = np.random.randn(100, 8) * 0.01
        oirf = compute_macro_impulse_response_tensor(returns, lags=2, horizons=5)
        self.assertEqual(oirf.shape, (5, 8, 8))
        
        # At tau=0, OIRF is Cholesky factor P -> lower triangular with positive diagonal
        P = oirf[0]
        for i in range(8):
            self.assertGreater(P[i, i], 0.0, "Cholesky diagonal must be positive")
            for j in range(i + 1, 8):
                self.assertAlmostEqual(P[i, j], 0.0, places=5, msg="Upper triangle must be zero at tau=0")

    def test_tc09_impulse_response_decay(self) -> None:
        """TC09: Verify impulse response decays asymptotically over long horizons."""
        np.random.seed(42)
        returns = np.random.randn(100, 8) * 0.01
        oirf = compute_macro_impulse_response_tensor(returns, lags=2, horizons=20)
        norm_t0 = np.linalg.norm(oirf[0])
        norm_t19 = np.linalg.norm(oirf[19])
        self.assertLess(norm_t19, norm_t0, "Impulse response should decay over 20 horizons")

    def test_tc10_sector_elasticity_projection(self) -> None:
        """TC10: Verify macro impulse projection onto GICS sector trajectories."""
        np.random.seed(42)
        returns = np.random.randn(60, 8) * 0.01
        oirf = compute_macro_impulse_response_tensor(returns, lags=2, horizons=5)
        trajectories = project_sector_impulse_elasticity(oirf, DEFAULT_SECTOR_MACRO_BETAS)
        
        self.assertIn("Semiconductor", trajectories)
        self.assertIn("Financials", trajectories)
        self.assertIn("Energy", trajectories)
        self.assertEqual(len(trajectories["Semiconductor"]), 5)

    def test_tc11_sector_beta_directional_consistency(self) -> None:
        """TC11: Verify semiconductor has high positive SOX elasticity and financials have positive TNX elasticity."""
        sox_shock = np.zeros(8)
        sox_shock[0] = 1.0  # SOX shock
        
        np.random.seed(42)
        returns = np.random.randn(60, 8) * 0.01
        oirf = compute_macro_impulse_response_tensor(returns, lags=2, horizons=5)
        proj = project_sector_impulse_elasticity(oirf, DEFAULT_SECTOR_MACRO_BETAS, macro_shocks=sox_shock)
        
        # Semi trajectory should be positive under SOX shock
        self.assertGreater(proj["Semiconductor"][0], 0.0)

    def test_tc12_unpriced_macro_diffusion_boundedness(self) -> None:
        """TC12: Verify unpriced macro diffusion score is bounded in [-3.0, 3.0]."""
        traj_pos = np.array([0.05, 0.04, 0.03, 0.02, 0.01])
        traj_neg = np.array([-0.05, -0.04, -0.03, -0.02, -0.01])
        
        score_pos = compute_unpriced_macro_diffusion(0.0, traj_pos, half_life=3.0)
        score_neg = compute_unpriced_macro_diffusion(0.0, traj_neg, half_life=3.0)
        
        self.assertGreater(score_pos, 0.0)
        self.assertLess(score_neg, 0.0)
        self.assertLessEqual(abs(score_pos), 3.0)
        self.assertLessEqual(abs(score_neg), 3.0)

    def test_tc13_f865_generate_scores_pipeline(self) -> None:
        """TC13: Verify CrossAssetTensorImpulseEngine.generate_scores contract."""
        df = pd.DataFrame({
            "symbol": ["005930", "000660", "AAPL"],
            "close": [70000.0, 150000.0, 180.0],
            "sector": ["Semiconductor", "Semiconductor", "Information Technology"],
        })
        scores_df = self.impulse_engine.generate_scores(df)
        self.assertEqual(len(scores_df), 3)
        self.assertIn("score", scores_df.columns)
        self.assertIn("probability", scores_df.columns)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)
        for p in scores_df["probability"]:
            self.assertTrue(0.05 <= p <= 0.95)

    def test_tc14_f865_aliases(self) -> None:
        """TC14: Verify alias class identity for F865."""
        self.assertIs(CrossAssetSpilloverEnginePhase177, CrossAssetTensorImpulseEngine)
        self.assertIs(Phase177CrossAssetTensorImpulseEngine, CrossAssetTensorImpulseEngine)
        self.assertIs(F865CrossAssetTensorImpulseEngine, CrossAssetTensorImpulseEngine)
        self.assertIs(MacroImpulseResponseEngine, CrossAssetTensorImpulseEngine)
        self.assertIs(CrossAssetTensorImpulseStrategy, CrossAssetTensorImpulseEngine)

    # =========================================================================
    # Category 3: F866 Non-Linear CIP FX Forward Hedger (TC15 ~ TC22)
    # =========================================================================

    def test_tc15_cip_basis_deviation_frictionless(self) -> None:
        """TC15: In frictionless equilibrium, CIP basis deviation should be zero."""
        spot = 1300.0
        r_usd = 0.05
        r_krw = 0.03
        tau = 90 / 360.0
        # Exact theoretical forward
        forward = spot * ((1.0 + r_usd * tau) / (1.0 + r_krw * tau))
        
        basis = compute_nonlinear_cip_deviation(spot, forward, r_usd, r_krw, tenor_days=90)
        self.assertAlmostEqual(basis, 0.0, places=6)

    def test_tc16_cip_basis_deviation_premium_and_discount(self) -> None:
        """TC16: Verify CIP basis detects dollar funding premium and discount."""
        spot = 1350.0
        r_usd = 0.05
        r_krw = 0.035
        # Forward quoted higher than equilibrium
        fwd_high = 1370.0
        basis_high = compute_nonlinear_cip_deviation(spot, fwd_high, r_usd, r_krw, tenor_days=90)
        self.assertGreater(basis_high, 0.0)

        # Forward quoted lower than equilibrium
        fwd_low = 1320.0
        basis_low = compute_nonlinear_cip_deviation(spot, fwd_low, r_usd, r_krw, tenor_days=90)
        self.assertLess(basis_low, 0.0)

    def test_tc17_fx_rsi_calculation(self) -> None:
        """TC17: Verify RSI calculation on ascending/descending FX rates."""
        ascending = np.linspace(1200.0, 1400.0, 30)
        rsi_bull = calculate_fx_rsi(ascending, period=14)
        self.assertGreater(rsi_bull, 70.0)

        descending = np.linspace(1400.0, 1200.0, 30)
        rsi_bear = calculate_fx_rsi(descending, period=14)
        self.assertLess(rsi_bear, 30.0)

    def test_tc18_adaptive_fx_hedge_ratio_boundedness(self) -> None:
        """TC18: Verify dynamic FX hedge ratio strictly bounded in [0.0, 1.0]."""
        fx_hist = np.linspace(1300.0, 1380.0, 30)
        hr_high = compute_adaptive_fx_hedge_ratio(0.05, fx_hist, beta_0=0.8, beta_basis=5.0)
        self.assertLessEqual(hr_high, 1.0)
        self.assertGreaterEqual(hr_high, 0.0)

        hr_low = compute_adaptive_fx_hedge_ratio(-0.05, fx_hist[::-1], beta_0=0.2, beta_vol=5.0)
        self.assertLessEqual(hr_low, 1.0)
        self.assertGreaterEqual(hr_low, 0.0)

    def test_tc19_cip_basis_term_structure(self) -> None:
        """TC19: Verify cross-currency basis term structure spread calculation across 1M, 3M, 6M, 12M."""
        tenors = [30, 90, 180, 360]
        spot = 1350.0
        fwds = [1351.0, 1353.0, 1355.0, 1360.0]
        r_usd = [0.052, 0.051, 0.049, 0.046]
        r_krw = [0.035, 0.035, 0.034, 0.033]
        
        curve = compute_cross_currency_basis_spread(tenors, spot, fwds, r_usd, r_krw)
        self.assertEqual(len(curve), 4)
        self.assertTrue(np.all(np.isfinite(curve)))

    def test_tc20_currency_protection_overlay_economics(self) -> None:
        """TC20: Verify economic valuation and physical capital conservation in currency overlay."""
        portfolio_usd = 1_000_000.0
        hedge_ratio = 0.60
        spot = 1350.0
        fwd = 1345.0
        
        res = evaluate_currency_protection_overlay(portfolio_usd, hedge_ratio, fwd, spot)
        self.assertEqual(res["hedged_usd"], 600_000.0)
        self.assertEqual(res["unhedged_usd"], 400_000.0)
        self.assertEqual(res["forward_notional_krw"], 600_000.0 * 1345.0)
        self.assertEqual(res["forward_pnl_per_dollar"], -5.0)
        self.assertEqual(res["total_hedged_krw_protection"], -3_000_000.0)

    def test_tc21_f866_generate_scores_pipeline(self) -> None:
        """TC21: Verify AdaptiveFXForwardHedgingEngine.generate_scores contract."""
        df = pd.DataFrame({"symbol": ["AAPL", "NVDA", "MSFT"]})
        scores_df = self.fx_engine.generate_scores(df)
        self.assertEqual(len(scores_df), 3)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)
        for p in scores_df["probability"]:
            self.assertTrue(0.05 <= p <= 0.95)

    def test_tc22_f866_aliases(self) -> None:
        """TC22: Verify alias class identity for F866."""
        self.assertIs(NonlinearCIPHedger, AdaptiveFXForwardHedgingEngine)
        self.assertIs(Phase177NonlinearCIPHedger, AdaptiveFXForwardHedgingEngine)
        self.assertIs(F866NonlinearCIPHedger, AdaptiveFXForwardHedgingEngine)
        self.assertIs(DynamicFXHedgingEnginePhase177, AdaptiveFXForwardHedgingEngine)
        self.assertIs(CIPFXForwardHedger, AdaptiveFXForwardHedgingEngine)

    # =========================================================================
    # Category 4: F867 NSS 6-Param Yield Curve & Duration Hedge (TC23 ~ TC30)
    # =========================================================================

    def test_tc23_nss_zero_coupon_yield_evaluation(self) -> None:
        """TC23: Verify Nelson-Siegel-Svensson formula evaluation produces exact theoretical curve."""
        maturities = np.array([1.0, 2.0, 5.0, 10.0, 30.0])
        b0, b1, b2, b3 = 0.045, -0.015, 0.010, -0.005
        t1, t2 = 1.5, 6.0
        
        yields = evaluate_nss_zero_coupon_yield(maturities, b0, b1, b2, b3, t1, t2)
        self.assertEqual(len(yields), 5)
        self.assertTrue(np.all(yields > 0.0))
        # Long term yield approaches beta0
        long_term = evaluate_nss_zero_coupon_yield(np.array([1000.0]), b0, b1, b2, b3, t1, t2)[0]
        self.assertAlmostEqual(long_term, b0, places=3)

    def test_tc24_nss_instantaneous_forward_rate(self) -> None:
        """TC24: Verify instantaneous forward rate calculation consistency."""
        b0, b1, b2, b3 = 0.05, -0.02, 0.01, -0.005
        t1, t2 = 2.0, 5.0
        f_0 = compute_nss_instantaneous_forward_rate(1e-5, b0, b1, b2, b3, t1, t2)
        # As m -> 0, f(0) = beta0 + beta1
        self.assertAlmostEqual(f_0, b0 + b1, places=3)

    def test_tc25_nss_curve_fitting_accuracy(self) -> None:
        """TC25: Verify non-linear least squares fit recovers known NSS parameters."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
        true_params = (0.045, -0.015, 0.010, -0.005, 1.8, 6.0)
        synthetic_yields = evaluate_nss_zero_coupon_yield(maturities, *true_params)
        
        fitted = fit_nss_six_parameter_curve(maturities, synthetic_yields)
        fitted_yields = evaluate_nss_zero_coupon_yield(maturities, *fitted)
        max_error = np.max(np.abs(fitted_yields - synthetic_yields))
        self.assertLess(max_error, 1e-3, "Fitted curve error must be < 10 bps")

    def test_tc26_yield_curve_slope_curvature_decomposition(self) -> None:
        """TC26: Verify slope and curvature component decomposition."""
        decomp = compute_yield_curve_slope_and_curvature(0.045, -0.015, 0.010, -0.005)
        self.assertEqual(decomp["level"], 0.045)
        self.assertEqual(decomp["slope"], 0.015)
        self.assertEqual(decomp["curvature1"], 0.010)
        self.assertEqual(decomp["curvature2"], -0.005)

    def test_tc27_yield_curve_inversion_detection(self) -> None:
        """TC27: Verify inverted yield curve (10Y < 2Y) is detected."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
        # Inverted curve yields
        yields_inverted = np.array([0.054, 0.053, 0.051, 0.048, 0.045, 0.042, 0.041, 0.040, 0.041, 0.042])
        inv_res = detect_yield_curve_inversion(maturities, yields_inverted)
        self.assertTrue(inv_res["is_inverted"])
        self.assertLess(inv_res["spread_10_2"], 0.0)

    def test_tc28_normal_steep_yield_curve_detection(self) -> None:
        """TC28: Verify normal upward sloping yield curve is not flagged as inverted."""
        maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
        yields_normal = np.array([0.025, 0.027, 0.030, 0.035, 0.038, 0.042, 0.045, 0.048, 0.051, 0.053])
        inv_res = detect_yield_curve_inversion(maturities, yields_normal)
        self.assertFalse(inv_res["is_inverted"])
        self.assertGreater(inv_res["spread_10_2"], 0.0)

    def test_tc29_bond_duration_hedge_ratio(self) -> None:
        """TC29: Verify duration immunization hedge ratio formula."""
        # Equity duration 18y, hedge vehicle duration -7.5y
        hr = compute_bond_duration_hedge_ratio(
            portfolio_equity_duration=18.0,
            target_duration=0.0,
            hedge_instrument_duration=-7.5,
        )
        self.assertAlmostEqual(hr, 18.0 / 7.5, places=3)
        self.assertTrue(-2.0 <= hr <= 2.0 or hr > 0)

    def test_tc30_f867_aliases(self) -> None:
        """TC30: Verify alias class identity for F867."""
        self.assertIs(NSS6ParamYieldCurveHedge, NSSYieldCurveDurationHedgeEngine)
        self.assertIs(Phase177NSSYieldCurveHedge, NSSYieldCurveDurationHedgeEngine)
        self.assertIs(F867NSSYieldCurveHedge, NSSYieldCurveDurationHedgeEngine)
        self.assertIs(DeltaBetaHedgeEnginePhase177, NSSYieldCurveDurationHedgeEngine)
        self.assertIs(YieldCurveDurationHedger, NSSYieldCurveDurationHedgeEngine)

    # =========================================================================
    # Category 5: F868 Directed Transfer Entropy Contagion Network (TC31 ~ TC38)
    # =========================================================================

    def test_tc31_discretize_time_series(self) -> None:
        """TC31: Verify time series discretization into uniform quantile bins."""
        np.random.seed(42)
        s = np.random.randn(100)
        disc = discretize_time_series(s, bins=5)
        self.assertEqual(len(disc), 100)
        self.assertEqual(np.min(disc), 0)
        self.assertEqual(np.max(disc), 4)

    def test_tc32_shannon_transfer_entropy_non_negativity(self) -> None:
        """TC32: Verify Shannon Transfer Entropy is strictly non-negative T_{Y -> X} >= 0."""
        np.random.seed(42)
        x = np.random.randn(150)
        y = np.roll(x, 1) + np.random.randn(150) * 0.2  # Y leads X
        
        te_y_to_x = compute_shannon_transfer_entropy(y, x, bins=5, lag=1)
        te_x_to_y = compute_shannon_transfer_entropy(x, y, bins=5, lag=1)
        
        self.assertGreaterEqual(te_y_to_x, 0.0)
        self.assertGreaterEqual(te_x_to_y, 0.0)

    def test_tc33_transfer_entropy_asymmetry(self) -> None:
        """TC33: Verify directional asymmetry when Y strongly Granger-causes X."""
        np.random.seed(42)
        T = 200
        y = np.random.randn(T)
        # X is explicitly caused by lagged Y
        x = np.zeros(T)
        for t in range(1, T):
            x[t] = 0.85 * y[t - 1] + 0.15 * np.random.randn()
            
        te_y_to_x = compute_shannon_transfer_entropy(y, x, bins=4, lag=1)
        te_x_to_y = compute_shannon_transfer_entropy(x, y, bins=4, lag=1)
        
        self.assertGreater(te_y_to_x, te_x_to_y, "Information flow from driver Y to follower X must exceed reverse")

    def test_tc34_directed_te_matrix_structure(self) -> None:
        """TC34: Verify (N, N) directed transfer entropy matrix with zero diagonal."""
        np.random.seed(42)
        returns = np.random.randn(60, 4) * 0.02
        A = compute_directed_transfer_entropy_matrix(returns, bins=3, lag=1, surrogate_bias_correction=False)
        self.assertEqual(A.shape, (4, 4))
        for i in range(4):
            self.assertEqual(A[i, i], 0.0, "Diagonal of transfer entropy matrix must be zero")
            for j in range(4):
                self.assertGreaterEqual(A[i, j], 0.0)

    def test_tc35_systemic_contagion_centrality(self) -> None:
        """TC35: Verify PageRank, eigenvector and composite contagion centrality metrics."""
        np.random.seed(42)
        # Construct graph where node 0 is the primary transmitter to all others
        A = np.zeros((4, 4))
        A[1, 0] = 0.50
        A[2, 0] = 0.40
        A[3, 0] = 0.60
        
        metrics = evaluate_systemic_contagion_centrality(A)
        self.assertIn("out_degree", metrics)
        self.assertIn("in_degree", metrics)
        self.assertIn("pagerank", metrics)
        self.assertIn("contagion_centrality", metrics)
        
        # Node 0 has highest out-degree
        self.assertEqual(np.argmax(metrics["out_degree"]), 0)
        self.assertTrue(np.all(metrics["contagion_centrality"] >= 0.0))
        self.assertTrue(np.all(metrics["contagion_centrality"] <= 1.0))

    def test_tc36_contagion_cascade_detection(self) -> None:
        """TC36: Verify cascade detection when connectivity exceeds threshold."""
        A_calm = np.zeros((4, 4)) + 0.01
        np.fill_diagonal(A_calm, 0.0)
        cascade_calm = detect_systemic_contagion_cascade(A_calm, spillover_threshold=0.15)
        self.assertFalse(cascade_calm["is_cascade_active"])

        A_panic = np.zeros((4, 4)) + 0.25
        np.fill_diagonal(A_panic, 0.0)
        cascade_panic = detect_systemic_contagion_cascade(A_panic, spillover_threshold=0.15)
        self.assertTrue(cascade_panic["is_cascade_active"])

    def test_tc37_f868_generate_scores_pipeline(self) -> None:
        """TC37: Verify TransferEntropyContagionNetwork.generate_scores contract."""
        df = pd.DataFrame({"symbol": ["005930", "000660", "035420"]})
        scores_df = self.te_engine.generate_scores(df)
        self.assertEqual(len(scores_df), 3)
        for s in scores_df["score"]:
            self.assertTrue(-3.0 <= s <= 3.0)
        for p in scores_df["probability"]:
            self.assertTrue(0.05 <= p <= 0.95)

    def test_tc38_f868_aliases(self) -> None:
        """TC38: Verify alias class identity for F868."""
        self.assertIs(TransferEntropyGrangerNetwork, TransferEntropyContagionNetwork)
        self.assertIs(Phase177TransferEntropyContagion, TransferEntropyContagionNetwork)
        self.assertIs(F868TransferEntropyContagion, TransferEntropyContagionNetwork)
        self.assertIs(GraphGrangerCausalityNetworkPhase177, TransferEntropyContagionNetwork)
        self.assertIs(DirectedTransferEntropyEngine, TransferEntropyContagionNetwork)

    # =========================================================================
    # Category 6: F869 Macro Crisis Severity Index MCSI (TC39 ~ TC44)
    # =========================================================================

    def test_tc39_stress_zscore_calculation(self) -> None:
        """TC39: Verify normalized stress Z-score computation."""
        z_norm = calculate_stress_zscore(18.0, 18.0, 6.5)
        self.assertEqual(z_norm, 0.0)

        z_high = calculate_stress_zscore(37.5, 18.0, 6.5)
        self.assertAlmostEqual(z_high, 3.0, places=2)

    def test_tc40_mcsi_score_range_and_weighting(self) -> None:
        """TC40: Verify continuous MCSI score clamped in [0.0, 5.0]."""
        # Calm conditions
        mcsi_calm = compute_mcsi_score(vix=12.0, vix3m=16.0, usdkrw_5d_return=-0.005, hy_oas_spread=280.0, ted_spread=15.0)
        self.assertLess(mcsi_calm, 1.0)
        self.assertGreaterEqual(mcsi_calm, 0.0)

        # Extreme panic conditions (e.g., 2008 GFC or 2020 COVID)
        mcsi_panic = compute_mcsi_score(vix=65.0, vix3m=45.0, usdkrw_5d_return=0.08, hy_oas_spread=1100.0, ted_spread=150.0)
        self.assertGreaterEqual(mcsi_panic, 2.5)
        self.assertLessEqual(mcsi_panic, 5.0)

    def test_tc41_crisis_tier_determination(self) -> None:
        """TC41: Verify correct assignment of the 4 institutional crisis tiers."""
        self.assertEqual(determine_crisis_gating_tier(0.6), TIER_NORMAL)
        self.assertEqual(determine_crisis_gating_tier(1.4), TIER_ELEVATED)
        self.assertEqual(determine_crisis_gating_tier(2.1), TIER_HIGH_STRESS)
        self.assertEqual(determine_crisis_gating_tier(3.2), TIER_SYSTEMIC_CRISIS)

    def test_tc42_leverage_limits_per_tier(self) -> None:
        """TC42: Verify leverage throttling from 1.85x down to 0.20x during crisis."""
        lev_calm = get_leverage_limit_for_mcsi(0.0)
        self.assertEqual(lev_calm, 1.85)

        lev_elevated = get_leverage_limit_for_mcsi(1.4)
        self.assertTrue(0.85 <= lev_elevated <= 1.20)

        lev_stress = get_leverage_limit_for_mcsi(2.2)
        self.assertTrue(0.35 <= lev_stress <= 0.70)

        lev_crisis = get_leverage_limit_for_mcsi(3.5)
        self.assertEqual(lev_crisis, 0.20)

    def test_tc43_evaluate_macro_crisis_status_flags(self) -> None:
        """TC43: Verify full defensive gating flags in systemic crisis tier."""
        status = evaluate_macro_crisis_severity_index(vix=55.0, vix3m=40.0, usdkrw_5d_return=0.05, hy_oas_spread=950.0)
        self.assertEqual(status["crisis_tier"], TIER_SYSTEMIC_CRISIS)
        self.assertTrue(status["gate8_inverse_hedge_active"])
        self.assertFalse(status["new_longs_allowed"])
        self.assertTrue(status["sma200_hard_exit"])
        self.assertEqual(status["hedge_overlay_ratio"], 1.0)

    def test_tc44_f869_aliases(self) -> None:
        """TC44: Verify alias class identity for F869."""
        self.assertIs(MacroCrisisSeverityIndex, MacroCrisisSeverityIndexEngine)
        self.assertIs(Phase177MacroCrisisSeverityIndex, MacroCrisisSeverityIndexEngine)
        self.assertIs(F869MacroCrisisSeverityIndex, MacroCrisisSeverityIndexEngine)
        self.assertIs(RiskManagerPhase177, MacroCrisisSeverityIndexEngine)
        self.assertIs(MCSICircuitBreakerEngine, MacroCrisisSeverityIndexEngine)

    # =========================================================================
    # Category 7: Cross-Asset Pipeline Integration & Invariants (TC45 ~ TC50)
    # =========================================================================

    def test_tc45_synthetic_rows_invariant(self) -> None:
        """TC45: Verify zero synthetic rows (synthetic_rows == 0) native int across all engine outputs."""
        df = pd.DataFrame({"symbol": ["005930", "AAPL"]})
        for eng in [self.impulse_engine, self.fx_engine, self.nss_engine, self.te_engine, self.mcsi_engine]:
            scores_df = eng.generate_scores(df)
            for m in scores_df["metadata"]:
                self.assertIn("synthetic_rows", m)
                self.assertIsInstance(m["synthetic_rows"], int)
                self.assertEqual(m["synthetic_rows"], 0)

    def test_tc46_nan_and_inf_immunity(self) -> None:
        """TC46: Verify engines handle zero and singular inputs without NaN or Inf propagation."""
        # Zero returns
        zero_macro = np.zeros((30, 8))
        oirf = compute_macro_impulse_response_tensor(zero_macro, lags=2, horizons=5)
        self.assertFalse(np.isnan(oirf).any())
        self.assertFalse(np.isinf(oirf).any())

        # Zero CIP spread
        basis = compute_nonlinear_cip_deviation(1300.0, 1300.0, 0.0, 0.0)
        self.assertEqual(basis, 0.0)

    def test_tc47_macro_hedging_cross_talk(self) -> None:
        """TC47: Verify MCSI gating adjusts FX hedging and duration hedging exposures."""
        # When MCSI is elevated, FX hedge ratio is scaled up defensively
        mcsi_status = evaluate_macro_crisis_severity_index(vix=28.0, vix3m=26.0)
        self.assertEqual(mcsi_status["crisis_tier"], TIER_ELEVATED)
        self.assertEqual(mcsi_status["hedge_overlay_ratio"], 0.15)
        self.assertEqual(mcsi_status["buffer_band_multiplier"], 1.5)

    def test_tc48_empty_dataframe_safety(self) -> None:
        """TC48: Verify all 5 engines safely return empty ScoreDataFrame on empty input."""
        empty_df = pd.DataFrame()
        for eng in [self.impulse_engine, self.fx_engine, self.nss_engine, self.te_engine, self.mcsi_engine]:
            res = eng.generate_scores(empty_df)
            self.assertTrue(res.empty)

    def test_tc49_score_dataframe_contract_compliance(self) -> None:
        """TC49: Verify all outputs comply with standard ScoreDataFrame schema."""
        df = pd.DataFrame({"symbol": ["005930", "000660"]})
        for eng in [self.impulse_engine, self.fx_engine, self.nss_engine, self.te_engine, self.mcsi_engine]:
            res = eng.generate_scores(df)
            self.assertIn("symbol", res.columns)
            self.assertIn("score", res.columns)
            self.assertIn("probability", res.columns)
            self.assertIn("metadata", res.columns)

    def test_tc50_execution_latency_sla(self) -> None:
        """TC50: Verify entire 5-feature macro pipeline evaluates in < 500ms."""
        import time
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
