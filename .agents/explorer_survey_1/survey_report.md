# Quantitative Architecture Survey Report — R1: Strategy Engines & Infrastructure

**Target Codebase**: `d:\Finance\code\stock`  
**Working Directory**: `d:\Finance\code\stock\.agents\explorer_survey_1`  
**Milestone**: R1 — High-Alpha Strategy Engines Implementation & Registry Integration  
**Date**: 2026-08-30  
**Status**: Comprehensive Survey & Specification Completed  

---

## 1. Executive Summary

This report establishes the forensic survey and architectural blueprint for **R1 (High-Alpha Strategy Engines & Infrastructure)** of the Stock Trading System across 5 core equity markets (**SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ**).

The survey examined:
1. `trading_system/src/core/base_strategy.py` (`BaseStrategyEngine`, `ScoreDataFrame`)
2. `trading_system/src/core/strategy_registry.py` (`StrategyRegistry`, `StrategyMeta`, `@register_strategy`, `auto_discover`)
3. `trading_system/src/ai/ml_strategy_adapters.py` (Adapter layer bridging ML models to `BaseStrategyEngine`)
4. `trading_system/src/ai/ensemble_scorer.py` (`EnsembleScoringEngine`, `REGIME_2D_WEIGHTS`, `strategy_cols`, dynamic registration)
5. `trading_system/run_pipeline.py` (Parallel strategy execution, `STRATEGY_REGISTRY`, report generation, score merging)
6. `trading_system/src/analysis/coverage_analyzer.py` (`StrategyCoverageAnalyzer` dynamic registry integration)
7. `trading_system/src/ai/score_normalizer.py` (`CrossSectionalScoreNormalizer`)
8. Existing tests in `tests/` (`test_phase5_registry.py`, `test_all_16_markets_31_strategies.py`, `test_new_5_strategies.py`, etc.)

---

## 2. Existing Strategy Infrastructure Architecture

### 2.1 `BaseStrategyEngine` (`src/core/base_strategy.py`)
`BaseStrategyEngine` provides the standardized abstract base class for all quantitative factor, technical, ML, and statistical arbitrage strategy engines in the project.

Key capabilities:
- **`extract_ohlcv(symbol, prices_dict, min_bars=5) -> Optional[pd.DataFrame]`**: Standardizes OHLCV casing (`Open`, `High`, `Low`, `Close`, `Volume`), unpacks MultiIndex columns, and filters out short/empty series.
- **`normalize_scores_series(raw_scores, min_clip=0.05, max_clip=0.95, neutral_fill=0.50) -> Dict[str, float]`**: Applies percentile rank normalization to raw alpha signals, clipping safely to $[0.05, 0.95]$ with neutral midpoint $0.50$.
- **`ScoreDataFrame` / `make_score_dataframe(scores, score_column="score")`**: A `pd.DataFrame` subclass that simultaneously supports standard DataFrame vector operations and dict-like symbol indexing/membership (`df['AAPL']`, `'AAPL' in df`, `df == dict`).

### 2.2 `StrategyRegistry` (`src/core/strategy_registry.py`)
`StrategyRegistry` is a thread-safe singleton managing strategy metadata and dynamic runtime discovery.

- **`StrategyMeta`**:
  ```python
  class StrategyMeta:
      def __init__(
          self,
          strategy_id: str,
          display_name: str,
          score_column: str,
          category: str = "factor",  # 'factor' | 'ml' | 'stat' | 'event' | 'technical' | 'cross_asset' | 'network' | 'breakout'
          default_regime_weights: Optional[Dict[str, float]] = None,
          output_file: Optional[str] = None,
          requires_fundamentals: bool = False,
          requires_indicators: bool = False,
          is_standalone: bool = False,
      ): ...
  ```
- **Registration Mechanism**:
  Engine classes are annotated with `@register_strategy(StrategyMeta(...))` which registers them into `StrategyRegistry._strategies[strategy_id] = (cls, meta)`.
- **Auto-Discovery**:
  `StrategyRegistry.auto_discover(package_paths=["src.core", "src.ai"])` imports all core and AI modules and walks subpackages so that all decorated strategy classes are loaded without manual registry file edits.

---

## 3. Detailed Specification for the 3 New High-Alpha Strategy Engines

### 3.1 Strategy 1: Cross-Asset Spillover Momentum
- **Target File**: `trading_system/src/core/cross_asset_spillover.py`
- **Class**: `CrossAssetSpilloverEngine(BaseStrategyEngine)`
- **Strategy ID**: `cross_asset_spillover`
- **Score Column**: `cross_asset_spillover_score`
- **Display Name**: `"Cross-Asset Spillover Momentum"`
- **Output File**: `cross_asset_spillover_predictions.txt`
- **Category**: `"cross_asset"` / `"factor"`
- **Regime Weights**:
  - `BEAR_LOW_VOL`: 0.03, `BEAR_HIGH_VOL`: 0.04, `SIDEWAYS_LOW_VOL`: 0.03, `SIDEWAYS_HIGH_VOL`: 0.03, `BULL_LOW_VOL`: 0.04, `BULL_HIGH_VOL`: 0.04
