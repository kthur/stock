r"""
tests/test_phase120_challenger_m3_empirical.py
=============================================
Empirical Challenge & Stress Test Suite for Milestone 3 (Feature F572):
Curvature-Aware Riemannian Manifold Portfolio Allocator & Fisher Information Metric Engine.

Challenger: teamwork_preview_challenger_m3_2
Role: EMPIRICAL CHALLENGER (critic, specialist)

Target Areas:
1. Gromov delta-hyperbolicity systemic crash alert (H_crash > 0.70 during contagion) across all 5 markets:
   SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
2. Geodesic Leland buffer turnover suppression vs Euclidean no-trade buffer bands.
3. 50-iteration Monte Carlo Execution Latency SLA (< 15ms) benchmark across N=10 to N=50 assets.
4. Adversarial Stress & Edge Case Boundary Testing:
   - Degenerate correlation matrices (perfect collinearity, near-singular, negative blocks)
   - Zero-volatility / singular covariance
   - Extreme dimension scaling (N=2 up to N=100)
   - Invariant conservation (\sum w_i + w_cash == 1.000000)
"""

import math
import time
import unittest
from typing import Dict, List, Tuple

import numpy as np

from src.risk.riemannian_manifold_portfolio_allocator import (
    CRASH_ALERT_THRESHOLD,
    CurvatureRegime,
    BypassAction,
    MARKET_RIEMANNIAN_PROFILES,
    MarketType,
    RiemannianAllocatorConfig,
    RiemannianManifoldPortfolioAllocator,
    apply_geodesic_leland_bands,
    compute_gromov_hyperbolicity,
    exponential_retraction,
    fisher_rao_metric_tensor,
    geodesic_distance,
    get_market_profile,
    project_tangent_space,
    spherical_embedding,
)


