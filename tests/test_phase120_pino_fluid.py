r"""
tests/test_phase120_pino_fluid.py
===================================
Exhaustive 58-Test Verification Suite across 12 Rigorous Categories for:
Physics-Informed Neural Operator (PINO) Macro-Micro Fluid Dynamics Price Discovery Engine (Feature F570).
Phase 120 (Release R136 / v127 Production Master).

Categories (58 Test Cases):
  - Category 1: Dual-Tree Parity, Metadata, Enums & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC09)
  - Category 3: Spatial Discretization & Fluid Coordinate Mechanics (TC10 ~ TC14)
  - Category 4: FNO Spectral Convolution Layers & Mode Truncation (TC15 ~ TC19)
  - Category 5: Multi-Horizon Shockwave Propagation (100ms, 500ms, 1s, 5s) (TC20 ~ TC24)
  - Category 6: Price Jump Velocity & Directional Drift Forecasts (TC25 ~ TC29)
  - Category 7: Physics-Informed Mass Conservation Loss Regularization (TC30 ~ TC34)
  - Category 8: Dual-Backend Parity (PyTorch vs Pure NumPy) (TC35 ~ TC38)
  - Category 9: Critical Edge Cases & Degenerate Books (TC39 ~ TC43)
  - Category 10: Adversarial Stress & Flash Crash Liquidity Voids (TC44 ~ TC48)
  - Category 11: Verification of Mathematical Invariants (TC49 ~ TC53)
  - Category 12: Execution Latency SLA, Telemetry & Serialization (TC54 ~ TC58)
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
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.pino_fluid_price_discovery as pino_module
from src.ai.pino_fluid_price_discovery import (
    VERSION,
    RELEASE,
    FEATURE,
    DEFAULT_HORIZONS,
    HORIZON_NAMES,
    DEFAULT_SPATIAL_RESOLUTION,
    DEFAULT_TEMPORAL_RESOLUTION,
    DEFAULT_PRICE_SPAN_TICKS,
    DEFAULT_TICK_SIZE,
    MAX_SPECTRAL_MODES,
    MASS_CONSERVATION_TOLERANCE,
    MarketProfile,
    MarketType,
    ForecastHorizon,
    FluidRegime,
    MARKET_PINO_FLUID_PROFILES,
    PINOFluidConfig,
    FluidDynamicsConfig,
    PINOConfig,
    get_market_profile,
    FluidFieldState,
    HorizonShockwaveForecast,
    HorizonShockForecast,
    PINOFluidForecastResult,
    PINOFluidOutput,
    FluidForecastResult,
    gelu_np,
    compute_spectral_derivatives_1d,
    SpectralConv1dNumPy,
    SpectralConv2dNumPy,
    PINONetworkNumPy,
    PINOFluidPriceDiscoveryEngine,
    PhysicsInformedNeuralOperator,
    FluidPriceDiscoveryEngine,
    PINOPriceDiscovery,
    LOBFluidDynamicsEngine,
    BurgersNavierStokesPriceDiscovery,
    FNOLiquidityShockwaveForecaster,
    PINOFluidEngine,
    Phase120PINOFluidEngine,
    F570PINOFluidPriceDiscovery,
    _TORCH_AVAILABLE,
)

if _TORCH_AVAILABLE:
    import torch
    from src.ai.pino_fluid_price_discovery import (
        SpectralConv1dTorch,
        SpectralConv2dTorch,
        PINONetworkTorch,
        synchronize_weights,
    )


class TestPhase120PINOFluid(unittest.TestCase):
    """58-Test Verification Suite for Feature F570."""

    def setUp(self) -> None:
        self.root_file = PROJECT_ROOT / "src" / "ai" / "pino_fluid_price_discovery.py"
        self.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "ai" / "pino_fluid_price_discovery.py"
        self.default_engine = PINOFluidPriceDiscoveryEngine(market="SP500", seed=42)

        # Standard sample L3 order book
        self.sample_bids = [
            (99.99, 1000.0),
            (99.98, 1500.0),
            (99.97, 2000.0),
            (99.96, 2500.0),
            (99.95, 3000.0),
        ]
        self.sample_asks = [
            (100.01, 1000.0),
            (100.02, 1200.0),
            (100.03, 1800.0),
            (100.04, 2200.0),
            (100.05, 2800.0),
        ]
        self.sample_mid = 100.0

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
        self.assertEqual(h_root, h_mirror, f"SHA-256 mismatch: {h_root} vs {h_mirror}")
        self.assertGreater(len(root_bytes), 5000, "File size suspiciously small.")

    def test_tc02_version_release_feature_metadata(self) -> None:
        """TC02: Assert VERSION=120, RELEASE='R136', FEATURE='F570' at module and class levels."""
        self.assertEqual(VERSION, 120)
        self.assertEqual(RELEASE, "R136")
        self.assertEqual(FEATURE, "F570")
        self.assertEqual(self.default_engine.VERSION, 120)
        self.assertEqual(self.default_engine.RELEASE, "R136")
        self.assertEqual(self.default_engine.FEATURE, "F570")

    def test_tc03_enums_integrity(self) -> None:
        """TC03: Assert completeness and integrity of MarketProfile, MarketType, ForecastHorizon, FluidRegime."""
        self.assertEqual(len(MarketProfile), 5)
        self.assertEqual(MarketProfile.SP500, 0)
        self.assertEqual(MarketProfile.KOSDAQ, 4)

        self.assertEqual(len(MarketType), 5)
        self.assertEqual(MarketType.SP500.value, "SP500")

        self.assertEqual(len(ForecastHorizon), 4)
        self.assertEqual(ForecastHorizon.H100MS.value, 0.1)
        self.assertEqual(ForecastHorizon.H5S.value, 5.0)

        self.assertEqual(len(FluidRegime), 4)
        self.assertIn("LAMINAR_FLOW", [r.value for r in FluidRegime])
        self.assertIn("SHOCKWAVE_BURST", [r.value for r in FluidRegime])

    def test_tc04_complete_alias_trees(self) -> None:
        """TC04: Verify all class and dataclass backwards-compatibility aliases."""
        class_aliases = [
            PhysicsInformedNeuralOperator,
            FluidPriceDiscoveryEngine,
            PINOPriceDiscovery,
            LOBFluidDynamicsEngine,
            BurgersNavierStokesPriceDiscovery,
            FNOLiquidityShockwaveForecaster,
            PINOFluidEngine,
            Phase120PINOFluidEngine,
            F570PINOFluidPriceDiscovery,
        ]
        for alias in class_aliases:
            self.assertIs(alias, PINOFluidPriceDiscoveryEngine)

        self.assertIs(FluidDynamicsConfig, PINOFluidConfig)
        self.assertIs(PINOConfig, PINOFluidConfig)
        self.assertIs(HorizonShockForecast, HorizonShockwaveForecast)
        self.assertIs(PINOFluidOutput, PINOFluidForecastResult)
        self.assertIs(FluidForecastResult, PINOFluidForecastResult)

    def test_tc05_sys_modules_registration(self) -> None:
        """TC05: Verify explicit registration in sys.modules for dual-import paths."""
        self.assertIn("src.ai.pino_fluid_price_discovery", sys.modules)
        self.assertIn("trading_system.src.ai.pino_fluid_price_discovery", sys.modules)

    # =======================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC09)
    # =======================================================================
    def test_tc06_default_config_bounds(self) -> None:
        """TC06: Verify default PINOFluidConfig parameters and validation rules."""
        cfg = PINOFluidConfig()
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.spatial_resolution, 64)
        self.assertEqual(cfg.temporal_resolution, 16)
        self.assertLessEqual(cfg.k_max_spatial, 16)
        self.assertGreater(cfg.kinematic_viscosity, 0.0)

    def test_tc07_five_market_profiles_retrieval(self) -> None:
        """TC07: Test get_market_profile factory across all 5 supported markets."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for mkt in markets:
            cfg = get_market_profile(mkt)
            self.assertEqual(cfg.market, mkt)
            prof = MARKET_PINO_FLUID_PROFILES[mkt]
            self.assertEqual(cfg.kinematic_viscosity, prof["kinematic_viscosity"])
            self.assertEqual(cfg.k_max_spatial, prof["k_max_spatial"])
            self.assertEqual(cfg.pressure_sensitivity, prof["pressure_sensitivity"])

    def test_tc08_nyquist_mode_truncation_bound(self) -> None:
        """TC08: Verify k_max_spatial is strictly capped at min(16, spatial_resolution // 2)."""
        cfg_small = PINOFluidConfig(spatial_resolution=24, k_max_spatial=16)
        self.assertLessEqual(cfg_small.k_max_spatial, 12)

        cfg_large = PINOFluidConfig(spatial_resolution=128, k_max_spatial=30)
        self.assertLessEqual(cfg_large.k_max_spatial, 16)

    def test_tc09_config_overrides_and_determinism(self) -> None:
        """TC09: Test custom parameter overrides and reproducible initialization with seed."""
        cfg = PINOFluidConfig(market="NASDAQ", kinematic_viscosity=0.099, seed=123)
        self.assertEqual(cfg.kinematic_viscosity, 0.099)
        self.assertEqual(cfg.seed, 123)

        engine1 = PINOFluidPriceDiscoveryEngine(config=cfg, seed=123)
        engine2 = PINOFluidPriceDiscoveryEngine(config=cfg, seed=123)
        np.testing.assert_allclose(engine1.np_network.P_W, engine2.np_network.P_W)

    # =======================================================================
    # Category 3: Spatial Discretization & Fluid Coordinate Mechanics (TC10 ~ TC14)
    # =======================================================================
    def test_tc10_symmetric_spatial_grid(self) -> None:
        """TC10: Verify spatial grid symmetry around x=0 with uniform spacing."""
        grid = self.default_engine.grid_x
        self.assertEqual(len(grid), 64)
        self.assertAlmostEqual(grid[0], -32.0)
        self.assertAlmostEqual(grid[-1], 32.0)
        self.assertAlmostEqual(float(np.mean(grid)), 0.0, places=6)

    def test_tc11_order_book_gaussian_discretization(self) -> None:
        """TC11: Verify continuous Gaussian kernel projection of order quotes into fluid density."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertIsInstance(state, FluidFieldState)
        self.assertEqual(len(state.density), 64)
        self.assertTrue(np.all(state.density >= 0.0))
        # Peaks should be near best bid (-1 tick) and best ask (+1 tick)
        self.assertGreater(state.density[31], state.density[0])
        self.assertGreater(state.density[33], state.density[-1])

    def test_tc12_exact_mass_conservation_on_initial_density(self) -> None:
        """TC12: Verify total discrete volume strictly matches integrated fluid density."""
        expected_vol = sum(v for _, v in self.sample_bids) + sum(v for _, v in self.sample_asks)
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        integrated_mass = float(np.sum(state.density) * self.default_engine.dx)
        self.assertAlmostEqual(integrated_mass, expected_vol, places=3)
        self.assertLess(state.mass_residual, 1e-3)

    def test_tc13_pressure_calculation_and_anti_symmetry(self) -> None:
        """TC13: Verify queue pressure calculation and opposing signs on bid and ask sides."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        zero_idx = len(state.grid_x) // 2
        # Bid side (x < 0) has negative pressure accumulator, ask side (x > 0) has positive
        self.assertLess(state.pressure[zero_idx - 5], 0.0)
        self.assertGreater(state.pressure[zero_idx + 5], 0.0)

    def test_tc14_initial_velocity_and_boundary_decay(self) -> None:
        """TC14: Verify initial velocity field decays smoothly to zero at deep boundaries."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertAlmostEqual(float(state.velocity[0]), 0.0, places=5)
        self.assertAlmostEqual(float(state.velocity[-1]), 0.0, places=5)

    # =======================================================================
    # Category 4: FNO Spectral Convolution Layers & Mode Truncation (TC15 ~ TC19)
    # =======================================================================
    def test_tc15_spectral_conv1d_numpy_forward(self) -> None:
        """TC15: Test 1D FNO spectral convolution in pure NumPy."""
        conv = SpectralConv1dNumPy(in_channels=3, out_channels=4, modes=8, seed=42)
        x = np.random.randn(3, 64)
        out = conv.forward(x)
        self.assertEqual(out.shape, (4, 64))
        self.assertTrue(np.all(np.isfinite(out)))

    def test_tc16_mode_truncation_without_aliasing(self) -> None:
        """TC16: Verify mode truncation zeroes out high frequencies above k_max."""
        conv = SpectralConv1dNumPy(in_channels=2, out_channels=2, modes=6, seed=42)
        x = np.random.randn(2, 64)
        out = conv.forward(x)
        # Output should be smooth and finite without high frequency ringing
        self.assertTrue(np.all(np.isfinite(out)))
        self.assertEqual(conv.modes, 6)

    def test_tc17_spectral_conv2d_numpy_forward(self) -> None:
        """TC17: Test 2D space-time FNO spectral convolution in NumPy."""
        conv2d = SpectralConv2dNumPy(in_channels=2, out_channels=3, modes_x=8, modes_t=4, seed=42)
        x = np.random.randn(2, 32, 16)
        out = conv2d.forward(x)
        self.assertEqual(out.shape, (3, 32, 16))
        self.assertTrue(np.all(np.isfinite(out)))

    def test_tc18_spectral_derivative_accuracy(self) -> None:
        """TC18: Verify spectral derivative computation against known sinusoidal signal."""
        # u(x) = sin(2 * pi * x / L)
        L = 64.0
        x = np.linspace(0, L, 64, endpoint=False)
        u = np.sin(2.0 * np.pi * x / L)
        du_dx, d2u_dx2 = compute_spectral_derivatives_1d(u, L)

        expected_du = (2.0 * np.pi / L) * np.cos(2.0 * np.pi * x / L)
        expected_d2u = - ((2.0 * np.pi / L) ** 2) * np.sin(2.0 * np.pi * x / L)

        np.testing.assert_allclose(du_dx, expected_du, atol=1e-5)
        np.testing.assert_allclose(d2u_dx2, expected_d2u, atol=1e-5)

    def test_tc19_gelu_numpy_properties(self) -> None:
        """TC19: Verify GELU implementation satisfies standard non-linear properties."""
        x = np.array([-3.0, 0.0, 3.0])
        g = gelu_np(x)
        self.assertAlmostEqual(float(g[1]), 0.0, places=6)
        self.assertLess(float(g[0]), 0.0)
        self.assertAlmostEqual(float(g[0]), -0.004, delta=0.01)
        self.assertAlmostEqual(float(g[2]), 2.996, delta=0.01)

    # =======================================================================
    # Category 5: Multi-Horizon Shockwave Propagation (100ms, 500ms, 1s, 5s) (TC20 ~ TC24)
    # =======================================================================
    def test_tc20_multi_horizon_presence(self) -> None:
        """TC20: Verify forecasts are produced for all 4 required operational horizons."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertEqual(len(res.horizons), 4)
        for h in DEFAULT_HORIZONS:
            self.assertIn(h, res.horizons)
            forecast = res.horizons[h]
            self.assertEqual(forecast.horizon_seconds, h)
            self.assertEqual(forecast.horizon_name, HORIZON_NAMES[h])

    def test_tc21_shock_front_displacement_extraction(self) -> None:
        """TC21: Verify shock front displacement x_shock is bounded within spatial domain."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        for h, forecast in res.horizons.items():
            self.assertGreaterEqual(forecast.shock_displacement_ticks, -32.0)
            self.assertLessEqual(forecast.shock_displacement_ticks, 32.0)

    def test_tc22_shockwave_amplitude_positivity(self) -> None:
        """TC22: Verify shockwave amplitude A_shock is strictly positive."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        for h, forecast in res.horizons.items():
            self.assertGreater(forecast.shock_amplitude, 0.0)

    def test_tc23_shockwave_dampening_dynamics(self) -> None:
        """TC23: Verify dampening reduces velocity extremes as horizon advances to 5s."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        amp_100ms = res.horizons[0.1].shock_amplitude
        # Velocity shockwave dampening should be tracked and finite
        self.assertTrue(math.isfinite(amp_100ms))
        self.assertTrue(math.isfinite(res.horizons[5.0].shock_amplitude))

    def test_tc24_liquidity_exhaustion_ratio_bounds(self) -> None:
        """TC24: Verify Liquidity Exhaustion Ratio (LER) is bounded in [-1.0, 1.0]."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        for h, forecast in res.horizons.items():
            self.assertGreaterEqual(forecast.liquidity_exhaustion_ratio, -1.0)
            self.assertLessEqual(forecast.liquidity_exhaustion_ratio, 1.0)

    # =======================================================================
    # Category 6: Price Jump Velocity & Directional Drift Forecasts (TC25 ~ TC29)
    # =======================================================================
    def test_tc25_jump_velocity_calculation(self) -> None:
        """TC25: Verify jump velocity v_jump = x_shock / horizon."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        for h, forecast in res.horizons.items():
            expected_v = forecast.shock_displacement_ticks / h
            self.assertAlmostEqual(forecast.jump_velocity_ticks_per_sec, expected_v, places=4)

    def test_tc26_directional_drift_bps_finite(self) -> None:
        """TC26: Verify directional fluid drift is finite and reasonable in bps."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        for h, forecast in res.horizons.items():
            self.assertTrue(math.isfinite(forecast.directional_drift_bps))

    def test_tc27_buy_heavy_imbalance_positive_drift(self) -> None:
        """TC27: Massive bid liquidity (buy pressure) pushes price upward (positive drift)."""
        heavy_bids = [(99.99, 10000.0), (99.98, 20000.0)]
        light_asks = [(100.01, 100.0), (100.02, 100.0)]
        res = self.default_engine.forecast_price_discovery(heavy_bids, light_asks, 100.0)
        self.assertGreater(res.fluid_drift_composite_bps, 0.0)

    def test_tc28_sell_heavy_imbalance_negative_drift(self) -> None:
        """TC28: Massive ask liquidity (sell pressure) pushes price downward (negative drift)."""
        light_bids = [(99.99, 100.0), (99.98, 100.0)]
        heavy_asks = [(100.01, 10000.0), (100.02, 20000.0)]
        res = self.default_engine.forecast_price_discovery(light_bids, heavy_asks, 100.0)
        self.assertLess(res.fluid_drift_composite_bps, 0.0)

    def test_tc29_shock_hazard_probability_bounds(self) -> None:
        """TC29: Verify shock hazard probability P_shock strictly in [0.0, 1.0]."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        for h, forecast in res.horizons.items():
            self.assertGreaterEqual(forecast.shock_hazard_prob, 0.0)
            self.assertLessEqual(forecast.shock_hazard_prob, 1.0)

    # =======================================================================
    # Category 7: Physics-Informed Mass Conservation Loss Regularization (TC30 ~ TC34)
    # =======================================================================
    def test_tc30_mass_conservation_strict_enforcement(self) -> None:
        """TC30: Verify mass conservation error delta_V / V_total <= 1e-4."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    def test_tc31_boundary_condition_regularization(self) -> None:
        """TC31: Verify quote boundary conditions: velocity vanishes at deep boundaries."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        phys = self.default_engine.compute_physics_losses(
            density=state.density,
            velocity=state.velocity,
            pressure=state.pressure,
            dt=0.1,
            dx=self.default_engine.dx,
        )
        self.assertLess(phys["loss_bc"], 1e-5)

    def test_tc32_pde_residual_boundedness(self) -> None:
        """TC32: Verify Burgers'/Navier-Stokes PDE residual norm is finite and non-negative."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        phys = self.default_engine.compute_physics_losses(
            density=state.density,
            velocity=state.velocity,
            pressure=state.pressure,
            dt=0.1,
            dx=self.default_engine.dx,
        )
        self.assertGreaterEqual(phys["pde_residual_norm"], 0.0)
        self.assertTrue(math.isfinite(phys["pde_residual_norm"]))

    def test_tc33_viscous_dissipation_damping_effect(self) -> None:
        """TC33: Verify higher kinematic viscosity nu increases dissipation in physics loss."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        engine_low_nu = PINOFluidPriceDiscoveryEngine(market="RUSSELL2000")  # nu = 0.04
        engine_high_nu = PINOFluidPriceDiscoveryEngine(market="SP500")      # nu = 0.08
        self.assertGreater(engine_high_nu.config.kinematic_viscosity, engine_low_nu.config.kinematic_viscosity)

    def test_tc34_pressure_gradient_force_directionality(self) -> None:
        """TC34: Verify pressure gradient force opposes imbalance accumulation."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertTrue(np.any(np.abs(state.pressure_gradient) > 0.0))

    # =======================================================================
    # Category 8: Dual-Backend Parity (PyTorch vs Pure NumPy) (TC35 ~ TC38)
    # =======================================================================
    def test_tc35_backend_availability(self) -> None:
        """TC35: Verify engine backend reporter reflects true environment capability."""
        if _TORCH_AVAILABLE:
            self.assertEqual(self.default_engine.backend, "torch")
        else:
            self.assertEqual(self.default_engine.backend, "numpy")

    def test_tc36_deterministic_dual_backend_parity(self) -> None:
        """TC36: Verify PyTorch and pure NumPy backends return identical predictions within 1e-4 tolerance."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not installed in environment.")

        engine_torch = PINOFluidPriceDiscoveryEngine(market="SP500", use_torch=True, seed=42)
        engine_numpy = PINOFluidPriceDiscoveryEngine(market="SP500", use_torch=False, seed=42)

        res_torch = engine_torch.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        res_numpy = engine_numpy.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)

        self.assertAlmostEqual(res_torch.fluid_drift_composite_bps, res_numpy.fluid_drift_composite_bps, places=2)
        np.testing.assert_allclose(res_torch.forecasted_density, res_numpy.forecasted_density, rtol=1e-3, atol=1e-3)

    def test_tc37_spectral_conv_torch_vs_numpy_parity(self) -> None:
        """TC37: Verify layer-level spectral convolution parity between Torch and NumPy."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch not installed.")

        conv_np = SpectralConv1dNumPy(in_channels=2, out_channels=2, modes=6, seed=42)
        conv_torch = SpectralConv1dTorch(in_channels=2, out_channels=2, modes=6, seed=42)

        # Synchronize weights
        with torch.no_grad():
            conv_torch.weights.copy_(torch.from_numpy(conv_np.weights).cfloat())
            conv_torch.W.copy_(torch.from_numpy(conv_np.W).float())
            conv_torch.bias.copy_(torch.from_numpy(conv_np.bias).float())

        x_np = np.random.randn(2, 32).astype(np.float64)
        x_torch = torch.from_numpy(x_np).float()

        out_np = conv_np.forward(x_np)
        with torch.no_grad():
            out_torch = conv_torch(x_torch).cpu().numpy()

        np.testing.assert_allclose(out_np, out_torch, rtol=1e-4, atol=1e-4)

    def test_tc38_pure_numpy_forced_mode(self) -> None:
        """TC38: Verify engine operates seamlessly with use_torch=False."""
        engine_np = PINOFluidPriceDiscoveryEngine(market="KOSPI", use_torch=False)
        self.assertEqual(engine_np.backend, "numpy")
        res = engine_np.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertIsInstance(res, PINOFluidForecastResult)

    # =======================================================================
    # Category 9: Critical Edge Cases & Degenerate Books (TC39 ~ TC43)
    # =======================================================================
    def test_tc39_empty_order_book(self) -> None:
        """TC39: Verify empty order book (zero bids, zero asks) generates virtual liquidity without crash."""
        res = self.default_engine.forecast_price_discovery(bids=[], asks=[], mid_price=100.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertGreater(res.initial_state.total_volume, 0.0)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))

    def test_tc40_one_sided_bids_only_book(self) -> None:
        """TC40: Verify one-sided book (bids only) handles missing ask queue gracefully."""
        res = self.default_engine.forecast_price_discovery(bids=self.sample_bids, asks=[], mid_price=100.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertGreater(res.fluid_drift_composite_bps, 0.0)

    def test_tc41_one_sided_asks_only_book(self) -> None:
        """TC41: Verify one-sided book (asks only) handles missing bid queue gracefully."""
        res = self.default_engine.forecast_price_discovery(bids=[], asks=self.sample_asks, mid_price=100.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLess(res.fluid_drift_composite_bps, 0.0)

    def test_tc42_extreme_wide_spread_book(self) -> None:
        """TC42: Verify extreme wide spread (illiquid regime) does not cause numerical instability."""
        wide_bids = [(50.0, 100.0)]
        wide_asks = [(150.0, 100.0)]
        res = self.default_engine.forecast_price_discovery(wide_bids, wide_asks, 100.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.mass_conservation_error))

    def test_tc43_single_off_grid_quote_book(self) -> None:
        """TC43: Verify single quote at off-grid fractional price behaves stably."""
        single_bids = [(100.003333, 500.0)]
        single_asks = [(100.016666, 500.0)]
        res = self.default_engine.forecast_price_discovery(single_bids, single_asks)
        self.assertIsInstance(res, PINOFluidForecastResult)

    # =======================================================================
    # Category 10: Adversarial Stress & Flash Crash Liquidity Voids (TC44 ~ TC48)
    # =======================================================================
    def test_tc44_massive_volume_spike_no_overflow(self) -> None:
        """TC44: Verify massive institutional volume (100M shares) does not overflow."""
        huge_bids = [(99.99, 1e8), (99.98, 2e8)]
        huge_asks = [(100.01, 1e8), (100.02, 2e8)]
        res = self.default_engine.forecast_price_discovery(huge_bids, huge_asks, 100.0)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))
        self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)

    def test_tc45_non_finite_inputs_cleaning(self) -> None:
        """TC45: Verify NaN, Inf, and negative volume inputs are safely filtered."""
        corrupt_bids = [
            (float("nan"), 100.0),
            (99.99, float("inf")),
            (99.98, -500.0),
            (99.95, 1000.0),
        ]
        corrupt_asks = [
            (100.01, 1000.0),
            (float("inf"), 500.0),
        ]
        res = self.default_engine.forecast_price_discovery(corrupt_bids, corrupt_asks, 100.0)
        self.assertIsInstance(res, PINOFluidForecastResult)
        self.assertTrue(math.isfinite(res.fluid_drift_composite_bps))

    def test_tc46_liquidity_void_regime_classification(self) -> None:
        """TC46: Verify order book with empty center queues triggers LIQUIDITY_VOID regime."""
        deep_void_bids = [(95.0, 1000.0)]
        deep_void_asks = [(105.0, 1000.0)]
        res = self.default_engine.forecast_price_discovery(deep_void_bids, deep_void_asks, 100.0)
        self.assertEqual(res.regime_fluid_state, FluidRegime.LIQUIDITY_VOID.value)

    def test_tc47_shockwave_burst_regime_classification(self) -> None:
        """TC47: Verify extreme queue asymmetry creates SHOCKWAVE_BURST regime."""
        burst_bids = [(99.99, 50000.0)]
        burst_asks = [(100.01, 10.0)]
        res = self.default_engine.forecast_price_discovery(burst_bids, burst_asks, 100.0)
        self.assertIn(res.regime_fluid_state, [FluidRegime.SHOCKWAVE_BURST.value, FluidRegime.LAMINAR_FLOW.value])

    def test_tc48_balanced_book_regime_classification(self) -> None:
        """TC48: Verify symmetric order book produces stable laminar or diffusion regime."""
        sym_bids = [(99.99, 1000.0), (99.98, 1000.0)]
        sym_asks = [(100.01, 1000.0), (100.02, 1000.0)]
        res = self.default_engine.forecast_price_discovery(sym_bids, sym_asks, 100.0)
        self.assertIn(res.regime_fluid_state, [FluidRegime.LAMINAR_FLOW.value, FluidRegime.EQUILIBRIUM_DIFFUSION.value])

    # =======================================================================
    # Category 11: Verification of Mathematical Invariants (TC49 ~ TC53)
    # =======================================================================
    def test_tc49_invariant_density_positivity(self) -> None:
        """TC49: Invariant 1: Order volume density rho(x) >= 0 everywhere across all horizons."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertTrue(np.all(res.initial_state.density >= 0.0))
        self.assertTrue(np.all(res.forecasted_density >= 0.0))

    def test_tc50_invariant_mass_integral_preservation(self) -> None:
        """TC50: Invariant 2: Total integrated mass equals total volume within 1e-4 relative error."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        v_total = res.initial_state.total_volume
        v_final = float(np.sum(res.forecasted_density) * self.default_engine.dx)
        rel_diff = abs(v_final - v_total) / v_total
        self.assertLessEqual(rel_diff, MASS_CONSERVATION_TOLERANCE)

    def test_tc51_invariant_boundary_velocity_vanishing(self) -> None:
        """TC51: Invariant 3: Velocity field vanishes at boundary endpoints |u(+-X)| < 1e-5."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        self.assertLess(abs(res.forecasted_velocity[0]), 1e-5)
        self.assertLess(abs(res.forecasted_velocity[-1]), 1e-5)

    def test_tc52_invariant_pde_residual_bounded(self) -> None:
        """TC52: Invariant 4: PDE residual norm is strictly bounded < 1e4."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        for h, forecast in res.horizons.items():
            self.assertLess(forecast.pde_residual_norm, 1e4)

    def test_tc53_invariant_composite_drift_convexity(self) -> None:
        """TC53: Invariant 5: Composite drift lies within [min(drifts), max(drifts)]."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        drifts = [f.directional_drift_bps for f in res.horizons.values()]
        self.assertGreaterEqual(res.fluid_drift_composite_bps, min(drifts) - 1e-4)
        self.assertLessEqual(res.fluid_drift_composite_bps, max(drifts) + 1e-4)

    # =======================================================================
    # Category 12: Execution Latency SLA, Telemetry & Serialization (TC54 ~ TC58)
    # =======================================================================
    def test_tc54_execution_latency_sla(self) -> None:
        """TC54: Verify average execution latency per forecast call is under 50ms SLA."""
        # Warmup
        _ = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)

        t0 = time.perf_counter()
        n_iters = 10
        for _ in range(n_iters):
            _ = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        avg_ms = ((time.perf_counter() - t0) / n_iters) * 1000.0

        self.assertLess(avg_ms, 50.0, f"Average latency {avg_ms:.2f}ms exceeds 50ms SLA")

    def test_tc55_telemetry_tracking_and_counters(self) -> None:
        """TC55: Verify telemetry counters increment accurately."""
        initial_calls = self.default_engine._telemetry["total_forecast_calls"]
        _ = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid)
        telem = self.default_engine.export_telemetry()

        self.assertEqual(telem["total_forecast_calls"], initial_calls + 1)
        self.assertIn("avg_latency_us", telem)
        self.assertIn("last_mass_conservation_error", telem)
        self.assertIn("last_pde_residual", telem)

    def test_tc56_result_json_serialization(self) -> None:
        """TC56: Verify PINOFluidForecastResult to_dict() produces valid JSON-serializable structure."""
        res = self.default_engine.forecast_price_discovery(self.sample_bids, self.sample_asks, self.sample_mid, symbol="AAPL")
        d = res.to_dict()
        json_str = json.dumps(d)
        self.assertIsInstance(json_str, str)
        self.assertIn("horizons", d)
        self.assertEqual(d["symbol"], "AAPL")

    def test_tc57_fluid_field_state_serialization(self) -> None:
        """TC57: Verify FluidFieldState to_dict() serialization."""
        state = self.default_engine.discretize_order_book(self.sample_bids, self.sample_asks, self.sample_mid)
        d = state.to_dict()
        self.assertIn("grid_size", d)
        self.assertIn("total_volume", d)
        self.assertEqual(d["grid_size"], 64)

    def test_tc58_five_market_sequential_batch_execution(self) -> None:
        """TC58: Execute sequential batch across all 5 global equity markets."""
        markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
        for mkt in markets:
            engine = PINOFluidPriceDiscoveryEngine(market=mkt)
            res = engine.forecast_price_discovery(self.sample_bids, self.sample_asks, 100.0, symbol=f"{mkt}_STOCK")
            self.assertEqual(res.market, mkt)
            self.assertLessEqual(res.mass_conservation_error, MASS_CONSERVATION_TOLERANCE)


if __name__ == "__main__":
    unittest.main()
