# Requirement 2 (R2) Codebase Audit Handoff Report

## 1. Observation

1. **`trading_system/generate_report.py` (lines 416–424)**:
   ```python
   def make_stock_link(symbol: str, market: str) -> str:
       if market in ['KOSPI', 'KOSDAQ', 'KONEX']:
           return f'<a href="https://finance.naver.com/item/main.naver?code={symbol}" target="_blank" class="stock-link">{symbol}</a>'
       else:
           # SP500 등 해외 주식
           s = symbol
           if not s.endswith('.O') and not s.endswith('.N') and not s.endswith('.A'):
               s = f"{s}.O"
           return f'<a href="https://m.stock.naver.com/worldstock/stock/{s}/total" target="_blank" class="stock-link">{symbol}</a>'
   ```
   *Observation*: Desktop Naver link is used for KRX (`finance.naver.com`). For SP500, `.O` is forcibly appended to foreign symbols (`worldstock/stock/{s}.O/total`), causing broken URLs for NYSE/AMEX stocks (e.g. `JPM.O`, `IBM.O`, `BRK.B.O`).

2. **`trading_system/generate_report.py` (lines 1012–1018)**:
   ```python
   ensemble = parse_ensemble(_read(result_dir / "ensemble_predictions.txt"))
   surge_date, surge_sections = parse_surge(_read(result_dir / "surge_predictions.txt"))
   vcp_date, vcp_rows = parse_vcp(_read(result_dir / "vcp_patterns.txt"))
   lag_date, follower_rows, leader_rows = parse_lead_lag(_read(result_dir / "lead_lag_predictions.txt"))
   vcp_ml_date, vcp_ml_sections = parse_vcp_ml(_read(result_dir / "vcp_ml_predictions.txt"))
   reg_date, reg_sections = parse_regression(_read(result_dir / "pipeline_result.txt"))
   ```
   *Observation*: `portfolio_allocation.txt` is completely ignored during report generation.

3. **`gh-pages/index.html` (Grep search for `canvas` or `Chart`)**:
   *Observation*: `grep_search` for `canvas` and `Chart` in `gh-pages/index.html` yielded zero results. There are no interactive JavaScript or Canvas charts rendered in the dashboard.

4. **`trading_system/result/portfolio_allocation.txt` (lines 1–15)**:
   ```
   === Portfolio Allocation Recommendations (Ensemble Kelly/Sharpe Optimized) ===
   Date: 2026-07-24 23:14
   Total Capital: 1,000,000,000 KRW/USD
   Target Horizon: 20d

   Current Market Regime Detected: SIDEWAYS (Code: 1)
   Maximum Total Allocation Allowed: 50.0%

   No. Symbol    Name                Market    Return    Volatility  Weight    Amount         
   --------------------------------------------------------------------------------------------
   1   007590    동방아그로               KOSPI         5.01%       0.42%     3.33%    33,333,333
   ```
   *Observation*: Valid HRP / Kelly portfolio position sizing results exist in `trading_system/result/portfolio_allocation.txt` but are unrendered in the web dashboard.

5. **`trading_system/src/risk/position_sizing.py` (lines 107–124)**:
   ```python
   if use_hrp:
       from src.analysis.portfolio_optimizer import calculate_hrp_weights
       symbols = df_candidates['symbol'].tolist()
       ...
       hrp_w = calculate_hrp_weights(cov_mat)
   ```
   *Observation*: `PortfolioAllocator` implements Hierarchical Risk Parity (`calculate_hrp_weights`).

---

## 2. Logic Chain

1. **Step 1 (Observation 1 -> Hyperlink Defect)**: `make_stock_link` uses desktop Naver links for KRX and blindly appends `.O` to SP500 symbols. On mobile devices, desktop Naver links have poor usability, and foreign stock symbols on NYSE/AMEX get broken URLs. Replacing them with Naver Mobile (`m.stock.naver.com/item/main.nhn?code={symbol}`) for KRX and Yahoo Finance (`finance.yahoo.com/quote/{symbol}`) for SP500 solves both usability and URL resolution.
2. **Step 2 (Observation 2 & 4 -> Missing HRP Tab)**: `run_pipeline.py` outputs `portfolio_allocation.txt` containing position sizes, expected return, volatility, weights, and cash reserves, but `generate_report.py` does not parse or display it. Adding a `parse_portfolio_allocation` function and a `Portfolio (HRP)` tab makes HRP recommendations visible on GitHub Pages.
3. **Step 3 (Observation 3 & 5 -> Chart Integration)**: The dashboard currently relies solely on static text tables. Adding responsive Chart.js Donut and Bar charts into the dashboard enables interactive visualization of HRP portfolio weights, asset allocations, and regime strategy weights.
4. **Step 4 (Regime Trend Integration)**: Current regime display is limited to a text badge (`🟡 SIDEWAYS`). Adding a `Regime & Strategy` tab with a regime parameter matrix and dynamic weight breakdown chart provides complete transparency into market regime behavior.

---

## 3. Caveats

- **Network Mode**: The environment operates in `CODE_ONLY` mode. External HTTP tools (`curl`, `wget`) cannot be called. The implementation will include Chart.js via standard CDN in the HTML template while providing a pure Canvas rendering script as a fallback.
- **Data Availability**: If `portfolio_allocation.txt` is missing or empty, `parse_portfolio_allocation` gracefully defaults to an empty `PortfolioData` object without crashing report generation.

---

## 4. Conclusion

Requirement 2 (R2) requires four clear enhancements:
1. Update `make_stock_link` to use Naver Mobile for KRX and Yahoo Finance for SP500.
2. Parse `portfolio_allocation.txt` and display HRP portfolio allocations.
3. Integrate interactive HRP allocation donut/bar charts and regime performance trend charts using Chart.js / Canvas.
4. Add `Portfolio (HRP)` and `Regime & Strategy` tabs to `gh-pages/index.html`.

All code changes are localized to `trading_system/generate_report.py`.

---

## 5. Verification Method

### A. Independent Verification Command
Run the report generator script and check output:
```bash
# Generate report using virtual environment
.venv/bin/python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html

# Verify contents
.venv/bin/python -c "
text = open('gh-pages/index.html', encoding='utf-8').read()
assert 'm.stock.naver.com' in text, 'Naver mobile link check failed'
assert 'finance.yahoo.com' in text, 'Yahoo Finance link check failed'
assert 'Portfolio (HRP)' in text, 'HRP portfolio tab check failed'
assert 'hrpWeightChart' in text, 'HRP chart canvas check failed'
print('ALL VERIFICATION CHECKS PASSED!')
"
```

### B. Invalidation Conditions
- Missing or invalid stock URL patterns in generated HTML.
- Unparsed `portfolio_allocation.txt` resulting in empty HRP table/chart.
- JavaScript syntax errors preventing chart rendering in browser console.
