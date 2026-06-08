# BRIEFING — 2026-06-07T20:23:00Z

## Mission
Implement the Global Macro correlation engine, ML predictor, global outperformer screener, and Dash UI integration in d:\Finance\code\stock\trading_system.

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_1
- Original parent: 02ac8878-50e3-4b3d-9049-7f8278bd7a9c
- Milestone: Global Macro Enhancements (R1-R4)

## 🔒 Key Constraints
- CODE_ONLY network mode: No external HTTP calls, curl, wget, or similar.
- Integrity: No cheating, no hardcoded results or dummy facades. Genuine implementations only.
- Write files only in their designated directories, metadata only in working directory.

## Current Parent
- Conversation ID: 02ac8878-50e3-4b3d-9049-7f8278bd7a9c
- Updated: 2026-06-07T20:23:00Z

## Task Summary
- **What to build**:
  - R1: Global Macro Correlation Engine (`src/analysis/macro_analyzer.py`)
  - R2: ML Predictor Model (`src/analysis/macro_predictor.py`)
  - R3: Global Outperformer Screener (`src/analysis/screener.py` extensions)
  - R4: Dash UI 'Global Macro' Tab Integration (`src/web/dashboard.py` changes)
- **Success criteria**:
  - Successful yfinance data retrieval with robust simulation fallbacks if offline.
  - RandomForestRegressor based predictor trained and metrics saved to `data/macro_model_metrics.json`.
  - Global Outperformer Screener returns top 10 US and top 10 KR outperforming stocks.
  - Dash UI displays heatmap and Datatables for US and KR outperformers.
  - pytest tests pass cleanly.

## Key Decisions Made
- Implemented robust stock returns simulation in `screener.py` to allow off-line fallback where stock returns correlate with local benchmark index and USDKRW=X exchange rates.
- Handled potential NaN targets gracefully in `macro_predictor.py` during fitting, by filtering out missing records to prevent RandomForestRegressor from raising exceptions.
- Added stateless callback helper tests in `tests/test_macro.py` for heatmap generation and outperformer recommendation data fetching to verify UI controller correctness.

## Artifact Index
- `d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_1\original_prompt.md` — Original request prompt copy.
- `d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_1\BRIEFING.md` — Persistent briefing and context.
- `d:\Finance\code\stock\.agents\teamwork_preview_worker_macro_1\progress.md` — Task progress checklist.

## Change Tracker
- **Files modified**:
  - `pyproject.toml` — Added dash dependency.
  - `requirements.txt` — Added dash dependency.
  - `src/analysis/macro_predictor.py` — Added NaN target filtering.
  - `src/analysis/screener.py` — Extended with screen_global_outperformers method.
  - `src/web/dashboard.py` — Extended with Global Macro layout tab, callback helper functions, and callback registrations.
  - `tests/test_macro.py` — Created unit and integration test suite.
- **Build status**: Pass
- **Pending issues**: None.

## Quality Status
- **Build/test result**: pytest tests/test_macro.py passed with 5/5 successful tests.
- **Lint status**: 0 violations.
- **Tests added/modified**: `tests/test_macro.py` added to test R1-R4 features.

## Loaded Skills
- None.
