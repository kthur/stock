# Scope: Global Macro & ML Outperformer Screening

## Architecture
- `trading_system/src/analysis/macro_analyzer.py`: Contains the `calculate_cross_correlation` logic to fetch yfinance data for S&P 500, Nasdaq, KOSPI, KOSDAQ, USDKRW=X, ^TNX, and ^VIX, and compute cross-correlation with lags (up to 5 days).
- `trading_system/src/analysis/macro_predictor.py`: Implements features extraction (returns, lags), training of Random Forest or similar models, and expected excess return predictions. Caches evaluations to `trading_system/data/macro_model_metrics.json`.
- `trading_system/src/analysis/screener.py`: Incorporates the `screen_global_outperformers()` method into `StockScreener` to screen and return top 10 KOSPI and top 10 S&P 500 stocks.
- `trading_system/src/web/dashboard.py`: Integrates the 'Global Macro' tab (`global-macro-tab`) with Plotly heatmap and recommended outperformers DataTable.
- `trading_system/run_dashboard.py`: Serves the Dash app.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Exploration & Feature Engineering | Explore existing stock lists, yfinance fetching capabilities, and ML packages. | None | PLANNED |
| 2 | Macro Correlation Engine (R1) | Implement yfinance loader and cross-correlation with lags. | M1 | PLANNED |
| 3 | ML Predictor Model (R2) | Implement feature builder, model training pipeline, and caching metrics to json. | M2 | PLANNED |
| 4 | Global Outperformer Screener (R3) | Implement outperformer screening for KOSPI 200 / S&P 500 top 10. | M3 | PLANNED |
| 5 | Dashboard Tab Integration (R4) | Add 'Global Macro' tab with Plotly heatmap and data table. | M4 | PLANNED |
| 6 | E2E Verification & Forensic Audit | Verification and audit of full features. | M5 | PLANNED |

## Interface Contracts
### R1. Cross-Correlation
- `calculate_cross_correlation(indices_data: pd.DataFrame, lags: int = 5) -> pd.DataFrame` or similar: Computes cross-correlation with lags.

### R2. ML Predictor
- `MacroPredictor.train_model(features: pd.DataFrame, targets: pd.Series) -> Dict`: Trains the Random Forest model and returns evaluation metrics.
- `MacroPredictor.predict_outperformers(features: pd.DataFrame) -> pd.DataFrame`: Predicts excess returns.
- Cache path: `trading_system/data/macro_model_metrics.json`

### R3. Outperformer Screener
- `StockScreener.screen_global_outperformers() -> Dict[str, List[Dict]]`: Returns KOSPI and S&P500 top 10 lists. Output dict structure:
  ```python
  {
      "US": [{"ticker": str, "expected_excess_return": float, "correlation_to_exchange_rate": float}, ...],
      "KR": [{"ticker": str, "expected_excess_return": float, "correlation_to_exchange_rate": float}, ...]
  }
  ```

### R4. Dash UI Tab
- Tab ID: `global-macro-tab` or equivalent.
- Heatmap Graph: Plotly `dcc.Graph`.
- Recommendation: Dash `DataTable` and cards.
