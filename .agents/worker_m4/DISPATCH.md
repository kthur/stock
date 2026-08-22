## 2026-08-21T16:31:51Z
You are worker_m4 (Domain 3 Implementation Worker: V6-17 ~ V6-24).
Your working directory is: d:\Finance\code\stock\.agents\worker_m4\

Mandatory inputs to read before starting:
1. d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
2. d:\Finance\code\stock\system_improvement_report_v6.md (Sections 4.1~4.8 for Domain 3: V6-17 ~ V6-24)
3. d:\Finance\code\stock\.agents\explorer_3\analysis.md (Domain 3 section)
4. d:\Finance\code\stock\AGENTS.md

Exclusive Write Ownership:
- `src/core/rim_valuation.py`
- `src/core/sector_rotation.py`
- `src/core/iv_skew.py`
- `src/core/event_driven.py`
- `src/core/card_factor.py`
- `src/core/stat_arb.py`
- `src/data_layer/data_validator.py`
- `src/data_layer/earnings_data.py`
- Factor rank normalization in `src/core/mq_factor.py`, `src/core/order_flow.py`, `src/core/short_term_reversal.py`, `src/core/arm_factor.py`, `src/core/latr_factor.py`, `src/core/inst_foreign_sector.py`, `src/core/supply_chain.py`, `src/core/accruals_quality.py`, `src/core/short_squeeze.py`, `src/core/value_up.py`, `src/core/trend_efficiency.py`, `src/core/gamma_squeeze.py`, `src/core/insider_buying.py`, `src/core/tone_drift.py`, `src/core/darkpool_tracker.py`, etc.
- Related tests under `tests/` for Domain 3

Tasks:
- V6-17: Synchronous vs Asynchronous Book Value Scale Discrepancies in `src/data_layer/earnings_data.py` and `src/core/rim_valuation.py` (Total Equity vs BPS scale alignment and remove flawed `bv > 1_000_000` heuristic).
- V6-18: Pass `symbol=sym` to `normalize_sector()` in `src/core/sector_rotation.py` to prevent bypassing curated symbol GICS sector map.
- V6-19: Prioritize live options chain fetch in `src/core/iv_skew.py` when `ENABLE_LIVE_OPTIONS_FETCH=true` instead of price proxy subordination.
- V6-20: Fix 8-digit DART `corp_code` vs 6-digit stock ticker string comparison in `src/core/event_driven.py` by integrating with `DARTCorpMapper`.
- V6-21: Align 5:1 temporal horizon mismatch (5-day stock vs 1-day macro) in `src/core/card_factor.py` to 5-day rolling macro change.
- V6-22: Fix single-stock evaluation rank saturation ($N=1 \implies \text{rank}=0.98$) across factor engines with $N=1$ neutral score guard (0.50).
- V6-23: Replace unbounded `INFO` logging of 100,000-element NumPy arrays in `src/core/stat_arb.py` with `DEBUG` count summary.
- V6-24: Add reverse stock split detection ($>+50\%$ price jump + volume contraction) in `src/data_layer/data_validator.py` and prevent false-positive spike interpolation.

Verification:
- Run pytest on Domain 3 tests: `.venv\Scripts\python.exe -m pytest tests/test_rim_valuation.py tests/test_sector_rotation.py tests/test_iv_skew.py tests/test_event_driven.py tests/test_card_factor.py tests/test_stat_arb.py tests/test_data_validator.py -q`
- Ensure all tests pass.
- Write your report to `d:\Finance\code\stock\.agents\worker_m4\handoff.md`.
- Send a completion message with summary of modified files, test results, and status.
