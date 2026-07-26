# Changes Summary — Requirement 2 (R2: GitHub Pages Dashboard & HRP UX Enhancement)

## Summary of Modifications

### 1. `trading_system/generate_report.py`
- **Mobile Stock Hyperlinks (`make_stock_link`)**: Updated URL logic so KRX symbols (`KOSPI`, `KOSDAQ`, `KONEX`) link to Naver Mobile (`https://m.stock.naver.com/item/main.nhn?code={symbol}`) and `SP500` symbols link to Yahoo Finance (`https://finance.yahoo.com/quote/{symbol}`).
- **HRP Portfolio Allocation Parsing & Fallback (`parse_portfolio_allocation`)**: Added `PortfolioRow` and `PortfolioAllocationData` data models. Created `parse_portfolio_allocation` to read `portfolio_allocation.txt` with regular expression matching, and implemented `_generate_fallback_portfolio` using `calculate_hrp_weights` / `calculate_risk_parity_weights` from `src.analysis.portfolio_optimizer` when text is empty/missing.
- **Interactive Donut & Bar Charts**: Integrated Chart.js script (`https://cdn.jsdelivr.net/npm/chart.js`) and embedded responsive container cards rendering `hrpDonutChart` (HRP allocation weights donut chart) and `marketExposureChart` (Market exposure distribution bar chart).
- **Regime & Strategy Trends Tab**: Added "Regime & Strategy" tab rendering dynamic strategy weights per regime for 1D (BULL, SIDEWAYS, BEAR) and 2D (BULL_LOW_VOL, BULL_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BEAR_LOW_VOL, BEAR_HIGH_VOL) alongside GMM/Sharpe regime reference parameters.
- **CLI Argument Parsing**: Modified `main(args_list: Optional[list[str]] = None)` signature so `parser.parse_args(args_list)` supports programmatically passing command-line argument lists in unit tests without conflicting with `sys.argv`.

### 2. `trading_system/tests/test_report_generator_hrp.py`
- Added unit test suite with flexible `sys.path` configuration for test runners:
  - `test_make_stock_link_krx()` (Naver Mobile link verification)
  - `test_make_stock_link_sp500()` (Yahoo Finance link verification)
  - `test_parse_portfolio_allocation_valid()` (Parsing valid `portfolio_allocation.txt`)
  - `test_parse_portfolio_allocation_empty_fallback()` (HRP fallback weight calculation)
  - `test_build_html_contains_hrp_and_regime_tabs()` (Verifying HRP & Regime tabs, Chart.js canvases, and links)
  - `test_generated_report_size_and_no_empty_warning()` (Verifying `gh-pages/index.html` size > 50KB and zero empty table warnings via `main([])`).

## Verification Results
- `generate_report.py`: Output `gh-pages/index.html` size is **598 KB** (> 50KB required) with **0** empty table warnings ("데이터 없음").
- `pytest`: 69/69 passed (`.venv/bin/python -m pytest trading_system/tests/ -v`).
- Artifact Verifier: `verify_gha_artifacts.py` reported **PASSED** across all 4 markets and 5 strategies.
