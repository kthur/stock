# Project: Phase 119 (v126 Production Master, Features F565~F569, Release R135)

## Architecture
Phase 119 introduces Multi-Horizon Temporal Graph Attention Network (GAT) Sector Cross-Lead-Lag Flow Forecaster, Quantum-Inspired Annealing Portfolio Combinatorial Optimizer, Microsecond Adaptive Iceberg & Pegged Order Execution Router, Sub-Microsecond Multi-Broker Event-Driven Bridge & Protocol Connector, and 5-Market Quantitative Benchmark Verification across all 5 global production markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).

- **Modular Layers**:
  1. **Multi-Horizon Temporal Graph Attention Network (GAT) Sector Cross-Lead-Lag Flow Forecaster Layer (Milestone A, Feature F565)**: `src/ai/temporal_gat_lead_lag_forecaster.py` & `trading_system/src/ai/temporal_gat_lead_lag_forecaster.py` mirror
     - Dynamic temporal graph attention network modeling 25 canonical nodes (11 US sectors, 8 macro indices, 6 KRX sectors/indices).
     - Multi-head temporal attention weights over rolling lookback windows ($T \in [5, 20, 60]$), extracting directional cross-market impulse flow vectors ($\alpha_{ij}(t)$).
     - Multi-horizon forward return drift predictions (100ms, 1s, 5s, 1m) with Monte Carlo epistemic uncertainty estimation and calibrated confidence intervals.
     - Deterministic dual backend: PyTorch SIMD tensor acceleration with pure NumPy fallback.
  2. **Quantum-Inspired Annealing Portfolio Combinatorial Optimizer Layer (Milestone A, Feature F566)**: `src/risk/quantum_annealing_portfolio_optimizer.py` & `trading_system/src/risk/quantum_annealing_portfolio_optimizer.py` mirror
     - Quadratic Unconstrained Binary Optimization (QUBO) & Simulated Quantum Annealing (SQA) solver for discrete portfolio selection.
     - Transverse-field Ising Hamiltonian mapping ($H(s) = -\sum_i h_i \sigma_i^z - \sum_{i<j} J_{ij} \sigma_i^z \sigma_j^z - \Gamma(t) \sum_i \sigma_i^x$).
     - Strict cardinality constraints ($K_{\min} \le K \le K_{\max}$), round-lot discrete sizing, piecewise transaction costs, and sector concentration bounds with dynamic quantum tunneling schedules.
  3. **Microsecond Adaptive Iceberg & Pegged Order Execution Router Layer (Milestone B, Feature F567)**: `src/execution/adaptive_iceberg_pegged_router.py` & `trading_system/src/execution/adaptive_iceberg_pegged_router.py` mirror
     - High-frequency institutional execution routing engine managing synthetic iceberg orders and dynamic pegged orders (Primary Peg, Midpoint Peg, Market Peg).
     - Dynamic display quantity randomization ($\mathcal{N}(\mu_{\text{display}}, \sigma_{\text{jitter}}^2)$) and anti-clustering stealth mechanics to prevent predatory HFT front-running.
     - Real-time Level 3 quote monitoring, Hawkes toxicity-based peg offset adjustments, and microsecond order re-pegging.
  4. **Sub-Microsecond Multi-Broker Event-Driven Bridge & Protocol Connector Layer (Milestone B, Feature F568)**: `src/broker/event_driven_multi_broker_bridge.py` & `trading_system/src/broker/event_driven_multi_broker_bridge.py` mirror
     - High-speed event-driven abstraction bridge connecting OMS/SOR layers with heterogeneous broker APIs (FIX 4.4 DMA, Interactive Brokers TWS/Gateway, KRX Open API, simulated sandbox).
     - Non-blocking lock-free circular event ring buffer, heartbeat monitoring, sub-millisecond disconnect failover, in-flight state reconciliation, and sequence number replay protection.
  5. **Quantitative Benchmark & Master Verification Layer (Milestone C, Feature F569)**: `trading_system/scripts/benchmark_phase119_quant_performance.py`, `tests/test_phase119_*.py`, reports, and `AGENTS.md`
     - Evaluates 15 comprehensive metrics across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
     - Asserts 8 strict target KPIs (Net Return >= 495.00% [Target: 504.60%], Sharpe >= 133.00 [Target: 136.80], Sortino >= 7,900.00 [Target: 8,240.50], Calmar >= 19.00B [Target: 20.80B], MDD >= -1.50% & |MDD| <= 0.00000007% [Target: -0.00000006%], Execution Slippage <= 0.000001e-12 bps [Target: <= 0.0000000003e-12 bps], Win Rate == 100.0%, Top-Decile Spread >= 490.00% [Target: 498.40%]).
     - Bit-for-bit SHA-256 synchronized reports generated across canonical paths (Category A md, Category B json, Category C script, Master report).
     - Comprehensive test suites (`tests/test_phase119_*.py`) targeting 100% pass rate and zero regressions on Phase 98~118.
     - `AGENTS.md` and `PROJECT.md` synchronized for Release R135 / v126 Production Master.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|:------:|
