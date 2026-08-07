## 2026-08-06T01:00:07Z
You are a teamwork_preview_challenger stress testing Milestone 1 (Financial Engineering & Quantitative Risk Audit).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_challenger_m1_1.
Read ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md.
Read PROJECT.md at: d:\Finance\code\stock\.agents\orchestrator_readiness_audit\PROJECT.md.

Task:
Empirically stress-test the quantitative risk and financial engineering logic:
1. Test `calculate_hrp_weights` in `portfolio_optimizer.py` with ill-conditioned, high-volatility, and singular covariance matrices.
2. Stress-test `merge_fundamentals` in `prediction_model.py` with unnamed DatetimeIndex, missing columns, duplicate dates, and out-of-order timestamps to verify 0 lookahead data leakage.
3. Test `AdvancedStatistics.get_performance_summary()` with extreme drawdowns (`total_return = -1.5`, `-2.0`, `0.0`), verifying no complex numbers or invalid JSON floats are returned.
4. Stress-test `IntradayStopLossEngine` with extreme price drops, NaN/Inf inputs, and volume spikes.

Run tests and report results. Write `handoff.md` with your verdict (APPROVE or REQUEST_CHANGES). Send a message to parent when finished.
