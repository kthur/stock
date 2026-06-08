# Global Macro Tab Integration Analysis & Recommendation

This report provides the analysis and architectural blueprint for integrating a new "Global Macro" tab into the existing Dash-based trading system dashboard.

---

## 1. Existing Dashboard Architecture

### A. Run Script (`run_dashboard.py`)
The run script acts as the entry point for the dashboard and the overall system:
1. It initializes an instance of `StockTradingSystem` with an initial cash value of $1,000,000.
2. It executes a trading day simulation for a ticker (e.g., "AAPL") asynchronously using `asyncio.run(system.simulate_trading_day("AAPL"))`.
3. It starts the dashboard using `system.start_dashboard()`.

### B. Dashboard Module (`src/web/dashboard.py`)
The dashboard is built on **Plotly Dash** and structured as follows:
- **Dash App Setup**: Creates a global instance of `dash.Dash` (`app`) and exposes the underlying Flask server via `app.server` (needed for deployment and E2E testing).
- **Layout Definition**: Assigns `app.layout` to a top-level `html.Div` containing:
  - Header: `html.H1("Trading System Dashboard")`
  - Tab Controller: `dcc.Tabs(id="tabs-example", children=[...])`
- **Tab Management**:
  - The tabs are statically defined as child components of `dcc.Tabs`.
  - Currently, there are 3 tabs:
    1. **Strategy Performance** (`id='performance-tab'`): Contains `dcc.Graph(id='performance-comparison-chart')`.
    2. **Real-time P&L** (`id='pnl-tab'`): Contains `dash_table.DataTable(id='pnl-status-table')`.
    3. **Backtest Viewer** (`id='backtest-tab'`): Contains symbol selection dropdown (`dcc.Dropdown(id='backtest-symbol-dropdown')`), performance chart (`dcc.Graph(id='backtest-curve-chart')`), and optimized parameter cache viewer (`html.Div(id='optimized-cache-viewer')`).
- **Callbacks Implementation Pattern**:
  - The dashboard uses a **stateless callback helper** pattern.
  - Rather than registering `@app.callback` decorators directly in the file, it defines stateless, functional helper functions (`update_backtest_chart`, `update_positions_table`, `update_performance_comparison`).
  - This design decouples UI computations from the Dash runtime, permitting unit tests to verify the UI logic by calling helper functions directly without running a live server.

---

## 2. 'Global Macro' Tab Integration

To integrate the "Global Macro" tab, we recommend adding a 4th `dcc.Tab` element inside the children array of the main `dcc.Tabs` component.

### Proposed Layout Elements
Within the `'Global Macro'` tab (`id='global-macro-tab'`), we need the following Dash components:
1. **Header**: `html.H2("Global Macro Monitoring & Sentiment")`
2. **Heatmap Section**:
   - Section Title: `html.H3("Macro Asset Cross-Correlation Matrix")`
   - Controls:
     - `dcc.Dropdown(id='macro-assets-dropdown', multi=True)`: Allows selection of macro assets (Default: `['^GSPC', '^KS11', 'TLT', 'UUP', 'GLD', 'USO', '^VIX']`).
     - `dcc.Dropdown(id='macro-correlation-timeframe', options=[...], value='3mo')`: Allows selection of rolling window period (`1mo`, `3mo`, `6mo`, `1y`).
   - Visualization: `dcc.Graph(id='macro-correlation-heatmap')` to display the interactive Pearson correlation matrix.
3. **Outperformers Section**:
   - Column layout container: `html.Div` with CSS grid/flex layout to place US and KR tables side-by-side.
   - **US Top 10 Outperformers Card**:
     - Title: `html.H3("US Market Top 10 (S&P 500)")`
     - Table: `dash_table.DataTable(id='us-outperformers-table')` containing columns: Rank, Symbol, Name, Price, and Period Return (%).
   - **KR Top 10 Outperformers Card**:
     - Title: `html.H3("KR Market Top 10 (KRX)")`
     - Table: `dash_table.DataTable(id='kr-outperformers-table')` containing columns: Rank, Symbol, Name, Price, and Period Return (%).
4. **Trigger Component**:
   - `dcc.Interval(id='macro-update-interval', interval=3600000)`: 1-hour auto-refresh interval for updating macroeconomic performance stats.

---

## 3. Required Callbacks Design

To align with the existing code style, we must implement two new stateless helper functions that return the appropriate component payloads, alongside their Dash decorators.

### A. Heatmap Callback Helper
Expose a stateless helper function:
```python
def update_macro_correlation_heatmap(selected_symbols: List[str], timeframe: str) -> Dict[str, Any]:
    """
    Computes daily percentage returns for selected symbols over a timeframe,
    calculates the Pearson correlation matrix, and returns a Plotly Heatmap figure dict.
    """
```
#### Signature & Inputs
- **Inputs**:
  - `selected_symbols` (List[str] or None): List of tickers. If `None` or empty, returns an empty figure dict.
  - `timeframe` (str): History period (e.g. `'3mo'`).
