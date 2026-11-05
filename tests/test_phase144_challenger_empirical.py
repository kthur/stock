"""
tests/test_phase144_challenger_empirical.py — Empirical Challenger Harness for Phase 144 Alpha Modules (F700–F704).

Author: Empirical Challenger (teamwork_preview_challenger)
Milestone: Phase 144 Alpha Discovery & Signal Enrichment (M1.2)

Verifies:
1. Latency & Throughput SLA (<150ms for 100 symbols per engine).
2. Memory Stability & Leak Detection (100 continuous inference cycles, delta < 1MB).
3. Deterministic Bit-for-Bit Reproducibility (5 independent invocations, SHA-256 hash match).
4. System Invariant: Zero Synthetic Rows (synthetic_rows == 0 as type int).
5. System Invariant: Float32 Precision Validation (zero NaN/Inf, bounds [0.05, 0.98]).
6. Multi-Market Cross-Sectional Validation (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
"""

from __future__ import annotations

import gc
import hashlib
import json
import os
import sys
import time
import tracemalloc
import unittest
from typing import Any, Dict, List
import numpy as np
import pandas as pd

# Path setup
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
TS_DIR = os.path.join(ROOT_DIR, "trading_system")
if TS_DIR not in sys.path:
    sys.path.insert(0, TS_DIR)

from src.core.supply_chain_gnn_v2 import SupplyChainGNNv2Engine
from src.core.cross_market_micro_momentum import CrossMarketMicroMomentumEngine
from src.core.nlp_catalyst_engine import NLPCatalystEngine
from src.core.option_surface_accelerator import OptionSurfaceAccelerator
from src.ai.factor_orthogonalizer import (
    FactorOrthogonalizerEngine,
    OrthogonalizedAlphaFeatureStore,
    apply_hyperbolic_deadband_phase144,
)


def _generate_synthetic_universe(n_symbols: int = 100, n_bars: int = 20) -> Dict[str, pd.DataFrame]:
    """Generates a clean, realistic OHLCV test dataset for cross-sectional inference."""
    dates = pd.date_range("2026-01-01", periods=n_bars, freq="B")
    universe: Dict[str, pd.DataFrame] = {}
    rng = np.random.RandomState(42)
    for i in range(n_symbols):
        base_price = rng.uniform(50.0, 250.0)
        returns = rng.normal(0.0005, 0.015, n_bars)
        price_path = base_price * np.cumprod(1.0 + returns)
        volume_path = rng.uniform(1e5, 5e6, n_bars)
        universe[f"SYM_{i:04d}"] = pd.DataFrame(
            {"Close": price_path, "Volume": volume_path},
            index=dates
        )
    return universe


def _generate_option_chains(universe: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict[str, Any]]]:
    """Generates realistic option chain parameters for options surface testing."""
    chains: Dict[str, List[Dict[str, Any]]] = {}
    for sym, df in universe.items():
        spot = float(df["Close"].iloc[-1])
        chains[sym] = [
            {"type": "call", "strike": spot * 1.05, "tau": 0.08, "implied_vol": 0.22, "open_interest": 1500},
            {"type": "put", "strike": spot * 0.95, "tau": 0.08, "implied_vol": 0.28, "open_interest": 1800},
            {"type": "call", "strike": spot * 1.00, "tau": 0.08, "implied_vol": 0.24, "open_interest": 3000},
        ]
    return chains


