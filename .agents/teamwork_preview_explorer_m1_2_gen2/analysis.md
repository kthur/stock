# Milestone 1: Feature Engineering Analysis and Design

This report outlines the analysis and draft design for **Milestone 1 (Feature Engineering)** of the Price Prediction Feature Upgrades. 

---

## 1. Analysis of Current Codebase
We investigated where daily price and volume data is fetched and processed in the current system. The key components identified are:

### A. Data Fetching and Caching
*   **`trading_system/src/data_layer/market_data_handler.py`**:
    *   **Live Data Fetching**: `fetch_live_data(symbol)` retrieves live price and volume from `yfinance` via `yf.Ticker(symbol).fast_info` or `ticker.history(period="1d", interval="1m")` as fallback.
    *   **Historical Data Fetching**: `fetch_historical_data(symbol, period)` retrieves daily price bars (Open, High, Low, Close, Volume) using `yf.Ticker(symbol).history(period=period)`. It caches this historical data locally in `trading_system/data/cache/<symbol>_<period>.parquet` with a 24-hour TTL.
*   **`trading_system/run_pipeline.py`**:
    *   `fetch_data_fdr(symbol, market, start_date)` fetches historical price data (Date, Open, High, Low, Close, Volume) using `FinanceDataReader.DataReader(symbol, start=start_date)`. It retrieves training data since `2023-01-01` and inference data since `2025-01-01`.
*   **`trading_system/scripts/post_market_scoring.py`**:
    *   `fetch_historical_prices(symbol, market)` fetches daily historical price bars (tail 90 rows) using `yf.Ticker(symbol).history(period="3mo")` for SP500 and `FinanceDataReader.DataReader(symbol)` for KRX. If fetching fails, it falls back to `generate_simulated_prices(symbol, length=70)`, which deterministically generates mock prices using the symbol's character sum.

### B. Feature Processing
*   **`trading_system/src/ai/prediction_model.py`**:
    *   `_create_features(df)` takes a DataFrame of daily price bars (Ohlcv) and processes it to create technical and momentum features. Currently, it generates 6 features: `'ret_1d'`, `'ret_5d'`, `'ret_20d'`, `'ret_60d'`, `'dist_sma_20'`, and `'vol_20d'`.
    *   It does not currently incorporate stock-level market features (Market Cap, Volume, Floating Value) or cross-sectional normalization.

---

## 2. Recommendations for Stock and Market-Level Calculations

To calculate market cap, volume, floating shares, floating value, and market baseline totals daily across the stock universe, we recommend the following approach:

### A. Stock-Level Calculations
1.  **Outstanding Shares ($OS_s$)**:
    *   Fetch once during data ingestion/initialization.
    *   *US Stocks (SP500)*: Retrieve `ticker.info.get('sharesOutstanding')` from `yfinance`.
    *   *Korean Stocks (KRX)*: Retrieve `'Stocks'` (listed shares count) from `fdr.StockListing('KRX')`.
2.  **Daily Market Cap ($MC_s(t)$)**:
    *   Calculated dynamically per day $t$ using the daily closing price:
        $$MC_s(t) = \text{Close}_s(t) \times OS_s$$
    *   Using outstanding shares times daily close ensures that the market cap accurately reflects daily price changes.
3.  **Daily Volume ($V_s(t)$)**:
    *   Obtained directly from the `'Volume'` column in the price DataFrame.
4.  **Floating Shares ($FS_s$)**:
    *   *US Stocks (SP500)*: Retrieve `ticker.info.get('floatShares')` from `yfinance`.
    *   *Korean Stocks (KRX)*: yfinance does not reliably return floating shares for KRX, and `FinanceDataReader` listings do not provide it. We recommend using a standard industry estimate of $70\%$ of outstanding shares ($FS_s = 0.70 \times OS_s$).
5.  **Daily Floating Value ($FV_s(t)$)**:
    *   Calculated as:
        $$FV_s(t) = \text{Close}_s(t) \times FS_s$$
    *   **Fallback**: If $FS_s$ is unavailable/missing, fall back to:
        $$FV_s(t) = \text{Close}_s(t) \times V_s(t)$$ (using daily trading volume as a proxy for floating liquidity)

### B. Market-Level Daily Baseline Totals
On each day $t$, we compute the cross-sectional sums across the active stock universe $U(t)$ (stocks that have valid data on day $t$):
1.  **Total Market Cap ($TMC(t)$)**:
    $$TMC(t) = \sum_{j \in U(t)} MC_j(t)$$
2.  **Total Floating Value ($TFV(t)$)**:
    $$TFV(t) = \sum_{j \in U(t)} FV_j(t)$$
3.  **Total Volume ($TV(t)$)**:
    $$TV(t) = \sum_{j \in U(t)} V_j(t)$$

---

## 3. Formulas and Implementation Logic for Normalized Stock Features

We define the cross-sectionally normalized features for each stock $s$ on day $t$ as follows:

