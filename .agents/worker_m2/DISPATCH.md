## 2026-08-21T16:31:45Z
You are worker_m2 (Domain 1 Implementation Worker: V6-01 ~ V6-08).
Your working directory is: d:\Finance\code\stock\.agents\worker_m2\

Mandatory inputs to read before starting:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
2. d:\Finance\code\stock\system_improvement_report_v6.md (Sections 2.1~2.8 for Domain 1: V6-01 ~ V6-08)
3. d:\Finance\code\stock\.agents\explorer_1\analysis.md (Domain 1 section)
4. d:\Finance\code\stock\AGENTS.md

Exclusive Write Ownership:
- `src/ai/prediction_model.py`
- `src/ai/ensemble_scorer.py`
- `src/ai/optuna_tuner.py`
- `src/ai/meta_ensemble.py`
- Related tests in `tests/` for Domain 1

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
- V6-01: Correct Causal LSTM target $\log(1+p)$ blending in `src/ai/prediction_model.py` (`transform_sharpe` / `_prepare_lstm_data` and inverse transform) so regression blending does not exponentially explode.
- V6-02: Fix Multi-Horizon Exponential Decay Filter column schema map in `src/ai/ensemble_scorer.py` and `src/ai/prediction_model.py` (`score_col_to_strat` alias map) to support all 31 strategies.
- V6-03: Dual-Regime weight squaring and cross-market weight contamination fix in `src/ai/ensemble_scorer.py` (decouple US weight squaring, extract relative suppression penalty factors).
- V6-04: Fix cross-market LSTM model hijacking in `src/ai/prediction_model.py` (market-partitioned batch evaluation preserving symbol market identity).
- V6-05: Normalize `predict_lead_lag` fallback multi-year cumulative return scaling to 1-day returns in `src/ai/prediction_model.py`.
- V6-06: Fix Optuna 2D regime objective volatility maximization anomaly in `src/ai/optuna_tuner.py` with quadratic risk utility $(\mu - 0.5 \cdot \lambda \sigma^2)$ and bounded iterative simplex projection in `AlphaDecayTracker`.
- V6-07: Remove 10-symbol hardcap bottleneck in Lead-Lag HPO to evaluate all $K = \min(\text{leaders\_count}, N)$ symbols.
- V6-08: Fix feature permutation corruption in `MetaEnsembleLearner` in `src/ai/meta_ensemble.py` with explicit column projection and DataFrame reindexing.

Verification:
- Run pytest on Domain 1 tests: `.venv\Scripts\python.exe -m pytest tests/test_prediction_model.py tests/test_ensemble_scorer.py tests/test_optuna_tuner.py tests/test_meta_ensemble.py -q`
- Ensure all tests pass.
- Write your report to `d:\Finance\code\stock\.agents\worker_m2\handoff.md`.
- Send a completion message with summary of modified files, test results, and status.
