# BRIEFING — 2026-09-04T00:43:00+09:00

## Mission
Recommend the exact fix strategy and code-level design for Milestone 1 Feature 3, Feature 4, Feature 5 (Tail Convexity, Bilinear Synergy Kernel, 2D Regime Half-Life Scaling in ensemble_scorer.py).

## 🔒 My Identity
- Archetype: explorer
- Roles: Tail Convexity & Synergy Kernel Specialist
- Working directory: d:\Finance\code\stock\.agents\explorer_m1_3_opt2
- Original parent: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Milestone: Milestone 1

## 🔒 Key Constraints
- Read-only investigation — do NOT modify source code directly
- Focus strictly on Milestone 1 Features 3, 4, 5 in `ensemble_scorer.py`
- Formulate exact diffs/guidelines and verification methods for the Worker
- Preserve backward compatibility with existing tests

## Current Parent
- Conversation ID: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Updated: 2026-09-04T00:48:00+09:00

## Investigation State
- **Explored paths**:
  - `trading_system/src/ai/ensemble_scorer.py`: lines 1210–1290, 1630–1750, 2440–2850, 3280–3514.
  - `tests/test_return_maximization_apex.py`: lines 95–130.
  - `tests/test_score_normalizer.py`: lines 190–223.
  - `tests/test_world_class_quant_enhancements.py`: lines 1–150.
  - `tests/test_adversarial_m1_challenger.py`: lines 70–140.
  - `tests/test_unified_portfolio_engine.py`: lines 460–485.
  - `tests/test_apex_tier_quant_enhancements.py`: lines 105–135.
- **Key findings**:
  1. `apply_bessembinder_convex_power_law` is implemented at line 3484 with right-tail scaling only and is dormant (never invoked in `combine_predictions()`). Upgrading to symmetric Richards S-curve with `symmetric=False` default preserves 100% test compatibility while enabling two-sided decile spread widening.
  2. Multi-pillar confluence in `combine_predictions()` (Phase 2-B) has binary step cuts at $s \ge 0.60$ and duplicate strategy allocations (`dual_correction`, `cross_asset_spillover`, `index_rebalance`). Replacing it with a continuous bilinear synergy kernel over 4 disjoint clusters eliminates churn and false confluence.
  3. `STRATEGY_HALF_LIVES` is static ($0.5$d–$60.0$d) regardless of regime. Scaling $\tau_k(R) = \tau_k^{(0)} \kappa_{\text{regime}}(R) \kappa_{\text{tier}}(k, R)$ provides regime adaptation while maintaining backward compatibility for existing callers.
- **Unexplored areas**:
  - Milestone 2 features (Features 7–11: Dynamic half-life convergence $\theta_i^*$, Leland buffers, OMS delta rebalancing) — owned by M2 explorer/worker.

## Key Decisions Made
- `apply_bessembinder_convex_power_law`: Keep signature compatible by adding `symmetric: bool = False` as default; execute symmetric Richards/Bessembinder power law when `symmetric=True`. Wire into `combine_predictions()` in Phase 2-E.
- Continuous bilinear synergy: Form 4 mutually exclusive clusters with zero strategy overlap; use smooth softplus conviction $\psi_p(\bar{s}) \in [0, 1]$ and 2D regime coupling matrix $\Omega(R)$ bounded at $[1.0, 1.10]$.
- Regime half-lives: Implement classmethod `get_regime_adaptive_half_lives(regime)` and add optional `regime` argument to `apply_exponential_decay_filter` and `apply_rank_ic_decay_calibration`.

## Artifact Index
- `plan_m1_3.md` — Detailed technical design, mathematical formulas, exact code diffs and test plans
- `handoff.md` — 5-component self-contained handoff report
- `progress.md` — Liveness heartbeat and step tracking

