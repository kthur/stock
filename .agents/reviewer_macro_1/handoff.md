# Handoff Report - Global Macro Correlation Engine and ML Predictor Review

This report summarizes the findings, reasoning, and conclusions regarding the review of `src/analysis/macro_analyzer.py` and `src/analysis/macro_predictor.py` within `trading_system`.

---

## 1. Observation

1. **File Path and Code**: `trading_system/src/analysis/macro_analyzer.py` calculates contemporaneous and lagged cross-correlations.
   - At line 19: `MACRO_SYMBOLS = ["^GSPC", "^IXIC", "^KS11", "^KQ11", "USDKRW=X", "^TNX", "^VIX"]`
   - At lines 65–71:
     ```python
     for l in range(lags + 1):
         shifted = returns.shift(l)
         for t1 in tickers:
             for t2 in tickers:
                 val = returns[t1].corr(shifted[t2])
                 corr_df.loc[t1, (t2, l)] = val if not pd.isna(val) else 0.0
     ```
   - At lines 39–46:
     ```python
     if not isinstance(df.index, pd.DatetimeIndex):
         df.index = pd.to_datetime(df.index)
     if df.index.tz is not None:
         df.index = df.index.tz_convert(None)
     df.index = df.index.normalize()
     ```
   - At lines 51–52:
     ```python
     # 2. Forward fill and backward fill missing values
     df = df.ffill().bfill()
     ```

2. **File Path and Code**: `trading_system/src/analysis/screener.py` trains the macro predictor and sorts the stock outperformers.
   - At lines 259–279:
     ```python
     def train_and_predict_region(tickers: List[str], stock_returns: pd.DataFrame, benchmark_symbol: str) -> List[Dict]:
         bench_returns = macro_returns[benchmark_symbol]
         X_list = []
         y_list = []
         for ticker in tickers:
             if ticker not in stock_returns.columns:
                 continue
             excess = stock_returns[ticker] - bench_returns
             idx = macro_features_df.index.intersection(excess.index)
             if len(idx) < 5:
                 continue
             X_list.append(macro_features_df.loc[idx])
             y_list.append(excess.loc[idx])
         ...
         X_pool = pd.concat(X_list, axis=0)
         y_pool = pd.concat(y_list, axis=0)

         predictor = MacroPredictor(max_depth=5, n_estimators=100)
         try:
             predictor.train_model(X_pool, y_pool)
         ...
     ```
   - At lines 301–308:
     ```python
             pred_series = predictor.predict_outperformers(latest_features)
             pred_val = float(pred_series.iloc[0])

             results.append({
                 "ticker": ticker,
                 "expected_excess_return": pred_val,
                 "correlation_to_exchange_rate": corr_val
             })
     ```
   - Note that `latest_features` does not contain any ticker-specific identifiers or features.

3. **Cached Model Metrics**: `trading_system/data/macro_model_metrics.json`
   - Content of the metrics file:
     ```json
     {
         "mse": 0.0011413384442604377,
         "r2_score": -0.021046337634039736,
         "num_samples": 2856,
         "timestamp": "2026-06-08T05:25:43.256970",
         "features": [
             "^GSPC_lag_1",
             ...
         ]
     }
     ```

4. **Pytest Run Output**: Command `.venv\Scripts\pytest tests/test_macro.py` run in `d:\Finance\code\stock\trading_system`.
   - Result:
     ```text
     tests\test_macro.py .....                                                [100%]
     ======================= 5 passed, 3 warnings in 45.63s ========================
     ```

---

## 2. Logic Chain

1. **Lack of Ticker-Specific Features**:
   - As observed in `screener.py` lines 259–279 and 301–308, the input features `latest_features` are exactly the same macro lag variables for every stock ticker.
   - The trained model `MacroPredictor` only receives macro features `X_pool` and excess returns `y_pool`. It does not receive any stock identity (like a stock one-hot vector or ticker-specific characteristics).
   - Therefore, the model's prediction `pred_val = float(pred_series.iloc[0])` evaluates to the exact same value for all stocks in the same region (US or KR).
   - This results in a trivial outperformer sort order that is identical to the initial ticker list order, making the "outperformer" classification mathematically meaningless.

2. **Look-Ahead Timezone Bias**:
   - As observed in `macro_analyzer.py` line 65–71, cross-correlation calculates lag 0 correlation between US indices and Korean indices on the same calendar day.
   - Because the US trading session starts and ends after the Korean trading session has closed, US returns on day T cannot influence Korean returns on day T in a tradable manner.
   - Direct calendar-date alignment for lag 0 introduces look-ahead bias if the US market is assumed to lead Korea on the same calendar date.

3. **Correlation Dilution**:
   - `macro_analyzer.py` performs price forward-filling (`ffill()`) before return calculations (`pct_change()`).
   - When a local holiday occurs, the price is carried forward, resulting in a 0.0 return for that day.
   - This 0.0 return artificially dampens the covariance term against other open markets, diluting the calculated Pearson correlation coefficients.

---

## 3. Caveats

- **No live trading was executed**: The predictor was reviewed based on its model definition, screener implementation, and dashboard callback logic. We did not run it against real live brokerage connections as it is out of scope.
- **Model Performance**: The negative R-squared score (`-0.021`) confirms that using only lagged macro indexes is insufficient to predict excess daily returns out-of-sample.

---

## 4. Conclusion

The Global Macro Engine and ML Predictor have a robust code layout and pass all existing tests, but they contain major structural model design issues and timezone/holiday math flaws:
1. **Identical Predictions**: The ML Predictor outputs identical predictions for all stocks in a region due to the absence of ticker-specific features.
2. **Timezone Look-ahead**: Contemporaneous lag-0 correlation between US and Korean sessions suffers from look-ahead bias because Korea closes before the US opens on the same calendar day.
3. **Holiday Correlation Dilution**: Forward-filling holiday prices before computing returns introduces artificial 0.0 returns that dilute correlation scores.

Verdicts: **REQUEST_CHANGES** is recommended until ticker-specific features are introduced and timezone/holiday alignment is corrected.

---

## 5. Verification Method

To independently verify this review:
1. **Execute Tests**: Run the following command in the `trading_system` folder to confirm tests pass:
   ```powershell
   .venv\Scripts\pytest tests/test_macro.py
   ```
2. **Inspect Cached Metrics**: View the contents of `trading_system/data/macro_model_metrics.json` and notice the negative R2 score (`-0.021046`).
3. **Review Code Locations**:
   - Check `trading_system/src/analysis/screener.py` lines 275–308 to verify that `latest_features` lacks stock identity, producing identical predictions for all stocks.
   - Check `trading_system/src/analysis/macro_analyzer.py` lines 65–71 to verify that lag 0 correlation is calculated contemporeneously for timezone-mismatched symbols.