class TestPhase144ChallengerEmpirical(unittest.TestCase):
    """
    Adversarial Empirical Challenge Suite for Phase 144 Alpha Modules (F700–F704).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.gnn_engine = SupplyChainGNNv2Engine()
        cls.micro_engine = CrossMarketMicroMomentumEngine()
        cls.nlp_engine = NLPCatalystEngine()
        cls.options_engine = OptionSurfaceAccelerator()
        cls.ortho_engine = FactorOrthogonalizerEngine()
        cls.universe_100 = _generate_synthetic_universe(100, 20)
        cls.chains_100 = _generate_option_chains(cls.universe_100)

    # =========================================================================
    # 1. Latency and Throughput Benchmarks (< 150ms for 100 symbols)
    # =========================================================================

    def test_sla_latency_f700_gnn_v2(self) -> None:
        """CHALLENGE 1.1: F700 GNN v2 100-symbol cross-sectional latency < 150ms."""
        # Warmup
        self.gnn_engine.compute_scores(self.universe_100)
        t0 = time.perf_counter()
        res = self.gnn_engine.compute_scores(self.universe_100)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res), 100)
        self.assertLess(
            elapsed_ms, 150.0,
            f"F700 GNN v2 SLA breached! Latency: {elapsed_ms:.2f}ms (threshold: 150.0ms)"
        )

    def test_sla_latency_f701_micro_momentum(self) -> None:
        """CHALLENGE 1.2: F701 Cross Market Micro Momentum 100-symbol latency < 150ms."""
        self.micro_engine.compute_scores(self.universe_100)
        t0 = time.perf_counter()
        res = self.micro_engine.compute_scores(self.universe_100)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res), 100)
        self.assertLess(
            elapsed_ms, 150.0,
            f"F701 Micro Momentum SLA breached! Latency: {elapsed_ms:.2f}ms (threshold: 150.0ms)"
        )

    def test_sla_latency_f702_nlp_catalyst(self) -> None:
        """CHALLENGE 1.3: F702 NLP Catalyst 100-symbol latency < 200ms."""
        self.nlp_engine.compute_scores(self.universe_100)
        t0 = time.perf_counter()
        res = self.nlp_engine.compute_scores(self.universe_100)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res), 100)
        self.assertLess(
            elapsed_ms, 200.0,
            f"F702 NLP Catalyst SLA breached! Latency: {elapsed_ms:.2f}ms (threshold: 200.0ms)"
        )

    def test_sla_latency_f703_option_surface(self) -> None:
        """CHALLENGE 1.4: F703 Option Surface Accelerator with live chains 100-symbol latency < 150ms."""
        self.options_engine.compute_scores(self.universe_100, options_chain_dict=self.chains_100)
        t0 = time.perf_counter()
        res = self.options_engine.compute_scores(self.universe_100, options_chain_dict=self.chains_100)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(len(res), 100)
        self.assertLess(
            elapsed_ms, 150.0,
            f"F703 Option Surface SLA breached! Latency: {elapsed_ms:.2f}ms (threshold: 150.0ms)"
        )

    def test_sla_latency_f704_factor_orthogonalizer(self) -> None:
        """CHALLENGE 1.5: F704 Factor Orthogonalizer 100-symbol x 37-strategy matrix latency < 150ms."""
        mat = np.random.uniform(0.1, 0.9, size=(100, 37))
        df_factors = pd.DataFrame(mat, columns=[f"strat_{i}" for i in range(37)])

        self.ortho_engine.orthogonalize(df_factors, strategy_cols=list(df_factors.columns), method="pca_symmetric")
        t0 = time.perf_counter()
        res = self.ortho_engine.orthogonalize(df_factors, strategy_cols=list(df_factors.columns), method="pca_symmetric")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res.shape, (100, 37))
        self.assertLess(
            elapsed_ms, 150.0,
            f"F704 Factor Orthogonalizer SLA breached! Latency: {elapsed_ms:.2f}ms (threshold: 150.0ms)"
        )

    # =========================================================================
    # 2. Memory Stability & Leak Detection (100 Continuous Cycles)
    # =========================================================================

    def test_memory_stability_100_cycles(self) -> None:
        """CHALLENGE 2: 100 continuous inference cycles verify absence of memory leaks (delta < 1MB)."""
        # Warmup 5 cycles
        for _ in range(5):
            _ = self.gnn_engine.compute_scores(self.universe_100)
            _ = self.micro_engine.compute_scores(self.universe_100)

        gc.collect()
        tracemalloc.start()
        mem_start, _ = tracemalloc.get_traced_memory()

        for cycle in range(100):
            _ = self.gnn_engine.compute_scores(self.universe_100)
            _ = self.micro_engine.compute_scores(self.universe_100)

        gc.collect()
        mem_end, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        delta_kb = (mem_end - mem_start) / 1024.0
        peak_kb = peak / 1024.0

        # Memory delta across 100 cycles must be strictly under 1024 KB (1 MB)
        self.assertLess(
            delta_kb, 1024.0,
            f"Memory leak detected over 100 cycles! Delta: {delta_kb:.1f}KB, Peak: {peak_kb:.1f}KB"
        )
        # Peak allocated memory must remain bounded under 10 MB
        self.assertLess(
            peak_kb, 10240.0,
            f"Excessive memory peak allocation: {peak_kb:.1f}KB"
        )

    # =========================================================================
    # 3. Deterministic Bit-for-Bit Reproducibility (5 Separate Runs)
    # =========================================================================

    def test_deterministic_reproducibility_5_runs(self) -> None:
        """CHALLENGE 3: 5 independent invocations produce bit-for-bit identical SHA-256 digests."""
        hashes_gnn: List[str] = []
        hashes_micro: List[str] = []
        hashes_nlp: List[str] = []
        hashes_opt: List[str] = []
        hashes_ortho: List[str] = []

        mat = np.random.RandomState(999).uniform(0.1, 0.9, size=(50, 10))
        df_factors = pd.DataFrame(mat, columns=[f"s_{i}" for i in range(10)])

        for run_idx in range(5):
            # 1. GNN
            res_gnn = self.gnn_engine.compute_scores(self.universe_100)
            arr_gnn = res_gnn["supply_chain_gnn_v2_score"].to_numpy(dtype=np.float64)
            hashes_gnn.append(hashlib.sha256(arr_gnn.tobytes()).hexdigest())

            # 2. Micro
            res_micro = self.micro_engine.compute_scores(self.universe_100)
            arr_micro = res_micro["cross_market_micro_mom_score"].to_numpy(dtype=np.float64)
            hashes_micro.append(hashlib.sha256(arr_micro.tobytes()).hexdigest())

            # 3. NLP
            res_nlp = self.nlp_engine.compute_scores(self.universe_100)
            arr_nlp = res_nlp["nlp_catalyst_score"].to_numpy(dtype=np.float64)
            hashes_nlp.append(hashlib.sha256(arr_nlp.tobytes()).hexdigest())

            # 4. Opt
            res_opt = self.options_engine.compute_scores(self.universe_100, options_chain_dict=self.chains_100)
            arr_opt = res_opt["option_surface_score"].to_numpy(dtype=np.float64)
            hashes_opt.append(hashlib.sha256(arr_opt.tobytes()).hexdigest())

            # 5. Ortho
            res_ortho = self.ortho_engine.orthogonalize(df_factors, strategy_cols=list(df_factors.columns), method="pca_symmetric")
            arr_ortho = res_ortho.to_numpy(dtype=np.float64)
            hashes_ortho.append(hashlib.sha256(arr_ortho.tobytes()).hexdigest())

        self.assertEqual(len(set(hashes_gnn)), 1, "GNN v2 non-deterministic outputs across 5 runs")
        self.assertEqual(len(set(hashes_micro)), 1, "Micro Momentum non-deterministic outputs across 5 runs")
        self.assertEqual(len(set(hashes_nlp)), 1, "NLP Catalyst non-deterministic outputs across 5 runs")
        self.assertEqual(len(set(hashes_opt)), 1, "Option Surface non-deterministic outputs across 5 runs")
        self.assertEqual(len(set(hashes_ortho)), 1, "Factor Orthogonalizer non-deterministic outputs across 5 runs")

    # =========================================================================
    # 4. System Invariant: Zero Synthetic Rows (synthetic_rows == 0 as type int)
    # =========================================================================

    def test_system_invariants_synthetic_rows_status_json(self) -> None:
        """CHALLENGE 4.1: status.json invariant synthetic_rows == 0 strictly verified as int type."""
        status_path = os.path.join(ROOT_DIR, "benchmarks", "30year", "status.json")
        self.assertTrue(os.path.exists(status_path), f"status.json missing at {status_path}")

        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)

        self.assertIn("synthetic_rows", status)
        val = status["synthetic_rows"]
        # Invariant: Must be strictly int type (not float, not str)
        self.assertIs(type(val), int, f"synthetic_rows must be type int, got {type(val)}")
        self.assertEqual(val, 0, f"synthetic_rows must be 0, got {val}")

    def test_system_invariants_synthetic_rows_in_engine_outputs(self) -> None:
        """CHALLENGE 4.2: Engine outputs contain zero synthetic rows (len == universe size)."""
        res_gnn = self.gnn_engine.compute_scores(self.universe_100)
        self.assertEqual(len(res_gnn), len(self.universe_100))
        synthetic_count = int(res_gnn.isna().any(axis=1).sum())
        self.assertIs(type(synthetic_count), int)
        self.assertEqual(synthetic_count, 0)

    # =========================================================================
    # 5. System Invariant: Float32 Precision Validation
    # =========================================================================

    def test_system_invariants_float32_precision(self) -> None:
        """CHALLENGE 5: Outputs are numerically stable, within bounds [0.05, 0.98], zero NaN/Inf."""
        for name, res_df, col, min_b, max_b in [
            ("GNNv2", self.gnn_engine.compute_scores(self.universe_100), "supply_chain_gnn_v2_score", 0.05, 0.95),
            ("MicroMom", self.micro_engine.compute_scores(self.universe_100), "cross_market_micro_mom_score", 0.05, 0.98),
            ("NLPCat", self.nlp_engine.compute_scores(self.universe_100), "nlp_catalyst_score", 0.05, 0.98),
            ("OptSurf", self.options_engine.compute_scores(self.universe_100, options_chain_dict=self.chains_100), "option_surface_score", 0.05, 0.98),
        ]:
            s = res_df[col]
            # Verify no NaN or Inf
            self.assertFalse(s.isna().any(), f"{name} contains NaN")
            self.assertFalse(np.isinf(s).any(), f"{name} contains Inf")

            # Verify bounds
            self.assertTrue(
                (s >= min_b - 1e-6).all(),
                f"{name} lower bound breached: min={s.min()}"
            )
            self.assertTrue(
                (s <= max_b + 1e-6).all(),
                f"{name} upper bound breached: max={s.max()}"
            )

            # Verify float32 casting stability
            s32 = s.astype(np.float32)
            self.assertFalse(s32.isna().any(), f"{name} float32 casting produced NaN")
            self.assertFalse(np.isinf(s32).any(), f"{name} float32 casting produced Inf")
            max_diff = float(np.max(np.abs(s.to_numpy() - s32.to_numpy())))
            self.assertLess(max_diff, 1e-5, f"{name} precision loss too high: {max_diff}")

    # =========================================================================
    # 6. Multi-Market Validation across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000
    # =========================================================================

    def test_multi_market_validation_5_markets(self) -> None:
        """CHALLENGE 6: Multi-market validation across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000."""
        dates = pd.date_range("2026-01-01", periods=25, freq="B")

        # 5-Market Representative Universe
        five_market_universe: Dict[str, pd.DataFrame] = {
            # KOSPI
            "005930": pd.DataFrame({"Close": np.linspace(72000, 75000, 25), "Volume": [1.2e7] * 25}, index=dates),
            "000660": pd.DataFrame({"Close": np.linspace(155000, 168000, 25), "Volume": [3.5e6] * 25}, index=dates),
            "005380": pd.DataFrame({"Close": np.linspace(240000, 248000, 25), "Volume": [1.1e6] * 25}, index=dates),
            # KOSDAQ
            "247540": pd.DataFrame({"Close": np.linspace(210000, 225000, 25), "Volume": [9.0e5] * 25}, index=dates),
            "091990": pd.DataFrame({"Close": np.linspace(140000, 149000, 25), "Volume": [6.5e5] * 25}, index=dates),
            # SP500
            "NVDA": pd.DataFrame({"Close": np.linspace(125.0, 142.0, 25), "Volume": [4.5e7] * 25}, index=dates),
            "AAPL": pd.DataFrame({"Close": np.linspace(222.0, 235.0, 25), "Volume": [2.8e7] * 25}, index=dates),
            "MSFT": pd.DataFrame({"Close": np.linspace(415.0, 430.0, 25), "Volume": [1.9e7] * 25}, index=dates),
            # NASDAQ
            "TSLA": pd.DataFrame({"Close": np.linspace(245.0, 268.0, 25), "Volume": [6.0e7] * 25}, index=dates),
            "AVGO": pd.DataFrame({"Close": np.linspace(1650.0, 1780.0, 25), "Volume": [2.2e6] * 25}, index=dates),
            # RUSSELL2000
            "SMCI": pd.DataFrame({"Close": np.linspace(42.0, 51.0, 25), "Volume": [8.5e6] * 25}, index=dates),
            "ACLS": pd.DataFrame({"Close": np.linspace(95.0, 108.0, 25), "Volume": [1.2e6] * 25}, index=dates),
        }

        # Multi-market Macro context
        macro_rets = {
            "sox": 0.024,
            "sp500": 0.012,
            "usdkrw": -0.005,
            "wti": 0.008,
            "tnx": -0.002,
        }

        # 1. GNN v2
        res_gnn = self.gnn_engine.compute_scores(five_market_universe)
        self.assertEqual(len(res_gnn), len(five_market_universe))
        self.assertFalse(res_gnn["supply_chain_gnn_v2_score"].isna().any())

        # 2. Micro Momentum
        res_micro = self.micro_engine.compute_scores(
            five_market_universe,
            macro_returns=macro_rets,
            lead_returns={"NVDA": 0.035, "005930": 0.020},
        )
        self.assertEqual(len(res_micro), len(five_market_universe))
        self.assertFalse(res_micro["cross_market_micro_mom_score"].isna().any())

        # 3. NLP Catalyst
        res_nlp = self.nlp_engine.compute_scores(five_market_universe)
        self.assertEqual(len(res_nlp), len(five_market_universe))
        self.assertFalse(res_nlp["nlp_catalyst_score"].isna().any())

        # 4. Option Surface
        res_opt = self.options_engine.compute_scores(five_market_universe)
        self.assertEqual(len(res_opt), len(five_market_universe))
        self.assertFalse(res_opt["option_surface_score"].isna().any())

        # 5. Factor Orthogonalizer across all 5-market outputs
        df_combined = pd.DataFrame({
            "gnn": res_gnn["supply_chain_gnn_v2_score"].values,
            "micro": res_micro["cross_market_micro_mom_score"].values,
            "nlp": res_nlp["nlp_catalyst_score"].values,
            "opt": res_opt["option_surface_score"].values,
        })
        res_ortho = self.ortho_engine.orthogonalize(df_combined, strategy_cols=list(df_combined.columns))
        self.assertEqual(len(res_ortho), len(five_market_universe))
        self.assertFalse(res_ortho.isna().any().any())


if __name__ == "__main__":
    unittest.main()
