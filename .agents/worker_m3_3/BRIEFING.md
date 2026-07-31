# BRIEFING — 2026-07-31T11:07:27Z

## Mission
1. Remediate the Double Position Scaling Bug in `trading_system/src/risk/risk_manager.py` where `stress_test_adjustment_factor` is applied twice when stress test fails, and add explicit assertions in test suites.
2. Incorporate edge-case guards in `trading_system/src/ai/cpcv_stress_tester.py` (Inf/NaN Finiteness Guard & Small Sample Size Guard).

## 🔒 My Identity
- Archetype: worker_m3_3
- Roles: implementer, qa, specialist
- Working directory: d:\Finance\code\stock\.agents\worker_m3_3
- Original parent: 1fe0721e-b4fd-439c-bbd3-fbdc36359790
- Milestone: Milestone 3 Remediation

## 🔒 Key Constraints
- Fix double scaling bug in `RiskManager.calculate_position_sizing` so `stress_test_adjustment_factor` (0.75) is applied exactly once.
- Update test cases in `tests/test_cpcv_stress_tester.py` and `trading_system/tests/test_cpcv_stress_tester.py` to explicitly assert `position_quantity == expected_0_75_quantity` when `stress_test_passed == False`.
- Add Inf/NaN Finiteness Guard & Small Sample Size Guard in `trading_system/src/ai/cpcv_stress_tester.py`.
- Verify all tests pass without breaking regression suite.

## Current Parent
- Conversation ID: 1fe0721e-b4fd-439c-bbd3-fbdc36359790
- Updated: 2026-07-31T11:07:27Z

## Task Summary
- **What to build**:
  - Fix double position scaling bug in `risk_manager.py`.
  - Add CPCV stress tester resilience guards in `cpcv_stress_tester.py`.
  - Update unit test assertions in CPCV stress tester test files.
- **Success criteria**:
  - Position quantity scales by 0.75 (not 0.5625) when `stress_test_passed == False`.
  - CPCV stress tester handles Inf/NaN and small sample sizes gracefully.
  - All unit tests and regression tests pass.
- **Interface contracts**: `PROJECT.md` / `AGENTS.md`
- **Code layout**: `trading_system/src/risk/risk_manager.py`, `trading_system/src/ai/cpcv_stress_tester.py`, `tests/test_cpcv_stress_tester.py`, `trading_system/tests/test_cpcv_stress_tester.py`

## Key Decisions Made
- Confirmed task scope includes RiskManager fix, CPCVStressTester resilience guards, and test assertion updates.

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Pending
- **Tests added/modified**: Pending

## Loaded Skills
- None

## Artifact Index
- `d:\Finance\code\stock\.agents\worker_m3_3\ORIGINAL_REQUEST.md` — Original prompt payload + additions
- `d:\Finance\code\stock\.agents\worker_m3_3\BRIEFING.md` — System briefing state
