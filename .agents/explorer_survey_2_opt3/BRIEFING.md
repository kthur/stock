# BRIEFING — 2026-09-04T05:54:00Z

## Mission
Investigate portfolio allocation 4-model blending and execution OMS optimization for Milestone 2 of 3rd Deep Quantitative Enhancement.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, synthesis, architecture
- Working directory: d:\Finance\code\stock\.agents\explorer_survey_2_opt3
- Original parent: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Milestone: Milestone 2 (R2 - Portfolio 4-Model Dynamic Blending & Darkpool/HFT OMS Optimization)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Adhere strictly to 5-Component Handoff Report format
- Write to own folder only (.agents/explorer_survey_2_opt3/)
- Must cite exact file paths, line numbers, and formulas

## Current Parent
- Conversation ID: b46202ea-01da-4d8b-b60e-9285cbf907d4
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`
  - `trading_system/src/risk/portfolio_allocator.py`
  - `trading_system/src/execution/oms_engine.py`
  - `trading_system/src/execution/smart_order_router.py`
  - `trading_system/src/execution/sor_router.py`
  - `trading_system/src/execution/adaptive_router.py`
  - `trading_system/src/core/hft_engine.py`
  - `trading_system/src/data_layer/darkpool_tracker.py`
  - `trading_system/src/execution/slippage_feedback.py`
  - `tests/test_m2_portfolio_execution.py`, `tests/test_portfolio_allocator.py`, `tests/test_portfolio_optimizer_and_oms.py`, `tests/test_smart_router.py`, `tests/test_adaptive_router.py`
- **Key findings**:
  - `unified_portfolio_allocator.py` uses discrete static regime dictionary for 4-model blending (BL, HERC, RP, CVaR), causing step-jump turnover on regime switches; needs continuous Markov/2D transition probability interpolation with 5-day EMA smoothing.
  - `calculate_cvar_weights` in `unified_portfolio_allocator.py` only runs empirical linear CVaR over 60-day returns (only 3 observations exceed 95% VaR), diverging from `portfolio_allocator.py` which contains rigorous EVT-GPD POT fitting and Clayton copula tail-stressed covariance $\Sigma_{stressed}$.
  - Gatheral 3/2-power market impact uses static $\kappa=1.0$; should be scaled by dynamic dark pool probing ratio $\kappa_{eff} = \kappa_0(1 - 0.75 \delta_{dark})$.
  - `oms_engine.py` order planning does not attach 3-tier SOR execution legs (`DARK_ATS_MIDPOINT`, `PRIMARY_EXCHANGE_MAKER`, `LIT_EXCHANGE_SWEEPER`) or compute net expected savings in bps.
  - Strategy #30 dark pool signals (`darkpool_score`, `dark_pool_ratio`, `is_accumulation`) are not currently utilized to scale dark pool probing ratios, nor is OBI utilized in Almgren-Chriss midpoint peg pricing.
  - Existing test suite (100% passing) covers baseline functionality; new enhancements will extend coverage without breaking backward compatibility.
- **Unexplored areas**: Investigation completed across all required modules.

## Key Decisions Made
- Formulated continuous Markov/2D regime probability 4-model dynamic blending with EMA smoothing.
- Formulated EVT-GPD tail risk and Clayton copula tail covariance integration into `UnifiedPortfolioAllocator`.
- Formulated dynamic dark pool probing ratio $\delta_{dark} \in [0.10, 0.75]$ and OBI-driven midpoint peg limit pricing for OMS execution.
- Formulated dark-pool-adjusted Gatheral market impact $\kappa_{eff}$.

## Artifact Index
- d:\Finance\code\stock\.agents\explorer_survey_2_opt3\DISPATCH.md — Received task instructions
- d:\Finance\code\stock\.agents\explorer_survey_2_opt3\progress.md — Liveness and task progress
- d:\Finance\code\stock\.agents\explorer_survey_2_opt3\handoff.md — Final comprehensive investigation report
