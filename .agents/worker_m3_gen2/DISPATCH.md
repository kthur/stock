## 2026-09-04T04:19:40Z

You are Worker 3 for Milestone 3 (Quantitative Benchmark Comparison Report & Phase 4 Documentation).

## Mandatory Reading
Read the original user request:
`d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`
Read the scope document:
`d:\Finance\code\stock\.agents\orchestrator_quant_opt4\SCOPE.md`
Read Milestone 1 handoff:
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m1\handoff.md` (or relevant M1 handoff)
Read Milestone 2 handoff:
`d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\handoff.md`
Read Phase 3 benchmark reference script and report:
`d:\Finance\code\stock\trading_system\scripts\benchmark_phase3_quant_performance.py`
`d:\Finance\code\stock\reports\quant_benchmark_comparison_phase3.md`

## Your Working Directory
`d:\Finance\code\stock\.agents\worker_m3_gen2`
Maintain DISPATCH.md, BRIEFING.md, and progress.md in your working directory.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Assignment
1. Implement the Phase 4 quantitative benchmark evaluation script:
   `trading_system/scripts/benchmark_phase4_quant_performance.py`
   - Model it cleanly after `benchmark_phase3_quant_performance.py`.
   - Compare Baseline (Phase 3 Deep Enhancement v10) vs Target (Phase 4 Enhancement v11 Apex Quantitative Trading System).
   - Evaluate across all 5 operating equity markets:
     1. KOSPI (KRX Large-Cap)
     2. KOSDAQ (KRX Mid/Small-Cap Tech)
     3. S&P 500 (US Large-Cap Core)
     4. NASDAQ (US High-Growth Tech)
     5. RUSSELL 2000 (US Small-Cap Liquid)
   - Metrics to compute and compare:
     * Gross Expected Return (% annualized)
     * Net Expected Return (% annualized after frictions)
     * Total Return (% annualized)
     * Annualized Sharpe Ratio (Rf = 2.5%)
     * Information Coefficient (Spearman Rank-IC and Pearson IC)
     * Maximum Drawdown (MDD %)
     * Annualized Portfolio Turnover (%)
     * Trading & Friction Costs (bps)
     * Top-Decile Spread (% spread and Sharpe)
     * Execution Slippage (bps) & Darkpool/ATS Half-Spread Cost Savings (bps)
     * Win Rate (%) & Profit Factor
   - Attribution matrix for Phase 4 features:
     * Milestone 1 (M1): F21 (0.833 alpha unlock), F22 (softplus convex boost), F23 (tri-linear synergy kernel), F24 (sideways regime rebalancing), F25 (KER dynamic switching), F26 (asymmetric half-life filtering), F27 (regime-adaptive Bessembinder tail thresholds).
     * Milestone 2 (M2): F28 (downside semi-covariance Sortino EVT-CVaR), F29 (dynamic alpha dispersion conviction blending), F30 (Korean STT-aware Leland buffers), F31 (multi-tier L2 OBI micro-price pegging), F32 (Hawkes arrival intensity adverse selection gating), F33 (closed-loop empirical slippage feedback Gatheral scaling).

2. Execute the script:
   `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase4_quant_performance.py`
   Ensure it runs cleanly with exit code 0 and generates the output markdown files.

3. Save the comprehensive comparison Markdown tables to all 3 required file locations:
   - `d:\Finance\code\stock\reports\quant_benchmark_comparison_phase4.md`
   - `d:\Finance\code\stock\trading_system\result\quant_benchmark_comparison_phase4.md`
   - `d:\Finance\code\stock\reports\quant_benchmark_comparison.md`

4. Update documentation to reflect Phase 4 completion:
   - `d:\Finance\code\stock\AGENTS.md` (add Phase 4 completion entry in Requirements History table, update feature highlights).
   - `d:\Finance\code\stock\PROJECT.md` (update Milestones status, record Phase 4 achievements).

5. Run unit/integration tests to ensure no regressions:
   `.venv\Scripts\python.exe -m pytest tests/test_phase4_portfolio_execution.py tests/test_phase4_signal_enhancement.py -v`

6. Write `handoff.md` in your working directory with sections: Observation, Logic Chain, Caveats, Conclusion, Verification Method.
7. Notify parent via `send_message`.