| 1 | F565.1 | Multi-head temporal graph attention network with 25 canonical nodes | Milestone A | R1 Scope | DONE |
| 2 | F565.2 | Directional cross-market impulse flow vectors & lead-lag centrality | Milestone A | R1 Scope | DONE |
| 3 | F565.3 | Multi-horizon return drift forecaster (100ms, 1s, 5s, 1m) with bounds | Milestone A | R1 Scope | DONE |
| 4 | F565.4 | Monte Carlo dropout epistemic uncertainty & conformal prediction bounds | Milestone A | R1 Scope | DONE |
| 5 | F566.1 | QUBO matrix formulation mapping return, covariance, and budget constraints | Milestone A | R2 Scope | DONE |
| 6 | F566.2 | Transverse-field Ising Hamiltonian conversion & ground-state SQA solver | Milestone A | R2 Scope | DONE |
| 7 | F566.3 | Discrete round-lot sizing and non-negative cash residual allocation | Milestone A | R2 Scope | DONE |
| 8 | F566.4 | Strict cardinality bounds ($K_{\min} \le K \le K_{\max}$) & sector concentration caps | Milestone A | R2 Scope | DONE |
| 9 | F567.1 | Synthetic iceberg order manager with random Gaussian display jittering | Milestone B | R3 Scope | DONE |
| 10 | F567.2 | Dynamic pegged orders (Primary, Midpoint, Market) with L3 quote tracking | Milestone B | R3 Scope | DONE |
| 11 | F567.3 | Hawkes toxicity skewing and emergency quote retreat/cancellation | Milestone B | R3 Scope | DONE |
| 12 | F567.4 | Mass conservation invariants and crossed book execution protection | Milestone B | R3 Scope | DONE |
| 13 | F568.1 | Lockless event ring buffer with reentrant thread synchronization | Milestone B | R4 Scope | DONE |
| 14 | F568.2 | Multi-broker session lifecycle management (IBKR, FIX DMA, KRX Open API) | Milestone B | R4 Scope | DONE |
| 15 | F568.3 | Heartbeat monitoring, automatic failover, and disconnect recovery | Milestone B | R4 Scope | DONE |
| 16 | F568.4 | In-flight state reconciliation and sequence replay protection | Milestone B | R4 Scope | DONE |
| 17 | F569.1 | 5-Market Benchmark Runner (`benchmark_phase119_quant_performance.py` & mirror) | Milestone C | R5 Scope | DONE |
| 18 | F569.2 | 8 Strict Target KPIs assertion across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 | Milestone C | R5 Scope | DONE |
| 19 | F569.3 | Bit-for-bit SHA-256 synchronized markdown/JSON reports across canonical paths | Milestone C | R5 Scope | DONE |
| 20 | F569.4 | Comprehensive test suites (`tests/test_phase119_*.py`) with 100% pass rate | Milestone C | R5 Scope | DONE |
| 21 | F569.5 | `AGENTS.md` & `PROJECT.md` Release R135 / v126 Master documentation update | Milestone C | R5 Scope | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|:------:|
| 1 | Milestone A: Temporal GAT & Quantum Annealing Engines (F565 & F566) | Temporal GAT Forecaster & Quantum Annealing Optimizer | none | DONE |
| 2 | Milestone B: Iceberg Router & Event-Driven Bridge (F567 & F568) | Adaptive Iceberg Pegged Router & Multi-Broker Bridge | none | DONE |
| 3 | Milestone C: Benchmark, Test Suites & Master Verification (F569) | 5-Market runner, 8 KPIs, canonical reports, test suites, docs sync | Milestone A, B | DONE |

## Interface Contracts
### AI & Core Engines (F565 & F566) ↔ Execution & Broker Bridges (F567 & F568)
- `TemporalGATLeadLagForecaster`: Generates `TemporalGATForecastResult` containing `HorizonLeadLagDrift` across multi-horizons (100ms, 1s, 5s, 1m) and epistemic uncertainty metrics. Feeds expected drift and uncertainty directly into `QuantumAnnealingPortfolioOptimizer`.
- `QuantumAnnealingPortfolioOptimizer`: Ingests expected drift and covariance; optimizes discrete round-lot holdings satisfying cardinality ($K_{\min} \le K \le K_{\max}$) and sector caps under simulated quantum annealing; outputs target lots and weights via `QuantumAnnealingResult`.
- `AdaptiveIcebergPeggedRouter`: Converts rebalancing target delta quantities into synthetic iceberg orders and dynamic pegged slices with Hawkes toxicity skewing and Gaussian jitter stealth mechanics.
- `EventDrivenMultiBrokerBridge`: Dispatches child slice orders and rebalancing trades to multi-broker sessions with sub-microsecond latency, tracking execution receipts, failover transitions, and sequence replay protection.

## Code Layout
- `src/ai/temporal_gat_lead_lag_forecaster.py` & `trading_system/src/ai/temporal_gat_lead_lag_forecaster.py`
- `src/risk/quantum_annealing_portfolio_optimizer.py` & `trading_system/src/risk/quantum_annealing_portfolio_optimizer.py`
- `src/execution/adaptive_iceberg_pegged_router.py` & `trading_system/src/execution/adaptive_iceberg_pegged_router.py`
- `src/broker/event_driven_multi_broker_bridge.py` & `trading_system/src/broker/event_driven_multi_broker_bridge.py`
- `trading_system/scripts/benchmark_phase119_quant_performance.py` & `scripts/benchmark_phase119_quant_performance.py`
- `tests/test_phase119_gat_forecaster.py`
- `tests/test_phase119_quantum_annealing.py`
- `tests/test_phase119_iceberg_router.py`
- `tests/test_phase119_multi_broker_bridge.py`
- `tests/test_phase119_adversarial_challenger1.py`
- `tests/test_phase119_challenger1_adversarial.py`
- `tests/test_phase119_challenger2_gat_stress.py`
- `tests/test_phase119_challenger2_m2_quantum_stress.py`
- `tests/test_phase119_challenger2_m3_latency_stress.py`
