## 2026-09-17T12:19:03Z
You are the Alpha Signal Specialist Worker for Phase 49 Quantitative Enhancement (Milestone M1).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase49_m1_1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Read the authoritative inputs:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-17T12:06:49Z)
2. d:\Finance\code\stock\.agents\orchestrator_quant_phase49_1\DISPATCH.md
3. d:\Finance\code\stock\.agents\explorer_quant_phase49_1\report.md
4. d:\Finance\code\stock\.agents\explorer_quant_phase49_1\handoff.md
5. tests/test_phase48_alpha.py (as blueprint for test_phase49_alpha.py)

Files you exclusively own and modify:
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase49_alpha.py` (new test suite)

Implementation Tasks:
1. Feature F216: Quantum Geometric Langlands Chiral Affine Borcherds-Moonshine Monster Whittaker Coupler
   - Extend `QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler` in `ensemble_scorer.py` (both definitions if present, e.g. line 115 and line 553):
     - Deformation polynomials up to 68th order: `+ (1.0 / 68.0) * (self.lambda_conformal * 0.00000002) * (diff ** 68)`
     - Topological defect polynomials up to 34th order: `+ (self.lambda_vertex * 0.000000001) * (pn[j]**34 - pn[k]**34)`
     - Parameters: kappa=10.50, lambda=0.82 for Phase 49
     - Support return of `FERI_v49`, `feri_v49`
   - In `combine_predictions` of `EnsembleScoringEngine`:
     - Gate evaluation under `if version >= 49:` (and preserve version >= 48 for backward compatibility)
     - Harmony factor boost: `+ (2.95 * h_monster_whit * z_monster_whit if version >= 49 else ...)`
   - Export and bind all 26 backward-compatible aliases on `EnsembleScoringEngine` and module level, as listed in `explorer_quant_phase49_1\report.md`.
2. Feature F217.1: 44th-order hyper-convex rank modulation
   - In `factor_suppression.py` and `ensemble_scorer.py`:
     - $g_{\text{v49}}(r) = 0.50 + 1.58 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{44})$ for $z \ge 0$, and $1.35 - 1.00 \cdot r$ for $z < 0$.
     - Regime-adaptive $\gamma_{\text{top}}$ up to 6.50 (`BULL_LOW_VOL`: 6.50, `BULL_HIGH_VOL`: 5.20, `SIDEWAYS_LOW_VOL`: 3.90, `SIDEWAYS_HIGH_VOL`: 2.60, `BEAR_LOW_VOL`: 1.30, `BEAR_HIGH_VOL`/`CRISIS`: 0.65).
     - At $r=0.70$, $g(0.70) \le 1.61 < 1.62$. At $r=1.00$, $g(1.00) \approx 1051.4 > 460.0$.
3. Feature F217.2: 200th-order bicentagonal hyperbolic noise deadband
   - Implement `apply_bicentagonal_hyperbolic_deadband` in `factor_suppression.py` and `ensemble_scorer.py`:
     - $z_{\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{eff}})^{200})$ where $\alpha=200.0, \delta=0.035$.
     - Bound leakage at $|z| \le 0.00035$ strictly to $< 10^{-120}$ ($0.0$).
     - Preserve $100.0\%$ of signals for $|z| \ge 0.15$.
4. Test Suite `tests/test_phase49_alpha.py`:
   - Build comprehensive unit test suite covering Coupler invariants, deformation order 68, defect order 34, all 26 aliases, 44th-order rank modulation values at bounds, and 200th-order deadband leakage.
   - Run verification using `.venv\Scripts\pytest.exe tests/test_phase49_alpha.py` and regression test `.venv\Scripts\pytest.exe tests/test_phase48_alpha.py`.

Deliverables:
- Implement the code and tests.
- Run tests and ensure 100% PASS with zero errors.
- Write a complete `handoff.md` and update `progress.md`.
- Send completion message to parent when done.
