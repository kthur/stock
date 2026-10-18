r"""
tests/test_phase119_challenger2_gat_stress.py
=============================================
Empirical Performance, Latency SLA (< 5ms), and Backend Determinism Stress Testing Suite
for TemporalGATLeadLagForecaster (Feature F565, Phase 119 Milestone 1).

Executed by: Challenger 2 (empirical_challenger / critic)
Scope:
  - Benchmark inference latency per pass (< 5ms SLA) across 5 markets and both backends.
  - Verify close numerical consistency / parity between PyTorch and pure NumPy backends.
  - Stress test boundary conditions: minimal lookback, extreme lookback, flash crash shocks,
    zero-volatility flatlines, collinear assets, and random seed invariance.
  - Verify mathematical invariants: row-stochasticity, flow conservation, variance monotonicity.
"""

from __future__ import annotations

import math
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List

import numpy as np

# Ensure project root and trading_system are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(TRADING_SYSTEM_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.ai.temporal_gat_lead_lag_forecaster as gat_module
from src.ai.temporal_gat_lead_lag_forecaster import (
    TemporalGATLeadLagForecaster,
    TemporalGATConfig,
    _TORCH_AVAILABLE,
    CANONICAL_MACRO_NODES,
    CANONICAL_SECTOR_NODES,
    CANONICAL_KRX_NODES,
    ALL_CANONICAL_NODES,
    NUM_CANONICAL_NODES,
)

if _TORCH_AVAILABLE:
    import torch


