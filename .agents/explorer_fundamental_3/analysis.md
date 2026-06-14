# Detailed Design & Strategy: Incorporating Fundamental Data and Features

## Executive Summary
This document proposes a detailed design and integration strategy to incorporate fundamental financial indicators (Revenue, Operating Income, Dividends) and three derived features (`operating_margin`, `revenue_to_market_cap`, `dividend_yield`) into the stock prediction models, database schemas, feature pipelines, and strategy engines.

---

## 1. Database Schema Updates (`market_indicators.db`)
**Location**: `trading_system/src/data_layer/indicator_storage.py` (Class: `MarketIndicatorStorage`)

We need to add a new table `stock_fundamentals` to store historical fundamental data.

### Proposed Database Schema
*   **Table Name**: `stock_fundamentals`
*   **Columns**:
    *   `symbol` (TEXT): Ticker symbol of the stock.
    *   `date` (TEXT): The report date (standard ISO `YYYY-MM-DD` format).
    *   `revenue` (REAL): Quarterly/annual revenue.
    *   `operating_income` (REAL): Operating income.
    *   `dividend_per_share` (REAL): Dividends declared per share.
    *   **Primary Key**: `(symbol, date)`

### Code Modifications in `indicator_storage.py`

1.  **Table Initialization (`_init_db` method)**:
    Add the SQL statement to create the table:
    ```python
    # Inside MarketIndicatorStorage._init_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            symbol TEXT,
            date TEXT,
            revenue REAL,
            operating_income REAL,
            dividend_per_share REAL,
            PRIMARY KEY (symbol, date)
        )
    ''')
    ```

2.  **Saving Fundamentals**:
    Add a method to bulk upsert fundamental records:
    ```python
    def save_fundamentals(self, df_fundamentals: pd.DataFrame):
        """
        Save fundamental records to stock_fundamentals table.
        df_fundamentals expects columns: ['symbol', 'date', 'revenue', 'operating_income', 'dividend_per_share']
        """
        sql = """
            INSERT OR REPLACE INTO stock_fundamentals 
            (symbol, date, revenue, operating_income, dividend_per_share)
            VALUES (?, ?, ?, ?, ?)
        """
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df_fundamentals.iterrows():
                conn.execute(sql, (
                    row['symbol'],
                    row['date'],
                    float(row['revenue']) if pd.notna(row['revenue']) else 0.0,
                    float(row['operating_income']) if pd.notna(row['operating_income']) else 0.0,
                    float(row['dividend_per_share']) if pd.notna(row['dividend_per_share']) else 0.0
                ))
            conn.commit()
    ```

3.  **Retrieving Fundamentals**:
    Add a method to query and load historical fundamentals for a stock symbol:
    ```python
    def get_fundamentals(self, symbol: str) -> pd.DataFrame:
        """Retrieve historical fundamentals for a single stock."""
        query = "SELECT * FROM stock_fundamentals WHERE symbol = ? ORDER BY date ASC"
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=(symbol,))
    ```

---

## 2. Data Fetching & Offline Mocking

### Live Data Fetching
*   **APIs Used**:
    *   `yfinance` (`yf`): Used in `market_data_handler.py`, `global_market.py`, `alt_data.py`, and `post_market_scoring.py` to retrieve stock metadata, real-time prices, indexes, and sentiment indicators.
    *   `FinanceDataReader` (`fdr`): Used in `indicator_storage.py` (fetching stock listings) and `run_pipeline.py` (fetching price series).
*   **Fundamental Fetching Implementation**:
    *   For US stocks (via `yfinance`), we can instantiate `yf.Ticker(symbol)` and read `.quarterly_financials` (or `.financials` for annual) and `.actions`.
        *   `revenue` corresponds to `'Total Revenue'`.
        *   `operating_income` corresponds to `'Operating Income'`.
        *   `dividend_per_share` can be aggregated by summing daily `.dividends` per quarter/date.
    *   For KR stocks (via `FinanceDataReader`), if direct financials are not available in offline mode, we will query them via public APIs or fallback on our mock data generator.

### Offline Testing & Mock Data
**Location**: `trading_system/src/ai/prediction_model.py` (Class: `FallbackMetadataDict`)

`FallbackMetadataDict` provides deterministic fallback mock metadata for any ticker not in the hardcoded benchmarks list. We will extend this dictionary and its generation logic to incorporate fundamental fields.

