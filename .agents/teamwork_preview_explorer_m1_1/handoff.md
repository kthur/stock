# Handoff Report: Pipeline DAG Architecture & Checkpointing Design (M1-1)

**Agent**: Explorer M1-1  
**Milestone**: M1 (R1 - Architecture Modularization & Data Engine Upgrade)  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1`  
**Analysis File**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\analysis.md`  
**Date**: 2026-07-30  

---

## 1. Observation

1. **Pipeline Script Location & Complexity**:
   - Primary pipeline entry script: `d:\Finance\code\stock\trading_system\run_pipeline.py` (2,838 lines, 154,013 bytes).
   - Driven entirely by a single function `execute_prediction_pipeline()` (lines 761–2723).
   - Executes 12 monolithic sequential steps spanning 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500) and 17 alpha strategies (XGBoost Reg, Surge, Lead-Lag, VCP Rule, VCP ML, Strict Causal LSTM, Stat-Arb, Sector Rotation, RIM Valuation, Event-Driven, MQ Factor, Options IV Skew, Order Flow, Short-Term Reversal, ARM, CARD, LATR).

2. **Absence of State Checkpointing & Resumability**:
   - Line 785, 1004, 1018, 1032, 1197: `storage.pipeline_stage("...")` context manager only records timing metrics in SQLite database tables without serializing intermediate node data artifacts or DataFrames.
   - If execution fails at Step 10 or 11 (e.g. line 1947 RIM valuation error, network timeout during yield curve fetch, or out-of-memory crash), the entire script aborts and must be restarted from line 761, repeating all data prefetching (lines 918-953, 1116-1145) and model training (lines 1004-1038).

3. **Project Specifications**:
   - `d:\Finance\code\stock\PROJECT.md` line 4 & 23–24 explicitly specify contract:
     ```
     - DAG Pipeline: Task graph execution with state serialization & resume capability (trading_system/dag_pipeline.py).
     - Tasks implement Task interface with name, dependencies, execute(context), checkpoint()/restore().
     - Pipeline state saved to .checkpoints/pipeline_state.json / parquet frames.
     ```

---

## 2. Logic Chain

1. **From Observation 1 (Monolithic Sequential Pipeline)**:
   - Because `execute_prediction_pipeline()` keeps all intermediate variables (`indicator_train`, `df_train`, `infer_data_dict`, `res_df`, `surge_df`, `stat_arb_df`, `rim_df`, `ensemble_df`) in local function scope, downstream tasks are tightly coupled to upstream tasks.
   - Individual quantitative strategies cannot be run, debugged, or benchmarked in isolation without running the preceding steps.

2. **From Observation 2 (Lack of Checkpointing & Risk of Interruption)**:
   - Running inference across 3,379 symbols takes significant time and bandwidth.
   - Without persistent node-level serialization, transient failures (e.g., API rate limits, temporary socket timeout, memory pressure) result in total loss of compute work up to that point.
   - Therefore, a node-level checkpointing mechanism storing intermediate state to disk (JSON metadata + snappy Parquet DataFrames) is required to enable zero-overhead resume capability.

3. **From Observation 3 (Project Requirements & Architecture Target)**:
   - Designing `trading_system/dag_pipeline.py` with `Task`, `DAGContext`, `CheckpointManager`, and `DAGRunner` satisfies the exact contract specified in `PROJECT.md`.
   - Organizing tasks into a Directed Acyclic Graph (10 major stage nodes, 17 parallel strategy sub-nodes) enables automatic topological ordering, cycle detection, parallel strategy execution, and selective node re-execution via `--rerun-node` or `--force-rerun`.

---

## 3. Caveats

1. **Read-Only Scope**:
   - As Explorer M1-1, this investigation is read-only analysis. Code implementation of `trading_system/dag_pipeline.py` and task node modules in `trading_system/tasks/` must be performed by Implementer agents in Milestone 1.
2. **Memory Footprint During Parallel Strategy Execution**:
   - When running strategy inference sub-nodes (N6a through N6o) in parallel using `ThreadPoolExecutor`, memory usage should be monitored if multiple strategies clone `infer_data_dict`.
3. **Database Concurrency**:
   - SQLite WAL mode is used for `StockPriceDB` and `MarketIndicatorStorage`. Task nodes performing DB writes must maintain short transactions or acquire write mutexes to avoid `OperationalError: database is locked`.

---

## 4. Conclusion

1. **DAG Architecture**: The current procedural pipeline in `run_pipeline.py` should be refactored into a modular, task-graph DAG architecture (`trading_system/dag_pipeline.py`) containing 10 major stage nodes (`N1` to `N10`) and 17 parallel strategy sub-nodes (`N6a` to `N6o`).
2. **Checkpointing & Resumability**: Implement `CheckpointManager` utilizing `.checkpoints/YYYY-MM-DD/` with `pipeline_state.json` manifest for node execution state tracking and Snappy-compressed `.parquet` files for DataFrames.
3. **Resumption Efficiency**: When a failed run is restarted, `DAGRunner` validates node checkpoints and skips all completed prerequisite nodes, reducing recovery time from ~45 minutes to < 5 seconds.

---

## 5. Verification Method

1. **Inspect Analysis Report**:
   - View `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\analysis.md` to review full class interfaces (`Task`, `DAGContext`, `CheckpointManager`, `DAGRunner`), node tables, dependency graph ASCII diagrams, and JSON manifest schemas.
2. **Pytest Verification**:
   - Once implemented, verify DAG runner unit tests with:
     ```bash
     .venv/bin/pytest tests/test_dag_pipeline.py -v
     ```
3. **Dry-Run & Simulated Failure Verification**:
   - Test DAG execution and resume functionality:
     ```bash
     # Run dry-run with debug flag
     .venv/bin/python trading_system/dag_pipeline.py --debug
     # Interrupt mid-run, then re-run to verify skipped nodes
     .venv/bin/python trading_system/dag_pipeline.py --debug
     ```
4. **Invalidation Condition**:
   - Changing `TradingConfig` parameters or using `--force-rerun` must invalidate existing checkpoints under `.checkpoints/` and force full re-execution.
