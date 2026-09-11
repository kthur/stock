# DISPATCH — worker_m2 (Risk Allocation Specialist - Milestone M2)

## Mandatory Reading
You MUST read `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically section ## 2026-09-10T01:13:45Z) and `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\PROJECT.md` before starting work.
Also read the detailed survey findings in `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\explorer_survey_2\survey_report.md`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership & Exclusivity
You have EXCLUSIVE write ownership of:
- `trading_system/src/risk/unified_portfolio_allocator.py`
- `trading_system/src/risk/portfolio_allocator.py`
You MUST NOT edit any AI ensemble, OMS, execution, or benchmark files.

## Technical Specifications & Requirements
1. **Feature F105.1: Lurie Chromatic Homotopy Theory Fisher-Rao Manifold Barycenter Blending**:
   - Implement `compute_lurie_chromatic_homotopy_fisher_rao_barycenter_blend(model_weights, max_iter=50, tol=1e-6, step_size=0.50) -> Dict[str, float]` in `UnifiedPortfolioAllocator` (version >= 21).
   - Aliases: `compute_chromatic_homotopy_fisher_rao_barycenter_blend`, `compute_lurie_chromatic_barycenter_blend`.
   - Chromatic metric weights: $\mu_{\text{chromatic}} = [1.90, 1.50, 1.45, 2.30]$ for the 4 models (BL, HERC, RP, CVaR).
   - Version >= 21 branching in `allocate()` or `blend_weights()`.
   - Ambiguity tilting parameter $\epsilon_w = 0.255$, entropy parity $\alpha_{\text{iep}} = 1.30$.
2. **Feature F105.1.2: 17th-Order Cumulant Expansion Hyper-Transcendent EVaR**:
   - Implement `compute_hyper_transcendent_evar_risk_measure(returns, alpha=0.05, ...) -> Dict[str, Any]` in `UnifiedPortfolioAllocator`.
   - Aliases: `compute_hyper_transcendent_evar`, `hyper_transcendent_evar_risk_measure`.
   - 17th-cumulant expansion: $17! = 355,687,428,096,000$, $\xi_{17} = 0.65$, odd power $|L|^{17}$ for positive loss penalty.
   - Return dictionary keys: `hyper_transcendent_evar_value` (and alias `hyper_transcendent_evar`), `kappa_17`, `order=17`.
   - In `PortfolioAllocator`: expose static methods and aliases matching `UnifiedPortfolioAllocator`.
   - Target metrics: MDD $\le -0.028\%$, Sharpe $\ge 15.92$.
3. **Testing & Verification**:
   - Run tests using `.venv\Scripts\python.exe -m pytest tests/test_portfolio_optimizer_and_oms.py` (or existing risk tests) to verify 100% pass and no regression.

## Deliverables
- Genuine implementation of M2 in `src/risk/unified_portfolio_allocator.py` and `src/risk/portfolio_allocator.py`.
- Write `handoff.md` with:
  * Files modified and line numbers
  * Test execution commands and passing output
  * Verification of all interface contracts and mathematical formulas
