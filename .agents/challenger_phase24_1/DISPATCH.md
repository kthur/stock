# DISPATCH: Challenger 1 (Adversarial Verifier: Alpha & Risk)

## Identity & Role
- Archetype: teamwork_preview_challenger
- Role: Adversarial Stress Tester (Alpha & Risk)
- Working directory: `d:\Finance\code\stock\.agents\challenger_phase24_1`

## Inputs
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-11T10:54:49Z`)
- Project Scope: `d:\Finance\code\stock\PROJECT.md`
- Target Code Files:
  - `src/ai/ensemble_scorer.py`
  - `src/ai/factor_suppression.py`
  - `src/risk/unified_portfolio_allocator.py`
  - `src/risk/portfolio_allocator.py`
  - `tests/test_phase24_alpha.py`
  - `tests/test_phase24_risk.py`

## Objective
Design and execute adversarial stress tests to empirically challenge the Alpha & Risk implementations:
1. Alpha Stress:
   - Extreme rank modulation inputs ($r \in [0.9999, 1.0]$, $r < 0$, $r > 1$, negative/zero $\gamma_{\text{top}}$).
   - 60th-order deadband: test noise leakage bounds across $[-0.005, 0.005]$ ($< 10^{-32}$), high conviction transmission at $|z| \ge 0.150$ ($100.000\%$).
   - F115 Étale-Motivic Coupler: test numerical stability under ill-conditioned matrices, zero correlation, collinear signals, NaNs/Infs.
2. Risk Stress:
   - F117.1 Lurie Arithmetic Spectral Fisher-Rao Barycenter: test Dirac distributions ($[1, 0, 0, 0]$), boundary states on $\Delta^3$, extreme perturbations, convergence speed.
   - F117.1.2 20th-Order Trans-Super-Hyper EVaR: verify exact factorial calculation ($20! = 2,432,902,008,176,640,000$), test under extreme fat-tail synthetic distributions (Cauchy, Pareto $\alpha=1.1$, Student-t $\nu=2.1$, Black Swan -50% shocks), and verify coherent tail risk monotonicity ($\text{VaR} \le \text{CVaR} \le \dots \le \text{Trans-Super-Hyper-EVaR}$).

Run adversarial test scripts via `.venv\Scripts\python.exe`.
Deliver a clear verdict (APPROVE or REQUEST_CHANGES) with empirical evidence in `handoff.md`.

## 2026-09-11T11:22:24Z
You are Challenger 1 (Adversarial Empirical Verifier: Alpha & Risk).
Your working directory is: d:\Finance\code\stock\.agents\challenger_phase24_1
Read your dispatch at: d:\Finance\code\stock\.agents\challenger_phase24_1\DISPATCH.md
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-11T10:54:49Z).

Empirically stress-test Alpha & Risk implementations:
1. Alpha stress: Extreme rank modulation inputs ($r \to 1.0, r < 0$), 60th-order deadband leakage across $[-0.005, 0.005]$ ($< 10^{-32}$), high conviction transmission at $|z| \ge 0.150$ ($100.000\%$), F115 Étale-Motivic Coupler numerical stability.
2. Risk stress: F117.1 Lurie Arithmetic Spectral Fisher-Rao Barycenter on boundary states and Dirac measures, F117.1.2 20th-Order Trans-Super-Hyper EVaR ($20! = 2,432,902,008,176,640,000$, $\xi_{\text{super\_hyper}}=0.80$), fat-tail synthetic distributions (Cauchy, Pareto, Student-t, Black Swan), and coherent tail risk hierarchy.

Run your stress tests using `.venv\Scripts\python.exe`.
Deliver your verdict (APPROVE or REQUEST_CHANGES) with empirical evidence in `d:\Finance\code\stock\.agents\challenger_phase24_1\handoff.md` and send a message when done.

