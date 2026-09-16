# DISPATCH: Milestone 2 — Risk Allocation Specialist (Worker 2)

## Role & Working Directory
- Subagent Type: `teamwork_preview_worker`
- Role: Risk Allocation Specialist
- Working Directory: `d:\Finance\code\stock\.agents\worker_phase46_risk`

## Authoritative Inputs
- Original Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: ## 2026-09-16T08:29:02Z)
- Orchestrator Plan: `d:\Finance\code\stock\.agents\orchestrator_quant_phase46_1\plan.md`
- Explorer 2 Technical Survey: `d:\Finance\code\stock\.agents\explorer_phase46_risk_oms\report.md`
- Explorer 2 Handoff: `d:\Finance\code\stock\.agents\explorer_phase46_risk_oms\handoff.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership (Exclusively Owned Files)
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase46_risk.py`

## Implementation Tasks (Milestone 2)

### 1. F205.1: Lurie-Borcherds-Whittaker Motivic Fisher-Rao Barycenter
- In `trading_system/src/risk/unified_portfolio_allocator.py`:
  - Implement `compute_lurie_borcherds_whittaker_fisher_rao_barycenter_blend(self, model_weights, max_iter=50, tol=1e-6, step_size=0.50)`:
    Metric weights $\mu_{\text{lbw}} = [3.60, 2.75, 2.70, 4.15]$ for models `["bl", "herc", "rp", "cvar"]`.
  - Register all 15 method aliases on `UnifiedPortfolioAllocator`.
  - Integrate version branching for `version >= 46`:
    Ambiguity tilting vector $\delta_{\text{borch\_whit}}$ with $\epsilon_w = 0.480$, $\alpha_{\text{iep}} = 2.70$, and amplified downside crisis dampening.
    Exit barycenter refinement under `version >= 46`.
- In `trading_system/src/risk/portfolio_allocator.py`:
  - Add staticmethod delegation and full 15-alias suite mapping to `UnifiedPortfolioAllocator`.

### 2. F205.1: 42nd-Order Cumulant Trans-Singular-Borcherds-Whittaker EVaR
- In `trading_system/src/risk/unified_portfolio_allocator.py`:
  - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_risk_measure`:
    Expand cumulant generating function to 42nd order:
    $42! = 1405006117752879898543142606244511569936384000000000.0$ and $\xi_{\text{borch}} = 0.9999999$.
    Enforce strict analytical lower bound: $\max(\text{best\_ts}, \text{trans\_km\_val})$ ensuring $EVaR_{42} \ge EVaR_{41}$.
  - Register all 26 aliases on `UnifiedPortfolioAllocator`.
- In `trading_system/src/risk/portfolio_allocator.py`:
  - Add staticmethod delegation and full 26-alias suite mapping to `UnifiedPortfolioAllocator`.

### 3. Unit Test Suite & Verification
- Author comprehensive unit tests in `tests/test_phase46_risk.py` covering:
  - F205.1 Fisher-Rao barycenter convergence, weights sum to 1.0, metric weighting response.
  - F205.1 42nd cumulant EVaR calculation, factorial precision, monotonicity $EVaR_{42} \ge EVaR_{41}$.
  - Version branching and ambiguity tilting vector under `version >= 46`.
  - All aliases functional on both `UnifiedPortfolioAllocator` and `PortfolioAllocator`.
  - Backward compatibility with Phase 1~45.
- Run tests:
  ```powershell
  python -m pytest tests/test_phase46_risk.py tests/test_phase45_risk.py -v
  ```
  Ensure 100% pass rate.

## Deliverables
- Code changes in `unified_portfolio_allocator.py` and `portfolio_allocator.py`.
- New unit test file `tests/test_phase46_risk.py`.
- Handoff report at `d:\Finance\code\stock\.agents\worker_phase46_risk\handoff.md`.

## 2026-09-16T08:38:42Z
You are Worker 2 (Risk Allocation Specialist) for Phase 46 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase46_risk
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-16T08:29:02Z)
Read your specific instructions at: d:\Finance\code\stock\.agents\worker_phase46_risk\DISPATCH.md
Read the technical report: d:\Finance\code\stock\.agents\explorer_phase46_risk_oms\report.md

MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You exclusively own:
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase46_risk.py`

Implement F205.1 (Fisher-Rao barycenter & 42nd-order cumulant EVaR), author unit tests in `tests/test_phase46_risk.py`, run tests to verify 100% pass rate, and produce a self-contained handoff at `d:\Finance\code\stock\.agents\worker_phase46_risk\handoff.md`. Send a completion message when done.

