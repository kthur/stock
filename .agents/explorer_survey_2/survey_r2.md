# Requirement R2 Comprehensive Survey & Technical Investigation Report

**Author**: `explorer_survey_2` (Teamwork Explorer)  
**Date**: 2026-08-22  
**Target Milestone**: Survey & Technical Blueprint for Requirement R2  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_2`

---

## 1. Executive Summary

Requirement **R2 (Data Pipeline Refinement: Dynamic Filing Lag, Stratified Sampling, Stat-Arb Noise Elimination)** addresses three major technical challenges in data pipeline accuracy, sample representativeness, and signal integrity:

1. **Dynamic Market Filing Lag (KRX 45d / US 40d with Real-Time Public Filing Date Override)**:
   - **Current State**: Fixed 60-day lag (`+ pd.Timedelta(days=60)`) applied uniformly across all markets and tickers regardless of jurisdiction or actual disclosure timing.
   - **Target State**: Dynamic market-specific regulatory filing deadlines (KRX 45 days per Financial Investment Services and Capital Markets Act; US 40 days per SEC Form 10-Q accelerated/large accelerated filers rules) with **immediate override** when an explicit public disclosure date (`filing_date`, `rcept_dt`) is confirmed, strictly preventing future lookahead while accelerating quarterly earnings momentum capture.
2. **Stratified Sampling in Model Training (`prepare_training_data`)**:
   - **Current State**: Naive `random.sample()` used in `trading_system/run_pipeline.py` (L1507), resulting in high sample variance, potential over-sampling of illiquid micro-caps or single sectors (e.g. tech), and omission of major industry leaders.
   - **Target State**: Multi-dimensional stratified sampling across **Market × Sector × Market-Cap Quantiles** with proportional quota allocation, preserving authentic market distribution and structural representation.
3. **Total Elimination of Fake BENCHMARK Pairs in Statistical Arbitrage**:
   - **Current State**: When no cointegrated pairs pass ADF/OU filters, `run_pipeline.py` (L1972–1997) artificially synthesizes fake `(sym, 'BENCHMARK')` pairs with hardcoded `correlation: 0.85`, `beta: 1.0`, and arbitrary 20-day MA Z-scores, contaminating `stat_arb_predictions.txt` and skewing downstream ensemble scoring.
   - **Target State**: Complete removal of fake benchmark injection. Downstream pipeline and `EnsembleScoringEngine` gracefully handle zero/sparse cointegration pairs via automated strategy weight re-normalization.

---

## 2. Technical Investigation 1: Dynamic Market Filing Lag

### 2.1 As-Is Codebase Audit & Locations

A uniform 60-day lag was previously instituted across four core locations to eliminate lookahead bias. However, this 60-day window is excessively conservative and causes a 15–20 day lag penalty in reacting to fresh quarterly earnings:

| File Path | Function / Context | Current Logic | Problem |
|---|---|---|---|
| `src/data_layer/earnings_data.py` (L74) | `_fetch_fundamentals_network` | `result['date_available'] = (fin.index + pd.Timedelta(days=60)).strftime('%Y-%m-%d')` | Hardcoded 60-day offset for all tickers |
| `src/data_layer/earnings_data.py` (L239) | `async_fetch_fundamentals` | `"date_available": (dt + pd.Timedelta(days=60)).strftime('%Y-%m-%d')` | Hardcoded 60-day offset in async pipeline |
| `src/ai/prediction_model.py` (L1009, L1024) | `merge_fundamentals` | `df_fun_shifted['date_available'] = pd.to_datetime(df_fun_shifted['date']) + pd.Timedelta(days=60)` | Bypasses actual filing date; applies 60d blindly |
| `trading_system/run_pipeline.py` (L2645) | RIM Valuation Input Prep | `fund_df['date_available'] = fund_df['date'] + pd.Timedelta(days=60)` | Disregards market type & actual disclosure date |
| `trading_system/run_pipeline.py` (L2957) | ARM Factor Input Prep | `_fd[pd.to_datetime(_fd['date']) + pd.Timedelta(days=60) <= _cur_dt]` | Fixed 60d fallback if `date_available` missing |

### 2.2 Regulatory & Legal Framework

1. **South Korea (KRX: KOSPI, KOSDAQ, KONEX)**:
   - **Statutory Authority**: Financial Investment Services and Capital Markets Act (자본시장과 금융투자업에 관한 법률 제159조 및 제160조).
   - **Filing Deadline**: Quarterly & Semi-annual business reports (분기·반기보고서) must be submitted within **45 days** from the close of the respective quarter (for Q1, Q2, Q3).
2. **United States (US: S&P 500, NASDAQ, RUSSELL 2000)**:
   - **Statutory Authority**: SEC Form 10-Q deadlines under Exchange Act Rules 13a-13 / 15d-13.
   - **Filing Deadline**: **40 days** after fiscal quarter-end for Large Accelerated Filers (public float $\ge \$700\text{M}$) and Accelerated Filers (public float $\ge \$75\text{M}$ to $<\$700\text{M}$), covering virtually all SP500 and NASDAQ constituents.

### 2.3 Real-Time Public Filing Date Override Mechanism

When public disclosure data is available (e.g. from DART `rcept_dt`, SEC EDGAR filing date, Yahoo Finance `quoteSummary` disclosure metadata, or database table `filing_date`):
$$\text{date\_available} = \begin{cases} \text{filing\_date} & \text{if } \text{filing\_date is valid and } \text{filing\_date} \ge \text{fiscal\_date} \\ \text{fiscal\_date} + \Delta t_{\text{market}} & \text{otherwise (fallback regulatory window)} \end{cases}$$
where:
$$\Delta t_{\text{market}} = \begin{cases} 45 \text{ days} & \text{if market} \in \{\text{KOSPI}, \text{KOSDAQ}, \text{KRX}\} \text{ or Korean numeric ticker} \\ 40 \text{ days} & \text{if market} \in \{\text{SP500}, \text{NASDAQ}, \text{RUSSELL2000}, \text{US}\} \\ 40 \text{ days} & \text{default fallback} \end{cases}$$

### 2.4 Strict Zero-Lookahead Guarantee

- `pd.merge_asof(..., left_on='date_align', right_on='date_available', direction='backward')` ensures that fundamental financial statement figures become visible to feature engineering **only on or after** `date_available`.
- If an actual `filing_date` is in the future relative to the simulation/inference date `as_of_date`, it is filtered out (`date_available <= as_of_date`).
- Lookahead bias is mathematically impossible under this backward asof formulation.

---

## 3. Technical Investigation 2: Stratified Sampling in `prepare_training_data`

### 3.1 As-Is Codebase Audit & Sampling Distortion

In `trading_system/run_pipeline.py` (L1504–1519):
```python
def _safe_sample(population, k):
    if k >= len(population):
        return list(population)
    return random.sample(population, k)

