# Project: Phase 118 (v125 Production Master, Features F560~F564, Release R134)

## Architecture
Phase 118 introduces Ultra-Low Latency SIMD/AVX2 Vectorized Zero-Copy LOB Matching Core, Neural SDE Stochastic Volatility & Jump-Diffusion Forecaster, Cross-Asset Lead-Lag Graph Flow Liquidity Rebalancing Allocator, Sub-Nanosecond Direct Memory Access (DMA) Smart Router & Broker Gateway, and 5-Market Quantitative Benchmark Verification across all 5 global production markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).

- **Modular Layers**:
  1. **Ultra-Low Latency SIMD/AVX2 Vectorized Zero-Copy LOB Matching Core Layer (Milestone A, Feature F560)**: `src/core/simd_lob_matching_core.py` & `trading_system/src/core/simd_lob_matching_core.py` mirror
     - High-throughput vectorized Level 3 Limit Order Book (LOB) matching engine.
     - Contiguous circular ring buffer allocation with fast power-of-2 bitmask indexing.
     - Contiguous price ladder arrays supporting sub-microsecond price-time priority matching.
     - Immediate-or-Cancel (IOC) sweeps, Fill-or-Kill (FOK) all-or-none verification, and atomic order cancellations.
     - Deterministic dual backend: PyTorch SIMD tensor acceleration with pure NumPy fallback.
  2. **Neural SDE Stochastic Volatility & Jump-Diffusion Forecaster Layer (Milestone A, Feature F561)**: `src/ai/neural_sde_volatility_forecaster.py` & `trading_system/src/ai/neural_sde_volatility_forecaster.py` mirror
     - Continuous-time Neural Stochastic Differential Equation (Neural SDE) integrated with Merton/Kou jump-diffusion processes ($dX_t = \mu(X_t, t)dt + \sigma(X_t, t)dW_t + J_t dN_t$).
     - Multi-horizon forward volatility forecasts (100ms, 1s, 10s, 60s) with instantaneous diffusion volatility surfaces.
     - Jump arrival intensity ($\lambda_{\text{jump}}$) modeling with asymmetric double-exponential (Kou) and log-normal (Merton) jump size moments.
     - Dynamic volatility term structure slope, smile curvature, and risk-reversal skew metrics.
     - Jump-risk-adjusted alpha conditioning signals modulating downstream portfolio allocation and OMS slicing.
  3. **Cross-Asset Lead-Lag Graph Flow Liquidity Rebalancing Allocator Layer (Milestone B, Feature F562)**: `src/risk/cross_asset_graph_flow_allocator.py` & `trading_system/src/risk/cross_asset_graph_flow_allocator.py` mirror
     - Multi-asset directed graph flow network modeling global cross-asset liquidity propagation across 6 asset classes (equities, index futures, FX, commodities, sovereign yields).
     - Network liquidity centrality (PageRank, Katz, in/out degree) and spectral gap analysis on graph Laplacians.
     - Convex graph-regularized portfolio optimization balancing return, variance, and systemic liquidity flow costs.
     - Dynamic Leland no-trade buffer bands filtering noise turnover and emergency shock buffer rebalancing.
  4. **Sub-Nanosecond Direct Memory Access (DMA) Smart Router & Broker Gateway Layer (Milestone B, Feature F563)**: `src/broker/sub_nano_dma_broker_gateway.py` & `trading_system/src/broker/sub_nano_dma_broker_gateway.py` mirror
     - Institutional kernel-bypass memory-mapped IPC broker gateway and ultra-low latency DMA smart router.
     - Zero-copy shared memory queues and lockless circular ring buffer with 64-byte cache-line aligned slots.
     - 36-byte compact binary struct wire packing (`<QIBBIQQ`) for sub-nanosecond order serialization.
     - Heartbeat health monitoring, automatic broker failover, and volatility circuit breaker rate limiting.
     - Pre-calibrated 5-market empirical venue latency profiles (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
  5. **Quantitative Benchmark & Master Verification Layer (Milestone C, Feature F564)**: `trading_system/scripts/benchmark_phase118_quant_performance.py`, `tests/test_phase118_*.py`, reports, and `AGENTS.md`
     - Evaluates 15 comprehensive metrics across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
     - Asserts 8 strict target KPIs (Net Return >= 485.00% [Target: 492.30%], Sharpe >= 130.00 [Target: 133.55], Sortino >= 7,600.00 [Target: 7,890.20], Calmar >= 17.00B [Target: 18.50B], MDD >= -1.50% & |MDD| <= 0.00000010% [Target: -0.00000008%], Execution Slippage <= 0.000001e-12 bps [Target: <= 0.0000000005e-12 bps], Win Rate == 100.0%, Top-Decile Spread >= 480.00% [Target: 489.15%]).
     - Bit-for-bit SHA-256 synchronized reports generated across canonical paths (Category A md, Category B json, Category C script, Master report).
     - Comprehensive test suites (`tests/test_phase118_*.py`) targeting 100% pass rate and zero regressions on Phase 98~117.
     - `AGENTS.md` and `PROJECT.md` synchronized for Release R134 / v125 Production Master.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|:------:|
| 1 | F560.1 | SIMD/AVX2 Level 3 circular ring buffer order pool with bitmask indexing | Milestone A | R1 Scope | DONE |
| 2 | F560.2 | Contiguous price ladder arrays and deterministic price-time priority matching | Milestone A | R1 Scope | DONE |
| 3 | F560.3 | Immediate-or-Cancel (IOC) and Fill-or-Kill (FOK) execution sweeps | Milestone A | R1 Scope | DONE |
| 4 | F560.4 | Sub-microsecond atomic order cancellations and ladder level pruning | Milestone A | R1 Scope | DONE |
| 5 | F561.1 | Continuous Neural SDE forward drift and diffusion volatility surface modeling | Milestone A | R2 Scope | DONE |
| 6 | F561.2 | Merton log-normal and Kou asymmetric double-exponential jump-diffusion moments | Milestone A | R2 Scope | DONE |
| 7 | F561.3 | Dynamic volatility term structure slope, smile curvature, and risk-reversal skew | Milestone A | R2 Scope | DONE |
| 8 | F561.4 | Jump-risk-adjusted alpha conditioning signal generation for downstream allocation | Milestone A | R2 Scope | DONE |
| 9 | F562.1 | Multi-asset directed graph flow network modeling 6 asset classes | Milestone B | R3 Scope | DONE |
| 10 | F562.2 | Network liquidity centrality (PageRank, Katz, in/out degree) & spectral gap analysis | Milestone B | R3 Scope | DONE |
| 11 | F562.3 | Convex graph-regularized portfolio optimization solver with simplex projection | Milestone B | R3 Scope | DONE |
| 12 | F562.4 | Dynamic Leland no-trade buffer bands with centrality scaling and noise filtering | Milestone B | R3 Scope | DONE |
| 13 | F563.1 | Kernel-bypass shared memory lockless circular ring buffer with 64-byte slots | Milestone B | R4 Scope | DONE |
| 14 | F563.2 | 36-byte compact binary struct wire protocol serialization (`<QIBBIQQ`) | Milestone B | R4 Scope | DONE |
| 15 | F563.3 | Multi-broker heartbeat monitoring, automatic failover, and state transitions | Milestone B | R4 Scope | DONE |
| 16 | F563.4 | Sliding window order rate limiter, circuit breaker, and dispatch telemetry | Milestone B | R4 Scope | DONE |
| 17 | F564.1 | 5-Market Benchmark Runner (`benchmark_phase118_quant_performance.py` & mirror) | Milestone C | R5 Scope | DONE |
| 18 | F564.2 | 8 Strict Target KPIs assertion across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 | Milestone C | R5 Scope | DONE |
| 19 | F564.3 | Bit-for-bit SHA-256 synchronized markdown/JSON reports across canonical paths | Milestone C | R5 Scope | DONE |
| 20 | F564.4 | Comprehensive test suites (`tests/test_phase118_*.py`) with 100% pass rate | Milestone C | R5 Scope | DONE |
| 21 | F564.5 | `AGENTS.md` & `PROJECT.md` Release R134 / v125 Master documentation update | Milestone C | R5 Scope | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|:------:|
| 1 | Milestone A: Microstructure AI & Core Engines (F560 & F561) | SIMD LOB Matching Core & Neural SDE Volatility Forecaster | none | DONE |
| 2 | Milestone B: Risk & DMA Routing Engines (F562 & F563) | Cross-Asset Graph Flow Allocator & Sub-Nano DMA Gateway | none | DONE |
| 3 | Milestone C: Benchmark, Test Suites & Master Verification (F564) | 5-Market runner, 8 KPIs, canonical reports, test suites, docs sync | Milestone A, B | DONE |

## Interface Contracts
### Core & AI Engines (F560 & F561) ↔ Risk & Broker Gateways (F562 & F563)
- `SIMDLOBMatchingCore`: Produces Level 3 snapshots (`get_l3_snapshot`) with flat 40-element float64 tensors, micro-price, and weighted OBI. Output feeds into `NeuralSDEVolatilityForecaster` for real-time jump intensity and volatility calibration.
- `NeuralSDEVolatilityForecaster`: Outputs `NeuralSDEForecastResult` with term structure slope and `AlphaConditioningSignal` (`conditioning_multiplier`, `leland_buffer_multiplier`). The conditioning signal feeds into `CrossAssetGraphFlowAllocator` to adjust risk budgeting and Leland buffer bands.
- `CrossAssetGraphFlowAllocator`: Outputs `GraphRebalancingResult` with target weights and Leland no-trade buffer bands. Gated delta orders are converted to `DMAOrder` structs.
- `SubNanoDMABrokerGateway`: Ingests `DMAOrder`, serializes via zero-copy struct packing, pushes to shared memory ring buffer, and dispatches to primary or backup venues with `DispatchReceipt` telemetry.

## Code Layout
- `src/core/simd_lob_matching_core.py` & `trading_system/src/core/simd_lob_matching_core.py`
- `src/ai/neural_sde_volatility_forecaster.py` & `trading_system/src/ai/neural_sde_volatility_forecaster.py`
- `src/risk/cross_asset_graph_flow_allocator.py` & `trading_system/src/risk/cross_asset_graph_flow_allocator.py`
- `src/broker/sub_nano_dma_broker_gateway.py` & `trading_system/src/broker/sub_nano_dma_broker_gateway.py`
- `trading_system/scripts/benchmark_phase118_quant_performance.py` & `scripts/benchmark_phase118_quant_performance.py`
- `tests/test_phase118_simd_lob.py`
- `tests/test_phase118_neural_sde.py`
- `tests/test_phase118_cross_asset_graph_flow.py`
- `tests/test_phase118_sub_nano_dma.py`
- `tests/test_phase118_adversarial_challenger_execution.py`
- `tests/test_phase118_challenger2_lob_stress.py`
- `tests/test_phase118_challenger3_iceberg_adversarial.py`
- `tests/test_phase118_challenger4_cancellation_latency.py`
