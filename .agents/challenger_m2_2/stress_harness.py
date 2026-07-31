"""
Comprehensive Adversarial Edge-Case Stress Testing Harness for PortfolioOptimizer.optimize_quad_factor_portfolio
"""

import sys
import os
import time
import logging
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
from src.strategy.quad_factor_optimizer import QuadFactorOptimizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StressHarness")

def generate_base_data(n_assets=8, seed=42):
    np.random.seed(seed)
    symbols = [f"STOCK_{i:03d}" for i in range(n_assets)]
    returns = pd.Series(np.random.uniform(0.05, 0.25, n_assets), index=symbols)
    
    rnd = np.random.randn(n_assets, n_assets) * 0.02
    cov = np.dot(rnd, rnd.T) + np.diag([0.04] * n_assets)
    cov_df = pd.DataFrame(cov, index=symbols, columns=symbols)
    
    factor_df = pd.DataFrame({
        'beta': np.random.uniform(0.5, 1.8, n_assets),
        'size': np.random.uniform(10.0, 15.0, n_assets),
        'volatility': np.random.uniform(0.1, 0.4, n_assets),
        'momentum': np.random.uniform(-0.1, 0.3, n_assets)
    }, index=symbols)
    
    sectors = ['Tech', 'Finance', 'Health', 'Energy', 'Consumer']
    sector_map = {sym: sectors[i % len(sectors)] for i, sym in enumerate(symbols)}
    
    return symbols, returns, cov_df, factor_df, sector_map

def verify_output_invariants(weights, symbols, scenario_name):
    issues = []
    if not isinstance(weights, dict):
        return False, [f"{scenario_name}: Output is not a dict, got {type(weights)}"]
    
    if len(weights) != len(symbols):
        issues.append(f"{scenario_name}: Expected {len(symbols)} symbols, got {len(weights)}")
    
    missing_syms = set(symbols) - set(weights.keys())
    if missing_syms:
        issues.append(f"{scenario_name}: Missing symbols in output: {missing_syms}")
        
    w_vals = np.array(list(weights.values())) if len(weights) > 0 else np.array([])
    
    if len(w_vals) > 0:
        if np.isnan(w_vals).any():
            issues.append(f"{scenario_name}: Output contains NaN values: {weights}")
        if np.isinf(w_vals).any():
            issues.append(f"{scenario_name}: Output contains Inf values: {weights}")
            
        min_w = np.min(w_vals)
        if min_w < -1e-6:
            issues.append(f"{scenario_name}: Negative weight detected: min={min_w}")
            
        total_w = np.sum(w_vals)
        if abs(total_w - 1.0) > 1e-3 and len(symbols) > 0:
            issues.append(f"{scenario_name}: Sum of weights is {total_w}, expected 1.0")
        
    return len(issues) == 0, issues

