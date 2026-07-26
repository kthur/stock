# Quality Fixes Analysis Report

## Executive Summary
This report analyzes and diagnoses the 4 strategy output quality bugs in the stock prediction pipeline. We identify key cache mismatches, imbalanced leader selection logic, and model loading issues that lead to empty or zeroed strategy predictions for KRX markets, and propose precise code modifications to resolve them.

---

## Findings & Root Cause Analysis

### Bug 1: Surge Classifier Outputting 0.0% Probability
- **Observation**: The daily prediction pipeline outputs `0.0%` for surge predictions.
- **Evidence**:
  - In GHA daily pipeline (`.github/workflows/pipeline.yml`), `SKIP_TRAINING: 'True'` is set, forcing the system to load models from disk.
  - The cache restore key in `pipeline.yml` is:
    `key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`
  - However, in `training.yml`, the cache save key is:
    `key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}`
- **Logic Chain**:
  1. Because the date and target variables are reversed in the GHA cache keys, the daily pipeline fails to restore the trained models to `trading_system/models`.
  2. With the directory empty, the fallback check logic in `prediction_model.py`'s `load_surge_models` fails. It attempts to load `xgb_surge_model_krx_1d.json`, which does not exist because the models are saved per-market (e.g. `xgb_surge_model_kospi_1d.json`).
  3. Consequently, the prediction engine defaults the probability to `0.0` and logs:
     `"Surge prediction for market={mkt}, horizon={h} defaulted to 0.0 due to missing models."`
- **Proposed Fix**:
  1. Correct the cache save key in `training.yml` to put the target name before the date, matching `pipeline.yml`'s pattern:
     `key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`
  2. Modify the fallback check in `prediction_model.py`'s `load_models()` and `load_surge_models()` to check for individual market names: `['sp500', 'kospi', 'kosdaq', 'konex']` instead of `['sp500', 'krx']`.

---

### Bug 2: Lead-Lag Predictions Missing for KRX Markets
- **Observation**: No lead-lag predictions are generated for Korean stock markets (KOSPI/KOSDAQ/KONEX).
- **Evidence**:
  - In `prediction_model.py`'s `compute_lead_lag()` method, the top 50 leaders are selected globally using:
    `cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'`
    `avg_caps = df_train.groupby('symbol')[cap_col].mean()`
    `top_50_leaders = avg_caps.nlargest(50).index.tolist()`
- **Logic Chain**:
  1. In a combined training run (where `df_train` contains both SP500 and KRX symbols), using `norm_market_cap` introduces market imbalance.
  2. Because the SP500 contains 500 large, well-distributed stocks, many of them have `norm_market_cap` values above `0.01`. In contrast, the KR market has over 2800 symbols where Samsung Electronics represents ~20% of the entire capitalization, leaving almost all other KRX symbols with extremely small normalized market caps.
  3. Consequently, `avg_caps.nlargest(50)` selects almost exclusively US symbols (e.g., 45+ SP500 giants and at most 1-2 KOSPI symbols), leaving KOSDAQ and KONEX with zero representation in the leader list.
  4. In `predict_lead_lag()`, the system calculates follower scores by looking up the leader's returns. Since KRX has no leaders represented, no follower scores are calculated, leaving the KRX predictions empty.
- **Proposed Fix**:
  - Partition the leader selection logic in `compute_lead_lag()` to guarantee up to 50 leaders are selected from both KRX and US markets:
    ```python
    krx_caps = avg_caps[avg_caps.index.map(self.is_krx_symbol)]
    us_caps = avg_caps[~avg_caps.index.map(self.is_krx_symbol)]
    top_50_krx = krx_caps.nlargest(50).index.tolist() if not krx_caps.empty else []
    top_50_us = us_caps.nlargest(50).index.tolist() if not us_caps.empty else []
    top_50_leaders = top_50_krx + top_50_us
    ```

---

