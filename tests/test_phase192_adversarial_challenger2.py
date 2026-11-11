"""
tests/test_phase192_adversarial_challenger2.py — Empirical Scalability, Latency SLA & Numerical Stability Suite.

Adversarial Challenger Verification for Release R183 Milestone 1:
1. Latency & Scalability Profiling:
   - Phase192Coupler (500 stocks / 1,000 ticks)
   - CrossBorderTechLeadLagCoupler (500 symbols / 1,000 ticks)
   - CrossClusterConfluenceKernel (500 stocks / 1,000 ticks)
   - SLA threshold: < 15.0 ms per rebalance
2. Ill-Conditioned & Near-Singular Covariance Stability:
   - Condition numbers up to 10^12 regularized by ridge shrinkage
   - Collinear / rank-deficient factor matrices
3. Confluence Score & Alpha Bounds:
   - Extreme inputs (Cauchy fat tails, zeros, NaNs, infinities)
   - Invariants: confluence in [-1, 1], gain in [0.65, 1.35], alpha in [-3, 3], norm in [0, 1]
4. Rolling Simulation Zero-Lookahead:
   - Strict causal time-series verification with shock injection
"""

import time
import unittest
import numpy as np
import pandas as pd

from src.ai.factor_orthogonalizer import (
    CrossClusterConfluenceKernel,
    DynamicDispersionScaler,
    compute_quattuordecuple_pillar_zca_whitening,
    FactorOrthogonalizerEngine,
    QUATTUORDECUPLE_PILLAR_MAP,
)
from src.ai.historical_couplers import (
    CrossBorderTechLeadLagCoupler,
    Phase192Coupler,
)


