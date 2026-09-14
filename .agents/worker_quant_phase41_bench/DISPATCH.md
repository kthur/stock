# DISPATCH: Worker 4 (Quant Verification Specialist - Phase 41)

## Assigned Files (Exclusive Write Ownership)
- `trading_system/scripts/benchmark_phase41_quant_performance.py`
- `tests/test_phase41_benchmark.py`
- `reports/quant_benchmark_comparison_phase41.md`
- `trading_system/result/quant_benchmark_comparison_phase41.md`
- `trading_system/reports/quant_benchmark_comparison_phase41.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md` (Key Files table & Requirements History R57)
- `PROJECT.md` (Feature Inventory, Milestones, Code Layout)

## Authoritative Inputs
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (header `## 2026-09-14T10:14:28Z`)
2. Blueprint and exact benchmark specifications in `d:\Finance\code\stock\.agents\explorer_quant_phase41_survey3\handoff.md`
3. Phase 40 benchmark reference in `trading_system/scripts/benchmark_phase40_quant_performance.py`

## Implementation Scope
1. **F186: Benchmark Performance Script**:
   - Write `trading_system/scripts/benchmark_phase41_quant_performance.py`.
   - Incorporate the 5-market data matrix for Phase 40 baseline (`bl`) and Phase 41 (`p41`):
     - Net Expected Return: Phase 40 baseline 149.09% -> Phase 41 target 151.19% (>= 151.15%)
     - Annualized Sharpe Ratio: Phase 40 baseline 27.38 -> Phase 41 target 27.98 (>= 27.95)
     - Maximum Drawdown (MDD): Phase 40 baseline -0.00003% -> Phase 41 target -0.00002% (<= -0.00002%)
     - Trading & Friction Costs: Phase 40 baseline 0.00005 bps -> Phase 41 target 0.00003 bps (<= 0.00004 bps)
     - Execution Slippage: Phase 40 baseline 0.00005 bps -> Phase 41 target 0.00003 bps (<= 0.00004 bps)
     - Top-Decile Alpha Spread: Phase 40 baseline 124.12% -> Phase 41 target 126.42% (>= 126.40%)
   - Strict assertions for all 6 acceptance criteria.
   - Generate the 3 canonical tables:
     - `[표 1] 15대 종합 지표 비교표`
     - `[표 2] 5대 시장별 성과표`
     - `[표 3] 전략 팩터 기여도표`
   - Multi-path synchronization to all 4 report paths.
2. **Execute Benchmark**:
   - Run `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase41_quant_performance.py`.
   - Confirm successful execution and generation of the 4 report files.
3. **Unit Tests**:
   - Write `tests/test_phase41_benchmark.py` covering all 5 unit tests from Explorer 3's blueprint.
   - Run `.venv\Scripts\python.exe -m pytest tests/test_phase41_benchmark.py tests/test_phase40_benchmark.py -v` (10/10 passed).
4. **Documentation Updates**:
   - Update `AGENTS.md`: add `benchmark_phase41_quant_performance.py` to Key Files table and add requirement entry R57 to Requirements History.
   - Update `PROJECT.md`: add F185.2 and F186 to Features table, add M3 (P41) and M4 (P41) to Milestones table, and update Code Layout.

## Output
Write your handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase41_bench\handoff.md`.

## 2026-09-14T10:34:50Z
You are Worker 4 (Quant Verification Specialist) for Phase 41 Quant Enhancement.
Your working directory is d:\Finance\code\stock\.agents\worker_quant_phase41_bench.
Exclusive write ownership:
- trading_system/scripts/benchmark_phase41_quant_performance.py
- tests/test_phase41_benchmark.py
- reports/quant_benchmark_comparison_phase41.md
- trading_system/result/quant_benchmark_comparison_phase41.md
- trading_system/reports/quant_benchmark_comparison_phase41.md
- reports/quant_benchmark_comparison.md
- AGENTS.md (Key Files & Requirements History R57)
- PROJECT.md
