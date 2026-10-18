r"""
tests/test_phase120_challenger2_stress.py
=========================================
Empirical Stress-Testing, Adversarial Challenge & Deterministic Parity Harness for:
Physics-Informed Neural Operator (PINO) Macro-Micro Fluid Dynamics Price Discovery Engine (Feature F570).
Phase 120 (Release R136 / v127 Production Master).

Executed by: teamwork_preview_challenger_m1_2 (Empirical Challenger)
"""

from __future__ import annotations

import hashlib
import math
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.pino_fluid_price_discovery as pino_mod
from src.ai.pino_fluid_price_discovery import (
    DEFAULT_HORIZONS,
    MARKET_PINO_FLUID_PROFILES,
    FluidRegime,
    PINOFluidConfig,
    PINOFluidPriceDiscoveryEngine,
    get_market_profile,
    _TORCH_AVAILABLE,
    compute_spectral_derivatives_1d,
)

if _TORCH_AVAILABLE:
    import torch


class TestPhase120Challenger2Stress(unittest.TestCase):
    """
    Empirical Stress Testing and Verification Harness for F570 PINO Fluid Price Discovery.
    """

    def setUp(self) -> None:
        self.rng = np.random.RandomState(42)
        # Standard balanced L3 book
        self.std_bids = [(100.0 - 0.01 * i, 100.0 + 10.0 * i) for i in range(20)]
        self.std_asks = [(100.01 + 0.01 * i, 100.0 + 10.0 * i) for i in range(20)]
        self.std_mid = 100.005

    # =======================================================================
    # SECTION 1: Dual-Backend Deterministic Parity Verification (PyTorch vs Pure NumPy)
    # Target: Relative error <= 1e-4 across network outputs and physical forecasts
    # =======================================================================
    def test_challenge_01_dual_backend_raw_network_parity(self) -> None:
        """Verify layer-level and raw network parity between PyTorch and NumPy (rel_err <= 1e-4)."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not available in this environment.")

        # Test across multiple random spatial field inputs and seeds
        for seed in [42, 100, 2026]:
            engine_torch = PINOFluidPriceDiscoveryEngine(market="SP500", use_torch=True, seed=seed)
            engine_numpy = PINOFluidPriceDiscoveryEngine(market="SP500", use_torch=False, seed=seed)

            # Generate random smooth physical fields
            x = np.linspace(-32.0, 32.0, 64)
            u = np.sin(x / 4.0)
            rho = 1.0 + 0.5 * np.cos(x / 8.0)
            p = - np.tanh(x / 10.0)
            input_field = np.stack([u, rho, p], axis=0)

            out_torch = engine_torch._forward_network(input_field)
            out_numpy = engine_numpy._forward_network(input_field)

            # Assert shape match
            self.assertEqual(out_torch.shape, out_numpy.shape)

            # Check max absolute and relative error
            abs_err = float(np.max(np.abs(out_torch - out_numpy)))
            rel_err = float(np.max(np.abs(out_torch - out_numpy) / (np.abs(out_numpy) + 1e-4)))

            self.assertLessEqual(
                rel_err,
                1e-4,
                f"Seed {seed}: Raw network rel_err {rel_err:.2e} exceeded 1e-4 threshold (abs_err={abs_err:.2e})",
            )

    def test_challenge_02_dual_backend_forecast_parity_across_order_books(self) -> None:
        """Verify end-to-end forecast parity between PyTorch and NumPy across diverse order books (rel_err <= 1e-4)."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not available in this environment.")

        test_scenarios = [
            # 1. Balanced book
            (self.std_bids, self.std_asks, self.std_mid, "balanced"),
            # 2. Strong buy imbalance
            (
                [(100.0 - 0.01 * i, 5000.0) for i in range(10)],
                [(100.01 + 0.01 * i, 100.0) for i in range(10)],
                100.005,
                "buy_heavy",
            ),
            # 3. Strong sell imbalance
            (
                [(100.0 - 0.01 * i, 100.0) for i in range(10)],
                [(100.01 + 0.01 * i, 5000.0) for i in range(10)],
                100.005,
                "sell_heavy",
            ),
            # 4. Wide spread
            (
                [(98.0 - 0.01 * i, 500.0) for i in range(10)],
                [(102.0 + 0.01 * i, 500.0) for i in range(10)],
                100.0,
                "wide_spread",
            ),
        ]

        for bids, asks, mid, label in test_scenarios:
            engine_t = PINOFluidPriceDiscoveryEngine(market="SP500", use_torch=True, seed=42)
            engine_np = PINOFluidPriceDiscoveryEngine(market="SP500", use_torch=False, seed=42)

            res_t = engine_t.forecast_price_discovery(bids, asks, mid)
            res_np = engine_np.forecast_price_discovery(bids, asks, mid)

            # 1. Forecasted density relative error
            density_rel_err = float(
                np.max(
                    np.abs(res_t.forecasted_density - res_np.forecasted_density)
                    / (np.abs(res_np.forecasted_density) + 1e-6)
                )
            )
            self.assertLessEqual(
                density_rel_err,
                1e-4,
                f"[{label}] Forecasted density rel_err {density_rel_err:.2e} exceeded 1e-4",
            )

            # 2. Forecasted velocity relative error
            vel_rel_err = float(
                np.max(
                    np.abs(res_t.forecasted_velocity - res_np.forecasted_velocity)
                    / (np.abs(res_np.forecasted_velocity) + 1e-4)
                )
            )
            self.assertLessEqual(
                vel_rel_err,
                1e-4,
                f"[{label}] Forecasted velocity rel_err {vel_rel_err:.2e} exceeded 1e-4",
            )

            # 3. Composite drift relative error
            drift_t = res_t.fluid_drift_composite_bps
            drift_np = res_np.fluid_drift_composite_bps
            drift_rel = float(abs(drift_t - drift_np) / (abs(drift_np) + 1e-4))
            self.assertLessEqual(
                drift_rel,
                1e-4,
                f"[{label}] Composite drift rel_err {drift_rel:.2e} (t={drift_t}, np={drift_np}) exceeded 1e-4",
            )

            # 4. Jump velocity and drift across all horizons
            for h in DEFAULT_HORIZONS:
                ht = res_t.horizons[h]
                hn = res_np.horizons[h]

                # Shock displacement match
                self.assertAlmostEqual(
                    ht.shock_displacement_ticks,
                    hn.shock_displacement_ticks,
                    delta=1e-3,
                    msg=f"[{label}] Horizon {h}s shock displacement mismatch",
                )

                # Jump velocity relative error
                v_rel = float(
                    abs(ht.jump_velocity_ticks_per_sec - hn.jump_velocity_ticks_per_sec)
                    / (abs(hn.jump_velocity_ticks_per_sec) + 1e-4)
                )
                self.assertLessEqual(
                    v_rel,
                    1e-4,
                    f"[{label}] Horizon {h}s jump velocity rel_err {v_rel:.2e} exceeded 1e-4",
                )

                # Directional drift relative error
                d_rel = float(
                    abs(ht.directional_drift_bps - hn.directional_drift_bps)
                    / (abs(hn.directional_drift_bps) + 1e-4)
                )
                self.assertLessEqual(
                    d_rel,
                    1e-4,
                    f"[{label}] Horizon {h}s drift rel_err {d_rel:.2e} exceeded 1e-4",
                )

    def test_challenge_03_dual_backend_parity_all_five_markets(self) -> None:
        """Verify PyTorch vs NumPy parity (rel_err <= 1e-4) holds across all 5 markets."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not available in this environment.")

        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

        for mkt in markets:
            engine_t = PINOFluidPriceDiscoveryEngine(market=mkt, use_torch=True, seed=42)
            engine_np = PINOFluidPriceDiscoveryEngine(market=mkt, use_torch=False, seed=42)

            tick = engine_t.config.tick_size
            mid = 70000.0 if "KOS" in mkt else 100.0
            bids = [(mid - tick * (i + 1), 300.0 * (10 - i)) for i in range(10)]
            asks = [(mid + tick * (i + 1), 300.0 * (i + 1)) for i in range(10)]

            res_t = engine_t.forecast_price_discovery(bids, asks, mid)
            res_np = engine_np.forecast_price_discovery(bids, asks, mid)

            drift_rel = float(abs(res_t.fluid_drift_composite_bps - res_np.fluid_drift_composite_bps) / (abs(res_np.fluid_drift_composite_bps) + 1e-4))
            self.assertLessEqual(
                drift_rel,
                1e-4,
                f"Market {mkt}: Composite drift rel_err {drift_rel:.2e} exceeded 1e-4",
            )

    # =======================================================================
    # SECTION 2: 5-Market Shockwave Velocity & Drift Profile Validation
    # Markets: SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ
    # =======================================================================
    def test_challenge_04_five_market_directional_drift_signs(self) -> None:
        """Verify across all 5 markets that buy-heavy produces positive drift and sell-heavy negative."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

        for mkt in markets:
            engine = PINOFluidPriceDiscoveryEngine(market=mkt, seed=42)
            tick = engine.config.tick_size
            mid = 70000.0 if "KOS" in mkt else 100.0

            # Buy-heavy order book (90% bids)
            bids_buy = [(mid - tick * (i + 1), 1000.0) for i in range(10)]
            asks_buy = [(mid + tick * (i + 1), 100.0) for i in range(10)]

            res_buy = engine.forecast_price_discovery(bids_buy, asks_buy, mid_price=mid)
            self.assertGreater(
                res_buy.fluid_drift_composite_bps,
                0.0,
                f"Market {mkt}: Expected positive drift for buy-heavy book, got {res_buy.fluid_drift_composite_bps}",
            )

            # Sell-heavy order book (90% asks)
            bids_sell = [(mid - tick * (i + 1), 100.0) for i in range(10)]
            asks_sell = [(mid + tick * (i + 1), 1000.0) for i in range(10)]

            res_sell = engine.forecast_price_discovery(bids_sell, asks_sell, mid_price=mid)
            self.assertLess(
                res_sell.fluid_drift_composite_bps,
                0.0,
                f"Market {mkt}: Expected negative drift for sell-heavy book, got {res_sell.fluid_drift_composite_bps}",
            )

    def test_challenge_05_five_market_shockwave_velocity_scaling(self) -> None:
        """Verify jump velocity v_jump = x_shock / H satisfies physical kinematic scaling across all 5 markets."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]

        for mkt in markets:
            engine = PINOFluidPriceDiscoveryEngine(market=mkt, seed=42)
            tick = engine.config.tick_size
            mid = 70000.0 if "KOS" in mkt else 100.0

            bids = [(mid - tick * (i + 1), 500.0 * (10 - i)) for i in range(10)]
            asks = [(mid + tick * (i + 1), 200.0 * (i + 1)) for i in range(10)]

            res = engine.forecast_price_discovery(bids, asks, mid_price=mid)

            for h in DEFAULT_HORIZONS:
                forecast = res.horizons[h]
                expected_v = forecast.shock_displacement_ticks / h
                self.assertAlmostEqual(
                    forecast.jump_velocity_ticks_per_sec,
                    expected_v,
                    places=5,
                    msg=f"Market {mkt}, Horizon {h}s: Jump velocity formula violation",
                )
                self.assertTrue(math.isfinite(forecast.jump_velocity_ticks_per_sec))
                self.assertTrue(math.isfinite(forecast.directional_drift_bps))

    def test_challenge_06_market_specific_viscosity_and_drift_multipliers(self) -> None:
        """Verify market profile parameters correctly differentiate market dynamics via get_market_profile."""
        cfg_sp = get_market_profile("SP500")
        cfg_nq = get_market_profile("NASDAQ")
        cfg_r2 = get_market_profile("RUSSELL2000")
        cfg_kp = get_market_profile("KOSPI")
        cfg_kd = get_market_profile("KOSDAQ")

        self.assertGreater(cfg_sp.kinematic_viscosity, cfg_nq.kinematic_viscosity)
        self.assertGreater(cfg_nq.kinematic_viscosity, cfg_r2.kinematic_viscosity)
        self.assertGreater(cfg_r2.base_drift_multiplier, cfg_nq.base_drift_multiplier)
        self.assertGreater(cfg_nq.base_drift_multiplier, cfg_sp.base_drift_multiplier)

        # Korean markets tick sizes
        self.assertEqual(cfg_kp.tick_size, 100.0)
        self.assertEqual(cfg_kd.tick_size, 50.0)
        self.assertEqual(cfg_sp.tick_size, 0.01)

    # =======================================================================
    # SECTION 3: Multi-Horizon Inference Latency SLA Benchmarking
    # Target: Multi-horizon (100ms, 500ms, 1s, 5s) latency under production SLA (< 15ms CPU)
    # =======================================================================
    def test_challenge_07_inference_latency_sla_benchmarking(self) -> None:
        """Benchmark multi-horizon inference latency over 50 sequential passes."""
        engine = PINOFluidPriceDiscoveryEngine(market="SP500", seed=42)

        # Warm-up pass
        for _ in range(5):
            engine.forecast_price_discovery(self.std_bids, self.std_asks, self.std_mid)

        n_trials = 50
        latencies_ms: List[float] = []

        for _ in range(n_trials):
            t0 = time.perf_counter()
            res = engine.forecast_price_discovery(self.std_bids, self.std_asks, self.std_mid)
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

        mean_lat = float(np.mean(latencies_ms))
        p95_lat = float(np.percentile(latencies_ms, 95))
        p99_lat = float(np.percentile(latencies_ms, 99))

        # Mean latency SLA < 15.0ms on CPU
        self.assertLess(
            mean_lat,
            15.0,
            f"Mean inference latency {mean_lat:.2f}ms exceeds 15.0ms SLA",
        )
        # P99 latency SLA < 30.0ms on CPU
        self.assertLess(
            p99_lat,
            30.0,
            f"P99 inference latency {p99_lat:.2f}ms exceeds 30.0ms SLA",
        )

    # =======================================================================
    # SECTION 4: Physics Invariants & Conservation Laws Stress Tests
    # =======================================================================
    def test_challenge_08_mass_conservation_invariant_across_horizons(self) -> None:
        """Empirically verify that mass conservation error <= 1e-4 holds under severe asymmetry."""
        engine = PINOFluidPriceDiscoveryEngine(market="SP500", seed=42)

        # Extreme unbalanced book
        extreme_bids = [(100.0 - 0.01 * i, 10000.0 * (i + 1)) for i in range(15)]
        extreme_asks = [(100.05 + 0.01 * i, 10.0) for i in range(5)]

        res = engine.forecast_price_discovery(extreme_bids, extreme_asks, mid_price=100.025)

        self.assertLessEqual(
            res.mass_conservation_error,
            1e-4,
            f"Mass conservation error {res.mass_conservation_error:.2e} exceeded 1e-4",
        )

        # Check total volume against integrated density
        total_vol = res.initial_state.total_volume
        final_mass = float(np.sum(res.forecasted_density) * engine.dx)
        rel_diff = abs(final_mass - total_vol) / total_vol
        self.assertLessEqual(
            rel_diff,
            1e-4,
            f"Final integrated mass relative difference {rel_diff:.2e} exceeded 1e-4",
        )

    def test_challenge_09_spectral_derivative_accuracy(self) -> None:
        """Verify spectral derivative accuracy on analytical test function sin(2 pi x / L) with periodic grid."""
        L = 64.0
        x = np.linspace(0, L, 64, endpoint=False)
        u = np.sin(2.0 * np.pi * x / L)

        expected_du = (2.0 * np.pi / L) * np.cos(2.0 * np.pi * x / L)
        expected_d2u = - ((2.0 * np.pi / L) ** 2) * np.sin(2.0 * np.pi * x / L)

        du_dx, d2u_dx2 = compute_spectral_derivatives_1d(u, L)

        np.testing.assert_allclose(du_dx, expected_du, atol=1e-5)
        np.testing.assert_allclose(d2u_dx2, expected_d2u, atol=1e-5)

    # =======================================================================
    # SECTION 5: Adversarial Boundary & Stress Cases
    # =======================================================================
    def test_challenge_10_adversarial_nan_inf_negative_quotes(self) -> None:
        """Verify graceful sanitization when given malicious or corrupted quote feeds."""
        engine = PINOFluidPriceDiscoveryEngine(market="SP500", seed=42)

        corrupt_bids = [
            (float("nan"), 100.0),
            (100.0, float("nan")),
            (float("inf"), 50.0),
            (99.0, float("-inf")),
            (-50.0, 100.0),      # Negative price is finite, but handled
            (98.0, -20.0),       # Negative volume ignored
            (99.5, 200.0),       # Valid quote
        ]
        corrupt_asks = [
            (float("nan"), 100.0),
            (100.5, 200.0),      # Valid quote
            (float("inf"), float("inf")),
        ]

        res = engine.forecast_price_discovery(corrupt_bids, corrupt_asks, mid_price=100.0)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertTrue(math.isfinite(res.max_shock_velocity))
        self.assertFalse(np.isnan(res.forecasted_density).any())
        self.assertFalse(np.isnan(res.forecasted_velocity).any())

    def test_challenge_11_adversarial_completely_empty_and_flat_book(self) -> None:
        """Verify zero or empty book does not trigger ZeroDivisionError or NaN and stabilizes into diffusion."""
        engine = PINOFluidPriceDiscoveryEngine(market="SP500", seed=42)

        res_empty = engine.forecast_price_discovery([], [], mid_price=None)
        self.assertTrue(math.isfinite(res_empty.fluid_drift_composite_bps))
        self.assertTrue(res_empty.initial_state.total_volume > 0.0)  # Baseline fallback
        self.assertIn(
            res_empty.regime_fluid_state,
            [FluidRegime.EQUILIBRIUM_DIFFUSION.value, FluidRegime.LIQUIDITY_VOID.value],
        )

    def test_challenge_12_adversarial_flash_crash_single_side_void(self) -> None:
        """Simulate flash crash order book where bids completely evaporate."""
        engine = PINOFluidPriceDiscoveryEngine(market="SP500", seed=42)

        # No bids, massive aggressive sell walls
        asks_wall = [(100.01 + 0.05 * i, 50000.0) for i in range(20)]

        res = engine.forecast_price_discovery([], asks_wall, mid_price=100.0)
        self.assertIn(
            res.regime_fluid_state,
            [FluidRegime.LIQUIDITY_VOID.value, FluidRegime.SHOCKWAVE_BURST.value],
        )
        self.assertLess(res.fluid_drift_composite_bps, 0.0)

    # =======================================================================
    # SECTION 6: Dual-Tree Cryptographic Parity
    # =======================================================================
    def test_challenge_13_dual_tree_sha256_cryptographic_parity(self) -> None:
        """Verify 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/."""
        p1 = PROJECT_ROOT / "src" / "ai" / "pino_fluid_price_discovery.py"
        p2 = PROJECT_ROOT / "trading_system" / "src" / "ai" / "pino_fluid_price_discovery.py"

        self.assertTrue(p1.exists(), f"Primary file missing: {p1}")
        self.assertTrue(p2.exists(), f"Mirror file missing: {p2}")

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()

        self.assertEqual(
            h1,
            h2,
            f"Dual-tree SHA-256 mismatch!\nPrimary ({p1}): {h1}\nMirror  ({p2}): {h2}",
        )


if __name__ == "__main__":
    unittest.main()
