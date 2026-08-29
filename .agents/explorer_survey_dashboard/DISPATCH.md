## 2026-08-28T22:47:51Z
You are an Explorer investigating the GitHub Pages dashboard reporting and health status display.

Read ORIGINAL_REQUEST.md at `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (specifically requirement R3) and inspect:
1. `trading_system/generate_report.py` and `gh-pages/index.html` (and any related templates/scripts/CSS).
2. How table data, metric cells, and tab contents are currently rendered across all 31 strategy tabs and summary views.
3. Identify all places where raw `nan`, `None`, or `undefined` could be rendered in HTML tables.
4. Design the Strategy Data Status Summary Card / Health Monitor to be displayed at the top of the dashboard showing coverage/validity rate for each strategy.
5. Design user-friendly badge components (e.g., `<span class="badge-na">N/A</span>`, `데이터 수집필요`) and tab-level warning/notice banners when a strategy or market has 0 or incomplete data.

Your working directory is: `d:\Finance\code\stock\.agents\explorer_survey_dashboard`.
Write your full findings, HTML/CSS structure designs, and concrete code changes to `d:\Finance\code\stock\.agents\explorer_survey_dashboard\handoff.md`.
Use `send_message` to notify the orchestrator when finished.
