# Handoff Report — R1: Strategy Engines & Infrastructure Survey

**Date**: 2026-08-30  
**From**: `explorer_survey_1` (Teamwork Explorer)  
**To**: `parent` (`0fcc7e25-ce9e-4ce3-aa13-c49ce672f67e`)  
**Type**: Hard Handoff (Investigation & Blueprint Complete)  
**Deliverables**:
- Survey Report: `d:\Finance\code\stock\.agents\explorer_survey_1\survey_report.md`
- Handoff Report: `d:\Finance\code\stock\.agents\explorer_survey_1\handoff.md`

---

## 1. Observation

1. **`BaseStrategyEngine` & `ScoreDataFrame`**:
   - Location: `trading_system/src/core/base_strategy.py:16-161`.
   - `BaseStrategyEngine` defines abstract base class with static methods `extract_ohlcv(symbol, prices_dict, min_bars=5)` and `normalize_scores_series(raw_scores, min_clip=0.05, max_clip=0.95, neutral_fill=0.50)`.
   - `ScoreDataFrame` is a `pd.DataFrame` subclass supporting dict-like symbol indexing/membership (`df['AAPL']`, `'AAPL' in df`, `df == dict`).
   - Strategy score outputs are returned via `make_score_dataframe(scores, score_column="score")`.

2. **`StrategyRegistry` & `StrategyMeta`**:
   - Location: `trading_system/src/core/strategy_registry.py:11-154`.
   - `StrategyMeta` accepts `strategy_id`, `display_name`, `score_column`, `category`, `default_regime_weights`, `output_file`, `requires_fundamentals`, `requires_indicators`, `is_standalone`.
   - Decorator `@register_strategy(meta)` registers strategy classes into singleton `StrategyRegistry`.
   - `auto_discover(["src.core", "src.ai"])` dynamically loads modules in `core_modules` list and walks packages.

3. **`EnsembleScoringEngine`**:
   - Location: `trading_system/src/ai/ensemble_scorer.py:218-417` (`REGIME_2D_WEIGHTS`), `833-858` (dynamic base weights), `2107-2139` (`strategy_cols`), `2150-2157` (`CrossSectionalScoreNormalizer`).
   - Dynamically pulls strategy weights from `StrategyRegistry` for any newly registered strategy.
   - `calculate_ensemble_score()` aggregates strategy DataFrames mapped through `strategy_cols`.

4. **Pipeline Execution**:
   - Location: `trading_system/run_pipeline.py:3040-3240` (`_eval_*` functions, `STRATEGY_REGISTRY`, parallel execution with `ThreadPoolExecutor`, report saving via `_save_strategy_predictions_report`).
   - `STRATEGY_REGISTRY` holds entries with `key`, `fn`, `col`, `title`, `file`, `hdr`, `w`.

5. **Existing Strategy Coverage & Tests**:
   - `StrategyCoverageAnalyzer` in `trading_system/src/analysis/coverage_analyzer.py:19-25` automatically queries `StrategyRegistry.get_all_ids()`.
   - Unit test `tests/test_phase5_registry.py` verified 5/5 tests passing (`pytest` exits code 0 in 25.78s).

---

## 2. Logic Chain

1. **Standard Compliance**:
   All new strategy engines must subclass `BaseStrategyEngine`, be decorated with `@register_strategy(StrategyMeta(...))`, and implement `compute_scores(self, prices_dict, fundamentals_dict=None, indicators_df=None, **kwargs) -> pd.DataFrame`.

2. **Cross-Asset Spillover Momentum Design**:
   - High-alpha signal capturing short-term momentum spillover from global macro drivers (USD/KRW, TNX, yield curve slope, WTI crude, Gold, DXY, VIX term structure & velocity) and overseas lead indices (SOX, NASDAQ, S&P 500) to domestic sector beneficiaries.
   - Calculates sector sensitivity vector $\boldsymbol{\beta}_s$, macro impulse $I_i(t) = \sum_k \beta_{s(i), k} \Delta M_k(t)$, and unpriced lead-lag diffusion $\Delta \text{Spillover}_i = I_i(t) - \gamma R_{i, 5d}(t)$ mapped to $[0.05, 0.95]$.

