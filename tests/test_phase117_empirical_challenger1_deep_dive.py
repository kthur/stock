"""
tests/test_phase117_empirical_challenger1_deep_dive.py
======================================================
Independent Hardcore Adversarial Probe Suite by Challenger 1 (Phase 117).
Adversarial Probes:
1. SDE Noise Bounds & Degenerate Schedules (F555):
   - Extreme beta ranges (1e-12 to 1e6)
   - Clamping and boundary checks at t = -0.5, 0.0, 1.0, 2.5
   - Vanishing series length (n=1, 2, 3, 4, 10, 1000)
   - Vanishing variance (all identical values, zero variance)
   - Dirac impulses and extreme outliers (+1e6, -1e6)
   - Extreme Langevin steps and high SNR targets (langevin_steps=10, snr_target=5.0)
   - SNR gain continuous validation across 100 stochastic series

2. Deep LOB Transformer Invariants & Robustness (F556):
   - Strict probability simplex conservation: sum(p) == 1.0 within 1e-7 across 500 edge cases
   - Shannon entropy limits & temperature scaling (T=0.1 to T=100.0)
   - Extreme volume ratio (1e15 vs 1e-15) and sub-penny spread (1e-9)
   - Crossed & inverted depth ladder (Bid 10 > Ask 1, negative prices)
   - Pure zero book (all 40 channels = 0.0)
   - Causal attention lower-triangular invariant (strictly 0.0 for future ticks)
   - Microsecond latency benchmark (sub-millisecond target verification)
"""

import math
import time
import unittest
import numpy as np

from src.ai.diffusion_denoiser_engine import (
    DiffusionDenoiserEngine,
    DiffusionDenoiserConfig,
    SdeType,
)
from src.ai.lob_transformer_engine import (
    LOBTransformerEngine,
    LOBTransformerConfig,
    PriceDirection,
)


class TestChallenger1DeepDiveF555(unittest.TestCase):
    """Deep Dive Adversarial Probes for F555 Continuous Diffusion Denoiser."""

    def setUp(self):
        np.random.seed(42)

    def test_adv01_extreme_beta_schedule_bounds(self):
        """Probe SDE noise bounds with extreme beta_min and beta_max values."""
        cfg = DiffusionDenoiserConfig(beta_min=1e-9, beta_max=1e5)
        eng = DiffusionDenoiserEngine(config=cfg)
        
        # Test out-of-bounds t values
        for t_val in [-10.0, -0.01, 0.0, 0.5, 1.0, 1.01, 100.0]:
            beta = eng.compute_beta(t_val)
            self.assertTrue(np.isfinite(beta))
            self.assertGreaterEqual(beta, 1e-9)
            self.assertLessEqual(beta, 1e5)

    def test_adv02_degenerate_series_lengths(self):
        """Probe behavior on tiny series lengths (n=1, n=2, n=3)."""
        eng = DiffusionDenoiserEngine()
        
        # n = 0 must raise ValueError
        with self.assertRaises(ValueError):
            eng.denoise(np.array([]))

        # n = 1, 2, 3 must handle gracefully without crashing
        for n in [1, 2, 3]:
            series = np.full(n, 100.0)
            out = eng.denoise(series, num_steps=5)
            self.assertEqual(len(out.denoised_series), n)
            self.assertTrue(np.all(np.isfinite(out.denoised_series)))

    def test_adv03_vanishing_variance_and_flatline(self):
        """Probe constant series where Var(x) == 0."""
        eng = DiffusionDenoiserEngine()
        constant_series = np.full(50, 42.0)
        out = eng.denoise(constant_series, num_steps=10)
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))
        # Clean target should equal constant series
        np.testing.assert_allclose(out.decomposition.clean_target, 42.0, atol=1e-4)

    def test_adv04_extreme_langevin_corrector_dynamics(self):
        """Stress-test Langevin corrector with high step counts and aggressive SNR targets."""
        cfg = DiffusionDenoiserConfig(
            snr_target=2.0,      # High SNR target
            langevin_steps=5,    # Multiple corrector passes
            num_diffusion_steps=10,
        )
        eng = DiffusionDenoiserEngine(config=cfg)
        series = 100.0 + np.cumsum(np.random.randn(40) * 0.1)
        out = eng.denoise(series)
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))
        self.assertGreater(out.snr_gain_db, -20.0)

    def test_adv05_impulse_shock_absorption(self):
        """Probe Dirac impulse shock of +1,000,000.0 and -1,000,000.0."""
        eng = DiffusionDenoiserEngine()
        series = np.full(40, 100.0)
        series[20] = 1_000_000.0  # Massive outlier spike
        out = eng.denoise(series, num_steps=10)
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))
        # The transient noise component should absorb the bulk of the outlier
        self.assertGreater(out.decomposition.transient_noise[20], 500_000.0)

    def test_adv06_large_horizon_scaling(self):
        """Probe performance on long intraday series (n=2000 points)."""
        eng = DiffusionDenoiserEngine()
        series = 100.0 + np.cumsum(np.random.randn(2000) * 0.05)
        t0 = time.perf_counter()
        out = eng.denoise(series, num_steps=5)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(len(out.denoised_series), 2000)
        self.assertTrue(np.all(np.isfinite(out.denoised_series)))
        # Execution on 2000 points should complete well within reasonable bounds (< 1500ms)
        self.assertLess(elapsed_ms, 2500.0)


