# Comprehensive Quantitative & Financial Engineering Audit Report
**Milestone 1 — Financial Engineering & Quantitative Risk Audit**

---

## Executive Summary

This audit evaluates the 18-strategy automated stock trading system for quantitative biases, lookahead leakage, filing lag enforcement, survivorship bias, empirical risk metrics, and backtest/real-money deployment realism.

### Core Findings Matrix
| Audit Area | Critical Vulnerabilities Found | Severity | Primary Files / Lines |
|---|---|---|---|
| **1. Lookahead Bias & Filing Lag** | Unnamed `DatetimeIndex` bypasses 60-day filing lag via `join()` fallback; RIM valuation `.last()` fetch lacks temporal cutoff. | **HIGH** | `prediction_model.py`: 912–934<br>`run_pipeline.py`: 1971–1984 |
| **2. Survivorship Bias & Universe Selection** | Universe defined strictly by current active constituents (3,379 symbols); historical delisted stocks omitted from 5-year feature calculations. | **HIGH** | `indicator_storage.py`: 257–358 |
| **3. Empirical Risk Metrics** | Annual return calculation produces complex numbers on >100% loss; Sign convention mismatch for CVaR/VaR; `float("inf")` breaks JSON export. | **MEDIUM** | `statistics.py`: 90–91, 163–174, 232<br>`portfolio_allocator.py`: 51–170 |
| **4. Return Expectations & Deployment Realism** | Linear return scaling multiplier (20.0%) predicts unrealistic +20% 20-day returns; Short borrow fees missing; Hysteresis buffer distorts rankings. | **HIGH** | `ensemble_scorer.py`: 1091, 1118–1126, 1202–1226 |

---

## 1. Lookahead Bias & Filing Lag Audit

### 1.1 Observation & Code Evidence
In `trading_system/src/ai/prediction_model.py`:
- **Line 912–924**: The 60-day conservative filing lag is defined as:
  ```python
  df_fun_shifted['date_available'] = pd.to_datetime(df_fun_shifted['date']) + pd.Timedelta(days=60)
  df['date_align'] = pd.to_datetime(df[date_col])
  df = pd.merge_asof(
      df.sort_values('date_align'),
      df_fun_shifted.sort_values('date_available'),
      left_on='date_align',
      right_on='date_available',
      direction='backward',
      suffixes=('', '_fund')
  )
  ```
- **Line 927–934 (CRITICAL BUG)**: If `df` has an unnamed `DatetimeIndex` when entering `merge_fundamentals()`, `df.reset_index()` names the index column `'index'`, rather than `'Date'` or `'date'`.
  The column detection loop `for col in ['Date', 'date']` fails to match `'index'`, setting `date_col = None`.
  Execution then falls through to line 927 `else:`:
  ```python
  else:
      try:
          df['index'] = pd.to_datetime(df['index'])
      except Exception:
          pass
      df = df.set_index('index')
      df_fun = df_fun.set_index('date')
      df = df.join(df_fun, how='left')
  ```
  `df.join(df_fun, how='left')` joins fundamental records directly on the exact fiscal end date (`date`), **completely bypassing the 60-day filing lag**!

- **In `trading_system/run_pipeline.py` (Lines 1971–1984)**:
  ```python
  fund_df = storage.get_all_fundamentals(df_rim_input['symbol'].tolist())
  if fund_df is not None and not fund_df.empty:
      fund_df = fund_df.sort_values('date').groupby('symbol').last().reset_index()
  ```
  `fund_df.sort_values('date').groupby('symbol').last()` fetches the absolute latest filing available in the DB. When evaluating backtests or historical simulation dates, this injects future fiscal statements that were not yet published on the evaluation date.

- **In `prediction_model.py` (Line 860)**:
  ```python
  FUND_COLS = ['revenue', 'operating_income', 'net_income', 'eps', 'dividend_per_share']
  ```
  `book_value` (BPS) was added to `earnings_data.py` (Line 80), but is missing from `prediction_model.py`'s `FUND_COLS`.

### 1.2 Impact Analysis
- Backtesting on price series with unnamed index silent leaks future corporate earnings (e.g. Q4 earnings released in March are joined directly to January price bars), inflating backtest Sharpe ratios and regression accuracy.
- Historical RIM evaluations leak future Book Value and Net Income.

