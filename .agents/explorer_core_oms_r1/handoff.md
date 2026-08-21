# Handoff Report: Core Strategies, Data Layer & OMS Deep Quantitative Audit

## 1. Observation
We completed a comprehensive, line-by-line quantitative audit across 31 strategy engines in `trading_system/src/core/*.py`, the persistence & data layer (`src/persistence/database.py`, `src/data_layer/indicator_storage.py`, `src/data_layer/earnings_data.py`), execution OMS (`src/execution/oms_engine.py`, `src/execution/slippage_feedback.py`, `src/core/order_management.py`), and pipeline configuration/orchestration (`src/config.py`, `trading_system/run_pipeline.py`).

Exact verbatim observations and evidence:
- **`src/core/card_factor.py:131`**: Code calls `res_rows.append({'symbol': sym, 'card_score': 0.5})` where `res_rows` is not defined in scope (dictionary is `scores = {}`), triggering `NameError`.
- **`src/core/gamma_squeeze.py:56-59`**: `compute_gamma_squeeze_scores(self, symbols, prices_dict, options_chain_dict)` does not take `**kwargs`, while caller methods `calculate_scores` and `compute_scores` pass `**kwargs`, triggering `TypeError`.
- **`src/core/hft_engine.py:181-193`**: `MicrostructureImbalanceEngine.compute_scores` initializes `universe = pd.DataFrame(columns=["symbol", "name", "market"])` when `universe=None`, returning 0 rows even when valid `prices_dict` is provided.
- **`src/core/short_interest_squeeze.py:114-126`**: Fallback proxy formula yields scores in $[1.0, 4.5]$ while explicit FINRA formula yields scores in $[0.05, 0.25]$. When cross-sectionally ranked, fallback stocks dominate top percentiles by scale artifact alone.
- **`src/execution/oms_engine.py:363-364` & `src/execution/slippage_feedback.py:56`**: `oms_engine.py` calls `SlippageFeedbackEngine().calculate_realized_slippage(sym)` which throws `TypeError` (0 arguments expected, 1 given) and expects a float scalar, but the method returns a `SlippageMetrics` object. The exception is swallowed by `except Exception: slip_mult = 1.0`, permanently disabling adaptive slippage feedback.
- **`src/core/cross_border_lead_lag.py:59-93`**: When run on KRX split-market runs where US tickers are omitted from `prices_dict`, US returns evaluate to 0.0, transforming the lead-lag model into $0.50 - 0.20 \times \text{kr\_ret}_{5d}$, penalizing winning Korean stocks.
- **`src/core/order_flow.py:103-108`**: OBV slope divides by `abs(obv_slice.iloc[-10])` where `obv_slice` is an arbitrary 20-bar cumulative sum initialized at 0 that crosses zero, causing division by 1.0 and multi-million value numerical explosions.
- **`src/core/rim_valuation.py:317-328`**: Cross-sectional ranking `.rank(pct=True)` is computed before invalidating operating loss and negative book value companies to `np.nan`, distorting the percentiles of legitimate companies.
- **`src/core/event_driven.py:245-255`**: Direct equality check `corp_code == sym_clean` compares 8-digit DART company identifiers with 6-digit exchange stock codes, failing Korean filing matching.
- **`src/core/multi_factor_neutralizer.py:276-281`**: Post-QR non-linear multiplier boosts re-introduce correlation with size/value factors, breaking the $\mathbf{X}^T \mathbf{\epsilon} = \mathbf{0}$ mathematical orthogonality SLA.
- **`src/persistence/database.py:437-459`**: Heuristic split detector triggers on any permanent price drop $> 25\%$, adjusting all past OHLC and volume downward for legitimate stock crashes or lower-limit events in split-adjusted feeds.
- **`src/execution/oms_engine.py:493-494`**: Hardcodes target price of synthetic inverse hedge overlay to $10,000$ KRW, causing an 80% under-hedge when hedging with 2,000 KRW Inverse 2X ETFs.
- **`src/config.py:240-242`**: Directly assigns `os.environ["TRAIN_SAMPLE_SP500"]` without `_get_env_int`, storing strings and raising `TypeError` on numerical operations.
- **`src/core/short_term_reversal.py:72`**: Hardcoded `df_sorted['Close']` raises `KeyError` on lowercase columns.
- **`src/core/iv_skew.py:126-132`**: Computes downside variance around the negative mean rather than downside semi-variance from zero.
- **`src/core/vol_target.py:113`**: Score compressed to $[0.212, 0.788]$, reducing variance contribution by 42%.

