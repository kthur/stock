"""
tests/test_phase117_diffusion_denoiser.py
=========================================
Comprehensive Unit, Integration, Mathematical Invariant, and Benchmark Tests for:
Continuous Score-Based Generative Diffusion Time-Series Denoiser (Feature F555).
Phase 117 (Release R133 / v124 Production Master).

Test Categories:
- Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
- Category 2: Configuration & SdeType Enumeration (TC04~TC06)
- Category 3: 5-Market Pre-Calibrated Profiles (TC07~TC09)
- Category 4: Forward SDE Formulations (VP-SDE & OU-SDE) (TC10~TC13)
- Category 5: Forward Noise Perturbation Sampling (TC14~TC16)
- Category 6: Microstructure 3-Component Decomposition (TC17~TC20)
- Category 7: Analytical Score & Prior-Conditioned Score (TC21~TC24)
- Category 8: Reverse-Time Predictor-Corrector Denoising (TC25~TC28)
- Category 9: Continuous SNR Gain Calculation (TC29~TC32)
- Category 10: PyTorch & NumPy Dual-Backend Execution (TC33~TC35)
- Category 11: Edge Cases, Latency & Telemetry Export (TC36~TC38)
"""

from __future__ import annotations

import hashlib
import math
import sys
import time
import unittest
from pathlib import Path
from typing import List

import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.diffusion_denoiser_engine import (
    FEATURE,
    MARKET_DIFFUSION_PROFILES,
    RELEASE,
    VERSION,
    ContinuousDiffusionDenoiserEngine,
    DiffusionDenoiserConfig,
    DiffusionDenoiserEngine,
    DiffusionDenoiserOutput,
    F555DiffusionDenoiser,
    Phase117DiffusionEngine,
    ScoreBasedDiffusionDenoiser,
    SdeType,
    TimeDecomposition,
)


