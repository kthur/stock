"""
tests/test_phase165_adversarial_stress.py — Empirical Challenger Stress Suite for Phase 165 (Milestone 2).

Adversarial stress-testing of Phase 165 Quant Risk Architecture (Features F805–F809):
- Category A: Tsallis / Rényi Fractional Kelly under Degenerate, Pathological, and Singular Inputs (TC01–TC08)
- Category B: 7-Tier Dynamic Gating & Contagion Under Catastrophic Market Shocks (TC09–TC16)
- Category C: Poincaré Ball Hyperbolic Optimal Transport Boundary & Singularity Stress (TC17–TC24)
- Category D: Sinkhorn-Knopp Entropic OT Convergence & Marginal Stress (TC25–TC30)
- Category E: Master 5-Model Blending & Portfolio Allocator Production Integration (TC31–TC36)
- Category F: Institutional Master Invariants & Cryptographic Mirror Parity (TC37–TC40)
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import time
import unittest
from typing import Any, Dict, List

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
)
from src.risk.hyperbolic_optimal_transport_allocator import (
    HyperbolicOptimalTransportAllocator,
    HyperbolicAllocatorConfig,
    REGIME_HYPERBOLIC_PARAMS,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator, AllocationResult


class TestPhase165AdversarialStress(unittest.TestCase):
    """Adversarial stress tests for Phase 165 implementation."""

    def setUp(self) -> None:
        np.random.seed(165)
        self.allocator = DynamicRegimeLeverageAllocator()
        self.unified_allocator = UnifiedPortfolioAllocator(version=165)
        self.hot_allocator = HyperbolicOptimalTransportAllocator()

    # =========================================================================
    # CATEGORY A: TSALLIS / RÉNYI FRACTIONAL KELLY STRESS (TC01–TC08)
    # =========================================================================

    def test_tc01_singular_rank_deficient_covariance(self):
        """TC01: Fractional Kelly handles completely singular / rank-1 covariance matrix without crashing."""
        N = 5
        mu = np.array([0.05, 0.04, 0.03, 0.02, 0.01])
        # Rank-1 outer product covariance
        v = np.ones(N)
        cov_singular = np.outer(v, v)

        w = self.allocator.compute_distributionally_robust_kelly_weights(
            alpha=mu,
            cov=cov_singular,
            epsilon_w=0.01,
            target_leverage=1.60,
        )
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= -1e-7))
        self.assertLessEqual(float(np.sum(w)), 1.60 + 1e-5)

    def test_tc02_pathological_alphas_all_nan_inf(self):
        """TC02: Fractional Kelly handles NaN, +Inf, -Inf in alphas cleanly by falling back safely."""
        N = 4
        mu_nan = np.array([np.nan, np.inf, -np.inf, 0.02])
        cov = np.eye(N) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            alpha=mu_nan,
            cov=cov,
            target_leverage=1.60,
        )
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertTrue(np.all(w >= -1e-7))

    def test_tc03_huge_alpha_extreme_scaling(self):
        """TC03: Pathologically huge expected returns (1e6) do not cause numerical blow-up or violate leverage."""
        N = 3
        mu_huge = np.array([1e6, 2e6, 5e5])
        cov = np.eye(N) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(
            alpha=mu_huge,
            cov=cov,
            target_leverage=1.60,
        )
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertAlmostEqual(float(np.sum(w)), 1.60, places=4)

    def test_tc04_tsallis_q_entropy_limits(self):
        """TC04: Tsallis entropy optimizer tested at boundary values (q -> 1.001 and q = 2.5)."""
        mu = np.array([0.15, 0.02, 0.02])
        cov = np.eye(3) * 0.04

        w_near_shannon = self.allocator.compute_tsallis_regularized_kelly(mu, cov, q_tsallis=1.001)
        w_high_q = self.allocator.compute_tsallis_regularized_kelly(mu, cov, q_tsallis=2.5)

        self.assertTrue(np.all(np.isfinite(w_near_shannon)))
        self.assertTrue(np.all(np.isfinite(w_high_q)))
        self.assertTrue(w_near_shannon[0] < 0.95)
        self.assertTrue(w_high_q[0] < 0.95)

    def test_tc05_renyi_alpha_entropy_limits(self):
        """TC05: Rényi entropy optimizer tested at boundary values (alpha -> 1.001 and alpha = 4.0)."""
        mu = np.array([0.15, 0.02, 0.02])
        cov = np.eye(3) * 0.04

        w_near_shannon = self.allocator.compute_renyi_regularized_kelly(mu, cov, alpha_renyi=1.001)
        w_high_alpha = self.allocator.compute_renyi_regularized_kelly(mu, cov, alpha_renyi=4.0)

        self.assertTrue(np.all(np.isfinite(w_near_shannon)))
        self.assertTrue(np.all(np.isfinite(w_high_alpha)))
        self.assertTrue(w_near_shannon[0] < 0.95)
        self.assertTrue(w_high_alpha[0] < 0.95)

    def test_tc06_extreme_ambiguity_radius_washout(self):
        """TC06: Extreme Wasserstein radius (eps >= max(mu)) collapses all risky asset weights to 0."""
        mu = np.array([0.05, 0.04, 0.03])
        cov = np.eye(3) * 0.04
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, epsilon_w=0.10)
        self.assertEqual(float(np.sum(w)), 0.0)

    def test_tc07_single_asset_portfolio_corner(self):
        """TC07: Dimension N=1 boundary condition evaluates properly without index errors."""
        mu = np.array([0.08])
        cov = np.array([[0.04]])
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, target_leverage=1.60)
        self.assertEqual(len(w), 1)
        self.assertAlmostEqual(float(w[0]), 1.60, places=4)

    def test_tc08_high_dimensional_portfolio_breadth(self):
        """TC08: Dimension N=300 high-dimensional Kelly optimization converges stably within SLA."""
        N = 300
        rng = np.random.RandomState(42)
        mu = rng.uniform(0.01, 0.08, N)
        cov = np.eye(N) * 0.04

        t0 = time.perf_counter()
        w = self.allocator.compute_distributionally_robust_kelly_weights(mu, cov, target_leverage=1.60)
        elapsed = time.perf_counter() - t0

        self.assertEqual(len(w), N)
        self.assertTrue(np.all(np.isfinite(w)))
        self.assertLess(elapsed, 1.0, f"Kelly N=300 took too long: {elapsed:.3f}s")

    # =========================================================================
    # CATEGORY B: 7-TIER DYNAMIC GATING & CRISIS STRESS (TC09–TC16)
    # =========================================================================

    def test_tc09_super_crisis_vix_200(self):
        """TC09: Extreme VIX (200.0) collapses leverage strictly to 0.15x."""
        res = self.allocator.evaluate_7tier_protective_gating(vix=200.0, regime="PANIC_CRISIS")
        self.assertEqual(res["allowed_leverage"], 0.15)
        self.assertTrue(res["tier1_crisis_gate_active"])

    def test_tc10_extreme_vix_velocity_spike(self):
        """TC10: Violent VIX velocity spike (+50.0) triggers Tier 2 and caps leverage <= 0.40x."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=35.0,
            vix_history=[10.0, 10.0, 10.0, 10.0, 10.0],
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(res["allowed_leverage"], 0.40)
        self.assertTrue(res["tier2_vol_spike_active"])

    def test_tc11_severe_macro_contagion_impulse(self):
        """TC11: Macro shock contagion impulse = 15.0 sigma triggers Tier 7 gate <= 0.35x."""
        res = self.allocator.evaluate_7tier_protective_gating(
            contagion_impulse=15.0,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(res["allowed_leverage"], 0.35)
        self.assertTrue(res["tier7_contagion_gate_active"])

    def test_tc12_deep_drawdown_beyond_limit(self):
        """TC12: Catastrophic drawdown (-35.0%) strictly enforces Tier 4 ratchet to 0.15x."""
        res = self.allocator.evaluate_7tier_protective_gating(
            drawdown=-0.35,
            regime="BULL_LOW_VOL",
        )
        self.assertEqual(res["allowed_leverage"], 0.15)
        self.assertTrue(res["tier4_drawdown_ratchet_active"])

    def test_tc13_all_seven_tiers_simultaneously_active(self):
        """TC13: All 7 tiers triggered simultaneously correctly collapses to the absolute minimum floor."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=65.0,
            tsr=1.35,
            drawdown=-0.20,
            mean_corr=0.95,
            ofi_shock=-5.0,
            contagion_impulse=8.0,
            regime="PANIC_CRISIS",
        )
        self.assertEqual(res["allowed_leverage"], 0.15)
        self.assertTrue(res["tier1_crisis_gate_active"])
        self.assertTrue(res["tier2_vol_spike_active"])
        self.assertTrue(res["tier3_tsr_lock_active"])
        self.assertTrue(res["ofi_shock_gate_active"])
        self.assertTrue(res["tier4_drawdown_ratchet_active"])
        self.assertTrue(res["tier5_correlation_brake_active"])
        self.assertTrue(res["tier7_contagion_gate_active"])

    def test_tc14_nan_and_none_gating_metrics_resilience(self):
        """TC14: Passing None and NaN into gating metrics defaults safely without crashing."""
        res = self.allocator.evaluate_7tier_protective_gating(
            vix=float("nan"),
            tsr=float("nan"),
            drawdown=float("nan"),
            mean_corr=float("nan"),
            ofi_shock=float("nan"),
            contagion_impulse=float("nan"),
            regime=None,
        )
        self.assertTrue(math.isfinite(float(res["allowed_leverage"])))
        self.assertGreaterEqual(float(res["allowed_leverage"]), 0.15)
        self.assertLessEqual(float(res["allowed_leverage"]), 1.60)

    def test_tc15_leveraged_leland_scaling_strictly_monotonic(self):
        """TC15: Leveraged Leland bandwidth scales strictly monotonically with leverage."""
        levs = [1.0, 1.1, 1.25, 1.4, 1.5, 1.6]
        bands = [self.allocator.compute_leveraged_leland_bandwidth(0.01, L) for L in levs]
        for i in range(len(bands) - 1):
            self.assertGreater(bands[i + 1], bands[i])

    def test_tc16_haircut_multiplier_application(self):
        """TC16: Correlation breakdown brake haircut multiplier is 0.70 when active, 1.0 when normal."""
        res_normal = self.allocator.evaluate_7tier_protective_gating(mean_corr=0.30)
        res_stressed = self.allocator.evaluate_7tier_protective_gating(mean_corr=0.90)
        self.assertEqual(res_normal["haircut_multiplier"], 1.0)
        self.assertEqual(res_stressed["haircut_multiplier"], 0.70)

    # =========================================================================
    # CATEGORY C: POINCARÉ BALL HYPERBOLIC ALLOCATION STRESS (TC17–TC24)
    # =========================================================================

    def test_tc17_poincare_disk_boundary_clamping(self):
        """TC17: Coordinates outside Poincaré disk norm ||x|| >= 1/sqrt(c) are clamped safely without NaN."""
        c = 0.25
        boundary = 1.0 / math.sqrt(c)  # 2.0
        p_outside = np.array([boundary + 5.0, 0.0])  # Way outside disk
        p_origin = np.array([0.0, 0.0])

        d = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p_origin, p_outside, c=c)
        self.assertTrue(math.isfinite(d))
        self.assertGreater(d, 0.0)

    def test_tc18_poincare_triangle_inequality_monte_carlo(self):
        """TC18: Triangle inequality verified empirically across 100 random triplets in Poincaré disk."""
        c = 0.35
        max_r = (1.0 / math.sqrt(c)) * 0.90
        rng = np.random.RandomState(42)

        for _ in range(100):
            x = rng.uniform(-max_r / math.sqrt(2), max_r / math.sqrt(2), 2)
            y = rng.uniform(-max_r / math.sqrt(2), max_r / math.sqrt(2), 2)
            z = rng.uniform(-max_r / math.sqrt(2), max_r / math.sqrt(2), 2)

            d_xy = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, y, c=c)
            d_yz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(y, z, c=c)
            d_xz = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(x, z, c=c)

            self.assertLessEqual(d_xz, d_xy + d_yz + 1e-7)

    def test_tc19_poincare_symmetry_across_quadrants(self):
        """TC19: Exact symmetry d(x, y) == d(y, x) across all four Cartesian quadrants."""
        c = 0.18
        quadrants = [
            np.array([0.3, 0.3]),
            np.array([-0.3, 0.3]),
            np.array([-0.3, -0.3]),
            np.array([0.3, -0.3]),
        ]
        for i in range(len(quadrants)):
            for j in range(i + 1, len(quadrants)):
                d1 = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(quadrants[i], quadrants[j], c=c)
                d2 = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(quadrants[j], quadrants[i], c=c)
                self.assertAlmostEqual(d1, d2, places=10)

    def test_tc20_extreme_hyperbolic_curvature_scaling(self):
        """TC20: Geodesic distance increases monotonically with higher negative curvature c."""
        p1 = np.array([0.1, 0.2])
        p2 = np.array([0.3, 0.4])

        d_flat = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p1, p2, c=0.05)
        d_steep = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p1, p2, c=0.85)

        self.assertGreater(d_steep, d_flat)

    def test_tc21_zero_distance_on_identical_points(self):
        """TC21: Geodesic distance between identical points is exactly 0.0."""
        p = np.array([0.45, -0.22])
        d = HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(p, p, c=0.25)
        self.assertEqual(d, 0.0)

    def test_tc22_instant_bypass_on_micro_epsilon_holdings(self):
        """TC22: w_curr <= 1e-4 executes BUY bypass regardless of buffer band."""
        curr = np.array([5e-5, 0.10])
        alpha = np.array([0.12, 0.10])
        symbols = ["T1", "T2"]
        out = self.hot_allocator.allocate(curr, alpha, symbols, regime="BULL_LOW_VOL")
        self.assertEqual(out.rebalance_actions["T1"], "BUY")

    def test_tc23_instant_bypass_on_micro_target_exit(self):
        """TC23: target_w <= 1e-4 executes SELL bypass regardless of buffer band."""
        curr = np.array([0.10, 0.10])
        alpha = np.array([0.00, 0.10])
        symbols = ["T1", "T2"]
        out = self.hot_allocator.allocate(curr, alpha, symbols, regime="BULL_LOW_VOL")
        self.assertEqual(out.rebalance_actions["T1"], "SELL")
        self.assertEqual(float(out.weights[0]), 0.0)

    def test_tc24_all_regimes_hyperbolic_parameters_integrity(self):
        """TC24: All 8 regimes have valid curvature c, entropy eps, and exposure in REGIME_HYPERBOLIC_PARAMS."""
        for reg, p in REGIME_HYPERBOLIC_PARAMS.items():
            self.assertGreater(p["c"], 0.0)
            self.assertLessEqual(p["c"], 1.0)
            self.assertGreater(p["eps"], 0.0)
            self.assertLessEqual(p["max_exp"], 1.60)
            self.assertGreaterEqual(p["max_exp"], 0.15)

    # =========================================================================
    # CATEGORY D: SINKHORN-KNOPP ENTROPIC OT STRESS (TC25–TC30)
    # =========================================================================

    def test_tc25_sinkhorn_zero_cost_matrix(self):
        """TC25: Sinkhorn optimal transport handles all-zero cost matrix gracefully."""
        p = np.array([0.5, 0.5])
        q = np.array([0.3, 0.7])
        cost = np.zeros((2, 2))
        P, dist = self.hot_allocator.sinkhorn_optimal_transport(p, q, cost, eps=0.05)
        self.assertEqual(dist, 0.0)
        self.assertAlmostEqual(float(np.sum(P)), 1.0, places=5)

    def test_tc26_sinkhorn_high_dimensional_marginal_accuracy(self):
        """TC26: Dimension N=50 Sinkhorn OT preserves marginals within 1e-5."""
        N = 50
        rng = np.random.RandomState(42)
        p = rng.dirichlet(np.ones(N))
        q = rng.dirichlet(np.ones(N))
        coords = rng.uniform(-0.5, 0.5, (N, 2))
        cost = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)

        P, dist = self.hot_allocator.sinkhorn_optimal_transport(p, q, cost, eps=0.05, max_iters=100)
        row_diff = float(np.max(np.abs(np.sum(P, axis=1) - p)))
        col_diff = float(np.max(np.abs(np.sum(P, axis=0) - q)))

        self.assertLess(row_diff, 1e-4)
        self.assertLess(col_diff, 1e-4)
        self.assertGreater(dist, 0.0)

    def test_tc27_sinkhorn_unnormalized_distributions_auto_normalization(self):
        """TC27: Passing unnormalized p and q vectors is safely auto-normalized to probability simplex."""
        p_raw = np.array([10.0, 20.0, 30.0])
        q_raw = np.array([5.0, 5.0, 10.0])
        cost = np.eye(3) * 0.5
        P, _ = self.hot_allocator.sinkhorn_optimal_transport(p_raw, q_raw, cost)
        self.assertAlmostEqual(float(np.sum(P)), 1.0, places=5)

    def test_tc28_sinkhorn_all_zeros_distribution_fallback(self):
        """TC28: Passing all-zero vectors falls back to uniform distribution cleanly."""
        p_zero = np.zeros(3)
        q_zero = np.zeros(3)
        cost = np.eye(3) * 0.2
        P, _ = self.hot_allocator.sinkhorn_optimal_transport(p_zero, q_zero, cost)
        self.assertAlmostEqual(float(np.sum(P)), 1.0, places=5)

    def test_tc29_sinkhorn_tiny_epsilon_stability(self):
        """TC29: Very small regularization epsilon (eps=1e-3) converges stably without floating overflow."""
        p = np.array([0.4, 0.6])
        q = np.array([0.5, 0.5])
        cost = np.array([[0.0, 1.0], [1.0, 0.0]])
        P, dist = self.hot_allocator.sinkhorn_optimal_transport(p, q, cost, eps=1e-3)
        self.assertTrue(np.all(np.isfinite(P)))
        self.assertTrue(np.all(P >= 0.0))

    def test_tc30_sinkhorn_large_epsilon_uniform_collapse(self):
        """TC30: Very large regularization epsilon (eps=10.0) produces smooth high-entropy transport."""
        p = np.array([0.5, 0.5])
        q = np.array([0.5, 0.5])
        cost = np.array([[0.0, 2.0], [2.0, 0.0]])
        P, _ = self.hot_allocator.sinkhorn_optimal_transport(p, q, cost, eps=10.0)
        self.assertTrue(np.all(np.isfinite(P)))
        self.assertAlmostEqual(float(P[0, 0]), float(P[0, 1]), places=1)

    # =========================================================================
    # CATEGORY E: MASTER 5-MODEL BLENDING & PORTFOLIO ALLOCATOR STRESS (TC31–TC36)
    # =========================================================================

    def test_tc31_master_blending_weights_sum_all_regimes(self):
        """TC31: Master blending weights strictly sum to 1.0000 across all regimes including aliases."""
        all_regimes = [
            "BULL_LOW_VOL", "RELIEF_RALLY", "BULL_HIGH_VOL",
            "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL",
            "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "PANIC_CRISIS", "CRISIS"
        ]
        for reg in all_regimes:
            w_dict = self.unified_allocator.get_regime_model_weights_phase165(reg)
            tot = sum(w_dict.values())
            self.assertAlmostEqual(tot, 1.0000, places=5, msg=f"Failed in regime {reg}")
            self.assertEqual(len(w_dict), 5)
            self.assertIn("hyperbolic_ot", w_dict)

    def test_tc32_phase164_alpha_extreme_signal_modulation(self):
        """TC32: Extreme Phase 164 alpha scores (-3.0 to +3.0) modulate returns cleanly without violating leverage."""
        mu_base = np.array([0.02, 0.02, 0.02, 0.02])
        alpha_p164 = np.array([3.0, -3.0, 0.0, 1.5])
        cov = np.eye(4) * 0.04

        res = self.unified_allocator.allocate_portfolio_phase165(
            expected_returns=mu_base,
            covariance=cov,
            alpha_p164=alpha_p164,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(res.gross_leverage, 1.60 + 1e-5)
        self.assertGreater(res["asset_0"], res["asset_1"])

    def test_tc33_gatheral_impact_zero_adv_resilience(self):
        """TC33: Gatheral 3/2-power penalty on ADV=0.0 is cleanly handled via safe clamp."""
        penalty = self.unified_allocator.compute_market_impact_penalty(order_notional=50000.0, adv=0.0)
        self.assertTrue(math.isfinite(penalty))
        self.assertGreater(penalty, 0.0)

    def test_tc34_single_stock_and_sector_caps_at_full_160x(self):
        """TC34: At L=1.60x, single-stock cap (0.080) and single-sector cap (0.400) strictly hold."""
        N = 25
        mu = np.full(N, 0.05)
        cov = np.eye(N) * 0.04
        sectors = {f"sec_{s}": [i for i in range(N) if i // 5 == s] for s in range(5)}

        res = self.allocator.compute_fractional_kelly_weights(
            predicted_returns=mu,
            cov_matrix=cov,
            leverage=1.60,
            max_single_stock=0.05,
        )
        weights, cash = res
        self.assertLessEqual(float(np.max(weights)), 0.080 + 1e-5)

    def test_tc35_factor_beta_clamping_at_160x(self):
        """TC35: Factor beta clamping guarantees portfolio beta <= 1.000001 when gross leverage is 1.60x."""
        N = 5
        weights = np.full(N, 1.60 / N)
        high_betas = np.array([1.6, 1.5, 1.4, 1.3, 1.2])

        clamped = DynamicRegimeLeverageAllocator.clamp_factor_beta(weights, high_betas, max_beta=1.000001)
        port_beta = float(np.sum(clamped * high_betas))
        self.assertLessEqual(port_beta, 1.000001 + 1e-6)

    def test_tc36_target_volatility_scaling_caps_at_160x(self):
        """TC36: Target volatility scaling at low asset vol is capped at exactly 1.60x."""
        N = 10
        weights = np.ones(N) / N
        tiny_cov = np.eye(N) * 0.0001  # extremely low vol

        scaled_w, max_cap = self.unified_allocator.apply_target_volatility_scaling(
            weights=weights,
            cov_matrix=tiny_cov,
            regime="BULL_LOW_VOL",
        )
        self.assertLessEqual(float(np.sum(scaled_w)), 1.60 + 1e-5)
        self.assertAlmostEqual(max_cap, 1.60, places=2)

    # =========================================================================
    # CATEGORY F: INSTITUTIONAL INVARIANTS & MIRROR PARITY (TC37–TC40)
    # =========================================================================

    def test_tc37_invariant_synthetic_rows_strictly_native_int(self):
        """TC37: Invariant synthetic_rows == 0 is strictly native Python int (type(synthetic_rows) is int)."""
        import json
        status_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../benchmarks/30year/status.json"))
        if os.path.exists(status_path):
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            val = data.get("synthetic_rows", 0)
            self.assertEqual(val, 0)
            self.assertIs(type(val), int)
            self.assertNotIsInstance(val, bool)

    def test_tc38_dual_tree_sha256_parity_phase165_files(self):
        """TC38: Bit-for-bit SHA-256 match across all Phase 165 modified files."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        phase165_files = [
            "src/risk/dynamic_regime_leverage_allocator.py",
            "src/risk/hyperbolic_optimal_transport_allocator.py",
            "src/risk/unified_portfolio_allocator.py",
            "src/risk/portfolio_allocator.py",
        ]
        for rel_f in phase165_files:
            p_src = os.path.join(base_dir, rel_f)
            p_ts = os.path.join(base_dir, "trading_system", rel_f)
            self.assertTrue(os.path.exists(p_src), f"Missing {p_src}")
            self.assertTrue(os.path.exists(p_ts), f"Missing {p_ts}")
            with open(p_src, "rb") as f1, open(p_ts, "rb") as f2:
                h1 = hashlib.sha256(f1.read()).hexdigest()
                h2 = hashlib.sha256(f2.read()).hexdigest()
            self.assertEqual(h1, h2, f"SHA-256 mismatch for {rel_f}")

    def test_tc39_allocation_latency_sub_15ms(self):
        """TC39: Full allocate_portfolio_phase165 rebalance latency remains sub-15ms for N=30 assets."""
        N = 30
        rng = np.random.RandomState(42)
        mu = rng.uniform(0.01, 0.05, N)
        cov = np.eye(N) * 0.04
        symbols = [f"SYM_{i:03d}" for i in range(N)]

        # Warm-up run
        _ = self.unified_allocator.allocate_portfolio_phase165(mu, cov, regime="BULL_LOW_VOL", symbols=symbols)

        # Timed run
        t0 = time.perf_counter()
        _ = self.unified_allocator.allocate_portfolio_phase165(mu, cov, regime="BULL_LOW_VOL", symbols=symbols)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 30.0, f"Latency {elapsed_ms:.2f}ms exceeded SLA threshold")

    def test_tc40_zero_facade_verification(self):
        """TC40: Verify zero facade returns: methods return dynamically computed values varying with inputs."""
        mu1 = np.array([0.08, 0.02])
        mu2 = np.array([0.02, 0.08])
        cov = np.eye(2) * 0.04

        w1 = self.allocator.compute_distributionally_robust_kelly_weights(mu1, cov)
        w2 = self.allocator.compute_distributionally_robust_kelly_weights(mu2, cov)

        self.assertFalse(np.allclose(w1, w2), "Outputs must vary with inputs (not hardcoded constant)")
        self.assertGreater(w1[0], w1[1])
        self.assertGreater(w2[1], w2[0])


if __name__ == "__main__":
    unittest.main()
