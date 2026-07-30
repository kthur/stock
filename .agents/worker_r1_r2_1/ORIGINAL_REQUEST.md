## 2026-07-30T01:39:23Z
You are Worker 1 assigned to Requirement 1 (R1) unit test verification and Requirement 2 (R2) Precision Order Book Market Impact Cost Modeling.
Working directory: D:\Finance\code\stock\.agents\worker_r1_r2_1

Read the exploration findings and specifications from:
- D:\Finance\code\stock\.agents\explorer_r1_1\analysis_r1.md
- D:\Finance\code\stock\.agents\explorer_r1_1\handoff.md
- D:\Finance\code\stock\.agents\explorer_r2_1\analysis_r2.md
- D:\Finance\code\stock\.agents\explorer_r2_1\handoff.md

Your Tasks:
1. Update `src/config.py` (`TradingConfig`):
   - Add parameters: `order_size_krx` (50,000,000.0), `order_size_sp500` (50,000.0), `market_impact_coeff_krx` (0.75), `market_impact_coeff_sp500` (0.50), base spread parameters, volatility defaults (0.020 for KRX, 0.015 for SP500). Allow env overrides.
2. Update `src/ai/ensemble_scorer.py` (`_get_cost_pct` & dynamic re-weighting verification):
   - Implement continuous dynamic spread ($\text{Spread}_{\%} = S_{base} \cdot (ADV_{ref} / ADV)^{0.25} \cdot (\sigma / \sigma_{ref})^{0.50}$).
   - Implement Kyle / Almgren-Chriss Square-Root market impact ($I_{impact} = Y \cdot \sigma \cdot \sqrt{Q / ADV}$) with participation rate overflow penalty ($P > 10\%$).
   - Ensure dynamic re-weighting in `combine_predictions` correctly scales active strategy weights to 1.0 (100%) when strategy predictions are missing, preserving valid 0.0 scores.
3. Write/enhance unit tests:
   - Create `tests/test_order_book_market_impact.py` testing square-root scaling, volatility sensitivity, participation overflow, and market-specific cost bounds.
   - Update/verify `tests/test_r1_ensemble_regime_fixes.py` or create unit test cases verifying dynamic re-weighting for missing strategy outputs (partial missingness, valid 0.0 vs NaN, omitted columns, full missing fallback).
4. Run tests with `.venv\Scripts\python.exe -m pytest tests/test_order_book_market_impact.py tests/test_r1_ensemble_regime_fixes.py -v`.
5. Report build/test results, implementation details, and save handoff to `D:\Finance\code\stock\.agents\worker_r1_r2_1\handoff.md`.
