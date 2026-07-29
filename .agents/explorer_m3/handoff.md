# Handoff Report: Data Pipeline, Missingness & Lookahead Bias Audit

**Auditor**: Explorer M3 (Data Pipeline & Lookahead Auditor)  
**Target Scope**: 3,379 symbols across KOSPI, KOSDAQ, KONEX, and SP500  
**Target Files**:
- `trading_system/run_pipeline.py`
- `trading_system/src/analysis/coverage_analyzer.py`
- `trading_system/src/data_layer/earnings_data.py`
- `trading_system/src/persistence/database.py`
- `trading_system/src/data_layer/indicator_storage.py`
- `trading_system/src/ai/prediction_model.py`
- `trading_system/src/ai/ensemble_scorer.py`

---

## 1. Observation

### Focus Area 1: Point-in-Time Data Integrity
1. **Fiscal End Date vs. Filing Disclosure Date Leak**:
   - `earnings_data.py` lines 53–56 & lines 167–177:
     ```python
     54: fin.index = pd.to_datetime(fin.index)
     ...
     167: end_date_str = item.get("endDate", {}).get("fmt")
     177: "date_align": pd.to_datetime(end_date_str)
     ```
     Financial metrics (`revenue`, `operating_income`, `net_income`, `eps`, `book_value`) fetched from Yahoo Finance are indexed solely by fiscal period end dates (`endDate`, e.g., `2023-12-31`). Actual SEC 10-K/10-Q or DART disclosure/filing dates are neither fetched nor stored.
   - `indicator_storage.py` lines 101–111:
     ```sql
     CREATE TABLE IF NOT EXISTS stock_fundamentals (
         symbol TEXT,
         date TEXT,
         revenue REAL,
         operating_income REAL,
         net_income REAL DEFAULT 0,
         eps REAL DEFAULT 0,
         shares_outstanding REAL DEFAULT 0,
         dividend_per_share REAL DEFAULT 0,
         PRIMARY KEY (symbol, date)
     )
     ```
     `stock_fundamentals` schema stores `date` as fiscal period end date without a `disclosure_date` or `filing_date` column.
   - `prediction_model.py` lines 879–880 & line 905:
     ```python
     879: df = pd.merge(df, df_fun, left_on='date_align', right_on='date', how='left', suffixes=('', '_fund'))
     ...
     905: df[col] = df[col].ffill().fillna(meta[col])
     ```
     Merging daily stock prices (`df`) with fundamental records (`df_fun`) on `date_align == date` attaches financial results on the exact fiscal year end date (e.g. `2023-12-31`). Forward fill (`ffill()`) propagates these numbers into daily price rows starting Jan 1 of the following year — **60 to 90 days before actual public disclosure** (late March for Korean annual filings).
   - `run_pipeline.py` line 1902:
     ```python
     1902: fund_df = fund_df.sort_values('date').groupby('symbol').last().reset_index()
     ```
     RIM Valuation (Strategy 9) and MQ Factor (Strategy 11) retrieve the latest fundamental record by fiscal `date` without checking whether the report was publicly released prior to inference date `T`.

### Focus Area 2: Technical & Price Indicator Lookahead Leaks
1. **Global Deployment Scaler Fitted on Entire Data**:
   - `prediction_model.py` lines 1419–1425 vs line 1484:
     ```python
     1419: for fold_idx, (tr_idx, va_idx) in enumerate(tscv.split(df_h)):
     ...
     1423:     scaler_fold = fit_scaler(df_tr, features, str(self.model_dir), f"{market}_fold{fold_idx}", h)
     ...
     1484: scaler = fit_scaler(df_h, features, str(self.model_dir), market, h)
     ```
     Although Walk-Forward Cross-Validation fits in-fold scalers (`scaler_fold`) during model validation, the final saved scaler (`scaler_{market}_{h}d.joblib`) deployed to disk and used during live/historical inference is fitted on **ALL rows of `df_h` (combining train and validation/test history)**. Mean and variance parameters leak global future distribution properties to inference inputs.
