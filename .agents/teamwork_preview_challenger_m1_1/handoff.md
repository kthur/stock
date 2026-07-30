# Handoff Report — Milestone 1 Empirical Stress-Test of DAG Pipeline

## 1. Observation

### System & Environment Under Test
- Target module: `trading_system/dag_pipeline.py` (602 lines)
- Test suite created: `tests/test_dag_pipeline_stress_m1.py` (15 test cases across 5 stress dimensions)
- Python environment: `.venv\Scripts\python.exe` (Python 3.11.9, pytest 9.1.1)

### Execution Command & Results
```bash
.venv\Scripts\python.exe -m pytest tests/test_dag_pipeline_stress_m1.py -v
```
Output:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Finance\code\stock\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Finance\code\stock
plugins: anyio-4.14.0, dash-2.18.2, cov-7.1.0
collected 15 items

tests/test_dag_pipeline_stress_m1.py::TestPipelineCrashRecovery::test_pipeline_crash_halts_downstream_tasks PASSED [  6%]
tests/test_dag_pipeline_stress_m1.py::TestPipelineCrashRecovery::test_pipeline_resumption_after_crash PASSED [ 13%]
tests/test_dag_pipeline_stress_m1.py::TestCorruptedCheckpointJSON::test_manifest_corrupted_completed_tasks_type PASSED [ 20%]
tests/test_dag_pipeline_stress_m1.py::TestCorruptedCheckpointJSON::test_manifest_malformed_json_recovery PASSED [ 26%]
tests/test_dag_pipeline_stress_m1.py::TestCorruptedCheckpointJSON::test_manifest_non_dict_json_vulnerability PASSED [ 33%]
tests/test_dag_pipeline_stress_m1.py::TestCorruptedCheckpointJSON::test_task_corrupted_json_artifact_during_restore PASSED [ 40%]
tests/test_dag_pipeline_stress_m1.py::TestMissingAndCorruptedParquetFrames::test_artifact_registry_erased_by_dagrunner PASSED [ 46%]
tests/test_dag_pipeline_stress_m1.py::TestMissingAndCorruptedParquetFrames::test_parquet_file_corrupted_zero_bytes PASSED [ 53%]
tests/test_dag_pipeline_stress_m1.py::TestDeepCyclicGraphsAndTopologies::test_deep_50_node_ring_cycle PASSED [ 60%]
tests/test_dag_pipeline_stress_m1.py::TestDeepCyclicGraphsAndTopologies::test_disconnected_graph_with_internal_cycle PASSED [ 66%]
tests/test_dag_pipeline_stress_m1.py::TestDeepCyclicGraphsAndTopologies::test_figure_eight_double_cycle PASSED [ 73%]
tests/test_dag_pipeline_stress_m1.py::TestDeepCyclicGraphsAndTopologies::test_self_loop_cycle PASSED [ 80%]
tests/test_dag_pipeline_stress_m1.py::TestDeepCyclicGraphsAndTopologies::test_unknown_dependency_raises_value_error PASSED [ 86%]
tests/test_dag_pipeline_stress_m1.py::TestHighConcurrencyAndRaceConditions::test_concurrent_manifest_updates_stress PASSED [ 93%]
tests/test_dag_pipeline_stress_m1.py::TestHighConcurrencyAndRaceConditions::test_concurrent_parquet_saves_same_filename_race_condition PASSED [100%]

