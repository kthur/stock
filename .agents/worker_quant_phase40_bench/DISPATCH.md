# DISPATCH: Worker 4 — Quant Verification Specialist (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\worker_quant_phase40_bench

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\explorer_quant_phase40_survey3\handoff.md`
3. `d:\Finance\code\stock\PROJECT.md`
4. `trading_system/scripts/benchmark_phase39_quant_performance.py`

## Exclusive File Ownership
- `trading_system/scripts/benchmark_phase40_quant_performance.py`
- `tests/test_phase40_benchmark.py`
- `reports/quant_benchmark_comparison_phase40.md`
- `trading_system/result/quant_benchmark_comparison_phase40.md`
- `trading_system/reports/quant_benchmark_comparison_phase40.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`

## Implementation Tasks
1. Create `trading_system/scripts/benchmark_phase40_quant_performance.py` (Feature F182):
   - Model exact 5-market performance data matrix replicating Phase 39 baseline numbers (Net Return 146.99%, Sharpe 26.78, MDD -0.00005%, Friction 0.00010 bps, Slippage 0.00010 bps, Top-Decile 121.82%).
   - Verify all 6 Phase 40 performance criteria: Net Return >= 149.05% (target 149.09%), Sharpe >= 27.35 (target 27.38), MDD <= -0.00004% (target -0.00003%), Friction <= 0.00008 bps, Slippage <= 0.00008 bps, Top-Decile Spread >= 124.10% (target 124.12%).
   - Generate 3 standard tables ([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표).
   - Write and synchronize reports across all 4 paths:
     - `reports/quant_benchmark_comparison_phase40.md`
     - `trading_system/result/quant_benchmark_comparison_phase40.md`
     - `trading_system/reports/quant_benchmark_comparison_phase40.md`
     - `reports/quant_benchmark_comparison.md` (prepend Phase 40, preserve Phase 39 and prior).
2. Execute `benchmark_phase40_quant_performance.py`:
   `python trading_system/scripts/benchmark_phase40_quant_performance.py`
   Ensure all 6 assertions pass and all 4 report files are generated.
3. Write `tests/test_phase40_benchmark.py` covering all 5 test scenarios from Explorer 3's blueprint.
4. Execute unit tests:
   `$env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_benchmark.py -v`
   Verify 100% pass rate.
5. Update `AGENTS.md`:
   - Add `benchmark_phase40_quant_performance.py` to Key Files table.
   - Add R56 to Requirements History.
6. Update `PROJECT.md`:
   - Add F179, F180.1, F180.2, F181.1, F181.2, F182 to Feature Inventory.
   - Add M1 (P40), M2 (P40), M3 (P40), M4 (P40) to Milestones table.
   - Add `benchmark_phase40_quant_performance.py` to Code Layout.
7. Write your completion report in `d:\Finance\code\stock\.agents\worker_quant_phase40_bench\handoff.md` and send a message back to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`).
