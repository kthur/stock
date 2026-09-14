# DISPATCH: Challenger 2 — Adversarial Stress Test: OMS & Benchmark Modules (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\challenger_phase40_2

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\worker_quant_phase40_oms\handoff.md`
3. `d:\Finance\code\stock\.agents\worker_quant_phase40_bench\handoff.md`
4. `d:\Finance\code\stock\PROJECT.md`

## Challenge Scope
Empirically stress test Phase 40 Microstructure OMS and Benchmark modules:
1. **L3 Hydrodynamics & Order Routing Stress**:
   - `FastOrderBookMatchingEngine`: massive order book depth, inverted book, zero spread, zero volume.
   - `SmartOrderRouter`: order quantities of $10^{15}$, single share orders, extreme Hawkes cross-excitation intensity ($h = 100.0$), zero toxicity. Verify maker ratio floor strictly respects $1 \times 10^{-12}$ and dark routing caps at $0.9999999999$.
   - `ExecutionOMSEngine` & `AlmgrenChrissScheduler`: micro-tick shading consistency across negative and positive spreads, infinite/NaN intensity.
2. **Benchmark Verification & Metric Rigor**:
   - Re-calculate 5-market compound aggregates independently from raw tables.
   - Verify that all 6 target assertions in `benchmark_phase40_quant_performance.py` are mathematically sound, non-tautological, and that reports are completely synchronized across all 4 destinations.
3. Run or write adversarial stress scripts as needed.
4. Output: Write your adversarial challenge report to `d:\Finance\code\stock\.agents\challenger_phase40_2\handoff.md` with verdict: `APPROVE` or `REJECT`.
Send a message back to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`).

## 2026-09-14T05:49:22Z
You are Challenger 2 for Phase 40 Quant Enhancement. Your working directory is d:\Finance\code\stock\.agents\challenger_phase40_2. Read your dispatch instructions at d:\Finance\code\stock\.agents\challenger_phase40_2\DISPATCH.md, the authoritative user request at d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T05:30:34Z), and Worker 3 & 4 reports.

Challenge Scope:
Adversarially stress test OMS and Benchmark modules:
1. FastOrderBookMatchingEngine with deep/inverted books, zero spread, high queue acceleration.
2. SmartOrderRouter with order sizes 10^15, single share, Hawkes toxicity h = 100.0, maker floor 1e-12 verification.
3. ExecutionOMSEngine & AlmgrenChrissScheduler dual tick shading under extreme spreads and intensities.
4. Independent recalculation of 5-market benchmark aggregations, verifying all 6 targets and 4 report files synchronization.
5. Deliver challenge report with verdict (APPROVE or REJECT) to d:\Finance\code\stock\.agents\challenger_phase40_2\handoff.md and notify orchestrator (ID: d589c15d-8af5-4fdc-85b9-702f9839272f).

