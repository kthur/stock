# Worker M1 Iteration 2 Dispatch: Implementation of Challenger Remediations & Tightened SLA Deflation

## Objective
Implement and verify the complete set of remediation patches and tightened SLA deflation:

1. `trading_system/src/core/multi_factor_neutralizer.py`:
   - Tighten secondary Gram-Schmidt deflation threshold to `corr_thresh = 0.05`.
   - Apply an additional post-scaling correlation check: if after min-max scaling $\max_k |\rho(z_k, \text{score})| \ge 0.15$, apply linear orthogonal adjustment $\text{score} \leftarrow \text{score} - \sum_k \rho(z_k, \text{score}) z_k$ and re-normalize, guaranteeing $|\rho| < 0.15$ across 100% of seeds under all missing data + extreme loading combinations.

2. `trading_system/src/ai/prediction_model.py`:
   - In `FallbackMetadataDict.__init__`, include `"book_value": mock_data.get("book_value", np.nan)` for all benchmark symbols (`AAPL`, `MSFT`, `005930`, etc.) and hashed symbols.

3. `trading_system/src/analysis/statistics.py`:
   - Guard annual return exponentiation: `total_ret_clamped = max(1e-6, 1.0 + total_return)` before `** (252.0 / n)` to prevent complex numbers.
   - Set `profit_factor = 999.0 if gross_profit > 0 else 0.0` when `gross_loss == 0.0` (and similarly for `calmar_ratio`, `recovery_factor`) instead of `float("inf")` for JSON compliance.
   - In `calculate_returns()` and `calculate_max_drawdown()`, guard against `prev_equity <= 0.0` or `peak_equity <= 0.0` to prevent `ZeroDivisionError`.

4. `trading_system/src/risk/intraday_stop_loss.py`:
   - In `evaluate()`, sanitize price arrays: `data["close"].replace([np.inf, -np.inf], np.nan).dropna().values` (and similarly for volume/high/atr) to prevent corrupted infinite prices.

5. `trading_system/src/risk/risk_manager.py`:
   - In `CrisisDetector.evaluate()`, add single-factor VIX fast shock overrides:
     - If `vix >= 30.0`: `composite = max(composite, 0.30)` (forcing at least `CrisisLevel.WATCH`).
     - If `vix >= 40.0`: `composite = max(composite, 0.60)` (forcing at least `CrisisLevel.ACTIVE`).

6. `trading_system/src/risk/portfolio_optimizer.py`:
   - Set constructor defaults: `default_max_weight=0.15` and `default_max_sector_weight=0.30`.

7. Run and verify all test suites:
   - `pytest tests/test_factor_neutralized_sla.py -v`
   - `pytest tests/test_challenger_m1_2_empirical.py -v`
   - `pytest tests/test_m1_master_suite.py -v`
   - `pytest tests/test_critical_bugs.py -v`
   - `.agents/teamwork_preview_challenger_m1_1/test_m1_stress.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverables
- Implemented and verified code files.
- Test execution output documented in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1_iter2\handoff.md`.
