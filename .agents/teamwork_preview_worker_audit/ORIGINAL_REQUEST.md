## 2026-07-11T00:28:40+09:00

You are a Worker agent. Your task is to generate a comprehensive professional audit report for the stock trading and prediction system codebase.

MANDATORY INTEGRITY WARNING:
> DO NOT CHEAT. All implementations must be genuine. DO NOT
> hardcode test results, create dummy/facade implementations, or
> circumvent the intended task. A Forensic Auditor will independently
> verify your work. Integrity violations WILL be detected and your
> work WILL be rejected.

Please perform the following steps:
1. Read the explorer's handoff report located at `d:/Finance/code/stock/.agents/teamwork_preview_explorer_audit/handoff.md` to review the 15 concrete improvement points, line ranges, and before/after snippets.
2. Draft and save the audit report at `d:/Finance/code/stock/reports/improvement_report.md` in Korean.
3. Ensure the report is extremely detailed, structured professionally, and has a total character length of at least 4,000 characters.
4. The report MUST include:
   - **Executive Summary (개요)**:
     - Overall system rating out of 5 with clear justification.
     - Top 3 priorities for action.
     - Expected ROI (quantified pipeline speedups, ML prediction stability, and CI/CD reliability gains).
   - **Master Priority Table (마스터 우선순위 테이블)**:
     - Columns: 분야 (Area), ID, 개선 항목 (Title), 우선순위 (Priority: P0/P1/P2/P3), 예상 영향도 (Expected Impact), 구현 난이도 (Difficulty: Easy/Medium/Hard), 파일 경로 (File Path), 라인 범위 (Line Range).
     - Must include all 15 distinct points.
   - **Detailed Analysis by 5 Areas (5대 영역별 상세 분석)**:
     - ML Model Quality, Pipeline Performance, CI/CD & Infrastructure, Code Quality, Operations & Monitoring.
     - At least 3 points per area.
     - For the top 5 highest impact improvements (Point 1.3: Unified Global Normalization Baselines, Point 2.1: Batch Fundamental Retrieval, Point 2.2: Thread-Safe DB Connection Pool, Point 1.1: Chronological Embargo Split, and Point 2.3: Binary Split Recovery for Prefetching), provide Before/After code snippets with exact changes and quantified expected gains.
     - For the remaining 10 points, write clear explanations and proposed implementation details.
   - **Weekly Execution Roadmap (실행 로드맵)**:
     - A 4-week implementation schedule (Week 1 for P0, Week 2 for P1, Week 3 for P2, Week 4 for P3) that organizes the execution flow logically.
5. After writing the file, verify that `d:/Finance/code/stock/reports/improvement_report.md` exists, has correct content, and that its length is indeed >= 4,000 characters.
6. Send a message back to the orchestrator (conversation ID: `d55a6efc-35d8-490d-a7e0-41244a702e2c`) with the path and confirmation of success.

Your working directory is `d:/Finance/code/stock/.agents/teamwork_preview_worker_audit`.
