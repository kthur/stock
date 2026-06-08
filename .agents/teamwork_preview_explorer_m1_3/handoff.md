# Handoff Report - R5 Dash Web UI Dashboard Investigation

This report presents the findings of the investigation into the implementation status of requirement R5 (Dash Web UI dashboard in `src/web/dashboard.py` and `run_dashboard.py`), and the verification of related tests under `tests/phase4/e2e/test_e2e.py`.

---

## 1. Observation

### A. Current File Structure and Environment
- The project is configured as a Python application utilizing a local virtual environment located at `d:\Finance\code\stock\trading_system\.venv\`.
- The entry points and files related to the web dashboard are located at:
  - `d:\Finance\code\stock\trading_system\src\web\dashboard.py` (FastAPI-based dashboard module)
  - `d:\Finance\code\stock\trading_system\run_dashboard.py` (FastAPI runner)
  - `d:\Finance\code\stock\trading_system\tests\phase4\e2e\test_e2e.py` (E2E testing suite containing Dash layout and callback assertions)

### B. Current Web Dashboard Implementation (`src/web/dashboard.py`)
- The class `WebDashboard` is defined starting at line 31 of `src/web/dashboard.py`:
  ```python
  class WebDashboard:
      """FastAPI 기반 실시간 거래 시스템 대시보드"""
  ```
- The framework used is **FastAPI**, not Plotly Dash. It defines endpoints like:
  - Line 64: `self.app = FastAPI(title="Stock Trading System Dashboard")`
  - Line 81: `@self.app.get("/", response_class=HTMLResponse)`
  - Line 89: `@self.app.get("/ws")` (WebSocket connection endpoint)
  - Line 600: `@self.app.post("/api/backtest")` (Backtest endpoint)
- The user interface is returned as a single raw HTML string inside the `get_dashboard_html(self)` method starting at line 1127.
- UI Tabs in the current FastAPI HTML representation are defined in JavaScript and HTML navigation blocks:
  - `"tabbtn-dashboard"` (Dashboard / 대시보드)
  - `"tabbtn-screener"` (Screener / 시장 스크리너)
  - `"tabbtn-backtest"` (Backtest / 백테스트)
  - `"tabbtn-risk"` (Risk Settings / 리스크 설정)
  - `"tabbtn-ai"` (AI Investment Advisor / AI 투자 의견)
  - `"tabbtn-vr"` (BCI WebXR VR / BCI VR 룸)
- The file **does not export** any module-level Dash instance called `app`, nor does it define the helper functions or structures expected by the test suite.

### C. Test Suite Contract (`tests/phase4/e2e/test_e2e.py`)
- The Dash E2E tests are defined under `tests/phase4/e2e/test_e2e.py` starting at line 354:
  - **`test_r5_dashboard_server_instance`** (line 355):
    ```python
    def test_r5_dashboard_server_instance():
        """R5: dashboard exposes app.server Flask instance."""
        from src.web.dashboard import app
        import flask
        assert hasattr(app, "server")
        assert isinstance(app.server, flask.Flask)
    ```
  - **`test_r5_dashboard_layout_tabs`** (line 362):
    ```python
    def test_r5_dashboard_layout_tabs():
        """R5: dashboard layout contains the 3 required tabs."""
        from src.web.dashboard import app
        layout = app.layout
        layout_str = str(layout)
        assert "performance-tab" in layout_str or "Strategy Performance" in layout_str
        assert "pnl-tab" in layout_str or "Real-time" in layout_str
        assert "backtest-tab" in layout_str or "Backtest" in layout_str
    ```
  - **`test_r5_dashboard_performance_tab_components`** (line 372): Asserts `"performance-comparison-chart"` and `"Graph"` exist in layout.
  - **`test_r5_dashboard_pnl_tab_components`** (line 380): Asserts `"DataTable"` or `"pnl-status-table"` exist in layout.
  - **`test_r5_dashboard_backtest_viewer_components`** (line 386): Asserts `"Dropdown"`, `"backtest-symbol-dropdown"`, and `"backtest-curve-chart"` exist in layout.
  - **`test_r5_dashboard_callback_missing_inputs`** (line 632):
    ```python
    def test_r5_dashboard_callback_missing_inputs():
        """R5 boundary: update callbacks handle None dropdown inputs gracefully."""
        from src.web.dashboard import update_backtest_chart
        fig = update_backtest_chart(None, None)
    ```
  - **`test_r5_dashboard_empty_positions_table`** (line 640): Imports and tests `update_positions_table` from `src.web.dashboard`.
  - **`test_r5_dashboard_missing_performance_data`** (line 647): Imports and tests `update_performance_comparison` from `src.web.dashboard`.
  - **`test_r5_dashboard_server_port_collision`** (line 654): Imports and tests `DashboardServer` from `src.web.dashboard`.
  - **`test_r5_dashboard_concurrent_connections`** (line 660): Imports and tests `update_backtest_chart` from `src.web.dashboard`.
  - **`test_r1_r5_combination`** (line 753): Imports `app` from `src.web.dashboard` and checks for `"optimized-cache-viewer"` in layout.

### D. Test Execution and Failure Output
- Executed the test command:
  ```powershell
  .venv\Scripts\pytest tests/phase4/e2e/test_e2e.py -k R5
  ```
- Output log from task `e7827a58-0dcf-4a8c-a731-74363d48b487/task-38`:
  ```
  tests\phase4\e2e\test_e2e.py FFFFFFFFFFF                                 [100%]
  ================================== FAILURES ===================================
  ______________________ test_r5_dashboard_server_instance ______________________
  ...
  >       from src.web.dashboard import app
  E       ImportError: cannot import name 'app' from 'src.web.dashboard' (D:\Finance\code\stock\trading_system\src\web\dashboard.py)
  ```
- All 11 tests prefixed with or referencing `R5` failed with a similar `ImportError` on either `app`, `update_backtest_chart`, `update_positions_table`, `update_performance_comparison`, or `DashboardServer`.

---

## 2. Logic Chain

1. **Framework Mismatch**:
   - *Observation A & B*: The current dashboard implementation (`src/web/dashboard.py`) runs a FastAPI application.
   - *Observation C*: The E2E tests in `tests/phase4/e2e/test_e2e.py` specifically import a Dash app instance (`app`), its Dash layout (`app.layout`), and callbacks (`update_backtest_chart`, etc.).
   - *Reasoning*: Because FastAPI has a completely different programming model and does not expose a Dash instance, any test importing `app` or layout components will fail.

2. **Missing Module-Level Names**:
   - *Observation B*: `src/web/dashboard.py` defines a single `WebDashboard` class which wraps a FastAPI instance inside `self.app`.
   - *Observation D*: The tests fail on import statements (e.g. `ImportError: cannot import name 'app'`).
   - *Reasoning*: The module-level scope of `src/web/dashboard.py` lacks the expected Dash instance (`app`), callback functions (`update_backtest_chart`, `update_positions_table`, `update_performance_comparison`), and the server configuration wrapper (`DashboardServer`).

3. **Tab and Feature Discrepancies**:
   - *Observation B*: The current FastAPI-based dashboard lacks the specific tab structures and components expected by the tests.
   - *Observation C*: The tests require specific Dash component IDs: `"performance-tab"`, `"pnl-tab"`, `"backtest-tab"`, `"performance-comparison-chart"`, `"pnl-status-table"`, `"backtest-symbol-dropdown"`, `"backtest-curve-chart"`, and `"optimized-cache-viewer"`.
   - *Reasoning*: Even if the FastAPI app were bypassed or wrapped, the HTML/JS rendered on the page does not declare Dash widgets or elements mapping to these IDs, which means E2E element lookups and callbacks would fail.

---

## 3. Caveats

- **Read-Only Scope**: In compliance with my Explorer role constraint, I have only performed filesystem analysis and test execution. No code was altered to fix the imports or implement the missing components.
- **FastAPI Core Execution**: The main trading system runner (`trading_system.py`) expects the dashboard to start via `self.dashboard.run()`. If we completely replace FastAPI with Dash, we need to ensure that the runner continues to function properly, or that the FastAPI server hosts the Dash application internally (e.g., mounting Dash inside FastAPI using WSGIMiddleware, or using Dash directly and exposing `app.server` which is a Flask app).
- **Network Restrictions**: Since the workspace is locked to `CODE_ONLY` mode, no external packages can be downloaded. Plotly/Dash and Dash Bootstrap Components must already be installed in the virtual environment or added to `pyproject.toml` / `requirements.txt` to be resolved during final build.

---

## 4. Conclusion

The implementation of R5 (Dash Web UI dashboard) in `src/web/dashboard.py` is **completely missing/unimplemented** relative to the required testing contract. While a functioning FastAPI web dashboard is present, it does not conform to the Dash-based structure expected by the 11 E2E tests under `tests/phase4/e2e/test_e2e.py`. 

To pass the tests, the dashboard must be rewritten (or wrapped) as a Plotly Dash application exporting `app`, `update_backtest_chart`, `update_positions_table`, `update_performance_comparison`, and `DashboardServer` at the module level, and incorporating the 3 specified tabs and respective component IDs.

---

## 5. Verification Method

### Test Execution Command
Run the following command from the `d:\Finance\code\stock\trading_system` directory inside the local environment:
```powershell
.venv\Scripts\pytest tests/phase4/e2e/test_e2e.py -k R5
```

### Invalidation Conditions
- The verification fails if the output does not report `11 failed` due to `ImportError`.
- If the tests pass, it means the dashboard has been successfully implemented or updated to export the required Dash objects and functions.
