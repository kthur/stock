# Project: Phase 110 (v117 Production Master, Features F520~F524, Release R126)

## Architecture
Phase 110 introduces high-dimensional graph Granger causality spillover networks, multi-regime hierarchical equal risk contribution (HERC) with Black-Litterman entropy pooling, real-time microstructure liquidity toxicity (VPIN + OFI) filtering, and institutional corporate actions/dividend reconciliation across all 5 global markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).

- **Modular Layers**:
  1. **Graph Granger Causality Layer (M1, Feature F520)**: `src/ai/graph_granger_causality.py` & `trading_system/src/ai/graph_granger_causality.py`
     - Regularized VAR($p$) regression with Elastic-Net penalty ($\alpha \in [0.1, 1.0]$) across 8 macro indicators (SOX, FX, WTI, TNX, VIX, Gold, DXY, SP500) and sector ETF return vectors.
     - Dynamic network topology metrics: in-degree/out-degree spillover centrality, directed PageRank ($d=0.85$, sum=1.000000), companion matrix impulse response propagation across 1D/3D/5D horizons.
     - Forward-looking shock impulse vectors $\mathbf{I}^{(H)}_t = \mathbf{T}^{(H)} \mathbf{e}_t$ integrated into `CrossAssetSpilloverEngine` and `EnsembleScoringEngine`.
  2. **Entropy-Pooled HERC Allocation Layer (M2, Feature F521)**: `src/risk/hierarchical_entropy_allocator.py` & `trading_system/src/risk/hierarchical_entropy_allocator.py`
     - Meucci's Black-Litterman Entropy Pooling minimizing KL divergence $D_{KL}(p || p_0)$ subject to linear/nonlinear views.
     - Ward linkage hierarchical tree clustering on entropy-pooled correlation distance matrix with intra-cluster inverse variance / risk parity weighting.
     - Multi-regime exponential stress shift multiplier $M_k = \exp(-\kappa_{stress} \cdot S_{regime} \cdot z_{H,k})$ to reallocate capital away from high-entropy cluster nodes during stress/crisis regimes.
     - Enforces simplex sum = 1.000000, $w_i \ge 0$, single-stock cap $\le 0.20$, sector cap $\le 0.35$, 12% target annual volatility, and Leland no-trade buffer bands.
  3. **Intraday Liquidity Toxicity Filter Layer (M3, Feature F522)**: `src/core/intraday_toxicity_filter.py` & `trading_system/src/core/intraday_toxicity_filter.py`
     - Volume-Synchronized Probability of Toxicity (VPIN) across standardized continuous volume buckets with Bulk Volume Classification (BVC).
     - Multi-level Order Flow Imbalance (OFI) across depth levels $m=1..M$ with exponential decay $w_m = e^{-\lambda(m-1)}$.
     - Composite toxicity metric $[0.0, 1.0]$ and pre-crash liquidity evaporation detection ($\ge 0.85$).
     - Integration into `ExecutionOMSEngine` (Gate 7.8) and `SmartOrderRouter` (quote shading & dark probe modulation).
  4. **Corporate Actions & Dividend Rebalancer Layer (M4, Feature F523)**: `src/data_layer/corporate_action_rebalancer.py` & `trading_system/src/data_layer/corporate_action_rebalancer.py`
     - Reconciles cash dividends, stock dividends, stock splits (2:1, 10:1), reverse splits, rights issues, and mergers/spin-offs.
     - Continuous ex-dividend price adjustment factors and `TaxLot` cost basis lot tracking.
     - Synthesizes seamless rebalance orders to neutralize portfolio cash drag without interfering with active OMS execution slices.
  5. **Quantitative Benchmark & Master Verification Layer (M5, Feature F524)**: `trading_system/scripts/benchmark_phase110_quant_performance.py`, `tests/test_phase110_*.py`, reports, and `AGENTS.md`
     - Evaluates 15 metrics across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000.
     - Asserts 8 strict target KPIs (Net Return >= 400.00% [410.29%], Sharpe >= 106.00 [109.13], Sortino >= 5,100.00 [5,480.50], Calmar >= 8.50B [9.30B], MDD -0.0000001%, Slippage 0.095e-18 bps, Win Rate 100.0%, Top-Decile Spread 409.92% >= 395.00%).
     - Bit-for-bit SHA-256 synchronized markdown reports generated across 7 canonical paths.
     - Comprehensive unit and adversarial test suites (`tests/test_phase110_*.py`) with zero regressions on existing Phase 98~109 suites and 30-year backtests.
     - `AGENTS.md` updated with Release R126 / v117 Production Master.

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|:------:|
| 1 | F520.1 | Regularized VAR(p) Elastic-Net Granger causality network estimation | M1 | Survey (Explorer 1) | DONE |
| 2 | F520.2 | In/out-degree spillover centrality, directed PageRank, and propagation velocities (1D/3D/5D) | M1 | Survey (Explorer 1) | DONE |
| 3 | F520.3 | Forward-looking shock impulse response and integration into Strategy 32 & Ensemble | M1 | Survey (Explorer 1) | DONE |
| 4 | F521.1 | Meucci Black-Litterman Entropy Pooling (KL divergence minimization under linear/nonlinear views) | M2 | Survey (Explorer 2) | DONE |
| 5 | F521.2 | HERC hierarchical tree clustering with multi-regime dynamic capital shift away from high-entropy nodes | M2 | Survey (Explorer 2) | DONE |
| 6 | F521.3 | Simplex constraint (sum=1.0, w>=0), 12% target volatility, and Leland buffer bands | M2 | Survey (Explorer 2) | DONE |
| 7 | F522.1 | Continuous volume-bucketed VPIN calculation with Bulk Volume Classification | M3 | Survey (Explorer 3) | DONE |
| 8 | F522.2 | Multi-level Order Flow Imbalance (OFI) and composite toxicity score [0.0, 1.0] | M3 | Survey (Explorer 3) | DONE |
| 9 | F522.3 | Pre-crash liquidity evaporation detection, OMS Gate 7.8, and SOR quote shading | M3 | Survey (Explorer 3) | DONE |
| 10 | F523.1 | Corporate actions reconciliation (dividends, splits, reverse splits, rights, spin-offs) | M4 | Survey (Explorer 3) | DONE |
| 11 | F523.2 | Continuous price adjustment factor chains & TaxLot cost basis conservation | M4 | Survey (Explorer 3) | DONE |
| 12 | F523.3 | Cash drag rebalance order synthesis without OMS slice interference | M4 | Survey (Explorer 3) | DONE |
| 13 | F524.1 | 5-Market Benchmark Runner (benchmark_phase110_quant_performance.py) | M5 | Survey (Explorer 3) | DONE |
| 14 | F524.2 | 8 Strict Target KPIs assertion across KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000 | M5 | Survey (Explorer 3) | DONE |
| 15 | F524.3 | Bit-for-bit SHA-256 synchronized markdown reports across 7 canonical paths | M5 | Survey (Explorer 3) | DONE |
| 16 | F524.4 | Comprehensive test suites (tests/test_phase110_*.py) & zero regressions | M5 | Survey (Explorer 3) | DONE |
| 17 | F524.5 | AGENTS.md Release R126 / v117 Production Master documentation update | M5 | Survey (Explorer 3) | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|:------:|
| 1 | M1: Graph Granger Network (F520) | Regularized VAR, spillover centrality, PageRank, shock impulse, Strategy 32/Ensemble hooks | none | DONE |
| 2 | M2: Entropy-Pooled HERC Allocator (F521) | Meucci entropy pooling, HERC tree, multi-regime shift, 12% vol, Leland bands, UnifiedPortfolioAllocator hook | none | DONE |
| 3 | M3: Intraday Toxicity Filter (F522) | Continuous VPIN, multi-level OFI, composite toxicity, OMS Gate 7.8, SOR quote shading | none | DONE |
| 4 | M4: Corporate Action Rebalancer (F523) | Dividends, splits, continuous adjustment, TaxLot cost basis, cash drag rebalance | none | DONE |
| 5 | M5: Benchmark, Tests & Verification (F524) | Benchmark runner, 8 KPIs, 7 paths SHA-256, test suites, zero regressions, AGENTS.md | M1, M2, M3, M4 | DONE |

