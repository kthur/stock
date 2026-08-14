"""
tests/run_m1_challenger_stress_benchmark.py
Deep Empirical Stress Benchmark Harness for Strategy 21 (MultiFactorNeutralizerEngine).
"""

import sys
import os
import time
import json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_system.src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine


def run_benchmark():
    engine = MultiFactorNeutralizerEngine()
    results = {}

    print("=" * 80)
    print("M1-1 CHALLENGER: EMPIRICAL STRESS & EXTREME COLLINEARITY BENCHMARK")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Test 1: Extreme Collinearity (r >= 0.9999) across Universe Sizes
    # -------------------------------------------------------------------------
    print("\n[Test 1] Extreme Factor Collinearity Matrix (r >= 0.9999)...")
    collinearity_results = []
    for n in [10, 50, 100, 500, 1000, 3379]:
        np.random.seed(42 + n)
        base = np.random.normal(0, 1, size=n)
        cap = np.exp(25.0 + 1.5 * (base + np.random.normal(0, 0.0001, size=n)))
        per = 20.0 + 5.0 * (base + np.random.normal(0, 0.0001, size=n))
        pbr = 2.0 + 0.5 * (base + np.random.normal(0, 0.0001, size=n))
        roe = 10.0 + 2.0 * (base + np.random.normal(0, 0.0001, size=n))
        cma = 0.05 + 0.01 * (base + np.random.normal(0, 0.0001, size=n))
        mom = 0.10 + 0.05 * (base + np.random.normal(0, 0.0001, size=n))

        universe = pd.DataFrame({
            "symbol": [f"S_{i}" for i in range(n)],
            "market": np.random.choice(["KOSPI", "SP500", "KOSDAQ"], size=n),
            "market_cap": cap,
            "per": per,
            "pbr": pbr,
            "roe": roe,
            "asset_growth_yoy": cma,
            "momentum_12m": mom,
        })
        raw_score = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": base * 0.95 + np.random.normal(0, 0.05, size=n),
        })

        t0 = time.perf_counter()
        res = engine.compute_scores(universe=universe, raw_scores=raw_score)
        lat_ms = (time.perf_counter() - t0) * 1000.0

        eval_df = pd.merge(universe, res[["symbol", "factor_neutralized_score"]], on="symbol").dropna()
        score = eval_df["factor_neutralized_score"]

        # Check if score has non-zero variance; if constant (e.g. 0.5 fallback), correlation is undefined / 0
        if score.std() > 1e-6:
            corrs = {
                "size": float(abs(score.corr(np.log(eval_df["market_cap"].clip(lower=1.0))))),
                "value": float(abs(score.corr(1.0 / eval_df["pbr"].clip(lower=0.01)))),
                "profit": float(abs(score.corr(eval_df["roe"]))),
                "invest": float(abs(score.corr(eval_df["asset_growth_yoy"]))),
                "momentum": float(abs(score.corr(eval_df["momentum_12m"]))),
            }
            max_rho = max(corrs.values())
        else:
            corrs = {"size": 0.0, "value": 0.0, "profit": 0.0, "invest": 0.0, "momentum": 0.0}
            max_rho = 0.0

        pass_sla = (max_rho < 0.15) and not res["factor_neutralized_score"].isna().any()

        collinearity_results.append({
            "N": n,
            "max_rho": round(max_rho, 5),
            "latency_ms": round(lat_ms, 2),
            "passed": bool(pass_sla),
            "corrs": {k: round(v, 4) for k, v in corrs.items()},
        })
        print(f"  N={n:4d}: max |rho|={max_rho:.4f} (Size:{corrs['size']:.3f}, Val:{corrs['value']:.3f}, Prof:{corrs['profit']:.3f}, Inv:{corrs['invest']:.3f}, Mom:{corrs['momentum']:.3f}), Latency={lat_ms:.2f}ms -> {'PASS' if pass_sla else 'FAIL'}")

    results["collinearity"] = collinearity_results

    # -------------------------------------------------------------------------
    # Test 2: Missing Data Gradient (0% -> 99.9% missingness across 3,379 symbols)
    # -------------------------------------------------------------------------
    print("\n[Test 2] Missing Fundamentals Gradient across 3,379 symbols...")
    missing_results = []
    for miss_pct in [0, 20, 50, 80, 90, 95, 98, 99, 99.9]:
        np.random.seed(123)
        n = 3379
        universe = pd.DataFrame({
            "symbol": [f"SYM_{i:04d}" for i in range(n)],
            "name": [f"Name_{i}" for i in range(n)],
            "market": np.random.choice(["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"], size=n),
            "market_cap": np.exp(np.random.normal(25.0, 1.5, size=n)),
            "per": np.random.uniform(5.0, 50.0, size=n),
            "pbr": np.random.uniform(0.5, 5.0, size=n),
            "roe": np.random.normal(12.0, 6.0, size=n),
            "asset_growth_yoy": np.random.normal(0.08, 0.15, size=n),
            "momentum_12m": np.random.normal(0.10, 0.25, size=n),
        })
        # Inject missingness
        if miss_pct > 0:
            rate = miss_pct / 100.0
            for col in ["per", "pbr", "roe", "asset_growth_yoy", "momentum_12m"]:
                mask = np.random.uniform(0, 1, size=n) < rate
                universe.loc[mask, col] = np.nan
            cap_mask = np.random.uniform(0, 1, size=n) < (rate * 0.95)
            universe.loc[cap_mask, "market_cap"] = np.nan

        raw_score = pd.DataFrame({
            "symbol": universe["symbol"],
            "score": np.random.uniform(0, 1, size=n),
        })

        t0 = time.perf_counter()
        res = engine.compute_scores(universe=universe, raw_scores=raw_score)
        lat_ms = (time.perf_counter() - t0) * 1000.0

        valid_count = int(res["factor_neutralized_score"].notna().sum())
        cov_pct = (valid_count / n) * 100.0
        scores_in_bounds = bool(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))

        passed = (cov_pct >= 95.0) and scores_in_bounds
        missing_results.append({
            "missing_rate_pct": miss_pct,
            "coverage_pct": round(cov_pct, 2),
            "latency_ms": round(lat_ms, 2),
            "in_bounds": scores_in_bounds,
            "passed": passed,
        })
        print(f"  Missing {miss_pct:4.1f}%: Coverage={cov_pct:.2f}% ({valid_count}/{n}), InBounds={scores_in_bounds}, Latency={lat_ms:.2f}ms -> {'PASS' if passed else 'FAIL'}")

    results["missingness"] = missing_results

    # -------------------------------------------------------------------------
    # Test 3: Zero-Variance & Constant Input Extremes
    # -------------------------------------------------------------------------
    print("\n[Test 3] Zero-Variance & Constant Input Extremes...")
    zero_var_results = []
    cases = [
        ("All 0.0 (Factors + Scores)", {"market_cap": 0.0, "per": 0.0, "pbr": 0.0, "roe": 0.0, "asset_growth_yoy": 0.0, "momentum_12m": 0.0, "score": 0.0}),
        ("All 100.0 (Factors + Scores)", {"market_cap": 100.0, "per": 100.0, "pbr": 100.0, "roe": 100.0, "asset_growth_yoy": 100.0, "momentum_12m": 100.0, "score": 100.0}),
        ("Constant Factors, Dynamic Score", {"market_cap": 1e9, "per": 15.0, "pbr": 1.5, "roe": 10.0, "asset_growth_yoy": 0.05, "momentum_12m": 0.1, "score": None}),
        ("Dynamic Factors, Constant Score (0.42)", {"score": 0.42}),
    ]

    for name, spec in cases:
        n = 100
        universe = pd.DataFrame({"symbol": [f"S_{i}" for i in range(n)], "market": "KOSPI"})
        for k in ["market_cap", "per", "pbr", "roe", "asset_growth_yoy", "momentum_12m"]:
            if k in spec and spec[k] is not None:
                universe[k] = spec[k]
            else:
                universe[k] = np.random.normal(10, 2, size=n)

        if "score" in spec and spec["score"] is not None:
            raw_scores = pd.DataFrame({"symbol": universe["symbol"], "score": spec["score"]})
        else:
            raw_scores = pd.DataFrame({"symbol": universe["symbol"], "score": np.linspace(0.1, 0.9, n)})

        res = engine.compute_scores(universe=universe, raw_scores=raw_scores)
        has_nan = bool(res["factor_neutralized_score"].isna().any())
        in_bounds = bool(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))
        passed = (not has_nan) and in_bounds

        zero_var_results.append({
            "case": name,
            "has_nan": has_nan,
            "in_bounds": in_bounds,
            "passed": passed,
        })
        print(f"  {name:38s}: HasNaN={has_nan}, InBounds={in_bounds} -> {'PASS' if passed else 'FAIL'}")

    results["zero_variance"] = zero_var_results

    # -------------------------------------------------------------------------
    # Test 4: Tiny Universes & Boundary Conditions (N=1 to 10)
    # -------------------------------------------------------------------------
    print("\n[Test 4] Tiny Universe Partitions (N=1..10, multi-market singletons)...")
    tiny_results = []
    for n in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        universe = pd.DataFrame({
            "symbol": [f"S_{i}" for i in range(n)],
            "market": "SP500",
            "market_cap": np.exp(np.linspace(20, 25, n)),
            "per": np.linspace(5, 30, n),
            "pbr": np.linspace(1, 4, n),
            "roe": np.linspace(5, 20, n),
            "asset_growth_yoy": np.linspace(0.01, 0.2, n),
            "momentum_12m": np.linspace(-0.1, 0.3, n),
            "score": np.linspace(0.1, 0.9, n) if n > 1 else 0.5,
        })
        res = engine.compute_scores(universe=universe)
        has_nan = bool(res["factor_neutralized_score"].isna().any())
        in_bounds = bool(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))
        passed = (len(res) == n) and (not has_nan) and in_bounds
        tiny_results.append({"N": n, "passed": passed, "has_nan": has_nan, "in_bounds": in_bounds})
        print(f"  N={n:2d}: Len={len(res)}, HasNaN={has_nan}, InBounds={in_bounds} -> {'PASS' if passed else 'FAIL'}")

    # Asymmetric 6-market singletons
    universe_singletons = pd.DataFrame({
        "symbol": ["KOSPI_1", "KOSDAQ_1", "KONEX_1", "SP500_1", "NASDAQ_1", "RUSSELL_1"],
        "market": ["KOSPI", "KOSDAQ", "KONEX", "SP500", "NASDAQ", "RUSSELL2000"],
        "market_cap": [1e12, 5e11, 1e10, 1e11, 2e11, 5e10],
        "per": [10.0, 15.0, 20.0, 25.0, 30.0, 12.0],
        "pbr": [1.0, 1.5, 2.0, 2.5, 3.0, 1.2],
        "roe": [12.0, 10.0, 8.0, 15.0, 18.0, 9.0],
        "asset_growth_yoy": [0.05, 0.1, 0.02, 0.08, 0.12, 0.04],
        "momentum_12m": [0.1, 0.15, -0.05, 0.2, 0.25, 0.05],
        "score": [0.6, 0.7, 0.4, 0.8, 0.9, 0.5],
    })
    res_sing = engine.compute_scores(universe=universe_singletons)
    sing_passed = (len(res_sing) == 6) and (not res_sing["factor_neutralized_score"].isna().any()) and bool(np.all(res_sing["factor_neutralized_score"] == 0.5))
    tiny_results.append({"case": "6-market singletons", "passed": sing_passed})
    print(f"  6-market Singletons: Len={len(res_sing)}, All 0.5 fallback={sing_passed} -> {'PASS' if sing_passed else 'FAIL'}")

    results["tiny_universes"] = tiny_results

    # -------------------------------------------------------------------------
    # Test 5: Extreme Outliers and Numerical Stress
    # -------------------------------------------------------------------------
    print("\n[Test 5] Extreme Numerical Outliers & Malformed Inputs...")
    n = 100
    universe = pd.DataFrame({
        "symbol": [f"S_{i}" for i in range(n)],
        "market": "KOSPI",
        "market_cap": np.exp(np.random.normal(25, 1, size=n)),
        "per": np.random.uniform(5, 30, size=n),
        "pbr": np.random.uniform(0.5, 3, size=n),
        "roe": np.random.normal(10, 5, size=n),
        "asset_growth_yoy": np.random.normal(0.05, 0.1, size=n),
        "momentum_12m": np.random.normal(0.1, 0.2, size=n),
    })
    # Inject extremes
    universe.loc[0, "market_cap"] = 1e18
    universe.loc[1, "market_cap"] = 1e-15
    universe.loc[2, "market_cap"] = -1e6
    universe.loc[3, "per"] = 1e12
    universe.loc[4, "per"] = -1e12
    universe.loc[5, "per"] = 0.000001
    universe.loc[6, "pbr"] = 1e12
    universe.loc[7, "pbr"] = -100.0
    universe.loc[8, "roe"] = -100000.0
    universe.loc[9, "roe"] = 100000.0
    universe.loc[10, "asset_growth_yoy"] = 1e9
    universe.loc[11, "asset_growth_yoy"] = -1e9
    universe.loc[12, "per"] = np.inf
    universe.loc[13, "roe"] = -np.inf

    raw_scores = pd.DataFrame({
        "symbol": universe["symbol"],
        "score": np.random.uniform(0, 1, size=n),
    })
    raw_scores.loc[0, "score"] = 1e12
    raw_scores.loc[1, "score"] = -1e12

    res = engine.compute_scores(universe=universe, raw_scores=raw_scores)
    has_nan = bool(res["factor_neutralized_score"].isna().any())
    has_inf = bool(np.isinf(res["factor_neutralized_score"].values).any())
    in_bounds = bool(np.all((res["factor_neutralized_score"] >= 0.0) & (res["factor_neutralized_score"] <= 1.0)))
    outlier_passed = (not has_nan) and (not has_inf) and in_bounds

    results["outliers"] = {
        "has_nan": has_nan,
        "has_inf": has_inf,
        "in_bounds": in_bounds,
        "passed": outlier_passed,
    }
    print(f"  Outliers: HasNaN={has_nan}, HasInf={has_inf}, InBounds={in_bounds} -> {'PASS' if outlier_passed else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Test 6: Monte Carlo 50-Seed SLA Stress Test (3,379 symbols, random contamination)
    # -------------------------------------------------------------------------
    print("\n[Test 6] Monte Carlo 50-Seed Hard SLA Gate (|rho| < 0.15 across 3,379 symbols)...")
    mc_rhos = []
    latencies = []
    for seed in range(50):
        np.random.seed(5000 + seed)
        n = 3379
        universe = pd.DataFrame({
            "symbol": [f"SYM_{i:04d}" for i in range(n)],
            "name": [f"Name_{i}" for i in range(n)],
            "market": np.random.choice(["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"], size=n),
            "market_cap": np.exp(np.random.normal(25.0, 1.5, size=n)),
            "pbr": np.random.uniform(0.5, 6.0, size=n),
            "roe": np.random.normal(12.0, 8.0, size=n),
            "asset_growth_yoy": np.random.normal(0.08, 0.15, size=n),
            "momentum_12m": np.random.normal(0.10, 0.25, size=n),
        })

        # Inject 15% realistic missingness
        for col in ["pbr", "roe", "asset_growth_yoy", "momentum_12m"]:
            mask = np.random.uniform(0, 1, size=n) < 0.15
            universe.loc[mask, col] = np.nan

        # Construct highly adversarial factor blend target
        z_size = (np.log(universe["market_cap"].clip(lower=1e8)) - 25.0) / 1.5
        bp_val = 1.0 / universe["pbr"].clip(lower=0.01)
        z_val = np.nan_to_num((bp_val - np.nanmean(bp_val)) / np.nanstd(bp_val), nan=0.0)
        z_prof = np.nan_to_num((universe["roe"] - 12.0) / 8.0, nan=0.0)
        z_cma = np.nan_to_num((universe["asset_growth_yoy"] - 0.08) / 0.15, nan=0.0)
        z_mom = np.nan_to_num((universe["momentum_12m"] - 0.10) / 0.25, nan=0.0)

        w = np.random.uniform(-1, 1, size=5)
        w /= np.linalg.norm(w)
        latent_factor = w[0]*z_size + w[1]*z_val + w[2]*z_prof + w[3]*z_cma + w[4]*z_mom
        raw_y = 0.90 * latent_factor + 0.10 * np.random.normal(0, 1, size=n)

        raw_df = pd.DataFrame({"symbol": universe["symbol"], "score": raw_y})

        t0 = time.perf_counter()
        res = engine.compute_scores(universe=universe, raw_scores=raw_df)
        lat = (time.perf_counter() - t0) * 1000.0
        latencies.append(lat)

        eval_df = pd.merge(universe, res[["symbol", "factor_neutralized_score"]], on="symbol").dropna()
        score = eval_df["factor_neutralized_score"]

        corrs = [
            abs(score.corr(np.log(eval_df["market_cap"].clip(lower=1e8)))),
            abs(score.corr(1.0 / eval_df["pbr"].clip(lower=0.01))),
            abs(score.corr(eval_df["roe"])),
            abs(score.corr(eval_df["asset_growth_yoy"])),
            abs(score.corr(eval_df["momentum_12m"])),
        ]
        max_rho = float(max(corrs))
        mc_rhos.append(max_rho)

    max_overall_rho = float(max(mc_rhos))
    avg_rho = float(np.mean(mc_rhos))
    p99_rho = float(np.percentile(mc_rhos, 99))
    avg_latency = float(np.mean(latencies))
    p99_latency = float(np.percentile(latencies, 99))

    mc_passed = bool(max_overall_rho < 0.15)
    results["monte_carlo_sla"] = {
        "num_runs": 50,
        "max_overall_rho": round(max_overall_rho, 5),
        "avg_rho": round(avg_rho, 5),
        "p99_rho": round(p99_rho, 5),
        "sla_threshold": 0.15,
        "avg_latency_ms": round(avg_latency, 2),
        "p99_latency_ms": round(p99_latency, 2),
        "passed": mc_passed,
    }
    print(f"  Monte Carlo 50 Runs: Max |rho|={max_overall_rho:.4f} (Avg:{avg_rho:.4f}, P99:{p99_rho:.4f}) < 0.15 SLA -> {'PASS' if mc_passed else 'FAIL'}")
    print(f"  Throughput: Avg Latency={avg_latency:.2f}ms, P99 Latency={p99_latency:.2f}ms for 3,379 symbols")

    # -------------------------------------------------------------------------
    # Overall Verdict
    # -------------------------------------------------------------------------
    all_passed = (
        all(x["passed"] for x in collinearity_results) and
        all(x["passed"] for x in missing_results) and
        all(x["passed"] for x in zero_var_results) and
        all(x["passed"] for x in tiny_results) and
        outlier_passed and
        mc_passed
    )

    results["overall_verdict"] = "APPROVE" if all_passed else "REQUEST_CHANGES"
    print("\n" + "=" * 80)
    print(f"FINAL VERDICT: {results['overall_verdict']}")
    print("=" * 80)

    # Save to JSON
    out_path = r"d:\Finance\code\stock\.agents\teamwork_preview_challenger_m1_1\test_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    run_benchmark()