- **Alpha Hypothesis & Mathematical Formulation**:
  1. *Macro Drivers*: Tracks multi-horizon returns (1D, 3D, 5D) of global macro factors:
     - FX: USD/KRW ($\Delta \text{FX}$), DXY
     - Rates: US 10Y Treasury yield ($\Delta \text{TNX}$), 2Y yield, 10Y-2Y yield curve slope ($\Delta \text{Slope}$)
     - Commodities: WTI Crude Oil ($\Delta \text{WTI}$), Gold ($\Delta \text{Gold}$)
     - Volatility & Risk: VIX level, VIX velocity ($\Delta \text{VIX}$), VIX futures term structure slope
     - Overseas Leading Indices: SOX Semiconductor Index ($\Delta \text{SOX}$), NASDAQ 100 ($\Delta \text{NDX}$), S&P 500 ($\Delta \text{SPX}$)
  2. *Sector Sensitivity Matrix*: Dynamic sector-level elasticity coefficients $\boldsymbol{\beta}_s = [\beta_{s, \text{SOX}}, \beta_{s, \text{FX}}, \beta_{s, \text{WTI}}, \beta_{s, \text{TNX}}, \beta_{s, \text{VIX}}]$.
  3. *Macro Spillover Impulse*:
     $$I_i(t) = \sum_k \beta_{s(i), k} \cdot \Delta M_k(t)$$
  4. *Lead-Lag Diffusion / Unpriced Tailwind*:
     $$\Delta \text{Spillover}_i = I_i(t) - \gamma \cdot R_{i, 5d}(t)$$
     High positive $\Delta \text{Spillover}_i$ signals that strong macro tailwinds have formed for sector $s(i)$ which stock $i$ has not yet fully reflected (or is in early stage of breakout).
  5. *Score Mapping*:
     $$\text{Score}_i = \frac{1}{1 + \exp\left(-15.0 \cdot \Delta \text{Spillover}_i\right)} \in [0.05, 0.95]$$
     Fallback: $0.50$ when indicators or prices are absent.

- **Exact Signature**:
  ```python
  def compute_scores(
      self,
      prices_dict: Dict[str, pd.DataFrame],
      fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
      indicators_df: Optional[Any] = None,
      **kwargs: Any
  ) -> pd.DataFrame: ...
  ```

---

### 3.2 Strategy 2: Supply Chain GNN & Sector Flow Dynamics
- **Target File**: `trading_system/src/core/supply_chain_gnn.py`
- **Class**: `SupplyChainGNNEngine(BaseStrategyEngine)`
- **Strategy ID**: `supply_chain_gnn`
- **Score Column**: `supply_chain_gnn_score`
- **Display Name**: `"Supply Chain GNN & Sector Flow Dynamics"`
- **Output File**: `supply_chain_gnn_predictions.txt`
- **Category**: `"network"` / `"factor"`
- **Regime Weights**:
  - `BEAR_LOW_VOL`: 0.02, `BEAR_HIGH_VOL`: 0.01, `SIDEWAYS_LOW_VOL`: 0.03, `SIDEWAYS_HIGH_VOL`: 0.03, `BULL_LOW_VOL`: 0.04, `BULL_HIGH_VOL`: 0.04
- **Alpha Hypothesis & Mathematical Formulation**:
  1. *Multi-Market Value Chain Graph*: Builds directed graph $\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathbf{W})$ connecting global tier-1 anchor nodes (NVDA, AAPL, TSLA, MSFT, ASML, TSM, Samsung Electronics, SK Hynix, Hyundai Motor, LIG Nex1, HD Hyundai Electric) with tier-1, tier-2 suppliers, materials, and equipment vendors across US and KRX universes.
  2. *Relational Message Passing with Bullwhip Non-Linearity*:
     - Node initial signal: $\mathbf{h}_i^{(0)} = 0.50 R_{i, 1d} + 0.30 R_{i, 3d} + 0.20 R_{i, 5d}$.
     - Asymmetric bullwhip amplification on negative shocks ($\times 1.35$) vs positive shocks ($\times 0.85$).
     - Multi-hop graph convolution:
       $$\mathbf{h}_i^{(l+1)} = \sigma\left( \sum_{j \in \mathcal{N}(i)} \frac{w_{ji}}{\sqrt{d_i d_j}} \mathbf{h}_j^{(l)} + \mathbf{W}_{\text{self}} \mathbf{h}_i^{(l)} \right)$$
  3. *Sector Liquidity Flow Acceleration*:
     Aggregates sector money flow intensity $\text{MFI}_s$ and volume surge ratios across sector peers:
     $$\text{FlowBoost}_s = \frac{\sum_{j \in \text{Sector}(s)} \text{Vol}_{j, 1d} \cdot R_{j, 1d}}{\sum_{j \in \text{Sector}(s)} \text{Vol}_{j, 20d}}$$
  4. *Composite Graph Signal*:
     $$\text{GraphSignal}_i = 0.35 \mathbf{h}_i^{(0)} + 0.40 \mathbf{h}_i^{(1)} + 0.25 \mathbf{h}_i^{(2)} + 0.20 \text{FlowBoost}_{s(i)}$$
     Mapped via continuous sigmoid to $[0.05, 0.95]$ with neutral midpoint $0.50$.

