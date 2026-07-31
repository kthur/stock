"""
Empirical Stress Test Harness for QuadFactorOptimizer.
Written by challenger_m2_1.
"""

import sys
import os
import traceback
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, r"d:\Finance\code\stock")

from src.strategy.quad_factor_optimizer import QuadFactorOptimizer

def setup_baseline_data():
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B']
    n_assets = len(symbols)
    expected_returns = pd.Series(
        [0.12, 0.10, 0.15, 0.08, 0.20, 0.18, 0.14, 0.06],
        index=symbols
    )
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

    return symbols, expected_returns, cov_df, factor_df, sector_map


def test_1_baseline_diagnostic():
    print("=== Test 1: Baseline Diagnostic on test_quad_factor_neutrality_bounds ===")
    symbols, mu, cov_df, factor_df, sector_map = setup_baseline_data()
    optimizer = QuadFactorOptimizer(default_max_weight=0.25, default_factor_tolerance=0.05)

    # Let's call internal _solve_scipy_slsqp directly to see why primary SLSQP failed
    mu_vec = mu.loc[symbols].values.astype(np.float64)
    Sigma = cov_df.loc[symbols, symbols].values.astype(np.float64)
    w0 = np.ones(len(symbols)) / len(symbols)

    # Standardize factors
    factors = ['beta', 'size', 'volatility', 'momentum']
    standardized_factors = {}
    for f in factors:
        raw_f = factor_df[f].values.astype(np.float64)
        std_f = (raw_f - np.mean(raw_f)) / np.std(raw_f)
        standardized_factors[f] = std_f

    tol_dict = {f: 0.05 for f in factors}

    res_primary = optimizer._solve_scipy_slsqp(
        symbols, mu_vec, Sigma, standardized_factors, sector_map,
        w0, max_w=0.25, max_sec_w=0.25, tolerances=tol_dict
    )
    print(f"Primary SLSQP result: {res_primary}")

    # Full optimize call
    weights = optimizer.optimize(mu, cov_df, factor_df, sector_map, max_weight=0.25)
    w_vec = np.array([weights[s] for s in symbols])

    print("Result weights:", weights)
    print("Weight sum:", sum(weights.values()))

    # Check factor exposures
    for col in factors:
        raw_f = factor_df[col].values
        std_f = (raw_f - np.mean(raw_f)) / np.std(raw_f)
        exp = float(np.dot(std_f, w_vec))
        print(f"Factor {col} exposure: {exp:.5f} (bound 0.05 -> pass: {abs(exp) <= 0.051})")

    # Check sector sums
    sec_sums = {}
    for sym, w in weights.items():
        sec = sector_map[sym]
        sec_sums[sec] = sec_sums.get(sec, 0.0) + w
    print("Sector sums:", sec_sums)


def test_2_ill_conditioned_cov():
    print("\n=== Test 2: Ill-conditioned & Non-PSD Covariance Matrix ===")
    symbols, mu, cov_df, factor_df, sector_map = setup_baseline_data()
    n = len(symbols)

    # Ill-conditioned matrix with condition number 1e14
    Q, _ = np.linalg.qr(np.random.randn(n, n))
    eigenvals = np.logspace(-10, 4, n) # ratio 1e14
    cov_ill = Q @ np.diag(eigenvals) @ Q.T
    cov_ill_df = pd.DataFrame(cov_ill, index=symbols, columns=symbols)

    optimizer = QuadFactorOptimizer(default_max_weight=0.25)
    weights = optimizer.optimize(mu, cov_ill_df, factor_df, sector_map)
    print("Ill-conditioned cov result weights sum:", sum(weights.values()) if weights else None)
    print("Contains NaN:", any(np.isnan(v) for v in weights.values()) if weights else True)

    # Non-PSD covariance matrix (negative eigenvalues)
    eigenvals_neg = np.array([-0.05, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07])
    cov_non_psd = Q @ np.diag(eigenvals_neg) @ Q.T
    cov_non_psd_df = pd.DataFrame(cov_non_psd, index=symbols, columns=symbols)

    weights_neg = optimizer.optimize(mu, cov_non_psd_df, factor_df, sector_map)
    print("Non-PSD cov result weights sum:", sum(weights_neg.values()) if weights_neg else None)


