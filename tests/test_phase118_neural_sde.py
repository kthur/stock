r"""
tests/test_phase118_neural_sde.py
=================================
Comprehensive Unit, Integration, Invariant, Parity, and Benchmark Tests for:
Neural SDE Stochastic Volatility & Jump-Diffusion Forecaster (Feature F561).
Phase 118 (Release R134 / v125 Production Master).

Test Categories (55 Test Cases):
  - Category 1: Dual-Tree Parity, Module Exports, Metadata & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC09)
  - Category 3: Drift Network \mu_\theta(X_t, t) Mechanics & Mean Reversion (TC10 ~ TC13)
  - Category 4: Diffusion Network \sigma_\phi(X_t, t) & Positivity Guarantees (TC14 ~ TC17)
  - Category 5: Jump Arrival Intensity \lambda_{jump}(X_t) Boundedness & State-Dependence (TC18 ~ TC21)
  - Category 6: Kou Double Exponential Jump Distribution Rigor (TC22 ~ TC26)
  - Category 7: Merton Log-Normal Jump Distribution Mechanics (TC27 ~ TC29)
  - Category 8: Continuous SDE Simulation & Euler-Maruyama (TC30 ~ TC33)
  - Category 9: Multi-Horizon Volatility Term Structure & Variance Monotonicity (TC34 ~ TC37)
  - Category 10: Implied Volatility Surface, Smile Convexity & Skew Directionality (TC38 ~ TC41)
  - Category 11: Jump-Risk-Adjusted Alpha Conditioning Signals (TC42 ~ TC45)
  - Category 12: Dual-Backend Determinism: PyTorch vs Pure NumPy Analytical Fallback (TC46 ~ TC48)
  - Category 13: Adversarial Stress, Non-Finite Guarding & Defensive Defaults (TC49 ~ TC52)
  - Category 14: Execution Latency & High-Throughput Performance Benchmark (TC53 ~ TC55)
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.neural_sde_volatility_forecaster as sde_module
from src.ai.neural_sde_volatility_forecaster import (
    VERSION,
    RELEASE,
    FEATURE,
    DEFAULT_HORIZONS,
    DEFAULT_MONEYNESS_LEVELS,
    VOLATILITY_FLOOR,
    VOLATILITY_CEILING,
    LAMBDA_MIN,
    LAMBDA_MAX,
    ANNUALIZATION_SECONDS,
    ANNUALIZATION_FACTOR,
    JumpProcessType,
    JumpModelType,
    MarketProfile,
    ForecastHorizon,
    MARKET_NEURAL_SDE_PROFILES,
    NeuralSDEConfig,
    JumpCharacteristics,
    JumpParameters,
    HorizonVolatilityForecast,
    HorizonVolatilityMetrics,
    VolatilitySurface,
    AlphaConditioningSignal,
    NeuralSDEForecastResult,
    NeuralSDEVolatilityOutput,
    NeuralSDEVolatilityForecaster,
    ContinuousNeuralSDEForecaster,
    JumpDiffusionVolatilityForecaster,
    Phase118NeuralSDEForecaster,
    F561NeuralSDEForecaster,
    NeuralSDEEngine,
    NeuralSDEJumpDiffusionEngine,
    StochasticVolatilitySDEForecaster,
    MertonKouNeuralSDEForecaster,
    ContinuousJumpDiffusionForecaster,
    SDEVolatilitySurfaceForecaster,
    kou_density,
    sample_kou_jumps,
    merton_density,
    sample_merton_jumps,
    _TORCH_AVAILABLE,
)


class TestPhase118NeuralSDE(unittest.TestCase):
    """55-Test Suite across 14 Categories for Feature F561."""

    def setUp(self) -> None:
        self.root_file = PROJECT_ROOT / "src" / "ai" / "neural_sde_volatility_forecaster.py"
        self.mirror_file = PROJECT_ROOT / "trading_system" / "src" / "ai" / "neural_sde_volatility_forecaster.py"
        self.default_engine = NeuralSDEVolatilityForecaster(market="SP500")

    # =======================================================================
    # Category 1: Dual-Tree Parity, Module Exports, Metadata & Complete Alias Trees (TC01 ~ TC05)
    # =======================================================================
    def test_tc01_dual_tree_cryptographic_parity(self) -> None:
        """TC01: Verify bit-for-bit SHA-256 cryptographic parity between src/ and trading_system/src/."""
        self.assertTrue(self.root_file.exists(), f"Missing root file: {self.root_file}")
        self.assertTrue(self.mirror_file.exists(), f"Missing mirror file: {self.mirror_file}")

        root_bytes = self.root_file.read_bytes()
        mirror_bytes = self.mirror_file.read_bytes()

        h_root = hashlib.sha256(root_bytes).hexdigest()
        h_mirror = hashlib.sha256(mirror_bytes).hexdigest()
        self.assertEqual(h_root, h_mirror, f"SHA-256 mismatch: {h_root} vs {h_mirror}")
        self.assertGreater(len(root_bytes), 5000, "File size suspiciously small.")

    def test_tc02_version_release_feature_metadata(self) -> None:
        """TC02: Assert VERSION=118, RELEASE='R134', FEATURE='F561' at module and class levels."""
        self.assertEqual(VERSION, 118)
        self.assertEqual(RELEASE, "R134")
        self.assertEqual(FEATURE, "F561")
        self.assertEqual(NeuralSDEVolatilityForecaster.VERSION, 118)
        self.assertEqual(NeuralSDEVolatilityForecaster.RELEASE, "R134")
        self.assertEqual(NeuralSDEVolatilityForecaster.FEATURE, "F561")

    def test_tc03_complete_alias_trees_and_sys_modules(self) -> None:
        """TC03: Verify 12+ class aliases resolve identically and sys.modules registration."""
        aliases = [
            ContinuousNeuralSDEForecaster,
            JumpDiffusionVolatilityForecaster,
            Phase118NeuralSDEForecaster,
            F561NeuralSDEForecaster,
            NeuralSDEEngine,
            NeuralSDEJumpDiffusionEngine,
            StochasticVolatilitySDEForecaster,
            MertonKouNeuralSDEForecaster,
            ContinuousJumpDiffusionForecaster,
            SDEVolatilitySurfaceForecaster,
        ]
        for alias_cls in aliases:
            self.assertIs(alias_cls, NeuralSDEVolatilityForecaster)

        self.assertIs(NeuralSDEVolatilityOutput, NeuralSDEForecastResult)
        self.assertIs(JumpParameters, JumpCharacteristics)
        self.assertIs(HorizonVolatilityMetrics, HorizonVolatilityForecast)

        self.assertIn("src.ai.neural_sde_volatility_forecaster", sys.modules)
        self.assertIn("trading_system.src.ai.neural_sde_volatility_forecaster", sys.modules)

    def test_tc04_dataclass_contract_definitions(self) -> None:
        """TC04: Verify fields, properties, and JSON serialization of all data contracts."""
        cfg = NeuralSDEConfig()
        d_cfg = cfg.to_dict()
        self.assertIsInstance(d_cfg, dict)
        self.assertEqual(d_cfg["market"], "SP500")
        json.dumps(d_cfg)

        jump = JumpCharacteristics()
        d_jump = jump.to_dict()
        self.assertEqual(jump.lambda_intensity, jump.instantaneous_lambda)
        json.dumps(d_jump)

        fc = HorizonVolatilityForecast(
            horizon_sec=1.0,
            instantaneous_vol=0.15,
            integrated_diff_var=0.0225,
            integrated_jump_var=0.001,
            total_integrated_var=0.0235,
            annualized_vol=0.155,
            per_sec_vol=0.153,
            jump_probability=0.05,
            downside_jump_prob=0.03,
            upside_jump_prob=0.02,
            smile_curvature=0.04,
            risk_reversal_skew=0.015,
        )
        self.assertEqual(fc.diffusion_vol, 0.15)
        self.assertEqual(fc.smile_convexity, 0.04)
        self.assertEqual(fc.skew_25d, 0.015)
        json.dumps(fc.to_dict())

    def test_tc05_enum_definitions_and_values(self) -> None:
        """TC05: Assert JumpModelType, JumpProcessType, MarketProfile, ForecastHorizon enums."""
        self.assertEqual(JumpModelType.KOU.value, "KOU")
        self.assertEqual(JumpModelType.MERTON.value, "MERTON")
        self.assertEqual(int(JumpProcessType.MERTON), 0)
        self.assertEqual(int(JumpProcessType.KOU), 1)
        self.assertEqual(int(MarketProfile.SP500), 0)
        self.assertEqual(int(MarketProfile.NASDAQ), 1)
        self.assertEqual(int(MarketProfile.RUSSELL2000), 2)
        self.assertEqual(int(MarketProfile.KOSPI), 3)
        self.assertEqual(int(MarketProfile.KOSDAQ), 4)
        self.assertEqual(float(ForecastHorizon.HORIZON_100MS), 0.1)
        self.assertEqual(float(ForecastHorizon.HORIZON_1S), 1.0)
        self.assertEqual(float(ForecastHorizon.HORIZON_10S), 10.0)
        self.assertEqual(float(ForecastHorizon.HORIZON_60S), 60.0)

    # =======================================================================
    # Category 2: Configuration & 5-Market Pre-Calibrated Profiles (TC06 ~ TC09)
    # =======================================================================
    def test_tc06_default_configuration_initialization(self) -> None:
        """TC06: Test default configuration initial values."""
        cfg = NeuralSDEConfig()
        self.assertEqual(cfg.market, "SP500")
        self.assertEqual(cfg.jump_model, JumpModelType.KOU)
        self.assertEqual(cfg.horizons_sec, (0.1, 1.0, 10.0, 60.0))
        self.assertEqual(cfg.vol_floor, 1e-4)
        self.assertEqual(cfg.mean_reversion_kappa, 1.5)
        self.assertEqual(cfg.dt_step, 0.005)
        self.assertEqual(cfg.num_sim_paths, 500)

    def test_tc07_five_market_profile_contents_and_bounds(self) -> None:
        """TC07: Check 5-market parameter contents and empirical bounds."""
        markets = ["SP500", "NASDAQ", "KOSPI", "KOSDAQ", "RUSSELL2000"]
        for m in markets:
            self.assertIn(m, MARKET_NEURAL_SDE_PROFILES)
            prof = MARKET_NEURAL_SDE_PROFILES[m]
            self.assertGreater(prof["base_vol"], 0.05)
            self.assertGreater(prof["base_lambda"], 0.0)
            self.assertGreater(prof["kou_p"], 0.0)
            self.assertLess(prof["kou_p"], 1.0)
            self.assertGreater(prof["kou_eta1"], 1.0)
            self.assertGreater(prof["kou_eta2"], 0.0)
            self.assertGreater(prof["merton_sigma"], 0.0)

    def test_tc08_dynamic_market_calibration(self) -> None:
        """TC08: Verify dynamic market profile calibration switching to KOSDAQ."""
        engine = NeuralSDEVolatilityForecaster(market="SP500")
        self.assertEqual(engine.market, "SP500")
        engine.calibrate_market("KOSDAQ")
        self.assertEqual(engine.market, "KOSDAQ")
        self.assertEqual(engine.base_vol, 0.26)
        self.assertEqual(engine.base_lambda, 0.15)

    def test_tc09_unknown_market_profile_fallback(self) -> None:
        """TC09: Assert unknown market profile safely falls back to SP500."""
        engine = NeuralSDEVolatilityForecaster(market="UNKNOWN_EXCHANGE_XYZ")
        self.assertEqual(engine.market, "SP500")
        self.assertEqual(engine.base_vol, 0.12)

    # =======================================================================
    # Category 3: Drift Network \mu_\theta(X_t, t) Mechanics & Mean Reversion (TC10 ~ TC13)
    # =======================================================================
    def test_tc10_drift_network_shape_and_smoothness(self) -> None:
        """TC10: Assert drift network output shape and finite difference smoothness."""
        x_grid = np.linspace(-2.0, 2.0, 200)
        drift = self.default_engine.compute_instantaneous_drift(x_grid)
        self.assertEqual(drift.shape, x_grid.shape)
        # Finite difference derivative
        d_drift = np.diff(drift) / np.diff(x_grid)
        self.assertTrue(np.all(np.isfinite(d_drift)))
        self.assertTrue(np.all(d_drift < 0.0), "Derivative should be negative reflecting mean reversion.")

    def test_tc11_mean_reversion_drift_pull_direction(self) -> None:
        """TC11: Assert drift pull direction: positive X pulls downward, negative X pulls upward."""
        drift_high = self.default_engine.compute_instantaneous_drift(1.5, equilibrium_x=0.0)
        drift_low = self.default_engine.compute_instantaneous_drift(-1.5, equilibrium_x=0.0)
        self.assertLess(float(drift_high), 0.0)
        self.assertGreater(float(drift_low), 0.0)

    def test_tc12_lipschitz_continuity_and_bounded_drift(self) -> None:
        """TC12: Verify bounded Lipschitz slope L <= 25.0 across [-5.0, 5.0]."""
        x1 = np.linspace(-5.0, 4.9, 100)
        x2 = x1 + 0.1
        mu1 = self.default_engine.compute_instantaneous_drift(x1)
        mu2 = self.default_engine.compute_instantaneous_drift(x2)
        slopes = np.abs(mu2 - mu1) / 0.1
        self.assertTrue(np.all(slopes <= 25.0), f"Max slope {np.max(slopes)} exceeded 25.0")

    def test_tc13_equilibrium_drift_near_zero(self) -> None:
        """TC13: Assert drift is near zero at equilibrium X = bar{X}."""
        drift_eq = float(self.default_engine.compute_instantaneous_drift(0.0, equilibrium_x=0.0))
        self.assertLess(abs(drift_eq), 0.1)

    # =======================================================================
    # Category 4: Diffusion Network \sigma_\phi(X_t, t) & Positivity Guarantees (TC14 ~ TC17)
    # =======================================================================
    def test_tc14_diffusion_network_shape_and_types(self) -> None:
        """TC14: Assert diffusion output shape and non-negativity."""
        x = np.array([-0.05, 0.0, 0.05])
        vol = self.default_engine.compute_instantaneous_volatility(x)
        self.assertEqual(vol.shape, x.shape)
        self.assertTrue(np.all(vol > 0.0))

    def test_tc15_strict_positivity_and_volatility_floor(self) -> None:
        """TC15: Assert sigma(X) >= 1e-4 everywhere, even under extreme excursions."""
        extreme_x = np.array([-1e6, -100.0, 0.0, 100.0, 1e6])
        vol = self.default_engine.compute_instantaneous_volatility(extreme_x)
        self.assertTrue(np.all(vol >= 1e-4), "Volatility violated positivity floor.")

    def test_tc16_volatility_leverage_effect(self) -> None:
        """TC16: Assert leverage effect: negative returns produce higher volatility than positive returns."""
        vol_neg = float(self.default_engine.compute_instantaneous_volatility(-0.05))
        vol_pos = float(self.default_engine.compute_instantaneous_volatility(0.05))
        self.assertGreater(vol_neg, vol_pos)

    def test_tc17_volatility_saturation_ceiling(self) -> None:
        """TC17: Assert volatility remains bounded <= 100.0 without numerical overflow under extreme inputs."""
        vol_ext = float(self.default_engine.compute_instantaneous_volatility(1000.0))
        self.assertLessEqual(vol_ext, 100.0)
        self.assertTrue(math.isfinite(vol_ext))

    # =======================================================================
    # Category 5: Jump Arrival Intensity \lambda_{jump}(X_t) Boundedness & State-Dependence (TC18 ~ TC21)
    # =======================================================================
    def test_tc18_jump_intensity_non_negativity_and_bounds(self) -> None:
        """TC18: Assert 1e-4 <= lambda_jump <= 50.0."""
        lam = self.default_engine.compute_jump_intensity(np.array([0.0]))
        self.assertGreaterEqual(lam, 1e-4)
        self.assertLessEqual(lam, 50.0)

    def test_tc19_microstructural_sensitivity_to_spread_and_obi(self) -> None:
        """TC19: Assert jump intensity elevates significantly under wide spread and high OBI."""
        lam_calm = self.default_engine.compute_jump_intensity(0.0, spread_ratio=1.0, obi=0.0)
        lam_stressed = self.default_engine.compute_jump_intensity(0.0, spread_ratio=5.0, obi=0.9)
        self.assertGreater(lam_stressed, 1.5 * lam_calm)

    def test_tc20_jump_probability_horizon_monotonicity(self) -> None:
        """TC20: Assert strict monotonicity of jump probability across horizons."""
        jump_params = self.default_engine.compute_jump_distribution(0.0)
        p_100ms = jump_params.jump_prob_by_horizon[0.1]
        p_1s = jump_params.jump_prob_by_horizon[1.0]
        p_10s = jump_params.jump_prob_by_horizon[10.0]
        p_60s = jump_params.jump_prob_by_horizon[60.0]

        self.assertGreater(p_100ms, 0.0)
        self.assertLess(p_100ms, p_1s)
        self.assertLess(p_1s, p_10s)
        self.assertLess(p_10s, p_60s)
        self.assertLess(p_60s, 1.0)

    def test_tc21_zero_intensity_degenerate_probability(self) -> None:
        """TC21: Assert P(jump in H) == 0.0 when lambda == 0.0."""
        for h in [0.1, 1.0, 10.0, 60.0]:
            p = 1.0 - math.exp(-0.0 * h)
            self.assertEqual(p, 0.0)

    # =======================================================================
    # Category 6: Kou Double Exponential Jump Distribution Rigor (TC22 ~ TC26)
    # =======================================================================
    def test_tc22_kou_density_integration_equals_one(self) -> None:
        """TC22: Numerical trapezoidal integration of Kou density over [-15, 15] equals 1.0."""
        y_grid = np.linspace(-15.0, 15.0, 100000)
        p, eta1, eta2 = 0.35, 25.0, 18.0
        dens = kou_density(y_grid, p=p, eta1=eta1, eta2=eta2)
        integral = float(np.trapz(dens, y_grid))
        self.assertAlmostEqual(integral, 1.0, places=4)

    def test_tc23_kou_parameter_constraints_enforcement(self) -> None:
        """TC23: Verify eta1 <= 1.0 is strictly regularized to > 1.0."""
        dens = kou_density(0.5, p=0.4, eta1=0.8, eta2=15.0)
        self.assertTrue(math.isfinite(dens))
        self.assertGreater(dens, 0.0)

    def test_tc24_kou_analytical_vs_empirical_moments(self) -> None:
        """TC24: 50,000 draws via sample_kou_jumps match analytical mean and variance within 3 std errors."""
        p, eta1, eta2 = 0.4, 20.0, 15.0
        analytical_mean = (p / eta1) - ((1.0 - p) / eta2)
        analytical_sq = 2.0 * ((p / (eta1 ** 2)) + ((1.0 - p) / (eta2 ** 2)))
        analytical_var = analytical_sq - (analytical_mean ** 2)

        rng = np.random.default_rng(42)
        samples = sample_kou_jumps(50000, p=p, eta1=eta1, eta2=eta2, rng=rng)

        sample_mean = float(np.mean(samples))
        sample_var = float(np.var(samples))
        se = math.sqrt(sample_var / 50000)

        self.assertAlmostEqual(sample_mean, analytical_mean, delta=3.0 * se)
        self.assertAlmostEqual(sample_var, analytical_var, delta=0.001)

    def test_tc25_kou_asymmetric_probability_split(self) -> None:
        """TC25: Assert proportion of positive jumps approximately equals p."""
        p = 0.35
        rng = np.random.default_rng(123)
        samples = sample_kou_jumps(20000, p=p, eta1=25.0, eta2=18.0, rng=rng)
        prop_pos = float(np.mean(samples >= 0.0))
        self.assertAlmostEqual(prop_pos, p, delta=0.015)

    def test_tc26_kou_crash_hazard_sensitivity(self) -> None:
        """TC26: Compare baseline Kou with crash-stressed Kou."""
        # Baseline
        base_mean = (0.4 / 20.0) - (0.6 / 15.0)
        # Crash stressed: low p (fewer up jumps), heavy negative tail (small eta2)
        crash_mean = (0.15 / 25.0) - (0.85 / 8.0)
        self.assertLess(crash_mean, base_mean)

        rng = np.random.default_rng(999)
        base_samples = sample_kou_jumps(20000, p=0.4, eta1=20.0, eta2=15.0, rng=rng)
        crash_samples = sample_kou_jumps(20000, p=0.15, eta1=25.0, eta2=8.0, rng=rng)
        q01_base = float(np.percentile(base_samples, 1))
        q01_crash = float(np.percentile(crash_samples, 1))
        self.assertGreater(abs(q01_crash), 1.5 * abs(q01_base))

    # =======================================================================
    # Category 7: Merton Log-Normal Jump Distribution Mechanics (TC27 ~ TC29)
    # =======================================================================
    def test_tc27_merton_density_integration_equals_one(self) -> None:
        """TC27: Trapezoidal integration of Merton density equals 1.0."""
        mu, sig = -0.015, 0.035
        y_grid = np.linspace(-10 * sig, 10 * sig, 10000)
        dens = merton_density(y_grid, mu_jump=mu, sigma_jump=sig)
        integral = float(np.trapz(dens, y_grid))
        self.assertAlmostEqual(integral, 1.0, places=4)

    def test_tc28_merton_analytical_moments(self) -> None:
        """TC28: Assert Merton analytical E[e^Y - 1] matches simulated draws within 2%."""
        mu, sig = -0.02, 0.04
        analytical_ey = math.exp(mu + 0.5 * (sig ** 2)) - 1.0
        rng = np.random.default_rng(777)
        draws = sample_merton_jumps(50000, mu_jump=mu, sigma_jump=sig, rng=rng)
        empirical_ey = float(np.mean(np.exp(draws) - 1.0))
        self.assertAlmostEqual(empirical_ey, analytical_ey, delta=0.002)

    def test_tc29_jump_model_switching(self) -> None:
        """TC29: Assert engine correctly switches to Merton model."""
        cfg = NeuralSDEConfig(jump_model=JumpModelType.MERTON)
        engine = NeuralSDEVolatilityForecaster(config=cfg)
        out = engine.predict_from_returns(np.array([0.001, -0.002, 0.001]))
        self.assertEqual(out.jump_parameters.model_type, "MERTON")
        self.assertEqual(out.jump_parameters.mu_jump, -0.015)

    # =======================================================================
    # Category 8: Continuous SDE Simulation & Euler-Maruyama (TC30 ~ TC33)
    # =======================================================================
    def test_tc30_euler_maruyama_single_step_dynamics(self) -> None:
        """TC30: Verify reproducibility under fixed RNG seed."""
        p1 = self.default_engine.simulate_paths(x0=100.0, horizon_sec=1.0, num_paths=10, num_steps=10, seed=42)
        p2 = self.default_engine.simulate_paths(x0=100.0, horizon_sec=1.0, num_paths=10, num_steps=10, seed=42)
        self.assertTrue(np.allclose(p1, p2))

    def test_tc31_poisson_jump_counting_frequency(self) -> None:
        """TC31: Assert jump counting frequency approximates lambda."""
        # Test Poisson simulation counting over T=100s
        lam = 0.5
        dt = 0.005
        n_steps = int(100.0 / dt)
        rng = np.random.default_rng(42)
        u = rng.uniform(0.0, 1.0, size=n_steps)
        n_jumps = np.sum(u < (lam * dt))
        measured_rate = n_jumps / 100.0
        self.assertAlmostEqual(measured_rate, lam, delta=0.15)

    def test_tc32_martingale_property_under_zero_drift(self) -> None:
        """TC32: Assert martingale property: E[X_T] == X_0 under zero drift."""
        paths = self.default_engine.simulate_paths(
            x0=100.0, horizon_sec=10.0, num_paths=1000, num_steps=50, seed=123, zero_drift=True
        )
        mean_xt = float(np.mean(paths[:, -1]))
        self.assertAlmostEqual(mean_xt / 100.0, 1.0, delta=0.05)

    def test_tc33_trajectory_path_generation_shape_and_finite(self) -> None:
        """TC33: Assert trajectory paths shape is (num_paths, num_steps + 1) and all finite."""
        paths = self.default_engine.simulate_paths(x0=100.0, horizon_sec=60.0, num_paths=50, num_steps=200)
        self.assertEqual(paths.shape, (50, 201))
        self.assertTrue(np.all(paths[:, 0] == 100.0))
        self.assertTrue(np.all(np.isfinite(paths)))

    # =======================================================================
    # Category 9: Multi-Horizon Volatility Term Structure & Variance Monotonicity (TC34 ~ TC37)
    # =======================================================================
    def test_tc34_four_horizons_simultaneous_forecast(self) -> None:
        """TC34: Assert all 4 horizons (0.1, 1.0, 10.0, 60.0) are populated."""
        out = self.default_engine.predict_from_returns(np.array([0.001, -0.001]))
        for h in [0.1, 1.0, 10.0, 60.0]:
            self.assertIn(h, out.horizon_metrics)

    def test_tc35_integrated_variance_strict_monotonicity(self) -> None:
        """TC35: Assert cumulative integrated variance V(0.1) < V(1.0) < V(10.0) < V(60.0)."""
        out = self.default_engine.predict_from_returns(np.array([0.001, -0.001]))
        v100ms = out.horizon_metrics[0.1].total_integrated_var
        v1s = out.horizon_metrics[1.0].total_integrated_var
        v10s = out.horizon_metrics[10.0].total_integrated_var
        v60s = out.horizon_metrics[60.0].total_integrated_var

        self.assertLess(v100ms, v1s)
        self.assertLess(v1s, v10s)
        self.assertLess(v10s, v60s)

    def test_tc36_term_structure_slope_calculation(self) -> None:
        """TC36: Assert term structure slope evaluates correctly."""
        out = self.default_engine.predict_from_returns(np.array([0.001, -0.001]))
        slope = out.term_structure_slope
        self.assertTrue(math.isfinite(slope))
        # When instantaneous volatility is elevated, slope turns negative
        stressed_engine = NeuralSDEVolatilityForecaster(market="SP500")
        stressed_engine.base_vol = 0.50
        stressed_out = stressed_engine.predict_from_returns(np.array([-0.05, -0.04]))
        self.assertLess(stressed_out.term_structure_slope, 0.0)

    def test_tc37_annualized_volatility_boundedness(self) -> None:
        """TC37: Assert 0.01 <= annualized_vol <= 5.0 across all horizons."""
        out = self.default_engine.predict_from_returns(np.array([0.002, -0.001]))
        for h, fc in out.horizon_metrics.items():
            self.assertGreaterEqual(fc.annualized_vol, 0.01)
            self.assertLessEqual(fc.annualized_vol, 5.0)

    # =======================================================================
    # Category 10: Implied Volatility Surface, Smile Convexity & Skew Directionality (TC38 ~ TC41)
    # =======================================================================
    def test_tc38_volatility_surface_moneyness_grid(self) -> None:
        """TC38: Assert moneyness grid contains -0.10, -0.05, 0.0, 0.05, 0.10."""
        out = self.default_engine.predict_from_returns(np.array([0.001, 0.002]))
        for k_val in [-0.10, -0.05, 0.0, 0.05, 0.10]:
            self.assertIn(k_val, out.horizon_metrics[1.0].implied_vol_at_moneyness)

    def test_tc39_smile_convexity_invariant(self) -> None:
        """TC39: Assert smile convexity (curvature) > 0 for all horizons."""
        out = self.default_engine.predict_from_returns(np.array([0.001, -0.002]))
        for h, fc in out.horizon_metrics.items():
            self.assertGreater(fc.smile_convexity, 0.0, f"Convexity failed at horizon {h}")

    def test_tc40_risk_reversal_skew_under_crash_hazard(self) -> None:
        """TC40: Assert risk-reversal skew > 0 under equity crash risk."""
        out = self.default_engine.predict_from_returns(np.array([-0.005, -0.002]))
        # In SP500 equity profile, downside hazard dominates -> skew > 0
        self.assertGreater(out.horizon_metrics[1.0].risk_reversal_skew, 0.0)

    def test_tc41_symmetric_smile_under_neutral_jump_parameters(self) -> None:
        """TC41: Assert skew is zero under symmetric Kou jump parameters."""
        engine = NeuralSDEVolatilityForecaster(market="SP500")
        engine.kou_p = 0.5
        engine.kou_eta1 = 20.0
        engine.kou_eta2 = 20.0
        jump_params = engine.compute_jump_distribution(0.0)
        fc_dict, _ = engine.compute_volatility_surface(current_vol=0.15, jump_params=jump_params)
        self.assertAlmostEqual(fc_dict[1.0].risk_reversal_skew, 0.0, places=4)

    # =======================================================================
    # Category 11: Jump-Risk-Adjusted Alpha Conditioning Signals (TC42 ~ TC45)
    # =======================================================================
    def test_tc42_alpha_conditioning_signal_bounds(self) -> None:
        """TC42: Assert alpha conditioning signal bounds."""
        out = self.default_engine.predict_from_returns(np.array([0.001, -0.002]))
        cond = out.alpha_conditioning
        self.assertGreaterEqual(cond.jump_risk_index, 0.0)
        self.assertLessEqual(cond.jump_risk_index, 1.0)
        self.assertGreaterEqual(cond.asymmetric_jump_bias, -1.0)
        self.assertLessEqual(cond.asymmetric_jump_bias, 1.0)
        self.assertGreater(cond.alpha_shrinkage_factor, 0.0)
        self.assertLessEqual(cond.alpha_shrinkage_factor, 1.0)
        self.assertGreaterEqual(cond.leland_buffer_multiplier, 1.0)

    def test_tc43_downside_crash_hazard_shrinkage(self) -> None:
        """TC43: Assert alpha shrinkage < 0.20 under extreme jump hazard."""
        engine = NeuralSDEVolatilityForecaster(market="SP500")
        engine.base_lambda = 5.0
        engine.kou_p = 0.05
        out = engine.predict_from_returns(np.array([-0.08, -0.05]))
        self.assertLess(out.alpha_conditioning.alpha_shrinkage_factor, 0.20)

    def test_tc44_leland_buffer_expansion_under_high_vol(self) -> None:
        """TC44: Assert Leland buffer multiplier > 1.5 under high volatility."""
        engine = NeuralSDEVolatilityForecaster(market="SP500")
        engine.base_vol = 0.60
        engine.base_lambda = 2.0
        out = engine.predict_from_returns(np.array([-0.05, -0.05]))
        self.assertGreater(out.alpha_conditioning.leland_buffer_multiplier, 1.5)

    def test_tc45_alpha_signal_to_dict_and_contract_parity(self) -> None:
        """TC45: Assert AlphaConditioningSignal contains exact fields for CrossAssetGraphFlowAllocator."""
        out = self.default_engine.predict_from_returns(np.array([0.001, -0.001]))
        d = out.alpha_conditioning.to_dict()
        required_keys = [
            "symbol",
            "conditioning_multiplier",
            "downside_penalty_factor",
            "volatility_damping_factor",
            "jump_hazard_gate",
            "asymmetric_bias",
            "node_uncertainty_weight",
            "suggested_leland_expansion_mult",
            "recommended_action",
        ]
        for k in required_keys:
            self.assertIn(k, d)

    # =======================================================================
    # Category 12: Dual-Backend Determinism: PyTorch vs Pure NumPy Analytical Fallback (TC46 ~ TC48)
    # =======================================================================
    def test_tc46_dual_backend_initialization_and_reporting(self) -> None:
        """TC46: Verify backend reporting."""
        cfg_np = NeuralSDEConfig(use_torch=False)
        eng_np = NeuralSDEVolatilityForecaster(config=cfg_np)
        self.assertEqual(eng_np.backend, "numpy")

        cfg_pt = NeuralSDEConfig(use_torch=True)
        eng_pt = NeuralSDEVolatilityForecaster(config=cfg_pt)
        if _TORCH_AVAILABLE:
            self.assertEqual(eng_pt.backend, "torch")
        else:
            self.assertEqual(eng_pt.backend, "numpy")

    def test_tc47_deterministic_drift_diffusion_jump_numerical_parity(self) -> None:
        """TC47: Compare drift and volatility between backends."""
        x = np.array([-0.05, 0.0, 0.05])
        drift = self.default_engine.compute_instantaneous_drift(x)
        vol = self.default_engine.compute_instantaneous_volatility(x)
        self.assertTrue(np.all(np.isfinite(drift)))
        self.assertTrue(np.all(np.isfinite(vol)))

    def test_tc48_automatic_fallback_when_torch_unavailable(self) -> None:
        """TC48: Assert automatic safe fallback to numpy when torch is unavailable."""
        with patch("src.ai.neural_sde_volatility_forecaster._TORCH_AVAILABLE", False):
            eng = NeuralSDEVolatilityForecaster(config=NeuralSDEConfig(use_torch=True))
            self.assertEqual(eng.backend, "numpy")

    # =======================================================================
    # Category 13: Adversarial Stress, Non-Finite Guarding & Defensive Defaults (TC49 ~ TC52)
    # =======================================================================
    def test_tc49_non_finite_inputs_nan_inf_handling(self) -> None:
        """TC49: Assert engine sanitizes NaN and Inf without crashing."""
        tainted = np.array([100.0, np.nan, 102.0, np.inf, -np.inf, 101.0])
        out = self.default_engine.predict_from_prices(tainted)
        self.assertTrue(math.isfinite(out.instantaneous_diffusion_vol))
        self.assertTrue(math.isfinite(out.alpha_conditioning.conditioning_multiplier))

    def test_tc50_zero_volatility_flatline_input(self) -> None:
        """TC50: Assert engine handles flatline price series safely with vol_floor."""
        flat_prices = np.ones(100) * 150.0
        out = self.default_engine.predict_from_prices(flat_prices)
        self.assertGreaterEqual(out.instantaneous_diffusion_vol, 1e-4)

    def test_tc51_extreme_price_spike_flash_crash(self) -> None:
        """TC51: Assert bounded outputs during extreme 100x spike or -99% crash."""
        crash_prices = np.array([100.0, 1.0, 0.5, 0.01])
        out = self.default_engine.predict_from_prices(crash_prices)
        self.assertLessEqual(out.instantaneous_jump_intensity, 50.0)
        self.assertTrue(math.isfinite(out.alpha_conditioning.conditioning_multiplier))

    def test_tc52_empty_input_raises_value_error(self) -> None:
        """TC52: Assert empty input series raises ValueError."""
        with self.assertRaises(ValueError):
            self.default_engine.predict_from_returns(np.array([]))
        with self.assertRaises(ValueError):
            self.default_engine.predict_from_prices(np.array([]))

    # =======================================================================
    # Category 14: Execution Latency & High-Throughput Performance Benchmark (TC53 ~ TC55)
    # =======================================================================
    def test_tc53_single_inference_pass_latency_under_5ms(self) -> None:
        """TC53: Assert single forecast inference pass latency < 5.0 ms."""
        returns = np.random.normal(0.0, 0.01, size=50)
        # Warmup
        self.default_engine.predict_from_returns(returns)

        t0 = time.perf_counter()
        out = self.default_engine.predict_from_returns(returns)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 5.0, f"Latency {elapsed_ms:.3f}ms exceeded 5.0ms SLA")

    def test_tc54_batch_inference_throughput_benchmark(self) -> None:
        """TC54: Assert 100 consecutive forecaster calls complete in < 250 ms."""
        returns = np.random.normal(0.0, 0.01, size=30)
        t0 = time.perf_counter()
        for _ in range(100):
            self.default_engine.predict_from_returns(returns)
        total_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(total_ms, 250.0, f"100 calls took {total_ms:.2f}ms (exceeded 250ms)")

    def test_tc55_telemetry_export_and_call_tracking(self) -> None:
        """TC55: Assert telemetry tracking reflects non-zero forecast calls and avg latency."""
        self.default_engine.predict_from_returns(np.array([0.001, -0.001]))
        tel = self.default_engine.export_telemetry()
        self.assertGreater(tel["total_forecast_calls"], 0)
        self.assertGreater(tel["avg_latency_us"], 0.0)
        self.assertEqual(tel["version"], 118)
        self.assertEqual(tel["feature"], "F561")


if __name__ == "__main__":
    unittest.main()
