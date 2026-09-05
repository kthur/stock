## 2026-09-06T07:34:05Z
You are Worker 1 (Alpha Signal Specialist) for Phase 17 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase17_alpha\
The authoritative original request is located at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
The detailed Survey Handoff Report is located at: d:\Finance\code\stock\.agents\explorer_quant_phase17_alpha\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Exclusive File Ownership:
- src/ai/factor_suppression.py
- src/ai/ensemble_scorer.py
- tests/test_phase17_signal_enhancement.py

Task Instructions:
1. Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md and d:\Finance\code\stock\.agents\explorer_quant_phase17_alpha\handoff.md.
2. In src/ai/factor_suppression.py and src/ai/ensemble_scorer.py:
   - Implement Feature F88.2: 32nd-Order (Dotriacontagonal, alpha=32.0) Hyperbolic Tangent Deadband `apply_dotriacontagonal_hyperbolic_deadband` and integrate into `apply_smooth_deadband_attenuation` when version >= 17.
   - Implement Feature F88.1: 12th-Order Ultra-Convex Rank Modulation $g_{\text{v17}}(r) = 0.50 + 1.00 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^{12})$ (with negative branch $1.35 - 1.00 \cdot r$), regime-adaptive $\gamma_{\text{top}}$ parameters (Bull Low Vol: 1.80, Bull High Vol: 1.55, Sideways Low Vol: 1.35, Sideways High Vol: 1.00, Bear Low Vol: 0.78, Bear High Vol: 0.52, Crisis: 0.32), and integrate into `combine_predictions` when version >= 17.
   - Implement Feature F87: Homological Mirror Symmetry & Fukaya Category Factor Disentanglement Engine `HomologicalMirrorSymmetryCoupler` class with symplectic flux $\Omega_{jk} = \theta_0 \frac{j-k}{1+|j-k|}$ ($\theta_0=0.18$), Lagrangian intersection instanton area $\mathcal{A}_{jk} = |\Omega_{jk}| [0.5(p_j - p_k)^2 + \lambda_{\text{inst}}(1 - \cos(\pi(p_j - p_k)))]$, mirror Ext discrepancy $\Delta_{\text{HMS}, jk} = |\Omega_{jk}| |(p_j^2 - p_k^2) + \lambda_{\text{ext}}(p_j^3 - p_k^3)|$, total obstruction energy $E_{\text{HMS}}$, topological invariant $Z_{\text{HMS}}$, Floer coupling $h_{\text{HMS}}$, Factor Energy Regularity Index $\text{FERI}_{\text{v17}}$, and $+0.35 \cdot h_{\text{HMS}} \cdot Z_{\text{HMS}}$ regularizer boost in `compute_quint_pillar_tensor_synergy`.
   - Expose aliases and class methods `compute_homological_mirror_symmetry_coupling` in `EnsembleScoringEngine`.
3. Create comprehensive test suite `tests/test_phase17_signal_enhancement.py` verifying noise leakage (< 1e-20), 100% transmission at conviction, strict rank monotonicity, strict convexity, input shapes (DataFrame, Dict, 2D, 1D), full `combine_predictions(version=17)` execution, and backward compatibility.
4. Execute tests using `.venv\Scripts\pytest.exe tests/test_phase17_signal_enhancement.py -v`.
5. Write your handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase17_alpha\handoff.md` detailing changes, formulas, test commands and passing output.
6. When done, send a message back to the orchestrator.
