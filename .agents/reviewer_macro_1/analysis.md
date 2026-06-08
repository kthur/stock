# Global Macro Engine & ML Predictor - Review and Critique

## Quality Review Report

### Review Summary
**Verdict**: REQUEST_CHANGES (due to major model structure issues and look-ahead timezone bugs)

This review examines the implementation of the Global Macro Correlation Engine (`macro_analyzer.py`) and the ML Predictor (`macro_predictor.py`), along with the associated outperformer screening logic (`screener.py`) and Web Dashboard callbacks. 

While the code is well-structured, implements a chronological train-test split correctly, and passes the unit tests successfully, there are critical mathematical and logical flaws regarding timezone alignment, holiday data handling, and the ML prediction structure that prevent it from functioning as a true stock screener.

---

### Findings

#### [Major] Finding 1: Lack of Ticker-Specific Features in ML Predictor
- **What**: The features pooled for training the `MacroPredictor` contain only general macro indices and do not include any ticker-specific identifiers or features.
- **Where**: `trading_system/src/analysis/screener.py` (lines 259–312) and `trading_system/src/analysis/macro_predictor.py` (lines 92–110).
- **Why**: Since `X_pool` consists only of lagged macro variables (e.g., `^GSPC_lag_1` through `^VIX_lag_5`) and `latest_features` represents a single row of the latest macro state, the predictor outputs the **exact same expected excess return** for every single ticker in the region (US or KR). The subsequent sorting in `screen_global_outperformers` is trivial and defaults to the original input order of tickers, failing the core objective of screening individual outperformers.
- **Suggestion**: Introduce ticker-specific features (e.g., individual stock lagged returns, stock beta, RSI, or one-hot encoded ticker IDs) into the feature matrix `X_pool` so that the model can learn ticker-specific sensitivities to macro events.

#### [Major] Finding 2: Timezone Misalignment and Look-Ahead Bias at Lag 0
- **What**: The correlation engine evaluates contemporaneous correlation (lag 0) between US indices and Korean indices on the same calendar day.
- **Where**: `trading_system/src/analysis/macro_analyzer.py` (lines 65–71).
- **Why**: The Korean market (KOSPI) closes at 15:30 KST (06:30 UTC), while the US market (S&P 500) opens at 09:30 EDT (13:30 UTC) and closes at 16:00 EDT (20:00 UTC) on the same calendar date. Therefore, the US trading session on day T happens 13.5 hours *after* the Korean session has already closed. Calculating contemporaneous (lag 0) correlation implies that US market movements on day T could affect Korea on day T, which is physically impossible and represents a look-ahead bias in live trading.
- **Suggestion**: Enforce a minimum of 1-day lag when analyzing the impact of US markets on Korean markets, or restrict contemporaneous correlation analysis to markets operating in overlapping or subsequent timezones.

#### [Minor] Finding 3: Correlation Dilution from Holiday Padding
- **What**: Missing prices for market holidays are forward-filled before calculating daily percentage returns.
- **Where**: `trading_system/src/analysis/macro_analyzer.py` (lines 51–55).
- **Why**: When a market is closed (e.g., KR holiday) while another is open (e.g., US open), forward-filling the price of the closed market creates a 0.0 return on that day. These artificial zero returns dilute the covariance term in the Pearson correlation coefficient, resulting in an underestimated correlation.
- **Suggestion**: Calculate returns first, and then drop rows where either of the indices has a missing value (inner join on mutual trading days) before computing the correlation matrix.

---

### Verified Claims

- **Claim 1**: Pearson correlation matrix is generated with a MultiIndex representing ticker and lag.
  - *Verified via*: Inspecting `macro_analyzer.py` lines 61–72 and running `test_r1_correlation_engine`.
  - *Result*: **PASS**.
- **Claim 2**: Model training uses chronological splitting (80/20 train/test) to prevent time-series data leakage.
  - *Verified via*: Inspecting `macro_predictor.py` lines 56–62.
  - *Result*: **PASS**.
- **Claim 3**: Model metrics cache successfully to JSON at `data/macro_model_metrics.json`.
  - *Verified via*: Running `pytest` and viewing `trading_system/data/macro_model_metrics.json`.
  - *Result*: **PASS**.
