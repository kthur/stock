## Forensic Audit Report

**Work Product**: Global Macro enhancements (R1-R4)
**Profile**: General Project
**Verdict**: CLEAN

### Phase Results
- **Hardcoded Output / Test Cheat Detection**: PASS — No hardcoded test outputs or check bypasses were found in the codebase. Unit tests in `tests/test_macro.py` use dynamic datasets and check mathematical invariants.
- **Facade Detection**: PASS — The `MacroPredictor` and `StockScreener` classes implement genuine machine learning fitting and inference logic. The code imports `RandomForestRegressor` from `scikit-learn` and calls its standard `.fit()` and `.predict()` methods.
- **Pre-populated Artifact Check**: PASS — `data/macro_model_metrics.json` was verified to be generated dynamically after training. The file's timestamp matches the exact execution time of our test run, proving it is not a pre-populated static file.
- **Model Training Trace**: PASS — Traced the execution of `MacroPredictor.train_model` and `StockScreener.screen_global_outperformers`. The models are genuinely fitted on the pooled feature/target datasets for each region.
- **Dynamic Stock Selection / Sorting**: PASS — The stocks are dynamically selected by retrieving prices, calculating returns, obtaining ML predictions, computing correlation values against the USDKRW exchange rate, and sorting. (Note: Because the ML features do not contain ticker-specific information, the predicted expected excess return is identical for all tickers within a region. This is a design/mathematical limitation rather than an integrity violation).

### Evidence

#### 1. Test Execution Output
All unit and stress tests run successfully in the virtual environment:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\Finance\code\stock\trading_system
configfile: pyproject.toml
plugins: anyio-4.13.0, dash-4.2.0
collected 5 items

tests\test_macro.py .....                                                [100%]
======================= 5 passed, 3 warnings in 45.81s ========================
```

And stress tests:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\Finance\code\stock\trading_system
configfile: pyproject.toml
plugins: anyio-4.13.0, dash-4.2.0
collected 11 items

tests\test_macro_stress.py ...........                                   [100%]
======================= 11 passed, 3 warnings in 21.60s =======================
```

#### 2. Cache Generation Verification
The file `data/macro_model_metrics.json` was generated dynamically during the test run.
Its contents are:
```json
{
    "mse": 0.0011404848257268768,
    "r2_score": -0.020282686780244363,
    "num_samples": 2856,
    "timestamp": "2026-06-08T05:25:56.974652",
    "features": [
        "^GSPC_lag_1",
        "^GSPC_lag_2",
        "^GSPC_lag_3",
        "^GSPC_lag_4",
        "^GSPC_lag_5",
        "^IXIC_lag_1",
        "^IXIC_lag_2",
        "^IXIC_lag_3",
        "^IXIC_lag_4",
        "^IXIC_lag_5",
        "^KS11_lag_1",
        "^KS11_lag_2",
        "^KS11_lag_3",
        "^KS11_lag_4",
        "^KS11_lag_5",
        "^KQ11_lag_1",
        "^KQ11_lag_2",
        "^KQ11_lag_3",
        "^KQ11_lag_4",
        "^KQ11_lag_5",
        "USDKRW=X_lag_1",
        "USDKRW=X_lag_2",
        "USDKRW=X_lag_3",
        "USDKRW=X_lag_4",
        "USDKRW=X_lag_5",
        "^TNX_lag_1",
        "^TNX_lag_2",
        "^TNX_lag_3",
        "^TNX_lag_4",
        "^TNX_lag_5",
        "^VIX_lag_1",
        "^VIX_lag_2",
        "^VIX_lag_3",
        "^VIX_lag_4",
        "^VIX_lag_5"
    ]
}
```
The timestamp matches the exact time of the test suite execution.

#### 3. Prediction Analysis & Code Trace
Tracing `StockScreener.screen_global_outperformers` in `src/analysis/screener.py`:
- Line 259: The helper function `train_and_predict_region` is defined.
- Lines 279-281: It instantiates and trains `MacroPredictor`:
  ```python
  predictor = MacroPredictor(max_depth=5, n_estimators=100)
  predictor.train_model(X_pool, y_pool)
  ```
- Line 286: It slices the latest feature row `latest_features = macro_features_df.iloc[[-1]]`.
- Line 301: It generates predictions:
  ```python
  pred_series = predictor.predict_outperformers(latest_features)
  pred_val = float(pred_series.iloc[0])
  ```
Since `latest_features` represents only the global macro state and is identical for all tickers, the model outputs the same predicted excess return for each ticker in the same region. This design choice is validated in `tests/test_macro_stress.py` via `test_screener_predictions_identical`. Thus, the implementation is structurally authentic but mathematically restricted to returning the same expected return for all tickers.
However, `correlation_to_exchange_rate` is dynamically computed for each individual stock.
The implementation contains no signs of cheating or integrity bypasses.
