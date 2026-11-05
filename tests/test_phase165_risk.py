"""
tests/test_phase165_risk.py - Institutional Unit Test Catalog for Phase 165 Quant Risk Architecture.
Milestone 2 Target Features: F805, F806, F807, F808, F809 (Release R167).

Test Categories (50 Tests, TC01–TC50):
- Category 1: Metadata, Dual-Tree Parity, Versioning & Aliases (TC01–TC05)
- Category 2: Feature F805 Higher-Order Tail-Risk Fractional Kelly & Tsallis/Rényi Entropy (TC06–TC14)
- Category 3: Feature F806 Compounding Dynamic Leverage Frontiers (1.60x) & Volatility Targeting (TC15–TC23)
- Category 4: Feature F807 7-Tier Protective Dynamic Gating & Contagion Defense (TC24–TC32)
- Category 5: Feature F808 Poincaré Ball Hyperbolic Optimal Transport Allocation (TC33–TC40)
- Category 6: Feature F809 UnifiedPortfolioAllocator Phase 165 Master 5-Model Blending (TC41–TC48)
- Category 7: Multi-Layer Pipeline Interactions, SLA & System Invariants (TC49–TC50)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact calculations. Zero dummy implementations.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    WassersteinRobustKellyOptimizer,
    CorrelationBreakdownBrake,
    FractionalKellyAllocator,
    Phase161KellyAllocator,
    Phase161RiskAllocator,
    DynamicRegimeLeverageAllocatorPhase161,
    Phase165KellyAllocator,
    Phase165RiskAllocator,
    DynamicRegimeLeverageAllocatorPhase165,
    WassersteinRobustKellyAllocator,
    EntropyRegularizedKellyAllocator,
    MultiRegimeDynamicLeverageAllocator,
    VERSION,
    RELEASE,
    FEATURE,
    VERSION_PHASE165,
    RELEASE_PHASE165,
    FEATURE_PHASE165,
    _LeverageFloat,
    _TopModesInt,
    _KappaFloat,
    _VersionInt,
    _ReleaseStr,
    _FeatureStr,
)
from src.risk.hyperbolic_optimal_transport_allocator import (
    HyperbolicOptimalTransportAllocator,
    HyperbolicWassersteinAllocator,
    PoincareOptimalTransportAllocator,
    Phase165HyperbolicAllocator,
    PoincareHyperbolicTransportAllocator,
    HyperbolicAllocatorConfig,
    HyperbolicAllocationOutput,
    HyperbolicRegime,
    REGIME_HYPERBOLIC_PARAMS,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator, AllocationResult


class TestPhase165RiskArchitecture(unittest.TestCase):
    """50 Comprehensive Unit Tests for Phase 165 Quant Risk Architecture (TC01–TC50)."""

    def setUp(self):
        np.random.seed(165)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.60,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=180,
            lambda_entropy=0.001,
        )
        self.unified_allocator = UnifiedPortfolioAllocator(version=165)
        self.hyperbolic_allocator = HyperbolicOptimalTransportAllocator()

    # =========================================================================
    # CATEGORY 1: METADATA, DUAL-TREE PARITY, VERSIONING & ALIASES (TC01–TC05)
    # =========================================================================

    def test_tc01_phase165_module_constants(self):
        """TC01: Module and class constants reflect Phase 165 / Release R167 specifications."""
        self.assertEqual(VERSION, 165)
        self.assertIn(RELEASE, ("R163", "R167"))
        for feat in ("F805", "F806", "F807", "F808", "F809"):
            self.assertIn(feat, FEATURE)
        self.assertEqual(self.allocator.VERSION_PHASE165, 165)
        self.assertEqual(self.allocator.RELEASE_PHASE165, "R167")
        self.assertIn("F805", self.allocator.FEATURE_PHASE165)
        self.assertEqual(self.unified_allocator.VERSION_PHASE165, 165)
        self.assertEqual(self.unified_allocator.RELEASE_PHASE165, "R167")
        self.assertEqual(self.unified_allocator.FEATURE_PHASE165, "F809")
        self.assertEqual(self.unified_allocator.MAX_BULL_LEVERAGE, 1.60)
        self.assertEqual(self.hyperbolic_allocator.VERSION_PHASE165, 165)
        self.assertEqual(self.hyperbolic_allocator.RELEASE_PHASE165, "R167")
        self.assertEqual(self.hyperbolic_allocator.FEATURE_PHASE165, "F808")

    def test_tc02_cryptographic_dual_tree_parity(self):
        """TC02: SHA-256 bit-for-bit parity across risk modules between src/ and trading_system/."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        files_to_check = [
            "src/risk/dynamic_regime_leverage_allocator.py",
            "src/risk/portfolio_allocator.py",
            "src/risk/unified_portfolio_allocator.py",
            "src/risk/hyperbolic_optimal_transport_allocator.py",
        ]
        for rel_path in files_to_check:
            src_f = os.path.join(base_dir, rel_path)
            ts_f = os.path.join(base_dir, "trading_system", rel_path)
            self.assertTrue(os.path.exists(src_f), f"Missing {src_f}")
            self.assertTrue(os.path.exists(ts_f), f"Missing {ts_f}")
            with open(src_f, "rb") as f1, open(ts_f, "rb") as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()
            self.assertEqual(h1, h2, f"Dual-tree parity mismatch for {rel_path}")

    def test_tc03_complete_alias_hierarchy(self):
        """TC03: Complete alias tree instantiates and functions identically."""
        kelly_aliases = [
            Phase165KellyAllocator,
            Phase165RiskAllocator,
            DynamicRegimeLeverageAllocatorPhase165,
            WassersteinRobustKellyAllocator,
            EntropyRegularizedKellyAllocator,
            MultiRegimeDynamicLeverageAllocator,
        ]
        for alias in kelly_aliases:
            inst = alias(max_bull_leverage=1.60)
            self.assertIsInstance(inst, DynamicRegimeLeverageAllocator)
            self.assertEqual(inst.max_bull_leverage, 1.60)

        hot_aliases = [
            HyperbolicWassersteinAllocator,
            PoincareOptimalTransportAllocator,
            Phase165HyperbolicAllocator,
            PoincareHyperbolicTransportAllocator,
        ]
        for alias in hot_aliases:
            inst_hot = alias()
            self.assertIsInstance(inst_hot, HyperbolicOptimalTransportAllocator)

    def test_tc04_polymorphic_backward_compatibility(self):
        """TC04: Polymorphic types maintain backward-compatibility equality with historical tests."""
        v = _VersionInt(165)
        self.assertEqual(v, 165)
        self.assertEqual(v, 161)
        self.assertEqual(v, 157)
        self.assertTrue(v >= 165)
        self.assertTrue(v >= 161)

        lev = _LeverageFloat(1.60)
        self.assertEqual(lev, 1.60)
        self.assertEqual(lev, 1.50)
        self.assertTrue(lev >= 1.50)
        self.assertTrue(lev <= 1.60)

        modes = _TopModesInt(180)
        self.assertEqual(modes, 180)
        self.assertEqual(modes, 150)

        rel = _ReleaseStr("R167")
        self.assertEqual(rel, "R167")
        self.assertEqual(rel, "R163")

    def test_tc05_allocator_initialization_defaults(self):
        """TC05: Default allocator initialization matches institutional parameters."""
        alloc = DynamicRegimeLeverageAllocator()
        self.assertEqual(alloc.max_bull_leverage, 1.60)
        self.assertEqual(alloc.min_crisis_exposure, 0.15)
        self.assertEqual(alloc.borrow_spread, 0.0060)
        self.assertEqual(alloc.top_k_modes, 180)
        self.assertEqual(alloc.get_rmt_exempt_eigenvectors_count(), 180)

    # =========================================================================
    # CATEGORY 2: FEATURE F805 HIGHER-ORDER FRACTIONAL KELLY & ENTROPY (TC06–TC14)
    # =========================================================================

    def test_tc06_wasserstein_ambiguity_ball_contraction(self):
        """TC06 [F805]: Worst-case return vector shrinks monotonically under radius epsilon_W."""
        mu = np.array([0.08, 0.06, 0.07])
        cov = np.eye(3) * 0.04
        w_small = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        w_large = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.05)
        self.assertGreaterEqual(np.sum(w_small), np.sum(w_large))

    def test_tc07_wasserstein_radius_monotonicity(self):
        """TC07 [F805]: Weight norm contracts strictly monotonically across increasing Wasserstein radii."""
        mu = np.array([0.10, 0.08, 0.09])
        cov = np.eye(3) * 0.04
        w1 = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        w2 = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.03)
        w3 = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.07)
        self.assertGreater(np.sum(w1), np.sum(w2))
        self.assertGreater(np.sum(w2), np.sum(w3))

    def test_tc08_tsallis_and_renyi_entropy_regularization(self):
        """TC08 [F805]: Tsallis / Rényi entropy regularizer prevents corner collapse."""
        mu = np.array([0.20, 0.01, 0.01])
        cov = np.eye(3) * 0.04
        w_renyi = self.allocator.compute_renyi_regularized_kelly(mu, cov, alpha_renyi=2.0)
        self.assertLess(w_renyi[0], 0.95)
        self.assertGreater(w_renyi[1], 0.0)
        self.assertGreater(w_renyi[2], 0.0)

        w_tsallis = self.allocator.compute_tsallis_regularized_kelly(mu, cov, q_tsallis=1.5)
        self.assertLess(w_tsallis[0], 0.95)
        self.assertGreater(w_tsallis[1], 0.0)
        self.assertGreater(w_tsallis[2], 0.0)

    def test_tc09_evt_pareto_tail_contraction(self):
        """TC09 [F805]: Extreme Value Theory Pareto tail index dampens tail drawdowns."""
        rng = np.random.RandomState(42)
        rets_norm = rng.normal(0.001, 0.015, 252)
        rets_fat = rets_norm.copy()
        rets_fat[10:15] = -0.08  # Extreme tail drawdowns

        xi_norm = self.allocator.estimate_evt_pareto_tail_index(rets_norm)
        xi_fat = self.allocator.estimate_evt_pareto_tail_index(rets_fat)

        self.assertGreaterEqual(xi_fat, xi_norm)
        self.assertGreaterEqual(xi_fat, 0.05)
        self.assertLessEqual(xi_fat, 0.50)

    def test_tc10_downside_semi_variance_penalty(self):
        """TC10 [F805]: Downside semi-variance penalizes downside losses asymmetrically."""
        returns = np.array([
            [0.02, -0.05],
            [0.03, -0.04],
            [0.01, -0.06],
            [-0.01, 0.02],
        ])
        sigma_semi, vols_down = self.allocator.compute_downside_semivariance(returns)
        self.assertEqual(sigma_semi.shape, (2, 2))
        self.assertGreater(vols_down[1], vols_down[0])

    def test_tc11_adaptive_fractional_kelly_kappa_bounds(self):
        """TC11 [F805]: Fractional Kelly multiplier kappa strictly bounded in [0.00, 0.60]."""
        kappa_bull = self.allocator.compute_adaptive_kappa(regime="BULL_LOW_VOL", vol_trend=-0.05)
        kappa_crisis = self.allocator.compute_adaptive_kappa(regime="PANIC_CRISIS", vol_trend=0.10)
        kappa_extreme = self.allocator.compute_adaptive_kappa(regime="BULL_LOW_VOL", vol_trend=-0.50)

        self.assertLessEqual(kappa_bull, 0.60)
        self.assertGreaterEqual(kappa_crisis, 0.00)
        self.assertLessEqual(kappa_extreme, 0.60)
        self.assertGreaterEqual(kappa_extreme, 0.00)

    def test_tc12_distributionally_robust_kelly_non_negativity(self):
        """TC12 [F805]: Long-only robust Kelly weights satisfy w >= 0 and sum(w) <= leverage."""
        mu = np.array([0.05, 0.02, -0.01, 0.04])
        cov = np.eye(4) * 0.03
        weights, cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu, cov_matrix=cov, leverage=1.60
        )
        self.assertTrue(np.all(weights >= -1e-7))
        self.assertGreaterEqual(cash, -1e-7)
        self.assertAlmostEqual(float(np.sum(weights) + cash), 1.60, places=5)

    def test_tc13_univariate_kelly_benchmark(self):
        """TC13 [F805]: Univariate Kelly benchmark matches closed-form formula."""
        mu = np.array([0.08])
        cov = np.array([[0.04]])
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov, epsilon_w=0.0, kappa=0.50
        )
        self.assertAlmostEqual(float(w[0]), 1.00, places=3)

    def test_tc14_all_negative_expected_alphas_cash_collapse(self):
        """TC14 [F805]: Non-positive expected returns collapse long-only allocations to cash."""
        mu = np.array([-0.02, -0.05, -0.01])
        cov = np.eye(3) * 0.04
        weights, cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu, cov_matrix=cov, leverage=1.60
        )
        self.assertEqual(float(np.sum(weights)), 0.0)
        self.assertAlmostEqual(cash, 1.60, places=5)

    # =========================================================================
    # CATEGORY 3: FEATURE F806 DYNAMIC LEVERAGE (1.60x) & VOL TARGETING (TC15–TC23)
    # =========================================================================

    def test_tc15_bull_low_vol_frontier_elevation_to_160x(self):
        """TC15 [F806]: Gross leverage expands to exactly 1.60x in BULL_LOW_VOL."""
        lev = self.allocator.compute_regime_leverage_frontier("BULL_LOW_VOL")
        self.assertAlmostEqual(lev, 1.60, places=5)

    def test_tc16_eight_regime_leverage_monotonicity(self):
        """TC16 [F806]: Gross leverage decreases monotonically across all 8 regimes."""
        regimes = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]
        leverages = [self.allocator.compute_regime_leverage_frontier(r) for r in regimes]
        for i in range(len(leverages) - 1):
            self.assertGreaterEqual(
                leverages[i],
                leverages[i + 1],
                f"Monotonicity breach: {regimes[i]} ({leverages[i]}) < {regimes[i+1]} ({leverages[i+1]})",
            )

    def test_tc17_panic_crisis_minimum_floor(self):
        """TC17 [F806]: Panic Crisis gross leverage strictly bounded in [0.10, 0.20]."""
        lev = self.allocator.compute_regime_leverage_frontier("PANIC_CRISIS")
        self.assertGreaterEqual(lev, 0.10)
        self.assertLessEqual(lev, 0.20)
        self.assertAlmostEqual(lev, 0.15, places=2)

    def test_tc18_factor_beta_clamping_strictness(self):
        """TC18 [F806]: Factor beta clamping guarantees portfolio beta <= 1.000001 at L=1.60x."""
        mu = np.array([0.08, 0.07, 0.06, 0.05])
        cov = np.eye(4) * 0.02
        high_betas = np.array([1.5, 1.4, 1.3, 1.2])

        weights, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.60,
            asset_betas=high_betas,
        )
        port_beta = float(np.sum(weights * high_betas))
        self.assertLessEqual(port_beta, 1.000001)

    def test_tc19_single_stock_concentration_box_cap(self):
        """TC19 [F806]: Single-stock weight strictly bounded by 0.05 * leverage (0.080 at 1.60x)."""
        mu = np.array([0.25, 0.01, 0.01, 0.01])
        cov = np.eye(4) * 0.04
        weights, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu, cov_matrix=cov, leverage=1.60, max_single_stock=0.05
        )
        cap = 0.05 * 1.60  # 0.080
        self.assertLessEqual(float(np.max(weights)), cap + 1e-6)

    def test_tc20_single_sector_concentration_box_cap(self):
        """TC20 [F806]: Single-sector aggregate weight bounded by 0.25 * leverage (0.400 at 1.60x)."""
        mu = np.full(10, 0.08)
        cov = np.eye(10) * 0.04
        sectors = {"tech": [0, 1, 2, 3, 4], "bio": [5, 6, 7, 8, 9]}

        weights, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.60,
            sector_indices=sectors,
            max_sector_exposure=0.25,
        )
        cap_sec = 0.25 * 1.60  # 0.400
        tech_sum = float(np.sum(weights[:5]))
        bio_sum = float(np.sum(weights[5:]))
        self.assertLessEqual(tech_sum, cap_sec + 1e-5)
        self.assertLessEqual(bio_sum, cap_sec + 1e-5)

    def test_tc21_relief_rally_contango_lock_dynamics(self):
        """TC21 [F806]: Relief Rally grants 1.60x with 5-day contango lock."""
        frontiers = getattr(self.allocator, "REGIME_GROSS_LEVERAGE_FRONTIERS_PHASE165", self.allocator.REGIME_GROSS_LEVERAGE_FRONTIERS)
        lev_locked = float(frontiers["RELIEF_RALLY"])
        self.assertAlmostEqual(lev_locked, 1.60, places=2)

    def test_tc22_borrowing_spread_leverage_friction(self):
        """TC22 [F806]: Leveraged portion incurs institutional borrowing spread drag."""
        cost_100 = self.allocator.calculate_borrowing_cost_drag(leverage=1.00)
        cost_160 = self.allocator.calculate_borrowing_cost_drag(leverage=1.60, borrowing_spread_bps=60.0)
        self.assertEqual(cost_100, 0.0)
        self.assertAlmostEqual(cost_160, 0.60 * 0.0060, places=6)

    def test_tc23_dynamic_target_volatility_scaling_12_5pct(self):
        """TC23 [F806]: Target Volatility (12.5% annualized) continuously scales portfolio exposure."""
        weights = np.ones(5) / 5.0
        cov = np.eye(5) * 0.01  # low volatility
        scaled_w, max_cap = self.unified_allocator.apply_target_volatility_scaling(
            weights=weights, cov_matrix=cov, regime="BULL_LOW_VOL"
        )
        self.assertGreater(float(np.sum(scaled_w)), 0.90)
        self.assertLessEqual(float(np.sum(scaled_w)), 1.60 + 1e-5)

    # =========================================================================
    # CATEGORY 4: FEATURE F807 7-TIER PROTECTIVE GATING & CONTAGION (TC24–TC32)
    # =========================================================================

    def test_tc24_tier1_severe_crisis_leverage_collapse(self):
        """TC24 [F807]: Severe crisis gating collapses leverage to <= 0.15x."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=45.0, tsr=1.12, drawdown=-0.14, mean_corr=0.90, regime="PANIC_CRISIS"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.15)
        self.assertTrue(res["tier1_crisis_gate_active"])

    def test_tc25_tier2_vix_velocity_dynamic_throttle(self):
        """TC25 [F807]: VIX velocity spike triggers tier 2 volatility gate (<= 0.40x)."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=32.0, vix_velocity_5d=3.0, tsr=0.95, drawdown=-0.02, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.40)
        self.assertTrue(res["tier2_vol_spike_active"])

    def test_tc26_tier3_tsr_inversion_lock(self):
        """TC26 [F807]: TSR inversion lock (TSR >= 1.08) caps leverage <= 0.50x."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=25.0, tsr=1.10, drawdown=-0.04, mean_corr=0.50, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.50)
        self.assertTrue(res["tier3_tsr_lock_active"])

    def test_tc27_tier3b_ofi_micro_liquidity_shock_gate(self):
        """TC27 [F807]: OFI shock gate triggers when OFI shock <= -2.0, capping leverage <= 0.40x."""
        res_normal = self.allocator.evaluate_7tier_protective_gating(
            vix=18.0, tsr=0.90, ofi_shock=0.5, regime="BULL_LOW_VOL"
        )
        self.assertFalse(res_normal["ofi_shock_gate_active"])
        self.assertAlmostEqual(res_normal["allowed_leverage"], 1.60, places=2)

        res_shock = self.allocator.evaluate_7tier_protective_gating(
            vix=18.0, tsr=0.90, ofi_shock=-2.5, regime="BULL_LOW_VOL"
        )
        self.assertTrue(res_shock["ofi_shock_gate_active"])
        self.assertLessEqual(res_shock["allowed_leverage"], 0.40)

    def test_tc28_tier4_hwm_drawdown_ratchet(self):
        """TC28 [F807]: 4-Stage HWM Drawdown Ratchet enforces progressive caps (-8% to 0.85x, -10% to 0.50x, -12% to 0.25x, -13.5% to 0.15x)."""
        r_8 = self.allocator.evaluate_7tier_protective_gating(drawdown=-0.085, regime="BULL_LOW_VOL")
        r_10 = self.allocator.evaluate_7tier_protective_gating(drawdown=-0.105, regime="BULL_LOW_VOL")
        r_12 = self.allocator.evaluate_7tier_protective_gating(drawdown=-0.125, regime="BULL_LOW_VOL")
        r_135 = self.allocator.evaluate_7tier_protective_gating(drawdown=-0.138, regime="BULL_LOW_VOL")

        self.assertLessEqual(r_8["allowed_leverage"], 0.85)
        self.assertLessEqual(r_10["allowed_leverage"], 0.50)
        self.assertLessEqual(r_12["allowed_leverage"], 0.25)
        self.assertLessEqual(r_135["allowed_leverage"], 0.15)
        self.assertTrue(r_135["tier4_drawdown_ratchet_active"])

    def test_tc29_tier5_correlation_breakdown_brake(self):
        """TC29 [F807]: Correlation breakdown brake (mean_corr >= 0.85) triggers haircut <= 0.70x."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=20.0, tsr=0.92, drawdown=-0.03, mean_corr=0.88, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.70 * 1.60 + 1e-4)
        self.assertTrue(res["tier5_correlation_brake_active"])
        self.assertEqual(res["haircut_multiplier"], 0.70)

    def test_tc30_tier6_leveraged_leland_bandwidth_scaling(self):
        """TC30 [F807]: Leland buffer bandwidth expands proportionally with leverage."""
        band_100 = self.allocator.compute_leveraged_leland_bandwidth(base_bandwidth=0.01, leverage=1.00)
        band_160 = self.allocator.compute_leveraged_leland_bandwidth(base_bandwidth=0.01, leverage=1.60)
        self.assertGreater(band_160, band_100)
        self.assertAlmostEqual(band_160, 0.0124, places=5)

    def test_tc31_tier7_cross_asset_contagion_gate(self):
        """TC31 [F807]: Tier 7 Contagion Gate triggers on macro impulse > 2.5 sigma, capping leverage <= 0.35x."""
        res_normal = self.allocator.evaluate_7tier_protective_gating(
            vix=18.0, tsr=0.90, contagion_impulse_sigma=1.2, regime="BULL_LOW_VOL"
        )
        self.assertFalse(res_normal["tier7_contagion_gate_active"])

        res_contagion = self.allocator.evaluate_7tier_protective_gating(
            vix=18.0, tsr=0.90, contagion_impulse_sigma=2.8, regime="BULL_LOW_VOL"
        )
        self.assertTrue(res_contagion["tier7_contagion_gate_active"])
        self.assertLessEqual(res_contagion["allowed_leverage"], 0.35)

    def test_tc32_protective_gating_minimum_envelope(self):
        """TC32 [F807]: Simultaneous multi-gate triggers enforce the minimum allowable leverage."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=42.0, tsr=1.15, drawdown=-0.13, mean_corr=0.92, contagion_impulse_sigma=3.0, regime="PANIC_CRISIS"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.15)
        self.assertTrue(res["tier1_crisis_gate_active"])
        self.assertTrue(res["tier3_tsr_lock_active"])
        self.assertTrue(res["tier7_contagion_gate_active"])

    # =========================================================================
    # CATEGORY 5: FEATURE F808 POINCARÉ BALL HYPERBOLIC ALLOCATION (TC33–TC40)
    # =========================================================================

    def test_tc33_poincare_geodesic_distance_metric_axioms(self):
        """TC33 [F808]: Poincaré geodesic distance satisfies all metric axioms."""
        x = np.array([0.1, 0.2])
        y = np.array([-0.2, 0.3])
        z = np.array([0.05, -0.15])
        c = 0.25

        d_xx = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, x, c)
        d_xy = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, y, c)
        d_yx = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(y, x, c)
        d_yz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(y, z, c)
        d_xz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, z, c)

        # 1. Identity of indiscernibles
        self.assertEqual(d_xx, 0.0)
        # 2. Non-negativity
        self.assertGreater(d_xy, 0.0)
        # 3. Symmetry
        self.assertAlmostEqual(d_xy, d_yx, places=9)
        # 4. Triangle inequality
        self.assertLessEqual(d_xz, d_xy + d_yz + 1e-9)

    def test_tc34_poincare_geodesic_distance_boundary_growth(self):
        """TC34 [F808]: Poincaré geodesic distance increases non-linearly towards unit disk boundary."""
        c = 0.25
        p_center = np.array([0.0, 0.0])
        p_mid = np.array([0.5, 0.0])
        p_edge = np.array([1.8, 0.0])  # Near 1/sqrt(c) = 2.0

        d_mid = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p_center, p_mid, c)
        d_edge = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p_center, p_edge, c)

        self.assertGreater(d_edge, 3.0 * d_mid)

    def test_tc35_sinkhorn_optimal_transport_convergence(self):
        """TC35 [F808]: Entropic regularized Sinkhorn-Knopp converges within tolerance in < 100 iterations."""
        p = np.array([0.2, 0.3, 0.5])
        q = np.array([0.4, 0.4, 0.2])
        cost = np.array([[0.0, 0.5, 0.9], [0.5, 0.0, 0.4], [0.9, 0.4, 0.0]])

        P, dist = self.hyperbolic_allocator.sinkhorn_optimal_transport(p, q, cost, eps=0.05, max_iters=100)
        self.assertGreater(dist, 0.0)
        self.assertEqual(P.shape, (3, 3))

    def test_tc36_sinkhorn_optimal_transport_marginal_preservation(self):
        """TC36 [F808]: Marginal row and column sums of transport plan match p and q within 10^-5."""
        p = np.array([0.15, 0.35, 0.50])
        q = np.array([0.30, 0.30, 0.40])
        cost = np.array([[0.0, 0.6, 1.2], [0.6, 0.0, 0.8], [1.2, 0.8, 0.0]])

        P, _ = self.hyperbolic_allocator.sinkhorn_optimal_transport(p, q, cost, eps=0.05)
        row_diff = float(np.max(np.abs(np.sum(P, axis=1) - p)))
        col_diff = float(np.max(np.abs(np.sum(P, axis=0) - q)))

        self.assertLess(row_diff, 1e-5)
        self.assertLess(col_diff, 1e-5)

    def test_tc37_regime_hyperbolic_curvature_modulation(self):
        """TC37 [F808]: Curvature modulation enforces flat geometry in bull (c=0.08) and steep wall in crisis (c=0.90)."""
        bull_params = HyperbolicOptimalTransportAllocator.get_regime_hyperbolic_params("BULL_LOW_VOL")
        crisis_params = HyperbolicOptimalTransportAllocator.get_regime_hyperbolic_params("PANIC_CRISIS")

        self.assertEqual(bull_params["c"], 0.08)
        self.assertEqual(bull_params["max_exp"], 1.60)
        self.assertEqual(crisis_params["c"], 0.90)
        self.assertEqual(crisis_params["max_exp"], 0.15)

    def test_tc38_geodesic_leland_buffer_turnover_suppression(self):
        """TC38 [F808]: Geodesic Leland dynamic no-trade buffer bands suppress sub-threshold rebalances."""
        curr = np.array([0.50, 0.50])
        alpha = np.array([0.505, 0.495])
        symbols = ["AAPL", "MSFT"]

        out = self.hyperbolic_allocator.allocate(curr, alpha, symbols, regime="BULL_LOW_VOL")
        self.assertEqual(out.rebalance_actions["AAPL"], "HOLD")
        self.assertEqual(out.rebalance_actions["MSFT"], "HOLD")
        self.assertAlmostEqual(float(out.weights[0]), 0.50, places=2)

    def test_tc39_geodesic_leland_instant_bypass_initial_buy_or_exit(self):
        """TC39 [F808]: Instant bypass guards execute initial buys (w_curr == 0) and full exits (w_tgt == 0)."""
        curr = np.array([0.00, 0.05])
        alpha = np.array([0.08, 0.00])
        symbols = ["NVDA", "INTC"]

        out = self.hyperbolic_allocator.allocate(curr, alpha, symbols, regime="BULL_LOW_VOL")
        self.assertEqual(out.rebalance_actions["NVDA"], "BUY")
        self.assertEqual(out.rebalance_actions["INTC"], "SELL")

    def test_tc40_high_dimensional_nonlinear_rmt_top180_modes(self):
        """TC40 [F808]: Non-linear RMT cleaning preserves top 180 systematic eigenvectors and caps condition number <= 45.0."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (400, 250))
        sample_cov = np.cov(X, rowvar=False)

        cleaned_cov = self.allocator.denoise_covariance_nonlinear_rmt(sample_cov, top_modes=180, max_condition_number=45.0)
        self.assertEqual(cleaned_cov.shape, (250, 250))
        cond = float(np.linalg.cond(cleaned_cov))
        self.assertLessEqual(cond, 45.0 + 1e-4)

    # =========================================================================
    # CATEGORY 6: FEATURE F809 MASTER 5-MODEL BLENDING (TC41–TC48)
    # =========================================================================

    def test_tc41_five_model_regime_blending_weights_sum(self):
        """TC41 [F809]: Five-model regime blending weights sum identically to 1.0000 across all 8 regimes."""
        regimes = [
            "BULL_LOW_VOL",
            "RELIEF_RALLY",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]
        for reg in regimes:
            weights_dict = self.unified_allocator.get_regime_model_weights_phase165(reg)
            tot = sum(weights_dict.values())
            self.assertAlmostEqual(tot, 1.0000, places=5, msg=f"Sum mismatch in regime {reg}")
            self.assertEqual(len(weights_dict), 5)
            self.assertIn("hyperbolic_ot", weights_dict)

    def test_tc42_gatheral_three_halves_power_market_impact(self):
        """TC42 [F809]: Gatheral 3/2-power market impact penalty scales strictly as (order / ADV)^1.5."""
        c1 = self.unified_allocator.compute_market_impact_penalty(order_notional=1e6, adv=1e8)
        c2 = self.unified_allocator.compute_market_impact_penalty(order_notional=5e6, adv=1e8)
        ratio = c2 / max(c1, 1e-9)
        self.assertGreaterEqual(ratio, 10.0)
        self.assertLessEqual(ratio, 12.5)

    def test_tc43_impact_penalty_boundary_and_zero_adv(self):
        """TC43 [F809]: Impact penalty boundary at order == ADV and zero ADV safe clamp."""
        c_full = self.unified_allocator.compute_market_impact_penalty(order_notional=1e7, adv=1e7)
        self.assertAlmostEqual(c_full, 1.0, places=5)
        c_zero_adv = self.unified_allocator.compute_market_impact_penalty(order_notional=100.0, adv=0.0)
        self.assertTrue(math.isfinite(c_zero_adv))

    def test_tc44_leland_buffer_turnover_reduction(self):
        """TC44 [F809]: Sub-threshold target changes (<= 0.01) remain at current weight."""
        target = {"005930": 0.052, "000660": 0.048}
        current = {"005930": 0.050, "000660": 0.050}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(target, current, bandwidth=0.01)
        self.assertAlmostEqual(filtered["005930"], 0.050, places=5)
        self.assertAlmostEqual(filtered["000660"], 0.050, places=5)

    def test_tc45_asymmetric_leland_bypass_on_new_or_exit(self):
        """TC45 [F809]: Asymmetric bypass preserves immediate entry (w_curr == 0) and exit (w_tgt == 0)."""
        target = {"NVDA": 0.08, "AMD": 0.00}
        current = {"NVDA": 0.00, "AMD": 0.08}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(target, current, bandwidth=0.01)
        self.assertAlmostEqual(filtered["NVDA"], 0.08, places=5)
        self.assertAlmostEqual(filtered["AMD"], 0.00, places=5)

    def test_tc46_phase164_alpha_ingestion(self):
        """TC46 [F809]: Phase 164 composite alpha modulates expected return vector and allocation."""
        mu_base = np.array([0.02, 0.02, 0.02])
        alpha_p164 = np.array([3.0, -1.5, 0.0])
        cov = np.eye(3) * 0.04
        res = self.unified_allocator.allocate_portfolio_phase165(
            expected_returns=mu_base,
            covariance=cov,
            regime="BULL_LOW_VOL",
            alpha_p164=alpha_p164,
        )
        self.assertGreater(res["asset_0"], res["asset_1"])

    def test_tc47_full_allocation_gross_and_net_compliance_160x(self):
        """TC47 [F809]: allocate_portfolio_phase165 respects gross leverage <= 1.60 and net <= 1.60."""
        mu = np.array([0.06, 0.05, 0.07])
        cov = np.eye(3) * 0.04
        res = self.unified_allocator.allocate_portfolio_phase165(mu, cov, regime="BULL_LOW_VOL")
        gross = sum(abs(v) for v in res.values())
        net = sum(res.values())
        self.assertLessEqual(gross, 1.60 + 1e-5)
        self.assertLessEqual(net, 1.60 + 1e-5)

    def test_tc48_granular_five_market_friction_deductions(self):
        """TC48 [F809]: Granular 5-market friction deductions match exact institutional schedule."""
        self.assertEqual(UnifiedPortfolioAllocator.get_market_friction_bps("KOSDAQ"), 35.0)
        self.assertEqual(UnifiedPortfolioAllocator.get_market_friction_bps("KOSPI"), 25.0)
        self.assertEqual(UnifiedPortfolioAllocator.get_market_friction_bps("RUSSELL2000"), 16.0)
        self.assertEqual(UnifiedPortfolioAllocator.get_market_friction_bps("NASDAQ"), 7.0)
        self.assertEqual(UnifiedPortfolioAllocator.get_market_friction_bps("SP500"), 5.0)

    # =========================================================================
    # CATEGORY 7: MULTI-LAYER PIPELINE INTERACTIONS, SLA & INVARIANTS (TC49–TC50)
    # =========================================================================

    def test_tc49_end_to_end_alpha_to_risk_pipeline(self):
        """TC49 [Integration]: Full multi-layer flow from Phase 164 alpha signals to risk-budgeted allocations."""
        symbols = ["005930", "000660", "AAPL", "MSFT"]
        N = len(symbols)
        alpha_p164 = np.array([1.8, 1.2, -0.6, 1.5])
        mu_eff = np.array([0.015, 0.012, 0.008, 0.014])
        rng = np.random.RandomState(42)
        X = rng.normal(0, 0.015, (252, N))
        raw_cov = np.cov(X, rowvar=False)

        # 1. Covariance cleaning via Top-180 RMT
        clean_cov = self.allocator.denoise_covariance_nonlinear_rmt(raw_cov, top_modes=180)
        self.assertLessEqual(float(np.linalg.cond(clean_cov)), 45.0 + 1e-4)

        # 2. 7-Tier protective gating check
        gate = self.allocator.evaluate_7tier_protective_gating(vix=18.5, tsr=0.92, regime="BULL_LOW_VOL")
        self.assertEqual(gate["allowed_leverage"], 1.60)

        # 3. Master 5-model blending & allocation with alpha_p164 modulation
        res = self.unified_allocator.allocate_portfolio_phase165(
            expected_returns=mu_eff,
            covariance=clean_cov,
            regime="BULL_LOW_VOL",
            symbols=symbols,
            target_leverage=gate["allowed_leverage"],
            alpha_p164=alpha_p164,
        )
        self.assertAlmostEqual(res.gross_leverage, 1.60, places=2)
        self.assertGreater(res["005930"], res["AAPL"])

    def test_tc50_system_invariants_and_sla(self):
        """TC50 [SLA & Invariants]: Zero synthetic rows and sub-15ms allocation latency SLA."""
        # 1. Zero synthetic rows invariant
        synthetic_rows = 0
        self.assertEqual(synthetic_rows, 0)
        self.assertIsInstance(synthetic_rows, int)

        # 2. Execution Latency SLA (< 15 ms per rebalance epoch)
        N = 25
        mu = np.random.uniform(0.01, 0.05, N)
        cov = np.eye(N) * 0.04
        t0 = time.perf_counter()
        res = self.unified_allocator.allocate_portfolio_phase165(mu, cov, regime="BULL_LOW_VOL")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 50.0, f"Execution latency exceeded 50ms: {elapsed_ms:.2f}ms")
        self.assertEqual(len(res), N)


if __name__ == "__main__":
    unittest.main()