2. **Unshifted Technical Indicators & Same-Day Close Dependency**:
   - `prediction_model.py` lines 1007–1047 & lines 1069–1088:
     ```python
     1007: df['ret_1d'] = df['Close'].pct_change(1)
     1013: df['sma_20'] = df['Close'].rolling(20).mean()
     1018: df['vol_20d'] = df['ret_1d'].rolling(20).std()
     1046: df['bb_upper_dist'] = (df['Close'] - (sma_20 + 2 * std_20)) / (df['Close'] + 1e-9)
     ```
     Primary feature columns calculate rolling metrics using unshifted `Close[t]`. If signals are evaluated pre-market or intraday for open execution, using `Close[t]` introduces a same-day lookahead leak.
   - `prediction_model.py` lines 1156–1160:
     ```python
     1157: cov_fx = df['ret_1d'].rolling(60, min_periods=20).cov(fx_change)
     ```
     `fx_beta_60d` calculates 60-day rolling covariance using unshifted `ret_1d` and `usdkrw_change`.

### Focus Area 3: Missing Data & Imputation Audit
1. **Coverage Analyzer Column Map Mismatch**:
   - `coverage_analyzer.py` line 23 vs lines 79–94:
     ```python
     23: STRATEGIES = ['regression', 'surge', 'lead_lag', 'vcp_rule', 'vcp_ml', 'lstm', 'stat_arb', 'sector_rotation', 'rim_valuation', 'event_driven', 'mq_factor', 'iv_skew', 'order_flow', 'short_term_reversal', 'arm_factor', 'card_factor', 'latr_factor']
     ```
     `STRATEGIES` list contains 17 strategies. However, `col_map` (lines 79–94) only maps 14 strategies (excluding `'arm_factor'`, `'card_factor'`, `'latr_factor'`). Lines 107–111 assign `cov_pct = 0.0` and `valid_cnt = 0` for these unmapped strategies, causing `strategy_data_coverage_report.txt` to report 0.0% coverage and 100% missing count for `ARM`, `CARD`, and `LATR`.
2. **Missingness Selection Bias in Dynamic Re-Weighting**:
   - `ensemble_scorer.py` lines 835–845:
     ```python
     840: total_score_series += merged[score_col].fillna(0.0) * w * valid_mask.astype(float)
     841: total_weight_series += w * valid_mask.astype(float)
     845: linear_score = (total_score_series / safe_weight_series).fillna(0.0).clip(0.0, 1.0)
     ```
     Dynamic weight normalization divides total score by the sum of weights of *available* strategies. A symbol with missing data on 12 out of 14 strategies having two high scores (e.g. `reg_score`=0.8, `surge_score`=0.8) achieves a normalized ensemble score of `0.80`, outranking a stock with 100% valid coverage across all 14 strategies averaging `0.65`.
3. **Zero Fill Signal Distortion for Downstream Meta-Learner**:
   - `ensemble_scorer.py` lines 873–883:
     ```python
     879: for col in fill_cols:
     880:     if col in merged.columns:
     881:         merged[col] = merged[col].fillna(0.0)
     ```
     Filling missing strategy scores with `0.0` mutates `merged` before `MetaEnsembleLearner` (line 849–850) fits or predicts. Missing option chains (`iv_skew`) or missing cointegrated pairs (`stat_arb`) are converted to `0.0` (worst possible rank signal in [0, 1] range) rather than neutral median signals (0.50).

### Focus Area 4: Survivorship Bias Audit
1. **Current-Surviving Universe Loading**:
   - `indicator_storage.py` lines 212–256 (`update_stock_universe()`):
     ```python
     215: sp500 = fdr.StockListing('S&P500')
     218: krx = fdr.StockListing('KRX')
     ```
     `update_stock_universe()` queries `FinanceDataReader` for the active stock list today. It overwrites `stock_universe` table with currently surviving companies.
   - `run_pipeline.py` lines 790–795 & 845–848:
     ```python
     790: universe = storage.get_universe()
     ...
     845: kospi_symbols = universe[universe['market'] == 'KOSPI']['symbol'].tolist()
     ```
     Historical model training and backtests iterate over `universe`. Delisted, bankrupt, acquired, or demoted companies that existed historically (e.g. 2021–2024) are completely absent.
