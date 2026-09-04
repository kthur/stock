## 2026-09-04T08:44:17Z
You are Worker M1 for Phase 5 Deep Quantitative Enhancements (Milestone 1).
Your working directory is: d:\Finance\code\stock\.agents\worker_m1

MANDATORY FIRST STEP:
Read the following authoritative files:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically header ## 2026-09-04T08:36:42Z)
2. d:\Finance\code\stock\PROJECT.md
3. d:\Finance\code\stock\.agents\orchestrator_quant_opt5\SCOPE.md
4. d:\Finance\code\stock\.agents\explorer_survey_1\analysis.md and handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write Ownership (Exclusive):
You exclusively own and may modify or create:
- 	rading_system/src/ai/ensemble_scorer.py (or src/ai/ensemble_scorer.py)
- 	ests/test_phase5_signal_enhancement.py

Mission:
Implement Milestone 1: Requirement R1 (Features F35 and F36) in src/ai/ensemble_scorer.py:
1. Feature F35: High-Order Non-Linear Signal Combination & Right-Tail Convexity
   - Regime-Adaptive Richards Right-Tail Exponent $\gamma_{\text{tail}}(R) \in [1.00, 1.30]$ and Quadratic Rank Modulation (.60 + 0.50 r + 0.50 r^2$) in Bull regimes, mathematically proven to preserve strict rank monotonicity ($\rho_s = 1.0000$).
   - Quad-Pillar Confluence Kernel $\Xi_{\text{quad}} = \Omega_{\text{quad}} \cdot (\psi_{\text{val}} \psi_{\text{mom}} \psi_{\text{flow}} \psi_{\text{cat}})$ and Tri-Catalyst term with regime-adaptive synergy caps (up to 0.150 in Bull Low Vol, i.e., 1.15x multiplier).
   - Hölder =2.0$ Quadratic Mean Top-$ Boost ({p=2} = \sqrt{\frac{1}{K}\sum S_{(k)}^2}$) and regime-adaptive $\lambda_{\text{boost}} \in [0.20, 0.40]$ preserving peak single-factor signals.
   - Asymmetric Richards Tail Scaling with $\eta_{\text{right}} = 2.0$ and lowered {\text{thresh}} = 0.40$ in Bull Low Vol.
2. Feature F36: Regime Transition Half-Life Dynamic Decay & Downside Noise Filtering
   - Probabilistic Regime Half-Life Expectation $\sum \pi_m \tau_k(R_m)$ compressed by Shannon Transition Entropy Factor $\phi_{\text{entropy}} = \exp(-0.35 H_{\text{norm}}^2)$ and Total Variation Jump Penalty $\phi_{\text{jump}} = \exp(-0.50 \max(0, d_{\text{TV}} - 0.25))$.
   - ^\infty$-Smooth Hyperbolic Tangent Noise Deadband Soft-Thresholding {\text{denoised}} = z \cdot \tanh((|z|/\delta_{\text{noise}})^3)$ with $\delta_0 \in [0.02, 0.07]$, eliminating $>85\%$ of near-0.50 Brownian noise in sideways/turbulent markets while preserving $>98\%$ of strong signals and guaranteeing strict rank monotonicity ($\rho_s = 1.0000$).
3. Testing & Verification:
   - Create 	ests/test_phase5_signal_enhancement.py covering:
     * F35.1: Top-decile return spread expansion $\ge 15\%$ and strict monotonicity ($\rho_s = 1.0000$).
     * F35.2: Quad-Pillar confluence kernel and regime synergy caps (.00 \sim 1.15$).
     * F35.3: Hölder =2.0$ quadratic mean boost vs arithmetic mean.
     * F35.4: Asymmetric Richards tail scaling ($\eta_{\text{right}} = 2.0$).
     * F36.1: Probabilistic regime half-life expectation and entropy compression.
     * F36.2: Hyperbolic tangent smooth noise deadband attenuation ($> 85\%$ noise squashed, $> 98\%$ signal preserved).
     * F36.3: Random stress universe across all 7 regimes verifying 0 NaNs, 0 Infs, $[0.0, 1.0]$ bounds.
   - Run tests using .venv\Scripts\python.exe -m pytest tests/test_phase5_signal_enhancement.py tests/test_phase4_signal_enhancement.py -v.
   - Ensure all tests pass with 100% exit code 0.
