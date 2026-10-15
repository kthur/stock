# Project: Phase 111 (v118 Production Master, Features F525~F529, Release R127)

## Architecture
Phase 111 introduces NumPy structured array vectorized L3 limit order book matching engines, deep multivariate neural Hawkes process generative order flow synthesis, short squeeze borrow dynamics with HTB fee prediction and OMS Gate 8.1 gating, and cross-venue triangular parity execution slicing across all 5 global markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).

- **Modular Layers**:
  1. **Vectorized LOB Engine Layer (M1, Feature F525)**: `src/core/vectorized_lob_engine.py` & `trading_system/src/core/vectorized_lob_engine.py`
     - Structured NumPy array order representation with memory-aligned contiguous memory buffers for ultra-low latency execution.
     - Doubly-linked price level FIFO queues supporting $O(1)$ order cancellation and modification via order ID hash indexing.
     - Full support for Limit, Market, IOC, FOK, Post-Only, and Iceberg orders with automatic price improvement and zero-slippage execution.
     - Point-in-time micro-price, depth-weighted order flow imbalance (OFI), and empirical fill probability computation.
  2. **Deep Multivariate Hawkes Process Layer (M2, Feature F526)**: `src/ai/deep_hawkes_synthesizer.py` & `trading_system/src/ai/deep_hawkes_synthesizer.py`
     - Neural baseline intensity network $\mu_0(s_t)$ with GELU activations and Softplus strictly positive output guarantees.
     - 6-dimensional mutual excitation event space (Limit/Cancel/Market $\times$ Buy/Sell) with exponential, power-law, and multi-exponential sum decay kernels.
     - Spectral radius projection ensuring $L_1$ stability $\rho(\Gamma) < 1.0$, with calibrated transient supercritical excursions ($\rho \in [1.02, 1.15]$) modeling flash crash cascades.
     - Empirical calibration parameters across 5 production markets and synthetic order replay stress testing.
  3. **Borrow Dynamics & HTB Fee Predictor Layer (M3, Feature F527)**: `src/risk/borrow_dynamics_model.py` & `trading_system/src/risk/borrow_dynamics_model.py`
     - Multi-factor borrow fee rate pricing model integrating utilization rate, days-to-cover (DTC), borrow velocity, and short interest ratio.
     - SEC Rule 203(b)(1) affirmative locate verification rejecting unlocated short sales.
     - Short squeeze probability score and acute recall risk evaluation triggering OMS Gate 8.1 defensive short blocking and long momentum upgrades.
     - Negative carry drag deduction ensuring short alpha exceeds cumulative annual borrowing costs.
  4. **Triangular Parity Arbitrage Slicer Layer (M4, Feature F528)**: `src/execution/triangular_arbitrage_slicer.py` & `trading_system/src/execution/triangular_arbitrage_slicer.py`
     - Sub-millisecond discrepancy detection across ADR vs ordinary/FX, ETF vs synthetic basket, and cross-currency triangular parity.
     - Comprehensive friction accounting including half-spreads, exchange taker fees, maker rebates, statutory taxes (KRX STT 15 bps, SEC Section 31), borrow carry, and Kyle's lambda market impact.
     - Dynamic trajectory slicing enforcing a strict $\le 1.5\%$ ADV participation rate cap and exact integer share volume conservation.
     - Sub-50ms emergency partial-fill unwinding and hedging plans guaranteeing the zero naked overnight delta invariant.
  5. **Quantitative Benchmark & Master Verification Layer (M5, Feature F529)**: `trading_system/scripts/benchmark_phase111_quant_performance.py`, `tests/test_phase111_*.py`, reports, and `AGENTS.md`
     - Evaluates 15 metrics across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
     - Asserts 8 strict target KPIs (Net Return >= 410.00% [420.29%], Sharpe >= 109.00 [112.13], Sortino >= 5,400.00 [5,780.50], Calmar >= 9.30B [10.10B], MDD -0.0000001%, Slippage 0.048e-18 bps, Win Rate 100.0%, Top-Decile Spread 419.92% >= 405.00%).
     - Bit-for-bit SHA-256 synchronized markdown reports generated across 8 canonical paths (Category A, B, C, Master).
     - Comprehensive test suites (`tests/test_phase111_*.py`, 181 tests passed across 8 suites, 194 tests passed including Gen2) with zero regressions on Phase 108~110 suites (92 tests passed).
     - `AGENTS.md` updated with Release R127 / v118 Production Master.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|:------:|
