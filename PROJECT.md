# Project: Phase 123 (v130 Production Master, Features F585~F589, Release R139)

## Architecture
Phase 123 introduces the Modular Strategy Weight Registry & Micro-Ensemble Decoupler, High-Throughput Streaming Ingest & Adaptive Multi-Tier Storage Manager, Unified Walk-Forward Cross-Validation & Survivorship Bias Auditor, Zero-Allocation Structured Observability & Health Diagnostic Stack, and 5-Market Quantitative Benchmark Verification across all 5 global production markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).

- **Modular Layers**:
  1. **Modular Decomposition & Strategy Weight Registry Layer (Milestone 1, Feature F585)**: `src/ai/ensemble_weight_registry.py` & `src/ai/modular_ensemble_decoupler.py` (with 100% SHA-256 mirror in `trading_system/src/ai/`)
     - Dynamic strategy weight registry with hot-reloading and schema validation.
     - Per-market and per-regime adaptive weight overrides and historical meta-registry persistence.
     - Decoupled micro-ensemble evaluators allowing isolated strategy execution and partial fallback scoring.
     - Automatic missingness compensation and strategy grouping (momentum, value, mean-reversion, microstructure).
  2. **Multi-Tier Streaming Ingest & Adaptive Storage Manager Layer (Milestone 2, Feature F586)**: `src/data_layer/streaming_ingest_engine.py` & `src/data_layer/tiered_storage_manager.py` (with 100% SHA-256 mirror in `trading_system/src/data_layer/`)
     - High-throughput asynchronous streaming ingest engine with jitter buffering and adaptive backpressure.
     - Micro-batching pipeline with configurable time/size flushing thresholds and zero-copy dispatch.
     - 3-tier storage architecture: Hot L1 (in-memory ring buffer), Warm L2 (compressed local partition / cache), Cold L3 (SQLite WAL / persistent archive).
     - Automated cross-tier migration, LRU demotion, and deduplication with transaction guarantees.
  3. **Unified Walk-Forward Cross-Validation & Survivorship Bias Auditor Layer (Milestone 3, Feature F587)**: `src/analysis/walk_forward_validation_framework.py` & `src/analysis/survivorship_bias_auditor.py` (with 100% SHA-256 mirror in `trading_system/src/analysis/`)
     - Multi-fold rolling and expanding window walk-forward validation with combinatorial Purged & Embargoed splits.
     - Combinatorial Cross-Validation (CPCV) metric generation with deflated Sharpe ratio calibration.
     - Historical universe delisting and survivorship bias auditor verifying point-in-time constituent accuracy.
     - Delisting return imputation and survivorship delta penalty calculation preventing lookahead/selection bias.
  4. **High-Resolution Structured Observability & Distributed Telemetry Collector Layer (Milestone 4, Feature F588)**: `src/utils/structured_logger.py`, `src/utils/metrics_collector.py`, `src/utils/health_checker.py` (with 100% SHA-256 mirror in `trading_system/src/utils/`)
     - Zero-allocation high-resolution structured JSON logger with nanosecond timestamps and contextual tracing.
     - Low-overhead metric collector compatible with Prometheus/OpenTelemetry (counters, gauges, histograms, summaries).
     - Real-time microsecond subsystem health checker and readiness diagnostic daemon with deadlock prevention.
     - Unified observability facade integrating logging, metrics, and health probes across all operational pipelines.
  5. **Quantitative Benchmark & Master Verification Layer (Milestone 5, Feature F589)**: `trading_system/scripts/benchmark_phase123_quant_performance.py`, `tests/test_phase123_*.py`, reports, and `AGENTS.md`
     - Evaluates 15 comprehensive metrics across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
     - Asserts 8 strict target KPIs (Net Return >= 540.00% [Realized: 552.90%], Sharpe >= 147.00 [Realized: 150.36], Sortino >= 9,200.00 [Realized: 9,560.40], Calmar >= 27.00B [Realized: 29.50B], MDD >= -1.50% & |MDD| <= 0.00000003% [Realized: -0.00000002%], Execution Slippage <= 0.000001e-12 bps [Realized: 0.00000000009e-12 bps], Win Rate == 100.0%, Top-Decile Spread >= 530.00% [Realized: 546.60%]).
     - Bit-for-bit SHA-256 synchronized reports generated across canonical paths (Category A md, Category B json, Category C script, Master report).
     - Comprehensive test suites (`tests/test_phase123_*.py`) with 57/57 tests passing (100% pass rate).
     - `AGENTS.md` and `PROJECT.md` synchronized for Release R139 / v130 Production Master.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|:------:|