### Bug 3: VCP ML Predictions Empty
- **Observation**: The VCP Machine Learning prediction output file is empty or missing.
- **Evidence**:
  - `vcp_ml` is initialized as `vcp_ml = VCPSurgePredictor()` in `run_pipeline.py`.
- **Logic Chain**:
  1. Similar to Bug 1, due to the cache restore failure in GHA daily jobs, `vcp_ml.load_models()` finds no models on disk under `trading_system/models`.
  2. As a result, `vcp_ml.models` is empty.
  3. When predicting, the method returns an empty DataFrame if no models are loaded:
     ```python
     if not self.models:
         logger.warning("No VCP ML models loaded, skipping prediction")
         return pd.DataFrame()
     ```
- **Proposed Fix**:
  1. Fixing the GHA cache key mismatch will restore the models to the path.
  2. Additionally, explicitly pass the resolved `model_dir` to `VCPSurgePredictor` to prevent any directory drift:
     `vcp_ml = VCPSurgePredictor(model_dir=str(model.model_dir))`

---

### Bug 4: Ensemble Outputting 0% for KRX
- **Observation**: KRX ensemble recommendations show `0.0%` score and expected returns.
- **Logic Chain**:
  1. The ensemble scoring engine computes:
     `ensemble_score = reg_score * w_reg + surge_score * w_surge + ll_score * w_ll + vcp_ml_score * w_vcp`
  2. Because of the empty/missing models (Bugs 1 & 3) and the missing leader selection (Bug 2), the individual scores default to `0.0`.
  3. Consequently, the final ensemble score calculates to `0.0`, resulting in a `0.0%` output.
- **Proposed Fix**: Resolving Bugs 1-3 will automatically populate the individual strategy scores, fixing the ensemble output.

---

### Bug 5: Output File Placeholder when Empty
- **Observation**: If a strategy produces no results, the text files are not created, leading to GHA upload/merge step warnings.
- **Proposed Fix**: Ensure `run_pipeline.py` always writes a header and a "No candidates found" message to the output text files even if the dataframes are empty.

---

## Proposed Code Modifications

### 1. Cache Key Mismatch (`.github/workflows/training.yml`)
#### Before (Line 66):
```yaml
      - name: Cache AI models (Save after training)
        uses: actions/cache@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-v2-${{ steps.date.outputs.date }}-${{ matrix.target }}
```

#### After:
```yaml
      - name: Cache AI models (Save after training)
        uses: actions/cache@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}
```

---

### 2. Model Fallback Load Checks (`trading_system/src/ai/prediction_model.py`)
#### Before (Lines 440-441):
```python
            if not self.models:
                for market in ['sp500', 'krx']:
```
#### After:
```python
            if not self.models:
                for market in ['sp500', 'kospi', 'kosdaq', 'konex']:
```

#### Before (Lines 577-578):
```python
            if not self.surge_models:
                for market in ['sp500', 'krx']:
```
#### After:
```python
            if not self.surge_models:
                for market in ['sp500', 'kospi', 'kosdaq', 'konex']:
```

---

### 3. Lead-Lag Leader Selection (`trading_system/src/ai/prediction_model.py`)
#### Before (Lines 2082-2085):
```python
        logger.info("Selecting top 50 leaders by market cap...")
        cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
        avg_caps = df_train.groupby('symbol')[cap_col].mean()
        top_50_leaders = avg_caps.nlargest(50).index.tolist()
```

#### After:
```python
        logger.info("Selecting top 50 leaders by market cap...")
        cap_col = 'market_cap' if 'market_cap' in df_train.columns else 'norm_market_cap'
        avg_caps = df_train.groupby('symbol')[cap_col].mean()

        # Partition leaders by market to ensure representation of both KRX and US markets
        krx_caps = avg_caps[avg_caps.index.map(self.is_krx_symbol)]
        us_caps = avg_caps[~avg_caps.index.map(self.is_krx_symbol)]

        top_50_krx = krx_caps.nlargest(50).index.tolist() if not krx_caps.empty else []
        top_50_us = us_caps.nlargest(50).index.tolist() if not us_caps.empty else []

        top_50_leaders = top_50_krx + top_50_us
```

