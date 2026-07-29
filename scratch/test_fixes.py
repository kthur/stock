import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Set cwd to trading_system
trading_sys_dir = Path(r"d:\Finance\code\stock\trading_system")
sys.path.insert(0, str(trading_sys_dir))
os.chdir(trading_sys_dir)

from src.ai.ensemble_scorer import EnsembleScoringEngine

print("Testing EnsembleScoringEngine fixes...")
scorer = EnsembleScoringEngine()

# Test DataFrame with preferred stock and SPAC
df = pd.DataFrame([
    {'symbol': '006490', 'name': '인스코비', 'reg_score': 0.84, 'surge_score': 0.40, 'vcp_ml_score': 0.83},
    {'symbol': '36328K', 'name': '티와이홀딩스우', 'reg_score': 0.96, 'surge_score': 0.43, 'vcp_ml_score': 0.76},
    {'symbol': '0131D0', 'name': '키움히어로제2호스팩', 'reg_score': 0.99, 'surge_score': 0.27, 'vcp_ml_score': 0.77},
    {'symbol': '005930', 'name': '삼성전자', 'reg_score': 0.75, 'surge_score': 0.50, 'vcp_ml_score': 0.60},
])

reg_df = df[['symbol', 'reg_score']].rename(columns={'reg_score': 20})
surge_df = df[['symbol', 'surge_score']].rename(columns={'surge_score': 'surge_20d'})
vcp_ml_df = df[['symbol', 'vcp_ml_score']].rename(columns={'vcp_ml_score': 'vcp_20d'})

res = scorer.calculate_ensemble_score(
    regime='BULL_LOW_VOL',
    regression_df=reg_df,
    surge_df=surge_df,
    lead_lag_df=pd.DataFrame(),
    vcp_ml_df=vcp_ml_df,
    target_horizon=20
)

res = res.merge(df[['symbol', 'name']], on='symbol', how='left')
print("\n--- Scored Results ---")
for idx, row in res.iterrows():
    print(f"Rank {idx+1}: {row['symbol']} | {row.get('name')} | Ens Score: {row['ensemble_score']*100:.1f}% | Expected Ret: {row['ensemble_expected_return']:.2f}%")

# Assertions
assert res.loc[res['symbol'] == '36328K', 'ensemble_score'].values[0] == 0.0, "Preferred stock failed Liquidity Gate filter!"
assert res.loc[res['symbol'] == '0131D0', 'ensemble_score'].values[0] == 0.0, "SPAC failed Liquidity Gate filter!"
assert res.loc[res['symbol'] == '005930', 'ensemble_score'].values[0] > 0.0, "Valid stock zeroed unexpectedly!"
assert res['ensemble_expected_return'].max() <= 50.0, "Expected return exceeded 50% cap!"

print("\nSUCCESS: All unit assertions passed cleanly!")
