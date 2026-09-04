## 2026-09-04T08:38:36Z
You are Explorer 2 for Phase 5 Deep Quantitative Enhancements.
Your working directory is: `d:\Finance\code\stock\.agents\explorer_survey_2`

MANDATORY FIRST STEP:
Read the following authoritative files:
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically header `## 2026-09-04T08:36:42Z`)
2. `d:\Finance\code\stock\PROJECT.md`
3. `d:\Finance\code\stock\.agents\handoff.md`

Your Mission:
Investigate and formulate the technical specification for Requirement R2:
Portfolio Optimal Allocation & Execution Slippage / Friction Cost Minimization 5th Deepening (Features F37, F38).

Specific Areas to Investigate:
1. Examine `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`:
   - Inspect 4-Model blending: Black-Litterman, HERC, Risk Parity, EVT-CVaR.
   - Inspect downside semi-covariance Sortino CVaR, cross-sectional alpha dispersion conviction weighting, and capital allocation efficiency.
   - How can Phase 5 further optimize risk-adjusted returns and capital allocation efficiency (e.g. tail risk budgeting refinement, higher-order co-skewness / co-kurtosis penalty, dynamic risk parity diversification ratio, adaptive target volatility scaling under regime uncertainty)?
2. Examine `src/execution/smart_order_router.py`, `src/execution/oms_engine.py`, `src/execution/slippage_feedback.py`:
   - Inspect `calculate_peg_limit_price()`, volume-weighted micro-price, multi-tier L2 OBI (Order Book Imbalance), Hawkes process arrival intensity adverse selection gating, and fee-aware Leland dynamic buffer bands (KRX 25 bps vs US 8 bps).
   - How can Phase 5 refine SOR routing logic, darkpool midpoint resting, and order slicing to achieve further slippage reduction and friction savings?
3. Check existing tests:
   - Run or inspect `tests/test_phase4_portfolio_execution.py` and related tests to understand existing test assertions and thresholds.

Deliverable:
Write a comprehensive report to:
`d:\Finance\code\stock\.agents\explorer_survey_2\analysis.md`
and a summary in `d:\Finance\code\stock\.agents\explorer_survey_2\handoff.md`.
Include exact file paths, line numbers, mathematical formulations, concrete parameter proposals for Phase 5 (F37, F38), and test design recommendations.
Then notify me via `send_message`.
