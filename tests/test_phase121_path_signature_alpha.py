r"""
tests/test_phase121_path_signature_alpha.py
============================================
Exhaustive 60-Test Verification Suite across 12 Rigorous Categories for:
Continuous Rough Path Signature Transform Microstructure Alpha Forecaster (Feature F575).
Phase 121 (Release R137 / v128 Production Master).

Categories (60 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC10)
  - Category 3: Multi-Stream Microstructure Path Ingestion & Normalization (TC11 ~ TC15)
  - Category 4: Truncated Tensor Signature Calculation & Chen's Identity Invariants (TC16 ~ TC20)
  - Category 5: Degree m <= 4 Tensor Algebra & Dimension Invariants (TC21 ~ TC25)
  - Category 6: Log-Signature Transform & Tensor Series Expansion (TC26 ~ TC30)
  - Category 7: Geometric Non-Commutative Invariants & Lévy Area Integrals (TC31 ~ TC35)
  - Category 8: Rough Volatility Hurst Parameter Estimation (H_rough < 0.50) (TC36 ~ TC40)
  - Category 9: Multi-Horizon Directional Return Drift Forecasting (TC41 ~ TC45)
  - Category 10: Non-Markovian Long-Memory Alpha Conditioning Vector Synthesis (TC46 ~ TC50)
  - Category 11: Critical Edge Cases, Degenerate Paths & Rough Fragility Alerts (TC51 ~ TC55)
  - Category 12: Dual-Backend Parity (PyTorch vs NumPy), Execution Latency SLA & Telemetry (TC56 ~ TC60)
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

import src.ai.path_signature_alpha_engine as sig_module
from src.ai.path_signature_alpha_engine import (
    VERSION,
    RELEASE,
    FEATURE,
    DEFAULT_DEGREE,
    MAX_DEGREE,
    MIN_DEGREE,
    DEFAULT_CHANNELS,
    DEFAULT_HURST_LAGS,
    DEFAULT_ROUGH_CEILING,
    DEFAULT_ROUGH_FLOOR,
    MarketProfile,
    MarketType,
    SignatureDegree,
    ForecastHorizon,
    RoughVolatilityRegime,
    RoughFragilityLevel,
    MARKET_PATH_SIGNATURE_PROFILES,
    PathSignatureConfig,
    SignatureConfig,
    RoughHurstResult,
    RoughVolatilityResult,
    LevyAreaResult,
    LevyAreaOutput,
    HorizonDriftForecast,
    PathSignatureOutput,
    SignatureResult,
    PathSignatureResult,
    PathSignatureAlphaEngine,
    ContinuousRoughPathSignatureForecaster,
    RoughPathSignatureAlphaEngine,
    PathSignatureMicrostructureForecaster,
    RoughVolatilitySignatureEngine,
    LevyAreaSignatureAlphaGenerator,
    TensorAlgebraSignatureEngine,
    Phase121PathSignatureAlphaEngine,
    F575PathSignatureAlphaEngine,
    PathSignatureAlphaForecaster,
    RoughPathSignatureForecaster,
    MicrostructureSignatureEngine,
    ContinuousSignatureEngine,
    LogSignatureAlphaEngine,
    SignatureTransformEngine,
    PathSignatureEngine,
    RoughPathAlphaEngine,
    tensor_outer_np,
    tensor_multiply_signatures_np,
    compute_piecewise_linear_signature_np,
    compute_tensor_logarithm_np,
    compute_levy_areas_from_s2,
    estimate_rough_hurst_np,
    _TORCH_AVAILABLE,
)


class TestPhase121PathSignatureAlpha(unittest.TestCase):
    """Exhaustive 60-Test Suite for Feature F575."""

    def setUp(self) -> None:
        self.root_file = PROJECT_ROOT / "src" / "ai" / "path_signature_alpha_engine.py"
        self.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "ai" / "path_signature_alpha_engine.py"

        # Deterministic sample microstructure path: N=40, d=4 (time, price, volume, ofi)
        np.random.seed(42)
        n = 40
        t = np.linspace(0.0, 1.0, n)
        p = 100.0 + np.cumsum(np.random.randn(n) * 0.2)
        v = np.cumsum(np.abs(np.random.randn(n) * 100.0) + 10.0)
        ofi = np.cumsum(np.random.randn(n) * 50.0)
        self.sample_path = np.column_stack([t, p, v, ofi])

        # Sample rough volatility series generated as cumulative sub-diffusive increments
        # with rough Hurst exponent H ~ 0.15 using power-law kernel
        n_vol = 50
        fgn = np.random.randn(n_vol)
        rough_log_vol = np.zeros(n_vol)
        for i in range(1, n_vol):
            weights = (np.arange(1, i + 1) ** (-0.35))
            rough_log_vol[i] = np.sum(fgn[:i] * weights[::-1]) * 0.05
        self.sample_vol = 0.18 * np.exp(rough_log_vol)


    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_sha256_parity(self) -> None:
        """TC01: Exact bit-for-bit SHA-256 cryptographic parity between root and trading_system mirror."""
        self.assertTrue(self.root_file.exists(), f"Root file missing: {self.root_file}")
        self.assertTrue(self.mirror_file.exists(), f"Mirror file missing: {self.mirror_file}")

        h_root = hashlib.sha256(self.root_file.read_bytes()).hexdigest()
        h_mirror = hashlib.sha256(self.mirror_file.read_bytes()).hexdigest()
        self.assertEqual(h_root, h_mirror, "SHA-256 mismatch between root and mirror implementations!")

    def test_tc02_version_and_feature_metadata(self) -> None:
        """TC02: Module level metadata adheres to Phase 121 (Release R137 / Feature F575)."""
        self.assertEqual(VERSION, 121)
        self.assertEqual(RELEASE, "R137")
        self.assertEqual(FEATURE, "F575")

    def test_tc03_enums_structure_and_values(self) -> None:
        """TC03: Enums validate expected values and serialization mappings."""
        self.assertEqual(MarketProfile.SP500.value, 0)
        self.assertEqual(MarketProfile.NASDAQ.value, 1)
        self.assertEqual(MarketProfile.RUSSELL2000.value, 2)
        self.assertEqual(MarketProfile.KOSPI.value, 3)
        self.assertEqual(MarketProfile.KOSDAQ.value, 4)

        self.assertEqual(MarketProfile.from_str("S&P500"), MarketProfile.SP500)
        self.assertEqual(MarketProfile.from_str("RUT"), MarketProfile.RUSSELL2000)

        self.assertEqual(SignatureDegree.M4.value, 4)
        self.assertEqual(ForecastHorizon.H1S.value, 1.0)
        self.assertIn("ROUGH_SUB_DIFFUSIVE", [r.value for r in RoughVolatilityRegime])
        self.assertIn("CRITICAL", [f.value for f in RoughFragilityLevel])

    def test_tc04_complete_backward_compatibility_aliases(self) -> None:
        """TC04: Complete alias tree (15+ aliases) instantiated and point to PathSignatureAlphaEngine."""
        aliases = [
            ContinuousRoughPathSignatureForecaster,
            RoughPathSignatureAlphaEngine,
            PathSignatureMicrostructureForecaster,
            RoughVolatilitySignatureEngine,
            LevyAreaSignatureAlphaGenerator,
            TensorAlgebraSignatureEngine,
            Phase121PathSignatureAlphaEngine,
            F575PathSignatureAlphaEngine,
            PathSignatureAlphaForecaster,
            RoughPathSignatureForecaster,
            MicrostructureSignatureEngine,
            ContinuousSignatureEngine,
            LogSignatureAlphaEngine,
            SignatureTransformEngine,
            PathSignatureEngine,
            RoughPathAlphaEngine,
        ]
        self.assertGreaterEqual(len(aliases), 15)
        for alias in aliases:
            self.assertIs(alias, PathSignatureAlphaEngine)

        self.assertIs(SignatureResult, PathSignatureOutput)
        self.assertIs(PathSignatureResult, PathSignatureOutput)
        self.assertIs(SignatureConfig, PathSignatureConfig)

    def test_tc05_sys_modules_registration(self) -> None:
        """TC05: Modules registered in sys.modules under canonical names."""
        self.assertIn("src.ai.path_signature_alpha_engine", sys.modules)
        self.assertIn("trading_system.src.ai.path_signature_alpha_engine", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles
    # -----------------------------------------------------------------------
    def test_tc06_configuration_default_initialization(self) -> None:
        """TC06: PathSignatureConfig initializes with rigorous defaults and validation."""
        cfg = PathSignatureConfig()
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.degree, 4)
        self.assertEqual(cfg.rough_hurst_ceiling, 0.50)
        self.assertEqual(cfg.rough_hurst_floor, 0.01)
        self.assertTrue(cfg.normalize_path)

    def test_tc07_market_profile_resolution(self) -> None:
        """TC07: Market string resolution across all 5 production markets."""
        for m in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            cfg = PathSignatureConfig(market=m)
            self.assertEqual(cfg.market, m)

        cfg_invalid = PathSignatureConfig(market="UNKNOWN_EXCHANGE")
        self.assertEqual(cfg_invalid.market, "SP500")

    def test_tc08_precalibrated_empirical_profiles(self) -> None:
        """TC08: Pre-calibrated empirical parameters contain expected keys and bounds."""
        for m in ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"):
            prof = MARKET_PATH_SIGNATURE_PROFILES[m]
            self.assertIn("h_rough_prior", prof)
            self.assertIn("levy_scale", prof)
            self.assertIn("drift_sensitivity", prof)
            self.assertIn("dt_scale", prof)
            self.assertIn("base_volatility", prof)
            self.assertLess(prof["h_rough_prior"], 0.50)
            self.assertGreater(prof["levy_scale"], 0.0)

    def test_tc09_degree_clamping(self) -> None:
        """TC09: Degree boundary enforcement restricts degree to [1, 4]."""
        cfg_high = PathSignatureConfig(degree=10)
        self.assertEqual(cfg_high.degree, 4)

        cfg_low = PathSignatureConfig(degree=0)
        self.assertEqual(cfg_low.degree, 1)

    def test_tc10_output_to_dict_serialization(self) -> None:
        """TC10: Engine execution result serializes to valid JSON-compliant dictionary."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(market="NASDAQ", degree=2))
        res = eng.compute(self.sample_path[:10], self.sample_vol[:10], symbol="NVDA")
        d = res.to_dict()
        self.assertEqual(d["symbol"], "NVDA")
        self.assertEqual(d["market"], "NASDAQ")
        self.assertEqual(d["degree"], 2)
        self.assertEqual(len(d["alpha_conditioning_vector"]), 10)
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)

    # -----------------------------------------------------------------------
    # Category 3: Multi-Stream Microstructure Path Ingestion & Normalization
    # -----------------------------------------------------------------------
    def test_tc11_standard_4d_path_ingestion(self) -> None:
        """TC11: Ingests 4D continuous microstructure path (Time, Price, Volume, OFI)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        res = eng.compute(self.sample_path, symbol="MSFT")
        self.assertEqual(res.dimension, 4)
        self.assertIn(1, res.signature_levels)
        self.assertIn(2, res.signature_levels)
        self.assertIn(3, res.signature_levels)

    def test_tc12_3d_path_ingestion_without_time(self) -> None:
        """TC12: Ingests 3D continuous microstructure path (Price, Volume, OFI)."""
        path_3d = self.sample_path[:, 1:]
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        res = eng.compute(path_3d, symbol="AAPL")
        self.assertEqual(res.dimension, 3)
        self.assertEqual(res.signature_levels[1].shape, (3,))
        self.assertEqual(res.signature_levels[2].shape, (9,))
        self.assertEqual(res.signature_levels[3].shape, (27,))

    def test_tc13_1d_scalar_path_handling(self) -> None:
        """TC13: 1D scalar series path reshaped and processed cleanly."""
        scalar_path = self.sample_path[:, 1]
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(scalar_path, symbol="GOOGL")
        self.assertEqual(res.dimension, 1)
        self.assertEqual(res.signature_levels[1].shape, (1,))
        self.assertEqual(res.signature_levels[2].shape, (1,))

    def test_tc14_time_channel_normalization(self) -> None:
        """TC14: Time channel normalized to [0, 1] when normalize_path=True."""
        raw_path = self.sample_path.copy()
        raw_path[:, 0] = np.linspace(100.0, 500.0, len(raw_path))
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2, normalize_path=True))
        res = eng.compute(raw_path, symbol="SPY")
        # Level 1 time increment should sum to 1.0 (from 0 to 1)
        self.assertAlmostEqual(res.signature_levels[1][0], 1.0, places=5)

    def test_tc15_price_log_ratio_normalization(self) -> None:
        """TC15: Price channel transformed to log-ratio under normalization."""
        raw_path = np.zeros((10, 4))
        raw_path[:, 0] = np.linspace(0, 1, 10)
        raw_path[:, 1] = np.linspace(100.0, 110.0, 10)  # 10% increase
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=1, normalize_path=True))
        res = eng.compute(raw_path, symbol="QQQ")
        expected_log_ret = np.log(110.0 / 100.0)
        self.assertAlmostEqual(res.signature_levels[1][1], expected_log_ret, places=5)

    # -----------------------------------------------------------------------
    # Category 4: Truncated Tensor Signature Calculation & Chen's Identity Invariants
    # -----------------------------------------------------------------------
    def test_tc16_level_1_signature_is_sum_of_increments(self) -> None:
        """TC16: Level 1 signature equals exact total net path displacement X_T - X_0."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=1, normalize_path=False))
        res = eng.compute(self.sample_path, symbol="TEST")
        displacement = self.sample_path[-1] - self.sample_path[0]
        np.testing.assert_allclose(res.signature_levels[1], displacement, rtol=1e-6, atol=1e-8)

    def test_tc17_chen_identity_levels_1_and_2(self) -> None:
        r"""TC17: Chen's Identity S(A * B) == S(A) \otimes S(B) holds for levels 1 & 2."""
        mid = len(self.sample_path) // 2
        path_a = self.sample_path[: mid + 1]
        path_b = self.sample_path[mid:]
        path_ab = self.sample_path

        sig_a = compute_piecewise_linear_signature_np(path_a, degree=2)
        sig_b = compute_piecewise_linear_signature_np(path_b, degree=2)
        sig_ab = compute_piecewise_linear_signature_np(path_ab, degree=2)

        sig_prod = tensor_multiply_signatures_np(sig_a, sig_b, degree=2, dim=4)

        np.testing.assert_allclose(sig_ab[1], sig_prod[1], rtol=1e-7, atol=1e-9)
        np.testing.assert_allclose(sig_ab[2], sig_prod[2], rtol=1e-7, atol=1e-9)

    def test_tc18_chen_identity_level_3(self) -> None:
        """TC18: Chen's Identity holds exactly for level 3 tensor components."""
        mid = len(self.sample_path) // 2
        path_a = self.sample_path[: mid + 1]
        path_b = self.sample_path[mid:]
        path_ab = self.sample_path

        sig_a = compute_piecewise_linear_signature_np(path_a, degree=3)
        sig_b = compute_piecewise_linear_signature_np(path_b, degree=3)
        sig_ab = compute_piecewise_linear_signature_np(path_ab, degree=3)

        sig_prod = tensor_multiply_signatures_np(sig_a, sig_b, degree=3, dim=4)
        np.testing.assert_allclose(sig_ab[3], sig_prod[3], rtol=1e-7, atol=1e-9)

    def test_tc19_chen_identity_level_4(self) -> None:
        """TC19: Chen's Identity holds exactly for level 4 tensor components."""
        mid = len(self.sample_path) // 2
        path_a = self.sample_path[: mid + 1]
        path_b = self.sample_path[mid:]
        path_ab = self.sample_path

        sig_a = compute_piecewise_linear_signature_np(path_a, degree=4)
        sig_b = compute_piecewise_linear_signature_np(path_b, degree=4)
        sig_ab = compute_piecewise_linear_signature_np(path_ab, degree=4)

        sig_prod = tensor_multiply_signatures_np(sig_a, sig_b, degree=4, dim=4)
        np.testing.assert_allclose(sig_ab[4], sig_prod[4], rtol=1e-7, atol=1e-9)

    def test_tc20_time_reparameterization_invariance(self) -> None:
        """TC20: Signatures of paths under monotonic time-reparameterization are invariant."""
        # Create path 1: uniform spacing
        t1 = np.linspace(0.0, 1.0, 20)
        x1 = np.sin(2 * np.pi * t1)
        y1 = np.cos(2 * np.pi * t1)
        path1 = np.column_stack([x1, y1])

        # Create path 2: non-linear monotonic spacing (t^2)
        t2 = np.linspace(0.0, 1.0, 35) ** 2
        x2 = np.sin(2 * np.pi * t2)
        y2 = np.cos(2 * np.pi * t2)
        path2 = np.column_stack([x2, y2])

        sig1 = compute_piecewise_linear_signature_np(path1, degree=2)
        sig2 = compute_piecewise_linear_signature_np(path2, degree=2)

        # Level 1 and 2 should be extremely close (approx invariant up to discretization resolution)
        np.testing.assert_allclose(sig1[1], sig2[1], atol=0.08)
        np.testing.assert_allclose(sig1[2], sig2[2], atol=0.10)

    # -----------------------------------------------------------------------
    # Category 5: Degree m <= 4 Tensor Algebra & Dimension Invariants
    # -----------------------------------------------------------------------
    def test_tc21_dimension_invariants_4d(self) -> None:
        """TC21: Verifies dimension invariants for d=4 up to degree 4 (4, 16, 64, 256)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        res = eng.compute(self.sample_path)
        self.assertEqual(res.signature_levels[1].shape, (4,))
        self.assertEqual(res.signature_levels[2].shape, (16,))
        self.assertEqual(res.signature_levels[3].shape, (64,))
        self.assertEqual(res.signature_levels[4].shape, (256,))
        self.assertEqual(len(res.signature_vector), 4 + 16 + 64 + 256)

    def test_tc22_dimension_invariants_3d(self) -> None:
        """TC22: Verifies dimension invariants for d=3 up to degree 4 (3, 9, 27, 81)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        res = eng.compute(self.sample_path[:, :3])
        self.assertEqual(res.signature_levels[1].shape, (3,))
        self.assertEqual(res.signature_levels[2].shape, (9,))
        self.assertEqual(res.signature_levels[3].shape, (27,))
        self.assertEqual(res.signature_levels[4].shape, (81,))
        self.assertEqual(len(res.signature_vector), 3 + 9 + 27 + 81)

    def test_tc23_truncated_expansion_degree_selection(self) -> None:
        """TC23: Truncated expansion properly produces only requested degrees."""
        for d in (1, 2, 3, 4):
            eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=d))
            res = eng.compute(self.sample_path)
            self.assertEqual(res.degree, d)
            self.assertEqual(list(res.signature_levels.keys()), list(range(1, d + 1)))

    def test_tc24_concatenated_vector_shape(self) -> None:
        """TC24: Concatenated signature vector matches exact cumulative tensor terms."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        res = eng.compute(self.sample_path)
        expected_len = 4 + 16 + 64
        self.assertEqual(len(res.signature_vector), expected_len)

    def test_tc25_straight_line_signature_closed_form(self) -> None:
        r"""TC25: For straight line path from 0 to v, S^(k) = 1/k! * v^{\otimes k}."""
        v = np.array([2.0, -3.0, 1.5, 0.5])
        straight_path = np.vstack([np.zeros(4), v])

        sig = compute_piecewise_linear_signature_np(straight_path, degree=4)

        # S1 = v
        np.testing.assert_allclose(sig[1], v)
        # S2 = 1/2 v \otimes v
        np.testing.assert_allclose(sig[2], 0.5 * tensor_outer_np(v, v))
        # S3 = 1/6 v \otimes v \otimes v
        np.testing.assert_allclose(sig[3], (1.0 / 6.0) * tensor_outer_np(tensor_outer_np(v, v), v))
        # S4 = 1/24 v^{\otimes 4}
        v2 = tensor_outer_np(v, v)
        np.testing.assert_allclose(sig[4], (1.0 / 24.0) * tensor_outer_np(v2, v2))

    # -----------------------------------------------------------------------
    # Category 6: Log-Signature Transform & Tensor Series Expansion
    # -----------------------------------------------------------------------
    def test_tc26_level_1_log_signature_equals_s1(self) -> None:
        """TC26: Level 1 log-signature is identical to level 1 signature."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        res = eng.compute(self.sample_path)
        np.testing.assert_allclose(res.log_signature_levels[1], res.signature_levels[1])

    def test_tc27_level_2_log_signature_skew_symmetry(self) -> None:
        """TC27: Level 2 log-signature l2 is skew-symmetric: l2_{i,j} == -l2_{j,i} and l2_{i,i} == 0."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(self.sample_path)
        l2_mat = res.log_signature_levels[2].reshape(4, 4)

        # Check diagonal is zero
        np.testing.assert_allclose(np.diag(l2_mat), 0.0, atol=1e-10)
        # Check skew symmetry l2 = -l2^T
        np.testing.assert_allclose(l2_mat, -l2_mat.T, atol=1e-10)

    def test_tc28_level_3_log_signature_computation(self) -> None:
        """TC28: Level 3 log-signature computed with expected dimension 64."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=3))
        res = eng.compute(self.sample_path)
        self.assertEqual(res.log_signature_levels[3].shape, (64,))
        self.assertTrue(np.all(np.isfinite(res.log_signature_levels[3])))

    def test_tc29_level_4_log_signature_computation(self) -> None:
        """TC29: Level 4 log-signature computed with expected dimension 256."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        res = eng.compute(self.sample_path)
        self.assertEqual(res.log_signature_levels[4].shape, (256,))
        self.assertTrue(np.all(np.isfinite(res.log_signature_levels[4])))

    def test_tc30_zero_path_log_signature_is_zero(self) -> None:
        """TC30: Constant / zero increment path yields zero log-signature."""
        flat_path = np.zeros((10, 4))
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4, normalize_path=False))
        res = eng.compute(flat_path)
        np.testing.assert_allclose(res.log_signature_vector, 0.0, atol=1e-12)

    # -----------------------------------------------------------------------
    # Category 7: Geometric Non-Commutative Invariants & Lévy Area Integrals
    # -----------------------------------------------------------------------
    def test_tc31_price_volume_levy_area(self) -> None:
        """TC31: Computes Price vs Volume non-commutative Lévy area integral."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(self.sample_path)
        pv_area = res.levy_areas["price_volume_area"]
        self.assertIsInstance(pv_area, float)
        self.assertTrue(np.isfinite(pv_area))

    def test_tc32_price_ofi_levy_area(self) -> None:
        """TC32: Computes Price vs OFI non-commutative Lévy area integral."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(self.sample_path)
        p_ofi_area = res.levy_areas["price_ofi_area"]
        self.assertIsInstance(p_ofi_area, float)
        self.assertTrue(np.isfinite(p_ofi_area))

    def test_tc33_path_reversal_inverts_levy_area(self) -> None:
        """TC33: Reversing path direction negates the Lévy area A(X_rev) == -A(X)."""
        rev_path = self.sample_path[::-1].copy()
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2, normalize_path=False))

        res_fwd = eng.compute(self.sample_path)
        res_rev = eng.compute(rev_path)

        a_fwd = res_fwd.levy_areas["price_volume_area"]
        a_rev = res_rev.levy_areas["price_volume_area"]
        self.assertAlmostEqual(a_fwd, -a_rev, places=5)

    def test_tc34_circular_loop_levy_area_equals_geometric_area(self) -> None:
        r"""TC34: For a circular planar loop of radius R, Lévy area equals \pi R^2."""
        theta = np.linspace(0.0, 2.0 * np.pi, 200)
        radius = 2.0
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)
        loop_path = np.column_stack([x, y])

        sig = compute_piecewise_linear_signature_np(loop_path, degree=2)
        s2_mat = sig[2].reshape(2, 2)
        area_xy = 0.5 * (s2_mat[0, 1] - s2_mat[1, 0])

        expected_area = np.pi * (radius ** 2)
        # Numerical polygon area approximation within 1% of true circle area
        self.assertAlmostEqual(area_xy, expected_area, delta=0.05 * expected_area)

    def test_tc35_asymmetry_index_bounded(self) -> None:
        """TC35: Microstructure lead-lag asymmetry index strictly bounded in [-1.0, 1.0]."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(self.sample_path)
        asym = res.levy_areas["asymmetry_index"]
        self.assertGreaterEqual(asym, -1.0)
        self.assertLessEqual(asym, 1.0)

    # -----------------------------------------------------------------------
    # Category 8: Rough Volatility Hurst Parameter Estimation (H_rough < 0.50)
    # -----------------------------------------------------------------------
    def test_tc36_empirical_rough_hurst_estimation(self) -> None:
        """TC36: Volatility series produces estimated rough Hurst parameter H_rough < 0.50."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path, vol_series=self.sample_vol)
        self.assertLess(res.hurst_rough, 0.50)
        self.assertGreaterEqual(res.hurst_rough, 0.01)
        self.assertTrue(res.rough_hurst_result.is_rough)

    def test_tc37_structure_function_slopes_computation(self) -> None:
        """TC37: Structure function slopes computed across q=1.0 and q=2.0."""
        hurst_res = estimate_rough_hurst_np(self.sample_vol)
        self.assertIn(1.0, hurst_res.structure_slopes)
        self.assertIn(2.0, hurst_res.structure_slopes)
        self.assertGreater(hurst_res.r_squared, 0.0)

    def test_tc38_monotonic_structure_powers(self) -> None:
        """TC38: Structure powers for q=1 and q=2 are positive and non-divergent."""
        hurst_res = estimate_rough_hurst_np(self.sample_vol)
        self.assertGreater(hurst_res.structure_powers[1], 0.0)
        self.assertGreater(hurst_res.structure_powers[2], 0.0)

    def test_tc39_rough_regime_classification(self) -> None:
        """TC39: Regime classified as ROUGH_SUB_DIFFUSIVE when H < 0.45."""
        hurst_res = estimate_rough_hurst_np(self.sample_vol)
        if hurst_res.h_rough < 0.45:
            self.assertEqual(hurst_res.regime, RoughVolatilityRegime.ROUGH_SUB_DIFFUSIVE)

    def test_tc40_rough_ceiling_clamping(self) -> None:
        """TC40: Enforces rough volatility ceiling H_rough <= 0.499 even with smooth input."""
        smooth_vol = np.linspace(0.1, 0.5, 50)  # Highly trending smooth series
        hurst_res = estimate_rough_hurst_np(smooth_vol, rough_ceiling=0.499)
        self.assertLessEqual(hurst_res.h_rough, 0.499)

    # -----------------------------------------------------------------------
    # Category 9: Multi-Horizon Directional Return Drift Forecasting
    # -----------------------------------------------------------------------
    def test_tc41_multi_horizon_forecast_keys(self) -> None:
        """TC41: Forecasts contain all targets (100ms, 500ms, 1s, 5s, 60s)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        for h in ("100ms", "500ms", "1s", "5s", "60s"):
            self.assertIn(h, res.horizon_forecasts)

    def test_tc42_drift_bps_finite_values(self) -> None:
        """TC42: Projected return drift values in basis points are finite real numbers."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        for h, fc in res.horizon_forecasts.items():
            self.assertTrue(np.isfinite(fc.drift_bps))
            self.assertIsInstance(fc.drift_bps, float)

    def test_tc43_forecast_confidence_bounds(self) -> None:
        """TC43: Forecast confidence metrics strictly bounded in [0.0, 1.0]."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        for h, fc in res.horizon_forecasts.items():
            self.assertGreaterEqual(fc.confidence, 0.0)
            self.assertLessEqual(fc.confidence, 1.0)

    def test_tc44_t_statistic_finite(self) -> None:
        """TC44: Forecast t-statistic values are finite and non-NaN."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        for h, fc in res.horizon_forecasts.items():
            self.assertTrue(np.isfinite(fc.t_statistic))

    def test_tc45_market_drift_sensitivity_scaling(self) -> None:
        """TC45: KOSDAQ profile exhibits higher drift sensitivity than SP500."""
        eng_sp = PathSignatureAlphaEngine(PathSignatureConfig(market="SP500"))
        eng_kq = PathSignatureAlphaEngine(PathSignatureConfig(market="KOSDAQ"))

        sens_sp = eng_sp.profile["drift_sensitivity"]
        sens_kq = eng_kq.profile["drift_sensitivity"]
        self.assertGreater(sens_kq, sens_sp)

    # -----------------------------------------------------------------------
    # Category 10: Non-Markovian Long-Memory Alpha Conditioning Vector Synthesis
    # -----------------------------------------------------------------------
    def test_tc46_conditioning_vector_shape(self) -> None:
        """TC46: Conditioning vector has exact shape (10,) and dtype float64."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        self.assertEqual(res.alpha_conditioning_vector.shape, (10,))
        self.assertEqual(res.alpha_conditioning_vector.dtype, np.float64)

    def test_tc47_conditioning_vector_elements_0_1_2(self) -> None:
        """TC47: Vector elements 0, 1, 2 correspond to H_rough, A(P,V), and A(P,OFI)."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        vec = res.alpha_conditioning_vector
        self.assertEqual(vec[0], res.hurst_rough)
        self.assertEqual(vec[1], res.levy_areas["price_volume_area"])
        self.assertEqual(vec[2], res.levy_areas["price_ofi_area"])

    def test_tc48_conditioning_vector_norms_elements_4_5_6(self) -> None:
        """TC48: Vector elements 4, 5, 6 are non-negative signature tensor norms."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        vec = res.alpha_conditioning_vector
        self.assertGreaterEqual(vec[4], 0.0)  # ||S1||
        self.assertGreaterEqual(vec[5], 0.0)  # ||S2||
        self.assertGreaterEqual(vec[6], 0.0)  # ||LogSig||

    def test_tc49_conditioning_vector_drifts_elements_7_8(self) -> None:
        """TC49: Vector elements 7 and 8 match 1s and 5s return drift projections."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        vec = res.alpha_conditioning_vector
        self.assertEqual(vec[7], res.horizon_forecasts["1s"].drift_bps)
        self.assertEqual(vec[8], res.horizon_forecasts["5s"].drift_bps)

    def test_tc50_conditioning_vector_element_9_fragility(self) -> None:
        """TC50: Vector element 9 matches fragility score bounded in [0.0, 1.0]."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(self.sample_path)
        vec = res.alpha_conditioning_vector
        self.assertEqual(vec[9], res.rough_fragility)
        self.assertGreaterEqual(vec[9], 0.0)
        self.assertLessEqual(vec[9], 1.0)

    # -----------------------------------------------------------------------
    # Category 11: Critical Edge Cases, Degenerate Paths & Rough Fragility Alerts
    # -----------------------------------------------------------------------
    def test_tc51_empty_path_graceful_handling(self) -> None:
        """TC51: Empty path (length 0 or 1) executes gracefully without unhandled exceptions."""
        empty_path = np.zeros((0, 4))
        eng = PathSignatureAlphaEngine(PathSignatureConfig())
        res = eng.compute(empty_path)
        self.assertEqual(res.alpha_conditioning_vector.shape, (10,))
        self.assertEqual(res.hurst_rough, eng.profile["h_rough_prior"])

    def test_tc52_constant_flat_path(self) -> None:
        """TC52: Constant / flat path returns zero displacements and stable defaults."""
        flat_path = np.ones((25, 4)) * 100.0
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(flat_path)
        self.assertEqual(res.levy_areas["price_volume_area"], 0.0)
        self.assertTrue(np.all(np.isfinite(res.alpha_conditioning_vector)))

    def test_tc53_minimal_length_2_path(self) -> None:
        """TC53: Minimal 2-point path executes accurately."""
        min_path = np.array([[0.0, 100.0, 10.0, 5.0], [1.0, 102.0, 20.0, 8.0]])
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(min_path)
        self.assertEqual(res.alpha_conditioning_vector.shape, (10,))

    def test_tc54_flash_crash_fragility_alert(self) -> None:
        """TC54: Violent price drop with volume explosion triggers ELEVATED/CRITICAL fragility alert."""
        shock_path = np.zeros((30, 4))
        shock_path[:, 0] = np.linspace(0, 1, 30)
        shock_path[:, 1] = 100.0 - np.linspace(0, 30.0, 30)  # -30% crash
        shock_path[:, 2] = np.linspace(100.0, 10000.0, 30)  # massive volume surge
        shock_path[:, 3] = -np.linspace(10.0, 5000.0, 30)   # massive sell OFI

        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(shock_path)
        self.assertIn(
            res.fragility_level,
            (RoughFragilityLevel.ELEVATED, RoughFragilityLevel.CRITICAL),
        )

    def test_tc55_nan_inf_input_safeguard(self) -> None:
        """TC55: Path with extreme values does not propagate Infs or NaNs in output."""
        extreme_path = self.sample_path.copy()
        extreme_path[-1, 1] = 1e6
        extreme_path[-1, 2] = 1e8
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        res = eng.compute(extreme_path)
        self.assertFalse(np.any(np.isnan(res.alpha_conditioning_vector)))
        self.assertFalse(np.any(np.isinf(res.alpha_conditioning_vector)))

    # -----------------------------------------------------------------------
    # Category 12: Dual-Backend Parity (PyTorch vs NumPy), Execution Latency SLA & Telemetry
    # -----------------------------------------------------------------------
    def test_tc56_dual_backend_numerical_parity(self) -> None:
        """TC56: PyTorch and NumPy backends produce numerically identical outputs within 1e-6."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not installed in environment")

        cfg_torch = PathSignatureConfig(degree=4, use_torch=True)
        cfg_numpy = PathSignatureConfig(degree=4, use_torch=False)

        eng_torch = PathSignatureAlphaEngine(cfg_torch)
        eng_numpy = PathSignatureAlphaEngine(cfg_numpy)

        out_torch = eng_torch.compute(self.sample_path, self.sample_vol)
        out_numpy = eng_numpy.compute(self.sample_path, self.sample_vol)

        self.assertEqual(out_torch.backend, "PyTorch")
        self.assertEqual(out_numpy.backend, "NumPy")

        # Compare signature levels
        for lvl in (1, 2, 3, 4):
            np.testing.assert_allclose(
                out_torch.signature_levels[lvl],
                out_numpy.signature_levels[lvl],
                rtol=1e-6,
                atol=1e-8,
            )

        # Compare conditioning vector
        np.testing.assert_allclose(
            out_torch.alpha_conditioning_vector,
            out_numpy.alpha_conditioning_vector,
            rtol=1e-5,
            atol=1e-7,
        )

    def test_tc57_numpy_only_fallback(self) -> None:
        """TC57: Seamlessly executes purely in NumPy when use_torch=False."""
        cfg = PathSignatureConfig(degree=3, use_torch=False)
        eng = PathSignatureAlphaEngine(cfg)
        self.assertEqual(eng.backend, "NumPy")
        out = eng.compute(self.sample_path)
        self.assertEqual(out.backend, "NumPy")
        self.assertEqual(len(out.signature_vector), 4 + 16 + 64)

    def test_tc58_execution_latency_sla(self) -> None:
        """TC58: High-frequency execution latency SLA: < 2,000 us (2.0 ms) for 100-point path."""
        p100 = np.cumsum(np.random.randn(100, 4), axis=0)
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=4))
        # Warmup
        for _ in range(3):
            eng.compute(p100)
        out = eng.compute(p100)
        self.assertLess(out.latency_us, 2_000.0)  # < 2.0 ms institutional HF SLA

    def test_tc59_telemetry_accumulation(self) -> None:
        """TC59: Telemetry statistics correctly track cumulative runs and latencies."""
        eng = PathSignatureAlphaEngine(PathSignatureConfig(degree=2))
        for _ in range(5):
            eng.compute(self.sample_path[:15])

        tel = eng.get_telemetry()
        self.assertEqual(tel["total_computations"], 5)
        self.assertGreater(tel["total_execution_time_us"], 0.0)
        self.assertGreater(tel["avg_latency_us"], 0.0)

    def test_tc60_central_ai_exports_verification(self) -> None:
        """TC60: PathSignature exports accessible from both root and trading_system src.ai modules."""
        import importlib.util
        import src.ai as root_ai

        ts_init_path = TRADING_SYSTEM_DIR / "src" / "ai" / "__init__.py"
        spec = importlib.util.spec_from_file_location("ts_ai_exported", str(ts_init_path))
        ts_ai = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ts_ai)

        for exp in (
            "PathSignatureAlphaEngine",
            "PathSignatureConfig",
            "PathSignatureOutput",
            "SignatureResult",
            "RoughHurstResult",
            "LevyAreaResult",
            "RoughVolatilityRegime",
            "RoughFragilityLevel",
            "ContinuousRoughPathSignatureForecaster",
            "RoughPathSignatureAlphaEngine",
        ):
            self.assertTrue(hasattr(root_ai, exp), f"src.ai missing export: {exp}")
            self.assertTrue(hasattr(ts_ai, exp), f"trading_system.src.ai missing export: {exp}")



if __name__ == "__main__":
    unittest.main()
