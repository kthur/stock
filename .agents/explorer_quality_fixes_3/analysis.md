# Analysis of Strategy Output Quality Bugs in Stock Prediction Pipeline

This report presents the findings, root causes, step-by-step logic chains, and concrete proposed code changes for the 4 strategy output quality bugs and the output file placeholder requirement.

---

## Executive Summary
1. **Bug 1 (Surge Classifier 0.0%) & Bug 3 (VCP ML Predictions Empty):** Caused by a cache key mismatch between `.github/workflows/training.yml` and `.github/workflows/pipeline.yml` in GitHub Actions. This cache miss prevents pre-trained models from being restored. In `SKIP_TRAINING: 'True'` mode, the missing models on disk trigger on-the-fly training fallback, which fails/stalls due to yfinance rate limits when trying to fetch all universe symbols from 2006. As a result, the prediction logic defaults probabilities to `0.0` or returns empty.
2. **Bug 2 (Lead-Lag KRX Missing):** The global leader selection logic in `OnDevicePredictionModel.compute_lead_lag` picks the top 50 symbols by market cap. Raw market caps (USD for SP500, KRW for KRX) are currency-mismatched, and `norm_market_cap` is relative, causing smaller markets like KOSDAQ and KONEX to have zero representation in the leaders list. During prediction, KOSDAQ/KONEX follower symbols get a score of `0.0` because their leaders are not present in the prediction data.
3. **Bug 4 (Ensemble Outputting 0%):** A direct consequence of Bugs 1-3. Since regression, surge, lead-lag, and VCP ML predictions all default to `0.0`, the weighted ensemble score is `0.0`, mapping to `0.0%` expected returns.
4. **Output File Placeholders:** Currently, if predictions are empty, the corresponding files are not written. This breaks subsequent steps in GHA. The fix is to always write the files, inserting human-readable placeholder messages (e.g. `No surge candidates found today.`) when the data is empty.

---

## Detailed Investigation & Analysis

### Bug 1: Surge Classifier Outputting 0.0% Probability & Bug 3: VCP ML Predictions Empty

#### 1. Observational Evidence
* **Cache Key Mismatch:**
  In `.github/workflows/training.yml` (lines 66-67):
  ```yaml
        uses: actions/cache@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
  ```
  In `.github/workflows/pipeline.yml` (lines 68-71):
  ```yaml
        uses: actions/cache/restore@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}
          restore-keys: |
            ai-models-v2-${{ matrix.target }}-
  ```
  The cache key prefix is mismatched (`ai-models-v2-[date]-[target]` vs `ai-models-v2-[target]-[date]`).
* **Fallback to Training:**
  In `trading_system/run_pipeline.py` (lines 708-725), if `cfg.skip_training` is true but models are not found on disk, the pipeline falls back to training (`should_skip = False`):
  ```python
  if cfg.skip_training:
      ...
      regression_loaded = any(len(mkt_dict) > 0 for mkt_dict in model.models.values()) ...
      if regression_loaded and surge_loaded and vcp_loaded:
          should_skip = True
      else:
          logger.warning("Missing or incomplete pre-trained models on disk. Falling back to training. Setting should_skip = False.")
          should_skip = False
  ```
* **Surge Classifier Defaulting to 0.0:**
  In `trading_system/src/ai/prediction_model.py` (lines 2004-2006):
  ```python
  else:
      res_df.loc[idx, col_name] = 0.0
      logger.warning(f"Surge prediction for market={mkt}, horizon={h} defaulted to 0.0 due to missing models.")
  ```
* **VCP ML Skip Prediction:**
  In `trading_system/src/ai/vcp_ml_predictor.py` (lines 487-489):
  ```python
  if not self.models:
      logger.warning("No VCP ML models loaded, skipping prediction")
      return pd.DataFrame()
  ```

#### 2. Logic Chain
1. The GHA Daily Pipeline fails to restore pre-trained models due to the mismatched cache key formats.
2. The models directory `/github/workspace/trading_system/models` remains empty.
3. `run_pipeline.py` detects missing models and falls back to training.
4. Training attempts to download historical price data from 2006 for all universe symbols via yfinance/FDR.
5. In a GHA environment, fetching data for thousands of symbols hits yfinance rate limits, resulting in empty/incomplete datasets.
6. The training phase fails to produce any models.
7. Prediction logic sees no loaded models, so surge probabilities default to `0.0` and VCP ML predictions return empty.

#### 3. Proposed Code Changes

##### Change A: Fix Cache Key in `.github/workflows/training.yml`
* **Before (line 66):**
  ```yaml
            key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
  ```
* **After:**
  ```yaml
            key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}
  ```

---

### Bug 2: Lead-Lag Predictions Missing for KRX Markets

#### 1. Observational Evidence
* **Global Leader Selection:**
  In `trading_system/src/ai/prediction_model.py` (lines 2082-2085):
  ```python
  logger.info("Selecting top 50 leaders by market cap...")
  cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
  avg_caps = df_train.groupby('symbol')[cap_col].mean()
  top_50_leaders = avg_caps.nlargest(50).index.tolist()
  ```
