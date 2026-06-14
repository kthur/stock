# Design Proposal: Incorporating Fundamental Data and Features

## Executive Summary
This document proposes a detailed design and implementation strategy to integrate fundamental data (**Revenue**, **Operating Income**, **Dividends**) and new fundamental-based features (**operating_margin**, **revenue_to_market_cap**, **dividend_yield**) into the existing stock prediction models, pipelines, strategy engines, database schemas, and testing infrastructure of the trading system. 

---

## 1. Database Schema Updates (`market_indicators.db`)
The database `market_indicators.db` is handled in `trading_system/src/data_layer/indicator_storage.py` by the `MarketIndicatorStorage` class.

### Proposed Table Schema
We will create a new table `stock_fundamentals` to persist the fundamental metrics.

```sql
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    symbol TEXT,
    date TEXT,
    revenue REAL,
    operating_income REAL,
    dividend_per_share REAL,
    PRIMARY KEY (symbol, date)
);
```

### Code Modifications in `indicator_storage.py`
1. **Modify `_init_db(self)`**: Add the SQL execution statement to create the `stock_fundamentals` table.
2. **Add CRUD Operations**:
   - `save_fundamentals(self, symbol: str, date_str: str, revenue: float, operating_income: float, dividend_per_share: float)`: Saves or replaces fundamental metrics for a symbol and date.
   - `get_fundamentals(self, symbol: str, date_str: Optional[str] = None) -> pd.DataFrame`: Retrieves historical fundamentals.

#### Implementation Sketch in `MarketIndicatorStorage`:
```python
    # In _init_db(self):
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

    # New Methods:
    def save_fundamentals(self, symbol: str, date_str: str, revenue: float, operating_income: float, dividend_per_share: float):
        sql = """
            INSERT OR REPLACE INTO stock_fundamentals 
            (symbol, date, revenue, operating_income, dividend_per_share)
            VALUES (?, ?, ?, ?, ?)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(sql, (symbol, date_str, revenue, operating_income, dividend_per_share))
            conn.commit()

    def get_fundamentals(self, symbol: str, date_str: Optional[str] = None) -> pd.DataFrame:
        cleaned = symbol.strip().upper().split('.')[0]
        with sqlite3.connect(self.db_path) as conn:
            if date_str:
                query = "SELECT * FROM stock_fundamentals WHERE symbol = ? AND date = ?"
                return pd.read_sql(query, conn, params=(cleaned, date_str))
            else:
                query = "SELECT * FROM stock_fundamentals WHERE symbol = ? ORDER BY date ASC"
                return pd.read_sql(query, conn, params=(cleaned,))
```

---

## 2. API Fetching & Offline Fallbacks
Stock data is fetched using `yfinance` and `FinanceDataReader` in `run_pipeline.py`, `post_market_scoring.py`, and `screener.py`. Offline testing relies on the `FallbackMetadataDict` class in `trading_system/src/ai/prediction_model.py`.

### Fetching Strategy
We will extend data-fetching paths to pull quarterly/annual fundamental reports:
- **US Stocks (`yfinance`)**: Use `yf.Ticker(symbol).quarterly_financials` or `yf.Ticker(symbol).financials` to retrieve Revenue and Operating Income. Retrieve Dividends via `yf.Ticker(symbol).dividends`.
- **Korean Stocks (`FinanceDataReader`)**: Use `fdr.DataReader` or fallback to `yfinance` (as yfinance supports Korean tickers such as `005930.KS`).
- The fetched data will be stored daily/quarterly in the `stock_fundamentals` table.

### Extending `FallbackMetadataDict` for Offline Testing
We will add `revenue`, `operating_income`, and `dividend_per_share` to both the real benchmark definitions and the dynamic mock generator in `FallbackMetadataDict` (inside `prediction_model.py`):

#### Real Benchmark Updates (Lines 25-41):
```python
        benchmarks = {
            "AAPL": {"shares_outstanding": 15000000000.0, "floating_shares": 14900000000.0, "revenue": 385000000000.0, "operating_income": 114000000000.0, "dividend_per_share": 0.96},
            "MSFT": {"shares_outstanding": 7400000000.0, "floating_shares": 7300000000.0, "revenue": 245000000000.0, "operating_income": 109000000000.0, "dividend_per_share": 3.00},
            # Add corresponding metrics for NVDA, TSLA, 005930, etc.
        }
```

#### Dynamic Mock Generator (Lines 68-77):
```python
    def _generate_mock_metadata(self, symbol: str) -> dict:
        h = hashlib.md5(symbol.encode('utf-8')).hexdigest()
        val = int(h, 16)
        shares_outstanding = 10000000 + (val % 990000000)
        float_pct = 0.5 + 0.4 * ((val >> 32) % 100) / 100.0
        floating_shares = shares_outstanding * float_pct
        
        # New: Deterministic mock fundamentals
        revenue = 100000000.0 + (val % 9000000000.0)  # $100M to $9.1B
        operating_margin = 0.05 + 0.25 * ((val >> 16) % 100) / 100.0  # 5% to 30%
        operating_income = revenue * operating_margin
        dividend_yield = 0.0 + 0.05 * ((val >> 8) % 100) / 100.0  # 0% to 5%
        # Approximate dividend per share based on a typical stock price of $100
        dividend_per_share = 100.0 * dividend_yield
        
        return {
            "shares_outstanding": float(shares_outstanding),
            "floating_shares": float(floating_shares),
            "revenue": float(revenue),
            "operating_income": float(operating_income),
            "dividend_per_share": float(dividend_per_share)
        }
```

