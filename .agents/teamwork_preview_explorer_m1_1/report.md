# Milestone 1 Investigation & Implementation Report: GHA Pipeline & Model Integrity (R1)

**Investigator**: Teamwork Explorer (`teamwork_preview_explorer_m1_1`)  
**Date**: 2026-08-31  
**Scope**: Milestone 1 (R1: GitHub Actions Data Seeding & Model Training End-to-End Pipeline Integrity)  
**Target Files**:
- `.github/workflows/pipeline.yml`
- `.github/workflows/training.yml`
- `.github/workflows/preseed.yml`
- `.github/workflows/weekly_hpo.yml`
- `.github/workflows/realtime_monitor.yml`
- `.github/workflows/pytest.yml`
- `trading_system/download_db.py`
- `trading_system/run_pipeline.py`

---

## 1. Executive Summary

Milestone 1 focuses on ensuring the end-to-end data seeding, fetching, caching, model training, and inference pipeline integrity across all 5 core target markets (**SP500**, **NASDAQ**, **RUSSELL2000**, **KOSPI**, **KOSDAQ**) within GitHub Actions and local execution environments.

### Core Findings
1. **`pipeline.yml` Omissions Confirmed**:
   - **Step Summary (Line 193)**: `lstm_predictions.txt` is missing from the file existence and size reporting loop.
   - **GitHub Release Upload (Line 333-345)**: `lstm_predictions.txt` is omitted from the `for f in ...` upload list, preventing `lstm_predictions.txt` from being attached to GitHub Releases.
   - Note: In line 241 (the split rename loop) and in `merge_predictions.py` (line 874), `lstm_predictions` is already handled properly, confirming that this is purely an omission in the static summary and release lists.
2. **`training.yml` Caching Fallback Confirmed**:
   - **AI Models Cache (Lines 118-124)**: The `models-cache` step uses `key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}` without `restore-keys`. Adding `restore-keys` allows the job to restore the previous week's model checkpoint or preseeded model if today's exact key does not exist yet.
   - **uv Cache (Lines 82-87)**: Lacks `restore-keys` for fallback package cache reuse across minor lockfile adjustments.
3. **Workflow & Data Seeding Matrix/Path Audit**:
   - `preseed.yml`, `training.yml`, `pipeline.yml`, and `weekly_hpo.yml` have 100% consistent `CORE_5` matrix definitions (`["SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ"]`).
   - `download_db.py` artifact naming (`stock-databases-${target}`) perfectly aligns with `preseed.yml` artifact upload step (`name: stock-databases-${{ matrix.target }}`).
   - `trading_system/models` directory path resolution is uniform across all AI training modules (`OnDevicePredictionModel`, `VCPSurgePredictor`, `LSTMPredictor`, `ModelCacheManager`, `OptunaStrategyTuner`).

---

## 2. Exact Line Edits Confirmed

### 2.1 `.github/workflows/pipeline.yml`