class TestPhase119Challenger2GATStress(unittest.TestCase):
    """Adversarial stress and SLA verification for Feature F565."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rng = np.random.RandomState(42)
        cls.canonical_nodes = NUM_CANONICAL_NODES  # 25
        cls.markets = ("SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ")

    def test_tc01_latency_sla_pytorch_across_5_markets(self) -> None:
        """TC01: PyTorch backend mean latency < 5.0ms SLA across all 5 markets."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed in this environment")

        ret = self.rng.randn(60, self.canonical_nodes) * 0.01

        for market in self.markets:
            forecaster = TemporalGATLeadLagForecaster(
                market=market,
                config=TemporalGATConfig(market=market, use_torch=True, seed=42),
            )
            # Warmup
            for _ in range(10):
                forecaster.predict_drift(input_tensor=ret)

            latencies = []
            N_RUNS = 100
            for _ in range(N_RUNS):
                t0 = time.perf_counter_ns()
                res = forecaster.predict_drift(input_tensor=ret)
                t1 = time.perf_counter_ns()
                latencies.append((t1 - t0) / 1e6)

            lat = np.array(latencies)
            mean_lat = float(np.mean(lat))
            p95_lat = float(np.percentile(lat, 95))

            self.assertEqual(res.backend, "torch")
            self.assertLess(
                mean_lat,
                5.0,
                f"Market {market} PyTorch mean latency {mean_lat:.4f}ms exceeds 5.0ms SLA",
            )
            self.assertLess(
                p95_lat,
                10.0,
                f"Market {market} PyTorch p95 latency {p95_lat:.4f}ms exceeds acceptable SLA threshold",
            )

    def test_tc02_latency_sla_numpy_across_5_markets(self) -> None:
        """TC02: Pure NumPy backend mean latency strictly < 5.0ms and p95 < 5.0ms across all 5 markets."""
        ret = self.rng.randn(60, self.canonical_nodes) * 0.01

        for market in self.markets:
            forecaster = TemporalGATLeadLagForecaster(
                market=market,
                config=TemporalGATConfig(market=market, use_torch=False, seed=42),
            )
            # Warmup
            for _ in range(10):
                forecaster.predict_drift(input_tensor=ret)

            latencies = []
            N_RUNS = 100
            for _ in range(N_RUNS):
                t0 = time.perf_counter_ns()
                res = forecaster.predict_drift(input_tensor=ret)
                t1 = time.perf_counter_ns()
                latencies.append((t1 - t0) / 1e6)

            lat = np.array(latencies)
            mean_lat = float(np.mean(lat))
            p95_lat = float(np.percentile(lat, 95))
            max_lat = float(np.max(lat))

            self.assertEqual(res.backend, "numpy")
            self.assertLess(
                mean_lat,
                5.0,
                f"Market {market} NumPy mean latency {mean_lat:.4f}ms exceeds 5.0ms SLA",
            )
            self.assertLess(
                p95_lat,
                5.0,
                f"Market {market} NumPy p95 latency {p95_lat:.4f}ms exceeds 5.0ms SLA",
            )
            self.assertLess(
                max_lat,
                15.0,
                f"Market {market} NumPy max latency {max_lat:.4f}ms exceeds boundary",
            )

    def test_tc03_high_throughput_batch_stress(self) -> None:
        """TC03: 100 consecutive inference calls complete under 350ms total time (throughput > 280 Hz)."""
        ret = self.rng.randn(60, self.canonical_nodes) * 0.01
        forecaster = TemporalGATLeadLagForecaster(
            config=TemporalGATConfig(use_torch=False, seed=42)
        )

        t0 = time.perf_counter_ns()
        for _ in range(100):
            res = forecaster.predict_drift(input_tensor=ret)
        total_time_ms = (time.perf_counter_ns() - t0) / 1e6

        self.assertLess(
            total_time_ms,
            350.0,
            f"100 consecutive inference calls took {total_time_ms:.2f}ms (threshold 350ms)",
        )

    def test_tc04_deterministic_reproducibility_pytorch(self) -> None:
        """TC04: Repeated calls with identical inputs on PyTorch backend produce bit-for-bit identical outputs."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed in this environment")

        ret = self.rng.randn(60, self.canonical_nodes) * 0.01
        forecaster = TemporalGATLeadLagForecaster(
            config=TemporalGATConfig(use_torch=True, seed=42)
        )

        res1 = forecaster.predict_drift(input_tensor=ret)
        res2 = forecaster.predict_drift(input_tensor=ret)

        np.testing.assert_array_equal(
            res1.impulse_flow.attention_weights,
            res2.impulse_flow.attention_weights,
            err_msg="PyTorch attention weights diverged on identical input",
        )
        for h in ("100ms", "1s", "5s", "1m"):
            np.testing.assert_array_equal(
                res1.horizons[h].expected_drift_bps,
                res2.horizons[h].expected_drift_bps,
                err_msg=f"PyTorch expected drift diverged on identical input for horizon {h}",
            )

    def test_tc05_deterministic_reproducibility_numpy(self) -> None:
        """TC05: Repeated calls with identical inputs on NumPy backend produce bit-for-bit identical outputs."""
        ret = self.rng.randn(60, self.canonical_nodes) * 0.01
        forecaster = TemporalGATLeadLagForecaster(
            config=TemporalGATConfig(use_torch=False, seed=42)
        )

        res1 = forecaster.predict_drift(input_tensor=ret)
        res2 = forecaster.predict_drift(input_tensor=ret)

        np.testing.assert_array_equal(
            res1.impulse_flow.attention_weights,
            res2.impulse_flow.attention_weights,
            err_msg="NumPy attention weights diverged on identical input",
        )
        for h in ("100ms", "1s", "5s", "1m"):
            np.testing.assert_array_equal(
                res1.horizons[h].expected_drift_bps,
                res2.horizons[h].expected_drift_bps,
                err_msg=f"NumPy expected drift diverged on identical input for horizon {h}",
            )

    def test_tc06_backend_numerical_consistency_multi_seed(self) -> None:
        """TC06: PyTorch and pure NumPy backends achieve close numerical parity across 5 distinct random seeds."""
        if not _TORCH_AVAILABLE:
            self.skipTest("PyTorch is not installed in this environment")

        seeds = [42, 100, 777, 2026, 9999]
        ret = self.rng.randn(60, self.canonical_nodes) * 0.015

        for seed in seeds:
            f_torch = TemporalGATLeadLagForecaster(
                config=TemporalGATConfig(use_torch=True, seed=seed)
            )
            f_numpy = TemporalGATLeadLagForecaster(
                config=TemporalGATConfig(use_torch=False, seed=seed)
            )

            res_t = f_torch.predict_drift(input_tensor=ret)
            res_n = f_numpy.predict_drift(input_tensor=ret)

            # 1. Attention matrix parity: max abs error < 1e-6
            w_err = np.max(np.abs(res_t.impulse_flow.attention_weights - res_n.impulse_flow.attention_weights))
            self.assertLess(
                w_err,
                1e-6,
                f"Seed {seed}: Attention weight difference {w_err:.2e} exceeds 1e-6",
            )

            # 2. Centrality parity: max abs error < 1e-6
            c_err = np.max(np.abs(res_t.impulse_flow.net_lead_lag_centrality - res_n.impulse_flow.net_lead_lag_centrality))
            self.assertLess(
                c_err,
                1e-6,
                f"Seed {seed}: Centrality difference {c_err:.2e} exceeds 1e-6",
            )

            # 3. Multi-horizon drift parity: max abs error < 1e-4, correlation > 0.99999
            for h in ("100ms", "1s", "5s", "1m"):
                d_t = res_t.horizons[h].expected_drift_bps
                d_n = res_n.horizons[h].expected_drift_bps
                d_err = np.max(np.abs(d_t - d_n))
                self.assertLess(
                    d_err,
                    1e-4,
                    f"Seed {seed}, Horizon {h}: Drift difference {d_err:.2e} exceeds 1e-4 bps",
                )
                corr = np.corrcoef(d_t, d_n)[0, 1]
                self.assertGreater(
                    corr,
                    0.99999,
                    f"Seed {seed}, Horizon {h}: Drift correlation {corr:.6f} below 0.99999",
                )

    def test_tc07_zero_volatility_flatline_stress(self) -> None:
        """TC07: Constant flatline input (all zeros) produces safe outputs without NaN/Inf on both backends."""
        ret = np.zeros((60, self.canonical_nodes), dtype=np.float64)

        for use_torch in (True, False) if _TORCH_AVAILABLE else (False,):
            f = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=use_torch, seed=42))
            res = f.predict_drift(input_tensor=ret)

            # Invariant: Attention matrix must remain valid row-stochastic probability distribution
            W = res.impulse_flow.attention_weights
            self.assertTrue(np.all(np.isfinite(W)))
            self.assertTrue(np.all(W >= 0.0))
            np.testing.assert_allclose(np.sum(W, axis=1), 1.0, atol=1e-5)

            # Drift and uncertainties must be finite
            for h in ("100ms", "1s", "5s", "1m"):
                drift = res.horizons[h].expected_drift_bps
                epistemic = res.horizons[h].epistemic_uncertainty
                self.assertTrue(np.all(np.isfinite(drift)))
                self.assertTrue(np.all(np.isfinite(epistemic)))
                self.assertTrue(np.all(epistemic > 0.0))

    def test_tc08_flash_crash_and_extreme_shock_resilience(self) -> None:
        """TC08: Extreme 99% market crash and 100x surge do not cause numerical overflow or NaN on either backend."""
        # 1. 99% flash crash on SOX and SP500
        crash_ret = self.rng.randn(60, self.canonical_nodes) * 0.01
        sox_idx = ALL_CANONICAL_NODES.index("SOX")
        sp_idx = ALL_CANONICAL_NODES.index("SP500")
        crash_ret[-1, sox_idx] = -0.99
        crash_ret[-1, sp_idx] = -0.50

        # 2. 100x spike on tech sector
        spike_ret = self.rng.randn(60, self.canonical_nodes) * 0.01
        xlk_idx = ALL_CANONICAL_NODES.index("XLK")
        spike_ret[-1, xlk_idx] = 100.0

        for use_torch in (True, False) if _TORCH_AVAILABLE else (False,):
            f = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=use_torch, seed=42))

            res_crash = f.predict_drift(input_tensor=crash_ret)
            res_spike = f.predict_drift(input_tensor=spike_ret)

            # Verify crash drift is finite and bounded
            d_crash = res_crash.horizons["1s"].expected_drift_bps
            self.assertTrue(np.all(np.isfinite(d_crash)))
            self.assertTrue(np.all(np.abs(d_crash) < 5000.0))

            # Verify spike drift is finite and bounded
            d_spike = res_spike.horizons["1s"].expected_drift_bps
            self.assertTrue(np.all(np.isfinite(d_spike)))
            self.assertTrue(np.all(np.abs(d_spike) < 5000.0))

    def test_tc09_collinear_assets_singular_matrix_handling(self) -> None:
        """TC09: Perfectly collinear asset returns (all 25 nodes identical) handled gracefully without singular matrix crash."""
        single_series = self.rng.randn(60) * 0.02
        collinear_ret = np.tile(single_series[:, np.newaxis], (1, self.canonical_nodes))

        for use_torch in (True, False) if _TORCH_AVAILABLE else (False,):
            f = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=use_torch, seed=42))
            res = f.predict_drift(input_tensor=collinear_ret)

            W = res.impulse_flow.attention_weights
            self.assertTrue(np.all(np.isfinite(W)))
            np.testing.assert_allclose(np.sum(W, axis=1), 1.0, atol=1e-5)

    def test_tc10_minimal_and_extended_lookback_boundaries(self) -> None:
        """TC10: Test lookback window boundaries: T=1, T=2, T=3, T=500, T=2000."""
        for T in (1, 2, 3, 500, 2000):
            ret = self.rng.randn(T, self.canonical_nodes) * 0.01
            f = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=False, seed=42))
            res = f.predict_drift(input_tensor=ret)

            self.assertEqual(len(res.horizons), 4)
            for h in ("100ms", "1s", "5s", "1m"):
                d = res.horizons[h].expected_drift_bps
                self.assertEqual(len(d), self.canonical_nodes)
                self.assertTrue(np.all(np.isfinite(d)))

    def test_tc11_krx_timezone_shift_mechanics_dual_backend(self) -> None:
        """TC11: KRX timezone shift aligns US macro correctly with identical behavior across backends."""
        ret = self.rng.randn(60, self.canonical_nodes) * 0.01

        f_t = TemporalGATLeadLagForecaster(market="KOSPI", config=TemporalGATConfig(market="KOSPI", use_torch=True, seed=42)) if _TORCH_AVAILABLE else None
        f_n = TemporalGATLeadLagForecaster(market="KOSPI", config=TemporalGATConfig(market="KOSPI", use_torch=False, seed=42))

        res_n = f_n.predict_drift(input_tensor=ret, is_krx=True)
        self.assertTrue(np.all(np.isfinite(res_n.horizons["1s"].expected_drift_bps)))

        if f_t is not None:
            res_t = f_t.predict_drift(input_tensor=ret, is_krx=True)
            w_diff = np.max(np.abs(res_t.impulse_flow.attention_weights - res_n.impulse_flow.attention_weights))
            self.assertLess(w_diff, 1e-6)

    def test_tc12_flow_vector_conservation_invariant(self) -> None:
        """TC12: Sum of net centrality flow vectors across all 25 nodes is strictly 0.000000."""
        ret = self.rng.randn(60, self.canonical_nodes) * 0.015

        for use_torch in (True, False) if _TORCH_AVAILABLE else (False,):
            f = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=use_torch, seed=42))
            res = f.predict_drift(input_tensor=ret)

            net_centrality = res.impulse_flow.net_lead_lag_centrality
            net_sum = float(np.sum(net_centrality))
            self.assertAlmostEqual(
                net_sum,
                0.0,
                places=5,
                msg=f"Net impulse flow conservation violated: sum = {net_sum}",
            )

    def test_tc13_variance_monotonicity_invariant(self) -> None:
        """TC13: Variance monotonicity strictly preserved: Var(100ms) <= Var(1s) <= Var(5s) <= Var(1m)."""
        ret = self.rng.randn(60, self.canonical_nodes) * 0.01

        for use_torch in (True, False) if _TORCH_AVAILABLE else (False,):
            f = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=use_torch, seed=42))
            res = f.predict_drift(input_tensor=ret)

            h_100ms = res.horizons["100ms"]
            h_1s = res.horizons["1s"]
            h_5s = res.horizons["5s"]
            h_1m = res.horizons["1m"]

            var_100ms = h_100ms.epistemic_uncertainty**2 + h_100ms.aleatoric_uncertainty**2
            var_1s = h_1s.epistemic_uncertainty**2 + h_1s.aleatoric_uncertainty**2
            var_5s = h_5s.epistemic_uncertainty**2 + h_5s.aleatoric_uncertainty**2
            var_1m = h_1m.epistemic_uncertainty**2 + h_1m.aleatoric_uncertainty**2

            self.assertTrue(np.all(var_100ms <= var_1s + 1e-8))
            self.assertTrue(np.all(var_1s <= var_5s + 1e-8))
            self.assertTrue(np.all(var_5s <= var_1m + 1e-8))

    def test_tc14_downstream_interfaces_contract_integrity(self) -> None:
        """TC14: downstream get_expected_returns, get_uncertainty_penalties, and get_leland_buffer_multiplier work correctly."""
        ret = self.rng.randn(60, self.canonical_nodes) * 0.01
        f = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=False, seed=42))
        res = f.predict_drift(input_tensor=ret)

        returns_dict = res.get_expected_returns(horizon="1m")
        penalties_dict = res.get_uncertainty_penalties(horizon="1m")

        self.assertEqual(len(returns_dict), self.canonical_nodes)
        self.assertEqual(len(penalties_dict), self.canonical_nodes)

        for node in ALL_CANONICAL_NODES:
            self.assertIn(node, returns_dict)
            self.assertIn(node, penalties_dict)
            mult = res.get_leland_buffer_multiplier(node)
            self.assertGreaterEqual(mult, 1.0)
            self.assertLessEqual(mult, 4.0)


if __name__ == "__main__":
    unittest.main()
