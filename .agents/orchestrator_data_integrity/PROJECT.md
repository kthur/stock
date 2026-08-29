# Project: Data Integrity, RIM Engine Fix & Dashboard Health Monitor

## Architecture
- **Core Strategy Engines**: `trading_system/src/core/` (31 strategies including `rim_valuation.py`, `order_flow.py`, `iv_skew.py`, etc.)
- **AI Models & Adapters**: `trading_system/src/ai/` (`score_normalizer.py`, `ensemble_scorer.py`, `ml_strategy_adapters.py`)
- **Analysis & Coverage**: `trading_system/src/analysis/` (`coverage_analyzer.py`, `portfolio_optimizer.py`)
- **Data Layer & Ingestion**: `trading_system/src/data_layer/` (`earnings_data.py`, `indicator_storage.py`)
- **Reporting & Visualization**: `trading_system/generate_report.py`, `gh-pages/index.html`
- **Orchestration Pipeline**: `trading_system/run_pipeline.py`

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | Survey Codebase & Architecture | Map code structure, identify NaN sources, examine missingness handling | Survey | ORIGINAL_REQUEST §R1-R3 | DONE |
| 2 | RIM Valuation NaN & Metric Fix | Fix BPS/ROE/equity calculations, eliminate nan/nan% in output & predictions, tag status | M1 | ORIGINAL_REQUEST §R2 | DONE |
| 3 | 31-Strategy Pipeline Normalization & Missingness | Audit all 31 strategies across 5 markets, fix vcp_rule column, symbol normalization & missingness codes | M2 | ORIGINAL_REQUEST §R1 | DONE |
| 4 | Dashboard Health Monitor & Badges | Add strategy data status summary card, replace raw NaN with N/A badges, add tab notice banners | M3 | ORIGINAL_REQUEST §R3 | DONE |
| 5 | Full Test Suite & E2E Validation | Run `pytest tests/ -v`, verify all output files in `trading_system/result/` | M4 | ORIGINAL_REQUEST §Acceptance Criteria | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 0 | Survey | Full codebase investigation of RIM, 31 strategies, and reporting | none | DONE |
| 1 | M1: RIM Valuation Fix | `src/core/rim_valuation.py`, `run_pipeline.py` (`_write_rim_file`), `generate_report.py` (`parse_rim`), tests | Survey | DONE |
| 2 | M2: 31-Strategy Data Quality | `ml_strategy_adapters.py`, `coverage_analyzer.py`, 31 strategy outputs, tests | Survey | DONE |
| 3 | M3: Dashboard Health Monitor | `generate_report.py`, HTML/CSS/JS templates, badges, tab banners | M1, M2 | DONE |
| 4 | M4: E2E Regression & Outputs | Full test suite execution across all markets, output file verification | M1, M2, M3 | DONE |

## Interface Contracts
### RIM Valuation Engine
- Input: `df: pd.DataFrame` with columns `['bps', 'roe', 'Close', 'operating_income', 'net_income', ...]`
- Output: `pd.DataFrame` with `rim_filter_reason` set to explicit tags (`MISSING_FUNDAMENTALS`, `CAPITAL_IMPAIRMENT`, `LOW_EARNINGS_QUALITY`, `OPERATING_LOSS`, `PREFERRED_SHARE`), `rim_score` set to `np.nan` for invalid rows, text formatters outputting `N/A` instead of `nan%`.

### Strategy Coverage Analyzer
- Input: `ensemble_df`, `prices_dict`, `features_df`, `col_map` with correct `vcp_rule_score` column.
- Output: `strategy_data_coverage_report.txt` with accurate coverage rates and granular missingness reason codes.

### Report Generator
- Input: Pipeline results, strategy files, `strategy_data_coverage_report.txt`
- Output: `gh-pages/index.html` with Strategy Data Health Monitor hero card, universal `format_metric_cell()` badges, tab-level notice banners, zero raw `nan` / `None` / `undefined`.

## Code Layout
- `trading_system/src/core/`: Strategy engines (`rim_valuation.py`, etc.)
- `trading_system/src/ai/`: Adapters and scorers (`ml_strategy_adapters.py`, `ensemble_scorer.py`)
- `trading_system/src/analysis/`: Coverage and optimization (`coverage_analyzer.py`)
- `trading_system/generate_report.py`: HTML dashboard generator
- `trading_system/run_pipeline.py`: Pipeline execution and text file writers
- `tests/`: Automated unit and integration test suite
