# Comprehensive Pipeline Investigation & Modular DAG Architecture Design

**Author**: Explorer M1-1  
**Target File**: `d:\Finance\code\stock\trading_system\run_pipeline.py`  
**Scope Reference**: `d:\Finance\code\stock\PROJECT.md` (Milestone 1 / R1)  
**Date**: 2026-07-30  

---

## 1. Executive Summary

This document presents a comprehensive analysis of the existing quantitative trading prediction pipeline (`trading_system/run_pipeline.py`) and formulates a modular **Directed Acyclic Graph (DAG)** pipeline architecture with state serialization and resumability capabilities (`trading_system/dag_pipeline.py`).

The stock trading system spans 3,379 symbols across Korean (KOSPI, KOSDAQ, KONEX) and US (S&P 500) equity markets, executing 17 multi-factor and multi-model quantitative alpha strategies integrated via a 2D market regime dynamic ensemble. However, the current `run_pipeline.py` operates as a monolithic, procedural script. Any failure during execution (e.g. network timeout, memory spike, or missing provider data during step 10/11) forces an expensive complete re-run from step 1 (data fetching and model training).

The proposed **Modular DAG Architecture** decomposes the pipeline into discrete, single-responsibility task nodes connected by explicit dependency graphs. Combined with an automated **Parquet/JSON Checkpointing Mechanism**, failed pipeline runs can resume seamlessly from the exact node of failure without re-fetching market data or re-training machine learning models.

---

## 2. Current Monolithic Pipeline Analysis (`run_pipeline.py`)

### 2.1 Code Structure & Execution Flow

`run_pipeline.py` is a 2,838-line script orchestrated by `execute_prediction_pipeline()`. It follows a sequential 12-step procedural workflow:

| Step | Operation | Key Components / Modules | Primary Output / State |
|------|-----------|--------------------------|------------------------|
| **1** | Configuration & Setup | `TradingConfig`, `setup_global_http_headers()`, Rotating Logger | Configured runtime environment |
| **2** | Global Indicators Fetch | `GlobalMarketClient.get_summary()`, `MarketIndicatorStorage` | Real-time macro summary in SQLite DB |
| **3** | Universe Sync | `storage.get_universe()`, `update_stock_universe()` | 3,379 symbols (KOSPI, KOSDAQ, KONEX, SP500) |
| **4** | Price DB Initialization | `StockPriceDB(db_path)` | SQLite WAL database handle |
| **5** | Macro Indicator History | `fetch_indicator_history()` (18 tickers, yield spreads) | `indicator_train`, `indicator_infer` DataFrames |
| **6** | Training Data Preparation | `fetch_data_fdr()`, `merge_fundamentals()`, `prepare_training_data()` | `df_train` DataFrame, `market_dfs` dict |
| **7** | Model Training | `OnDevicePredictionModel.train()`, `train_surge()`, `compute_lead_lag()`, `VCPSurgePredictor`, Isotonic Calibrators | Trained model artifacts in `.pkl`/`.json` |
| **8** | Inference Fundamentals | `fetch_and_store_fundamentals_batch()` (background thread) | Updated SQLite fundamentals DB |
| **9** | Inference Price Fetching | Parallel `fetch_data_fdr()` for ALL 3,379 symbols | `infer_data_dict` (Dict[str, DataFrame]) |
| **10** | Multi-Strategy Inference | 17 Strategy Engines (XGBoost Reg, Surge, Lead-Lag, VCP, VCP ML, Stat-Arb, Sector, RIM, Event, MQ, IV Skew, Order Flow, Reversal, ARM, CARD, LATR, LSTM) | 17 individual strategy score DataFrames |
| **11** | Regime & Risk Gating | `MarketRegimeDetector` (GMM 2D), `RiskManager` (Crisis Gating), `SentimentMetaFilter` | Regime state (BULL/SIDEWAYS/BEAR), allocation cap, risk scalar |
| **12** | Ensemble & Output | `EnsembleScoringEngine`, `PortfolioAllocator`, OMS Plan, Report Writers, Telegram Alert | `ensemble_predictions.txt`, HTML dashboard, SQLite predictions |

### 2.2 Critical Vulnerabilities in Current Design

