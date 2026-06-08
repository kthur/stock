# Stock Screener and Macro Correlation Analysis Report

## Executive Summary
This report analyzes the existing `StockScreener` structure within the `trading_system` codebase, investigates ticker list management for the S&P 500 and KOSPI 200 universes, defines the mathematical methodology for calculating stock price correlation with the USDKRW=X exchange rate, and recommends implementation details for the proposed `StockScreener.screen_global_outperformers()` method. 

---

## 1. StockScreener Class Structure (`screener.py`)
The class `StockScreener` is defined in `trading_system/src/analysis/screener.py`. It is designed to filter a list of stocks (a "universe") based on technical and volume indicators.

### Properties and Initialization
- **`__init__` Parameters**:
  - `min_volume` (float, default: `100000.0`): The minimum 1-month average trading volume filter.
  - `min_rsi` (float, default: `30.0`): The lower bound for the Relative Strength Index (RSI).
  - `max_rsi` (float, default: `70.0`): The upper bound for the RSI.
  - `max_distance_from_high` (float, default: `0.20`): The maximum allowed percentage decline from the 52-week high.
  - `config_path` (Optional[str], default: `None`): An optional JSON configuration file path to override default thresholds.
- **Fields**:
  - `self.min_volume`, `self.min_rsi`, `self.max_rsi`, `self.max_distance_from_high`.

### Private Helper Methods
1. **`_get_average_volume(self, symbol: str) -> float`**
   - Downloads 1 month of historical data using `yfinance`.
   - Returns the mean of the `Volume` column.
   - Falls back to `ticker.info.get("volume")` or a default value of `2000000.0` if history is unavailable.
2. **`_calc_rsi_list(self, closes: List[float], window: int = 14) -> float`**
   - Helper function that computes the RSI value for a list of close prices using Wilder's smoothed moving average.
3. **`_calculate_rsi(self, symbol: str) -> float`**
   - Downloads 1 month of history for the symbol.
   - Extracts the close prices and calls `_calc_rsi_list`. Returns `50.0` if data is insufficient (<15 closes).
4. **`_get_52week_prices(self, symbol: str) -> Dict[str, float]`**
   - Downloads 1 year of history for the symbol.
   - Returns a dictionary with `"current"` (last close) and `"52week_high"` (max high).
   - Falls back to `ticker.info` properties (`regularMarketPrice` and `fiftyTwoWeekHigh`) or mocks if missing.

### Public Screening Method
- **`screen(self, universe: List[str]) -> List[str]`**
   - Deduplicates the input list of tickers while maintaining order.
   - For each unique symbol, applies three sequential filters:
     1. **Volume**: Average volume $\ge$ `self.min_volume`.
     2. **RSI**: `self.min_rsi` $\le$ RSI $\le$ `self.max_rsi`.
     3. **52-Week High Distance**: $\frac{52\text{-week high} - \text{current price}}{52\text{-week high}} \le$ `self.max_distance_from_high`.
   - Returns a list of symbols that passed all filters.

---

## 2. S&P 500 and KOSPI 200 Ticker List Management

### Current State of the Repository
Currently, there are **no** pre-defined lists of S&P 500 or KOSPI 200 constituents stored in the repository.
- `trading_system/src/utils/stock_list.py` contains a utility `KoreanStockList` that dynamically fetches all KRX (KOSPI & KOSDAQ) stock listings using `FinanceDataReader.StockListing('KRX')` and filters them by `'KOSPI'` or `'KOSDAQ'` to append `.KS` or `.KQ` suffixes. If fetching fails, it falls back to a hardcoded dictionary of ~30 major Korean stocks.
- There is no logic for retrieving S&P 500 tickers or subsetting KOSPI 200 constituents.

### Retrieval & Storage Recommendations

#### Option A: Offline/Local Storage (Recommended)
Store the lists of S&P 500 and KOSPI 200 tickers in static files inside the repository (e.g., `trading_system/data/sp500_tickers.json` and `trading_system/data/kospi200_tickers.json`).
* **Why**: Constituents change infrequently (quarterly/semi-annually). Local caching avoids the latency, rate-limiting, and network failures associated with scraping external sites during screening execution.
* **Maintenance**: Provide a utility/maintenance script (e.g., `tools/update_constituents.py`) that can be run on demand to fetch and refresh the local JSON files.

#### Option B: Dynamic Online Retrieval (Fallback)
If dynamic retrieval is required:
1. **S&P 500**: Scrape Wikipedia's list of S&P 500 companies using pandas:
   ```python
   import pandas as pd
   
   def fetch_sp500_tickers() -> list:
       url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
       table = pd.read_html(url)[0]
       # Convert tickers like BRK.B to BRK-B for yfinance compatibility
       tickers = table['Symbol'].str.replace('.', '-', regex=False).tolist()
       return tickers
   ```
2. **KOSPI 200**: Since FinanceDataReader does not provide a direct KOSPI 200-specific constituent list, we can query Naver Finance page-by-page or scrape it:
   ```python
   import pandas as pd
   
   def fetch_kospi200_tickers() -> list:
       # Fetch KOSPI 200 from Naver Finance (10 pages, 20 items per page)
       tickers = []
       for page in range(1, 11):
           url = f"https://finance.naver.com/sise/entry_sub_page.naver?sosok=0&page={page}"
           try:
               tables = pd.read_html(url, encoding='cp949')
               if tables:
                   df = tables[0].dropna()
                   for _, row in df.iterrows():
                       # Extract the 6-digit stock code from the link/name
                       # Typically, Naver lists name, which points to code
                       # We can also fetch the entire KRX listing from fdr and map names
                       pass
           except Exception:
               break
       return tickers
   ```
   *Alternative*: Load the full KRX listing using `FinanceDataReader.StockListing('KRX')`, sort by market cap (`Marcap`), and take the top 200 KOSPI-market stocks. While this is an approximation of KOSPI 200, it is robust and does not require complex HTML scraping.