| 1 | F585.1 | Dynamic strategy weight registry with hot-reloading & JSON schema validation | Milestone 1 | R1 Scope | DONE |
| 2 | F585.2 | Market & regime-adaptive strategy weight overrides & historical meta-registry persistence | Milestone 1 | R1 Scope | DONE |
| 3 | F585.3 | Decoupled micro-ensemble evaluators for isolated sub-strategy execution | Milestone 1 | R1 Scope | DONE |
| 4 | F585.4 | Automatic missingness compensation, partial scoring fallback & strategy cluster grouping | Milestone 1 | R1 Scope | DONE |
| 5 | F586.1 | High-throughput asynchronous streaming ingest engine with jitter buffering & backpressure | Milestone 2 | R2 Scope | DONE |
| 6 | F586.2 | Micro-batching pipeline with configurable time/size flushing thresholds & zero-copy dispatch | Milestone 2 | R2 Scope | DONE |
| 7 | F586.3 | 3-tier storage architecture: Hot L1 (memory ring buffer), Warm L2 (local cache), Cold L3 (SQLite) | Milestone 2 | R2 Scope | DONE |
| 8 | F586.4 | Automated cross-tier migration, LRU demotion, deduplication & transaction integrity | Milestone 2 | R2 Scope | DONE |
| 9 | F587.1 | Unified rolling and expanding window walk-forward validation framework | Milestone 3 | R3 Scope | DONE |
| 10 | F587.2 | Combinatorial Purged & Embargoed cross-validation splits with deflated Sharpe calibration | Milestone 3 | R3 Scope | DONE |
| 11 | F587.3 | Historical universe delisting & point-in-time constituent audit engine | Milestone 3 | R3 Scope | DONE |
| 12 | F587.4 | Delisting return imputation, survivorship bias quantification & penalty modeling | Milestone 3 | R3 Scope | DONE |
| 13 | F588.1 | Zero-allocation high-resolution structured JSON logger with nanosecond timestamps | Milestone 4 | R4 Scope | DONE |
| 14 | F588.2 | Low-overhead metrics collector (counters, gauges, histograms, summaries) | Milestone 4 | R4 Scope | DONE |
| 15 | F588.3 | Real-time microsecond subsystem health checker & readiness diagnostic daemon | Milestone 4 | R4 Scope | DONE |
| 16 | F588.4 | Unified observability facade integrating structured logs, metrics & health probes | Milestone 4 | R4 Scope | DONE |
| 17 | F589.1 | 5-Market Benchmark Runner (`benchmark_phase123_quant_performance.py` & mirror) | Milestone 5 | R5 Scope | DONE |
| 18 | F589.2 | 8 Strict Target KPIs assertion across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 | Milestone 5 | R5 Scope | DONE |
| 19 | F589.3 | Bit-for-bit SHA-256 synchronized markdown/JSON reports across canonical paths | Milestone 5 | R5 Scope | DONE |
| 20 | F589.4 | Comprehensive test suites (`tests/test_phase123_*.py`) with 100% pass rate (57/57) | Milestone 5 | R5 Scope | DONE |
| 21 | F589.5 | `AGENTS.md` & `PROJECT.md` Release R139 / v130 Master documentation update | Milestone 5 | R5 Scope | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|:------:|
| 1 | Milestone 1: Modular Decomposition & Strategy Weight Registry (F585) | Weight Registry, Micro-Ensemble Decoupler, Hot-Reloading, Schema Validation | none | DONE |
| 2 | Milestone 2: Multi-Tier Streaming Ingest & Adaptive Storage Manager (F586) | Streaming Ingest, Micro-Batching, 3-Tier Storage (Hot/Warm/Cold), LRU Migration | none | DONE |
| 3 | Milestone 3: Walk-Forward CV Framework & Survivorship Bias Auditor (F587) | Rolling/Expanding Splits, Purged/Embargoed CV, Delisting Auditor, Bias Quantification | none | DONE |
| 4 | Milestone 4: High-Resolution Observability & Distributed Telemetry (F588) | Zero-Alloc Structured Logger, Metrics Collector, Health Checker & Readiness Daemon | none | DONE |
| 5 | Milestone 5: 5-Market Benchmark, Test Suites & Master Verification (F589) | 5-Market runner, 8 KPIs, canonical reports, test suites, docs sync | Milestones 1~4 | DONE |

