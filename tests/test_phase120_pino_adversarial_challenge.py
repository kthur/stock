r"""
tests/test_phase120_pino_adversarial_challenge.py
=================================================
EMPIRICAL ADVERSARIAL STRESS CHALLENGE SUITE FOR FEATURE F570:
Physics-Informed Neural Operator (PINO) Macro-Micro Fluid Dynamics Price Discovery Engine.
Phase 120 (Release R136 / v127 Production Master).

Adversarial Stress Dimensions:
  1. Degenerate books (empty books, negative spread, infinite spread, off-grid quotes, zero/negative volume, single quotes, crossed books)
  2. Flash crash shockwaves and massive liquidity voids (100M share injections, 99.999% queue depletion, asymmetric shockwaves)
  3. High-frequency oscillations, Dirac combs, Nyquist wave injections, and Gibbs ringing checks
  4. Extreme volume scales (micro-volume 1e-12 to macro-volume 1e16) and volume ratios (1e18 dynamic range)
  5. Multi-grid resolution scaling (Nx in {16, 32, 64, 128, 256}) and Fourier mode truncation
  6. Strict mathematical invariants:
     - Mass conservation invariant: Delta V / V_total <= 1e-4 across all conditions and horizons
     - Boundary velocity vanishing: |u(+-X)| < 1e-5
     - Density non-negativity: rho(x) >= 0 everywhere
     - Finite drift and bounded PDE residual norm
  7. 5-market empirical profile stress tests (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ)
  8. Deterministic dual-backend parity (PyTorch vs pure NumPy) under stress
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.ai.pino_fluid_price_discovery import (
    PINOFluidConfig,
    PINOFluidPriceDiscoveryEngine,
    PINOFluidForecastResult,
    FluidFieldState,
    FluidRegime,
    DEFAULT_HORIZONS,
    MASS_CONSERVATION_TOLERANCE,
    MARKET_PINO_FLUID_PROFILES,
    compute_spectral_derivatives_1d,
    SpectralConv1dNumPy,
    SpectralConv2dNumPy,
    PINONetworkNumPy,
    _TORCH_AVAILABLE,
)

if _TORCH_AVAILABLE:
    import torch


class TestPhase120PINOAdversarialChallenge(unittest.TestCase):
    """Adversarial stress challenge suite for PINO Fluid Price Discovery Engine."""

    def setUp(self) -> None:
        self.engine_sp500 = PINOFluidPriceDiscoveryEngine(market="SP500", seed=42)
        self.engine_np = PINOFluidPriceDiscoveryEngine(market="SP500", use_torch=False, seed=42)

    # =========================================================================
    # 1. DEGENERATE BOOKS & EXTREME BOUNDARY CONDITIONS
    # =========================================================================

    def test_adv01_completely_empty_book_with_none_mid(self) -> None:
        """ADV-01: Completely empty book with mid_price=None."""
        res = self.engine_sp500.forecast_price_discovery(bids=[], asks=[], mid_price=None)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertTrue(math.isfinite(res.mass_conservation_error))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertTrue(np.all(res.forecasted_density >= 0.0))
        self.assertLess(abs(res.forecasted_velocity[0]), 1e-5)
        self.assertLess(abs(res.forecasted_velocity[-1]), 1e-5)

    def test_adv02_empty_book_with_abnormal_mid_prices(self) -> None:
        """ADV-02: Empty book with 0, negative, NaN, Inf mid prices."""
        for bad_mid in [0.0, -100.0, float("nan"), float("inf"), float("-inf")]:
            res = self.engine_sp500.forecast_price_discovery(bids=[], asks=[], mid_price=bad_mid)
            self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
            self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
            self.assertTrue(np.all(res.forecasted_density >= 0.0))

    def test_adv03_crossed_inverted_order_book(self) -> None:
        """ADV-03: Crossed book where best bid > best ask (inverted spread)."""
        crossed_bids = [(105.0, 500.0), (104.0, 300.0)]
        crossed_asks = [(95.0, 400.0), (96.0, 200.0)]
        res = self.engine_sp500.forecast_price_discovery(crossed_bids, crossed_asks, mid_price=100.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertTrue(np.all(res.forecasted_density >= 0.0))

    def test_adv04_infinite_and_astronomical_spread(self) -> None:
        """ADV-04: Astronomical spread (bid at 0.01, ask at 1,000,000.0)."""
        wide_bids = [(0.01, 1000.0)]
        wide_asks = [(1_000_000.0, 1000.0)]
        res = self.engine_sp500.forecast_price_discovery(wide_bids, wide_asks, mid_price=500_000.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertEqual(res.regime_fluid_state, FluidRegime.LIQUIDITY_VOID.value)

    def test_adv05_subpenny_nanoscopic_spread(self) -> None:
        """ADV-05: Sub-penny nanoscopic spread (0.00000001 tick difference)."""
        tiny_bids = [(100.00000000, 1000.0)]
        tiny_asks = [(100.00000001, 1000.0)]
        res = self.engine_sp500.forecast_price_discovery(tiny_bids, tiny_asks, mid_price=100.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    def test_adv06_single_sided_deep_out_of_bounds_quotes(self) -> None:
        """ADV-06: Quotes positioned 500 ticks away from grid boundary."""
        far_bids = [(50.0, 10000.0)]   # 5000 ticks away when tick_size=0.01
        far_asks = [(150.0, 10000.0)]  # 5000 ticks away
        res = self.engine_sp500.forecast_price_discovery(far_bids, far_asks, mid_price=100.0)
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertTrue(np.all(res.forecasted_density >= 0.0))

    def test_adv07_unaggregated_duplicate_price_levels(self) -> None:
        """ADV-07: Unaggregated raw L3 stream with 100 duplicate prices at the same tick."""
        dup_bids = [(99.99, 10.0) for _ in range(100)]
        dup_asks = [(100.01, 15.0) for _ in range(100)]
        res = self.engine_sp500.forecast_price_discovery(dup_bids, dup_asks, mid_price=100.0)
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertAlmostEqual(res.initial_state.total_volume, 2500.0, places=4)

    def test_adv08_zero_and_negative_volume_filtering(self) -> None:
        """ADV-08: Books with only zero, negative, or NaN volume entries."""
        zero_bids = [(99.99, 0.0), (99.98, -50.0), (99.97, float("nan"))]
        zero_asks = [(100.01, 0.0), (100.02, -100.0), (100.03, float("inf"))]
        res = self.engine_sp500.forecast_price_discovery(zero_bids, zero_asks, mid_price=100.0)
        # Should gracefully treat as empty book with virtual baseline volume 100.0
        self.assertGreater(res.initial_state.total_volume, 0.0)
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    # =========================================================================
    # 2. FLASH CRASH SHOCKWAVES & LIQUIDITY VOIDS
    # =========================================================================

    def test_adv09_flash_crash_bid_wipeout(self) -> None:
        """ADV-09: Flash crash sudden wipeout: 1 share on bids, 50,000,000 on asks."""
        # Case A: Tight touch (spread=2 ticks) with extreme volume asymmetry -> SHOCKWAVE_BURST
        crash_bids_tight = [(99.99, 1.0)]
        crash_asks_tight = [(100.01, 5e7), (100.02, 5e7)]
        res_tight = self.engine_sp500.forecast_price_discovery(crash_bids_tight, crash_asks_tight, mid_price=100.0)
        self.assertLess(res_tight.fluid_drift_composite_bps, 0.0)
        self.assertEqual(res_tight.regime_fluid_state, FluidRegime.SHOCKWAVE_BURST.value)
        self.assertLessEqual(res_tight.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

        # Case B: Wide touch (spread=101 ticks) with queue wipeout -> LIQUIDITY_VOID
        crash_bids_wide = [(99.00, 1.0)]
        crash_asks_wide = [(100.01, 5e7)]
        res_wide = self.engine_sp500.forecast_price_discovery(crash_bids_wide, crash_asks_wide, mid_price=100.0)
        self.assertEqual(res_wide.regime_fluid_state, FluidRegime.LIQUIDITY_VOID.value)
        self.assertLessEqual(res_wide.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    def test_adv10_short_squeeze_ask_wipeout(self) -> None:
        """ADV-10: Short squeeze ask wipeout: 100,000,000 shares on bids, 1 share on asks."""
        # Case A: Tight touch (spread=2 ticks) with extreme buy pressure -> SHOCKWAVE_BURST
        squeeze_bids_tight = [(99.99, 5e7), (99.98, 5e7)]
        squeeze_asks_tight = [(100.01, 1.0)]
        res_tight = self.engine_sp500.forecast_price_discovery(squeeze_bids_tight, squeeze_asks_tight, mid_price=100.0)
        self.assertGreater(res_tight.fluid_drift_composite_bps, 0.0)
        self.assertEqual(res_tight.regime_fluid_state, FluidRegime.SHOCKWAVE_BURST.value)
        self.assertLessEqual(res_tight.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

        # Case B: Wide touch (spread=101 ticks) with ask vacuum -> LIQUIDITY_VOID
        squeeze_bids_wide = [(99.99, 5e7)]
        squeeze_asks_wide = [(101.00, 1.0)]
        res_wide = self.engine_sp500.forecast_price_discovery(squeeze_bids_wide, squeeze_asks_wide, mid_price=100.0)
        self.assertEqual(res_wide.regime_fluid_state, FluidRegime.LIQUIDITY_VOID.value)
        self.assertLessEqual(res_wide.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    def test_adv11_center_hole_liquidity_vacuum(self) -> None:
        """ADV-11: Order book center liquidity vacuum (empty queues +/- 15 ticks)."""
        vacuum_bids = [(99.50, 1000.0), (99.40, 2000.0)]
        vacuum_asks = [(100.50, 1000.0), (100.60, 2000.0)]
        res = self.engine_sp500.forecast_price_discovery(vacuum_bids, vacuum_asks, mid_price=100.0)
        self.assertEqual(res.regime_fluid_state, FluidRegime.LIQUIDITY_VOID.value)
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    def test_adv12_multi_step_shockwave_cascade(self) -> None:
        """ADV-12: Multi-step consecutive shockwave cascade (50 sequential steps)."""
        bids = [(99.99, 1000.0), (99.98, 2000.0)]
        asks = [(100.01, 1000.0), (100.02, 2000.0)]
        p_mid = 100.0

        for step in range(50):
            # Dynamic shock perturbations
            if step % 5 == 0:
                # Add flash buy or sell spike
                step_bids = [(p_mid - 0.01, 50000.0)]
                step_asks = [(p_mid + 0.01, 500.0)]
            else:
                step_bids = bids
                step_asks = asks

            res = self.engine_sp500.forecast_price_discovery(step_bids, step_asks, mid_price=p_mid)
            self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
            self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))

    # =========================================================================
    # 3. HIGH-FREQUENCY OSCILLATIONS, NYQUIST WAVES & GIBBS RINGING
    # =========================================================================

    def test_adv13_dirac_comb_alternating_spikes(self) -> None:
        """ADV-13: Dirac comb high-frequency alternating spikes across consecutive ticks."""
        comb_bids = []
        comb_asks = []
        p_mid = 100.0
        tick = 0.01

        # Place spikes every 2 ticks
        for i in range(1, 20):
            if i % 2 == 1:
                comb_bids.append((p_mid - i * tick, 10000.0))
                comb_asks.append((p_mid + i * tick, 10000.0))
            else:
                comb_bids.append((p_mid - i * tick, 1.0))
                comb_asks.append((p_mid + i * tick, 1.0))

        res = self.engine_sp500.forecast_price_discovery(comb_bids, comb_asks, mid_price=p_mid)
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertTrue(np.all(np.isfinite(res.forecasted_density)))
        self.assertTrue(np.all(np.isfinite(res.forecasted_velocity)))

    def test_adv14_nyquist_frequency_spectral_derivatives(self) -> None:
        """ADV-14: Spectral derivative computation under exact Nyquist oscillation."""
        N = 64
        L_x = 64.0
        # Alternating +1, -1 signal (highest possible frequency k = N//2)
        u_nyquist = np.array([1.0 if i % 2 == 0 else -1.0 for i in range(N)], dtype=np.float64)
        du_dx, d2u_dx2 = compute_spectral_derivatives_1d(u_nyquist, L_x)

        self.assertEqual(len(du_dx), N)
        self.assertEqual(len(d2u_dx2), N)
        self.assertTrue(np.all(np.isfinite(du_dx)))
        self.assertTrue(np.all(np.isfinite(d2u_dx2)))

    def test_adv15_gibbs_ringing_boundary_decay_attenuation(self) -> None:
        """ADV-15: Gibbs ringing suppression at boundary endpoints |u(+-X)| < 1e-5."""
        # Create square-wave step function density (prime candidate for Gibbs ringing)
        square_bids = [(100.0 - i * 0.01, 10000.0 if i < 10 else 0.0) for i in range(1, 30)]
        square_asks = [(100.0 + i * 0.01, 10000.0 if i < 10 else 0.0) for i in range(1, 30)]

        res = self.engine_sp500.forecast_price_discovery(square_bids, square_asks, mid_price=100.0)
        # Even with square wave discontinuity, boundary velocities must vanish
        self.assertLess(abs(res.forecasted_velocity[0]), 1e-5)
        self.assertLess(abs(res.forecasted_velocity[-1]), 1e-5)
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    # =========================================================================
    # 4. EXTREME VOLUME SCALES & DYNAMIC RANGE
    # =========================================================================

    def test_adv16_nanoscopic_micro_volume_scale(self) -> None:
        """ADV-16: Extremely small volume (1e-12 shares, e.g. fractional crypto/micro-lots)."""
        tiny_bids = [(99.99, 1e-12), (99.98, 2e-12)]
        tiny_asks = [(100.01, 1e-12), (100.02, 2e-12)]
        res = self.engine_sp500.forecast_price_discovery(tiny_bids, tiny_asks, mid_price=100.0)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertTrue(np.all(res.forecasted_density >= 0.0))

    def test_adv17_astronomical_macro_volume_scale(self) -> None:
        """ADV-17: Massive volume scale (1e15 shares, national debt / forex-scale)."""
        huge_bids = [(99.99, 1e15), (99.98, 2e15)]
        huge_asks = [(100.01, 1e15), (100.02, 2e15)]
        res = self.engine_sp500.forecast_price_discovery(huge_bids, huge_asks, mid_price=100.0)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertTrue(np.all(res.forecasted_density >= 0.0))

    def test_adv18_extreme_volume_ratio_dynamic_range(self) -> None:
        """ADV-18: 18 orders of magnitude volume asymmetry: 1e12 vs 1e-6."""
        asym_bids = [(99.99, 1e12)]
        asym_asks = [(100.01, 1e-6)]
        res = self.engine_sp500.forecast_price_discovery(asym_bids, asym_asks, mid_price=100.0)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    # =========================================================================
    # 5. MULTI-GRID RESOLUTION SCALING & MODE TRUNCATION
    # =========================================================================

    def test_adv19_grid_resolutions_16_to_256(self) -> None:
        """ADV-19: Grid spatial resolution scaling across {16, 32, 64, 128, 256}."""
        bids = [(99.99, 1000.0), (99.98, 2000.0)]
        asks = [(100.01, 1000.0), (100.02, 2000.0)]

        for nx in [16, 32, 64, 128, 256]:
            engine = PINOFluidPriceDiscoveryEngine(market="SP500", spatial_resolution=nx, seed=42)
            self.assertEqual(len(engine.grid_x), nx)
            res = engine.forecast_price_discovery(bids, asks, mid_price=100.0)
            self.assertEqual(len(res.forecasted_density), nx)
            self.assertEqual(len(res.forecasted_velocity), nx)
            self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    def test_adv20_temporal_resolutions_8_to_32(self) -> None:
        """ADV-20: 2D Space-Time FNO convolution across temporal resolutions {8, 16, 32}."""
        for nt in [8, 16, 32]:
            conv2d = SpectralConv2dNumPy(in_channels=2, out_channels=4, modes_x=8, modes_t=nt // 2, seed=42)
            x_in = np.random.randn(2, 64, nt).astype(np.float64)
            out = conv2d.forward(x_in)
            self.assertEqual(out.shape, (4, 64, nt))
            self.assertTrue(np.all(np.isfinite(out)))

    # =========================================================================
    # 6. MONTE CARLO MASS CONSERVATION INVARIANT SWEEP (1,000 RUNS)
    # =========================================================================

    def test_adv21_monte_carlo_1000_mass_conservation_stress_sweep(self) -> None:
        """ADV-21: 1,000 randomized adversarial order books asserting Delta V / V_total <= 1e-4."""
        rng = np.random.RandomState(42)
        max_mass_error = 0.0

        for trial in range(1000):
            # Generate random number of bids and asks
            n_b = rng.randint(0, 30)
            n_a = rng.randint(0, 30)

            p_mid = 100.0 + rng.uniform(-10.0, 10.0)
            tick = rng.choice([0.01, 0.05, 0.1, 1.0, 50.0])

            bids = []
            for _ in range(n_b):
                p = p_mid - rng.uniform(0.1, 30.0) * tick
                v = 10.0 ** rng.uniform(-3.0, 7.0)  # Volume from 0.001 to 10M
                bids.append((p, v))

            asks = []
            for _ in range(n_a):
                p = p_mid + rng.uniform(0.1, 30.0) * tick
                v = 10.0 ** rng.uniform(-3.0, 7.0)
                asks.append((p, v))

            res = self.engine_sp500.forecast_price_discovery(bids, asks, mid_price=p_mid)
            err = res.mass_conservation_error
            max_mass_error = max(max_mass_error, err)

            self.assertLessEqual(
                err,
                MASS_CONSERVATION_TOLERANCE,
                f"Trial {trial} violated mass conservation: rel_err={err:.2e} > 1e-4",
            )
            # Invariant: Density positivity
            self.assertTrue(
                np.all(res.forecasted_density >= 0.0),
                f"Trial {trial} produced negative volume density!",
            )
            # Invariant: Boundary velocity decay
            self.assertLess(
                abs(res.forecasted_velocity[0]),
                1e-5,
                f"Trial {trial} boundary velocity failed left: u(-X)={res.forecasted_velocity[0]}",
            )
            self.assertLess(
                abs(res.forecasted_velocity[-1]),
                1e-5,
                f"Trial {trial} boundary velocity failed right: u(+X)={res.forecasted_velocity[-1]}",
            )

        print(f"\n[ADV-21] Monte Carlo 1,000 Stress Trials Peak Mass Conservation Error: {max_mass_error:.2e}")

    # =========================================================================
    # 7. 5-MARKET CALIBRATED PROFILES ADVERSARIAL STRESS
    # =========================================================================

    def test_adv22_five_market_profile_stress(self) -> None:
        """ADV-22: 5-market stress testing under asymmetrical liquidity shocks."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        shock_bids = [(99.0, 1e6)]
        shock_asks = [(101.0, 10.0)]

        for mkt in markets:
            engine = PINOFluidPriceDiscoveryEngine(market=mkt, seed=42)
            res = engine.forecast_price_discovery(shock_bids, shock_asks, mid_price=100.0)
            self.assertEqual(res.market, mkt)
            self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
            self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
            # Verify market-specific parameters loaded correctly
            self.assertEqual(engine.config.kinematic_viscosity, MARKET_PINO_FLUID_PROFILES[mkt]["kinematic_viscosity"])

    # =========================================================================
    # 8. DUAL-BACKEND (TORCH vs NUMPY) EQUIVALENCE UNDER EXTREME STRESS
    # =========================================================================

    def test_adv23_dual_backend_equivalence_under_stress(self) -> None:
        """ADV-23: Deterministic parity between PyTorch and pure NumPy under extreme shockwave."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not installed.")

        engine_torch = PINOFluidPriceDiscoveryEngine(market="NASDAQ", use_torch=True, seed=42)
        engine_np = PINOFluidPriceDiscoveryEngine(market="NASDAQ", use_torch=False, seed=42)

        stress_bids = [(99.95, 50000.0), (99.90, 80000.0)]
        stress_asks = [(100.05, 100.0), (100.10, 50.0)]
        p_mid = 100.0

        res_torch = engine_torch.forecast_price_discovery(stress_bids, stress_asks, mid_price=p_mid)
        res_np = engine_np.forecast_price_discovery(stress_bids, stress_asks, mid_price=p_mid)

        # Both must conserve mass
        self.assertLessEqual(res_torch.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)
        self.assertLessEqual(res_np.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

        # Parity in directional drift and density
        self.assertAlmostEqual(res_torch.fluid_drift_composite_bps, res_np.fluid_drift_composite_bps, places=2)
        np.testing.assert_allclose(res_torch.forecasted_density, res_np.forecasted_density, rtol=1e-3, atol=1e-3)
        np.testing.assert_allclose(res_torch.forecasted_velocity, res_np.forecasted_velocity, rtol=1e-3, atol=1e-3)


if __name__ == "__main__":
    unittest.main()
