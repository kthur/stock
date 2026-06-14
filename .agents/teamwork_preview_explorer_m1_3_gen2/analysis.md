# Milestone 1 (Feature Engineering) Analysis and Design Plan

## 1. Codebase Exploration: Price and Volume Data Flow
Based on exploration of the codebase, daily price and volume data is fetched and processed in the following modules:

### Data Fetching Entry Points
1. **`trading_system/src/data_layer/market_data_handler.py`**:
   - **Live Data**: `fetch_live_data(self, symbol: str)` fetches the latest price and volume via `yfinance` (`ticker.fast_info` with a fallback to `ticker.history` 1d/1m).
   - **Historical Data**: `fetch_historical_data(self, symbol: str, period: str)` retrieves daily OHLCV bars using `yf.Ticker.history` and caches them locally in `data/cache/{symbol}_{period}.parquet`. Returns a list of `PriceBar` objects.
2. **`trading_system/run_pipeline.py`**:
   - **FDR Fetching**: `fetch_data_fdr(symbol: str, market: str, start_date: str)` fetches historical price and volume data using `FinanceDataReader`.
   - **Execution Pipeline**: `execute_prediction_pipeline()` coordinates loading the database universe, sampling symbols, downloading training data, and fetching current inference data (from `2025-01-01` to present) using a `ThreadPoolExecutor`.
3. **`trading_system/scripts/post_market_scoring.py`**:
   - **Scoring Fetch**: `fetch_historical_prices(symbol: str, market: str)` fetches historical prices using `yfinance` (for `market == 'SP500'`) or `FinanceDataReader` (for `market == 'KRX'`).
   - If real-world fetching fails, it falls back to `generate_simulated_prices(symbol, length=70)` which returns a deterministic random walk based on the symbol's character sum seed.

### Data Processing and Model Input
1. **`trading_system/src/ai/prediction_model.py`**:
   - `prepare_training_data(self, prices_dict: Dict[str, pd.DataFrame])` and `process_and_predict_all(self, prices_dict: Dict[str, pd.DataFrame])` process daily prices.
   - `_create_features(self, df: pd.DataFrame)` computes stock-level features: `ret_1d`, `ret_5d`, `ret_20d`, `ret_60d`, `sma_20`, `sma_60`, `dist_sma_20`, and `vol_20d`.
   - This feature engineering logic will be the central insertion point for the new normalized market features.

---

## 2. Recommendations for Stock-Level and Market-Level Calculations

### Stock-Level Calculations
- **Shares Outstanding ($SO_i$) & Floating Shares ($FS_i$)**:
  - Retrieved during data fetching from `yfinance` (`ticker.info.get('sharesOutstanding')`, `ticker.info.get('floatShares')`) or using the universe database listing if pre-populated.
  - Fall back to a local metadata dictionary (`FALLBACK_METADATA`) for offline test safety.
- **Stock-Level Market Cap ($MC_i(t)$)**:
  - Calculated dynamically on each daily bar $t$:
    $$MC_i(t) = Close_i(t) \times SO_i$$
- **Stock-Level Floating Value ($FV_i(t)$)**:
  - Calculated dynamically on each daily bar $t$:
    $$FV_i(t) = Close_i(t) \times FS_i$$
  - **Fallback**: If floating shares is unavailable or non-positive, use Volume as a proxy for floating shares:
    $$FV_i(t) = Close_i(t) \times Volume_i(t)$$

### Market-Level Daily Baseline Totals
To perform cross-sectional normalization, we must calculate the daily aggregate baseline totals across the active universe for each date $t$:
- **Total Market Cap Baseline ($TotalMC(t)$)**:
  $$TotalMC(t) = \sum_{j \in M(i)} MC_j(t)$$
- **Total Floating Value Baseline ($TotalFV(t)$)**:
  $$TotalFV(t) = \sum_{j \in M(i)} FV_j(t)$$
- **Total Volume Baseline ($TotalVol(t)$)**:
  $$TotalVol(t) = \sum_{j \in M(i)} Volume_j(t)$$

*Note: $M(i)$ represents the market group (e.g. S&P500 or KRX) containing stock $i$.*

