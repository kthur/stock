# Handoff Report — Requirement R2 Technical Investigation & Blueprint

**Agent**: `explorer_survey_2`  
**Role**: Teamwork Explorer (Investigation & Synthesis)  
**Date**: 2026-08-22  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_2`  
**Related Report**: `d:\Finance\code\stock\.agents\explorer_survey_2\survey_r2.md`

---

## 1. Observation

Direct observations from source code inspection:

1. **Fixed 60-Day Filing Lag**:
   - `trading_system/src/data_layer/earnings_data.py` (L74): `result['date_available'] = (fin.index + pd.Timedelta(days=60)).strftime('%Y-%m-%d')` enforces a static 60-day lag on synchronous fundamental fetch.
   - `trading_system/src/data_layer/earnings_data.py` (L239): `"date_available": (dt + pd.Timedelta(days=60)).strftime('%Y-%m-%d')` enforces a static 60-day lag on asynchronous fundamental fetch.
   - `trading_system/src/ai/prediction_model.py` (L1009, L1024): `df_fun_shifted['date_available'] = pd.to_datetime(df_fun_shifted['date']) + pd.Timedelta(days=60)` applies static 60-day lag when merging fundamentals onto prices.
   - `trading_system/run_pipeline.py` (L2645, L2957): Static 60-day lag applied during RIM input preparation and ARM factor calculation.
   - *Observation Detail*: The 60-day lag causes a 15–20 day unnecessary delay for Korean quarterly reports (statutory deadline: 45 days) and US quarterly 10-Q filings (statutory deadline: 40 days for accelerated/large accelerated filers). Furthermore, when real-time disclosure dates (`filing_date` or `rcept_dt`) exist, they are ignored in favor of the static 60-day offset.

2. **Naive Random Sampling in Training Data Preparation**:
   - `trading_system/run_pipeline.py` (L1504–1519):
     ```python
     def _safe_sample(population, k):
         if k >= len(population):
             return list(population)
         return random.sample(population, k)
     train_krx_overall = _safe_sample(active_krx_symbols, krx_sample) if active_krx_symbols else []
     train_us_overall = _safe_sample(active_us_symbols, sp500_sample) if active_us_symbols else []
     ```
   - *Observation Detail*: `random.sample()` selects tickers with uniform probability. Because small-caps outnumber large-caps by ~5:1, random sampling underrepresents mega/large caps and frequently produces sector imbalances (e.g. over-concentrating in technology and starving financial/industrial sectors).

3. **Fake BENCHMARK Pair Injection in Statistical Arbitrage**:
   - `trading_system/run_pipeline.py` (L1972–1997):
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
   - `trading_system/src/core/stat_arb.py` (L635–640): Leftover special cases checking `s2 == "BENCHMARK"`.
   - *Observation Detail*: When no statistically valid cointegrated pairs exist (e.g. in trending markets), this fallback manufactures fake benchmark pairs with hardcoded correlation 0.85 and beta 1.0 based on simple 20-day moving averages. This pollutes `stat_arb_predictions.txt` and distorts ensemble scoring.

---

## 2. Logic Chain

1. **Dynamic Filing Lag Rationale**:
   - *Step 1*: South Korea's Capital Markets Act mandates quarterly filing within 45 days. US SEC Form 10-Q mandates filing within 40 days for accelerated/large accelerated filers.
   - *Step 2*: Replacing the static 60-day lag with 45d (KRX) and 40d (US) aligns the model with legal disclosure deadlines, accelerating earnings momentum recognition by 15–20 days.
   - *Step 3*: When an authentic public filing date (`filing_date`, `rcept_dt`) is available and confirmed to be $\le \text{as\_of\_date}$, setting $\text{date\_available} = \text{filing\_date}$ immediately incorporates earnings data into the causal time series.
   - *Step 4*: The existing `pd.merge_asof(..., direction='backward')` structure guarantees zero lookahead bias because fundamentals are merged strictly up to each trading date.

2. **Stratified Sampling Rationale**:
   - *Step 1*: Training on a representative cross-section of the market is essential for cross-sectional normalization (`apply_market_normalization`) and model generalization across market regimes.
   - *Step 2*: Grouping the universe by `(Market, Sector, Market-Cap Quantile)` partitions the universe into homogeneous sub-populations.
   - *Step 3*: Allocating sample quotas proportionally to strata sizes ($k_{s,q} \propto |S_{s,q}|$) ensures that large, mid, and small caps across all economic sectors are reliably represented in the training set in every run.
   - *Step 4*: Seeding the sampling guarantees deterministic reproducibility for backtesting and production stability.

3. **Fake BENCHMARK Pair Elimination Rationale**:
   - *Step 1*: Statistical arbitrage relies on the stationarity of price residuals ($p < 0.05$ Engle-Granger ADF test, OU half-life $< 40$ days).
   - *Step 2*: A single stock's 20-day moving average Z-score is a trend/momentum indicator, not cointegration. Packaging it as a cointegrated pair with hardcoded correlation 0.85 and beta 1.0 is statistically invalid.
   - *Step 3*: When no pairs pass cointegration tests, returning 0 pairs is the statistically honest outcome.
   - *Step 4*: Under Requirement R1's dynamic weight re-normalization, an empty `stat_arb_df` naturally receives 0% weight, and the remaining active strategies are re-normalized to 100%, completely avoiding ensemble skew without fabricating dummy data.

---

## 3. Caveats

1. **Market Metadata Availability**: In offline mode or synthetic tests where sector or market cap is not populated in `universe`, stratified sampling must gracefully fall back to market-only or uniform stratification without raising exceptions.
2. **Backward Compatibility with Existing Tests**: Tests asserting fundamental alignment (e.g. `test_fundamental_prediction_adversarial.py`) test chronological forward-filling. The 40d/45d window retains exact backward compatibility while reducing latency.
3. **Empty Stat-Arb Result**: Downstream report generators and text formatters must cleanly output `Total cointegrated pairs found: 0` without KeyError or division-by-zero errors when `stat_arb_pairs` is empty.

---

## 4. Conclusion

All three components of Requirement R2 are fully analyzed and architected:
1. **Dynamic Filing Lag**: Implement `get_filing_lag_days(market, symbol)` (KRX 45d, US 40d) with immediate `filing_date` override across `earnings_data.py`, `prediction_model.py`, and `run_pipeline.py`.
2. **Stratified Sampling**: Implement `stratified_sample_symbols(universe, sample_size, market, seed)` in `prediction_model.py` and replace `random.sample()` in `run_pipeline.py`.
3. **Total Fake Pair Removal**: Delete lines 1972–1997 in `run_pipeline.py` and clean up `src/core/stat_arb.py`, letting `EnsembleScoringEngine` handle zero/sparse pairs via dynamic weight re-normalization.

---

## 5. Verification Method

1. **Unit Test Suite Execution**:
   ```bash
   .venv/Scripts/pytest tests/ -v
   ```
2. **Dedicated Unit Tests to Implement**:
   - `test_dynamic_filing_lag_krx_vs_us`: Verify 45d lag for KOSPI/KOSDAQ and 40d lag for SP500/NASDAQ/RUSSELL2000.
   - `test_dynamic_filing_lag_explicit_override`: Verify `filing_date` immediately takes precedence.
   - `test_stratified_sampling_distribution`: Verify all market/sector/market-cap strata are represented proportionally.
   - `test_stat_arb_zero_fake_benchmark_pairs`: Verify 0 fake pairs are generated when input prices are uncorrelated random walks.
3. **Pipeline Verification**:
   - Run pipeline in test/demo mode and inspect `stat_arb_predictions.txt` to confirm no `(sym, 'BENCHMARK')` pairs appear.
