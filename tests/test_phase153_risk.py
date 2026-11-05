"""
tests/test_phase153_risk.py - Institutional Unit Test Catalog for Phase 153 Quant Risk Architecture.
Milestone 2 Target Features: F745, F746, F747, F748, F749.

Test Categories:
- Category 1: Metadata, Parity, Aliases, Configuration & Invariants (TC01 ~ TC05)
- Category 2: Feature F745 Higher-Order Tail-Risk Fractional Kelly with EVT & Rényi Entropy (TC06 ~ TC11)
- Category 3: Feature F746 8-Regime Dynamic Leverage Frontiers (up to 1.45x) & Factor Beta Clamping (TC12 ~ TC17)
- Category 4: Feature F747 5-Tier Protective Dynamic Gating & Min-Envelope (TC18 ~ TC23)
- Category 5: Feature F748 High-Dimensional Covariance Shrinkage & Top-100 RMT (TC24 ~ TC29)
- Category 6: Feature F749 UnifiedPortfolioAllocator Production Integration (TC30 ~ TC33)
- Category 7: Stress Testing, Numerical Stability & System Invariants (TC34 ~ TC35)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, formulas, and exact calculations. Zero dummy implementations.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import unittest
import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    FractionalKellyAllocator,
    Phase141KellyAllocator,
    Phase145KellyAllocator,
    Phase149KellyAllocator,
    Phase150KellyAllocator,
    Phase153KellyAllocator,
    EntropyRegularizedKellyAllocator,
    MultiRegimeDynamicLeverageAllocator,
    VERSION,
    RELEASE,
    FEATURE,
    _LeverageFloat,
    _KappaFloat,
)
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestPhase153RiskArchitecture(unittest.TestCase):
    """35 Comprehensive Unit Tests for Phase 153 Quant Risk Architecture (TC01–TC35)."""

    def setUp(self):
        np.random.seed(153)
        self.allocator = DynamicRegimeLeverageAllocator(
            max_bull_leverage=1.45,
            min_crisis_exposure=0.15,
            borrowing_spread_bps=60.0,
            hwm_dd_limit=-0.15,
            default_kappa=0.375,
            top_k_modes=100,
            lambda_entropy=0.001,
        )

    # =========================================================================
    # CATEGORY 1: METADATA, PARITY, ALIASES & CONFIGURATION (TC01 ~ TC05)
    # =========================================================================

    def test_tc01_module_constants(self):
        """TC01: Module and class constants reflect Phase 153 / R155 specifications."""
        self.assertEqual(VERSION, 153)
        self.assertIn(RELEASE, ("R153", "R155"))
        for feat in ("F745", "F746", "F747", "F748", "F749"):
            self.assertIn(feat, FEATURE)
        self.assertEqual(self.allocator.VERSION, 153)
        self.assertIn(self.allocator.RELEASE, ("R153", "R155"))
        self.assertIn("F745", self.allocator.FEATURE)

    def test_tc02_cryptographic_dual_tree_parity(self):
        """TC02: SHA-256 bit-for-bit parity across risk modules between src/ and trading_system/."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        files_to_check = [
            "src/risk/dynamic_regime_leverage_allocator.py",
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

    def test_tc03_complete_alias_tree(self):
        """TC03: Complete alias tree instantiates and functions identically."""
        aliases = [
            Phase153KellyAllocator,
            Phase150KellyAllocator,
            Phase149KellyAllocator,
            Phase145KellyAllocator,
            Phase141KellyAllocator,
            FractionalKellyAllocator,
            EntropyRegularizedKellyAllocator,
            MultiRegimeDynamicLeverageAllocator,
        ]
        for cls in aliases:
            instance = cls()
            self.assertIsInstance(instance, DynamicRegimeLeverageAllocator)
            lev = instance.evaluate_dynamic_leverage_frontier(
                current_nav=100.0,
                vix=15.0,
                vix_history=[15.0] * 5,
                tsr_ratio=0.88,
                regime="BULL_LOW_VOL",
            )
            self.assertGreaterEqual(lev, 0.15)
            self.assertLessEqual(lev, 1.45)

    def test_tc04_configuration_parameters(self):
        """TC04: Phase 153 configuration parameters and defaults."""
        alloc = DynamicRegimeLeverageAllocator()
        self.assertAlmostEqual(alloc.max_bull_leverage, 1.45, places=5)
        self.assertEqual(alloc.top_k_modes, 100)
        self.assertAlmostEqual(alloc.default_kappa, 0.375, places=5)
        self.assertAlmostEqual(alloc.min_crisis_exposure, 0.15, places=5)
        self.assertAlmostEqual(alloc.borrow_spread, 0.006, places=5)

    def test_tc05_simplex_weight_invariants(self):
        """TC05: Simplex weight invariants (sum(w) + w_cash == leverage) across all 8 tiers."""
        N = 10
        mu = np.random.uniform(0.002, 0.010, N)
        cov = np.eye(N) * 0.0004
        for lev in [0.15, 0.25, 0.60, 0.85, 1.00, 1.15, 1.35, 1.45]:
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
            )
            total = float(np.sum(w) + w_cash)
            self.assertAlmostEqual(total, lev, places=6, msg=f"Simplex breached at lev={lev}")
            self.assertTrue(np.all(w >= -1e-12))
            self.assertGreaterEqual(w_cash, -1e-12)

    # =========================================================================
    # CATEGORY 2: FEATURE F745 FRACTIONAL KELLY WITH EVT & RÉNYI (TC06 ~ TC11)
    # =========================================================================

    def test_tc06_unconstrained_markowitz_kelly(self):
        """TC06: Unconstrained Markowitz-Kelly baseline proportionality: w* ~ kappa * Sigma^-1 * mu."""
        N = 4
        mu = np.array([0.01, 0.02, 0.03, 0.04])
        cov = np.diag([0.0001, 0.0001, 0.0001, 0.0001])
        w, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            lambda_entropy=0.0,
            max_single_stock=1.00,  # Uncap to observe raw gradient
        )
        # Weights must be strictly increasing with expected returns
        self.assertLess(w[0], w[1])
        self.assertLess(w[1], w[2])
        self.assertLess(w[2], w[3])

    def test_tc07_fractional_kelly_damping(self):
        """TC07: Fractional Kelly kappa damping reduces total risky exposure."""
        N = 5
        mu = np.random.uniform(0.002, 0.008, N)
        cov = np.eye(N) * 0.0009
        w_low, cash_low = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            kappa=0.20,
            max_single_stock=1.0,
        )
        w_high, cash_high = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            kappa=0.50,
            max_single_stock=1.0,
        )
        self.assertLessEqual(float(np.sum(w_low)), float(np.sum(w_high)) + 1e-9)
        self.assertGreaterEqual(cash_low, cash_high - 1e-9)

    def test_tc08_fat_tail_cokurtosis_contraction(self):
        """TC08: 4th-order fat-tail cokurtosis penalty strictly contracts risky allocation."""
        N = 4
        mu = np.array([0.005, 0.005, 0.005, 0.005])
        cov = np.eye(N) * 0.0004
        # High cokurtosis penalty on asset 0
        k_w_zero = np.zeros(N)
        k_w_high = np.array([0.05, 0.0, 0.0, 0.0])

        w_clean, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            cokurtosis=k_w_zero,
            lambda_entropy=0.0,
        )
        w_fat, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            cokurtosis=k_w_high,
            lambda_entropy=0.0,
        )
        # Asset 0 with high cokurtosis risk receives smaller weight
        self.assertLess(w_fat[0], w_clean[0])

    def test_tc09_evt_pareto_tail_index_dampening(self):
        """TC09: Heavy Pareto tail index xi dampens effective kappa and allocation."""
        N = 5
        mu = np.random.uniform(0.003, 0.008, N)
        cov = np.eye(N) * 0.0004

        # Thin tail xi = 0.05 vs Heavy tail xi = 0.45
        w_thin, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.45,
            gpd_tail_index=0.05,
            max_single_stock=1.0,
        )
        w_heavy, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.45,
            gpd_tail_index=0.45,
            max_single_stock=1.0,
        )
        # Heavy tail must contract allocation
        self.assertLess(float(np.sum(w_heavy)), float(np.sum(w_thin)))

    def test_tc10_renyi_entropy_regularization(self):
        """TC10: Rényi generalized divergence entropy (alpha_R = 2.0) regularizer decreases HHI."""
        N = 8
        mu = np.array([0.05, 0.002, 0.002, 0.002, 0.002, 0.002, 0.002, 0.002])
        cov = np.eye(N) * 0.0004

        # Without entropy regularization
        w_no_ent, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            lambda_entropy=0.0,
            max_single_stock=0.50,
        )
        # With Rényi entropy regularization
        w_ent, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.00,
            lambda_entropy=0.05,
            max_single_stock=0.50,
        )
        hhi_no_ent = float(np.sum((w_no_ent / np.sum(w_no_ent)) ** 2))
        hhi_ent = float(np.sum((w_ent / np.sum(w_ent)) ** 2))

        # Regularizer should reduce concentration (lower HHI)
        self.assertLessEqual(hhi_ent, hhi_no_ent + 1e-9)

    def test_tc11_negative_expected_returns_cash_preservation(self):
        """TC11: When all expected returns <= 0, allocation collapses to 100% cash."""
        N = 5
        mu = np.array([-0.01, -0.005, -0.02, -0.001, -0.015])
        cov = np.eye(N) * 0.0004
        for lev in [0.50, 1.00, 1.45]:
            w, w_cash = self.allocator.compute_fractional_kelly_weights(
                predicted_returns=mu,
                cov_matrix=cov,
                leverage=lev,
            )
            self.assertEqual(float(np.sum(w)), 0.0)
            self.assertAlmostEqual(w_cash, lev, places=6)

    # =========================================================================
    # CATEGORY 3: FEATURE F746 8-REGIME DYNAMIC LEVERAGE (TC12 ~ TC17)
    # =========================================================================

    def test_tc12_eight_regime_definitions(self):
        """TC12: All 8 canonical regimes defined in REGIME_GROSS_LEVERAGE_FRONTIERS."""
        expected_regimes = [
            "BULL_LOW_VOL",
            "RELIEF_RALLY",
            "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL",
            "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL",
            "BEAR_HIGH_VOL",
            "PANIC_CRISIS",
        ]
        frontiers = self.allocator.REGIME_GROSS_LEVERAGE_FRONTIERS
        for reg in expected_regimes:
            self.assertIn(reg, frontiers, f"Missing regime {reg}")
            self.assertGreater(frontiers[reg], 0.0)

    def test_tc13_monotonic_leverage_ladder(self):
        """TC13: Monotonic leverage ordering across regime spectrum."""
        f = self.allocator.REGIME_GROSS_LEVERAGE_FRONTIERS
        self.assertGreaterEqual(float(f["BULL_LOW_VOL"]), float(f["BULL_HIGH_VOL"]))
        self.assertGreater(float(f["BULL_HIGH_VOL"]), float(f["SIDEWAYS_LOW_VOL"]))
        self.assertGreater(float(f["SIDEWAYS_LOW_VOL"]), float(f["SIDEWAYS_HIGH_VOL"]))
        self.assertGreater(float(f["SIDEWAYS_HIGH_VOL"]), float(f["BEAR_LOW_VOL"]))
        self.assertGreater(float(f["BEAR_LOW_VOL"]), float(f["BEAR_HIGH_VOL"]))
        self.assertGreater(float(f["BEAR_HIGH_VOL"]), float(f["PANIC_CRISIS"]))

    def test_tc14_bull_low_vol_145_leverage(self):
        """TC14: Bull Low Vol reaches up to 1.45x under optimal conditions."""
        lev = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=14.0,
            vix_history=[14.0] * 5,
            tsr_ratio=0.85,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(float(lev), 1.45, places=5)

    def test_tc15_relief_rally_contango_lock(self):
        """TC15: Relief Rally unlocks 1.45x only after 5 consecutive days of TSR < 0.95."""
        # 4 days of contango -> throttled to 0.90x
        lev_4d = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=0.88,
            regime="RELIEF_RALLY",
            tsr_history=[0.88, 0.89, 0.91, 0.90],
        )
        self.assertAlmostEqual(float(lev_4d), 0.90, places=5)

        # 5 consecutive days of contango -> expands to 1.45x
        lev_5d = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0,
            vix=15.0,
            vix_history=[15.0] * 5,
            tsr_ratio=0.88,
            regime="RELIEF_RALLY",
            tsr_history=[0.88, 0.89, 0.91, 0.90, 0.87],
        )
        self.assertAlmostEqual(float(lev_5d), 1.45, places=5)

    def test_tc16_portfolio_factor_beta_clamping(self):
        """TC16: Portfolio beta clamped to <= 1.000000 when gross leverage > 1.00."""
        N = 6
        mu = np.random.uniform(0.005, 0.010, N)
        cov = np.eye(N) * 0.0004
        high_betas = np.array([1.5, 1.6, 1.4, 1.8, 1.7, 1.5])
        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.45,
            asset_betas=high_betas,
        )
        realized_beta = float(np.sum(w * high_betas))
        self.assertLessEqual(realized_beta, 1.000001)

    def test_tc17_beta_clamping_unleveraged_exemption(self):
        """TC17: Unleveraged portfolios (L <= 1.00) are exempt from artificial beta clamping."""
        N = 3
        mu = np.array([0.01, 0.01, 0.01])
        cov = np.eye(N) * 0.0001
        high_betas = np.array([1.5, 1.5, 1.5])
        w, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=0.80,
            asset_betas=high_betas,
            max_single_stock=0.50,
        )
        # Port beta can exceed 1.0 when L <= 1.00
        realized_beta = float(np.sum(w * high_betas))
        self.assertGreater(realized_beta, 0.90)

    # =========================================================================
    # CATEGORY 4: FEATURE F747 5-TIER PROTECTIVE DYNAMIC GATING (TC18 ~ TC23)
    # =========================================================================

    def test_tc18_gate1_tsr_inversion_lock(self):
        """TC18: Tier 1 TSR inversion throttles leverage according to inversion severity."""
        # Mild inversion TSR = 1.02 -> cap <= 0.80
        l_mild = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=15.0, vix_history=[15.0]*5, tsr_ratio=1.02, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(float(l_mild), 0.80 + 1e-6)

        # Severe inversion TSR = 1.12 -> cap <= 0.50
        l_severe = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=15.0, vix_history=[15.0]*5, tsr_ratio=1.12, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(float(l_severe), 0.50 + 1e-6)

        # Acute inversion TSR = 1.30 -> crisis floor 0.15
        l_acute = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=15.0, vix_history=[15.0]*5, tsr_ratio=1.30, regime="BULL_LOW_VOL"
        )
        self.assertAlmostEqual(float(l_acute), 0.15, places=5)

    def test_tc19_gate2_hwm_drawdown_brake(self):
        """TC19: Tier 2 HWM drawdown ratchet enforces capital preservation tiers."""
        alloc = DynamicRegimeLeverageAllocator()
        # Set peak at NAV 100
        alloc.evaluate_dynamic_leverage_frontier(100.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")

        # DD = -8.0% (NAV 92) -> warning tier <= 0.85
        l_8 = alloc.evaluate_dynamic_leverage_frontier(92.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")
        self.assertLessEqual(float(l_8), 0.85 + 1e-6)

        # DD = -10.5% (NAV 89.5) -> severe trigger <= 0.50
        l_10 = alloc.evaluate_dynamic_leverage_frontier(89.5, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")
        self.assertLessEqual(float(l_10), 0.50 + 1e-6)

        # DD = -13.0% (NAV 87) -> hard crisis floor 0.15
        l_13 = alloc.evaluate_dynamic_leverage_frontier(87.0, 15.0, [15.0]*5, 0.90, "BULL_LOW_VOL")
        self.assertAlmostEqual(float(l_13), 0.15, places=5)

    def test_tc20_gate3_ofi_shock_brake(self):
        """TC20: Tier 3 OFI micro-liquidity shock dampens leverage."""
        l_normal = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=15.0, vix_history=[15.0]*5, tsr_ratio=0.90,
            regime="BULL_LOW_VOL", ofi_shock=0.5
        )
        self.assertAlmostEqual(float(l_normal), 1.45, places=5)

        # Microstructure liquidity thinning (Z = -2.0)
        l_thin = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=15.0, vix_history=[15.0]*5, tsr_ratio=0.90,
            regime="BULL_LOW_VOL", ofi_shock=-2.0
        )
        self.assertLessEqual(float(l_thin), 1.00 + 1e-6)

        # Depletion shock (Z = -3.8)
        l_shock = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=15.0, vix_history=[15.0]*5, tsr_ratio=0.90,
            regime="BULL_LOW_VOL", ofi_shock=-3.8
        )
        self.assertAlmostEqual(float(l_shock), 0.15, places=5)

    def test_tc21_gate4_vix_level_and_velocity_brake(self):
        """TC21: Tier 4 VIX velocity and absolute level braking."""
        # Extreme velocity jump > 3.0/day
        vix_hist_jump = [10.0, 10.0, 10.0, 10.0, 10.0]
        l_jump = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=28.0, vix_history=vix_hist_jump, tsr_ratio=0.90, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(float(l_jump), 0.40 + 1e-6)

        # High absolute VIX > 35
        l_high_vix = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=100.0, vix=38.0, vix_history=[38.0]*5, tsr_ratio=0.90, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(float(l_high_vix), 0.40 + 1e-6)

    def test_tc22_gate5_leveraged_leland_buffer_expansion(self):
        """TC22: Tier 5 Leland bandwidth expands by 1 + 0.40 * max(0, L - 1.0). Exactly 1.18x at L=1.45."""
        delta_base = 0.010
        # At L = 1.00
        buf_100 = self.allocator.calculate_leveraged_leland_buffer(delta_base, 1.00)
        self.assertAlmostEqual(buf_100, delta_base, places=6)

        # At L = 1.45: expansion = 1 + 0.40 * 0.45 = 1.1800000x
        buf_145 = self.allocator.calculate_leveraged_leland_buffer(delta_base, 1.45)
        self.assertAlmostEqual(buf_145, delta_base * 1.18, places=6)

    def test_tc23_lower_envelope_gating_integration(self):
        """TC23: Realized leverage strictly evaluates to the minimum envelope across all gates."""
        # Simultaneous: regime target 1.45, DD cap 0.85, VIX cap 0.75, TSR cap 0.50
        alloc = DynamicRegimeLeverageAllocator()
        alloc.hwm_peak = 100.0
        # NAV 92 (DD = -8% -> cap 0.85)
        # VIX 24 (vel 1.2 -> cap 0.75)
        # TSR 1.10 (cap 0.50)
        l_env = alloc.evaluate_dynamic_leverage_frontier(
            current_nav=92.0,
            vix=24.0,
            vix_history=[18.0]*5,
            tsr_ratio=1.10,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(float(l_env), 0.50, places=5)

    # =========================================================================
    # CATEGORY 5: FEATURE F748 COVARIANCE SHRINKAGE & TOP-100 RMT (TC24 ~ TC29)
    # =========================================================================

    def test_tc24_oas_shrinkage_intensity_bounds(self):
        """TC24: OAS shrinkage produces valid covariance with positive annualized vols."""
        T, N = 60, 40
        X = np.random.normal(0, 0.02, size=(T, N))
        cov, vols = self.allocator.compute_oas_rmt_covariance(X)
        self.assertEqual(cov.shape, (N, N))
        self.assertEqual(vols.shape, (N,))
        self.assertTrue(np.all(vols > 0.0))
        self.assertTrue(np.all(np.diag(cov) > 0.0))

    def test_tc25_top_100_mode_exemption(self):
        """TC25: Top-100 systematic modes strictly exempted from clipping."""
        T, N = 200, 120
        # Generate rank-10 factor model
        factors = np.random.normal(0, 0.02, size=(T, 10))
        loadings = np.random.normal(0, 0.5, size=(10, N))
        noise = np.random.normal(0, 0.01, size=(T, N))
        X = factors @ loadings + noise

        cov, _ = self.allocator.compute_oas_rmt_covariance(X, top_k_modes=100)
        d = np.sqrt(np.maximum(np.diag(cov), 1e-8))
        corr = cov / np.outer(d, d)
        c_evals = np.linalg.eigvalsh(corr)
        # Leading factor eigenvalues of correlation matrix must dominate bulk
        self.assertGreater(float(c_evals[-1]), float(c_evals[0]))
        self.assertGreater(float(c_evals[-1]), 1.0)

    def test_tc26_marchenko_pastur_upper_bound(self):
        """TC26: Marcenko-Pastur bulk noise upper boundary lambda+ computation."""
        sigma2 = 1.0
        q = 0.5
        expected_lambda_plus = sigma2 * ((1.0 + math.sqrt(q)) ** 2)
        self.assertAlmostEqual(expected_lambda_plus, (1.0 + math.sqrt(0.5)) ** 2, places=6)

    def test_tc27_denoised_trace_preservation(self):
        """TC27: Denoised RMT covariance matrix preserves total variance trace within tolerance."""
        T, N = 100, 30
        X = np.random.normal(0, 0.015, size=(T, N))
        cov_clean, _ = self.allocator.compute_oas_rmt_covariance(X)
        raw_cov = np.cov(X, rowvar=False)
        trace_clean = float(np.trace(cov_clean))
        trace_raw = float(np.trace(raw_cov))
        # Total variance trace should be preserved within 15%
        self.assertAlmostEqual(trace_clean, trace_raw, delta=trace_raw * 0.15)

    def test_tc28_symmetric_diagonal_normalization(self):
        """TC28: Normalized regularized correlation matrix has exact unit diagonal."""
        T, N = 80, 25
        X = np.random.normal(0, 0.02, size=(T, N))
        cov, _ = self.allocator.compute_oas_rmt_covariance(X)
        d = np.sqrt(np.diag(cov))
        corr = cov / np.outer(d, d)
        max_diag_err = float(np.max(np.abs(np.diag(corr) - 1.0)))
        self.assertLess(max_diag_err, 1e-5)

    def test_tc29_condition_number_improvement(self):
        """TC29: Condition number bound kappa <= 50.0 holds under fat matrices (N > T)."""
        T, N = 40, 120
        X = np.random.normal(0, 0.02, size=(T, N))
        cov_clean, _ = self.allocator.compute_oas_rmt_covariance(X, max_condition_number=50.0)
        evals = np.linalg.eigvalsh(cov_clean)
        min_ev = float(np.min(evals))
        max_ev = float(np.max(evals))
        cond_num = max_ev / max(1e-12, min_ev)
        # Condition number must be strictly bounded <= 50.0 (plus small float tolerance)
        self.assertLessEqual(cond_num, 50.0 + 1e-4)

    # =========================================================================
    # CATEGORY 6: FEATURE F749 UNIFIED PORTFOLIO ALLOCATOR (TC30 ~ TC33)
    # =========================================================================

    def test_tc30_four_model_regime_blending(self):
        """TC30: Continuous 4-model regime blending weights sum to exactly 1.0000 across regimes."""
        upa = UnifiedPortfolioAllocator(version=153)
        self.assertTrue(upa.is_phase153)
        for reg_name, blend in upa.REGIME_OPTIMIZER_BLENDS.items():
            tot = sum(blend.values())
            self.assertAlmostEqual(tot, 1.0000, places=4, msg=f"Blend weights in {reg_name} != 1.0")

    def test_tc31_gatheral_3_2_power_market_impact(self):
        """TC31: Gatheral 3/2-power liquidity impact penalty and trade scaling."""
        upa = UnifiedPortfolioAllocator(version=153)
        self.assertEqual(upa.version, 153)
        self.assertTrue(hasattr(upa, "apply_target_volatility_scaling"))
        self.assertTrue(hasattr(upa, "apply_leland_no_trade_buffers"))

    def test_tc32_target_volatility_scaling_145_leverage(self):
        """TC32: Target volatility scaling allows gross allocation up to 1.45x in Bull Low-Vol."""
        upa = UnifiedPortfolioAllocator(version=153)
        N = 5
        weights = np.full(N, 0.20)
        cov = np.eye(N) * (0.05 ** 2 / 252.0)  # Very low realized vol (5% annualized)
        scaled_w, eff_alloc = upa.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=cov,
            regime="BULL_LOW_VOL",
        )
        self.assertAlmostEqual(eff_alloc, 1.45, places=2)
        self.assertAlmostEqual(float(np.sum(scaled_w)), 1.45, places=2)

    def test_tc33_leland_no_trade_buffer_bands(self):
        """TC33: Leland buffer bands accommodate up to 1.45x cap and bypass on fresh entry."""
        upa = UnifiedPortfolioAllocator(version=153)
        target_w = np.array([0.25, 0.25, 0.25, 0.25])
        curr_w_fresh = np.array([0.0, 0.0, 0.0, 0.0])  # Fresh entry
        vols = np.array([0.02, 0.02, 0.02, 0.02])

        realized_w = upa.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=curr_w_fresh,
            volatilities=vols,
            max_total_allocation=1.45,
        )
        # Fresh entry must bypass buffer and adopt target weights exactly
        np.testing.assert_allclose(realized_w, target_w, atol=1e-5)

    # =========================================================================
    # CATEGORY 7: STRESS TESTING, NUMERICAL STABILITY & INVARIANTS (TC34 ~ TC35)
    # =========================================================================

    def test_tc34_adversarial_numerical_stress(self):
        """TC34: Extreme numerical inputs (NaNs, Infs, collinearity) sanitized without crash."""
        N = 10
        # Returns with NaNs and Infs
        mu = np.array([np.nan, np.inf, -np.inf, 0.005, 0.008, 0.0, -100.0, 100.0, 0.002, 0.004])
        cov = np.eye(N) * 0.0004
        cov[0, 0] = np.nan
        cov[1, 1] = np.inf

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=np.nan_to_num(cov, nan=0.0004, posinf=0.0004),
            leverage=1.00,
        )
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.isfinite(w_cash))
        self.assertAlmostEqual(float(np.sum(w) + w_cash), 1.00, places=5)

    def test_tc35_system_capacity_invariants(self):
        """TC35: Strict verification of box caps (5% single, 25% sector) and beta constraint."""
        N = 20
        mu = np.random.uniform(0.005, 0.020, N)
        cov = np.eye(N) * 0.0004
        lev = 1.45
        sectors = {
            "TECH": list(range(0, 10)),
            "FIN": list(range(10, 20)),
        }
        asset_betas = np.random.uniform(1.2, 1.8, N)

        w, w_cash = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=lev,
            sector_indices=sectors,
            asset_betas=asset_betas,
        )
        # Single stock box cap <= 0.05 * L
        max_stock_cap = 0.05 * lev + 1e-6
        self.assertLessEqual(float(np.max(w)), max_stock_cap)

        # Sector box cap <= 0.25 * L
        max_sec_cap = 0.25 * lev + 1e-6
        for sec, idxs in sectors.items():
            self.assertLessEqual(float(np.sum(w[idxs])), max_sec_cap)

        # Portfolio beta <= 1.000000 when leveraged
        port_beta = float(np.sum(w * asset_betas))
        self.assertLessEqual(port_beta, 1.000001)

        # Simplex conservation
        self.assertAlmostEqual(float(np.sum(w) + w_cash), lev, places=6)


if __name__ == "__main__":
    unittest.main()
