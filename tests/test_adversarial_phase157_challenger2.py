"""
Adversarial Stress Testing & Empirical Challenge Suite for Milestone 2 (Phase 157)
Challenger 2 (Features F767, F768, F769).

Coverage:
1. Gating Threshold Stress: Borderline inputs across all 6 tiers:
   - VIX = 39.99 vs 40.01
   - TSR = 1.079 vs 1.081
   - DD = -0.1199 vs -0.1201
   - Rho = 0.849 vs 0.851
   Assert exact binary gating and minimum envelope behavior.
2. Systemic Correlation Breakdown & Absorption Ratio Stress:
   - Cross-asset correlation rho = 0.95 with high absorption ratio.
   - Assert immediate collapse to 0.15x crisis leverage and 0.70x haircut multiplier.
3. RMT Spectrum Capping & Mode Exemption Stress (N=500):
   - Condition number kappa <= 45.0 + 1e-4
   - Minimum eigenvalue lambda_min > 1e-8
   - Exact trace conservation Tr(Sigma_clean) == Tr(Sigma_raw)
   - Top-150 modes preserved.
4. Market Impact Penalty Edge Cases & Convexity:
   - Zero ADV, massive order relative to ADV (> 10.0), negative order.
   - Strict finiteness, non-negativity, and 3/2-power monotonic convexity.
5. Asymmetric Leland Dynamic Buffer Band Bypass:
   - New position entry (w0 = 0 -> w1 > 0) zero-delay bypass.
   - Full liquidation (w0 > 0 -> w1 = 0) zero-delay bypass.
   - Intra-band sub-threshold suppression (|w1 - w0| <= delta).
6. Latency SLA & Multithreaded Concurrency Stress:
   - 100 consecutive allocations assert P95 < 100 ms.
   - 100 multithreaded allocations across 8 threads assert P95 < 100 ms.
"""

import math
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from src.risk.dynamic_regime_leverage_allocator import (
    DynamicRegimeLeverageAllocator,
    CorrelationBreakdownBrake,
)
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    AllocationResult,
)