* **Unconverted Raw Market Cap:**
  In `apply_market_normalization` (line 668):
  ```python
  df_copy['market_cap'] = close * shares_out
  ```
  Where `shares_out` is raw outstanding shares. For KRX, market cap is in KRW (numerically ~1300x larger than SP500 in USD). If raw `market_cap` is used, KOSPI symbols completely dominate `top_50_leaders` (e.g. Samsung Electronics is 400 Trillion vs MSFT 3 Trillion).
* **Exclusion of KOSDAQ/KONEX:**
  If `norm_market_cap` is used, it is normalized per market. Because KOSDAQ and KONEX have much smaller total market caps compared to KOSPI/SP500, KOSDAQ/KONEX symbols are excluded from the global `nlargest(50)`.
* **Follower Calculation Dependency:**
  In `predict_lead_lag` (lines 2197-2200):
  ```python
  for leader, followers in self.lead_lag_matrix.items():
      leader_ret = today_returns.get(leader, 0.0)
      if leader_ret <= 0.01:
          continue
  ```
  For KOSDAQ or KONEX, `prices_dict` passed to `predict_lead_lag` only contains KOSDAQ/KONEX symbols. Since KOSDAQ/KONEX has no leaders in the matrix, `today_returns.get(leader)` is evaluated on KOSPI/SP500 leaders which are missing from `prices_dict`, returning `0.0`. Thus, KOSDAQ/KONEX followers never receive scores.

#### 2. Logic Chain
1. `compute_lead_lag` selects the global top 50 leaders by raw market cap (currency-mismatched) or normalized market cap (scale-mismatched).
2. KOSDAQ, KONEX, and SP500 (depending on which column is active) are completely excluded from the top 50 leaders.
3. During inference for KOSDAQ or KONEX targets, their leaders are not present in `prices_dict`, so no follower scoring is triggered.
4. Lead-lag predictions for KOSDAQ, KONEX, and SP500 remain empty.

#### 3. Proposed Code Changes

##### Change B: Make Leader Selection Market-Aware in `trading_system/src/ai/prediction_model.py`
* **Before (lines 2082-2085):**
  ```python
          logger.info("Selecting top 50 leaders by market cap...")
          cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
          avg_caps = df_train.groupby('symbol')[cap_col].mean()
          top_50_leaders = avg_caps.nlargest(50).index.tolist()
  ```
* **After:**
  ```python
          logger.info("Selecting leaders by market cap per market...")
          cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
          avg_caps = df_train.groupby('symbol')[cap_col].mean()
          
          # Map symbols to their markets
          if symbol_to_market is None:
              symbol_to_market = {}
              for sym in avg_caps.index:
                  symbol_to_market[sym] = 'KRX' if self.is_krx_symbol(sym) else 'SP500'
                  
          # Group by market segment
          market_groups = {}
          for sym, cap in avg_caps.items():
              mkt = symbol_to_market.get(sym, 'SP500').upper()
              if mkt not in market_groups:
                  market_groups[mkt] = []
              market_groups[mkt].append((sym, cap))
              
          # Select top leaders per market to ensure balanced representation
          top_leaders = []
          market_limits = {'SP500': 20, 'KOSPI': 20, 'KOSDAQ': 20, 'KONEX': 5, 'KRX': 20}
          for mkt, sym_caps in market_groups.items():
              sym_caps.sort(key=lambda x: -x[1])
              limit = market_limits.get(mkt, 20)
              top_leaders.extend([sym for sym, _ in sym_caps[:limit]])
              
          top_50_leaders = top_leaders
  ```
* **Note:** Update the signature of `compute_lead_lag` to include `symbol_to_market: Optional[Dict[str, str]] = None` and update the call in `run_pipeline.py` (line 922):
  ```python
  model.compute_lead_lag(df_train, indicator_df=indicator_train, symbol_to_market=symbol_market)
  ```

---

### Bug 4: Ensemble Outputting 0% for KRX

#### 1. Observational Evidence
* **Ensemble Score Calculation:**
  In `trading_system/src/ai/ensemble_scorer.py` (lines 125-136):
  ```python
  merged['ensemble_score'] = (
      weights['regression'] * merged['reg_score'] +
      weights['surge'] * merged['surge_score'] +
      weights['lead_lag'] * merged['ll_score'] +
      weights['vcp_ml'] * merged['vcp_ml_score']
  )
  merged['ensemble_expected_return'] = merged['ensemble_score'] * 20.0
  ```
* **Default Values:**
  If the inputs are missing/NaN:
  ```python
  fill_cols = ['reg_pred', 'reg_score', 'surge_score', 'll_raw', 'll_score', 'vcp_ml_score']
  for col in fill_cols:
      if col in merged.columns:
          merged[col] = merged[col].fillna(0.0)
  ```

