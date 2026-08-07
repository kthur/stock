## 2026-08-06T01:00:07Z
<USER_REQUEST>
You are a teamwork_preview_reviewer inspecting Milestone 1 (Financial Engineering & Quantitative Risk Audit).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_reviewer_m1_2.
Read ORIGINAL_REQUEST.md at: d:\Finance\code\stock\ORIGINAL_REQUEST.md.
Read PROJECT.md at: d:\Finance\code\stock\.agents\orchestrator_readiness_audit\PROJECT.md.

Task:
Review risk management, HRP portfolio allocation, covariance matrix handling, position sizing limits, liquidity checks, CrisisDetector gating, and microstructure friction costs across:
- `src/analysis/portfolio_optimizer.py`
- `src/risk/portfolio_allocator.py` & `src/risk/position_sizing.py` & `src/risk/pretrade_gatekeeper.py`
- `src/risk/risk_manager.py` & `trading_system/run_pipeline.py`
- `src/ai/ensemble_scorer.py`

Run test suites and verify that risk controls fail closed, position caps (15% single asset, 30% sector, ADV 5%) are strictly enforced, and microstructure cost deductions are accurate.
Write `handoff.md` with your verdict (APPROVE or REQUEST_CHANGES) and justification. Send a message to parent when finished.
</USER_REQUEST>