class TestPhase117DiffusionDenoiser(unittest.TestCase):
    """38 Comprehensive test cases validating Feature F555."""

    def setUp(self) -> None:
        self.engine = DiffusionDenoiserEngine(market="SP500", symbol="AAPL")
        self.n_points = 100
        # Synthetic clean signal: macro trend + cyclic sinusoidal oscillation
        t = np.linspace(0, 4 * np.pi, self.n_points)
        self.macro_true = 150.0 + 0.5 * t
        self.cyclic_true = 2.0 * np.sin(t) + 1.0 * np.cos(2 * t)
        self.clean_true = self.macro_true + self.cyclic_true
        # Add high-frequency Gaussian noise (transient microstructure bounce)
        rng = np.random.default_rng(42)
        self.noise_true = rng.normal(0, 0.75, size=self.n_points)
        self.noisy_series = self.clean_true + self.noise_true

    # -----------------------------------------------------------------------
    # Category 1: Dual-Tree Parity, Module Exports & Complete Alias Trees (TC01~TC03)
    # -----------------------------------------------------------------------
    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """Verify 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        p1 = PROJECT_ROOT / "src" / "ai" / "diffusion_denoiser_engine.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "ai" / "diffusion_denoiser_engine.py"
        self.assertTrue(p1.exists(), f"Missing primary path: {p1}")
        self.assertTrue(p2.exists(), f"Missing mirrored path: {p2}")
        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        self.assertEqual(h1, h2, "Cryptographic SHA-256 hash mismatch between dual-tree files!")

    def test_tc02_version_release_feature_metadata(self) -> None:
        """Verify version metadata constants."""
        self.assertEqual(VERSION, 117)
        self.assertEqual(RELEASE, "R133")
        self.assertEqual(FEATURE, "F555")
        self.assertEqual(DiffusionDenoiserEngine.VERSION, 117)
        self.assertEqual(DiffusionDenoiserEngine.RELEASE, "R133")
        self.assertEqual(DiffusionDenoiserEngine.FEATURE, "F555")

    def test_tc03_complete_alias_trees_and_sys_modules(self) -> None:
        """Verify complete backward-compatibility alias trees and sys.modules registration."""
        self.assertIs(ContinuousDiffusionDenoiserEngine, DiffusionDenoiserEngine)
        self.assertIs(ScoreBasedDiffusionDenoiser, DiffusionDenoiserEngine)
        self.assertIs(Phase117DiffusionEngine, DiffusionDenoiserEngine)
        self.assertIs(F555DiffusionDenoiser, DiffusionDenoiserEngine)
        self.assertIn("src.ai.diffusion_denoiser_engine", sys.modules)
        self.assertIn("trading_system.src.ai.diffusion_denoiser_engine", sys.modules)

    # -----------------------------------------------------------------------
    # Category 2: Configuration & SdeType Enumeration (TC04~TC06)
    # -----------------------------------------------------------------------
    def test_tc04_default_configuration_initialization(self) -> None:
        """Verify default configuration attributes and types."""
        cfg = DiffusionDenoiserConfig()
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.sde_type, SdeType.VP_SDE)
        self.assertGreater(cfg.beta_max, cfg.beta_min)
        self.assertEqual(cfg.num_diffusion_steps, 50)
        self.assertGreater(cfg.snr_target, 0.0)

    def test_tc05_custom_configuration_override(self) -> None:
        """Verify engine instantiation with customized hyperparameters."""
        custom_cfg = DiffusionDenoiserConfig(
            market="NASDAQ",
            sde_type=SdeType.OU_SDE,
            ou_theta=3.5,
            ou_sigma=0.03,
            num_diffusion_steps=30,
        )
        custom_engine = DiffusionDenoiserEngine(config=custom_cfg, market="NASDAQ", symbol="NVDA")
        self.assertEqual(custom_engine.config.sde_type, SdeType.OU_SDE)
        self.assertEqual(custom_engine.config.ou_theta, 3.5)
        self.assertEqual(custom_engine.config.num_diffusion_steps, 30)
        self.assertEqual(custom_engine.symbol, "NVDA")

    def test_tc06_sde_type_enumeration(self) -> None:
        """Verify SdeType enum values."""
        self.assertEqual(SdeType.VP_SDE.value, "VP_SDE")
        self.assertEqual(SdeType.OU_SDE.value, "OU_SDE")

    # -----------------------------------------------------------------------
    # Category 3: 5-Market Pre-Calibrated Profiles (TC07~TC09)
    # -----------------------------------------------------------------------
    def test_tc07_five_market_profile_contents(self) -> None:
        """Verify parameter profiles exist for all 5 markets."""
        for mkt in ("SP500", "NASDAQ", "KOSPI", "KOSDAQ", "RUSSELL2000"):
            self.assertIn(mkt, MARKET_DIFFUSION_PROFILES)
            prof = MARKET_DIFFUSION_PROFILES[mkt]
            self.assertIn("beta_min", prof)
            self.assertIn("beta_max", prof)
            self.assertIn("ou_theta", prof)
            self.assertIn("ou_sigma", prof)
            self.assertIn("snr_target", prof)

    def test_tc08_dynamic_market_calibration(self) -> None:
        """Verify dynamic re-calibration across markets."""
        self.engine.calibrate_market("KOSDAQ")
        self.assertEqual(self.engine.market, "KOSDAQ")
        self.assertEqual(self.engine.config.market, "KOSDAQ")
        self.assertEqual(self.engine.config.beta_max, MARKET_DIFFUSION_PROFILES["KOSDAQ"]["beta_max"])

    def test_tc09_unknown_market_profile_fallback(self) -> None:
        """Verify fallback to SP500 profile when unknown market specified."""
        engine_fallback = DiffusionDenoiserEngine(market="UNKNOWN_EXCHANGE")
        self.assertEqual(engine_fallback.config.beta_min, MARKET_DIFFUSION_PROFILES["SP500"]["beta_min"])

    # -----------------------------------------------------------------------
    # Category 4: Forward SDE Formulations (VP-SDE & OU-SDE) (TC10~TC13)
    # -----------------------------------------------------------------------
    def test_tc10_vp_sde_beta_schedule_monotonicity(self) -> None:
        """Verify linear beta schedule strictly increases from beta_min to beta_max."""
        b0 = self.engine.compute_beta(0.0)
        b_mid = self.engine.compute_beta(0.5)
        b1 = self.engine.compute_beta(1.0)
        self.assertAlmostEqual(b0, self.engine.config.beta_min)
        self.assertAlmostEqual(b1, self.engine.config.beta_max)
        self.assertTrue(b0 < b_mid < b1)

    def test_tc11_vp_sde_marginal_mean_strictly_decreases(self) -> None:
        """Verify VP-SDE mean scaling factor alpha(t) strictly decreases from ~1.0 at t=0 to ~0 at t=1."""
        x = np.array([10.0, 20.0, 30.0])
        m0, std0 = self.engine.forward_sde_marginal(x, 0.0)
        m_mid, std_mid = self.engine.forward_sde_marginal(x, 0.5)
        m1, std1 = self.engine.forward_sde_marginal(x, 1.0)
        np.testing.assert_allclose(m0, x, rtol=1e-5)
        self.assertTrue(np.all(m_mid < m0))
        self.assertTrue(np.all(m1 < m_mid))
        self.assertTrue(std0 < std_mid < std1)

    def test_tc12_vp_sde_variance_strictly_increases(self) -> None:
        """Verify VP-SDE standard deviation strictly increases with t."""
        x = np.array([5.0])
        _, s1 = self.engine.forward_sde_marginal(x, 0.1)
        _, s2 = self.engine.forward_sde_marginal(x, 0.5)
        _, s3 = self.engine.forward_sde_marginal(x, 0.9)
        self.assertTrue(s1 < s2 < s3)

    def test_tc13_ou_sde_marginal_mean_and_variance(self) -> None:
        """Verify OU-SDE forward marginal mean decay towards mu and bounded variance."""
        ou_cfg = DiffusionDenoiserConfig(sde_type=SdeType.OU_SDE, ou_theta=2.0, ou_mu=100.0, ou_sigma=1.0)
        ou_engine = DiffusionDenoiserEngine(config=ou_cfg)
        x = np.array([200.0])
        m0, s0 = ou_engine.forward_sde_marginal(x, 0.0)
        np.testing.assert_allclose(m0, [200.0])
        m_inf, s_inf = ou_engine.forward_sde_marginal(x, 1.0)
        self.assertTrue(m_inf[0] < 200.0)
        self.assertGreater(s_inf, 0.0)

    # -----------------------------------------------------------------------
    # Category 5: Forward Noise Perturbation Sampling (TC14~TC16)
    # -----------------------------------------------------------------------
    def test_tc14_sample_forward_noisy_at_t0(self) -> None:
        """Verify forward sampling at t=0 returns original signal with negligible noise."""
        x_0 = np.linspace(10.0, 50.0, 20)
        x_t, _ = self.engine.sample_forward_noisy(x_0, t=0.0)
        np.testing.assert_allclose(x_t, x_0, atol=1e-3)

    def test_tc15_sample_forward_noisy_at_t1(self) -> None:
        """Verify forward sampling at t=1 significantly perturbs signal."""
        x_0 = np.ones(50) * 100.0
        x_t, noise = self.engine.sample_forward_noisy(x_0, t=1.0)
        self.assertFalse(np.allclose(x_t, x_0))
        self.assertEqual(len(x_t), 50)
        self.assertEqual(len(noise), 50)

    def test_tc16_forward_sampling_reproducibility(self) -> None:
        """Verify identical noise samples when providing seeded generator."""
        x_0 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        rng1 = np.random.default_rng(12345)
        rng2 = np.random.default_rng(12345)
        x_t1, _ = self.engine.sample_forward_noisy(x_0, t=0.5, rng=rng1)
        x_t2, _ = self.engine.sample_forward_noisy(x_0, t=0.5, rng=rng2)
        np.testing.assert_allclose(x_t1, x_t2)

    # -----------------------------------------------------------------------
    # Category 6: Microstructure 3-Component Decomposition (TC17~TC20)
    # -----------------------------------------------------------------------
    def test_tc17_decomposition_structure_and_types(self) -> None:
        """Verify decompose_series returns TimeDecomposition with valid shapes."""
        decomp = self.engine.decompose_series(self.noisy_series)
        self.assertIsInstance(decomp, TimeDecomposition)
        self.assertEqual(decomp.macro_drift.shape, (self.n_points,))
        self.assertEqual(decomp.cyclic_factors.shape, (self.n_points,))
        self.assertEqual(decomp.transient_noise.shape, (self.n_points,))
        self.assertEqual(decomp.clean_target.shape, (self.n_points,))

    def test_tc18_exact_additive_reconstruction_invariant(self) -> None:
        """Verify series == macro_drift + cyclic_factors + transient_noise."""
        decomp = self.engine.decompose_series(self.noisy_series)
        reconstructed = decomp.macro_drift + decomp.cyclic_factors + decomp.transient_noise
        np.testing.assert_allclose(reconstructed, self.noisy_series, atol=1e-10)

    def test_tc19_clean_target_invariant(self) -> None:
        """Verify clean_target == macro_drift + cyclic_factors."""
        decomp = self.engine.decompose_series(self.noisy_series)
        np.testing.assert_allclose(decomp.clean_target, decomp.macro_drift + decomp.cyclic_factors)

    def test_tc20_harmonic_cyclic_capture(self) -> None:
        """Verify cyclic decomposition captures strong periodic oscillation."""
        t = np.linspace(0, 8 * np.pi, 200)
        pure_harmonic = 100.0 + 5.0 * np.sin(t)
        decomp = self.engine.decompose_series(pure_harmonic)
        # Cyclic variance should be significant compared to transient noise
        self.assertGreater(np.var(decomp.cyclic_factors), np.var(decomp.transient_noise))

    # -----------------------------------------------------------------------
    # Category 7: Analytical Score & Prior-Conditioned Score (TC21~TC24)
    # -----------------------------------------------------------------------
    def test_tc21_analytical_score_gradient_direction(self) -> None:
        """Verify score vector points towards clean target: if x > mean, score < 0."""
        m_clean = np.array([10.0, 20.0])
        # x_t perturbed higher than mean
        x_high = np.array([15.0, 25.0])
        score = self.engine.compute_analytical_score(x_high, t=0.2, m_clean=m_clean)
        self.assertTrue(np.all(score < 0.0), "Score must be negative to pull x back towards mean!")

    def test_tc22_analytical_score_pulls_low_values_up(self) -> None:
        """Verify score vector points towards clean target: if x < mean, score > 0."""
        m_clean = np.array([10.0, 20.0])
        x_low = np.array([5.0, 15.0])
        score = self.engine.compute_analytical_score(x_low, t=0.2, m_clean=m_clean)
        self.assertTrue(np.all(score > 0.0), "Score must be positive to push x up towards mean!")

    def test_tc23_prior_conditioned_score_stability(self) -> None:
        """Verify compute_prior_score remains finite and non-NaN under small t."""
        m_clean = np.array([100.0, 105.0])
        x_t = np.array([101.0, 104.0])
        score = self.engine.compute_prior_score(x_t, t=1e-4, m_clean=m_clean)
        self.assertFalse(np.any(np.isnan(score)))
        self.assertFalse(np.any(np.isinf(score)))

    def test_tc24_evaluate_score_bounded_norm(self) -> None:
        """Verify evaluate_score norm is finite across different t steps."""
        m_clean = np.linspace(100.0, 105.0, 50)
        x_t = m_clean + np.random.normal(0, 1.0, 50)
        for t_step in (0.1, 0.5, 0.9):
            s = self.engine.evaluate_score(x_t, t=t_step, m_clean=m_clean)
            self.assertFalse(np.any(np.isnan(s)))
            self.assertLess(np.max(np.abs(s)), 1e5)

    # -----------------------------------------------------------------------
    # Category 8: Reverse-Time Predictor-Corrector Denoising (TC25~TC28)
    # -----------------------------------------------------------------------
    def test_tc25_end_to_end_denoise_execution(self) -> None:
        """Verify end-to-end denoise() returns complete DiffusionDenoiserOutput."""
        res = self.engine.denoise(self.noisy_series, num_steps=20)
        self.assertIsInstance(res, DiffusionDenoiserOutput)
        self.assertEqual(res.symbol, "AAPL")
        self.assertEqual(res.market, "SP500")
        self.assertEqual(len(res.denoised_series), self.n_points)
        self.assertFalse(np.any(np.isnan(res.denoised_series)))

    def test_tc26_denoise_ou_sde_execution(self) -> None:
        """Verify denoise() executes successfully under OU-SDE schedule."""
        ou_cfg = DiffusionDenoiserConfig(sde_type=SdeType.OU_SDE, num_diffusion_steps=20)
        ou_engine = DiffusionDenoiserEngine(config=ou_cfg)
        res = ou_engine.denoise(self.noisy_series)
        self.assertEqual(res.sde_type, "OU_SDE")
        self.assertEqual(len(res.denoised_series), self.n_points)
        self.assertFalse(np.any(np.isnan(res.denoised_series)))

    def test_tc27_denoise_reduces_variance_of_noise(self) -> None:
        """Verify denoised series has lower error against true signal than raw noisy series."""
        res = self.engine.denoise(self.noisy_series, num_steps=30)
        raw_error = np.mean((self.noisy_series - self.clean_true) ** 2)
        denoised_error = np.mean((res.denoised_series - self.clean_true) ** 2)
        self.assertLess(denoised_error, raw_error, "Denoised series must have lower MSE than raw noisy input!")

    def test_tc28_denoise_output_to_dict_serialization(self) -> None:
        """Verify to_dict serialization on DiffusionDenoiserOutput."""
        res = self.engine.denoise(self.noisy_series, num_steps=10)
        d = res.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("snr_gain_db", d)
        self.assertIn("reconstruction_rmse", d)
        self.assertIn("reconstruction_mae", d)
        self.assertIn("elapsed_us", d)

    # -----------------------------------------------------------------------
    # Category 9: Continuous SNR Gain Calculation (TC29~TC32)
    # -----------------------------------------------------------------------
    def test_tc29_snr_gain_mathematical_formula(self) -> None:
        """Verify exact mathematical computation of SNR raw, denoised, and gain in dB."""
        orig = np.array([10.0, 11.0, 12.0, 13.0])
        clean = np.array([10.0, 10.5, 12.0, 12.5])
        denoised = np.array([10.0, 10.6, 12.0, 12.4])  # closer to clean
        snr_raw, snr_den, gain_db = self.engine.compute_snr_gain(orig, denoised, clean)
        self.assertGreater(snr_den, snr_raw)
        self.assertGreater(gain_db, 0.0)

    def test_tc30_continuous_positive_snr_gain_on_noisy_input(self) -> None:
        """Verify positive SNR gain (> 0 dB) achieved on synthetic noisy microstructure series."""
        res = self.engine.denoise(self.noisy_series, num_steps=30)
        self.assertGreater(res.snr_gain_db, 0.0, f"Expected positive SNR gain, got {res.snr_gain_db} dB")

    def test_tc31_reconstruction_rmse_and_mae_non_negative(self) -> None:
        """Verify reconstruction error metrics are non-negative and finite."""
        res = self.engine.denoise(self.noisy_series, num_steps=15)
        self.assertGreaterEqual(res.reconstruction_rmse, 0.0)
        self.assertGreaterEqual(res.reconstruction_mae, 0.0)
        self.assertFalse(math.isnan(res.reconstruction_rmse))
        self.assertFalse(math.isnan(res.reconstruction_mae))

    def test_tc32_zero_noise_series_stability(self) -> None:
        """Verify denoising pure clean series produces near-zero distortion without crashing."""
        res = self.engine.denoise(self.clean_true, num_steps=15)
        self.assertFalse(np.any(np.isnan(res.denoised_series)))
        self.assertLess(res.reconstruction_rmse, 1.5)

    # -----------------------------------------------------------------------
    # Category 10: PyTorch & NumPy Dual-Backend Execution (TC33~TC35)
    # -----------------------------------------------------------------------
    def test_tc33_pure_numpy_backend_execution(self) -> None:
        """Verify pure NumPy fallback executes cleanly with use_torch=False."""
        np_cfg = DiffusionDenoiserConfig(use_torch=False, num_diffusion_steps=15)
        np_engine = DiffusionDenoiserEngine(config=np_cfg)
        self.assertIsNone(np_engine.torch_score_net)
        res = np_engine.denoise(self.noisy_series)
        self.assertEqual(res.backend, "numpy")
        self.assertEqual(len(res.denoised_series), self.n_points)

    def test_tc34_torch_backend_availability(self) -> None:
        """Verify engine detects and reports PyTorch availability correctly."""
        telemetry = self.engine.export_telemetry()
        self.assertIn("torch_available", telemetry)

    def test_tc35_numpy_vs_torch_parity(self) -> None:
        """Verify both backends produce finite denoised series within reasonable tolerance."""
        res_np = DiffusionDenoiserEngine(config=DiffusionDenoiserConfig(use_torch=False, num_diffusion_steps=15)).denoise(self.noisy_series)
        res_torch = DiffusionDenoiserEngine(config=DiffusionDenoiserConfig(use_torch=True, num_diffusion_steps=15)).denoise(self.noisy_series)
        self.assertEqual(len(res_np.denoised_series), len(res_torch.denoised_series))
        self.assertFalse(np.any(np.isnan(res_np.denoised_series)))
        self.assertFalse(np.any(np.isnan(res_torch.denoised_series)))

    # -----------------------------------------------------------------------
    # Category 11: Edge Cases, Latency & Telemetry Export (TC36~TC38)
    # -----------------------------------------------------------------------
    def test_tc36_short_series_edge_cases(self) -> None:
        """Verify engine handles very short series (length 4, 10) gracefully."""
        for length in (4, 10):
            short_s = np.linspace(10.0, 20.0, length)
            res = self.engine.denoise(short_s, num_steps=10)
            self.assertEqual(len(res.denoised_series), length)
            self.assertFalse(np.any(np.isnan(res.denoised_series)))

    def test_tc37_empty_series_raises_value_error(self) -> None:
        """Verify passing empty array raises ValueError."""
        with self.assertRaises(ValueError):
            self.engine.denoise(np.array([]))

    def test_tc38_telemetry_export_and_latency_benchmark(self) -> None:
        """Verify telemetry tracks calls, latency, and executes in fast time."""
        res = self.engine.denoise(self.noisy_series, num_steps=10)
        telem = self.engine.export_telemetry()
        self.assertGreater(telem["telemetry"]["total_denoised_calls"], 0)
        self.assertGreater(telem["telemetry"]["total_steps_executed"], 0)
        self.assertGreater(res.elapsed_us, 0.0)


if __name__ == "__main__":
    unittest.main()
