r"""
trading_system/scripts/benchmark_phase119_gat_latency_determinism.py
===================================================================
Standalone Empirical Benchmark and Determinism Verification Harness
for TemporalGATLeadLagForecaster (Feature F565, Phase 119 Milestone 1).

Author: Challenger 2 (empirical_challenger)
Date: 2026-10-17
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TRADING_SYS_DIR = SCRIPT_DIR.parent

for p in (str(TRADING_SYS_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

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


def run_latency_benchmark(
    n_runs: int = 500,
    warmup: int = 20,
) -> Dict[str, Any]:
    """Runs latency benchmarks across all 5 markets for PyTorch and NumPy backends."""
    markets = ["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]
    backends = ["numpy"]
    if _TORCH_AVAILABLE:
        backends.insert(0, "torch")

    rng = np.random.RandomState(42)
    ret = rng.randn(60, NUM_CANONICAL_NODES) * 0.01

    results = {}

    for backend in backends:
        use_torch = (backend == "torch")
        results[backend] = {}

        for market in markets:
            config = TemporalGATConfig(market=market, use_torch=use_torch, seed=42)
            forecaster = TemporalGATLeadLagForecaster(market=market, config=config)

            # Warmup
            for _ in range(warmup):
                forecaster.predict_drift(input_tensor=ret)

            latencies_ms = []
            for _ in range(n_runs):
                t0 = time.perf_counter_ns()
                res = forecaster.predict_drift(input_tensor=ret)
                t1 = time.perf_counter_ns()
                latencies_ms.append((t1 - t0) / 1e6)

            lat_arr = np.array(latencies_ms)
            results[backend][market] = {
                "mean_ms": float(np.mean(lat_arr)),
                "median_ms": float(np.median(lat_arr)),
                "std_ms": float(np.std(lat_arr)),
                "p95_ms": float(np.percentile(lat_arr, 95)),
                "p99_ms": float(np.percentile(lat_arr, 99)),
                "min_ms": float(np.min(lat_arr)),
                "max_ms": float(np.max(lat_arr)),
                "pass_sla_5ms": bool(np.mean(lat_arr) < 5.0),
                "p95_under_5ms": bool(np.percentile(lat_arr, 95) < 5.0),
                "sla_pass_rate_pct": float(np.mean(lat_arr < 5.0) * 100.0),
            }

    return results


def run_cross_backend_numerical_parity() -> Dict[str, Any]:
    """Evaluates cross-backend numerical consistency across seeds and input distributions."""
    if not _TORCH_AVAILABLE:
        return {"torch_available": False}

    seeds = [42, 100, 777, 2026, 9999]
    input_scenarios = {
        "gaussian_normal": lambda rng: rng.randn(60, 25) * 0.01,
        "fat_tail_student_t": lambda rng: rng.standard_t(df=3, size=(60, 25)) * 0.01,
        "flash_crash_shock": lambda rng: _make_crash_scenario(rng),
        "extreme_surge_shock": lambda rng: _make_surge_scenario(rng),
        "zero_flatline": lambda rng: np.zeros((60, 25), dtype=np.float64),
    }

    parity_results = {}

    for scenario_name, scenario_fn in input_scenarios.items():
        parity_results[scenario_name] = {}
        for seed in seeds:
            rng = np.random.RandomState(seed)
            ret = scenario_fn(rng)

            f_torch = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=True, seed=seed))
            f_numpy = TemporalGATLeadLagForecaster(config=TemporalGATConfig(use_torch=False, seed=seed))

            res_t = f_torch.predict_drift(input_tensor=ret)
            res_n = f_numpy.predict_drift(input_tensor=ret)

            w_diff = float(np.max(np.abs(res_t.impulse_flow.attention_weights - res_n.impulse_flow.attention_weights)))
            c_diff = float(np.max(np.abs(res_t.impulse_flow.net_lead_lag_centrality - res_n.impulse_flow.net_lead_lag_centrality)))
            v_diff = float(np.max(np.abs(res_t.impulse_flow.impulse_flow_vectors - res_n.impulse_flow.impulse_flow_vectors)))

            horizon_diffs = {}
            for h in ("100ms", "1s", "5s", "1m"):
                d_t = res_t.horizons[h].expected_drift_bps
                d_n = res_n.horizons[h].expected_drift_bps
                d_max_diff = float(np.max(np.abs(d_t - d_n)))
                
                # Pearson correlation
                if np.std(d_t) > 1e-12 and np.std(d_n) > 1e-12:
                    corr = float(np.corrcoef(d_t, d_n)[0, 1])
                else:
                    corr = 1.0

                # Cosine similarity
                norm_t = np.linalg.norm(d_t)
                norm_n = np.linalg.norm(d_n)
                if norm_t > 1e-12 and norm_n > 1e-12:
                    cos_sim = float(np.dot(d_t, d_n) / (norm_t * norm_n))
                else:
                    cos_sim = 1.0

                horizon_diffs[h] = {
                    "max_drift_abs_diff_bps": d_max_diff,
                    "correlation": corr,
                    "cosine_similarity": cos_sim,
                }

            parity_results[scenario_name][f"seed_{seed}"] = {
                "max_attention_weight_diff": w_diff,
                "max_centrality_diff": c_diff,
                "max_impulse_vector_diff": v_diff,
                "horizons": horizon_diffs,
            }

    return parity_results


def _make_crash_scenario(rng: np.random.RandomState) -> np.ndarray:
    ret = rng.randn(60, 25) * 0.01
    ret[-1, :] = -0.15  # 15% systemic crash
    ret[-1, 0] = -0.90  # 90% crash on SOX
    return ret


def _make_surge_scenario(rng: np.random.RandomState) -> np.ndarray:
    ret = rng.randn(60, 25) * 0.01
    ret[-1, :] = 0.20   # 20% systemic rally
    ret[-1, 8] = 10.0   # 10x spike on XLK
    return ret


def print_report(latency_res: Dict[str, Any], parity_res: Dict[str, Any]) -> None:
    """Prints formatted summary tables."""
    print("=" * 80)
    print("EMPIRICAL LATENCY SLA BENCHMARK (< 5.0ms) -- 500 PASSES PER MARKET")
    print("=" * 80)
    print(f"{'Backend':<8} | {'Market':<11} | {'Mean (ms)':<9} | {'Median (ms)':<11} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'Max (ms)':<9} | {'Pass Rate':<10}")
    print("-" * 88)

    for backend, mkts in latency_res.items():
        for mkt, stats in mkts.items():
            print(
                f"{backend:<8} | {mkt:<11} | {stats['mean_ms']:<9.4f} | {stats['median_ms']:<11.4f} | "
                f"{stats['p95_ms']:<9.4f} | {stats['p99_ms']:<9.4f} | {stats['max_ms']:<9.4f} | "
                f"{stats['sla_pass_rate_pct']:<9.1f}%"
            )
        print("-" * 88)

    print("\n" + "=" * 80)
    print("CROSS-BACKEND NUMERICAL PARITY (PYTORCH vs PURE NUMPY)")
    print("=" * 80)
    if not parity_res.get("torch_available", True):
        print("PyTorch not available for parity check.")
        return

    for scenario, seeds in parity_res.items():
        print(f"\nScenario: {scenario}")
        print(f"{'Seed':<10} | {'Max Attn Diff':<15} | {'Max Cent Diff':<15} | {'1s Drift Max Diff':<18} | {'1s Cosine Sim':<15}")
        print("-" * 80)
        for seed_key, stats in seeds.items():
            h1s = stats["horizons"]["1s"]
            print(
                f"{seed_key:<10} | {stats['max_attention_weight_diff']:<15.2e} | "
                f"{stats['max_centrality_diff']:<15.2e} | "
                f"{h1s['max_drift_abs_diff_bps']:<18.2e} | "
                f"{h1s['cosine_similarity']:<15.9f}"
            )


if __name__ == "__main__":
    print("Starting Phase 119 GAT Forecaster Benchmark Harness...")
    lat_results = run_latency_benchmark(n_runs=500, warmup=20)
    parity_results = run_cross_backend_numerical_parity()
    print_report(lat_results, parity_results)