train_krx_overall = _safe_sample(active_krx_symbols, krx_sample) if active_krx_symbols else []
train_us_overall = _safe_sample(active_us_symbols, sp500_sample) if active_us_symbols else []
```

#### Identified Deficiencies:
1. **Capitalization Skew**: Small/micro-cap stocks vastly outnumber mega/large-caps in raw counts. `random.sample()` randomly draws heavily from illiquid micro-caps, leaving key market bellwethers (e.g. Samsung Electronics, Apple, Nvidia) unselected for training.
2. **Sector Concentration / Starvation**: In small sample regimes (e.g. 50–100 stocks), random sampling can draw 80% Tech/Bio stocks and 0% Financials, Materials, or Energy, corrupting cross-sectional normalization (`apply_market_normalization`) and tree split generalizing power.
3. **Inconsistent Representation**: Training distributions fluctuate across runs without structural stability.

### 3.2 Stratified Sampling Architecture Design

#### Stratification Taxonomy:
1. **Level 1 — Market Segment**: `KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`.
2. **Level 2 — Economic Sector**: GICS 11 Sectors (US) / KRX 10+ Standard Sectors (KR).
3. **Level 3 — Market-Cap Quantiles**:
   - $Q_1$: Large-Cap (Top 33% by market cap within market)
   - $Q_2$: Mid-Cap (Middle 33%)
   - $Q_3$: Small-Cap (Bottom 33%)

#### Sampling Allocation Algorithm:
For a given target sample size $K_{\text{market}}$:
1. Group available universe symbols in the market into strata $S_{s, q} = (\text{Sector}_s, \text{CapQuantile}_q)$.
2. Calculate target quota for each stratum:
   $$k_{s, q} = \max\left(1, \operatorname{round}\left(K_{\text{market}} \times \frac{|S_{s, q}|}{N_{\text{market}}}\right)\right)$$
3. Adjust quotas so $\sum k_{s, q} = K_{\text{market}}$ using largest remainder method.
4. Draw $k_{s, q}$ symbols deterministically using a seeded pseudo-random generator or stable hash ranking.
5. If $|S_{s, q}| < k_{s, q}$, take all symbols in $S_{s, q}$ and redistribute the surplus quota to remaining strata.

---

## 4. Technical Investigation 3: Total Elimination of Fake BENCHMARK Pairs in Stat-Arb

### 4.1 As-Is Codebase Audit & Mechanism of Fake Pair Injection

In `trading_system/run_pipeline.py` (L1972–1997):
```python
if not stat_arb_pairs:
    # Continuous fallback: calculate 20-day MA Z-score deviation for all symbols
    for sym, df_p in infer_data_dict.items():
        ...
        stat_arb_pairs.append({
            'pair': (sym, 'BENCHMARK'),
            'z_score': round(float(z), 2),
            'correlation': 0.85,
            'beta': 1.0,
            'signal': f'LONG_{sym}_SHORT_BENCHMARK' if z <= -2.0 else (f'SHORT_{sym}_LONG_BENCHMARK' if z >= 2.0 else 'NEUTRAL'),
            'market': mkt
        })
