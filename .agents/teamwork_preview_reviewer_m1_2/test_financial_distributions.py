"""
test_financial_distributions.py — Test correlation across various financial distributions
"""
import numpy as np
import pandas as pd

def run_simulation(dist_type="lognormal", clip_residuals=True):
    N = 3379
    K = 5
    np.random.seed(42)
    
    if dist_type == "normal":
        Z = np.random.randn(N, K)
    elif dist_type == "lognormal":
        # Financial market cap is lognormal, returns are slightly heavy-tailed (t with df=5)
        raw_cap = np.exp(np.random.normal(25, 1.5, N))
        Z0 = (np.log(raw_cap) - np.mean(np.log(raw_cap))) / np.std(np.log(raw_cap))
        Z1 = np.random.normal(0, 1, N)
        Z2 = np.random.normal(0, 1, N)
        Z3 = np.random.normal(0, 1, N)
        Z4 = np.random.standard_t(df=5, size=N)
        Z = np.column_stack([Z0, Z1, Z2, Z3, Z4])
    elif dist_type == "heavy_t":
        Z = np.random.standard_t(df=3, size=(N, K))
        
    X = np.column_stack([np.ones(N), Z])
    
    # y with 80% factor loading
    factor_composite = np.dot(Z, [0.4, 0.3, 0.3, 0.2, 0.5])
    factor_composite = (factor_composite - np.mean(factor_composite)) / np.std(factor_composite)
    y = 0.8 * factor_composite + 0.6 * np.random.randn(N)
    
    # QR decomposition
    Q, _ = np.linalg.qr(X, mode="reduced")
    residual = y - np.dot(Q, np.dot(Q.T, y))
    
    corrs_before = [np.corrcoef(Z[:, k], residual)[0, 1] for k in range(K)]
    
    if clip_residuals:
        p1, p99 = np.percentile(residual, 1), np.percentile(residual, 99)
        denom = (p99 - p1) if (p99 - p1) > 1e-8 else 1.0
        scores = np.clip((residual - p1) / denom, 0.0, 1.0)
    else:
        # Min-max without clipping
        scores = (residual - np.min(residual)) / (np.max(residual) - np.min(residual))
        
    corrs_after = [np.corrcoef(Z[:, k], scores)[0, 1] for k in range(K)]
    
    print(f"Distribution: {dist_type:<10} | Max |rho| before: {max(np.abs(corrs_before)):.2e} | Max |rho| after: {max(np.abs(corrs_after)):.4f}")
    return max(np.abs(corrs_after))

print("=== Comparing clipping effects on correlation ===")
run_simulation("normal", clip_residuals=True)
run_simulation("lognormal", clip_residuals=True)
run_simulation("heavy_t", clip_residuals=True)
print("\n=== Without clipping (pure min-max) ===")
run_simulation("normal", clip_residuals=False)
run_simulation("lognormal", clip_residuals=False)
run_simulation("heavy_t", clip_residuals=False)
