# Survey Task 3: R4 Benchmark Performance & Test Suite Architecture

## Target Files
- `trading_system/scripts/benchmark_phase22_quant_performance.py` (and phase 21/20)
- `tests/test_phase22_*.py`
- `reports/quant_benchmark_comparison_phase22.md`
- `trading_system/result/quant_benchmark_comparison_phase22.md`
- `AGENTS.md`

## Instructions
1. Read `ORIGINAL_REQUEST.md` (specifically ## 2026-09-11T07:03:36Z) and project rules in `AGENTS.md`.
2. Inspect `trading_system/scripts/benchmark_phase22_quant_performance.py`: how it computes 15 key metrics across 5 markets, how F107-F110 contributions are measured, how baseline values are stored and comparison tables formatted.
3. Map out requirements for `trading_system/scripts/benchmark_phase23_quant_performance.py` (F114):
   - 15 core quant metrics across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
   - Phase 22 baselines and Phase 23 targets:
     - Net Expected Return: >= 113.35% (Phase 22 baseline 111.27%)
     - Sharpe Ratio: >= 17.15 (Phase 22 baseline 16.59)
     - MDD: <= -0.020% (Phase 22 baseline -0.023%)
     - Friction: <= 0.025 bps (Phase 22 baseline 0.036 bps)
     - Slippage: <= 0.0015 bps (Phase 22 baseline 0.002 bps)
     - Top-Decile Spread: >= 84.8% (Phase 22 baseline 82.5%)
   - Output files: `reports/quant_benchmark_comparison_phase23.md` and `trading_system/result/quant_benchmark_comparison_phase23.md`.
   - AGENTS.md updates: Key Files table and Requirements History R39.
4. Inspect existing test patterns in `tests/test_phase22_*.py` and design the plan for `tests/test_phase23_*.py`.
5. Produce a detailed exploration report in `handoff.md`.

## 2026-09-11T07:06:12Z
Scope:
Investigate R4 Benchmark Performance & Test Suite Architecture:
- Inspect `trading_system/scripts/benchmark_phase22_quant_performance.py` (and phase 21/20), `tests/test_phase22_*.py`, `reports/quant_benchmark_comparison_phase22.md`, `trading_system/result/quant_benchmark_comparison_phase22.md`, and `AGENTS.md`.
- Examine how Phase 22 benchmark script evaluates 15 key quant metrics across 5 markets, how F107-F110 contributions are measured, how baseline values are stored, and how comparison tables are formatted and written.
- Map out requirements for `trading_system/scripts/benchmark_phase23_quant_performance.py` (F114):
  - 15 core quant metrics across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000).
  - Phase 22 baselines and Phase 23 targets:
    - Net Expected Return: >= 113.35% (Phase 22 baseline 111.27%)
    - Sharpe Ratio: >= 17.15 (Phase 22 baseline 16.59)
    - MDD: <= -0.020% (Phase 22 baseline -0.023%)
    - Friction: <= 0.025 bps (Phase 22 baseline 0.036 bps)
    - Slippage: <= 0.0015 bps (Phase 22 baseline 0.002 bps)
    - Top-Decile Spread: >= 84.8% (Phase 22 baseline 82.5%)
  - Output files: `reports/quant_benchmark_comparison_phase23.md` and `trading_system/result/quant_benchmark_comparison_phase23.md`.
  - AGENTS.md updates: Key Files table and Requirements History R39.
  - Test suite architecture in `tests/test_phase23_*.py`.
Write a complete, structured exploration report to `d:\Finance\code\stock\.agents\explorer_quant_phase23_survey3\handoff.md` with exact line numbers, formulas, and integration steps. Send a message when finished.
