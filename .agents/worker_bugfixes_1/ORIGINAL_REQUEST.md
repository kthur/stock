You are a teamwork_preview_worker.
Your working directory is d:\Finance\code\stock\.agents\worker_bugfixes_1.
Your task is to implement the following 5 bug fixes in the codebase:

1. R1 (Prediction horizon data leak):
   - File: `trading_system/src/data_layer/indicator_storage.py`
   - In `save_predictions` (around line 166), change the list `[1, 5, 10, 20, 30, 60]` to `[1, 5, 10, 20, 30, 60, 120, 200]`.

2. R2 (merge_fundamentals KeyError):
   - File: `trading_system/src/ai/prediction_model.py`
   - In `merge_fundamentals` (around line 457), modify the drop statement to include `errors='ignore'`, i.e.:
     `df = df.drop(columns=['date_align', 'date_fund'], errors='ignore')`

3. R3 (run_pipeline.py VCP universe map):
   - File: `trading_system/run_pipeline.py`
   - In `vcp_universe_map` construction (around lines 706-707), change:
     ```python
     vcp_universe_map = {s: (n, m) for s, n, m in zip(universe.get('symbol', []),
                         universe.get('name', []), universe.get('market', []))}
     ```
     to:
     ```python
     vcp_universe_map = {s: (n, m) for s, n, m in zip(universe['symbol'],
                         universe['name'], universe['market'])}
     ```

4. R4 (pandas Deprecation Warning):
   - File: `trading_system/src/ai/prediction_model.py`
   - Around lines 542-545, remove `fill_method=None` from all four `pct_change()` calls:
     ```python
     df['ret_1d'] = df['Close'].pct_change(1)
     df['ret_5d'] = df['Close'].pct_change(5)
     df['ret_20d'] = df['Close'].pct_change(20)
     df['ret_60d'] = df['Close'].pct_change(60)
     ```

5. R5 (StockPriceDB Thread-safety):
   - File: `trading_system/src/persistence/database.py`
   - In `__init__` (around line 370), initialize `self._conn_lock = threading.Lock()`.
   - In `_get_conn` (around line 377), implement double-checked locking using `self._conn_lock` to ensure that initialization of `self._conn` is thread-safe and connection leaks are prevented. E.g.:
     ```python
     def _get_conn(self) -> sqlite3.Connection:
         if self._conn is None:
             with self._conn_lock:
                 if self._conn is None:
                     self._conn = sqlite3.connect(
                         str(self.db_path), timeout=30, check_same_thread=False
                     )
                     self._conn.execute("PRAGMA journal_mode=WAL")
                     self._conn.execute("PRAGMA synchronous=NORMAL")
         return self._conn
     ```

After implementing these changes, you must run the tests to verify the implementation:
- Run the test suite: `.venv\Scripts\pytest trading_system/tests/ -v` (or run python's pytest module) and ensure all tests pass.
- Verify that `trading_system/run_pipeline.py` runs without errors.
Write your completion report in handoff.md under your working directory and notify the parent orchestrator.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-06-19T13:44:00Z
Please execute the task in d:\Finance\code\stock\.agents\worker_bugfixes_1\ORIGINAL_REQUEST.md. Implement the 5 bug fixes (R1-R5) and verify via the test suite and by running run_pipeline.py. Write your report to d:\Finance\code\stock\.agents\worker_bugfixes_1\handoff.md and notify me.
