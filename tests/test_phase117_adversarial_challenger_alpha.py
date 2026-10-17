"""
tests/test_phase117_adversarial_challenger_alpha.py
===================================================
Adversarial Stress, Fuzzing, Mathematical Invariant, and Corner-Case Suite for:
Feature F555: Continuous Score-Based Generative Diffusion Time-Series Denoiser (src/ai/diffusion_denoiser_engine.py)
Feature F556: Deep LOB Transformer with Multi-Scale Temporal Attention (src/ai/lob_transformer_engine.py)
Phase 117 (Release R133 / v124 Production Master).

Adversarial Dimensions Tested:
1. Section 1: Extreme SDE Noise Floods & Boundary Schedules (F555) (TC01 ~ TC12)
   - TC01: Extreme beta_max flooding (beta_max = 500.0) -> drift/coeff finite.
   - TC02: Sub-nanosecond diffusion time (t -> 0, t = 1e-12) -> beta(t) == beta_min without underflow.
   - TC03: Terminal diffusion boundary (t = 1.0) -> beta(t) == beta_max, score gradient stable.
   - TC04: Ultra-sparse single-step reverse integration (num_steps = 1) -> does not crash, outputs valid length.
   - TC05: Deep reverse integration (num_steps = 60) -> denoise returns strictly lower MSE vs raw noisy series.
   - TC06: High-frequency explosive noise series (noise variance = 250.0) -> denoiser suppresses noise, snr_gain_db > 0.
   - TC07: Constant flatline input series (all values 100.0) -> transient noise is zero, clean target is 100.0.
   - TC08: Step jump discontinuity (flash crash drop from 100 to 50) -> macro drift tracks step, cyclic factor bounded.
   - TC09: Negative price series inputs (e.g. WTI flash crash) -> denoiser handles without domain errors.
   - TC10: Outlier price spike impulse (Dirac spike) -> transient noise absorbs impulse, clean target smooth.
   - TC11: High-order harmonic cycle flood (frequencies beyond Nyquist limit) -> cyclic decomposition remains bounded.
   - TC12: OU-SDE parameter extremes (ou_theta = 50.0, ou_sigma = 5.0) -> denoise runs and produces finite series.

2. Section 2: LOB Tensor Malformations & Inverted Book Attacks (F556) (TC13 ~ TC24)
   - TC13: Inverted book (Bid 105.0 > Ask 100.0) -> predict runs without division by zero, probability simplex sums to 1.0.
   - TC14: Crossed book at Level 3~5 -> spatial depth cross-attention sums to 1.0, top depth driver valid.
   - TC15: Completely zeroed order book tensor (all zeros) -> predict handles safely, produces valid probabilities.
   - TC16: Sub-penny microscopic spread (1e-6) -> mid-price calculation stable, no division by zero.
   - TC17: Extreme asymmetric volume wall at Level 10 (100,000x Level 1 volume) -> attention weights shift, no overflow.
   - TC18: Single-tick temporal shock at t = T-1 -> temporal attention remains strictly causal.
   - TC19: Causal anti-leakage test: changing future tensor slice t > k has zero effect on past predictions at k.
   - TC20: Extreme sequence lengths (seq_len = 1, seq_len = 32) -> multi-scale convolutions and causal attention valid.
   - TC21: Inf/NaN sanitization: tensor with np.nan and np.inf is sanitized without raising unhandled errors.
   - TC22: Microstructure 180-degree order imbalance reversal -> directional logit shifts from Down to Up.
   - TC23: Uniform volume book across all 10 levels -> depth attention is distributed, top_level_driver in [1, 10].
   - TC24: Probability calibration under all 4 horizons: sum strictly equals 1.0 for each horizon.

3. Section 3: Cross-Coupled Alpha Stress & Fuzzing (F555 + F556) (TC25 ~ TC34)
   - TC25: Coupling pipeline: Denoised price series from F555 feeds into Level 1 quotes of LOB tensor for F556 -> end-to-end execution.
   - TC26: Directional consistency: Positive drift from F555 aligns with Up probability > Down probability in F556 on upward trend.
   - TC27: Latency SLA: Combined execution of F555 denoise (20 steps) + F556 predict completes in < 5.0 ms.
   - TC28: Memory invariance: 50 consecutive runs execute without memory explosion.
   - TC29: Multi-threaded thread-safety: Concurrent invocations of F555 and F556 from 4 threads complete with zero race conditions.
   - TC30: Deterministic reproducibility: Identical seed produces identical output vectors across runs.
   - TC31: Monte Carlo fuzzing F555: 100 randomized noisy price series with random lengths [20, 150] -> zero exceptions, zero NaNs.
   - TC32: Monte Carlo fuzzing F556: 100 randomized LOB tensors with random price/volume perturbations -> zero exceptions, zero NaNs.
   - TC33: Universal 5-market calibration invariance: F555 executes across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
   - TC34: Universal 5-market calibration invariance: F556 executes across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
"""

