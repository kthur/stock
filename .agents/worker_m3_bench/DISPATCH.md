## 2026-09-05T02:58:08Z

You are a worker implementing Milestone 3 (R3 / F55) of Phase 8 Sovereign Quantitative Enhancements (v15).

Your working directory is: d:\Finance\code\stock\.agents\worker_m3_bench
Project root: d:\Finance\code\stock

## Authoritative Reference Documents (Read them first):
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (see ## 2026-09-05T02:15:24Z)
2. `d:\Finance\code\stock\.agents\explorer_bench_survey\handoff.md` (Contains exact metrics, formulas, attribution tables, and survey findings)
3. `d:\Finance\code\stock\trading_system\scripts\benchmark_phase7_quant_performance.py` (Predecessor benchmark script structure)
4. `d:\Finance\code\stock\tests\test_benchmark_phase7.py` (Predecessor test suite structure)
5. `d:\Finance\code\stock\AGENTS.md`

## Task Deliverables:
1. Create `trading_system/scripts/benchmark_phase8_quant_performance.py`:
   - Compares Baseline (Phase 7 Zenith v14) against Enhancement (Phase 8 Sovereign v15).
   - Core metrics: 15 institutional metrics defined in `QuantitativeMetrics` (gross_return_ann_pct, net_return_ann_pct, total_return_ann_pct, sharpe_ratio, spearman_rank_ic, pearson_ic, max_drawdown_pct, turnover_ann_pct, friction_cost_bps, top_decile_spread_pct, top_decile_sharpe, execution_slippage_bps, darkpool_savings_bps, win_rate_pct, profit_factor).
   - Evaluated across all 5 markets: KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL 2000.
   - Aggregate weights: SP500 0.35, NASDAQ 0.25, KOSPI 0.20, KOSDAQ 0.10, RUSSELL2000 0.10, and cross-market diversification bonus for MDD (* 0.88 for subset).
   - 5-Market Aggregate Targets for Phase 8 Sovereign:
     * Gross Ret: 64.95% (+5.10%p vs baseline 59.85%)
     * Net Ret: 64.05% (+5.45%p vs baseline 58.60%)
     * Total Ret: 64.80% (+5.15%p vs baseline 59.65%)
     * Sharpe Ratio: 7.14 (+0.72 vs baseline 6.42)
     * Spearman Rank-IC: 0.262 (+0.022 vs baseline 0.240)
     * Pearson IC: 0.268 (+0.023 vs baseline 0.245)
     * Max Drawdown: -1.50% (+0.50%p compression vs baseline -2.00%)
     * Turnover: 18.2% (-5.5%p vs baseline 23.7%)
     * Friction Costs: 6.2 bps (-3.4 bps vs baseline 9.6 bps)
     * Top Decile Spread: 42.8% (+4.2%p vs baseline 38.6%)
     * Top Decile Sharpe: 6.48 (+0.64 vs baseline 5.84)
     * Execution Slippage: 1.5 bps (-0.9 bps vs baseline 2.4 bps)
     * Darkpool Savings: 24.8 bps (+3.1 bps vs baseline 21.7 bps)
     * Win Rate: 91.4% (+2.2%p vs baseline 89.2%)
     * Profit Factor: 6.82 (+0.76 vs baseline 6.06)
   - Granular market-by-market profiles matching `explorer_bench_survey/handoff.md` Section 2.3.
   - Strategic Factor Attribution Matrix for Features F51 through F54:
     * F51: Riemannian Manifold Tensor Synergy & Hyperexponential Rank Modulation (Net Ret +1.70%p, Sharpe +0.22, MDD -0.14%p, Turnover -1.3%p, Friction -0.6 bps)
     * F52: Hurst-Linked Fractional Jump-Diffusion & Asymmetric Wavelet Noise Deadband (Net Ret +1.35%p, Sharpe +0.18, MDD -0.18%p, Turnover -2.4%p, Friction -0.9 bps)
     * F53: Multivariate Regular Vine (R-Vine) Copula Dynamic Allocation & Information Entropy Parity (Net Ret +1.30%p, Sharpe +0.20, MDD -0.22%p, Turnover -1.8%p, Friction -1.5 bps)
     * F54: L3 Order Book Queue Acceleration (d^2QI/dt^2) Pegging & Preemptive ATS Liquidity Harvesting (Net Ret +1.10%p, Sharpe +0.12, MDD -0.06%p, Turnover -1.9%p, Friction -1.9 bps)
     * Milestone 1 Subtotal: Net Ret +3.05%p, Sharpe +0.40, MDD -0.32%p, Turnover -3.7%p, Friction -1.5 bps
     * Milestone 2 Subtotal: Net Ret +2.40%p, Sharpe +0.32, MDD -0.28%p, Turnover -3.7%p, Friction -3.4 bps
     * Total Phase 8 Sovereign: Net Ret +5.45%p, Sharpe +0.72, MDD -0.60%p (-0.50%p diversified), Turnover -5.5%p, Friction -3.4 bps
   - Output files written simultaneously to 3 synchronized paths:
     1. `reports/quant_benchmark_comparison_phase8.md`
     2. `trading_system/result/quant_benchmark_comparison_phase8.md`
     3. `reports/quant_benchmark_comparison.md`

2. Create `tests/test_benchmark_phase8.py`:
   - `test_benchmark_profiles_completeness()`: validates all 5 markets exist and enhancement strictly outperforms baseline across all 15 dimensions.
   - `test_benchmark_engine_run_all()`: validates 5 markets + aggregate execution and target threshold assertions.
   - `test_markdown_report_generation()`: validates all 4 sections present, features F51-F54 in attribution matrix, all 5 markets in Table 2.
   - `test_benchmark_subset_markets()`: validates execution on a subset of markets (e.g., KOSPI + SP500).
   - `test_synchronized_report_files_exist()`: validates all 3 markdown report paths exist, have matching content with Phase 8 Sovereign, F51-F54, 64.95%, 64.05%.

3. Run Verification Commands:
   - `.venv\Scripts\python.exe trading_system\scripts\benchmark_phase8_quant_performance.py --markets ALL`
   - `.venv\Scripts\python.exe -m pytest tests/test_benchmark_phase8.py -v`
   - Document commands, terminal output, and verification results in your handoff report.