class TestPhase157AdversarialChallenger2(unittest.TestCase):
    """
    Adversarial Stress Testing Suite for Phase 157 (Release R159) - Features F767, F768, F769.
    """

    @classmethod
    def setUpClass(cls):
        cls.allocator = DynamicRegimeLeverageAllocator()
        cls.brake = CorrelationBreakdownBrake()
        cls.unified_allocator = UnifiedPortfolioAllocator()

    # =========================================================================
    # VECTOR 1: GATING THRESHOLD STRESS & BORDERLINE INPUTS
    # =========================================================================

    def test_v1_01_vix_threshold_boundary_stress(self):
        """V1.01: Borderline VIX stress: 39.99 vs 40.01."""
        # VIX = 39.99 (Tier 1 inactive, Tier 2 active because VIX >= 30.0 -> lev <= 0.40)
        res_sub = self.allocator.evaluate_6tier_protective_gating(
            vix=39.99, tsr=0.90, drawdown=0.0, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertFalse(res_sub["tier1_crisis_gate_active"])
        self.assertTrue(res_sub["tier2_vol_spike_active"])
        self.assertEqual(res_sub["allowed_leverage"], 0.40)

        # VIX = 40.01 (Tier 1 active -> lev <= 0.15)
        res_sup = self.allocator.evaluate_6tier_protective_gating(
            vix=40.01, tsr=0.90, drawdown=0.0, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertTrue(res_sup["tier1_crisis_gate_active"])
        self.assertEqual(res_sup["allowed_leverage"], 0.15)

    def test_v1_02_tsr_inversion_boundary_stress(self):
        """V1.02: Borderline TSR stress: 1.079 vs 1.081."""
        # TSR = 1.079 (Tier 3 inactive -> full 1.50x in BULL_LOW_VOL)
        res_sub = self.allocator.evaluate_6tier_protective_gating(
            vix=20.0, tsr=1.079, drawdown=0.0, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertFalse(res_sub["tier3_tsr_lock_active"])
        self.assertEqual(res_sub["allowed_leverage"], 1.50)

        # TSR = 1.081 (Tier 3 active -> capped at 0.50x)
        res_sup = self.allocator.evaluate_6tier_protective_gating(
            vix=20.0, tsr=1.081, drawdown=0.0, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertTrue(res_sup["tier3_tsr_lock_active"])
        self.assertEqual(res_sup["allowed_leverage"], 0.50)

    def test_v1_03_drawdown_ratchet_boundary_stress(self):
        """V1.03: Borderline HWM Drawdown stress: -0.1199 vs -0.1201."""
        # DD = -0.1199 (Tier 4 inactive -> full 1.50x in BULL_LOW_VOL)
        res_sub = self.allocator.evaluate_6tier_protective_gating(
            vix=20.0, tsr=0.90, drawdown=-0.1199, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertFalse(res_sub["tier4_drawdown_ratchet_active"])
        self.assertEqual(res_sub["allowed_leverage"], 1.50)

        # DD = -0.1201 (Tier 4 active -> crisis collapse 0.15x)
        res_sup = self.allocator.evaluate_6tier_protective_gating(
            vix=20.0, tsr=0.90, drawdown=-0.1201, mean_corr=0.40, regime="BULL_LOW_VOL"
        )
        self.assertTrue(res_sup["tier4_drawdown_ratchet_active"])
        self.assertEqual(res_sup["allowed_leverage"], 0.15)

    def test_v1_04_mean_correlation_boundary_stress(self):
        """V1.04: Borderline Cross-Asset Mean Correlation stress: 0.849 vs 0.851."""
        # Rho = 0.849 (Tier 5 inactive -> haircut 1.0, full 1.50x)
        res_sub = self.allocator.evaluate_6tier_protective_gating(
            vix=20.0, tsr=0.90, drawdown=0.0, mean_corr=0.849, regime="BULL_LOW_VOL"
        )
        self.assertFalse(res_sub["tier5_correlation_brake_active"])
        self.assertEqual(res_sub["haircut_multiplier"], 1.0)
        self.assertEqual(res_sub["allowed_leverage"], 1.50)

        # Rho = 0.851 (Tier 5 active -> haircut 0.70, capped at 0.70x)
        res_sup = self.allocator.evaluate_6tier_protective_gating(
            vix=20.0, tsr=0.90, drawdown=0.0, mean_corr=0.851, regime="BULL_LOW_VOL"
        )
        self.assertTrue(res_sup["tier5_correlation_brake_active"])
        self.assertEqual(res_sup["haircut_multiplier"], 0.70)
        self.assertEqual(res_sup["allowed_leverage"], 0.70)

    def test_v1_05_simultaneous_multi_gate_envelope_invariance(self):
        """V1.05: Multi-gate envelope invariance: minimum allowable leverage strictly wins."""
        # Simultaneously trigger TSR (0.50), Vol Spike (0.40), Drawdown (0.15), Correlation (0.70)
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=35.0, tsr=1.12, drawdown=-0.13, mean_corr=0.89, regime="BULL_LOW_VOL"
        )
        self.assertTrue(res["tier2_vol_spike_active"])
        self.assertTrue(res["tier3_tsr_lock_active"])
        self.assertTrue(res["tier4_drawdown_ratchet_active"])
        self.assertTrue(res["tier5_correlation_brake_active"])
        # Expected minimum envelope is 0.15
        self.assertEqual(res["allowed_leverage"], 0.15)
        self.assertEqual(res["haircut_multiplier"], 0.70)

    # =========================================================================
    # VECTOR 2: CORRELATION BREAKDOWN & ABSORPTION RATIO STRESS
    # =========================================================================

    def test_v2_01_correlation_brake_absorption_ratio_stress(self):
        """V2.01: Correlation breakdown brake under rho = 0.95 equicorrelation."""
        N = 25
        cov_high = np.full((N, N), 0.95 * 0.04)
        np.fill_diagonal(cov_high, 0.04)

        stress_res = self.brake.evaluate_correlation_stress(cov_high)
        self.assertTrue(stress_res["brake_active"])
        self.assertEqual(stress_res["haircut_multiplier"], 0.70)
        self.assertAlmostEqual(stress_res["mean_pairwise_corr"], 0.95, places=5)
        self.assertGreaterEqual(stress_res["absorption_ratio"], 0.80)
        self.assertGreater(stress_res["condition_number"], 50.0)

    def test_v2_02_correlation_collapse_in_5tier_gating(self):
        """V2.02: 5-tier gating collapses to 0.15x under systemic correlation breakdown."""
        N = 20
        corr_high = np.full((N, N), 0.95)
        np.fill_diagonal(corr_high, 1.0)

        lev = self.allocator.evaluate_5tier_protective_gating(
            current_nav=100.0,
            vix=20.0,
            vix_history=[20.0] * 5,
            tsr_ratio=0.90,
            regime="BULL_LOW_VOL",
            correlation_matrix=corr_high,
        )
        self.assertEqual(float(lev), 0.15)

    def test_v2_03_correlation_collapse_in_6tier_panic_regime(self):
        """V2.03: 6-tier gating with rho = 0.95 in PANIC_CRISIS collapses to 0.15x with 0.70 haircut."""
        res = self.allocator.evaluate_6tier_protective_gating(
            vix=42.0, tsr=1.10, drawdown=-0.14, mean_corr=0.95, regime="PANIC_CRISIS"
        )
        self.assertEqual(res["allowed_leverage"], 0.15)
        self.assertEqual(res["haircut_multiplier"], 0.70)
        self.assertTrue(res["tier5_correlation_brake_active"])

    # =========================================================================
    # VECTOR 3: RMT SPECTRUM CAPPING & MODE EXEMPTION (N=500)
    # =========================================================================

    def test_v3_01_rmt_denoise_n500_wishart_matrix(self):
        """V3.01: N=500 Wishart covariance denoised with top-150 modes exempted."""
        rng = np.random.RandomState(42)
        N = 500
        T = 1000
        X = rng.normal(0, 1, (T, N))
        raw_cov = np.cov(X, rowvar=False)
        tr_raw = float(np.trace(raw_cov))

        clean_cov = self.allocator.denoise_covariance_nonlinear_rmt(raw_cov, top_modes=150)
        self.assertEqual(clean_cov.shape, (500, 500))

        # 1. Condition number <= 45.0 + 1e-4
        evals = np.linalg.eigvalsh(clean_cov)
        cond = float(evals[-1] / evals[0])
        self.assertLessEqual(cond, 45.0 + 1e-4)

        # 2. Positive definiteness lambda_min > 1e-8
        self.assertGreater(evals[0], 1e-8)

        # 3. Exact trace conservation
        tr_clean = float(np.trace(clean_cov))
        self.assertAlmostEqual(tr_raw, tr_clean, places=5)

    def test_v3_02_rmt_denoise_n500_singular_rank50(self):
        """V3.02: N=500 Rank-50 singular covariance matrix regularized to kappa <= 45.0."""
        rng = np.random.RandomState(101)
        N = 500
        Rank = 50
        factors = rng.normal(0, 1, (N, Rank))
        cov_sing = (factors @ factors.T) / N
        tr_raw = float(np.trace(cov_sing))

        clean_cov = self.allocator.denoise_covariance_nonlinear_rmt(cov_sing, top_modes=150)
        evals = np.linalg.eigvalsh(clean_cov)
        cond = float(evals[-1] / evals[0])

        self.assertLessEqual(cond, 45.0 + 1e-4)
        self.assertGreater(evals[0], 1e-8)
        tr_clean = float(np.trace(clean_cov))
        self.assertAlmostEqual(tr_raw, tr_clean, places=5)

    def test_v3_03_rmt_denoise_n500_near_zero_variances(self):
        """V3.03: N=500 with 50 near-zero variance degenerate assets remains stable."""
        rng = np.random.RandomState(202)
        N = 500
        X = rng.normal(0, 1, (600, N))
        raw_cov = np.cov(X, rowvar=False)
        # Force 50 assets to near-zero variance
        raw_cov[10:60, :] = 0.0
        raw_cov[:, 10:60] = 0.0
        np.fill_diagonal(raw_cov[10:60, 10:60], 1e-12)

        clean_cov = self.allocator.denoise_covariance_nonlinear_rmt(raw_cov, top_modes=150)
        evals = np.linalg.eigvalsh(clean_cov)
        cond = float(evals[-1] / evals[0])

        self.assertLessEqual(cond, 45.0 + 1e-4)
        self.assertGreater(evals[0], 1e-8)
        # Diagonal entries strictly positive
        self.assertTrue((np.diag(clean_cov) > 0.0).all())

    def test_v3_04_rmt_mode_exemption_invariants(self):
        """V3.04: Exactly 150 modes are exempted across all risk allocators."""
        count_regime = self.allocator.get_rmt_exempt_eigenvectors_count()
        count_portfolio = PortfolioAllocator.get_rmt_exempt_eigenvectors_count()
        self.assertEqual(count_regime, 150)
        self.assertEqual(count_portfolio, 150)

    # =========================================================================
    # VECTOR 4: MARKET IMPACT PENALTY EDGE CASES & CONVEXITY
    # =========================================================================

    def test_v4_01_zero_adv_strictly_finite(self):
        """V4.01: Zero ADV safe clamping: penalty strictly finite and non-negative."""
        p = self.unified_allocator.compute_market_impact_penalty(order_notional=100.0, adv=0.0)
        self.assertTrue(math.isfinite(p))
        self.assertGreaterEqual(p, 0.0)
        # safe_adv = max(0.0, 1.0) = 1.0 -> 100^1.5 = 1000.0
        self.assertAlmostEqual(p, 1000.0, places=5)

    def test_v4_02_massive_order_relative_to_adv(self):
        """V4.02: Massive order relative to ADV (> 10.0x ADV) strictly finite."""
        p = self.unified_allocator.compute_market_impact_penalty(order_notional=25.0, adv=1.0)
        self.assertTrue(math.isfinite(p))
        # 25^1.5 = 125.0
        self.assertAlmostEqual(p, 125.0, places=5)

    def test_v4_03_negative_order_quantities_clamped_non_negative(self):
        """V4.03: Negative order quantities are clamped to 0.0 (non-negative)."""
        p = self.unified_allocator.compute_market_impact_penalty(order_notional=-50.0, adv=1000.0)
        self.assertEqual(p, 0.0)

    def test_v4_04_three_halves_power_monotonic_convexity(self):
        """V4.04: 3/2-power law is strictly monotonically increasing and convex."""
        adv = 10_000.0
        orders = [50.0, 100.0, 200.0, 400.0, 800.0]
        penalties = [self.unified_allocator.compute_market_impact_penalty(o, adv) for o in orders]

        # 1. Monotonicity: P(w1) < P(w2) < P(w3)...
        for i in range(len(penalties) - 1):
            self.assertLess(penalties[i], penalties[i + 1])

        # 2. Convexity: Discrete marginal impact (slopes) strictly increase
        slopes = [
            (penalties[i + 1] - penalties[i]) / (orders[i + 1] - orders[i])
            for i in range(len(orders) - 1)
        ]
        for i in range(len(slopes) - 1):
            self.assertLess(slopes[i], slopes[i + 1])

    # =========================================================================
    # VECTOR 5: ASYMMETRIC LELAND DYNAMIC BUFFER BAND BYPASS
    # =========================================================================

    def test_v5_01_new_position_entry_zero_delay_bypass(self):
        """V5.01: New entry (w0 = 0 -> w1 = 0.005) bypasses bandwidth (0.010) immediately."""
        tgt = {"005930": 0.005}
        curr = {"005930": 0.000}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(
            target_weights=tgt, current_holdings=curr, bandwidth=0.010, asymmetric=True
        )
        self.assertEqual(filtered["005930"], 0.005)

    def test_v5_02_full_liquidation_zero_delay_bypass(self):
        """V5.02: Full liquidation (w0 = 0.005 -> w1 = 0) bypasses bandwidth (0.010) immediately."""
        tgt = {"005930": 0.000}
        curr = {"005930": 0.005}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(
            target_weights=tgt, current_holdings=curr, bandwidth=0.010, asymmetric=True
        )
        self.assertEqual(filtered["005930"], 0.000)

    def test_v5_03_intra_band_sub_threshold_damping(self):
        """V5.03: Existing position sub-threshold change (0.050 -> 0.055) is dampened to 0.050."""
        tgt = {"AAPL": 0.055}
        curr = {"AAPL": 0.050}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(
            target_weights=tgt, current_holdings=curr, bandwidth=0.010, asymmetric=True
        )
        self.assertEqual(filtered["AAPL"], 0.050)

    def test_v5_04_super_threshold_trade_executed(self):
        """V5.04: Existing position super-threshold change (0.050 -> 0.065) executes to 0.065."""
        tgt = {"AAPL": 0.065}
        curr = {"AAPL": 0.050}
        filtered = self.unified_allocator.filter_rebalance_with_leland_bands(
            target_weights=tgt, current_holdings=curr, bandwidth=0.010, asymmetric=True
        )
        self.assertEqual(filtered["AAPL"], 0.065)

    # =========================================================================
    # VECTOR 6: LATENCY & CONCURRENCY SLA
    # =========================================================================

    def test_v6_01_sequential_100_runs_sla(self):
        """V6.01: 100 consecutive allocate_portfolio executions assert P95 < 100 ms."""
        N = 50
        rng = np.random.RandomState(42)
        mu = rng.uniform(0.01, 0.05, N)
        cov = np.eye(N) * 0.04

        latencies = []
        for _ in range(100):
            t0 = time.perf_counter()
            res = self.unified_allocator.allocate_portfolio(
                predictions_df=mu, prices_dict=cov, regime="BULL_LOW_VOL"
            )
            latencies.append((time.perf_counter() - t0) * 1000.0)
            self.assertIsInstance(res, (AllocationResult, dict))

        p95 = float(np.percentile(latencies, 95))
        self.assertLess(p95, 100.0, f"Sequential P95 latency violated SLA: {p95:.2f} ms")

    def test_v6_02_concurrent_multithreaded_sla(self):
        """V6.02: 100 concurrent multithreaded allocations across 8 workers assert P95 < 100 ms."""
        N = 50
        cov = np.eye(N) * 0.04

        def _run_alloc(worker_id: int):
            rng = np.random.RandomState(worker_id)
            mu_w = rng.uniform(0.01, 0.05, N)
            t0 = time.perf_counter()
            res = self.unified_allocator.allocate_portfolio(
                predictions_df=mu_w, prices_dict=cov, regime="BULL_LOW_VOL"
            )
            lat = (time.perf_counter() - t0) * 1000.0
            return lat, len(res)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_run_alloc, range(100)))

        latencies = [r[0] for r in results]
        lengths = [r[1] for r in results]

        p95 = float(np.percentile(latencies, 95))
        self.assertLess(p95, 100.0, f"Concurrent P95 latency violated SLA: {p95:.2f} ms")
        self.assertTrue(all(l == N for l in lengths), "Concurrent allocation length corrupted")


if __name__ == "__main__":
    unittest.main()
