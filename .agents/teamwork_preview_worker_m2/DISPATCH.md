## 2026-08-29T14:02:32Z
You are worker_m2 for Milestone 2: Multi-Market Merge Synchronization.
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2

Please read:
- d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
- d:\Finance\code\stock\PROJECT.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_1\handoff.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. In `trading_system/merge_predictions.py`:
   - Implement robust multi-artifact market discovery in `main()` so markets are detected via any market-suffixed file (`*_{m}.txt`, `*_{m}.json`, dedicated split dirs like `result_{m}`, `result-{m}`, or multi-probe `[surge, pipeline_result, ensemble, rim, sentiment]`) rather than gating solely on surge files.
   - Refactor section extraction in `merge_ensemble_predictions()` with a robust multi-tier parser (`_extract_ensemble_market_section`) supporting flexible separators (`===`, `---`, varying border widths, line-by-line fallback) without leaking footers into market tables.
   - Expand header prefix matching in `merge_generic_strategy_files()` to include `Pair`, `No.`, `Symbol`, `Rank`, `Filters:` so Stat-Arb and portfolio table headers do not leak into data rows.
   - Standardize strategy list and darkpool merging.
   - Add `"KONEX"` to `KNOWN_MARKETS` if applicable.
2. In `tests/test_merge_generic_strategies.py`:
   - Expand unit and integration test suite to cover multi-market merge across all 31+ strategies, empty market handling, multi-probe market discovery, and section extraction.
3. Run tests using `.venv\Scripts\pytest.exe tests/test_merge_generic_strategies.py tests/test_report_generator_hrp.py tests/test_challenger_rim_2_stress.py -v`
4. Run `trading_system/merge_predictions.py` standalone and verify clean merge.
5. Document all changes, test commands, and passing results in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\handoff.md` and send a message back.
