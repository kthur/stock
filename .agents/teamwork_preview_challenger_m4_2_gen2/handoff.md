# Empirical Stress Test Challenge & Verification Report: Automated Test Suites

**Target Directories**: `tests/` and `trading_system/tests/`  
**Challenger**: Challenger M4_2 (Empirical Challenger)  
**Date**: 2026-07-29  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_challenger_m4_2_gen2`  

---

## Challenge Summary

**Overall Risk Assessment**: **MEDIUM-HIGH** (Structural duplications, environment state leaks, non-isolated module-level side-effects, and missing test discovery paths).

---

## 1. Observation

### Observation 1.1: Double Test Discovery and Wrapper Proxy Duplication (`tests/` vs `trading_system/tests/`)
- **Location**: `tests/*.py` (55 files) vs `trading_system/tests/*.py` (53 files)
- **Verbatim Code Example**: `tests/test_adversarial_fundamental.py` line 1:
  ```python
  from trading_system.tests.test_adversarial_fundamental import *
  ```
- **Finding**: 
  - All 55 files in `tests/` are thin 1-line re-export wrappers forwarding imports to `trading_system.tests.<test_module>`.
  - When running `.venv\Scripts\python.exe -m pytest tests/` vs `.venv\Scripts\python.exe -m pytest trading_system/tests/`, running from root directory (`pytest`) causes Pytest to discover both directories simultaneously.
  - Every single test case is collected and executed **twice** (once under `tests.test_foo` and once under `trading_system.tests.test_foo`).

### Observation 1.2: Misplaced Test File Causing Silent Exclusions
- **Location**: `tests/test_macro_indicators_smoke.py`
- **Verbatim Code**:
  ```python
  from trading_system.test_macro_indicators_smoke import *
  ```
- **Finding**:
  - `test_macro_indicators_smoke.py` in `trading_system/` is located directly at `trading_system/test_macro_indicators_smoke.py`, NOT inside `trading_system/tests/`.
  - Running `.venv\Scripts\python.exe -m pytest trading_system/tests/` skips `test_macro_indicators_smoke.py` completely because it resides outside the target subfolder.

### Observation 1.3: Persistent Global Environment Leakage at Module Import Time
- **Locations**:
  - `trading_system/tests/test_e2e_consolidated.py` (lines 25–33)
  - `trading_system/tests/test_post_market_scoring.py` (lines 6–10)
  - `trading_system/tests/test_orchestrator.py` (lines 17–20)
- **Verbatim Code Snippet** (`test_e2e_consolidated.py` lines 25–33):
  ```python
  tmp_db_indicator = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
  tmp_db_prices = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
  TEST_INDICATOR_DB_PATH = tmp_db_indicator.name
  TEST_PRICES_DB_PATH = tmp_db_prices.name
  tmp_db_indicator.close()
  tmp_db_prices.close()

  os.environ["DB_PATH"] = TEST_INDICATOR_DB_PATH
  os.environ["STOCK_PRICE_DB_PATH"] = TEST_PRICES_DB_PATH
  ```
- **Finding**:
  - Temporary files and environment variable mutations (`os.environ["DB_PATH"]`) take place at **module import time** (top level of the test scripts).
  - During Pytest test collection, simply scanning or importing these files permanently alters `os.environ["DB_PATH"]` for the entire Pytest execution process.
  - In `test_post_market_scoring.py`, `setUp()` captures `self.original_env` *after* module-level execution has already mutated `os.environ`. Consequently, `tearDown()` restores the already-polluted environment state.

### Observation 1.4: Temporary Database File Leaks on Disk
- **Locations**: `test_e2e_consolidated.py`, `test_post_market_scoring.py`, `test_orchestrator.py`
- **Finding**:
  - `tempfile.NamedTemporaryFile(delete=False)` creates `.db` files on disk at module top level.
  - No module cleanup (`tearDownModule` or `pytest_unconfigure`) unlinks or deletes these temporary `.db` files after test execution. They leak permanently in `%TEMP%` across test executions.

### Observation 1.5: Source Tree Side Effects During Daemon Tests
- **Location**: `trading_system/tests/test_orchestrator.py` (lines 56–60)
- **Verbatim Code**:
  ```python
  pid_file = Path(run_orchestrator.__file__).parent / "orchestrator.pid"
  ```
- **Finding**:
  - The orchestrator daemon tests write `orchestrator.pid` directly into `trading_system/` (the application source code directory).
  - Writing state files into the source directory violates workspace isolation guidelines and risks leaving dirty state in production source folders if test runs are aborted mid-flight.

---

## 2. Logic Chain

1. **Test Discovery Logic**:
   - Pytest automatically traverses all directories matching test patterns. If `tests/` re-exports everything from `trading_system/tests/`, running `pytest` without path restrictions will run 108 test files instead of 53, executing every single unit, integration, and E2E test twice.
   - Any state modified by the first execution (e.g. database schema creation, mock overrides) will impact the second execution if global objects are not reset between runs.

2. **Environment Variable Mutability Logic**:
   - `TradingConfig` in `src/config.py` evaluates environment variables (`DB_PATH`, `STOCK_PRICE_DB_PATH`) upon initialization.
   - Top-level `os.environ["DB_PATH"] = ...` calls in `test_e2e_consolidated.py` overwrite `DB_PATH` before test classes even instantiate.
   - Any test module running after `test_e2e_consolidated.py` that relies on default `TradingConfig` database paths will erroneously point to the temporary DB created by `test_e2e_consolidated.py`.

3. **File Resource Lifecycle Logic**:
   - `delete=False` in `tempfile.NamedTemporaryFile` delegates file deletion responsibility to the caller.
   - Without an explicit call to `os.unlink()` or `Path.unlink()`, every test execution leaks 3 to 5 SQLite database files into the temporary system directory.

---

## 3. Caveats

- **Sandbox Tool Execution Restriction**: Direct command execution via `run_command` failed at the sandbox runner level (`sandbox configuration error: readwrite stock: non-absolute file path`). All findings are derived from static code audit, path tracing, import dependency analysis, and structural inspection.
- **Dynamic Market Data Calls**: Most external market data APIs (`yfinance`, `FinanceDataReader`, `requests`, `DART`) are appropriately wrapped in `unittest.mock.patch` calls in the test files, protecting offline test execution.

---

## 4. Conclusion

The automated test suite in `trading_system/tests/` is functionally rich and provides extensive coverage over all 14 multi-factor strategies, macro regimes, and system components. However, it exhibits significant architectural and environmental weaknesses:

1. **Proxy Re-Export Redundancy**: `tests/` mirrors `trading_system/tests/` via `from trading_system.tests.test_xyz import *`, leading to 2x duplicate test executions when running global `pytest`.
2. **Environmental Leaks**: Overriding `os.environ["DB_PATH"]` at module import level pollutes the process environment for subsequent test suites.
3. **Resource Leaks**: Temporary `.db` files created with `delete=False` at module level are never removed after test completion.
4. **Directory Misalignment**: `test_macro_indicators_smoke.py` is situated directly in `trading_system/` rather than `trading_system/tests/`, causing it to be bypassed during `pytest trading_system/tests/` executions.

---

## 5. Verification Method

To independently verify these findings on a local development machine:

1. **Verify Test Duplication**:
   Run:
   ```cmd
   .venv\Scripts\python.exe -m pytest --collect-only tests/
   .venv\Scripts\python.exe -m pytest --collect-only trading_system/tests/
   ```
   Compare the collected test node IDs to observe duplicate imports.

2. **Verify Misplaced Test File**:
   Run:
   ```cmd
   .venv\Scripts\python.exe -m pytest trading_system/tests/
   ```
   Observe that `trading_system/test_macro_indicators_smoke.py` is NOT executed.

3. **Verify Environment Variable Leak**:
   Execute a python snippet importing `test_e2e_consolidated`:
   ```cmd
   .venv\Scripts\python.exe -c "import os; print('Before:', os.environ.get('DB_PATH')); import trading_system.tests.test_e2e_consolidated; print('After:', os.environ.get('DB_PATH'))"
   ```
   Confirm that `os.environ['DB_PATH']` is mutated upon import.

4. **Verify Temp File Residuals**:
   Check `%TEMP%` directory before and after running test files to observe lingering `.db` temp files.
