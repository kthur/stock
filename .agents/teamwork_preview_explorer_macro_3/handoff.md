# Handoff Report: Global Macro Tab Integration Investigation

This handoff report summarizes the structure of the Dash app layout and recommends the exact integration plan and callback signatures for adding the "Global Macro" tab.

---

## 1. Observation

### A. Dashboard Files & Layout Structure
- **File**: `d:\Finance\code\stock\trading_system\src\web\dashboard.py`
  - Defines the Dash app layout at lines 18-46:
    ```python
    app.layout = html.Div([
        html.H1("Trading System Dashboard"),
        dcc.Tabs(id="tabs-example", children=[
            dcc.Tab(label='Strategy Performance', id='performance-tab', children=[
                html.Div([
                    dcc.Graph(id='performance-comparison-chart')
                ])
            ]),
            ...
        ])
    ])
    ```
  - Layout features three static tabs inside `dcc.Tabs(id="tabs-example")`: `performance-tab`, `pnl-tab`, and `backtest-tab`.
  - Exposes stateless callback helpers at lines 48-150:
    - `update_backtest_chart(symbol: Optional[str], strategy: Optional[str]) -> Dict[str, Any]` (Lines 50-78)
    - `update_positions_table(positions: List[Any]) -> List[Dict[str, Any]]` (Lines 80-113)
    - `update_performance_comparison(performance_data: Dict[str, Any]) -> Dict[str, Any]` (Lines 115-149)
  - Defines `WebDashboard` class (Lines 157-178) containing the `run` method to start the Dash server in a daemon background thread (Line 175).

- **File**: `d:\Finance\code\stock\trading_system\run_dashboard.py`
  - Contains the system execution loop:
    ```python
    if __name__ == "__main__":
        system = StockTradingSystem(initial_cash=1000000)
        asyncio.run(system.simulate_trading_day("AAPL"))
        system.start_dashboard()
    ```

### B. Existing Scanners & Tickers
- **File**: `d:\Finance\code\stock\trading_system\src\analysis\market_scanner.py`
  - Defines `MarketScanner` which fetches Korean market listing from KRX (KOSPI/KOSDAQ) via `FinanceDataReader.StockListing('KRX')` (Line 22) and ranks them using historical returns/expected returns.

### C. Test Run Failures and Missing Dependencies
- Running `pytest tests/phase4/e2e/test_e2e.py` failed with 26 errors.
- **Traceback quote from `task-58.log`**:
  ```
  _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
  src\web\dashboard.py:7: in <module>
      import dash
  E   ModuleNotFoundError: No module named 'dash'
  ```
- **Dependencies Inspection**:
  - `d:\Finance\code\stock\trading_system\pyproject.toml` (lines 19-31) has no entry for `dash`.
  - `d:\Finance\code\stock\trading_system\requirements.txt` has no entry for `dash`.
  - Checking the active python environment (`python -m pip list`) confirms `dash` is not installed.

---

## 2. Logic Chain

1. **App Structure & Tab Management**: Since `app.layout` statically declares tabs as children of `dcc.Tabs(id="tabs-example")` and tests assert their presence by verifying the layout string representation (e.g. `test_r5_dashboard_layout_tabs` in `test_e2e.py`), adding the new "Global Macro" tab requires inserting a new `dcc.Tab` entry directly into this static child list.
2. **Tab Integration & UI Elements**: To support cross-correlation and outperformers tables, the new tab needs a container (`html.Div`), a graph component for the heatmap (`dcc.Graph`), and two datatable components (`dash_table.DataTable`) for the US and KR Top 10 lists.
3. **Callback Design**:
   - The test suite tests the dashboard callbacks by importing the module-level helper functions and passing `None` or mock inputs to verify robust error-handling (e.g., `update_backtest_chart(None, None)` returning `{'data': []}`).
   - Therefore, the Global Macro callbacks must also be implemented as standalone, stateless helper functions (e.g., `update_macro_correlation_heatmap` and `update_outperformers_table`) that return structured dictionary/list payloads and handle boundary conditions (like `None` or empty lists) gracefully.
4. **Missing Dependency Blocker**: The 26 test suite failures are directly caused by `ModuleNotFoundError: No module named 'dash'`. Because `dash` is used in `src/web/dashboard.py` but is not in `pyproject.toml` or `requirements.txt`, we conclude that the project has a packaging/dependency definition gap that must be resolved before verification can pass.

---

## 3. Caveats

- **Network Restrictions**: In CODE_ONLY network mode, external API calls via `yfinance` or `FinanceDataReader` will fail or timeout. The implementation of callback helpers must have mock fallbacks (similar to the existing dashboard code which returns hardcoded mock arrays for AAPL/MSFT when yfinance/market data is missing).
- **Korean Ticker Names**: Fetching Korean names requires parsing KRX listing data; a dictionary lookup fallback should be provided if `FinanceDataReader` calls fail.

---

## 4. Conclusion

The "Global Macro" tab should be integrated by:
1. Adding a new `dcc.Tab(label='Global Macro', id='global-macro-tab', children=[...])` component containing a `dcc.Graph(id='macro-correlation-heatmap')` and two `dash_table.DataTable` components for `kr-outperformers-table` and `us-outperformers-table`.
2. Exposing two new stateless module-level helper functions in `src/web/dashboard.py`:
   - `update_macro_correlation_heatmap(selected_symbols: List[str], timeframe: str) -> Dict[str, Any]`
   - `update_outperformers_table(country: str, timeframe: str = '1mo', limit: int = 10) -> List[Dict[str, Any]]`
3. Ensuring these helper functions handle missing or `None` inputs gracefully by returning default empty graphs/tables without raising exceptions.
4. Adding `dash>=2.11.0` to `pyproject.toml` and `requirements.txt` to fix the blocker.

---

## 5. Verification Method

To verify the integration:
1. **Dependency Installation**: Install the missing dependency `dash` (e.g. `pip install dash`).
2. **Layout Verification**: Verify that the app layout loads properly by checking:
   ```python
   from src.web.dashboard import app
   layout_str = str(app.layout)
   assert "global-macro-tab" in layout_str
   assert "macro-correlation-heatmap" in layout_str
   assert "kr-outperformers-table" in layout_str
   assert "us-outperformers-table" in layout_str
   ```
3. **Callback Unit Verification**: Unit-test the helper functions to verify statelessness and boundary handling:
   ```python
   from src.web.dashboard import update_macro_correlation_heatmap, update_outperformers_table
   
   # Heatmap None/Empty test
   fig = update_macro_correlation_heatmap([], '3mo')
   assert isinstance(fig, dict) and 'data' in fig
   
   # Heatmap statelessness test
   fig_a = update_macro_correlation_heatmap(['GLD', 'USO'], '3mo')
   fig_b = update_macro_correlation_heatmap(['SPY', 'TLT'], '3mo')
   assert fig_a != fig_b
   
   # Outperformers empty/limit test
   rows_kr = update_outperformers_table('KR', limit=10)
   rows_us = update_outperformers_table('US', limit=10)
   assert len(rows_kr) <= 10
   assert len(rows_us) <= 10
   ```
4. **Run Pytest Suite**: Execute `pytest tests/phase4/e2e/test_e2e.py` to confirm that all 26 dashboard and system tests pass cleanly.
