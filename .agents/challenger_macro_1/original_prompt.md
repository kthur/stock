## 2026-06-07T20:23:22Z

You are teamwork_preview_challenger. Your working directory is d:\Finance\code\stock\.agents\challenger_macro_1\.
Please empirically challenge the Global Macro Correlation Engine and ML Predictor.
1. Write a script or stress test to verify the behavior of `calculate_cross_correlation` when given:
   - Completely missing/NaN datasets.
   - Datasets with varying lengths or non-overlapping timezones.
   - Out-of-bounds/extreme numbers.
2. Stress test `MacroPredictor` with edge case datasets (e.g. all constant values, all NaNs, very small dataset sizes, large number of features). Ensure that it does not crash, trains properly, and falls back correctly.
3. Check the robustness of the cached metrics JSON file `data/macro_model_metrics.json`.
4. Run the test suite and verify performance.
5. Write your empirical challenge findings and results to d:\Finance\code\stock\.agents\challenger_macro_1\analysis.md and a handoff report at d:\Finance\code\stock\.agents\challenger_macro_1\handoff.md.