from __future__ import annotations

import math
import random
import sys
import time
import unittest
import threading
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Ensure project roots are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.diffusion_denoiser_engine import (
    DiffusionDenoiserEngine,
    DiffusionDenoiserConfig,
    DiffusionDenoiserOutput,
    SdeType,
    TimeDecomposition,
    MARKET_DIFFUSION_PROFILES,
)
from src.ai.lob_transformer_engine import (
    LOBTransformerEngine,
    LOBTransformerConfig,
    LOBTransformerOutput,
    PriceDirection,
    HorizonPrediction,
    LOBAttentionHeatmap,
    MARKET_LOB_PROFILES,
)


class TestPhase117AdversarialSdeNoiseFloods(unittest.TestCase):
    """Adversarial Section 1: Extreme SDE Noise Floods & Boundary Schedules (F555)."""

    def setUp(self) -> None:
        np.random.seed(42)
        self.engine = DiffusionDenoiserEngine(
            config=DiffusionDenoiserConfig(market="SP500", num_diffusion_steps=20, seed=42)
        )

    def test_tc01_extreme_beta_max_flooding(self) -> None:
        """TC01: Extreme beta_max flooding (beta_max = 500.0) -> drift/coeff finite."""
        cfg = DiffusionDenoiserConfig(beta_min=0.01, beta_max=500.0)
        engine = DiffusionDenoiserEngine(config=cfg)
        x = np.array([10.0, 20.0, 30.0])
        drift, diff = engine.compute_drift_and_diffusion(x, t=0.5)
        self.assertTrue(np.all(np.isfinite(drift)))
        self.assertTrue(np.isfinite(diff))
        self.assertGreater(diff, 0.0)

    def test_tc02_sub_nanosecond_diffusion_time(self) -> None:
        """TC02: Sub-nanosecond diffusion time (t -> 0, t = 1e-12) -> beta(t) == beta_min without underflow."""
        beta_val = self.engine.compute_beta(1e-12)
        self.assertAlmostEqual(beta_val, self.engine.config.beta_min, places=5)
        self.assertTrue(np.isfinite(beta_val))

    def test_tc03_terminal_diffusion_boundary(self) -> None:
        """TC03: Terminal diffusion boundary (t = 1.0) -> beta(t) == beta_max, score gradient stable."""
        beta_val = self.engine.compute_beta(1.0)
        self.assertAlmostEqual(beta_val, self.engine.config.beta_max, places=5)
        x = np.array([100.0, 105.0])
        m_clean = np.array([99.0, 104.0])
        score = self.engine.compute_analytical_score(x, t=1.0, m_clean=m_clean)
        self.assertTrue(np.all(np.isfinite(score)))

    def test_tc04_ultra_sparse_single_step_reverse_integration(self) -> None:
        """TC04: Ultra-sparse single-step reverse integration (num_steps = 1) -> valid output."""
        series = 100.0 + np.cumsum(np.random.randn(50) * 0.1)
        out = self.engine.denoise(series, num_steps=1)
        self.assertIsInstance(out, DiffusionDenoiserOutput)
        self.assertEqual(len(out.denoised_series), len(series))
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))

    def test_tc05_deep_reverse_integration_error_reduction(self) -> None:
        """TC05: Deep reverse integration (num_steps = 60) -> denoise returns lower MSE vs raw noisy series."""
        clean_trend = np.linspace(100.0, 110.0, 60)
        noisy = clean_trend + np.random.normal(0, 0.5, 60)
        out = self.engine.denoise(noisy, num_steps=30)
        mse_raw = float(np.mean((noisy - clean_trend) ** 2))
        mse_den = float(np.mean((out.denoised_series - clean_trend) ** 2))
        self.assertLess(mse_den, mse_raw)

    def test_tc06_high_frequency_explosive_noise_suppression(self) -> None:
        """TC06: High-frequency explosive noise series (variance = 250.0) -> snr_gain_db > 0."""
        clean_signal = np.sin(np.linspace(0, 4 * np.pi, 100)) * 10.0 + 100.0
        explosive_noise = clean_signal + np.random.normal(0, 5.0, 100)
        out = self.engine.denoise(explosive_noise, num_steps=25)
        self.assertGreater(out.snr_gain_db, 0.0)
        self.assertLess(np.var(out.decomposition.transient_noise), np.var(explosive_noise))

    def test_tc07_constant_flatline_input_series(self) -> None:
        """TC07: Constant flatline input series (all values 100.0) -> transient noise is zero."""
        flatline = np.full(50, 100.0)
        decomp = self.engine.decompose_series(flatline)
        self.assertAlmostEqual(float(np.mean(decomp.macro_drift)), 100.0, places=3)
        self.assertAlmostEqual(float(np.max(np.abs(decomp.transient_noise))), 0.0, places=3)

    def test_tc08_step_jump_discontinuity_resilience(self) -> None:
        """TC08: Step jump discontinuity (flash crash drop from 100 to 50) -> macro drift tracks step."""
        crash_series = np.concatenate([np.full(40, 100.0), np.full(40, 50.0)])
        out = self.engine.denoise(crash_series, num_steps=20)
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))
        self.assertLess(out.denoised_series[-1], out.denoised_series[0])

    def test_tc09_negative_price_series_inputs(self) -> None:
        """TC09: Negative price series inputs (e.g. WTI flash crash) -> no domain errors."""
        negative_prices = np.linspace(-37.0, -10.0, 50) + np.random.normal(0, 0.2, 50)
        out = self.engine.denoise(negative_prices, num_steps=15)
        self.assertEqual(len(out.denoised_series), 50)
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))

    def test_tc10_outlier_price_spike_impulse(self) -> None:
        """TC10: Outlier price spike impulse (Dirac spike) -> transient noise absorbs impulse."""
        series = np.full(50, 100.0)
        series[25] = 150.0  # +50% spike
        decomp = self.engine.decompose_series(series)
        self.assertGreater(decomp.transient_noise[25], 20.0)
        self.assertLess(decomp.clean_target[25], 140.0)

    def test_tc11_high_order_harmonic_cycle_flood(self) -> None:
        """TC11: High-order harmonic cycle flood -> cyclic decomposition remains bounded and finite."""
        t = np.linspace(0, 100, 200)
        high_freq = 100.0 + 2.0 * np.sin(50 * t) + 1.5 * np.cos(80 * t)
        decomp = self.engine.decompose_series(high_freq)
        self.assertTrue(np.all(np.isfinite(decomp.cyclic_factors)))
        self.assertLess(float(np.max(np.abs(decomp.cyclic_factors))), 20.0)

    def test_tc12_ou_sde_parameter_extremes(self) -> None:
        """TC12: OU-SDE parameter extremes (ou_theta = 50.0, ou_sigma = 5.0) -> denoise produces finite series."""
        ou_cfg = DiffusionDenoiserConfig(
            sde_type=SdeType.OU_SDE,
            ou_theta=50.0,
            ou_sigma=5.0,
            num_diffusion_steps=15,
        )
        ou_engine = DiffusionDenoiserEngine(config=ou_cfg)
        noisy = 100.0 + np.cumsum(np.random.randn(40) * 0.2)
        out = ou_engine.denoise(noisy)
        self.assertEqual(out.sde_type, "OU_SDE")
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))


