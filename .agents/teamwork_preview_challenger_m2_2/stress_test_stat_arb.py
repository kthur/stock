import sys
import os
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("trading_system"))
from src.core.stat_arb import StatisticalArbitrageEngine, _extract_15d_features, _estimate_adf_pvalue, _estimate_half_life

def test_edge_cases():
    print("=" * 60)
    print("EMPIRICAL STRESS TEST & FAILURE MODE ANALYSIS")
    print("=" * 60)
    
    engine = StatisticalArbitrageEngine()
    
    # Test 1: Constant / Zero Variance Prices
    print("\n[Test 1] Zero Variance / Constant Prices")
    p_flat = [100.0] * 120
    prices_dict_flat = {
        "FLAT_A": p_flat,
        "FLAT_B": p_flat,
        "NORMAL_C": list(100.0 + np.cumsum(np.random.normal(0, 1, 120)))
    }
    try:
        res = engine.find_cointegrated_pairs(prices_dict_flat)
        print(f"    Result count: {len(res)} (Expected: 0 flat pairs)")
        print("    Status: PASS (No unhandled exceptions on zero variance)")
    except Exception as e:
        print(f"    Status: FAIL - Exception raised: {e}")
        
    # Test 2: NaN and Inf Handling
    print("\n[Test 2] NaN and Inf Input Handling")
    p_nan = list(100.0 + np.cumsum(np.random.normal(0, 1, 120)))
    p_nan[50] = np.nan
    p_inf = list(100.0 + np.cumsum(np.random.normal(0, 1, 120)))
    p_inf[20] = np.inf
    
    prices_dict_corrupt = {
        "CORRUPT_NAN": p_nan,
        "CORRUPT_INF": p_inf,
        "NORMAL_1": list(100.0 + np.cumsum(np.random.normal(0, 1, 120))),
        "NORMAL_2": list(100.0 + np.cumsum(np.random.normal(0, 1, 120)))
    }
    try:
        res = engine.find_cointegrated_pairs(prices_dict_corrupt)
        print(f"    Result count: {len(res)}")
        print("    Status: PASS (Handled corrupt inputs without crashing)")
    except Exception as e:
        print(f"    Status: FAIL - Exception raised: {e}")

    # Test 3: Short Price Series (<30 bars)
    print("\n[Test 3] Short Price Histories (<30 bars)")
    prices_short = {
        "SHORT_1": [10.0, 11.0, 10.5, 12.0],
        "SHORT_2": [100.0, 101.0, 100.5, 102.0]
    }
    res_short = engine.find_cointegrated_pairs(prices_short)
    print(f"    Result count: {len(res_short)} (Expected: 0)")
    
    # Test 4: False Positive Rate under Independent Random Walks
    print("\n[Test 4] False Positive Rate (500 Independent Random Walks)")
    np.random.seed(123)
    n_rand = 500
    prices_dict_rand = {}
    for i in range(n_rand):
        prices_dict_rand[f"RND_{i:03d}"] = (100.0 * np.exp(np.cumsum(np.random.normal(0, 0.02, 120)))).tolist()
        
    t_start = time.perf_counter()
    res_rand = engine.find_cointegrated_pairs(prices_dict_rand)
    t_elapsed = time.perf_counter() - t_start
    print(f"    500 Pure Noise Symbols scanned in {t_elapsed:.3f}s")
    print(f"    False Positive Pairs Found: {len(res_rand)} out of max candidates")

    # Test 5: Exhaustive Scan without Clustering (use_clustering=False) SLA test
    print("\n[Test 5] Non-Clustered (Exhaustive) Scan for N=1000 symbols")
    engine_no_cluster = StatisticalArbitrageEngine(use_clustering=False)
    prices_dict_1000 = {}
    for i in range(1000):
        prices_dict_1000[f"SYM_{i:04d}"] = (100.0 * np.exp(np.cumsum(np.random.normal(0, 0.02, 120)))).tolist()
    
    t_start = time.perf_counter()
    res_no_cluster = engine_no_cluster.find_cointegrated_pairs(prices_dict_1000)
    t_elapsed = time.perf_counter() - t_start
    total_pairs = 1000 * 999 // 2
    print(f"    Exhaustive scan of {total_pairs:,} pairs across 1,000 symbols took: {t_elapsed:.3f}s")

if __name__ == "__main__":
    test_edge_cases()