---

## 3. Correlation with USDKRW=X Exchange Rate

### Mathematical Methodology
Asset prices are typically non-stationary (exhibit trends). Running correlation on raw prices leads to **spurious correlation**, which is mathematically invalid for risk or statistical analysis. The correct methodology is to compute correlation using **daily percentage/logarithmic returns**.

1. **Alignment**: Since the US and Korean markets operate in different time zones and have different trading holidays, the price histories will have missing data points when joined. We must merge the datasets using an outer or inner join, followed by forward-filling (`ffill()`) and backward-filling (`bfill()`) to align dates.
2. **Returns Calculation**: Compute daily returns:
   $$r_t = \frac{p_t - p_{t-1}}{p_{t-1}}$$
3. **Pearson Correlation Coefficient**: Compute the Pearson correlation:
   $$\rho_{S, E} = \frac{\text{Cov}(R_S, R_E)}{\sigma_S \sigma_E}$$
   where $R_S$ is the stock return series and $R_E$ is the `USDKRW=X` return series.

### Python Code Implementation
```python
import pandas as pd
import yfinance as yf

def calculate_exchange_rate_correlation(
    stock_ticker: str, 
    exchange_ticker: str = "USDKRW=X", 
    period: str = "1y"
) -> float:
    """
    Calculates the Pearson correlation coefficient between daily returns of
    a stock and the USDKRW=X exchange rate.
    """
    tickers = [stock_ticker, exchange_ticker]
    try:
        # Download historical data
        data = yf.download(tickers, period=period, progress=False)['Close']
        
        # Check if both columns exist and have enough data
        if stock_ticker not in data.columns or exchange_ticker not in data.columns:
            return 0.0
        
        # Align time series by forward-filling missing values (handling timezone / holiday mismatches)
        aligned_data = data[[stock_ticker, exchange_ticker]].ffill().bfill()
        
        # Compute daily percentage returns
        returns = aligned_data.pct_change().dropna()
        
        if len(returns) < 10:
            return 0.0
            
        # Calculate Pearson correlation
        correlation = returns[stock_ticker].corr(returns[exchange_ticker])
        return float(correlation) if not pd.isna(correlation) else 0.0
    except Exception as e:
        # Log error and return 0.0 fallback
        return 0.0
```

---

## 4. Recommendations for `screen_global_outperformers()`

### Method Contract and Output Structure
According to the interface contracts defined in `.agents/orchestrator/SCOPE.md`, the method should be added to `StockScreener` and have the following signature and return format:

```python
def screen_global_outperformers(self) -> Dict[str, List[Dict[str, Any]]]:
    """
    Screens S&P 500 and KOSPI 200 ticker universes.
    Returns the top 10 US and top 10 KR stocks by expected excess return.
    """
```

#### Output Structure:
```python
{
    "US": [
        {
            "ticker": "AAPL", 
            "expected_excess_return": 0.045, 
            "correlation_to_exchange_rate": -0.23
        },
        ... # exactly 10 items
    ],
    "KR": [
        {
            "ticker": "005930.KS", 
            "expected_excess_return": 0.032, 
            "correlation_to_exchange_rate": -0.45
        },
        ... # exactly 10 items
    ]
}
```

### Proposed Step-by-Step Implementation Logic

#### Step 1: Universe Loading
Load the S&P 500 and KOSPI 200 ticker lists. It is highly recommended to read from pre-cached files:
```python
import json
import os

def _load_universe_tickers(self, region: str) -> List[str]:
    # Locate data files in the trading system data folder
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    file_path = os.path.join(base_dir, "data", f"{region.lower()}_tickers.json")
    
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    # Fallback lists if files are missing
    if region == "US":
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "V", "JPM", "UNH"]
    else:
        return ["005930.KS", "000660.KS", "005380.KS", "000270.KS", "005490.KS", "035420.KS", "035720.KS"]
```

#### Step 2: Bulk Data Downloading
To prevent IP rate limits from `yfinance` when checking 700+ tickers individually, download tickers in batches:
```python
import yfinance as yf

# Example bulk download for USDKRW=X and a list of tickers
all_tickers = tickers + ["USDKRW=X"]
data = yf.download(all_tickers, period="1y", group_by="ticker", progress=False)
```

#### Step 3: Feature Construction and Excess Return Prediction
For each ticker, extract features and use the `MacroPredictor` model (defined in `trading_system/src/analysis/macro_predictor.py`) to predict the expected excess return over the benchmark.
- **US Benchmark**: S&P 500 Index (`^GSPC`)
- **KR Benchmark**: KOSPI Index (`^KS11`)
- **Expected Excess Return**:
  $$\text{Expected Excess Return} = E[R_{\text{stock}}] - E[R_{\text{benchmark}}]$$
  This is retrieved from the trained `MacroPredictor` model using the stock features.

#### Step 4: Correlation Computation
Calculate the correlation between the stock's returns and the aligned returns of `USDKRW=X` (as described in Section 3).

#### Step 5: Sorting and Selection
Sort the resulting lists for `"US"` and `"KR"` independently in descending order of `expected_excess_return`. Take the top 10 for each region.

#### Step 6: Formatting and Validation
Ensure the return dictionary matches the interface contract and contains exactly 10 tickers per region. Include robust error handling to skip invalid/delisted tickers while ensuring the final list is populated with fallbacks if necessary.
