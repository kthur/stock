# Explorer M1-3 Dispatch: Strategy Noise Filtering & Correlation SLA Test Design

## 2026-08-14T09:26:45Z
- **User / Orchestrator Request**: Explorer M1-3 (Test & Quality Designer)
- **Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3`
- **Objectives**:
  1. Design comprehensive test suite `tests/test_factor_neutralized_sla.py` asserting:
     - Coverage across 3,379 symbols $\ge 95\%$.
     - For all 5 Fama-French factors (Size, Value, Profitability, Investment, Momentum), Pearson $|\rho| < 0.15$ unconditionally.
     - Robustness under synthetic missing data (up to 80% missing fundamentals) and small-universe subsets.
  2. Review noise filtering in Surge, VCP, Stat-Arb, and Sector Rotation to ensure no regressions and pristine signal precision.
- **Deliverables**:
  - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\analysis.md`
  - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_3\handoff.md`
