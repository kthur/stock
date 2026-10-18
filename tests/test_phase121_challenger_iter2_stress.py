"""
tests/test_phase121_challenger_iter2_stress.py
==============================================
Empirical Adversarial Stress Suite by Challenger 1 (Iteration 2).
Deep-probe validation of Feature F575 defect remediation:
1. All-NaN / All-Inf / Boundary NaN/Inf input sanitization.
2. 0-channel path execution across degrees 1..4 without IndexError.
3. Dynamic rough Hurst ceiling and floor enforcement.
4. Sub-4D normalization mechanics (1D, 2D, 3D).
5. High-frequency latency SLA adherence across 5 markets.
"""

from __future__ import annotations

import math
import sys
import time
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.path_signature_alpha_engine import (  # noqa: E402
    PathSignatureAlphaEngine,
    PathSignatureConfig,
    estimate_rough_hurst_np,
)


class TestPhase121ChallengerIter2Stress(unittest.TestCase):
    """Aggressive empirical verification of Feature F575 iteration 2 fixes."""

    def setUp(self) -> None:
        np.random.seed(2026)
        n = 100
        t = np.linspace(0.0, 1.0, n)
        p = 100.0 + np.cumsum(np.random.randn(n) * 0.2)
        v = 1000.0 + np.cumsum(np.abs(np.random.randn(n) * 20.0))
        ofi = np.cumsum(np.random.randn(n) * 10.0)
        self.sample_path = np.column_stack([t, p, v, ofi])

    # -------------------------------------------------------------------------
    # 1. NaN / Inf Sanitization Stress
    # -------------------------------------------------------------------------

    def test_stress_all_nan_path_matrix(self) -> None:
        """Path consisting entirely of NaNs yields a valid, finite 10D conditioning vector."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        all_nan = np.full((60, 4), np.nan)
        out = eng.compute(all_nan)

        self.assertEqual(out.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(
            np.all(np.isfinite(out.alpha_conditioning_vector)),
            f"Non-finite values found in all-nan output: {out.alpha_conditioning_vector}",
        )

    def test_stress_all_inf_path_matrix(self) -> None:
        """Path consisting entirely of +Inf and -Inf yields finite 10D vector."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        all_inf = np.full((60, 4), np.inf)
        all_inf[::2, :] = -np.inf
        out = eng.compute(all_inf)

        self.assertEqual(out.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(
            np.all(np.isfinite(out.alpha_conditioning_vector)),
            f"Non-finite values found in all-inf output: {out.alpha_conditioning_vector}",
        )

    def test_stress_leading_and_trailing_nans(self) -> None:
        """First 10 rows and last 10 rows NaN are cleanly backfilled and forward-filled."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        path = self.sample_path.copy()
        path[:10, :] = np.nan
        path[-10:, :] = np.nan

        out = eng.compute(path)
        self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))

    def test_stress_volatility_series_all_nans(self) -> None:
        """Volatility series containing all NaNs safely falls back to prior without crashing."""
        for mkt, expected_prior in (
            ("SP500", 0.13),
            ("NASDAQ", 0.11),
            ("RUSSELL2000", 0.16),
            ("KOSPI", 0.14),
            ("KOSDAQ", 0.09),
        ):
            eng = PathSignatureAlphaEngine(PathSignatureConfig(market=mkt, degree=2))
            all_nan_vol = [np.nan] * 50
            res = eng.estimate_rough_hurst(all_nan_vol)

            self.assertTrue(math.isfinite(res.h_rough))
            self.assertEqual(res.h_rough, expected_prior, f"Market {mkt} fallback prior mismatch")

    # -------------------------------------------------------------------------
    # 2. 0-Channel Degenerate Path Stress
    # -------------------------------------------------------------------------

    def test_stress_zero_channel_paths_various_shapes_and_degrees(self) -> None:
        """0-channel paths (shape (N, 0)) across varying N and degrees 1..4."""
        for degree in (1, 2, 3, 4):
            eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=degree))
            for length in (0, 1, 2, 10, 100):
                zero_ch = np.zeros((length, 0))
                out = eng.compute(zero_ch)
                self.assertEqual(out.alpha_conditioning_vector.shape, (10,))
                self.assertTrue(
                    np.all(np.isfinite(out.alpha_conditioning_vector)),
                    f"Degree {degree}, length {length} produced non-finite: {out.alpha_conditioning_vector}",
                )

    # -------------------------------------------------------------------------
    # 3. Dynamic Rough Hurst Ceiling and Floor Stress
    # -------------------------------------------------------------------------

    def test_stress_dynamic_rough_ceiling_clamp(self) -> None:
        """When ceiling is set to 0.35, even super-diffusive data is clamped to <= 0.35."""
        n = 500
        fgn = np.random.randn(n)
        super_log_vol = np.zeros(n)
        for i in range(1, n):
            weights = (np.arange(1, i + 1) ** (+0.25))
            super_log_vol[i] = np.sum(fgn[:i] * weights[::-1]) * 0.03
        super_vol = np.exp(super_log_vol)

        res_clamped = estimate_rough_hurst_np(super_vol, rough_ceiling=0.35)
        self.assertLessEqual(res_clamped.h_rough, 0.35 + 1e-9)

        # Unconstrained ceiling allows > 0.50
        res_unclamped = estimate_rough_hurst_np(super_vol, rough_ceiling=0.85)
        self.assertGreater(res_unclamped.h_rough, 0.50)
        self.assertLessEqual(res_unclamped.h_rough, 0.85)

    def test_stress_dynamic_rough_floor_clamp(self) -> None:
        """When floor is set to 0.25, rough sub-diffusive data is clamped to >= 0.25."""
        n = 500
        fgn = np.random.randn(n)
        rough_log_vol = np.zeros(n)
        for i in range(1, n):
            weights = (np.arange(1, i + 1) ** (-0.45))
            rough_log_vol[i] = np.sum(fgn[:i] * weights[::-1]) * 0.05
        rough_vol = np.exp(rough_log_vol)

        res = estimate_rough_hurst_np(rough_vol, rough_floor=0.25)
        self.assertGreaterEqual(res.h_rough, 0.25 - 1e-9)

    # -------------------------------------------------------------------------
    # 4. Sub-4D Normalization Mechanics Stress
    # -------------------------------------------------------------------------

    def test_stress_sub_4d_normalization_1d_2d_3d(self) -> None:
        """Sub-4D paths (1D, 2D, 3D) normalize properly without crash or NaN."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2, normalize_path=True))

        # 1D price path
        prices = np.array([100.0, 102.0, 105.0, 103.0, 108.0])
        out_1d = eng.compute(prices)
        self.assertTrue(np.all(np.isfinite(out_1d.alpha_conditioning_vector)))

        # 2D price + volume path
        pv = np.array([[100.0, 500.0], [102.0, 600.0], [105.0, 550.0]])
        out_2d = eng.compute(pv)
        self.assertTrue(np.all(np.isfinite(out_2d.alpha_conditioning_vector)))

        # 3D price + volume + ofi path
        pvo = np.array([[100.0, 500.0, 10.0], [102.0, 600.0, 15.0], [105.0, 550.0, -5.0]])
        out_3d = eng.compute(pvo)
        self.assertTrue(np.all(np.isfinite(out_3d.alpha_conditioning_vector)))

    def test_stress_sub_4d_zero_initial_price(self) -> None:
        """1D/2D/3D paths starting at 0.0 or negative do not cause ZeroDivisionError or NaN."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2, normalize_path=True))
        zero_start = np.array([[0.0, 100.0], [10.0, 120.0], [15.0, 110.0]])
        out = eng.compute(zero_start)
        self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))

        neg_start = np.array([[-50.0, -100.0], [-40.0, -80.0], [-45.0, -90.0]])
        out_neg = eng.compute(neg_start)
        self.assertTrue(np.all(np.isfinite(out_neg.alpha_conditioning_vector)))

    # -------------------------------------------------------------------------
    # 5. Latency SLA Across 5 Markets
    # -------------------------------------------------------------------------

    def test_stress_latency_sla_all_5_markets(self) -> None:
        """100-tick path latency is < 2.0 ms across all 5 markets."""
        p100 = self.sample_path[:100]
        for mkt in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            eng = PathSignatureAlphaEngine(PathSignatureConfig(market=mkt, degree=2))
            # Warmup
            eng.compute(p100[:20])

            times = []
            for _ in range(20):
                t0 = time.perf_counter()
                _ = eng.compute(p100)
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1000.0)

            median_ms = float(np.median(times))
            self.assertLess(
                median_ms,
                2.0,
                f"Market {mkt} 100-tick median latency {median_ms:.2f} ms exceeded 2.0 ms SLA",
            )


if __name__ == "__main__":
    unittest.main()