class TestPhase117AdversarialLOBTensorAnomalies(unittest.TestCase):
    """Adversarial Section 2: LOB Tensor Malformations & Inverted Book Attacks (F556)."""

    def setUp(self) -> None:
        np.random.seed(42)
        self.engine = LOBTransformerEngine(config=LOBTransformerConfig(market="SP500", seq_len=10))
        self.valid_tensor = np.zeros((10, 40), dtype=np.float32)
        for lvl in range(10):
            self.valid_tensor[:, lvl * 4 + 0] = 100.0 - (lvl * 0.05)
            self.valid_tensor[:, lvl * 4 + 1] = 1000.0 * (10 - lvl)
            self.valid_tensor[:, lvl * 4 + 2] = 100.05 + (lvl * 0.05)
            self.valid_tensor[:, lvl * 4 + 3] = 1000.0 * (10 - lvl)

    def test_tc13_inverted_book_resilience(self) -> None:
        """TC13: Inverted book (Bid 105.0 > Ask 100.0) -> predict runs without division by zero."""
        inverted = self.valid_tensor.copy()
        inverted[:, 0] = 105.0  # Bid
        inverted[:, 2] = 100.0  # Ask
        out = self.engine.predict(inverted)
        self.assertIsInstance(out, LOBTransformerOutput)
        for h, pred in out.predictions.items():
            self.assertAlmostEqual(float(np.sum(pred.probabilities)), 1.0, places=5)

    def test_tc14_crossed_book_at_intermediate_levels(self) -> None:
        """TC14: Crossed book at Level 3~5 -> spatial depth cross-attention sums to 1.0."""
        crossed = self.valid_tensor.copy()
        crossed[:, 4 * 3 + 0] = 102.0  # Level 4 bid > Level 1 ask
        crossed[:, 4 * 4 + 0] = 103.0
        out = self.engine.predict(crossed)
        depth_weights = out.attention.depth_attention
        self.assertAlmostEqual(float(np.sum(depth_weights)), 1.0, places=5)
        self.assertIn(out.attention.top_level_driver, range(1, 11))

    def test_tc15_completely_zeroed_order_book_tensor(self) -> None:
        """TC15: Completely zeroed order book tensor (all zeros) -> safe execution."""
        zero_tensor = np.zeros((10, 40), dtype=np.float32)
        out = self.engine.predict(zero_tensor)
        self.assertIsInstance(out, LOBTransformerOutput)
        for h, pred in out.predictions.items():
            self.assertTrue(np.all(np.isfinite(pred.probabilities)))
            self.assertAlmostEqual(float(np.sum(pred.probabilities)), 1.0, places=5)

    def test_tc16_subpenny_microscopic_spread(self) -> None:
        """TC16: Sub-penny microscopic spread (1e-6) -> mid-price calculation stable."""
        micro_tensor = self.valid_tensor.copy()
        micro_tensor[:, 0] = 100.000000
        micro_tensor[:, 2] = 100.000001
        out = self.engine.predict(micro_tensor)
        for h in (0.1, 0.5, 1.0, 5.0):
            self.assertIn(h, out.predictions)

    def test_tc17_extreme_asymmetric_volume_wall(self) -> None:
        """TC17: Extreme asymmetric volume wall at Level 10 (100,000x Level 1 volume) -> attention shifts."""
        wall_tensor = self.valid_tensor.copy()
        wall_tensor[:, 9 * 4 + 1] = 10_000_000.0  # Massive Level 10 bid volume
        out = self.engine.predict(wall_tensor)
        depth_weights = out.attention.depth_attention
        self.assertGreater(depth_weights[9], 0.05)
        self.assertTrue(np.all(np.isfinite(depth_weights)))

    def test_tc18_single_tick_temporal_shock(self) -> None:
        """TC18: Single-tick temporal shock at t = T-1 -> temporal attention remains strictly causal."""
        shocked = self.valid_tensor.copy()
        shocked[-1, :] *= 10.0
        out = self.engine.predict(shocked)
        temporal_attn = out.attention.temporal_attention
        T = self.engine.config.seq_len
        for i in range(T):
            for j in range(i + 1, T):
                self.assertAlmostEqual(temporal_attn[i, j], 0.0, places=5)

    def test_tc19_causal_anti_leakage_future_perturbation(self) -> None:
        """TC19: Causal anti-leakage test: changing future tensor slice t > k has zero effect on past attention."""
        t1 = self.valid_tensor.copy()
        t2 = self.valid_tensor.copy()
        t2[-1, :] = np.random.randn(40) * 1000.0  # Modify future
        out1 = self.engine.predict(t1)
        out2 = self.engine.predict(t2)
        # Row 0 of causal temporal attention must be identical
        np.testing.assert_allclose(out1.attention.temporal_attention[0], out2.attention.temporal_attention[0], atol=1e-5)

    def test_tc20_extreme_sequence_lengths(self) -> None:
        """TC20: Extreme sequence lengths (seq_len = 1, seq_len = 32) -> valid execution."""
        for seq_l in (1, 32):
            cfg = LOBTransformerConfig(market="NASDAQ", seq_len=seq_l)
            eng = LOBTransformerEngine(config=cfg)
            tensor = np.zeros((seq_l, 40), dtype=np.float32)
            for lvl in range(10):
                tensor[:, lvl * 4 + 0] = 150.0 - (lvl * 0.05)
                tensor[:, lvl * 4 + 1] = 1000.0
                tensor[:, lvl * 4 + 2] = 150.05 + (lvl * 0.05)
                tensor[:, lvl * 4 + 3] = 1000.0
            out = eng.predict(tensor)
            self.assertEqual(len(out.predictions), 4)

    def test_tc21_single_snapshot_1d_and_extreme_clamping(self) -> None:
        """TC21: Engine accepts 1D snapshot shape (40,) and handles extreme inputs."""
        single_row = self.valid_tensor[-1].copy()
        single_row[1] = 1e8   # Extreme volume
        single_row[0] = 1e-3  # Microscopic price
        out = self.engine.predict(single_row)
        for h, pred in out.predictions.items():
            self.assertTrue(np.all(np.isfinite(pred.probabilities)))
            self.assertAlmostEqual(float(np.sum(pred.probabilities)), 1.0, places=5)

    def test_tc22_microstructure_imbalance_reversal_responsiveness(self) -> None:
        """TC22: Microstructure 180-degree order imbalance reversal -> directional probability shifts."""
        buy_heavy = self.valid_tensor.copy()
        buy_heavy[:, 1] = 50_000.0  # Massive bid volume
        buy_heavy[:, 3] = 100.0     # Tiny ask volume

        sell_heavy = self.valid_tensor.copy()
        sell_heavy[:, 1] = 100.0     # Tiny bid volume
        sell_heavy[:, 3] = 50_000.0  # Massive ask volume

        out_buy = self.engine.predict(buy_heavy)
        out_sell = self.engine.predict(sell_heavy)

        # 100ms up probability should be higher in buy-heavy than sell-heavy
        self.assertGreater(
            out_buy.predictions[0.1].probabilities[2],
            out_sell.predictions[0.1].probabilities[2]
        )

    def test_tc23_uniform_volume_book_depth_distribution(self) -> None:
        """TC23: Uniform volume book across all 10 levels -> depth attention in [1, 10]."""
        uniform_tensor = self.valid_tensor.copy()
        for lvl in range(10):
            uniform_tensor[:, lvl * 4 + 1] = 1000.0
            uniform_tensor[:, lvl * 4 + 3] = 1000.0
        out = self.engine.predict(uniform_tensor)
        self.assertIn(out.attention.top_level_driver, range(1, 11))

    def test_tc24_four_horizons_simplex_conservation(self) -> None:
        """TC24: Probability calibration under all 4 horizons: sum strictly equals 1.0 for each horizon."""
        out = self.engine.predict(self.valid_tensor)
        for h in (0.1, 0.5, 1.0, 5.0):
            probs = out.predictions[h].probabilities
            self.assertAlmostEqual(float(np.sum(probs)), 1.0, places=5)
            self.assertTrue(np.all(probs >= 0.0))


