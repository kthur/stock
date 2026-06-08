# BRIEFING — 2026-06-07T14:14:00Z

## Mission
Investigate the Dash app layout and tab management in the trading system dashboard, determine how to integrate the 'Global Macro' tab, outline needed layout elements and callbacks (heatmap and top 10 US/KR outperformers), and document findings/recommendations in analysis.md and handoff.md.

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: Read-only investigator, analyzer, synthesizer, report writer
- Working directory: d:\Finance\code\stock\.agents\teamwork_preview_explorer_macro_3\
- Original parent: 02ac8878-50e3-4b3d-9049-7f8278bd7a9c
- Milestone: Global Macro Dashboard Integration

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code changes.
- Write reports and analysis only in my working directory.
- Use send_message to notify parent agent when done.

## Current Parent
- Conversation ID: 21db4364-fb8b-4e68-b651-abc6649c4058
- Updated: 2026-06-07T14:14:00Z

## Investigation State
- **Explored paths**:
  - `d:\Finance\code\stock\trading_system\src\web\dashboard.py` (App layout, tabs definition, helper callbacks, WebDashboard server wrapper)
  - `d:\Finance\code\stock\trading_system\run_dashboard.py` (Runner entry point)
  - `d:\Finance\code\stock\trading_system\src\risk\risk_manager.py` (Correlation calculation and risk metrics)
  - `d:\Finance\code\stock\trading_system\src\analysis\market_scanner.py` (KRX scan logic)
  - `d:\Finance\code\stock\trading_system\src\analysis\screener.py` (Stock screening indicators)
- **Key findings**:
  - Dash tabs are statically declared inside `dcc.Tabs`.
  - Callback logic is implemented as module-level stateless helper functions which simplifies unit testing.
  - Adding "Global Macro" tab requires declaring a new `dcc.Tab(label='Global Macro', id='global-macro-tab', children=[...])` inside `dcc.Tabs`.
  - Required elements: `dcc.Graph(id='macro-correlation-heatmap')`, `dash_table.DataTable(id='kr-outperformers-table')`, and `dash_table.DataTable(id='us-outperformers-table')`.
  - Required callbacks: `update_macro_correlation_heatmap` and `update_outperformers_table` with robust boundary handling (fallback data on offline/None inputs).
- **Unexplored areas**:
  - Live data fetching under proxy settings (assumed mock fallbacks will be used).

## Key Decisions Made
- Recommended static declaration of the fourth tab inside `app.layout` to maintain consistency with `performance-tab`, `pnl-tab`, and `backtest-tab`.
- Recommended implementing the two new callbacks as stateless helper functions in `dashboard.py` to match the existing codebase architecture and enable simple test-suite verification.

## Artifact Index
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_macro_3\analysis.md — Detailed integration analysis and design for the Global Macro tab.
- d:\Finance\code\stock\.agents\teamwork_preview_explorer_macro_3\handoff.md — 5-component handoff report.
