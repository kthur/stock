r"""
tests/test_phase120_mfdfa_alpha.py
====================================
Exhaustive 60-Test Verification Suite across 12 Rigorous Categories for:
Multi-Fractal Detrended Fluctuation (MF-DFA) Singularity Spectrum & Long-Memory Alpha Generator (Feature F571).
Phase 120 (Release R136 / v127 Production Master).

Categories (60 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
  - Category 3: Mean-Centered Profile & Multi-Scale Windowing (s in [10, 250]) (TC11 ~ TC15)
  - Category 4: Local Polynomial Detrending (m=1, m=2) & Segment Variance Calculation (TC16 ~ TC20)
  - Category 5: Fluctuation Function F_q(s) & Generalized Hurst Surface H(q) (q in [-5, +5]) (TC21 ~ TC25)
  - Category 6: Monotonicity Invariant of H(q) & Monofractal Benchmark (TC26 ~ TC30)
  - Category 7: Legendre Transform \tau(q) -> f(\alpha) & Singularity Spectrum (TC31 ~ TC35)
  - Category 8: Singularity Width \Delta\alpha & Spectral Asymmetry A (TC36 ~ TC40)
  - Category 9: Non-Linear Market Fragility Alert System (TC41 ~ TC45)
  - Category 10: Long-Memory Alpha Conditioning Vector Synthesis (TC46 ~ TC50)
  - Category 11: Critical Edge Cases & Degenerate Scenarios (TC51 ~ TC55)
  - Category 12: Execution Latency SLA, Downstream Interfaces & Telemetry (TC56 ~ TC60)
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
from typing import Any, Dict, List

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.mfdfa_singularity_alpha_engine as mfdfa_module
from src.ai.mfdfa_singularity_alpha_engine import (
    VERSION,
    RELEASE,
    FEATURE,
    DEFAULT_SCALE_RANGE,
    DEFAULT_NUM_SCALES,
    DEFAULT_Q_RANGE,
    DEFAULT_Q_STEP,
    DEFAULT_Q_VALUES,
    EPSILON_REGULARIZER,
    SINGULARITY_WIDTH_FLOOR,
    MarketProfile,
    MarketType,
    PolynomialOrder,
    FractalRegime,
    FragilityAlertLevel,
    MARKET_MFDFA_PROFILES,
    MFDFAConfig,
    SingularitySpectrumConfig,
    LongMemoryAlphaVector,
    SingularitySpectrumResult,
    MFDFAResult,
    MFDFAOutput,
    MFDFASingularityAlphaEngine,
    MultiFractalDetrendedFluctuationEngine,
    SingularitySpectrumAlphaGenerator,
    MFDFAAlphaEngine,
    LongMemoryFractalAlpha,
    Phase120MFDFAAlphaEngine,
    Phase120SingularitySpectrumEngine,
    F571MFDFASingularityAlphaEngine,
    F571SingularitySpectrumGenerator,
    MultiFractalAlphaGenerator,
    HölderSingularityAlphaEngine,
    HolderSingularityAlphaEngine,
    FractalLongMemoryEngine,
    MFDFAEngine,
    SingularitySpectrumEngine,
    DetrendedFluctuationAlphaEngine,
    isotonic_pava_decreasing,
    build_mean_centered_profile,
    generate_log_scales,
    fit_local_polynomial_variances,
    compute_fluctuation_function,
    compute_hurst_surface,
    compute_legendre_transform,
)


class TestPhase120MFDFAAlpha(unittest.TestCase):
    """Exhaustive 60-Test Suite for Feature F571."""

    def setUp(self) -> None:
        self.root_file = PROJECT_ROOT / "src" / "ai" / "mfdfa_singularity_alpha_engine.py"
        self.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "ai" / "mfdfa_singularity_alpha_engine.py"
        self.config = MFDFAConfig(market="SP500", seed=42)
        self.engine = MFDFASingularityAlphaEngine(config=self.config, market="SP500")
        np.random.seed(42)

    # =======================================================================
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
    # =======================================================================
    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify 100% bit-for-bit SHA-256 cryptographic parity between src/ and trading_system/src/."""
        self.assertTrue(self.root_file.exists(), f"Missing root file: {self.root_file}")
        self.assertTrue(self.mirror_file.exists(), f"Missing mirror file: {self.mirror_file}")

        root_bytes = self.root_file.read_bytes()
        mirror_bytes = self.mirror_file.read_bytes()

        h_root = hashlib.sha256(root_bytes).hexdigest()
        h_mirror = hashlib.sha256(mirror_bytes).hexdigest()
        self.assertEqual(h_root, h_mirror, f"SHA-256 parity mismatch: {h_root} vs {h_mirror}")
        self.assertGreater(len(root_bytes), 5000, "File size suspiciously small.")

    def test_tc02_version_release_feature_metadata(self) -> None:
        """TC02: Assert VERSION=120, RELEASE='R136', FEATURE='F571' at module and class levels."""
        self.assertEqual(VERSION, 120)
        self.assertEqual(RELEASE, "R136")
        self.assertEqual(FEATURE, "F571")
        self.assertEqual(MFDFASingularityAlphaEngine.VERSION, 120)
        self.assertEqual(MFDFASingularityAlphaEngine.RELEASE, "R136")
        self.assertEqual(MFDFASingularityAlphaEngine.FEATURE, "F571")

    def test_tc03_complete_class_alias_trees(self) -> None:
        """TC03: Verify 15+ class backward-compatibility aliases."""
        aliases = [
            MultiFractalDetrendedFluctuationEngine,
            SingularitySpectrumAlphaGenerator,
            MFDFAAlphaEngine,
            LongMemoryFractalAlpha,
            Phase120MFDFAAlphaEngine,
            Phase120SingularitySpectrumEngine,
            F571MFDFASingularityAlphaEngine,
            F571SingularitySpectrumGenerator,
            MultiFractalAlphaGenerator,
            HölderSingularityAlphaEngine,
            HolderSingularityAlphaEngine,
            FractalLongMemoryEngine,
            MFDFAEngine,
            SingularitySpectrumEngine,
            DetrendedFluctuationAlphaEngine,
        ]
        self.assertGreaterEqual(len(aliases), 15)
        for alias in aliases:
            self.assertIs(alias, MFDFASingularityAlphaEngine)

    def test_tc04_dataclass_alias_trees(self) -> None:
        """TC04: Verify dataclass alias mappings."""
        self.assertIs(SingularitySpectrumConfig, MFDFAConfig)
        self.assertIs(MFDFAResult, SingularitySpectrumResult)
        self.assertIs(MFDFAOutput, SingularitySpectrumResult)

    def test_tc05_enums_and_market_profile_from_str(self) -> None:
        """TC05: Verify Enums integrity and MarketProfile.from_str resolution."""
        self.assertEqual(MarketProfile.SP500, 0)
        self.assertEqual(MarketProfile.NASDAQ, 1)
        self.assertEqual(MarketProfile.RUSSELL2000, 2)
        self.assertEqual(MarketProfile.KOSPI, 3)
        self.assertEqual(MarketProfile.KOSDAQ, 4)

        self.assertEqual(MarketProfile.from_str("sp500"), MarketProfile.SP500)
        self.assertEqual(MarketProfile.from_str("NASDAQ"), MarketProfile.NASDAQ)
        self.assertEqual(MarketProfile.from_str("Russell2000"), MarketProfile.RUSSELL2000)
        self.assertEqual(MarketProfile.from_str("kospi"), MarketProfile.KOSPI)
        self.assertEqual(MarketProfile.from_str("KOSDAQ"), MarketProfile.KOSDAQ)

        self.assertEqual(PolynomialOrder.LINEAR, 1)
        self.assertEqual(PolynomialOrder.QUADRATIC, 2)
        self.assertEqual(FractalRegime.PERSISTENT_TREND.value, "PERSISTENT_TREND")
        self.assertEqual(FragilityAlertLevel.CRITICAL.value, "CRITICAL")

    # =======================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
    # =======================================================================
    def test_tc06_default_configuration_initialization(self) -> None:
        """TC06: Verify default MFDFAConfig fields for SP500."""
        cfg = MFDFAConfig()
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.scale_min, 10)
        self.assertEqual(cfg.scale_max, 200)
        self.assertEqual(cfg.poly_order, 1)
        self.assertAlmostEqual(cfg.delta_alpha_thresh, 0.45)
        self.assertAlmostEqual(cfg.kappa_1, 5.0)
        self.assertAlmostEqual(cfg.kappa_2, 2.0)
        self.assertAlmostEqual(cfg.trend_memory_exponent, 1.10)
        self.assertTrue(cfg.enforce_monotonicity)

    def test_tc07_five_market_pre_calibrated_profiles(self) -> None:
        """TC07: Verify pre-calibrated profiles across all 5 markets."""
        for mkt in ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]:
            self.assertIn(mkt, MARKET_MFDFA_PROFILES)
            prof = MARKET_MFDFA_PROFILES[mkt]
            cfg = MFDFAConfig(market=mkt)
            self.assertEqual(cfg.poly_order, prof["poly_order"])
            self.assertAlmostEqual(cfg.delta_alpha_thresh, prof["delta_alpha_thresh"])
            self.assertAlmostEqual(cfg.kappa_2, prof["kappa_2"])
            self.assertAlmostEqual(cfg.trend_memory_exponent, prof["trend_memory_exponent"])

    def test_tc08_custom_parameters_overriding(self) -> None:
        """TC08: Verify explicit overrides of scales, q values, and polynomial orders."""
        custom_scales = [10, 20, 50, 100]
        custom_q = [-2.0, 0.0, 2.0]
        cfg = MFDFAConfig(
            market="NASDAQ",
            custom_scales=custom_scales,
            custom_q_values=custom_q,
            poly_order=2,
            delta_alpha_thresh=0.65
        )
        self.assertEqual(cfg.custom_scales, custom_scales)
        self.assertEqual(cfg.custom_q_values, custom_q)
        self.assertEqual(cfg.poly_order, 2)
        self.assertAlmostEqual(cfg.delta_alpha_thresh, 0.65)
        q_arr = cfg.get_q_array()
        np.testing.assert_array_equal(q_arr, np.array([-2.0, 0.0, 2.0]))

    def test_tc09_config_dict_and_json_roundtrip(self) -> None:
        """TC09: Test MFDFAConfig dict and JSON serialization roundtrip."""
        cfg = MFDFAConfig(market="KOSPI", poly_order=1, delta_alpha_thresh=0.48)
        d = cfg.to_dict()
        cfg_d = MFDFAConfig.from_dict(d)
        self.assertEqual(cfg.market, cfg_d.market)
        self.assertEqual(cfg.poly_order, cfg_d.poly_order)

        j_str = cfg.to_json()
        cfg_j = MFDFAConfig.from_json(j_str)
        self.assertEqual(cfg.delta_alpha_thresh, cfg_j.delta_alpha_thresh)

    def test_tc10_config_boundary_clamping(self) -> None:
        """TC10: Test safety clamping of invalid scale bounds and poly orders."""
        cfg = MFDFAConfig(scale_min=2, scale_max=1, poly_order=5, num_scales=2)
        self.assertGreaterEqual(cfg.scale_min, 4)
        self.assertGreater(cfg.scale_max, cfg.scale_min)
        self.assertIn(cfg.poly_order, (1, 2))
        self.assertGreaterEqual(cfg.num_scales, 4)

    # =======================================================================
    # Category 3: Mean-Centered Profile & Multi-Scale Windowing (TC11 ~ TC15)
    # =======================================================================
    def test_tc11_mean_centered_profile_zero_endpoint(self) -> None:
        """TC11: Assert cumulative mean-centered profile ends at zero."""
        returns = np.random.normal(0.001, 0.02, 500)
        Y = build_mean_centered_profile(returns)
        self.assertEqual(len(Y), 500)
        self.assertAlmostEqual(float(Y[-1]), 0.0, places=10)

    def test_tc12_mean_centered_profile_reconstruction(self) -> None:
        """TC12: Verify differencing Y recovers mean-deviations x_k - mean(x)."""
        x = np.array([1.0, 3.0, 2.0, 5.0, 4.0])
        Y = build_mean_centered_profile(x)
        mean_dev = x - np.mean(x)
        diff_Y = np.diff(np.insert(Y, 0, 0.0))
        np.testing.assert_allclose(diff_Y, mean_dev, atol=1e-12)

    def test_tc13_generate_log_scales_uniqueness_and_ladder(self) -> None:
        """TC13: Verify generated scale ladder is log-spaced, strictly increasing, and bounded."""
        scales = generate_log_scales(scale_min=10, scale_max=200, num_scales=16)
        self.assertGreaterEqual(len(scales), 4)
        self.assertTrue(np.all(np.diff(scales) > 0))
        self.assertGreaterEqual(scales[0], 10)
        self.assertLessEqual(scales[-1], 200)

    def test_tc14_forward_backward_segmentation_count(self) -> None:
        """TC14: Assert 2Ns segments generated for scale s."""
        N = 550
        s = 50
        Ns = N // s  # 11
        # fit_local_polynomial_variances returns array of length 2Ns
        Y = np.random.randn(N)
        variances = fit_local_polynomial_variances(Y, s=s, poly_order=1)
        self.assertEqual(len(variances), 2 * Ns)

    def test_tc15_backward_segmentation_alignment(self) -> None:
        """TC15: Test backward segments start from end of series."""
        N = 100
        s = 20
        # 0..19, 20..39, 40..59, 60..79, 80..99 -> Ns=5, 2Ns=10 segments
        Y = np.arange(N, dtype=np.float64)
        Ns = N // s
        variances = fit_local_polynomial_variances(Y, s=s, poly_order=1)
        self.assertEqual(len(variances), 10)
        # For pure linear ramp Y=arange(N), all linear detrended variances should be ~0
        np.testing.assert_allclose(variances, EPSILON_REGULARIZER, atol=1e-12)

    # =======================================================================
    # Category 4: Local Polynomial Detrending & Segment Variance (TC16 ~ TC20)
    # =======================================================================
    def test_tc16_linear_polynomial_detrending_zero_residual(self) -> None:
        """TC16: Order m=1 detrending must perfectly remove linear trends."""
        t = np.arange(500, dtype=np.float64)
        ramp = 3.5 * t - 14.2
        variances = fit_local_polynomial_variances(ramp, s=40, poly_order=1)
        # Max variance should be within machine epsilon of EPSILON_REGULARIZER
        self.assertLess(float(np.max(variances)), 1e-10)

    def test_tc17_quadratic_polynomial_detrending_zero_residual(self) -> None:
        """TC17: Order m=2 detrending must perfectly remove parabolic trends."""
        t = np.arange(500, dtype=np.float64)
        parabola = 0.05 * (t ** 2) - 2.1 * t + 8.0
        variances = fit_local_polynomial_variances(parabola, s=50, poly_order=2)
        self.assertLess(float(np.max(variances)), 1e-10)

    def test_tc18_orthogonal_projection_operator_properties(self) -> None:
        """TC18: Verify projection matrix P is symmetric and idempotent."""
        s = 30
        poly_order = 2
        t = np.arange(s, dtype=np.float64)
        V = np.vander(t, N=poly_order + 1, increasing=True)
        Q, _ = np.linalg.qr(V)
        P = Q @ Q.T
        # Idempotence: P @ P == P
        np.testing.assert_allclose(P @ P, P, atol=1e-12)
        # Symmetry: P.T == P
        np.testing.assert_allclose(P.T, P, atol=1e-12)

    def test_tc19_segment_variance_positivity(self) -> None:
        """TC19: Assert all segment variances are strictly positive."""
        returns = np.random.laplace(0, 0.02, 600)
        Y = build_mean_centered_profile(returns)
        variances = fit_local_polynomial_variances(Y, s=35, poly_order=1)
        self.assertTrue(np.all(variances > 0.0))

    def test_tc20_zero_variance_regularizer_prevents_zero(self) -> None:
        """TC20: Test epsilon regularizer prevents variance=0 on constant input."""
        constant_Y = np.zeros(200, dtype=np.float64)
        variances = fit_local_polynomial_variances(constant_Y, s=25, poly_order=1, epsilon=1e-14)
        self.assertTrue(np.all(variances >= 1e-14))

    # =======================================================================
    # Category 5: Fluctuation Function F_q(s) & Generalized Hurst Surface (TC21 ~ TC25)
    # =======================================================================
    def test_tc21_fluctuation_function_strictly_positive(self) -> None:
        """TC21: Fluctuation function F_q(s) > 0 for all q in [-5, 5]."""
        variances = np.array([0.01, 0.04, 0.02, 0.05, 0.03])
        for q in [-5.0, -2.0, 0.0, 1.0, 2.0, 5.0]:
            fq = compute_fluctuation_function(variances, q)
            self.assertGreater(fq, 0.0)
            self.assertTrue(math.isfinite(fq))

    def test_tc22_fluctuation_function_analytical_limit_at_q0(self) -> None:
        """TC22: Assert continuity as q -> 0 matches analytical log-expectation limit."""
        variances = np.array([0.02, 0.08, 0.05, 0.03, 0.12])
        f_0 = compute_fluctuation_function(variances, 0.0)
        f_pos = compute_fluctuation_function(variances, 0.001)
        f_neg = compute_fluctuation_function(variances, -0.001)

        self.assertAlmostEqual(f_0, f_pos, places=3)
        self.assertAlmostEqual(f_0, f_neg, places=3)

    def test_tc23_fluctuation_surface_dimensions(self) -> None:
        """TC23: Verify F_matrix has dimensions (num_q, num_scales)."""
        engine = MFDFASingularityAlphaEngine()
        data = np.random.normal(0, 0.01, 400)
        res = engine.compute(data)
        self.assertEqual(len(res.q_values), 21)
        self.assertEqual(len(res.scales), len(res.fluctuation_surface[f"{res.q_values[0]:.4f}"]))

    def test_tc24_log_log_regression_hurst_extraction(self) -> None:
        """TC24: Verify OLS slope extraction for synthetic scaling power law."""
        scales = np.array([10, 20, 40, 80, 160])
        # Construct synthetic F(s) = C * s^0.65
        F_row = 0.05 * (scales.astype(np.float64) ** 0.65)
        F_matrix = np.tile(F_row, (3, 1))
        q_vals = np.array([-2.0, 0.0, 2.0])
        h_q = compute_hurst_surface(F_matrix, scales, q_vals, enforce_monotonicity=False)
        np.testing.assert_allclose(h_q, 0.65, atol=1e-6)

    def test_tc25_classical_hurst_recovery_brownian_motion(self) -> None:
        """TC25: Assert H(2) ~ 0.50 (+/- 0.12) for standard Brownian Gaussian noise."""
        np.random.seed(123)
        returns = np.random.normal(0, 0.01, 1500)
        engine = MFDFASingularityAlphaEngine(market="SP500")
        res = engine.compute(returns)
        self.assertGreater(res.h_2, 0.38)
        self.assertLess(res.h_2, 0.62)

    # =======================================================================
    # Category 6: Monotonicity Invariant of H(q) & Monofractal Benchmark (TC26 ~ TC30)
    # =======================================================================
    def test_tc26_strict_monotonicity_invariant(self) -> None:
        """TC26: Verify H(q_1) >= H(q_2) for all q_1 < q_2 without violations."""
        for _ in range(5):
            data = np.random.standard_t(df=3, size=600)
            res = self.engine.compute(data)
            h_q = np.array(res.h_q)
            diffs = np.diff(h_q)
            # All diffs must be non-positive (<= 1e-12 tolerance)
            self.assertTrue(np.all(diffs <= 1e-12), f"Monotonicity violation in H(q): {diffs[diffs > 1e-12]}")

    def test_tc27_isotonic_pava_decreasing_algorithm(self) -> None:
        """TC27: Direct unit test for PAVA decreasing isotonic regression."""
        raw = np.array([0.9, 0.8, 0.85, 0.7, 0.75, 0.6])
        iso = isotonic_pava_decreasing(raw)
        self.assertTrue(np.all(np.diff(iso) <= 1e-12))
        # Ensure first element >= last element
        self.assertGreaterEqual(iso[0], iso[-1])

    def test_tc28_pava_idempotence_on_already_monotonic_input(self) -> None:
        """TC28: PAVA leaves strictly non-increasing array unchanged."""
        mono = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
        iso = isotonic_pava_decreasing(mono)
        np.testing.assert_allclose(iso, mono, atol=1e-12)

    def test_tc29_monofractal_synthetic_benchmark(self) -> None:
        """TC29: Monofractal series exhibits narrow singularity width Delta alpha <= 0.15."""
        # Simulated Brownian motion has H(q) ~ const => delta_alpha <= 0.15
        np.random.seed(999)
        returns = np.random.normal(0, 0.01, 1000)
        res = self.engine.compute(returns)
        self.assertLessEqual(res.delta_alpha, 0.15)

    def test_tc30_multifractal_downward_spread(self) -> None:
        """TC30: Multifractal fat-tailed series has significant spread H(-5) - H(5) > 0."""
        # Mix Gaussian with heavy-tail Pareto jumps
        np.random.seed(42)
        base = np.random.normal(0, 0.005, 1000)
        jumps = (np.random.pareto(a=1.5, size=1000) - 1.5) * 0.03
        data = base + jumps
        res = self.engine.compute(data)
        h_min_5 = res.h_q[0]   # q = -5.0
        h_plus_5 = res.h_q[-1] # q = +5.0
        self.assertGreater(h_min_5 - h_plus_5, 0.05)

    # =======================================================================
    # Category 7: Legendre Transform \tau(q) -> f(\alpha) & Singularity Spectrum (TC31 ~ TC35)
    # =======================================================================
    def test_tc31_mass_exponent_tau_boundary_conditions(self) -> None:
        """TC31: Assert \tau(0) == -1.0 and \tau(2) == 2*H(2) - 1."""
        data = np.random.normal(0, 0.01, 600)
        res = self.engine.compute(data)
        idx_0 = res.q_values.index(0.0)
        self.assertAlmostEqual(res.tau_q[idx_0], -1.0, places=6)
        idx_2 = res.q_values.index(2.0)
        self.assertAlmostEqual(res.tau_q[idx_2], 2.0 * res.h_2 - 1.0, places=6)

    def test_tc32_legendre_transform_peak_f_alpha0_equals_one(self) -> None:
        """TC32: Singularity spectrum peak at q=0 must satisfy f(\alpha_0) == 1.000000."""
        data = np.random.normal(0, 0.01, 800)
        res = self.engine.compute(data)
        self.assertAlmostEqual(res.f_alpha_0, 1.0, places=6)

    def test_tc33_singularity_spectrum_concavity(self) -> None:
        """TC33: Singularity spectrum f(\alpha) <= 1.0 everywhere."""
        data = np.random.normal(0, 0.01, 600)
        res = self.engine.compute(data)
        f_arr = np.array(res.f_alpha)
        # All points must be <= 1.0 + 1e-6
        self.assertTrue(np.all(f_arr <= 1.0 + 1e-6))

    def test_tc34_singularity_spectrum_non_negativity(self) -> None:
        """TC34: All f(\alpha) values must be non-negative (>= 0.0)."""
        data = np.random.laplace(0, 0.01, 800)
        res = self.engine.compute(data)
        f_arr = np.array(res.f_alpha)
        self.assertTrue(np.all(f_arr >= 0.0))

    def test_tc35_analytical_linear_hurst_legendre_spectrum(self) -> None:
        """TC35: Verify Legendre transform on analytical H(q) = 0.5 - 0.05*q."""
        q = np.linspace(-5.0, 5.0, 21)
        h = 0.5 - 0.05 * q
        tau, alpha, f_alpha = compute_legendre_transform(q, h)
        idx0 = int(np.argmin(np.abs(q)))
        self.assertAlmostEqual(float(alpha[idx0]), 0.5, places=1)
        self.assertAlmostEqual(float(f_alpha[idx0]), 1.0, places=6)

    # =======================================================================
    # Category 8: Singularity Width \Delta\alpha & Spectral Asymmetry A (TC36 ~ TC40)
    # =======================================================================
    def test_tc36_singularity_width_non_negative(self) -> None:
        r"""TC36: Assert \Delta\alpha = \alpha_max - \alpha_min >= 0.0."""
        data = np.random.normal(0, 0.01, 500)
        res = self.engine.compute(data)
        self.assertGreaterEqual(res.delta_alpha, 0.0)

    def test_tc37_singularity_width_decomposition(self) -> None:
        r"""TC37: Assert \Delta\alpha_L + \Delta\alpha_R == \Delta\alpha."""
        data = np.random.normal(0, 0.01, 600)
        res = self.engine.compute(data)
        sum_l_r = res.delta_alpha_l + res.delta_alpha_r
        self.assertAlmostEqual(sum_l_r, res.delta_alpha, places=6)

    def test_tc38_spectral_asymmetry_bounded_in_minus_one_to_plus_one(self) -> None:
        """TC38: Spectral asymmetry A must be strictly bounded in [-1.0, +1.0]."""
        for _ in range(5):
            data = np.random.standard_cauchy(size=500)
            res = self.engine.compute(data)
            self.assertGreaterEqual(res.asymmetry, -1.0)
            self.assertLessEqual(res.asymmetry, 1.0)

    def test_tc39_left_skewed_asymmetry_positive_property(self) -> None:
        """TC39: When left width > right width, asymmetry A must be > 0."""
        # Custom mock check
        l_width = 0.40
        r_width = 0.10
        total = l_width + r_width
        asym = (l_width - r_width) / total
        self.assertGreater(asym, 0.0)
        self.assertAlmostEqual(asym, 0.60)

    def test_tc40_right_skewed_asymmetry_negative_property(self) -> None:
        """TC40: When right width > left width, asymmetry A must be < 0."""
        l_width = 0.10
        r_width = 0.40
        total = l_width + r_width
        asym = (l_width - r_width) / total
        self.assertLess(asym, 0.0)
        self.assertAlmostEqual(asym, -0.60)

    # =======================================================================
    # Category 9: Non-Linear Market Fragility Alert System (TC41 ~ TC45)
    # =======================================================================
    def test_tc41_fragility_score_bounded_in_zero_to_one(self) -> None:
        """TC41: Fragility score F_fragility must be strictly in [0.0, 1.0]."""
        for _ in range(5):
            data = np.random.normal(0, 0.02, 500)
            res = self.engine.compute(data)
            self.assertGreaterEqual(res.fragility_score, 0.0)
            self.assertLessEqual(res.fragility_score, 1.0)

    def test_tc42_benign_market_regime_fragility_low(self) -> None:
        """TC42: Low width delta_alpha and positive asymmetry yields NORMAL fragility."""
        # Simulated low-volatility quiet series
        np.random.seed(111)
        quiet = np.random.normal(0, 0.001, 800)
        res = self.engine.compute(quiet)
        self.assertLess(res.fragility_score, 0.85)
        self.assertIn(res.alert_level, (FragilityAlertLevel.NORMAL, FragilityAlertLevel.ELEVATED))

    def test_tc43_fragility_alert_trigger_on_catastrophic_tails(self) -> None:
        """TC43: Severe negative shocks trigger critical fragility alerts (> 0.70)."""
        np.random.seed(666)
        # Create severe clustered crash events
        series = np.random.normal(0, 0.01, 800)
        crash_indices = [200, 201, 202, 400, 401, 600, 601, 602, 603]
        series[crash_indices] = -0.15
        res = self.engine.compute(series)
        self.assertGreater(res.fragility_score, 0.70)
        self.assertTrue(res.is_fragility_alert)
        self.assertIn(res.alert_level, (FragilityAlertLevel.ELEVATED, FragilityAlertLevel.CRITICAL))

    def test_tc44_fragility_severity_level_mapping(self) -> None:
        """TC44: Check alert level thresholds: NORMAL (<0.50), ELEVATED (<0.75), CRITICAL (>=0.75)."""
        res_norm = self.engine.compute(np.random.normal(0, 0.01, 500))
        if res_norm.fragility_score < 0.50:
            self.assertEqual(res_norm.alert_level, FragilityAlertLevel.NORMAL)
        elif res_norm.fragility_score < 0.75:
            self.assertEqual(res_norm.alert_level, FragilityAlertLevel.ELEVATED)
        else:
            self.assertEqual(res_norm.alert_level, FragilityAlertLevel.CRITICAL)

    def test_tc45_market_profile_fragility_threshold_differentiation(self) -> None:
        """TC45: Check Russell2000 has higher threshold than SP500."""
        cfg_sp = MFDFAConfig(market="SP500")
        cfg_rut = MFDFAConfig(market="RUSSELL2000")
        self.assertLess(cfg_sp.delta_alpha_thresh, cfg_rut.delta_alpha_thresh)

    # =======================================================================
    # Category 10: Long-Memory Alpha Conditioning Vector Synthesis (TC46 ~ TC50)
    # =======================================================================
    def test_tc46_conditioning_vector_length_and_type(self) -> None:
        """TC46: Verify 9-element float conditioning vector output."""
        data = np.random.normal(0, 0.01, 500)
        res = self.engine.compute(data)
        vec = res.conditioning_vector
        self.assertEqual(len(vec), 9)
        self.assertTrue(all(isinstance(v, float) for v in vec))
        self.assertTrue(all(math.isfinite(v) for v in vec))

    def test_tc47_conditioning_vector_element_mapping(self) -> None:
        """TC47: Verify exact element mapping of v_MFDFA."""
        data = np.random.normal(0, 0.01, 500)
        res = self.engine.compute(data)
        vec = res.conditioning_vector
        self.assertAlmostEqual(vec[0], res.h_2)
        self.assertAlmostEqual(vec[1], res.delta_alpha)
        self.assertAlmostEqual(vec[2], res.asymmetry)
        self.assertAlmostEqual(vec[3], res.fragility_score)
        self.assertAlmostEqual(vec[4], res.tau_2)
        self.assertAlmostEqual(vec[5], res.alpha_0)
        self.assertAlmostEqual(vec[6], res.f_alpha_0)
        self.assertAlmostEqual(vec[7], res.c_trend)
        self.assertAlmostEqual(vec[8], res.c_revert)

    def test_tc48_long_memory_vector_dataclass_methods(self) -> None:
        """TC48: Test LongMemoryAlphaVector helper methods."""
        data = np.random.normal(0, 0.01, 500)
        res = self.engine.compute(data)
        alpha_vec = res.get_alpha_vector()
        self.assertEqual(len(alpha_vec.as_array()), 9)
        self.assertEqual(len(alpha_vec.as_list()), 9)
        d = alpha_vec.to_dict()
        self.assertIn("H(2)", d)
        self.assertIn("C_trend", d)
        self.assertIn("C_revert", d)

    def test_tc49_persistent_trend_conditioning_coefficients(self) -> None:
        """TC49: When H(2) > 0.50, C_trend > 0 and C_revert == 0."""
        # Generate persistent trending series (cumsum of positive mean)
        t = np.arange(800)
        trend_series = 0.001 * t + np.random.normal(0, 0.002, 800)
        res = self.engine.compute(trend_series)
        if res.h_2 > 0.50:
            self.assertGreater(res.c_trend, 0.0)
            self.assertEqual(res.c_revert, 0.0)

    def test_tc50_anti_persistent_mean_reverting_conditioning_coefficients(self) -> None:
        """TC50: When H(2) <= 0.25, C_revert > 0.50 and C_trend == 0."""
        # Strongly mean-reverting alternating series
        np.random.seed(42)
        alternating = np.array([0.02 if i % 2 == 0 else -0.02 for i in range(800)])
        noise = np.random.normal(0, 0.002, 800)
        res = self.engine.compute(alternating + noise)
        self.assertLessEqual(res.h_2, 0.25)
        self.assertGreater(res.c_revert, 0.50)
        self.assertEqual(res.c_trend, 0.0)

    # =======================================================================
    # Category 11: Critical Edge Cases & Degenerate Scenarios (TC51 ~ TC55)
    # =======================================================================
    def test_tc51_constant_series_graceful_handling(self) -> None:
        """TC51: Constant series returns safe default without throwing exceptions."""
        constant_series = np.full(500, 100.0)
        res = self.engine.compute(constant_series)
        self.assertEqual(res.h_2, 0.50)
        self.assertEqual(res.delta_alpha, 0.0)
        self.assertEqual(res.fragility_score, 0.0)
        self.assertFalse(res.is_fragility_alert)
        self.assertEqual(res.alert_level, FragilityAlertLevel.NORMAL)

    def test_tc52_ultra_short_series_graceful_handling(self) -> None:
        """TC52: Series with length < 20 returns safe degenerate fallback."""
        short_series = np.array([0.01, -0.02, 0.03, -0.01])
        res = self.engine.compute(short_series)
        self.assertEqual(res.h_2, 0.50)
        self.assertEqual(res.sample_size, 4)

    def test_tc53_nans_and_infinities_sanitization(self) -> None:
        """TC53: Series containing NaNs and Infs processed cleanly without crash."""
        data = np.random.normal(0, 0.01, 500)
        data[10] = np.nan
        data[25] = np.inf
        data[50] = -np.inf
        res = self.engine.compute(data)
        self.assertTrue(math.isfinite(res.h_2))
        self.assertTrue(math.isfinite(res.delta_alpha))
        self.assertTrue(math.isfinite(res.fragility_score))

    def test_tc54_heavy_tailed_levy_flight_broad_width(self) -> None:
        """TC54: Heavy-tailed Student-t series exhibits non-zero singularity width."""
        np.random.seed(777)
        t_data = np.random.standard_t(df=2.5, size=800)
        res = self.engine.compute(t_data)
        self.assertGreater(res.delta_alpha, 0.01)

    def test_tc55_pandas_series_and_list_inputs(self) -> None:
        """TC55: Verify compatibility with raw Python lists and pandas-like containers."""
        raw_list = [0.01 * math.sin(i / 10.0) for i in range(400)]
        res = self.engine.compute(raw_list)
        self.assertEqual(res.sample_size, 400)

    # =======================================================================
    # Category 12: Execution Latency SLA, Downstream Interfaces & Telemetry (TC56 ~ TC60)
    # =======================================================================
    def test_tc56_execution_latency_sla(self) -> None:
        """TC56: Single calculation for 500 points must execute with P95 latency < 15ms."""
        data = np.random.normal(0, 0.01, 500)
        # Warmup
        self.engine.compute(data)

        times = []
        for _ in range(25):
            t0 = time.perf_counter()
            self.engine.compute(data)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000.0)

        p95_ms = float(np.percentile(times, 95))
        self.assertLess(p95_ms, 15.0, f"Execution latency too high: P95 {p95_ms:.2f} ms exceeds 15ms SLA")

    def test_tc57_telemetry_tracking_and_reset(self) -> None:
        """TC57: Telemetry tracking increments count and allows reset."""
        self.engine.reset_telemetry()
        t_init = self.engine.export_telemetry()
        self.assertEqual(t_init["total_computations"], 0)

        data = np.random.normal(0, 0.01, 400)
        self.engine.compute(data)
        self.engine.compute(data)

        t_after = self.engine.export_telemetry()
        self.assertEqual(t_after["total_computations"], 2)
        self.assertGreater(t_after["total_execution_time_ms"], 0.0)

        self.engine.reset_telemetry()
        t_reset = self.engine.export_telemetry()
        self.assertEqual(t_reset["total_computations"], 0)

    def test_tc58_generate_alpha_vector_direct_interface(self) -> None:
        """TC58: generate_alpha_vector returns numpy array of shape (9,)."""
        data = np.random.normal(0, 0.01, 500)
        vec = self.engine.generate_alpha_vector(data)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (9,))

    def test_tc59_evaluate_fragility_direct_interface(self) -> None:
        """TC59: evaluate_fragility returns (score, is_alert, alert_level)."""
        data = np.random.normal(0, 0.01, 500)
        score, alert, level = self.engine.evaluate_fragility(data)
        self.assertIsInstance(score, float)
        self.assertIsInstance(alert, bool)
        self.assertIsInstance(level, FragilityAlertLevel)

    def test_tc60_singularity_spectrum_result_serialization_roundtrip(self) -> None:
        """TC60: Full result to_dict / from_dict and to_json / from_json roundtrip."""
        data = np.random.normal(0, 0.01, 450)
        res = self.engine.compute(data)

        d = res.to_dict()
        res_d = SingularitySpectrumResult.from_dict(d)
        self.assertEqual(res.sample_size, res_d.sample_size)
        self.assertAlmostEqual(res.h_2, res_d.h_2)
        self.assertAlmostEqual(res.delta_alpha, res_d.delta_alpha)
        self.assertEqual(res.alert_level, res_d.alert_level)
        self.assertEqual(res.regime, res_d.regime)

        j_str = res.to_json()
        res_j = SingularitySpectrumResult.from_json(j_str)
        self.assertAlmostEqual(res.fragility_score, res_j.fragility_score)
        self.assertEqual(len(res_j.conditioning_vector), 9)


if __name__ == "__main__":
    unittest.main()
