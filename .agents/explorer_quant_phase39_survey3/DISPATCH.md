# DISPATCH: Explorer 3 (Microstructure OMS & Benchmark Survey)

## Identity
- Role: Codebase Researcher (Microstructure OMS & Benchmark)
- Archetype: teamwork_preview_explorer
- Working directory: `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3`
- Original request: `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Header: `## 2026-09-13T20:29:00Z`)

## Objectives
1. Inspect Microstructure & OMS code:
   - `src/core/fast_lob_engine.py`: Kerr-Newman-Kiselev 18-Dark-Energy PCQTGBDDDDHKMA Dunkl-Hecke-Cherednik-Kostka-Macdonald-Askey-Wilson ($w_{\text{pcqtgbddddhkma}} = -20/3$, $k_{\text{askey}} = 0.10$) DAHA L3 orderbook hydrodynamics model (F177.2).
   - `src/execution/smart_order_router.py`: maker floor $0.000000000005$.
   - `src/execution/oms_engine.py`: tick shading coefficient $-0.999999998 \cdot \text{spread} \cdot (h - 0.0008)$, darkpool ATS routing 99.99999998%, anti-gaming MinQty 99.999999995%.
   - Targets: friction $\le 0.00015$ bps, slippage $\le 0.0001$ bps.
2. Inspect Benchmark & Verification code:
   - `trading_system/scripts/benchmark_phase38_quant_performance.py` (and previous scripts) to understand the structure of the 15 quant metrics, the 5 markets (KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000), the 3 standard comparison tables ([표 1] 15대 종합 지표 비교표, [표 2] 5대 시장별 성과표, [표 3] 전략 팩터 기여도표), and target values.
   - Requirements for F178 in `trading_system/scripts/benchmark_phase39_quant_performance.py`:
     - Net Expected Return: >= 146.95% (target: 146.89% ~ 146.99%)
     - Sharpe Ratio: >= 26.75 (target: 26.78)
     - MDD: <= -0.00008% (target: -0.00005%)
     - Friction: <= 0.00015 bps (target: 0.0001 bps)
     - Slippage: <= 0.0001 bps
     - Top-Decile Spread: >= 121.8% (target: 121.82%)
   - Report synchronization paths:
     - `reports/quant_benchmark_comparison_phase39.md`
     - `trading_system/result/quant_benchmark_comparison_phase39.md`
     - `trading_system/reports/quant_benchmark_comparison_phase39.md`
     - `reports/quant_benchmark_comparison.md`
   - `AGENTS.md` (Key Files & Requirements History R55) and `PROJECT.md` update requirements.
3. Check `tests/test_phase38_oms.py` and `tests/test_phase38_benchmark.py` to formulate test design for Phase 39.
4. Output a comprehensive report to `d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3\handoff.md`.

## 2026-09-13T20:31:03Z
You are explorer_quant_phase39_survey3 (Microstructure OMS & Benchmark Researcher).
Working directory: d:\Finance\code\stock\.agents\explorer_quant_phase39_survey3
Task:
1. Inspect Microstructure & OMS
2. Inspect Benchmark & Verification
3. Inspect tests/test_phase38_oms.py and tests/test_phase38_benchmark.py and formulate test specifications
4. Write full findings to handoff.md, update progress.md, send completion message.