1.  **Extend Benchmark Dictionary**:
    Add fundamental benchmarks for real key stocks:
    ```python
    # Inside FallbackMetadataDict.__init__()
    benchmarks = {
        "AAPL": {
            "shares_outstanding": 15000000000.0, 
            "floating_shares": 14900000000.0,
            "revenue": 383285000000.0,
            "operating_income": 114301000000.0,
            "dividend_per_share": 0.96
        },
        "MSFT": {
            "shares_outstanding": 7400000000.0, 
            "floating_shares": 7300000000.0,
            "revenue": 227583000000.0,
            "operating_income": 88523000000.0,
            "dividend_per_share": 3.00
        },
        # ... Add other benchmarks
    }
    ```

2.  **Extend Mock Generator (`_generate_mock_metadata`)**:
    Add deterministic mock generation logic for fundamental data based on the symbol's MD5 hash value:
    ```python
    def _generate_mock_metadata(self, symbol: str) -> dict:
        h = hashlib.md5(symbol.encode('utf-8')).hexdigest()
        val = int(h, 16)
        shares_outstanding = 10000000 + (val % 990000000)
        float_pct = 0.5 + 0.4 * ((val >> 32) % 100) / 100.0
        floating_shares = shares_outstanding * float_pct
        
        # Mock fundamentals based on MD5 value
        revenue = 1000000.0 + (val % 100000000.0)
        operating_income = revenue * (0.05 + 0.25 * ((val >> 16) % 100) / 100.0)
        dividend_per_share = 0.1 + 4.9 * ((val >> 8) % 100) / 100.0
        
        return {
            "shares_outstanding": float(shares_outstanding),
            "floating_shares": float(floating_shares),
            "revenue": float(revenue),
            "operating_income": float(operating_income),
            "dividend_per_share": float(dividend_per_share)
        }
    ```

---

## 3. Feature Engineering & Integration Pipeline
**Location**: `trading_system/src/ai/prediction_model.py` (Method: `OnDevicePredictionModel._create_features`)

### Merging Fundamentals with Price Series
Since fundamental reports occur quarterly or annually while price data is daily, we will perform a left join on date and **forward-fill (`ffill()`)** the fundamental fields so every trading day contains the latest available fundamental metrics.

1.  **Data Alignment Step**:
    In the data preparation methods (`prepare_training_data`, `predict_current`, and `process_and_predict_all`), we must load fundamental data from `MarketIndicatorStorage` or the `FALLBACK_METADATA` client and merge it with the price dataframe:
    ```python
    def merge_fundamentals(self, symbol: str, df_prices: pd.DataFrame, storage: MarketIndicatorStorage = None) -> pd.DataFrame:
        df = df_prices.copy()
        
        # Try to retrieve real fundamentals from database
        df_fun = None
        if storage is not None:
            try:
                df_fun = storage.get_fundamentals(symbol)
            except Exception as e:
                logger.warning(f"Failed to fetch fundamentals from DB for {symbol}: {e}")
                
        # If no DB records exist, load from FallbackMetadata
        if df_fun is None or df_fun.empty:
            meta = FALLBACK_METADATA[symbol]
            df['revenue'] = meta['revenue']
            df['operating_income'] = meta['operating_income']
            df['dividend_per_share'] = meta['dividend_per_share']
        else:
            # Format and align date index / column
            df_fun['date'] = pd.to_datetime(df_fun['date'])
            df = df.reset_index()
            df['date'] = pd.to_datetime(df['Date']) # Ensure casing aligns
            df = pd.merge(df, df_fun, on='date', how='left')
            df = df.set_index('Date')
            
            # Forward-fill quarterly data to daily resolution
            df[['revenue', 'operating_income', 'dividend_per_share']] = \
                df[['revenue', 'operating_income', 'dividend_per_share']].ffill().fillna(0.0)
                
        return df
    ```

2.  **Calculating the Three New Features**:
    Inject the feature calculations into `_create_features(df)`:
    ```python
    # 1. operating_margin = operating_income / revenue
    df['operating_margin'] = df['operating_income'] / df['revenue'].replace(0.0, np.nan)
    df['operating_margin'] = df['operating_margin'].fillna(0.0)
    
    # 2. revenue_to_market_cap = revenue / market_cap
    # Note: market_cap is Close * shares_outstanding (computed in apply_market_normalization)
    df['revenue_to_market_cap'] = df['revenue'] / df['market_cap'].replace(0.0, np.nan)
    df['revenue_to_market_cap'] = df['revenue_to_market_cap'].fillna(0.0)
    
    # 3. dividend_yield = dividend_per_share / Close
    df['dividend_yield'] = df['dividend_per_share'] / df['Close'].replace(0.0, np.nan)
    df['dividend_yield'] = df['dividend_yield'].fillna(0.0)
    ```

