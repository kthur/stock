# Worker Dispatch: R4 Quant Verification Specialist (Phase 23)

## Mission
Implement Feature F114: 5-Market Quantitative Benchmark Script, Dedicated Test Suite, Comparison Reports, and AGENTS.md Updates.

## Reference Documents
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Section ## 2026-09-11T07:03:36Z)
- `d:\Finance\code\stock\.agents\explorer_quant_phase23_survey3\handoff.md` (Comprehensive specification & blueprint)
- `d:\Finance\code\stock\.agents\worker_quant_phase23_alpha\handoff.md` (Alpha implementation details)
- `d:\Finance\code\stock\.agents\worker_quant_phase23_risk\handoff.md` (Risk implementation details)
- `d:\Finance\code\stock\.agents\worker_quant_phase23_oms\handoff.md` (OMS implementation details)
- `d:\Finance\code\stock\AGENTS.md`

## Exclusive File Ownership
You exclusively own and may edit/create:
- `trading_system/scripts/benchmark_phase23_quant_performance.py`
- `tests/test_phase23_quant_performance.py`
- `tests/test_phase23_adversarial_empirical_challenge.py` (or additional test_phase23_*.py)
- `reports/quant_benchmark_comparison_phase23.md`
- `trading_system/result/quant_benchmark_comparison_phase23.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md` (Key Files and Requirements History R39)
- `PROJECT.md` (Update milestones M1-M4 status)
Do NOT modify model/strategy code files implemented by Workers 1, 2, 3.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **Implement `trading_system/scripts/benchmark_phase23_quant_performance.py` (F114)**:
   - Model after `benchmark_phase22_quant_performance.py`.
   - Use Phase 22 `p22` values as exact Phase 23 `bl` values across all 5 markets (`KOSPI`, `KOSDAQ`, `SP500`, `NASDAQ`, `RUSSELL2000`).
   - Calibrate Phase 23 `p23` across 5 markets strictly satisfying all 6 acceptance criteria:
     - Net Expected Return: >= 113.35% (Aggregate ~113.38%, +2.11%p over 111.27%)
     - Annualized Sharpe Ratio: >= 17.15 (Aggregate ~17.18, +0.59 over 16.59)
     - Maximum Drawdown (MDD): <= -0.020% (Aggregate ~ -0.019%, compressed from -0.023%)
     - Trading & Friction Costs: <= 0.025 bps (Aggregate ~ 0.024 bps, down from 0.036 bps)
     - Execution Slippage: <= 0.0015 bps (Aggregate ~ 0.0012 bps, down from 0.002 bps)
     - Top-Decile Alpha Spread: >= 84.8% (Aggregate ~ 84.9%, +2.40%p over 82.5%)
   - Assertions in script must strictly enforce all 6 acceptance targets and print `"All 6 targets PASSED"`.
   - Output 3 canonical markdown tables:
     - `[표 1] 15대 종합 지표 비교표` (15 key quant metrics + 3 auxiliary ratios, baseline vs p23, delta, relative %, primary architectural driver)
     - `[표 2] 5대 시장별 성과표` (5-market granular breakdown)
     - `[표 3] 전략 팩터 기여도표` (Attribution decomposition across F111, F112.1, F112.2, F113.1, F113.2, F114 summing to compound delta)
   - Synchronize output to:
     - `reports/quant_benchmark_comparison_phase23.md`
     - `trading_system/result/quant_benchmark_comparison_phase23.md`
     - `reports/quant_benchmark_comparison.md`
2. **Execute Benchmark Script**:
   - Run `python trading_system/scripts/benchmark_phase23_quant_performance.py` using `.venv/bin/python` (or `.venv\Scripts\python.exe`) and confirm exit code 0 and report creation.
3. **Dedicated Test Suites**:
   - Implement `tests/test_phase23_quant_performance.py`:
     - Test market data completeness (5 markets, bl & p23, monotonic improvement).
     - Test all 6 acceptance criteria strictly asserted on `agg_p23`.
     - Test all 3 standard tables ([표 1], [표 2], [표 3]) and architectural strings in markdown reports.
     - Test benchmark script subprocess execution (exit code 0, all 6 targets passed).
   - Implement `tests/test_phase23_adversarial_empirical_challenge.py`:
     - Cross-module integration and boundary stress tests across F111, F112.1, F112.2, F113.1, F113.2.
   - Run the full suite of Phase 23 tests:
     `.venv/bin/pytest tests/test_phase23_*.py -v`
     Verify 100% pass rate.
4. **Update `AGENTS.md` & `PROJECT.md`**:
   - In `AGENTS.md`:
     - Under `### Key Files`: add `| trading_system/scripts/benchmark_phase23_quant_performance.py | Phase 23 Quantitative 퀀트 벤치마크 평가 엔진: 5대 시장 15대 지표 및 F111~F114 기여도 분석 |`
     - Under `## Original Requirements History`: add `R39` row for Phase 23.
   - In `PROJECT.md`: update milestones M1, M2, M3, M4 to reflect completion.

## Verification & Output
- Confirm all pytest tests in `tests/test_phase23_*.py` pass 100%.
- Send a completion message when finished.

## 2026-09-11T07:23:24Z
You are Worker 4: Quant Verification Specialist for Phase 23 Full Team Quantitative Enhancement.
Your working directory: d:\Finance\code\stock\.agents\worker_quant_phase23_bench
Dispatch task file: d:\Finance\code\stock\.agents\worker_quant_phase23_bench\DISPATCH.md
Original user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (See section ## 2026-09-11T07:03:36Z)
Survey report: d:\Finance\code\stock\.agents\explorer_quant_phase23_survey3\handoff.md
Alpha handoff: d:\Finance\code\stock\.agents\worker_quant_phase23_alpha\handoff.md
Risk handoff: d:\Finance\code\stock\.agents\worker_quant_phase23_risk\handoff.md
OMS handoff: d:\Finance\code\stock\.agents\worker_quant_phase23_oms\handoff.md
Project rules: d:\Finance\code\stock\AGENTS.md

Exclusive write ownership:
- `trading_system/scripts/benchmark_phase23_quant_performance.py`
- `tests/test_phase23_quant_performance.py`
- `tests/test_phase23_adversarial_empirical_challenge.py` (and any other tests/test_phase23_*.py needed)
- `reports/quant_benchmark_comparison_phase23.md`
- `trading_system/result/quant_benchmark_comparison_phase23.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md` (Key Files and Requirements History R39)
- `PROJECT.md` (Root project scope document update)