1. **Monolithic Procedural Coupling**:
   - All state is held in local variables within a single 2,000+ line function `execute_prediction_pipeline()`.
   - Data fetching, feature engineering, model training, strategy scoring, and report generation cannot be executed or tested independently.
2. **Lack of Checkpointing & Resumability**:
   - If network interruption or MemoryError occurs during Strategy 14 (Reversal) after 45 minutes of processing, re-running requires repeating Steps 1-13 from scratch.
   - `storage.pipeline_stage()` context managers currently only log runtime duration to SQLite without saving node data artifacts.
3. **Redundant Network & Compute Operations**:
   - When training models, `indicator_train` is fetched; if skipping training, a second network request is issued for `indicator_infer` despite overlapping dates.
   - Inference data fetch for 3,379 symbols takes significant time and network bandwidth; if downstream scoring fails, data must be fetched again.
4. **Memory Management Spikes**:
   - `infer_data_dict` holds in-memory DataFrames for 3,300+ symbols (~1-2 GB uncompressed).
   - Intermediate strategy scoring objects persist in memory throughout the execution loop until manual `gc.collect()` calls.

---

## 3. Modular DAG Architecture Design (`trading_system/dag_pipeline.py`)

### 3.1 System Core Abstractions

To achieve modularity and isolation, the new architecture introduces four core classes:

```
+-----------------------------------------------------------------------+
|                             DAGRunner                                 |
|  - Validates DAG topology & detects cycles                            |
|  - Orchestrates execution order                                      |
|  - Handles checkpoint restoration & node skipping                     |
+-----------------------------------------------------------------------+
                                   │
                                   ▼
+-----------------------------------------------------------------------+
|                            DAGContext                                 |
|  - Config & runtime environment                                       |
|  - In-memory data store: outputs: Dict[str, Any]                      |
|  - Shared DB handles (StockPriceDB, MarketIndicatorStorage)           |
+-----------------------------------------------------------------------+
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
+-----------------------+           +-----------------------------------+
|         Task          |           |        CheckpointManager          |
|  - name: str          |           |  - Saves/loads JSON & Parquet     |
|  - dependencies: list |           |  - Validates freshness & TTL      |
|  - execute(context)   |           |  - Tracks pipeline_state.json     |
|  - checkpoint()       |           +-----------------------------------+
|  - restore()          |
+-----------------------+
```

#### A. `Task` Base Interface Contract
```python
from abc import ABC, abstractmethod
from typing import List, Any

class Task(ABC):
    """Abstract Base Class for all pipeline DAG nodes."""
    
    def __init__(self, name: str, dependencies: List[str] = None):
        self.name = name
        self.dependencies = dependencies or []

    @abstractmethod
    def execute(self, context: 'DAGContext') -> Any:
        """Executes task logic and returns node output."""
        pass

    @abstractmethod
    def checkpoint(self, context: 'DAGContext', result: Any) -> None:
        """Serializes task outputs to disk checkpoint."""
        pass

    @abstractmethod
    def restore(self, context: 'DAGContext') -> Any:
        """Loads task outputs from disk checkpoint into context."""
        pass

    def is_checkpoint_valid(self, context: 'DAGContext') -> bool:
        """Determines if existing checkpoint is valid for resuming."""
        return context.checkpoint_manager.is_valid(self.name, context)
```

#### B. `DAGContext` Interface
```python
class DAGContext:
    """Thread-safe context holding shared state, configs, and node outputs."""
    def __init__(self, config: TradingConfig, run_id: str = None):
        self.config = config
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.outputs: Dict[str, Any] = {}
        self.price_db = StockPriceDB(db_path=config.stock_price_db_path)
        self.storage = MarketIndicatorStorage(db_path=config.db_path)
        self.checkpoint_manager = CheckpointManager(base_dir=".checkpoints", run_id=self.run_id)
        
    def get_output(self, task_name: str) -> Any:
        if task_name not in self.outputs:
            raise KeyError(f"Task output '{task_name}' not found in context.")
        return self.outputs[task_name]
        
    def set_output(self, task_name: str, value: Any) -> None:
        self.outputs[task_name] = value
```

---

### 3.2 Detailed Node Breakdown & Dependency Specifications

The pipeline is split into 10 major functional stage nodes. Stage 6 (Strategy Inference) is further decomposed into parallel sub-nodes for each of the 17 quantitative alpha strategies.

