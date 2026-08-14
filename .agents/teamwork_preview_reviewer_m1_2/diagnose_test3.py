"""
diagnose_test3.py — Diagnose correlation leakage in Test 3
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

res = engine.compute_scores(df)
eval_df = pd.merge(df, res, on="symbol")

print("Overall pooled correlation:")
for col in ["market_cap", "per", "roe", "asset_growth_yoy", "momentum_12m"]:
    if col == "market_cap":
        x = np.log(eval_df[col])
    else:
        x = eval_df[col]
    print(f"  {col}: Pearson={eval_df['factor_neutralized_score'].corr(x):.4f}")

print("\nPer-market correlation in KOSPI:")
k_df = eval_df[eval_df["market"] == "KOSPI"]
for col in ["market_cap", "per", "roe", "asset_growth_yoy", "momentum_12m"]:
    if col == "market_cap":
        x = np.log(k_df[col])
    else:
        x = k_df[col]
    print(f"  {col}: Pearson={k_df['factor_neutralized_score'].corr(x):.4f}")

print("\nPer-market correlation in KOSDAQ:")
q_df = eval_df[eval_df["market"] == "KOSDAQ"]
for col in ["market_cap", "per", "roe", "asset_growth_yoy", "momentum_12m"]:
    if col == "market_cap":
        x = np.log(q_df[col])
    else:
        x = q_df[col]
    print(f"  {col}: Pearson={q_df['factor_neutralized_score'].corr(x):.4f}")
