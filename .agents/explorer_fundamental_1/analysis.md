# Detailed Design: Fundamental Data Integration Strategy

This document proposes a comprehensive design and integration strategy to incorporate fundamental data (Revenue, Operating Income, Dividends) and three new calculated features (operating_margin, revenue_to_market_cap, dividend_yield) into the stock prediction models, pipelines, strategy engine, database schemas, and testing frameworks.

---

## 1. Database Schema Changes (`market_indicators.db`)

### Current DB State
The SQLite database `market_indicators.db` is managed by `MarketIndicatorStorage` inside `src/data_layer/indicator_storage.py`. It currently initializes four tables:
- `global_indicators` (macro indicators, FX, and commodity prices)
- `stock_universe` (list of tickers, names, and markets)
- `ai_predictions` (saved AI models predictions)
- `post_market_rankings` (daily post-market composite scores and ranks)

### Proposed Table: `stock_fundamentals`
A new table `stock_fundamentals` will be created to store time-series fundamental data for all stocks in the universe.

#### Table Definition (SQL)
```sql
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    symbol TEXT,
    date TEXT,
    revenue REAL,
    operating_income REAL,
    dividend_per_share REAL,
    PRIMARY KEY (symbol, date)
)
```

### Required Code Modifications in `src/data_layer/indicator_storage.py`
We need to update `MarketIndicatorStorage` to create this table during database initialization and add methods for saving/retrieving fundamental data.

1. **Table Creation**: Add the table definition inside `_init_db()`:
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

2. **Save Method**: Add a method to save fundamentals:
   ```python
   def save_fundamentals(self, df_fundamentals: pd.DataFrame):
       """
       Save fundamental data.
       df_fundamentals: pd.DataFrame with columns ['symbol', 'date', 'revenue', 'operating_income', 'dividend_per_share']
       """
       sql = """
           INSERT OR REPLACE INTO stock_fundamentals (symbol, date, revenue, operating_income, dividend_per_share)
           VALUES (?, ?, ?, ?, ?)
       """
       with sqlite3.connect(self.db_path) as conn:
           for _, row in df_fundamentals.iterrows():
               conn.execute(sql, (
                   row['symbol'],
                   row['date'],
                   float(row['revenue']),
                   float(row['operating_income']),
                   float(row['dividend_per_share'])
               ))
           conn.commit()
   ```

3. **Retrieve Method**: Add a method to get fundamentals:
   ```python
   def get_fundamentals(self, symbol: Optional[str] = None, date_str: Optional[str] = None) -> pd.DataFrame:
       """Retrieve fundamental data for a given symbol and/or date."""
       query = "SELECT * FROM stock_fundamentals"
       params = []
       conditions = []
       if symbol:
           conditions.append("symbol = ?")
           params.append(symbol)
       if date_str:
           conditions.append("date = ?")
           params.append(date_str)
           
       if conditions:
           query += " WHERE " + " AND ".join(conditions)
           
       with sqlite3.connect(self.db_path) as conn:
           return pd.read_sql(query, conn, params=params)
   ```

---

## 2. API Data Fetching & Testing Bypasses

### Real Data Fetching (Production)
We will fetch the fundamental data using `yfinance` for US stocks (`SP500`) and fall back to custom handlers or yfinance (using `.KS` or `.KQ` suffixes) for Korean stocks (`KRX`).

#### US Tickers (`yfinance` implementation)
```python
ticker = yf.Ticker(symbol)

# Retrieve annual/quarterly financials
try:
    # Option A: Fast retrieval from ticker.info
    info = ticker.info
    revenue = info.get("totalRevenue")
    operating_margins = info.get("operatingMargins")
    operating_income = revenue * operating_margins if revenue and operating_margins else None
    dividend_per_share = info.get("dividendRate")
    
    # Option B: Fallback to financials dataframe if info is missing fields
    if revenue is None or operating_income is None:
        financials = ticker.financials  # Or quarterly_financials
        if not financials.empty and 'Total Revenue' in financials.index:
            revenue = financials.loc['Total Revenue'].iloc[0]
        if not financials.empty and 'Operating Income' in financials.index:
            operating_income = financials.loc['Operating Income'].iloc[0]
except Exception as e:
    logger.warning(f"Failed to fetch yfinance fundamentals for {symbol}: {e}")
```

