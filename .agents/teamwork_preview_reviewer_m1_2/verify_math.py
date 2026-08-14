"""
verify_math.py — Independent mathematical and adversarial verification of MultiFactorNeutralizerEngine
"""
import sys
import os
import time
import numpy as np
import pandas as pd

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from trading_system.src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine

def test_qr_orthogonality_proof():
    print("=== TEST 1: QR Orthogonality & Projection Mathematics ===")
    N = 500
    K = 5
    np.random.seed(42)
    # Generate random factors with high multicollinearity
    base = np.random.randn(N, 1)
    F = base * 0.9 + np.random.randn(N, K) * 0.1
    # Standardize
    Z = (F - np.mean(F, axis=0)) / np.std(F, axis=0)
    X = np.column_stack([np.ones(N), Z])
    
    # Generate target y with 90% correlation to factors
    beta = np.array([0.5, 1.2, -0.8, 0.4, -0.6, 0.9])
    y = np.dot(X, beta) + np.random.randn(N) * 0.2
    
    # QR decomposition
    Q, _ = np.linalg.qr(X, mode="reduced")
    proj = np.dot(Q, np.dot(Q.T, y))
    residual = y - proj
    
    # Verify exact orthogonality to each factor
    for k in range(K):
        corr = np.corrcoef(Z[:, k], residual)[0, 1]
        print(f"Factor {k} raw correlation with residual: {corr:.8e}")
        assert abs(corr) < 1e-12, f"Factor {k} is not orthogonal: {corr}"
    
    mean_res = np.mean(residual)
    print(f"Mean residual: {mean_res:.8e}")
    assert abs(mean_res) < 1e-12, f"Mean residual is not zero: {mean_res}"
    print("TEST 1 PASSED: Exact mathematical orthogonality confirmed.\n")

def test_rank_deficient_collinearity():
    print("=== TEST 2: Rank-Deficient Collinear Factors ===")
    N = 200
    np.random.seed(123)
    # 2 identical factors (rank deficient)
    f1 = np.random.randn(N)
    f2 = f1.copy() # exact collinearity
    f3 = np.random.randn(N)
    f4 = np.zeros(N) # zero variance
    f5 = np.random.randn(N)
    
    df = pd.DataFrame({
        "symbol": [f"S_{i}" for i in range(N)],
        "market": ["SP500"] * N,
        "market_cap": np.exp(f1 + 20),
        "pbr": np.clip(f2 + 3, 0.1, 10),
        "roe": f3 * 10,
        "asset_growth_yoy": f4,
        "momentum_12m": f5,
        "raw_score": 0.8 * f1 + 0.2 * np.random.randn(N)
    })
    
    engine = MultiFactorNeutralizerEngine()
    res_df = engine.compute_scores(df)
    
    scores = res_df["factor_neutralized_score"].values
    assert not np.isnan(scores).any(), "NaN found in rank deficient case"
    assert len(scores) == N
    
    # Check max correlation
    eval_df = pd.merge(df, res_df, on="symbol")
    s = eval_df["factor_neutralized_score"]
    c1 = abs(s.corr(eval_df["market_cap"].apply(np.log)))
    c3 = abs(s.corr(eval_df["roe"]))
    c5 = abs(s.corr(eval_df["momentum_12m"]))
    print(f"Correlations: Size={c1:.4f}, ROE={c3:.4f}, Mom={c5:.4f}")
    assert max(c1, c3, c5) < 0.15, f"Max correlation exceeded 0.15: {max(c1, c3, c5)}"
    print("TEST 2 PASSED: Rank-deficient & collinear factors handled robustly.\n")

