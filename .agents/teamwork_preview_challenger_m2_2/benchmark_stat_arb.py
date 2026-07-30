import sys
import os
import time
import numpy as np
import pandas as pd

# Add trading_system root to sys.path
sys.path.insert(0, os.path.abspath("trading_system"))

from src.core.stat_arb import StatisticalArbitrageEngine

def generate_synthetic_universe(n_symbols=3379, n_bars=120, seed=42):
    np.random.seed(seed)
    prices_dict = {}
    
    # 1. Generate base random walks for bulk symbols
    for i in range(n_symbols - 100):
        sym = f"SYM_{i:04d}"
        init_price = np.random.uniform(10.0, 500.0)
        returns = np.random.normal(0.0005, 0.02, n_bars)
        price_path = init_price * np.exp(np.cumsum(returns))
        prices_dict[sym] = price_path.tolist()
        
    # 2. Add 50 cointegrated pairs (100 symbols)
    for i in range(50):
        sym1 = f"COINT_A_{i:02d}"
        sym2 = f"COINT_B_{i:02d}"
        init_p1 = np.random.uniform(50.0, 200.0)
        ret1 = np.random.normal(0.0003, 0.015, n_bars)
        p1 = init_p1 * np.exp(np.cumsum(ret1))
        
        # Cointegrated: p2 = 1.2 * p1 + stationary noise
        noise = np.random.normal(0, 0.5, n_bars)
        p2 = 1.2 * p1 + 10.0 + noise
        
        # Force spread divergence at end to trigger signal
        p1[-1] += 2.0
        
        prices_dict[sym1] = p1.tolist()
        prices_dict[sym2] = p2.tolist()
        
    return prices_dict

def run_benchmark():
    print("=" * 60)
    print("STATISTICAL ARBITRAGE ENGINE - SLA BENCHMARK & CHALLENGE")
    print("=" * 60)
    
    print("[1] Generating 3,379 synthetic symbol price histories (120 bars each)...")
    t0 = time.perf_counter()
    prices_dict = generate_synthetic_universe(n_symbols=3379, n_bars=120, seed=42)
    t_gen = time.perf_counter() - t0
    print(f"    Generated {len(prices_dict)} symbols in {t_gen:.3f}s")
    
    print("\n[2] Executing StatisticalArbitrageEngine scanning...")
    engine = StatisticalArbitrageEngine(use_clustering=True, n_clusters=40)
    
    t_start = time.perf_counter()
    pairs = engine.find_cointegrated_pairs(prices_dict)
    t_scan = time.perf_counter() - t_start
    
    print(f"\n[3] Execution Results:")
    print(f"    - Execution Time: {t_scan:.4f} seconds")
    print(f"    - Target SLA: < 30.0000 seconds")
    print(f"    - SLA Pass/Fail: {'PASS' if t_scan < 30.0 else 'FAIL'}")
    print(f"    - Active Pairs Found: {len(pairs)}")
    
    if pairs:
        print("\n    Top 5 Cointegrated Pairs Found:")
        for idx, p in enumerate(pairs[:5], 1):
            print(f"      {idx}. {p['s1']} / {p['s2']} | Corr: {p['correlation']} | ADF t-stat: {p['adf_stat']:.2f} | p-val: {p['adf_pvalue']} | Half-life: {p['half_life']}d | z-score: {p['z_score']} | Signal: {p['signal']}")
            
    # Check cointegrated synthetic pair recall
    detected_coint_count = 0
    for p in pairs:
        s1, s2 = p['s1'], p['s2']
        if s1.startswith("COINT_") and s2.startswith("COINT_"):
            detected_coint_count += 1
    print(f"\n    Synthetic Cointegrated Pair Detection (Recall): {detected_coint_count} / 50 pairs detected in top pairs")
    
    return t_scan, len(pairs)

if __name__ == "__main__":
    run_benchmark()