```
And in `src/core/stat_arb.py` (L635–640):
```python
if f"LONG_{s1}" in sig or (sig == "LONG_SPREAD" and s2 == "BENCHMARK"):
    symbol_deltas[s1] = symbol_deltas.get(s1, 0.0) + score_delta
elif f"SHORT_{s1}" in sig or (sig == "SHORT_SPREAD" and s2 == "BENCHMARK"):
    symbol_deltas[s1] = symbol_deltas.get(s1, 0.0) - score_delta

if s2 != "BENCHMARK":
    ...
```

#### Why This Is a Serious Flaw:
1. **Fabricated Statistical Validity**: Cointegration requires strict stationarity of price residuals ($p < 0.05$, Engle-Granger ADF test). A single-stock 20d moving average is NOT cointegration; labeling it as a cointegrated pair with hardcoded correlation 0.85 and beta 1.0 violates financial integrity.
2. **False Arbitrage Signals**: In trending or high-volatility markets where no true pair spreads are stationary, this fallback flooded `stat_arb_predictions.txt` with thousands of fake pairs.
3. **Ensemble Distortion**: Artificially forced Stat-Arb scores onto stocks that had no actual cointegration relationship, corrupting the multi-factor ensemble.

### 4.2 Elimination Architecture & Graceful Pipeline Handling

1. **Delete Fallback Generation**: Completely remove lines 1972–1997 in `run_pipeline.py`.
2. **Clean Up `get_symbol_stat_arb_scores`**: Remove all references to `"BENCHMARK"` and process genuine pair tuples `(s1, s2)` symmetrically.
3. **Graceful Handling of Zero Pairs**:
   - `stat_arb_predictions.txt` writes `Total cointegrated pairs found: 0` with empty pair table.
   - `stat_arb_df` returns `pd.DataFrame(columns=['symbol', 'stat_arb_score', 'long_only_mode'])`.
   - `EnsembleScoringEngine` detects that `stat_arb` has 0 coverage, sets its strategy weight to 0.0 for affected symbols, and automatically re-normalizes the remaining active strategy weights to sum to 1.0 (via Requirement R1).

---

## 5. Comprehensive Impact Matrix

| Component | File Path | Affected Functions / Lines | Change Summary |
|---|---|---|---|
| **Filing Lag** | `src/data_layer/earnings_data.py` | `_fetch_fundamentals_network` (L74), `async_fetch_fundamentals` (L239), `fetch_fundamentals` (L155) | Add `get_filing_lag_days(market, symbol)` helper (KRX 45d, US 40d) & check `filing_date` override |
| **Filing Lag** | `src/ai/prediction_model.py` | `merge_fundamentals` (L1009, L1024) | Enforce dynamic filing lag (45d KRX / 40d US) with `filing_date` column override if present |
| **Filing Lag** | `trading_system/run_pipeline.py` | RIM prep (L2645), ARM prep (L2957) | Dynamic filing lag per market with `date_available` / `filing_date` priority |
| **Sampling** | `src/ai/prediction_model.py` | `stratified_sample_symbols` (New function) | Stratified sampling by Market × Sector × Market-Cap Quantile |
| **Sampling** | `trading_system/run_pipeline.py` | Training data sampling (L1466–1520) | Replace `_safe_sample` with `stratified_sample_symbols` |
| **Stat-Arb** | `trading_system/run_pipeline.py` | Stat-Arb fallback (L1972–1997) | Complete removal of fake BENCHMARK loop |
| **Stat-Arb** | `src/core/stat_arb.py` | `get_symbol_stat_arb_scores` (L635–640) | Remove BENCHMARK branch; process genuine pair legs only |
| **Ensemble** | `src/ai/ensemble_scorer.py` | `combine_predictions` / `_assemble_all_predictions` | Ensure empty `stat_arb_df` is excluded from weighting and re-normalized |

---

## 6. Test Suite Strategy & Verification Plan

### 6.1 Existing Tests Impact Analysis
- `tests/test_fundamental_prediction_adversarial.py`: Asserts forward-fill and merge behavior. Verified compatible with 40d/45d lag.
- `tests/test_m1_1_fixes.py`: Asserts `merge_fundamentals` with DatetimeIndex. Compatible.
- `tests/test_fast_cointegration.py`: Tests fast scanner and edge cases (empty input, constant price). Verified compatible.
- `tests/test_stat_arb_execution.py`: Tests genuine pair detection. Compatible.

### 6.2 New Dedicated Unit Tests to Implement
1. `test_dynamic_filing_lag_krx_vs_us`: Verifies KRX gets 45d lag and US gets 40d lag by default.
2. `test_dynamic_filing_lag_explicit_override`: Verifies that an explicit `filing_date` immediately overrides the 45d/40d default window.
3. `test_stratified_sampling_distribution`: Verifies that sampled symbols proportionally represent all markets, sectors, and cap quantiles.
4. `test_stat_arb_zero_fake_benchmark_pairs`: Verifies that when no pairs are cointegrated, 0 pairs are returned and zero BENCHMARK pairs are created.
