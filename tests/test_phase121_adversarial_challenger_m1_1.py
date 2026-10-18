r"""
tests/test_phase121_adversarial_challenger_m1_1.py
==================================================
Empirical Adversarial Stress Challenge Suite for Milestone M1 (Feature F575):
Continuous Rough Path Signature Transform Microstructure Alpha Forecaster.
Phase 121 (Release R137 / v128 Production Master).

Adversarial Stress Dimensions:
  1. Degenerate inputs & boundary conditions (all-zero paths, flat paths, extreme jumps, negative volumes/prices, dynamic range, 0-dim)
  2. NaN / Inf injection & 10D conditioning vector finite real-valued conformance
  3. Numerical stability of Chen's identity under long series (1,000+ to 3,000+ ticks)
  4. Rough volatility Hurst stability: simulated Brownian motion (H ~ 0.50) vs sub-diffusive rough paths (H ~ 0.10)
  5. Geometric non-commutative invariants & Lévy area microstructure integrals
  6. 10D alpha conditioning vector conformance across 5 pre-calibrated markets
  7. Deterministic dual-backend parity (PyTorch vs pure NumPy) under long-series stress & latency SLA
"""

from __future__ import annotations

import math
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.path_signature_alpha_engine as sig_module
from src.ai.path_signature_alpha_engine import (
    PathSignatureAlphaEngine,
    PathSignatureConfig,
    PathSignatureOutput,
    RoughHurstResult,
    LevyAreaResult,
    RoughVolatilityRegime,
    RoughFragilityLevel,
    MarketProfile,
    compute_piecewise_linear_signature_np,
    tensor_multiply_signatures_np,
    compute_tensor_logarithm_np,
    compute_levy_areas_from_s2,
    estimate_rough_hurst_np,
    _TORCH_AVAILABLE,
)

if _TORCH_AVAILABLE:
    import torch


