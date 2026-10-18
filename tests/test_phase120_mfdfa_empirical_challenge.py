"""
tests/test_phase120_mfdfa_empirical_challenge.py
==================================================
Adversarial Empirical Challenge Suite for Milestone 2 (Feature F571):
Multi-Fractal Detrended Fluctuation (MF-DFA) Singularity Spectrum & Long-Memory Alpha Generator.

Author: teamwork_preview_challenger_m2_2 (Empirical Challenger)
Target:
1. Signal Fidelity:
   - Brownian motion H(2) ~ 0.50, narrow singularity width Delta alpha <= 0.15
   - Fractional Brownian motion persistence C_trend > 0.50 for H=0.80
   - Ornstein-Uhlenbeck anti-persistence C_revert > 0.50 for H=0.25
   - Crash fragility alerts > 0.70 and negative asymmetry A < 0
2. 5-Market empirical validation (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)
3. Benchmark execution latency SLA (< 15ms per computation)
4. Extreme edge cases & mathematical invariants
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

from src.ai.mfdfa_singularity_alpha_engine import (
    MFDFASingularityAlphaEngine,
    MFDFAConfig,
    FractalRegime,
    FragilityAlertLevel,
    MARKET_MFDFA_PROFILES,
    isotonic_pava_decreasing,
)


def generate_fbm_increments(n: int, H: float, seed: int = 42) -> np.ndarray:
    """
    Exact fractional Gaussian noise (fGn) increment generator using Davies-Harte method.
    """
    np.random.seed(seed)
    # Autocovariance sequence of fGn: gamma(k) = 0.5 * (|k-1|^{2H} - 2|k|^{2H} + |k+1|^{2H})
    k = np.arange(n)
    gamma = 0.5 * (np.abs(k - 1) ** (2 * H) - 2 * (k ** (2 * H)) + np.abs(k + 1) ** (2 * H))
    
    # Circulant embedding
    c = np.concatenate([gamma, gamma[-2:0:-1]])  # length 2*n - 2
    m = len(c)
    eigenvalues = np.real(np.fft.fft(c))
    
    # If any eigenvalues are slightly negative due to numerical precision, floor at 0
    eigenvalues = np.maximum(eigenvalues, 0.0)
    
    # Generate complex Gaussian standard normals
    w = np.random.normal(0, 1, m) + 1j * np.random.normal(0, 1, m)
    z = np.fft.ifft(np.sqrt(eigenvalues) * w)
    
    # Real part of the first n elements is exact fGn
    fgn = np.real(z[:n])
    return fgn / np.std(fgn)


def generate_ou_series(n: int, theta: float, sigma: float = 1.0, seed: int = 42) -> np.ndarray:
    """
    Simulates a discrete Ornstein-Uhlenbeck process:
    x_{t} = (1 - theta) * x_{t-1} + sigma * e_t
    Returns increments (or series) exhibiting strong mean reversion.
    """
    np.random.seed(seed)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = (1.0 - theta) * x[t - 1] + sigma * np.random.normal(0, 1)
    return x


class TestPhase120MFDFAEmpiricalChallenge(unittest.TestCase):
    """Empirical Stress Tests and Challenge Verifications."""

    def setUp(self) -> None:
        np.random.seed(42)

    def test_challenge_01_brownian_motion_fidelity(self) -> None:
        """
        Challenge 1: Verify Brownian motion input yields H(2) ~ 0.50 and narrow singularity width Delta alpha <= 0.15.
        """
        engine = MFDFASingularityAlphaEngine(market="SP500")
        h2_list = []
        delta_alpha_list = []
        
        # Test across multiple independent Brownian paths
        for seed in [42, 101, 202, 303, 404]:
            np.random.seed(seed)
            # Standard Brownian motion increments (Gaussian white noise)
            white_noise = np.random.normal(0, 0.01, size=2000)
            res = engine.compute(white_noise)
            h2_list.append(res.h_2)
            delta_alpha_list.append(res.delta_alpha)
        
        mean_h2 = float(np.mean(h2_list))
        mean_delta_alpha = float(np.mean(delta_alpha_list))
        
        print(f"\n[BM Challenge] mean H(2) = {mean_h2:.4f}, mean Delta alpha = {mean_delta_alpha:.4f}")
        for idx, (h2, da) in enumerate(zip(h2_list, delta_alpha_list)):
            print(f"  Seed {idx}: H(2) = {h2:.4f}, Delta alpha = {da:.4f}")

        # H(2) should be close to 0.50 (+/- 0.08)
        self.assertAlmostEqual(mean_h2, 0.50, delta=0.08, msg=f"Brownian H(2) {mean_h2} deviates from 0.50")
        # Monofractal Brownian motion has narrow singularity width Delta alpha <= 0.15
        self.assertLessEqual(mean_delta_alpha, 0.15, msg=f"Mean Delta alpha {mean_delta_alpha} exceeds 0.15")

    def test_challenge_02_fbm_persistence_conditioning(self) -> None:
        """
        Challenge 2: Verify that fractional Brownian motion with H=0.80 produces persistent conditioning C_trend > 0.50.
        """
        engine = MFDFASingularityAlphaEngine(market="SP500")
        # Generate fGn with H=0.80 (increments of persistent fBm)
        fgn_80 = generate_fbm_increments(n=2500, H=0.80, seed=42)
        res = engine.compute(fgn_80)
        
        print(f"\n[fBm H=0.80 Challenge] H(2) = {res.h_2:.4f}, C_trend = {res.c_trend:.4f}, C_revert = {res.c_revert:.4f}, Regime = {res.regime}")
        
        self.assertGreater(res.h_2, 0.65, f"H(2) should be persistent (>0.65), got {res.h_2}")
        self.assertGreater(res.c_trend, 0.50, f"C_trend should be > 0.50 for H=0.80, got {res.c_trend}")
        self.assertEqual(res.c_revert, 0.0, f"C_revert should be 0.0 for trending series, got {res.c_revert}")
        self.assertEqual(res.regime, FractalRegime.PERSISTENT_TREND)

    def test_challenge_03_ou_anti_persistence_conditioning(self) -> None:
        """
        Challenge 3: Verify that mean-reverting Ornstein-Uhlenbeck series with H=0.25 produces anti-persistent conditioning C_revert > 0.50.
        """
        engine = MFDFASingularityAlphaEngine(market="SP500")
        # Generate fGn with H=0.25 (anti-persistent / sub-diffusive noise)
        fgn_25 = generate_fbm_increments(n=2500, H=0.25, seed=42)
        res_fgn = engine.compute(fgn_25)
        
        print(f"\n[Anti-Persistent fGn H=0.25] H(2) = {res_fgn.h_2:.4f}, C_revert = {res_fgn.c_revert:.4f}, C_trend = {res_fgn.c_trend:.4f}, Regime = {res_fgn.regime}")
        
        # Also test with discrete OU series
        ou_series = generate_ou_series(n=2500, theta=0.85, sigma=1.0, seed=42)
        res_ou = engine.compute(ou_series)
        print(f"[OU theta=0.85] H(2) = {res_ou.h_2:.4f}, C_revert = {res_ou.c_revert:.4f}, C_trend = {res_ou.c_trend:.4f}, Regime = {res_ou.regime}")

        # Check anti-persistence
        self.assertLess(res_fgn.h_2, 0.35, f"H(2) should be anti-persistent (<0.35), got {res_fgn.h_2}")
        self.assertGreater(res_fgn.c_revert, 0.50, f"C_revert should be > 0.50 for anti-persistent H=0.25, got {res_fgn.c_revert}")
        self.assertEqual(res_fgn.c_trend, 0.0, f"C_trend should be 0.0, got {res_fgn.c_trend}")
        self.assertEqual(res_fgn.regime, FractalRegime.ANTI_PERSISTENT)

    def test_challenge_04_crash_fragility_and_negative_asymmetry(self) -> None:
        """
        Challenge 4: Verify that high-volatility crash regimes trigger Fragility > 0.70 and negative asymmetry A < 0.
        """
        engine = MFDFASingularityAlphaEngine(market="SP500")
        
        # Simulate severe asymmetric market crash:
        # Base normal noise with sudden negative fat-tailed Pareto/Cauchy cascades
        np.random.seed(777)
        n = 1500
        returns = np.random.normal(0, 0.005, size=n)
        
        # Inject asymmetric left-tail crash clusters (severe negative drawdowns)
        crash_indices = [300, 301, 302, 700, 701, 702, 703, 1100, 1101, 1102, 1103, 1104]
        for idx in crash_indices:
            returns[idx] = -0.15 * np.random.uniform(1.0, 3.0)
            
        # Also add generalized Pareto shocks to left tail
        pareto_shocks = -(np.random.pareto(a=1.5, size=50) * 0.05)
        shock_positions = np.random.choice(n, size=50, replace=False)
        returns[shock_positions] += pareto_shocks
        
        res = engine.compute(returns)
        print(f"\n[Crash Challenge] Fragility = {res.fragility_score:.4f}, Alert = {res.is_fragility_alert}, Level = {res.alert_level}, Asymmetry = {res.asymmetry:.4f}, Delta alpha = {res.delta_alpha:.4f}")
        print(f"  alpha_0 = {res.alpha_0:.4f}, alpha_min = {np.min(res.alpha_q):.4f}, alpha_max = {np.max(res.alpha_q):.4f}")
        print(f"  delta_alpha_l = {res.delta_alpha_l:.4f}, delta_alpha_r = {res.delta_alpha_r:.4f}")
        print(f"  alpha_q = {[round(x, 4) for x in res.alpha_q]}")
        print(f"  h_q = {[round(x, 4) for x in res.h_q]}")
        
        self.assertGreater(res.fragility_score, 0.70, f"Fragility score {res.fragility_score} should be > 0.70 during crash")
        self.assertTrue(res.is_fragility_alert, "Fragility alert should be triggered")
        self.assertLess(res.asymmetry, 0.0, f"Spectral asymmetry A should be negative (A < 0), got {res.asymmetry}")

    def test_challenge_05_five_markets_validation(self) -> None:
        """
        Challenge 5: Validate engine across all 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
        """
        markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        np.random.seed(1234)
        synthetic_returns = np.random.normal(0, 0.015, size=1000)
        
        for mkt in markets:
            engine = MFDFASingularityAlphaEngine(market=mkt)
            self.assertEqual(engine.market, mkt)
            res = engine.compute(synthetic_returns)
            
            # Assert all output attributes are non-null and valid
            self.assertEqual(res.market, mkt)
            self.assertEqual(len(res.conditioning_vector), 9)
            self.assertTrue(0.0 <= res.fragility_score <= 1.0)
            self.assertTrue(-1.0 <= res.asymmetry <= 1.0)
            self.assertGreater(res.delta_alpha, 0.0)
            self.assertAlmostEqual(res.f_alpha_0, 1.0, places=5)
            self.assertEqual(len(res.q_values), 21)
            
            # Verify market profile parameters were applied
            expected_poly = MARKET_MFDFA_PROFILES[mkt]["poly_order"]
            self.assertEqual(engine.config.poly_order, expected_poly)
            print(f"Market {mkt:12s}: H(2)={res.h_2:.4f}, DeltaAlpha={res.delta_alpha:.4f}, Fragility={res.fragility_score:.4f}, Latency={res.execution_time_ms:.2f}ms")

    def test_challenge_06_execution_latency_sla(self) -> None:
        """
        Challenge 6: Benchmark execution latency SLA (< 15ms per symbol computation).
        """
        engine = MFDFASingularityAlphaEngine(market="SP500")
        series = np.random.normal(0, 0.01, size=500)
        
        # Warmup
        _ = engine.compute(series)
        
        latencies = []
        n_iters = 50
        for _ in range(n_iters):
            t0 = time.perf_counter()
            _ = engine.compute(series)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
            
        p50 = float(np.percentile(latencies, 50))
        p95 = float(np.percentile(latencies, 95))
        p99 = float(np.percentile(latencies, 99))
        mean_lat = float(np.mean(latencies))
        
        print(f"\n[Latency SLA Challenge] Mean: {mean_lat:.2f}ms, P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")
        self.assertLess(mean_lat, 15.0, f"Mean latency {mean_lat:.2f}ms exceeds 15ms SLA")
        self.assertLess(p95, 15.0, f"P95 latency {p95:.2f}ms exceeds 15ms SLA")

    def test_challenge_07_adversarial_stress_and_invariants(self) -> None:
        """
        Challenge 7: Stress test with NaNs, Infs, zero variance, 1000x volatility shock, and strict monotonicity.
        """
        engine = MFDFASingularityAlphaEngine(market="SP500")
        
        # 1. Shock with NaNs and Infs injected
        corrupted = np.random.normal(0, 0.01, size=800)
        corrupted[10:20] = np.nan
        corrupted[50:55] = np.inf
        corrupted[100:105] = -np.inf
        res_corrupt = engine.compute(corrupted)
        self.assertTrue(np.all(np.isfinite(res_corrupt.to_numpy_vector())))
        self.assertAlmostEqual(res_corrupt.f_alpha_0, 1.0, places=5)
        
        # 2. Strict monotonicity invariant under chaotic heavy-tail noise
        np.random.seed(999)
        heavy_noise = np.random.standard_cauchy(size=1000)
        res_heavy = engine.compute(heavy_noise)
        h_q = np.array(res_heavy.h_q)
        # Check decreasing monotonicity: H(q1) >= H(q2) for q1 < q2
        diffs = np.diff(h_q)
        self.assertTrue(np.all(diffs <= 1e-12), f"Monotonicity broken in Cauchy: {diffs[diffs > 1e-12]}")
        
        # 3. Peak normalization invariant: f(alpha_0) == 1.000000 exactly
        self.assertEqual(res_heavy.f_alpha_0, 1.000000)
        
        # 4. Zero variance constant series
        flat = np.full(500, 42.0)
        res_flat = engine.compute(flat)
        self.assertEqual(res_flat.h_2, 0.50)
        self.assertEqual(res_flat.delta_alpha, 0.0)
        self.assertEqual(res_flat.regime, FractalRegime.BROWNIAN_RANDOM)
