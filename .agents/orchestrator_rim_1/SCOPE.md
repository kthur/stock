# Scope: Strategy #9 RIM Valuation Engine & 5-Market Pipeline Fix

## Architecture
- `trading_system/src/core/rim_valuation.py`: Core RIM valuation engine (Residual Income Model, ROE normalization, holding company SOTP discount, EQ filter, type-safe vectorization).
- `trading_system/src/data_layer/indicator_storage.py`: SQLite WAL indicator and fundamental storage with auto-migration for `book_value`, `bps`, `total_debt`, `cash_equivalents`.
- `trading_system/run_pipeline.py`: Pipeline orchestration, background fundamental fetch synchronization, 5-market RIM prediction evaluation, and 12-column text report emission (`rim_predictions_{MARKET}.txt`).
- `trading_system/merge_predictions.py`: Merging 5 market files (`SP500`, `NASDAQ`, `RUSSELL2000`, `KOSPI`, `KOSDAQ`) into unified `rim_predictions.txt`.
- `trading_system/generate_report.py`: HTML dashboard generation parsing 12-column RIM predictions and rendering 5-market valuation tables.
- `tests/test_rim_strategy.py`, `tests/test_indicator_storage.py`, `tests/test_pipeline_integration.py`, `tests/test_e2e_consolidated.py`, `tests/test_challenger_rim_2_stress.py`, `tests/test_merge_generic_strategies.py`: Comprehensive test suite.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Scalar vs Series Type Safety | Safe Series handling for all columns (avoid `.fillna()` on scalar default) | M1 | Survey |
| 2 | Elimination of Fake BPS | Remove `eps / 0.08` and fake BPS; invalidate with `NaN` when genuine BPS missing | M1 | Survey |
| 3 | Operating-Profit ROE & EQ Gating | Authentic ROE normalization, EQ score, nonrecurring spike detection, SOTP discount | M1 | Survey |
| 4 | DB Auto-Migration | Auto-migrate `bps`, `total_debt`, `cash_equivalents` in SQLite `MarketIndicatorStorage` | M1 | Survey |
| 5 | Background Fundamental Sync | Ensure fundamental fetch completion before Strategy #9 inference | M1 | Survey |
| 6 | 5-Market Clean File Output | Produce non-empty `rim_predictions_{MARKET}.txt` for all 5 markets without exceptions | M1 | Survey |
| 7 | 12-Column HTML Dashboard | Update `parse_rim` and HTML generation in `generate_report.py` for 12 columns | M1 | Survey |
| 8 | 5-Market Prediction Merging | Header deduplication and metadata line filtering across 5 markets | M1 | Survey |
| 9 | Comprehensive Unit & E2E Tests | Pass all 1,409 tests in test suite | M1 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Core RIM Valuation & Pipeline Fix | `rim_valuation.py`, `indicator_storage.py`, `run_pipeline.py`, `generate_report.py`, `merge_predictions.py`, `tests/` | none | DONE |

## Code Layout
- `trading_system/src/core/rim_valuation.py`
- `trading_system/src/data_layer/indicator_storage.py`
- `trading_system/run_pipeline.py`
- `trading_system/generate_report.py`
- `trading_system/merge_predictions.py`
- `tests/test_rim_strategy.py`
- `tests/test_indicator_storage.py`
- `tests/test_challenger_rim_2_stress.py`
- `tests/test_merge_generic_strategies.py`
