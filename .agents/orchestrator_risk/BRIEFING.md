# BRIEFING — 2026-06-13T13:46:36+09:00

## Mission
Audit and enhance risk manager and asset allocation, implement dynamic position sizing and adaptive stops, backtest, generate expert report, and pass unit tests.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\Finance\code\stock\.agents\orchestrator_risk
- Original parent: main agent
- Original parent conversation ID: 29f32446-4699-4f44-82dd-752202990a2a

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: d:\Finance\code\stock\.agents\orchestrator_risk\SCOPE.md
1. **Decompose**: Decompose the upgrades into logical milestones (Audit, Position Sizing, Stops, Backtest, Report/Verify).
2. **Dispatch & Execute**:
   - **Direct (iteration loop)**: For each milestone, spawn Explorer(s) -> Worker -> Reviewer -> Challenger -> Auditor.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (last resort)
4. **Succession**: Self-succeed at 16 spawns.
- **Work items**:
  - M1: PyTorch & Config Fixes [done]
  - M2: Risk Management & Allocation Audit [pending]
  - M3: Position Sizing & Stop Improvements [pending]
  - M4: Comparative Backtesting & Reporting [pending]
  - M5: Final Verification & Testing [pending]
- **Current phase**: 1
- **Current focus**: Decompose and plan

## 🔒 Key Constraints
- Never write or modify source code files directly.
- Never run build/test commands directly — use subagents.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh.

## Current Parent
- Conversation ID: 29f32446-4699-4f44-82dd-752202990a2a
- Updated: not yet

## Key Decisions Made
- [TBD]

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| explorer_m1_1 | teamwork_preview_explorer | Audit Risk Manager | completed | a64620d3-e7c8-4e89-9ddd-119cdecd6fba |
| explorer_m1_2 | teamwork_preview_explorer | Audit Asset Allocation | completed | d75a0ba4-5bd6-499a-a7ff-80e76244bfbc |
| explorer_m1_3 | teamwork_preview_explorer | Find Backtesting Framework | completed | 8c4811a7-c7f3-41f8-bf53-1d745719b185 |
| worker_m2 | teamwork_preview_worker | Implement Risk & Stops Upgrades | completed | cd1f3d76-38f9-4413-8828-59d66b4267b3 |
| worker_m3_m4 | teamwork_preview_worker | Backtest, Report, verify tests | completed | fd17b2a1-cb45-465f-898a-e3c5f349fcf8 |
| auditor_m5 | teamwork_preview_auditor | Perform forensic integrity audit | completed | d399d980-7639-4624-9c9f-adb7bfbf7ee9 |

## Succession Status
- Succession required: no
- Spawn count: 6 / 16
- Pending subagents: none
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: stopped
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run `manage_task(Action="list")` — re-create if missing

## Artifact Index
- d:\Finance\code\stock\.agents\orchestrator_risk\ORIGINAL_REQUEST.md — Original request record
- d:\Finance\code\stock\.agents\orchestrator_risk\BRIEFING.md — Persistent working memory
- d:\Finance\code\stock\.agents\orchestrator_risk\progress.md — Liveness and checkpoint file
- d:\Finance\code\stock\.agents\orchestrator_risk\SCOPE.md — Decomposed scope of milestones
