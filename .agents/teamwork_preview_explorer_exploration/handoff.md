# Handoff Report: Price Prediction Feature Upgrades Exploration

## 1. Observation
- The definition of `OnDevicePredictionModel` was located in `d:\Finance\code\stock\trading_system\src\ai\prediction_model.py` (lines 14–157). It uses a feature array containing:
  ```python
  features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d']
  ```
- The `MacroPredictor` class was located in `d:\Finance\code\stock\trading_system\src\analysis\macro_predictor.py` (lines 32–136). It uses XGBoost and LightGBM models trained on macro indicators and stock return lags in `src/analysis/screener.py` (lines 280–330).
- The `HybridStrategyEngine` class was located in `d:\Finance\code\stock\trading_system\src\core\strategy_engine.py` (lines 86–972). It contains the `_compute_technical_indicators` method (lines 209–308) which only accepts price bars:
  ```python
  def _compute_technical_indicators(self, price_bars: list) -> Dict:
  ```
- The post-market scoring script is in `d:\Finance\code\stock\trading_system\scripts\post_market_scoring.py` (lines 1–284). It fetches stock data sequentially and calculates scores inside a single loop:
  ```python
  for _, stock in universe.iterrows():
      # Fetch Prices, calculate Technical, AI, Sentiment scores
  ```
- The database storage initialization is in `d:\Finance\code\stock\trading_system\src\data_layer\indicator_storage.py` (lines 14–59), creating SQLite tables but currently lacking fields for `market_cap` or `floating_shares` in `stock_universe`.

## 2. Logic Chain
- To implement **R1** (Market Cap, Volume, Floating Shares Feature Engineering), we must fetch `marketCap` and `floatShares` from yfinance's info API, and KRX listed shares from FinanceDataReader. Since daily prices change, these must be multiplied by prices dynamically to compute floating values. To normalize these stock features cross-sectionally, we need a cross-sectional function that pools all stock price/volume/metadata histories, computes daily market-level totals, and calculates normalized ratios.
- To implement **R2** (Price Prediction Model Update), the new `norm_market_cap`, `norm_floating_value`, and `norm_volume` features must be appended to the feature sets of both `OnDevicePredictionModel` and `MacroPredictor` during both feature extraction, training, and inference.
- To implement **R3** (Strategy Engine & Post-Market Scoring updates), `HybridStrategyEngine._compute_technical_indicators` must be updated to take volume/floating shares to calculate volume-momentum adjustments and low-liquidity penalties. Furthermore, `post_market_scoring.py` must pre-fetch all stock prices first to allow cross-sectional normalization across the universe before calling model predictions.
- To implement **R4** (Documentation & Test Updates), unit tests must be added to verify the calculations of `norm_market_cap`, `norm_floating_value`, `norm_volume`, and the updated prediction models and scoring pipeline.

## 3. Caveats
- Since the workspace must operate in offline/CODE_ONLY mode during local test executions, calling live APIs (yfinance and FinanceDataReader) will time out or fail. The designs rely heavily on the fallback mock metadata dictionary (`FALLBACK_METADATA`) to guarantee deterministic offline execution.
- We assume that the stock universe fetched by `prices_dict` in `prepare_training_data` or `process_and_predict_all` represents the total market for calculation of baseline market totals.

## 4. Conclusion
The codebase is structurally ready for the proposed updates. No code was modified during this read-only investigation. A comprehensive implementation plan has been written to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_exploration\analysis.md` detailing the file modifications, contract designs, and code outlines needed for requirements R1, R2, R3, and R4.

## 5. Verification Method
- **Inspect Files**: Inspect the analysis file `d:\Finance\code\stock\.agents\teamwork_preview_explorer_exploration\analysis.md` to ensure the detailed recommendations and draft designs match the requirements.
- **Run Existing Test Suite**: Execute the command `pytest d:\Finance\code\stock\trading_system` to confirm that the existing test suite compiles and runs correctly before the proposed implementations begin.
