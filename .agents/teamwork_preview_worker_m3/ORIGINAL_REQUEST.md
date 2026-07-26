## 2026-07-24T16:22:13Z

You are Worker 3 (`teamwork_preview_worker`) working in `.agents/teamwork_preview_worker_m3/`.
Your objective is to implement Requirement 2 (R2: GitHub Pages Dashboard & HRP UX Enhancement).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Create workspace directory `.agents/teamwork_preview_worker_m3/` if it doesn't exist.
2. Update `trading_system/generate_report.py`:
   - Mobile Stock Hyperlinks: Update `make_stock_link` so KRX symbols (KOSPI, KOSDAQ, KONEX) link to Naver Mobile (`https://m.stock.naver.com/item/main.nhn?code={symbol}`) and SP500 symbols link to Yahoo Finance (`https://finance.yahoo.com/quote/{symbol}`).
   - HRP Portfolio Allocation Tab (`parse_portfolio_allocation`): Read `portfolio_allocation.txt` or calculate HRP weights using `AssetAllocator` / `calculate_risk_parity_weights`, and render a "Portfolio (HRP)" tab with position weights, expected returns, volatility, and cash reserves.
   - Interactive Donut & Bar Charts: Embed Chart.js with responsive container for HRP allocation weights donut chart and market exposure bar chart in `gh-pages/index.html`.
   - Regime & Strategy Trends Tab: Add a "Regime & Strategy" tab rendering dynamic strategy weights per regime (1D and 2D) alongside regime reference parameters.
3. Test report generation: Run `generate_report.py` to produce `gh-pages/index.html` and verify size > 50KB with zero empty table warnings ("데이터 없음").
4. Create unit tests `trading_system/tests/test_report_generator_hrp.py` and run `.venv/bin/python -m pytest trading_system/tests/ -v`.
5. Run `.venv/bin/python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages` to verify output.
6. Write `.agents/teamwork_preview_worker_m3/changes.md` and `handoff.md`, and send a message to parent (Recipient: "parent") when completed.