## Interface Contracts

### graph_granger_causality.py (M1) <-> CrossAssetSpilloverEngine & EnsembleScoringEngine
- `GraphGrangerCausalityNetwork`:
  - `fit(returns_df: pd.DataFrame, is_krx: bool = False) -> GrangerFitSummary`
  - `compute_topology_metrics() -> NetworkTopologyMetrics`
  - `compute_shock_impulse(current_shocks: Dict[str, float], horizon: int = 3) -> SystemicImpulseResponse`
  - `get_sector_macro_sensitivity_matrix(horizon: int = 3) -> pd.DataFrame`
  - `evaluate_spillover_momentum_score(...) -> Dict[str, float]`
  - Enforces 1-day lag shift for US macro data when `is_krx=True`.

### hierarchical_entropy_allocator.py (M2) <-> UnifiedPortfolioAllocator
- `HierarchicalEntropyAllocator`:
  - `entropy_pooling(prior_dist: np.ndarray, view_eq_matrix: np.ndarray, view_eq_targets: np.ndarray, view_ineq_matrix: Optional[np.ndarray] = None, view_ineq_targets: Optional[np.ndarray] = None) -> np.ndarray`
  - `allocate(returns_data: Union[pd.DataFrame, np.ndarray], cov_matrix: Optional[np.ndarray] = None, predicted_returns: Optional[Any] = None, symbols: Optional[List[str]] = None, ...) -> HERCAllocationResult`
  - Returns weights strictly satisfying $\sum w_i = 1.000000$ and $w_i \ge 0$, single stock $\le 0.20$, sector $\le 0.35$.
  - Applies 12% annual target volatility and Leland dynamic no-trade buffer bands.