### 1.3 Recommended Fixes
1. **Fix `prediction_model.py` Index Detection**:
   ```python
   # Replace lines 905-911 with explicit index/column normalization:
   if df.index.name is None:
       df.index.name = 'date'
   df = df.reset_index()
   date_col = None
   for col in ['Date', 'date', 'index']:
       if col in df.columns:
           date_col = col
           break
   ```
2. **Fix RIM Fundamental Merge cutoff in `run_pipeline.py`**:
   Filter `fund_df` by `pd.to_datetime(fund_df['date']) + pd.Timedelta(days=60) <= evaluation_date`.
3. **Include `book_value` in `FUND_COLS`**:
   Add `'book_value'` to `FUND_COLS` in `prediction_model.py:860`.

---

## 2. Survivorship Bias & Universe Selection Audit

### 2.1 Observation & Code Evidence
In `trading_system/src/data_layer/indicator_storage.py` (Lines 257–358):
```python
def update_stock_universe(self):
    sp500 = fdr.StockListing('S&P500')
    nasdaq = fdr.StockListing('NASDAQ')
    russell2000 = ... # iShares IWM CSV holdings
    krx = fdr.StockListing('KRX')
    ...
```
- `update_stock_universe()` queries live constituent lists as of the execution date.
- The 3,379 symbols stored in `stock_universe` represent only surviving companies today.
- `update_stock_universe()` explicitly excludes `KRX-ADMINISTRATIVE` stocks at present (line 301).

### 2.2 Impact Analysis
- Historical feature calculations (e.g. 5-year rolling correlation, sector relative momentum in `sector_rotation.py`, lead-lag correlation matrices in `prediction_model.py`, and factor quantiles in `mq_factor.py`) are computed exclusively over surviving stocks.
- Delisted stocks, bankrupt entities, or acquired companies from 2021–2026 are omitted. Because bankrupt/delisted stocks suffer heavy drawdowns before exit, omitting them introduces **Survivorship Bias**, artificially inflating historical backtest returns and underestimating tail risk (CVaR).

### 2.3 Recommended Fixes
1. Maintain point-in-time universe snapshots (`universe_history` table) containing historical index membership and delisting dates.
2. For historical backtesting, filter universe to assets active as of each historical rebalance date.

---

## 3. Empirical Risk Metrics Audit

### 3.1 Observation & Code Evidence

#### 3.1.1 Annual Return Complex Number Bug
In `trading_system/src/analysis/statistics.py` (Line 232):
```python
annual_return = (1 + total_return) ** (252 / n) - 1 if n > 0 else 0
```
- If a strategy or trade sequence suffers a drawdown > 100% (`total_return < -1.0`), `(1 + total_return)` becomes negative.
- Exponentiation of negative float to a fractional power `(-0.2) ** (252 / 100)` produces a **complex number** (e.g. `-0.03 + 0.12j`), causing `TypeError` or corrupting downstream calculations and JSON serialization.

#### 3.1.2 Sign Convention Mismatch in VaR / CVaR
- In `trading_system/src/risk/portfolio_allocator.py` (Lines 51–170):
  `losses = -returns_arr`. Losses are positive numbers; `estimate_evt_cvar` returns **positive loss percentages** (e.g. `cvar = 0.04` for 4% tail loss).
- In `trading_system/src/analysis/statistics.py` (Lines 153–175):
  `calculate_var` and `calculate_cvar` compute empirical quantiles directly on signed returns $R$. They return **negative return values** (e.g. `cvar = -0.04`).
- Calling modules expecting positive loss numbers will misinterpret negative numbers (e.g., `max_cvar - cvar_val` constraint logic in portfolio optimization).

#### 3.1.3 Sortino Ratio `float("inf")` Serialization Issue
In `trading_system/src/analysis/statistics.py` (Lines 90–91):
```python
if not downside_returns:
    return float("inf") if avg_return > target_return else 0
```
- Returning `float("inf")` causes standard `json.dumps()` calls to fail with `ValueError: Out of range float values are not JSON compliant`.

