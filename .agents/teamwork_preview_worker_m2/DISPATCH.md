## 2026-08-21T10:25:28Z
You are Worker M2 for the Stock Trading System.
Your working directory is: D:\Finance\code\stock\.agents\teamwork_preview_worker_m2\

Read:
1. D:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
2. D:\Finance\code\stock\system_improvement_report_v5.md (Focus on Domain 2: V5-07 ~ V5-12)
3. D:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md

Your exclusive write boundaries:
- `trading_system/src/analysis/portfolio_optimizer.py`
- `trading_system/src/analysis/coverage_analyzer.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `trading_system/src/risk/risk_manager.py`
- `trading_system/src/ai/prediction_model.py`
Do NOT modify files outside your boundary.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks to implement:
- **V5-07**: In `portfolio_optimizer.py:170-178, 204-220`, fix Black-Litterman prior vs view scale alignment and quadratic utility optimization on negative excess return (`if port_ret <= risk_free_rate: return - (port_ret - 0.5 * lambda_aversion * port_var)`).
- **V5-08**: In `portfolio_allocator.py:106-112`, Clayton copula asymmetric correlation PSD spectral projection (`c_evals, c_evecs = np.linalg.eigh(asym_corr); c_evals = np.maximum(c_evals, 1e-4); asym_corr = c_evecs @ np.diag(c_evals) @ c_evecs.T; res = stressed_cov + 1e-5 * np.eye(K)`).
- **V5-09**: In `prediction_model.py:156-170`, chronological forward expanding time series cross-validation (`train_end_idx = (i + 1) * test_size`).
- **V5-10**: In `portfolio_optimizer.py:406-422`, HRP inverse-variance cluster variance floor (`1e-4` on vols, `1e-8` on var, alpha clamped to `[0.01, 0.99]`).
- **V5-11**: In `risk_manager.py:207-210, 310-315`, fix `np.isnan(None)` with `isinstance` / `np.isfinite` check, and forward-fill macro history queue synchronously.
- **V5-12**: In `coverage_analyzer.py:37-41, 165-170`, align fundamental column schema with engineered feature names (`['revenue_to_market_cap', 'dividend_yield', 'eps_yield', 'eps_growth_1y', 'operating_margin', 'roe']`).

Run relevant tests using `.venv\Scripts\python.exe -m pytest tests/test_portfolio_optimization.py tests/test_risk_manager.py tests/test_coverage_analyzer.py -v`.
Write your complete report to `D:\Finance\code\stock\.agents\teamwork_preview_worker_m2\handoff.md`.
Send message to parent when done.
