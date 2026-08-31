## 2026-08-31T15:14:00Z
You are a Worker (teamwork_preview_worker).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\
Original Request path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Project Scope path: d:\Finance\code\stock\PROJECT.md

Mission: Implement Milestone 2 (R2: 31-Strategy Canonical Sequence Unification Across Pipeline & Verifiers).
Read the findings from:
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_1\report.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_2\report.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_3\report.md

Tasks to execute:
1. Edit trading_system/run_pipeline.py:
   - In STRATEGY_REGISTRY (lines ~3201-3231), ensure Strategy 30 is `darkpool` (`darkpool_predictions.txt`, 'Darkpool Score') and Strategy 31 is `earnings_tone_drift` (`earnings_tone_drift_predictions.txt`, 'Tone Score').
   - In verification_files (lines ~4338-4352), expand from 13 to all 31 strategy `.txt` files plus ensemble_predictions.txt, strategy_data_coverage_report.txt, and portfolio_allocation.txt (34 files total).
2. Edit AGENTS.md:
   - In 31-Strategy table lines 42-43: ensure Strategy 30 is Darkpool & HFT Flow (`darkpool`) and Strategy 31 is Earnings Tone Drift (`earnings_tone_drift`).
   - In Mermaid diagram lines 119-120 and Key Files list lines 193-194: align Strategy 30 and 31.
3. Edit trading_system/scripts/verify_gha_artifacts.py:
   - Update `STRATEGIES` list to 31 items in exact canonical order 1..31 (`regression` to `earnings_tone_drift`).
   - Add file mappings and check functions for strategies 24..31.
   - Update `verify_gh_pages()` with `STRATEGY_PANEL_ALIASES` to check all 31 strategy panels in DOM.
   - Update `print_report()` with 31-column matrix display.
4. Edit .agents/skills/gha-artifact-verifier/SKILL.md:
   - Update Key Verification Requirements table to enumerate all 31 strategies individually in canonical sequence.
5. Run verification tests:
   - Run python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages
   - Run pytest tests/test_verify_gha_artifacts.py (if exists) and pytest tests/test_score_normalizer.py tests/test_critical_bugs.py -v
6. Write your report to d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\report.md and a handoff.md in your working directory.
7. Send a message to your caller parent with your summary and test results.
