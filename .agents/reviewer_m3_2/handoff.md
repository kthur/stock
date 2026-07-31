# Handoff Report — Milestone 3: CPCV & Historical Stress Testing Engine (Code & Risk Reviewer 2)

**Reviewer**: `reviewer_m3_2` (Code & Risk Reviewer 2)  
**Date**: 2026-07-31  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Test Suite Execution
- Primary test suite (`.venv\Scripts\python.exe -m pytest tests/test_cpcv_stress_tester.py -v`): 6/6 passed.
- Mirror test suite (`.venv\Scripts\python.exe -m pytest trading_system/tests/test_cpcv_stress_tester.py -v`): 6/6 passed.

### 1.2 Adversarial Verification & Finding: Double Position Scaling Bug
During adversarial integration testing of `RiskManager.calculate_position_sizing`, position size scaling under stress test failure was evaluated:
- **Base Position Size** (`pass_flag = True`, `stress_test_adjustment_factor = 1.0`): `2,000` shares (capped by `max_position_size_pct = 0.20` on $1,000,000 portfolio at $100 entry price).
- **Scaled Position Size** (`pass_flag = False`, `stress_test_adjustment_factor = 0.75`): `1,125` shares.
- **Expected Scaled Position Size**: `1,500` shares ($2,000 \times 0.75$).
- **Actual Scaling Ratio**: $1,125 / 2,000 = 0.5625 = 0.75^2$.

### 1.3 Code Inspection (`trading_system/src/risk/risk_manager.py`)
- **Line 736**: `calculate_max_position_size` multiplies `max_value` by `self.stress_test_adjustment_factor`:
  ```python
  max_value = self.portfolio_value * self.max_position_size_pct * self.stress_test_adjustment_factor
  ```
- **Line 861–862**: `calculate_position_sizing` calls `calculate_max_position_size(entry_price)` and caps `position_quantity`:
  ```python
  max_position = self.calculate_max_position_size(entry_price)
  position_quantity = min(position_quantity, max_position)
  ```
- **Line 874–880**: `calculate_position_sizing` AGAIN multiplies `position_quantity` by `self.stress_test_adjustment_factor`:
  ```python
  if self.stress_test_adjustment_factor < 1.0:
      old_qty = position_quantity
      position_quantity = max(1, int(position_quantity * self.stress_test_adjustment_factor))
  ```

---

## 2. Logic Chain

1. When `stress_test_adjustment_factor` is set to $0.75$ (due to a stress test failure):
   - `calculate_max_position_size` returns a position limit that is already scaled down to $75\%$ of normal capacity ($1,500$ shares instead of $2,000$).
   - Line 862 caps `position_quantity` to `max_position` ($1,500$ shares).
   - Lines 874–880 re-multiply `position_quantity` ($1,500$) by `self.stress_test_adjustment_factor` ($0.75$), resulting in $1,125$ shares.
2. This applies $0.75 \times 0.75 = 0.5625$ ($56.25\%$) position scaling instead of the intended $0.75$ ($75\%$).
3. Unit tests in `test_cpcv_stress_tester.py` did not catch this because they invoked `get_risk_adjusted_position_size` directly instead of `calculate_position_sizing`.

---

## 3. Caveats

- `update_stress_test_results` itself correctly parses stress reports and updates state.
- Step 11 in `run_pipeline.py` correctly passes stress reports to `RiskManager` and formats `strategy_data_coverage_report.txt`.
- Boundary conditions (zero vol, NaNs/Infs, logit rank clipping $[1e-5, 1-1e-5]$, small sample size $N<4$, $M<2$) are all cleanly handled.

---

## 4. Conclusion

**Verdict**: **REQUEST_CHANGES**

### Findings

#### [Major] Finding 1: Double Position Scaling in `RiskManager.calculate_position_sizing`
- **What**: `calculate_position_sizing` applies `self.stress_test_adjustment_factor` twice when stress testing fails, scaling position sizes down by $0.75^2 = 0.5625$ instead of $0.75$.
- **Where**: `trading_system/src/risk/risk_manager.py`, lines 736 and 874–880.
- **Why**: `calculate_max_position_size` already includes `self.stress_test_adjustment_factor` in calculating `max_position`. Clamping `position_quantity = min(position_quantity, max_position)` at line 862 already applies the factor. Re-multiplying by `self.stress_test_adjustment_factor` at line 876 applies it a second time.
- **Suggestion**: Either remove `self.stress_test_adjustment_factor` from `calculate_max_position_size` (so `calculate_max_position_size` calculates the unscaled structural limit) OR remove lines 874–880 in `calculate_position_sizing` so the factor is applied consistently once. Also update `test_cpcv_stress_tester.py` to add an explicit assertion testing `calculate_position_sizing` under failed stress test status.

---

## 5. Verification Method

To verify the issue and validate the fix, execute the following PowerShell command:

```powershell
.venv\Scripts\python.exe -c "
from trading_system.src.ai.cpcv_stress_tester import StressTestReport
from trading_system.src.risk.risk_manager import RiskManager

rm = RiskManager(portfolio_value=1000000)
pos1 = rm.calculate_position_sizing('AAPL', 100.0, 95.0)

fail_report = StressTestReport(
    scenario='2008_CRISIS', mdd=0.45, var_95=-0.05, var_99=-0.08,
    cvar_95=-0.07, cvar_99=-0.10, stress_sharpe=-0.5, stress_recovery_time=100,
    pass_flag=False, details={}
)
rm.update_stress_test_results(fail_report, fail_adjustment_factor=0.75)
pos2 = rm.calculate_position_sizing('AAPL', 100.0, 95.0)

print(f'Unscaled Qty: {pos1}, Scaled Qty: {pos2}, Expected: {int(pos1 * 0.75)}')
assert pos2 == max(1, int(pos1 * 0.75)), f'Double scaling bug detected: {pos2} != {int(pos1 * 0.75)}'
"
```