#### 3.1.4 EVT-CVaR Robustness (`portfolio_allocator.py`)
In `trading_system/src/risk/portfolio_allocator.py` (Lines 110–128):
- Tier 1 EVT-GPD implementation clamps `xi_clamped = min(xi, 0.50)` which safely avoids division by zero in `(1.0 - xi_clamped)`.
- Tier 2 Cornish-Fisher expansion and Tier 3 Empirical fallback provide robust multi-tier fallback.

### 3.2 Recommended Fixes
1. **Fix `annual_return` in `statistics.py:232`**:
   ```python
   annual_return = (max(0.0, 1.0 + total_return)) ** (252 / n) - 1.0 if n > 0 else 0.0
   ```
2. **Standardize VaR/CVaR Sign Convention**:
   Ensure `statistics.py` returns positive loss values (`cvar = float(max(0.0, -mean_worse_return))`).
3. **Cap Sortino Ratio**:
   Replace `float("inf")` with a finite maximum float cap (e.g., `100.0`).

---

## 4. Backtest Calculations & Return Expectations Realism

### 4.1 Observation & Code Evidence

#### 4.1.1 Unrealistic Expected Return Scaling
In `trading_system/src/ai/ensemble_scorer.py` (Lines 1118–1126):
```python
mult = self._return_multiplier if self._return_multiplier <= 1.0 else (self._return_multiplier / 100.0)
raw_exp_ret = merged['ensemble_score'] * mult * 100.0
```
- `self._return_multiplier` defaults to `20.0`.
- For `ensemble_score = 1.0`, `raw_exp_ret = 1.0 * (20.0 / 100.0) * 100.0 = 20.0%` net 20-day expected return (~250% annualized).
- Subtracting ~0.50% micro-costs yields `19.50%` net expected return per 20-day period.
- **Unrealistic Assumption**: Real-world quantitative equity factor signals yield net alpha of 0.5% ~ 2.5% per 20-day horizon (6% ~ 30% annualized). Scaling raw scores linearly to +20.0% sets uncalibrated, overly aggressive return expectations.

#### 4.1.2 Omission of Short Borrow Fees
In `trading_system/src/ai/ensemble_scorer.py` (Lines 1137–1224) & `backtest.py` (Lines 105–149):
- Micro-cost model computes STT tax, SEC fees, brokerage fees, dynamic bid-ask spread, and market impact.
- **Omission**: For short-side signals (e.g. Stat-Arb pairs short leg, short-term reversal short entry), short borrow fees (which range from 1% to 15%+ p.a. for hard-to-borrow equities) and borrow locate availability constraints are omitted.

#### 4.1.3 Turnover Hysteresis Buffer Distortion
In `trading_system/src/ai/ensemble_scorer.py` (Line 1091):
```python
blended_score.loc[held_mask] = (blended_score.loc[held_mask] + 0.05).clip(upper=1.0)
```
- Adding a flat `+0.05` bonus to currently held symbols reduces turnover, but it distorts the calibrated cross-sectional score ranking without accounting for holding period duration or alpha decay.

#### 4.1.4 Isotonic Calibration Target Mismatch
In `ensemble_scorer.py` (Lines 335–350):
- `fit_calibrators()` fits Isotonic Regression on historical outcomes defined as `>20% gain in 20 days`.
- Using an extreme tail surge binary target for calibrating mean-reversion, valuation, and sector rotation models miscalibrates probability estimates for non-surge strategies.

### 4.2 Recommended Fixes
1. **Calibrate `_return_multiplier`**:
   Adjust `_return_multiplier` to a realistic quantitative alpha range (e.g. `2.0` ~ `3.0` for 20-day horizon, corresponding to +2.0% ~ +3.0% max expected return).
2. **Add Short Borrow Fee Model**:
   Deduct annualized short borrow fee (e.g., 1.5% p.a. default, higher for small-caps) for short positions.
3. **Refine Hysteresis Buffer**:
   Scale the hysteresis bonus dynamically based on position age and transaction cost avoidance, rather than a static +0.05 offset.
4. **Strategy-Specific Calibration Targets**:
   Use strategy-appropriate target metrics (e.g. positive excess return over benchmark for RIM/Sector Rotation, rather than >20% tail surge).