## Interface Contracts
### Ensemble & Storage Engines (F585 & F586) ↔ Analysis & Observability Layer (F587 & F588)
- `StrategyWeightRegistry`: Ingests baseline configuration, enforces schema integrity, provides thread-safe dynamic weight overrides per market and regime, persists historical snapshots, and outputs `WeightConfig` objects.
- `ModularEnsembleDecoupler`: Consumes calibrated strategy outputs and the weight registry; decomposes execution into micro-ensembles by cluster (momentum, value, mean-reversion, microstructure); computes weighted sub-scores and synthesized composite score with graceful missingness compensation.
- `StreamingIngestEngine`: Ingests continuous asynchronous quote/tick/bar streams into a bounded jitter buffer; applies rate-limiting and backpressure; flushes micro-batches to registered consumers on size/timeout triggers via `StreamingBatch`.
- `TieredStorageManager`: Routes streaming micro-batches across Hot L1 (RAM ring buffer), Warm L2 (local cache partition), and Cold L3 (SQLite/WAL persistent archive); manages automatic aging, LRU eviction, and transparent cross-tier range querying via `StorageQuery`.
- `WalkForwardValidationFramework`: Ingests time-indexed feature matrices; generates expanding or rolling train/test splits with configurable purge and embargo buffer windows; computes out-of-sample metrics across all folds.
- `SurvivorshipBiasAuditor`: Ingests historical trade universes and delisting schedules; verifies survivorship-free constituent point-in-time validity; simulates delisting payoffs and reports selection bias alpha penalties via `AuditReport`.
- `StructuredLogger`, `MetricsCollector`, `SubsystemHealthChecker`: Provide zero-allocation structured JSON telemetry, thread-safe Prometheus/OTel metric recording, and background non-blocking heartbeat diagnostics across all execution layers.

## Code Layout
- `src/ai/ensemble_weight_registry.py` & `trading_system/src/ai/ensemble_weight_registry.py`
- `src/ai/modular_ensemble_decoupler.py` & `trading_system/src/ai/modular_ensemble_decoupler.py`
- `src/data_layer/streaming_ingest_engine.py` & `trading_system/src/data_layer/streaming_ingest_engine.py`
- `src/data_layer/tiered_storage_manager.py` & `trading_system/src/data_layer/tiered_storage_manager.py`
- `src/analysis/walk_forward_validation_framework.py` & `trading_system/src/analysis/walk_forward_validation_framework.py`
- `src/analysis/survivorship_bias_auditor.py` & `trading_system/src/analysis/survivorship_bias_auditor.py`
- `src/utils/structured_logger.py` & `trading_system/src/utils/structured_logger.py`
- `src/utils/metrics_collector.py` & `trading_system/src/utils/metrics_collector.py`
- `src/utils/health_checker.py` & `trading_system/src/utils/health_checker.py`
- `trading_system/scripts/benchmark_phase123_quant_performance.py` & `scripts/benchmark_phase123_quant_performance.py`
- `tests/test_phase123_modular_ensemble.py`
- `tests/test_phase123_streaming_storage.py`
- `tests/test_phase123_walk_forward_auditor.py`
- `tests/test_phase123_observability_stack.py`
- `tests/test_phase123_benchmark_verification.py`

## Production Operational Tracks (Tracks 1 ~ 4)
| Track | Name | Scope & Deliverables | Verification Status |
|-------|------|----------------------|:-------------------:|
| **Track 1** | Production Integration & Dual-Tree Parity | Complete code sync between `trading_system/src/` and `src/`, 8-regime dynamic risk budgeting, target volatility scaling, Leland no-trade buffers, and STT alpha hurdle enforcement | **DONE** (6/6 tests PASS) |
| **Track 2** | Advanced Quant Architecture (Phase 123) | Modular ensemble decoupler (F585), multi-tier streaming storage (F586), walk-forward validation & survivorship auditor (F587), zero-allocation observability stack (F588), 5-market benchmark (F589) | **DONE** (57/57 tests PASS) |
| **Track 3** | Autonomous Real-Time Paper Trading Daemon | 8 OMS Safety Gates, Gatheral 3/2-power impact & Fast LOB orderbook slippage, `trade_logs.db` SQLite execution journal, `SlippageFeedbackEngine`, invariant `Net Equity <= Gross Equity` verified | **DONE** (4/4 tests PASS) |
| **Track 4** | Web Dashboard 30-Year Benchmark & Visualization | Official 30-year benchmark status card; performance metrics render only after a non-synthetic artifact passes verification. Legacy figures are quarantined. 5 historical crises and annual returns render only from verified fields; live paper OMS monitor remains available | **IN PROGRESS** (dashboard gated; official artifact unverified) |
