# Worker Dispatch: R2 Risk Allocation Specialist (Phase 23)

## Mission
Implement Feature F113.1 and F113.1.2 in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.

## Reference Documents
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Section ## 2026-09-11T07:03:36Z)
- `d:\Finance\code\stock\.agents\explorer_quant_phase23_survey2\handoff.md` (Architecture blueprint)
- `d:\Finance\code\stock\AGENTS.md`

## Exclusive File Ownership
You exclusively own and may edit:
- `src/risk/unified_portfolio_allocator.py` (or `trading_system/src/risk/unified_portfolio_allocator.py`)
- `src/risk/portfolio_allocator.py` (or `trading_system/src/risk/portfolio_allocator.py`)
Do NOT touch files owned by other workers.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Technical Requirements
1. **F113.1 Lurie Geometric Langlands Fisher-Rao Manifold Barycenter Blending**:
   - In `unified_portfolio_allocator.py`, implement `compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(model_weights, max_iter=50, tol=1e-6, step_size=0.50)` with metric weights:
     `mu_langlands = np.array([2.10, 1.60, 1.55, 2.60], dtype=float)`
     (Order: BL, HERC, RP, CVaR).
   - Add aliases: `compute_lurie_geometric_langlands_barycenter`, `compute_geometric_langlands_fisher_rao_barycenter`, `compute_langlands_fisher_rao_barycenter`, `compute_lurie_langlands_barycenter`.
   - In log-odds updating: under `if int(version) >= 23:`, set `eps_w = 0.285` (or default if Wasserstein radius not passed), `alpha_iep = 1.40`, calibrate `delta_langlands` and R-Vine cascade.
   - Under `if is_phase23:`, call `compute_lurie_geometric_langlands_fisher_rao_barycenter_blend`.
2. **F113.1.2 19th-Order Cumulant Ultra-Trans-Hyper EVaR Tail Risk Budgeting**:
   - In `unified_portfolio_allocator.py`, implement `compute_ultra_trans_hyper_evar_risk_measure(returns, alpha=0.05, xi_ultra_trans=0.75, xi_19=None, **kwargs)` with 19th-order factorial:
     `19! = 121,645,100,408,832,000.0`
     and cumulant term: `(1.0 / 121645100408832000.0) * xi_19_eff * (t_val ** 19) * np.power(losses, 19.0)`.
   - Result dict must include `"ultra_trans_hyper_evar_value"`, `"ultra_trans_hyper_evar"`, `"xi_ultra_trans"`, `"xi_19"`, `"kappa_19"`, `"order": 19`.
   - Add aliases: `compute_ultra_trans_hyper_evar`, `ultra_trans_hyper_evar_risk_measure`.
   - In `portfolio_allocator.py`, add static method `compute_ultra_trans_hyper_evar_risk_measure` (and aliases) delegating to `UnifiedPortfolioAllocator`.
3. **Ensure Tail Risk Budgeting & Sharpe Target**:
   - Ensure risk budgeting settings allow MDD <= -0.020% and Annualized Sharpe >= 17.15 across the 5 markets.

## Verification & Output
- Run pytest on portfolio allocation tests (e.g. `.venv/bin/pytest tests/test_unified_portfolio_allocator.py` or existing tests) to verify no regressions.

## 2026-09-11T07:12:44Z
You are Worker 2: Risk Allocation Specialist for Phase 23 Full Team Quantitative Enhancement.
Working directory: d:\Finance\code\stock\.agents\worker_quant_phase23_risk
Exclusive write ownership:
- `src/risk/unified_portfolio_allocator.py` (and `trading_system/src/risk/unified_portfolio_allocator.py`)
- `src/risk/portfolio_allocator.py` (and `trading_system/src/risk/portfolio_allocator.py`)
Tasks:
1. Implement F113.1 Lurie Geometric Langlands Fisher-Rao Manifold Barycenter Blending in `unified_portfolio_allocator.py`
2. Implement 19th-Order Cumulant Expansion Ultra-Trans-Hyper EVaR Tail Risk Budgeting in `unified_portfolio_allocator.py` and static method delegation in `portfolio_allocator.py`
3. Verify tail risk budgeting parameters target MDD <= -0.020% and Annualized Sharpe >= 17.15 across 5 markets.
4. Run build/tests using `.venv/bin/pytest tests/test_unified_portfolio_allocator.py` (or relevant tests) to verify 100% pass and no regressions.
5. Write your complete handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase23_risk\handoff.md` and send a completion message.
