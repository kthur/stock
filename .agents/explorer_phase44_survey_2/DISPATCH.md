# Task Assignment: Phase 44 Survey Explorer 2 — Risk Allocation & Microstructure OMS Scope

## Identity & Working Directory
- Role: Survey Explorer 2 (Risk Allocation & Microstructure OMS Investigation)
- Working Directory: d:\Finance\code\stock\.agents\explorer_phase44_survey_2

## Context & Inputs
- Authoritative Request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)
- Orchestrator Dispatch: d:\Finance\code\stock\.agents\orchestrator_quant_phase44_1\DISPATCH.md
- Scope Document: d:\Finance\code\stock\PROJECT.md

## Target Files to Investigate
- `src/risk/unified_portfolio_allocator.py`
- `src/risk/portfolio_allocator.py`
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- Relevant tests: `tests/test_phase43_*.py`

## Investigation Objectives
1. Inspect how Phase 43 (F193.1, F193.2) is currently implemented:
   - Lurie-W-Algebra Motivic Barycenter in `unified_portfolio_allocator.py` (version >= 43)
   - 39th-cumulant Trans-Singular-W-Algebra EVaR in `portfolio_allocator.py`
   - KNK 22-Dark-Energy DAHA L3 in `fast_lob_engine.py`
   - Maker floor (1e-15), dark ATS (99.999999999%), anti-gaming (99.9999999998%) in `smart_order_router.py`
   - Preemptive tick shading in `oms_engine.py`
2. Specify exact implementation design for Phase 44:
   - F197.1: Lurie-Virasoro-Whittaker Motivic Fisher-Rao manifold barycenter blending ($\mu_{\text{lvw}} = [3.40, 2.65, 2.60, 3.95]$) in `unified_portfolio_allocator.py` (version >= 44 branch)
   - 40th-cumulant Trans-Singular-Virasoro EVaR ($40! \approx 8.159 \times 10^{47}$, $\xi_{\text{vir}} = 0.9999995$) in `portfolio_allocator.py`
   - F197.2: Kerr-Newman-Kiselev 23-Dark-Energy PCQTGBDDDDHKMAEETUV Elliptic-Hypergeometric-Askey-Wilson ($w = -25/3$, $k_{\text{daha}} = 0.15$) DAHA L3 in `fast_lob_engine.py`
   - Maker floor $1 \times 10^{-16}$, dark ATS 99.9999999995%, Anti-Gaming MinQty 99.9999999999% in `smart_order_router.py`
   - Preemptive tick shading coefficient $-0.99999999995 \cdot \text{spread} \cdot (h - 0.0003)$ in `oms_engine.py` (target slippage & friction $\le 0.000005$ bps)
3. Document exact function names, signatures, math formulas, line numbers, and backward compatibility hooks.

## Output
Write your comprehensive investigation report to:
`d:\Finance\code\stock\.agents\explorer_phase44_survey_2\handoff.md`
and send a completion message back with summary.

## 2026-09-15T12:43:16Z
You are Survey Explorer 2 for Phase 44 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\explorer_phase44_survey_2
Read your instructions at: d:\Finance\code\stock\.agents\explorer_phase44_survey_2\DISPATCH.md
Also read the authoritative user request at: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T12:29:31Z)

Scope:
Investigate `src/risk/unified_portfolio_allocator.py`, `src/risk/portfolio_allocator.py`, `src/core/fast_lob_engine.py`, `src/execution/smart_order_router.py`, and `src/execution/oms_engine.py` for how Phase 43 (F193.1, F193.2) is implemented, and specify the exact Phase 44 design for:
- F197.1: Lurie-Virasoro-Whittaker Motivic Fisher-Rao manifold barycenter blending (mu_lvw = [3.40, 2.65, 2.60, 3.95]) in unified_portfolio_allocator.py (version >= 44); 40th-cumulant Trans-Singular-Virasoro EVaR (40! ~ 8.159e47, xi_vir = 0.9999995) in portfolio_allocator.py (MDD <= -0.00001%, Sharpe >= 29.75)
- F197.2: KNK 23-Dark-Energy PCQTGBDDDDHKMAEETUV Elliptic-Hypergeometric-Askey-Wilson (w = -25/3, k_daha = 0.15) DAHA L3 in fast_lob_engine.py; maker floor 1e-16, dark ATS 99.9999999995%, Anti-Gaming MinQty 99.9999999999% in smart_order_router.py; preemptive tick shading -0.99999999995 * spread * (h - 0.0003) in oms_engine.py (slippage & friction <= 0.000005 bps)

Write your findings to `d:\Finance\code\stock\.agents\explorer_phase44_survey_2\handoff.md` and use send_message to report back.
