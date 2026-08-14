"""
diagnose_details.py
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from trading_system.src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine

np.random.seed(999)
engine = MultiFactorNeutralizerEngine()

N = 1000
f_raw = np.random.standard_t(df=2, size=(N, 5))
y_raw = 0.85 * f_raw[:, 0] + 0.3 * np.random.randn(N)

df = pd.DataFrame({
    "symbol": [f"S_{i}" for i in range(N)],
    "market": ["KOSPI"] * (N // 2) + ["KOSDAQ"] * (N // 2),
    "market_cap": np.exp(np.clip(f_raw[:, 0] + 20, 10, 30)),
    "per": np.clip(f_raw[:, 1] * 10 + 15, -100, 1000),
    "roe": f_raw[:, 2] * 5 + 10,
    "asset_growth_yoy": f_raw[:, 3] * 0.1,
    "momentum_12m": f_raw[:, 4] * 0.2,
    "score": y_raw
})

# Look at per in df:
# In df, per is generated from f_raw[:, 1] * 10 + 15.
# In multi_factor_neutralizer.py:
# Line 201: pbr_series and per_series.
# In df, there is NO "pbr" column!
# So val_from_pbr is NaN.
# val_from_per:
# np.where(per > 0, 1.0 / max(per, 0.1), np.where(per < 0, -1.0 / max(abs(per), 0.1), nan))
# Notice: f_hml in the engine is 1 / per (E/P yield)!
# BUT in test_heavy_tail_clipping_sla(), what did the test correlate?
# In test_heavy_tail_clipping_sla(), it correlated with market_cap (log(market_cap)), roe, asset_growth_yoy, momentum_12m.

res = engine.compute_scores(df)

# Let's inspect KOSPI alone
eval_df = pd.merge(df, res[['symbol', 'factor_neutralized_score']], on='symbol')
k_df = eval_df.iloc[:500] # First 500 are KOSPI
q_df = eval_df.iloc[500:] # Last 500 are KOSDAQ

print("KOSPI Size correlation:", k_df['factor_neutralized_score'].corr(np.log(k_df['market_cap'])))
print("KOSDAQ Size correlation:", q_df['factor_neutralized_score'].corr(np.log(q_df['market_cap'])))
print("POOLED Size correlation:", eval_df['factor_neutralized_score'].corr(np.log(eval_df['market_cap'])))