### Offline Testing Fallback Strategy (`FallbackMetadataDict`)
For unit testing and strict offline environments (such as Antigravity's `CODE_ONLY` mode), we mock fundamental values. The class `FallbackMetadataDict` in `src/ai/prediction_model.py` dynamically returns deterministic mock data based on MD5 hashes of stock symbols.

#### Code Modifications in `src/ai/prediction_model.py`

1. **Hardcoded Benchmark Values**: Update the `benchmarks` dictionary with realistic values for standard tickers:
   ```python
   # Inside FallbackMetadataDict.__init__()
   benchmarks = {
       "AAPL": {
           "shares_outstanding": 15000000000.0,
           "floating_shares": 14900000000.0,
           "revenue": 385000000000.0,
           "operating_income": 115000000000.0,
           "dividend_per_share": 0.96
       },
       "MSFT": {
           "shares_outstanding": 7400000000.0,
           "floating_shares": 7300000000.0,
           "revenue": 225000000000.0,
           "operating_income": 88000000000.0,
           "dividend_per_share": 2.80
       },
       "005930": {
           "shares_outstanding": 5969782550.0,
           "floating_shares": 4500000000.0,
           "revenue": 300000000000000.0,
           "operating_income": 15000000000000.0,
           "dividend_per_share": 1444.0
       },
       # ... other benchmarks updated similarly
   }
   ```

2. **Adversarial Mock Generation**: Update `_generate_mock_metadata` to return deterministic fundamental values for unknown tickers:
   ```python
   def _generate_mock_metadata(self, symbol: str) -> dict:
       h = hashlib.md5(symbol.encode('utf-8')).hexdigest()
       val = int(h, 16)
       shares_outstanding = 10000000 + (val % 990000000)
       float_pct = 0.5 + 0.4 * ((val >> 32) % 100) / 100.0
       floating_shares = shares_outstanding * float_pct
       
       # Generate deterministic fundamental mock metrics
       revenue = 50000000.0 + (val % 9500000000.0)
       operating_pct = 0.05 + 0.25 * ((val >> 16) % 100) / 100.0
       operating_income = revenue * operating_pct
       dividend_per_share = 0.0 + 5.0 * ((val >> 48) % 100) / 100.0
       
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

The calculated features are:
1. **`operating_margin`** = `operating_income` / `revenue`
2. **`revenue_to_market_cap`** = `revenue` / `market_cap`
3. **`dividend_yield`** = `dividend_per_share` / `Close`

### Feature Injection Strategy
We will inject these features directly in `OnDevicePredictionModel` inside `src/ai/prediction_model.py`. The design ensures that if raw fundamentals are not pre-merged into the input stock DataFrame, the model queries `FALLBACK_METADATA` as a fallback.

#### Modification 1: `apply_market_normalization`
Ensure `df_copy` contains `revenue`, `operating_income`, and `dividend_per_share` columns before performing cross-sectional normalization.
```python
# Inside OnDevicePredictionModel.apply_market_normalization()
metadata = FALLBACK_METADATA[sym]

shares_out = df_copy['shares_outstanding'] if 'shares_outstanding' in df_copy.columns else metadata['shares_outstanding']
float_sh = df_copy['floating_shares'] if 'floating_shares' in df_copy.columns else metadata['floating_shares']

# Extract raw fundamentals (using column or fallback metadata)
revenue = df_copy['revenue'] if 'revenue' in df_copy.columns else metadata.get('revenue', 0.0)
operating_inc = df_copy['operating_income'] if 'operating_income' in df_copy.columns else metadata.get('operating_income', 0.0)
div_per_share = df_copy['dividend_per_share'] if 'dividend_per_share' in df_copy.columns else metadata.get('dividend_per_share', 0.0)

# Set columns to df_copy
df_copy['shares_outstanding'] = shares_out
df_copy['floating_shares'] = float_sh
df_copy['revenue'] = revenue
df_copy['operating_income'] = operating_inc
df_copy['dividend_per_share'] = div_per_share

df_copy['market_cap'] = df_copy['Close'] * shares_out
# (existing market cap and floating value normalization logic remains unchanged)
```

#### Modification 2: `_create_features`
Perform calculations of the three new fundamental features:
```python
# Inside OnDevicePredictionModel._create_features()
# After applying normalization columns...

# 1. Operating Margin (zero-division protected)
df['operating_margin'] = df['operating_income'] / df['revenue'].replace(0, np.nan)
df['operating_margin'] = df['operating_margin'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

# 2. Revenue to Market Cap (zero-division protected)
df['revenue_to_market_cap'] = df['revenue'] / df['market_cap'].replace(0, np.nan)
df['revenue_to_market_cap'] = df['revenue_to_market_cap'].fillna(0.0).replace([np.inf, -np.inf], 0.0)

# 3. Dividend Yield (zero-division protected)
df['dividend_yield'] = df['dividend_per_share'] / df['Close'].replace(0, np.nan)
df['dividend_yield'] = df['dividend_yield'].fillna(0.0).replace([np.inf, -np.inf], 0.0)
```

---

## 4. Model Configurations & Training (`OnDevicePredictionModel`)

### Feature Schema Expansion
We expand the feature names list from **9 features** to **12 features**. 

#### Changes in `src/ai/prediction_model.py`
In `train()`, `predict_current()`, and `process_and_predict_all()`, update the hardcoded feature list:
```python
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
    'operating_margin',       # New Feature 1
    'revenue_to_market_cap',  # New Feature 2
    'dividend_yield'          # New Feature 3
]
```

### Model Training Pipeline Impact
The XGBoost models (trained for horizons: `[1, 5, 10, 20, 30, 60, 120, 200]`) will now fit on a 12-column input matrix instead of 9 columns.
- **Model Storage**: Trained model parameters will be saved as usual.
- **Execution Script**: In `run_pipeline.py` and `scripts/predict_best_stock.py`, the training flow will execute identically but will train models using the 12 features. The data fetching function `fetch_data_fdr` can be updated to fetch and append fundamental metrics if running in online/live production mode.

*Note on `MacroPredictor` (`src/analysis/macro_predictor.py`)*: This model trains on regional macro variables (like VIX, FX rates, yields) rather than stock-level technical/fundamental features. Thus, the feature schema of `MacroPredictor` is untouched by these stock-level fundamental features.

---

## 5. Strategy Engine & Daily Rankings

### Daily Post-Market Scoring (`scripts/post_market_scoring.py`)
During daily post-market scoring:
1. Historical prices are fetched for each stock (via `fetch_historical_prices`).
2. We query the `stock_fundamentals` database table to load current fundamental records for each stock.
3. The script merges `revenue`, `operating_income`, and `dividend_per_share` into each stock's price DataFrame.
   ```python
   # Inside post_market_scoring.py main()
   # Fetch fundamentals from DB
   fundamentals_df = storage.get_fundamentals(date_str=date_str)
   
   # For each stock:
   df_prices = prices_dict[symbol]
   if not fundamentals_df.empty:
       stock_fund = fundamentals_df[fundamentals_df['symbol'] == symbol]
       if not stock_fund.empty:
           df_prices['revenue'] = float(stock_fund['revenue'].iloc[0])
           df_prices['operating_income'] = float(stock_fund['operating_income'].iloc[0])
           df_prices['dividend_per_share'] = float(stock_fund['dividend_per_share'].iloc[0])
   ```
4. `prediction_model.apply_market_normalization(prices_dict)` is called. The model calculates normalized market caps, volumes, and computes the 12 features.
5. `prediction_model.predict_current(df_features)` is run. Predictions for the 20-day horizon will be outputted and saved as `ai_score` in the database ranking table.

### Strategy Engine (`src/core/strategy_engine.py`)
`HybridStrategyEngine` processes various active signals:
- **`ml_engine`** (`src/analysis/ml_engine.py`): In `HybridStrategyEngine.analyze`, the `ml_engine` runs classification algorithms predicting next-day up/down trends using technical indicators (currently 24 features). 
- We can propose adding a new fundamental scoring layer inside `HybridStrategyEngine` or incorporating `operating_margin` / `dividend_yield` directly in the `DividendStrategy` class in `src/strategy/famous_investors.py`. Currently, `DividendStrategy` searches for `dividend_yield` inside `stock_data.get("dividend_yield", 0)` (in %). We should update this mapping to load from the newly calculated database values, which ensures a single source of truth for dividend calculations.

---

## 6. Testing Strategy & Updates

The addition of 3 new features changes the expected structure of training and prediction inputs. All unit and integration test assertions must be updated to expect 12 features.

### A. Test files to modify:
1. **`tests/test_feature_normalization.py`**:
   - Update `test_fallback_metadata_dict` to assert that `FALLBACK_METADATA` contains keys `"revenue"`, `"operating_income"`, and `"dividend_per_share"`.
   - Update `test_apply_market_normalization` to verify that the returned DataFrame has the 3 new columns.
   
2. **`tests/test_feature_normalization_stress.py`**:
   - Verify that division-by-zero protection handles cases when `revenue` is `0.0` or `Close` is `0.0` (producing clean `0.0` features instead of `NaN` or `Inf`).

3. **`tests/test_post_market_scoring.py`**:
   - Update patches for `OnDevicePredictionModel.predict_current` to mock prediction with 12 features.
   - Insert mock fundamental records in `setUp` test database to mock retrieval during post-market ranking checks.

### B. New tests to create:
Create a new test file `tests/test_fundamentals_features.py` that verifies:
- `MarketIndicatorStorage` correctly creates the `stock_fundamentals` table, saves data, and retrieves it cleanly.
- `OnDevicePredictionModel._create_features` accurately calculates `operating_margin`, `revenue_to_market_cap`, and `dividend_yield` for known edge cases (e.g., negative operating income, zero revenue, zero price).
- A full XGBoost train/predict loop with a 12-feature schema runs successfully under offline mock data constraints.

---

## Summary Integration Matrix

| Target File | Action | Purpose |
|---|---|---|
| `src/data_layer/indicator_storage.py` | Create table `stock_fundamentals`, add `save_fundamentals` and `get_fundamentals`. | Establish DB storage and query APIs for fundamental data. |
| `src/ai/prediction_model.py` | Update `FallbackMetadataDict` benchmarks and `_generate_mock_metadata` generator. | Provide mock fundamental values for offline testing and fallback execution. |
| `src/ai/prediction_model.py` | Update `apply_market_normalization` and `_create_features`. | Inject the three new calculated features into the feature pipeline. |
| `src/ai/prediction_model.py` | Update feature name array to contain 12 features. | Train/infer XGBoost models using the expanded fundamental feature schema. |
| `scripts/post_market_scoring.py` | Fetch fundamentals from DB/fallback and merge into price DataFrame. | Incorporate fundamentals into the daily composite ranking system. |
| `tests/test_feature_normalization.py` | Update assertions to check new metadata and columns. | Guarantee feature schema consistency during normalization. |
| `tests/test_post_market_scoring.py` | Mock fundamentals table and scoring inputs. | Validate post-market scoring script outputs under the new schema. |
