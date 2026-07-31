## 2026-07-31T11:06:24Z
You are worker_m3_3, the Remediation Worker for Milestone 3 (R3: CPCV & Historical Stress Testing Engine).

Your working directory is `d:\Finance\code\stock\.agents\worker_m3_3`. Please create your working directory first if it does not exist.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mission:
Remediate the Double Position Scaling Bug in `trading_system/src/risk/risk_manager.py` identified by `reviewer_m3_2`:

Finding Details:
1. `RiskManager.calculate_position_sizing` (`trading_system/src/risk/risk_manager.py`) has a double scaling bug when `stress_test_passed == False`.
2. `calculate_max_position_size` (line 736) already scales `max_value` by `self.stress_test_adjustment_factor`.
3. When `calculate_position_sizing` caps `position_quantity = min(position_quantity, max_position)` at line 862, it already incorporates the $0.75\times$ factor.
4. Then lines 874-880 re-multiply `position_quantity` by `self.stress_test_adjustment_factor` ($0.75$) a second time, resulting in $0.75 \times 0.75 = 0.5625$ ($56.25\%$) scaling instead of the intended $0.75$ ($75\%$).

Instructions:
1. Inspect `trading_system/src/risk/risk_manager.py`.
2. Fix `calculate_position_sizing` so `self.stress_test_adjustment_factor` is applied ONCE, returning exactly `0.75 * base_quantity` (75% of unpenalized position size) when stress test fails.
3. Update unit tests in `tests/test_cpcv_stress_tester.py` and `trading_system/tests/test_cpcv_stress_tester.py`:
   - Add explicit assertion verifying `position_quantity == expected_0_75_quantity` when `stress_test_passed == False`.
4. Run tests: `.venv\Scripts\python.exe -m pytest tests/test_cpcv_stress_tester.py trading_system/tests/test_cpcv_stress_tester.py -v`.
5. Run regression suite: `.venv\Scripts\python.exe -m pytest tests/ -v`.

Write your report to `d:\Finance\code\stock\.agents\worker_m3_3\handoff.md` and notify orchestrator when done via `send_message`.

## 2026-07-31T11:07:27Z
**Context**: Additional edge-case remediation findings for Milestone 3 (`CPCVStressTester`).

**Content**:
`challenger_m3_1` completed empirical stress testing and identified 2 minor edge-case resilience items in `trading_system/src/ai/cpcv_stress_tester.py` to fix alongside the RiskManager position scaling fix:

1. **Inf/NaN Finiteness Guard**:
   - In `_stress_test_single_series`, change return array filter from `ret_arr = ret_arr[~np.isnan(ret_arr)]` to `ret_arr = ret_arr[np.isfinite(ret_arr)]` so both `NaN` and `\pm \infty` are cleaned.
   - In `compute_pbo`, sanitize strategy matrix using `np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)` before Sharpe ratio calculation.

2. **Small Sample Size (< 4 bars) Guard**:
   - In `compute_pbo`, if `len(X) < 4` or `n_models < 2`, log warning and return safe default dictionary (`{"pbo": 0.0, "logits": [], "ranks": [], "is_overfitted": False, "n_combinations": 0}`).
   - In `_stress_test_single_series`, if `len(ret_arr) < 2` or `std == 0`, set `stress_sharpe = 0.0` to avoid division-by-zero or `ddof=1` `NaN` outputs.

**Action**: Please incorporate these edge-case guards into your implementation in `trading_system/src/ai/cpcv_stress_tester.py` along with the RiskManager double position scaling fix. Run all tests and update handoff report when complete.

## 2026-07-31T11:30:42Z
**Context**: Heartbeat check on Milestone 3 remediation progress.

**Content**: Checking status on RiskManager position size scaling fix and CPCV stress tester edge-case guards.

**Action**: Please report status, progress, or write handoff report if completed.