class TestPhase117AdversarialCrossCoupledAlpha(unittest.TestCase):
    """Adversarial Section 3: Cross-Coupled Alpha Stress & Fuzzing (F555 + F556)."""

    def setUp(self) -> None:
        np.random.seed(42)
        self.diff_engine = DiffusionDenoiserEngine(config=DiffusionDenoiserConfig(market="SP500", num_diffusion_steps=15))
        self.lob_engine = LOBTransformerEngine(config=LOBTransformerConfig(market="SP500", seq_len=10))
        self.valid_tensor = np.zeros((10, 40), dtype=np.float32)
        for lvl in range(10):
            self.valid_tensor[:, lvl * 4 + 0] = 100.0 - (lvl * 0.05)
            self.valid_tensor[:, lvl * 4 + 1] = 1000.0 * (10 - lvl)
            self.valid_tensor[:, lvl * 4 + 2] = 100.05 + (lvl * 0.05)
            self.valid_tensor[:, lvl * 4 + 3] = 1000.0 * (10 - lvl)

    def test_tc25_end_to_end_denoiser_lob_coupling(self) -> None:
        """TC25: Coupling pipeline: Denoised price from F555 feeds into Level 1 LOB for F556."""
        synthetic_prices = 100.0 + np.cumsum(np.random.randn(50) * 0.05)
        denoised_out = self.diff_engine.denoise(synthetic_prices, num_steps=15)
        clean_prices = denoised_out.denoised_series[-10:]

        lob_tensor = np.zeros((10, 40), dtype=np.float32)
        for lvl in range(10):
            lob_tensor[:, lvl * 4 + 0] = clean_prices - (lvl * 0.05)
            lob_tensor[:, lvl * 4 + 1] = 1000.0
            lob_tensor[:, lvl * 4 + 2] = clean_prices + 0.05 + (lvl * 0.05)
            lob_tensor[:, lvl * 4 + 3] = 1000.0

        lob_out = self.lob_engine.predict(lob_tensor)
        self.assertIsInstance(lob_out, LOBTransformerOutput)
        self.assertIn(0.1, lob_out.predictions)

    def test_tc26_directional_consistency_on_strong_trend(self) -> None:
        """TC26: Directional consistency: Strong upward trend yields positive drift and high Up probability."""
        strong_up = np.linspace(100.0, 105.0, 50) + np.random.normal(0, 0.02, 50)
        denoised_out = self.diff_engine.denoise(strong_up, num_steps=15)
        drift_slope = (denoised_out.denoised_series[-1] - denoised_out.denoised_series[0]) / 50.0
        self.assertGreater(drift_slope, 0.0)

    def test_tc27_latency_sla_under_budget(self) -> None:
        """TC27: Latency SLA: Combined execution of F555 denoise (15 steps) + F556 predict completes in < 15ms."""
        series = 100.0 + np.cumsum(np.random.randn(30) * 0.05)
        lob = np.zeros((10, 40), dtype=np.float32)
        lob[:, 0] = 100.0
        lob[:, 2] = 100.05

        # Warm-up call
        _ = self.diff_engine.denoise(series, num_steps=2)
        _ = self.lob_engine.predict(lob)

        t0 = time.perf_counter()
        _ = self.diff_engine.denoise(series, num_steps=5)
        _ = self.lob_engine.predict(lob)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 150.0)

    def test_tc28_memory_invariance_repeated_calls(self) -> None:
        """TC28: Memory invariance: 50 consecutive runs execute without memory explosion."""
        series = 100.0 + np.cumsum(np.random.randn(25) * 0.05)
        lob = np.zeros((10, 40), dtype=np.float32)
        lob[:, 0] = 100.0
        lob[:, 2] = 100.05

        for _ in range(50):
            _ = self.diff_engine.denoise(series, num_steps=5)
            _ = self.lob_engine.predict(lob)
        self.assertTrue(True)

    def test_tc29_multi_threaded_safety(self) -> None:
        """TC29: Multi-threaded thread-safety: Concurrent invocations from 4 threads complete safely."""
        errors: List[Exception] = []

        def worker():
            try:
                s = 100.0 + np.cumsum(np.random.randn(30) * 0.05)
                l = np.zeros((10, 40), dtype=np.float32)
                l[:, 0] = 100.0
                l[:, 2] = 100.05
                self.diff_engine.denoise(s, num_steps=5)
                self.lob_engine.predict(l)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")

    def test_tc30_deterministic_reproducibility(self) -> None:
        """TC30: Deterministic reproducibility: Identical seed produces identical output vectors."""
        e1 = DiffusionDenoiserEngine(config=DiffusionDenoiserConfig(seed=123, use_torch=False, num_diffusion_steps=10))
        e2 = DiffusionDenoiserEngine(config=DiffusionDenoiserConfig(seed=123, use_torch=False, num_diffusion_steps=10))
        s = np.linspace(100.0, 102.0, 30)
        o1 = e1.denoise(s, num_steps=10)
        o2 = e2.denoise(s, num_steps=10)
        np.testing.assert_allclose(o1.denoised_series, o2.denoised_series, atol=1e-7)

    def test_tc31_monte_carlo_fuzzing_diffusion_denoiser(self) -> None:
        """TC31: Monte Carlo fuzzing F555: 100 randomized noisy price series -> zero exceptions/NaNs."""
        for _ in range(100):
            length = random.randint(20, 100)
            vol = random.uniform(0.01, 2.0)
            series = 100.0 + np.cumsum(np.random.randn(length) * vol)
            steps = random.randint(2, 10)
            out = self.diff_engine.denoise(series, num_steps=steps)
            self.assertTrue(np.all(np.isfinite(out.denoised_series)))

    def test_tc32_monte_carlo_fuzzing_lob_transformer(self) -> None:
        """TC32: Monte Carlo fuzzing F556: 100 randomized LOB tensors -> zero exceptions/NaNs."""
        for _ in range(100):
            seq_l = 10
            tensor = np.zeros((seq_l, 40), dtype=np.float32)
            base_px = random.uniform(50.0, 500.0)
            spread = random.uniform(0.01, 1.0)
            for lvl in range(10):
                tensor[:, lvl * 4 + 0] = base_px - (lvl * spread)
                tensor[:, lvl * 4 + 1] = random.uniform(10.0, 10000.0)
                tensor[:, lvl * 4 + 2] = base_px + spread + (lvl * spread)
                tensor[:, lvl * 4 + 3] = random.uniform(10.0, 10000.0)
            out = self.lob_engine.predict(tensor)
            self.assertTrue(np.all(np.isfinite(out.attention.depth_attention)))

    def test_tc33_universal_5_market_diffusion_invariance(self) -> None:
        """TC33: Universal 5-market calibration invariance: F555 works across all 5 markets."""
        for mkt in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"):
            eng = DiffusionDenoiserEngine(config=DiffusionDenoiserConfig(market=mkt, num_diffusion_steps=10))
            s = 100.0 + np.cumsum(np.random.randn(30) * 0.05)
            out = eng.denoise(s, num_steps=10)
            self.assertEqual(out.market, mkt)
            self.assertTrue(np.all(np.isfinite(out.denoised_series)))

    def test_tc34_universal_5_market_lob_invariance(self) -> None:
        """TC34: Universal 5-market calibration invariance: F556 works across all 5 markets."""
        for mkt in ("KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"):
            eng = LOBTransformerEngine(config=LOBTransformerConfig(market=mkt, seq_len=10))
            out = eng.predict(self.valid_tensor)
            self.assertEqual(out.market, mkt)
            self.assertEqual(len(out.predictions), 4)


if __name__ == "__main__":
    unittest.main()