def run_stress_tests():
    po = PortfolioOptimizer()
    results = []
    
    # -------------------------------------------------------------
    # Category 1: Invalid / Corrupted Inputs
    # -------------------------------------------------------------
    
    # 1.1 NaN Covariance Entries
    symbols, ret, cov, fac, sec = generate_base_data(8)
    cov.iloc[0, 1] = np.nan
    cov.iloc[1, 0] = np.nan
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.1 NaN Covariance Entries")
        results.append(("1.1 NaN Covariance Entries", passed, msg, w))
    except Exception as e:
        results.append(("1.1 NaN Covariance Entries", False, [f"Exception raised: {str(e)}"], None))

    # 1.2 Inf Covariance Entries
    symbols, ret, cov, fac, sec = generate_base_data(8)
    cov.iloc[2, 2] = np.inf
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.2 Inf Covariance Entries")
        results.append(("1.2 Inf Covariance Entries", passed, msg, w))
    except Exception as e:
        results.append(("1.2 Inf Covariance Entries", False, [f"Exception raised: {str(e)}"], None))

    # 1.3 All-Zero Covariance Matrix
    symbols, ret, cov, fac, sec = generate_base_data(8)
    zero_cov = pd.DataFrame(0.0, index=symbols, columns=symbols)
    try:
        w = po.optimize_quad_factor_portfolio(ret, zero_cov, fac, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.3 All-Zero Covariance Matrix")
        results.append(("1.3 All-Zero Covariance Matrix", passed, msg, w))
    except Exception as e:
        results.append(("1.3 All-Zero Covariance Matrix", False, [f"Exception raised: {str(e)}"], None))

    # 1.4 Single Asset with Zero Variance (One row/col zero)
    symbols, ret, cov, fac, sec = generate_base_data(8)
    cov.iloc[0, :] = 0.0
    cov.iloc[:, 0] = 0.0
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.4 Zero Variance Single Asset")
        results.append(("1.4 Zero Variance Single Asset", passed, msg, w))
    except Exception as e:
        results.append(("1.4 Zero Variance Single Asset", False, [f"Exception raised: {str(e)}"], None))

    # 1.5 Missing Factor Columns in factor_df
    symbols, ret, cov, fac, sec = generate_base_data(8)
    fac_missing = fac[['beta', 'size']]
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac_missing, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.5 Missing Factor Columns")
        results.append(("1.5 Missing Factor Columns", passed, msg, w))
    except Exception as e:
        results.append(("1.5 Missing Factor Columns", False, [f"Exception raised: {str(e)}"], None))

    # 1.6 Completely Empty factor_df
    symbols, ret, cov, fac, sec = generate_base_data(8)
    fac_empty = pd.DataFrame(index=symbols)
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac_empty, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.6 Empty Factor DF")
        results.append(("1.6 Empty Factor DF", passed, msg, w))
    except Exception as e:
        results.append(("1.6 Empty Factor DF", False, [f"Exception raised: {str(e)}"], None))

    # 1.7 Factor DF contains NaN and Inf values
    symbols, ret, cov, fac, sec = generate_base_data(8)
    fac_nan = fac.copy()
    fac_nan.iloc[0, 0] = np.nan
    fac_nan.iloc[1, 1] = np.inf
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac_nan, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.7 Factor DF with NaN/Inf")
        results.append(("1.7 Factor DF with NaN/Inf", passed, msg, w))
    except Exception as e:
        results.append(("1.7 Factor DF with NaN/Inf", False, [f"Exception raised: {str(e)}"], None))

    # 1.8 Factor Column with Zero Variance (constant values)
    symbols, ret, cov, fac, sec = generate_base_data(8)
    fac_const = fac.copy()
    fac_const['beta'] = 1.0
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac_const, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.8 Constant Factor Column")
        results.append(("1.8 Constant Factor Column", passed, msg, w))
    except Exception as e:
        results.append(("1.8 Constant Factor Column", False, [f"Exception raised: {str(e)}"], None))

    # 1.9 Expected Returns contains NaN / Inf
    symbols, ret, cov, fac, sec = generate_base_data(8)
    ret_nan = ret.copy()
    ret_nan.iloc[0] = np.nan
    try:
        w = po.optimize_quad_factor_portfolio(ret_nan, cov, fac, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.9 Expected Returns NaN")
        results.append(("1.9 Expected Returns NaN", passed, msg, w))
    except Exception as e:
        results.append(("1.9 Expected Returns NaN", False, [f"Exception raised: {str(e)}"], None))

    # 1.10 Covariance matrix as 2D numpy array
    symbols, ret, cov, fac, sec = generate_base_data(8)
    cov_np = cov.values
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov_np, fac, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.10 Covariance as 2D Array")
        results.append(("1.10 Covariance as 2D Array", passed, msg, w))
    except Exception as e:
        results.append(("1.10 Covariance as 2D Array", False, [f"Exception raised: {str(e)}"], None))

    # 1.11 Uppercase Factor Column Names
    symbols, ret, cov, fac, sec = generate_base_data(8)
    fac_upper = fac.rename(columns={'beta': 'BETA', 'size': 'SIZE', 'volatility': 'VOLATILITY', 'momentum': 'MOMENTUM'})
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac_upper, sec)
        passed, msg = verify_output_invariants(w, symbols, "1.11 Uppercase Factor Column Names")
        results.append(("1.11 Uppercase Factor Column Names", passed, msg, w))
    except Exception as e:
        results.append(("1.11 Uppercase Factor Column Names", False, [f"Exception raised: {str(e)}"], None))

    # -------------------------------------------------------------
    # Category 2: Single-Asset & Large Portfolios
    # -------------------------------------------------------------
    
    # 2.1 Single-Asset Portfolio (N=1)
    symbols, ret, cov, fac, sec = generate_base_data(1)
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec)
        passed, msg = verify_output_invariants(w, symbols, "2.1 Single-Asset N=1")
        results.append(("2.1 Single-Asset N=1", passed, msg, w))
    except Exception as e:
        results.append(("2.1 Single-Asset N=1", False, [f"Exception raised: {str(e)}"], None))

    # 2.2 Zero-Asset Portfolio (N=0)
    symbols, ret, cov, fac, sec = generate_base_data(0)
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec)
        passed = (w == {})
        msg = [] if passed else [f"2.2 Zero-Asset N=0 expected {{}}, got {w}"]
        results.append(("2.2 Zero-Asset N=0", passed, msg, w))
    except Exception as e:
        results.append(("2.2 Zero-Asset N=0", False, [f"Exception raised: {str(e)}"], None))

    # 2.3 100-Asset Portfolio (N=100)
    symbols, ret, cov, fac, sec = generate_base_data(100)
    t0 = time.time()
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec, max_weight=0.05)
        dt = time.time() - t0
        passed, msg = verify_output_invariants(w, symbols, "2.3 100-Asset Portfolio")
        msg.append(f"Execution time: {dt:.4f}s")
        results.append(("2.3 100-Asset Portfolio", passed, msg, w))
    except Exception as e:
        results.append(("2.3 100-Asset Portfolio", False, [f"Exception raised: {str(e)}"], None))

    # 2.4 200-Asset Portfolio (N=200)
    symbols, ret, cov, fac, sec = generate_base_data(200)
    t0 = time.time()
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec, max_weight=0.02)
        dt = time.time() - t0
        passed, msg = verify_output_invariants(w, symbols, "2.4 200-Asset Portfolio")
        msg.append(f"Execution time: {dt:.4f}s")
        results.append(("2.4 200-Asset Portfolio", passed, msg, w))
    except Exception as e:
        results.append(("2.4 200-Asset Portfolio", False, [f"Exception raised: {str(e)}"], None))

    # -------------------------------------------------------------
    # Category 3: Fallback & Tight Bounds Edge Cases
    # -------------------------------------------------------------

    # 3.1 Over-constrained max_weight=0.05 (N=10)
    symbols, ret, cov, fac, sec = generate_base_data(10)
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec, max_weight=0.05)
        passed, msg = verify_output_invariants(w, symbols, "3.1 Over-constrained max_weight=0.05")
        results.append(("3.1 Over-constrained max_weight=0.05", passed, msg, w))
    except Exception as e:
        results.append(("3.1 Over-constrained max_weight=0.05", False, [f"Exception raised: {str(e)}"], None))

    # 3.2 Over-constrained single sector max_sector_weight=0.05
    symbols, ret, cov, fac, sec = generate_base_data(8)
    sec_single = {s: 'Tech' for s in symbols}
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec_single, max_sector_weight=0.05)
        passed, msg = verify_output_invariants(w, symbols, "3.2 Over-constrained max_sector_weight=0.05")
        results.append(("3.2 Over-constrained max_sector_weight=0.05", passed, msg, w))
    except Exception as e:
        results.append(("3.2 Over-constrained max_sector_weight=0.05", False, [f"Exception raised: {str(e)}"], None))

    # 3.3 Ultra-Strict Factor Tolerance (1e-7)
    symbols, ret, cov, fac, sec = generate_base_data(8)
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec, factor_tolerances=1e-7)
        passed, msg = verify_output_invariants(w, symbols, "3.3 Ultra-Strict Factor Tolerance")
        results.append(("3.3 Ultra-Strict Factor Tolerance", passed, msg, w))
    except Exception as e:
        results.append(("3.3 Ultra-Strict Factor Tolerance", False, [f"Exception raised: {str(e)}"], None))

    # 3.4 Incomplete Sector Map
    symbols, ret, cov, fac, sec = generate_base_data(8)
    sec_incomplete = {symbols[0]: 'Tech'}
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec_incomplete)
        passed, msg = verify_output_invariants(w, symbols, "3.4 Incomplete Sector Map")
        results.append(("3.4 Incomplete Sector Map", passed, msg, w))
    except Exception as e:
        results.append(("3.4 Incomplete Sector Map", False, [f"Exception raised: {str(e)}"], None))

    # 3.5 Corrupted w_initial
    symbols, ret, cov, fac, sec = generate_base_data(8)
    w_init_bad = {symbols[0]: -1.0, symbols[1]: np.nan, symbols[2]: 5.0}
    try:
        w = po.optimize_quad_factor_portfolio(ret, cov, fac, sec, w_initial=w_init_bad)
        passed, msg = verify_output_invariants(w, symbols, "3.5 Corrupted w_initial")
        results.append(("3.5 Corrupted w_initial", passed, msg, w))
    except Exception as e:
        results.append(("3.5 Corrupted w_initial", False, [f"Exception raised: {str(e)}"], None))

    return results

if __name__ == '__main__':
    res = run_stress_tests()
    print("=" * 80)
    print("STRESS TEST RESULTS SUMMARY")
    print("=" * 80)
    n_pass = 0
    n_fail = 0
    for name, passed, msg, weights in res:
        status = "PASS" if passed else "FAIL"
        if passed:
            n_pass += 1
        else:
            n_fail += 1
        print(f"[{status}] {name}")
        for m in msg:
            print(f"       -> {m}")
    print("=" * 80)
    print(f"Total: {len(res)} | Passed: {n_pass} | Failed: {n_fail}")
    print("=" * 80)
