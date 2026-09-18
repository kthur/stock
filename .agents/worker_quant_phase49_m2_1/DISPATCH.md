## 2026-09-17T12:19:14Z

You are the Risk Allocation Specialist Worker for Phase 49 Quantitative Enhancement (Milestone M2).
Your working directory is: d:\Finance\code\stock\.agents\worker_quant_phase49_m2_1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Read the authoritative inputs:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-17T12:06:49Z)
2. d:\Finance\code\stock\.agents\orchestrator_quant_phase49_1\DISPATCH.md
3. d:\Finance\code\stock\.agents\explorer_quant_phase49_1\report.md
4. d:\Finance\code\stock\.agents\explorer_quant_phase49_1\handoff.md
5. tests/test_phase48_risk.py (as blueprint for test_phase49_risk.py)

Files you exclusively own and modify:
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
- `tests/test_phase49_risk.py` (new test suite)

Implementation Tasks:
1. Feature F218.1: Lurie-Borcherds-Monster-Moonshine-Whittaker Motivic Fisher-Rao Barycenter Blending
   - In `unified_portfolio_allocator.py`:
     - Extend or implement `compute_lurie_borcherds_monster_moonshine_whittaker_fisher_rao_barycenter_blend` with metric curvature vector $\mu_{\text{lmbw}} = [3.90, 2.95, 2.90, 4.45]$ across $[\text{BL}, \text{HERC}, \text{RP}, \text{CVaR}]$ on the Riemannian probability simplex.
     - Ensure strict simplex conservation ($\sum q_i = 1.0, q_i > 0$).
     - Export all 15 method aliases on `UnifiedPortfolioAllocator` as detailed in `report.md`.
   - In `portfolio_allocator.py`:
     - Expose static delegates and all 15 aliases delegating to `UnifiedPortfolioAllocator`.
2. 45th-Cumulant Expansion EVaR:
   - In `unified_portfolio_allocator.py`:
     - Implement `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_evar_risk_measure` (or version 49 method with appropriate aliases).
     - Extend cumulant expansion to order 45 with $45! \approx 1.1962222086548019e+56$ and parameter $\xi_{\text{monster}} = 0.99999999$.
     - Ensure monotonicity, convexity, and sharp Chernoff bounds under heavy tails.
   - In `portfolio_allocator.py`:
     - Expose static delegates and aliases.
3. Ambiguity Tilting:
   - In `unified_portfolio_allocator.py` (`compute_information_theoretic_blend_weights` and `calculate_weights`):
     - Under `is_phase49` or `version >= 49`, apply ambiguity tilting with $\alpha_{\text{iep}} = 2.95$ and $\epsilon_W = 0.500$.
4. Test Suite `tests/test_phase49_risk.py`:
   - Build comprehensive unit tests covering:
     - Fisher-Rao barycenter weight bounds, positive-definiteness, simplex sum = 1.0.
     - All 15 barycenter method aliases across both `UnifiedPortfolioAllocator` and `PortfolioAllocator`.
     - 45th-cumulant EVaR bounds, scaling, and monotonicity.
     - Ambiguity tilting weights under version >= 49.
   - Verify tests with `.venv\Scripts\pytest.exe tests/test_phase49_risk.py` and regression test `.venv\Scripts\pytest.exe tests/test_phase48_risk.py`.
