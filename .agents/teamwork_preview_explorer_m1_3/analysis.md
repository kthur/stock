# Comprehensive Analysis & Testing Strategy for Milestone 1 (R1)

**Author**: Explorer M1-3  
**Date**: 2026-07-30  
**Scope**: Architecture Modularization & Data Engine Upgrade (DAG Pipeline, Task Checkpointing & Resumability, Hybrid Data Engine Zero Write-Lock Concurrency)  
**Target Files & Modules**:
- `trading_system/dag_pipeline.py` (DAG Execution Engine, Task Interface, Pipeline Context, Checkpoint Manager)
- `src/data_layer/hybrid_storage.py` & `src/data_layer/parquet_wal_engine.py` (Hybrid SQLite/Parquet Engine, Parquet WAL Append-Log)
- `tests/` & `trading_system/tests/` (Pytest test suite & fixture infrastructure)

---

## 1. Executive Summary & Existing Test Suite Audit

### 1.1 Architecture & Test Suite Overview
The stock trading system codebase contains **69 test files** in `tests/` (with mirrored files in `trading_system/tests/`). The current test suite relies on two primary testing patterns:
1. **`unittest.TestCase` Framework**: Used across legacy core components (`test_database.py`, `test_orchestrator.py`, `test_event_bus.py`, `test_async_helper.py`).
2. **`pytest` Functions & Markers**: Used in feature/strategy test files (`test_pipeline_data_filter.py`, `test_hpo_and_2d_ensemble.py`, `test_phase3_pipeline_data_filter.py`).

Configuration and entry points:
- `tests/conftest.py`: Dynamically inserts project root and `trading_system/` into `sys.path`.
- Environment isolation: Tests instantiate SQLite databases in temporary files (`tempfile.NamedTemporaryFile`) and set `TradingConfig.db_path` or `os.environ["DB_PATH"]`.

### 1.2 Audit of Current Concurrency & Storage Tests
1. **`TestMarketIndicatorStorageConcurrency` (`trading_system/tests/test_database.py`)**:
   - Tests multi-threaded writes using 5 threads doing 20 writes each (`save_indicators()`).
   - Uses `threading.Thread` and a `queue.Queue` to trap exceptions.
   - Evaluates basic SQLite table insertion under modest thread counts.
2. **`TestStockPriceDBConcurrency` (`trading_system/tests/test_database.py`)**:
   - Tests 5 concurrent threads updating price history (`update_prices()`).
   - Relies on internal mutex locks inside `StockPriceDB`.
3. **`TestEventBus` (`trading_system/tests/test_event_bus.py`)**:
   - Tests multi-threaded event registration and dispatch (`10 subscriber threads` + `10 publisher threads`).

### 1.3 Critical Deficiencies & Gaps for Milestone 1 (R1)
While legacy database tests verify simple SQLite mutexes, they **fail to cover the M1 architecture requirements**:
- **Zero DAG Pipeline Coverage**: No existing test file tests task graph definition, topological execution order, cycle detection, or task context propagation.
- **Zero Checkpoint & Resumability Coverage**: No tests exist for `.checkpoints/pipeline_state.json`, parquet checkpoint state dumps, or resuming failed pipeline runs without re-executing successful tasks.
- **Insufficient Concurrency Scale & Storage Isolation**: Current SQLite tests only use 5 threads with tiny payloads. They do NOT test multi-asset streaming across 3,379 symbols, nor do they test Parquet append-log / Timescale WAL engine hybrid reads/writes under zero-lock constraints.

### 1.4 Pytest Collection & Module Resolution Anomaly
During empirical verification running `.venv\Scripts\python.exe -m pytest tests/ --collect-only`, 59 test files in root `tests/` raised:
`ModuleNotFoundError: No module named 'trading_system.tests'`
- **Root Cause**: The 59 root test files consist of wrapper statements like `from trading_system.tests.test_X import *`. When running `pytest tests/`, Pytest loads `tests` from the root directory into `sys.modules['tests']`, which shadows `trading_system/tests`.
- **Resolution**:
  1. Tests must be executed pointing directly to `trading_system/tests/`: `.venv\Scripts\python.exe -m pytest trading_system/tests/`.
  2. For M1 test files (`test_dag_pipeline.py`, `test_checkpoint_manager.py`, `test_hybrid_data_engine.py`), co-locate tests under `tests/` and `trading_system/tests/` with explicit package namespace handling in `conftest.py`.

---


## 2. Testing Strategy for DAG Pipeline Execution

The DAG Pipeline (`trading_system/dag_pipeline.py`) replaces sequential execution in `run_pipeline.py` with a task-graph execution engine.

