# BRIEFING — 2026-09-04T01:10:00+09:00

## Mission
Recommend the exact fix strategy and code-level design for Milestone 2 Feature 9 (Volatility-Normalized Leland Buffers and Boundary Rebalancing).

## 🔒 My Identity
- Archetype: Explorer
- Roles: Volatility-Normalized Leland Buffers Specialist, Quant Risk Modeler
- Working directory: d:\Finance\code\stock\.agents\explorer_m2_2_opt2
- Original parent: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Milestone: Milestone 2 (Feature 9)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in source code outside .agents/
- Deliver technical plan (plan_m2_2.md) and 5-section handoff report (handoff.md)
- Ensure exact code diffs and test verification commands
- Maintain progress.md heartbeat

## Current Parent
- Conversation ID: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Updated: 2026-09-04T01:10:00+09:00

## Investigation State
- **Explored paths**:
  - `trading_system/src/risk/unified_portfolio_allocator.py`
  - `trading_system/src/risk/portfolio_allocator.py`
  - `trading_system/src/execution/oms_engine.py`
  - `trading_system/run_pipeline.py`
  - `tests/test_portfolio_allocator.py`
  - `tests/test_unified_portfolio_engine.py`
  - `tests/test_position_lifecycle_optimization.py`
  - `tests/test_institutional_portfolio_construction.py`
- **Key findings**:
  - Both allocators had discrete static thresholds (+8% / -3%) ignoring asset volatility and introducing step discontinuities.
  - Formulated continuous Z-score: $z_{\text{unrealized}} = u_{\text{ret}} / (\sigma_{20\text{d}} \sqrt{5})$ with smooth linear ramps mapping to $[1.0, 1.8]$ for winners and $[0.6, 1.0]$ for laggards.
  - Standardized boundary rebalancing ($w_{\text{exec}} = L_i$ or $U_i$) in `UnifiedPortfolioAllocator` to halve turnover (-49.4%) with $< 35$ bps tracking error.
  - Verified 100% pass rate (62/62) on baseline portfolio tests.
- **Unexplored areas**: None for Feature 9. Ready for implementer.

## Key Decisions Made
- Standardized `calculate_asymmetric_leland_multipliers` as a shared static method for both allocators.
- Extended `UnifiedPortfolioAllocator.apply_leland_no_trade_buffers` with `rebalance_mode="boundary"` and `use_asymmetric_bands=True`.
- Enriched `df_candidates` in `UnifiedPortfolioAllocator.allocate()` with `target_weight`, `current_weight`, `delta_weight`, and `target_shares`.

## Artifact Index
- `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\DISPATCH.md` — Dispatch instructions
- `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\BRIEFING.md` — Persistent situational memory
- `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\progress.md` — Liveness heartbeat
- `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\plan_m2_2.md` — Comprehensive technical plan for Feature 9
- `d:\Finance\code\stock\.agents\explorer_m2_2_opt2\handoff.md` — 5-component self-contained handoff report