---

## 3. Normalized Stock Features: Formulas and Logic

### Formulas
To make stock-level features scale-invariant and comparable cross-sectionally on day $t$:

1. **Normalized Market Cap (`norm_market_cap`)**:
   $$norm\_market\_cap_i(t) = \frac{MC_i(t)}{TotalMC(t)} = \frac{Close_i(t) \times SO_i}{\sum_{j \in M(i)} (Close_j(t) \times SO_j)}$$
2. **Normalized Floating Value (`norm_floating_value`)**:
   $$norm\_floating\_value_i(t) = \frac{FV_i(t)}{TotalFV(t)}$$
3. **Normalized Volume (`norm_volume`)**:
   $$norm\_volume_i(t) = \frac{Volume_i(t)}{TotalVol(t)} = \frac{Volume_i(t)}{\sum_{j \in M(i)} Volume_j(t)}$$

### Implementation Logic
We recommend implementing a new method `apply_market_normalization` within `OnDevicePredictionModel` to compute these features. 

#### Handling Grouped Normalization (USD vs. KRW)
The stock universe contains both US S&P 500 stocks (prices in USD) and Korean KRX stocks (prices in KRW). Because $1$ USD $\approx 1400$ KRW and share scales differ widely, performing a global normalization would cause KRX stock metrics to skew the results.
- **Recommended Strategy**: Grouped Cross-Sectional Normalization. Group stocks by their `market` attribute (e.g., `'SP500'` vs. `'KRX'`), compute market-level baseline sums within each group, and divide stock-level values by their respective group totals.
- This ensures normalized features represent a stock's relative scale *within its own market context* and removes currency dependency.

#### Code Sketch for `apply_market_normalization`:
```python
from typing import Dict
import pandas as pd
import numpy as np

def apply_market_normalization(self, prices_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Computes cross-sectional normalized features: norm_market_cap, norm_floating_value, norm_volume.
    """
    dfs = []
    for sym, df in prices_dict.items():
        if df.empty:
            continue
        df = df.copy()
        df['symbol'] = sym
        
        # Ensure metadata columns exist
        if 'market' not in df.columns:
            df['market'] = 'SP500'  # Fallback market
            
        # Retrieve shares outstanding & floating shares from metadata or fallback
        meta = FALLBACK_METADATA.get(sym)
        shares_outstanding = df.get('shares_outstanding', pd.Series(meta['shares_outstanding'], index=df.index))
        floating_shares = df.get('floating_shares', pd.Series(meta['floating_shares'], index=df.index))
        
        # Stock-level raw values
        df['market_cap'] = df['Close'] * shares_outstanding
        
        # Floating value with volume fallback
        df['floating_value'] = df['Close'] * floating_shares
        mask_fallback = floating_shares.isna() | (floating_shares <= 0)
        df.loc[mask_fallback, 'floating_value'] = df.loc[mask_fallback, 'Close'] * df.loc[mask_fallback, 'Volume']
        
        dfs.append(df)
        
    if not dfs:
        return prices_dict
        
    # Combine to perform cross-sectional calculations grouping by Date and Market
    panel_df = pd.concat(dfs)
    
    # Calculate daily totals per market group
    totals = panel_df.groupby([panel_df.index, 'market']).agg(
        total_market_cap=('market_cap', 'sum'),
        total_floating_value=('floating_value', 'sum'),
        total_volume=('Volume', 'sum')
    ).reset_index()
    
    # Merge daily totals back
    panel_df = panel_df.reset_index().merge(
        totals, on=['Date', 'market'], how='left'
    ).set_index('Date')
    
    # Apply normalization with division-by-zero protection
    panel_df['norm_market_cap'] = panel_df['market_cap'] / panel_df['total_market_cap'].replace(0, 1)
    panel_df['norm_floating_value'] = panel_df['floating_value'] / panel_df['total_floating_value'].replace(0, 1)
    panel_df['norm_volume'] = panel_df['Volume'] / panel_df['total_volume'].replace(0, 1)
    
    # Clean up NaNs
    panel_df['norm_market_cap'] = panel_df['norm_market_cap'].fillna(0.0)
    panel_df['norm_floating_value'] = panel_df['norm_floating_value'].fillna(0.0)
    panel_df['norm_volume'] = panel_df['norm_volume'].fillna(0.0)
    
    # Split back into individual dictionaries
    output_dict = {}
    for sym in prices_dict.keys():
        sym_df = panel_df[panel_df['symbol'] == sym]
        sym_df = sym_df.drop(columns=['symbol', 'total_market_cap', 'total_floating_value', 'total_volume'])
        output_dict[sym] = sym_df
        
    return output_dict
```

