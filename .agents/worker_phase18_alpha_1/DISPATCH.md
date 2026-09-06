## 2026-09-05T23:24:14Z
<USER_REQUEST>
You are Worker R1 (Alpha Signal Specialist) for Phase 18 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase18_alpha_1
You MUST read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md before starting work.
Also review the handoff reports from:
- d:\Finance\code\stock\.agents\explorer_phase18_arch_1\handoff.md
- d:\Finance\code\stock\.agents\spec_miner_phase18_1\handoff.md
Project guidelines: d:\Finance\code\stock\AGENTS.md

WRITE OWNERSHIP:
You exclusively own:
- `src/ai/ensemble_scorer.py`
- `src/ai/factor_suppression.py`
- `tests/test_phase18_signal_enhancement.py`
DO NOT edit files outside this scope!

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR TASKS:
1. Feature F92.2: Implement 36th-Order Hexatriacontagonal Hyperbolic Noise Deadband (`apply_hexatriacontagonal_hyperbolic_deadband`):
   - $\alpha = 36.0$, $\delta_{\text{noise}} = 0.035$, ensuring noise leakage $< 10^{-20}$ for $|z| \le 0.005$, and 100% transmission for $|z| \ge 0.150$.
   - Register in `factor_suppression.py` and `ensemble_scorer.py`.
2. Feature F92.1: Implement 13th-Order Hyper-Convex Rank Modulation (`compute_phase18_hyperconvex_rank_modulation`):
   - $g_{\text{v18}}(r) = 0.50 + 1.00 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{13})$ for $z \ge 0$, and $1.35 - 1.00 \cdot r$ for $z < 0$.
   - Update `get_regime_adaptive_gamma_top` for `version >= 18` (e.g. BULL_LOW_VOL: 1.85, CRISIS: 0.35, etc.).
3. Feature F91: Implement `DerivedAlgebraicGeometryMotivicCoupler`:
   - Obstruction complex $E_{\text{derived}}$, motivic cohomology algebraic cycle invariants $Z_{\text{derived}}$, coupling factor $h_{\text{derived}}$, and $\text{FERI}_{\text{v18}}$.
   - Integrate into `combine_predictions` under `version >= 18`.
4. Create comprehensive unit tests in `tests/test_phase18_signal_enhancement.py` verifying all mathematical properties, boundary behaviors, and backward compatibility.
5. Run tests via `.venv\Scripts\pytest.exe -p no:cov tests/test_phase18_signal_enhancement.py -v` (and existing signal enhancement tests). Ensure all pass!
6. Write a complete handoff report to `d:\Finance\code\stock\.agents\worker_phase18_alpha_1\handoff.md` and send a completion message to parent.
</USER_REQUEST>
