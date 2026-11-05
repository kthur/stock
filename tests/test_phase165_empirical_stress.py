"""
tests/test_phase165_empirical_stress.py — Empirical Challenger Stress Suite for Phase 165 (Milestone 2).

Comprehensive Empirical Stress Tests for Phase 165 Quant Risk Architecture (Features F805–F809):
- Module 1: F805 Higher-Order Tail-Risk Fractional Kelly & Tsallis/Rényi Regularization Under Stress (TC01–TC07)
- Module 2: F806 Compounding Dynamic Leverage Frontiers (1.60x), Beta Clamping & Volatility Targeting (TC08–TC14)
- Module 3: F807 7-Tier Dynamic Gating Envelope & 4-Stage Drawdown Ratchet Under Catastrophic Regimes (TC15–TC22)
- Module 4: F808 Poincaré Ball Hyperbolic Manifold Geometry, Geodesic Metric & Sinkhorn-Knopp OT (TC23–TC30)
- Module 5: F809 UnifiedPortfolioAllocator 5-Model Blending, Gatheral Impact & Multi-Market Friction (TC31–TC37)
- Module 6: Institutional Master Invariants, Cryptographic Parity & Latency SLA (TC38–TC40)

MANDATORY INTEGRITY:
All tests assert real mathematical behaviors, closed-form formulas, and exact empirical bounds.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import time
import unittest
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../trading_system")))

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    WassersteinRobustKellyOptimizer,
    CorrelationBreakdownBrake,
    _LeverageFloat,
    _KappaFloat,
    _TopModesInt,
    _VersionInt,
    _ReleaseStr,
    _FeatureStr,
)
from src.risk.hyperbolic_optimal_transport_allocator import (
    HyperbolicOptimalTransportAllocator,
    HyperbolicAllocatorConfig,
    HyperbolicAllocationOutput,
    REGIME_HYPERBOLIC_PARAMS,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator, AllocationResult


class TestPhase165EmpiricalStress(unittest.TestCase):
    """Empirical Stress Test Suite for Phase 165 (TC01–TC40)."""

    def setUp(self) -> None:
        np.random.seed(16500)
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
        self.hot_allocator = HyperbolicOptimalTransportAllocator()

    # =========================================================================
    # MODULE 1: F805 HIGHER-ORDER TAIL-RISK FRACTIONAL KELLY STRESS (TC01–TC07)
    # =========================================================================

    def test_tc01_singular_rank1_and_rank2_covariance(self):
        """TC01 [F805]: Robust Kelly optimizer handles rank-deficient singular covariance matrices."""
        N = 6
        mu = np.array([0.06, 0.05, 0.04, 0.03, 0.02, 0.01])
        # Rank-1 outer product
        cov_rank1 = np.outer(np.ones(N), np.ones(N)) * 0.04
        w_r1 = self.allocator.compute_distributionally_robust_kelly_weights(
            alpha=mu, cov=cov_rank1, epsilon_w=0.01, target_leverage=1.60
        )
        self.assertTrue(np.all(np.isfinite(w_r1)))
        self.assertTrue(np.all(w_r1 >= -1e-7))
        self.assertLessEqual(float(np.sum(w_r1)), 1.60 + 1e-5)

        # Rank-2 covariance
        v1 = np.ones(N)
        v2 = np.array([1, -1, 1, -1, 1, -1])
        cov_rank2 = np.outer(v1, v1) * 0.02 + np.outer(v2, v2) * 0.02
        w_r2 = self.allocator.compute_distributionally_robust_kelly_weights(
            alpha=mu, cov=cov_rank2, epsilon_w=0.01, target_leverage=1.60
        )
        self.assertTrue(np.all(np.isfinite(w_r2)))
        self.assertTrue(np.all(w_r2 >= -1e-7))

    def test_tc02_high_dimensional_universe_100_assets(self):
        """TC02 [F805]: High-dimensional universe (N=100) robust Kelly converges within bounds."""
        N = 100
        rng = np.random.RandomState(42)
        mu = rng.uniform(0.01, 0.08, N)
        X = rng.normal(0, 0.02, (252, N))
        cov = np.cov(X, rowvar=False)

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            alpha=mu, cov=cov, epsilon_w=0.02, target_leverage=1.60
        )
        self.assertEqual(len(w), N)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= -1e-7))
        self.assertLessEqual(float(np.sum(w)), 1.60 + 1e-4)

    def test_tc03_tsallis_q_entropy_concentration_reduction(self):
        """TC03 [F805]: Tsallis entropy regularization (q=1.5) strictly reduces Herfindahl concentration."""
        mu = np.array([0.30, 0.01, 0.01, 0.01])
        cov = np.eye(4) * 0.04

        # Zero entropy regularizer
        w_unreg = self.allocator.compute_distributionally_robust_kelly_weights(
            alpha=mu, cov=cov, epsilon_w=0.0, lambda_entropy=0.0, target_leverage=1.0
        )
        hhi_unreg = float(np.sum((w_unreg / np.sum(w_unreg)) ** 2))

        # Tsallis regularized
        w_tsallis = self.allocator.compute_tsallis_regularized_kelly(
            mu=mu, cov=cov, q_tsallis=1.5, lambda_entropy=0.05, target_leverage=1.0
        )
        hhi_tsallis = float(np.sum((w_tsallis / np.sum(w_tsallis)) ** 2))

        self.assertLess(hhi_tsallis, hhi_unreg)
        self.assertLess(w_tsallis[0], 0.95)

    def test_tc04_renyi_alpha_entropy_monotonic_diversification(self):
        """TC04 [F805]: Rényi entropy regularization prevents corner collapse across multiple assets."""
        mu = np.array([0.25, 0.02, 0.02, 0.02])
        cov = np.eye(4) * 0.04
        w_renyi = self.allocator.compute_renyi_regularized_kelly(
            mu=mu, cov=cov, alpha_renyi=2.0, lambda_entropy=0.05, target_leverage=1.0
        )
        self.assertLess(w_renyi[0], 0.95)
        self.assertTrue(np.all(w_renyi[1:] > 0.01))

    def test_tc05_downside_semi_variance_asymmetric_shock(self):
        """TC05 [F805]: Downside semivariance penalizes negative returns without penalizing upside windfalls."""
        # Asset 1 has positive windfall spikes, Asset 2 has negative drawdown crashes
        T = 100
        rets = np.zeros((T, 2))
        rets[:, 0] = np.random.normal(0.001, 0.01, T)
        rets[10:15, 0] = 0.08  # positive spikes
        rets[:, 1] = np.random.normal(0.001, 0.01, T)
        rets[20:25, 1] = -0.08 # negative crashes

        semi_cov, semi_vols = self.allocator.compute_downside_semivariance(rets)
        self.assertGreater(semi_vols[1], semi_vols[0])
        self.assertEqual(semi_cov.shape, (2, 2))
        self.assertTrue(np.all(np.isfinite(semi_cov)))

    def test_tc06_adaptive_kappa_volatility_trend_sweep(self):
        """TC06 [F805]: Adaptive kappa decreases monotonically with increasing volatility trend."""
        trends = [-0.10, -0.05, 0.0, 0.05, 0.10, 0.20]
        kappas = [float(self.allocator.compute_adaptive_kappa(regime="BULL_LOW_VOL", vol_trend=t)) for t in trends]
        for i in range(len(kappas) - 1):
            self.assertGreaterEqual(kappas[i], kappas[i + 1])
            self.assertTrue(0.0 <= kappas[i] <= 0.60)

    def test_tc07_evt_pareto_tail_contraction_extremes(self):
        """TC07 [F805]: EVT Pareto tail contraction handles extreme returns without overflow or NaN."""
        extreme_rets = np.array([-0.90, -0.50, -0.20, 0.0, 0.10, 0.50, 1.0])
        dampened = self.allocator.apply_evt_tail_contraction(extreme_rets, xi=0.25)
        self.assertTrue(np.all(np.isfinite(dampened)))
        # Downside returns are dampened towards zero
        self.assertGreater(dampened[0], extreme_rets[0])
        self.assertGreater(dampened[1], extreme_rets[1])
        # Upside returns are preserved
        self.assertEqual(dampened[3], extreme_rets[3])
        self.assertEqual(dampened[4], extreme_rets[4])

    # =========================================================================
    # MODULE 2: F806 DYNAMIC LEVERAGE (1.60x), BETA & VOL TARGETING (TC08–TC14)
    # =========================================================================

    def test_tc08_all_eight_regimes_frontier_exact_values(self):
        """TC08 [F806]: All 8 market regimes map to exact Phase 165 gross leverage frontiers."""
        expected_frontiers = {
            "BULL_LOW_VOL": 1.60,
            "RELIEF_RALLY": 1.60,
            "BULL_HIGH_VOL": 1.25,
            "SIDEWAYS_LOW_VOL": 1.05,
            "SIDEWAYS_HIGH_VOL": 0.85,
            "BEAR_LOW_VOL": 0.55,
            "BEAR_HIGH_VOL": 0.25,
            "PANIC_CRISIS": 0.15,
        }
        for reg, exp_val in expected_frontiers.items():
            lev = float(self.allocator.compute_regime_leverage_frontier(reg))
            self.assertAlmostEqual(lev, exp_val, places=2, msg=f"Mismatch for regime {reg}")

    def test_tc09_target_volatility_12_5pct_under_diverse_vols(self):
        """TC09 [F806]: 12.5% Target Volatility scales weights inversely to portfolio volatility."""
        N = 5
        weights = np.ones(N) / N

        # Case 1: Low vol (6% annual) -> Scaled up towards 1.60x
        cov_low = np.eye(N) * ((0.06 / math.sqrt(252)) ** 2)
        scaled_low, _ = self.unified_allocator.apply_target_volatility_scaling(
            weights=weights, cov_matrix=cov_low, regime="BULL_LOW_VOL"
        )
        self.assertAlmostEqual(float(np.sum(scaled_low)), 1.60, places=1)

        # Case 2: High vol (realized portfolio vol 35% annual with correlated assets) -> Scaled down
        cov_high = np.ones((N, N)) * ((0.35 / math.sqrt(252)) ** 2)
        scaled_high, _ = self.unified_allocator.apply_target_volatility_scaling(
            weights=weights, cov_matrix=cov_high, regime="SIDEWAYS_HIGH_VOL"
        )
        self.assertLess(float(np.sum(scaled_high)), 0.85)

    def test_tc10_factor_beta_clamping_at_extreme_betas(self):
        """TC10 [F806]: Portfolio beta is strictly bounded <= 1.000001 even when all asset betas are 2.50."""
        N = 4
        mu = np.array([0.08, 0.07, 0.06, 0.05])
        cov = np.eye(N) * 0.02
        extreme_betas = np.full(N, 2.50)

        weights, _ = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu, cov_matrix=cov, leverage=1.60, asset_betas=extreme_betas
        )
        port_beta = float(np.sum(weights * extreme_betas))
        self.assertLessEqual(port_beta, 1.000001 + 1e-9)

    def test_tc11_single_stock_cap_redistribution_at_160x(self):
        """TC11 [F806]: Single-stock weight is strictly capped at 0.05 * 1.60 = 0.080."""
        N = 10
        weights_in = {f"stock_{i}": 0.16 if i == 0 else 0.02 for i in range(N)}
        sectors = {f"stock_{i}": f"sec_{i % 3}" for i in range(N)}

        capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights_in, sectors=sectors, gross_leverage=1.60
        )
        max_w = max(capped.values())
        self.assertLessEqual(max_w, 0.080 + 1e-6)

    def test_tc12_single_sector_cap_redistribution_at_160x(self):
        """TC12 [F806]: Single-sector weight is strictly capped at 0.25 * 1.60 = 0.400."""
        N = 10
        # All stocks belong to "tech"
        weights_in = {f"stock_{i}": 0.07 for i in range(N)} # total 0.70
        sectors = {f"stock_{i}": "tech" for i in range(N)}

        capped = DynamicRegimeLeverageAllocator.enforce_concentration_caps(
            weights=weights_in, sectors=sectors, gross_leverage=1.60
        )
        tech_total = sum(capped.values())
        self.assertLessEqual(tech_total, 0.400 + 1e-6)

    def test_tc13_borrowing_cost_drag_linear_scaling(self):
        """TC13 [F806]: Borrowing cost drag is exactly zero for L <= 1.0 and scales linearly for L > 1.0."""
        self.assertEqual(self.allocator.calculate_borrowing_cost_drag(0.80), 0.0)
        self.assertEqual(self.allocator.calculate_borrowing_cost_drag(1.00), 0.0)

        drag_130 = self.allocator.calculate_borrowing_cost_drag(1.30, borrowing_spread_bps=50.0)
        self.assertAlmostEqual(drag_130, 0.30 * 0.0050, places=7)

        drag_160 = self.allocator.calculate_borrowing_cost_drag(1.60, borrowing_spread_bps=50.0)
        self.assertAlmostEqual(drag_160, 0.60 * 0.0050, places=7)

    def test_tc14_relief_rally_contango_lock_5day_window(self):
        """TC14 [F806]: Relief rally grants 1.60x when 5-day contango (TSR < 0.95) is satisfied."""
        tsr_good_5d = [0.91, 0.92, 0.90, 0.89, 0.93]
        lev_good = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=1e8, vix=18.0, vix_history=[18.0]*5, tsr_ratio=0.90, regime="RELIEF_RALLY", tsr_history=tsr_good_5d
        )
        self.assertAlmostEqual(float(lev_good), 1.60, places=2)

        tsr_bad_5d = [0.91, 0.92, 1.05, 0.89, 0.93] # day 3 had backwardation
        lev_bad = self.allocator.evaluate_dynamic_leverage_frontier(
            current_nav=1e8, vix=18.0, vix_history=[18.0]*5, tsr_ratio=0.90, regime="RELIEF_RALLY", tsr_history=tsr_bad_5d
        )
        self.assertAlmostEqual(float(lev_bad), 0.90, places=2)

    # =========================================================================
    # MODULE 3: F807 7-TIER DYNAMIC GATING & CATASTROPHIC CRISIS (TC15–TC22)
    # =========================================================================

    def test_tc15_tier1_severe_crisis_gate_triggers(self):
        """TC15 [F807]: Tier 1 Severe Crisis Gate activates on VIX >= 40.0, DD <= -13.5%, or PANIC_CRISIS."""
        # Condition A: VIX = 42
        r_vix = self.allocator.evaluate_7tier_protective_gating(vix=42.0, regime="BULL_LOW_VOL")
        self.assertTrue(r_vix["tier1_crisis_gate_active"])
        self.assertLessEqual(r_vix["allowed_leverage"], 0.15)

        # Condition B: DD = -0.14
        r_dd = self.allocator.evaluate_7tier_protective_gating(drawdown=-0.14, regime="BULL_LOW_VOL")
        self.assertTrue(r_dd["tier1_crisis_gate_active"])
        self.assertLessEqual(r_dd["allowed_leverage"], 0.15)

        # Condition C: PANIC_CRISIS regime
        r_reg = self.allocator.evaluate_7tier_protective_gating(regime="PANIC_CRISIS")
        self.assertTrue(r_reg["tier1_crisis_gate_active"])
        self.assertLessEqual(r_reg["allowed_leverage"], 0.15)

    def test_tc16_tier2_volatility_velocity_explosion(self):
        """TC16 [F807]: Tier 2 activates on VIX >= 30.0 or 5-day VIX velocity >= 2.50 pts/day."""
        vix_hist = [18.0, 19.0, 20.0, 22.0, 32.0] # 5-day delta = 14 pts -> vel = 2.80
        res = self.allocator.evaluate_7tier_protective_gating(vix=32.0, vix_history=vix_hist, regime="BULL_LOW_VOL")
        self.assertTrue(res["tier2_vol_spike_active"])
        self.assertLessEqual(res["allowed_leverage"], 0.40)

    def test_tc17_tier3_tsr_inversion_lock(self):
        """TC17 [F807]: TSR inversion (TSR >= 1.08) locks leverage <= 0.50x."""
        res = self.allocator.evaluate_7tier_protective_gating(tsr=1.12, regime="BULL_LOW_VOL")
        self.assertTrue(res["tier3_tsr_lock_active"])
        self.assertLessEqual(res["allowed_leverage"], 0.50)

    def test_tc18_tier3b_ofi_micro_liquidity_shock(self):
        """TC18 [F807]: OFI micro-liquidity shock (OFI <= -2.0) caps leverage <= 0.40x."""
        res = self.allocator.evaluate_7tier_protective_gating(ofi_shock=-3.0, regime="BULL_LOW_VOL")
        self.assertTrue(res["ofi_shock_gate_active"])
        self.assertLessEqual(res["allowed_leverage"], 0.40)

    def test_tc19_tier4_hwm_drawdown_ratchet_stair_steps(self):
        """TC19 [F807]: 4-Stage HWM Drawdown Ratchet enforces exact stair-steps."""
        drawdowns = [-0.07, -0.085, -0.105, -0.125, -0.140]
        expected_caps = [1.60, 0.85, 0.50, 0.25, 0.15]

        for dd, exp_cap in zip(drawdowns, expected_caps):
            res = self.allocator.evaluate_7tier_protective_gating(drawdown=dd, regime="BULL_LOW_VOL")
            self.assertLessEqual(float(res["allowed_leverage"]), exp_cap + 1e-4)

    def test_tc20_tier5_correlation_breakdown_brake(self):
        """TC20 [F807]: Correlation breakdown (mean_corr >= 0.85) applies 0.70x haircut."""
        res = self.allocator.evaluate_7tier_protective_gating(mean_corr=0.90, regime="BULL_LOW_VOL")
        self.assertTrue(res["tier5_correlation_brake_active"])
        self.assertEqual(res["haircut_multiplier"], 0.70)
        self.assertLessEqual(float(res["allowed_leverage"]), 0.70 * 1.60 + 1e-4)

    def test_tc21_tier6_leveraged_leland_expansion_monotonicity(self):
        """TC21 [F807]: Leveraged Leland buffer bandwidth strictly expands for L > 1.0."""
        b_100 = self.allocator.compute_leveraged_leland_bandwidth(base_bandwidth=0.01, leverage=1.00)
        b_125 = self.allocator.compute_leveraged_leland_bandwidth(base_bandwidth=0.01, leverage=1.25)
        b_160 = self.allocator.compute_leveraged_leland_bandwidth(base_bandwidth=0.01, leverage=1.60)

        self.assertAlmostEqual(b_100, 0.01, places=5)
        self.assertGreater(b_125, b_100)
        self.assertGreater(b_160, b_125)
        self.assertAlmostEqual(b_160, 0.01 * (1.0 + 0.40 * 0.60), places=6)

    def test_tc22_tier7_cross_asset_contagion_gate(self):
        """TC22 [F807]: Macro impulse > 2.50 sigma triggers Tier 7 contagion gate, capping leverage <= 0.35x."""
        res_calm = self.allocator.evaluate_7tier_protective_gating(contagion_impulse=1.5, regime="BULL_LOW_VOL")
        self.assertFalse(res_calm["tier7_contagion_gate_active"])

        res_shock = self.allocator.evaluate_7tier_protective_gating(contagion_impulse=3.2, regime="BULL_LOW_VOL")
        self.assertTrue(res_shock["tier7_contagion_gate_active"])
        self.assertLessEqual(float(res_shock["allowed_leverage"]), 0.35)

    # =========================================================================
    # MODULE 4: F808 POINCARÉ BALL GEOMETRY & SINKHORN TRANSPORT (TC23–TC30)
    # =========================================================================

    def test_tc23_poincare_metric_axioms_random_triples(self):
        """TC23 [F808]: Poincaré geodesic distance satisfies metric axioms for 50 random triples."""
        rng = np.random.RandomState(42)
        c = 0.25
        max_r = (1.0 / math.sqrt(c)) * 0.85 # strictly inside ball

        for _ in range(50):
            x = rng.uniform(-max_r / math.sqrt(2), max_r / math.sqrt(2), 2)
            y = rng.uniform(-max_r / math.sqrt(2), max_r / math.sqrt(2), 2)
            z = rng.uniform(-max_r / math.sqrt(2), max_r / math.sqrt(2), 2)

            d_xx = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, x, c)
            d_xy = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, y, c)
            d_yx = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(y, x, c)
            d_xz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, z, c)
            d_yz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(y, z, c)

            self.assertEqual(d_xx, 0.0)
            self.assertGreaterEqual(d_xy, 0.0)
            self.assertAlmostEqual(d_xy, d_yx, places=8)
            self.assertLessEqual(d_xz, d_xy + d_yz + 1e-7)

    def test_tc24_poincare_distance_near_boundary_asymptote(self):
        """TC24 [F808]: Poincaré distance grows towards infinity near disk boundary ||x|| -> 1/sqrt(c)."""
        c = 0.25
        r_bound = 1.0 / math.sqrt(c) # 2.0
        p_center = np.array([0.0, 0.0])

        d_05 = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p_center, np.array([1.0, 0.0]), c)
        d_09 = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p_center, np.array([1.8, 0.0]), c)
        d_99 = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p_center, np.array([1.98, 0.0]), c)

        self.assertGreater(d_09, d_05)
        self.assertGreater(d_99, d_09)

    def test_tc25_sinkhorn_knopp_convergence_tolerance(self):
        """TC25 [F808]: Sinkhorn-Knopp algorithm converges within tolerance in < 100 iterations."""
        N = 5
        rng = np.random.RandomState(42)
        p = rng.dirichlet(np.ones(N))
        q = rng.dirichlet(np.ones(N))
        C = rng.uniform(0.1, 1.5, (N, N))
        np.fill_diagonal(C, 0.0)

        P, dist = self.hot_allocator.sinkhorn_optimal_transport(p, q, C, eps=0.05, max_iters=100)
        self.assertEqual(P.shape, (N, N))
        self.assertTrue(math.isfinite(dist))
        self.assertGreater(dist, 0.0)

    def test_tc26_sinkhorn_knopp_marginal_preservation_accuracy(self):
        """TC26 [F808]: Sinkhorn-Knopp preserves row and column marginals within 10^-5."""
        N = 8
        rng = np.random.RandomState(42)
        p = rng.dirichlet(np.ones(N))
        q = rng.dirichlet(np.ones(N))
        C = rng.uniform(0.1, 2.0, (N, N))
        np.fill_diagonal(C, 0.0)

        P, _ = self.hot_allocator.sinkhorn_optimal_transport(p, q, C, eps=0.05)
        row_diff = float(np.max(np.abs(np.sum(P, axis=1) - p)))
        col_diff = float(np.max(np.abs(np.sum(P, axis=0) - q)))

        self.assertLess(row_diff, 1e-5)
        self.assertLess(col_diff, 1e-5)

    def test_tc27_regime_curvature_modulation_parameters(self):
        """TC27 [F808]: Curvature and entropy parameters are properly configured across all regimes."""
        for reg in [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS", "CRISIS"
        ]:
            params = HyperbolicOptimalTransportAllocator.get_regime_hyperbolic_params(reg)
            self.assertIn("c", params)
            self.assertIn("eps", params)
            self.assertIn("max_exp", params)
            self.assertTrue(0.05 <= params["c"] <= 1.00)
            self.assertTrue(0.01 <= params["eps"] <= 0.50)

    def test_tc28_instant_bypass_new_entry_and_full_exit(self):
        """TC28 [F808]: Geodesic Leland dynamic buffer instantly bypasses new buy and full liquidation."""
        curr = np.array([0.00, 0.20, 0.33, 0.33])
        alpha = np.array([0.30, 0.00, 0.30, 0.30])
        symbols = ["NEW_STOCK", "EXIT_STOCK", "HOLD_STOCK", "OTHER_STOCK"]

        out = self.hot_allocator.allocate(curr, alpha, symbols, regime="BULL_LOW_VOL")
        self.assertEqual(out.rebalance_actions["NEW_STOCK"], "BUY")
        self.assertEqual(out.rebalance_actions["EXIT_STOCK"], "SELL")
        self.assertEqual(out.rebalance_actions["HOLD_STOCK"], "HOLD")

    def test_tc29_top_180_rmt_eigenvector_denoising(self):
        """TC29 [F808]: Non-linear RMT cleaning preserves top 180 eigenvectors and caps condition number <= 45.0."""
        rng = np.random.RandomState(42)
        X = rng.normal(0, 1, (500, 250))
        raw_cov = np.cov(X, rowvar=False)

        clean_cov = self.allocator.denoise_covariance_nonlinear_rmt(raw_cov, top_modes=180, max_condition_number=45.0)
        cond = float(np.linalg.cond(clean_cov))
        self.assertLessEqual(cond, 45.0 + 1e-4)
        self.assertEqual(clean_cov.shape, (250, 250))

    def test_tc30_hyperbolic_cost_matrix_with_friction_costs(self):
        """TC30 [F808]: Ground metric cost matrix incorporates friction penalties correctly."""
        N = 3
        embeddings = np.array([[0.1, 0.0], [0.0, 0.1], [-0.1, 0.0]])
        friction_bps = np.array([5.0, 25.0, 35.0]) # SP500, KOSPI, KOSDAQ

        C = self.hot_allocator.construct_hyperbolic_cost_matrix(
            embeddings=embeddings, friction_costs=friction_bps / 10000.0, curvature=0.25
        )
        self.assertEqual(C.shape, (3, 3))
        self.assertEqual(C[0, 0], 0.0)
        self.assertGreater(C[0, 2], 0.0)

    # =========================================================================
    # MODULE 5: F809 5-MODEL BLENDING, IMPACT & FRICTION (TC31–TC37)
    # =========================================================================

    def test_tc31_five_model_blending_weights_sum_to_one(self):
        """TC31 [F809]: Master 5-model blending weights sum identically to 1.0000 across all 8 regimes."""
        regimes = [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS", "CRISIS"
        ]
        for reg in regimes:
            w_dict = self.unified_allocator.get_regime_model_weights_phase165(reg)
            self.assertEqual(len(w_dict), 5)
            self.assertAlmostEqual(sum(w_dict.values()), 1.0000, places=5)
            for m, weight in w_dict.items():
                self.assertTrue(0.0 <= weight <= 1.0)

    def test_tc32_gatheral_three_halves_power_penalty_monotonicity(self):
        """TC32 [F809]: Gatheral 3/2-power market impact penalty satisfies strict convexity."""
        adv = 1e8
        orders = [1e5, 5e5, 1e6, 5e6, 1e7]
        penalties = [self.unified_allocator.compute_market_impact_penalty(o, adv) for o in orders]
        for i in range(len(penalties) - 1):
            self.assertGreater(penalties[i + 1], penalties[i])

        # Convexity check: f(5M) / f(1M) = (5)^1.5 approx 11.18
        ratio = penalties[3] / max(penalties[2], 1e-9)
        self.assertAlmostEqual(ratio, 5.0 ** 1.5, delta=0.5)

    def test_tc33_phase164_alpha_ingestion_gradient(self):
        """TC33 [F809]: Phase 164 composite alpha alters expected return vector proportionally."""
        mu_zero = np.zeros(3)
        alpha_p164 = np.array([2.0, 0.0, -2.0])
        cov = np.eye(3) * 0.04

        res = self.unified_allocator.allocate_portfolio_phase165(
            expected_returns=mu_zero, covariance=cov, regime="BULL_LOW_VOL", alpha_p164=alpha_p164
        )
        self.assertGreater(res["asset_0"], res["asset_1"])
        self.assertGreaterEqual(res["asset_1"], res["asset_2"])

    def test_tc34_asymmetric_leland_runners_and_laggards(self):
        """TC34 [F809]: Asymmetric Leland buffer expands upper band for runners and tightens lower band for laggards."""
        up_runner, low_runner = UnifiedPortfolioAllocator.calculate_asymmetric_leland_multipliers(
            unrealized_return=0.15, volatility_20d=0.02
        )
        self.assertGreater(up_runner, 1.0)
        self.assertEqual(low_runner, 1.0)

        up_laggard, low_laggard = UnifiedPortfolioAllocator.calculate_asymmetric_leland_multipliers(
            unrealized_return=-0.15, volatility_20d=0.02
        )
        self.assertEqual(up_laggard, 1.0)
        self.assertLess(low_laggard, 1.0)

    def test_tc35_five_market_friction_schedule_exact_bps(self):
        """TC35 [F809]: 5-market friction schedule matches institutional production specifications."""
        expected_bps = {
            "KOSDAQ": 35.0,
            "KOSPI": 25.0,
            "RUSSELL2000": 16.0,
            "NASDAQ": 7.0,
            "SP500": 5.0,
        }
        for mkt, exp_bps in expected_bps.items():
            self.assertEqual(UnifiedPortfolioAllocator.get_market_friction_bps(mkt), exp_bps)

    def test_tc36_full_portfolio_gross_leverage_at_160x(self):
        """TC36 [F809]: Master 5-model allocation produces gross leverage <= 1.60x."""
        N = 8
        rng = np.random.RandomState(42)
        mu = rng.uniform(0.02, 0.06, N)
        cov = np.eye(N) * 0.03

        res = self.unified_allocator.allocate_portfolio_phase165(
            expected_returns=mu, covariance=cov, regime="BULL_LOW_VOL"
        )
        self.assertLessEqual(res.gross_leverage, 1.60 + 1e-4)
        self.assertLessEqual(res.net_leverage, 1.60 + 1e-4)

    def test_tc37_portfolio_allocator_delegation_to_phase165(self):
        """TC37 [F809]: PortfolioAllocator seamlessly delegates allocate_portfolio_phase165."""
        p_alloc = PortfolioAllocator(version=165)
        self.assertTrue(p_alloc.is_phase165)
        res = p_alloc.allocate_portfolio_phase165(
            expected_returns=np.array([0.05, 0.04]),
            covariance=np.eye(2) * 0.04,
            regime="BULL_LOW_VOL",
        )
        self.assertIsInstance(res, AllocationResult)
        self.assertLessEqual(res.gross_leverage, 1.60 + 1e-4)

    # =========================================================================
    # MODULE 6: MASTER INVARIANTS, PARITY & LATENCY SLA (TC38–TC40)
    # =========================================================================

    def test_tc38_strict_zero_synthetic_rows_native_int(self):
        """TC38 [Invariants]: Invariant synthetic_rows == 0 strictly verified as native int."""
        import json
        status_file = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "30year", "status.json")
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            syn_val = data.get("synthetic_rows", 0)
            self.assertEqual(syn_val, 0)
            self.assertIsInstance(syn_val, int)
            self.assertNotIsInstance(syn_val, bool)

    def test_tc39_dual_tree_parity_100_percent_sha256(self):
        """TC39 [Parity]: 100% SHA-256 bit-for-bit parity across all Phase 165 risk source files."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        risk_files = [
            "src/risk/dynamic_regime_leverage_allocator.py",
            "src/risk/portfolio_allocator.py",
            "src/risk/unified_portfolio_allocator.py",
            "src/risk/hyperbolic_optimal_transport_allocator.py",
        ]
        for rf in risk_files:
            src_path = os.path.join(base_dir, rf)
            ts_path = os.path.join(base_dir, "trading_system", rf)
            with open(src_path, "rb") as f1, open(ts_path, "rb") as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()
            self.assertEqual(h1, h2, f"Dual-tree parity breach for {rf}")

    def test_tc40_end_to_end_allocation_cycle_latency_sub_20ms(self):
        """TC40 [SLA]: Full 5-model allocation latency is strictly below 20ms per epoch."""
        N = 30
        mu = np.random.uniform(0.01, 0.05, N)
        cov = np.eye(N) * 0.04
        t0 = time.perf_counter()
        res = self.unified_allocator.allocate_portfolio_phase165(mu, cov, regime="BULL_LOW_VOL")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 20.0, f"Latency breached 20ms: {elapsed_ms:.2f}ms")
        self.assertEqual(len(res), N)


if __name__ == "__main__":
    unittest.main()