- **Exact Signature**:
  ```python
  def compute_scores(
      self,
      prices_dict: Dict[str, pd.DataFrame],
      fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
      indicators_df: Optional[Any] = None,
      **kwargs: Any
  ) -> pd.DataFrame: ...
  ```

---

### 3.3 Strategy 3: Intraday Volatility & Range Expansion Breakout
- **Target File**: `trading_system/src/core/range_expansion_breakout.py`
- **Class**: `RangeExpansionBreakoutEngine(BaseStrategyEngine)`
- **Strategy ID**: `range_expansion_breakout`
- **Score Column**: `range_expansion_score`
- **Display Name**: `"Intraday Volatility & Range Expansion Breakout"`
- **Output File**: `range_expansion_predictions.txt`
- **Category**: `"technical"` / `"breakout"`
- **Regime Weights**:
  - `BEAR_LOW_VOL`: 0.02, `BEAR_HIGH_VOL`: 0.01, `SIDEWAYS_LOW_VOL`: 0.03, `SIDEWAYS_HIGH_VOL`: 0.03, `BULL_LOW_VOL`: 0.04, `BULL_HIGH_VOL`: 0.05
- **Alpha Hypothesis & Mathematical Formulation**:
  1. *Volatility Contraction Precursor (Compression Score $C_i \in [0, 1]$)*:
     - NR7 flag: $\text{Range}_t = \min_{k=0..6}(\text{High}_{t-k} - \text{Low}_{t-k})$.
     - Bollinger Bandwidth contraction: $\text{BW}_t = \frac{BB_{\text{upper}} - BB_{\text{lower}}}{BB_{\text{mid}}} \le \text{Percentile}_{20}(\text{BW}_{t-20..t})$.
     - Inside Day / Multi-bar range compression.
  2. *Range Expansion Trigger (Expansion Factor $E_i \in [0, 1]$)*:
     - $\text{REF}_t = \frac{\text{High}_t - \text{Low}_t}{\text{ATR}_{14}(t)}$. Expansion trigger when $\text{REF}_t \ge 1.5$ (up to $3.0\times$).
  3. *Volume & Close Quality Verification ($V_i, Q_i \in [0, 1]$)*:
     - Relative Volume: $\text{RVOL}_t = \frac{\text{Volume}_t}{\text{SMA}_{20}(\text{Volume})_t} \ge 1.8$.
     - Close Location Value: $\text{CLV}_t = \frac{\text{Close}_t - \text{Low}_t}{\text{High}_t - \text{Low}_t + 10^{-6}} \ge 0.65$ (closing strongly near the high).
     - Breakout confirmation: $\text{Close}_t > \max_{k=1..20} \text{High}_{t-k}$ or $\text{Close}_t > BB_{\text{upper}}$.
  4. *Composite Breakout Probability*:
     $$\text{RawSignal}_i = 0.25 C_i + 0.35 E_i + 0.25 V_i + 0.15 Q_i$$
     Mapped to calibrated probability $[0.05, 0.95]$ with neutral default $0.50$.

- **Exact Signature**:
  ```python
  def compute_scores(
      self,
      prices_dict: Dict[str, pd.DataFrame],
      fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
      indicators_df: Optional[Any] = None,
      **kwargs: Any
  ) -> pd.DataFrame: ...
  ```

---

## 4. Pipeline & System Integration Points

### 4.1 `StrategyRegistry` Auto-Discovery (`src/core/strategy_registry.py`)
Add the module paths to `core_modules` in `StrategyRegistry.auto_discover()`:
- `"src.core.cross_asset_spillover"`
- `"src.core.supply_chain_gnn"`
- `"src.core.range_expansion_breakout"`

