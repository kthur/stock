# BRIEFING — 2026-09-10T01:23:37Z

## Mission
Implement Milestone M3: Microstructure OMS Specialist for Phase 21 Quant Enhancement (Feature F105.2 Kerr-Newman-AdS-dS L3 hydrodynamics, F105.2.2 maker floor 0.000005, F105.2.3/4 ATS 99.98% & MinQty 99.995%, F105.2.5 preemptive micro-tick shading -0.998 * spread * (h - 0.05)).

## 🔒 My Identity
- Archetype: Microstructure OMS Specialist
- Roles: implementer, qa, specialist
- Working directory: d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\worker_m3
- Original parent: 71775911-987d-4377-a3ae-82e4a04c2ac3
- Milestone: M3 (Microstructure OMS Specialist - Requirement R3)

## 🔒 Key Constraints
- Exclusive write ownership of:
  * src/core/fast_lob_engine.py
  * src/execution/smart_order_router.py
  * src/execution/oms_engine.py
- MUST NOT edit any AI ensemble, risk, or benchmark files.
- Full backward compatibility with legacy phases (Phases 7 through 20).
- Zero tracking error between ExecutionOMSEngine and AlmgrenChrissScheduler peg limit calculations.
- No shortcuts or dummy implementations; genuine physics and math.

## Current Parent
- Conversation ID: 71775911-987d-4377-a3ae-82e4a04c2ac3
- Updated: 2026-09-10T01:23:37Z

## Task Summary
- **What to build**:
  1. Kerr-Newman-AdS-dS cosmological black hole L3 hydrodynamics in `FastOrderBookMatchingEngine` (`fast_lob_engine.py`), with dark routing cap 0.9998 in `DeepHawkesArrivalProcess`.
  2. Maker floor contracted to 0.000005 (0.70 * (1.0 - 0.99999286 * gamma_toxic)), dark cap 0.9998, and dynamic MinQty 0.99995 in `smart_order_router.py`.
  3. Preemptive Hawkes micro-tick shading `-direction * 0.998 * spr * (h - 0.05)` for $h > 0.05$ in `ExecutionOMSEngine` and `AlmgrenChrissScheduler` in `oms_engine.py`.
- **Success criteria**: 100% tests pass, zero regressions, all interface contracts met.
- **Interface contracts**: `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\PROJECT.md` § Interface Contracts (M3).

## Key Decisions Made
- Follow exact physical formulas for Kerr-Newman-AdS-dS spacetime geometry: cosmological constant $\Lambda = 3/L_{dS}^2 - 3/L_{AdS}^2$, rotation factor $\Xi_{AdS-dS}$, de Sitter horizon $r_C = L_{dS}(1 - M/L_{dS})$, and hydrodynamic acceleration $a_{AdS-dS}$.
- Maintain exact parity between `ExecutionOMSEngine` and `AlmgrenChrissScheduler`.

## Artifact Index
- `d:\Finance\code\stock\src\core\fast_lob_engine.py` — L3 orderbook engine & Hawkes arrival process
- `d:\Finance\code\stock\src\execution\smart_order_router.py` — Smart order router
- `d:\Finance\code\stock\src\execution\oms_engine.py` — OMS execution engine & scheduler
- `d:\Finance\code\stock\.agents\orchestrator_quant_phase21_1\worker_m3\handoff.md` — Handoff report

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Not yet run
- **Lint status**: Clean
- **Tests added/modified**: Pending
