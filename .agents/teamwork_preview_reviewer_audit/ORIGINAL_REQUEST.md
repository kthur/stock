## 2026-07-11T00:44:45+09:00
You are a Reviewer agent. Your task is to perform an independent quality and correctness review of the generated audit report located at `d:/Finance/code/stock/reports/improvement_report.md`.

Please verify that:
1. The report is written in professional Korean.
2. The character length is at least 4,000 characters (excluding whitespace if possible).
3. It has all the required sections:
   - Executive Summary (including a rating out of 5, top 3 priorities, and expected ROI).
   - Master Priority Table (detailing all 15 points with Area, ID, Title, Priority, Impact, Difficulty, File Path, and Line Range).
   - Detailed audit findings for each of the 5 areas (ML Model Quality, Pipeline Performance, CI/CD & Infrastructure, Code Quality, Operations & Monitoring), with at least 3 concrete points per area.
   - Before/After code snippets for the top 5 highest impact improvements showing exact modifications and quantified gains.
   - A 4-week execution roadmap mapping tasks logically.
4. The proposed Before/After code snippets are technically correct, realistic, and address the specific code paths cited.

Write your detailed review report to `handoff.md` in your working directory `d:/Finance/code/stock/.agents/teamwork_preview_reviewer_audit/`.
Once completed, send a message back to the orchestrator (conversation ID: `d55a6efc-35d8-490d-a7e0-41244a702e2c`) summarizing your review verdict (PASS/FAIL) and any notes.
Your working directory is `d:/Finance/code/stock/.agents/teamwork_preview_reviewer_audit`.