---

### 4. VCP ML Model Dir Alignment (`trading_system/run_pipeline.py`)
#### Before (Lines 712-713, 925-926):
```python
        from src.ai.vcp_ml_predictor import VCPSurgePredictor
        vcp_ml = VCPSurgePredictor()
```
#### After:
```python
        from src.ai.vcp_ml_predictor import VCPSurgePredictor
        vcp_ml = VCPSurgePredictor(model_dir=str(model.model_dir))
```

---

### 5. Output File Placeholders (`trading_system/run_pipeline.py`)
#### Before (Lines 1217-1219):
```python
    if not surge_df.empty:
        surge_output_path = os.path.join(result_dir, "surge_predictions.txt")
        with open(surge_output_path, "w", encoding="utf-8") as f:
```
#### After:
```python
    surge_output_path = os.path.join(result_dir, "surge_predictions.txt")
    with open(surge_output_path, "w", encoding="utf-8") as f:
        f.write("=== Surge Detection Results (>= 20% return) ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Threshold: >= {model.surge_threshold*100:.0f}%\n")
        if not surge_df.empty:
            f.write(f"Total symbols: {len(surge_df)}\n\n")
            # Merge name/market info
            surge_df_merged = surge_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
            krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
            for h in model.surge_horizons:
                col = f'surge_{h}d'
                if col not in surge_df_merged.columns:
                    continue
                for m in krx_markets + ['SP500']:
                    m_df = surge_df_merged[surge_df_merged['market'] == m].sort_values(by=col, ascending=False)
                    if m_df.empty:
                        continue
                    f.write(f"{'='*60}\n")
                    f.write(f"[{h}일] {m} Top 20 Surge Candidates\n")
                    f.write(f"{'='*60}\n")
                    for rank, (_, row) in enumerate(m_df.head(20).iterrows(), 1):
                        name = row.get('name', 'Unknown')
                        prob = row[col] * 100
                        f.write(f"  {rank}. [{m}] {row['symbol']} ({name}): {prob:.1f}%\n")
                    f.write("\n")
        else:
            f.write("Total symbols: 0\n\n")
            f.write("No surge candidates detected.\n")
```

#### Before (Lines 1259-1265):
```python
    if not lead_lag_df.empty:
        lead_lag_output_path = os.path.join(result_dir, "lead_lag_predictions.txt")
        ...
        with open(lead_lag_output_path, "w", encoding="utf-8") as f:
```
#### After:
```python
    lead_lag_output_path = os.path.join(result_dir, "lead_lag_predictions.txt")
    with open(lead_lag_output_path, "w", encoding="utf-8") as f:
        f.write("=== Lead-Lag Surge Predictions ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Based on today's top {len(model.lead_lag_leaders)} leader stock movements\n")
        f.write("Metric: Lead-Lag Pearson Correlation Index [0.0 ~ 1.0]\n")
        f.write("        (Higher = stronger historical co-movement with market leaders)\n\n")
        if not lead_lag_df.empty:
            lead_lag_df_merged = lead_lag_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
            lead_lag_df_merged['lead_lag_score'] = lead_lag_df_merged['lead_lag_score'].clip(0.0, 1.0)
            krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
            for m in krx_markets + ['SP500']:
                m_df = lead_lag_df_merged[lead_lag_df_merged['market'] == m].sort_values(by='lead_lag_score', ascending=False)
                if m_df.empty:
                    continue
                f.write(f"--- {m} Top 20 ---\n")
                for rank, (_, row) in enumerate(m_df.head(20).iterrows(), 1):
                    name = row.get('name', 'Unknown')
                    score = row['lead_lag_score'] * 100
                    f.write(f"  {rank}. [{m}] {row['symbol']} ({name}): {score:.2f}%\n")
                f.write("\n")
        else:
            f.write("No lead-lag predictions generated.\n")
```

