r"""
tests/test_phase120_m2_adversarial_challenger.py
================================================
Milestone 2 (Feature F571) Empirical Adversarial Stress Test Suite.
Author: Empirical Challenger (teamwork_preview_challenger_m2_1)

Adversarial Challenge Objectives:
1. Stress test with degenerate/constant price series and zero volatility regimes.
2. Heavy-tailed Pareto, Cauchy, and Student-t shock sequences (infinite variance).
3. Sequence length boundaries: extremely short (N < s_min) and astronomical (N >= 10,000, N = 25,000).
4. Extreme fluctuation orders q in [-10.0, +10.0] and numerical stability of F_q(s) with epsilon = 10^-14.
5. Invariant verification: strict monotonicity H(q1) >= H(q2) for q1 < q2 across all adversarial series.
6. Mathematical invariants of Legendre singularity spectrum: f(alpha_0) == 1.0, f(alpha) >= 0, alpha(q1) >= alpha(q2).
7. Finite conditioning vector bounds across all 5 market profiles under adversarial inputs.
8. Bit-for-bit SHA-256 parity between primary and mirror paths.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.mfdfa_singularity_alpha_engine as mfdfa_mod
from src.ai.mfdfa_singularity_alpha_engine import (
    MFDFAConfig,
    MFDFASingularityAlphaEngine,
    SingularitySpectrumResult,
    isotonic_pava_decreasing,
    compute_fluctuation_function,
    compute_hurst_surface,
    compute_legendre_transform,
    build_mean_centered_profile,
    fit_local_polynomial_variances,
    generate_log_scales,
)


class TestPhase120M2AdversarialChallenger(unittest.TestCase):
    """Empirical Adversarial Test Suite for Feature F571."""

    @classmethod
    def setUpClass(cls):
        cls.engine = MFDFASingularityAlphaEngine()
        cls.root_file = PROJECT_ROOT / "src" / "ai" / "mfdfa_singularity_alpha_engine.py"
        cls.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "ai" / "mfdfa_singularity_alpha_engine.py"

    # =========================================================================
    # Group 1: Cryptographic Parity & Baseline Integrity
    # =========================================================================
    def test_adv01_sha256_cryptographic_parity(self):
        """Verify 100% bit-for-bit SHA-256 parity between src and trading_system/src."""
        self.assertTrue(self.root_file.exists(), f"Missing {self.root_file}")
        self.assertTrue(self.mirror_file.exists(), f"Missing {self.mirror_file}")

        root_hash = hashlib.sha256(self.root_file.read_bytes()).hexdigest()
        mirror_hash = hashlib.sha256(self.mirror_file.read_bytes()).hexdigest()
        self.assertEqual(root_hash, mirror_hash, "SHA-256 mismatch between primary and mirror engine files!")
        self.assertEqual(root_hash, "25adf2d797d3eb0f1777255f9f59002388ec594bc53d5b146af630fef60a3fdb".lower())

    # =========================================================================
    # Group 2: Degenerate, Constant & Micro-Variance Edge Cases
    # =========================================================================
    def test_adv02_empty_and_sub_minimum_series(self):
        """Stress test ultra-short series (N = 0, 1, 2, 5, 10, 19)."""
        lengths = [0, 1, 2, 5, 10, 19]
        for N in lengths:
            series = np.ones(N, dtype=np.float64) * 42.0 if N > 0 else np.array([], dtype=np.float64)
            res = self.engine.compute(series)
            self.assertIsInstance(res, SingularitySpectrumResult)
            self.assertEqual(res.sample_size, N)
            self.assertEqual(res.h_2, 0.50)
            self.assertEqual(res.delta_alpha, 0.0)
            self.assertEqual(res.f_alpha_0, 1.0)
            self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))

    def test_adv03_pure_constant_series(self):
        """Stress test purely flat series of various constants and lengths."""
        constants = [0.0, 1.0, -100.0, 1e-12, 1e8]
        lengths = [20, 50, 100, 500, 2000]
        for c in constants:
            for n in lengths:
                series = np.full(n, c, dtype=np.float64)
                res = self.engine.compute(series)
                self.assertEqual(res.h_2, 0.50)
                self.assertEqual(res.delta_alpha, 0.0)
                self.assertFalse(res.is_fragility_alert)
                vec = res.to_numpy_vector()
                self.assertTrue(np.all(np.isfinite(vec)))

    def test_adv04_near_zero_variance_perturbation(self):
        """Stress test series with infinitesimal variance (e.g., 1e-16 delta)."""
        np.random.seed(42)
        n = 200
        # Perturbation on order of 1e-16 (below epsilon regularizer 1e-14)
        series = 100.0 + np.random.randn(n) * 1e-16
        res = self.engine.compute(series)
        self.assertTrue(np.all(np.isfinite(res.h_q)))
        self.assertTrue(np.all(np.isfinite(res.f_alpha)))
        self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)
        # Verify strict monotonicity
        hq = np.array(res.h_q)
        self.assertTrue(np.all(np.diff(hq) <= 1e-9), f"Monotonicity violated on micro-variance: {np.diff(hq)}")

    def test_adv05_step_function_and_square_wave(self):
        """Stress test alternating square wave and single step jump."""
        n = 300
        # Alternating square wave
        square_wave = np.array([1.0 if (i // 10) % 2 == 0 else -1.0 for i in range(n)])
        res_sq = self.engine.compute(square_wave)
        self.assertTrue(np.all(np.isfinite(res_sq.to_numpy_vector())))
        self.assertTrue(np.all(np.diff(res_sq.h_q) <= 1e-9))

        # Single catastrophic step jump in the middle
        step_series = np.zeros(n)
        step_series[n // 2 :] = 1000.0
        res_step = self.engine.compute(step_series)
        self.assertTrue(np.all(np.isfinite(res_step.to_numpy_vector())))
        self.assertTrue(np.all(np.diff(res_step.h_q) <= 1e-9))

    def test_adv06_pure_linear_and_quadratic_trends(self):
        """Stress test perfect deterministic polynomial series (linear & quadratic)."""
        n = 250
        t = np.arange(n, dtype=np.float64)
        linear = 2.5 * t + 10.0
        res_lin = self.engine.compute(linear)
        self.assertTrue(np.all(np.isfinite(res_lin.to_numpy_vector())))
        self.assertTrue(np.all(np.diff(res_lin.h_q) <= 1e-9))

        quadratic = 0.05 * (t ** 2) - 1.2 * t + 5.0
        config_quad = MFDFAConfig(poly_order=2)
        engine_quad = MFDFASingularityAlphaEngine(config=config_quad)
        res_quad = engine_quad.compute(quadratic)
        self.assertTrue(np.all(np.isfinite(res_quad.to_numpy_vector())))
        self.assertTrue(np.all(np.diff(res_quad.h_q) <= 1e-9))

    # =========================================================================
    # Group 3: Heavy-Tailed Pareto, Cauchy & Extreme Tail Shocks
    # =========================================================================
    def test_adv07_heavy_tailed_pareto_shocks(self):
        """Stress test Pareto distributed returns with shape alpha in [0.9, 1.2, 1.5, 2.0]."""
        np.random.seed(101)
        shapes = [0.9, 1.2, 1.5, 2.0]
        for shape in shapes:
            n = 500
            # Pareto returns with random sign to model two-sided heavy tails
            magnitudes = np.random.pareto(a=shape, size=n)
            signs = np.random.choice([-1.0, 1.0], size=n)
            pareto_returns = signs * magnitudes
            res = self.engine.compute(pareto_returns)

            # Monotonicity check
            hq = np.array(res.h_q)
            self.assertTrue(np.all(np.diff(hq) <= 1e-9), f"PAVA monotonicity failed for Pareto shape {shape}!")
            # Singularity spectrum checks
            self.assertGreaterEqual(res.delta_alpha, 0.0)
            self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)
            self.assertTrue(np.all(np.array(res.f_alpha) >= 0.0))
            # Conditioning vector checks
            vec = res.to_numpy_vector()
            self.assertEqual(len(vec), 9)
            self.assertTrue(np.all(np.isfinite(vec)))

    def test_adv08_cauchy_extreme_distribution(self):
        """Stress test Cauchy distribution (infinite variance and undefined mean)."""
        np.random.seed(202)
        for trial in range(5):
            cauchy_data = np.random.standard_cauchy(size=600)
            res = self.engine.compute(cauchy_data)
            hq = np.array(res.h_q)
            self.assertTrue(np.all(np.diff(hq) <= 1e-9), f"Monotonicity failed on Cauchy trial {trial}!")
            self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))
            self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)
            self.assertGreater(res.delta_alpha, 0.20, "Cauchy series should exhibit significant multifractality width")

    def test_adv09_student_t_fat_tails(self):
        """Stress test Student-t distribution with degrees of freedom df = 1, 2, 3."""
        np.random.seed(303)
        for df in [1, 2, 3]:
            t_data = np.random.standard_t(df=df, size=500)
            res = self.engine.compute(t_data)
            hq = np.array(res.h_q)
            self.assertTrue(np.all(np.diff(hq) <= 1e-9), f"Monotonicity failed on Student-t df={df}!")
            self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))

    def test_adv10_flash_crash_and_isolated_monster_outliers(self):
        """Stress test flash crash shock: 1000 steps normal noise with 10^8 single spike."""
        np.random.seed(404)
        data = np.random.randn(800)
        data[400] = 1e8  # 100-million standard deviation shock
        data[401] = -1e8
        res = self.engine.compute(data)
        self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))
        self.assertTrue(np.all(np.diff(res.h_q) <= 1e-9))
        self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)

    # =========================================================================
    # Group 4: Extreme Fluctuation Orders q in [-10.0, +10.0]
    # =========================================================================
    def test_adv11_extreme_q_range_minus_10_to_plus_10(self):
        """Test wide q range [-10.0, 10.0] with step 0.5."""
        cfg = MFDFAConfig(q_min=-10.0, q_max=10.0, q_step=0.5)
        engine_wide = MFDFASingularityAlphaEngine(config=cfg)
        np.random.seed(505)
        series = np.cumsum(np.random.randn(500))
        res = engine_wide.compute(series)

        self.assertEqual(len(res.q_values), 41)
        self.assertAlmostEqual(res.q_values[0], -10.0)
        self.assertAlmostEqual(res.q_values[-1], 10.0)
        hq = np.array(res.h_q)
        self.assertTrue(np.all(np.diff(hq) <= 1e-9), "Monotonicity violated on extreme q range [-10, 10]!")
        self.assertTrue(np.all(np.isfinite(hq)))
        self.assertTrue(np.all(np.isfinite(res.f_alpha)))
        self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)

    def test_adv12_fine_grained_q_singularity_limit(self):
        """Verify numerical stability of F_q(s) in tight neighborhood of q = 0 (q = 1e-12, 1e-8, 1e-4)."""
        variances = np.array([0.01, 0.05, 0.2, 0.8, 1.5], dtype=np.float64)
        f0_exact = compute_fluctuation_function(variances, q=0.0)

        small_qs = [1e-12, -1e-12, 1e-8, -1e-8, 1e-4, -1e-4]
        for q in small_qs:
            fq = compute_fluctuation_function(variances, q=q)
            self.assertTrue(np.isfinite(fq))
            self.assertAlmostEqual(fq, f0_exact, places=3, msg=f"Continuity failed at q={q}")

    def test_adv13_extreme_subnormal_variances(self):
        """Verify F_q(s) when segment variances hit machine epsilon floor (1e-14, 1e-18, 0.0)."""
        underflow_variances = np.array([0.0, 1e-20, 1e-18, 1e-16], dtype=np.float64)
        for q in [-5.0, -2.0, 0.0, 2.0, 5.0]:
            fq = compute_fluctuation_function(underflow_variances, q=q, epsilon=1e-14)
            self.assertTrue(np.isfinite(fq))
            self.assertGreaterEqual(fq, 1e-14)

    # =========================================================================
    # Group 5: Sequence Length Limits: Short N < s_min and Astronomical N > 10,000
    # =========================================================================
    def test_adv14_boundary_length_at_minimum_scale(self):
        """Test boundary sequence lengths N = 20, 21, 25, 30 with scale_min = 10."""
        for N in [20, 21, 25, 30]:
            series = np.cumsum(np.random.RandomState(N).randn(N))
            res = self.engine.compute(series)
            self.assertGreaterEqual(len(res.scales), 3)
            self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))
            self.assertTrue(np.all(np.diff(res.h_q) <= 1e-9))

    def test_adv15_astronomical_series_10000_and_25000_samples(self):
        """Stress test astronomical length sequence N = 10,000 and N = 25,000."""
        np.random.seed(606)
        for N in [10000, 25000]:
            series = np.cumsum(np.random.randn(N))
            t0 = time.perf_counter()
            res = self.engine.compute(series)
            elapsed_sec = time.perf_counter() - t0

            self.assertEqual(res.sample_size, N)
            self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))
            self.assertTrue(np.all(np.diff(res.h_q) <= 1e-9))
            self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)
            # Latency should be fast (under 2.5s even for 25,000 points on modern CPU)
            self.assertLess(elapsed_sec, 3.0, f"Astronomical N={N} took {elapsed_sec:.3f}s (exceeds SLA 3.0s)")

    def test_adv16_prime_and_non_divisible_lengths(self):
        """Test prime and odd sequence lengths (N = 251, 503, 1009, 3331)."""
        primes = [251, 503, 1009, 3331]
        for p in primes:
            series = np.sin(np.linspace(0, 20 * np.pi, p)) + 0.1 * np.random.RandomState(p).randn(p)
            res = self.engine.compute(series)
            self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))
            self.assertTrue(np.all(np.diff(res.h_q) <= 1e-9))

    # =========================================================================
    # Group 6: Mathematical Invariants of MF-DFA
    # =========================================================================
    def test_adv17_invariant_monotonicity_across_50_synthetic_universes(self):
        """Exhaustively verify H(q1) >= H(q2) for q1 < q2 across 50 diverse synthetic series."""
        rng = np.random.RandomState(777)
        for seed_idx in range(50):
            case_type = seed_idx % 5
            n = rng.randint(50, 600)
            if case_type == 0:
                # Fractional Brownian motion approximation via cumulative Gaussian
                data = np.cumsum(rng.randn(n))
            elif case_type == 1:
                # Heavy-tailed Student-t
                data = rng.standard_t(df=rng.uniform(1.2, 5.0), size=n)
            elif case_type == 2:
                # Multiplicative cascade / log-normal volatility
                vol = np.exp(np.cumsum(0.05 * rng.randn(n)))
                data = rng.randn(n) * vol
            elif case_type == 3:
                # Sinusoidal regime switching with noise
                data = np.sin(np.linspace(0, 10 * np.pi, n)) + 0.5 * rng.randn(n)
            else:
                # Correlated AR(1) process
                phi = rng.uniform(-0.9, 0.9)
                data = np.zeros(n)
                for t in range(1, n):
                    data[t] = phi * data[t - 1] + rng.randn()

            res = self.engine.compute(data)
            hq = np.array(res.h_q)
            diffs = np.diff(hq)
            # Strict non-increasing: hq[i+1] <= hq[i] -> diffs <= 0
            max_viol = np.max(diffs)
            self.assertLessEqual(max_viol, 1e-9, f"Monotonicity invariant violated on seed {seed_idx}, case {case_type}: max diff = {max_viol}")

    def test_adv18_singularity_spectrum_convexity_and_peak(self):
        """Verify Hölder alpha(q) is non-increasing, f(alpha) is non-negative, and f(alpha_0) == 1.0."""
        rng = np.random.RandomState(888)
        for i in range(15):
            data = np.cumsum(rng.randn(300))
            res = self.engine.compute(data)
            alpha_q = np.array(res.alpha_q)
            # alpha(q) must be non-increasing with respect to q
            self.assertTrue(np.all(np.diff(alpha_q) <= 1e-9), f"Hölder alpha not monotonic on trial {i}")
            # f(alpha) peak at alpha_0 is exactly 1.0
            self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)
            # f(alpha) >= 0 everywhere
            self.assertTrue(np.all(np.array(res.f_alpha) >= 0.0))

    def test_adv19_pava_isotonic_regression_fuzzing(self):
        """Fuzz test PAVA decreasing algorithm on random, reverse, and degenerate float arrays."""
        rng = np.random.RandomState(999)
        for trial in range(100):
            length = rng.randint(2, 50)
            raw = rng.randn(length) * 100.0
            pava_out = isotonic_pava_decreasing(raw)
            # Check length preserved
            self.assertEqual(len(pava_out), length)
            # Check non-increasing monotonicity
            self.assertTrue(np.all(np.diff(pava_out) <= 1e-12), f"PAVA fuzz violation on trial {trial}")

    # =========================================================================
    # Group 7: 5-Market Pre-Calibrated Profiles Under Adversarial Load
    # =========================================================================
    def test_adv20_all_five_market_profiles_adversarial_stress(self):
        """Stress all 5 market empirical profiles (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) with Cauchy shocks."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        np.random.seed(1111)
        cauchy_shocks = np.random.standard_cauchy(size=400)

        for mkt in markets:
            engine_mkt = MFDFASingularityAlphaEngine(market=mkt)
            res = engine_mkt.compute(cauchy_shocks)
            self.assertEqual(res.market, mkt)
            self.assertTrue(np.all(np.isfinite(res.to_numpy_vector())))
            self.assertTrue(np.all(np.diff(res.h_q) <= 1e-9))
            self.assertGreaterEqual(res.fragility_score, 0.0)
            self.assertLessEqual(res.fragility_score, 1.0)
            self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