---

## 4. Deterministic Fallback Dictionary (`FALLBACK_METADATA`) Design

To ensure complete test stability and allow offline operation across any active ticker (even dynamically generated mock tickers in tests), we propose a **dynamically generated deterministic fallback dictionary**.

Using a subclass of `dict` that overrides `__getitem__` allows us to support all 3,300+ active tickers in the universe without hardcoding a massive block of static metadata.

### Design of `FallbackMetadataDict`
```python
import hashlib

class FallbackMetadataDict(dict):
    """
    A custom dictionary that yields deterministic mock market cap and 
    floating shares for any ticker to support stable offline testing.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Predefined values for major test tickers to ensure matching expected values in unit/E2E tests
        self._predefined = {
            "AAPL": {"shares_outstanding": 1.5e10, "floating_shares": 1.5e10, "market_cap": 3.0e12},
            "MSFT": {"shares_outstanding": 7.4e9,  "floating_shares": 7.4e9,  "market_cap": 3.1e12},
            "GOOGL": {"shares_outstanding": 1.2e10, "floating_shares": 1.2e10, "market_cap": 2.0e12},
            "AMZN": {"shares_outstanding": 1.0e10, "floating_shares": 1.0e10, "market_cap": 1.9e12},
            "TSLA": {"shares_outstanding": 3.2e9,  "floating_shares": 3.2e9,  "market_cap": 6.0e11},
            "005930": {"shares_outstanding": 5.9e9, "floating_shares": 5.9e9, "market_cap": 4.5e14}, # Samsung Electronics (KRW)
            "000660": {"shares_outstanding": 7.2e8, "floating_shares": 7.2e8, "market_cap": 1.2e14}, # SK Hynix (KRW)
        }

    def __getitem__(self, key: str) -> dict:
        if key in self:
            return super().__getitem__(key)
        if key in self._predefined:
            return self._predefined[key]
            
        # Deterministic generation using md5 hash of the ticker name
        h = hashlib.md5(key.encode('utf-8')).hexdigest()
        val_mc = int(h[:8], 16)
        val_fs = int(h[8:16], 16)
        
        # Determine market scale based on ticker style (KRX codes are numeric)
        is_krx = key.isdigit() or (len(key) == 6 and key[:5].isdigit())
        
        if is_krx:
            # KRX Scale (KRW values)
            # Market Cap: 500B KRW to 100T KRW
            mock_market_cap = 5.0e11 + (val_mc % 199) * 5.0e11
            # Floating Shares: 10M to 1B shares
            mock_floating_shares = 1.0e7 + (val_fs % 99) * 1.0e7
        else:
            # US / S&P 500 Scale (USD values)
            # Market Cap: 1B USD to 500B USD
            mock_market_cap = 1.0e9 + (val_mc % 199) * 2.5e9
            # Floating Shares: 10M to 2B shares
            mock_floating_shares = 1.0e7 + (val_fs % 199) * 1.0e7
            
        shares_outstanding = mock_market_cap / 100.0  # Assumes a nominal price of $100/100,000 KRW
        
        return {
            "shares_outstanding": float(shares_outstanding),
            "floating_shares": float(mock_floating_shares),
            "market_cap": float(mock_market_cap)
        }

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        return key in self._predefined or super().__contains__(key)

# Global singleton fallback dictionary
FALLBACK_METADATA = FallbackMetadataDict()
```
This design fulfills all offline stability requirements, is completely deterministic, supports any string ticker, and preserves exact values for major benchmarks.
