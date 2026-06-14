# Codebase Analysis & Implementation Plan: Price Prediction Feature Upgrades

This document provides a detailed codebase analysis and step-by-step implementation plan for incorporating stock-level market capitalization, trading volume, and floating shares/value normalized by overall market benchmarks into the price prediction models, strategy engine, and scoring pipelines (Requirements R1, R2, R3, R4).

---

## 1. Codebase Mapping & Component Locations

### 1.1 Data Collection & Feature Engineering
- **`trading_system/src/data_layer/market_data_handler.py`**: Fetches daily price data via `yfinance` (US) and manages parquet caching.
- **`trading_system/src/data_layer/indicator_storage.py`**: Manages SQLite tables (`stock_universe`, `ai_predictions`, `post_market_rankings`, etc.).
- **`trading_system/run_pipeline.py`**: Consolidates market indicator fetching and samples/runs training & inference for `OnDevicePredictionModel`.
- **`trading_system/scripts/post_market_scoring.py`**: Runs daily post-market scoring on the stock universe using technical indicators, sentiment, and XGBoost predictions.

### 1.2 Prediction Models
- **`trading_system/src/ai/prediction_model.py` (`OnDevicePredictionModel`)**: Local XGBoost regressor predicting forward returns at multiple horizons (1d, 5d, 10d, 20d, 30d, 60d, 120d, 200d) using 6 technical and momentum features.
- **`trading_system/src/analysis/macro_predictor.py` (`MacroPredictor`)**: Local ensemble model (XGBoost + LightGBM) predicting excess stock returns based on lagged global macro features and stock lags.
- **`trading_system/src/analysis/screener.py` (`StockScreener`)**: Handles data loading and feature building for `MacroPredictor` to screen top outperforming stocks.

### 1.3 Strategy Engine & Scoring Scripts
- **`trading_system/src/core/strategy_engine.py` (`HybridStrategyEngine`)**: Ensembles multiple strategies (sentiment, technical, ML, RL, macro) and implements market regime detection and weight adaptation.
- **`trading_system/scripts/post_market_scoring.py`**: Coordinates daily scoring and saves rankings to the database.

### 1.4 Documentation & Existing Tests
- **`trading_system/docs/SYSTEM_ARCHITECTURE.md`**: Section 10 (ML/DL) and Section 12 (Regime Detection) outline the system's current architecture.
- **`trading_system/tests/test_post_market_scoring.py`**: Verifies post-market scoring script and database updates under mocked yfinance/FDR behaviors.
- **`trading_system/tests/test_macro.py` & `test_macro_stress.py`**: Test `MacroPredictor` training, prediction, and edge cases (constant data, NaNs, small datasets).

---

## 2. Requirement Specifications & Detailed Designs

### R1. Market Cap, Volume, and Floating Shares Feature Engineering
**Goal**: Calculate stock-level market capitalization, floating shares, and floating value, then normalize these cross-sectionally by daily market-level totals to generate `norm_market_cap`, `norm_floating_value`, and `norm_volume`.

#### A. Data Collection Strategy
- **US Stocks (yfinance)**:
  - Query `yf.Ticker(symbol).info` to fetch `'marketCap'` and `'floatShares'`.
  - Fall back to `'sharesOutstanding'` if `'floatShares'` is not available.
- **KR Stocks (FinanceDataReader)**:
  - Query `fdr.StockListing('KRX')` to retrieve `'Marcap'` (market cap) and `'Stocks'` (listed shares).
  - Estimate floating shares by applying a default float ratio (e.g., `0.70 * Stocks`), or fall back to volume-based calculations.
- **Offline Mock Support (Unit Tests)**:
  - Define a deterministic fallback dictionary of stock metadata in `src/ai/prediction_model.py` and `src/analysis/screener.py` to prevent HTTP timeouts and ensure consistent runs.
  ```python
  FALLBACK_METADATA = {
      "AAPL": {"market_cap": 3.0e12, "floating_shares": 15.0e9},
      "MSFT": {"market_cap": 3.1e12, "floating_shares": 7.4e9},
      "005930.KS": {"market_cap": 4.5e14, "floating_shares": 5.9e9},
      # Add default entries for all universe tickers...
  }
  ```

#### B. Floating Value & Market Baseline Calculations
- **Floating Value**:
  $$\text{FloatingValue}(t) = \text{ClosePrice}(t) \times \text{FloatingShares}$$
  If floating shares are unavailable, fall back to:
  $$\text{FloatingValue}(t) = \text{ClosePrice}(t) \times \text{Volume}(t)$$
- **Market-Level Normalization**:
  Align all stock dataframes by date. For each day $t$, sum across all active stocks in the universe:
  $$\text{TotalMarketCap}(t) = \sum_{s} \text{MarketCap}_{s}(t)$$
  $$\text{TotalFloatingValue}(t) = \sum_{s} \text{FloatingValue}_{s}(t)$$
  $$\text{TotalVolume}(t) = \sum_{s} \text{Volume}_{s}(t)$$
  Compute normalized features:
  $$\text{norm\_market\_cap}_{s}(t) = \frac{\text{MarketCap}_{s}(t)}{\text{TotalMarketCap}(t)}$$
  $$\text{norm\_floating\_value}_{s}(t) = \frac{\text{FloatingValue}_{s}(t)}{\text{TotalFloatingValue}(t)}$$
  $$\text{norm\_volume}_{s}(t) = \frac{\text{Volume}_{s}(t)}{\text{TotalVolume}(t)}$$

---

### R2. Price Prediction Model Update
**Goal**: Integrate `norm_market_cap`, `norm_floating_value`, and `norm_volume` into the training and inference stages of `OnDevicePredictionModel` and `MacroPredictor`.