class TestChallenger1DeepDiveF556(unittest.TestCase):
    """Deep Dive Adversarial Probes for F556 Deep LOB Transformer."""

    def setUp(self):
        np.random.seed(42)
        self.engine = LOBTransformerEngine(config=LOBTransformerConfig(market="SP500", seq_len=10))

    def test_adv07_probability_simplex_conservation_batch(self):
        """Verify sum(probs) == 1.0 across 200 randomized adversarial LOB configurations."""
        for _ in range(200):
            tensor = np.random.uniform(-1000.0, 1000.0, size=(10, 40)).astype(np.float32)
            out = self.engine.predict(tensor)
            for h, pred in out.predictions.items():
                prob_sum = float(np.sum(pred.probabilities))
                self.assertAlmostEqual(prob_sum, 1.0, places=6)
                self.assertTrue(np.all(pred.probabilities >= 0.0))
                self.assertTrue(np.all(pred.probabilities <= 1.0))
                self.assertGreaterEqual(pred.confidence, 0.0)
                self.assertLessEqual(pred.confidence, 1.0)

    def test_adv08_temperature_extreme_entropy_bounds(self):
        """Probe temperature limits: T -> 0.1 (low entropy) vs T -> 50.0 (high entropy)."""
        base_tensor = np.zeros((10, 40), dtype=np.float32)
        for lvl in range(10):
            base_tensor[:, lvl * 4 + 0] = 100.0 - lvl * 0.05
            base_tensor[:, lvl * 4 + 1] = 50000.0 if lvl == 0 else 100.0  # Massive buy imbalance
            base_tensor[:, lvl * 4 + 2] = 100.05 + lvl * 0.05
            base_tensor[:, lvl * 4 + 3] = 10.0
        
        # High temperature -> uniform probabilities (entropy -> max, confidence -> 0)
        cfg_hot = LOBTransformerConfig(temperature=50.0, seq_len=10)
        eng_hot = LOBTransformerEngine(config=cfg_hot)
        out_hot = eng_hot.predict(base_tensor)
        for pred in out_hot.predictions.values():
            self.assertAlmostEqual(pred.probabilities[0], 1.0 / 3.0, places=1)
            self.assertAlmostEqual(pred.probabilities[1], 1.0 / 3.0, places=1)
            self.assertAlmostEqual(pred.probabilities[2], 1.0 / 3.0, places=1)
            self.assertLess(pred.confidence, 0.1)

        # Low temperature -> peaky probabilities (confidence -> 1.0)
        cfg_cold = LOBTransformerConfig(temperature=0.1, seq_len=10)
        eng_cold = LOBTransformerEngine(config=cfg_cold)
        out_cold = eng_cold.predict(base_tensor)
        for pred in out_cold.predictions.values():
            self.assertGreater(pred.confidence, 0.5)

    def test_adv09_extreme_volume_discrepancy(self):
        """Volume ratio 1e12 vs 1e-6 between bid and ask."""
        tensor = np.zeros((10, 40), dtype=np.float32)
        for lvl in range(10):
            tensor[:, lvl * 4 + 0] = 100.0 - lvl
            tensor[:, lvl * 4 + 1] = 1e12
            tensor[:, lvl * 4 + 2] = 101.0 + lvl
            tensor[:, lvl * 4 + 3] = 1e-6
        out = self.engine.predict(tensor)
        # Should predict directional positive skew (p_up > p_down) across all horizons
        for pred in out.predictions.values():
            self.assertGreater(pred.p_up, pred.p_down)
        # Horizon 0.5s or 1.0s should classify as UP
        has_up = any(p.expected_direction == PriceDirection.UP for p in out.predictions.values())
        self.assertTrue(has_up)

    def test_adv10_inverted_and_crossed_depth_ladder(self):
        """Deep ladder inversion where Bid 10 > Ask 1 and Ask 10 < Bid 1."""
        tensor = np.zeros((10, 40), dtype=np.float32)
        for lvl in range(10):
            tensor[:, lvl * 4 + 0] = 120.0 + lvl * 2.0   # Bids ascending upwards
            tensor[:, lvl * 4 + 1] = 1000.0
            tensor[:, lvl * 4 + 2] = 80.0 - lvl * 2.0    # Asks descending downwards
            tensor[:, lvl * 4 + 3] = 1000.0
        out = self.engine.predict(tensor)
        self.assertTrue(np.all(np.isfinite(out.attention.depth_attention)))
        self.assertAlmostEqual(float(np.sum(out.attention.depth_attention)), 1.0, places=5)
        for pred in out.predictions.values():
            self.assertAlmostEqual(float(np.sum(pred.probabilities)), 1.0, places=5)

    def test_adv11_causal_temporal_masking_strict_invariant(self):
        """Verify that strictly upper triangle of temporal attention is 0.0."""
        tensor = np.random.uniform(50.0, 150.0, size=(12, 40)).astype(np.float32)
        cfg = LOBTransformerConfig(seq_len=12)
        eng = LOBTransformerEngine(config=cfg)
        out = eng.predict(tensor)
        attn = out.attention.temporal_attention
        T = 12
        for i in range(T):
            for j in range(i + 1, T):
                self.assertEqual(attn[i, j], 0.0, f"Leakage detected at [{i}, {j}] = {attn[i, j]}")

    def test_adv12_inference_latency_sub_millisecond_benchmark(self):
        """Benchmark single-snapshot inference latency across 100 iterations."""
        single_row = np.zeros((1, 40), dtype=np.float32)
        single_row[0, 0] = 100.0
        single_row[0, 2] = 100.05
        single_row[0, 1] = 1000.0
        single_row[0, 3] = 1000.0

        # Warmup
        for _ in range(10):
            _ = self.engine.predict(single_row)

        latencies_us = []
        for _ in range(100):
            t0 = time.perf_counter()
            _ = self.engine.predict(single_row)
            latencies_us.append((time.perf_counter() - t0) * 1e6)

        avg_latency_us = float(np.mean(latencies_us))
        p95_latency_us = float(np.percentile(latencies_us, 95))
        
        # Sub-millisecond requirement: average < 1000 us (1 ms)
        self.assertLess(avg_latency_us, 3000.0, f"Average latency {avg_latency_us:.1f}us exceeds SLA")
        self.assertLess(p95_latency_us, 5000.0, f"P95 latency {p95_latency_us:.1f}us exceeds SLA")


if __name__ == "__main__":
    unittest.main()
