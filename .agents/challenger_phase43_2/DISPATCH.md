# DISPATCH: Challenger 2 (OMS & Benchmark Adversarial Challenger)

## Working Directory
d:\Finance\code\stock\.agents\challenger_phase43_2

## Authoritative User Request
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

## Objective & Scope
Adversarially challenge and stress-test the Phase 43 implementations of:
1. **Microstructure OMS Specialist (Milestone R3)**:
   - `trading_system/src/core/fast_lob_engine.py`: F193.2 KNK 22-Dark-Energy DAHA L3 hydrodynamics ($w = -8.0$, $k_{\text{daha}} = 0.14$).
   - `trading_system/src/execution/smart_order_router.py`: `is_phase43`, dark cap at 0.99999999999, lit maker floor contracted to $1 \times 10^{-15}$ under extreme toxicity, Anti-Gaming MinQty cap at 0.999999999998.
   - `trading_system/src/execution/oms_engine.py`: Preemptive micro-tick shading when $h > 0.0004$.
2. **Quant Verification Specialist (Milestone R4)**:
   - `trading_system/scripts/benchmark_phase43_quant_performance.py`: baseline continuity, 6 acceptance criteria, 5 markets, 3 markdown tables.

## Stress-Testing Directives
- Write property-based oracles, extreme input generators, and adversarial stress tests:
  - OMS: Test order router with orders of size 1 share, $10^9$ shares, $10^{15}$ shares (quadrillion). Test maker floor precision under arbitrary $\gamma_{\text{toxic}} \in [0, 1]$. Test anti-gaming MinQty across extreme manipulation scores. Test Hawkes tick shading with extreme jump intensities ($h \to \infty, h \le 0$).
  - Benchmark: Test benchmark execution under varied environments, assert that all 6 target assertions fire properly if values are manipulated, verify markdown table parsing integrity.
- Execute your test harness using `.venv/Scripts/python.exe`.
- Deliver verdict: APPROVE or REQUEST_CHANGES in `d:\Finance\code\stock\.agents\challenger_phase43_2\handoff.md`.
- Send completion message to orchestrator.

## 2026-09-15T06:53:09Z
You are Challenger 2 (OMS & Benchmark Adversarial Challenger) for Phase 43 Quant Enhancement.
Your working directory is: d:\Finance\code\stock\.agents\challenger_phase43_2
Read your dispatch instructions at:
d:\Finance\code\stock\.agents\challenger_phase43_2\DISPATCH.md
Read the authoritative user request at:
d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-15T06:20:40Z)

Adversarially stress-test:
- OMS: Fast LOB hydrodynamics on extreme queue depths/cancellations, SmartOrderRouter on 1-share vs 10^15-share orders, maker floor precision at 1e-15 under extreme toxicity, Anti-Gaming MinQty at 0.999999999998, preemptive tick shading under extreme jump hazard.
- Benchmark: Verify that script asserts fail if target thresholds are violated, verify report table parsing.

Write and run your adversarial test harness using .venv/Scripts/python.exe.
Deliver verdict: APPROVE or REQUEST_CHANGES in:
d:\Finance\code\stock\.agents\challenger_phase43_2\handoff.md
Send a completion message back to orchestrator.
