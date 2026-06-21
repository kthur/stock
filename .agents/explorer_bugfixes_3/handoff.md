# Handoff Report - VCP Universe Map Investigation

## 1. Observation
In `trading_system/run_pipeline.py` (lines 706-707), the dictionary `vcp_universe_map` is constructed using `.get()` on the `universe` object:
```python
        vcp_universe_map = {s: (n, m) for s, n, m in zip(universe.get('symbol', []),
                            universe.get('name', []), universe.get('market', []))}
```

### Universe DataFrame Definition
The `universe` variable is loaded from `storage.get_universe()` (lines 305-309):
```python
    universe = storage.get_universe()
    if universe.empty:
        logger.info("Universe is empty. Syncing stock universe...")
        storage.update_stock_universe()
        universe = storage.get_universe()
```
The `get_universe()` method in `src/data_layer/indicator_storage.py` (lines 152-159) returns a `pd.DataFrame`:
```python
    def get_universe(self, market: Optional[str] = None) -> pd.DataFrame:
        query = "SELECT * FROM stock_universe"
        params: tuple = ()
        if market:
            query += " WHERE market = ?"
            params = (market,)
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=params)
```
The table schema for `stock_universe` is created in `src/data_layer/indicator_storage.py` (lines 28-33) with columns: `symbol`, `name`, and `market`:
```sql
            # Create table for stock universe
            conn.execute('''
                CREATE TABLE IF NOT EXISTS stock_universe (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT
                )
            ''')
```

### Inconsistent Column Access
Throughout the rest of `run_pipeline.py`, the `universe` DataFrame columns are accessed directly via standard dictionary-like bracket notation:
- **Line 210**: `markets[m] = set(universe[universe['market'] == m]['symbol'])`
- **Line 313**: `symbol_market = dict(zip(universe['symbol'], universe['market']))`
- **Line 327**: `kospi_symbols = universe[universe['market'] == 'KOSPI']['symbol'].tolist()`
- **Line 645**: `surge_df = surge_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')`
- **Line 698**: `name_row = universe[universe['symbol'] == sym]`

---

## 2. Logic Chain
1. **Schema Guarantee**: Since the database schema defines `symbol`, `name`, and `market` columns on `stock_universe`, any successful query returning `universe` as a `pd.DataFrame` will contain these columns (Observation 1 - table schema).
2. **Standard Bracket Usage**: The rest of the pipeline accesses columns directly (e.g. `universe['symbol']`), showing that direct column access is assumed and relied upon throughout `run_pipeline.py` (Observation 1 - inconsistent column access).
3. **Silent Failure Risk of `.get()`**:
   - If a column (e.g., `'symbol'`) were somehow missing, `universe.get('symbol', [])` returns `[]`.
   - Zipping a list `[]` with other populated Pandas Series results in an empty iterator because `zip()` terminates at the shortest input length.
   - Consequently, `vcp_universe_map` silently evaluates to `{}` (empty dictionary).
   - This empty mapping causes the downstream market filtering list comprehension (line 714) to return `''` for all symbols, matching no markets, and silently dropping all found VCP patterns from the final report file `vcp_patterns.txt`.
4. **KeyError for Loud Failure**: Using direct column access `universe['symbol']` would cause pandas to raise a `KeyError` immediately if the database schema did not match the expected columns, pointing developers directly to the database mismatch rather than silently producing an empty report file.
5. **Conclusion**: Direct column access is pandas-idiomatic, consistent with the rest of the codebase, and prevents silent output omissions.

---

## 3. Caveats
- This investigation assumes that the database table schema `stock_universe` contains columns `symbol`, `name`, and `market` as defined in `src/data_layer/indicator_storage.py`. If the database schema is modified in an unexpected way, the pipeline will raise a `KeyError` (which is the desired, fail-fast behavior).
- **Pre-existing Test Failures**: There are 11 pre-existing failing tests in the test suite on the main branch (e.g., `AttributeError: 'coroutine' object has no attribute 'get'` in `trading_system.py:497` triggered by `test_portfolio_risk.py` and other adversarial/normalization tests). These are unrelated to R3 and do not invalidate the findings or proposed fix for `run_pipeline.py`.

---

## 4. Conclusion
The use of `.get('column', [])` on `universe` is an anti-pattern that deviates from consistent direct column access in the rest of `run_pipeline.py` and risks silent failures.
It should be refactored to:
```python
        vcp_universe_map = {s: (n, m) for s, n, m in zip(universe['symbol'],
                            universe['name'], universe['market'])}
```
A complete patch file `vcp_universe_map.patch` has been written to the agent's folder.

---

## 5. Verification Method
- **Test execution**: Run `python -m pytest tests/ -v` from `d:\Finance\code\stock\trading_system`. Note that 11 tests are expected to fail due to pre-existing, unrelated issues in `trading_system.py` and `prediction_model.py` (which are in the scope of other bugfix tasks R1, R2, R4, R5). Verify that no new failures are introduced in the test suite.
- **Pipeline integration**: Execute the pipeline and verify that `vcp_patterns.txt` is correctly generated and contains matching patterns sorted by market.
- **Fail-fast behavior**: If a column is dropped from `stock_universe` table schema, verify that running the pipeline raises a `KeyError` loudly rather than completing silently with empty outputs.
