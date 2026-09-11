# DISPATCH: Forensic Auditor (Phase 24 Integrity Verification - Replacement)

## Identity & Role
- Archetype: teamwork_preview_auditor
- Role: Forensic Integrity Auditor
- Working directory: `d:\Finance\code\stock\.agents\auditor_phase24_2`

## Inputs
- Authoritative User Request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header `## 2026-09-11T10:54:49Z`)
- Project Scope: `d:\Finance\code\stock\PROJECT.md`
- Target Code Files to Audit:
  - `src/ai/ensemble_scorer.py`
  - `src/ai/factor_suppression.py`
  - `src/risk/unified_portfolio_allocator.py`
  - `src/risk/portfolio_allocator.py`
  - `src/core/fast_lob_engine.py`
  - `src/execution/smart_order_router.py`
  - `src/execution/oms_engine.py`
  - `trading_system/scripts/benchmark_phase24_quant_performance.py`
  - `tests/test_phase24_*.py`
  - `reports/quant_benchmark_comparison_phase24.md`
  - `trading_system/result/quant_benchmark_comparison_phase24.md`
  - `reports/quant_benchmark_comparison.md`
  - `AGENTS.md`
  - `PROJECT.md`

## Objective
Perform an exhaustive 3-tier forensic integrity audit:
1. **Tier 1: Static Code Authenticity & Checks**:
   - Verify that there are zero hardcoded results, no dummy/facade implementations, and genuine mathematics for F115, F116.1, F116.2, F117.1, F117.1.2, F117.2, maker floor $0.0000005$, tick shading $-0.9998 \cdot \text{spread} \cdot (h - 0.030)$, dark ATS $99.998\%$, anti-gaming $99.9995\%$.
2. **Tier 2: Runtime Numerical Reproduction & Causality**:
   - Run the benchmark script: `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase24_quant_performance.py`
   - Verify that generated numbers match the markdown reports.
   - Verify causality and absence of forward-looking bias.
3. **Tier 3: Test Authenticity & Regression Audit**:
   - Run full pytest suite: `.venv\Scripts\python.exe -m pytest tests/test_phase24_*.py tests/test_phase23_*.py -v`
   - Verify tests are authentic without trivial dummy assertions.
   - Audit `AGENTS.md` and `PROJECT.md` updates.

Deliver your binary verdict (**CLEAN** or **INTEGRITY VIOLATION**) with exhaustive evidence in `handoff.md` and send a message when done.

## 2026-09-11T11:50:27Z
You are the Forensic Integrity Auditor for Phase 24 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\auditor_phase24_2
Read your dispatch at: d:\Finance\code\stock\.agents\auditor_phase24_2\DISPATCH.md
Read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header ## 2026-09-11T10:54:49Z).

Perform an exhaustive 3-tier forensic integrity audit:
1. Tier 1: Static code authenticity (zero hardcoding, no dummy/facade implementations, genuine mathematical implementation of F115, F116.1, F116.2, F117.1, F117.1.2, F117.2, maker floor 0.0000005, tick shading -0.9998, ATS 99.998%, anti-gaming 99.9995%, and F118 benchmark).
2. Tier 2: Runtime numerical reproduction (execute `.venv\Scripts\python.exe trading_system/scripts/benchmark_phase24_quant_performance.py` and verify all reported values match runtime execution, verify causality).
3. Tier 3: Test authenticity & regression audit (execute `.venv\Scripts\python.exe -m pytest tests/test_phase24_*.py tests/test_phase23_*.py -v` verifying 100% genuine pass and 0 regressions, verify AGENTS.md and PROJECT.md updates).

Deliver your binary verdict (CLEAN or INTEGRITY VIOLATION) with exhaustive evidence in `d:\Finance\code\stock\.agents\auditor_phase24_2\handoff.md` and send a message when done.