- **Outputs**:
  - `fig` (Dict[str, Any]): Plotly figure structure containing `data` and `layout`.

#### Core Implementation Logic
1. **Fallback checks**: If `selected_symbols` is empty, return a blank plot dictionary gracefully: `{'data': [], 'layout': {'title': 'No data (Select assets)'}}`.
2. **Data Fetching**: Use `yfinance` to download historical data for `selected_symbols` for the requested `timeframe` (adjusted close prices).
3. **Correlation Calculation**:
   - Extract Close prices into a DataFrame.
   - Calculate returns: `returns_df = df.pct_change().dropna()`
   - Compute Pearson matrix: `corr_df = returns_df.corr()`
4. **Figure Construction**:
   ```python
   return {
       'data': [{
           'type': 'heatmap',
           'z': corr_df.values.tolist(),
           'x': list(corr_df.columns),
           'y': list(corr_df.index),
           'colorscale': 'RdBu',
           'zmin': -1.0,
           'zmax': 1.0
       }],
       'layout': {
           'title': f"Macro Cross-Correlation Heatmap ({timeframe})",
           'xaxis': {'title': 'Asset'},
           'yaxis': {'title': 'Asset'}
       }
   }
   ```

### B. Outperformers Table Callback Helper
Expose a stateless helper function:
```python
def update_outperformers_table(country: str, timeframe: str = '1mo', limit: int = 10) -> List[Dict[str, Any]]:
    """
    Scans a stock universe for the given country, calculates returns over the timeframe,
    and returns the top N outperformers formatted for Dash DataTable.
    """
```
#### Signature & Inputs
- **Inputs**:
  - `country` (str): `'US'` or `'KR'`.
  - `timeframe` (str): Period over which to measure returns (default `'1mo'`).
  - `limit` (int): Number of rows to return (default 10).
- **Outputs**:
  - `data_rows` (List[Dict[str, Any]]): Rows containing keys: `'rank'`, `'symbol'`, `'name'`, `'price'`, `'return'`.

#### Core Implementation Logic
1. **Determine Stock Universe**:
   - For `country == 'KR'`, extract the top market cap stocks using `FinanceDataReader.StockListing('KRX')` or a default major KOSPI index list.
   - For `country == 'US'`, define or fetch a subset of top S&P 500 stocks (e.g. `['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA', 'JPM', 'UNH', 'LLY']`).
2. **Performance Calculation**:
   - Fetch historical data for all symbols in the universe over the timeframe.
   - For each symbol, compute return: `ret = (last_close / first_close) - 1`.
3. **Ranking & Formatting**:
   - Sort symbols by return in descending order.
   - Take the top `limit` symbols.
   - Format:
     ```python
     rows = []
     for rank, (symbol, name, price, ret) in enumerate(top_picks, 1):
         rows.append({
             'rank': rank,
             'symbol': symbol,
             'name': name,
             'price': round(price, 2),
             'return': round(ret * 100, 2)
         })
     return rows
     ```
4. **Boundary Fallback**: If yfinance or FinanceDataReader fails (due to network block/proxy/offline), return an empty list or mock rows indicating "Data Unavailable" gracefully to prevent crashes.

---

## 4. Critical Dependency Issue & Resolutions

### The Problem
During our investigation, we ran the test suite and discovered **26 test failures** with the traceback:
`ModuleNotFoundError: No module named 'dash'`

We cross-referenced `pyproject.toml` and `requirements.txt` and confirmed that **`dash` is completely missing** from both project files, although the source file `src/web/dashboard.py` actively imports it (`import dash`, `from dash import dcc, html, dash_table`).

### Recommendations for Resolution
1. **Update `pyproject.toml`**:
   Add `"dash>=2.11.0"` to the `dependencies` block.
2. **Update `requirements.txt`**:
   Append `dash>=2.11.0` to the file.
3. **Install Environment Dependencies**:
   Once the network context permits, run `pip install dash` or `uv pip install dash` in the development environment.

---

## 5. Integration Verification Plan

After implementation, validation should verify that:
1. `app.layout` string contains `global-macro-tab`, `macro-correlation-heatmap`, `kr-outperformers-table`, and `us-outperformers-table`.
2. Helper functions `update_macro_correlation_heatmap` and `update_outperformers_table` can be successfully imported from `src.web.dashboard`.
3. Calling helpers with `None` inputs or empty list returns a dictionary with key `'data'` (for heatmap) or an empty list (for tables) without throwing exceptions.
4. Consecutive calls with different symbols yield distinct and independent outputs (verifying statelessness).
5. All 26 test suite failures are resolved once the `dash` dependency is installed.
