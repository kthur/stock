## 2026-08-05T12:57:38Z
<USER_REQUEST>
You are the Project Orchestrator for the multi-agent evaluation and optimization of the Stock Trading System (`d:\Finance\code\stock`).

Working directory: `d:\Finance\code\stock\.agents\orchestrator_eval_opt`
Original request file: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md`

Your job is to orchestrate specialists (explorer, worker, reviewer, challenger, etc.) to evaluate, optimize, verify, and resolve all requirements specified in `ORIGINAL_REQUEST.md`:

### Requirements Summary:
1. **R1. Financial Engineering & Model Optimization**:
   - Verify PCA Symmetric ZCA factor orthogonalization and correlation suppression under all 6 market regimes to prevent multi-collinearity.
   - Ensure Isotonic Regression calibrators and rolling Sharpe weights seamlessly adapt without signal degradation.
2. **R2. Risk Management & Portfolio Optimization**:
   - Verify GICS sector-based stress scenarios and crisis level thresholds in `generate_report.py`.
   - Validate real-time order execution tracking in `trade_logs.db` and tracking error monitoring in OMS engine.
3. **R3. Pipeline Resilience & UI/UX Presentation**:
   - Audit SQLite WAL multi-thread write locks and workflow execution timing for GHA pipeline resilience.
   - Verify mobile (375px/414px) and desktop (1920px) rendering, sticky table headers, and macro badges in GitHub Pages report (`index.html` / `update_dashboard.py`).

### Acceptance Criteria:
- [ ] All unit and integration tests pass cleanly (`.venv\Scripts\python.exe -m pytest tests/ -v`).
- [ ] GHA Artifact Verifier (`verify_gha_artifacts.py`) confirms 100% valid non-zero data across all 18 strategy panels and 5 markets.
- [ ] No regression in trading logic, position sizing, or risk manager thresholds.

Instructions:
1. Create your `BRIEFING.md` and `plan.md` in `d:\Finance\code\stock\.agents\orchestrator_eval_opt`.
2. Maintain `progress.md` continuously throughout execution.
3. Spawn subagents in their own dedicated working directories under `d:\Finance\code\stock\.agents/` (e.g. `.agents/explorer_...`, `.agents/worker_...`, `.agents/reviewer_...`).
4. Ensure all changes are thoroughly tested and verified via pytest and `verify_gha_artifacts.py`.
5. When all milestones are complete and verified, send a detailed completion report back to Sentinel.
</USER_REQUEST>
