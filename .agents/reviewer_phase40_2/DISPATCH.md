# DISPATCH: Reviewer 2 — OMS & Benchmark Modules (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\reviewer_phase40_2

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\worker_quant_phase40_oms\handoff.md`
3. `d:\Finance\code\stock\.agents\worker_quant_phase40_bench\handoff.md`
4. `d:\Finance\code\stock\PROJECT.md`

## Review Scope
1. Review code in:
   - `src/core/fast_lob_engine.py`
   - `src/execution/smart_order_router.py`
   - `src/execution/oms_engine.py`
   - `trading_system/scripts/benchmark_phase40_quant_performance.py`
   - `reports/quant_benchmark_comparison_phase40.md` and mirror files
   - `AGENTS.md` and `PROJECT.md`
2. Verify:
   - F181.2 KNK 19-Dark-Energy Elliptic DAHA L3 hydrodynamics ($w = -7.0$, $k_{\text{elliptic}} = 0.11$) and all aliases.
   - Lit maker floor contracted to $1 \times 10^{-12}$, Anti-Gaming MinQty cap $99.999999998\%$, dark routing $99.99999999\%$.
   - Dual preemptive micro-tick shading in `ExecutionOMSEngine` and `AlmgrenChrissScheduler` for $h > 0.0007$.
   - F182 benchmark numbers replicating Phase 39 baseline and meeting all 6 Phase 40 criteria.
   - 3 comparison tables across all 4 report destinations.
   - Documentation synchronization in `AGENTS.md` (Key Files, R56) and `PROJECT.md`.
3. Run test suites:
   `$env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_oms.py tests/test_phase40_benchmark.py -v`
   Verify 100% pass rate.
4. Output: Write your structured review report to `d:\Finance\code\stock\.agents\reviewer_phase40_2\handoff.md` with verdict: `APPROVE` or `REQUEST_CHANGES`.
Send a message back to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`).

## 2026-09-14T05:49:22Z
You are Reviewer 2 for Phase 40 Quant Enhancement. Your working directory is d:\Finance\code\stock\.agents\reviewer_phase40_2. Read your dispatch instructions at d:\Finance\code\stock\.agents\reviewer_phase40_2\DISPATCH.md, the authoritative user request at d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T05:30:34Z), Worker 3's report at d:\Finance\code\stock\.agents\worker_quant_phase40_oms\handoff.md, and Worker 4's report at d:\Finance\code\stock\.agents\worker_quant_phase40_bench\handoff.md.

Review Scope:
1. Verify Microstructure OMS (src/core/fast_lob_engine.py, src/execution/smart_order_router.py, src/execution/oms_engine.py): F181.2 KNK 19-Dark-Energy Elliptic DAHA (w = -7.0, k_elliptic = 0.11), maker floor 1e-12, dark routing 99.99999999%, anti-gaming 99.999999998%, preemptive tick shading -0.999999999 * spread * (h - 0.0007).
2. Verify Benchmark Engine (trading_system/scripts/benchmark_phase40_quant_performance.py), 3 comparison tables, 4 synchronized report paths, AGENTS.md, PROJECT.md.
3. Run test suites: $env:BYPASS_TORCH="1"; python -m pytest tests/test_phase40_oms.py tests/test_phase40_benchmark.py -v.
4. Deliver your review report with verdict (APPROVE or REQUEST_CHANGES) to d:\Finance\code\stock\.agents\reviewer_phase40_2\handoff.md and notify orchestrator (ID: d589c15d-8af5-4fdc-85b9-702f9839272f).
