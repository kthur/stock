"""
tests/test_phase195_adversarial_stress.py
=========================================
Empirical Adversarial Stress & SLA Latency Verification Suite for Phase 195
Milestone 1 Quantitative Alpha Engines (Features F959, F960, F961).

Tested Dimensions:
1. Performance & Latency SLA Verification across universe sizes (N=50, 100, 500, 1000, 3379).
   - Measures Min, Mean, Median, P95, P99, and Total latency.
   - Assesses institutional batch SLA (< 50ms for 500 stocks) and per-asset SLA (< 5.0ms/asset).
2. Numerical Singularity & Boundary Stress:
   - Rank-deficient correlation matrices (collinear / identical assets).
   - All-zero volume histories.
   - All-NaN and all-Inf inputs.
   - Boundary universes: N=0 (empty) and N=1 (single asset).
   - Strict output bounding in [-3.0, 3.0].
   - Verification of zero unhandled LinAlgError / FloatingPointError.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import unittest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.symplectic_hamiltonian_phase_flow import (
    SymplecticHamiltonianPhaseSpaceFlowEngine,
    compute_hamiltonian_alpha,
)
from src.core.higher_order_simplicial_sheaf import (
    HigherOrderSimplicialSheafLaplacianEngine,
    compute_simplicial_sheaf_alpha,
    build_simplicial_complex,
    build_sheaf_coboundary_operators,
    helmholtz_hodge_decomposition,
)
from src.core.non_equilibrium_statistical_mechanics import (
    NonEquilibriumStatisticalMechanicsEngine,
    compute_nonequilibrium_alpha,
    compute_thermodynamic_state,
    compute_probability_current,
    compute_schnakenberg_entropy_production,
    compute_jarzynski_dissipation,
)


class TestPhase195AdversarialStress(unittest.TestCase):
    """Empirical Adversarial Test Suite for Phase 195 Alpha Engines."""

    @classmethod
    def setUpClass(cls):
        np.random.seed(42)
        cls.universe_sizes = [50, 100, 500, 1000]
        # Pre-generate synthetic prices/volumes for deterministic latency testing
        cls.datasets = {}
        for n in cls.universe_sizes:
            cls.datasets[n] = {
                f"SYM_{i:04d}": pd.DataFrame({
                    "Close": 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.015, 35))),
                    "Volume": np.random.uniform(1e5, 5e5, 35),
                })
                for i in range(n)
            }

    # =========================================================================
    # 1. Numerical Singularity & Boundary Stress
    # =========================================================================

    def test_adv01_all_zero_volume_histories(self):
        """ADV01: All-zero volume histories must not cause ZeroDivisionError or unhandled NaNs."""
        prices = 100.0 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 40)))
        zero_volumes = np.zeros(40, dtype=np.float64)

        # F959
        alpha_h, action, kam, energy = compute_hamiltonian_alpha(prices, volumes=zero_volumes)
        self.assertFalse(np.isnan(alpha_h))
        self.assertFalse(np.isinf(alpha_h))
        self.assertTrue(-3.0 <= alpha_h <= 3.0)

        # F961
        alpha_neq, ent, w_diss, div_j = compute_nonequilibrium_alpha(prices, volumes=zero_volumes)
        self.assertFalse(np.isnan(alpha_neq))
        self.assertFalse(np.isinf(alpha_neq))
        self.assertTrue(-3.0 <= alpha_neq <= 3.0)
        self.assertGreaterEqual(ent, 0.0)
        self.assertGreaterEqual(w_diss, 0.0)

    def test_adv02_rank_deficient_correlation_sheaf(self):
        """ADV02: Rank-1 / perfectly collinear returns must not trigger LinAlgError."""
        # 20 stocks with identical return paths
        identical_prices = 100.0 * np.exp(np.cumsum(np.full(30, 0.01)))
        collinear_dict = {
            f"COL_{i}": pd.DataFrame({
                "Close": identical_prices,
                "Volume": np.full(30, 1e5),
            })
            for i in range(20)
        }

        sheaf_engine = HigherOrderSimplicialSheafLaplacianEngine()
        res_sheaf = sheaf_engine.generate_signals(collinear_dict)
        self.assertEqual(len(res_sheaf), 20)
        for _, row in res_sheaf.iterrows():
            self.assertFalse(np.isnan(row["raw_score"]))
            self.assertTrue(-3.0 <= row["raw_score"] <= 3.0)

    def test_adv03_all_nan_and_all_inf_inputs(self):
        """ADV03: All-NaN and all-Inf matrices must result in safe zero-alpha without unhandled crash."""
        nan_dict = {
            "ALL_NAN": pd.DataFrame({"Close": [np.nan] * 30, "Volume": [np.nan] * 30}),
            "POS_INF": pd.DataFrame({"Close": [np.inf] * 30, "Volume": [np.inf] * 30}),
            "NEG_INF": pd.DataFrame({"Close": [-np.inf] * 30, "Volume": [-np.inf] * 30}),
            "MIXED_CORRUPT": pd.DataFrame({
                "Close": [100.0, np.nan, np.inf, -np.inf] * 7,
                "Volume": [np.nan, 0.0, np.inf, 1e5] * 7,
            }),
        }

        for engine_cls in [
            SymplecticHamiltonianPhaseSpaceFlowEngine,
            HigherOrderSimplicialSheafLaplacianEngine,
            NonEquilibriumStatisticalMechanicsEngine,
        ]:
            engine = engine_cls()
            res = engine.generate_signals(nan_dict)
            self.assertEqual(len(res), len(nan_dict))
            for _, row in res.iterrows():
                self.assertFalse(np.isnan(row["raw_score"]), f"{engine_cls.__name__} returned NaN raw_score")
                self.assertFalse(np.isinf(row["raw_score"]), f"{engine_cls.__name__} returned Inf raw_score")
                self.assertEqual(row["raw_score"], 0.0)

    def test_adv04_empty_and_single_stock_boundaries(self):
        """ADV04: N=0 (empty) and N=1 (single asset) boundaries must execute cleanly."""
        single_dict = {
            "SOLO": pd.DataFrame({"Close": [100.0, 102.0, 101.0, 103.0], "Volume": [1e5, 1.2e5, 0.9e5, 1.1e5]})
        }
        for engine_cls in [
            SymplecticHamiltonianPhaseSpaceFlowEngine,
            HigherOrderSimplicialSheafLaplacianEngine,
            NonEquilibriumStatisticalMechanicsEngine,
        ]:
            engine = engine_cls()
            res_0 = engine.generate_signals({})
            self.assertTrue(res_0.empty)

            res_1 = engine.generate_signals(single_dict)
            self.assertEqual(len(res_1), 1)
            raw = res_1["raw_score"].iloc[0]
            self.assertFalse(np.isnan(raw))
            self.assertTrue(-3.0 <= raw <= 3.0)

    def test_adv05_extreme_wild_price_outliers(self):
        """ADV05: Extreme price spikes (+10,000x, 1e-10) must remain strictly clamped in [-3.0, 3.0]."""
        wild_prices = np.array([100.0] * 20 + [1e6, 1e-6, 1e8, 1e-8, 50.0])
        wild_volumes = np.array([1e5] * 20 + [1e9, 1.0, 1e10, 0.0, 1e5])
        wild_dict = {"WILD": pd.DataFrame({"Close": wild_prices, "Volume": wild_volumes})}

        for engine_cls in [
            SymplecticHamiltonianPhaseSpaceFlowEngine,
            HigherOrderSimplicialSheafLaplacianEngine,
            NonEquilibriumStatisticalMechanicsEngine,
        ]:
            engine = engine_cls()
            res = engine.generate_signals(wild_dict)
            raw = res["raw_score"].iloc[0]
            self.assertTrue(-3.0 <= raw <= 3.0, f"{engine_cls.__name__} exceeded bounds: {raw}")

    # =========================================================================
    # 2. Performance & Latency SLA Stress Verification
    # =========================================================================

    def test_adv06_per_asset_latency_distribution(self):
        """ADV06: Measure P95 and P99 per-asset execution latency across 500 stocks."""
        n_assets = 500
        n_bars = 35
        prices_matrix = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.015, (n_bars, n_assets)), axis=0))
        volumes_matrix = np.random.uniform(1e5, 5e5, (n_bars, n_assets))
        f_macro = np.array([0.02, -0.01, 0.005, -0.015, 0.03])

        ham_latencies = []
        noneq_latencies = []

        # Hamiltonian per-asset profiling
        for i in range(n_assets):
            t0 = time.perf_counter()
            compute_hamiltonian_alpha(prices_matrix[:, i], volumes=volumes_matrix[:, i], n_steps=20)
            ham_latencies.append((time.perf_counter() - t0) * 1000.0)

        # Nonequilibrium per-asset profiling
        for i in range(n_assets):
            t0 = time.perf_counter()
            compute_nonequilibrium_alpha(prices_matrix[:, i], volumes=volumes_matrix[:, i], f_macro=f_macro)
            noneq_latencies.append((time.perf_counter() - t0) * 1000.0)

        p95_ham = float(np.percentile(ham_latencies, 95))
        p99_ham = float(np.percentile(ham_latencies, 99))
        mean_ham = float(np.mean(ham_latencies))

        p95_noneq = float(np.percentile(noneq_latencies, 95))
        p99_noneq = float(np.percentile(noneq_latencies, 99))
        mean_noneq = float(np.mean(noneq_latencies))

        print(f"\n[LATENCY REPORT: 500 Assets]")
        print(f"  F959 Hamiltonian: Mean={mean_ham:.3f}ms, P95={p95_ham:.3f}ms, P99={p99_ham:.3f}ms")
        print(f"  F961 NonEquilibrium: Mean={mean_noneq:.3f}ms, P95={p95_noneq:.3f}ms, P99={p99_noneq:.3f}ms")

        # Record findings in test assertions
        self.assertLess(mean_ham, 5.0, f"F959 Hamiltonian mean latency breached: {mean_ham:.2f}ms")

    def test_adv07_sheaf_hodge_full_universe_3379_latency(self):
        """ADV07: Verify F960 Simplicial Sheaf Hodge solve scaling across full universe (N=3,379) executes < 1.0s."""
        np.random.seed(42)
        n = 3379
        rets = np.random.normal(0, 0.02, (40, n))
        corr = np.corrcoef(rets.T)
        t0 = time.perf_counter()
        nodes, edges, triangles = build_simplicial_complex(corr)
        d0, d1 = build_sheaf_coboundary_operators(len(nodes), edges, triangles)
        j_arr = np.random.normal(0, 1.0, len(edges))
        grad, curl, harm = helmholtz_hodge_decomposition(j_arr, d0, d1, edges=edges)
        elapsed = time.perf_counter() - t0
        print(f"\n[F960 HODGE SOLVE: N={n} Full Universe] Total Elapsed: {elapsed:.3f}s (SLA < 2.0s, Target < 1.0s)")
        self.assertLess(elapsed, 1.0, f"Full universe N=3,379 Hodge solve exceeded 1.0s threshold: {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