### 2.1 Task Interface Contract Verification
All tasks executed in the pipeline MUST adhere strictly to the `Task` interface:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Task(ABC):
    name: str
    dependencies: List[str]

    @abstractmethod
    def execute(self, context: PipelineContext) -> TaskResult:
        pass

    @abstractmethod
    def checkpoint(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def restore(self, state: Dict[str, Any]) -> None:
        pass
```

**Testing Approach**:
- **Interface Compliance Test**: A meta-test iterating over all concrete `Task` subclasses to ensure all required properties and methods are implemented with correct type signatures.
- **Execution Isolation**: Verify that tasks interact only via `PipelineContext` and do not rely on global side effects.

### 2.2 Toposort & Graph Invariants
The DAG engine must construct an execution graph and sort nodes topologically.

**Test Scenarios**:
1. **Diamond Graph Execution**:
   - Graph: `A -> B`, `A -> C`, `B -> D`, `C -> D`.
   - Verification: `A` executes first; `B` and `C` can execute in parallel; `D` executes ONLY after both `B` and `C` report `SUCCESS`.
2. **Deep Linear Chain**:
   - Graph: 100 sequential tasks (`T0 -> T1 -> ... -> T99`).
   - Verification: Strict sequential ordering preserved, zero recursion depth limit errors during topological sort.
3. **Disconnected Components**:
   - Subgraph 1: `A -> B`; Subgraph 2: `X -> Y`.
   - Verification: Both subgraphs execute to completion without blocking each other.

### 2.3 Cycle Detection & Fault Rejection
Before running any tasks, `DAGPipeline.validate_dag()` must detect circular dependencies and throw `CyclicDependencyError`.

**Test Scenarios**:
1. **Direct Cycle**: `A -> B -> A`.
2. **Indirect Cycle**: `A -> B -> C -> D -> A`.
3. **Self Loop**: `A -> A`.

### 2.4 Parallel Task Graph Execution & Context Safety
Independent nodes at the same DAG level should execute concurrently using `ThreadPoolExecutor` or `asyncio.gather`.

**Test Scenarios**:
1. **Concurrency Verification**: Tasks `B1, B2, B3` depending on `A` must run concurrently in separate threads.
2. **Context Thread-Safety**: `PipelineContext` must use explicit thread locks or copy-on-write dictionaries when tasks read/write intermediate artifacts.

---

## 3. Testing Strategy for Task Checkpointing & Resumability

Pipeline state serialization and resuming from partial failures are critical for production reliability across 3,379 symbols.

### 3.1 Dual-Tier Serialization Architecture
Checkpointing uses a two-tier approach:
1. **Metadata Tier**: Lightweight JSON (`.checkpoints/pipeline_state.json`) recording node status (`SUCCESS`, `FAILED`, `SKIPPED`), execution start/end timestamps, task parameters, and execution signatures.
2. **Data Tier**: Heavy DataFrames serialized to Parquet files (`.checkpoints/{task_name}_output.parquet`).

### 3.2 Resumability & Partial Failure Recovery Testing
**Test Scenario**:
1. Construct 5-task DAG: `T1 (Ingest) -> T2 (Features) -> T3 (Train) -> T4 (Predict) -> T5 (Report)`.
2. Run pipeline. `T1` and `T2` succeed. `T3` raises a simulated exception (`RuntimeError("CUDA OOM")`).
3. Assert pipeline halts gracefully. Verify `.checkpoints/pipeline_state.json` records:
   - `T1`: `SUCCESS`
   - `T2`: `SUCCESS`
   - `T3`: `FAILED`
   - `T4`: `PENDING` / `SKIPPED`
   - `T5`: `PENDING` / `SKIPPED`
4. Re-instantiate `DAGPipeline` with `resume=True` and fixed `T3`.
5. Run pipeline. Verify:
   - `T1` and `T2` `execute()` methods are **NEVER CALLED** (their outputs are loaded directly from `.checkpoints/`).
   - `T3` executes successfully.
   - `T4` and `T5` execute to completion.

### 3.3 Idempotency & Hash Verification
To prevent using outdated checkpoints:
- Compute SHA-256 hash of task inputs (configuration parameters + dependency output hashes).
- If hash changes, invalidate checkpoint automatically and force re-execution.

### 3.4 Atomic Write & Crash Recovery
- Checkpoints must be written to `.checkpoints/{name}.tmp` and atomically renamed to `.checkpoints/{name}.json` (using `os.replace`).
- Test spec: Simulate abrupt process death during checkpoint write; ensure pipeline state is not corrupted.

---

## 4. Multi-Asset Streaming Concurrency Strategy (Zero Write-Locks)

To handle real-time streaming data for 3,379 symbols without SQLite `database is locked` operational errors, M1 introduces a Hybrid Data Engine (`HybridDataEngine`) with a Parquet Append-Log / Timescale WAL engine.

```
[3,379 Asset Streamers] ---> [Parquet WAL Engine (Append-Log)] ---> [RAM Micro-Buffer]
                                                                            |
                                  [Zero Write-Lock]                         v
[Concurrent Query Readers] <--------------------------------- [SQLite WAL / Parquet Storage]
```

### 4.1 Hybrid Parquet / SQLite WAL Concurrency Model
1. **Streaming Writers**: High-frequency tick/bar ingestion writes directly to partitioned Parquet append logs (`data/wal/{date}/{symbol}.parquet`) or in-memory ring buffers.
2. **Background Flush Engine**: Periodically batches Parquet logs and writes to SQLite with WAL mode (`PRAGMA journal_mode=WAL`) or atomic Parquet partitioning.
3. **Query Readers**: Readers query SQLite/Parquet snapshot views without acquiring write locks.

### 4.2 Zero Write-Lock Load Testing Specification
**Test Setup**:
- **Stress Parameters**: 50 concurrent writer threads/processes.
- **Payload**: Streaming bar updates for 500 symbols per thread (total 25,000 symbol updates per iteration) for 100 iterations.
- **Simultaneous Readers**: 10 reader threads running heavy aggregate queries (`SELECT symbol, AVG(Close), MAX(High) GROUP BY symbol`).

**Assertion Rules**:
1. Zero `sqlite3.OperationalError: database is locked` raised across all 50 writer threads and 10 reader threads.
2. Writer throughput must exceed 5,000 records/sec.
3. Reader query latency P99 must remain < 50ms during active writes.

### 4.3 Buffer Flush & Atomic Swap Mechanics
**Test Scenarios**:
1. **Buffer Overflow Flush**: Fill memory buffer to capacity (`max_buffer_size=10,000`). Verify background worker flushes buffer to storage asynchronously without blocking incoming stream.
2. **Atomic Swap Verification**: When swapping buffer to persistent Parquet partitions, active read queries must return complete data without experiencing partial read anomalies.

---

## 5. Detailed Specifications for New Unit Test Modules

Below are the exact unit test specifications to be implemented by Implementer agents for Milestone 1.

### 5.1 `tests/test_dag_pipeline.py`
| Test Function | Description & Assertion |
|---------------|-------------------------|
| `test_task_contract_compliance()` | Inspects all concrete task classes, asserting inheritance from `Task` ABC and presence of required methods. |
| `test_dag_topological_sort_diamond()` | Validates execution order of diamond DAG (`A -> B/C -> D`). |
| `test_dag_cycle_detection_raises_error()` | Ensures cyclic graph throws `CyclicDependencyError`. |
| `test_dag_parallel_execution_order()` | Measures thread execution timestamps to verify independent nodes run in parallel. |
| `test_pipeline_context_thread_safety()` | Tests concurrent reads/writes to `PipelineContext` under 20 threads. |
| `test_failed_task_skips_downstream()` | Asserts that when node `B` fails in `A -> B -> C`, `C` is marked `SKIPPED` and not executed. |

### 5.2 `tests/test_checkpoint_manager.py`
| Test Function | Description & Assertion |
|---------------|-------------------------|
| `test_checkpoint_state_serialization_json()` | Tests metadata serialization and deserialization in `.checkpoints/pipeline_state.json`. |
| `test_checkpoint_parquet_data_dump_and_restore()` | Serializes DataFrame state to `.checkpoints/{task}.parquet` and verifies byte-for-byte restoration. |
| `test_resumability_skip_completed_tasks()` | Mocks a pipeline restart after failure; asserts completed tasks are skipped. |
| `test_checkpoint_input_hash_invalidation()` | Changes input parameters for a completed task; verifies checkpoint is invalidated and task re-runs. |
| `test_atomic_checkpoint_write_on_crash()` | Simulates write interruption; verifies existing checkpoint remains valid without corruption. |

### 5.3 `tests/test_hybrid_data_engine.py`
| Test Function | Description & Assertion |
|---------------|-------------------------|
| `test_parquet_wal_append_stream()` | Tests rapid streaming appends to Parquet WAL files across 100 tickers. |
| `test_zero_sqlite_write_lock_under_50_threads()` | Runs 50 concurrent writer threads against SQLite/Parquet hybrid engine; asserts 0 lock errors. |
| `test_concurrent_readers_and_writers_no_blocking()` | Runs 10 reader queries during 50-thread streaming write; asserts zero query blocking. |
| `test_buffer_flush_and_atomic_swap()` | Fills buffer, triggers async flush, and verifies data integrity in final storage. |
| `test_multi_asset_3379_symbols_partitioning()` | Validates symbol-based directory partitioning (`data/market=KOSPI/symbol=005930/`). |

---

## 6. Synthesis & Recommendations for Next Steps

1. **Test Helper Expansion**: Upgrade `tests/conftest.py` with custom fixtures:
   - `@pytest.fixture` `temp_checkpoint_dir`: Provides isolated temporary checkpoint directory.
   - `@pytest.fixture` `hybrid_db`: Sets up a clean temporary `HybridDataEngine` instance in SQLite WAL mode.
2. **Stress Test Integration**: Mark heavy concurrency tests with `@pytest.mark.stress` so they can be run selectively during CI/CD.
3. **Coverage Enforcement**: Set minimum test coverage threshold to 90% for `trading_system/dag_pipeline.py` and `src/data_layer/hybrid_storage.py`.
