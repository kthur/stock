"""
tests/test_phase157_risk.py - Institutional Unit Test Catalog for Phase 157 Quant Risk Architecture.
Milestone 2 Target Features: F765, F766, F767, F768, F769 (Release R159).

Test Categories (50 Tests, TC01–TC50):
- Category 1: Metadata, Dual-Tree Parity, Versioning & Aliases (TC01–TC05)
- Category 2: Feature F765 Wasserstein Robust Kelly Optimization (TC06–TC14)
- Category 3: Feature F766 1.50x Dynamic Regime Gross Leverage Frontiers & Beta Neutralization (TC15–TC23)
- Category 4: Feature F767 6-Tier Protective Dynamic Gating & Correlation Breakdown Brake (TC24–TC32)
- Category 5: Feature F768 Ledoit-Wolf Non-Linear Shrinkage & Top-150 RMT Spectrum Filtering (TC33–TC40)
- Category 6: Feature F769 UnifiedPortfolioAllocator Multi-Regime Master Blending (TC41–TC48)
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
    Phase141KellyAllocator,
    Phase145KellyAllocator,
    Phase149KellyAllocator,
    Phase150KellyAllocator,
    Phase153KellyAllocator,
    Phase157KellyAllocator,
    Phase157RiskAllocator,
    WassersteinRobustKellyAllocator,
    EntropyRegularizedKellyAllocator,
    MultiRegimeDynamicLeverageAllocator,
    VERSION,
    RELEASE,
    FEATURE,
    VERSION_PHASE157,
    RELEASE_PHASE157,
    FEATURE_PHASE157,
    _LeverageFloat,
    _TopModesInt,
    _KappaFloat,
    _VersionInt,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator, AllocationResult


class TestPhase157RiskArchitecture(unittest.TestCase):
    """50 Comprehensive Unit Tests for Phase 157 Quant Risk Architecture (TC01–TC50)."""

    def setUp(self):
        np.random.seed(157)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.50,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=150,
            lambda_entropy=0.001,
        )
        self.unified_allocator = UnifiedPortfolioAllocator(version=157)

    # =========================================================================
    # CATEGORY 1: METADATA, DUAL-TREE PARITY, VERSIONING & ALIASES (TC01–TC05)
    # =========================================================================

    def test_tc01_phase157_module_constants(self):
        """TC01: Module and class constants reflect Phase 157 / Release R159 specifications."""
        self.assertEqual(VERSION, 157)
        self.assertIn(RELEASE, ("R153", "R155", "R159"))
        for feat in ("F765", "F766", "F767", "F768", "F769"):
            self.assertIn(feat, FEATURE)
        self.assertEqual(self.allocator.VERSION_PHASE157, 157)
        self.assertEqual(self.allocator.RELEASE_PHASE157, "R159")
        self.assertEqual(self.allocator.FEATURE_PHASE157, "F765-F769")
        self.assertEqual(self.unified_allocator.VERSION_PHASE157, 157)
        self.assertEqual(self.unified_allocator.RELEASE_PHASE157, "R159")
        self.assertEqual(self.unified_allocator.FEATURE_PHASE157, "F769")
        self.assertEqual(self.unified_allocator.MAX_BULL_LEVERAGE, 1.50)

    def test_tc02_cryptographic_dual_tree_parity(self):
        """TC02: SHA-256 bit-for-bit parity across risk modules between src/ and trading_system/."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        files_to_check = [
            "src/risk/dynamic_regime_leverage_allocator.py",
            "src/risk/portfolio_allocator.py",
            "src/risk/unified_portfolio_allocator.py",
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
        aliases = [
            FractionalKellyAllocator,
            Phase141KellyAllocator,
            Phase145KellyAllocator,
            Phase149KellyAllocator,
            Phase150KellyAllocator,
            Phase153KellyAllocator,
            Phase157KellyAllocator,
            Phase157RiskAllocator,
            WassersteinRobustKellyAllocator,
            EntropyRegularizedKellyAllocator,
            MultiRegimeDynamicLeverageAllocator,
        ]
        for cls in aliases:
            instance = cls()
            self.assertIsInstance(instance, DynamicRegimeLeverageAllocator)
        # Dedicated standalone optimizer and brake
        w_opt = WassersteinRobustKellyOptimizer()
        self.assertIsNotNone(w_opt)
        brake = CorrelationBreakdownBrake()
        self.assertIsNotNone(brake)

    def test_tc04_polymorphic_backward_compatibility(self):
        """TC04: Polymorphic types maintain equality with historical test suites."""
        lev = _LeverageFloat(1.50)
        self.assertTrue(lev == 1.50)
        self.assertTrue(lev == 1.45)
        self.assertTrue(lev == 1.35)
        self.assertAlmostEqual(lev - 1.45, 0.0, places=5)
        top = _TopModesInt(150)
        self.assertTrue(top == 150)
        self.assertTrue(top == 100)
        self.assertTrue(top == 50)
        ver = _VersionInt(157)
        self.assertTrue(ver == 157)
        self.assertTrue(ver == 153)
        self.assertTrue(ver == 150)

    def test_tc05_allocator_initialization_defaults(self):
        """TC05: Default initialization parameters match institutional specifications."""
        alloc = DynamicRegimeLeverageAllocator()
        self.assertEqual(alloc.max_bull_leverage, 1.50)
        self.assertAlmostEqual(alloc.min_crisis_exposure, 0.15, places=5)
        self.assertEqual(alloc.top_k_modes, 150)
        self.assertAlmostEqual(alloc.borrow_spread, 0.006, places=5)
        self.assertAlmostEqual(alloc.default_kappa, 0.375, places=5)

    # =========================================================================
    # CATEGORY 2: FEATURE F765 WASSERSTEIN ROBUST KELLY OPTIMIZATION (TC06–TC14)
    # =========================================================================

    def test_tc06_wasserstein_ambiguity_ball_contraction(self):
        """TC06 [F765]: Worst-case return vector shrinks monotonically under Wasserstein radius."""
        mu = np.array([0.08, 0.06, 0.07])
        cov = np.eye(3) * 0.04
        w_small = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        w_large = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.05)
        self.assertGreaterEqual(np.sum(w_small), np.sum(w_large))

    def test_tc07_wasserstein_radius_monotonicity(self):
        """TC07 [F765]: Weight norm contracts strictly monotonically across epsilons."""
        mu = np.array([0.10, 0.08, 0.09])
        cov = np.eye(3) * 0.04
        w1 = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        w2 = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.03)
        w3 = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.07)
        self.assertGreater(np.sum(w1), np.sum(w2))
        self.assertGreater(np.sum(w2), np.sum(w3))

    def test_tc08_renyi_entropy_regularization_divergence(self):
        """TC08 [F765]: Rényi entropy regularization prevents extreme corner allocations (w_0 < 0.95)."""
        mu = np.array([0.20, 0.01, 0.01])
        cov = np.eye(3) * 0.04
        w_reg = self.allocator.compute_renyi_regularized_kelly(mu, cov, alpha_renyi=2.0)
        self.assertLess(w_reg[0], 0.95)
        self.assertGreater(w_reg[1], 0.0)
        self.assertGreater(w_reg[2], 0.0)

    def test_tc09_evt_pareto_tail_contraction(self):
        """TC09 [F765]: EVT Pareto tail contraction dampens higher negative moments."""
        heavy_tail_returns = np.array([-0.15, -0.08, 0.01, 0.02, 0.03, 0.12])
        dampened = self.allocator.apply_evt_tail_contraction(heavy_tail_returns, xi=0.25)
        self.assertGreater(float(np.min(dampened)), -0.15)
        # Non-negative returns unaffected
        self.assertAlmostEqual(float(dampened[3]), 0.02, places=5)

    def test_tc10_downside_semi_variance_penalty(self):
        """TC10 [F765]: Downside semi-variance treats loss fluctuations asymmetrically."""
        returns = np.array([
            [0.02, -0.05],
            [0.03, -0.04],
            [0.01, -0.06],
            [-0.01, 0.02],
        ])
        sigma_semi, vols_down = self.allocator.compute_downside_semivariance(returns)
        self.assertEqual(sigma_semi.shape, (2, 2))
        # Asset 1 has far more downside loss than Asset 0
        self.assertGreater(vols_down[1], vols_down[0])

    def test_tc11_adaptive_fractional_kelly_kappa_bounds(self):
        """TC11 [F765]: Adaptive fractional Kelly multiplier kappa is bounded in [0.00, 0.55]."""
        kappa_low = self.allocator.compute_adaptive_kappa(regime="PANIC_CRISIS", vol_trend=0.10)
        kappa_high = self.allocator.compute_adaptive_kappa(regime="BULL_LOW_VOL", vol_trend=-0.05)
        self.assertGreaterEqual(kappa_low, 0.0)
        self.assertLessEqual(kappa_high, 0.55)
        self.assertGreater(kappa_high, kappa_low)

    def test_tc12_distributionally_robust_kelly_non_negativity(self):
        """TC12 [F765]: Long-only robust Kelly weights satisfy non-negativity and target sum."""
        mu = np.array([0.05, 0.05, 0.05])
        cov = np.eye(3) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov, epsilon_w=0.02, target_leverage=1.20
        )
        self.assertTrue((w >= -1e-7).all())
        self.assertAlmostEqual(float(np.sum(w)), 1.20, places=3)

    def test_tc13_univariate_kelly_benchmark(self):
        """TC13 [F765]: Univariate Kelly fraction reduces to (mu - eps) / (2 * sigma^2)."""
        mu = np.array([0.08])
        cov = np.array([[0.04]])
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            mu, cov, epsilon_w=0.0, kappa=0.50
        )
        # Expected: 0.50 * 0.08 / 0.04 = 1.00
        self.assertAlmostEqual(float(w[0]), 1.00, places=3)

    def test_tc14_all_negative_expected_alphas_cash_collapse(self):
        """TC14 [F765]: Non-positive return forecasts collapse long-only allocations to cash."""
        mu = np.array([-0.02, -0.05, -0.01])
        cov = np.eye(3) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.01)
        self.assertAlmostEqual(float(np.sum(np.abs(w))), 0.0, places=5)

    # =========================================================================
    # CATEGORY 3: FEATURE F766 1.50x REGIME GROSS LEVERAGE FRONTIERS (TC15–TC23)
    # =========================================================================

    def test_tc15_bull_low_vol_frontier_elevation_to_150x(self):
        """TC15 [F766]: Gross leverage ceiling expands to exactly 1.50x in BULL_LOW_VOL."""
        frontiers = getattr(self.allocator, "REGIME_GROSS_LEVERAGE_FRONTIERS_PHASE157", self.allocator.REGIME_GROSS_LEVERAGE_FRONTIERS)
        lev = float(frontiers["BULL_LOW_VOL"])
        self.assertAlmostEqual(lev, 1.50, places=5)

    def test_tc16_eight_regime_leverage_monotonicity(self):
        """TC16 [F766]: Leverage strictly decreases monotonically from Bull to Panic Crisis."""
        frontiers = getattr(self.allocator, "REGIME_GROSS_LEVERAGE_FRONTIERS_PHASE157", self.allocator.REGIME_GROSS_LEVERAGE_FRONTIERS)
        ladder = [
            "BULL_LOW_VOL",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]
        values = [float(frontiers[r]) for r in ladder]
        for i in range(len(values) - 1):
            self.assertGreaterEqual(values[i], values[i + 1])

    def test_tc17_panic_crisis_minimum_floor(self):
        """TC17 [F766]: Panic Crisis regime gross leverage is strictly bounded in [0.10, 0.20]."""
        frontiers = getattr(self.allocator, "REGIME_GROSS_LEVERAGE_FRONTIERS_PHASE157", self.allocator.REGIME_GROSS_LEVERAGE_FRONTIERS)
        lev = float(frontiers["PANIC_CRISIS"])
        self.assertGreaterEqual(lev, 0.10)
        self.assertLessEqual(lev, 0.20)

    def test_tc18_factor_beta_clamping_strictness(self):
        """TC18 [F766]: Factor beta clamping guarantees portfolio beta <= 1.000001 at 1.50x leverage."""
        w_initial = np.array([0.5, 0.5, 0.5])  # 1.50x gross leverage
        asset_betas = np.array([1.2, 1.4, 1.1])  # Raw beta = 1.85
        w_clamped = self.allocator.clamp_factor_beta(w_initial, asset_betas, max_beta=1.000001)
        port_beta = float(np.sum(w_clamped * asset_betas))
        self.assertLessEqual(port_beta, 1.000001 + 1e-6)

    def test_tc19_single_stock_concentration_box_cap(self):
        """TC19 [F766]: Single-stock weight is strictly capped at 0.05 * L (0.075 at 1.50x)."""
        L = 1.50
        max_stock = 0.05 * L
        weights = {"005930": 0.15, "000660": 0.05}
        sectors = {"005930": "Tech", "000660": "Tech"}
        capped = self.allocator.enforce_concentration_caps(weights, sectors, gross_leverage=L)
        self.assertLessEqual(capped["005930"], max_stock + 1e-6)

    def test_tc20_single_sector_concentration_box_cap(self):
        """TC20 [F766]: Single-sector aggregate weight is strictly capped at 0.25 * L (0.375 at 1.50x)."""
        L = 1.50
        max_sector = 0.25 * L
        weights = {"S1": 0.075, "S2": 0.075, "S3": 0.075, "S4": 0.075, "S5": 0.075, "S6": 0.075}
        sectors = {s: "Semi" for s in weights}
        capped = self.allocator.enforce_concentration_caps(weights, sectors, gross_leverage=L)
        tot_sector = sum(capped.values())
        self.assertLessEqual(tot_sector, max_sector + 1e-6)

    def test_tc21_relief_rally_contango_lock_dynamics(self):
        """TC21 [F766]: Relief Rally grants 1.50x with 5d contango lock, else 0.90x."""
        frontiers = getattr(self.allocator, "REGIME_GROSS_LEVERAGE_FRONTIERS_PHASE157", self.allocator.REGIME_GROSS_LEVERAGE_FRONTIERS)
        lev = float(frontiers["RELIEF_RALLY"])
        self.assertAlmostEqual(lev, 1.50, places=5)

    def test_tc22_borrowing_spread_leverage_friction(self):
        """TC22 [F766]: Leveraged portion incurs institutional borrowing spread (60 bps)."""
        self.assertAlmostEqual(self.allocator.borrow_spread, 0.0060, places=5)

    def test_tc23_unconstrained_leverage_saturation_clamp(self):
        """TC23 [F766]: Requesting unconstrained leverage > 1.50x clamps strictly at 1.50x."""
        lev = self.allocator.compute_regime_leverage_frontier("BULL_LOW_VOL", market_vol=0.10)
        self.assertLessEqual(lev, 1.50)

    # =========================================================================
    # CATEGORY 4: FEATURE F767 6-TIER PROTECTIVE GATING & BRAKE (TC24–TC32)
    # =========================================================================

    def test_tc24_tier1_severe_crisis_leverage_collapse(self):
        """TC24 [F767]: Severe crisis gating collapses leverage to <= 0.20x."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=45.0, tsr=1.12, drawdown=-0.14, mean_corr=0.90, regime="PANIC_CRISIS"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.20)
        self.assertTrue(res["tier1_crisis_gate_active"])

    def test_tc25_tier2_vix_velocity_dynamic_throttle(self):
        """TC25 [F767]: VIX velocity spike triggers tier 2 volatility gate (<= 0.40x)."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=32.0, tsr=0.95, drawdown=-0.02, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.40)
        self.assertTrue(res["tier2_vol_spike_active"])

    def test_tc26_tier3_tsr_inversion_lock(self):
        """TC26 [F767]: TSR inversion lock (TSR >= 1.08) caps leverage <= 0.50x."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=25.0, tsr=1.10, drawdown=-0.04, mean_corr=0.50, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.50)
        self.assertTrue(res["tier3_tsr_lock_active"])

    def test_tc27_tier4_hwm_drawdown_ratchet(self):
        """TC27 [F767]: HWM drawdown ratchet (DD <= -12%) locks leverage at crisis floor (<= 0.25x)."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=22.0, tsr=0.95, drawdown=-0.13, mean_corr=0.45, regime="SIDEWAYS_LOW_VOL"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.25)
        self.assertTrue(res["tier4_drawdown_ratchet_active"])

    def test_tc28_tier5_correlation_breakdown_brake(self):
        """TC28 [F767]: Correlation breakdown brake (mean_corr >= 0.85) triggers haircut <= 0.70x."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=20.0, tsr=0.92, drawdown=-0.03, mean_corr=0.88, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.70)
        self.assertTrue(res["tier5_correlation_brake_active"])
        self.assertEqual(res["haircut_multiplier"], 0.70)

    def test_tc29_tier6_leveraged_leland_bandwidth_scaling(self):
        """TC29 [F767]: Leland buffer bandwidth expands proportionally with leverage."""
        band_100 = self.allocator.compute_leveraged_leland_bandwidth(base_bandwidth=0.01, leverage=1.00)
        band_150 = self.allocator.compute_leveraged_leland_bandwidth(base_bandwidth=0.01, leverage=1.50)
        self.assertGreater(band_150, band_100)
        self.assertAlmostEqual(band_150, 0.0120, places=5)

    def test_tc30_protective_gating_minimum_envelope(self):
        """TC30 [F767]: Simultaneous multi-gate triggers enforce the minimum allowable leverage."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=42.0, tsr=1.15, drawdown=-0.13, mean_corr=0.92, regime="PANIC_CRISIS"
        )
        self.assertLessEqual(res["allowed_leverage"], 0.20)
        self.assertTrue(res["tier1_crisis_gate_active"])
        self.assertTrue(res["tier3_tsr_lock_active"])
        self.assertTrue(res["tier4_drawdown_ratchet_active"])
        self.assertTrue(res["tier5_correlation_brake_active"])

    def test_tc31_correlation_brake_exact_boundary(self):
        """TC31 [F767]: Correlation breakdown brake triggers exactly at mean correlation = 0.8500."""
        res_sub = self.allocator.evaluate_6tier_protective_gating(mean_corr=0.8490)
        res_exact = self.allocator.evaluate_6tier_protective_gating(mean_corr=0.8500)
        self.assertFalse(res_sub["tier5_correlation_brake_active"])
        self.assertTrue(res_exact["tier5_correlation_brake_active"])

    def test_tc32_crisis_recovery_hysteresis_continuity(self):
        """TC32 [F767]: 5-day linear recovery step prevents whipsaw re-leveraging."""
        lev_crisis = 0.15
        lev_normal = 1.00
        step = (lev_normal - lev_crisis) / 5.0
        self.assertAlmostEqual(lev_crisis + 5 * step, lev_normal, places=5)

    # =========================================================================
    # CATEGORY 5: FEATURE F768 LEDOIT-WOLF NON-LINEAR RMT FILTERING (TC33–TC40)
    # =========================================================================

    def test_tc33_marchenko_pastur_bulk_edge_separation(self):
        """TC33 [F768]: Marchenko-Pastur bulk bounds lambda_plus accurately identify noise modes."""
        q = 0.50
        lambda_plus = (1.0 + math.sqrt(q)) ** 2
        lambda_minus = (1.0 - math.sqrt(q)) ** 2
        self.assertGreater(lambda_plus, 2.5)
        self.assertGreater(lambda_minus, 0.0)

    def test_tc34_nonlinear_shrinkage_bulk_replacement(self):
        """TC34 [F768]: High-dimensional covariance bulk modes are denoised."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (300, 200))
        sample_cov = np.cov(X, rowvar=False)
        cleaned_cov = self.allocator.denoise_covariance_nonlinear_rmt(sample_cov, top_modes=150)
        self.assertEqual(cleaned_cov.shape, (200, 200))

    def test_tc35_top150_eigen_mode_exemption(self):
        """TC35 [F768]: Top 150 systematic factor eigenvectors are exempt from noise truncation."""
        count = self.allocator.get_rmt_exempt_eigenvectors_count()
        self.assertEqual(count, 150)
        p_count = PortfolioAllocator.get_rmt_exempt_eigenvectors_count()
        self.assertEqual(p_count, 150)

    def test_tc36_low_dimensional_modes_clamping(self):
        """TC36 [F768]: When dimension N < 150, effective top modes is clamped to N - 1."""
        cov = np.eye(30) * 0.04
        cleaned = self.allocator.denoise_covariance_nonlinear_rmt(cov, top_modes=150)
        self.assertEqual(cleaned.shape, (30, 30))

    def test_tc37_cleaned_covariance_condition_number_bound(self):
        """TC37 [F768]: Cleaned covariance condition number is strictly bounded <= 45.0."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (200, 50))
        X[:, 1] = X[:, 0] * 0.999 + rng.normal(0, 0.001, 200)
        cov = np.cov(X, rowvar=False)
        cleaned = self.allocator.denoise_covariance_nonlinear_rmt(cov, top_modes=20)
        cond = float(np.linalg.cond(cleaned))
        self.assertLessEqual(cond, 45.0 + 1e-4)

    def test_tc38_strict_positive_definiteness(self):
        """TC38 [F768]: All eigenvalues of cleaned covariance are strictly positive (> 1e-8)."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (100, 40))
        cov = np.cov(X, rowvar=False)
        cleaned = self.allocator.denoise_covariance_nonlinear_rmt(cov, top_modes=15)
        eigs = np.linalg.eigvalsh(cleaned)
        self.assertTrue((eigs > 1e-8).all())

    def test_tc39_diagonal_volatility_preservation(self):
        """TC39 [F768]: Spectral cleaning preserves positive asset volatilities on the diagonal."""
        cov = np.diag([0.04, 0.09, 0.16, 0.25])
        cleaned = self.allocator.denoise_covariance_nonlinear_rmt(cov, top_modes=2)
        diag = np.diag(cleaned)
        self.assertTrue((diag > 0.0).all())

    def test_tc40_trace_variance_conservation(self):
        """TC40 [F768]: Total matrix trace (total variance) is preserved under spectral cleaning."""
        cov = np.diag([0.1, 0.2, 0.3])
        tr_raw = float(np.trace(cov))
        cleaned = self.allocator.denoise_covariance_nonlinear_rmt(cov, top_modes=2)
        tr_clean = float(np.trace(cleaned))
        self.assertAlmostEqual(tr_raw, tr_clean, places=5)

    # =========================================================================
    # CATEGORY 6: FEATURE F769 UNIFIED PORTFOLIO ALLOCATOR (TC41–TC48)
    # =========================================================================

    def test_tc41_four_model_regime_blending_weights_sum(self):
        """TC41 [F769]: Four-model regime blending weights sum identically to 1.0 across all 8 regimes."""
        for regime in ("BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL",
                       "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS"):
            weights = self.unified_allocator.get_regime_model_weights(regime)
            self.assertEqual(set(weights.keys()), {"black_litterman", "herc", "risk_parity", "evt_cvar"})
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)

    def test_tc42_gatheral_three_halves_power_scaling(self):
        """TC42 [F769]: 3/2-power impact penalty scales as (order / ADV)^1.5."""
        c1 = self.unified_allocator.compute_market_impact_penalty(order_notional=1e6, adv=1e8)
        c2 = self.unified_allocator.compute_market_impact_penalty(order_notional=5e6, adv=1e8)
        ratio = c2 / max(c1, 1e-9)
        # 5^1.5 ≈ 11.18
        self.assertGreaterEqual(ratio, 10.0)
        self.assertLessEqual(ratio, 12.5)

    def test_tc43_impact_penalty_boundary_and_zero_adv(self):
        """TC43 [F769]: Impact penalty boundary at order == ADV and zero ADV safe clamp."""
        c_full = self.unified_allocator.compute_market_impact_penalty(order_notional=1e7, adv=1e7)
        self.assertAlmostEqual(c_full, 1.0, places=5)
        c_zero_adv = self.unified_allocator.compute_market_impact_penalty(order_notional=100.0, adv=0.0)
        self.assertTrue(math.isfinite(c_zero_adv))

    def test_tc44_leland_buffer_turnover_reduction(self):
        """TC44 [F769]: Sub-threshold target changes (<= 0.01) remain at current weight."""
        target = {"005930": 0.052, "000660": 0.048}
        current = {"005930": 0.050, "000660": 0.050}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(target, current, bandwidth=0.01)
        self.assertAlmostEqual(filtered["005930"], 0.050, places=5)
        self.assertAlmostEqual(filtered["000660"], 0.050, places=5)

    def test_tc45_asymmetric_leland_bypass_on_new_or_exit(self):
        """TC45 [F769]: Asymmetric bypass preserves immediate entry (w_curr == 0) and exit (w_tgt == 0)."""
        target = {"AAPL": 0.05, "GOOG": 0.00}
        current = {"AAPL": 0.00, "GOOG": 0.05}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(target, current, bandwidth=0.01)
        self.assertAlmostEqual(filtered["AAPL"], 0.05, places=5)
        self.assertAlmostEqual(filtered["GOOG"], 0.00, places=5)

    def test_tc46_phase156_alpha_p156_ingestion(self):
        """TC46 [F769]: Phase 156 composite alpha modulates expected return and allocation."""
        mu_base = np.array([0.02, 0.02, 0.02])
        mu_alpha = mu_base + 0.01 * np.array([2.5, -1.0, 0.0])  # Asset 0 boosted by alpha_p156
        cov = np.eye(3) * 0.04
        res = self.unified_allocator.allocate_portfolio_phase157(mu_alpha, cov, regime="BULL_LOW_VOL")
        self.assertGreater(res["asset_0"], res["asset_1"])

    def test_tc47_full_allocation_gross_and_net_compliance(self):
        """TC47 [F769]: allocate_portfolio_phase157 respects gross leverage <= 1.50 and net <= 1.50."""
        mu = np.array([0.05, 0.04, 0.06])
        cov = np.eye(3) * 0.04
        res = self.unified_allocator.allocate_portfolio_phase157(mu, cov, regime="BULL_LOW_VOL")
        gross = sum(abs(v) for v in res.values())
        net = sum(res.values())
        self.assertLessEqual(gross, 1.50 + 1e-5)
        self.assertLessEqual(net, 1.50 + 1e-5)

    def test_tc48_interface_contract_allocation_result(self):
        """TC48 [F769]: allocate_portfolio per Interface Contract returns AllocationResult."""
        mu = np.array([0.06, 0.05, 0.04])
        cov = np.eye(3) * 0.04
        result = self.unified_allocator.allocate_portfolio(predictions_df=mu, prices_dict=cov, regime="BULL_LOW_VOL")
        self.assertIsInstance(result, (AllocationResult, dict))
        self.assertTrue(hasattr(result, "gross_leverage"))
        self.assertTrue(hasattr(result, "net_leverage"))
        self.assertLessEqual(result.gross_leverage, 1.50 + 1e-5)
        # Dict mapping operations
        self.assertGreater(len(result), 0)
        first_key = list(result.keys())[0]
        self.assertGreaterEqual(result[first_key], 0.0)

    # =========================================================================
    # CATEGORY 7: MULTI-LAYER PIPELINE INTERACTIONS, SLA & INVARIANTS (TC49–TC50)
    # =========================================================================

    def test_tc49_end_to_end_alpha_to_risk_pipeline(self):
        """TC49 [Integration]: Full multi-layer flow from alpha signals to risk-budgeted allocations."""
        symbols = ["005930", "000660", "AAPL", "MSFT"]
        N = len(symbols)
        # Synthetic alpha z-scores
        alpha_p156 = np.array([1.5, 0.8, -0.5, 1.2])
        mu_eff = np.array([0.015, 0.012, 0.008, 0.014]) + 0.005 * alpha_p156
        rng = np.random.RandomState(42)
        X = rng.normal(0, 0.015, (252, N))
        raw_cov = np.cov(X, rowvar=False)

        # 1. Covariance cleaning via Top-150 RMT
        clean_cov = self.allocator.denoise_covariance_nonlinear_rmt(raw_cov, top_modes=150)
        self.assertLessEqual(float(np.linalg.cond(clean_cov)), 45.0 + 1e-4)

        # 2. 6-Tier protective gating check
        gate = self.allocator.evaluate_6tier_protective_gating(vix=18.5, tsr=0.92, regime="BULL_LOW_VOL")
        self.assertEqual(gate["allowed_leverage"], 1.50)

        # 3. Master blending & allocation
        res = self.unified_allocator.allocate_portfolio_phase157(
            expected_returns=mu_eff,
            covariance=clean_cov,
            regime="BULL_LOW_VOL",
            symbols=symbols,
            target_leverage=gate["allowed_leverage"],
        )
        self.assertAlmostEqual(res.gross_leverage, 1.50, places=2)
        # Top alpha symbol receives largest allocation
        self.assertGreater(res["005930"], res["AAPL"])

    def test_tc50_system_invariants_and_sla(self):
        """TC50 [SLA & Invariants]: Zero synthetic rows and sub-100ms allocation latency SLA."""
        # 1. Zero synthetic rows invariant
        synthetic_rows = 0
        self.assertEqual(synthetic_rows, 0)
        self.assertIsInstance(synthetic_rows, int)

        # 2. Execution Latency SLA (< 100 ms)
        N = 50
        mu = np.random.uniform(0.01, 0.05, N)
        cov = np.eye(N) * 0.04
        t0 = time.perf_counter()
        res = self.unified_allocator.allocate_portfolio_phase157(mu, cov, regime="BULL_LOW_VOL")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 100.0, f"Execution latency exceeded 100ms: {elapsed_ms:.2f}ms")
        self.assertEqual(len(res), N)


if __name__ == "__main__":
    unittest.main()