============================= 15 passed in 44.89s =============================
```

### Specific Vulnerabilities & Bugs Empirically Isolated

#### 1. Manifest Artifact Erasure Bug in DAGRunner (`trading_system/dag_pipeline.py:284-285`)
- **Location**: `trading_system/dag_pipeline.py:284-285`
- **Observed Code**:
  ```python
  task.checkpoint(self.context, result)
  elapsed = time.time() - t0
  self.context.checkpoint_manager.mark_completed(task.name, duration=elapsed, context=self.context)
  ```
- **Observed Error / Verbatim Data**: `mark_completed` takes parameter `artifacts: Optional[List[str]] = None`, defaulting to `[]`. When `task.checkpoint()` registers generated artifact filenames (e.g. `['N1_universe.parquet', 'N1_macro_summary.json']`), `DAGRunner.run()` immediately calls `mark_completed()` right after without passing `artifacts`. This overwrites `manifest["completed_tasks"][task_name]["artifacts"]` with `[]`.
- **Impact**: Manifest on disk records `"artifacts": []` for every task. `CheckpointManager.is_valid()` checks `task_entry.get("artifacts", [])`. Because `artifacts` is empty `[]`, `is_valid()` returns `True` even if parquet files are deleted from disk!

#### 2. Uncaught `AttributeError` on Corrupted JSON Manifest (`trading_system/dag_pipeline.py:101`)
- **Location**: `trading_system/dag_pipeline.py:58-64` & `101`
- **Observed Code**:
  ```python
  def _load_manifest(self) -> Dict[str, Any]:
      if self.manifest_path.exists():
          try:
              with open(self.manifest_path, "r", encoding="utf-8") as f:
                  return json.load(f)
          except Exception as e:
              logger.warning(...)
  ...
  task_entry = self._manifest.get("completed_tasks", {}).get(task_name)
  ```
- **Observed Verbatim Exception**:
  ```
  AttributeError: 'list' object has no attribute 'get'
  ```
- **Impact**: If `pipeline_state.json` contains valid JSON that is a list `[1, 2, 3]` (or if `"completed_tasks"` is a list), `_load_manifest` loads it without checking `isinstance(data, dict)`. Calling `.get()` crashes pipeline initialization with an unhandled `AttributeError`.

#### 3. Concurrent File Access & Temporary Name Collision on Windows (`trading_system/dag_pipeline.py:146-149`)
- **Location**: `trading_system/dag_pipeline.py:146-149`
- **Observed Code**:
  ```python
  def save_parquet(self, filename: str, df: pd.DataFrame) -> str:
      path = self.checkpoint_dir / filename
      tmp_path = path.with_suffix(".tmp")
      df.to_parquet(tmp_path, compression="snappy", index=True)
      os.replace(tmp_path, path)
      return filename
  ```
- **Observed Verbatim Exception**:
  ```
  PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: '...concurrent_test.tmp' -> '...concurrent_test.parquet'
  ```
- **Impact**: Multi-threaded or parallel tasks writing parquet files with identical names collide on `path.with_suffix(".tmp")` (`<name>.tmp`). On Windows, `os.replace` fails with `PermissionError` when another thread holds an open file handle on the `.tmp` file.

#### 4. Shallow File Existence Check ignores Truncated/Corrupted 0-Byte Artifacts (`trading_system/dag_pipeline.py:106-110`)
- **Location**: `trading_system/dag_pipeline.py:106-110`
- **Observed Code**:
  ```python
  for artifact_name in task_entry.get("artifacts", []):
      art_path = self.checkpoint_dir / artifact_name
      if not art_path.exists():
          return False
  ```
- **Impact**: If a parquet or JSON artifact is 0 bytes (e.g. truncated due to process crash or disk write error), `art_path.exists()` returns `True`. `is_valid()` passes, and `task.restore()` subsequently fails with an unhandled `pyarrow.lib.ArrowInvalid` or `json.JSONDecodeError` during pipeline execution instead of triggering re-execution.

---

## 2. Logic Chain

1. **Topological Ordering & Cycle Detection**:
   - Kahn's algorithm in `_topological_sort()` (`dag_pipeline.py:238-264`) correctly tracks in-degrees and detects cycles in deep 50-node rings, figure-eight cycles, self-loops, and disconnected cyclic components by checking `len(order) != len(self.tasks)`. It raises `CyclicDependencyError`. (Verified in tests 9-12).

2. **Pipeline Execution & Crash Halting**:
   - In `DAGRunner.run()`, when node `T2` throws `RuntimeError`, execution halts immediately in the loop (`dag_pipeline.py:288-291`), marking `T2` as `FAILED` in `manifest["failed_tasks"]`. Downstream task `T3` is never executed. On resume, `T1` checkpoint is restored without re-execution. (Verified in tests 1-2).

3. **Manifest Artifact Overwrite Vulnerability**:
   - When `task.checkpoint(context, result)` executes, concrete task implementations register generated artifacts by calling `checkpoint_manager.mark_completed(task.name, artifacts=[...])`.
   - Immediately after `task.checkpoint()` returns, line 285 calls `self.context.checkpoint_manager.mark_completed(task.name, duration=elapsed, context=self.context)` without passing `artifacts`.
   - `mark_completed` sets `"artifacts": artifacts or []`, overwriting the list registered during `task.checkpoint()` with `[]`.
   - Consequently, `is_valid()` checks `for artifact_name in []`, effectively bypassing artifact validation entirely. (Verified in test 7).

4. **Manifest Deserialization Type Insecurity**:
   - `_load_manifest()` assumes `json.load(f)` returns a `dict`.
   - If `pipeline_state.json` is a JSON array `[...]` or string, or if `completed_tasks` is a `list` or `None`, `_load_manifest()` returns the non-dict object without validation.
   - When `is_valid()` executes `self._manifest.get("completed_tasks", {}).get(task_name)`, calling `.get()` on a non-dict object raises `AttributeError`, preventing pipeline startup. (Verified in tests 3 & 5).

5. **Concurrency & File Lock Race Conditions**:
   - `save_parquet()` uses a deterministic temporary filename `path.with_suffix(".tmp")`.
   - Under concurrent thread execution, two threads saving to the same target filename attempt to write to the same `.tmp` path simultaneously.
   - On Windows filesystem, opening the same `.tmp` file in parallel prevents `os.replace(tmp_path, path)` from replacing the target file, raising `PermissionError: [WinError 32]`. (Verified in test 15).

---

## 3. Caveats

- **Scope Limit**: As an EMPIRICAL CHALLENGER (critic, specialist), I write and run stress tests to surface vulnerabilities. Implementation code (`trading_system/dag_pipeline.py`) was NOT modified by this agent.
- **Platform Specificity**: `PermissionError: [WinError 32]` on concurrent `.tmp` file replacement is specific to Windows file locking mechanics (Linux permits atomic unlinked file replacement).
- **Process vs Thread Concurrency**: High-concurrency tests were executed using `ThreadPoolExecutor`. Multi-process execution (`ProcessPoolExecutor` or separate CLI invocations) on un-locked `pipeline_state.json` will additionally cause lost updates on `manifest` writes.

---

## 4. Conclusion

`trading_system/dag_pipeline.py` passes topological sorting, basic cycle detection, and happy-path node resumption. However, empirical stress testing revealed **four (4) critical vulnerabilities and design bugs**:

1. **CRITICAL**: `DAGRunner.run()` erases task artifact registries on completion by calling `mark_completed()` with default `artifacts=None`.
2. **HIGH**: `CheckpointManager._load_manifest()` lacks type validation for `dict`, crashing with `AttributeError` when `pipeline_state.json` contains corrupted non-dict JSON or invalid `completed_tasks` structures.
3. **HIGH**: `CheckpointManager.save_parquet()` uses deterministic `.tmp` filenames, causing Windows `PermissionError` file collisions under concurrency.
4. **MEDIUM**: `CheckpointManager.is_valid()` checks file existence only (`exists()`), ignoring 0-byte or corrupted artifact files.

---

## 5. Verification Method

To independently verify these findings, run the newly created stress test suite:

```bash
.venv\Scripts\python.exe -m pytest tests/test_dag_pipeline_stress_m1.py -v
```

### Invalidation Conditions
- If `tests/test_dag_pipeline_stress_m1.py::test_artifact_registry_erased_by_dagrunner` fails (meaning artifacts are preserved), the artifact overwrite bug has been fixed.
- If `tests/test_dag_pipeline_stress_m1.py::test_manifest_non_dict_json_vulnerability` fails (meaning `is_valid` gracefully handles non-dict JSON), the manifest deserialization bug has been fixed.
- If `tests/test_dag_pipeline_stress_m1.py::test_concurrent_parquet_saves_same_filename_race_condition` fails without `PermissionError`, thread-safe unique temporary files have been implemented.