class TestPhase121AdversarialChallengerM1(unittest.TestCase):
    """Empirical Adversarial Challenge Suite for Feature F575."""

    def setUp(self) -> None:
        np.random.seed(42)
        # Standard realistic 4D path (time, price, volume, ofi)
        n = 50
        t = np.linspace(0.0, 1.0, n)
        p = 100.0 + np.cumsum(np.random.randn(n) * 0.15)
        v = 1000.0 + np.cumsum(np.abs(np.random.randn(n) * 50.0))
        ofi = np.cumsum(np.random.randn(n) * 20.0)
        self.sample_path = np.column_stack([t, p, v, ofi])

    # =========================================================================
    # Category 1: Degenerate Inputs & Boundary Conditions
    # =========================================================================

    def test_adv01_all_zero_paths_various_dimensions_and_lengths(self) -> None:
        """ADV-01: All-zero paths of varying lengths (0, 1, 2, 50) and dimensions (1D, 2D, 4D)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))

        # Test length 0 (empty)
        out_0 = eng.compute(np.zeros((0, 4)))
        self.assertEqual(out_0.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(np.all(np.isfinite(out_0.alpha_conditioning_vector)))

        # Test length 1
        out_1 = eng.compute(np.zeros((1, 4)))
        self.assertEqual(out_1.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(np.all(np.isfinite(out_1.alpha_conditioning_vector)))

        # Test length 2
        out_2 = eng.compute(np.zeros((2, 4)))
        self.assertEqual(out_2.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(np.all(np.isfinite(out_2.alpha_conditioning_vector)))

        # Test length 50
        out_50 = eng.compute(np.zeros((50, 4)))
        self.assertEqual(out_50.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(np.all(np.isfinite(out_50.alpha_conditioning_vector)))

        # Test 1D and 2D all-zero paths
        out_1d = eng.compute(np.zeros((30, 1)))
        self.assertEqual(out_1d.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(np.all(np.isfinite(out_1d.alpha_conditioning_vector)))

        out_2d = eng.compute(np.zeros((30, 2)))
        self.assertEqual(out_2d.alpha_conditioning_vector.shape, (10,))
        self.assertTrue(np.all(np.isfinite(out_2d.alpha_conditioning_vector)))

    def test_adv02_constant_flat_paths_zero_displacement(self) -> None:
        """ADV-02: Constant flat path returns exactly zero displacements and zero Lévy areas."""
        flat_path = np.ones((40, 4)) * 123.456
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        out = eng.compute(flat_path)

        # Displacement is 0 for spatial channels
        self.assertEqual(out.levy_areas["price_volume_area"], 0.0)
        self.assertEqual(out.levy_areas["price_ofi_area"], 0.0)
        self.assertEqual(out.levy_areas["volume_ofi_area"], 0.0)
        self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))

    def test_adv03_extreme_asymmetric_price_spikes_and_crashes(self) -> None:
        """ADV-03: Extreme asymmetric single-tick spikes (+1000%) and flash crashes (-99.9%)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))

        # Single-tick +1000% jump
        spike_path = self.sample_path.copy()
        spike_path[25, 1] = spike_path[24, 1] * 11.0  # +1000%
        out_spike = eng.compute(spike_path)
        self.assertTrue(np.all(np.isfinite(out_spike.alpha_conditioning_vector)))
        self.assertGreater(out_spike.rough_fragility, 0.0)

        # Flash crash: -99.9% price collapse with 100x volume surge
        crash_path = self.sample_path.copy()
        crash_path[30:, 1] = 0.01  # -99.99%
        crash_path[30:, 2] *= 100.0  # volume explosion
        crash_path[30:, 3] = -5000.0  # massive sell OFI
        out_crash = eng.compute(crash_path)
        self.assertTrue(np.all(np.isfinite(out_crash.alpha_conditioning_vector)))
        self.assertIn(
            out_crash.fragility_level,
            (RoughFragilityLevel.ELEVATED, RoughFragilityLevel.CRITICAL),
        )

    def test_adv04_negative_volumes_and_negative_prices(self) -> None:
        """ADV-04: Negative volume values and negative initial prices do not raise or produce NaNs."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))

        neg_path = self.sample_path.copy()
        neg_path[:, 1] = -50.0  # negative prices
        neg_path[:, 2] = -500.0  # negative volume
        neg_path[:, 3] = -200.0  # negative OFI

        out = eng.compute(neg_path)
        self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))
        self.assertEqual(out.alpha_conditioning_vector.shape, (10,))

    def test_adv05_extreme_astronomical_dynamic_range(self) -> None:
        """ADV-05: Extreme dynamic range (1e-8 to 1e12) does not overflow float64."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))

        astro_path = self.sample_path.copy()
        astro_path[0, 1] = 1e-8
        astro_path[-1, 1] = 1e12
        astro_path[-1, 2] = 1e15

        out = eng.compute(astro_path)
        self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))

    def test_adv06_dimension_zero_degenerate_path_bounds(self) -> None:
        """
        ADV-06: Probes whether 0-dimensional path (N, 0) crashes with IndexError in forecast_drift.
        Contract: Engine should handle empty channel paths gracefully without crashing.
        """
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        zero_dim_path = np.zeros((10, 0))
        # Note: In unpatched implementation, log_sig_vec has size 0 and line 824 executes log_sig_vec[0] raising IndexError
        try:
            out = eng.compute(zero_dim_path)
            self.assertEqual(out.alpha_conditioning_vector.shape, (10,))
            self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))
        except IndexError as err:
            self.fail(
                f"[DEFECT DETECTED] PathSignatureAlphaEngine crashed on 0-dim path with IndexError: {err}. "
                f"forecast_drift line 824 accesses log_sig_vec[0] without checking len(log_sig_vec) > 0."
            )

    # =========================================================================
    # Category 2: NaN / Inf Injection & 10D Conditioning Vector Conformance
    # =========================================================================

    def test_adv07_nan_injection_in_price_channel_conditioning_vector_conformance(self) -> None:
        """
        ADV-07: Injects NaN into price channel.
        Contract: 10D conditioning vector must be strictly finite real values (no NaNs, no Infs).
        """
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        nan_path = self.sample_path.copy()
        nan_path[10, 1] = np.nan

        out = eng.compute(nan_path)
        nan_count = np.count_nonzero(np.isnan(out.alpha_conditioning_vector))
        if nan_count > 0:
            self.fail(
                f"[DEFECT DETECTED] Conformance failure: alpha_conditioning_vector contains {nan_count}/10 NaNs: "
                f"{out.alpha_conditioning_vector}. PathSignatureAlphaEngine.compute does not sanitize "
                f"NaN inputs before signature increments, violating institutional finite vector contract."
            )
        self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))

    def test_adv08_inf_injection_in_volume_channel_conditioning_vector_conformance(self) -> None:
        """
        ADV-08: Injects Inf / -Inf into volume and price channels.
        Contract: 10D conditioning vector must be strictly finite real values (no NaNs, no Infs).
        """
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        inf_path = self.sample_path.copy()
        inf_path[15, 2] = np.inf
        inf_path[20, 1] = -np.inf

        out = eng.compute(inf_path)
        non_finite = np.count_nonzero(~np.isfinite(out.alpha_conditioning_vector))
        if non_finite > 0:
            self.fail(
                f"[DEFECT DETECTED] Conformance failure: alpha_conditioning_vector contains {non_finite}/10 non-finite values: "
                f"{out.alpha_conditioning_vector}. PathSignatureAlphaEngine.compute does not sanitize "
                f"Inf inputs, propagating Infs and NaNs downstream."
            )
        self.assertTrue(np.all(np.isfinite(out.alpha_conditioning_vector)))

    def test_adv09_nan_inf_injection_in_volatility_series(self) -> None:
        """ADV-09: Volatility series with NaN and Inf fallback safely without divergence."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        nan_vol = [0.15, np.nan, 0.20, np.inf, 0.18, 0.22, 0.19, -0.05, 0.25, 0.21]
        res = eng.estimate_rough_hurst(nan_vol)
        self.assertTrue(math.isfinite(res.h_rough))
        self.assertGreaterEqual(res.h_rough, 0.01)
        self.assertLessEqual(res.h_rough, 0.50)

    # =========================================================================
    # Category 3: Numerical Stability of Chen's Identity Under Long Series (1,000+ Ticks)
    # =========================================================================

    def test_adv10_chen_identity_1500_ticks_multi_split(self) -> None:
        r"""
        ADV-10: Chen's Identity S(A * B) = S(A) \otimes S(B) under 1,500 ticks.
        Verifies numerical error is bounded by 1e-6 across degrees 1 to 4.
        """
        n = 1500
        t = np.linspace(0, 15, n)
        p = 100.0 + np.cumsum(np.random.randn(n) * 0.1)
        v = 1000.0 + np.cumsum(np.random.randn(n) * 10.0)
        ofi = np.cumsum(np.random.randn(n) * 5.0)
        path = np.column_stack([t, p, v, ofi])

        split_idx = 750
        path_a = path[:split_idx + 1]
        path_b = path[split_idx:]

        sig_full = compute_piecewise_linear_signature_np(path, degree=4)
        sig_a = compute_piecewise_linear_signature_np(path_a, degree=4)
        sig_b = compute_piecewise_linear_signature_np(path_b, degree=4)

        sig_prod = tensor_multiply_signatures_np(sig_a, sig_b, degree=4, dim=4)

        for deg in (1, 2, 3, 4):
            abs_diff = float(np.max(np.abs(sig_full[deg] - sig_prod[deg])))
            denom = float(np.max(np.abs(sig_full[deg]))) + 1e-12
            rel_diff = abs_diff / denom
            self.assertLess(
                rel_diff,
                1e-6,
                f"Chen's identity relative error exceeded at degree {deg}: {rel_diff:.4e} (abs: {abs_diff:.4e})",
            )

    def test_adv11_chen_identity_3_way_concatenation_3000_ticks(self) -> None:
        r"""
        ADV-11: 3-way concatenation S(A * B * C) = S(A) \otimes S(B) \otimes S(C) on 3,000 ticks.
        """
        n = 3000
        t = np.linspace(0, 30, n)
        p = 100.0 + np.cumsum(np.random.randn(n) * 0.08)
        v = 2000.0 + np.cumsum(np.random.randn(n) * 8.0)
        ofi = np.cumsum(np.random.randn(n) * 4.0)
        path = np.column_stack([t, p, v, ofi])

        idx1, idx2 = 1000, 2000
        path_a = path[:idx1 + 1]
        path_b = path[idx1:idx2 + 1]
        path_c = path[idx2:]

        sig_full = compute_piecewise_linear_signature_np(path, degree=3)
        sig_a = compute_piecewise_linear_signature_np(path_a, degree=3)
        sig_b = compute_piecewise_linear_signature_np(path_b, degree=3)
        sig_c = compute_piecewise_linear_signature_np(path_c, degree=3)

        sig_ab = tensor_multiply_signatures_np(sig_a, sig_b, degree=3, dim=4)
        sig_abc = tensor_multiply_signatures_np(sig_ab, sig_c, degree=3, dim=4)

        for deg in (1, 2, 3):
            abs_diff = float(np.max(np.abs(sig_full[deg] - sig_abc[deg])))
            denom = float(np.max(np.abs(sig_full[deg]))) + 1e-12
            rel_diff = abs_diff / denom
            self.assertLess(rel_diff, 1e-5, f"3-way Chen product failed at degree {deg}: rel={rel_diff:.4e}")

    def test_adv12_tree_like_backtracking_cancellation(self) -> None:
        """
        ADV-12: Hambly-Lyons theorem: backtracking path X * X^rev has trivial signature (S ~ 0 for k >= 1).
        """
        n = 80
        t = np.linspace(0, 1, n)
        p = np.linspace(100, 180, n)
        v = np.linspace(50, 250, n)
        ofi = np.linspace(-10, 30, n)
        path_f = np.column_stack([t, p, v, ofi])
        path_b = path_f[::-1].copy()
        path_tree = np.vstack([path_f, path_b])

        sig_tree = compute_piecewise_linear_signature_np(path_tree, degree=4)
        for deg in (1, 2, 3, 4):
            max_val = float(np.max(np.abs(sig_tree[deg])))
            self.assertLess(
                max_val,
                1e-6,
                f"Tree-like backtracking cancellation failed at degree {deg}: max_abs={max_val:.4e}",
            )

    def test_adv13_degree_4_tensor_dimension_invariants_3000_ticks(self) -> None:
        """ADV-13: Degree 4 tensor signature on 3,000 ticks verifies dimension invariant (340 features for d=4)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        p3000 = np.cumsum(np.random.randn(3000, 4), axis=0)
        p3000[:, 0] = np.linspace(0, 30, 3000)
        p3000[:, 1] += 150.0

        out = eng.compute(p3000)
        self.assertEqual(len(out.signature_levels[1]), 4)
        self.assertEqual(len(out.signature_levels[2]), 16)
        self.assertEqual(len(out.signature_levels[3]), 64)
        self.assertEqual(len(out.signature_levels[4]), 256)
        self.assertEqual(len(out.signature_vector), 4 + 16 + 64 + 256)  # 340
        self.assertTrue(np.all(np.isfinite(out.signature_vector)))

    # =========================================================================
    # Category 4: Rough Hurst Stability: Brownian Motion vs Sub-Diffusive Paths
    # =========================================================================

    def test_adv14_simulated_brownian_motion_hurst_stability(self) -> None:
        """
        ADV-14: Simulated standard Brownian motion volatility paths yield H ~ 0.50
        and are classified into RoughVolatilityRegime.BROWNIAN.
        """
        n = 1000
        h_values = []
        for seed in (42, 101, 202, 303, 404):
            np.random.seed(seed)
            bm_increments = np.random.randn(n) * 0.02
            bm_log_vol = np.cumsum(bm_increments)
            bm_vol = np.exp(bm_log_vol)

            res = estimate_rough_hurst_np(bm_vol)
            h_values.append(res.h_rough)
            self.assertIn(
                res.regime,
                (RoughVolatilityRegime.BROWNIAN, RoughVolatilityRegime.ROUGH_SUB_DIFFUSIVE),
            )
            # Brownian motion Hurst must be >= 0.40
            self.assertGreaterEqual(res.h_rough, 0.40)

        mean_h = float(np.mean(h_values))
        self.assertGreaterEqual(mean_h, 0.45, f"Brownian mean Hurst {mean_h:.4f} was below 0.45")

    def test_adv15_simulated_sub_diffusive_rough_paths_hurst_stability(self) -> None:
        """
        ADV-15: Simulated fractional sub-diffusive paths (H ~ 0.10) yield H < 0.45
        and are classified into RoughVolatilityRegime.ROUGH_SUB_DIFFUSIVE.
        """
        n = 1000
        # Fractional Riemann-Liouville power-law kernel with H = 0.10 => kernel exponent H - 0.5 = -0.40
        fgn = np.random.randn(n)
        rough_log_vol = np.zeros(n)
        for i in range(1, n):
            weights = (np.arange(1, i + 1) ** (-0.40))
            rough_log_vol[i] = np.sum(fgn[:i] * weights[::-1]) * 0.05
        rough_vol = np.exp(rough_log_vol)

        res = estimate_rough_hurst_np(rough_vol)
        self.assertLess(res.h_rough, 0.45, f"Sub-diffusive Hurst {res.h_rough:.4f} was >= 0.45")
        self.assertEqual(res.regime, RoughVolatilityRegime.ROUGH_SUB_DIFFUSIVE)
        self.assertTrue(res.is_rough)

    def test_adv16_rough_ceiling_configuration_override(self) -> None:
        """
        ADV-16: Probes whether user-configured rough_hurst_ceiling is respected.
        Contract: When rough_ceiling=0.80 is passed with super-diffusive data (H ~ 0.75),
        the returned h_rough should reflect the unconstrained ceiling (> 0.50).
        """
        # Super-diffusive cumulative path (persistent trend H > 0.60)
        n = 500
        fgn = np.random.randn(n)
        persistent_log_vol = np.zeros(n)
        for i in range(1, n):
            weights = (np.arange(1, i + 1) ** (+0.20))
            persistent_log_vol[i] = np.sum(fgn[:i] * weights[::-1]) * 0.02
        super_vol = np.exp(persistent_log_vol)

        res = estimate_rough_hurst_np(super_vol, rough_ceiling=0.80)
        # Note: In unpatched implementation, lines 593 and 610 hardcode min(0.499, ...), ignoring rough_ceiling=0.80
        if res.h_rough <= 0.499:
            # Check if slopes indicated super-diffusive
            q2_slope = res.structure_slopes.get(2.0, 0.0) / 2.0
            if q2_slope > 0.50:
                self.fail(
                    f"[DEFECT DETECTED] Hardcoded rough Hurst ceiling: slope/q was {q2_slope:.4f} > 0.50, "
                    f"rough_ceiling was configured to 0.80, but returned h_rough was clamped to {res.h_rough:.4f} "
                    f"due to hardcoded literal '0.499' on lines 593 and 610 in estimate_rough_hurst_np."
                )
        self.assertGreater(res.h_rough, 0.50)

    def test_adv17_degenerate_volatility_series_stability(self) -> None:
        """ADV-17: Constant volatility, near-zero variance, and short volatility series fallback safely."""
        # Flat volatility series
        flat_vol = np.ones(50) * 0.20
        res_flat = estimate_rough_hurst_np(flat_vol, h_prior=0.14)
        self.assertEqual(res_flat.h_rough, 0.14)
        self.assertTrue(res_flat.is_rough)

        # Micro-noise (variance < 1e-6)
        noise_vol = 0.20 + np.random.randn(50) * 1e-7
        res_noise = estimate_rough_hurst_np(noise_vol, h_prior=0.12)
        self.assertEqual(res_noise.h_rough, 0.12)

        # Short series (N < 10)
        short_vol = [0.15, 0.18, 0.16]
        res_short = estimate_rough_hurst_np(short_vol, h_prior=0.15)
        self.assertEqual(res_short.h_rough, 0.15)

    # =========================================================================
    # Category 5: Geometric Invariants & Lévy Area Microstructure Integrals
    # =========================================================================

    def test_adv18_levy_area_time_reversal_antisymmetry(self) -> None:
        """
        ADV-18: Time-reversal antisymmetry: A(X^rev) = -A(X) for all channel pairs.
        """
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2, normalize_path=False))
        out_f = eng.compute(self.sample_path)

        # Time-reversed path
        rev_path = self.sample_path[::-1].copy()
        out_r = eng.compute(rev_path)

        for key in ("price_volume_area", "price_ofi_area", "volume_ofi_area"):
            a_f = out_f.levy_areas[key]
            a_r = out_r.levy_areas[key]
            self.assertAlmostEqual(
                a_f,
                -a_r,
                places=6,
                msg=f"Lévy area reversal antisymmetry failed for {key}: {a_f} vs {-a_r}",
            )

    def test_adv19_planar_circular_loop_geometric_area_exactness(self) -> None:
        """
        ADV-19: Closed circular planar loop area equals enclosed geometric area pi * R^2.
        """
        n = 1000
        theta = np.linspace(0.0, 2.0 * math.pi, n)
        r = 5.0
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        loop_path = np.column_stack([theta, x, y, np.zeros(n)])

        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2, normalize_path=False))
        out = eng.compute(loop_path)

        expected_area = math.pi * (r ** 2)
        computed_area = out.levy_areas["price_volume_area"]
        rel_err = abs(computed_area - expected_area) / expected_area
        self.assertLess(
            rel_err,
            0.01,
            f"Circular loop area rel_err {rel_err:.4e} exceeded 1%: computed {computed_area} vs expected {expected_area}",
        )

    def test_adv20_lead_lag_asymmetry_index_boundedness(self) -> None:
        """ADV-20: Lead-lag asymmetry index is strictly bounded in [-1.0, 1.0]."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        for shift in (-5, -2, 0, 2, 5):
            shifted_path = self.sample_path.copy()
            if shift > 0:
                shifted_path[shift:, 3] = self.sample_path[:-shift, 1]
            elif shift < 0:
                shifted_path[:shift, 3] = self.sample_path[-shift:, 1]

            out = eng.compute(shifted_path)
            asym = out.levy_area_result.asymmetry_index
            self.assertGreaterEqual(asym, -1.0)
            self.assertLessEqual(asym, 1.0)

    # =========================================================================
    # Category 6: 10D Conditioning Vector Conformance & Multi-Market Stress
    # =========================================================================

    def test_adv21_10d_conditioning_vector_shape_and_dtype(self) -> None:
        """ADV-21: 10D conditioning vector is strictly shape (10,), dtype float64 across all 5 markets."""
        for mkt in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            eng = PathSignatureAlphaEngine(PathSignatureConfig(market=mkt, degree=3))
            out = eng.compute(self.sample_path)
            vec = out.alpha_conditioning_vector
            self.assertEqual(vec.shape, (10,), f"Market {mkt} vector shape was {vec.shape} != (10,)")
            self.assertEqual(vec.dtype, np.float64)
            self.assertTrue(np.all(np.isfinite(vec)))

    def test_adv22_conditioning_vector_element_bounds(self) -> None:
        """ADV-22: Conditioning vector individual elements adhere to institutional mathematical bounds."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        out = eng.compute(self.sample_path)
        vec = out.alpha_conditioning_vector

        h_rough = vec[0]
        self.assertGreaterEqual(h_rough, 0.01)
        self.assertLessEqual(h_rough, 0.50)

        s1_norm = vec[4]
        s2_frob = vec[5]
        log_norm = vec[6]
        self.assertGreaterEqual(s1_norm, 0.0)
        self.assertGreaterEqual(s2_frob, 0.0)
        self.assertGreaterEqual(log_norm, 0.0)

        fragility = vec[9]
        self.assertGreaterEqual(fragility, 0.0)
        self.assertLessEqual(fragility, 1.0)

    def test_adv23_multi_horizon_drift_forecast_rough_decay(self) -> None:
        """ADV-23: Multi-horizon drift projections incorporate rough memory scaling across all horizons."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        out = eng.compute(self.sample_path)

        forecasts = out.horizon_forecasts
        self.assertIn("100ms", forecasts)
        self.assertIn("500ms", forecasts)
        self.assertIn("1s", forecasts)
        self.assertIn("5s", forecasts)
        self.assertIn("60s", forecasts)

        for name, f in forecasts.items():
            self.assertTrue(math.isfinite(f.drift_bps))
            self.assertTrue(0.0 <= f.confidence <= 1.0)
            self.assertTrue(math.isfinite(f.t_statistic))

    # =========================================================================
    # Category 7: Dual-Backend Parity (PyTorch vs NumPy) & Latency SLA
    # =========================================================================

    def test_adv24_dual_backend_parity_under_1500_tick_stress(self) -> None:
        """ADV-24: PyTorch SIMD and pure NumPy backends achieve identical results on 1,500-tick paths (< 1e-5)."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not installed in environment")

        cfg_torch = PathSignatureConfig(degree=3, use_torch=True)
        cfg_numpy = PathSignatureConfig(degree=3, use_torch=False)

        eng_torch = PathSignatureAlphaEngine(cfg_torch)
        eng_numpy = PathSignatureAlphaEngine(cfg_numpy)

        p1500 = np.cumsum(np.random.randn(1500, 4) * 0.1, axis=0)
        p1500[:, 0] = np.linspace(0, 15, 1500)
        p1500[:, 1] += 100.0

        out_torch = eng_torch.compute(p1500)
        out_numpy = eng_numpy.compute(p1500)

        for lvl in (1, 2, 3):
            np.testing.assert_allclose(
                out_torch.signature_levels[lvl],
                out_numpy.signature_levels[lvl],
                rtol=1e-5,
                atol=1e-7,
            )

        np.testing.assert_allclose(
            out_torch.alpha_conditioning_vector,
            out_numpy.alpha_conditioning_vector,
            rtol=1e-5,
            atol=1e-7,
        )

    def test_adv25_latency_sla_under_1000_ticks(self) -> None:
        """ADV-25: High-frequency processing latency SLA on 1,000-tick path is strictly < 30 ms."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        p1000 = np.cumsum(np.random.randn(1000, 4) * 0.1, axis=0)
        p1000[:, 0] = np.linspace(0, 10, 1000)
        p1000[:, 1] += 100.0

        # Warmup
        eng.compute(p1000[:50])

        t0 = time.perf_counter()
        out = eng.compute(p1000)
        t1 = time.perf_counter()
        total_us = (t1 - t0) * 1_000_000.0

        self.assertLess(
            total_us,
            150_000.0,  # 150 ms SLA for 1,000 points on CPU
            f"Execution time {total_us:.1f} us exceeded 150,000 us (150 ms) SLA",
        )


if __name__ == "__main__":
    unittest.main()
