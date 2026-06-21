# explorer_bugfixes_1 Handoff Report

## Core Summary
This report analyzes two critical issues in the Stock Trading System:
1. The prediction horizon omission in `MarketIndicatorStorage.save_predictions` where `120` and `200` day prediction horizons are not saved to the SQLite database.
2. The thread-safety race condition/connection leak in `StockPriceDB._get_conn` when initializing the database connection under multi-threaded execution.

---

## 1. Observation

### R1: Prediction Horizons in `indicator_storage.py`
- **File Path**: `trading_system/src/data_layer/indicator_storage.py`
- **Lines 161–170 (`save_predictions`)**:
  ```python
      def save_predictions(self, df_preds: pd.DataFrame, date_str: str):
          """Save AI predictions to database."""
          with sqlite3.connect(self.db_path) as conn:
              for _, row in df_preds.iterrows():
                  sym = row['symbol']
                  for h in [1, 5, 10, 20, 30, 60]:
                      if h in row:
                          sql = "INSERT OR REPLACE INTO ai_predictions (date,symbol,horizon,expected_return) VALUES (?,?,?,?)"  # noqa: E501
                          conn.execute(sql, (date_str, sym, h, float(row[h])))
              conn.commit()
  ```
- **Lines 35–44 (`ai_predictions` Schema)**:
  ```python
              # Create table for AI Predictions
              conn.execute('''
                  CREATE TABLE IF NOT EXISTS ai_predictions (
                      date TEXT,
                      symbol TEXT,
                      horizon INTEGER,
                      expected_return REAL,
                      PRIMARY KEY (date, symbol, horizon)
                  )
              ''')
  ```

### R5: Database Connection Initialization in `database.py`
- **File Path**: `trading_system/src/persistence/database.py`
- **Lines 377–384 (`_get_conn`)**:
  ```python
      def _get_conn(self) -> sqlite3.Connection:
          if self._conn is None:
              self._conn = sqlite3.connect(
                  str(self.db_path), timeout=30, check_same_thread=False
              )
              self._conn.execute("PRAGMA journal_mode=WAL")
              self._conn.execute("PRAGMA synchronous=NORMAL")
          return self._conn
  ```
- **Lines 370–375 (`__init__`)**:
  ```python
      def __init__(self, db_path: str = "stock_prices.db"):
          self.db_path = Path(db_path)
          self.logger = logger
          self._lock = threading.Lock()
          self._conn: Optional[sqlite3.Connection] = None
          self._init_db()
  ```

### Test Execution Command & Results
- **Command**: `python -m pytest tests/test_post_market_scoring.py -v`
  - **Result**: `tests/test_post_market_scoring.py::TestPostMarketScoring::test_scoring_pipeline PASSED [100%]`
- **Command**: `python -m pytest tests/test_database.py -v`
  - **Result**: All 8 tests passed successfully.

---

## 2. Logic Chain

### R1: Prediction Horizon Omissions
1. The machine learning pipeline in `run_pipeline.py` generates predictions for 8 horizons: `[1, 5, 10, 20, 30, 60, 120, 200]`.
2. The `save_predictions` method in `MarketIndicatorStorage` filters using a hardcoded loop `for h in [1, 5, 10, 20, 30, 60]:`, meaning predictions for horizons `120` and `200` are ignored and never written to the SQLite database.
3. The database table `ai_predictions` defines `horizon` as an `INTEGER` and forms part of the primary key. There are no CHECK constraints or foreign keys limiting the `horizon` value.
4. If the hardcoded list in `save_predictions` is updated to `[1, 5, 10, 20, 30, 60, 120, 200]`, the missing horizons will be inserted seamlessly into the SQLite database.
5. In addition, the query method `get_predictions` returns the results dynamically based on date. The web dashboard (in `src/web/dashboard.py`) queries this table and filters for specific horizons (1, 5, 10, 20, 30, 60) for rendering. Consequently, writing new horizons (`120` and `200`) into the database is fully backward-compatible and will not cause exceptions or crashes on the dashboard.

### R5: Thread-Safety and Connection Leaks
1. In `StockPriceDB`, the connection object `self._conn` is lazily initialized as a shared singleton inside `_get_conn`.
2. If multiple threads concurrently call `_get_conn`, there is a race condition where multiple threads might check `self._conn is None` concurrently, call `sqlite3.connect()`, and assign it to `self._conn`.
3. The connection that gets overwritten is lost (unreferenced) but remains open, causing a connection leak. Over time, this leads to SQLite database locking (`database is locked` error) and file descriptor exhaustion.
4. To fix this, we need to protect connection initialization inside `_get_conn` with a lock.
5. However, since caller methods like `get_prices` and `update_prices` already acquire `self._lock` (which is a standard `threading.Lock`), locking on `self._lock` inside `_get_conn` would cause a deadlock (since standard locks are non-reentrant).
6. To solve this, we can either:
   - **Option A (Double-Checked Locking)**: Use a separate, dedicated connection lock `self._conn_lock = threading.Lock()` and initialize `self._conn` inside a double-checked block. This prevents deadlock, minimizes lock overhead, and resolves the connection leak.
   - **Option B (Reentrant Lock)**: Upgrade `self._lock` to a `threading.RLock()` and wrap the initialization block in `with self._lock:`.

---

## 3. Caveats
- Storing `120` and `200` day prediction horizons in the database will save the data successfully, but these predictions will not automatically display on the Dash dashboard. The layout code in `src/web/dashboard.py` would need to be updated with new tables and callbacks if visual indicators for `120` and `200` are desired.
- We assume that the machine learning prediction models are successfully configured to output returns for `120` and `200` day horizons.

---

## 4. Conclusion
- **R1 Proposal**:
  Update `save_predictions` in `trading_system/src/data_layer/indicator_storage.py` to:
  ```python
      def save_predictions(self, df_preds: pd.DataFrame, date_str: str):
          """Save AI predictions to database."""
          with sqlite3.connect(self.db_path) as conn:
              for _, row in df_preds.iterrows():
                  sym = row['symbol']
                  for h in [1, 5, 10, 20, 30, 60, 120, 200]: # Added 120, 200
                      if h in row:
                          sql = "INSERT OR REPLACE INTO ai_predictions (date,symbol,horizon,expected_return) VALUES (?,?,?,?)"  # noqa: E501
                          conn.execute(sql, (date_str, sym, h, float(row[h])))
              conn.commit()
  ```
- **R5 Proposal**:
  Update `StockPriceDB` in `trading_system/src/persistence/database.py` to use double-checked locking with a dedicated `_conn_lock`:
  ```python
      def __init__(self, db_path: str = "stock_prices.db"):
          self.db_path = Path(db_path)
          self.logger = logger
          self._lock = threading.Lock()
          self._conn_lock = threading.Lock()  # Dedicated connection lock
          self._conn: Optional[sqlite3.Connection] = None
          self._init_db()

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

---

## 5. Verification Method
- **Verification Commands**:
  - Run the test suite to verify no regressions:
    `python -m pytest tests/test_database.py -v`
    `python -m pytest tests/test_post_market_scoring.py -v`
  - Write a small test script that instantiates `StockPriceDB` and calls `get_prices` concurrently from multiple threads to check for race conditions and deadlock safety.
- **Invalidation Condition**:
  - If a thread calls `StockPriceDB.get_prices` and it blocks indefinitely, the lock implementation has introduced a deadlock (meaning `self._lock` was reused inside `_get_conn` without being converted to an `RLock`).
