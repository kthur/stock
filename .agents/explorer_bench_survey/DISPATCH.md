# DISPATCH: Survey Explorer Bench (Benchmark Scripts & Test Infrastructure)

## Working Directory
`d:\Finance\code\stock\.agents\explorer_bench_survey`

## Mission
Investigate Benchmark & Testing Infrastructure for Phase 8 Sovereign Quantitative Enhancements (v15):
1. Investigate existing benchmark scripts:
   - `trading_system/scripts/benchmark_phase7_quant_performance.py` (or phase6, phase5, phase4, etc.).
   - Check how metrics (Gross/Net Return, Sharpe, Rank-IC, MDD, Turnover, Friction, Slippage, Darkpool Savings, Win Rate, etc.) are computed and simulated.
   - Inspect `reports/quant_benchmark_comparison_phase7.md` and `reports/quant_benchmark_comparison.md`.
2. Map out the creation/update of `trading_system/scripts/benchmark_phase8_quant_performance.py` for Phase 8 Sovereign v15 evaluation across all 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).
3. Investigate the full test suite (`pytest tests/`):
   - Total test count (2,580+ tests).
   - Test execution commands and environment requirements (`.venv\Scripts\python.exe -m pytest tests/`).
   - Identify test files touching `ensemble_scorer`, `factor_suppression`, `score_normalizer`, `unified_portfolio_allocator`, `smart_order_router`, `fast_lob_engine`, `oms_engine`.
4. Write handoff report with exact script structures, metric formulas, and verification commands to `d:\Finance\code\stock\.agents\explorer_bench_survey\handoff.md`.
