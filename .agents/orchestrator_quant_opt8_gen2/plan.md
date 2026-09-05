# Execution Plan: Milestone 3 (R3 / F55) — Phase 8 Sovereign Quantitative Enhancements (v15)

## 1. Architecture & Background
- **Predecessor Milestones**:
  - Milestone 1 (R1: F51, F52): Riemannian manifold tensor synergy, hyperexponential rank modulation, Hurst-linked fractional jump diffusion mixture, asymmetric septic wavelet noise deadband. Verified & Audited CLEAN.
  - Milestone 2 (R2: F53, F54): 4-model R-Vine copula dynamic allocation, Information Entropy Parity (IEP), L3 orderbook 2nd-order queue acceleration, composite toxicity blending & peg shift, preemptive ATS liquidity harvesting up to 85%. Verified & Audited CLEAN.
- **Milestone 3 (R3 / F55) Objectives**:
  1. Create `trading_system/scripts/benchmark_phase8_quant_performance.py`:
     - Baseline: Phase 7 Zenith (v14)
     - Enhancement: Phase 8 Sovereign (v15)
     - 15 core institutional metrics across 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL 2000).
     - Strategic Factor Attribution Matrix for Features F51~F54.
     - Synchronized markdown output written to 3 canonical locations:
       - `reports/quant_benchmark_comparison_phase8.md`
       - `trading_system/result/quant_benchmark_comparison_phase8.md`
       - `reports/quant_benchmark_comparison.md`
  2. Create test suite `tests/test_benchmark_phase8.py`:
     - Test benchmark profiles completeness & strict monotonicity across all 15 metrics.
     - Test benchmark engine execution across all 5 markets and aggregate metrics.
     - Test markdown report generation and attribution matrix section presence.
     - Test benchmark subset market execution.
     - Test synchronized report file existence and content.
  3. Execute benchmark script and verify reports are generated.
  4. Run independent reviews (2 Reviewers), adversarial challenges (2 Challengers), and Forensic Integrity Audit (Auditor).
  5. Run full test suite regression gate across 2,580+ tests (`pytest tests/ -q`) to guarantee 0 regressions.
  6. Final handoff documentation and notification to Sentinel.

## 2. Iteration Loop & Subagents
- **Step 1: Worker Dispatch**:
  - Agent: `teamwork_preview_worker`
  - Scope: Implement `trading_system/scripts/benchmark_phase8_quant_performance.py`, `tests/test_benchmark_phase8.py`, execute script, run tests, and report results.
- **Step 2: Reviewers Dispatch (2 independent)**:
  - Agent: `teamwork_preview_reviewer` (2 instances)
  - Scope: Review code quality, mathematical consistency, attribution matrix, edge cases, report synchronization.
- **Step 3: Challengers Dispatch (2 independent)**:
  - Agent: `teamwork_preview_challenger` (2 instances)
  - Scope: Adversarial verification of metric computations, market weights, report consistency, failure resilience.
- **Step 4: Forensic Auditor Dispatch**:
  - Agent: `teamwork_preview_auditor`
  - Scope: Audit benchmark engine and test files for 0 hardcoded results, 0 facades, authentic simulation, proper error handling.
- **Step 5: Full Regression Gate**:
  - Worker runs full test suite: `.venv\Scripts\python.exe -m pytest tests/ -q`
  - Expected: 100% pass across all 2,580+ tests with 0 regressions.
- **Step 6: Synthesis & Final Handoff**:
  - Synthesize findings, update gate status, generate final `handoff.md`, notify Sentinel.