- **Claim 4**: Test suite `tests/test_macro.py` runs and passes successfully.
  - *Verified via*: Executing `.venv\Scripts\pytest tests/test_macro.py` in the local workspace.
  - *Result*: **PASS** (5 tests passed, 3 deprecation warnings).

---

### Coverage Gaps

- **Extreme Market Scenarios / Holiday Gaps**: The correlation engine does not separate normal periods from high-stress periods (e.g., VIX > 30), which can cause correlation breakdown. *Risk Level*: Medium. *Recommendation*: Add a stress-regime filter in the correlation analysis.
- **Model Overfitting / Negative R2**: The model cached in `data/macro_model_metrics.json` reports an out-of-sample R2 score of `-0.021`. This means the model predictions are worse than the simple target mean, indicating a lack of predictive power. *Risk Level*: High. *Recommendation*: Enhance model features with stock-specific and macro-regime indicators.

---

### Unverified Items

- **Actual Live Broker Order Execution with Macro Signals**: The macro predictor is currently only hooked up to the screener and web dashboard, and not directly driving the `strategy_engine` order routing. *Reason*: Out of scope for this milestone.

---

## Adversarial Review Report

### Challenge Summary
**Overall risk assessment**: HIGH

The main risks stem from the model's structural design where no asset-specific features are supplied, causing identical predictions across all tickers, and the timezone alignment which introduces un-tradable look-ahead signals. Furthermore, the model has negative out-of-sample R2, meaning it lacks actual predictive power.

---

### Challenges

#### [High] Challenge 1: The "Same-Return-For-All" Vulnerability
- **Assumption challenged**: The model is capable of screening and identifying "outperformers" based on macro variables.
- **Attack scenario**: A user relies on the "US Expected Outperformers" table to select AAPL over MSFT. Because both tickers receive the exact same predicted excess return, the sorting is entirely determined by their hardcoded order in the `US_TICKERS` list. If MSFT has a stronger macro sensitivity but happens to be listed after AAPL, the system fails to highlight it.
- **Blast radius**: Poor portfolio allocation. The user is misled into believing the ML model is selecting specific stocks when it is actually just outputting a market-wide macro return prediction.
- **Mitigation**: Add ticker-specific features, such as trailing beta to benchmark, sector encoding, and individual stock technical indicators, to differentiate returns.

#### [Medium] Challenge 2: Contemporaneous Feedback Loop (Look-ahead)
- **Assumption challenged**: Lag 0 correlation is tradable.
- **Attack scenario**: A strategy tries to trade KOSPI on day T using day T S&P 500 price signals. Since the Korean market closes long before the US market opens, the day T S&P 500 return cannot be observed at KOSPI trade time.
- **Blast radius**: Backtests will show high correlation and profit potential (due to S&P 500's lead effect on KOSPI), but execution will fail in live trading because the signal is unavailable.
- **Mitigation**: Explicitly lag US indices by 1 day (`lag >= 1`) when calculating correlations or generating features for Korean market trades.

#### [Medium] Challenge 3: Negligible Predictive Power (Negative R2)
- **Assumption challenged**: The RandomForestRegressor is learning meaningful predictive signals.
- **Attack scenario**: The model is deployed live. Since the out-of-sample R2 is negative (`-0.021`), the model predictions are noisier than a simple historical average, leading to bad trade signals.
- **Blast radius**: Capital loss from trading on noise.
- **Mitigation**: Apply feature selection, add cross-validation, and utilize regularization or simpler linear/shrinkage models (like Ridge or Lasso) which are more robust to noisy macroeconomic data.

---

### Stress Test Results

- **Contemporaneous Correlation lag=0**: Expected: No lookahead in trading. Actual: Look-ahead bias present since US market closes after KR market on the same day. **FAIL**.
- **Model out-of-sample R2 score**: Expected: Positive R2 score (better than mean predictor). Actual: `-0.021` (worse than mean). **FAIL**.
- **Trained features count**: Expected: 35 features. Actual: 35 features. **PASS**.
