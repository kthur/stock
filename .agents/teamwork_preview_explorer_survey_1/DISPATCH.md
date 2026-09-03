## 2026-08-31T14:49:35Z
Mission: Survey and investigate requirement R1: GitHub Actions Data Seeding & Model Training End-to-End Pipeline Integrity.
1. Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md and AGENTS.md.
2. Investigate all GitHub Actions workflow files: .github/workflows/pipeline.yml, preseed.yml, training.yml, etc.
3. Investigate the data seeding and fetching scripts: trading_system/scripts/preseed_data.py, fetch_global_indicators.py, train_models.py, run_pipeline.py, and caching mechanisms.
4. Verify how the 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ) are handled in workflows, data seeding, indicator storage, caching, and model training (Regression, Surge, VCP ML, LSTM).
5. Identify any discrepancies, missing steps, caching bugs, path mismatches, or execution failure points.
6. Write a comprehensive survey report to d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\survey_report.md and a handoff.md in your working directory.
7. Send a message to your caller parent with your findings summary and file paths.

## 2026-09-03T11:56:34Z
You are an Explorer agent (teamwork_preview_explorer) surveying the codebase for Milestone 1 / Requirement 1 (R1).
Your identity: Explorer Survey 1 (Alpha Signal & Strategy Engine Expert)
Your working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1
Parent conversation ID: 9f89ea60-abb5-4468-88df-62eb0473f19b

MANDATORY FIRST STEP:
Read d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md and d:\Finance\code\stock\system_improvement_plan_v8.md.

TASK:
Investigate and produce a detailed, actionable blueprint for R1: 37대 전략 신호 품질 및 예측력(Alpha) 극대화:
1. Multi-Horizon (1d, 3d, 5d, 20d, 60d, 120d, 200d) alpha half-life calculation, decay weights, and horizon scaling in `src/ai/ensemble_scorer.py`, `src/ai/prediction_model.py`.
2. Cross-Sectional Normalization in `src/ai/score_normalizer.py`: Winsorized Gaussian CDF [0.05, 0.95], sector-neutral ranking, handling inactive 0-score blocks (MED-09: N < 10 threshold).
3. 2D Regime adaptive weights matrix, Löwdin orthogonalization, consensus alpha preservation (CRIT-11), and missing strategy drop-out / zero-weighting (CRIT-09, HIGH-09, HIGH-10).
4. Critical & High strategy defects from system_improvement_plan_v8.md:
   - CRIT-03: `src/ai/lstm_predictor.py` causal rolling normalization lookahead fix
   - CRIT-04: `src/core/rim_valuation.py` Ohlson ROE decay loop update
   - CRIT-10: `src/ai/ml_strategy_adapters.py` Darkpool adapter instantiation fix
   - CRIT-12: `src/core/card_factor.py` VIX sensitivity sign inversion
   - HIGH-02: `src/core/supply_chain.py` timezone ffill fix
   - HIGH-08: `src/ai/factor_suppression.py` CLUSTER_MAP missing strategies 35, 36, 37
   - HIGH-11: `src/ai/ensemble_scorer.py` US ticker dot regex for STT fee
   - HIGH-12: `src/core/short_interest_squeeze.py` missing data NaN handling
   - MED-04: `src/core/arm_factor.py` missing score NaN return
   - MED-05: `src/core/short_term_reversal.py` 80-bar warm-up
   - MED-06: `src/core/stat_arb.py` universe 0.50 rank combination
   - MED-08: `hft_engine.py` and `dual_correction.py` StrategyRegistry metadata
5. For each item, provide: exact file path, line numbers, current behavior vs required behavior, and exact code modification guidance.

OUTPUT:
Write your comprehensive investigation report to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\handoff.md`.
Update `d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_1\progress.md` with timestamps.
Send a message back to parent when complete.