#### A. Modify `src/ai/prediction_model.py`
1. Add a cross-sectional normalization helper inside `OnDevicePredictionModel` to compute market totals from a dictionary of price DataFrames:
   ```python
   def apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
       # Ensure each df has stock-level market_cap and floating_shares columns
       # Calculate floating_value = Close * FloatingShares (fallback: Close * Volume)
       # Compute daily sums for market_cap, floating_value, and Volume
       # Map sums back to each stock's DataFrame index
       # Calculate norm_market_cap, norm_floating_value, and norm_volume
       # Handle division by zero and NaNs by filling with defaults
       return prices_dict
   ```
2. Update `_create_features` to expect these normalized features:
   ```python
   # Existing technical features + the 3 new normalized features
   features = ['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 
               'norm_market_cap', 'norm_floating_value', 'norm_volume']
   ```
3. Update `prepare_training_data`, `process_and_predict_all`, and `predict_current` to run `apply_market_normalization` and include these new features in the features array passed to the XGBoost models.

#### B. Modify `src/analysis/screener.py` & `src/analysis/macro_predictor.py`
1. In `screener.py`'s `screen_global_outperformers()`:
   - Extract the volume data for US and KR tickers from the `yf.download` payload.
   - Fetch static `market_cap` and `floating_shares` from `yf.Ticker().info` or the `FALLBACK_METADATA` cache.
   - Calculate `norm_market_cap`, `norm_floating_value`, and `norm_volume` daily across each region's active tickers.
   - Inject these normalized columns and their lag features into the `X_pool` feature DataFrame.
2. In `macro_predictor.py`:
   - Keep the class feature-agnostic so that `X_train` columns are automatically fit and aligned during inference without structural regression errors.

---

### R3. Strategy Engine & Post-Market Scoring Updates
**Goal**: Update `HybridStrategyEngine` technical scoring and allocation rules, and modify `post_market_scoring.py` to support cross-sectional feature generation before inference.

#### A. Modify `src/core/strategy_engine.py` (`HybridStrategyEngine`)
1. Extend `_compute_technical_indicators` signature:
   ```python
   def _compute_technical_indicators(self, price_bars: list, volume_bars: list = None, floating_shares: float = None) -> Dict:
   ```
2. Add volume momentum adjustment:
   - Calculate 5-day volume SMA and 20-day volume SMA.
   - If 5-day volume SMA is greater than 1.5x of the 20-day volume SMA (volume expansion):
     - If price trend is positive (EMA20 > EMA50 or MACD > 0), add a volume bonus of $+0.05$ to the score.
     - If price trend is negative, subtract a volume penalty of $-0.05$.
3. Add a liquidity/floating value penalty:
   - Calculate daily floating value. If the asset's floating value is extremely low (indicating high manipulation risk and low liquidity), cap the technical score or decrease the allocation confidence.
4. Update position sizing / allocation rules in the portfolio management callbacks to scale down targets for assets with low `norm_volume` or low `norm_floating_value`.

#### B. Modify `scripts/post_market_scoring.py`
1. Re-architect the scoring loop:
   - Instead of fetching prices and scoring stocks one-by-one, **pre-fetch all historical prices** into a dictionary `prices_dict = {symbol: df}`.
   - Apply `OnDevicePredictionModel.apply_market_normalization(prices_dict)` to compute normalized market features cross-sectionally.
   - Loop through the universe:
     - Access pre-computed, normalized features for the stock.
     - Call `prediction_model.predict_current(df_features)` using the updated 9-feature model.
     - Call `strategy_engine._compute_technical_indicators(closes, volumes, floating_shares)`.
     - Calculate composite score, sort, rank, and store to database.

---

### R4. Documentation & Test Updates
**Goal**: Verify all calculations, model predictions, and scoring logic under automated tests.

#### A. Documentation Modifications
- Update `docs/SYSTEM_ARCHITECTURE.md` (Section 10 and 12) and `docs/ALGORITHMS_AND_STRATEGY.md` to document:
  - The 9-feature model structure (`ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `dist_sma_20`, `vol_20d`, `norm_market_cap`, `norm_floating_value`, `norm_volume`).
  - The cross-sectional market normalization formulas.
  - The volume momentum and floating value adjustments in technical scoring.

#### B. Test Suite Modifications
1. Create unit tests in `tests/test_indicators.py` or a new `tests/test_price_prediction_upgrades.py`:
   - Verify `apply_market_normalization` correctly aligns dates and returns normalized values.
   - Test `OnDevicePredictionModel` training and predicting using the new 9 features.
   - Verify `_compute_technical_indicators` correctly adjusts the score based on volume expansion and low floating values.
2. Update `tests/test_post_market_scoring.py`:
   - Mock `yf.Ticker` to return `marketCap` and `floatShares` info keys.
   - Verify `post_market_scoring.py` completes without exceptions and populates `post_market_rankings` table in the temporary test database.

---

## 3. Implementation Step-by-Step Plan

```
┌────────────────────────────────────────────────────────┐
│  Milestone 1: Feature Engineering (R1)                │
│  - Implement market-level normalization in data layer  │
│  - Add metadata fetch for US/KR universe              │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│  Milestone 2: Prediction Model Updates (R2)            │
│  - Update OnDevicePredictionModel feature definitions  │
│  - Update MacroPredictor and screener lag features     │
│  - Update training & pipeline execution scripts        │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│  Milestone 3: Strategy & Scoring Upgrades (R3)        │
│  - Incorporate volume/liquidity in HybridStrategyEngine│
│  - Refactor post_market_scoring.py pricing loop       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│  Milestone 4: Verification & Docs (R4)                │
│  - Update architecture and specification documents      │
│  - Add unit/integration tests and verify passes       │
└────────────────────────────────────────────────────────┘
```
