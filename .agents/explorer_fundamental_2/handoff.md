# Handoff Report: Fundamental Data Integration Analysis

## 1. Observation
- **Database Schema Handler**: Database `market_indicators.db` is managed by `MarketIndicatorStorage` in `trading_system/src/data_layer/indicator_storage.py` (lines 14–59), where it initializes tables `global_indicators`, `stock_universe`, `ai_predictions`, and `post_market_rankings`.
- **APIs and Fallback Metadata**: yfinance and FinanceDataReader are utilized to fetch stock data in `run_pipeline.py`, `post_market_scoring.py`, and `screener.py`. Offline mock data is defined in `trading_system/src/ai/prediction_model.py` within `FallbackMetadataDict` (lines 17–78), which provides `shares_outstanding` and `floating_shares` for 16 benchmarks and hash-based mock values for other symbols.
- **Model Features**: `OnDevicePredictionModel` in `trading_system/src/ai/prediction_model.py` hardcodes its feature set of 9 features (`ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `dist_sma_20`, `vol_20d`, `norm_market_cap`, `norm_floating_value`, `norm_volume`) inside `train()` (line 236), `predict_current()` (line 270), and `process_and_predict_all()` (line 288).
- **Daily Scoring and Prediction**: `post_market_scoring.py` uses `OnDevicePredictionModel` to perform expected return predictions for horizon 20 (lines 252–257) if they are not pre-calculated in the database.
- **Unit Tests**: The normalization and fallback metadata are tested in `trading_system/tests/test_feature_normalization.py` (lines 14–44), while the scoring pipeline is tested in `trading_system/tests/test_post_market_scoring.py`.

---

## 2. Logic Chain
1. **Database Schema updates**: Because database table initialization is centralized in `MarketIndicatorStorage._init_db`, the new `stock_fundamentals` table must be defined here. We will add a CRUD interface to write/read from this table.
2. **Offline Mock updates**: Since `FallbackMetadataDict` is the singleton source of truth for mock ticker information, it must be extended to support fundamentals (`revenue`, `operating_income`, `dividend_per_share`) to avoid model training crashes in offline test environments.
3. **Feature Engineering updates**: In `_create_features`, we will calculate the three new features (`operating_margin`, `revenue_to_market_cap`, `dividend_yield`) using the merged fundamentals or fallbacks from `FALLBACK_METADATA`.
4. **Model Configuration**: To support the 12-feature schema, the hardcoded feature lists in `OnDevicePredictionModel`'s train and predict methods must be updated to include the three new columns.
5. **Daily Scoring Integration**: The daily scoring script `post_market_scoring.py` must align with the new model schema by ensuring the price DataFrames are joined with fundamental values before feature extraction.

---

## 3. Caveats
- **Data availability**: Korean stock fundamentals can be noisy or missing on certain APIs. The design handles this by using `FallbackMetadataDict` as a robust fallback.
- **Scope limitation**: This is a read-only investigation. No code changes have been applied to the production directories.

---

## 4. Conclusion
We have formulated a detailed integration design covering database schemas, data fetching, feature engineering, models training, strategy engine, and tests. The proposal is successfully saved to `analysis.md`.

---

## 5. Verification Method
- **Test Command**: Run pytest:
  ```bash
  pytest trading_system/tests/test_feature_normalization.py
  pytest trading_system/tests/test_post_market_scoring.py
  ```
- **Inspect Files**: Review `analysis.md` in `d:\Finance\code\stock\.agents\explorer_fundamental_2\analysis.md` for specific code snippets and design specifications.
