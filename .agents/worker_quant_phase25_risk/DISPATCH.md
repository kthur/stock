# DISPATCH — 2026-09-11T12:19:24Z

Worker 2 (Risk Allocation Specialist) for Phase 25 Quant Enhancement.
Working directory: d:\Finance\code\stock\.agents\worker_quant_phase25_risk

Exclusive Files Owned:
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase25_risk.py`

Tasks:
1. In `src/risk/unified_portfolio_allocator.py`:
   - Implement Feature F121.1: Lurie Non-Abelian Hodge Fisher-Rao Manifold Barycenter Blending (`compute_lurie_non_abelian_hodge_fisher_rao_barycenter_blend`) with metric weights $\mu_{\text{hodge}} = [2.20, 1.70, 1.65, 2.75]$ and all aliases (`compute_lurie_non_abelian_hodge_barycenter`, `compute_non_abelian_hodge_fisher_rao_barycenter`, `compute_non_abelian_hodge_barycenter`, `compute_non_abelian_hodge_fisher_rao_barycenter_blend`, `compute_lurie_hodge_barycenter`, `compute_lurie_hodge_barycenter_blend`).
   - Implement Feature F121.1.2: 21st-order cumulant expansion Ultra-Trans-Super-Hyper EVaR ($21! = 51,090,942,171,709,440,000$, $\xi_{\text{ultra\_super}} = 0.85$) in `compute_ultra_trans_super_hyper_evar_risk_measure` (with aliases `compute_ultra_trans_super_hyper_evar`, `ultra_trans_super_hyper_evar_risk_measure`, `compute_ultra_trans_super_hyper_evar_blend`).
   - Wire version >= 25 branching into `compute_information_theoretic_blend_weights` and `calculate_cvar_weights` (both parametric Cornish-Fisher and empirical branches).
2. In `src/risk/portfolio_allocator.py`:
   - Add static method delegations and aliases for all new Phase 25 barycenter and EVaR methods.
3. Implement unit test suite `tests/test_phase25_risk.py` (14 comprehensive tests verifying simplex sum, metric prioritization, exact 21! factorial, strict coherent tail hierarchy, heavy-tail stability, and empirical targets).
4. Execute tests using `.venv/Scripts/python.exe -m pytest tests/test_phase25_risk.py tests/test_phase24_risk.py -v`. Ensure 100% pass and 0 regressions.
5. Write detailed handoff report to `d:\Finance\code\stock\.agents\worker_quant_phase25_risk\handoff.md`.
6. Send completion message back to orchestrator.
