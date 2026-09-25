# Orchestration Plan: Core Trading System Integrity & Remediation

## Objective
Remediate ~116 failing test cases and numerical discrepancies across core trading and prediction modules (signal enhancement, ensemble scoring, ML predictors, and benchmark sync) to achieve 100% test pass rate with 0 regressions across 5,624+ passing tests and full pipeline integrity.

## Scope & Requirements Breakdown
- **R1: Ensemble & Factor Numerical Stability** (Phase 5, 6, 7 adversarial edge cases: all zeros/ones, high NaN 90-100%, extreme outliers, small universe 5-8 symbols, monotonic top-decile spread scaling).
- **R2: Signal Enhancement & Gamma/Regime Adaptive Parameters** (Phase 8, 9: hyper-exponential rank modulation, gamma_top reachability, multi-market regime branch ordering and backward compatibility).
- **R3: Benchmark Report & SHA256 Hash Synchronization** (Phase 60~65: reconciliation of markdown benchmark reports and SHA256 hashes).
- **R4: Machine Learning Predictors & Alpha Returns Maximization** (TransformerPredictor tensor shape/forward pipeline, Sprint 3 Multivariate LSTM, v7 returns maximization / P90 hurdle rate & unscaled costs).
- **R5: Zero Regressions & End-to-End Pipeline Integrity** (Preserve 5,624+ existing passing tests, verify `trading_system/run_pipeline.py` executable without syntax/import errors).

## Execution Strategy (Dual/Multi-Track Project Pattern)
### Phase 0: Survey & Initial Diagnostics
- Explorer 1: Investigate R1 & R2 failures (`test_phase5_m1_challenger2_adversarial`, `test_phase5_signal_enhancement`, Phase 6-9 tests in `src/ai/ensemble_scorer.py`, `src/ai/factor_suppression.py`, `src/ai/score_normalizer.py`).
- Explorer 2: Investigate R4 failures (`test_transformer_predictor`, `test_sprint3_alpha_refactor`, `test_v7_returns_maximization`, `src/ai/` predictors).
- Explorer 3: Investigate R3 failures (`test_phase60_adversarial_oms_benchmark` through `test_phase65_adversarial_oms_benchmark`, report markdown files and SHA256 mismatch).

### Phase 1: Remediation Execution
- Milestone 1 (M1): Track 1 Remediation (R1 & R2 Ensemble & Factor Stability)
- Milestone 2 (M2): Track 2 Remediation (R4 ML Predictors & Alpha Maximization)
- Milestone 3 (M3): Track 3 Remediation (R3 Benchmark Report & SHA256 Sync)

### Phase 2: Full System Gate & Regression Audit
- Milestone 4 (M4): Track 4 Verification (Full test suite `not benchmark_phase`, pipeline integrity `run_pipeline.py`, 0 regressions).
- Independent Challenger & Forensic Auditor verification across all modified modules.

### Phase 3: Final Synthesis & Sentinel Report
- Completion synthesis, handoff.md generation, and final status reporting to Sentinel.
