import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("trading_system"))
from src.core.stat_arb import StatisticalArbitrageEngine

def test_cluster_isolation():
    print("=" * 60)
    print("TESTING PRE-CLUSTERING ISOLATION / RECALL LIMITATIONS")
    print("=" * 60)
    
    np.random.seed(42)
    n_symbols = 500
    n_days = 120
    
    prices_dict = {}
    for i in range(n_symbols):
        prices_dict[f"SYM_{i:04d}"] = (100.0 * np.exp(np.cumsum(np.random.normal(0.0001 * (i % 10), 0.01 + 0.005 * (i % 5), n_days)))).tolist()
        
    # Plant a pair with different drift/volatility profiles (SYM_0005 and SYM_0495)
    p1 = np.array(prices_dict["SYM_0005"])
    p2 = 0.8 * p1 + 50.0 + np.random.normal(0, 0.2, n_days)
    prices_dict["SYM_0495"] = p2.tolist()
    
    # 1. Run clustered scan
    engine_clustered = StatisticalArbitrageEngine(use_clustering=True, n_clusters=40)
    res_clustered = engine_clustered.find_cointegrated_pairs(prices_dict)
    found_clustered = any((p['s1'] in ("SYM_0005", "SYM_0495") and p['s2'] in ("SYM_0005", "SYM_0495")) for p in res_clustered)
    
    # 2. Run unclustered scan
    engine_unclustered = StatisticalArbitrageEngine(use_clustering=False)
    res_unclustered = engine_unclustered.find_cointegrated_pairs(prices_dict)
    found_unclustered = any((p['s1'] in ("SYM_0005", "SYM_0495") and p['s2'] in ("SYM_0005", "SYM_0495")) for p in res_unclustered)
    
    print(f"    Clustered Scan found planted pair (SYM_0005/SYM_0495): {found_clustered}")
    print(f"    Unclustered Scan found planted pair (SYM_0005/SYM_0495): {found_unclustered}")

if __name__ == "__main__":
    test_cluster_isolation()
