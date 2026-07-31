"""
Deep Stress Testing & Edge-Case Exploitation for QuadFactorOptimizer.
Written by challenger_m2_1.
"""

import sys
import os
import numpy as np
import pandas as pd
import scipy.optimize as opt

sys.path.insert(0, r"d:\Finance\code\stock")

from src.strategy.quad_factor_optimizer import QuadFactorOptimizer

def test_slsqp_feasibility_with_factor_neutrality():
    print("=== Deep Test 1: SLSQP Feasibility when sector caps are high (0.60) ===")
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B']
    n_assets = len(symbols)
    mu = pd.Series([0.12, 0.10, 0.15, 0.08, 0.20, 0.18, 0.14, 0.06], index=symbols)

    np.random.seed(42)
    random_matrix = np.random.randn(n_assets, n_assets) * 0.02
    cov = np.dot(random_matrix, random_matrix.T) + np.diag([0.04] * n_assets)
    cov_df = pd.DataFrame(cov, index=symbols, columns=symbols)

    factor_df = pd.DataFrame({
        'beta': [1.2, 0.9, 1.1, 1.0, 1.5, 1.8, 1.3, 0.6],
        'size': [12.5, 12.4, 12.2, 12.3, 11.8, 11.5, 12.0, 12.1],
        'volatility': [0.22, 0.18, 0.20, 0.21, 0.35, 0.45, 0.28, 0.14],
        'momentum': [0.15, 0.10, 0.05, -0.02, 0.40, 0.30, 0.12, -0.05]
    }, index=symbols)

    sector_map = {
        'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'AMZN': 'Consumer',
        'NVDA': 'Tech', 'TSLA': 'Consumer', 'META': 'Tech', 'BRK.B': 'Financials'
    }

    # Use max_sector_weight = 0.70 (so sector caps sum to 0.70 * 3 = 2.1 > 1.0)
    optimizer = QuadFactorOptimizer(default_max_weight=0.25, default_max_sector_weight=0.70, default_factor_tolerance=0.05)
    weights = optimizer.optimize(mu, cov_df, factor_df, sector_map, max_weight=0.25, max_sector_weight=0.70)

    print("Result weights with max_sector_weight=0.70:", weights)
    print("Weight sum:", sum(weights.values()))

    w_vec = np.array([weights[s] for s in symbols])
    for col in ['beta', 'size', 'volatility', 'momentum']:
        raw_f = factor_df[col].values
        std_f = (raw_f - np.mean(raw_f)) / np.std(raw_f)
        exp = float(np.dot(std_f, w_vec))
        print(f"Factor {col} exposure: {exp:.5f} (bound 0.05 -> pass: {abs(exp) <= 0.051})")


def test_nan_inf_handling():
    print("\n=== Deep Test 2: Handling NaN and Inf in Returns, Cov, Factors ===")
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    n_assets = len(symbols)

    mu_nan = pd.Series([0.12, np.nan, 0.15, np.inf], index=symbols)

    cov = np.eye(n_assets) * 0.04
    cov[1, 2] = np.nan
    cov_df = pd.DataFrame(cov, index=symbols, columns=symbols)

    factor_df = pd.DataFrame({
        'beta': [1.2, np.nan, 1.1, np.inf],
        'size': [12.5, 12.4, np.nan, 12.3],
        'volatility': [0.22, 0.18, 0.20, np.nan],
        'momentum': [0.15, np.nan, 0.05, -0.02]
    }, index=symbols)

    sector_map = {'AAPL': 'Tech', 'MSFT': 'Tech', 'GOOGL': 'Tech', 'AMZN': 'Consumer'}

    optimizer = QuadFactorOptimizer(default_max_weight=0.50)
    try:
        weights = optimizer.optimize(mu_nan, cov_df, factor_df, sector_map)
        print("NaN/Inf inputs result weights:", weights)
        print("Contains NaN weights:", any(np.isnan(v) for v in weights.values()))
    except Exception as e:
        print(f"Exception on NaN/Inf inputs: {type(e).__name__}: {e}")


def test_large_scale_universe():
    print("\n=== Deep Test 3: Scaling to 100 Assets ===")
    np.random.seed(123)
    n_assets = 100
    symbols = [f"STOCK_{i:03d}" for i in range(n_assets)]

    mu = pd.Series(np.random.randn(n_assets) * 0.10 + 0.05, index=symbols)

    # Random positive definite cov matrix
    A = np.random.randn(n_assets, n_assets) * 0.05
    cov = np.dot(A, A.T) + np.diag(np.random.rand(n_assets) * 0.02 + 0.01)
    cov_df = pd.DataFrame(cov, index=symbols, columns=symbols)

    factor_df = pd.DataFrame({
        'beta': np.random.randn(n_assets) * 0.3 + 1.0,
        'size': np.random.randn(n_assets) * 1.5 + 10.0,
        'volatility': np.random.rand(n_assets) * 0.3 + 0.1,
        'momentum': np.random.randn(n_assets) * 0.2
    }, index=symbols)

    sectors = ['Tech', 'Health', 'Finance', 'Consumer', 'Energy']
    sector_map = {sym: np.random.choice(sectors) for sym in symbols}

    optimizer = QuadFactorOptimizer(default_max_weight=0.05, default_max_sector_weight=0.30, default_factor_tolerance=0.05)
    import time
    t0 = time.time()
    weights = optimizer.optimize(mu, cov_df, factor_df, sector_map, max_weight=0.05, max_sector_weight=0.30)
    t1 = time.time()

    print(f"100 Assets Optimization completed in {t1 - t0:.4f} seconds.")
    print("Weight sum:", sum(weights.values()))
    print("Max weight:", max(weights.values()))

    w_vec = np.array([weights[s] for s in symbols])
    for col in ['beta', 'size', 'volatility', 'momentum']:
        raw_f = factor_df[col].values
        std_f = (raw_f - np.mean(raw_f)) / np.std(raw_f)
        exp = float(np.dot(std_f, w_vec))
        print(f"Factor {col} exposure: {exp:.5f} (bound 0.05 -> pass: {abs(exp) <= 0.051})")


if __name__ == '__main__':
    test_slsqp_feasibility_with_factor_neutrality()
    test_nan_inf_handling()
    test_large_scale_universe()