#### 2. Logic Chain
1. Due to Bug 1 (Surge models not restored/trained) and Bug 3 (VCP ML models not restored/trained), `surge_score` and `vcp_ml_score` default to `0.0`.
2. Due to Bug 2 (missing leaders for KRX markets), `ll_score` defaults to `0.0`.
3. Due to cache mismatch, regression models are not loaded, and training fails, so `reg_score` defaults to `0.0`.
4. As a result, the weighted sum `ensemble_score` becomes `0.0` for all KRX stocks.
5. The `ensemble_expected_return` is calculated as `0.0 * 20.0 = 0.0%`.

#### 3. Proposed Code Changes
* No direct code changes are needed in `ensemble_scorer.py` to fix this bug. Resolving Bug 1, 2, and 3 will naturally populate all inputs with non-zero scores, resolving Bug 4.

---

### Requirement 5: Output File Placeholder When Empty

#### 1. Observational Evidence
* **Conditional File Writing:**
  In `trading_system/run_pipeline.py`, files are only saved if the DataFrames are not empty:
  ```python
  if not surge_df.empty:
      surge_output_path = os.path.join(result_dir, "surge_predictions.txt")
      ...
  ```
  If predictions are empty, the files do not exist on disk.
* **GHA Step Failure / Missing Assets:**
  When `Rename output files to avoid conflicts` step in `pipeline.yml` runs:
  ```yaml
        run: |
          mkdir -p trading_system/result_split
          for f in pipeline_result surge_predictions lead_lag_predictions vcp_patterns vcp_ml_predictions ensemble_predictions; do
            src="trading_system/result/${f}.txt"
            if [ -f "$src" ]; then
              cp "$src" "trading_system/result_split/${f}_${{ matrix.target }}.txt"
            fi
          done
  ```
  The target files are not found and thus not renamed or uploaded, causing warnings or empty release assets.

#### 2. Logic Chain
1. Empty predictions cause file creation to be skipped.
2. The GHA run complains about missing files during renaming/uploading.
3. To comply with requirements (R4) and ensure reliable pipelines, the output files must always exist.

#### 3. Proposed Code Changes
Modify `run_pipeline.py` to always write prediction output files. If the predictions are empty, write a file containing the standard header and a descriptive placeholder message.

##### Change C: Modify `run_pipeline.py` file saving blocks
* **Surge Predictions (lines 1217-1245):**
  ```python
      # Save surge detection results to separate file
      surge_output_path = os.path.join(result_dir, "surge_predictions.txt")
      with open(surge_output_path, "w", encoding="utf-8") as f:
          f.write("=== Surge Detection Results (>= 20% return) ===\n")
          f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
          f.write(f"Threshold: >= {model.surge_threshold*100:.0f}%\n")
          if surge_df.empty:
              f.write("\nNo surge candidates found today.\n")
          else:
              f.write(f"Total symbols: {len(surge_df)}\n\n")
              # Merge name/market info
              surge_df = surge_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
              ... (existing write logic)
  ```

* **Lead-Lag Predictions (lines 1259-1305):**
  ```python
      # Save lead-lag predictions to separate file
      lead_lag_output_path = os.path.join(result_dir, "lead_lag_predictions.txt")
      with open(lead_lag_output_path, "w", encoding="utf-8") as f:
          f.write("=== Lead-Lag Surge Predictions ===\n")
          f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
          if lead_lag_df.empty:
              f.write("\nNo lead-lag predictions generated today.\n")
          else:
              lead_lag_df = lead_lag_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
              # P1: clip correlation index to [0, 1]
              lead_lag_df = lead_lag_df.copy()
              lead_lag_df['lead_lag_score'] = lead_lag_df['lead_lag_score'].clip(0.0, 1.0)
              f.write(f"Based on today's top {len(model.lead_lag_leaders)} leader stock movements\n")
              f.write("Metric: Lead-Lag Pearson Correlation Index [0.0 ~ 1.0]\n")
              f.write("        (Higher = stronger historical co-movement with market leaders)\n\n")
              ... (existing write logic)
  ```

* **VCP Patterns (lines 1308-1334):**
  ```python
      # Save VCP pattern detection results
      vcp_output_path = os.path.join(result_dir, "vcp_patterns.txt")
      with open(vcp_output_path, "w", encoding="utf-8") as f:
          f.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
          f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
          if not vcp_results:
              f.write("\nNo VCP patterns detected today.\n")
          else:
              f.write(f"Total VCP patterns found: {len(vcp_results)}\n\n")
              vcp_universe_map = {s: (n, m) for s, n, m in zip(universe['symbol'], universe['name'], universe['market'])}
              ... (existing write logic)
  ```

* **VCP ML Predictions (lines 1341-1365):**
  ```python
      # Save VCP ML predictions
      vcp_ml_output_path = os.path.join(result_dir, "vcp_ml_predictions.txt")
      with open(vcp_ml_output_path, "w", encoding="utf-8") as f:
          f.write("=== VCP ML Surge Predictions ===\n")
          f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
          if vcp_ml_df.empty:
              f.write("No VCP ML predictions generated today.\n")
          else:
              vcp_ml_df = vcp_ml_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left', suffixes=('', '_univ'))
              ... (existing write logic)
  ```
