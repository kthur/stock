## 2026-06-08T05:23:22Z
You are teamwork_preview_challenger. Your working directory is d:\Finance\code\stock\.agents\challenger_macro_2\.
Please empirically challenge the Stock Screener and Dash UI tab:
1. Write a script or stress test to verify that `screen_global_outperformers` behaves correctly under offline fallback (lack of network/yfinance failure). Does it generate realistic mock data and still return exactly 10 US and 10 KR stocks with correct keys?
2. Verify the Dash UI callbacks with invalid arguments (e.g. passing empty lists or non-existent symbols to `update_macro_correlation_heatmap`, or non-existent country to `update_outperformers_table`). Does it fail gracefully?
3. Run the dashboard server using `run_dashboard.py` and verify it starts and app.server is exposed.
4. Write your empirical findings and results to d:\Finance\code\stock\.agents\challenger_macro_2\analysis.md and a handoff report at d:\Finance\code\stock\.agents\challenger_macro_2\handoff.md.