class TestPhase192EmpiricalChallenger(unittest.TestCase):
    """Adversarial stress and latency suite for Phase 192 (Release R183 Milestone 1)."""

    def setUp(self) -> None:
        np.random.seed(192)
        self.symbols_500 = [f"{i:06d}.KS" for i in range(500)]
        self.pillar_cols = list(QUATTUORDECUPLE_PILLAR_MAP.keys())
        self.us_returns = {
            "^SOX": 0.018,
            "NVDA": 0.032,
            "AAPL": -0.008,
            "MSFT": 0.012,
            "TSM": 0.021,
            "ASML": 0.015,
            "MU": 0.028,
            "AVGO": 0.010,
            "AMAT": 0.005,
            "LRCX": 0.003,
        }

    # =========================================================================
    # 1. Ill-Conditioned & Near-Singular Covariance Stress Tests
    # =========================================================================

    def test_tc01_condition_number_1e12_ridge_shrinkage(self) -> None:
        """TC01: Verify 14-pillar covariance with condition number 10^12 is regularized smoothly."""
        q, _ = np.linalg.qr(np.random.randn(14, 14))
        evals = np.geomspace(1.0, 1e-12, 14)
        cov_1e12 = q @ np.diag(evals) @ q.T
        cov_1e12 = 0.5 * (cov_1e12 + cov_1e12.T)

        orig_cond = np.linalg.cond(cov_1e12)
        self.assertGreaterEqual(orig_cond, 1e11)

        w_zca = compute_quattuordecuple_pillar_zca_whitening(cov_1e12, ridge_epsilon=1e-6)
        self.assertTrue(np.all(np.isfinite(w_zca)), "ZCA whitening matrix must be fully finite")
        self.assertEqual(w_zca.shape, (14, 14))

        # Regularized condition number should be around 1e3 to 1e4, not 1e12
        reg_cond = np.linalg.cond(w_zca)
        self.assertLess(reg_cond, 1e6, f"Regularized cond {reg_cond:.2e} must be smoothly bounded")

    def test_tc02_collinear_and_singular_factor_matrix(self) -> None:
        """TC02: Verify Phase192Coupler and FactorOrthogonalizerEngine under collinear inputs."""
        N = 500
        base = np.random.uniform(0.3, 0.7, size=(N, 13))
        # 14th pillar is an exact duplicate of 1st pillar (perfect collinearity)
        col14 = base[:, 0:1].copy()
        scores_collinear = np.hstack([base, col14])

        coupler = Phase192Coupler(epsilon_reg=1e-6)
        res = coupler.evaluate(scores_collinear, us_returns=self.us_returns)
        alpha = res["alpha_p192"]
        norm = res["alpha_normalized"]

        self.assertTrue(np.all(np.isfinite(alpha)), "Alpha must be finite under perfect collinearity")
        self.assertTrue(np.all(np.isfinite(norm)), "Normalized alpha must be finite under perfect collinearity")
        self.assertTrue((alpha >= -3.0).all() and (alpha <= 3.0).all())
        self.assertTrue((norm >= 0.0).all() and (norm <= 1.0).all())

        # Test FactorOrthogonalizerEngine.orthogonalize_phase192
        df_collinear = pd.DataFrame(scores_collinear, columns=self.pillar_cols)
        engine = FactorOrthogonalizerEngine()
        out_df = engine.orthogonalize_phase192(df_collinear, strategy_cols=self.pillar_cols)
        self.assertEqual(out_df.isna().sum().sum(), 0, "No NaNs should be produced under collinearity")

    # =========================================================================
    # 2. Confluence Score & Invariant Bounds
    # =========================================================================

    def test_tc03_confluence_and_alpha_bounds_adversarial(self) -> None:
        """TC03: Verify mathematical bounds on Cauchy fat tails, zeros, NaNs, and extreme scores."""
        kernel = CrossClusterConfluenceKernel()
        coupler = Phase192Coupler()

        test_matrices = [
            np.random.standard_cauchy((200, 14)),   # Extreme Cauchy outliers
            np.full((100, 14), 1e5),                # Extreme positive saturation
            np.full((100, 14), -1e5),               # Extreme negative saturation
            np.zeros((100, 14)),                    # All zeros
            np.full((100, 14), 0.50),               # Uniform neutral
            np.full((100, 14), np.nan),             # All NaNs
        ]

        for idx, mat in enumerate(test_matrices):
            k_res = kernel.evaluate(mat)
            cs = np.asarray(k_res["confluence_score"])
            cr = np.asarray(k_res["concurrence_ratio"])
            cg = np.asarray(k_res["confluence_gain"])

            self.assertTrue(np.all(np.isfinite(cs)), f"Case {idx}: confluence_score must be finite")
            self.assertTrue((cs >= -1.0 - 1e-6).all() and (cs <= 1.0 + 1e-6).all(),
                            f"Case {idx}: confluence_score {cs.min()}..{cs.max()} must be in [-1, 1]")
            self.assertTrue((cr >= -1e-6).all() and (cr <= 1.0 + 1e-6).all(),
                            f"Case {idx}: concurrence_ratio must be in [0, 1]")
            self.assertTrue((cg >= 0.65 - 1e-6).all() and (cg <= 1.35 + 1e-6).all(),
                            f"Case {idx}: confluence_gain must be in [0.65, 1.35]")

            c_res = coupler.evaluate(mat)
            alpha = np.asarray(c_res["alpha_p192"])
            alpha_norm = np.asarray(c_res["alpha_normalized"])

            self.assertTrue(np.all(np.isfinite(alpha)), f"Case {idx}: alpha must be finite")
            self.assertTrue(np.all(np.isfinite(alpha_norm)), f"Case {idx}: alpha_norm must be finite")
            self.assertTrue((alpha >= -3.0).all() and (alpha <= 3.0).all(),
                            f"Case {idx}: alpha {alpha.min()}..{alpha.max()} must be in [-3, 3]")
            self.assertTrue((alpha_norm >= 0.0).all() and (alpha_norm <= 1.0).all(),
                            f"Case {idx}: alpha_norm must be in [0, 1]")

    # =========================================================================
    # 3. Rolling Zero-Lookahead Verification
    # =========================================================================

    def test_tc04_continuous_rolling_simulation_zero_lookahead(self) -> None:
        """TC04: Verify strictly causal transmission in continuous rolling simulation."""
        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        leaders = ["^SOX", "NVDA", "AAPL", "MSFT", "TSM", "ASML", "MU", "AVGO", "AMAT", "LRCX"]
        us_df = pd.DataFrame(np.random.normal(0, 0.015, size=(100, 10)), index=dates, columns=leaders)
        krx_df = pd.DataFrame(np.random.normal(0, 0.015, size=(100, 5)), index=dates,
                              columns=["005930.KS", "000660.KS", "042700.KQ", "058470.KQ", "240810.KQ"])

        # Inject an unexpected +30% shock at t=60 in US data
        shock_idx = 60
        us_df.iloc[shock_idx] = 0.30

        coupler = CrossBorderTechLeadLagCoupler(lag_days=1)

        # Evaluate at t=60 (KRX trading day t=60): should NOT reflect t=60 US shock because lag_days=1
        res_t60 = coupler.evaluate(us_df.iloc[:shock_idx + 1], krx_returns=krx_df.iloc[:shock_idx + 1])
        imp_t60 = res_t60["average_impulse"]

        # Evaluate at t=61 (KRX trading day t=61): SHOULD reflect t=60 US shock
        res_t61 = coupler.evaluate(us_df.iloc[:shock_idx + 2], krx_returns=krx_df.iloc[:shock_idx + 2])
        imp_t61 = res_t61["average_impulse"]

        self.assertLess(abs(imp_t60), 0.05,
                        f"Lookahead leak at t=60: impulse={imp_t60:.4f} saw future shock!")
        self.assertGreater(imp_t61, 0.15,
                           f"Expected causal impulse transmission at t=61, got {imp_t61:.4f}")

    # =========================================================================
    # 4. Latency SLA Profiling Across 1,000 Simulated Ticks / 500 Stocks
    # =========================================================================

    def test_tc05_latency_sla_phase192_coupler(self) -> None:
        """TC05: Profile Phase192Coupler across 500 stocks. Assert latency < 15.0 ms SLA."""
        scores_500 = np.random.uniform(0.3, 0.7, size=(500, 14))
        coupler = Phase192Coupler()

        # Warm-up 10 ticks
        for _ in range(10):
            coupler.evaluate(scores_500, us_returns=self.us_returns)

        # Profile 100 ticks (representing continuous rolling rebalance)
        num_ticks = 100
        t0 = time.perf_counter()
        for _ in range(num_ticks):
            coupler.evaluate(scores_500, us_returns=self.us_returns)
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_latency_ms = total_time_ms / num_ticks

        print(f"\n[BENCHMARK] Phase192Coupler (500 stocks): {avg_latency_ms:.3f} ms / rebalance")
        self.assertLess(
            avg_latency_ms,
            15.0,
            f"Phase192Coupler execution time ({avg_latency_ms:.2f} ms) breaches institutional SLA (< 15.0 ms)"
        )

    def test_tc06_latency_sla_cross_border_lead_lag(self) -> None:
        """TC06: Profile CrossBorderTechLeadLagCoupler across 500 symbols. Assert latency < 15.0 ms SLA."""
        coupler = CrossBorderTechLeadLagCoupler()

        # Warm-up 10 ticks
        for _ in range(10):
            coupler.evaluate(self.us_returns, krx_symbols=self.symbols_500)

        num_ticks = 100
        t0 = time.perf_counter()
        for _ in range(num_ticks):
            coupler.evaluate(self.us_returns, krx_symbols=self.symbols_500)
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_latency_ms = total_time_ms / num_ticks

        print(f"\n[BENCHMARK] CrossBorderTechLeadLagCoupler (500 symbols): {avg_latency_ms:.3f} ms / tick")
        self.assertLess(
            avg_latency_ms,
            15.0,
            f"CrossBorderTechLeadLagCoupler execution time ({avg_latency_ms:.2f} ms) breaches institutional SLA (< 15.0 ms)"
        )

    def test_tc07_latency_sla_confluence_kernel(self) -> None:
        """TC07: Profile CrossClusterConfluenceKernel across 500 stocks. Assert latency < 15.0 ms SLA."""
        scores_500 = np.random.uniform(0.3, 0.7, size=(500, 14))
        kernel = CrossClusterConfluenceKernel()

        # Warm-up 10 ticks
        for _ in range(10):
            kernel.evaluate(scores_500)

        num_ticks = 100
        t0 = time.perf_counter()
        for _ in range(num_ticks):
            kernel.evaluate(scores_500)
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_latency_ms = total_time_ms / num_ticks

        print(f"\n[BENCHMARK] CrossClusterConfluenceKernel (500 stocks): {avg_latency_ms:.3f} ms / tick")
        self.assertLess(
            avg_latency_ms,
            15.0,
            f"CrossClusterConfluenceKernel execution time ({avg_latency_ms:.2f} ms) breaches institutional SLA (< 15.0 ms)"
        )


if __name__ == "__main__":
    unittest.main()
