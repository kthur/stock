## 2026-06-08T05:23:22+09:00
Please review the implementation of the Stock Screener and Dash dashboard UI:
1. Review `src/analysis/screener.py` (specifically `screen_global_outperformers`) and `src/web/dashboard.py` (specifically the 'Global Macro' tab and callbacks).
2. Verify that the Stock Screener returns exactly 10 US and 10 KR outperforming stocks with required fields (`ticker`, `expected_excess_return`, `correlation_to_exchange_rate`).
3. Verify that the Dash layout contains the 'Global Macro' tab (`id='global-macro-tab'`), a Plotly heatmap (`id='macro-correlation-heatmap'`), and the two DataTables (`id='us-outperformers-table'` and `id='kr-outperformers-table'`).
4. Verify that callback helpers `update_macro_correlation_heatmap` and `update_outperformers_table` are implemented, registered with callbacks, and run without runtime exceptions.
5. Verify the dashboard starts cleanly without errors.
6. Write your findings and review verdict to d:\Finance\code\stock\.agents\reviewer_macro_2\analysis.md and a handoff report at d:\Finance\code\stock\.agents\reviewer_macro_2\handoff.md.
