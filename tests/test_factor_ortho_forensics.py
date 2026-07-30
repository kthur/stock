import os
import sys
import time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine

def run_forensic_benchmarks():
    print("==========================================================")
    print("   EMPIRICAL FORENSIC ANALYSIS: FactorOrthogonalizerEngine")
    print("==========================================================")
    
    engine = FactorOrthogonalizerEngine(default_method='pca_symmetric', ridge_epsilon=1e-6)
    strategy_cols = [f"strat_{i}" for i in range(17)]
    
    # ---------------------------------------------------------
    # TEST 1: Perfectly Collinear Columns (Rank-deficient Matrix)
    # ---------------------------------------------------------
    N = 500
    np.random.seed(42)
    latent = np.random.uniform(0.1, 0.9, N)
    matrix_collinear = np.column_stack([latent for _ in range(17)]) # All 17 identical
    df_collinear = pd.DataFrame(matrix_collinear, columns=strategy_cols)
    
    res_pca_collinear = engine.orthogonalize(df_collinear, strategy_cols, method='pca_symmetric')
    res_gs_collinear = engine.orthogonalize(df_collinear, strategy_cols, method='gram_schmidt')
    
    pca_vals = res_pca_collinear[strategy_cols].values
    gs_vals = res_gs_collinear[strategy_cols].values
    
    print("\n--- TEST 1: Perfectly Collinear (17 Identical Columns) ---")
    print(f"PCA output shape: {pca_vals.shape}, NaNs: {np.isnan(pca_vals).sum()}, Infs: {np.isinf(pca_vals).sum()}")
    print(f"PCA output range: [{pca_vals.min():.4f}, {pca_vals.max():.4f}]")
    print(f"Gram-Schmidt output shape: {gs_vals.shape}, NaNs: {np.isnan(gs_vals).sum()}, Infs: {np.isinf(gs_vals).sum()}")
    print(f"Gram-Schmidt output range: [{gs_vals.min():.4f}, {gs_vals.max():.4f}]")
    
    # ---------------------------------------------------------
    # TEST 2: Singular Covariance Matrix (N < K, e.g., N = 5, K = 17)
    # ---------------------------------------------------------
    matrix_singular = np.random.uniform(0.0, 1.0, (5, 17))
    df_singular = pd.DataFrame(matrix_singular, columns=strategy_cols)
    
    res_pca_singular = engine.orthogonalize(df_singular, strategy_cols, method='pca_symmetric')
    vals_sing = res_pca_singular[strategy_cols].values
    
    print("\n--- TEST 2: Singular Covariance (N = 5 < K = 17) ---")
    print(f"Output shape: {vals_sing.shape}, NaNs: {np.isnan(vals_sing).sum()}")
    print(f"Output range: [{vals_sing.min():.4f}, {vals_sing.max():.4f}]")
    
    # ---------------------------------------------------------
    # TEST 3: Zero Variance / Constant Features
    # ---------------------------------------------------------
    matrix_zero_var = np.random.uniform(0.1, 0.9, (500, 17))
    matrix_zero_var[:, 0] = 0.0 # Zero constant
    matrix_zero_var[:, 1] = 1.0 # Max constant
    matrix_zero_var[:, 2] = 0.5 # Mid constant
    df_zero_var = pd.DataFrame(matrix_zero_var, columns=strategy_cols)
    
    res_pca_zero = engine.orthogonalize(df_zero_var, strategy_cols, method='pca_symmetric')
    vals_zero = res_pca_zero[strategy_cols].values
    
    print("\n--- TEST 3: Zero Variance / Constant Features ---")
    print(f"Constant col 0 std: {np.std(vals_zero[:, 0]):.6f}")
    print(f"Constant col 1 std: {np.std(vals_zero[:, 1]):.6f}")
    print(f"Constant col 2 std: {np.std(vals_zero[:, 2]):.6f}")
    print(f"NaNs present: {np.isnan(vals_zero).sum()}")
    
    # ---------------------------------------------------------
    # TEST 4: Highly Correlated Scores (80% correlation) & Correlation Reduction
    # ---------------------------------------------------------
    base_corr = 0.80
    latent = np.random.normal(0, 1, N)
    data = {}
    for col in strategy_cols:
        noise = np.random.normal(0, 1, N)
        raw = np.sqrt(base_corr) * latent + np.sqrt(1.0 - base_corr) * noise
        data[col] = 1.0 / (1.0 + np.exp(-raw)) # sigmoid to [0,1]
        
    df_corr = pd.DataFrame(data)
    raw_matrix = df_corr[strategy_cols].values
    raw_corr_matrix = np.corrcoef(raw_matrix, rowvar=False)
    mask = ~np.eye(17, dtype=bool)
    mean_raw_corr = np.mean(np.abs(raw_corr_matrix[mask]))
    
    res_pca_corr = engine.orthogonalize(df_corr, strategy_cols, method='pca_symmetric')
    res_gs_corr = engine.orthogonalize(df_corr, strategy_cols, method='gram_schmidt')
    
    pca_corr_matrix = np.corrcoef(res_pca_corr[strategy_cols].values, rowvar=False)
    gs_corr_matrix = np.corrcoef(res_gs_corr[strategy_cols].values, rowvar=False)
    
    mean_pca_corr = np.mean(np.abs(pca_corr_matrix[mask]))
    mean_gs_corr = np.mean(np.abs(gs_corr_matrix[mask]))
    
    print("\n--- TEST 4: Highly Correlated Scores (Base corr ~ 0.80) ---")
    print(f"Raw mean off-diagonal correlation: {mean_raw_corr:.4f}")
    print(f"PCA ZCA mean off-diagonal correlation: {mean_pca_corr:.4f} (Pass < 0.30: {mean_pca_corr < 0.30})")
    print(f"Gram-Schmidt mean off-diagonal correlation: {mean_gs_corr:.4f} (Pass < 0.30: {mean_gs_corr < 0.30})")
    
    # Rank correlation preservation
    raw_sums = raw_matrix.sum(axis=1)
    pca_sums = res_pca_corr[strategy_cols].values.sum(axis=1)
    spearman_rho = pd.Series(raw_sums).corr(pd.Series(pca_sums), method='spearman')
    print(f"Spearman rank correlation (Raw sum vs PCA ortho sum): {spearman_rho:.4f} (Pass >= 0.70: {spearman_rho >= 0.70})")

    # ---------------------------------------------------------
    # TEST 5: Latency and Scaling Benchmark (3,379 symbols x 17 factors)
    # ---------------------------------------------------------
    N_large = 3379
    latent_large = np.random.normal(0, 1, N_large)
    data_large = {}
    for col in strategy_cols:
        noise = np.random.normal(0, 1, N_large)
        raw = np.sqrt(base_corr) * latent_large + np.sqrt(1.0 - base_corr) * noise
        data_large[col] = 1.0 / (1.0 + np.exp(-raw))
    df_large = pd.DataFrame(data_large)
    
    t0 = time.perf_counter()
    res_large = engine.orthogonalize(df_large, strategy_cols, method='pca_symmetric')
    t_pca_ms = (time.perf_counter() - t0) * 1000.0
    
    t0 = time.perf_counter()
    res_large_gs = engine.orthogonalize(df_large, strategy_cols, method='gram_schmidt')
    t_gs_ms = (time.perf_counter() - t0) * 1000.0
    
    print("\n--- TEST 5: Benchmark (3,379 symbols x 17 strategies) ---")
    print(f"PCA ZCA Execution Time: {t_pca_ms:.2f} ms (Target < 50 ms)")
    print(f"Gram-Schmidt Execution Time: {t_gs_ms:.2f} ms")
    
    print("\n==========================================================")

if __name__ == '__main__':
    run_forensic_benchmarks()
