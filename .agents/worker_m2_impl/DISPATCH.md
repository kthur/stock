## 2026-08-12T14:48:33Z

Task: Implement Milestone 2 (R2: Inference Vectorization & SQLite Concurrency Protection):
Read d:/Finance/code/stock/.agents/explorer_survey_2/report.md, d:/Finance/code/stock/ORIGINAL_REQUEST.md, and d:/Finance/code/stock/PROJECT.md.

1. **Inference Vectorization**:
   - Refactor `OnDevicePredictionModel` (`trading_system/src/ai/prediction_model.py`):
     - Replace the symbol-level loop calling single-sample LSTM inference `lstm_m.predict(x_in)[0]` with batch array prediction `lstm_m.predict(X_batch)` of 3D shape `(N_valid, seq_len, num_features)` to process 3,379 symbols in vectorized batches.
   - Refactor strategy scorers in `trading_system/src/core/` (`trend_efficiency.py`, `short_term_reversal.py`, `accruals_quality.py`, etc.):
     - Vectorize symbol-level loop calculations using Pandas/NumPy 2D matrix operations across close/volume DataFrames.
2. **SQLite Concurrency Protection (`PRAGMA busy_timeout = 30000;`)**:
   - In `trading_system/src/persistence/database.py` (`StockPriceDB`):
     - Ensure connection initialization sets `PRAGMA busy_timeout = 30000;` and `PRAGMA journal_mode = WAL;`.
   - In `trading_system/src/data_layer/indicator_storage.py` (`MarketIndicatorStorage`):
     - Update connection initialization `PRAGMA busy_timeout` from `5000` to `30000;`.
   - In raw `sqlite3.connect` calls across `trading_system/src/execution/oms_engine.py`, `trading_system/src/risk/portfolio_allocator.py`, `trading_system/src/ai/slippage_feedback.py`, etc.:
     - Ensure all SQLite connection helper functions or connection contexts execute `PRAGMA busy_timeout = 30000;` and `PRAGMA journal_mode = WAL;`.
3. **Unit Tests & Verification**:
   - Add/update unit test file `trading_system/tests/test_database_concurrency.py` to run multi-threaded SQLite stress test (e.g. 20 parallel threads writing/reading simultaneously) and verify ZERO `database is locked` errors occur under `busy_timeout=30000`.
   - Add/update benchmark verification in `trading_system/tests/test_prediction_model.py` or new benchmark test verifying vectorized inference performance.
   - Execute tests: `.venv\Scripts\python.exe -m pytest tests/test_database_concurrency.py trading_system/tests/test_database.py -v`.
   - Run full pytest suite: `.venv\Scripts\python.exe -m pytest tests/` and `.venv\Scripts\python.exe -m pytest trading_system/tests/`.
