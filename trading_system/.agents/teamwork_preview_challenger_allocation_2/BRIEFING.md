# BRIEFING — 2026-06-06T19:50:00+09:00

## Mission
Stress-test and empirically verify `allocate_assets` function in `src/strategy/allocation.py` to ensure it always correctly handles all edge cases.

## 🔒 My Identity
- Archetype: EMPIRICAL CHALLENGER
- Roles: critic, specialist
- Working directory: d:/Finance/code/stock/trading_system/.agents/teamwork_preview_challenger_allocation_2
- Original parent: 4f3be3a5-b1cf-4a8e-a5d9-93a71e1c0722
- Milestone: Milestone 2: Asset Allocation
- Instance: 1 of 1

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Run verification code myself. Do NOT trust the worker's claims or logs.
- If I cannot reproduce a bug empirically, it does not count.

## Current Parent
- Conversation ID: 4f3be3a5-b1cf-4a8e-a5d9-93a71e1c0722
- Updated: 2026-06-06T19:50:00+09:00

## Review Scope
- **Files to review**: `src/strategy/allocation.py`
- **Interface contracts**: The weights must sum exactly to 1.0, invalid prices filtered out, proportional weighting.
- **Review criteria**: Check correctness and edge cases.

## Key Decisions Made
- [TBD]

## Artifact Index
- `test_allocation_stress.py` — stress tests to check validity.
