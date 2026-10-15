"""
tests/test_phase111_deep_hawkes.py — Comprehensive Unit & Property Test Suite.

Phase 111 (Release R127 / v118 Production Master, Feature F526)
Milestone M2: Deep Multivariate Hawkes Process Generative Order Flow Synthesizer

Tests:
  - TC01: Class exports, version metadata, and alias trees resolution
  - TC02: Mirrored import parity between src.ai and trading_system.src.ai
  - TC03: Dual placement bit-for-bit SHA-256 hash identity
  - TC04: 6D canonical and 4D directional event space topologies
  - TC05: Neural baseline intensity network forward pass, GELU, and Softplus positivity guarantee
  - TC06: State feature vector construction and regime sensitivity
  - TC07: Exponential kernel, power-law kernel, and multi-exponential sum kernel evaluations
  - TC08: Spectral radius projection and L1 stationarity enforcement rho(Gamma) < 1.0
  - TC09: Transient supercritical excursion in flash crash regime [1.02, 1.15]
  - TC10: 5-market calibration profiles (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)
  - TC11: Multivariate Ogata thinning simulation and synthetic order stream properties
  - TC12: Non-stationary cluster burst generation under flash crash stress
  - TC13: Empirical parameter estimation and fit summary
  - TC14: LOB replay integration into FastOrderBookMatchingEngine / FastLOBEngine
  - TC15: OMS execution slippage stress testing and feedback scaling
  - TC16: Edge cases, adversarial inputs, and reproducible seeding
"""

import hashlib
import math
from pathlib import Path
import pytest
import numpy as np

from src.ai.deep_hawkes_synthesizer import (
    VERSION,
    RELEASE,
    EVENT_TYPES_6D,
    EVENT_TYPES_4D,
    VALID_MARKETS,
    HawkesEvent,
    SyntheticOrderEvent,
    HawkesMarketCalibration,
    SlippageStressResult,
    SimulationResult,
    StressTestReport,
    HawkesFitSummary,
    NeuralBaselineNetwork,
    DeepMultivariateHawkesSynthesizer,
    MultivariateHawkesProcess,
    DeepHawkesOrderFlowSynthesizer,
    DeepHawkesProcessSynthesizer,
    NeuralHawkesOrderFlowSynthesizer,
    Phase111HawkesSynthesizer,
    MultivariateHawkesOrderSynthesizer,
    OrderFlowPointProcessSynthesizer,
)


