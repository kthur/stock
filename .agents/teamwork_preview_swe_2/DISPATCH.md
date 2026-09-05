## 2026-09-05T03:19:53Z

Fix GitHub Pages dashboard menu click unresponsiveness, market category corruption (69 abnormal category buttons like 'Acquisition', 'Corp', '1') in the Ensemble TOP list, and outdated 34-strategy labels (updating to 37 strategies) in the Korean & US stock automated trading system.

Working directory: d:/Finance/code/stock
Integrity mode: development
Python executable: d:\Finance\code\stock\.venv\Scripts\python.exe

## Requirements

### R1. Resolve Market Classification & Column Parsing Corruption in Portfolio Allocation and Ensemble Filtering
- In `trading_system/merge_predictions.py`, fix `merge_portfolio_allocation` so that it robustly parses both 8-column and 10-column table formats (with `Shares` and `Lot` columns). It must reliably extract the true stock `name` and valid `market` (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`), preventing lot numbers (`1`) or tokens of multi-word company names (`Sciences`, `Acquisition`, `Mellon`, `66`) from being parsed as the market identifier.
- In `trading_system/generate_report.py`, update `parse_portfolio_allocation` with the same robust token parsing, and enforce strict validation on `all_seen_markets` so that only verified markets in `KNOWN_ALL_MKTS` can ever generate market filter buttons and panels. This eliminates the 69 abnormal market category buttons (e.g., `🌐 Acquisition`, `🌐 Corp`, `🌐 1`) in the Ensemble TOP stock list.

### R2. Restore Full Navigation Menu and Filter Button Click Operability
- Ensure that clicking any menu tab, market filter button, column preset, quick filter chip, stock table row, and stock card reliably triggers its intended DOM action without silent failures or hidden panels.
- Ensure that `filterMarket(btn, 'ensemble')` smoothly shows/hides only the valid market panels (`all`, `KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`) without being obstructed by empty or corrupt fake market panels.
- Verify through headless browser automation (Edge CDP) that all clicking interactions on `gh-pages/index.html` succeed with zero JavaScript exceptions or unhandled rejections.

### R3. Synchronize Strategy Count Display Across Dashboard & Pipeline (37 Strategies)
- In `trading_system/generate_report.py`:
  - Update line 4094: Change `34-Strategy Ensemble scores mapped to expected returns` to `37-Strategy Ensemble scores mapped to expected returns`.
  - Update line 6086: Change `34-Factor Drawer lookup` to `37-Factor Drawer lookup`.
- In `trading_system/run_pipeline.py`:
  - Ensure the ensemble summary headers in lines 4190, 4227, 4275, 4282 dynamically reflect `len(_STRAT_DISPLAY_MAP)` (37 strategies) instead of raw dictionary lengths that might fluctuate.
- In `trading_system/src/ai/ensemble_scorer.py`:
  - Update `DeflatedSharpeRatioValidator(n_strategies=37, n_horizons=8)` and documentation strings from 34 to 37.
- Regenerate `gh-pages/index.html` and verify that all 37 strategy tabs, panels, radar charts, and drawer metrics accurately reflect 37 strategies.

## Acceptance Criteria

### Correct Market Filtering & Category Buttons
- [ ] In `gh-pages/index.html`, the Ensemble TOP stock list filter bar contains ONLY valid market buttons (`전체`, `KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`), with zero spurious company-name tokens or number buttons (`Acquisition`, `Corp`, `1`, `66`, etc.).
- [ ] In `trading_system/result/portfolio_allocation.txt`, the `Market` column contains only valid market codes (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`), and stock names with spaces (e.g. `Gilead Sciences`, `Johnson & Johnson`) are preserved intact.

### Menu & Click Interaction Operability
- [ ] Clicking on Row 1 navigation tabs (`Portfolio`, `Backtest`, `Regime Info`, `Scenario Simulator`, `Pipeline History`) smoothly switches active panels without console errors.
- [ ] Clicking on Row 2 strategy tabs (1..37) switches to the corresponding strategy panel.
- [ ] Clicking on any stock row or card properly opens the stock drawer with factor metrics and radar charts.
- [ ] Edge CDP browser automation test confirms all click handlers execute with zero exceptions.

### Strategy Count Consistency
- [ ] All strategy counts on the dashboard (titles, descriptions, Regime Detector Parameters, Health Monitor, Column Presets) consistently display 37 strategies.
- [ ] Pytest test suites (`tests/test_report_ux_and_rounding.py`, `tests/test_canonical_31_strategies.py`, `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_report_generator_hrp.py`) pass 100%.