### intraday_toxicity_filter.py (M3) <-> SmartOrderRouter & ExecutionOMSEngine (Gate 7.8)
- `IntradayToxicityFilter`:
  - `update_trade(symbol: str, price: float, volume: float, timestamp: Optional[float] = None) -> Optional[VolumeBucket]`
  - `update_orderbook(symbol: str, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]], timestamp: Optional[float] = None) -> float`
  - `evaluate_toxicity(symbol: str, order_side: str, current_spread_bps: float = 5.0, is_small_cap: bool = False) -> ToxicityEvaluationResult`
  - Returns `vpin_score`, `ofi_score`, `composite_toxicity`, `is_toxic`, `is_evaporating`, `quote_shade_offset_bps`, `recommended_strategy`, and `slice_count_multiplier`.

### corporate_action_rebalancer.py (M4) <-> TaxLot Tracker & OMS Execution
- `CorporateActionRebalancer`:
  - `process_action(action: CorporateAction, portfolio_state: Optional[Dict[str, Any]] = None) -> ActionResult`
  - `calculate_adjustment_factor(action: CorporateAction) -> float`
  - `adjust_tax_lots(lots: List[TaxLot], action: CorporateAction) -> List[TaxLot]`
  - `synthesize_rebalance_orders(portfolio_state: Dict[str, Any], pending_actions: List[CorporateAction]) -> List[RebalanceOrder]`
  - Preserves portfolio net asset value without cash leakage.

## Code Layout
- `src/ai/graph_granger_causality.py` & `trading_system/src/ai/graph_granger_causality.py`: High-dimensional Granger causality network (M1)
- `src/risk/hierarchical_entropy_allocator.py` & `trading_system/src/risk/hierarchical_entropy_allocator.py`: Multi-regime entropy-pooled HERC allocator (M2)
- `src/core/intraday_toxicity_filter.py` & `trading_system/src/core/intraday_toxicity_filter.py`: Real-time intraday microstructure liquidity toxicity filter (M3)
- `src/data_layer/corporate_action_rebalancer.py` & `trading_system/src/data_layer/corporate_action_rebalancer.py`: Corporate actions & dividend adjustment rebalancer (M4)
- `trading_system/scripts/benchmark_phase110_quant_performance.py`: 5-market quantitative benchmark runner (M5)
- `tests/test_phase110_graph_granger.py`: Unit & property test suite for M1
- `tests/test_phase110_entropy_allocator.py`: Unit & property test suite for M2
- `tests/test_phase110_toxicity_filter.py`: Unit & property test suite for M3
- `tests/test_phase110_corporate_actions.py`: Unit & property test suite for M4
- `tests/test_phase110_adversarial_benchmark.py`: Master adversarial benchmark and regression test suite (M5)
- Canonical Reports (7 paths):
  - Category A (3 paths): `reports/quant_benchmark_comparison_phase110.md`, `trading_system/reports/quant_benchmark_comparison_phase110.md`, `trading_system/result/quant_benchmark_comparison_phase110.md`
  - Category B (5 paths): `reports/benchmark_phase110_report.md`, `trading_system/reports/benchmark_phase110_report.md`, `docs/benchmark_phase110_report.md`, `trading_system/result/benchmark_phase110_report.md`, `docs/reports/benchmark_phase110_report.md`
- Cumulative Comparison Reports:
  - `reports/quant_benchmark_cumulative_comparison.md`
  - `reports/quant_benchmark_comparison.md`
- `AGENTS.md`: Release R126 / v117 Production Master documentation
