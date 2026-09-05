import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "trading_system")
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator

alloc = UnifiedPortfolioAllocator()

# 1. Monotonicity of cascade tilting
cvar_weights = []
rp_weights = []
cascades = np.linspace(0.0, 0.9, 10)
for c in cascades:
    w = alloc.compute_information_theoretic_blend_weights(
        regime="BEAR_HIGH_VOL",
        rvine_cascade_index=float(c),
        version=8
    )
    cvar_weights.append(w["cvar"])
    rp_weights.append(w["rp"])

cvar_increasing = all(cvar_weights[i] <= cvar_weights[i+1] for i in range(len(cvar_weights)-1))
rp_decreasing = all(rp_weights[i] >= rp_weights[i+1] for i in range(len(rp_weights)-1))
print("CVaR monotonically increasing with cascade:", cvar_increasing, cvar_weights[0], "->", cvar_weights[-1])
print("RP monotonically decreasing with cascade:", rp_decreasing, rp_weights[0], "->", rp_weights[-1])

# 2. Information Entropy Parity (IEP) dispersion reduction
regime_uniform = {
    "BULL_LOW_VOL": 0.17, "BULL_HIGH_VOL": 0.17,
    "SIDEWAYS_LOW_VOL": 0.17, "SIDEWAYS_HIGH_VOL": 0.17,
    "BEAR_LOW_VOL": 0.16, "BEAR_HIGH_VOL": 0.16
}
w_v7 = alloc.compute_information_theoretic_blend_weights(
    regime=regime_uniform,
    rvine_cascade_index=0.0,
    version=7
)
w_v8 = alloc.compute_information_theoretic_blend_weights(
    regime=regime_uniform,
    rvine_cascade_index=0.0,
    version=8
)
dev_v7 = sum((v - 0.25)**2 for v in w_v7.values())
dev_v8 = sum((v - 0.25)**2 for v in w_v8.values())
print("IEP dispersion reduction:", dev_v7, "->", dev_v8, "Reduced:", dev_v8 < dev_v7)

# 3. Portfolio Allocator weights validity (sum to 1, non-negative, bounds)
symbols = ["S1", "S2", "S3", "S4", "S5"]
n = len(symbols)
pred_ret = np.array([0.08, 0.05, 0.03, 0.02, -0.01])
cov = np.eye(n) * 0.04
df_rets = pd.DataFrame(np.random.normal(0, 0.02, size=(60, n)), columns=symbols)

w_res = alloc.optimize_multi_model_blend(
    predicted_returns=pred_ret,
    returns_df=df_rets,
    cov_matrix=cov,
    symbols=symbols,
    version=8
)
print("Allocated weights:", w_res)
print("Sum of weights:", np.sum(w_res))
print("All non-negative:", np.all(w_res >= -1e-6))