---

## 4. OnDevicePredictionModel Configurations
**Location**: `trading_system/src/ai/prediction_model.py`

### Feature Dimension Upgrade (9 → 12)
We must expand the list of feature column names from 9 to 12.

```python
# Updated features list inside OnDevicePredictionModel
features = [
    'ret_1d', 
    'ret_5d', 
    'ret_20d', 
    'ret_60d', 
    'dist_sma_20', 
    'vol_20d', 
    'norm_market_cap', 
    'norm_floating_value', 
    'norm_volume',
    'operating_margin',        # New Feature 1
    'revenue_to_market_cap',   # New Feature 2
    'dividend_yield'           # New Feature 3
]
```

This updated list must be applied to the following methods:
1.  `train(self, df_train)`: The features list passed to XGBoost training.
2.  `predict_current(self, df_current)`: Feature matrix generation for single ticker inference.
3.  `process_and_predict_all(self, prices_dict)`: Feature matrix generation for batch inference.

### Model Training & Prediction Pipelines
*   **Model Training Location**: `OnDevicePredictionModel.train`
    *   Fits an `xgb.XGBRegressor` for each horizon (`[1, 5, 10, 20, 30, 60, 120, 200]`).
*   **Pipeline Coordination**: `trading_system/run_pipeline.py`
    *   Fetches S&P 500 and KRX data.
    *   Calls `prepare_training_data` and triggers training.
    *   Runs predictions on inference data and updates the `ai_predictions` table.
    *   **Updates Required**: In `run_pipeline.py`, ensure we query fundamentals data and merge it into `train_data_dict` and `infer_data_dict` before feeding them to the prediction model.

---

## 5. Strategy Engines and Scoring Updates

### Post-Market Scoring
**Location**: `trading_system/scripts/post_market_scoring.py`
*   **Function**: Calculates composite scores (`0.40 * tech_score + 0.40 * ai_score + 0.20 * sentiment_score`) and ranks stocks daily.
*   **Updates Required**:
    *   In the scoring loop, load fundamental data from `MarketIndicatorStorage` (or fallback metadata) and merge it with `df_prices_norm` before feeding it to `prediction_model._create_features`.
    *   Ensure the data generator `generate_simulated_prices` creates mock fundamentals columns so the scoring pipeline doesn't crash during offline tests when real price data falls back to simulations.

### HybridStrategyEngine
**Location**: `trading_system/src/core/strategy_engine.py`
*   **Function**: Uses `MLEngine` (RandomForest + XGBoost Classifier) to compute the probability of a price increase.
*   **Prediction Model Use**: It consumes AI predictions via `storage.get_predictions(date_str)` and applies liquidity-scaling penalties based on `norm_volume` and `norm_floating_value`.
*   **Updates Required**: No core logic changes are needed in `HybridStrategyEngine` because it uses predictions stored in `ai_predictions.db` which will automatically incorporate the new 12-feature model's outputs.

---

## 6. Test Updates and Verification Strategy

To verify our changes work correctly without breaking existing logic, the following tests must be updated:

1.  **`tests/test_database.py`**:
    *   Add tests for `MarketIndicatorStorage.save_fundamentals` and `MarketIndicatorStorage.get_fundamentals`.
    *   Verify SQL constraints and data type conversions.
2.  **`tests/test_feature_normalization.py`**:
    *   Update mock dataframes used in test cases (like `df_aapl`, `df_msft`, `df_samsung`) to include mock fundamental fields (`revenue`, `operating_income`, `dividend_per_share`).
    *   Add assertions checking that `operating_margin`, `revenue_to_market_cap`, and `dividend_yield` are correctly calculated and handled.
3.  **`tests/test_feature_normalization_stress.py`**:
    *   Test edge cases for fundamental features:
        *   Division by zero (e.g., `revenue = 0` or `Close = 0`).
        *   Negative fundamental inputs (e.g., negative operating income).
        *   Missing records (`NaN` values) and check that forward-filling operates correctly.
4.  **`tests/test_post_market_scoring.py`**:
    *   Update the mocked price dataframes to include mock fundamental columns to prevent schema mismatch errors during test runs.

### Verification Command
Run the system tests:
```powershell
pytest tests/test_feature_normalization.py tests/test_feature_normalization_stress.py tests/test_post_market_scoring.py tests/test_database.py
```