### A. Mathematical Formulas
1.  **Normalized Market Cap (`norm_market_cap`)**:
    $$\text{norm\_market\_cap}_s(t) = \frac{MC_s(t)}{TMC(t)} = \frac{\text{Close}_s(t) \times OS_s}{\sum_{j \in U(t)} (\text{Close}_j(t) \times OS_j)}$$
2.  **Normalized Floating Value (`norm_floating_value`)**:
    $$\text{norm\_floating\_value}_s(t) = \frac{FV_s(t)}{TFV(t)} = \frac{\text{Close}_s(t) \times FS_s}{\sum_{j \in U(t)} (\text{Close}_j(t) \times FS_j)}$$
3.  **Normalized Volume (`norm_volume`)**:
    $$\text{norm\_volume}_s(t) = \frac{V_s(t)}{TV(t)} = \frac{V_s(t)}{\sum_{j \in U(t)} V_j(t)}$$

### B. Implementation Contract
The implementation must adhere to the interface contract specified in `SCOPE.md`:
*   **Signature**: `OnDevicePredictionModel.apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]`
*   **Input**: `prices_dict` containing mappings of `symbol` to DataFrames. Each DataFrame must have columns: `Close`, `Volume`, and metadata columns `outstanding_shares`, `floating_shares`.
*   **Output**: Updated DataFrames in `prices_dict` with columns: `norm_market_cap`, `norm_floating_value`, `norm_volume`.

### C. Reference Normalization Logic
To perform cross-sectional daily calculations efficiently, we merge all stocks' dataframes, perform grouping by `Date`, and divide individual values by the group sum:

```python
def apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Apply cross-sectional market normalization over the stock universe daily.
    """
    # 1. Combine all symbols' data into a single DataFrame with multi-index
    combined_list = []
    for symbol, df in prices_dict.items():
        if df is None or df.empty:
            continue
        df = df.copy()
        
        # Ensure index is datetime and named 'Date'
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df.index.name = 'Date'
        
        # Add symbol column and reset index to make Date a column for merging
        df = df.reset_index()
        df['symbol'] = symbol
        
        # Resolve metadata if not present in DataFrame
        metadata = self.get_metadata(symbol) # retrieval from fallback/live
        if 'outstanding_shares' not in df.columns:
            df['outstanding_shares'] = metadata['outstanding_shares']
        if 'floating_shares' not in df.columns:
            df['floating_shares'] = metadata['floating_shares']
            
        # Compute daily stock-level metrics
        df['market_cap'] = df['Close'] * df['outstanding_shares']
        
        # Compute daily floating value with fallback to Close * Volume
        if df['floating_shares'].isna().all() or (df['floating_shares'] <= 0).all():
            df['floating_value'] = df['Close'] * df['Volume']
        else:
            df['floating_value'] = df['Close'] * df['floating_shares']
            
        combined_list.append(df)
        
    if not combined_list:
        return prices_dict

    combined_df = pd.concat(combined_list, ignore_index=True)
    
    # 2. Group by Date to calculate daily market-level totals
    daily_totals = combined_df.groupby('Date')[['market_cap', 'floating_value', 'Volume']].transform('sum')
    
    # Avoid division by zero by replacing 0 with epsilon or NaN
    daily_totals.replace(0, np.nan, inplace=True)
    
    # 3. Calculate normalized features
    combined_df['norm_market_cap'] = combined_df['market_cap'] / daily_totals['market_cap']
    combined_df['norm_floating_value'] = combined_df['floating_value'] / daily_totals['floating_value']
    combined_df['norm_volume'] = combined_df['Volume'] / daily_totals['Volume']
    
    # Fill remaining NaNs with 0.0
    combined_df[['norm_market_cap', 'norm_floating_value', 'norm_volume']] = \
        combined_df[['norm_market_cap', 'norm_floating_value', 'norm_volume']].fillna(0.0)
    
    # 4. Split back into the original dictionary format
    result_dict = {}
    for symbol in prices_dict.keys():
        symbol_df = combined_df[combined_df['symbol'] == symbol].copy()
        if symbol_df.empty:
            result_dict[symbol] = prices_dict[symbol]
            continue
        # Set Date index back
        symbol_df.set_index('Date', inplace=True)
        # Drop temporary working columns or keep them
        symbol_df.drop(columns=['symbol'], inplace=True)
        result_dict[symbol] = symbol_df
        
    return result_dict
```

---

## 4. Design of Deterministic Fallback Dictionary (`FALLBACK_METADATA`)

To support offline testing, backtests, and system execution when live metadata calls are unavailable, we design a custom dictionary class that contains real-world data for key benchmark stocks and generates realistic, deterministic mock metadata for any other ticker using a hash function.

### A. Design Constraints
*   **Stability**: Must be 100% deterministic (same symbol name always returns same mock value).
*   **Completeness**: Must support **all** active tickers in the universe (KOSPI, KOSDAQ, SP500, etc. — over 3,300 tickers) without bloating the codebase with a huge dictionary file.
*   **Realism**: Core benchmark stocks must use actual/realistic market cap and floating share values.

