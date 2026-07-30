import sys
import os
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("trading_system"))
from src.core.stat_arb import StatisticalArbitrageEngine

def profile_scan_variations():
    print("=" * 70)
    print("DIAGNOSTIC PROFILING OF CANDIDATE PAIR COUNT & TIMING VARIANCE")
    print("=" * 70)
    
    n_symbols = 3379
    n_days = 120
    
    for seed in [42, 100, 2026]:
        np.random.seed(seed)
        rets = np.random.normal(0.0002, 0.015, size=(n_symbols, n_days))
        prices_mat = 100.0 * np.exp(np.cumsum(rets, axis=1))
        universe = {f"SYM_{i:04d}": prices_mat[i].tolist() for i in range(n_symbols)}
        
        engine = StatisticalArbitrageEngine(use_clustering=True, n_clusters=40)
        
        t0 = time.perf_counter()
        pairs = engine.find_cointegrated_pairs(universe)
        t_elapsed = time.perf_counter() - t0
        
        print(f"Seed {seed:4d} | Execution Time: {t_elapsed:6.3f}s | SLA (<30s): {'PASS' if t_elapsed < 30.0 else 'FAIL'} | Active Pairs: {len(pairs)}")

if __name__ == "__main__":
    profile_scan_variations()
