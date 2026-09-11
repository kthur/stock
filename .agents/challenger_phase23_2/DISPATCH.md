# Challenger 2 Dispatch: L3 OMS & Multi-Market Benchmark Adversarial Testing

## Assigned Scope
Empirically challenge and stress test R3 (Microstructure OMS & KNK-P Hydrodynamics) and R4 (5-Market Benchmark & 6 Acceptance Targets).

## Reference Documents
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Read Section ## 2026-09-11T07:03:36Z before starting)
- `d:\Finance\code\stock\AGENTS.md`
- `d:\Finance\code\stock\.agents\worker_quant_phase23_oms\handoff.md`
- `d:\Finance\code\stock\.agents\worker_quant_phase23_bench\handoff.md`

## Instructions
1. Design and execute adversarial stress tests against:
   - F113.2 Kerr-Newman-Kiselev Quintessence-Phantom L3 Hydrodynamics: metric horizon roots, phantom energy equation of state ($w_p = -4/3$, $\rho_p = 2 c_p r$), repulsive tidal force clamping, frame dragging, conformal factor boundaries, and 99.995% dark ATS cap precision.
   - F113.2.2 Micro-Friction: maker floor contraction under toxic flow down to $0.000001$, Anti-Gaming MinQty boundary $0.99999$, bid/ask preemptive micro-tick shading symmetry at $h > 0.035$.
   - F114 Benchmark Integrity: verify no hardcoding or dummy facades in `benchmark_phase23_quant_performance.py`, verify that `agg_p23` genuinely satisfies all 6 acceptance criteria, verify that [표 3] attribution sums identically to compound delta.
2. Run tests:
   `.venv\Scripts\python.exe -m pytest tests/test_phase23_microstructure_oms.py tests/test_phase23_quant_performance.py -v`
3. Deliver a verdict: `APPROVE` or `REJECT` based on empirical correctness in `handoff.md`.

## 2026-09-11T07:32:23Z
You are Challenger 2 for Phase 23 Full Team Quantitative Enhancement.
Your working directory: d:\Finance\code\stock\.agents\challenger_phase23_2
Dispatch file: d:\Finance\code\stock\.agents\challenger_phase23_2\DISPATCH.md
Original user request: d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Read Section ## 2026-09-11T07:03:36Z before starting)
Project rules: d:\Finance\code\stock\AGENTS.md
Worker 3 handoff: d:\Finance\code\stock\.agents\worker_quant_phase23_oms\handoff.md
Worker 4 handoff: d:\Finance\code\stock\.agents\worker_quant_phase23_bench\handoff.md

Instructions:
1. Adversarially challenge R3 (F113.2, F113.2.2) and R4 (F114).
2. Stress test KNK-P double dark energy equations of state (w_p = -4/3, rho_p = 2 c_p r), tidal force limits, maker floor 0.000001, Anti-Gaming MinQty 0.99999, bid/ask tick shading symmetry at h > 0.035, and benchmark metrics empirical validity.
3. Run pytest: `.venv\Scripts\python.exe -m pytest tests/test_phase23_microstructure_oms.py tests/test_phase23_quant_performance.py -v`.
4. Deliver a verdict (APPROVE or REJECT) in `handoff.md` and send a message.
