# BRIEFING — 2026-06-12T22:01:11+09:00

## Mission
Fix the prediction model bugs (lookahead bias, row duplication, missing columns, KeyErrors, constant prices dropna), verify using unit/stress/adversarial tests, pass forensic integrity audit, and complete the fundamental data integration.

## 🔒 My Identity
- Archetype: teamwork_preview_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: d:\Finance\code\stock\.agents\orchestrator_fundamental_gen2\
- Original parent: main agent
- Original parent conversation ID: 0a48f293-413b-4873-a143-dd878508de2c

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: d:\Finance\code\stock\PROJECT.md
1. **Decompose**:
   - Milestone 1: Implement fixes for lookahead bias, row duplication, duplicate symbol column, KeyError on partial features, missing columns, constant/halted prices dropna, and stale prediction warning in prediction_model.py.
   - Milestone 2: Verify all tests (database, feature normalization, stress, post-market scoring, and adversarial tests) pass.
   - Milestone 3: Run Forensic Integrity Audit and verify Clean status.
2. **Dispatch & Execute** (pick ONE):
   - **Direct (iteration loop)**: We run a single Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate cycle to implement and verify the fixes.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: at 16 spawns, write handoff.md, spawn successor.
- **Work items**:
  1. Initialize Plan and Progress [done]
  2. Spawn Explorers to analyze codebase and confirm fix strategies [pending]
  3. Spawn Worker to implement fixes in prediction_model.py [pending]
  4. Spawn Reviewers and Challengers to verify correctness [pending]
  5. Spawn Forensic Auditor to verify integrity and compile results [pending]
- **Current phase**: 2
- **Current focus**: Milestone 1 Implementation

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- You MAY use file-editing tools ONLY for metadata/state files (.md) in your .agents/ folder.
- Follow the Project pattern.
- Verify everything via workers running tests.

## Current Parent
- Conversation ID: 0a48f293-413b-4873-a143-dd878508de2c
- Updated: not yet

## Key Decisions Made
- Resume from the previous resource exhausted run.
- Use a single iteration loop Explorer -> Worker -> Reviewer -> Challenger -> Auditor to address all remaining issues.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| Explorer 1 | teamwork_preview_explorer | Analyze codebase and recommend fixes | completed | 95563411-32da-407c-943d-bc63cbff12d1 |
| Explorer 2 | teamwork_preview_explorer | Analyze codebase and recommend fixes | completed | a0fc833a-743a-4ff3-bbe6-b077d0ed72c1 |
| Explorer 3 | teamwork_preview_explorer | Analyze codebase and recommend fixes | completed | a4cca4fe-46bc-4eb3-8c10-9333b5e86f83 |
| Worker 1 | teamwork_preview_worker | Verify codebase and apply refinements | pending | 5247d78d-5caf-4189-905f-cce7dbd9ef40 |

## Succession Status
- Succession required: no
- Spawn count: 4 / 16
- Pending subagents: 5247d78d-5caf-4189-905f-cce7dbd9ef40
- Predecessor: orchestrator_fundamental
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: task-59
- Safety timer: task-142

## Artifact Index
- d:\Finance\code\stock\.agents\orchestrator_fundamental_gen2\ORIGINAL_REQUEST.md — Verbatim user request
- d:\Finance\code\stock\.agents\orchestrator_fundamental_gen2\BRIEFING.md — Context memory
- d:\Finance\code\stock\.agents\orchestrator_fundamental_gen2\plan.md — Project plan
- d:\Finance\code\stock\.agents\orchestrator_fundamental_gen2\progress.md — Heartbeat and progress checklist