3. **Supply Chain GNN & Sector Flow Dynamics Design**:
   - Extends graph message passing across global anchor leaders (NVDA, AAPL, TSLA, MSFT, ASML, TSM, 005930, 000660, 005380, etc.) and tier-1/tier-2 suppliers/equipment vendors.
   - Integrates 2-hop graph convolution with asymmetric bullwhip shock amplification ($\times 1.35$ for negative customer shocks) and sector institutional money flow acceleration ($\text{FlowBoost}_s$).

4. **Intraday Volatility & Range Expansion Breakout Design**:
   - Detects high-probability directional breakouts post volatility contraction.
   - Combines 4 signals: Compression precursor $C_i$ (NR7, Bollinger Bandwidth squeeze $< 20$th percentile, Inside Day), Range expansion trigger $E_i$ ($\text{REF} = (\text{High} - \text{Low})/\text{ATR}_{14} \ge 1.5$), Relative volume $V_i$ ($\text{RVOL} \ge 1.8$), and Close Location Quality $Q_i$ ($\text{CLV} \ge 0.65$, breakout above 20-day High).

5. **Integration Points**:
   - Registration: Add module names to `StrategyRegistry.auto_discover()`.
   - Weights & Scoring: Add strategy keys to `REGIME_2D_WEIGHTS` and `strategy_cols` in `EnsembleScoringEngine`.
   - Pipeline Orchestration: Add `_eval_*` callbacks, `STRATEGY_REGISTRY` entries, and argument passing in `run_pipeline.py`.
   - Normalization & Coverage: Handled automatically by `CrossSectionalScoreNormalizer` and `StrategyCoverageAnalyzer`.

---

## 3. Caveats

1. **Macro Indicator Availability**:
   In offline or unit test scenarios, `indicators_df` may be empty or contain minimal synthetic data. `CrossAssetSpilloverEngine` must have a fallback that derives proxy sector momentum or returns neutral $0.50$ when macro data is absent.
2. **Graph Connectivity**:
   Some universe stocks may not be part of the explicit supply chain adjacency matrix. `SupplyChainGNNEngine` must handle isolated nodes gracefully by utilizing sector peer flow and self-momentum without causing zero-division or NaNs.
3. **Short Price History**:
   Stocks with $< 20$ trading bars must be handled with neutral score $0.50$ across all engines.

---

## 4. Conclusion

1. The strategy engine infrastructure (`BaseStrategyEngine`, `StrategyRegistry`, `ScoreDataFrame`) is modular, robust, and fully operational.
2. The exact mathematical specifications, class signatures, data inputs, output formats, and registration points for the 3 new strategy engines:
   - `CrossAssetSpilloverEngine` (`trading_system/src/core/cross_asset_spillover.py`, `cross_asset_spillover_score`)
   - `SupplyChainGNNEngine` (`trading_system/src/core/supply_chain_gnn.py`, `supply_chain_gnn_score`)
   - `RangeExpansionBreakoutEngine` (`trading_system/src/core/range_expansion_breakout.py`, `range_expansion_score`)
   are thoroughly specified in `d:\Finance\code\stock\.agents\explorer_survey_1\survey_report.md`.
3. System integration points across `StrategyRegistry`, `EnsembleScoringEngine`, `run_pipeline.py`, `CrossSectionalScoreNormalizer`, and `StrategyCoverageAnalyzer` are fully mapped.

---

## 5. Verification Method

1. **Inspect Survey Report**:
   Read `d:\Finance\code\stock\.agents\explorer_survey_1\survey_report.md`.

2. **Verify Existing Registry Tests**:
   ```powershell
   cmd /c "set PYTHONPATH=trading_system;trading_system\src;. && .venv\Scripts\pytest.exe tests/test_phase5_registry.py -v"
   ```

3. **Verify Target Files & Modules**:
   - `trading_system/src/core/base_strategy.py`
   - `trading_system/src/core/strategy_registry.py`
   - `trading_system/src/ai/ensemble_scorer.py`
   - `trading_system/run_pipeline.py`
