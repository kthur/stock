# BRIEFING — 2026-07-31T00:33:30Z

## Mission
Investigate `src/risk/portfolio_optimizer.py` and `src/risk/risk_manager.py` to design Extreme Value Theory (EVT) CVaR loss budget constraints using Generalized Pareto Distribution (GPD) fitting.

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: Explorer M3-1 (Gen 2) - Read-only investigator & risk budget constraint designer
- Working directory: d:\Finance\code\stock\.agents\explorer_m3_1_gen2
- Original parent: a6e25fff-c97b-4a66-ab43-ac371c3c1047
- Milestone: Milestone 3 (EVT-CVaR Risk Budget Constraints)

## 🔒 Key Constraints
- Read-only investigation — do NOT modify codebase directly (only write report files in `.agents/explorer_m3_1_gen2`)
- High mathematical rigor for GPD POT fitting, EVT-VaR, EVT-CVaR, and portfolio optimization integration
- Must specify exact equations, scipy.optimize / cvxpy implementation snippets, and edge case fallbacks (e.g., Gaussian/Empirical fallback when tail samples < threshold)

## Current Parent
- Conversation ID: a6e25fff-c97b-4a66-ab43-ac371c3c1047
- Updated: 2026-07-31T00:33:30Z

## Investigation State
- **Explored paths**:
  - `PROJECT.md`
  - `src/risk/portfolio_optimizer.py`
  - `trading_system/src/risk/portfolio_optimizer.py`
  - `trading_system/src/risk/risk_manager.py`
  - `trading_system/src/risk/portfolio_risk.py`
  - Python prototype verification (`scipy.stats.genpareto.fit`, POT threshold, EVT-VaR, EVT-CVaR, SLSQP optimization with EVT-CVaR loss budget constraint)
- **Key findings**:
  - Existing `RiskManager.calculate_cvar` relies on empirical percentiles, which suffer from high variance in extreme tails (99%, 99.5%) when sample size is modest.
  - EVT Peaks-Over-Threshold (POT) with Generalized Pareto Distribution (GPD) provides smooth, accurate tail risk estimation.
  - `PortfolioOptimizer` can enforce $\text{EVT\_CVaR}_\alpha(w) \le \text{max\_cvar\_limit}$ in SLSQP, successfully shifting weight away from high tail-risk assets to keep expected tail loss within budget (verified numerically).
  - Robust 3-tier fallback chain (EVT-GPD $\to$ Cornish-Fisher $\to$ Empirical/Gaussian) handles small sample sizes ($N_u < 15$), invalid shape parameters ($\xi \ge 0.95$), and non-convergence.
- **Unexplored areas**: None. All tasks fully analyzed and verified.

## Key Decisions Made
- Formulated complete mathematical framework for EVT-VaR, EVT-CVaR, and SLSQP non-linear constraint integration.
- Designed edge case fallback hierarchy and band-based dynamic rebalancing logic.

## Artifact Index
- `ORIGINAL_REQUEST.md` — Original request transcript
- `BRIEFING.md` — Agent briefing & state tracker
- `progress.md` — Liveness & task execution status log
- `handoff.md` — Final structured handoff report
