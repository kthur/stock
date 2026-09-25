# Dispatch: Explorer M0 Track 1 (R1 & R2 Numerical Stability)

## Working Directory
d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track1

## Original Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
d:\Finance\code\stock\ORIGINAL_REQUEST.md

## Objective
Investigate all failing test cases and numerical discrepancies related to Requirements R1 & R2:
- R1: Ensemble & Factor Numerical Stability (Phase 5, 6, 7 adversarial edge cases: all zeros, all ones, high NaN proportion 90-100%, extreme outliers, small universe 5-8 symbols; monotonic top-decile spread scaling).
- R2: Signal Enhancement & Gamma/Regime Adaptive Parameters (Phase 8, 9: hyper-exponential rank modulation, gamma_top reachability, multi-market regime branch ordering and backward compatibility).

Relevant tests to investigate:
- `tests/test_phase5_m1_challenger2_adversarial.py`
- `tests/test_phase5_signal_enhancement.py`
- `tests/test_phase6_*.py`
- `tests/test_phase7_*.py`
- `tests/test_phase8_*.py`
- `tests/test_phase9_*.py`
(Run pytest using `trading_system\.venv\Scripts\python.exe -m pytest tests -k "test_phase5_m1_challenger2_adversarial or test_phase5_signal_enhancement"` and any other Phase 6-9 tests that fail)

Relevant implementation source files:
- `src/ai/ensemble_scorer.py`
- `src/ai/score_normalizer.py`
- `src/ai/factor_suppression.py`

## Instructions
1. Run targeted pytest commands using `trading_system\.venv\Scripts\python.exe` to reproduce and identify every failing test in Track 1.
2. Read the source code and failing assertions to analyze the exact mathematical/numerical root causes.
3. Formulate a concrete, step-by-step fix strategy with exact file paths, line numbers, and proposed code modifications.
4. Output your full report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m0_track1\handoff.md`.
