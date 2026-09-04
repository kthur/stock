## 2026-09-03T11:56:34Z
MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md and d:\Finance\code\stock\system_improvement_plan_v8.md.

TASK:
Investigate and produce a detailed, actionable blueprint for R2: 포트폴리오 최적 배분 및 회전율·거래비용 차감 순수익률 최적화:
1. CRIT-01: Multi-currency FX translation in src/risk/unified_portfolio_allocator.py:494 (llocate method) and 	rading_system/run_pipeline.py:4044. Ensure US shares calculation converts KRW allocation amount to USD using usd_krw exchange rate (preventing 1,350x share explosion).
2. CRIT-02: Black-Litterman 20-day return horizon vs daily covariance scaling mismatch in src/analysis/portfolio_optimizer.py:143-265 and unified_portfolio_allocator.py:211.
3. CRIT-06: Small universe ( \le 4$) CVaR upper bound constraint infeasibility in unified_portfolio_allocator.py:136.
4. CRIT-07: Hardcoded KRW 50,000 threshold in 	urnover_optimizer.py:75 and portfolio_allocator.py:1297 breaking USD accounts.
5. HIGH-15: Cornish-Fisher VaR fallback in portfolio_allocator.py:680 -> proper Expected Shortfall integration.
6. HIGH-16: Gatheral 3/2-power market impact formulation in unified_portfolio_allocator.py:259 and ensemble_scorer.py:2801.
7. MED-12: HERC hardcoded weight caps in portfolio_optimizer.py:630 -> dynamic upper bound delegation.
8. Asymmetric Leland No-Trade Buffer Bands: How to calibrate entry and exit buffer bands based on volatility and transaction friction to minimize unnecessary turnover and maximize Net Expected Return.
9. For each item, provide: exact file path, line numbers, current behavior vs required behavior, and exact code modification guidance.

OUTPUT:
Write your comprehensive investigation report to d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\handoff.md.
Update d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\progress.md with timestamps.
Send a message back to parent when complete.
## 2026-09-04T00:33:52Z
You are Explorer 2: Signal Quality & Top-Decile Alpha Spread Explorer.
Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2
Maintain progress.md in your working directory.

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md completely, especially the latest request under `## 2026-09-04T00:32:34Z` regarding R1: 37-strategy dynamic signal quality and top-decile alpha spread enhancement.

Your assignment:
1. Thoroughly investigate `src/ai/ensemble_scorer.py`, `src/ai/score_normalizer.py`, `src/ai/factor_orthogonalizer.py`, `src/ai/factor_suppression.py`, and `src/ai/prediction_model.py`.
2. Inspect how signals from the 37 strategies are combined, normalized, orthogonalized, regime-weighted, and filtered:
   - Non-linear interactions & factor coupling
   - Cross-sectional ranking preservation (Percentile Rank, Winsorized Gaussian CDF, Top-Decile Alpha Spread)
   - 2D Regime adaptive weighting (BULL, BEAR, SIDEWAYS x LOW/HIGH VOL, CRISIS) and Markov transition smoothing
   - Dynamic half-life delay filtering and noise suppression
3. Check existing unit and integration tests in `tests/` related to ensemble scoring and signal normalization (e.g., `tests/test_ensemble_scorer.py`, `tests/test_score_normalizer.py`, etc.). Note any edge cases or strict assertions that must be preserved.
4. Formulate concrete, actionable implementation recommendations for Phase 4:
   - Exactly what formulas, parameters, and algorithms to refine
   - Specific file locations and function signatures to enhance
   - How to maximize Top-Decile Alpha Spread and suppress noise/sideways loss without breaking backward compatibility or any existing test.
5. Write a comprehensive, self-contained handoff report at:
   `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_2\handoff.md`
and notify the caller via send_message when complete.
