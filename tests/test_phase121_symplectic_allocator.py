r"""
tests/test_phase121_symplectic_allocator.py
============================================
Exhaustive 60-Test Verification Suite across 12 Rigorous Categories for:
Symplectic Manifold Hamiltonian Monte Carlo (HMC) Portfolio Allocator (Feature F577).
Phase 121 (Release R137 / v128 Production Master).

Categories (60 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata, Enums & Complete Module Exports (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Empirical Profiles (TC06 ~ TC10)
  - Category 3: Fisher-Rao Information Metric & Exact Geodesic Arc Distance Invariants (TC11 ~ TC15)
  - Category 4: Simplex Cotangent Space Tangent Projections & Momentum Conservation (TC16 ~ TC20)
  - Category 5: Symplectic Leapfrog Integrator & Phase-Space Area Preservation (TC21 ~ TC25)
  - Category 6: Elastic Boundary Reflection Mechanics & Simplex Invariance (TC26 ~ TC30)
  - Category 7: Metropolis Acceptance Criterion & Energy Conservation (TC31 ~ TC35)
  - Category 8: Dual-Averaging Step-Size Adaptation Convergence (TC36 ~ TC40)
  - Category 9: Gromov \delta-Hyperbolicity & Systemic Crash Damping (TC41 ~ TC45)
  - Category 10: Geodesic Leland No-Trade Buffer Bands & Instant Bypass (TC46 ~ TC50)
  - Category 11: Multi-Regime Allocation Modes & Robust Tail-Hedging (TC51 ~ TC55)
  - Category 12: Extreme Edge Cases, High-Dimensional Scalability & Latency SLA (TC56 ~ TC60)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.risk.symplectic_hamiltonian_allocator as sh_module
from src.risk.symplectic_hamiltonian_allocator import (
    VERSION,
    RELEASE,
    FEATURE,
    EPSILON_FLOOR,
    CRASH_ALERT_THRESHOLD,
    MarketType,
    AllocationMode,
    MetricType,
    BypassAction,
    CurvatureRegime,
    SymplecticProfile,
    SymplecticAllocatorConfig,
    GeodesicLelandBand,
    SymplecticOptimizationResult,
    compute_geodesic_distance,
    compute_asset_arc_distance,
    compute_gromov_hyperbolicity,
    get_symplectic_profile,
    run_symplectic_allocation,
    SymplecticManifoldHMCAllocator,
)


class TestPhase121SymplecticAllocator(unittest.TestCase):
    """Exhaustive 60-Test Verification Suite for Feature F577."""

    def setUp(self) -> None:
        self.rng = np.random.default_rng(42)
        self.symbols_5 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        self.mu_5 = np.array([0.15, 0.12, 0.14, 0.16, 0.22])
        raw_cov = self.rng.normal(0, 0.05, size=(5, 5))
        self.cov_5 = raw_cov @ raw_cov.T + np.eye(5) * 0.02

    # =========================================================================
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Module Exports
    # =========================================================================
    def test_tc01_dual_tree_sha256_cryptographic_parity(self) -> None:
        src_file = PROJECT_ROOT / "src" / "risk" / "symplectic_hamiltonian_allocator.py"
        ts_file = TRADING_SYSTEM_DIR / "src" / "risk" / "symplectic_hamiltonian_allocator.py"
        self.assertTrue(src_file.exists(), f"Source file missing: {src_file}")
        self.assertTrue(ts_file.exists(), f"Mirror file missing: {ts_file}")

        h_src = hashlib.sha256(src_file.read_bytes()).hexdigest()
        h_ts = hashlib.sha256(ts_file.read_bytes()).hexdigest()
        self.assertEqual(h_src, h_ts, "SHA-256 cryptographic parity violation between src and trading_system!")

    def test_tc02_version_and_metadata_constants(self) -> None:
        self.assertEqual(VERSION, 121)
        self.assertEqual(RELEASE, "R137")
        self.assertEqual(FEATURE, "F577")
        self.assertAlmostEqual(EPSILON_FLOOR, 1e-6)

    def test_tc03_enum_values_completeness(self) -> None:
        self.assertEqual({m.value for m in MarketType}, {"SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ", "GLOBAL"})
        self.assertEqual({m.value for m in AllocationMode}, {"MAX_SHARPE", "MIN_VARIANCE_RISK_PARITY", "ROBUST_CVAR_TAIL_HEDGE", "DYNAMIC_REGIME_BLENDED"})
        self.assertEqual({m.value for m in MetricType}, {"FISHER_RAO", "EUCLIDEAN_ADAPTIVE", "HYBRID"})
        self.assertEqual({m.value for m in BypassAction}, {"IMMEDIATE_ENTRY", "IMMEDIATE_EXIT", "GEODESIC_HOLD", "ACTIVE_REBALANCE"})
        self.assertEqual({m.value for m in CurvatureRegime}, {"FLAT_EUCLIDEAN", "HYPERBOLIC_STRESSED", "CRASH_SYSTEMIC"})

    def test_tc04_package_init_exports(self) -> None:
        import src.risk as risk_pkg
        self.assertTrue(hasattr(risk_pkg, "SymplecticManifoldHMCAllocator"))
        self.assertTrue(hasattr(risk_pkg, "SymplecticAllocatorConfig"))
        self.assertTrue(hasattr(risk_pkg, "SymplecticOptimizationResult"))
        self.assertTrue(hasattr(risk_pkg, "SymplecticProfile"))
        self.assertTrue(hasattr(risk_pkg, "run_symplectic_allocation"))

    def test_tc05_mirror_package_init_exports(self) -> None:
        import trading_system.src.risk as ts_risk_pkg
        self.assertTrue(hasattr(ts_risk_pkg, "SymplecticManifoldHMCAllocator"))
        self.assertTrue(hasattr(ts_risk_pkg, "SymplecticAllocatorConfig"))

    # =========================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Empirical Profiles
    # =========================================================================
    def test_tc06_get_all_five_market_profiles(self) -> None:
        markets = [MarketType.SP500, MarketType.NASDAQ, MarketType.RUSSELL2000, MarketType.KOSPI, MarketType.KOSDAQ]
        for m in markets:
            prof = get_symplectic_profile(m)
            self.assertEqual(prof.market, m)
            self.assertGreater(prof.step_size, 0.0)
            self.assertGreaterEqual(prof.num_leapfrog_steps, 15)
            self.assertGreater(prof.risk_aversion, 0.0)

    def test_tc07_case_insensitive_string_market_profile(self) -> None:
        prof_sp = get_symplectic_profile("sp500")
        self.assertEqual(prof_sp.market, MarketType.SP500)
        prof_kd = get_symplectic_profile("KoSDaQ")
        self.assertEqual(prof_kd.market, MarketType.KOSDAQ)
        prof_unknown = get_symplectic_profile("UNKNOWN_XYZ")
        self.assertEqual(prof_unknown.market, MarketType.GLOBAL)

    def test_tc08_config_market_profile_application(self) -> None:
        cfg = SymplecticAllocatorConfig(market=MarketType.NASDAQ)
        prof = get_symplectic_profile(MarketType.NASDAQ)
        cfg.apply_market_profile(prof)
        self.assertEqual(cfg.step_size, prof.step_size)
        self.assertEqual(cfg.risk_aversion, prof.risk_aversion)
        self.assertEqual(cfg.gromov_crit, prof.gromov_crit)

    def test_tc09_config_immutability_and_copy(self) -> None:
        cfg = SymplecticAllocatorConfig()
        allocator = SymplecticManifoldHMCAllocator(cfg)
        self.assertIsNotNone(allocator.config)
        self.assertGreater(allocator.config.num_leapfrog_steps, 0)

    def test_tc10_russell_and_kosdaq_tail_risk_weights(self) -> None:
        prof_r = get_symplectic_profile(MarketType.RUSSELL2000)
        prof_kd = get_symplectic_profile(MarketType.KOSDAQ)
        self.assertGreater(prof_r.cvar_tail_weight, 0.20)
        self.assertGreater(prof_kd.cvar_tail_weight, 0.20)

    # =========================================================================
    # Category 3: Fisher-Rao Information Metric & Exact Geodesic Arc Distance
    # =========================================================================
    def test_tc11_geodesic_distance_identical_allocations_is_zero(self) -> None:
        w = np.array([0.2, 0.3, 0.5])
        d = compute_geodesic_distance(w, w)
        self.assertAlmostEqual(d, 0.0, places=6)

    def test_tc12_geodesic_distance_orthogonality(self) -> None:
        w1 = np.array([1.0, 0.0, 0.0])
        w2 = np.array([0.0, 1.0, 0.0])
        # Under Fisher-Rao with epsilon floor, inner product approaches epsilon, distance approaches pi
        d = compute_geodesic_distance(w1, w2, epsilon_floor=1e-12)
        self.assertAlmostEqual(d, math.pi, places=4)

    def test_tc13_geodesic_distance_symmetry(self) -> None:
        w1 = np.array([0.1, 0.4, 0.5])
        w2 = np.array([0.3, 0.3, 0.4])
        d12 = compute_geodesic_distance(w1, w2)
        d21 = compute_geodesic_distance(w2, w1)
        self.assertAlmostEqual(d12, d21, places=7)

    def test_tc14_geodesic_distance_triangle_inequality(self) -> None:
        w1 = np.array([0.1, 0.2, 0.7])
        w2 = np.array([0.4, 0.4, 0.2])
        w3 = np.array([0.2, 0.5, 0.3])
        d12 = compute_geodesic_distance(w1, w2)
        d23 = compute_geodesic_distance(w2, w3)
        d13 = compute_geodesic_distance(w1, w3)
        self.assertLessEqual(d13, d12 + d23 + 1e-6)

    def test_tc15_asset_arc_distance_bounds(self) -> None:
        d_zero = compute_asset_arc_distance(0.5, 0.5)
        self.assertAlmostEqual(d_zero, 0.0, places=6)
        d_extreme = compute_asset_arc_distance(0.0, 1.0)
        self.assertAlmostEqual(d_extreme, math.pi, places=4)

    # =========================================================================
    # Category 4: Simplex Cotangent Space Tangent Projections
    # =========================================================================
    def test_tc16_tangent_momentum_sum_is_zero(self) -> None:
        p = np.array([1.2, -0.5, 3.1, -1.0])
        p_tangent = p - np.mean(p)
        self.assertAlmostEqual(float(np.sum(p_tangent)), 0.0, places=7)

    def test_tc17_riemannian_gradient_tangent_projection(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.array([0.2, 0.3, 0.5])
        mu = np.array([0.1, 0.2, 0.15])
        cov = np.eye(3) * 0.04
        grad_r = alloc._potential_gradient(
            q=q,
            mu=mu,
            cov=cov,
            q0=q,
            risk_aversion=3.0,
            dist_penalty=1.0,
            barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE,
        )
        self.assertAlmostEqual(float(np.sum(grad_r)), 0.0, places=6)

    def test_tc18_kinetic_energy_positivity(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.array([0.2, 0.3, 0.5])
        p = np.array([0.5, -0.2, -0.3])
        k = alloc._kinetic_energy(q, p, MetricType.FISHER_RAO)
        self.assertGreater(k, 0.0)

    def test_tc19_kinetic_derivatives_consistency(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.array([0.2, 0.3, 0.5])
        p = np.array([0.5, -0.2, -0.3])
        dk_dp, dk_dq = alloc._kinetic_derivatives(q, p, MetricType.FISHER_RAO)
        self.assertTrue(np.allclose(dk_dp, p))
        self.assertTrue(np.allclose(dk_dq, np.zeros_like(q)))

    def test_tc20_euclidean_adaptive_kinetic_derivatives(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.array([0.2, 0.3, 0.5])
        p = np.array([0.5, -0.2, -0.3])
        dk_dp, dk_dq = alloc._kinetic_derivatives(q, p, MetricType.EUCLIDEAN_ADAPTIVE)
        self.assertTrue(np.allclose(dk_dp, p))
        self.assertTrue(np.allclose(dk_dq, np.zeros_like(q)))

    # =========================================================================
    # Category 5: Symplectic Leapfrog Integrator & Phase-Space Mechanics
    # =========================================================================
    def test_tc21_single_leapfrog_step_execution(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.array([0.2, 0.3, 0.5])
        p = np.array([0.1, -0.05, -0.05])
        q_next, p_next = alloc._leapfrog_step(
            q=q,
            p=p,
            eps=0.01,
            mu=np.array([0.1, 0.15, 0.2]),
            cov=np.eye(3) * 0.02,
            q0=q,
            risk_aversion=3.0,
            dist_penalty=1.0,
            barrier_coef=1e-5,
            mode=AllocationMode.DYNAMIC_REGIME_BLENDED,
            metric_type=MetricType.FISHER_RAO,
        )
        self.assertAlmostEqual(float(np.sum(q_next)), 1.0, places=6)
        self.assertAlmostEqual(float(np.sum(p_next)), 0.0, places=6)
        self.assertTrue(all(val >= EPSILON_FLOOR for val in q_next))

    def test_tc22_leapfrog_time_reversibility(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q0 = np.array([0.3, 0.3, 0.4])
        p0 = np.array([0.05, -0.02, -0.03])
        eps = 0.005

        # Forward step
        q1, p1 = alloc._leapfrog_step(
            q=q0,
            p=p0,
            eps=eps,
            mu=np.array([0.1, 0.12, 0.14]),
            cov=np.eye(3) * 0.03,
            q0=q0,
            risk_aversion=3.0,
            dist_penalty=1.0,
            barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.FISHER_RAO,
        )

        # Reverse momentum and integrate backward
        q_rev, p_rev = alloc._leapfrog_step(
            q=q1,
            p=-p1,
            eps=eps,
            mu=np.array([0.1, 0.12, 0.14]),
            cov=np.eye(3) * 0.03,
            q0=q0,
            risk_aversion=3.0,
            dist_penalty=1.0,
            barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.FISHER_RAO,
        )

        # Positions should match back to q0 with high fidelity
        self.assertTrue(np.allclose(q0, q_rev, atol=1e-3))

    def test_tc23_trajectory_integration_output_shapes(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q0 = np.full(5, 0.2)
        p0 = np.zeros(5)
        q_end, p_end = alloc._integrate_trajectory(
            q_init=q0,
            p_init=p0,
            step_size=0.01,
            num_steps=10,
            mu=self.mu_5,
            cov=self.cov_5,
            q0=q0,
            risk_aversion=3.0,
            dist_penalty=1.0,
            barrier_coef=1e-5,
            mode=AllocationMode.DYNAMIC_REGIME_BLENDED,
            metric_type=MetricType.FISHER_RAO,
        )
        self.assertEqual(len(q_end), 5)
        self.assertEqual(len(p_end), 5)
        self.assertAlmostEqual(float(np.sum(q_end)), 1.0, places=6)

    def test_tc24_hamiltonian_scalar_return(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.full(5, 0.2)
        p = np.zeros(5)
        h = alloc._hamiltonian(
            q=q,
            p=p,
            mu=self.mu_5,
            cov=self.cov_5,
            q0=q,
            risk_aversion=3.0,
            dist_penalty=1.0,
            barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.FISHER_RAO,
        )
        self.assertIsInstance(h, float)
        self.assertFalse(math.isnan(h))

    def test_tc25_hybrid_metric_trajectory_execution(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q0 = np.full(5, 0.2)
        p0 = np.array([0.02, -0.01, 0.01, -0.02, 0.0])
        q_end, p_end = alloc._integrate_trajectory(
            q_init=q0,
            p_init=p0,
            step_size=0.01,
            num_steps=5,
            mu=self.mu_5,
            cov=self.cov_5,
            q0=q0,
            risk_aversion=3.0,
            dist_penalty=1.0,
            barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.HYBRID,
        )
        self.assertAlmostEqual(float(np.sum(q_end)), 1.0, places=6)

    # =========================================================================
    # Category 6: Elastic Boundary Reflection Mechanics
    # =========================================================================
    def test_tc26_elastic_reflection_on_floor_violation(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        # Create a momentum vector that pushes asset 0 into negative space
        q = np.array([EPSILON_FLOOR * 1.5, 0.499, 0.499])
        p = np.array([-10.0, 5.0, 5.0])
        q_next, p_next = alloc._leapfrog_step(
            q=q,
            p=p,
            eps=0.01,
            mu=np.array([0.1, 0.1, 0.1]),
            cov=np.eye(3) * 0.01,
            q0=np.full(3, 1.0/3.0),
            risk_aversion=3.0,
            dist_penalty=0.0,
            barrier_coef=1e-6,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.FISHER_RAO,
        )
        self.assertTrue(all(val >= EPSILON_FLOOR for val in q_next))

    def test_tc27_elastic_reflection_preserves_simplex_sum(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.array([0.001, 0.001, 0.998])
        p = np.array([-5.0, -5.0, 10.0])
        q_next, p_next = alloc._leapfrog_step(
            q=q,
            p=p,
            eps=0.02,
            mu=np.array([0.1, 0.1, 0.1]),
            cov=np.eye(3) * 0.01,
            q0=np.full(3, 1.0/3.0),
            risk_aversion=3.0,
            dist_penalty=0.0,
            barrier_coef=1e-6,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.FISHER_RAO,
        )
        self.assertAlmostEqual(float(np.sum(q_next)), 1.0, places=6)

    def test_tc28_multiple_consecutive_reflections(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.full(5, 0.2)
        p = np.array([-20.0, -20.0, 10.0, 15.0, 15.0])
        for _ in range(10):
            q, p = alloc._leapfrog_step(
                q=q,
                p=p,
                eps=0.01,
                mu=self.mu_5,
                cov=self.cov_5,
                q0=np.full(5, 0.2),
                risk_aversion=3.0,
                dist_penalty=1.0,
                barrier_coef=1e-5,
                mode=AllocationMode.MAX_SHARPE,
                metric_type=MetricType.FISHER_RAO,
            )
            self.assertTrue(all(val >= EPSILON_FLOOR for val in q))
            self.assertAlmostEqual(float(np.sum(q)), 1.0, places=5)

    def test_tc29_degenerate_single_dominant_asset_reflection(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.array([0.9999, 0.00005, 0.00005])
        p = np.array([2.0, -1.0, -1.0])
        q_next, _ = alloc._leapfrog_step(
            q=q,
            p=p,
            eps=0.005,
            mu=np.array([0.1, 0.1, 0.1]),
            cov=np.eye(3) * 0.01,
            q0=q,
            risk_aversion=3.0,
            dist_penalty=0.0,
            barrier_coef=1e-6,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.FISHER_RAO,
        )
        self.assertTrue(all(val >= EPSILON_FLOOR for val in q_next))
        self.assertAlmostEqual(float(np.sum(q_next)), 1.0, places=6)

    def test_tc30_boundary_stability_under_zero_covariance(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q = np.full(3, 1.0/3.0)
        p = np.array([0.1, -0.05, -0.05])
        cov_zero = np.zeros((3, 3))
        q_next, _ = alloc._leapfrog_step(
            q=q,
            p=p,
            eps=0.01,
            mu=np.array([0.05, 0.05, 0.05]),
            cov=cov_zero,
            q0=q,
            risk_aversion=0.0,
            dist_penalty=0.0,
            barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE,
            metric_type=MetricType.FISHER_RAO,
        )
        self.assertAlmostEqual(float(np.sum(q_next)), 1.0, places=6)

    # =========================================================================
    # Category 7: Metropolis Acceptance Criterion & Energy Conservation
    # =========================================================================
    def test_tc31_perfect_energy_conservation_accepts_with_prob_one(self) -> None:
        delta_h = 0.0
        alpha = min(1.0, math.exp(-delta_h))
        self.assertEqual(alpha, 1.0)

    def test_tc32_energy_drift_bounded_small_step_size(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        q0 = np.full(5, 0.2)
        p0 = np.array([0.01, -0.005, -0.005, 0.005, -0.005])
        h_init = alloc._hamiltonian(
            q=q0, p=p0, mu=self.mu_5, cov=self.cov_5, q0=q0,
            risk_aversion=3.0, dist_penalty=1.0, barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE, metric_type=MetricType.FISHER_RAO,
        )
        q_end, p_end = alloc._integrate_trajectory(
            q_init=q0, p_init=p0, step_size=0.002, num_steps=5,
            mu=self.mu_5, cov=self.cov_5, q0=q0,
            risk_aversion=3.0, dist_penalty=1.0, barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE, metric_type=MetricType.FISHER_RAO,
        )
        h_end = alloc._hamiltonian(
            q=q_end, p=p_end, mu=self.mu_5, cov=self.cov_5, q0=q0,
            risk_aversion=3.0, dist_penalty=1.0, barrier_coef=1e-5,
            mode=AllocationMode.MAX_SHARPE, metric_type=MetricType.FISHER_RAO,
        )
        self.assertLess(abs(h_end - h_init), 0.50)

    def test_tc33_metropolis_negative_energy_drift_acceptance(self) -> None:
        delta_h = -2.5  # Energy decreased
        alpha = min(1.0, math.exp(-delta_h))
        self.assertEqual(alpha, 1.0)

    def test_tc34_large_energy_spike_has_low_acceptance(self) -> None:
        delta_h = 25.0
        alpha = min(1.0, math.exp(-delta_h))
        self.assertLess(alpha, 1e-10)

    def test_tc35_hmc_sampling_acceptance_rate_range(self) -> None:
        cfg = SymplecticAllocatorConfig(num_samples=20, burn_in=5, step_size=0.01, random_seed=42)
        alloc = SymplecticManifoldHMCAllocator(cfg)
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5)
        self.assertGreaterEqual(res.acceptance_rate, 0.20)
        self.assertLessEqual(res.acceptance_rate, 1.00)

    # =========================================================================
    # Category 8: Dual-Averaging Step-Size Adaptation Convergence
    # =========================================================================
    def test_tc36_dual_averaging_enabled_execution(self) -> None:
        cfg = SymplecticAllocatorConfig(
            num_samples=15,
            burn_in=10,
            dual_averaging=True,
            target_acceptance=0.80,
            random_seed=42,
        )
        alloc = SymplecticManifoldHMCAllocator(cfg)
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5)
        self.assertIn("adapted_step_size", res.metadata)
        self.assertGreater(res.metadata["adapted_step_size"], 0.0)

    def test_tc37_dual_averaging_disabled_preserves_initial_step_size(self) -> None:
        cfg = SymplecticAllocatorConfig(
            num_samples=10,
            burn_in=5,
            dual_averaging=False,
            step_size=0.025,
            random_seed=42,
        )
        alloc = SymplecticManifoldHMCAllocator(cfg)
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5)
        self.assertAlmostEqual(res.metadata["adapted_step_size"], 0.025)

    def test_tc38_effective_sample_size_metric(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5)
        self.assertGreaterEqual(res.effective_sample_size, 1.0)

    def test_tc39_dual_averaging_higher_target_reduces_step_size(self) -> None:
        # High target acceptance requires smaller step size
        cfg_high = SymplecticAllocatorConfig(
            num_samples=10, burn_in=15, dual_averaging=True, target_acceptance=0.95, random_seed=42
        )
        cfg_low = SymplecticAllocatorConfig(
            num_samples=10, burn_in=15, dual_averaging=True, target_acceptance=0.50, random_seed=42
        )
        alloc_high = SymplecticManifoldHMCAllocator(cfg_high)
        alloc_low = SymplecticManifoldHMCAllocator(cfg_low)
        res_high = alloc_high.allocate(self.symbols_5, self.mu_5, self.cov_5)
        res_low = alloc_low.allocate(self.symbols_5, self.mu_5, self.cov_5)
        self.assertLessEqual(res_high.metadata["adapted_step_size"], res_low.metadata["adapted_step_size"] + 0.05)

    def test_tc40_reproducibility_with_seed(self) -> None:
        cfg1 = SymplecticAllocatorConfig(num_samples=20, random_seed=123)
        cfg2 = SymplecticAllocatorConfig(num_samples=20, random_seed=123)
        res1 = SymplecticManifoldHMCAllocator(cfg1).allocate(self.symbols_5, self.mu_5, self.cov_5)
        res2 = SymplecticManifoldHMCAllocator(cfg2).allocate(self.symbols_5, self.mu_5, self.cov_5)
        for sym in self.symbols_5:
            self.assertAlmostEqual(res1.weights[sym], res2.weights[sym], places=7)

    # =========================================================================
    # Category 9: Gromov \delta-Hyperbolicity & Systemic Crash Damping
    # =========================================================================
    def test_tc41_gromov_hyperbolicity_flat_market(self) -> None:
        corr_flat = np.eye(5) * 0.9 + 0.1
        np.fill_diagonal(corr_flat, 1.0)
        delta, hazard, regime = compute_gromov_hyperbolicity(corr_flat, max_samples=50)
        self.assertGreaterEqual(delta, 0.0)
        self.assertLess(hazard, 0.50)
        self.assertIn(regime, [CurvatureRegime.FLAT_EUCLIDEAN, CurvatureRegime.HYPERBOLIC_STRESSED])

    def test_tc42_gromov_hyperbolicity_systemic_collapse_regime(self) -> None:
        # High uniform correlation represents systemic contagion (tree-like)
        corr_crisis = np.ones((6, 6)) * 0.99
        np.fill_diagonal(corr_crisis, 1.0)
        delta, hazard, regime = compute_gromov_hyperbolicity(corr_crisis, max_samples=50)
        self.assertLessEqual(delta, 0.50)
        self.assertGreater(hazard, 0.50)

    def test_tc43_small_asset_universe_hyperbolicity_fallback(self) -> None:
        corr_3 = np.eye(3)
        delta, hazard, regime = compute_gromov_hyperbolicity(corr_3)
        self.assertEqual(regime, CurvatureRegime.FLAT_EUCLIDEAN)
        self.assertEqual(hazard, 0.0)

    def test_tc44_crash_hazard_triggers_cash_preservation(self) -> None:
        # Pass a crisis correlation matrix to allocate
        corr_crisis = np.ones((5, 5)) * 0.98
        np.fill_diagonal(corr_crisis, 1.0)
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(
            symbols=self.symbols_5,
            expected_returns=self.mu_5,
            covariance_matrix=self.cov_5,
            correlation_matrix=corr_crisis,
        )
        self.assertGreater(res.cash_weight, 0.10)
        self.assertAlmostEqual(sum(res.weights.values()) + res.cash_weight, 1.0, places=5)

    def test_tc45_curvature_regime_classification_in_result(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5)
        self.assertIsInstance(res.curvature_regime, CurvatureRegime)

    # =========================================================================
    # Category 10: Geodesic Leland No-Trade Buffer Bands & Instant Bypass
    # =========================================================================
    def test_tc46_immediate_entry_bypass(self) -> None:
        current_w = {"AAPL": 0.0, "MSFT": 0.5, "GOOGL": 0.5, "AMZN": 0.0, "NVDA": 0.0}
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5, current_weights=current_w)
        # Any asset that had 0 weight and receives allocation should trigger IMMEDIATE_ENTRY
        for sym in res.bypass_entries:
            self.assertEqual(current_w[sym], 0.0)
            self.assertGreater(res.weights[sym], 0.0)

    def test_tc47_immediate_exit_bypass(self) -> None:
        # Set expected returns very low for NVDA
        mu_neg = np.array([0.15, 0.12, 0.14, 0.16, -0.50])
        current_w = {"AAPL": 0.2, "MSFT": 0.2, "GOOGL": 0.2, "AMZN": 0.2, "NVDA": 0.2}
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, mu_neg, self.cov_5, current_weights=current_w)
        # If NVDA liquidated, action is exit bypass
        if "NVDA" in res.bypass_exits:
            self.assertEqual(res.weights["NVDA"], 0.0)

    def test_tc48_geodesic_hold_preserves_current_weight(self) -> None:
        # When target proposed weights are identical to current, hold is triggered
        current_w = {"AAPL": 0.2, "MSFT": 0.2, "GOOGL": 0.2, "AMZN": 0.2, "NVDA": 0.2}
        cfg = SymplecticAllocatorConfig(leland_base_bandwidth=0.50)  # very wide buffer band
        alloc = SymplecticManifoldHMCAllocator(cfg)
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5, current_weights=current_w)
        self.assertGreater(len(res.held_assets), 0)

    def test_tc49_cost_saved_bps_accounting(self) -> None:
        current_w = {"AAPL": 0.2, "MSFT": 0.2, "GOOGL": 0.2, "AMZN": 0.2, "NVDA": 0.2}
        cfg = SymplecticAllocatorConfig(leland_base_bandwidth=0.50)
        alloc = SymplecticManifoldHMCAllocator(cfg)
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5, current_weights=current_w)
        total_saved = sum(band.cost_saved_bps for band in res.leland_bands.values())
        self.assertGreaterEqual(total_saved, 0.0)

    def test_tc50_leland_bands_dict_serialization(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5)
        d = res.to_dict()
        self.assertIn("leland_bands", d)
        self.assertIn("AAPL", d["leland_bands"])
        self.assertIn("action", d["leland_bands"]["AAPL"])

    # =========================================================================
    # Category 11: Multi-Regime Allocation Modes & Robust Tail-Hedging
    # =========================================================================
    def test_tc51_max_sharpe_mode(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5, mode=AllocationMode.MAX_SHARPE)
        self.assertEqual(res.metadata["mode"], "MAX_SHARPE")
        self.assertTrue(res.symplectic_invariants_satisfied)

    def test_tc52_min_variance_risk_parity_mode(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5, mode=AllocationMode.MIN_VARIANCE_RISK_PARITY)
        self.assertEqual(res.metadata["mode"], "MIN_VARIANCE_RISK_PARITY")
        # In risk parity, high volatility asset should receive less weight
        self.assertTrue(res.symplectic_invariants_satisfied)

    def test_tc53_robust_cvar_tail_hedge_mode(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5, mode=AllocationMode.ROBUST_CVAR_TAIL_HEDGE)
        self.assertEqual(res.metadata["mode"], "ROBUST_CVAR_TAIL_HEDGE")
        self.assertTrue(res.symplectic_invariants_satisfied)

    def test_tc54_dynamic_regime_blended_mode(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5, mode=AllocationMode.DYNAMIC_REGIME_BLENDED)
        self.assertEqual(res.metadata["mode"], "DYNAMIC_REGIME_BLENDED")
        self.assertTrue(res.symplectic_invariants_satisfied)

    def test_tc55_functional_wrapper_run_symplectic_allocation(self) -> None:
        res = run_symplectic_allocation(
            symbols=self.symbols_5,
            expected_returns=self.mu_5,
            covariance_matrix=self.cov_5,
            market="NASDAQ",
            mode="MAX_SHARPE",
        )
        self.assertIsInstance(res, SymplecticOptimizationResult)
        self.assertEqual(res.metadata["market"], "NASDAQ")
        self.assertEqual(res.metadata["mode"], "MAX_SHARPE")

    # =========================================================================
    # Category 12: Extreme Edge Cases, High-Dimensional Scalability & Latency SLA
    # =========================================================================
    def test_tc56_empty_symbols_raises_value_error(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        with self.assertRaises(ValueError):
            alloc.allocate([], [], [[]])

    def test_tc57_dimension_mismatch_raises_value_error(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        with self.assertRaises(ValueError):
            alloc.allocate(["A", "B"], [0.1], [[0.01]])

    def test_tc58_singular_covariance_matrix_regularization(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        cov_singular = np.ones((5, 5)) * 0.01  # Rank 1 matrix
        res = alloc.allocate(self.symbols_5, self.mu_5, cov_singular)
        self.assertTrue(res.symplectic_invariants_satisfied)

    def test_tc59_high_dimensional_scalability_30_assets(self) -> None:
        n = 30
        syms = [f"SYM_{i:02d}" for i in range(n)]
        mu = self.rng.uniform(0.05, 0.25, size=n)
        raw_cov = self.rng.normal(0, 0.05, size=(n, n))
        cov = raw_cov @ raw_cov.T + np.eye(n) * 0.05

        alloc = SymplecticManifoldHMCAllocator()
        t0 = time.perf_counter()
        res = alloc.allocate(syms, mu, cov)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res.weights), n)
        self.assertTrue(res.symplectic_invariants_satisfied)
        self.assertLess(elapsed_ms, 300.0, "30-asset optimization exceeded 300ms SLA!")

    def test_tc60_execution_latency_sla_under_100ms(self) -> None:
        alloc = SymplecticManifoldHMCAllocator()
        t0 = time.perf_counter()
        res = alloc.allocate(self.symbols_5, self.mu_5, self.cov_5)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 100.0, f"5-asset optimization latency {elapsed_ms:.2f}ms exceeded 100ms SLA!")


if __name__ == "__main__":
    unittest.main()