class TestPhase120ChallengerM3Empirical(unittest.TestCase):
    """Empirical challenge suite for Feature F572."""

    def setUp(self) -> None:
        self.rng = np.random.RandomState(42)
        self.markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

    # =========================================================================
    # CHALLENGE 1: Gromov delta-Hyperbolicity Systemic Crash Alert Across 5 Markets
    # =========================================================================
    def test_c01_gromov_crash_alert_triggers_under_contagion_all_5_markets(self) -> None:
        """
        Challenge 1A: Empirically verify that under severe contagion (rho >= 0.95),
        H_crash strictly exceeds 0.70 across ALL 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
        """
        n_assets = 12
        corr_contagion = np.full((n_assets, n_assets), 0.97, dtype=np.float64)
        np.fill_diagonal(corr_contagion, 1.0)

        results: Dict[str, Tuple[float, bool]] = {}
        for mkt in self.markets:
            allocator = RiemannianManifoldPortfolioAllocator(market=mkt)
            diag = compute_gromov_hyperbolicity(
                corr_matrix=corr_contagion,
                critical_delta=allocator.config.critical_hyperbolicity,
                kappa_hyp=allocator.config.kappa_hyp,
                cash_de_risk_multiplier=allocator.config.cash_de_risk_multiplier,
            )
            results[mkt] = (diag.h_crash, diag.is_crash_alert)

            self.assertGreater(
                diag.h_crash,
                0.70,
                f"Market {mkt} failed H_crash > 0.70 under contagion: H_crash={diag.h_crash:.4f}"
            )
            self.assertTrue(
                diag.is_crash_alert,
                f"Market {mkt} failed to trigger is_crash_alert under contagion"
            )
            self.assertEqual(
                diag.curvature_regime,
                CurvatureRegime.SYSTEMIC_TREE_CONTAGION,
                f"Market {mkt} failed to identify SYSTEMIC_TREE_CONTAGION regime"
            )
            self.assertGreater(
                diag.cash_allocation,
                0.0,
                f"Market {mkt} failed to allocate safety cash under crash alert"
            )

    def test_c02_gromov_crash_alert_quiet_regime_no_false_alarm_all_5_markets(self) -> None:
        """
        Challenge 1B: Empirically verify that under quiet/decorrelated regimes (rho <= 0.15),
        H_crash remains below 0.20 (no false alarm) across ALL 5 markets.
        """
        n_assets = 12
        corr_quiet = np.full((n_assets, n_assets), 0.05, dtype=np.float64)
        np.fill_diagonal(corr_quiet, 1.0)

        for mkt in self.markets:
            allocator = RiemannianManifoldPortfolioAllocator(market=mkt)
            diag = compute_gromov_hyperbolicity(
                corr_matrix=corr_quiet,
                critical_delta=allocator.config.critical_hyperbolicity,
                kappa_hyp=allocator.config.kappa_hyp,
            )
            self.assertLess(
                diag.h_crash,
                0.20,
                f"Market {mkt} triggered false alarm in quiet regime: H_crash={diag.h_crash:.4f}"
            )
            self.assertFalse(
                diag.is_crash_alert,
                f"Market {mkt} raised crash alert in quiet regime"
            )
            self.assertEqual(
                diag.cash_allocation,
                0.0,
                f"Market {mkt} allocated non-zero cash in quiet regime"
            )

    def test_c03_gromov_crash_alert_hierarchical_factor_contagion(self) -> None:
        """
        Challenge 1C: Test empirical contagion generated by a single dominant market crash factor
        (1-factor model: r_i = beta_i * F_crash + eps_i, F_crash variance dominates).
        """
        n_assets = 16
        betas = self.rng.uniform(0.9, 1.3, size=n_assets)
        # Dominant factor variance = 0.20, idiosyncratic = 0.005
        cov_factor = 0.20 * np.outer(betas, betas) + np.eye(n_assets) * 0.005
        vols = np.sqrt(np.diag(cov_factor))
        corr_factor = cov_factor / np.outer(vols, vols)
        np.fill_diagonal(corr_factor, 1.0)

        for mkt in self.markets:
            allocator = RiemannianManifoldPortfolioAllocator(market=mkt)
            diag = compute_gromov_hyperbolicity(
                corr_matrix=corr_factor,
                critical_delta=allocator.config.critical_hyperbolicity,
                kappa_hyp=allocator.config.kappa_hyp,
            )
            self.assertGreater(
                diag.h_crash,
                0.70,
                f"Market {mkt} failed factor contagion test: H_crash={diag.h_crash:.4f}"
            )
            self.assertTrue(diag.is_crash_alert)

    # =========================================================================
    # CHALLENGE 2: Geodesic Leland Buffer Turnover Suppression
    # =========================================================================
    def test_c04_geodesic_leland_turnover_suppression_vs_euclidean_and_unbuffered(self) -> None:
        """
        Challenge 2A: Empirically verify that Geodesic Leland buffer suppresses turnover
        compared to unbuffered rebalancing and Euclidean buffer bands over 20 quiet periods.
        """
        n = 15
        base_weights = np.full(n, 1.0 / n, dtype=np.float64)
        vols = np.full(n, 0.15, dtype=np.float64)

        current_geo = base_weights.copy()
        current_euclid = base_weights.copy()

        cum_turnover_unbuffered = 0.0
        cum_turnover_geo = 0.0
        cum_turnover_euclid = 0.0

        euclid_band_half_width = 0.015  # 1.5% band

        for step in range(25):
            # Small random drift in optimal weights (quiet regime noise)
            noise = self.rng.normal(0.0, 0.006, size=n)
            target = np.maximum(0.005, base_weights + noise)
            target = target / np.sum(target)

            # 1. Unbuffered turnover
            cum_turnover_unbuffered += float(0.5 * np.sum(np.abs(target - current_geo)))

            # 2. Geodesic Leland buffer
            leland_res = apply_geodesic_leland_bands(
                target_weights=target,
                current_weights=current_geo,
                asset_vols=vols,
                h_crash=0.02,
                base_band=0.018,
            )
            cum_turnover_geo += float(0.5 * np.sum(np.abs(leland_res.rebalanced_weights - current_geo)))
            current_geo = leland_res.rebalanced_weights.copy()

            # 3. Euclidean buffer
            reb_euclid = current_euclid.copy()
            for i in range(n):
                diff = abs(target[i] - current_euclid[i])
                if diff > euclid_band_half_width:
                    reb_euclid[i] = target[i]
            reb_euclid = reb_euclid / np.sum(reb_euclid)
            cum_turnover_euclid += float(0.5 * np.sum(np.abs(reb_euclid - current_euclid)))
            current_euclid = reb_euclid.copy()

        # Geodesic Leland must suppress turnover significantly compared to unbuffered
        self.assertLess(
            cum_turnover_geo,
            cum_turnover_unbuffered * 0.40,
            f"Geodesic turnover ({cum_turnover_geo:.4f}) failed to reduce unbuffered turnover ({cum_turnover_unbuffered:.4f})"
        )
        # Geodesic turnover should be lower than or competitive with Euclidean buffer
        self.assertLessEqual(
            cum_turnover_geo,
            cum_turnover_euclid * 1.05,
            f"Geodesic turnover ({cum_turnover_geo:.4f}) exceeded Euclidean ({cum_turnover_euclid:.4f})"
        )

    def test_c05_immediate_entry_and_exit_bypass_correctness(self) -> None:
        """
        Challenge 2B: Empirically verify instant entry bypass (w_0 == 0 -> w_t)
        and instant exit bypass (w_t == 0 -> 0.0) without being trapped in buffer bands.
        """
        # Asset 0: existing holding to liquidate (w_0 > 0, w_t = 0)
        # Asset 1: new entrant to buy (w_0 = 0, w_t > 0)
        # Asset 2: existing holding with tiny drift (w_0 = 0.50, w_t = 0.505) -> should hold
        current_w = np.array([0.40, 0.00, 0.60], dtype=np.float64)
        target_w = np.array([0.00, 0.395, 0.605], dtype=np.float64)
        vols = np.array([0.20, 0.20, 0.20], dtype=np.float64)

        leland = apply_geodesic_leland_bands(
            target_weights=target_w,
            current_weights=current_w,
            asset_vols=vols,
            h_crash=0.0,
            base_band=0.03,
            asset_names=["ASSET_EXIT", "ASSET_ENTRY", "ASSET_HOLD"],
        )

        self.assertIn("ASSET_EXIT", leland.bypassed_exits)
        self.assertIn("ASSET_ENTRY", leland.bypassed_entries)
        self.assertIn("ASSET_HOLD", leland.held_assets)

        # Asset 0 liquidated to 0.0
        self.assertEqual(leland.rebalanced_weights[0], 0.0)
        # Asset 1 received non-zero allocation immediately
        self.assertGreater(leland.rebalanced_weights[1], 0.35)
        # Simplex sum strictly preserved
        self.assertAlmostEqual(float(np.sum(leland.rebalanced_weights)), 1.0, places=10)

    # =========================================================================
    # CHALLENGE 3: 50-Iteration Monte Carlo Latency SLA Benchmark (< 15ms)
    # =========================================================================
    def test_c06_monte_carlo_50_iterations_latency_sla_across_asset_scales(self) -> None:
        """
        Challenge 3: Benchmark execution latency SLA (< 15ms) across 50 Monte Carlo iterations
        spanning universe sizes N in [10, 20, 30, 40, 50].
        Collect detailed distribution: mean, median, p95, max, and check SLA violations.
        """
        latencies_by_n: Dict[int, List[float]] = {10: [], 20: [], 30: [], 40: [], 50: []}
        all_latencies: List[float] = []

        allocator = RiemannianManifoldPortfolioAllocator(market="SP500")

        # 50 Monte Carlo iterations: 10 runs per dimension
        iterations_per_n = 10
        for n in [10, 20, 30, 40, 50]:
            for _ in range(iterations_per_n):
                A = self.rng.randn(n, n)
                cov = (A @ A.T) * 0.01 + np.eye(n) * 0.04
                mu = self.rng.uniform(0.05, 0.20, size=n)

                t0 = time.perf_counter()
                res = allocator.optimize(mu, cov)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0

                latencies_by_n[n].append(elapsed_ms)
                all_latencies.append(elapsed_ms)

        mean_lat = float(np.mean(all_latencies))
        median_lat = float(np.median(all_latencies))
        p95_lat = float(np.percentile(all_latencies, 95))
        max_lat = float(np.max(all_latencies))
        violations = [l for l in all_latencies if l >= 15.0]

        print(f"\n[CHALLENGER 50-MC LATENCY BENCHMARK REPORT]")
        print(f"Total Iterations: {len(all_latencies)}")
        print(f"Overall Mean Latency:   {mean_lat:.2f} ms")
        print(f"Overall Median Latency: {median_lat:.2f} ms")
        print(f"Overall 95th-Pct:       {p95_lat:.2f} ms")
        print(f"Overall Max Latency:    {max_lat:.2f} ms")
        print(f"SLA Violations (>=15ms): {len(violations)} / {len(all_latencies)} ({len(violations)/len(all_latencies)*100:.1f}%)")
        for n, l_list in latencies_by_n.items():
            print(f"  N={n:2d}: Mean={np.mean(l_list):.2f} ms, Max={np.max(l_list):.2f} ms, Violations={sum(1 for x in l_list if x >= 15.0)}/{len(l_list)}")

        # Verify mean latency is comfortably below 15ms
        self.assertLess(
            mean_lat,
            15.0,
            f"Mean latency {mean_lat:.2f} ms exceeded 15.0 ms SLA"
        )

    # =========================================================================
    # CHALLENGE 4: Adversarial Stress & Edge Case Boundary Testing
    # =========================================================================
    def test_c07_adversarial_degenerate_correlation_all_ones_or_zeros(self) -> None:
        """
        Challenge 4A: Degenerate correlation matrix (all 1.0s or rank 1).
        Verifies no NaN/Inf and simplex sum is strictly 1.000000.
        """
        n = 10
        cov_all_ones = np.ones((n, n), dtype=np.float64) * 0.04
        mu = np.full(n, 0.10)

        allocator = RiemannianManifoldPortfolioAllocator(market="NASDAQ")
        res = allocator.optimize(mu, cov_all_ones)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertFalse(np.any(np.isinf(res.optimal_weights)))
        total_weight = float(np.sum(res.optimal_weights) + res.cash_weight)
        self.assertAlmostEqual(total_weight, 1.0, places=10)

    def test_c08_adversarial_zero_and_negative_eigenvalues_covariance(self) -> None:
        """
        Challenge 4B: Covariance matrix with negative eigenvalues (non-positive semi-definite).
        """
        n = 8
        cov_bad = np.array([
            [1.0, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
            [0.9, 1.0, -0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
            [0.9, -0.9, 1.0, 0.9, 0.9, 0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9, 1.0, 0.9, 0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9, 0.9, 1.0, 0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9, 0.9, 0.9, 1.0, 0.9, 0.9],
            [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0, 0.9],
            [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0],
        ], dtype=np.float64) * 0.05
        mu = self.rng.uniform(0.05, 0.20, size=n)

        allocator = RiemannianManifoldPortfolioAllocator(market="KOSPI")
        res = allocator.optimize(mu, cov_bad)

        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertTrue(np.all(res.optimal_weights >= 0.0))

    def test_c09_adversarial_tiny_universe_n2_n3(self) -> None:
        """
        Challenge 4C: Tiny universes (N=2, N=3) where Gromov 4-tuple cannot be formed.
        Allocator must fall back cleanly without crashing.
        """
        for n in [2, 3]:
            cov = np.eye(n) * 0.04
            mu = np.linspace(0.10, 0.20, n)
            allocator = RiemannianManifoldPortfolioAllocator(market="KOSDAQ")
            res = allocator.optimize(mu, cov)

            self.assertEqual(len(res.optimal_weights), n)
            self.assertFalse(res.hyperbolicity_diagnostics.is_crash_alert)
            self.assertAlmostEqual(float(np.sum(res.optimal_weights)), 1.0, places=10)

    def test_c10_adversarial_extreme_dimension_n100(self) -> None:
        """
        Challenge 4D: Large dimension N=100 assets.
        Must complete without memory exhaustion, combinatorial explosion, or NaN.
        """
        n = 100
        A = self.rng.randn(n, 10)  # Rank 10 factor structure
        cov = (A @ A.T) * 0.005 + np.eye(n) * 0.02
        mu = self.rng.uniform(0.01, 0.30, size=n)

        allocator = RiemannianManifoldPortfolioAllocator(market="RUSSELL2000", max_iterations=100)
        t0 = time.perf_counter()
        res = allocator.optimize(mu, cov)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res.optimal_weights), 100)
        self.assertFalse(np.any(np.isnan(res.optimal_weights)))
        self.assertAlmostEqual(float(np.sum(res.optimal_weights) + res.cash_weight), 1.0, places=8)


if __name__ == "__main__":
    unittest.main()