#### Edit 1: Step Summary File List (Line 193)
- **Location**: `.github/workflows/pipeline.yml`, line 193
- **Context**: The `Write Step Summary` step iterates over prediction output files to display table metrics in GitHub Actions summary.
- **Canonical Strategy Position**: Strategy #6 (`lstm_predictions.txt`) should follow Strategy #5 (`vcp_ml_predictions.txt`) and precede Strategy #7 (`stat_arb_predictions.txt`).
- **Diff / Replacement**:
```yaml
<<<< CURRENT (Line 193)
          for f in ensemble_predictions.txt strategy_data_coverage_report.txt portfolio_allocation.txt pipeline_result.txt surge_predictions.txt lead_lag_predictions.txt vcp_patterns.txt vcp_ml_predictions.txt stat_arb_predictions.txt sector_predictions.txt rim_predictions.txt event_driven_predictions.txt mq_factor_predictions.txt iv_skew_predictions.txt order_flow_predictions.txt short_term_reversal_predictions.txt arm_factor_predictions.txt card_factor_predictions.txt latr_factor_predictions.txt inst_foreign_sector_predictions.txt supply_chain_predictions.txt sentiment_predictions.txt factor_neutralized_predictions.txt vol_target_predictions.txt microstructure_predictions.txt accruals_quality_predictions.txt short_squeeze_predictions.txt valueup_catalyst_predictions.txt trend_efficiency_predictions.txt gamma_squeeze_predictions.txt insider_buying_predictions.txt earnings_tone_drift_predictions.txt hft_order_flow_predictions.txt darkpool_predictions.txt dual_correction_predictions.txt index_rebalance_predictions.txt overnight_gap_predictions.txt pipeline_result.csv; do
==== PROPOSED (Line 193)
          for f in ensemble_predictions.txt strategy_data_coverage_report.txt portfolio_allocation.txt pipeline_result.txt surge_predictions.txt lead_lag_predictions.txt vcp_patterns.txt vcp_ml_predictions.txt lstm_predictions.txt stat_arb_predictions.txt sector_predictions.txt rim_predictions.txt event_driven_predictions.txt mq_factor_predictions.txt iv_skew_predictions.txt order_flow_predictions.txt short_term_reversal_predictions.txt arm_factor_predictions.txt card_factor_predictions.txt latr_factor_predictions.txt inst_foreign_sector_predictions.txt supply_chain_predictions.txt sentiment_predictions.txt factor_neutralized_predictions.txt vol_target_predictions.txt microstructure_predictions.txt accruals_quality_predictions.txt short_squeeze_predictions.txt valueup_catalyst_predictions.txt trend_efficiency_predictions.txt gamma_squeeze_predictions.txt insider_buying_predictions.txt earnings_tone_drift_predictions.txt hft_order_flow_predictions.txt darkpool_predictions.txt dual_correction_predictions.txt index_rebalance_predictions.txt overnight_gap_predictions.txt pipeline_result.csv; do
>>>>
```

#### Edit 2: GitHub Release Asset Upload List (Lines 333–345)
- **Location**: `.github/workflows/pipeline.yml`, lines 333–345
- **Context**: The `Create GitHub Release and Upload Assets` step uploads prediction `.txt` files to the tagged release.
- **Canonical Strategy Position**: Add `lstm_predictions.txt \` immediately after `vcp_patterns.txt vcp_ml_predictions.txt \`.
- **Diff / Replacement**:
```yaml
<<<< CURRENT (Lines 333-336)
            for f in pipeline_result.txt surge_predictions.txt lead_lag_predictions.txt \
                      vcp_patterns.txt vcp_ml_predictions.txt \
                      stat_arb_predictions.txt sector_predictions.txt \
                      rim_predictions.txt event_driven_predictions.txt mq_factor_predictions.txt \
==== PROPOSED (Lines 333-336)
            for f in pipeline_result.txt surge_predictions.txt lead_lag_predictions.txt \
                      vcp_patterns.txt vcp_ml_predictions.txt lstm_predictions.txt \
                      stat_arb_predictions.txt sector_predictions.txt \
                      rim_predictions.txt event_driven_predictions.txt mq_factor_predictions.txt \
>>>>
```

---

### 2.2 `.github/workflows/training.yml`

#### Edit 1: AI Models Cache `restore-keys` (Lines 118–124)
- **Location**: `.github/workflows/training.yml`, lines 118–124
- **Context**: Caching AI models (`trading_system/models`) after training.
- **Diff / Replacement**:
```yaml
<<<< CURRENT (Lines 118-124)
      - name: Cache AI models (Save after training)
        uses: actions/cache@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}
==== PROPOSED (Lines 118-127)
      - name: Cache AI models (Save after training)
        uses: actions/cache@v4
        id: models-cache
        with:
          path: trading_system/models
          key: ai-models-${{ matrix.target }}-${{ steps.date.outputs.date }}
          restore-keys: |
            ai-models-${{ matrix.target }}-
            ai-models-