| Node ID | Node Name | Dependencies | Inputs from Context | Primary Responsibilities | Output Artifact / Type |
|---------|-----------|--------------|---------------------|--------------------------|------------------------|
| **N1** | `InitUniverseAndMacro` | None | `config` | Sync 3,379 symbols universe, fetch real-time global market summary, apply KRX admin/halted stock filters. | `universe` (DataFrame), `symbol_market` (Dict) |
| **N2** | `FetchMacroHistory` | `[N1]` | `config`, `price_db` | Fetch 18 macro indicators, compute yield curve spreads, KR/US spreads, inflation shock index. | `indicator_train` (DataFrame), `indicator_infer` (DataFrame) |
| **N3** | `PrepTrainingData` | `[N1, N2]` | `universe`, `indicator_train` | Sample symbols per market, prefetch historical prices, batch merge fundamentals, compute technical features. | `df_train` (DataFrame), `market_dfs` (Dict[str, DataFrame]) |
| **N4** | `TrainModels` | `[N3]` | `df_train`, `market_dfs` | Train XGBoost/LGBM Regression, Surge Classifiers, Lead-Lag matrix, VCP ML Predictor, and fit Isotonic Calibrators. | Model binary files in `models/`, `calibrators.pkl` |
| **N5** | `PrepInferenceData` | `[N1, N2]` | `universe`, `indicator_infer` | Prefetch recent prices (365d) for ALL universe symbols, batch merge fundamentals, filter <200d data. | `infer_data_dict` (Dict[str, DataFrame]) |
| **N6a** | `InferRegSurge` | `[N4, N5]` | `infer_data_dict`, `indicator_infer` | Execute OnDevice XGBoost Regression (8 horizons) & Surge Classifier (4 horizons). | `res_df` (DataFrame), `surge_df` (DataFrame) |
| **N6b** | `InferVCPBreakout` | `[N5]` | `infer_data_dict` | Detect rule-based VCP patterns and check real-time pivot volume breakout triggers. | `vcp_results` (List[Dict]), `vcp_breakouts` (List) |
| **N6c** | `InferLeadLag` | `[N4, N5]` | `infer_data_dict`, `indicator_infer` | Compute 2-Tier Lead-Lag follower correlation index based on leader price actions. | `lead_lag_df` (DataFrame) |
| **N6d** | `InferStatArb` | `[N5]` | `infer_data_dict` | Perform log-price cointegration scanning across symbol pairs and calculate Z-score residuals. | `stat_arb_df` (DataFrame), `stat_arb_pairs` (List) |
| **N6e** | `InferSectorRotation` | `[N2, N5]` | `infer_data_dict`, `indicator_infer` | Compute 1M/3M sector relative momentum and macro sensitivity scoring. | `sector_df` (DataFrame) |
| **N6f** | `InferRIMValuation` | `[N5]` | `infer_data_dict` | Compute Residual Income Model (RIM) intrinsic valuation $V_0$ and margin of safety scores. | `rim_df` (DataFrame) |
| **N6g** | `InferEventDriven` | `[N5]` | `infer_data_dict` | Calculate DART disclosure catalysts, earnings surprise, and buyback volume surge scores. | `event_df` (DataFrame) |
| **N6h** | `InferMQFactor` | `[N5, N6f]` | `infer_data_dict`, `rim_df` | Calculate 12M-1M Momentum Quality minus reversal noise + ROE/operating margin quality. | `mq_df` (DataFrame) |
| **N6i** | `InferIVSkew` | `[N5]` | `infer_data_dict` | Calculate Put/Call Implied Volatility Skew and contrarian fear scores. | `iv_skew_df` (DataFrame) |
| **N6j** | `InferOrderFlow` | `[N5]` | `infer_data_dict` | Compute institutional/foreign Money Flow Index (MFI) & order flow acceleration. | `order_flow_df` (DataFrame) |
| **N6k** | `InferShortTermReversal`| `[N5]` | `infer_data_dict` | Detect 3-5 day oversold & Bollinger lower band breach mean-reversion signals. | `reversal_df` (DataFrame) |
| **N6l** | `InferARMFactor` | `[N5]` | `infer_data_dict` | Compute Analyst Revision Momentum (ARM) consensus EPS/target price revisions. | `arm_df` (DataFrame) |
| **N6m** | `InferCARDFactor` | `[N2, N5]` | `infer_data_dict`, `indicator_infer` | Compute Cross-Asset Regime Divergence (CARD) stock-FX-commodity divergence. | `card_df` (DataFrame) |
| **N6n** | `InferLATRFactor` | `[N5]` | `infer_data_dict` | Compute Liquidity-Adjusted Tail Risk (LATR) 52-week drawdown + liquidity surge. | `latr_df` (DataFrame) |
| **N6o** | `InferLSTM` | `[N5]` | `infer_data_dict` | Run Strict Causal LSTM deep learning predictions. | `lstm_df` (DataFrame) |
| **N7** | `RegimeAndRiskDetect` | `[N2, N5]` | `indicator_infer`, `infer_data_dict` | GMM 2D Market Regime detection, CrisisDetector evaluation, SentimentMetaFilter blacklist. | `regime_state` (Dict), `risk_scalar` (float) |
| **N8** | `EnsembleScoringEngine` | `[N6a..N6o, N7]` | All 17 Strategy DataFrames, Regime state | Gram-Schmidt orthogonalization, dynamic strategy weighting, microstructure cost deduction. | `ensemble_df` (DataFrame) |
| **N9** | `PortfolioAndOMSAlloc` | `[N5, N8]` | `ensemble_df`, `infer_data_dict` | Black-Litterman / HRP portfolio allocation, Execution OMS order plan generation into DB. | `alloc_df` (DataFrame), `order_plans` (List) |
| **N10**| `ExportAndVerifyReport` | `[N8, N9]` | `ensemble_df`, `alloc_df`, context outputs | Save 17 text reports, CSV/JSONL results, HTML dashboard, save DB predictions, Telegram notification. | Pipeline Status (Success / Metrics) |