### 4.2 `EnsembleScoringEngine` (`src/ai/ensemble_scorer.py`)
1. **`REGIME_2D_WEIGHTS`**:
   Add the 3 strategy keys (`cross_asset_spillover`, `supply_chain_gnn`, `range_expansion_breakout`) to all 6 regime weight dictionaries (`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`) with properly normalized sum $= 1.00$.
2. **`calculate_ensemble_score()`**:
   - Add parameter arguments:
     - `cross_asset_spillover_df: Optional[pd.DataFrame] = None`
     - `supply_chain_gnn_df: Optional[pd.DataFrame] = None`
     - `range_expansion_df: Optional[pd.DataFrame] = None`
   - Add tuples to `strategy_cols`:
     - `('cross_asset_spillover', 'cross_asset_spillover_score')`
     - `('supply_chain_gnn', 'supply_chain_gnn_score')`
     - `('range_expansion_breakout', 'range_expansion_score')`
3. **`CrossSectionalScoreNormalizer`**:
   The normalizer dynamically receives `strategy_cols` from `EnsembleScoringEngine` and performs cross-sectional ranking / Winsorized Gaussian CDF transformation per market.

### 4.3 `run_pipeline.py` Orchestration
1. **Evaluation Callbacks**:
   - `_eval_cross_asset_spillover()`
   - `_eval_supply_chain_gnn()`
   - `_eval_range_expansion_breakout()`
2. **`STRATEGY_REGISTRY` entries**:
   Add dictionary specs for concurrent execution via `ThreadPoolExecutor` and report file output generation:
   - `cross_asset_spillover` $\to$ `cross_asset_spillover_predictions.txt`
   - `supply_chain_gnn` $\to$ `supply_chain_gnn_predictions.txt`
   - `range_expansion_breakout` $\to$ `range_expansion_predictions.txt`
3. **Merging & Ensemble Execution**:
   Include resulting DataFrames in `_all_strategy_dfs` and pass them to `scorer.calculate_ensemble_score(...)`.

---

## 5. Verification Strategy & Test Matrix

1. **Unit & Integration Test Suite**:
   Implement `tests/test_r1_high_alpha_strategies.py` containing:
   - `test_cross_asset_spillover_engine()`: Verify metadata, empty handling, synthetic OHLCV + macro indicators calculation, score bounds in $[0.0, 1.0]$, sector beta response.
   - `test_supply_chain_gnn_engine()`: Verify metadata, empty handling, multi-hop graph message passing, bullwhip asymmetric shock calculation, score bounds in $[0.0, 1.0]$.
   - `test_range_expansion_breakout_engine()`: Verify metadata, empty handling, NR7 / BB squeeze + volume expansion detection, score bounds in $[0.0, 1.0]$.
   - `test_strategy_registry_integration()`: Verify auto-discovery registers all 3 new strategies with valid `StrategyMeta` attributes.
   - `test_ensemble_scorer_integration_with_new_strategies()`: Verify `EnsembleScoringEngine` computes ensemble score seamlessly with the 3 new strategy outputs.
   - `test_cross_sectional_normalizer_with_new_strategies()`: Verify `CrossSectionalScoreNormalizer` normalizes the 3 new score columns without NaN corruption.

2. **Test Command**:
   ```powershell
   cmd /c "set PYTHONPATH=trading_system;trading_system\src;. && .venv\Scripts\pytest.exe tests/test_r1_high_alpha_strategies.py -v"
   ```
   and full test suite verification:
   ```powershell
   cmd /c "set PYTHONPATH=trading_system;trading_system\src;. && .venv\Scripts\pytest.exe tests/ -v"
   ```

---

## 6. Implementation Readiness Summary

| Component | Status | Readiness |
|---|---|---|
| `BaseStrategyEngine` base class | Existing (`src/core/base_strategy.py`) | Ready for inheritance |
| `StrategyRegistry` infrastructure | Existing (`src/core/strategy_registry.py`) | Ready for auto-discovery |
| `ScoreDataFrame` structure | Existing (`src/core/base_strategy.py`) | Ready for standardized output |
| Strategy 1: Cross-Asset Spillover Momentum | Specification complete | Ready for implementation |
| Strategy 2: Supply Chain GNN & Sector Flow Dynamics | Specification complete | Ready for implementation |
| Strategy 3: Intraday Volatility & Range Expansion Breakout | Specification complete | Ready for implementation |
| `EnsembleScoringEngine` integration | Integration points identified | Ready for wiring |
| `run_pipeline.py` integration | Integration points identified | Ready for wiring |
| `StrategyCoverageAnalyzer` | Dynamic registry compliant | Ready (auto-detects new strategies) |
| Test suite plan | Fully defined | Ready for test creation |
