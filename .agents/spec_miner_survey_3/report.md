# Specification Mining Report: Dynamic Slippage Model, OMS Guardrails, and CI/CD Build Artifact Archiving

**Agent**: Spec Miner 3  
**Working Directory**: `d:/Finance/code/stock/.agents/spec_miner_survey_3`  
**Target Codebase**: `d:/Finance/code/stock`  
**Date**: 2026-08-12  

---

## Executive Summary & Scope

This specification mining report covers:
1. **R3: Dynamic Slippage Model & OMS Portfolio Guardrails**:
   - Technical breakdown of `MicrostructureCostModel` (`trading_system/src/risk/microstructure.py`).
   - Integration design for Intraday ATR and ADV-dependent scaling.
   - Enforcement of portfolio allocation guardrails (single stock $\le 5\%$, sector $\le 20\%$) across `PortfolioAllocator` (`trading_system/src/risk/portfolio_allocator.py`) and `ExecutionOMSEngine` (`trading_system/src/execution/oms_engine.py`).
   - Compliance logging schema and implementation in `trade_logs.db`.
2. **R4 (CI/CD portion): CI/CD Build Artifact Archiving**:
   - Examination of GitHub Actions workflows in `.github/workflows/` (`pipeline.yml`, `training.yml`, `pytest.yml`, `preseed.yml`, `realtime_monitor.yml`, `weekly_hpo.yml`).
   - Generation, merging, and deployment flow for `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, and `index.html`.
   - Workflow specification for artifact archiving.
3. **Existing Unit Tests Audit**:
   - Audit of `trading_system/tests/test_microstructure.py`, `trading_system/tests/test_portfolio_optimizer_and_oms.py`, and related test modules.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Microstructure | Square-root Market Impact Model | Calculates execution friction using square-root participation model: $\text{Impact} = \gamma \times \sigma_{\text{daily}} \times \sqrt{\frac{\text{Order}}{\text{ADV}}}$ | `order_amount`, `adv`, `volatility` | `float` (impact ratio) | Fallback to 5 bps (0.0005) if `adv <= 0` or `order_amount <= 0` | `trading_system/src/risk/microstructure.py:64-71` |
| 2 | Microstructure | Dynamic Bid-Ask Half-Spread | Estimates spread based on price level & volatility: $\max(\text{base\_pct}, (0.0002 + 0.02 \sigma) \times \text{price\_factor})$ | `volatility`, `price`, `market` | `float` (half-spread pct) | Returns `base_spread_pct` (0.05%) if `price <= 0` | `trading_system/src/risk/microstructure.py:54-62` |
| 3 | Microstructure | Statutory Tax & Fee Rates | Computes KRX STT (0.18% KOSPI/KOSDAQ, 0.08% KONEX) and US SEC fee (0.00278%) + brokerage fees | `market`, `is_sell` | `float` (tax+fee rate) | Default fallback to KOSPI STT + brokerage fee | `trading_system/src/risk/microstructure.py:38-52` |
| 4 | Microstructure | Net Expected Return Adjustment | Subtracts total transaction friction (tax + half-spread + impact) from gross expected return | `gross_return`, `symbol`, `market`, `price`, `volatility`, `order_amount`, `adv` | `float` (net return) | Uses friction fallback when inputs invalid | `trading_system/src/risk/microstructure.py:90-110` |
| 5 | Portfolio Risk | Single Stock Exposure Constraint | Restricts individual asset allocation upper bound in portfolio optimizer | `weights`, `max_weight` | Dict[`symbol`, `weight`] | Currently defaults to 0.20 (20%) instead of requirement $\le 5\%$ (0.05) | `trading_system/src/risk/portfolio_allocator.py:33, 194-228` |
| 6 | Portfolio Risk | Sector Exposure Constraint | Restricts total sector exposure to prevent over-concentration | `weights`, `sector_map`, `regime`, `max_sector_cap` | Dict[`symbol`, `weight`] | Currently caps sector at 0.25 (BEAR) or 0.35 (BULL) instead of requirement $\le 20\%$ (0.20) | `trading_system/src/risk/portfolio_allocator.py:34, 482-536` |
| 7 | OMS Execution | Order Execution Plan Generation | Converts top strategy predictions & portfolio weights into validated order plan entries | `top_predictions`, `portfolio_weights`, `total_capital`, `crisis_level` | List[Dict] order plans | Blocks all orders if kill switch active or `crisis_level == 'SEVERE'` | `trading_system/src/execution/oms_engine.py:88-193` |
| 8 | OMS Execution | Trade Execution & Slippage Logging | Records fill prices in `execution_logs` table and computes realized slippage in bps | `order_id`, `symbol`, `target_price`, `executed_price`, `executed_volume` | Dict execution summary | `slippage_bps = 0.0` if `target_price <= 0` | `trading_system/src/execution/oms_engine.py:195-236` |
| 9 | OMS Execution | Compliance Guardrail Audit Logging | Database table/column to audit single-stock ($\le 5\%$) and sector ($\le 20\%$) compliance | `order_plans`, `portfolio_weights`, `sector_map` | DB records in `trade_logs.db` | Currently missing compliance table / columns | `trading_system/src/execution/oms_engine.py:32-73` |
| 10 | CI/CD Pipeline | Per-Market Pipeline Execution & Split Artifact Upload | Matrix build for 5 markets; saves prediction files and uploads `result-${market}` artifacts | Matrix `target` in [SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ] | Split `.txt` & `.json` files | `continue-on-error: true` on download; halts if 0 markets succeed | `.github/workflows/pipeline.yml:15-203` |
| 11 | CI/CD Pipeline | Prediction Output Merging & Release Upload | Merges split market results via `merge_predictions.py`, uploads `merged-results` artifact & GH release assets | `result_*` directories | `trading_system/result/` files | Skips release creation if no text files found | `.github/workflows/pipeline.yml:204-315` |
| 12 | CI/CD Pipeline | HTML Dashboard Build & GHA Pages Deployment | Generates `gh-pages/index.html` via `generate_report.py`, uploads Pages artifact, deploys to GitHub Pages | `trading_system/result/` | `gh-pages/index.html`, GHA Pages deploy | Aborts deployment if merged result files missing | `.github/workflows/pipeline.yml:317-378` |

---

## Edge Cases

| # | Feature | Input | Observed / Expected Behavior |
|---|---------|-------|-------------------|
| 1 | `MicrostructureCostModel` | `adv <= 0` or `order_amount <= 0` | `calculate_market_impact` returns `0.0005` (5 bps fallback). |
| 2 | `MicrostructureCostModel` | High intraday volatility with missing ATR | Falls back to daily volatility derived from annualized volatility `volatility / sqrt(252)`. |
| 3 | `MicrostructureCostModel` | Order size participation rate $> 100\%$ of ADV | Participation rate is clamped at `1.0`, avoiding infinite / imaginary impact calculations. |
| 4 | `PortfolioAllocator` | Sector map missing / empty | `apply_sector_and_factor_constraints` falls back to normalizing weights without sector capping. |
| 5 | `PortfolioAllocator` | Asset weight exceeds $5\%$ or sector weight exceeds $20\%$ | Rescaling iteratively scales down over-concentrated items while preserving relative ranking. |
| 6 | `ExecutionOMSEngine` | Target stock price is outside $[\text{KRW } 1.0, \text{KRW } 100,000,000]$ | Plan generation drops symbol to protect against corrupt or missing price data. |
| 7 | `ExecutionOMSEngine` | Upstream corrupt ticker symbol (e.g. stringified dict) | Regex validator `_validate_symbol` drops invalid symbols. |
| 8 | `ExecutionOMSEngine` | Crisis level `SEVERE` or active Kill Switch | Order plan generation returns an empty list immediately without accessing DB. |
| 9 | CI/CD Pipeline | Matrix market pipeline fails for 1 of 5 markets | `merge-and-release` job continues using results from remaining 4 markets and merges them cleanly. |
| 10 | CI/CD Pipeline | All 5 market pipelines fail | `merge-and-release` guard detects `FOUND != 1`, outputs error, and halts deployment without publishing stale data. |

---

## Detailed Investigation 1: R3 - Dynamic Slippage Model & OMS Portfolio Guardrails

### 1.1 Microstructure Cost Model Breakdown (`trading_system/src/risk/microstructure.py`)

#### Current Implementation Analysis
- **File Path**: `trading_system/src/risk/microstructure.py` (Note: `PROJECT.md` references `src/core/microstructure.py`, but the actual Python implementation resides at `trading_system/src/risk/microstructure.py`).
- **Classes**:
  1. `TransactionCostConfig` (lines 20–30):
     - `kospi_stt_rate`: `0.0018` (0.18% STT tax)
     - `kosdaq_stt_rate`: `0.0018` (0.18% STT tax)
     - `konex_stt_rate`: `0.0008` (0.08% STT tax)
     - `brokerage_fee_rate`: `0.00035` (0.035% KRX fee)
     - `us_sec_rate`: `0.0000278` (0.00278% SEC regulatory fee)
     - `us_brokerage_fee_rate`: `0.00005` (0.005% US fee)
     - `base_spread_pct`: `0.0005` (0.05% base half-spread)
     - `market_impact_gamma`: `0.1` (Kyle's Lambda / square-root coefficient)
  2. `MicrostructureCostModel` (lines 32–111):
     - `get_tax_fee_rate(market: str, is_sell: bool = True) -> float` (lines 38–52): Resolves exchange tax & fee.
     - `calculate_bid_ask_spread(volatility: float, price: float, market: str = "KOSPI") -> float` (lines 54–62): Computes half-spread percentage.
     - `calculate_market_impact(order_amount: float, adv: float, volatility: float) -> float` (lines 64–71):
       $$\text{impact} = \gamma \times \text{daily\_vol} \times \sqrt{\frac{\text{order\_amount}}{\text{adv}}}$$
       where $\text{daily\_vol} = \max(0.005, \frac{\text{volatility}}{\sqrt{252}})$.

#### Limitations in Current Model
1. **No Intraday ATR Integration**: `calculate_market_impact` only receives annualized volatility (`volatility`) and converts it via $\sqrt{252}$. It cannot account for intraday volatility surges or ATR (Average True Range) expansion.
2. **Linear Participation Scaling**: Square-root model uses linear participation rate without non-linear penalty for high ADV participation (e.g. when order size exceeds $5\%$ or $10\%$ of ADV).

#### Design for Enhancing `MicrostructureCostModel`
1. **Intraday ATR Parameter & Scaling**:
   - Signature update:
     ```python
     def calculate_market_impact(
         self,
         order_amount: float,
         adv: float,
         volatility: float,
         atr: Optional[float] = None,
         price: Optional[float] = None,
         intraday_atr_pct: Optional[float] = None
     ) -> float
     ```
   - Logic: If `intraday_atr_pct` is provided or `(atr is not None and price > 0)`, use $\text{vol\_factor} = \max(0.005, \frac{\text{atr}}{\text{price}})$. Multiply base gamma by $\frac{\text{vol\_factor}}{\text{daily\_vol}}$ to dynamically scale market impact during high-volatility intraday windows.
2. **ADV-Dependent Non-Linear Penalty**:
   - Introduce participation rate threshold parameter `adv_penalty_threshold: float = 0.05` in `TransactionCostConfig`.
   - If $\text{participation\_rate} = \frac{\text{order\_amount}}{\text{adv}} > 0.05$, apply non-linear impact acceleration factor:
     $$\text{impact\_mult} = 1.0 + 2.0 \times (\text{participation\_rate} - 0.05)^{1.5}$$
     $$\text{impact} = \gamma \times \text{vol\_factor} \times \sqrt{\text{participation\_rate}} \times \text{impact\_mult}$$

---

### 1.2 Portfolio Allocation Guardrails (`trading_system/src/risk/portfolio_allocator.py` & `trading_system/src/execution/oms_engine.py`)

#### Single Stock ($\le 5\%$) & Sector ($\le 20\%$) Analysis
- **Current State in `PortfolioAllocator`** (`trading_system/src/risk/portfolio_allocator.py`):
  - Line 33: `default_max_weight: float = 0.20` (defaults to $20\%$ max weight per asset).
  - Line 34: `default_max_sector_weight: float = 0.35` (defaults to $35\%$ max sector weight).
  - Lines 501–504: `apply_sector_and_factor_constraints` uses `sector_cap = 0.35` in BULL market and `0.25` in BEAR/SIDEWAYS.
- **Requirement R3 Constraint Guardrails**:
  - **Single Stock Maximum Weight**: Must be enforced at $\le 5\%$ ($0.05$).
  - **Sector Maximum Weight**: Must be enforced at $\le 20\%$ ($0.20$).

#### Specification for Updating `PortfolioAllocator`:
1. Change default `default_max_weight` from `0.20` to `0.05` in `PortfolioAllocator.__init__`.
2. Change default `default_max_sector_weight` from `0.35` to `0.20` in `PortfolioAllocator.__init__`.
3. In `apply_sector_and_factor_constraints`, enforce `max_sector_cap` upper bound at `0.20` regardless of regime unless explicitly overridden.

---

### 1.3 Compliance Recording in `trade_logs.db`

#### Current State in `ExecutionOMSEngine` (`trading_system/src/execution/oms_engine.py`):
- `_init_db()` creates tables:
  - `order_plans` (`order_id`, `symbol`, `name`, `market`, `action`, `target_weight`, `target_amount`, `target_price`, `quantity`, `status`, `created_at`).
  - `execution_logs` (`execution_id`, `order_id`, `symbol`, `target_price`, `executed_price`, `slippage_bps`, `executed_volume`, `executed_at`).
- **Missing**: There is currently no record of single-stock limit compliance ($\le 5\%$) or sector limit compliance ($\le 20\%$).

#### Compliance Table & Migration Specification:
1. **Schema Update in `_init_db()`**:
   - Create table `portfolio_compliance_logs`:
     ```sql
     CREATE TABLE IF NOT EXISTS portfolio_compliance_logs (
         compliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
         timestamp TEXT NOT NULL,
         total_symbols INTEGER NOT NULL,
         max_single_stock_weight REAL NOT NULL,
         single_stock_compliant INTEGER NOT NULL, -- 1 if all <= 0.05 else 0
         max_sector_weight REAL NOT NULL,
         sector_compliant INTEGER NOT NULL,       -- 1 if all sectors <= 0.20 else 0
         violations_json TEXT NOT NULL
     );
     ```
   - Add columns to `order_plans` via safe migration:
     ```sql
     ALTER TABLE order_plans ADD COLUMN single_stock_compliant INTEGER DEFAULT 1;
     ALTER TABLE order_plans ADD COLUMN sector_name TEXT DEFAULT 'UNKNOWN';
     ALTER TABLE order_plans ADD COLUMN sector_weight REAL DEFAULT 0.0;
     ALTER TABLE order_plans ADD COLUMN sector_compliant INTEGER DEFAULT 1;
     ```
2. **Execution Method in `ExecutionOMSEngine`**:
   - Add `audit_and_record_compliance(portfolio_weights: Dict[str, float], sector_map: Optional[Dict[str, str]] = None)` method that verifies each stock $\le 0.05$ and each sector total weight $\le 0.20$, logs compliance status to `portfolio_compliance_logs`, and populates compliance fields when `generate_order_plan` creates order records.

---

## Detailed Investigation 2: R4 - CI/CD Build Artifact Archiving

### 2.1 Examination of `.github/workflows/`

The repository contains 6 GitHub Actions workflows in `.github/workflows/`:
1. `pipeline.yml`: Daily automated execution matrix (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
2. `training.yml`: Weekly model retraining pipeline.
3. `pytest.yml`: Continuous integration tests, type checking, security auditing, and code coverage.
4. `preseed.yml`: Initial market data pre-seeding pipeline.
5. `realtime_monitor.yml`: Real-time market monitoring.
6. `weekly_hpo.yml`: Hyperparameter optimization schedule.

### 2.2 Output File Generation, Merging, and Deployment Flow

In `pipeline.yml`:
1. **Job 1 (`run-pipeline`)**:
   - Matrix runs `trading_system/run_pipeline.py` for each `matrix.target`.
   - Generates 25+ strategy result `.txt` files in `trading_system/result/`.
   - Renames files into `trading_system/result_split/{file}_{target}.txt` (lines 180–194).
   - Uploads `result-${matrix.target}` artifact via `actions/upload-artifact@v4` with `retention-days: 7` (lines 196–203).
2. **Job 2 (`merge-and-release`)**:
   - Downloads split results `result-SP500`, `result-KOSPI`, `result-KOSDAQ`, `result-NASDAQ`, `result-RUSSELL2000`.
   - Executes `python3 trading_system/merge_predictions.py` (lines 263–276) to construct unified files in `trading_system/result/`:
     - `ensemble_predictions.txt`
     - `strategy_data_coverage_report.txt`
     - `pipeline_result.txt`
     - 22 other strategy prediction files.
   - Uploads `merged-results` artifact via `actions/upload-artifact@v4` (lines 277–284).
   - Creates GitHub Release (`vYYYY-MM-DD`) and uploads asset `.txt` files (lines 285–315).
3. **Job 3 (`deploy-pages`)**:
   - Downloads `merged-results` artifact into `trading_system/result`.
   - Runs `.venv/bin/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html`.
   - Copies `pipeline_result.txt` into `gh-pages/`.
   - Uploads GitHub Pages artifact via `actions/upload-pages-artifact@v3` (path: `gh-pages/`).
   - Deploys dashboard to GitHub Pages via `actions/deploy-pages@v4`.

### 2.3 Required Workflow Modification for R4 Build Artifact Archiving

To fulfill R4 ("Update GitHub Actions workflows to archive output files (`ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, `index.html`) as build artifacts"):

