# DISPATCH: Explorer 3 — Microstructure OMS & Benchmark Architecture (Phase 40)

## Working Directory
d:\Finance\code\stock\.agents\explorer_quant_phase40_survey3

## Mandatory References
1. `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-14T05:30:34Z`)
2. `d:\Finance\code\stock\.agents\orchestrator_quant_phase40_1\DISPATCH.md`
3. `d:\Finance\code\stock\PROJECT.md`

## Target Files to Inspect
- `src/core/fast_lob_engine.py`
- `src/execution/smart_order_router.py`
- `src/execution/oms_engine.py`
- `trading_system/scripts/benchmark_phase39_quant_performance.py`
- `tests/test_phase39_oms.py`, `tests/test_phase39_benchmark.py`

## Investigation Scope
1. **F181.2: KNK 19-Dark-Energy PCQTGBDDDDHKMAE Elliptic Macdonald-Koornwinder-Askey-Wilson DAHA L3 Hydrodynamics**:
   - Parameters: $w = -7.0$, $k_{\text{elliptic}} = 0.11$.
   - Inspect how Phase 39 implemented F177.2 in `src/core/fast_lob_engine.py`.
   - Determine how the hydrodynamics arrival intensity and pricing equations are adapted.
2. **Execution OMS & Smart Order Router Parameters**:
   - `src/execution/smart_order_router.py`: maker floor $1 \times 10^{-12}$.
   - `src/execution/oms_engine.py`:
     - Preemptive tick shading: $-0.999999999 \cdot \text{spread} \cdot (h - 0.0007)$
     - Darkpool routing: 99.99999999% ATS
     - Anti-Gaming MinQty: 99.999999998%
   - Verify that execution slippage $\le 0.00008$ bps, friction costs $\le 0.00008$ bps.
3. **F182: Benchmark Engine & Multi-Market Comparison**:
   - Inspect `trading_system/scripts/benchmark_phase39_quant_performance.py`.
   - Note Phase 39 baseline numbers (Net Return 146.99%, Sharpe 26.78, MDD -0.00005%, Friction 0.00010 bps, Slippage 0.00010 bps, Top-Decile 121.82%).
   - Plan `benchmark_phase40_quant_performance.py`:
     - 5 markets (SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ).
     - 15 core quantitative metrics.
     - 3 standard Markdown comparison tables ([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표).
     - 4 destination report files:
       - `reports/quant_benchmark_comparison_phase40.md`
       - `trading_system/result/quant_benchmark_comparison_phase40.md`
       - `trading_system/reports/quant_benchmark_comparison_phase40.md`
       - `reports/quant_benchmark_comparison.md`
     - Documentation updates in `AGENTS.md` (Key Files & Requirements History R56) and `PROJECT.md`.
4. **Testing & Validation Plan**:
   - Outline unit tests to be written in `tests/test_phase40_oms.py` and `tests/test_phase40_benchmark.py`.

## Output Deliverable
Write your comprehensive survey findings and detailed implementation blueprint in `d:\Finance\code\stock\.agents\explorer_quant_phase40_survey3\handoff.md`.
Then send a message back to orchestrator (`d589c15d-8af5-4fdc-85b9-702f9839272f`) notifying completion.

## 2026-09-14T05:33:23Z
You are Explorer 3 for Phase 40 Quant Enhancement. Your working directory is d:\Finance\code\stock\.agents\explorer_quant_phase40_survey3. Read your dispatch file at d:\Finance\code\stock\.agents\explorer_quant_phase40_survey3\DISPATCH.md and the authoritative user request at d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md (Header: ## 2026-09-14T05:30:34Z). Inspect src/core/fast_lob_engine.py, src/execution/smart_order_router.py, src/execution/oms_engine.py, trading_system/scripts/benchmark_phase39_quant_performance.py, tests/test_phase39_oms.py, and tests/test_phase39_benchmark.py. Investigate F181.2 (KNK 19-Dark-Energy Elliptic Macdonald-Koornwinder-Askey-Wilson DAHA L3 hydrodynamics with w = -7.0, k_elliptic = 0.11), maker floor 1e-12, tick shading -0.999999999 * spread * (h - 0.0007), darkpool ATS 99.99999999%, anti-gaming MinQty 99.999999998%, and F182 benchmark engine architecture. Write a detailed blueprint and handoff report to d:\Finance\code\stock\.agents\explorer_quant_phase40_survey3\handoff.md. When complete, send a message back to orchestrator (ID: d589c15d-8af5-4fdc-85b9-702f9839272f).

