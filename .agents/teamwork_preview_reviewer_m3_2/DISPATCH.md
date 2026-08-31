## 2026-08-31T15:30:42Z
Mission: Review Milestone 3 (R3: Metric Consolidation Accuracy & Data Integrity).
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and M3 Worker handoff.
2. Verify that all quantitative metrics (Regime 2D, Crisis Level, VIX velocity, Strategy Coverage, Missingness Reasons, CPCV/PBO, HRP Weights, EVT-CVaR, Leland Bands, Realized Slippage) accurately render without NaN, corrupt formatting, or missing keys.
3. Validate gh-pages/index.html generation: python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html.
4. Provide a clear verdict (APPROVE or REQUEST_CHANGES) with detailed rationale in your handoff.md.
5. Write your report to d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m3_2\review_report.md and a handoff.md.
6. Send a message to your caller parent with your verdict and summary.
