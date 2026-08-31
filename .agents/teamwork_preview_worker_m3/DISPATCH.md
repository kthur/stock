## 2026-08-31T15:23:00Z
You are a Worker (teamwork_preview_worker).
Your working directory is: d:\Finance\code\stock\.agents\teamwork_preview_worker_m3\
Original Request path: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md
Project Scope path: d:\Finance\code\stock\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Mission: Implement Milestone 3 (R3: GitHub Pages Dashboard Metric Consolidation & UX Enhancement).
Read the architecture and structural blueprint in:
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\survey_report.md
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_survey_3\handoff.md

Tasks to execute in `trading_system/generate_report.py`:
1. Consolidate fragmented dashboard cards into the 3 Target Core Unified Cards:
   - **Card 1: Market Regime & Risk Gates Console (`🌐 2D Market Regime & Risk Gates`)**:
     Integrate dual-market 2D regime status badges (US & KR), Crisis Detector levels (NONE/WATCH/ACTIVE/SEVERE), VIX velocity and term structure gating, macro indicators with fallback badges and tooltips, 6-regime matrix, and AI Strategy Decision Rationale into a single high-density executive command card.
   - **Card 2: Strategy Coverage & Missingness Diagnostic Center (`🩺 Strategy Coverage & Data Health Diagnostic Center`)**:
     Integrate 31-strategy health monitor cards with dynamic status filtering (`[All]`, `[Healthy]`, `[Partial]`, `[Fallback]`, `[Need Data]`), multi-tier progress bars, Korean missingness reason explanations, symbol diagnostics, zero-weight safeguard notices, and CPCV / PBO overfitting stress test diagnostics. Add interactive click-to-jump navigation to strategy tab panels.
   - **Card 3: Portfolio Optimization & Execution OMS Command Center (`💼 Portfolio Optimization & Execution OMS`)**:
     Integrate HRP / Black-Litterman asset allocation donut chart and cross-market exposure bar chart with EVT-GPD CVaR tail risk budgeting metrics (95%/99% VaR/CVaR), Leland dynamic no-trade buffer bands (±2.5%), closed-loop realized slippage feedback by market (from `trade_logs.db`), OMS 7-Safety Gates status badges, and compact sortable execution order table with Leland status tags.
2. Synchronize Canonical 31-Strategy Sequence (1..31):
   - Ensure strategy tabs in navigation bar, tab panels, table columns, and stock drawer factor breakdown dictionaries strictly adhere to canonical sequence 1..31 (Strategy 30: `darkpool`, Strategy 31: `earnings_tone_drift`).
3. Responsive UX & Interactive Styling:
   - Ensure clean desktop (>1200px), tablet (768~1199px), and mobile (<768px) views.
   - Add accessible tooltips, badge styles, collapsible mobile sections, and interactive stock drawer modal.
4. Execute Dashboard Generation and Verification:
   - Run `python trading_system/generate_report.py --result-dir trading_system/result --out gh-pages/index.html`.
   - Run `python trading_system/scripts/verify_gha_artifacts.py --result-dir trading_system/result --gh-pages-dir gh-pages`.
   - Run pytest tests: `pytest tests/test_report_generator_hrp.py tests/test_report_ux_and_rounding.py tests/test_verify_gha_artifacts.py -v`.
5. Write your implementation report to d:\Finance\code\stock\.agents\teamwork_preview_worker_m3\report.md and a handoff.md in your working directory.
6. Send a message to your caller parent with your summary, dashboard file size, and test results.