Add an explicit build artifact archiving step in `pipeline.yml` inside `deploy-pages` (after `generate_report.py` execution):

```yaml
- name: Archive build output artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: build-prediction-artifacts
    path: |
      trading_system/result/ensemble_predictions.txt
      trading_system/result/strategy_data_coverage_report.txt
      gh-pages/index.html
    retention-days: 30
```

---

## Detailed Investigation 3: Unit Test Suite Audit

### 3.1 Existing Tests Audit

1. **`trading_system/tests/test_microstructure.py`**:
   - Current tests:
     - `test_tax_fee_rates`: Tests `get_tax_fee_rate` for KOSPI buy/sell and SP500 sell.
     - `test_net_expected_return`: Tests `net_expected_return` with basic parameters.
   - **Gaps**: Does NOT test ATR-based scaling or ADV penalty threshold scaling.
2. **`trading_system/tests/test_portfolio_optimizer_and_oms.py`**:
   - Current tests:
     - `test_portfolio_optimizer_risk_parity`: Tests risk parity weights.
     - `test_factor_and_sector_constraints`: Tests sector cap constraint.
     - `test_execution_oms_engine`: Tests order plan generation and execution slippage calculation.
     - `test_oms_rejects_dict_string_symbols`: Tests symbol regex safety.
     - `test_oms_skips_plans_without_explicit_price`: Tests price bounds.
     - `test_oms_blocks_all_plans_in_severe_crisis`: Tests crisis gating.
     - `test_oms_rejects_out_of_bounds_prices`: Tests price validation.
     - `test_oms_kill_switch_blocks_all_plans`: Tests kill switch integration.
     - `test_oms_quantity_conversion_and_lot_rounding`: Tests share lot rounding.
   - **Gaps**:
     - Does NOT test $\le 5\%$ single stock limit or $\le 20\%$ sector cap limit.
     - Does NOT test compliance table/column logging in `trade_logs.db`.

