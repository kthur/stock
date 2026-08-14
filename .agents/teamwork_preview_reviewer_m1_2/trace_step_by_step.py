"""
trace_step_by_step.py
"""
import numpy as np
import pandas as pd

np.random.seed(999)

N = 500
f_raw = np.random.standard_t(df=2, size=(N, 5))
y_raw = 0.85 * f_raw[:, 0] + 0.3 * np.random.randn(N)

cap_series = np.exp(np.clip(f_raw[:, 0] + 20, 10, 30))
per_series = np.clip(f_raw[:, 1] * 10 + 15, -100, 1000)
roe = f_raw[:, 2] * 5 + 10
cma = f_raw[:, 3] * 0.1
umd = f_raw[:, 4] * 0.2

# 4. Construct Fama-French 5-Factor Raw Series
f_smb = np.where(cap_series > 0, np.log(np.maximum(cap_series, 1.0)), np.nan)
val_from_pbr = np.full(N, np.nan)
val_from_per = np.where(
    per_series > 0,
    1.0 / np.maximum(per_series, 0.1),
    np.where(per_series < 0, -1.0 / np.maximum(np.abs(per_series), 0.1), np.nan)
)
f_hml = np.where(np.isfinite(val_from_pbr), val_from_pbr, val_from_per)
f_rmw = roe
f_cma = cma
f_umd = umd

F_m = np.column_stack([f_smb, f_hml, f_rmw, f_cma, f_umd])
y_m = y_raw.copy()

# Standardization
Z_m = np.zeros((N, 5))
for k in range(5):
    f_k = F_m[:, k]
    valid_mask = np.isfinite(f_k)
    med_k = float(np.nanmedian(f_k[valid_mask]))
    f_clean = np.where(valid_mask, f_k, med_k)
    f_std = float(np.std(f_clean, ddof=0))
    f_mean = float(np.mean(f_clean))
    Z_m[:, k] = (f_clean - f_mean) / f_std

X_m = np.column_stack([np.ones(N), Z_m])

Q_m, _ = np.linalg.qr(X_m, mode="reduced")
proj_coef = np.dot(Q_m.T, y_m)
y_pred = np.dot(Q_m, proj_coef)
residual = y_m - y_pred

print("Step 5 raw residual corr with Z_m[:, 0]:", np.corrcoef(Z_m[:, 0], residual)[0, 1])

# Step 6: SLA Gate
res_std = float(np.std(residual, ddof=0))
print("res_std:", res_std)
for k in range(5):
    z_k = Z_m[:, k]
    corr_val = float(np.corrcoef(z_k, residual)[0, 1])
    print(f"  Factor {k} corr with residual BEFORE SLA gate:", corr_val)

# Step 7: Robust scaling
p1, p99 = np.percentile(residual, 1), np.percentile(residual, 99)
denom = (p99 - p1) if (p99 - p1) > 1e-8 else 1.0
norm_scores = np.clip((residual - p1) / denom, 0.0, 1.0)

print("Percentiles p1, p99 of residual:", p1, p99)
print("Min, max of residual:", np.min(residual), np.max(residual))
print("Score corr with Z_m[:, 0] AFTER clipping:", np.corrcoef(Z_m[:, 0], norm_scores)[0, 1])
print("Score corr with log(market_cap) AFTER clipping:", np.corrcoef(f_smb, norm_scores)[0, 1])
