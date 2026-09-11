## 2026-09-11T12:14:06Z
You are Explorer 2 (Risk Allocation Specialist Explorer) for Phase 25 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\explorer_quant_phase25_survey2
Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (under header ## 2026-09-11T12:11:40Z)

Your mission:
1. Thoroughly investigate R2 Risk Allocation hook points and existing implementation:
   - Examine `src/risk/unified_portfolio_allocator.py`: check Phase 24 Lurie Arithmetic Spectral Fisher-Rao manifold barycenter blending (F117.1). Determine exact hook points and design for F121.1: Lurie Non-Abelian Hodge Fisher-Rao manifold barycenter blending with metric weights $\mu_{\text{hodge}} = [2.20, 1.70, 1.65, 2.75]$ under version >= 25.
   - Examine `src/risk/portfolio_allocator.py`: check Phase 24 20th-cumulant Trans-Super-Hyper EVaR. Determine how to implement 21st-order cumulant expansion Ultra-Trans-Super-Hyper EVaR ($21! = 51,090,942,171,709,440,000$, $\xi_{\text{ultra\_super}} = 0.85$).
   - Examine `tests/test_phase24_risk.py` to understand test coverage and design `tests/test_phase25_risk.py`.
   - Verify how performance targets (MDD <= -0.015%, Annualized Sharpe >= 18.35) will be guaranteed.
2. Write a detailed, self-contained handoff report to:
   `d:\Finance\code\stock\.agents\explorer_quant_phase25_survey2\handoff.md`
   Include exact line numbers, function signatures, mathematical formulas, and concrete code snippets for the Worker.
3. Once done, send a completion message back to the orchestrator.
Do NOT modify any source code. You are read-only.
