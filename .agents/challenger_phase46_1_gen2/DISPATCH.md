# DISPATCH: Challenger 1 gen2 (Alpha & Risk Adversarial Challenger)

## Role & Working Directory
- Subagent Type: `teamwork_preview_challenger`
- Role: Alpha & Risk Adversarial Challenger
- Working Directory: `d:\Finance\code\stock\.agents\challenger_phase46_1_gen2`

## Authoritative Inputs
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Implementation Files to Stress-Test:
  - `trading_system/src/ai/ensemble_scorer.py`
  - `trading_system/src/ai/factor_suppression.py`
  - `trading_system/src/risk/unified_portfolio_allocator.py`
  - `trading_system/src/risk/portfolio_allocator.py`

## Adversarial Verification Tasks
1. **Adversarial Noise Annihilation Stress Test**:
   - Test deadband on floating point boundaries: $z \in \{0.0, 10^{-15}, 0.0001, 0.000299, 0.0003, -0.0003\}$. Verify $|z_{\text{denoised}}| < 10^{-102}$ (strictly $0.0$).
   - Test signal transmission on boundaries: $z \in \{0.150, 0.200, 1.0, 5.0\}$. Verify $|z_{\text{denoised}} - z| / |z| < 10^{-9}$.
   - Stress-test subnormals and extreme values ($z = 10^{300}, z = -10^{300}, z = 10^{-300}$).
2. **Adversarial Rank Modulation Convexity**:
   - Check strict monotonicity for positive and negative convictions.
   - Verify right-tail amplification at $r=1.0$ ($g_{\text{v46}}(1.0) > 300.0$) and lower 70% damping ($g_{\text{v46}}(0.7) < 1.60$).
3. **Adversarial Barycenter & EVaR Verification**:
   - Test Fisher-Rao barycenter convergence on extreme input distributions (degenerate single-model mass, uniform, inverted distributions). Verify output is strictly in $\Delta^3$ (sums to 1.0, all $\ge 0$).
   - Test 42nd cumulant EVaR on heavy-tailed Student-t and Cauchy-like return vectors.
   - Verify analytical monotonicity: $EVaR_{42} \ge EVaR_{41}$ across 100 random return vectors.
4. Author and execute an adversarial test suite (`tests/test_phase46_adversarial_challenger1.py`).
5. Record empirical verdict: **APPROVE** or **REQUEST_CHANGES** in `handoff.md`.

## 2026-09-16T11:00:35Z
You are Challenger 1 gen2 (Alpha & Risk Adversarial Challenger) for Phase 46 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\challenger_phase46_1_gen2
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-16T08:29:02Z)
Read your specific instructions at: d:\Finance\code\stock\.agents\challenger_phase46_1_gen2\DISPATCH.md
Read the orchestrator plan: d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md

Perform adversarial stress testing on Alpha (F203, F204.1, F204.2) and Risk (F205.1):
- Subnormals, extreme inputs ($z \in [-10^{300}, 10^{300}]$), deadband leakage at boundary ($|z| \le 0.0003 \to 0.0$), signal transmission at $|z| \ge 0.150 \to 100.0\%$.
- Monotonicity of rank modulation, right-tail convex amplification ($g(1.0) > 300.0$).
- Fisher-Rao barycenter convergence on degenerate distributions.
- 42nd cumulant EVaR monotonicity ($EVaR_{42} \ge EVaR_{41}$) across random distributions.
Author and execute `tests/test_phase46_adversarial_challenger1.py`.
Write your report and handoff at `d:\Finance\code\stock\.agents\challenger_phase46_1_gen2\handoff.md` with an explicit verdict (**APPROVE** or **REQUEST_CHANGES**). Send a message when done.