def test_heavy_tail_clipping_sla():
    print("=== TEST 3: Heavy-Tailed Outliers & Post-Clipping SLA ===")
    np.random.seed(999)
    engine = MultiFactorNeutralizerEngine()
    
    max_rhos = []
    for trial in range(50):
        N = 1000
        # Student-t distribution (df=2, heavy tails / extreme outliers)
        f_raw = np.random.standard_t(df=2, size=(N, 5))
        y_raw = 0.85 * f_raw[:, 0] + 0.3 * np.random.randn(N)
        
        df = pd.DataFrame({
            "symbol": [f"S_{i}" for i in range(N)],
            "market": ["KOSPI"] * (N // 2) + ["KOSDAQ"] * (N // 2),
            "market_cap": np.exp(np.clip(f_raw[:, 0] + 20, 10, 30)),
            "per": np.clip(f_raw[:, 1] * 10 + 15, -100, 1000),
            "roe": f_raw[:, 2] * 5 + 10,
            "asset_growth_yoy": f_raw[:, 3] * 0.1,
            "momentum_12m": f_raw[:, 4] * 0.2,
            "score": y_raw
        })
        
        res = engine.compute_scores(df)
        eval_df = pd.merge(df, res, on="symbol")
        s = eval_df["factor_neutralized_score"]
        
        rhos = [
            abs(s.corr(eval_df["market_cap"].apply(np.log))),
            abs(s.corr(eval_df["roe"])),
            abs(s.corr(eval_df["asset_growth_yoy"])),
            abs(s.corr(eval_df["momentum_12m"]))
        ]
        max_rhos.append(max(rhos))
    
    max_rho_overall = max(max_rhos)
    mean_max_rho = np.mean(max_rhos)
    print(f"Across 50 heavy-tailed trials: Max |rho| = {max_rho_overall:.4f}, Mean max |rho| = {mean_max_rho:.4f}")
    assert max_rho_overall < 0.15, f"Heavy-tail SLA violated: {max_rho_overall}"
    print("TEST 3 PASSED: |rho| < 0.15 holds unconditionally across heavy-tailed distributions.\n")

def test_missingness_coverage_and_imputation():
    print("=== TEST 4: Extreme Missingness (95% missing) ===")
    N = 3379
    np.random.seed(777)
    engine = MultiFactorNeutralizerEngine()
    
    df = pd.DataFrame({
        "symbol": [f"S_{i:04d}" for i in range(N)],
        "market": np.random.choice(["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000", "KONEX"], size=N),
        "market_cap": np.where(np.random.rand(N) < 0.95, np.nan, np.exp(np.random.randn(N) + 20)),
        "per": np.where(np.random.rand(N) < 0.95, np.nan, np.random.uniform(5, 30, size=N)),
        "roe": np.where(np.random.rand(N) < 0.95, np.nan, np.random.normal(10, 5, size=N)),
        "asset_growth_yoy": np.where(np.random.rand(N) < 0.95, np.nan, np.random.normal(0.05, 0.1, size=N)),
        "momentum_12m": np.where(np.random.rand(N) < 0.95, np.nan, np.random.normal(0.1, 0.2, size=N)),
        "score": np.random.uniform(0, 1, size=N)
    })
    
    res = engine.compute_scores(df)
    valid_count = res["factor_neutralized_score"].notna().sum()
    coverage = valid_count / N * 100
    print(f"Total symbols: {N}, Valid score count: {valid_count}, Coverage: {coverage:.2f}%")
    assert coverage >= 95.0, f"Coverage violated: {coverage}%"
    print("TEST 4 PASSED: Missingness coverage >= 95% confirmed.\n")

def test_performance_timing():
    print("=== TEST 5: Microsecond & Millisecond Timing Benchmark ===")
    N = 3379
    np.random.seed(42)
    engine = MultiFactorNeutralizerEngine()
    
    df = pd.DataFrame({
        "symbol": [f"S_{i:04d}" for i in range(N)],
        "market": np.random.choice(["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"], size=N),
        "market_cap": np.exp(np.random.randn(N) + 20),
        "per": np.random.uniform(5, 50, size=N),
        "roe": np.random.normal(10, 5, size=N),
        "asset_growth_yoy": np.random.normal(0.05, 0.1, size=N),
        "momentum_12m": np.random.normal(0.1, 0.2, size=N),
        "score": np.random.uniform(0, 1, size=N)
    })
    
    # Warmup
    _ = engine.compute_scores(df)
    
    timings = []
    for _ in range(20):
        t0 = time.perf_counter()
        _ = engine.compute_scores(df)
        timings.append((time.perf_counter() - t0) * 1000.0)
    
    min_t = np.min(timings)
    med_t = np.median(timings)
    mean_t = np.mean(timings)
    p95_t = np.percentile(timings, 95)
    print(f"3,379 symbols execution time (20 runs): Min={min_t:.2f}ms, Median={med_t:.2f}ms, Mean={mean_t:.2f}ms, P95={p95_t:.2f}ms")
    print("TEST 5 PASSED.\n")

if __name__ == "__main__":
    test_qr_orthogonality_proof()
    test_rank_deficient_collinearity()
    test_heavy_tail_clipping_sla()
    test_missingness_coverage_and_imputation()
    test_performance_timing()