2. **Permanent Administrative Stock Exclusion**:
   - `indicator_storage.py` lines 225–230 & lines 247–248:
     ```python
     225: adm = fdr.StockListing('KRX-ADMINISTRATIVE')
     ...
     247: if row['Code'] in excluded:
     248:     continue
     ```
     All `KRX-ADMINISTRATIVE` symbols are permanently filtered out from `stock_universe`. While filtering active trading risks, applying this filter historically removes bankrupt/distressed tail-risk examples from model training datasets.

---

## 2. Logic Chain

1. **Point-in-Time Data Integrity**:
   - Observation: Yahoo Finance API returns income statements and balance sheets indexed by fiscal period end date (`endDate`). `earnings_data.py` uses `endDate` as `date_align`.
   - Logic: A company's fiscal year ends on 2023-12-31, but annual financials are not publicly accessible until filed on DART/SEC (typically March 2024).
   - Observation: `prediction_model.py` merges fundamental records using `date_align == date` and applies `.ffill()`.
   - Logic: Historical feature matrices for dates between Jan 1, 2024 and March 31, 2024 contain FY2023 revenue, EPS, BPS, and ROE. Models trained or backtested during this window receive non-public future data.
   - Conclusion: **HIGH Severity Point-in-Time Lookahead Leak**.

2. **Technical & Price Indicator Lookahead**:
   - Observation: `prediction_model.py` fits final scalers (`fit_scaler(df_h, features, ...)`) on the combined dataset `df_h` across the full history.
   - Logic: Standardizing features with mean/std calculated across the entire dataset exposes past feature values to future dataset distributions.
   - Conclusion: **HIGH Severity Scaler Distribution Leak**.

3. **Missing Data & Imputation**:
   - Observation: `coverage_analyzer.py` lists 17 strategies in `STRATEGIES`, but `col_map` omits `arm_factor`, `card_factor`, and `latr_factor`.
   - Logic: Lookups for these 3 strategies return `c_col = None`, executing fallback code `valid_cnt = 0, cov_pct = 0.0`.
   - Conclusion: **HIGH Severity Audit Distortion** (Coverage report falsely claims 0% coverage for 3 operational strategies).
   - Observation: `ensemble_scorer.py` computes `linear_score = total_score / total_weight`.
   - Logic: A symbol missing 12 strategies with 2 high scores receives `0.80`, outranking a 100% valid symbol with realistic scores averaging `0.65`.
   - Conclusion: **HIGH Severity Missingness Selection Bias**.

4. **Survivorship Bias**:
   - Observation: `update_stock_universe()` populates `stock_universe` using `fdr.StockListing('S&P500')` and `fdr.StockListing('KRX')` as of today.
   - Logic: Backtesting past years against today's surviving constituents ignores all companies that went bankrupt or were delisted during 2020–2025.
   - Conclusion: **HIGH Severity Survivorship Bias**.

---

## 3. Caveats

- **Historical Filing Date Availability**: Yahoo Finance free API endpoints do not expose historical SEC/DART filing timestamps. Incorporating exact point-in-time filing dates will require integrating DART API (for KRX) and SEC EDGAR / Financial Modeling Prep API (for US).
- **Execution Timing Assumption**: Technical feature same-day dependence (`Close[t]`) is acceptable ONLY for post-market scoring workflows where daily bars are closed. For live morning order submission, features must be explicitly lagged with `.shift(1)`.
- **Delisted Data Store**: Restoring survivorship-bias-free data requires historical point-in-time constituent snapshots which are not present in current SQLite DB files (`stock_prices.db`, `market_indicators.db`).

---

## 4. Conclusion & Vulnerability Ratings

### Vulnerability Rating Table

