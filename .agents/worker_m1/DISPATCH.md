# DISPATCH — Worker M1 (Phase 6 Milestone 1)

**Role**: Quantitative Signal Implementer
**Working Directory**: `d:\Finance\code\stock\.agents\worker_m1\`
**Authoritative Request**: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (see ## 2026-09-04T13:40:12Z)
**Technical Blueprint**: `d:\Finance\code\stock\.agents\explorer_m1_1\handoff.md` and `d:\Finance\code\stock\.agents\explorer_m1_1\analysis.md`
**Project Scope**: `d:\Finance\code\stock\.agents\orchestrator_quant_opt6\PROJECT.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own and may edit:
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase6_signal_enhancement.py`
Do NOT edit any other production files.

## Mission & Tasks
1. Read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` and `d:\Finance\code\stock\.agents\explorer_m1_1\handoff.md`.
2. Implement **F41 (High-Order Tensor Signal Coupling & Right-Tail Confidence Scaling)** in `src/ai/ensemble_scorer.py`:
   - **F41.1**: Quint-Pillar Economic Decomposition partitioning 37 strategies into 5 disjoint groups (`val`: 6, `mom`: 9, `flow`: 9, `cat`: 6, `net`: 7). Implement `compute_quint_pillar_tensor_synergy` with multi-linear contractions and regime caps up to 1.180x in `BULL_LOW_VOL`. Preserve backward compatibility for legacy `compute_bilinear_cross_pillar_synergy`.
   - **F41.2**: Adaptive Hölder $p(R)$-norm boost in `apply_top_decile_convex_boost` with regime-adaptive $p(R) \in [1.25, 2.50]$ and dispersion-adaptive sigmoid gating $\theta_{\text{gate}}(\sigma_{\text{cross}})$.
   - **F41.3**: Bilateral Asymmetric Generalized Richards S-Curve (Version 6) in `get_regime_adaptive_bessembinder_params` and `apply_bessembinder_convex_power_law` with independent left/right thresholds and exponents, strictly preserving rank monotonicity ($\rho_s \equiv 1.0000$).
3. Implement **F42 (Adaptive Regime Transition Half-Life & Noise Deadband Precision)**:
   - **F42.1**: Continuous-time Markov stationary distribution divergence $\phi_{\text{KL}}$ and 4-tier strategy-class elasticity ($\nu_A = 1.30, \nu_B = 1.00, \nu_C = 0.75, \nu_D = 0.40$) in `get_regime_adaptive_half_lives`.
   - **F42.2**: Asymmetric Kurtosis-Adaptive Noise Deadband in `apply_smooth_noise_deadband` and `get_regime_adaptive_noise_deadband` with asymmetric thresholds $(\delta^+, \delta^-)$ and exponent $\alpha(z) \in [3.0, 4.0]$.
4. Create `tests/test_phase6_signal_enhancement.py` containing the 6 rigorous test cases specified in Explorer M1-1's handoff.
5. Execute test verification using Python virtual environment:
   `$env:PYTHONPATH="trading_system;trading_system/src;."; .venv\Scripts\pytest.exe tests/test_phase6_signal_enhancement.py tests/test_phase5_signal_enhancement.py tests/test_phase4_signal_enhancement.py -v`
6. Verify 100% pass rate with zero regressions.
7. Write your complete handoff report to `d:\Finance\code\stock\.agents\worker_m1\handoff.md`.

## 2026-09-04T13:47:42Z
You are worker_m1.
Your working directory is: d:\Finance\code\stock\.agents\worker_m1\
Read d:\Finance\code\stock\.agents\worker_m1\DISPATCH.md and d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (mandatory).
Read d:\Finance\code\stock\.agents\explorer_m1_1\handoff.md and d:\Finance\code\stock\.agents\explorer_m1_1\analysis.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive Write Ownership:
- src/ai/ensemble_scorer.py
- src/ai/factor_suppression.py
- tests/test_phase6_signal_enhancement.py

Execute the implementation of F41 and F42 as specified.
Write and run tests in tests/test_phase6_signal_enhancement.py.
Run regression tests:
.venv\Scripts\python.exe -m pytest tests/test_phase6_signal_enhancement.py tests/test_phase5_signal_enhancement.py tests/test_phase4_signal_enhancement.py -v
Ensure all pass with 0 regressions.
Write handoff report to: d:\Finance\code\stock\.agents\worker_m1\handoff.md
Send completion message back to parent.