---

## 2. Logic Chain
1. **Mathematical Invariance & Correctness**: Alpha models rely on consistent scaling and smooth gradient properties. In `short_interest_squeeze.py`, combining two formulas with a 15x scale difference before percentile ranking corrupts the ranking order. In `order_flow.py`, dividing by an unanchored cumulative sum that crosses zero creates numerical explosions. In `rim_valuation.py`, computing percentiles prior to dropping distressed assets pollutes the rank distribution.
2. **Interface Contract & Concurrency Safety**: The pipeline relies on polymorphic invocation across 31 strategies. When `gamma_squeeze.py` omits `**kwargs` or `hft_engine.py` assumes `universe` is always provided as a non-empty DataFrame, polymorphic dispatch fails.
3. **Execution Closed-Loop Integrity**: The OMS safety gate requires real execution slippage feedback. Because `oms_engine.py` calls `calculate_realized_slippage(sym)` with an illegal signature and expects a float from a dataclass return, the call fails silently on every execution, breaking the closed-loop feedback design.
4. **Data Layer Purity**: Pre-adjusted data feeds should not be subjected to coarse price-drop split heuristics ($>25\%$), which misclassify daily limit-down drops as stock splits and corrupt historical price series.

---

## 3. Caveats
- Real-time order routing to live brokerage endpoints (e.g. KIS REST/WebSocket API) was evaluated via static simulation and mock engines; actual broker gateway responses were not exercised with live exchange credentials.
- Machine learning weights (XGBoost regression, Surge classifier, LSTM sequences) depend on historical retraining; the mathematical flaws identified herein directly affect feature inputs and ensemble score aggregation.

---

## 4. Conclusion
We identified **20 distinct, previously undiscovered defects** across 4 domains (Core Strategy Math, Execution OMS, Data Persistence, and Pipeline Orchestration).
- 5 Critical Severity (NameErrors, TypeErrors, Empty DataFrame returns, Scale Inconsistencies, Severed Feedback Loops)
- 9 High Severity (Alpha Inversions, Numerical Explosions, Cross-Sectional Ranking Pollution, Key Mismatches, Orthogonality Violations, Split Data Corruption, Hedge Under-Sizing, String Type Pollution, Case-Sensitivity KeyErrors)
- 6 Medium Severity (Downside Variance Distortions, Score Variance Suppressions, Boundary Collapses, Step Jump Discontinuities, False Attribution Biases, Metric Scale Distortions)

Full details, mathematical analysis, and before/after code diffs are documented in `d:\Finance\code\stock\.agents\explorer_core_oms_r1\core_oms_findings.md`.

---

## 5. Verification Method
1. **Targeted Python AST / Syntax & Invocation Verification**:
   ```bash
   .venv/Scripts/python.exe -c "
   import pandas as pd
   from src.core.card_factor import CARDFactorEngine
   from src.core.gamma_squeeze import OptionsGammaSqueezeEngine
   from src.core.hft_engine import MicrostructureImbalanceEngine
   from src.execution.oms_engine import ExecutionOMSEngine
   from src.execution.slippage_feedback import SlippageFeedbackEngine

   # 1. Test CARDFactorEngine fallback
   card = CARDFactorEngine()
   res = card.compute_scores({'005930': pd.DataFrame()})

   # 2. Test Gamma Squeeze kwargs
   gamma = OptionsGammaSqueezeEngine()
   gamma.calculate_scores(['AAPL'], prices_dict={'AAPL': pd.DataFrame()}, indicators_df=pd.DataFrame())

   # 3. Test Microstructure default prices dict
   micro = MicrostructureImbalanceEngine()
   res_micro = micro.compute_scores(prices_dict={'005930': pd.DataFrame({'Close': [100]*50, 'Volume': [1000]*50})})

   # 4. Test OMS slippage call
   oms = ExecutionOMSEngine()
   slip = SlippageFeedbackEngine()
   "
   ```
2. **Full Unit Test Suite**:
   ```bash
   .venv/Scripts/pytest tests/ -v
   ```
3. **Invalidation Conditions**:
   - If `card_factor.py` runs on a dictionary with empty DataFrames without raising `NameError`.
   - If `gamma_squeeze.py` can be called with `**kwargs` without raising `TypeError`.
   - If `oms_engine.py` receives a valid float multiplier from `SlippageFeedbackEngine` rather than throwing an exception.
