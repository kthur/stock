# Task Assignment: Phase 44 Survey Explorer — Microstructure OMS Scope (F197.2)

## Identity & Working Directory
- Role: Survey Explorer (Microstructure & OMS Scope)
- Working Directory: d:\Finance\code\stock\.agents\explorer_phase44_survey_oms

## Context & Inputs
- Authoritative Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)
- Orchestrator Dispatch: d:\Finance\code\stock\.agents\orchestrator_quant_phase44_1\DISPATCH.md
- Scope Document: d:\Finance\code\stock\PROJECT.md

## Target Files (ONLY 3 Files to Investigate)
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- Test reference: `tests/test_phase43_oms.py`

## Objectives
1. Inspect Phase 43 implementation:
   - KNK 22-Dark-Energy DAHA L3 in `fast_lob_engine.py`
   - Maker floor (1e-15), dark ATS (99.999999999%), anti-gaming (99.9999999998%) in `smart_order_router.py`
   - Preemptive tick shading in `oms_engine.py` (and `almgren_chriss.py` if relevant)
2. Specify exact Phase 44 implementation design for F197.2:
   - Kerr-Newman-Kiselev 23-Dark-Energy PCQTGBDDDDHKMAEETUV Elliptic-Hypergeometric-Askey-Wilson ($w = -25/3$, $k_{\text{daha}} = 0.15$) DAHA L3 in `fast_lob_engine.py`
   - Maker floor $1 \times 10^{-16}$, dark ATS 99.9999999995%, Anti-Gaming MinQty 99.9999999999% in `smart_order_router.py`
   - Preemptive tick shading coefficient $-0.99999999995 \cdot \text{spread} \cdot (h - 0.0003)$ in `oms_engine.py`
   - Target slippage & friction: $\le 0.000005$ bps
   - Specify all method names, aliases, signatures, line numbers, and backward compatibility hooks.

## Output
Write your report to: `d:\Finance\code\stock\.agents\explorer_phase44_survey_oms\handoff.md` and send a completion message.

## 2026-09-15T13:41:57Z

<USER_REQUEST>
You are Survey Explorer (Microstructure & OMS Scope) for Phase 44 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\explorer_phase44_survey_oms
Read your instructions at: d:\Finance\code\stock\.agents\explorer_phase44_survey_oms\DISPATCH.md
Authoritative request is at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)

Scope: ONLY 3 files:
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- Reference: `tests/test_phase43_oms.py`

Investigate Phase 43 implementation and specify exact Phase 44 designs for F197.2:
- KNK 23-Dark-Energy DAHA L3 (w = -25/3, k_daha = 0.15) in fast_lob_engine.py
- Maker floor 1e-16, dark ATS 99.9999999995%, Anti-Gaming 99.9999999999% in smart_order_router.py
- Preemptive tick shading -0.99999999995 * spread * (h - 0.0003) in oms_engine.py (slippage & friction <= 0.000005 bps)

Write your report to `d:\Finance\code\stock\.agents\explorer_phase44_survey_oms\handoff.md` and use send_message to report completion.
</USER_REQUEST>
