# BRIEFING — 2026-09-04T01:10:00+09:00

## Mission
Recommend the exact fix strategy and code-level design for Milestone 2 Feature 7 (Dynamic Half-Life Convergence Velocity theta*) and Feature 8 (Liquidity-Constrained Cash Buffer) in unified_portfolio_allocator.py.

## 🔒 My Identity
- Archetype: explorer
- Roles: Half-Life Convergence & Cash Buffer Specialist
- Working directory: d:\Finance\code\stock\.agents\explorer_m2_1_opt2
- Original parent: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Milestone: M2 (Milestone 2 - Portfolio Allocation Convergence & Leland Buffer Execution)

## 🔒 Key Constraints
- Read-only investigation — do NOT modify codebase source files
- Deliver findings in `plan_m2_1.md` and `handoff.md` in `.agents/explorer_m2_1_opt2/`
- Target files owned: `trading_system/src/risk/unified_portfolio_allocator.py`
- Verify backward compatibility with existing test suites

## Current Parent
- Conversation ID: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `trading_system/src/risk/unified_portfolio_allocator.py` (lines 350-465, 500-750)
  - `trading_system/src/risk/portfolio_allocator.py` (lines 1100-1400)
  - `trading_system/src/analysis/portfolio_optimizer.py` (`apply_portfolio_constraints`)
  - `trading_system/src/execution/oms_engine.py` (`STRATEGY_ALPHA_HALF_LIVES`, order routing)
  - `trading_system/src/ai/ensemble_scorer.py` (`get_regime_adaptive_half_lives`)
  - `tests/test_institutional_portfolio_construction.py`
  - `tests/test_unified_portfolio_engine.py`
  - `tests/test_challenger_portfolio_stress.py`
  - `tests/test_v8_remediation.py`
- **Key findings**:
  - `optimize_multi_model_blend()` in `unified_portfolio_allocator.py` currently dampens weights using heuristic `exp(-2 * impact)` and clips to 5% ADV, but re-normalizes twice (`s_damp`, `s_bound`), and then calls `apply_portfolio_constraints()` which re-normalizes again (`w /= sum_w`), destroying any liquidity damping and inflating other assets.
  - Closed-form optimal convergence velocity $\theta_i^* \in (0, 1]$ balances alpha decay $\lambda_{\alpha, i} = \ln(2)/\tau_{1/2, i}$ against Gatheral 3/2-power impact $\kappa_i \sigma_i (\Delta W_i / \text{ADV}_i)^{1.5}$.
  - Derivation yields: $\theta_i^* = \min(1.0, \max(0.15, [(\alpha_i + \lambda_{\alpha, i}) / (1.5 \kappa_i \sigma_i)]^2 \cdot (\text{ADV}_i / \Delta W_i)))$.
  - Fast alpha ($\tau \le 2$d) naturally converges at $\theta^* \to 1.0$. Slow alpha ($\tau \ge 25$d) with large participation converges at $\theta^* \in [0.15, 0.40]$, avoiding market impact.
  - To prevent re-normalization inflation, `apply_portfolio_constraints()` must be applied to the target portfolio $w^*$, followed by the convergence step $w_{t+1} = w_t + \theta^* (w^* - w_t)$. The remaining unallocated weight $w_{\text{cash}} = 1.0 - \sum w_{t+1}$ is routed to cash.
- **Unexplored areas**: None for M2-1 scope. Ready for implementation.

## Key Decisions Made
- Feature 7 formula: Closed-form analytical $\theta_i^* = \min(1.0, \max(0.15, [(\alpha_i + \lambda_{\alpha, i}) / (1.5 \kappa_i \sigma_i)]^2 \cdot (\text{ADV}_i / \Delta W_i)))$ with dynamic max liquidity participation cap $\rho_{\max, i} = 0.05 + 0.10 \cdot \exp(-\tau / 3.0)$.
- Feature 8 architecture: Apply portfolio constraints to target portfolio $w^*$ before liquidity convergence, execute partial convergence step $w_{t+1, i} = w_{t, i} + \Delta w_{\text{exec}, i}$, and route residual $w_{\text{cash}} = 1.0 - \sum w_{t+1}$ to cash buffer without post-hoc normalization.
- Metadata capture: Capture `cash_buffer_weight`, `cash_buffer_amount`, and `total_invested_weight` in `df_candidates.attrs`.

## Artifact Index
- `plan_m2_1.md` — Detailed technical implementation plan, code diffs, mathematical derivation, and test suite for Features 7 & 8
- `handoff.md` — 5-component self-contained handoff report
- `progress.md` — Heartbeat and status tracking

