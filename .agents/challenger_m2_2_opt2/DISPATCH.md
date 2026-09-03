# DISPATCH - Challenger M2-2

## Mission
Adversarially challenge Milestone 2 execution and OMS logic:
Target modules:
- `trading_system/src/execution/oms_engine.py`
Input documents:
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (read section ## 2026-09-03T15:32:22Z)
- `d:\Finance\code\stock\AGENTS.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_orchestrator_quant_opt2\PROJECT.md`
- `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2_opt2\handoff.md`

Tasks:
1. Write adversarial test harness to challenge:
   - Delta rebalancing under extreme inventory scenarios (e.g. current holdings exceed 200% of target, partial liquidations, zero-dollar prices, sub-lot residuals).
   - Verify that $\sum \text{tranche\_quantity} == \text{total\_order\_quantity}$ strictly for 1000 randomized orders across all slice counts ($1 \dots 10$).
   - Verify tagging invariants: single slices use strategy tag, multi-slice uses `MIDPOINT_PEG` for $1 \dots N-1$ and `AGGRESSIVE_TAKER` for $N$.
2. Execute empirical challenge tests via `.venv\Scripts\pytest`.
3. Report verdict: APPROVE or REJECT in `d:\Finance\code\stock\.agents\challenger_m2_2_opt2\handoff.md`.
Update `progress.md` with timestamps as your liveness heartbeat.
When finished, send a brief message with your handoff report path.