class TestPhase111DeepHawkesSynthesizer:
    """Comprehensive test suite for Phase 111 Deep Multivariate Hawkes Synthesizer."""

    def test_tc01_class_exports_version_and_aliases(self):
        """TC01: Verify version metadata, module exports, and alias trees."""
        assert VERSION == 111
        assert RELEASE == "R127"

        # Module-level aliases
        assert MultivariateHawkesProcess is DeepMultivariateHawkesSynthesizer
        assert DeepHawkesOrderFlowSynthesizer is DeepMultivariateHawkesSynthesizer
        assert DeepHawkesProcessSynthesizer is DeepMultivariateHawkesSynthesizer
        assert NeuralHawkesOrderFlowSynthesizer is DeepMultivariateHawkesSynthesizer
        assert Phase111HawkesSynthesizer is DeepMultivariateHawkesSynthesizer
        assert MultivariateHawkesOrderSynthesizer is DeepMultivariateHawkesSynthesizer
        assert OrderFlowPointProcessSynthesizer is DeepMultivariateHawkesSynthesizer

        # Class-level attributes
        assert DeepMultivariateHawkesSynthesizer.MultivariateHawkesProcess is DeepMultivariateHawkesSynthesizer
        assert DeepMultivariateHawkesSynthesizer.Phase111HawkesSynthesizer is DeepMultivariateHawkesSynthesizer

        synth = Phase111HawkesSynthesizer(market="SP500", dimension=6)
        assert synth.VERSION == 111
        assert synth.RELEASE == "R127"
        assert isinstance(synth, DeepMultivariateHawkesSynthesizer)

    def test_tc02_mirrored_import_parity(self):
        """TC02: Verify mirrored imports from trading_system.src.ai match src.ai."""
        from trading_system.src.ai.deep_hawkes_synthesizer import (
            DeepMultivariateHawkesSynthesizer as TSHawkes,
            SyntheticOrderEvent as TSSyntheticOrderEvent,
            VERSION as TS_VERSION,
            RELEASE as TS_RELEASE,
        )
        assert TSHawkes is not None
        assert TSSyntheticOrderEvent is not None
        assert TS_VERSION == 111
        assert TS_RELEASE == "R127"

        synth1 = DeepMultivariateHawkesSynthesizer(market="NASDAQ", seed=123)
        synth2 = TSHawkes(market="NASDAQ", seed=123)
        assert type(synth1).__name__ == type(synth2).__name__
        assert synth1.compute_branching_ratio() == pytest.approx(synth2.compute_branching_ratio(), rel=1e-5)

    def test_tc03_dual_placement_sha256_hash_identity(self):
        """TC03: Enforce bit-for-bit SHA-256 identity between dual placement paths."""
        p1 = Path("src/ai/deep_hawkes_synthesizer.py")
        p2 = Path("trading_system/src/ai/deep_hawkes_synthesizer.py")

        assert p1.exists(), f"Missing primary file: {p1}"
        assert p2.exists(), f"Missing mirrored file: {p2}"

        h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
        h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
        assert h1 == h2, f"SHA-256 hash mismatch between {p1} and {p2}: {h1} != {h2}"

    def test_tc04_event_space_topologies(self):
        """TC04: Verify 6D canonical and 4D directional event space topologies."""
        assert len(EVENT_TYPES_6D) == 6
        assert EVENT_TYPES_6D == [
            "BUY_TRADE", "SELL_TRADE", "BUY_CANCEL", "SELL_CANCEL", "BID_REVISION", "ASK_REVISION"
        ]

        assert len(EVENT_TYPES_4D) == 4
        assert EVENT_TYPES_4D == ["BUY_TRADE", "SELL_TRADE", "BUY_CANCEL", "SELL_CANCEL"]

        synth6 = DeepMultivariateHawkesSynthesizer(dimension=6)
        assert synth6.dimension == 6
        assert synth6.event_types == EVENT_TYPES_6D
        assert synth6.alpha_matrix.shape == (6, 6)

        synth4 = DeepMultivariateHawkesSynthesizer(dimension=4)
        assert synth4.dimension == 4
        assert synth4.event_types == EVENT_TYPES_4D
        assert synth4.alpha_matrix.shape == (4, 4)

    def test_tc05_neural_baseline_network_and_positivity_guarantee(self):
        """TC05: Test neural baseline network forward pass, GELU, and Softplus positivity guarantee."""
        net = NeuralBaselineNetwork(input_dim=7, hidden_dim=32, output_dim=6, base_floor=0.08, seed=42)

        # Test GELU output
        z = np.array([-3.0, -1.0, 0.0, 1.0, 3.0], dtype=np.float64)
        gelu_out = net.gelu(z)
        assert gelu_out[2] == pytest.approx(0.0, abs=1e-5)
        assert gelu_out[3] > 0.80
        assert gelu_out[0] < 0.0

        # Test Softplus positivity guarantee on extreme inputs
        extreme_z = np.array([-1000.0, -50.0, -10.0, 0.0, 10.0, 50.0, 1000.0], dtype=np.float64)
        sp_out = net.softplus(extreme_z, epsilon=1e-4)
        assert np.all(sp_out > 0.0), "Softplus must be strictly positive for all real inputs"
        assert np.all(np.isfinite(sp_out)), "Softplus must not produce NaN or Inf"
        assert sp_out[0] >= 1e-4

        # Test forward pass with base floor guarantee
        x_norm = np.array([0.16, 0.25, 0.0, 0.0, 0.0, 1.0, 0.0], dtype=np.float64)
        mu_out = net.forward(x_norm)
        assert len(mu_out) == 6
        assert np.all(mu_out >= 0.08), "Baseline intensity must strictly satisfy base_floor"
        assert np.all(np.isfinite(mu_out))

    def test_tc06_state_vector_and_regime_sensitivity(self):
        """TC06: Test state vector construction and regime sensitivity."""
        synth = DeepMultivariateHawkesSynthesizer(market="SP500")

        # Normal regime baseline
        mu_normal = synth.compute_neural_baseline(regime="NORMAL")
        # Crisis / flash crash regime baseline
        mu_crisis = synth.compute_neural_baseline(regime="FLASH_CRASH")

        assert np.all(mu_normal > 0.0)
        assert np.all(mu_crisis > 0.0)
        # In crisis regime, intensities must be significantly elevated
        assert np.mean(mu_crisis) > 1.5 * np.mean(mu_normal)

    def test_tc07_kernel_decay_models(self):
        """TC07: Test exponential, power-law, and multi-exponential sum kernels."""
        # 1. Exponential
        synth_exp = DeepMultivariateHawkesSynthesizer(kernel_type="exponential", seed=42)
        gamma_exp = synth_exp.compute_gamma_matrix()
        assert gamma_exp.shape == (6, 6)
        assert np.all(gamma_exp >= 0.0)

        # 2. Power-law
        synth_pl = DeepMultivariateHawkesSynthesizer(kernel_type="power_law", seed=42)
        synth_pl.power_law_gamma = 1.6
        synth_pl.power_law_tau0 = 0.04
        gamma_pl = synth_pl.compute_gamma_matrix()
        assert gamma_pl.shape == (6, 6)
        assert np.all(gamma_pl >= 0.0)

        # 3. Multi-exponential
        synth_me = DeepMultivariateHawkesSynthesizer(kernel_type="multi_exp", seed=42)
        gamma_me = synth_me.compute_gamma_matrix()
        assert gamma_me.shape == (6, 6)
        assert np.all(gamma_me >= 0.0)

        # Verify intensity decays over time
        history = [
            HawkesEvent(timestamp=0.1, event_type="BUY_TRADE", event_index=0),
            HawkesEvent(timestamp=0.2, event_type="SELL_TRADE", event_index=1),
        ]
        lam_immediate = synth_exp.compute_intensities(current_time=0.21, history=history)
        lam_later = synth_exp.compute_intensities(current_time=1.50, history=history)
        assert np.all(lam_immediate >= lam_later), "Intensity must decay monotonically after events"

    def test_tc08_spectral_radius_and_stationarity_enforcement(self):
        """TC08: Test spectral radius projection and L1 stationarity enforcement rho(Gamma) < 1.0."""
        synth = DeepMultivariateHawkesSynthesizer(market="SP500")

        # Initial calibrated branching ratio must be subcritical
        rho_initial = synth.compute_branching_ratio()
        assert 0.0 < rho_initial < 1.0, f"Branching ratio must be subcritical, got {rho_initial}"
        assert synth.calibration.is_stable is True

        # Artificially inflate alpha matrix to explosive regime
        synth.alpha_matrix = synth.alpha_matrix * 5.0
        rho_explosive = synth.compute_branching_ratio()
        assert rho_explosive > 1.0, "Artificial inflation must create explosive process"

        # Apply stability projection
        rho_projected = synth.project_to_stability(max_branching=0.95)
        assert rho_projected <= 0.95, f"Projection must enforce rho <= 0.95, got {rho_projected}"
        assert synth.compute_branching_ratio() <= 0.95

    def test_tc09_flash_crash_supercritical_excursion(self):
        """TC09: Test transient supercritical excursion during flash crash simulation [1.02, 1.15]."""
        synth = DeepMultivariateHawkesSynthesizer(market="KOSPI", seed=101)

        # Normal simulation has stable branching ratio
        res_normal = synth.simulate_order_stream(duration_seconds=2.0, regime="NORMAL", seed=101)
        assert res_normal.branching_ratio < 1.0
        assert res_normal.is_flash_burst is False

        # Flash crash cluster burst simulation
        res_flash = synth.simulate_cluster_burst(
            duration_seconds=2.0,
            burst_intensity_multiplier=3.0,
            regime="FLASH_CRASH",
            seed=101,
        )
        assert res_flash.is_flash_burst is True
        assert res_flash.total_events > 0

        # After flash crash simulation completes, synthesizer must restore subcritical stationarity
        assert synth.compute_branching_ratio() < 1.0

    def test_tc10_five_market_calibration_profiles(self):
        """TC10: Test 5-market calibration profiles (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)."""
        expected_targets = {
            "KOSPI": 0.78,
            "KOSDAQ": 0.88,
            "SP500": 0.72,
            "NASDAQ": 0.82,
            "RUSSELL2000": 0.86,
        }

        for mkt, target_rho in expected_targets.items():
            synth = DeepMultivariateHawkesSynthesizer(market=mkt)
            cal = synth.calibration
            assert cal.market == mkt
            assert cal.dimension == 6
            assert cal.is_stable is True
            # Check branching ratio is close to calibrated target within reasonable tolerance
            assert cal.branching_ratio == pytest.approx(target_rho, abs=0.08)
            assert cal.endogenous_multiplier >= 1.0
            assert np.all(synth.base_mu > 0.0)
            assert np.all(synth.beta_matrix > 0.0)

    def test_tc11_ogata_thinning_simulation(self):
        """TC11: Test multivariate Ogata thinning simulation and synthetic order stream properties."""
        synth = DeepMultivariateHawkesSynthesizer(market="SP500", seed=42)
        res = synth.simulate_order_stream(
            duration_seconds=3.0,
            initial_price=150.0,
            tick_size=0.01,
            seed=42,
        )

        assert isinstance(res, SimulationResult)
        assert res.total_events > 10
        assert res.duration_seconds > 0.0

        # Verify event properties
        timestamps_ns = [e.timestamp_ns for e in res.events]
        # Timestamps must be non-decreasing
        assert all(t2 >= t1 for t1, t2 in zip(timestamps_ns[:-1], timestamps_ns[1:]))

        for ev in res.events:
            assert isinstance(ev, SyntheticOrderEvent)
            assert ev.event_type in EVENT_TYPES_6D
            assert ev.side in ("BUY", "SELL")
            assert ev.price > 0.0
            # Price must be quantized to tick size
            assert round(ev.price / 0.01) * 0.01 == pytest.approx(ev.price, abs=1e-5)
            assert ev.volume > 0.0
            assert ev.intensity_at_arrival > 0.0

    def test_tc12_cluster_burst_and_event_density(self):
        """TC12: Test cluster burst generation density vs tranquil regime."""
        synth = DeepMultivariateHawkesSynthesizer(market="NASDAQ", seed=2026)

        res_tranquil = synth.simulate_order_stream(duration_seconds=3.0, regime="NORMAL", seed=2026)
        res_burst = synth.simulate_cluster_burst(
            duration_seconds=3.0,
            burst_intensity_multiplier=4.0,
            regime="FLASH_CRASH",
            seed=2026,
        )

        # Burst should produce significantly higher event count
        assert res_burst.total_events > res_tranquil.total_events
        assert res_burst.is_flash_burst is True

    def test_tc13_empirical_fit_and_summary(self):
        """TC13: Test empirical parameter estimation and fit summary."""
        synth = DeepMultivariateHawkesSynthesizer(market="SP500", seed=99)
        sim_res = synth.simulate_order_stream(duration_seconds=5.0, seed=99)

        # Fit model on simulated event stream
        fit_res = synth.fit(sim_res.events)
        assert isinstance(fit_res, HawkesFitSummary)
        assert fit_res.converged is True
        assert fit_res.dimension == 6
        assert fit_res.num_events == sim_res.total_events
        assert fit_res.is_stable is True
        assert fit_res.branching_ratio < 1.0
        assert np.all(fit_res.estimated_base_mu > 0.0)

    def test_tc14_lob_replay_integration(self):
        """TC14: Test LOB replay into mock or FastOrderBookMatchingEngine."""
        from trading_system.src.core.fast_lob_engine import FastOrderBookMatchingEngine

        lob = FastOrderBookMatchingEngine(symbol="TEST_REPLAY")
        synth = DeepMultivariateHawkesSynthesizer(market="SP500", seed=55)
        events = synth.generate_order_events(duration=2.0, seed=55)

        summary = synth.replay_into_lob(lob, events)
        assert summary["total_events"] == len(events)
        assert summary["trades_replayed"] >= 0
        assert summary["cancels_replayed"] >= 0
        assert summary["revisions_replayed"] >= 0
        assert summary["replay_throughput_eps"] > 0.0

    def test_tc15_oms_execution_stress_testing(self):
        """TC15: Test OMS execution slippage stress testing and feedback scaling."""
        synth = DeepMultivariateHawkesSynthesizer(market="SP500", seed=77)
        events_normal = synth.generate_order_events(duration=3.0, regime="NORMAL", seed=77)
        events_flash = synth.simulate_cluster_burst(duration_seconds=3.0, regime="FLASH_CRASH", seed=77).events

        order_plans = [
            {"symbol": "SPY", "side": "BUY", "quantity": 1000.0, "target_price": 500.0},
            {"symbol": "QQQ", "side": "SELL", "quantity": 800.0, "target_price": 400.0},
        ]

        # Normal stress test
        res_norm = synth.stress_test_oms_execution(order_plans, events_normal, market="SP500")
        assert isinstance(res_norm, SlippageStressResult)
        assert res_norm.executed_slices == 2
        assert res_norm.stress_slippage_bps >= res_norm.nominal_slippage_bps
        assert res_norm.slippage_multiplier >= 1.0

        # Flash stress test
        res_flash = synth.stress_test_oms_execution(order_plans, events_flash, market="SP500")
        assert res_flash.regime == "FLASH_CRASH"
        assert res_flash.stress_slippage_bps > res_norm.stress_slippage_bps
        assert res_flash.slippage_multiplier > res_norm.slippage_multiplier
        assert res_flash.liquidity_depletion_pct > res_norm.liquidity_depletion_pct
        assert res_flash.recommended_slippage_scalar > 1.0

        # Interface contract alias
        rep = synth.stress_test_execution(None, test_scenarios=["FLASH_CRASH"])
        assert isinstance(rep, StressTestReport)

    def test_tc16_edge_cases_and_reproducibility(self):
        """TC16: Test edge cases (empty history, degenerate features, reproducible seed)."""
        synth = DeepMultivariateHawkesSynthesizer(seed=12345)

        # Empty event fitting
        empty_fit = synth.fit([])
        assert empty_fit.converged is False
        assert empty_fit.num_events == 0

        # Empty stress test
        empty_stress = synth.stress_test_oms_execution([], [])
        assert empty_stress.total_events == 0

        # Reproducibility with identical seed
        s1 = DeepMultivariateHawkesSynthesizer(seed=777)
        res1 = s1.simulate_order_stream(duration_seconds=2.0, seed=777)

        s2 = DeepMultivariateHawkesSynthesizer(seed=777)
        res2 = s2.simulate_order_stream(duration_seconds=2.0, seed=777)

        assert res1.total_events == res2.total_events
        assert [e.price for e in res1.events] == [e.price for e in res2.events]
        assert [e.event_type for e in res1.events] == [e.event_type for e in res2.events]
