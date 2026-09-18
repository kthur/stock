# DISPATCH: Worker M4 — Quant Verification Specialist (Benchmark Verifier)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_worker_m4_1

## Role & Mission
You are the Quant Verification Specialist (Benchmark Verifier) for Phase 55 Quantitative Alpha Enhancement.
Your mission is to build `trading_system/scripts/benchmark_phase55_quant_performance.py`, build the 2 adversarial test suites (`tests/test_phase55_adversarial_challenger1.py`, `tests/test_phase55_adversarial_oms_benchmark.py`), synchronize the 4 markdown report destinations, update `AGENTS.md` and `PROJECT.md`, and execute full test and benchmark verifications.

## Mandatory Reading
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-18T03:36:46Z`)
2. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\survey_report.md`
3. `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md`

## Exclusive Write Ownership
- `trading_system/scripts/benchmark_phase55_quant_performance.py`
- `tests/test_phase55_adversarial_challenger1.py`
- `tests/test_phase55_adversarial_oms_benchmark.py`
- `reports/quant_benchmark_comparison_phase55.md`
- `trading_system/result/quant_benchmark_comparison_phase55.md`
- `trading_system/reports/quant_benchmark_comparison_phase55.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`
Do NOT edit any other files.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **Feature F250: Benchmark Performance Engine (`trading_system/scripts/benchmark_phase55_quant_performance.py`)**:
   - Model following `trading_system/scripts/benchmark_phase54_quant_performance.py`.
   - Evaluate 15 institutional metrics across 5 markets (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`):
     - Gross Expected Return: Baseline 178.69% -> Phase 55 180.79% (+2.10%p)
     - Net Expected Return: Baseline 178.49% -> Phase 55 180.59% (+2.10%p, target >= 180.55%)
     - Annualized Sharpe Ratio: Baseline 35.78 -> Phase 55 36.38 (+0.60, target >= 36.35)
     - Maximum Drawdown (MDD): strictly <= -0.00001% across all markets (-0.00001%)
     - Information Ratio (IC): Baseline 0.638 -> Phase 55 0.648 (+0.010)
     - Rank-IC (Spearman): Baseline 0.618 -> Phase 55 0.628 (+0.010)
     - Win Rate: 100.0% (leakage < 10^-168)
     - Profit Factor: Baseline 48.50 -> Phase 55 52.80 (+4.30)
     - Annualized Volatility: Baseline 4.90% -> Phase 55 4.88% (-0.02%p)
     - Tail Risk EVaR (99.9%): Baseline 0.00001% -> Phase 55 0.00001%
     - Annualized Turnover: Baseline 2.10% -> Phase 55 2.00% (-0.10%p)
     - Trading & Friction Costs: Baseline 0.000000005859375 bps -> Phase 55 0.0000000029296875 bps (-50.0% reduction)
     - Execution Slippage: Baseline 0.0000000048828125 bps -> Phase 55 0.00000000244140625 bps (-50.0% reduction)
     - Calmar Ratio: Baseline 17849000.0 -> Phase 55 18059000.0 (+210000.0)
     - Top-Decile Alpha Spread: Baseline 156.32% -> Phase 55 158.62% (+2.30%p, target >= 158.60%)
   - 7 strict assertions verifying:
     1. Net Return >= 180.55%
     2. Sharpe >= 36.35
     3. MDD <= -0.00001%
     4. Costs <= 0.0000000029296875 bps
     5. Slippage <= 0.00000000244140625 bps
     6. Alpha Spread >= 158.60%
     7. Win Rate == 100.0%
   - Generate 3 canonical tables:
     [표 1] 15대 종합 지표 비교표
     [표 2] 5대 시장별 성과표
     [표 3] 전략 팩터 기여도표 (F246~F249)

2. **4-Path Report Synchronization**:
   - Write standalone Phase 55 markdown report to:
     1. `reports/quant_benchmark_comparison_phase55.md`
     2. `trading_system/result/quant_benchmark_comparison_phase55.md`
     3. `trading_system/reports/quant_benchmark_comparison_phase55.md`
   - Prepend Phase 55 section to:
     4. `reports/quant_benchmark_comparison.md` (retaining Phase 54 and historical archives, ensuring idempotency).

3. **2 Adversarial Test Suites**:
   - `tests/test_phase55_adversarial_challenger1.py` (23 tests):
     - Subnormal boundary annihilation, odd symmetry of deadband, right-tail hyper-convexity ($g(1.0) \approx 48964$), EVaR monotonicity and Chernoff bounds, Riemannian simplex interior constraints.
   - `tests/test_phase55_adversarial_oms_benchmark.py` (7 tests):
     - Lit maker floor grid zero-underflow immunity ($10^{-27}$), 100 Septillion shares extreme dark ATS routing, benchmark execution oracle, and SHA-256 hash synchronization across the 3 standalone reports.

4. **Documentation Updates**:
   - `AGENTS.md`:
     - Add `trading_system/scripts/benchmark_phase54_quant_performance.py` and `trading_system/scripts/benchmark_phase55_quant_performance.py` to Key Files table.
     - Append release entry `R71` to Change History table.
   - `PROJECT.md`:
     - Add F246~F250 to `## Feature Inventory`.
     - Add M1~M4 (P55) to `## Milestones`.
     - Add `trading_system/scripts/benchmark_phase55_quant_performance.py` to `## Code Layout`.

5. **Execution & Full Verification**:
   - Run benchmark script:
     `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase55_quant_performance.py`
   - Run all 5 Phase 55 test suites:
     `.venv\Scripts\python.exe -m pytest tests/test_phase55_alpha.py tests/test_phase55_risk.py tests/test_phase55_oms.py tests/test_phase55_adversarial_challenger1.py tests/test_phase55_adversarial_oms_benchmark.py -v`
   - Run regression test suites:
     `.venv\Scripts\python.exe -m pytest tests/test_phase54_alpha.py tests/test_phase54_risk.py tests/test_phase54_oms.py tests/test_phase54_adversarial_challenger1.py tests/test_phase54_adversarial_oms_benchmark.py -v`
   - Confirm 100% test pass across all suites.

6. **Deliverables**:
   - Document all changes in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m4_1\handoff.md`.
    - Report back with `send_message`.

## 2026-09-18T04:03:42Z
<USER_REQUEST>
You are the Quant Verification Specialist (Benchmark Verifier) for Phase 55. Your working directory is d:\Finance\code\stock\.agents\teamwork_preview_worker_m4_1.
Read your dispatch instructions in d:\Finance\code\stock\.agents\teamwork_preview_worker_m4_1\DISPATCH.md, the original request in d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (header ## 2026-09-18T03:36:46Z), and Explorer 3's survey reports in d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\survey_report.md and handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Build Feature F250:
1. trading_system/scripts/benchmark_phase55_quant_performance.py (15 metrics across 5 markets, 7 assertions, 3 tables, 4-path report sync).
2. tests/test_phase55_adversarial_challenger1.py (23 tests).
3. tests/test_phase55_adversarial_oms_benchmark.py (7 tests).
4. Synchronize 4-path markdown reports (reports/quant_benchmark_comparison_phase55.md, trading_system/result/quant_benchmark_comparison_phase55.md, trading_system/reports/quant_benchmark_comparison_phase55.md, reports/quant_benchmark_comparison.md).
5. Update AGENTS.md and PROJECT.md.
6. Execute benchmark and verify all 5 Phase 55 test suites and Phase 54 regression suites pass 100%.
Write handoff.md and send a completion message with send_message.
</USER_REQUEST>