def test_3_extreme_returns():
    print("\n=== Test 3: Extreme Expected Returns Scale ===")
    symbols, mu, cov_df, factor_df, sector_map = setup_baseline_data()

    # Extreme returns (1e8)
    mu_extreme = mu * 1e8
    optimizer = QuadFactorOptimizer(default_max_weight=0.25)
    weights = optimizer.optimize(mu_extreme, cov_df, factor_df, sector_map)
    print("Extreme return (1e8) weights sum:", sum(weights.values()) if weights else None)

    # Microscopic returns (1e-12)
    mu_micro = mu * 1e-12
    weights_micro = optimizer.optimize(mu_micro, cov_df, factor_df, sector_map)
    print("Microscopic return (1e-12) weights sum:", sum(weights_micro.values()) if weights_micro else None)


def test_4_collinear_factors():
    print("\n=== Test 4: Collinear & Degenerate Factors ===")
    symbols, mu, cov_df, factor_df, sector_map = setup_baseline_data()

    # Create collinear factor_df: momentum = 2 * volatility
    factor_df_coll = factor_df.copy()
    factor_df_coll['momentum'] = factor_df_coll['volatility'] * 2.0
    factor_df_coll['beta'] = 1.0  # Zero variance across assets!

    optimizer = QuadFactorOptimizer(default_max_weight=0.25)
    weights = optimizer.optimize(mu, cov_df, factor_df_coll, sector_map)
    print("Collinear factor result weights sum:", sum(weights.values()) if weights else None)


def test_5_missing_index_and_keyerror_vulnerability():
    print("\n=== Test 5: Mismatched Index / Missing Symbols in factor_df ===")
    symbols, mu, cov_df, factor_df, sector_map = setup_baseline_data()

    # Drop one symbol from factor_df or scramble order
    factor_df_missing = factor_df.iloc[:-1].copy() # missing last symbol BRK.B

    optimizer = QuadFactorOptimizer(default_max_weight=0.25)
    try:
        weights = optimizer.optimize(mu, cov_df, factor_df_missing, sector_map)
        print("Missing symbol factor_df weights sum:", sum(weights.values()) if weights else None)
    except Exception as e:
        print(f"EXCEPTIONAL FAILURE on missing symbol factor_df: {type(e).__name__}: {e}")
        traceback.print_exc()


def test_6_infeasible_sector_cap_post_processing_violation():
    print("\n=== Test 6: Infeasible Sector Cap & Post-Processing Violation ===")
    symbols, mu, cov_df, factor_df, sector_map = setup_baseline_data()

    # Highly concentrated sector assignment:
    # 7 stocks in Tech, 1 stock in Financials.
    # max_sector_weight = 0.25.
    # Total max weight possible = Tech (0.25) + Financials (0.25) = 0.50 < 1.0!
    optimizer = QuadFactorOptimizer(default_max_weight=0.15, default_max_sector_weight=0.25)
    weights = optimizer.optimize(mu, cov_df, factor_df, sector_map, max_sector_weight=0.25)

    sec_sums = {}
    for sym, w in weights.items():
        sec = sector_map[sym]
        sec_sums[sec] = sec_sums.get(sec, 0.0) + w

    print("Sector sums under max_sector_weight=0.25:", sec_sums)
    for sec, total_w in sec_sums.items():
        violation = total_w > 0.25
        print(f"Sector {sec}: sum={total_w:.4f}, cap=0.25, VIOLATION={violation}")

    for sym, w in weights.items():
        violation = w > 0.15
        if violation:
            print(f"Asset {sym}: weight={w:.4f}, cap=0.15, VIOLATION={violation}")


if __name__ == '__main__':
    test_1_baseline_diagnostic()
    test_2_ill_conditioned_cov()
    test_3_extreme_returns()
    test_4_collinear_factors()
    test_5_missing_index_and_keyerror_vulnerability()
    test_6_infeasible_sector_cap_post_processing_violation()