#### Before (Lines 1308-1313):
```python
    if vcp_results:
        vcp_output_path = os.path.join(result_dir, "vcp_patterns.txt")
        ...
        with open(vcp_output_path, "w", encoding="utf-8") as f:
```
#### After:
```python
    vcp_output_path = os.path.join(result_dir, "vcp_patterns.txt")
    with open(vcp_output_path, "w", encoding="utf-8") as f:
        f.write("=== VCP (Volatility Contraction Pattern) Results ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        if vcp_results:
            f.write(f"Total VCP patterns found: {len(vcp_results)}\n\n")
            vcp_universe_map = {s: (n, m) for s, n, m in zip(universe['symbol'],
                                universe['name'], universe['market'])}
            krx_markets = ['KOSPI', 'KOSDAQ', 'KONEX']
            for m in krx_markets + ['SP500']:
                m_results = [r for r in vcp_results if vcp_universe_map.get(r['symbol'], ('', ''))[1] == m]
                if not m_results:
                    continue
                f.write(f"--- {m} ---\n")
                for rank, r in enumerate(m_results[:30], 1):
                    sym = r['symbol']
                    name, _market = vcp_universe_map.get(sym, ('Unknown', ''))
                    peaks = ' > '.join(f'{p:.1f}%' for p in r['contraction_peaks'])
                    f.write(f"  {rank}. [{m}] {sym} ({name})\n")
                    f.write(f"       Score: {r['vcp_score']:.0f}/100 | "
                            f"Current range: {r['current_range_pct']:.1f}% | "
                            f"Contraction: {peaks}\n")
                    f.write(f"       Above MA50: {'✓' if r['above_sma50'] else '✗'} | "
                            f"Above MA200: {'✓' if r['above_sma200'] else '✗'} | "
                            f"Near high: {'✓' if r['near_high'] else '✗'} | "
                            f"Volume declining: {'✓' if r['volume_declining'] else '✗'}\n\n")
        else:
            f.write("Total VCP patterns found: 0\n\n")
            f.write("No VCP patterns found.\n")
```

#### Before (Lines 1341-1344):
```python
    if not vcp_ml_df.empty:
        vcp_ml_df = vcp_ml_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left', suffixes=('', '_univ'))
        vcp_ml_output_path = os.path.join(result_dir, "vcp_ml_predictions.txt")
        with open(vcp_ml_output_path, "w", encoding="utf-8") as f:
```
#### After:
```python
    vcp_ml_output_path = os.path.join(result_dir, "vcp_ml_predictions.txt")
    with open(vcp_ml_output_path, "w", encoding="utf-8") as f:
        f.write("=== VCP ML Surge Predictions ===\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        if not vcp_ml_df.empty:
            vcp_ml_df_merged = vcp_ml_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left', suffixes=('', '_univ'))
            for h in SURGE_HORIZONS:
                col = f'vcp_{h}d'
                if col not in vcp_ml_df_merged.columns:
                    continue
                for market in ['KOSPI', 'KOSDAQ', 'KONEX', 'SP500']:
                    m_df = vcp_ml_df_merged[vcp_ml_df_merged['market'] == market].sort_values(by=col, ascending=False)
                    if m_df.empty:
                        if market in ['KOSPI', 'KOSDAQ', 'KONEX']:
                            f.write(f"[{h}일] {market} - (no symbols)\n\n")
                        continue
                    top_n = min(10, len(m_df))
                    f.write(f"[{h}일] {market} TOP {top_n}\n")
                    for rank, (_, row) in enumerate(m_df.head(top_n).iterrows(), 1):
                        name = row.get('name', 'Unknown')
                        prob = row[col] * 100
                        f.write(f"  {rank}. [{market}] {row['symbol']} ({name}): {prob:.1f}%\n")
                    f.write("\n")
        else:
            f.write("No VCP ML predictions generated.\n")
```