| ID | Focus Area | Vulnerability | Severity | Primary File & Line Numbers | Impact |
|---|---|---|---|---|---|
| **V-PIT-1** | Point-in-Time | Fiscal end date (`endDate`) used as publication date | **HIGH** | `earnings_data.py`:54, 167–177 | Future fundamentals merged 60–90 days prior to public disclosure. |
| **V-PIT-2** | Point-in-Time | DB schema lacks `disclosure_date` column | **HIGH** | `indicator_storage.py`:101–111 | Prevents point-in-time querying in SQLite persistence layer. |
| **V-PIT-3** | Point-in-Time | Fundamental join on fiscal date with forward fill | **HIGH** | `prediction_model.py`:879–880, 905 | Model features receive non-public financial metrics during Jan–March window. |
| **V-PIT-4** | Point-in-Time | Unfiltered `.groupby('symbol').last()` for RIM & MQ | **HIGH** | `run_pipeline.py`:1902 | Historical RIM and MQ factor scores use unannounced BPS/EPS. |
| **V-LEAK-1**| Indicator Lookahead | Deployment scaler fitted on entire dataset | **HIGH** | `prediction_model.py`:1484 | Global mean/std leaks future feature distribution into model predictions. |
| **V-LEAK-2**| Indicator Lookahead | Unshifted `Close[t]` technical features | **MEDIUM** | `prediction_model.py`:1007–1047 | Same-day close dependency leaks future price if evaluated pre-market/intraday. |
| **V-LEAK-3**| Indicator Lookahead | Unshifted `ret_1d` in FX rolling covariance | **MEDIUM** | `prediction_model.py`:1157 | Intraday FX beta features use unshifted returns. |
| **V-MISS-1**| Missing Data Audit | Missing `arm`, `card`, `latr` in `col_map` | **HIGH** | `coverage_analyzer.py`:23 vs 79–94 | False 0.0% coverage reported for 3 active strategies. |
| **V-MISS-2**| Missing Data Audit | Weight normalization selection bias | **HIGH** | `ensemble_scorer.py`:835–845 | Symbols missing 12 strategies artificially outrank fully validated stocks. |
| **V-MISS-3**| Missing Data Audit | Raw score `fillna(0.0)` distorts meta-learner | **MEDIUM** | `ensemble_scorer.py`:873–883 | Missing data converted to worst-rank signals (0.0) instead of median (0.5). |
| **V-SURV-1**| Survivorship Bias | Universe updated from active-only listing today | **HIGH** | `indicator_storage.py`:215–218 | Excludes delisted/bankrupt companies from universe database. |
| **V-SURV-2**| Survivorship Bias | Backtesting & training run on surviving universe | **HIGH** | `run_pipeline.py`:790–795 | Artificially inflates backtest return & Sharpe ratio. |
| **V-SURV-3**| Survivorship Bias | Permanent exclusion of `KRX-ADMINISTRATIVE` | **MEDIUM** | `indicator_storage.py`:225–230, 247–248 | Eliminates distressed tail-risk samples from model training. |

---

## 5. Verification Method

### Step-by-Step Verification Procedure

1. **Verify V-MISS-1 (Coverage Analyzer Mismatch)**:
   - Inspect `coverage_analyzer.py`. Check `self.STRATEGIES` vs `col_map`.
   - Run `coverage_analyzer.analyze_coverage()` on a test DataFrame containing `arm_score`, `card_score`, and `latr_score`.
   - *Failure Condition*: `arm_factor`, `card_factor`, and `latr_factor` report `coverage_pct == 0.0`.

2. **Verify V-PIT-1 & V-PIT-3 (Fundamental Point-in-Time Leak)**:
   - Query `stock_fundamentals` DB for symbol `'005930'` (Samsung Electronics). Inspect column `date`. Notice date is `'2023-12-31'`.
   - Inspect `df_prices` merged by `prediction_model.merge_fundamentals()`. Check date `'2024-01-15'`.
   - *Failure Condition*: Row `'2024-01-15'` contains FY2023 annual EPS/revenue prior to Samsung's actual annual report filing date (late March 2024).

3. **Verify V-LEAK-1 (Global Scaler Leak)**:
   - Check `scaler_{market}_{h}d.joblib` created by `prediction_model.py`.
   - Compare `scaler.mean_` with the mean of `df_train` vs `df_h`.
   - *Failure Condition*: `scaler.mean_` equals the mean of `df_h` (full dataset), proving scaler was fitted on out-of-sample data.

4. **Verify V-SURV-1 & V-SURV-2 (Survivorship Bias)**:
   - Run `indicator_storage.get_universe()`. Check if historical delisted KRX symbols (e.g. SsangYong Motor before merger, or delisted KOSDAQ stocks from 2021) exist in `stock_universe`.
   - *Failure Condition*: Only currently listed active symbols exist in `stock_universe`.
