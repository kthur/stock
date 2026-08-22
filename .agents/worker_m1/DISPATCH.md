## 2026-08-22T06:12:54Z
You are worker_m1, a teamwork_preview_worker.
Your working directory is d:\Finance\code\stock\.agents\worker_m1.
Read ORIGINAL_REQUEST.md at d:\Finance\code\stock\ORIGINAL_REQUEST.md, PROJECT.md at d:\Finance\code\stock\PROJECT.md, and the R1 investigation report at d:\Finance\code\stock\.agents\explorer_survey_1\survey_r1.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

TASK: Implement Milestone 1 (Requirement R1: 31-Strategy Score Normalization, 0.50 Purge, Dynamic Weight Re-normalization):
1. Build `CrossSectionalScoreNormalizer` in `trading_system/src/ai/score_normalizer.py`:
   - Implement methods for cross-sectional normalization: `percentile_rank` and `winsorized_zscore` (Winsorize 1st/99th percentiles, calculate Z-score, apply Gaussian CDF $\Phi(z)$ to map to $[0, 1]$).
   - Group by market (with combined region/global fallback if sample size $N < 10$).
   - Strictly preserve `NaN` for missing strategies so downstream masks know the factor was not computed.
2. Integrate into `trading_system/src/ai/ensemble_scorer.py`:
   - Apply `CrossSectionalScoreNormalizer` to all 31 strategy inputs.
   - Enforce dynamic zero-weighting: for ticker $i$, if strategy $k$ is missing/NaN, its effective weight is 0.
   - Re-normalize active weights per ticker: $\tilde{w}_{i,k} = \frac{m_{i,k} w_k^{(i)}}{\sum_j m_{i,j} w_j^{(i)}}$ such that the sum of active weights for each stock is strictly 1.0.
3. Purge artificial `0.50` default fallbacks across strategy engines:
   - `trading_system/src/core/accruals_quality.py`
   - `trading_system/src/core/valueup_catalyst.py`
   - `trading_system/src/core/short_interest_squeeze.py`
   - `trading_system/src/core/trend_efficiency.py`
   - `trading_system/src/core/insider_buying.py`
   - `trading_system/src/core/earnings_tone_drift.py`
   - `trading_system/src/core/iv_skew.py`
   - `trading_system/run_pipeline.py` (any `fillna(0.5)` for strategy scores)
   - `trading_system/src/ai/ensemble_scorer.py` (missing column fallbacks)
   Ensure they output genuine `np.nan` on missing data.
4. Testing & Verification:
   - Create thorough unit tests in `tests/test_score_normalizer.py`.
   - Run tests: `.venv/Scripts/python.exe -m pytest tests/test_score_normalizer.py tests/test_ensemble_scorer.py tests/test_dynamic_weights.py -v`.
   - Ensure all affected and existing unit tests pass 100%.
5. Document all changes, files modified, test commands, and passing output in `d:\Finance\code\stock\.agents\worker_m1\handoff.md`.
Communicate completion via send_message to your parent.
