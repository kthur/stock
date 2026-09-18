# DISPATCH: Risk Allocation Specialist Worker (Phase 54)

## Working Directory
d:\Finance\code\stock\.agents\worker_phase54_risk

## Mission
Implement Phase 54 Portfolio Risk Allocation & 50th-Cumulant EVaR Tail Budgeting (Features F243.1, F243.2).

## Exclusive Write Ownership
You EXCLUSIVELY own and may modify:
- `trading_system/src/risk/unified_portfolio_allocator.py` (or `src/risk/unified_portfolio_allocator.py`)
- `trading_system/src/risk/portfolio_allocator.py` (or `src/risk/portfolio_allocator.py`)
You MUST NOT modify any other files.

## Technical Requirements & Specifications
Follow the survey report at: `d:\Finance\code\stock\.agents\explorer_phase54_risk\handoff.md`

### 1. F243.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-4 Fisher-Rao Barycenter Blending
- In `unified_portfolio_allocator.py`:
  - Implement method: `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend(self, model_weights, max_iter=50, tol=1e-6, step_size=0.50)`
  - Curvature vector: $\mu_{\text{lmbwdh4}} = [4.40, 3.20, 3.15, 4.95]$ across `["bl", "herc", "rp", "cvar"]`.
  - Maintain simplex conservation ($\sum q_i = 1.0$) via Riemannian natural gradient mapping.
  - Define all 18 class method aliases on `UnifiedPortfolioAllocator` and module level.
- In `portfolio_allocator.py`:
  - Expose staticmethod `compute_lurie_borcherds_monster_moonshine_whittaker_drinfeld_higher_homology_4_fisher_rao_barycenter_blend` delegating to `UnifiedPortfolioAllocator`, along with all 18 aliases.

### 2. F243.2: 50th-Cumulant Expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure
- In `unified_portfolio_allocator.py`:
  - Implement method: `compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_4_evar_risk_measure(self, returns, alpha=0.05, t_grid=None, xi_monster=0.9999999998, order=50, **kwargs)`
  - Order parameter: $50! \approx 3.04140932 \times 10^{64}$, $\xi_{\text{monster}} = 0.9999999998$.
  - Exact cumulant generating function expansion with 50th-cumulant bounds.
  - Define all 18 method aliases on `UnifiedPortfolioAllocator`.
- In `portfolio_allocator.py`:
  - Expose staticmethod delegating to `UnifiedPortfolioAllocator`, along with all 18 aliases.

### 3. Ambiguity Tilting & Version Gating
- In `UnifiedPortfolioAllocator.compute_information_theoretic_blend_weights` / `calculate_weights`:
  - For `version >= 54`:
    - Entropy scaling: $\epsilon_w = 0.540$
    - Ambiguity shifts: $\delta_{\text{bl}} = -10.25 \cdot \epsilon_w - 5.60 \cdot u^2, \delta_{\text{herc}} = +6.50 \cdot \epsilon_w + 4.50 \cdot u, \delta_{\text{rp}} = -10.75 \cdot \epsilon_w, \delta_{\text{cvar}} = +15.30 \cdot \epsilon_w + 6.30 \cdot c_{\text{crisis}}$
    - Information entropy parity: $\alpha_{\text{iep}} = 3.20$
    - Contagion damping: $\max(0.0, 1.0 - 9.5 \cdot \lambda_{\text{casc}})$
    - Refine weights with Higher-Homology-4 Fisher-Rao barycenter blending.

### 4. Verification & Testing
- Run test suite: `.venv\Scripts\pytest.exe tests/test_phase53_risk.py` to ensure zero regression.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Output your handoff report to: `d:\Finance\code\stock\.agents\worker_phase54_risk\handoff.md`.

## 2026-09-18T02:04:53Z
You are the Risk Allocation Specialist Worker for Phase 54 Quantitative Alpha Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\worker_phase54_risk
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Read your dispatch instructions at: d:\Finance\code\stock\.agents\worker_phase54_risk\DISPATCH.md
Read the technical specification handoff at: d:\Finance\code\stock\.agents\explorer_phase54_risk\handoff.md

EXCLUSIVE WRITE OWNERSHIP:
You EXCLUSIVELY own and may modify:
- `trading_system/src/risk/unified_portfolio_allocator.py` (or `src/risk/unified_portfolio_allocator.py`)
- `trading_system/src/risk/portfolio_allocator.py` (or `src/risk/portfolio_allocator.py`)
You MUST NOT modify any other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Implement Features F243.1 and F243.2:
1. F243.1: Lurie-Borcherds-Monster-Moonshine-Whittaker-Drinfeld Higher-Homology-4 Fisher-Rao Barycenter Blending with curvature mu_lmbwdh4 = [4.40, 3.20, 3.15, 4.95] in unified_portfolio_allocator.py, simplex conservation sum q_i = 1.0, and all 18 aliases on both UnifiedPortfolioAllocator and PortfolioAllocator.
2. F243.2: 50th-cumulant expansion Trans-Singular-Eternal-Omni-Cosmic-Infinite-Supreme-Transcendent EVaR Tail Risk Measure (50! approx 3.04141e64, xi_monster = 0.9999999998) in unified_portfolio_allocator.py and PortfolioAllocator with all 18 aliases.
3. Ambiguity tilting in calculate_weights under version >= 54 with eps_w = 0.540, alpha_iep = 3.20, regime shifts (delta_bl = -10.25, delta_herc = +6.50, delta_rp = -10.75, delta_cvar = +15.30), contagion damping max(0.0, 1.0 - 9.5 * lambda_casc), and higher homology 4 barycenter refinement.

Verify by running:
`.venv\Scripts\pytest.exe tests/test_phase53_risk.py`
Document commands, code changes, and test results in `d:\Finance\code\stock\.agents\worker_phase54_risk\handoff.md`.
Send a completion message when finished.