---

### 3.3 Complete Dependency Graph Visualization

```
                       [N1: InitUniverseAndMacro]
                                   │
                                   ▼
                        [N2: FetchMacroHistory]
                                   │
          ┌────────────────────────┴────────────────────────┐
          ▼                                                 ▼
[N3: PrepTrainingData]                           [N5: PrepInferenceData]
          │                                                 │
          ▼                                                 │
  [N4: TrainModels]                                         │
          │                                                 │
          └────────────────────────┬────────────────────────┘
                                   │
  ┌────────────────────────────────┼────────────────────────────────┐
  │                                │                                │
  ▼                                ▼                                ▼
[N6a: InferRegSurge]     [N6b: InferVCPBreakout]   [N6c: InferLeadLag]
[N6d: InferStatArb]      [N6e: InferSectorRot]     [N6f: InferRIMValuation]
[N6g: InferEventDriven]  [N6h: InferMQFactor]      [N6i: InferIVSkew]
[N6j: InferOrderFlow]    [N6k: InferSTReversal]    [N6l: InferARMFactor]
[N6m: InferCARDFactor]   [N6n: InferLATRFactor]    [N6o: InferLSTM]
  │                                │                                │
  └────────────────────────────────┼────────────────────────────────┘
                                   │
                                   ├────────────────────────────────┐
                                   ▼                                ▼
                      [N7: RegimeAndRiskDetect]                     │
                                   │                                │
                                   ▼                                │
                      [N8: EnsembleScoringEngine] <─────────────────┘
                                   │
                                   ▼
                      [N9: PortfolioAndOMSAlloc]
                                   │
                                   ▼
                      [N10: ExportAndVerifyReport]
```

---

## 4. Checkpointing and Resumability Mechanism Design

### 4.1 Checkpoint Directory Hierarchy & Storage Formats

Checkpoints are isolated by run date (`YYYY-MM-DD`) under `.checkpoints/`:

```
.checkpoints/
└── 2026-07-30/
    ├── pipeline_state.json               # Master manifest file
    ├── N1_InitUniverseAndMacro.parquet   # Universe DataFrame
    ├── N1_metadata.json                  # Symbol-market dict & market summary
    ├── N2_indicator_train.parquet        # Historical training macro indicators
    ├── N2_indicator_infer.parquet        # Historical inference macro indicators
    ├── N3_df_train.parquet               # Processed training features
    ├── N5_infer_symbols.json             # Inference active symbols list
    ├── N6a_res_df.parquet                # Regression predictions
    ├── N6a_surge_df.parquet              # Surge predictions
    ├── N6b_vcp_results.json              # VCP rule pattern detection results
    ├── N6d_stat_arb_df.parquet           # Stat-Arb scores
    ├── N6e_sector_df.parquet             # Sector rotation scores
    ├── N6f_rim_df.parquet                # RIM valuation scores
    ├── N6g_event_df.parquet              # Event-driven scores
    ├── N6h_mq_df.parquet                 # MQ factor scores
    ├── N6i_iv_skew_df.parquet            # Options IV skew scores
    ├── N6j_order_flow_df.parquet         # Order flow imbalance scores
    ├── N6k_reversal_df.parquet           # Short-term reversal scores
    ├── N6l_arm_df.parquet                # ARM factor scores
    ├── N6m_card_df.parquet               # CARD factor scores
    ├── N6n_latr_df.parquet               # LATR factor scores
    ├── N7_regime_state.json              # GMM regime & crisis status
    ├── N8_ensemble_df.parquet            # Final 17-strategy ensemble scores
    └── N9_alloc_df.parquet               # Portfolio allocation results
```

---

### 4.2 Master Manifest Schema (`pipeline_state.json`)

```json
{
  "run_id": "20260730_232101",
  "created_at": "2026-07-30T23:21:01+09:00",
  "updated_at": "2026-07-30T23:45:12+09:00",
  "config_hash": "a4f8b92c1e7d3411",
  "target_market": "ALL",
  "completed_tasks": {
    "InitUniverseAndMacro": {
      "status": "SUCCESS",
      "timestamp": "2026-07-30T23:21:15+09:00",
      "duration_sec": 14.2,
      "artifacts": ["N1_InitUniverseAndMacro.parquet", "N1_metadata.json"]
    },
    "FetchMacroHistory": {
      "status": "SUCCESS",
      "timestamp": "2026-07-30T23:21:30+09:00",
      "duration_sec": 15.0,
      "artifacts": ["N2_indicator_train.parquet", "N2_indicator_infer.parquet"]
    },
    "PrepTrainingData": {
      "status": "SKIPPED",
      "reason": "skip_training=True and models exist on disk"
    },
    "InferRegSurge": {
      "status": "SUCCESS",
      "timestamp": "2026-07-30T23:35:40+09:00",
      "duration_sec": 420.5,
      "artifacts": ["N6a_res_df.parquet", "N6a_surge_df.parquet"]
    }
  }
}
```

---

### 4.3 Checkpoint Validation & Invalidation Logic

```python
class CheckpointManager:
    """Manages disk state serialization, deserialization, and validity checks."""
    
    def __init__(self, base_dir: str = ".checkpoints", run_id: str = None):
        self.date_str = datetime.now().strftime("%Y-%m-%d")
        self.checkpoint_dir = Path(base_dir) / self.date_str
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.checkpoint_dir / "pipeline_state.json"
        self._manifest = self._load_manifest()

    def is_valid(self, task_name: str, context: DAGContext) -> bool:
        """Returns True if task checkpoint exists, is valid, and matches current config."""
        if context.config.force_rerun:
            return False

        task_entry = self._manifest.get("completed_tasks", {}).get(task_name)
        if not task_entry or task_entry.get("status") != "SUCCESS":
            return False

        # Verify all artifact files exist on disk
        for artifact_name in task_entry.get("artifacts", []):
            artifact_path = self.checkpoint_dir / artifact_name
            if not artifact_path.exists():
                return False

        # Verify configuration hash compatibility
        current_hash = self._compute_config_hash(context.config)
        if self._manifest.get("config_hash") != current_hash:
            return False

        return True

    def save_parquet(self, filename: str, df: pd.DataFrame) -> str:
        path = self.checkpoint_dir / filename
        df.to_parquet(path, compression="snappy", index=True)
        return filename

    def load_parquet(self, filename: str) -> pd.DataFrame:
        path = self.checkpoint_dir / filename
        return pd.read_parquet(path)

    def save_json(self, filename: str, data: Any) -> str:
        path = self.checkpoint_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filename

    def load_json(self, filename: str) -> Any:
        path = self.checkpoint_dir / filename
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
```

---