>>>>
```

#### Edit 2: uv Package Cache `restore-keys` (Lines 82–87)
- **Location**: `.github/workflows/training.yml`, lines 82–87
- **Context**: Caching uv virtual environments and wheels across weekly training runs.
- **Diff / Replacement**:
```yaml
<<<< CURRENT (Lines 82-87)
      - name: Cache uv packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-uv-${{ hashFiles('trading_system/requirements.lock') }}
==== PROPOSED (Lines 82-89)
      - name: Cache uv packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/uv
          key: ${{ runner.os }}-uv-${{ hashFiles('trading_system/requirements.lock') }}
          restore-keys: |
            ${{ runner.os }}-uv-
>>>>
```

---

## 3. Workflow & Data Seeding Consistency Audit

| Workflow / Script | Matrix Targets | DB Caching Keys & Fallbacks | Model Caching Keys & Fallbacks | Path Consistency |
|-------------------|----------------|-----------------------------|--------------------------------|------------------|
| `pipeline.yml` | `CORE_5` (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) | `stock-prices-db-${target}-${date}-${run_id}` (`restore-keys` configured) | `ai-models-${target}-${date}` (restore-only with `restore-keys`) | `trading_system/models`, `trading_system/result` (100% compliant) |
| `training.yml` | `CORE_5` (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) | `stock-prices-db-${target}-${date}` (`restore-keys` configured) | `ai-models-${target}-${date}` (**Patch with `restore-keys`**) | `trading_system/models` (100% compliant) |
| `preseed.yml` | `ALL` (default) / `CORE_5` | `stock-prices-db-${target}-${date}` (`restore-keys` configured) | `ai-models-${target}-${date}` (`restore-keys` configured) | `trading_system/models`, `stock-databases-${target}` artifact (100% compliant) |
| `weekly_hpo.yml` | `CORE_5` | `stock-prices-db-${target}-${date}` (`restore-keys` configured) | `ai-models-${target}-${date}` (`restore-keys` configured) | `trading_system/models/*.json` artifact (100% compliant) |
| `realtime_monitor.yml` | Single (KRX) | `realtime-state-${date}` (`restore-keys` configured) | Downloads `ensemble_predictions.txt` from latest GitHub Release | `trading_system/realtime_state.db` (100% compliant) |
| `pytest.yml` | Single (Ubuntu, Py3.12) | N/A | N/A | Sets `PYTHONPATH: trading_system:trading_system/src:.` (100% compliant) |
| `download_db.py` | Resolves from `INFERENCE_TARGET` | Resolves `stock-databases-${target}` and handles Azure Blob 302 redirects | N/A | Extracts to `trading_system/stock_prices.db` & `trading_system/market_indicators.db` (100% compliant) |

---

## 4. Implementation Plan for Worker Agent

### Step 1: Apply Edits to `.github/workflows/pipeline.yml`
- Edit line 193 to add `lstm_predictions.txt`.
- Edit line 334 to add `lstm_predictions.txt \`.

### Step 2: Apply Edits to `.github/workflows/training.yml`
- Add `restore-keys:` under `Cache AI models` (line 124).
- Add `restore-keys:` under `Cache uv packages` (line 87).

### Step 3: Run Validation & Integrity Checks
- Run pytest suite: `.venv/bin/pytest tests/ -v`.
- Verify YAML syntax: parse `.github/workflows/pipeline.yml` and `training.yml` with Python yaml parser or action checker.
- Confirm all 8 model cache tests pass: `.venv/bin/pytest tests/test_model_cache_pipeline.py -v`.

---

## 5. Verification Method

1. **YAML Syntax Validation**:
   ```bash
   .venv/bin/python -c "import yaml; [yaml.safe_load(open(p, encoding='utf-8')) for p in ['.github/workflows/pipeline.yml', '.github/workflows/training.yml', '.github/workflows/preseed.yml']]; print('All YAML files valid')"
   ```
2. **Pytest Test Suite Execution**:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
3. **Model Cache Integrity Tests**:
   ```bash
   .venv/bin/pytest tests/test_model_cache_pipeline.py -v
   ```
