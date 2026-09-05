## 2026-09-05T13:54:37Z

You are a Worker subagent for the Quantitative Full Team Optimization project.
Working directory: d:\Finance\code\stock\.agents\worker_fullteam_1
Original request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (read the latest request under ## 2026-09-05T13:47:02Z).
Project rules: d:\Finance\code\stock\AGENTS.md.
Plan & Survey references:
- d:\Finance\code\stock\.agents\orchestrator_quant_fullteam_1\plan.md
- d:\Finance\code\stock\.agents\explorer_survey_1\survey_report.md and handoff.md
- d:\Finance\code\stock\.agents\explorer_survey_2\survey_report.md and handoff.md
- d:\Finance\code\stock\.agents\explorer_survey_3\survey_report.md and handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Fix the version plumbing and dynamic deadband propagation in trading_system/src/ai/ensemble_scorer.py and trading_system/run_pipeline.py:
   - In run_pipeline.py line 3473: ensure version=15 is passed to calculate_ensemble_score().
   - In ensemble_scorer.py line 3311: default version to 15 (instead of 5).
   - In ensemble_scorer.py lines 4596–4601: dynamicize version passing in apply_smooth_noise_deadband() so it uses the active version (e.g. 15 for 24th-order deadband) rather than hardcoded 13.
2. Verify that all components for R1, R2, R3, R4 are in pristine working order:
   - R1: Factor unentanglement (PCA-ZCA whitening, factor suppression), rank modulation (g_v15), tetracosagonal hyperbolic deadband.
   - R2: 4-model blending with Langlands Automorphic Hecke Operator Fisher-Rao Barycenter on S^3, 6th-order cumulant EVaR budgeting with CCVaR headroom redistribution, Ledoit-Wolf + Hybrid EWMA covariance, asymmetric Leland buffer bands with boundary rebalancing.
   - R3: L3 fluid dynamics (QI_L3*, a_QI, j_QI, Deep-OFI), preemptive ATS darkpool routing (up to 99%), lit maker contraction (0.0005), anti-gaming MinQty (99.5%), multivariate Hawkes preemptive tick shading, and closed-loop slippage feedback.
   - R4: Execute benchmark evaluation across all 5 markets via trading_system/scripts/benchmark_phase15_quant_performance.py, ensuring the 3 standard tables ([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표) are fully generated and synchronized into reports/quant_benchmark_comparison_phase15.md and reports/quant_benchmark_comparison.md.
3. Validate all 6 Acceptance Criteria targets:
   - Net Expected Return >= 95.0%
   - Annualized Sharpe Ratio >= 12.0
   - Maximum Drawdown (MDD) <= -0.18%
   - Trading & Friction Costs <= 0.6 bps
   - Execution Slippage <= 0.05 bps
   - Top-Decile Alpha Spread >= 65.0%
4. Run tests with .venv\Scripts\python.exe -m pytest:
   - tests/test_benchmark_phase15.py
   - tests/test_factor_orthogonalization.py
   - tests/test_correlation_suppression.py
   - tests/test_phase15_portfolio_execution.py
   Ensure all tests pass 100% with zero regression.
5. Write your detailed report to d:\Finance\code\stock\.agents\worker_fullteam_1\changes.md and complete with handoff.md. Send a completion message back to parent.
