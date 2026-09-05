# Dispatch to Alpha Signal Specialist (Worker M1)

## Mission: Milestone M1 — Alpha Signal Enhancement (R1)
You are the Alpha Signal Specialist. Implement Phase 16 Alpha Signal innovations according to:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically request `## 2026-09-05T14:24:02Z`)
- `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey\handoff.md` (specifically Section 1.1, 2.1, 4.1)
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_phase16\PROJECT.md`

## File Ownership (Exclusively Owned)
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase16_signal_enhancement.py`
DO NOT touch any other files outside your ownership.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Specifications
1. **Sheaf Cohomology Factor Disentanglement**:
   - Implement `QuantumToposSheafCoupler` in `trading_system/src/ai/ensemble_scorer.py`.
   - Calculate obstruction energy $E_{\text{sheaf}}$, global section coherence $Z_{\text{sheaf}}$, coupling factor $h_{\text{sheaf}}$, and $\text{FERI}_{\text{v16}}$.
   - Provide static binding `compute_quantum_topos_sheaf_coupling` on `EnsembleScoringEngine`.
2. **11th-Order Ultra-Convex Rank Modulation ($g_{\text{v16}}$)**:
   - Implement `compute_phase16_hyperconvex_rank_modulation(ranks, gamma_top=1.0, z_denoised=None)`:
     $$g_{\text{v16}}(r) = 0.50 + 0.95 \cdot r \cdot \exp\left(\gamma_{\text{top}} \cdot r^{11}\right) \quad (\text{for } z \ge 0)$$
     $$g_{\text{neg}}(r) = 1.40 - 0.95 \cdot r \quad (\text{for } z < 0)$$
   - Wire into `combine_predictions` for `int(version) >= 16`.
   - Update `get_regime_adaptive_gamma_top` for `version >= 16` with expanded parameters:
     CRISIS: 0.30, BEAR_HIGH_VOL: 0.50, BEAR_LOW_VOL: 0.75, SIDEWAYS_HIGH_VOL: 0.95, SIDEWAYS_LOW_VOL: 1.30, BULL_HIGH_VOL: 1.50, BULL_LOW_VOL: 1.75, Default: 1.35.
3. **28th-Order Octacosagonal Hyperbolic Deadband**:
   - Implement `apply_octacosagonal_hyperbolic_deadband` with $\alpha=28.0$ in `trading_system/src/ai/ensemble_scorer.py` and `trading_system/src/ai/factor_suppression.py`.
   - Wire into `apply_smooth_noise_deadband` for `int(version) >= 16` setting `eff_alpha = 28.0`.
4. **Unit Tests**:
   - Create comprehensive unit test suite `tests/test_phase16_signal_enhancement.py`.
   - Execute tests via `.venv\Scripts\pytest tests/test_phase16_signal_enhancement.py tests/test_phase15_signal_enhancement.py -v`.
   - Ensure 100% tests pass with 0 regressions.

## Deliverable
Write your completion report to `d:\Finance\code\stock\.agents\teamwork_preview_worker_alpha\handoff.md`.
Send completion message to orchestrator via `send_message`.

## 2026-09-05T14:34:13Z
Alpha Signal Specialist invoked for Milestone M1 (Alpha Signal Enhancement).
Scope:
1. Sheaf cohomology factor disentanglement (QuantumToposSheafCoupler).
2. 11th-order ultra-convex rank modulation (g_v16).
3. 28th-order octacosagonal hyperbolic deadband (alpha=28.0).
4. Create tests/test_phase16_signal_enhancement.py and verify via .venv\Scripts\pytest.
5. Ensure 100% tests pass with 0 regressions.