---

## 3. Feature Engineering Pipeline
The feature calculations occur in `OnDevicePredictionModel._create_features` and `OnDevicePredictionModel.apply_market_normalization`.

### Injecting the Three New Features
The three new features are:
1. `operating_margin = operating_income / revenue`
2. `revenue_to_market_cap = revenue / market_cap`
3. `dividend_yield = dividend_per_share / Close`

We will modify `OnDevicePredictionModel._create_features` to compute these.

#### Step 1: Pre-populate DataFrame with Fundamentals
When loading the price DataFrame for feature calculation, we must join the fundamental columns. If columns are not in the DataFrame, we retrieve them from `FALLBACK_METADATA`.

```python
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if len(df) < 65:
            return pd.DataFrame()

        # If normalized features are not present, apply market normalization
        if not all(col in df.columns for col in ['norm_market_cap', 'norm_floating_value', 'norm_volume']):
            norm_dict = self.apply_market_normalization({'TEMP': df})
            df = norm_dict['TEMP']

        # Inject/Align Fundamental Columns
        symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'TEMP'
        metadata = FALLBACK_METADATA.get(symbol)
        
        revenue = df['revenue'] if 'revenue' in df.columns else metadata.get('revenue', 1e9)
        operating_income = df['operating_income'] if 'operating_income' in df.columns else metadata.get('operating_income', 1e8)
        div_per_share = df['dividend_per_share'] if 'dividend_per_share' in df.columns else metadata.get('dividend_per_share', 1.0)
        
        # Calculate new features with division-by-zero protection
        def safe_divide(series_num, series_den):
            return series_num.div(series_den).replace([np.inf, -np.inf], 0.0).fillna(0.0)
            
        df['operating_margin'] = safe_divide(operating_income, revenue)
        df['revenue_to_market_cap'] = safe_divide(revenue, df['market_cap'])
        df['dividend_yield'] = safe_divide(div_per_share, df['Close'])
        
        # Return technical + momentum features
        df['ret_1d'] = df['Close'].pct_change(1)
        df['ret_5d'] = df['Close'].pct_change(5)
        df['ret_20d'] = df['Close'].pct_change(20)
        df['ret_60d'] = df['Close'].pct_change(60)
        
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['sma_60'] = df['Close'].rolling(60).mean()
        df['dist_sma_20'] = df['Close'] / df['sma_20'] - 1
        df['vol_20d'] = df['ret_1d'].rolling(20).std()
        
        # Drop NaN rows
        df.dropna(inplace=True)
        return df
```

---

## 4. Model Configuration & Training
`OnDevicePredictionModel` is defined in `trading_system/src/ai/prediction_model.py`. 

### Schema Configuration (12 Features)
The feature schema will be expanded to exactly 12 features. In `train()`, `predict_current()`, and `process_and_predict_all()`, we will modify the hardcoded feature list:

```python
        features = [
            'ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d', 
            'norm_market_cap', 'norm_floating_value', 'norm_volume',
            'operating_margin', 'revenue_to_market_cap', 'dividend_yield'
        ]
```

### Model Training & Prediction
- **Training Pipeline**: Triggers in `run_pipeline.py` (lines 125-126) on training symbols data.
- **Batch Predictions**: Triggers in `run_pipeline.py` (line 154) on the inference database universe.
- **On-the-fly Prediction**: Triggers in `post_market_scoring.py` (lines 252-257).
- **MacroPredictor**: Defined in `trading_system/src/analysis/macro_predictor.py` and run via `StockScreener` in `screener.py`. If desired, we will also expand `screener.py` to extract these three features and pass them/their lags to `MacroPredictor`.

---

## 5. Strategy Engine & Daily Scoring Updates
`HybridStrategyEngine` and `post_market_scoring.py` use predictions for scoring and order allocations.

### Updates in `post_market_scoring.py`
In `main()` of `post_market_scoring.py`:
- Join fundamental columns (`revenue`, `operating_income`, `dividend_per_share`) to the loaded historical DataFrames.
- Pass the enriched DataFrames to `OnDevicePredictionModel` so that the model can compute the 12 features and perform predictions correctly.

### Updates in `HybridStrategyEngine`
In `strategy_engine.py` (line 615):
- Scale down confidence scores or allocate less capital to stocks with weak operating margin or dividend yield.
- Use fundamental metrics directly in allocation rule checks (e.g. limiting portfolio weights on stocks with high `revenue_to_market_cap` or low operating margin).

---

## 6. Testing Strategy
To verify these additions, we need to update existing tests or create new ones in `trading_system/tests/`:

### Updated Tests:
1. **`test_feature_normalization.py`**:
   - Verify `FallbackMetadataDict` includes key/mock fundamentals.
   - Verify `OnDevicePredictionModel._create_features` outputs exactly 12 features and calculates `operating_margin`, `revenue_to_market_cap`, and `dividend_yield` correctly.
2. **`test_post_market_scoring.py`**:
   - Update `mock_yf_ticker` and `mock_fdr_reader` to return DataFrames containing mock fundamentals columns.
   - Verify the pipeline completes successfully without feature size mismatch errors.

### New Tests:
1. **`test_fundamentals_db.py`**:
   - Test `MarketIndicatorStorage.save_fundamentals` and `get_fundamentals` CRUD capabilities.
   - Assert key constraints and primary key collisions behavior.