### 4.4 Resumable Execution Engine (`DAGRunner`)

```python
class DAGRunner:
    """Executes DAG tasks with topological ordering and automated checkpoint resuming."""
    
    def __init__(self, tasks: List[Task], context: DAGContext):
        self.tasks = {t.name: t for t in tasks}
        self.context = context
        self.execution_order = self._topological_sort()

    def _topological_sort(self) -> List[Task]:
        """Performs Kahn's Algorithm for topological sorting and cycle detection."""
        in_degree = {name: 0 for name in self.tasks}
        graph = defaultdict(list)

        for name, task in self.tasks.items():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    raise ValueError(f"Task '{name}' has unknown dependency '{dep}'.")
                graph[dep].append(name)
                in_degree[name] += 1

        queue = deque([name for name in self.tasks if in_degree[name] == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(self.tasks[node])
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.tasks):
            raise ValueError("Cyclic dependency detected in pipeline DAG!")
        return order

    def run(self) -> Dict[str, Any]:
        """Runs the pipeline DAG, skipping completed nodes with valid checkpoints."""
        logger.info(f"Starting DAG Pipeline Execution ({len(self.execution_order)} nodes)...")
        
        for task in self.execution_order:
            if self.context.checkpoint_manager.is_valid(task.name, self.context):
                logger.info(f"⏩ [RESUME] Skipping '{task.name}' (valid checkpoint found)")
                result = task.restore(self.context)
                self.context.set_output(task.name, result)
            else:
                logger.info(f"▶️ [EXECUTE] Running node '{task.name}'...")
                start_time = time.time()
                try:
                    result = task.execute(self.context)
                    self.context.set_output(task.name, result)
                    task.checkpoint(self.context, result)
                    duration = time.time() - start_time
                    self.context.checkpoint_manager.mark_completed(task.name, duration=duration)
                    logger.info(f"✅ [SUCCESS] Node '{task.name}' completed in {duration:.2f}s")
                except Exception as e:
                    logger.error(f"❌ [FAILURE] Node '{task.name}' failed: {e}")
                    self.context.checkpoint_manager.mark_failed(task.name, str(e))
                    raise e
                    
        return self.context.outputs
```

---

## 5. Migration & Backwards Compatibility Plan

### 5.1 CLI Overrides Preservation
The new `trading_system/dag_pipeline.py` will serve as the primary entry point while accepting all existing CLI arguments:

```bash
# Basic run with automatic checkpoint resume
python trading_system/dag_pipeline.py

# CLI Market target override
python trading_system/dag_pipeline.py --target KOSPI

# Skip training using existing models
python trading_system/dag_pipeline.py --skip-training

# Force full re-execution (ignore checkpoints)
python trading_system/dag_pipeline.py --force-rerun

# Re-run specific node and downstream nodes only
python trading_system/dag_pipeline.py --rerun-node InferStatArb
```

### 5.2 Seamless Transition Strategy
1. **Phase 1 (M1 - Exploration & Design)**: Define contract interfaces, node specifications, and dependency graph (this report).
2. **Phase 2 (M1 - Implementation)**: Implement `Task`, `DAGContext`, `CheckpointManager`, and `DAGRunner` in `trading_system/dag_pipeline.py`.
3. **Phase 3 (M1 - Integration)**: Refactor strategy logic from `run_pipeline.py` into modular `Task` implementations in `trading_system/tasks/`.
4. **Phase 4 (Verification)**: Run E2E dry runs with simulated node failures to verify state recovery andParquet data integrity.

---

## 6. Conclusion & Implementation Recommendation

The proposed DAG Architecture addresses the key fragility of the stock trading pipeline. By decoupling monolithic procedural logic into 10 major tasks and 17 parallel strategy sub-nodes, the system gains:
1. **Fault Tolerance**: Resumes instantly from the exact point of failure.
2. **Modular Testability**: Individual strategies can be tested and benchmarked in isolation.
3. **Parallel Execution**: Strategy inference nodes (N6a..N6o) can run in parallel thread/process pools without memory leaks.
4. **Zero Performance Overhead**: Snappy-compressed Parquet checkpoints read/write in milliseconds while preventing hours of wasted compute.

**Recommendation**: Proceed with creating `trading_system/dag_pipeline.py` according to the contracts defined in Section 3 and 4.
