# DISPATCH: Reviewer 1 (Alpha Signal & Risk Allocation Verification)

## Identity & Role
- Archetype: teamwork_preview_reviewer
- Role: Code Reviewer & Verifier (Alpha & Risk)
- Working directory: `d:\Finance\code\stock\.agents\reviewer_phase24_1`

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
Thoroughly review code correctness, mathematical rigor, robustness, boundary cases, and interface consistency for R1 and R2:
1. F115 Derived Arithmetic Topology & Étale-Motivic Spectral Homotopy Coupler.
2. F116.1 19th-Order Hyper-Convex Rank Modulation ($g_{\text{v24}}(r) = 0.50 + 1.12 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{19})$, $\gamma_{\text{top}} \le 2.50$).
3. F116.2 60th-Order Hexacontagonal Hyperbolic Noise Deadband ($\alpha=60.0$, noise leakage $< 10^{-32}$).
4. F117.1 Lurie Arithmetic Spectral Fisher-Rao Manifold Barycenter Blending with metric weights $\mu_{\text{arithmetic}} = [2.15, 1.65, 1.60, 2.70]$.
5. F117.1.2 20th-Order Cumulant Expansion Trans-Super-Hyper EVaR ($20! = 2,432,902,008,176,640,000$, $\xi_{\text{super\_hyper}} = 0.80$).
6. Version branching `version >= 24` with 100% backward compatibility for v13–v23.

Run test commands:
`.venv\Scripts\python.exe -m pytest tests/test_phase24_alpha.py tests/test_phase24_risk.py tests/test_phase23_*.py -v`

Deliver a clear verdict (APPROVE or REQUEST_CHANGES) with supporting evidence in `handoff.md`.

## 2026-09-11T11:22:24Z
You are Reviewer 1 (Alpha Signal & Risk Allocation Verification).
Your working directory is: d:\Finance\code\stock\.agents\reviewer_phase24_1
Read your dispatch at: d:\Finance\code\stock\.agents\reviewer_phase24_1\DISPATCH.md
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-11T10:54:49Z).

Review code correctness, math, robustness, and tests for:
- src/ai/ensemble_scorer.py
- src/ai/factor_suppression.py
- src/risk/unified_portfolio_allocator.py
- src/risk/portfolio_allocator.py
- tests/test_phase24_alpha.py
- tests/test_phase24_risk.py

Run test suite:
.venv\Scripts\python.exe -m pytest tests/test_phase24_alpha.py tests/test_phase24_risk.py tests/test_phase23_*.py -v

Deliver your verdict (APPROVE or REQUEST_CHANGES) with detailed evidence in `d:\Finance\code\stock\.agents\reviewer_phase24_1\handoff.md` and send a message when done.