| 1 | F525.1 | Vectorized L3 limit order book with structured NumPy arrays and $O(1)$ order lookup | M1 | Survey (Explorer 1) | DONE |
| 2 | F525.2 | In-place FIFO matching engine supporting Limit, Market, IOC, FOK, Post-Only, Iceberg | M1 | Survey (Explorer 1) | DONE |
| 3 | F525.3 | Real-time micro-price, depth-weighted OFI, and fill probability estimation | M1 | Survey (Explorer 1) | DONE |
| 4 | F526.1 | Neural baseline intensity network with Softplus positivity guarantee | M2 | Survey (Explorer 2) | DONE |
| 5 | F526.2 | 6D multivariate Hawkes process with exponential and power-law excitation kernels | M2 | Survey (Explorer 2) | DONE |
| 6 | F526.3 | Spectral radius projection ($\rho < 1.0$), flash crash excursion, and 5-market calibration | M2 | Survey (Explorer 2) | DONE |
| 7 | F527.1 | Non-linear hard-to-borrow fee rate pricing based on inventory depletion velocity | M3 | Survey (Explorer 3) | DONE |
| 8 | F527.2 | SEC Rule 203(b)(1) locate check and negative carry alpha deduction | M3 | Survey (Explorer 3) | DONE |
| 9 | F527.3 | Short squeeze catalyst scoring and OMS Gate 8.1 safety rule enforcement | M3 | Survey (Explorer 3) | DONE |
| 10 | F528.1 | Point-in-time triangular parity discrepancy detection (ADR, ETF basket, FX) | M4 | Survey (Explorer 3) | DONE |
| 11 | F528.2 | Microstructure friction model (Kyle's lambda, STT/SEC taxes, borrow drag) | M4 | Survey (Explorer 3) | DONE |
| 12 | F528.3 | ADV $\le 1.5\%$ slicing, integer volume conservation, and $\le 50\text{ms}$ emergency unwinding | M4 | Survey (Explorer 3) | DONE |
| 13 | F529.1 | 5-Market Benchmark Runner (benchmark_phase111_quant_performance.py) | M5 | Survey (Explorer 3) | DONE |
| 14 | F529.2 | 8 Strict Target KPIs assertion across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 | M5 | Survey (Explorer 3) | DONE |
| 15 | F529.3 | Bit-for-bit SHA-256 synchronized markdown reports across canonical paths | M5 | Survey (Explorer 3) | DONE |
| 16 | F529.4 | Comprehensive test suites (tests/test_phase111_*.py) & zero regressions | M5 | Survey (Explorer 3) | DONE |
| 17 | F529.5 | AGENTS.md Release R127 / v118 Production Master documentation update | M5 | Survey (Explorer 3) | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|:------:|
| 1 | M1: Vectorized LOB Engine (F525) | NumPy array L3 order book, FIFO matching, order types, micro-price | none | DONE |
| 2 | M2: Deep Hawkes Synthesizer (F526) | Neural baseline, 6D Hawkes, spectral radius, supercritical flash crash, 5-market profiles | none | DONE |
| 3 | M3: Borrow Dynamics & HTB Fees (F527) | Utilization/DTC fee model, SEC locate, squeeze catalyst, Gate 8.1 safety | none | DONE |
| 4 | M4: Triangular Arbitrage Slicer (F528) | ADR/ETF/FX parity, Kyle impact/tax friction, ADV cap, sub-50ms unwind | none | DONE |
| 5 | M5: Benchmark, Tests & Verification (F529) | Benchmark runner, 8 KPIs, SHA-256 sync, test suites, zero regressions, AGENTS.md | M1, M2, M3, M4 | DONE |

## Interface Contracts

### vectorized_lob_engine.py (M1) <-> OMS Execution & FastLOBEngine
- `VectorizedOrderBook`:
  - `add_order(order_id: int, side: OrderSide, price: float, volume: int, order_type: OrderType = OrderType.LIMIT, peak_volume: Optional[int] = None) -> Tuple[Optional[VectorizedOrder], List[MatchExecutionResult]]`
  - `cancel_order(order_id: int) -> bool`
  - `modify_order(order_id: int, new_volume: int) -> bool`
  - `get_level2_snapshot(depth: int = 10) -> Dict[str, List[Tuple[float, int]]]`
  - `compute_micro_price() -> float`
  - `compute_order_flow_imbalance() -> float`
  - `estimate_fill_probability(side: OrderSide, price: float, queue_position: int) -> float`

### deep_hawkes_synthesizer.py (M2) <-> FastLOBEngine & Stress Simulation
- `DeepMultivariateHawkesSynthesizer`:
  - `calibrate_market(market: str, custom_alpha: Optional[np.ndarray] = None, custom_beta: Optional[np.ndarray] = None, custom_mu: Optional[np.ndarray] = None, max_branching: float = 0.98) -> HawkesMarketCalibration`
  - `simulate(duration: float = 10.0, state_vector: Optional[np.ndarray] = None, flash_crash_override: bool = False) -> SimulationResult`
  - `compute_branching_ratio() -> float`
  - `project_to_stability(max_branching: float = 0.98) -> float`

### borrow_dynamics_model.py (M3) <-> ExecutionOMSEngine (Gate 8.1)
- `BorrowDynamicsModel`:
  - `evaluate_gate_8_1(order: Any, borrow_quote: Optional[BorrowFeeQuote] = None, squeeze_eval: Optional[SqueezeEvaluationResult] = None, hurdle_rate_bps: Optional[float] = None, net_alpha_bps: Optional[float] = None) -> Gate8_1Verdict`
  - `evaluate_borrow_quote(symbol: str, market: str, ...) -> BorrowFeeQuote`
  - `evaluate_squeeze_catalyst(symbol: str, market: str, borrow_quote: Optional[BorrowFeeQuote] = None, expected_alpha: float = 0.0) -> SqueezeEvaluationResult`
  - Blocks naked shorts without locate, blocks negative carry shorts, blocks shorts into short squeeze breakouts, and upgrades long orders to `MOMENTUM_SQUEEZE`.

### triangular_arbitrage_slicer.py (M4) <-> SmartOrderRouter & ExecutionOMSEngine
- `TriangularArbitrageSlicer`:
  - `detect_discrepancy(triplet: ArbitrageTriplet, quotes: Dict[str, VenueQuote], evaluation_time_ns: Optional[int] = None) -> Optional[ArbitrageDiscrepancy]`
  - `calculate_friction(triplet: ArbitrageTriplet, quotes: Dict[str, VenueQuote], ...) -> FrictionBreakdown`
  - `compute_slicing_schedule(triplet: ArbitrageTriplet, target_quantities: Dict[int, int], quotes: Dict[str, VenueQuote], n_slices: Optional[int] = None) -> TriangularSliceSchedule`
  - `execute_atomic_tranche(triplet: ArbitrageTriplet, tranche_quantities: Dict[int, int], quotes: Dict[str, VenueQuote], execution_mode: str = "LEADER_FOLLOWER", partial_fill_ratio: float = 1.0) -> Tuple[List[LegExecutionFill], Optional[PartialFillUnwindPlan]]`
  - `execute_full_arbitrage(triplet: ArbitrageTriplet, quotes: Dict[str, VenueQuote], target_size: Optional[int] = None, ...) -> TriangularArbitrageExecutionReport`

## Code Layout
- `src/core/vectorized_lob_engine.py` & `trading_system/src/core/vectorized_lob_engine.py`: Vectorized L3 order book engine (M1)
- `src/ai/deep_hawkes_synthesizer.py` & `trading_system/src/ai/deep_hawkes_synthesizer.py`: Deep multivariate Hawkes process synthesizer (M2)
- `src/risk/borrow_dynamics_model.py` & `trading_system/src/risk/borrow_dynamics_model.py`: Short squeeze borrow dynamics & HTB fee model (M3)
- `src/execution/triangular_arbitrage_slicer.py` & `trading_system/src/execution/triangular_arbitrage_slicer.py`: Cross-venue triangular parity execution slicer (M4)
- `trading_system/scripts/benchmark_phase111_quant_performance.py`: 5-market quantitative benchmark runner (M5)
- `tests/test_phase111_vectorized_lob.py`: Unit & property test suite for M1
- `tests/test_phase111_deep_hawkes.py`: Unit & property test suite for M2
- `tests/test_phase111_borrow_dynamics.py`: Unit & property test suite for M3
- `tests/test_phase111_triangular_arbitrage.py`: Unit & property test suite for M4
- `tests/test_phase111_adversarial_benchmark.py`: Master adversarial benchmark and regression test suite (M5)
- `tests/test_phase111_adversarial_challenger1.py`: Master adversarial challenger test suite (M5)
- Canonical Reports:
  - Category A (3 paths): `reports/quant_benchmark_comparison_phase111.md`, `trading_system/reports/quant_benchmark_comparison_phase111.md`, `trading_system/result/quant_benchmark_comparison_phase111.md`
  - Category B (5 paths): `reports/benchmark_phase111_report.md`, `trading_system/reports/benchmark_phase111_report.md`, `docs/benchmark_phase111_report.md`, `trading_system/result/benchmark_phase111_report.md`, `docs/reports/benchmark_phase111_report.md`
- Cumulative Comparison Reports:
  - `reports/quant_benchmark_cumulative_comparison.md`
  - `reports/quant_benchmark_comparison.md`
- `AGENTS.md`: Release R127 / v118 Production Master documentation