### 3.2 Required Test Suite Extensions

When implementing M3 (Dynamic Slippage & OMS Guardrails), the following unit tests must be added to `trading_system/tests/test_microstructure.py` and `trading_system/tests/test_portfolio_optimizer_and_oms.py`:

1. `test_microstructure_atr_and_adv_scaling()`: Verify that providing high `atr` increases calculated market impact compared to baseline, and providing order size $> 5\%$ ADV triggers non-linear penalty factor.
2. `test_portfolio_allocator_5pct_stock_and_20pct_sector_guardrails()`: Verify that single stock weights $> 0.05$ are scaled down to $\le 0.05$, and sector totals $> 0.20$ are scaled down to $\le 0.20$.
3. `test_oms_compliance_logging_to_trade_logs_db()`: Verify that `portfolio_compliance_logs` and `order_plans` compliance columns in `trade_logs.db` correctly record compliant vs non-compliant portfolio states.

---

## Conclusion & Action Plan for Downstream Implementers

1. **M3 Implementation Plan**:
   - Update `trading_system/src/risk/microstructure.py`: Add `atr`/`price` parameters, ATR volatility scaling, and non-linear participation rate impact scaling.
   - Update `trading_system/src/risk/portfolio_allocator.py`: Enforce `default_max_weight = 0.05` and `default_max_sector_weight = 0.20`.
   - Update `trading_system/src/execution/oms_engine.py`: Add `portfolio_compliance_logs` table schema and compliance columns to `order_plans`, and add compliance auditing method.
2. **M4 Implementation Plan**:
   - Update `.github/workflows/pipeline.yml`: Add `actions/upload-artifact@v4` step archiving `ensemble_predictions.txt`, `strategy_data_coverage_report.txt`, and `index.html`.
