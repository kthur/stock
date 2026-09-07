## 2026-09-05T13:48:47Z

You are an Explorer subagent for Portfolio Risk Budgeting and Adaptive Allocation.
Working directory: d:\Finance\code\stock\.agents\explorer_survey_2
Original request file: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (read the latest request under ## 2026-09-05T13:47:02Z).
Project rules: d:\Finance\code\stock\AGENTS.md.

Your Mission:
Investigate the existing codebase regarding R2:
- Portfolio risk budgeting and adaptive optimal asset allocation
- 4-model allocation (Black-Litterman, HERC, Risk Parity, EVT-CVaR) blending
- Information-geometric barycenter blending across the 4 models
- High-order cumulant expansion based super-coherent tail risk (EVaR / Entropic Value-at-Risk) budgeting
- Target files to examine: src/risk/unified_portfolio_allocator.py, src/risk/portfolio_allocator.py, src/analysis/portfolio_optimizer.py, src/risk/risk_manager.py.
- Check current blending methods, covariance shrinkage, risk parity, CVaR/EVaR formulation, Leland buffer bands, and MDD control mechanisms.
- Determine exact current implementations, mathematical formulations used in previous phases, and what changes are needed to achieve Sharpe Ratio >= 12.0, MDD <= -0.18%, Net Expected Return >= 95.0%.
- Write your detailed report to d:\Finance\code\stock\.agents\explorer_survey_2\survey_report.md and complete with handoff.md. Include specific file paths, line numbers, and proposed mathematical formulas.

## 2026-09-06T15:04:00Z

You are an Explorer subagent (identity: explorer_survey_2).
Working directory: d:\Finance\code\stock\.agents\explorer_survey_2
Original Request Path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Please read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (specifically section ## 2026-09-06T15:02:05Z).

Your mission:
Investigate the codebase for Phase 19 Quant Enhancement R3 (Microstructure & OMS).
Specifically examine:
1. `src/core/fast_lob_engine.py`:
   - How are L3 orderbook hydrodynamics models implemented (look for Kerr spacetime ergosphere or Kerr-Newman charged rotating spacetime hydrodynamics in Phase 17/18)?
   - What are the class names, methods, parameters, and how are queue priorities or execution intensities computed?
2. `src/execution/smart_order_router.py`:
   - How is maker floor configured and applied? Look for previous values (e.g., 0.0001 in Phase 17, 0.00005 in Phase 18).
3. `src/execution/oms_engine.py`:
   - How is tick shading implemented? Look for formula `-0.98 * spread * (h - 0.12)` or `-0.99 * spread * (h - 0.10)`.
   - How is dark pool routing implemented? Look for 99.8%, 99.9% ATS routing logic.
   - How is Anti-Gaming MinQty implemented? Look for 99.9%, 99.95% anti-gaming logic.

Requirements for your output:
Write your complete technical exploration report to `d:\Finance\code\stock\.agents\explorer_survey_2\handoff.md`. Include exact line numbers, function signatures, and recommendations for implementing:
- F97.2 Reissner-Nordström extremal black hole spacetime L3 orderbook hydrodynamics
- Maker floor 0.00002 in SmartOrderRouter
- Tick shading `-0.995 * spread * (h - 0.08)` in OMSEngine
- Dark pool routing 99.95% ATS in OMSEngine
- Anti-Gaming MinQty 99.98% in OMSEngine
Then send a message to parent with a concise summary.