### B. Fallback Dict Implementation Code
We recommend placing this class and its instance `FALLBACK_METADATA` in a shared location, such as a new utility or in the prediction model file:

```python
import hashlib

class FallbackMetadataDict(dict):
    """
    A dictionary-like container that returns realistic, deterministic mock metadata 
    for any requested ticker. Core benchmark stocks return real values.
    """
    def __init__(self, base_dict):
        super().__init__(base_dict)
        
    def __getitem__(self, key):
        # Clean symbol to support both "005930" and "005930.KS"
        clean_key = key.split('.')[0]
        if clean_key in self:
            return super().__getitem__(clean_key)
        if key in self:
            return super().__getitem__(key)
            
        # Generate deterministic mock values based on hash of symbol
        h = int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)
        is_krx = clean_key.isdigit()
        
        if is_krx:
            # KRX stock: typical market cap 100B to 10T KRW
            mock_market_cap = 1e11 + (h % 99) * 1e11
            # Assume nominal price of 50,000 KRW to find outstanding shares
            mock_outstanding = mock_market_cap / 50000.0
            mock_floating = mock_outstanding * 0.70
        else:
            # US stock: typical market cap $1B to $500B USD
            mock_market_cap = 1e9 + (h % 499) * 1e9
            # Assume nominal price of $150 USD to find outstanding shares
            mock_outstanding = mock_market_cap / 150.0
            mock_floating = mock_outstanding * 0.75
            
        return {
            "market_cap": float(mock_market_cap),
            "outstanding_shares": float(mock_outstanding),
            "floating_shares": float(mock_floating)
        }
        
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
            
    def __contains__(self, key):
        # Always contains any ticker due to dynamic generation
        return True


# Populate core benchmark stocks with realistic 2026 values
FALLBACK_METADATA = FallbackMetadataDict({
    # US Major Stocks (SP500 benchmarks)
    "AAPL": {"market_cap": 3.2e12, "outstanding_shares": 15.4e9, "floating_shares": 15.3e9},
    "MSFT": {"market_cap": 3.1e12, "outstanding_shares": 7.43e9, "floating_shares": 7.4e9},
    "GOOGL": {"market_cap": 2.1e12, "outstanding_shares": 5.9e9, "floating_shares": 5.8e9},
    "GOOG": {"market_cap": 2.1e12, "outstanding_shares": 5.9e9, "floating_shares": 5.8e9},
    "AMZN": {"market_cap": 1.9e12, "outstanding_shares": 10.4e9, "floating_shares": 10.4e9},
    "TSLA": {"market_cap": 6.5e11, "outstanding_shares": 3.18e9, "floating_shares": 3.2e9},
    "NVDA": {"market_cap": 3.0e12, "outstanding_shares": 24.6e9, "floating_shares": 24.5e9},
    "META": {"market_cap": 1.2e12, "outstanding_shares": 2.22e9, "floating_shares": 2.2e9},
    
    # KRX Major Stocks (KOSPI & KOSDAQ benchmarks)
    "005930": {"market_cap": 4.5e14, "outstanding_shares": 5.97e9, "floating_shares": 4.2e9}, # Samsung Electronics
    "000660": {"market_cap": 1.4e14, "outstanding_shares": 7.28e8, "floating_shares": 5.8e8}, # SK Hynix
    "005380": {"market_cap": 5.2e13, "outstanding_shares": 2.1e8, "floating_shares": 1.5e8},  # Hyundai Motor
    "000270": {"market_cap": 4.6e13, "outstanding_shares": 4.0e8, "floating_shares": 2.8e8},  # Kia
    "035420": {"market_cap": 2.8e13, "outstanding_shares": 1.6e8, "floating_shares": 1.2e8},  # NAVER
    "035720": {"market_cap": 1.8e13, "outstanding_shares": 4.4e8, "floating_shares": 3.1e8},  # Kakao
    "068270": {"market_cap": 3.6e13, "outstanding_shares": 2.2e8, "floating_shares": 1.6e8},  # Celltrion
    "207940": {"market_cap": 5.8e13, "outstanding_shares": 7.1e7, "floating_shares": 1.8e7},  # Samsung Biologics
})
```

---

## 5. Verification Plan
To verify the feature engineering calculations:
1.  **Unit Tests**: Add tests in `trading_system/tests/test_feature_normalization.py` to:
    *   Verify `apply_market_normalization` with a small mock dictionary of 3 stocks over 5 days.
    *   Confirm that `norm_market_cap`, `norm_floating_value`, and `norm_volume` sum up to exactly `1.0` on each day cross-sectionally.
    *   Verify that `FALLBACK_METADATA` returns correct predefined values for AAPL/005930, and deterministic mock values for random strings (e.g. "INVALID_TICKER").
2.  **Test Execution**: Run tests using:
    `pytest trading_system/tests/test_feature_normalization.py` or `python -m unittest discover -s trading_system/tests`
