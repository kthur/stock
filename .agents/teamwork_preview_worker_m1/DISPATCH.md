## 2026-09-04T23:30:24Z

Target Milestone: Milestone 1 (M1) — Dynamic Alpha Signal Synergy & Right-Tail Confidence 7th Deepening (Features F47 & F48).

Read the following reference and blueprint artifacts created by the M1 Explorers:
- d:\Finance\code\stock\.agents\orchestrator_quant_opt7\PROJECT.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_1\exploration_report.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\exploration_report.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\exploration_report.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\proposed_factor_suppression.patch
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\proposed_ensemble_scorer.patch
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\proposed_test_phase7_signal_enhancement.py

Your Exclusive File Write Ownership:
- `trading_system/src/ai/ensemble_scorer.py` (and `src/ai/ensemble_scorer.py` if present / check symlink)
- `trading_system/src/ai/factor_suppression.py` (and `src/ai/factor_suppression.py` if present / check symlink)
- `tests/test_phase7_signal_enhancement.py`

Implementation Objectives:
1. `factor_suppression.py`:
   - Implement `apply_quintic_hyperbolic_deadband(z, delta, alpha=5.0)` with true C^infinity quintic soft-thresholding ($z \cdot \tanh((|z|/\delta)^5)$), reducing near-zero noise leakage to 0.054%, preserving odd symmetry and strict rank monotonicity.
2. `ensemble_scorer.py`:
   - In `compute_quint_pillar_tensor_synergy`: add `version: int = 6` default (preserving exact Phase 6 behavior when version<=6). When `version >= 7`, apply 1.40x boost on core trilinear `('val', 'mom', 'flow')`, 1.20x boost on `('flow', 'cat', 'net')`, calculate Pillar Harmony Regularizer H_pillar = exp(-1.20 * CV_psi^2), expand `BULL_LOW_VOL` cap to 0.220 (1.220x multiplier), strictly preserve `CRISIS` cap at 0.040 (1.040x multiplier), and preserve strict 5 > 4 > 3 > 2 > 1 hierarchy.
   - In `combine_predictions`: forward `version=version` to `compute_quint_pillar_tensor_synergy`, and apply Quartic Rank Modulation $g_{\text{v7}}(r) = 0.60 + 0.25 r + 0.25 r^2 + 0.40 r^3 + 0.35 r^4$ when `version >= 7`.
   - In `get_base_weights`: add `version: int = 6` default. When `version >= 7` and total variation distance $d_{TV} > 0.25$, apply Merton Jump-Diffusion mixture: $w_{\text{Zenith}}^* = (1 - 0.60 J_{\text{regime}}) w_{\text{diffusion}} + 0.60 J_{\text{regime}} W_{2D}(R_{\text{jump}})$.
   - In `get_regime_adaptive_half_lives`: when `version >= 7`, calculate Net Volatility Shift $S_{\text{vol}} = \Pi_{t, \text{high}} - 0.43$ and modulate $\kappa_{\text{Markov}}(S_{\text{vol}}) = \text{clip}(0.25(1 + 0.80 \max(0, S_{\text{vol}})), 0.25, 0.45)$, while preserving exact Phase 6 half-lives when $S_{\text{vol}} \le 0$ or `version <= 6`.
   - In `apply_smooth_noise_deadband`: integrate `apply_quintic_hyperbolic_deadband` for `version >= 7`.
3. Create `tests/test_phase7_signal_enhancement.py`:
   - Implement the 7 comprehensive unit/integration test cases designed by Explorer 3.
4. Execute verification tests via command line:
   - `.venv\Scripts\pytest.exe tests/test_phase7_signal_enhancement.py -v`
   - `.venv\Scripts\pytest.exe tests/test_phase6_signal_enhancement.py tests/test_phase6_m1_challenger1_adversarial.py tests/test_phase6_m1_challenger2_adversarial.py -v`
5. Report all build and test command outputs in `d:\Finance\code\stock\.agents\teamwork_preview_worker_m1\handoff.md`.
